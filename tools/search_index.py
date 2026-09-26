"""Full-text search index for The Library (called by build.py).

Layout written to search/data/:
  manifest.json          books, passage ranges (book + language per id range), bucket list
  passages/<n>.json      CHUNK passages each: [section title, anchor id, text]
  terms/<key>.json       {term: "base36 delta-encoded passage ids"} for terms whose
                         normalised form starts with <key> (2 or 3 characters)

Every block of text (paragraph, list item, heading, table cell, note) is one passage.
Normalisation must stay identical to search/search-worker.js.
"""
import html, json, os, re, shutil, unicodedata, hashlib
from html.parser import HTMLParser

CHUNK = 100
SPLIT_BYTES = 180_000
STOP = set('''a an and are as at be but by for from had has have he her his i if in into is it its of on or
that the their them there these they this to was were which with not no so than then also been
who whom what when where will would can could should may might must do does did one all any'''.split())

AR_PREFIXES = ('وبال', 'وكال', 'وفال', 'ولل', 'فبال', 'فال', 'وال', 'بال', 'كال', 'لل', 'ال', 'و', 'ف', 'ب', 'ل', 'ك')
ARABIC = re.compile(r'[؀-ۿ]')


def normalise(text):
    t = unicodedata.normalize('NFKD', text)
    t = ''.join(c for c in t if not unicodedata.combining(c))
    t = t.replace('ـ', '')
    t = re.sub('[أإآٱ]', 'ا', t)
    t = t.replace('ى', 'ي').replace('ة', 'ه').replace('ؤ', 'و').replace('ئ', 'ي')
    return t.lower()


def arabic_stem(w):
    for p in AR_PREFIXES:
        if w.startswith(p) and len(w) - len(p) >= 3:
            return w[len(p):]
    return w


TOKEN = re.compile(r'[^\W_]+', re.U)


def terms(text):
    out = []
    for w in TOKEN.findall(normalise(text)):
        if ARABIC.search(w):
            w = arabic_stem(w)
        out.append(w)
    return out


def bucket2(term):
    return '-'.join('%x' % ord(c) for c in term[:2])


def bucket3(term):
    return '-'.join('%x' % ord(c) for c in term[:3])


BLOCKS = {'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'td', 'th', 'dt', 'dd', 'figcaption', 'pre'}
SKIP = {'nav', 'script', 'style', 'button', 'sup'}


class Passages(HTMLParser):
    """Collect text blocks with their nearest anchor and section title."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # (tag, id)
        self.section_title = ''
        self.last_id = None
        self.blocks = []
        self.buf = None
        self.depth = 0
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('br', 'img', 'hr', 'input', 'meta', 'link', 'wbr'):
            if tag == 'br' and self.buf is not None:
                self.buf['text'].append(' ')
            return
        self.stack.append(tag)
        if tag == 'section' and 'book-section' in (a.get('class') or ''):
            self.section_title = a.get('data-title') or a.get('id') or ''
        if tag in SKIP:
            self.skip += 1
        if a.get('id'):
            self.last_id = a['id']
        cls = a.get('class') or ''
        is_block = tag in BLOCKS or (tag == 'div' and ('gloss-footnote-body' in cls))
        if is_block:
            if self.buf is not None:  # nested block: close the outer one first
                self.flush()
            self.buf = {'tag': tag, 'id': a.get('id') or self.last_id, 'text': [], 'depth': len(self.stack)}

    def handle_endtag(self, tag):
        if tag in ('br', 'img', 'hr', 'input', 'meta', 'link', 'wbr'):
            return
        if self.buf is not None and len(self.stack) == self.buf['depth'] and tag == self.buf['tag']:
            self.flush()
        if tag in SKIP and self.skip:
            self.skip -= 1
        while self.stack:
            t = self.stack.pop()
            if t == tag:
                break

    def handle_data(self, data):
        if self.buf is not None and not self.skip:
            self.buf['text'].append(data)

    def flush(self):
        b, self.buf = self.buf, None
        text = re.sub(r'\s+', ' ', ''.join(b['text'])).strip()
        if len(text) >= 2 and b['id']:
            self.blocks.append((self.section_title, b['id'], text))


def passages_of(fragment):
    p = Passages()
    p.feed(fragment)
    p.close()
    return p.blocks


def b36(n):
    s = ''
    while True:
        n, r = divmod(n, 36)
        s = '0123456789abcdefghijklmnopqrstuvwxyz'[r] + s
        if not n:
            return s


def build(root, library, corpus):
    out = os.path.join(root, 'search', 'data')
    records, ranges, books = [], [], []
    corpus = sorted(corpus, key=lambda c: c[0]['searchId'])
    assert [c[0]['searchId'] for c in corpus] == list(range(len(corpus))), 'searchId values must be 0..n-1'
    for book, content, views in corpus:
        bid = book['searchId']
        books.append({
            'id': bid, 'slug': book['slug'], 'title': book['title']['en'] if not book.get('series') else
            f"{library['series'][book['series']['work']]['title'].split(' in ')[0]} · Volume {['I','II','III','IV'][book['series']['volume']-1]}",
            'author': book['author']['en'], 'url': '../' + book['path'] + '/',
        })
        chunks = [(v['lang'], content[v['start']:v['end']]) for v in views]
        store = book.get('sourceStore')
        if store:
            with open(os.path.join(root, book['path'], store['file']), encoding='utf-8') as f:
                chunks.append((store['lang'], f.read()))
        for lang, frag in chunks:
            start = len(records)
            for sec, anchor, text in passages_of(frag):
                records.append((sec, anchor, text))
            if len(records) > start:
                ranges.append([start, len(records), bid, lang])

    postings = {}
    for pid, (sec, anchor, text) in enumerate(records):
        for t in set(terms(text)):
            if t in STOP or len(t) < 2:
                continue
            postings.setdefault(t, []).append(pid)

    # bucket terms by 2-character prefix, splitting large buckets by 3 characters
    by2 = {}
    for t, ids in postings.items():
        by2.setdefault(bucket2(t), {})[t] = ids

    def encode(ids):
        prev, parts = 0, []
        for i in ids:
            parts.append(b36(i - prev))
            prev = i
        return ','.join(parts)

    files = {}
    for k2, group in by2.items():
        enc = {t: encode(ids) for t, ids in group.items()}
        size = sum(len(t) + len(v) + 6 for t, v in enc.items())
        if size <= SPLIT_BYTES:
            files[k2] = enc
            continue
        short = {t: v for t, v in enc.items() if len(t) < 3}
        if short:
            files[k2] = short
        for t, v in enc.items():
            if len(t) >= 3:
                files.setdefault(bucket3(t), {})[t] = v

    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, 'terms'))
    os.makedirs(os.path.join(out, 'passages'))
    for key, enc in files.items():
        with open(os.path.join(out, 'terms', key + '.json'), 'w', encoding='utf-8') as f:
            json.dump(enc, f, ensure_ascii=False, separators=(',', ':'))
    for c in range(0, len(records), CHUNK):
        with open(os.path.join(out, 'passages', f'{c // CHUNK}.json'), 'w', encoding='utf-8') as f:
            json.dump([list(r) for r in records[c:c + CHUNK]], f, ensure_ascii=False, separators=(',', ':'))

    digest = hashlib.sha1(json.dumps([len(records), sorted(files)], ensure_ascii=False).encode() + b''.join(r[2].encode()[:64] for r in records[::500])).hexdigest()[:12]
    langs = {}
    for a, b, bid, lang in ranges:
        langs[lang] = langs.get(lang, 0) + (b - a)
    manifest = {
        'schema': 2, 'version': digest, 'chunk': CHUNK, 'passages': len(records), 'languages': langs,
        'books': books, 'ranges': ranges, 'buckets': sorted(files), 'stop': sorted(STOP),
        'arPrefixes': list(AR_PREFIXES),
    }
    with open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, separators=(',', ':'))
    total = sum(os.path.getsize(os.path.join(dp, fn)) for dp, _, fns in os.walk(out) for fn in fns)
    print(f'search index: {len(records)} passages, {len(postings)} terms, {len(files)} term files, '
          f'{(len(records) + CHUNK - 1) // CHUNK} passage files, {total / 1e6:.1f} MB')
