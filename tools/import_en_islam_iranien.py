#!/usr/bin/env python3
"""Import Henry Corbin's *En Islam iranien* (four volumes, English + French Markdown).

Usage: python3 tools/import_en_islam_iranien.py /path/to/folder-with-the-eight-md-files
       python3 tools/build.py

The folder holds `En_Islam_Iranien_Volume_<I..IV>_<English|French>.md` (the names the
translators supplied). For each volume this writes, under within-iranian-islam/volume-N/:

  index.html    the book text between the BOOK-CONTENT markers (build.py adds the page around it)
  book.json     reader settings: titles, contents (nav), downloads, Reviewer Mode
  *.md          the two Markdown downloads (the supplied files, with the structural fixes below)
  figures/      the figures, decoded from the images embedded in the Markdown

It also writes within-iranian-islam/Within Iranian Islam - Complete Markdown.zip.

The Markdown renderer covers the syntax these files use (headings, paragraphs, block
quotes, ordered and bulleted lists, pipe tables, images, rules, emphasis, footnotes). It
escapes all text and never passes raw HTML through. Standard library only; Pillow is used,
when installed, to scale down the very large scans in Volume III.

Both languages are cut into the same sections (title pages, front matter, one section per
chapter, printed contents, back matter, notes) with the same data-key values, so the
language switch keeps the reader in place and Reviewer Mode pairs the right sections.
Inside a section, headings carry matching data-source-key values and paragraphs carry the
note numbers they contain (data-notes), which Reviewer Mode uses as alignment anchors.
"""
import argparse
import base64
import hashlib
import html
import io
import json
import re
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = 'within-iranian-islam'
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']
WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8,
         'premier': 1, 'premiere': 1}
NUMBER_WORDS_EN = ['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven']
SOURCE_NAMES = {'en': 'En_Islam_Iranien_Volume_{v}_English.md', 'fr': 'En_Islam_Iranien_Volume_{v}_French.md'}
DOWNLOADS = {'en': 'Within Iranian Islam {v} - English.md', 'fr': 'En Islam iranien {v} - French.md'}
ZIP_NAME = 'Within Iranian Islam - Complete Markdown.zip'

VOLUMES = {
    1: {'year': 1971, 'title': {'en': 'Twelver Shiism', 'fr': 'Le shî’isme duodécimain'}},
    2: {'year': 1971, 'title': {'en': 'Sohrawardî and the Platonists of Persia', 'fr': 'Sohrawardî et les Platoniciens de Perse'}},
    3: {'year': 1972, 'title': {'en': 'The Faithful of Love\u00a0· Shiism and Sufism', 'fr': 'Les Fidèles d’amour\u00a0· Shî’isme et soufisme'}},
    4: {'year': 1972, 'title': {'en': 'The School of Isfahan\u00a0· The Shaykhi School\u00a0· The Twelfth Imam',
                                'fr': 'L’École d’Ispahan\u00a0· L’École shaykhie\u00a0· Le Douzième Imâm'}},
}
# Book (part) titles, set in capitals in the source; given here in reading case.
BOOKS = {
    1: {'en': 'Aspects of Twelver Shiism', 'fr': 'Aspects du shî’isme duodécimain'},
    2: {'en': 'Sohrawardî and the Platonists of Persia', 'fr': 'Sohrawardî et les Platoniciens de Perse'},
    3: {'en': 'Ruzbihan Baqli Shirazi and the Sufism of the Faithful of Love',
        'fr': 'Rûzbehân Baqlî Shîrâzî et le soufisme des Fidèles d’amour'},
    4: {'en': 'Shiism and Sufism', 'fr': 'Shî’isme et soufisme'},
    5: {'en': 'The School of Isfahan', 'fr': 'L’École d’Ispahan'},
    6: {'en': 'The Shaykhi School', 'fr': 'L’École shaykhie'},
    7: {'en': 'The Twelfth Imam and Spiritual Chivalry', 'fr': 'Le Douzième Imâm et la chevalerie spirituelle'},
}
LABELS = {
    'en': {'title-pages': 'Title Pages', 'contents': 'Printed Contents', 'back-matter': 'Back Matter', 'notes': 'Notes',
           'overviews': 'Overviews', 'book': 'Book', 'chapter': 'Chapter', 'note': 'Note', 'back': 'Back to text'},
    'fr': {'title-pages': 'Pages de titre', 'contents': 'Table des matières', 'back-matter': 'Pages de fin', 'notes': 'Notes',
           'overviews': 'Arguments', 'book': 'Livre', 'chapter': 'Chapitre', 'note': 'Note', 'back': 'Retour au texte'},
}

# Structural slips in the supplied Markdown, corrected before conversion (the downloads carry
# the corrections too). Each is an exact replacement; if a revised supply no longer contains
# the text, the fix is skipped and reported.
FIXES = {
    (4, 'en'): [
        # Two successor biographies and a chapter opening were typed as bold text, not headings.
        ('**4. Shaykh Hâjj Zaynol-\'Âbidîn-Khân Kermânî (1276/1859–1360/1942)** ',
         '##### 4. Shaykh Hâjj Zaynol-\'Âbidîn-Khân Kermânî (1276/1859–1360/1942)\n\n'),
        ('**5. Shaykh Abû\'l-Qâsem-Khân Ebrâhîmî, Sarkâr Âghâ (1314/1896–1389/1969)** ',
         '##### 5. Shaykh Abû\'l-Qâsem-Khân Ebrâhîmî, Sarkâr Âghâ (1314/1896–1389/1969)\n\n'),
        ('**Chapter III\nSome Points of Doctrine\nI. Tradition and Renewal**\n',
         '### Chapter III\n\n#### Some Points of Doctrine\n\n##### 1. Tradition and Renewal\n\n'),
    ],
}

# The supplied English files call the work "In Iranian Islam"; the edition is published as
# "Within Iranian Islam", which keeps Corbin's sense of writing from within the tradition.
ENGLISH_TITLE = ('In Iranian Islam', 'Within Iranian Islam')

esc = lambda s: html.escape(s, quote=True)


def fold(s):
    """Lower-case, accent-free, emphasis-free form of a heading, for classification."""
    s = unicodedata.normalize('NFKD', s.replace('*', ''))
    return ''.join(c for c in s if not unicodedata.combining(c)).lower().strip()


# --------------------------------------------------------------------------- inline Markdown
PUNCT = set('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~') | {'“', '”', '‘', '’', '«', '»', '—', '–', '…'}


class Inline:
    """CommonMark-style emphasis (delimiter runs of *), footnote references, escapes, hard breaks."""

    def __init__(self, renderer):
        self.r = renderer

    def render(self, text):
        # 1. split into literal text pieces, footnote refs and '*' runs
        tokens = []  # dicts: {'t': 'text'|'html'|'delim', ...}
        i, n, buf = 0, len(text), []

        def flush():
            if buf:
                tokens.append({'t': 'text', 's': ''.join(buf)})
                buf.clear()
        while i < n:
            c = text[i]
            if c == '\\' and i + 1 < n and text[i + 1] in PUNCT:
                buf.append(text[i + 1]); i += 2; continue
            if c == '\\' and i + 1 < n and text[i + 1] == '\n':
                flush(); tokens.append({'t': 'html', 's': '<br>\n'}); i += 2; continue
            if c == ' ' and (m := re.match(r' {2,}\n', text[i:i + 64])):
                flush(); tokens.append({'t': 'html', 's': '<br>\n'}); i += m.end(); continue
            if c == '[' and text.startswith('[^', i):
                m = re.match(r'\[\^([^\]\s]+)\]', text[i:])
                if m:
                    flush(); tokens.append({'t': 'html', 's': self.r.note_ref(m.group(1))}); i += m.end(); continue
            if c == '*':
                j = i
                while j < n and text[j] == '*':
                    j += 1
                flush()
                before = text[i - 1] if i > 0 else ' '
                after = text[j] if j < n else ' '
                ws_b, ws_a = before.isspace(), after.isspace()
                p_b, p_a = before in PUNCT, after in PUNCT
                left = not ws_a and (not p_a or ws_b or p_b)
                right = not ws_b and (not p_b or ws_a or p_a)
                tokens.append({'t': 'delim', 'n': j - i, 'orig': j - i, 'open': left, 'close': right, 'pre': '', 'post': ''})
                i = j; continue
            buf.append(c); i += 1
        flush()
        # 2. process emphasis (CommonMark "process emphasis", '*' only)
        delims = [k for k, t in enumerate(tokens) if t['t'] == 'delim']
        stack = []
        for k in delims:
            t = tokens[k]
            if t['close']:
                matched = True
                while matched and t['n'] and t['close']:
                    matched = False
                    for si in range(len(stack) - 1, -1, -1):
                        o = tokens[stack[si]]
                        if not o['n'] or not o['open']:
                            continue
                        if (o['close'] or t['open']) and (o['orig'] + t['orig']) % 3 == 0 and not (o['orig'] % 3 == 0 and t['orig'] % 3 == 0):
                            continue
                        use = 2 if o['n'] >= 2 and t['n'] >= 2 else 1
                        tag = 'strong' if use == 2 else 'em'
                        o['n'] -= use; t['n'] -= use
                        o['post'] = f'<{tag}>' + o['post']
                        t['pre'] += f'</{tag}>'
                        del stack[si + 1:]
                        if not o['n']:
                            del stack[si]
                        matched = True
                        break
            if t['n'] and t['open']:
                stack.append(k)
        out = []
        for t in tokens:
            if t['t'] == 'text':
                out.append(esc(t['s']))
            elif t['t'] == 'html':
                out.append(t['s'])
            else:
                out.append(t['pre'] + '*' * t['n'] + t['post'])
        return ''.join(out)


def plain(text):
    """Heading text for the contents and data-title: no emphasis marks, notes or escapes."""
    text = re.sub(r'\[\^[^\]]+\]', '', text)
    text = re.sub(r'\\(.)', r'\1', text)
    return re.sub(r'\s+', ' ', text.replace('*', '')).strip()


# --------------------------------------------------------------------------- block Markdown
LIST_ITEM = re.compile(r'^( {0,3})(?:(\d{1,9})([.)])|([-*+]))( +|$)')
HR = re.compile(r'^ {0,3}(?:(?:\* *){3,}|(?:- *){3,}|(?:_ *){3,})$')
HEADING = re.compile(r'^ {0,3}(#{1,6})(?: +(.*?))?(?: +#+)? *$')
IMAGE = re.compile(r'^ {0,3}!\[((?:[^\]\\]|\\.)*)\]\(([^)\s]+)\) *$')
TABLE_SEP = re.compile(r'^ *\|? *:?-{3,}:? *(\| *:?-{3,}:? *)*\|? *$')


def starts_block(line, in_paragraph=True):
    if HEADING.match(line) or line.lstrip().startswith('>') or IMAGE.match(line) or HR.match(line):
        return True
    m = LIST_ITEM.match(line)
    if m and m.group(5):
        # an ordered list interrupts a paragraph only when it starts at 1 (CommonMark)
        return not in_paragraph or m.group(4) or m.group(2) == '1'
    return False


def parse_blocks(lines):
    blocks, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1; continue
        if m := HEADING.match(line):
            blocks.append({'type': 'h', 'level': len(m.group(1)), 'text': (m.group(2) or '').strip()}); i += 1; continue
        if HR.match(line):
            blocks.append({'type': 'hr'}); i += 1; continue
        if m := IMAGE.match(line):
            blocks.append({'type': 'img', 'alt': re.sub(r'\\(.)', r'\1', m.group(1)), 'src': m.group(2)}); i += 1; continue
        if line.lstrip().startswith('>'):
            inner = []
            while i < n and (lines[i].lstrip().startswith('>') or (lines[i].strip() and inner and inner[-1].strip()
                                                                    and not starts_block(lines[i]))):
                l = lines[i].lstrip()
                inner.append(re.sub(r'^> ?', '', l) if l.startswith('>') else l)
                i += 1
            blocks.append({'type': 'quote', 'children': parse_blocks(inner)}); continue
        if line.lstrip().startswith('|') and i + 1 < n and TABLE_SEP.match(lines[i + 1]):
            rows = []
            while i < n and lines[i].lstrip().startswith('|'):
                rows.append(lines[i]); i += 1
            cells = lambda r: [c.strip() for c in re.split(r'(?<!\\)\|', r.strip().strip('|'))]
            blocks.append({'type': 'table', 'head': cells(rows[0]), 'rows': [cells(r) for r in rows[2:]]}); continue
        if (m := LIST_ITEM.match(line)) and m.group(5):
            ordered = m.group(2) is not None
            items, start = [], int(m.group(2)) if ordered else None
            while i < n:
                m = LIST_ITEM.match(lines[i])
                if not (m and m.group(5)) or (m.group(2) is not None) != ordered:
                    break
                gap = len(m.group(5))
                indent = len(m.group(0)) if 1 <= gap <= 4 else len(m.group(0)) - gap + 1
                body = [lines[i][len(m.group(0)):]]
                i += 1
                while i < n:
                    l = lines[i]
                    if not l.strip():
                        # a blank line continues the item only if the next line is indented into it
                        if i + 1 < n and lines[i + 1].strip() and len(lines[i + 1]) - len(lines[i + 1].lstrip()) >= indent:
                            body.append(''); i += 1; continue
                        break
                    if len(l) - len(l.lstrip()) >= indent:
                        body.append(l[indent:]); i += 1; continue
                    if body[-1].strip() and not starts_block(l) and not (LIST_ITEM.match(l) and LIST_ITEM.match(l).group(5)):
                        body.append(l); i += 1; continue  # lazy continuation
                    break
                items.append(parse_blocks(body))
                # skip blank lines between items of the same list
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and (m2 := LIST_ITEM.match(lines[j])) and m2.group(5) and (m2.group(2) is not None) == ordered:
                    i = j
                else:
                    break
            blocks.append({'type': 'list', 'ordered': ordered, 'start': start, 'items': items}); continue
        para = [line]
        i += 1
        while i < n and lines[i].strip() and not starts_block(lines[i]) and not (
                lines[i].lstrip().startswith('|') and i + 1 < n and TABLE_SEP.match(lines[i + 1])):
            para.append(lines[i]); i += 1
        blocks.append({'type': 'p', 'text': '\n'.join(l.lstrip() for l in para).rstrip()})
    return blocks


# --------------------------------------------------------------------------- figures
class Figures:
    def __init__(self, folder):
        self.folder = folder
        self.by_hash, self.files = {}, {}

    def add(self, src):
        m = re.match(r'data:image/([a-z+]+);base64,(.+)$', src, re.S)
        assert m, 'only embedded images are supported'
        data = base64.b64decode(m.group(2))
        h = hashlib.sha1(data).hexdigest()
        if h not in self.by_hash:
            n = len(self.by_hash) + 1
            data, ext, (w, hgt) = self.optimise(data, m.group(1))
            name = f'figure-{n}.{ext}'
            self.by_hash[h] = (name, w, hgt)
            self.files[name] = data
        return self.by_hash[h]

    @staticmethod
    def optimise(data, ext):
        try:
            from PIL import Image
        except ImportError:  # keep the image as supplied
            w, h = png_size(data) if ext == 'png' else (0, 0)
            return data, ext, (w, h)
        im = Image.open(io.BytesIO(data))
        w, h = im.size
        if max(w, h) <= 1800:
            return data, ext, (w, h)
        scale = 1800 / max(w, h)
        im = im.convert('L' if im.mode in ('L', '1', 'LA') else 'RGB').resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        candidates = []
        for fmt, kw in (('PNG', {'optimize': True}), ('JPEG', {'quality': 84, 'optimize': True, 'progressive': True})):
            b = io.BytesIO()
            im.save(b, fmt, **kw)
            candidates.append((len(b.getvalue()), b.getvalue(), 'png' if fmt == 'PNG' else 'jpg'))
        size, best, new_ext = min(candidates)
        if len(data) <= size:  # already compact (line drawings): keep the supplied file
            return data, ext, (w, h)
        return best, new_ext, im.size


def png_size(data):
    return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')


# --------------------------------------------------------------------------- renderer
class Renderer:
    def __init__(self, lang, figures, notes):
        self.lang, self.figures, self.notes = lang, figures, notes
        self.counter = 0
        self.refs = {}           # note key -> number of references so far
        self.inline = Inline(self)
        self.block_notes = None  # notes referenced inside the block being rendered
        self.flat_lists = False

    def anchor(self):
        self.counter += 1
        return f'passage-{self.lang}-{self.counter:05d}'

    def note_ref(self, key):
        assert key in self.notes, f'{self.lang}: reference to undefined note {key}'
        self.refs[key] = self.refs.get(key, 0) + 1
        rid = f'ref-{self.lang}-{key}' + ('' if self.refs[key] == 1 else f'-{self.refs[key]}')
        num = note_number(key)
        if self.block_notes is not None:
            self.block_notes.append(str(num))
        return (f'<sup class="note-ref" id="{esc(rid)}"><a href="#note-{self.lang}-{esc(key)}" '
                f'aria-label="{LABELS[self.lang]["note"]} {num}">{num}</a></sup>')

    def text(self, md):
        return self.inline.render(md)

    def para_attrs(self, html_text):
        return ''

    def blocks(self, blocks, depth=0, heading=None):
        """Render a list of blocks. heading(block) -> html or None lets the caller handle headings."""
        out = []
        k = 0
        while k < len(blocks):
            b = blocks[k]
            t = b['type']
            if t == 'h':
                h = heading(b) if heading else None
                out.append(h if h is not None else self.generic_heading(b))
            elif t == 'p':
                out.append(self.paragraph(b['text'], depth))
            elif t == 'hr':
                out.append('<hr>')
            elif t == 'img':
                caption = None
                nxt = blocks[k + 1] if k + 1 < len(blocks) else None
                if nxt and nxt['type'] == 'p' and re.fullmatch(r'\*\s*Fig\.[^*]*\*', nxt['text'].strip()):
                    caption = nxt['text'].strip().strip('*').strip()
                    k += 1
                out.append(self.figure(b, caption))
            elif t == 'quote':
                out.append(f'<blockquote{self.notes_attr_for(b)}>{self.blocks(b["children"], depth + 1, heading)}</blockquote>')
            elif t == 'list' and self.flat_lists and b['ordered']:
                # printed contents: "1. …, 3. — 2. …, 9." lines are text, not lists
                for n_item, item in enumerate(b['items']):
                    first = f'{b["start"] + n_item}. '
                    for j, blk in enumerate(item):
                        if blk['type'] == 'p':
                            out.append(self.paragraph((first if j == 0 else '') + blk['text'], depth))
                        else:
                            out.append(self.blocks([blk], depth, heading))
            elif t == 'list':
                tag = 'ol' if b['ordered'] else 'ul'
                start = f' start="{b["start"]}"' if b['ordered'] and b['start'] != 1 else ''
                items = []
                for item in b['items']:
                    if len(item) == 1 and item[0]['type'] == 'p':
                        self.block_notes = []
                        body = self.text(item[0]['text'])
                        notes, self.block_notes = self.block_notes, None
                        attr = f' data-notes="{" ".join(notes)}"' if notes and depth == 0 else ''
                        items.append(f'<li id="{self.anchor()}"{attr}>{body}</li>')
                    else:
                        items.append(f'<li id="{self.anchor()}">{self.blocks(item, depth + 1, heading)}</li>')
                out.append(f'<{tag}{start}>' + ''.join(items) + f'</{tag}>')
            elif t == 'table':
                head = ''.join(f'<th>{self.text(c)}</th>' for c in b['head'])
                rows = ''.join('<tr>' + ''.join(f'<td>{self.text(c)}</td>' for c in r) + '</tr>' for r in b['rows'])
                out.append(f'<table id="{self.anchor()}"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>')
            k += 1
        return '\n'.join(out)

    def notes_attr_for(self, quote):
        """Block quotes are a single review unit: list the notes referenced anywhere inside."""
        keys = re.findall(r'\[\^([^\]\s]+)\]', json.dumps(quote, ensure_ascii=False))
        return f' data-notes="{" ".join(str(note_number(k)) for k in keys)}"' if keys else ''

    def paragraph(self, md, depth=0):
        self.block_notes = []
        body = self.text(md)
        notes, self.block_notes = self.block_notes, None
        attr = f' data-notes="{" ".join(notes)}"' if notes and depth == 0 else ''
        return f'<p id="{self.anchor()}"{attr}>{body}</p>'

    def generic_heading(self, b, level=None):
        level = level or min(4, max(2, b['level']))
        return f'<h{level} id="{self.anchor()}">{self.text(b["text"])}</h{level}>'

    def figure(self, b, caption):
        name, w, h = self.figures.add(b['src'])
        dw, dh = (round(w / 2), round(h / 2)) if w > 900 else (w, h)
        alt = plain(b['alt'])
        label = caption or alt
        cap = f'<figcaption>{self.text(caption)}</figcaption>' if caption else ''
        return (f'<figure class="facsimile plate" id="{self.anchor()}"><button class="facsimile-zoom" type="button" '
                f'aria-label="{esc("Enlarge: " + label if self.lang == "en" else "Agrandir : " + label)}" '
                f'data-facsimile-src="figures/{name}" data-facsimile-caption="{esc(plain(label))}">'
                f'<img src="figures/{name}" width="{dw}" height="{dh}" alt="{esc(alt)}" loading="lazy" decoding="async"></button>{cap}</figure>')


def note_number(key):
    return int(key.rsplit('-', 1)[1])


# --------------------------------------------------------------------------- structure
def classify(b, in_chapters):
    """What a heading starts: book, chapter, contents, notes, back matter, front matter or nothing."""
    if b['type'] != 'h':
        return None
    f, lv = fold(b['text']), b['level']
    if lv == 1 and re.match(r'(book|livre)\b', f):
        return 'book'
    if lv <= 3 and re.match(r'(chapter|chapitre)\b', f):
        return 'chapter'
    if lv == 1 and f in ('footnotes', 'notes'):
        return 'notes'
    if lv <= 3 and f in ('contents', 'table'):
        return 'contents'
    if re.match(r'(other works|du meme auteur|printing details|acheve d.imprimer|colophon)', f) or (in_chapters and f == 'henry corbin'):
        return 'back'
    if not in_chapters and lv == 2:
        if f.startswith('prologue'):
            return 'prologue'
        if 'transcription' in f:
            return 'transcription'
        if re.match(r'(outline|overview|argument)s?\b', f):
            return 'overview'
    return None


SMALL_WORDS = {'a', 'an', 'and', 'by', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'with'}
NAMES = {'henry', 'corbin'}


def reading_case(text, lang):
    """Front- and back-matter headings set in capitals ('ARGUMENT DES LIVRES I ET II') in reading case."""
    letters = [c for c in text if c.isalpha()]
    if not letters or any(c.islower() for c in letters):
        return text
    out = []
    for i, w in enumerate(text.split(' ')):
        bare = w.strip('*_.,:;()')
        if bare.upper() in ROMAN:
            out.append(w)
        elif bare.lower() in NAMES or i == 0 or (lang == 'en' and bare.lower() not in SMALL_WORDS):
            out.append(w[:1] + w[1:].lower())
        else:
            out.append(w.lower())
    return ' '.join(out)


def numeral(word):
    w = fold(word).strip('. ')
    if w.upper() in ROMAN:
        return ROMAN.index(w.upper()) + 1
    return WORDS[w]


def split_number(text):
    """'I. - *Title*' -> ('I', 'Title'); returns (None, text) when unnumbered."""
    t = text.strip()
    wrapped = re.fullmatch(r'\*([^*].*?)\*\.?', t)
    if wrapped and '*' not in wrapped.group(1):
        t = wrapped.group(1)
    m = re.match(r'^((?:\d+)|(?:[IVXLC]+)|i|[a-h])\s*[.)]\s*(?:[-—–]\s*)?(.*)$', t)
    if not m:
        return None, t
    rest = m.group(2).strip()
    w2 = re.fullmatch(r'\*([^*].*?)\*(\.?)', rest)
    if w2 and '*' not in w2.group(1):
        rest = w2.group(1) + w2.group(2)
    return m.group(1), rest


def strip_wrap(text):
    t = text.strip()
    w = re.fullmatch(r'\*([^*].*?)\*(\.?)', t)
    return (w.group(1) + w.group(2)) if w and '*' not in w.group(1) else t


def segment(blocks):
    """Cut a volume's block list into ordered parts: (kind, info, blocks)."""
    parts, cur, in_chapters = [], None, False
    pending_book = None
    i = 0
    cur = {'kind': 'title-pages', 'blocks': []}
    while i < len(blocks):
        b = blocks[i]
        c = classify(b, in_chapters)
        if c == 'book':
            # the book heading and the headings that follow it (subtitle, dates) up to the first chapter
            j = i + 1
            while j < len(blocks) and blocks[j]['type'] == 'h' and classify(blocks[j], True) != 'chapter':
                j += 1
            pending_book = {'n': numeral(re.sub(r'^(book|livre)\s+', '', fold(b['text']))), 'heads': blocks[i:j]}
            i = j
            continue
        if c == 'chapter':
            parts.append(cur)
            assert i + 1 < len(blocks) and blocks[i + 1]['type'] == 'h', f'chapter without a title: {b}'
            num = numeral(re.sub(r'^(chapter|chapitre)\s+', '', fold(b['text'])))
            cur = {'kind': 'chapter', 'num': num, 'title': strip_wrap(blocks[i + 1]['text']), 'book': pending_book,
                   'blocks': [], 'level': blocks[i + 1]['level']}
            pending_book, in_chapters = None, True
            i += 2
            continue
        if c in ('notes', 'contents', 'back', 'prologue', 'transcription', 'overview'):
            kind = {'back': 'back-matter'}.get(c, c)
            if not (cur['kind'] == kind and kind in ('back-matter', 'overview')):
                parts.append(cur)
                cur = {'kind': kind, 'blocks': []}
            if c != 'notes':
                cur['blocks'].append(b)
            i += 1
            continue
        cur['blocks'].append(b)
        i += 1
    parts.append(cur)
    return [p for p in parts if p['blocks'] or p['kind'] in ('chapter', 'notes')]


def parse_notes(lines):
    notes = {}
    for line in lines:
        if not line.strip():
            continue
        m = re.match(r'\[\^([^\]\s]+)\]:\s*(.*)$', line)
        assert m, f'unexpected line in notes: {line[:80]}'
        assert m.group(1) not in notes, f'duplicate note {m.group(1)}'
        notes[m.group(1)] = m.group(2)
    return notes


def convert(text, lang, vol, figures):
    lines = text.split('\n')
    starts = [i for i, l in enumerate(lines) if re.match(r'^# (Footnotes|Notes)\s*$', l)]
    assert len(starts) == 1
    notes = parse_notes(lines[starts[0] + 1:])
    blocks = parse_blocks(lines[:starts[0]])
    parts = segment(blocks) + [{'kind': 'notes', 'blocks': []}]
    r = Renderer(lang, figures, notes)
    L = LABELS[lang]
    sections, nav = [], []
    chapter_counter = {}
    for part in parts:
        kind = part['kind']
        attrs = ''
        if kind == 'chapter':
            book = part['book']
            bn = (book or {}).get('n') or sections[-1]['book']
            chapter_counter[bn] = chapter_counter.get(bn, 0) + 1
            key = f'book-{bn}-ch-{chapter_counter[bn]}'
            roman = ROMAN[part['num'] - 1]
            title_md = part['title']
            title_plain = plain(title_md)
            sid = f'{lang}-{key}'
            out = []
            if book:
                bid = f'{lang}-book-{bn}'
                book_no = (f'Book {NUMBER_WORDS_EN[bn]}' if bn == 1 else f'Book {ROMAN[bn - 1]}') if lang == 'en' else \
                          ('Livre premier' if bn == 1 else f'Livre {ROMAN[bn - 1]}')
                dates = next((plain(h['text']) for h in book['heads'] if re.fullmatch(r'\(.*\)', plain(h['text']))), None)
                out.append(f'<div class="part-head" id="{bid}"><p class="part-no">{book_no}</p>'
                           f'<p class="part-title">{esc(BOOKS[bn][lang])}</p>'
                           + (f'<p class="part-dates">{esc(dates)}</p>' if dates else '') + '</div>')
                sep = ' : ' if lang == 'fr' else ': '
                nav.append({'id': bid, 'title': f'{book_no}{sep}{BOOKS[bn][lang]}', 'level': 1})
            ch_word = f'Chapter {roman}' if lang == 'en' else ('Chapitre premier' if part['num'] == 1 else f'Chapitre {roman}')
            hid = r.anchor()
            out.append(f'<h2 class="chapter-title" id="{hid}" data-source-key="chapter"><span class="chapter-no">{ch_word}</span> '
                       f'<span class="chapter-name">{r.text(title_md)}</span></h2>')
            nav.append({'id': hid if book else sid, 'title': f'{roman}. {title_plain}', 'level': 2})
            # sub-headings: numbered sections (h3, in the contents); their own divisions (h4)
            heads = [b for b in part['blocks'] if b['type'] == 'h']
            seen_arabic, h3_count, prev_num = False, 0, None
            plan = {}
            for idx, b in enumerate(heads):
                num, rest = split_number(b['text'])
                nxt = split_number(heads[idx + 1]['text'])[0] if idx + 1 < len(heads) else None
                if b['level'] >= 6 or (num and re.fullmatch(r'[a-h]', num)):
                    plan[id(b)] = ('h4', num, rest)
                elif num and num.isdigit():
                    seen_arabic = True
                    plan[id(b)] = ('h3', num, rest)
                elif num in ('I', 'i') and not seen_arabic and nxt == '2':
                    seen_arabic = True
                    plan[id(b)] = ('h3', '1', rest)
                elif num and seen_arabic:
                    plan[id(b)] = ('h4', num, rest)   # roman divisions inside a numbered section
                elif not num and seen_arabic:
                    plan[id(b)] = ('h4', None, rest)
                else:
                    plan[id(b)] = ('h3', num, rest)

            def chapter_heading(b, plan=plan):
                nonlocal h3_count
                tag, num, rest = plan[id(b)]
                label_md = f'{num}. {rest}' if num and not re.fullmatch(r'[a-h]', num) else (f'{num}) {rest}' if num else rest)
                if tag == 'h3':
                    h3_count += 1
                    hid = f'{lang}-{key}-s{h3_count}'
                    nav.append({'id': hid, 'title': plain(label_md), 'level': 3})
                    return f'<h3 id="{hid}" data-source-key="s{h3_count}">{r.text(label_md)}</h3>'
                return f'<h4 id="{r.anchor()}">{r.text(label_md)}</h4>'
            out.append(r.blocks(part['blocks'], heading=chapter_heading))
            sections.append({'key': key, 'title': f'{roman}. {title_plain}', 'html': '\n'.join(out), 'book': bn, 'cls': 'chapter'})
            continue

        if kind == 'notes':
            text_refs = dict(r.refs)  # note bodies may cite other notes; those are not text references
            head_id = r.anchor()
            items = []
            for k, body in notes.items():
                num = note_number(k)
                back = (f' <a class="backref" href="#ref-{lang}-{esc(k)}" aria-label="{L["back"]} {num}">↩</a>' if k in text_refs else '')
                r.block_notes = None
                items.append(f'<li id="note-{lang}-{esc(k)}" value="{num}" data-source-key="{esc(k)}"><p id="{r.anchor()}">{r.text(body)}{back}</p></li>')
            html_out = f'<h2 id="{head_id}" data-source-key="heading">{L["notes"]}</h2>\n<ol class="notes-list">\n' + '\n'.join(items) + '\n</ol>'
            sections.append({'key': 'notes', 'title': L['notes'], 'html': html_out, 'cls': 'notes'})
            nav.append({'id': f'{lang}-notes', 'title': L['notes'], 'level': 1})
            continue

        if kind == 'title-pages':
            def tp_heading(b):
                return f'<p class="tp tp-{b["level"]}" id="{r.anchor()}">{r.text(b["text"])}</p>'
            sections.append({'key': 'title-pages', 'title': L['title-pages'], 'html': r.blocks(part['blocks'], heading=tp_heading), 'cls': 'title-pages'})
            nav.append({'id': f'{lang}-title-pages', 'title': L['title-pages'], 'level': 1})
            continue

        # front and back matter: the first heading opens the section, later ones are sub-heads
        heads = [b for b in part['blocks'] if b['type'] == 'h']
        base = heads[0]['level'] if heads else 2
        if kind == 'overview' and len([b for b in heads if classify(b, False) == 'overview']) > 1:
            title = L['overviews']
            first_html = f'<h2 id="{r.anchor()}" data-source-key="heading">{title}</h2>'
            sub_level = 3
        else:
            title = reading_case(plain(heads[0]['text']), lang) if heads else L.get(kind, kind)
            if kind in ('contents', 'back-matter'):
                title = L[kind]
            first_html, sub_level = None, None
        key = kind
        sid = f'{lang}-{key}'
        entry = {'id': sid, 'title': title, 'level': 1}
        nav.append(entry)
        counter = [0]

        def matter_heading(b, kind=kind, base=base, sub_level=sub_level):
            counter[0] += 1
            if counter[0] == 1 and sub_level is None:
                return f'<h2 id="{r.anchor()}" data-source-key="heading">{r.text(reading_case(strip_wrap(b["text"]), lang))}</h2>'
            if kind == 'overview' and classify(b, False) == 'overview':
                hid = f'{lang}-overview-{counter[0]}'
                nav.append({'id': hid, 'title': plain(b['text']), 'level': 2})
                return f'<h{sub_level or 2} id="{hid}" data-source-key="o{counter[0]}">{r.text(b["text"])}</h{sub_level or 2}>'
            level = min(4, max(3, b['level'] - base + 2))
            text = b['text']
            if kind == 'back-matter' and classify(b, True) == 'back':
                level, text = 2, reading_case(text, lang)
            return f'<h{level} id="{r.anchor()}">{r.text(text)}</h{level}>'
        r.flat_lists = kind == 'contents'
        body = r.blocks(part['blocks'], heading=matter_heading)
        r.flat_lists = False
        sections.append({'key': key, 'title': title, 'html': (first_html + '\n' if first_html else '') + body, 'cls': kind})

    text_refs = locals().get('text_refs', r.refs)
    unused = [k for k in notes if k not in text_refs]
    out = [f'<div class="language-view" data-lang="{lang}">']
    for s in sections:
        out.append(f'<section class="book-section {s["cls"]}" id="{lang}-{s["key"]}" data-key="{s["key"]}" '
                   f'data-title="{esc(s["title"])}" lang="{lang}" dir="ltr">\n{s["html"]}\n</section>')
    out.append('</div>')
    return '\n'.join(out), nav, [s['key'] for s in sections], {'notes': len(notes), 'unreferenced': unused,
                                                                 'multi': {k: v for k, v in text_refs.items() if v > 1}}


# --------------------------------------------------------------------------- main
def apply_fixes(text, vol, lang, report):
    if lang == 'en':  # the English title chosen for this edition (title pages and back cover)
        text = text.replace(ENGLISH_TITLE[0], ENGLISH_TITLE[1])
    for old, new in FIXES.get((vol, lang), []):
        if text.count(old) == 1:
            text = text.replace(old, new)
        else:
            report.append(f'Volume {vol} {lang}: fix not applied (text not found once): {old[:50]!r}')
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source', type=Path, help='folder with the eight supplied Markdown files')
    args = ap.parse_args()
    library = json.loads((ROOT / 'library.json').read_text())
    taken = [json.loads((ROOT / r / 'book.json').read_text())['searchId'] for b in library['books'] for r in b['readers']
             if not r.startswith(WORK + '/')]
    next_id = max(taken) + 1
    report, zip_entries = [], []
    for vol in (1, 2, 3, 4):
        v = ROMAN[vol - 1]
        folder = ROOT / WORK / f'volume-{vol}'
        (folder / 'figures').mkdir(parents=True, exist_ok=True)
        figures = Figures(folder / 'figures')
        fragments, navs, keys, texts = [], {}, {}, {}
        for lang in ('en', 'fr'):
            src = args.source / SOURCE_NAMES[lang].format(v=v)
            text = apply_fixes(src.read_text(encoding='utf-8'), vol, lang, report)
            texts[lang] = text
            fragment, navs[lang], keys[lang], info = convert(text, lang, vol, figures)
            fragments.append(fragment)
            if info['unreferenced']:
                report.append(f'Volume {v} {lang}: notes never referenced in the text: {", ".join(info["unreferenced"])}')
            if info['multi']:
                report.append(f'Volume {v} {lang}: notes referenced more than once: {", ".join(f"{k} ×{n}" for k, n in info["multi"].items())}')
        assert keys['en'] == keys['fr'], f'Volume {v}: sections differ\n en {keys["en"]}\n fr {keys["fr"]}'
        for lang in ('en', 'fr'):
            name = DOWNLOADS[lang].format(v=v)
            (folder / name).write_text(texts[lang], encoding='utf-8')
            zip_entries.append((name, texts[lang]))
        for old in (folder / 'figures').iterdir():
            if old.name not in figures.files:
                old.unlink()
        for name, data in figures.files.items():
            (folder / 'figures' / name).write_bytes(data)
        if not figures.files:
            (folder / 'figures').rmdir()
        (folder / 'index.html').write_text('<!-- BOOK-CONTENT:START -->\n' + '\n'.join(fragments) + '\n<!-- BOOK-CONTENT:END -->\n', encoding='utf-8')
        meta = VOLUMES[vol]
        version = hashlib.sha256((texts['en'] + texts['fr']).encode()).hexdigest()[:16]
        book_path = folder / 'book.json'
        old = json.loads(book_path.read_text()) if book_path.exists() else {}
        book = {
            'searchId': old.get('searchId', next_id + vol - 1),
            'slug': f'{WORK}-volume-{vol}', 'path': f'{WORK}/volume-{vol}',
            'pageTitle': f'Within Iranian Islam — Volume {v}',
            'description': f'Henry Corbin’s Within Iranian Islam (En Islam iranien), Volume {v}: {meta["title"]["en"]}. '
                           'Free English translation with the complete French original.',
            'languages': ['en', 'fr'], 'langKey': f'minimal-library-lang-{WORK}',
            'title': {'en': 'Within Iranian Islam', 'fr': 'En Islam iranien'},
            'subtitle': meta['title'],
            'author': {'en': 'Henry Corbin', 'fr': 'Henry Corbin'},
            'edition': {'en': f'French edition · Gallimard, {meta["year"]}', 'fr': f'Édition originale · Gallimard, {meta["year"]}'},
            'downloads': {lang: DOWNLOADS[lang].format(v=v) for lang in ('en', 'fr')},
            'home': {'href': '../', 'label': 'All four volumes'},
            'series': {'work': WORK, 'volume': vol},
            'review': {'slug': f'{WORK}-volume-{vol}', 'title': f'Within Iranian Islam — Volume {v}', 'sourceLanguage': 'fr',
                       'version': old.get('review', {}).get('version', version),
                       'englishMarkdown': DOWNLOADS['en'].format(v=v), 'sourceMarkdown': DOWNLOADS['fr'].format(v=v)},
            'nav': navs,
        }
        book_path.write_text(json.dumps(book, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Volume {v}: {len(keys["en"])} sections, {len(navs["en"])} / {len(navs["fr"])} contents entries, {len(figures.files)} figures')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, text in zip_entries:
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 5, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, text.encode('utf-8'))
    (ROOT / WORK / ZIP_NAME).write_bytes(buf.getvalue())
    for line in report:
        print('note:', line)


if __name__ == '__main__':
    main()
