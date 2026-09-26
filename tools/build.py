#!/usr/bin/env python3
"""Build The Library.

    python3 tools/build.py            # rebuild every page and the search index
    python3 tools/build.py --pages    # pages only (fast)
    python3 tools/build.py --check    # validate without writing

Sources of truth
  library.json              catalogue: shelves, cards, series, site metadata
  <book>/book.json          one reader: titles, languages, navigation, downloads, reviewer settings
  <book>/index.html         the book text lives between the BOOK-CONTENT markers; everything
                            around it is regenerated from templates here
  assets/                   shared CSS and JavaScript

The output is committed, so GitHub Pages serves the repository as-is. Standard library only.
"""
import argparse, hashlib, html, json, os, re, sys
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

START, END = '<!-- BOOK-CONTENT:START -->', '<!-- BOOK-CONTENT:END -->'
esc = lambda s: html.escape(str(s or ''), quote=True)


def read(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()


def write(path, text, check=False):
    full = os.path.join(ROOT, path)
    old = open(full, encoding='utf-8').read() if os.path.exists(full) else None
    if old == text:
        return False
    if not check:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            f.write(text)
    return True


def load_json(path):
    return json.loads(read(path))


# --------------------------------------------------------------------------- assets
_hashes = {}


def asset(name, prefix):
    """URL for a file under the repository root, with a content hash for cache busting."""
    if name not in _hashes:
        with open(os.path.join(ROOT, name), 'rb') as f:
            _hashes[name] = hashlib.sha1(f.read()).hexdigest()[:10]
    return f'{prefix}{name}?v={_hashes[name]}'


ICONS = {
    'sidebar': '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M9.5 4.5v15"/>',
    'menu': '<path d="M4 7h16M4 12h16M4 17h16"/>',
    'close': '<path d="M6 6l12 12M18 6 6 18"/>',
    'search': '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/>',
    'back': '<path d="M19 12H5M11 18l-6-6 6-6"/>',
    'arrow-right': '<path d="M5 12h14M13 6l6 6-6 6"/>',
    'arrow-down': '<path d="M12 5v14M6 13l6 6 6-6"/>',
    'arrow-up-right': '<path d="M7 17 17 7M9 7h8v8"/>',
    'download': '<path d="M12 4v11M7 10l5 5 5-5M5 19h14"/>',
    'review': '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/>',
    'check': '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.5 12h-2M21.5 12h-2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/>',
    'moon': '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/>',
    'auto': '<circle cx="12" cy="12" r="8"/><path d="M12 4v16" /><path d="M12 4a8 8 0 0 1 0 16Z" fill="currentColor" stroke="none"/>',
    'type': '<path d="M3 19 8 6l5 13M4.8 14.5h6.4"/><path d="M14.5 19l3.5-9 3.5 9M15.6 16h4.8"/>',
    'chevron': '<path d="m9 6 6 6-6 6"/>',
    'bookmark': '<path d="M7 4h10v16l-5-3.5L7 20V4Z"/>',
    'book': '<path d="M12 6.5C9.5 5 6.5 4.5 3.5 5v13c3-.5 6 0 8.5 1.5 2.5-1.5 5.5-2 8.5-1.5V5c-3-.5-6 0-8.5 1.5Zm0 0V19.5"/>',
    'exit': '<path d="M15 12H4M9 7l-5 5 5 5M13 4h6v16h-6"/>',
    'list': '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r=".6" fill="currentColor"/><circle cx="4.5" cy="12" r=".6" fill="currentColor"/><circle cx="4.5" cy="18" r=".6" fill="currentColor"/>',
}


def icon_sprite(names):
    body = ''.join(f'<symbol id="i-{n}" viewBox="0 0 24 24">{ICONS[n]}</symbol>' for n in names)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute" aria-hidden="true">{body}</svg>'


def icon(name, cls='i'):
    return f'<svg class="{cls}" aria-hidden="true"><use href="#i-{name}"/></svg>'


LOGO = ('<svg viewBox="0 0 32 32" width="28" height="28" fill="none" aria-hidden="true">'
        '<path d="M16 8C11 5 6 5 3 6v20c5-1 9 0 13 3 4-3 8-4 13-3V6c-3-1-8-1-13 2Z" stroke="currentColor" stroke-width="1.5"/>'
        '<path d="M16 8v21M7 11c2 0 4 .5 5 1M7 16c2 0 4 .5 5 1M21 12c1-1 3-1 4-1M21 17c1-1 3-1 4-1" stroke="currentColor" stroke-width="1.5"/></svg>')


def head(*, title, description, prefix, canonical, site, css, lang='en', extra='', boot='', og_type='website'):
    return f'''<!doctype html>
<html lang="{lang}" data-theme="light"{extra}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="theme-color" content="#f5f2eb">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:site_name" content="{esc(site['name'])}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="{asset('assets/library-mark.svg', prefix)}" type="image/svg+xml">
<script>{boot}</script>
{css}
'''


THEME_BOOT = ("(function(){var d=document.documentElement;try{var t=localStorage.getItem('minimal-library-theme');"
              "d.dataset.theme=t==='dark'||t==='light'?t:(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light')}catch(e){}})();")


# --------------------------------------------------------------------------- book content
SECTION_TOKEN = re.compile(r'<section\b[^>]*>|</section>')
VIEW_OPEN = re.compile(r'<div class="language-view" data-lang="(\w+)">')
VIEW_LOOSE = re.compile(r'<div\s+class="language-view"\s+data-lang="(\w+)"\s*>')
PAGER = re.compile(r'<nav[^>]*class="chapter-pager"[^>]*>.*?</nav>', re.S)


def attr(tag, name):
    m = re.search(r'\s%s="([^"]*)"' % re.escape(name), tag)
    return html.unescape(m.group(1)) if m else None


def parse_content(content):
    """Split book content into language views and their top-level sections (by offsets)."""
    views = []
    starts = list(VIEW_OPEN.finditer(content))
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(content)
        views.append({'lang': m.group(1), 'start': m.end(), 'end': end})
    for v in views:
        secs, depth, cur = [], 0, None
        for t in SECTION_TOKEN.finditer(content, v['start'], v['end']):
            if t.group(0).startswith('</'):
                depth -= 1
                if depth == 0 and cur:
                    cur['close'] = t.start()
                    secs.append(cur)
                    cur = None
            else:
                if depth == 0:
                    tag = t.group(0)
                    cur = {'open': t.start(), 'tag': tag, 'tag_end': t.end(), 'id': attr(tag, 'id'),
                           'key': attr(tag, 'data-key'), 'title': attr(tag, 'data-title')}
                depth += 1
        v['sections'] = secs
    return views


def pager_html(lang, prev, nxt):
    ar = lang == 'ar'
    words = ('السابق', 'التالي') if ar else ('Previous', 'Next')
    out = [f'<nav class="chapter-pager" aria-label="{"التنقل بين الفصول" if ar else "Chapter navigation"}">']
    if prev:
        out.append(f'<a class="pager-link prev" href="#{esc(prev["id"])}" data-key="{esc(prev["key"])}"><span>{words[0]}</span><strong>{esc(prev["title"])}</strong></a>')
    if nxt:
        out.append(f'<a class="pager-link next" href="#{esc(nxt["id"])}" data-key="{esc(nxt["key"])}"><span>{words[1]}</span><strong>{esc(nxt["title"])}</strong></a>')
    out.append('</nav>')
    return ''.join(out)


def normalise_content(content):
    """Idempotent clean-up: regenerate chapter pagers and make sure each section has a key."""
    content = PAGER.sub('', content)
    content = VIEW_LOOSE.sub(lambda m: f'<div class="language-view" data-lang="{m.group(1)}">', content)
    views = parse_content(content)
    edits = []  # (position, delete_len, insert)
    for v in views:
        secs = v['sections']
        for i, s in enumerate(secs):
            s['title'] = s['title'] or s['key'] or s['id']
            s['key'] = s['key'] or s['id']
            # character count, used by the reader for progress without measuring text at runtime
            chars = len(html.unescape(re.sub(r'<[^>]+>', '', content[s['tag_end']:s['close']])))
            tag = s['tag'] if ' data-key="' in s['tag'] else s['tag'][:-1] + f' data-key="{esc(s["id"])}">'
            tag = re.sub(r'\s+data-chars="\d*"', '', tag)
            new_tag = tag[:-1] + f' data-chars="{chars}">'
            if new_tag != s['tag']:
                edits.append((s['open'], len(s['tag']), new_tag))
        for i, s in enumerate(secs):
            prev = secs[i - 1] if i else None
            nxt = secs[i + 1] if i + 1 < len(secs) else None
            edits.append((s['close'], 0, pager_html(v['lang'], prev, nxt)))
    for pos, dl, ins in sorted(edits, key=lambda e: e[0], reverse=True):
        content = content[:pos] + ins + content[pos + dl:]
    return content, parse_content(content)


def book_content(path):
    page = read(os.path.join(path, 'index.html'))
    a, b = page.find(START), page.find(END)
    if a < 0 or b < 0:
        raise SystemExit(f'{path}/index.html has no BOOK-CONTENT markers')
    return page[a + len(START):b].strip()


def word_count(content, lang='en'):
    text = re.sub(r'<[^>]+>', ' ', content)
    return len(re.findall(r'\w+', html.unescape(text)))


# --------------------------------------------------------------------------- reader page
def nav_tree(items):
    """Turn a flat list with levels into nested nodes."""
    root = {'children': [], 'level': 0}
    stack = [root]
    for it in items:
        node = dict(it, children=[])
        while stack[-1]['level'] >= node['level']:
            stack.pop()
        stack[-1]['children'].append(node)
        stack.append(node)
    return root['children']


def render_toc(nodes, lang, collapse, uid):
    out = ['<ol>']
    for n in nodes:
        label = n.get('label') or n['title']
        link = f'<a href="#{esc(n["id"])}" data-title="{esc(n["title"])}">{esc(label)}</a>'
        if n['children']:
            uid[0] += 1
            list_id = f'toc-{lang}-{uid[0]}'
            open_ = not collapse
            toggle = (f'<button class="toc-toggle" type="button" aria-expanded="{str(open_).lower()}" aria-controls="{list_id}" '
                      f'aria-label="{esc(("أقسام " if lang == "ar" else "Sections in ") + n["title"])}">{icon("chevron")}</button>')
            sub = render_toc(n['children'], lang, collapse, uid).replace('<ol>', f'<ol id="{list_id}"{"" if open_ else " hidden"}>', 1)
            out.append(f'<li><div class="toc-row">{link}{toggle}</div>{sub}</li>')
        else:
            out.append(f'<li><div class="toc-row">{link}</div></li>')
    out.append('</ol>')
    return ''.join(out)


def L(d, lang):
    return (d or {}).get(lang) or (d or {}).get('en') or ''


def both(d, langs, tag='span', cls=''):
    """One element per language; the stylesheet shows the active one."""
    c = f' class="{cls}"' if cls else ''
    if len(langs) == 1:
        return esc(L(d, langs[0]))
    parts = []
    for l in langs:
        la = ' lang="ar" dir="rtl"' if l == 'ar' else ''
        parts.append(f'<{tag} data-l="{l}"{la}{c}>{esc(L(d, l))}</{tag}>')
    return ''.join(parts)


UI = {
    'library': {'en': 'Library', 'ar': 'المكتبة'},
    'search': {'en': 'Search the library', 'ar': 'البحث في المكتبة'},
    'back_search': {'en': 'Back to search results', 'ar': 'العودة إلى نتائج البحث'},
    'contents': {'en': 'Contents', 'ar': 'المحتويات'},
    'begin': {'en': 'Begin reading', 'ar': 'ابدأ القراءة'},
    'continue': {'en': 'Continue', 'ar': 'تابع القراءة'},
    'download': {'en': 'Download', 'ar': 'تنزيل'},
    'bilingual': {'en': 'Bilingual edition', 'ar': 'طبعة ثنائية اللغة'},
}


def render_reader(book, library, content, views, prefix, site):
    langs = book['languages']
    bilingual = len(langs) > 1
    series = None
    if book.get('series'):
        series = library['series'][book['series']['work']]
        vol = next(v for v in series['volumes'] if v['n'] == book['series']['volume'])
    title_en = book['title']['en']
    doc_titles = {l: f"{L(book['title'], l)}{' — ' + ('المجلد ' + str(vol['n']) if l == 'ar' else 'Volume ' + vol['roman']) if series else ''} — {'المكتبة' if l == 'ar' else site['name']}" for l in langs}
    canonical = site['baseUrl'] + book['path'] + '/'
    description = book.get('blurb') or book['description']

    # kicker
    if book.get('kicker'):
        kicker = book['kicker']
    elif series:
        kicker = {'en': f"Volume {vol['roman']} of {len(series['volumes'])} · Bilingual edition",
                  'ar': f"المجلد {vol['n']} من {len(series['volumes'])} · طبعة ثنائية اللغة"}
    elif bilingual:
        kicker = UI['bilingual']
    else:
        kicker = {'en': 'English translation'}

    first_ids = {v['lang']: v['sections'][0]['id'] for v in views if v['sections']}
    boot = ("(function(){var d=document.documentElement,s=localStorage;try{var t=s.getItem('minimal-library-theme');"
            "d.dataset.theme=t==='dark'||t==='light'?t:(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');"
            f"var L={json.dumps(langs)},p=new URLSearchParams(location.search).get('lang'),h=location.hash.slice(1,4),"
            f"l=L.indexOf(p)>=0?p:(L.indexOf(h.slice(0,2))>=0&&h[2]==='-'?h.slice(0,2):s.getItem({json.dumps(book['langKey'])}));"
            "if(L.indexOf(l)>=0){d.dataset.lang=l;d.lang=l}"
            "var z=+s.getItem('minimal-library-reader-size');if(z>=15&&z<=28)d.style.setProperty('--reader-size',z+'px');"
            "if(s.getItem('library-sidebar-collapsed')==='1')d.classList.add('sidebar-collapsed')}catch(e){}"
            # Lazy rendering of long books is measured to help in Chromium only (see reader.css).
            "if(navigator.userAgentData)d.classList.add('lazy-render')})();")
    data = {
        'slug': book['slug'], 'path': book['path'], 'root': prefix, 'langKey': book['langKey'], 'languages': langs,
        'titles': {l: L(book['title'], l) for l in langs}, 'documentTitles': doc_titles,
        'shortTitle': (title_en if not series else f"{series['title']} · Vol. {vol['roman']}"),
        'assets': {'reviewerJs': asset('assets/reviewer.js', prefix), 'reviewerCss': asset('assets/reviewer.css', prefix)},
        'review': book.get('review'),
        'sourceStore': book.get('sourceStore'),
    }
    jsonld = {
        '@context': 'https://schema.org', '@type': 'Book', 'name': title_en,
        'author': {'@type': 'Person', 'name': book['author']['en']},
        'inLanguage': langs, 'url': canonical, 'isAccessibleForFree': True,
        'publisher': {'@type': 'Organization', 'name': f"{site['name']} — {site['tagline']}"},
    }
    if series:
        jsonld['isPartOf'] = {'@type': 'BookSeries', 'name': series['title']}
        jsonld['name'] = f"{title_en} — Volume {vol['roman']}: {vol['title']}"

    parts = [head(title=doc_titles['en'], description=description, prefix=prefix, canonical=canonical, site=site,
                  og_type='book', boot=boot, extra=f' data-lang="{langs[0]}"',
                  css=f'<link rel="stylesheet" href="{asset("assets/base.css", prefix)}">\n<link rel="stylesheet" href="{asset("assets/reader.css", prefix)}">')]
    parts.append(f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>\n')
    parts.append(f'<script type="application/json" id="book-data">{json.dumps(data, ensure_ascii=False)}</script>\n')
    parts.append(f'<script src="{asset("assets/reader.js", prefix)}" defer></script>\n</head>\n<body class="reader">\n')
    parts.append(icon_sprite(['sidebar', 'close', 'search', 'back', 'arrow-down', 'download', 'review', 'check', 'sun', 'moon', 'auto', 'type', 'chevron', 'bookmark', 'exit', 'arrow-right']))
    parts.append(f'\n<a class="skip-link" href="#{esc(first_ids.get(langs[0], "top"))}">Skip to the text</a>\n<div id="progress" aria-hidden="true"></div>\n')

    # top bar
    badge = f'<span class="volume-badge">Vol. {vol["roman"]}</span>' if series else ''
    lang_btn = ''
    if bilingual:
        lang_btn = (f'<button class="icon-btn lang-btn reading-only" id="lang-toggle" type="button" aria-label="Read the Arabic original" title="Read the Arabic original">'
                    f'<span data-l="en" lang="ar">عربي</span><span data-l="ar" lang="en">EN</span></button>')
    review_btn = ''
    if book.get('review'):
        review_btn = (f'<button class="icon-btn review-enter-btn reading-only" id="review-enter" type="button" aria-label="Reviewer Mode: mark passages and suggest corrections" '
                      f'title="Reviewer Mode — mark passages and suggest corrections">{icon("review")}<span class="label">Review</span></button>'
                      f'<button class="review-count review-only" id="review-count" type="button" aria-label="0 passages selected"><span class="review-count-number">0</span><span class="review-count-label">selected</span></button>'
                      f'<button class="icon-btn outlined review-action-btn review-only" id="review-action" type="button" disabled>{icon("check")}<span class="review-action-label">Review selected</span></button>'
                      f'<button class="icon-btn review-exit-btn review-only" id="review-exit" type="button" aria-label="Exit Reviewer Mode" title="Exit Reviewer Mode">{icon("exit")}<span class="review-exit-label">Exit</span></button>')
    parts.append(f'''<header class="topbar">
<button class="icon-btn" id="menu-toggle" type="button" aria-controls="sidebar" aria-expanded="true" aria-label="Hide contents">{icon("sidebar")}</button>
<a class="icon-btn home-mark" href="{prefix}" aria-label="{esc(site['name'])} — all books" title="{esc(site['name'])} — all books">{LOGO}</a>
<div class="bar-title"><a class="book-link" href="#top" title="{esc(title_en)}">{both(book['title'], langs)}</a>{badge}<span class="current" data-fallback="{esc(title_en)}"></span></div>
<div class="controls">
<button class="icon-btn" id="settings-toggle" type="button" aria-controls="settings" aria-expanded="false" aria-label="Text size and theme" title="Text size and theme">{icon("type")}</button>
{lang_btn}{review_btn}
</div>
</header>
<div class="popover" id="settings" role="dialog" aria-label="Reading settings" hidden>
<section><h2>Text size</h2><div class="size-row"><button class="icon-btn size-small" id="size-down" type="button" aria-label="Smaller text">A</button><span class="size-range-wrap"><span class="size-default-notch" aria-hidden="true"></span><input type="range" id="size-range" min="15" max="28" step="1" value="19" aria-label="Text size"></span><button class="icon-btn size-large" id="size-up" type="button" aria-label="Larger text">A</button><span class="size-value" id="size-value" aria-hidden="true">19</span></div></section>
<section><h2>Theme</h2><div class="segmented" role="group" aria-label="Theme"><button type="button" data-theme-choice="auto" aria-pressed="true">{icon("auto")}Auto</button><button type="button" data-theme-choice="light" aria-pressed="false">{icon("sun")}Light</button><button type="button" data-theme-choice="dark" aria-pressed="false">{icon("moon")}Dark</button></div></section>
</div>
''')

    # sidebar
    home_label = book['home']['label']
    home = {'en': home_label, 'ar': 'المجلدات الأربعة' if series else UI['library']['ar']}
    side = [f'<aside class="sidebar" id="sidebar" aria-label="Book navigation">\n<nav class="side-links" aria-label="Library">'
            f'<a class="side-link accent" id="search-return" href="{prefix}search/" hidden>{icon("back")}<span>{both(UI["back_search"], langs)}</span></a>'
            f'<a class="side-link" href="{esc(book["home"]["href"])}">{icon("back")}<span>{both(home, langs)}</span></a>'
            f'<a class="side-link" href="{prefix}search/">{icon("search")}<span>{both(UI["search"], langs)}</span></a></nav>']
    if series:
        items = ''
        for v in series['volumes']:
            here = v['n'] == vol['n']
            href = './' if here else '../volume-%d/' % v['n']
            cur = ' aria-current="page"' if here else ''
            items += f'<li><a href="{href}"{cur} title="Volume {v["roman"]}: {esc(v["title"])}">{v["roman"]}</a></li>'
        side.append(f'<nav class="volume-switch" aria-label="Volumes"><span class="side-heading">{both({"en": "Volume", "ar": "المجلد"}, langs)}</span><ol>{items}</ol></nav>')
    side.append(f'<h2 class="side-heading" id="toc-heading">{both(UI["contents"], langs)}</h2>')
    total_items = sum(len(v) for v in book['nav'].values()) / max(1, len(book['nav']))
    for l in langs:
        tree = nav_tree(book['nav'][l])
        rtl = ' dir="rtl" lang="ar"' if l == 'ar' else ' dir="ltr"'
        side.append(f'<nav class="toc" data-l="{l}"{rtl} aria-labelledby="toc-heading">{render_toc(tree, l, total_items > 40, [0])}</nav>')
    dl = []
    for l in langs:
        f = book['downloads'].get(l)
        if f:
            name = {'en': 'English text', 'ar': 'Arabic original · النص العربي'}[l]
            dl.append(f'<li><a class="side-link" href="{esc(quote(f))}" download>{icon("download")}<span>{name}</span><small>.md</small></a></li>')
    if series:
        dl.append(f'<li><a class="side-link" href="../{esc(quote(series["zip"]))}" download>{icon("download")}<span>All four volumes</span><small>.zip</small></a></li>')
    side.append(f'<div class="side-downloads"><h2 class="side-heading">{both(UI["download"], langs)}</h2><ul>{"".join(dl)}</ul></div>\n</aside>\n<div class="sidebar-backdrop" aria-hidden="true"></div>\n')
    parts.append(''.join(side))

    # cover
    begin = ''
    for l in langs:
        if l in first_ids:
            dl_attr = f' data-l="{l}"' if bilingual else ''
            begin += f'<a class="btn primary" href="#{esc(first_ids[l])}"{dl_attr}>{esc(L(UI["begin"], l))}{icon("arrow-down")}</a>'
    note = ''
    if bilingual:
        note = ('<p class="cover-note"><span data-l="en">English translation with the Arabic original. Switch between them at any point with the <b lang="ar">عربي</b> button.</span>'
                '<span data-l="ar" lang="ar" dir="rtl">النص العربي الأصلي مع الترجمة الإنجليزية. يمكنك التبديل بينهما في أي وقت بزر <b lang="en">EN</b>.</span></p>')
    subtitle = f'<p class="subtitle">{both(book["subtitle"], langs)}</p>' if L(book['subtitle'], 'en') else ''
    parts.append(f'''<div class="layout">
<main class="main" id="main">
<section class="cover" id="top" aria-labelledby="book-title">
<div class="cover-inner">
<p class="eyebrow">{both(kicker, langs)}</p>
<h1 id="book-title">{both(book['title'], langs)}</h1>
{subtitle}
<p class="author">{both(book['author'], langs)}</p>
<p class="edition">{both(book['edition'], langs)}</p>
<div class="cover-actions">{begin}<a class="btn resume-btn" id="resume-btn" href="#" hidden>{icon("bookmark")}<span>{both(UI["continue"], langs)}</span><span class="where"></span></a></div>
{note}
</div>
</section>
''')
    parts.append(f'{START}\n{content}\n{END}\n')
    if series:
        prev = next((v for v in series['volumes'] if v['n'] == vol['n'] - 1), None)
        nxt = next((v for v in series['volumes'] if v['n'] == vol['n'] + 1), None)
        links = []
        if prev:
            links.append(f'<a class="prev" href="../volume-{prev["n"]}/"><span>Previous volume</span><strong>{prev["roman"]} · {esc(prev["title"])}</strong></a>')
        if nxt:
            links.append(f'<a class="next" href="../volume-{nxt["n"]}/"><span>Next volume</span><strong>{nxt["roman"]} · {esc(nxt["title"])}</strong></a>')
        parts.append(f'<nav class="series-pager" aria-label="Volumes">{"".join(links)}</nav>\n')
    byline = {l: f"{L(book['title'], l)} · {L(book['author'], l)}" + (f" · {'المجلد' if l == 'ar' else 'Volume'} {vol['n'] if l == 'ar' else vol['roman']}" if series else '') for l in langs}
    parts.append(f'<footer class="site-footer"><p>{both(byline, langs)}</p>'
                 f'<p><a href="{prefix}">{esc(site["name"])}</a> · {esc(site["tagline"])} · Free to read</p></footer>\n'
                 f'<div id="reviewer-workspace" class="reviewer-workspace"></div>\n</main>\n</div>\n</body>\n</html>\n')
    return ''.join(parts)


# --------------------------------------------------------------------------- library pages
def site_header(prefix, site, current=''):
    links = [('Collection', f'{prefix}#collection', 'collection'), ('Search', f'{prefix}search/', 'search'), ('About', f'{prefix}#about', 'about')]
    cur = ' aria-current="page"'
    nav = ''.join(f'<a href="{h}"{cur if k == current else ""}>{t}</a>' for t, h, k in links)
    return f'''<header class="site-top">
<a class="wordmark" href="{prefix}">{LOGO}<span><strong>{esc(site["name"])}</strong><small>{esc(site["tagline"])}</small></span></a>
<nav class="top-links" aria-label="Main">{nav}<button class="icon-btn outlined theme-toggle" id="theme-toggle" type="button" aria-label="Switch to dark theme" title="Switch to dark theme">{icon("moon")}</button></nav>
</header>'''


def site_footer(prefix, site):
    return f'''<footer class="site-foot">
<p><strong>{esc(site["name"])}</strong> · {esc(site["tagline"])}</p>
<p>Have a book in mind? Reach out on the community Discord to add it to the queue.</p>
<a href="#top">Back to top <span aria-hidden="true">↑</span></a>
</footer>'''


def reading_time(words):
    hours = words / 250 / 60
    if hours < 1:
        return f'{max(1, round(words / 250))} min read'
    return f'About {round(hours)} {"hour" if round(hours) == 1 else "hours"}'


def render_home(library, stats, site):
    prefix = ''
    books = library['books']
    shelves = library['shelves']
    langs_n = len({b['shelf'] for b in books})
    cards = {}
    for b in books:
        tag = f'<span class="card-tag">{esc(b["tag"])}</span>' if b.get('tag') else ''
        sub = f'<p class="card-sub">{esc(b["subtitle"])}</p>' if b.get('subtitle') else ''
        ar = f'<p class="card-ar" lang="ar" dir="rtl">{esc(b["arabicTitle"])}</p>' if b.get('arabicTitle') else ''
        vols = len(b['readers'])
        langs = 'English · <bdi lang="ar">العربية</bdi>' if b.get('arabicTitle') else 'English'
        meta = [f'{vols} volumes' if vols > 1 else '', langs, reading_time(stats[b['href']])]
        meta = ' <span aria-hidden="true">·</span> '.join(m for m in meta if m)
        cards.setdefault(b['shelf'], []).append(
            f'<li><a class="book-card" href="{esc(b["href"])}" data-progress-key="{esc(",".join(r.replace("/", "-") for r in b["readers"]))}">'
            f'<span class="card-top"><span class="card-no">№ {b["no"]:02d}</span>{tag}</span>'
            f'<span class="card-body"><h3 class="card-title">{esc(b["title"])}</h3>{sub}{ar}</span>'
            f'<span class="card-foot"><span class="card-author">{esc(b["author"])}</span><span class="card-meta">{meta}</span></span>'
            f'<span class="card-progress" hidden></span>'
            f'<span class="card-arrow" aria-hidden="true">{icon("arrow-up-right")}</span></a></li>')
    filters = [f'<button type="button" data-filter="all" aria-pressed="true">All works <span>{len(books)}</span></button>']
    shelf_html = []
    for s in shelves:
        n = len(cards.get(s['id'], []))
        if not n:
            continue
        filters.append(f'<button type="button" data-filter="{s["id"]}" aria-pressed="false">{esc(s["language"])} <span>{n}</span></button>')
        shelf_html.append(f'<section class="shelf" data-shelf="{s["id"]}" aria-labelledby="shelf-{s["id"]}"><div class="shelf-head"><h3 id="shelf-{s["id"]}">{esc(s["label"])}</h3><span>{esc(s["region"])}</span></div>'
                          f'<ul class="books" role="list">{"".join(cards[s["id"]])}</ul></section>')
    canonical = site['baseUrl']
    out = [head(title=f'{site["name"]} — {site["tagline"]}', description=site['description'], prefix=prefix, canonical=canonical, site=site, boot=THEME_BOOT,
                css=f'<link rel="stylesheet" href="{asset("assets/base.css", prefix)}">\n<link rel="stylesheet" href="{asset("assets/library.css", prefix)}">')]
    out.append(f'<script type="application/json" id="library-data">{json.dumps({"books": [{"href": b["href"], "title": b["title"], "readers": b["readers"]} for b in books]}, ensure_ascii=False)}</script>\n')
    out.append(f'<script src="{asset("assets/library.js", prefix)}" defer></script>\n</head>\n<body id="top">\n')
    out.append(icon_sprite(['moon', 'sun', 'search', 'arrow-up-right', 'arrow-right', 'bookmark', 'close']))
    out.append(f'''
<a class="skip-link" href="#collection">Skip to the collection</a>
<div class="shell">
{site_header(prefix, site)}
<main>
<section class="hero" aria-labelledby="library-title">
<div><p class="eyebrow">An Infrared Community initiative</p><h1 id="library-title">The Library<span class="title-stop">.</span></h1><p class="hero-caption">Across languages. Open to everyone.</p></div>
<div class="hero-intro"><p>Previously untranslated books from around the world, brought into modern, readable English.</p>
<form class="hero-search" action="search/" role="search"><label class="sr-only" for="hero-q">Search every book</label>{icon("search")}<input id="hero-q" name="q" type="search" placeholder="Search every book…" autocomplete="off" enterkeyhint="search"><button type="submit" class="icon-btn" aria-label="Search">{icon("arrow-right")}</button></form></div>
</section>
<section class="continue" id="continue" aria-labelledby="continue-title" hidden><div class="section-head"><h2 id="continue-title">Continue reading</h2></div><ul class="continue-list" role="list"></ul></section>
<section id="collection" class="collection" aria-labelledby="collection-title" tabindex="-1">
<div class="section-head"><h2 id="collection-title">The collection</h2><p>{len(books)} works <span aria-hidden="true">/</span> {langs_n} source languages <span aria-hidden="true">/</span> Free to read</p></div>
<div class="filters" role="group" aria-label="Filter by original language" hidden>{"".join(filters)}</div>
<p id="result-count" class="sr-only" role="status" aria-live="polite"></p>
<div class="shelves">{"".join(shelf_html)}</div>
</section>
<section class="about" id="about" aria-labelledby="about-title"><div><p class="eyebrow">A shared undertaking</p><h2 id="about-title">Discovering books.<br>Bridging civilisations.</h2></div>
<div class="about-copy"><p>The Library is an Infrared Community initiative to make previously untranslated books accessible to English readers.</p>
<p>Where available, the original text sits alongside the translation: switch between them while reading, or compare them passage by passage in Reviewer Mode. Every work is free to read, and each can be downloaded as Markdown for reading offline.</p>
<p class="credit">Translated by TMoC and other community members using frontier AI models.</p></div></section>
</main>
{site_footer(prefix, site)}
</div>
</body>
</html>
''')
    return ''.join(out)


def render_series(key, library, stats, site):
    s = library['series'][key]
    prefix = '../'
    card = next(b for b in library['books'] if b.get('series') == key)
    vols = []
    for v in s['volumes']:
        words = stats.get(v['path'], 0)
        vols.append(f'<li><a class="book-card volume-card" href="volume-{v["n"]}/" data-progress-key="{esc(v["path"].replace("/", "-"))}">'
                    f'<span class="card-top"><span class="card-no">Volume {v["roman"]}</span></span>'
                    f'<span class="card-body"><h3 class="card-title">{esc(v["title"])}</h3><p class="card-ar" lang="ar" dir="rtl">{esc(v["arabic"])}</p><p class="card-blurb">{esc(v["blurb"])}</p></span>'
                    f'<span class="card-foot"><span class="card-meta">English · <bdi lang="ar">العربية</bdi> <span aria-hidden="true">·</span> {reading_time(words)}</span></span>'
                    f'<span class="card-progress" hidden></span><span class="card-arrow" aria-hidden="true">{icon("arrow-up-right")}</span></a></li>')
    canonical = site['baseUrl'] + key + '/'
    title = f'{s["title"]} — {site["name"]}'
    out = [head(title=title, description=card['description'], prefix=prefix, canonical=canonical, site=site, boot=THEME_BOOT, og_type='book',
                css=f'<link rel="stylesheet" href="{asset("assets/base.css", prefix)}">\n<link rel="stylesheet" href="{asset("assets/library.css", prefix)}">')]
    out.append(f'<script src="{asset("assets/library.js", prefix)}" defer></script>\n</head>\n<body id="top">\n')
    out.append(icon_sprite(['moon', 'sun', 'arrow-up-right', 'arrow-right', 'download', 'back']))
    out.append(f'''
<a class="skip-link" href="#volumes">Skip to the volumes</a>
<div class="shell">
{site_header(prefix, site)}
<main>
<nav class="crumbs" aria-label="Breadcrumb"><a href="../">{icon("back", "i i-sm")}The collection</a></nav>
<section class="work-hero" aria-labelledby="work-title">
<p class="eyebrow">№ {card["no"]:02d} · Four-volume work · From the Arabic</p>
<h1 id="work-title">{esc(s["title"])}</h1>
<p class="work-ar" lang="ar" dir="rtl">{esc(s["arabicTitle"])}</p>
<p class="work-byline">{esc(s["author"])} <span aria-hidden="true">·</span> <span lang="ar">{esc(s["authorAr"])}</span></p>
<p class="work-lead">{esc(s["lead"])}</p>
<div class="work-actions"><a class="btn primary" href="volume-1/">Begin Volume I{icon("arrow-right")}</a><a class="btn" href="{esc(quote(s["zip"]))}" download>{icon("download")}All eight Markdown files <small>(.zip)</small></a></div>
</section>
<section class="volumes" id="volumes" aria-labelledby="volumes-title" tabindex="-1">
<div class="section-head"><h2 id="volumes-title">Four volumes, one work</h2><p>Read in order, or start where you need</p></div>
<ul class="books" role="list">{"".join(vols)}</ul>
</section>
</main>
{site_footer(prefix, site)}
</div>
</body>
</html>
''')
    return ''.join(out)


def render_search_page(library, site):
    prefix = '../'
    canonical = site['baseUrl'] + 'search/'
    out = [head(title=f'Search — {site["name"]}', description='Search every text in The Library: English translations, Arabic originals and German source text.',
                prefix=prefix, canonical=canonical, site=site, boot=THEME_BOOT,
                css=f'<link rel="stylesheet" href="{asset("assets/base.css", prefix)}">\n<link rel="stylesheet" href="{asset("assets/library.css", prefix)}">')]
    out.append(f'<script>window.SEARCH_WORKER={json.dumps(asset("search/search-worker.js", prefix).replace("../search/", ""))};</script>\n')
    out.append(f'<script src="{asset("assets/library.js", prefix)}" defer></script>\n<script src="{asset("search/search.js", prefix)}" defer></script>\n</head>\n<body id="top">\n')
    out.append(icon_sprite(['moon', 'sun', 'search', 'arrow-up-right', 'arrow-right', 'close']))
    out.append(f'''
<a class="skip-link" href="#search-results">Skip to results</a>
<div class="shell">
{site_header(prefix, site, 'search')}
<main>
<div class="search-heading"><p class="eyebrow">Explore the texts</p><h1>Follow a thought<span class="title-stop">.</span></h1><p>Find a passage anywhere in the Library’s translations and original texts.</p></div>
<form class="global-search" id="search-form" role="search"><label class="sr-only" for="query">Search all texts</label>{icon("search")}<input id="query" name="q" type="search" placeholder="A name, an idea, a phrase…" maxlength="120" autocomplete="off" enterkeyhint="search" spellcheck="false"><button type="button" class="icon-btn clear-btn" id="clear-query" aria-label="Clear search" hidden>{icon("close")}</button><button type="submit" class="btn primary">Search</button></form>
<div class="search-options"><div class="select-wrap"><label for="work-filter">Work</label><select id="work-filter"><option value="all">All works</option></select></div><div class="select-wrap"><label for="language-filter">Language</label><select id="language-filter"><option value="all">All languages</option><option value="en">English</option><option value="ar">Arabic</option><option value="de">German</option></select></div><p class="search-tip">Use “quotation marks” for an exact phrase.</p></div>
<section class="search-results" id="search-results" aria-labelledby="results-title" tabindex="-1">
<div class="results-top"><h2 id="results-title">A place to begin</h2><span id="result-summary" role="status" aria-live="polite" aria-atomic="true"></span></div>
<div class="search-progress" id="search-progress" hidden><span></span></div>
<div id="search-intro" class="search-intro"><h3>Where will a word take you?</h3><p>Search inside every book, then follow a passage back to its place in the text.</p>
<div class="suggestions" aria-label="Suggestions"><button type="button" data-query="Marx">Marx</button><button type="button" data-query="Hegel">Hegel</button><button type="button" data-query="Ibn Sina">Ibn Sīnā</button><button type="button" data-query="Karbala">Karbala</button><button type="button" data-query="&quot;social justice&quot;">“social justice”</button><button type="button" data-query="الحرية" lang="ar" dir="rtl">الحرية</button></div>
<p class="search-note">English, Arabic and German · Accents and Arabic vowel marks are optional · Arabic words match with or without prefixes like ال and و</p></div>
<div id="search-message" class="search-message" hidden></div><ol id="results-list" class="results-list"></ol><div class="more-row"><button id="load-more" class="btn" type="button" hidden>More passages</button></div>
</section>
<noscript><p class="search-message">Search needs JavaScript. You can still <a href="../">browse and read every book</a>.</p></noscript>
</main>
{site_footer(prefix, site)}
</div>
</body>
</html>
''')
    return ''.join(out)


def render_404(site):
    from urllib.parse import urlparse
    prefix = urlparse(site['baseUrl']).path or '/'  # 404 pages are served at any depth, so links are root-relative
    out = [head(title=f'Page not found — {site["name"]}', description='This page could not be found.', prefix=prefix,
                canonical=site['baseUrl'], site=site, boot=THEME_BOOT,
                css=f'<link rel="stylesheet" href="{asset("assets/base.css", prefix)}">\n<link rel="stylesheet" href="{asset("assets/library.css", prefix)}">')]
    out.append(f'<script src="{asset("assets/library.js", prefix)}" defer></script>\n</head>\n<body id="top">\n')
    out.append(icon_sprite(['moon', 'sun', 'search', 'arrow-right']))
    out.append(f'''<div class="shell">
{site_header(prefix, site)}
<main class="not-found">
<p class="eyebrow">404</p><h1>This page is not on the shelves<span class="title-stop">.</span></h1>
<p>The link may be old, or the page may have moved. Try the collection, or search every book.</p>
<form class="hero-search" action="{prefix}search/" role="search"><label class="sr-only" for="nf-q">Search every book</label>{icon("search")}<input id="nf-q" name="q" type="search" placeholder="Search every book…"><button type="submit" class="icon-btn" aria-label="Search">{icon("arrow-right")}</button></form>
<p><a class="btn" href="{prefix}">Browse the collection{icon("arrow-right")}</a></p>
</main>
{site_footer(prefix, site)}
</div>
</body>
</html>
''')
    return ''.join(out)


# --------------------------------------------------------------------------- validation
def validate(book, content, views, problems):
    ids = re.findall(r'\sid="([^"]+)"', content)
    seen, dups = set(), set()
    for i in ids:
        (dups if i in seen else seen).add(i)
    if dups:
        problems.append(f'{book["path"]}: duplicate ids {sorted(dups)[:5]}')
    for lang, items in book['nav'].items():
        for it in items:
            if it['id'] not in seen:
                problems.append(f'{book["path"]}: nav link #{it["id"]} ({lang}) has no target')
    for lang, f in book['downloads'].items():
        if not os.path.exists(os.path.join(ROOT, book['path'], f)):
            problems.append(f'{book["path"]}: download {f} is missing')
    have = {v['lang'] for v in views if v['sections']}
    for l in book['languages']:
        if l not in have:
            problems.append(f'{book["path"]}: no sections found for language {l}')
    for v in views:
        if v['lang'] not in book['languages']:
            problems.append(f'{book["path"]}: content has language {v["lang"]} not listed in book.json')
    for m in re.finditer(r'href="#([^"]+)"', content):
        if m.group(1) not in seen:
            problems.append(f'{book["path"]}: broken in-text link #{m.group(1)}')
            break


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pages', action='store_true', help='skip the search index')
    ap.add_argument('--check', action='store_true', help='validate and report, write nothing')
    args = ap.parse_args()

    library = load_json('library.json')
    site = library['site']
    readers = [r for b in library['books'] for r in b['readers']]
    problems, changed = [], []
    stats, corpus = {}, []
    for path in readers:
        book = load_json(os.path.join(path, 'book.json'))
        content, views = normalise_content(book_content(path))
        validate(book, content, views, problems)
        prefix = '../' * (path.count('/') + 1)
        page = render_reader(book, library, content, views, prefix, site)
        if write(os.path.join(path, 'index.html'), page, args.check):
            changed.append(path)
        en = next((v for v in views if v['lang'] == 'en'), None)
        stats[path] = word_count(content[en['start']:en['end']]) if en else 0
        corpus.append((book, content, views))
    for b in library['books']:
        stats[b['href']] = sum(stats[r] for r in b['readers'])
    for name, text in [('index.html', render_home(library, stats, site)),
                       ('search/index.html', render_search_page(library, site)),
                       ('404.html', render_404(site))]:
        if write(name, text, args.check):
            changed.append(name)
    for key in library['series']:
        if write(os.path.join(key, 'index.html'), render_series(key, library, stats, site), args.check):
            changed.append(key)
    if not args.pages and not args.check:
        import search_index
        search_index.build(ROOT, library, corpus)
    for p in problems:
        print('!', p)
    print(('would change' if args.check else 'wrote'), len(changed), 'pages', '' if not changed else '(' + ', '.join(changed) + ')')
    if args.check and changed:
        print('Pages are out of date: run `python3 tools/build.py` and commit the result.')
        return 1
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
