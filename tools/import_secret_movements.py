#!/usr/bin/env python3
"""Import the final bilingual Markdown pair, then run tools/build.py."""

import argparse
import hashlib
import json
import re
import zipfile
from html import escape
from itertools import groupby
from pathlib import Path

from build import END, START

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'secret-movements-in-islam'
TITLE = {'en': 'Secret Movements in Islam', 'ar': 'الحركات السرية في الإسلام'}
AUTHOR = {'en': 'Mahmoud Ismail', 'ar': 'محمود إسماعيل'}
FILES = {lang: f'{TITLE["en"]} - {name}.md' for lang, name in [('en', 'English'), ('ar', 'Arabic')]}
ZIP_NAME = f'{TITLE["en"]} - Complete Bilingual Markdown.zip'
DESCRIPTION = ('Mahmoud Ismail’s study of five movements that challenged political and religious authority '
               'in Islamic history, followed by a debate on his approach. English and original Arabic, '
               'from the 1997 fifth edition.')

# The heading levels and PDF page numbers agree in both final manuscripts.
# Keep these keys stable so bookmarks and reviews survive a rebuild.
OUTLINE = [
    ('title-pages', 1, 1, 1, 'opening'),
    ('printed-contents', 2, 3, 1, 'opening'),
    ('preface-fifth-edition', 2, 5, 1, 'opening'),
    ('preface-first-edition', 2, 9, 1, 'opening'),
    ('kharijites', 2, 15, 1, 'chapter'),
    ('murjiites', 2, 33, 1, 'chapter'),
    ('abbasids', 2, 59, 1, 'chapter'),
    ('mutazilites', 2, 87, 1, 'chapter'),
    ('qarmatians', 2, 115, 1, 'chapter'),
    ('debate', 2, 157, 1, 'division'),
    ('critical-views', 3, 157, 2, 'group'),
    ('counter-revolution', 4, 157, 3, 'section'),
    ('criticising-an-approach', 4, 162, 3, 'section'),
    ('qarmatians-critique', 4, 168, 3, 'section'),
    ('intellectual-intimidation', 4, 174, 3, 'section'),
    ('modern-approach-and-authenticity', 4, 180, 3, 'section'),
    ('modern-approach-strengthens-authenticity', 4, 189, 3, 'section'),
    ('arab-thought-under-accusation', 4, 198, 3, 'section'),
    ('who-makes-the-accusations', 4, 203, 3, 'section'),
    ('supportive-views', 3, 209, 2, 'group'),
    ('risen-from-their-coffins', 4, 211, 3, 'section'),
    ('modest-opinion', 4, 212, 3, 'section'),
    ('shuubiyya', 4, 213, 3, 'section'),
    ('footnotes', 2, 220, 1, 'notes'),
]
CHAPTERS = dict(zip(('KH', 'MJ', 'AB', 'MT', 'QA'), (row[0] for row in OUTLINE[4:9])))
TOC_KEYS = [row[0] for row in OUTLINE[2:11]] + ['supportive-views']
NOTE_ID = r'(?:KH|MJ|AB|MT|QA)-(?:star-)?[0-9]+'
REF = re.compile(rf'\[\^({NOTE_ID})\]')
DEFINITION = re.compile(rf'\[\^({NOTE_ID})\]: (\S.*)')
PAGE = re.compile(r'<!-- PDF page ([0-9]+) \| [^>]+ -->')
HEADING = re.compile(r'^([#]{1,4}) (.+)$', re.M)
INLINE = re.compile(
    rf'{PAGE.pattern}|{REF.pattern}|\\\*|'
    r'\*\*(?=\S)(.+?)(?<=\S)\*\*|'
    r'(?<!\*)\*(?!\*)(?=\S)(.+?)(?<=\S)\*(?!\*)| {2,}\n',
    re.S,
)
AR_DIGITS = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')


def note_label(key, lang):
    if '-star-' in key:
        return '*'
    number = key.rsplit('-', 1)[1]
    return number.translate(AR_DIGITS) if lang == 'ar' else number


def divide_source(text):
    headings = list(HEADING.finditer(text))
    pages = list(PAGE.finditer(text))
    markers = [int(page[1]) for page in pages]
    if markers != list(range(1, 221)):
        raise ValueError('Expected source PDF page markers 1–220 in order.')

    # The five chapter subtitles stay in their own chapter.
    sections = []
    page_index = 0
    for heading in headings:
        while page_index + 1 < len(pages) and pages[page_index + 1].end() < heading.start():
            page_index += 1
        page = pages[page_index]
        depth = len(heading[1])
        if sections and depth == 3 and sections[-1]['kind'] == 'chapter' and 'subtitle' not in sections[-1]:
            sections[-1]['subtitle'] = heading[2]
            continue
        if len(sections) == len(OUTLINE):
            raise ValueError(f'Unexpected heading: {heading[0]}')
        key, expected_depth, expected_page, level, kind = OUTLINE[len(sections)]
        if (depth, int(page[1])) != (expected_depth, expected_page):
            raise ValueError(f'Unexpected heading at PDF page {page[1]}: {heading[0]}')
        start = heading.start()
        if key != 'footnotes' and not text[page.end():start].strip():
            start = page.start()
        sections.append(dict(key=key, level=level, kind=kind, title=heading[2], start=start))
    if len(sections) != len(OUTLINE) or any('subtitle' not in section for section in sections if section['kind'] == 'chapter'):
        raise ValueError('The manuscript is missing one or more expected headings.')
    for index, section in enumerate(sections):
        end = sections[index + 1]['start'] if index + 1 < len(sections) else len(text)
        section['body'] = text[section['start']:end].strip()
    return sections


def audit_notes(text, sections):
    before_notes = text[:sections[-1]['start']]
    pages = PAGE.split(before_notes)
    positions = [(int(page), key) for page, body in zip(pages[1::2], pages[2::2]) for key in REF.findall(body)]
    lines = sections[-1]['body'].splitlines()[1:]
    definitions = {}
    for line in lines:
        match = DEFINITION.fullmatch(line)
        if match and match[1] not in definitions:
            definitions[match[1]] = [match[2]]
        elif not line.strip():
            if definitions:
                definitions[next(reversed(definitions))].append('')
        elif definitions and line.startswith('    '):
            definitions[next(reversed(definitions))].append(line[4:])
        else:
            raise ValueError(f'Invalid or repeated footnote definition: {line[:100]}')
    definitions = {key: '\n'.join(body).strip() for key, body in definitions.items()}
    numbered = [f'{prefix}-{n}' for prefix, count in zip(CHAPTERS, (25, 110, 26, 106, 108))
                for n in range(1, count + 1)]
    expected = set(numbered + ['KH-star-24', 'KH-star-26', 'KH-star-33'])
    if set(definitions) != expected or [key for _, key in positions] != list(definitions):
        raise ValueError('Expected 378 footnotes, with each reference and definition in matching order.')
    return positions, definitions


class Renderer:
    def __init__(self, lang, sections):
        self.lang = lang
        self.sections = sections
        self.titles = {section['key']: section['title'] for section in sections}
        self.passage = 0
        self.nav = []
        self.contents = []

    def anchor(self):
        self.passage += 1
        return f'passage-{self.lang}-{self.passage:05d}'

    def note_id(self, key):
        return f'note-{self.lang}-{key}'

    def reference_id(self, key):
        return f'ref-{self.lang}-{key}'

    def inline(self, text):
        parts, offset = [], 0
        for match in INLINE.finditer(text):
            parts.append(escape(text[offset:match.start()]))
            if match[1]:
                parts.append(f'<span id="{self.lang}-pdf-page-{match[1]}"></span>{match[0]}')
            elif match[2]:
                key = match[2]
                label = note_label(key, self.lang)
                accessible = f'حاشية {label}' if self.lang == 'ar' else f'Footnote {label}'
                parts.append(f'<sup class="note-ref" id="{self.reference_id(key)}">'
                             f'<a href="#{self.note_id(key)}" role="doc-noteref" aria-label="{accessible}">{label}</a></sup>')
            elif match[3]:
                parts.append(f'<strong>{self.inline(match[3])}</strong>')
            elif match[4]:
                parts.append(f'<em>{self.inline(match[4])}</em>')
            else:
                parts.append('*' if match[0] == r'\*' else '<br>\n')
            offset = match.end()
        parts.append(escape(text[offset:]))
        return ''.join(parts)

    @staticmethod
    def note_attributes(text):
        keys = REF.findall(text)
        return f' data-notes="{" ".join(keys)}"' if keys else ''

    def add_nav(self, key, title, level, kind, label=None):
        anchor = f'{self.lang}-{key}'
        self.nav.append({'id': anchor, 'title': title, 'level': level})
        entry = {'id': anchor, 'level': level, 'kind': kind}
        if label:
            entry['label'] = label
        self.contents.append(entry)
        return anchor

    def printed_contents(self, block):
        lines = block.splitlines()
        if len(lines) != len(TOC_KEYS):
            raise ValueError('Printed contents entries do not match the outline.')
        rows = []
        for key, line in zip(TOC_KEYS, lines):
            title, separator, page = line.strip()[2:].rpartition(' — ')
            if not separator:
                title, page = line.strip()[2:], ''
            elif not page.isdecimal():
                raise ValueError(f'Invalid printed page number: {line}')
            link = f'<a href="#{self.lang}-{key}">{self.inline(title)}</a>'
            leaders = f'<span class="toc-leader" aria-hidden="true"></span><span class="toc-page">{page}</span>' if page else ''
            rows.append(f'<p class="toc-line" id="{self.anchor()}" data-source-key="toc-{key}">{link}{leaders}</p>')
        return '\n'.join(rows)

    def render_blocks(self, text, key):
        html = []
        for block in re.split(r'\n[ \t]*\n', text.strip()):
            if PAGE.fullmatch(block):
                html.append(self.inline(block))
            elif block == '---':
                html.append('<hr>')
            elif heading := HEADING.fullmatch(block):
                tag = 3 if key in CHAPTERS.values() and len(heading[1]) == 3 else 2
                classes = ' class="tp tp-1"' if key == 'title-pages' else ''
                html.append(f'<h{tag}{classes} id="{self.anchor()}" data-source-key="{key}-h{tag}">'
                            f'{self.inline(heading[2])}</h{tag}>')
            elif block.startswith('>'):
                quote = re.sub(r'^> ?', '', block, flags=re.M)
                html.append(f'<blockquote id="{self.anchor()}"{self.note_attributes(quote)}>'
                            f'{self.render_blocks(quote, key)}</blockquote>')
            elif block.startswith('- '):
                if key == 'printed-contents':
                    html.append(self.printed_contents(block))
                else:
                    items = block[2:].split('\n- ')
                    html.append('<ul>' + ''.join(f'<li id="{self.anchor()}"{self.note_attributes(item)}>'
                                                f'{self.inline(item)}</li>' for item in items) + '</ul>')
            elif block:
                html.append(f'<p id="{self.anchor()}"{self.note_attributes(block)}>{self.inline(block)}</p>')
        return '\n'.join(html)

    def render_notes(self, definitions):
        html = []
        for prefix, notes in groupby(definitions, key=lambda key: key.split('-', 1)[0]):
            chapter = CHAPTERS[prefix]
            title = self.titles[chapter]
            anchor = self.add_nav(f'footnotes-{chapter}', title, 2, 'group')
            html.append(f'<h3 id="{anchor}" data-source-key="footnotes-{chapter}">{escape(title)}</h3>')
            html.append('<ol class="footnotes-list" role="list">')
            for key in notes:
                label = note_label(key, self.lang)
                back = 'العودة إلى النص' if self.lang == 'ar' else 'Back to text'
                backlink = (f'<a class="backref" role="doc-backlink" href="#{self.reference_id(key)}" '
                            f'aria-label="{back}">↩</a>')
                body = self.render_blocks(definitions[key], 'footnotes')
                if body.endswith('</p>'):
                    body = f'{body[:-4]} {backlink}</p>'
                else:
                    body += backlink
                html.append(f'<li id="{self.note_id(key)}" data-source-key="{key}" role="doc-endnote">'
                            f'<span class="note-number">{label}</span>{body}</li>')
            html.append('</ol>')
        return '\n'.join(html)

    def render(self, definitions):
        parts = [f'<div class="language-view" data-lang="{self.lang}">']
        direction = 'rtl' if self.lang == 'ar' else 'ltr'
        for section in self.sections:
            key = section['key']
            title = section['title']
            label = None
            if key == 'title-pages':
                title = 'صفحات العنوان والنشر' if self.lang == 'ar' else 'Title and publication pages'
            if 'subtitle' in section:
                label, title = title, f'{title}: {section["subtitle"]}'
            anchor = self.add_nav(key, title, section['level'], section['kind'], label)
            content = (self.render_blocks(section['body'].splitlines()[0], key) + '\n' +
                       self.render_notes(definitions) if key == 'footnotes' else self.render_blocks(section['body'], key))
            classes = 'book-section title-pages' if key == 'title-pages' else 'book-section'
            parts.append(f'<section class="{classes}" id="{anchor}" data-key="{key}" '
                         f'data-title="{escape(title)}" lang="{self.lang}" dir="{direction}">\n{content}\n</section>')
        return '\n'.join(parts + ['</div>'])


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Directory containing the two final Markdown files')
    args = parser.parse_args()

    sources = {lang: (args.source / name).read_bytes() for lang, name in FILES.items()}
    fragments, nav, contents, audits = [], {}, {}, {}
    for lang, data in sources.items():
        text = data.decode('utf-8')
        sections = divide_source(text)
        audits[lang], definitions = audit_notes(text, sections)
        renderer = Renderer(lang, sections)
        fragments.append(renderer.render(definitions))
        nav[lang] = renderer.nav
        contents[lang] = {
            'sourceHash': hashlib.sha256(json.dumps(renderer.nav, ensure_ascii=False).encode()).hexdigest(),
            'entries': renderer.contents,
        }
    if audits['en'] != audits['ar']:
        raise ValueError('English and Arabic footnote references differ by note or PDF page.')

    folder = ROOT / SLUG
    library = json.loads((ROOT / 'library.json').read_text(encoding='utf-8'))
    ids = [json.loads((ROOT / reader / 'book.json').read_text(encoding='utf-8'))['searchId']
           for card in library['books'] for reader in card['readers'] if reader != SLUG]
    book_path = folder / 'book.json'
    search_id = json.loads(book_path.read_text(encoding='utf-8'))['searchId'] if book_path.exists() else max(ids) + 1
    version = hashlib.sha256(b''.join(sources.values())).hexdigest()[:16]
    book = {
        'searchId': search_id, 'slug': SLUG, 'path': SLUG,
        'pageTitle': f'{TITLE["en"]} — {AUTHOR["en"]}',
        'description': DESCRIPTION,
        'languages': list(FILES), 'langKey': f'minimal-library-lang-{SLUG}',
        'title': TITLE, 'author': AUTHOR,
        'subtitle': {'en': '', 'ar': ''},
        'edition': {'en': 'Final editorial edition · Fifth Arabic edition, 1997',
                    'ar': 'الطبعة الخامسة · سينا للنشر، ١٩٩٧'},
        'downloads': FILES, 'bilingualZip': ZIP_NAME,
        'home': {'href': '../', 'label': 'Library'},
        'review': {'slug': SLUG, 'title': TITLE['en'], 'sourceLanguage': 'ar', 'version': version,
                   'englishMarkdown': FILES['en'], 'sourceMarkdown': FILES['ar']},
        'nav': nav, 'contentsFile': 'contents.json',
    }

    folder.mkdir(exist_ok=True)
    for lang, data in sources.items():
        (folder / FILES[lang]).write_bytes(data)
    with zipfile.ZipFile(folder / ZIP_NAME, 'w') as archive:
        for lang, data in sources.items():
            entry = zipfile.ZipInfo(FILES[lang])
            archive.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    (folder / 'index.html').write_text('\n'.join([START, *fragments, END, '']), encoding='utf-8')
    write_json(book_path, book)
    write_json(folder / 'contents.json', {'version': 1, 'initiallyCollapsed': True, 'languages': contents})
    print(f'Imported {len(OUTLINE)} paired sections, 220 PDF page markers and {len(audits["en"])} notes per language.')


if __name__ == '__main__':
    main()
