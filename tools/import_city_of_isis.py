#!/usr/bin/env python3
"""Import the supplied final Markdown pair, then run tools/build.py.

Usage: python3 tools/import_city_of_isis.py /path/to/final-markdown-pair
The downloads are copied byte for byte. This renderer handles the syntax used in
this pair only; it escapes all text and does not execute or interpret raw HTML.
"""
import argparse
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'the-city-of-isis'
FILES = {'en': 'The City of Isis - English.md', 'fr': "La Cité d'Isis - French.md"}
ROMANS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
TITLES = {
    'en': ['From the Pyramids to the Medici Chapel', 'Five Seas, Five Rivers, Five Empires',
           'The Seven Planets', 'The Divine Lessons', 'Astronomy and the Art of Living',
           'The Great Aramean King', 'Ptolemies and Seleucids: Hereditary Rivals',
           'Rome, an Egyptian Colony', 'Byzantium and the Holy Wars', 'The Peace of Islam'],
    'fr': ['Des Pyramides à la chapelle Médicis', 'Cinq mers, cinq fleuves, cinq empires',
           'Les sept planètes', 'Les divines leçons', 'Astronomie et art de vivre',
           'Le Grand Roi araméen', 'Ptolémées et Séleucides : adversaires héréditaires',
           'Rome, colonie égyptienne', 'Byzance et les guerres saintes', 'La paix de l’Islam'],
}
LABELS = {
    'en': ['Title pages & Translator’s Note', 'Preface', 'Printed Contents & Colophon', 'Footnotes'],
    'fr': ['Pages de titre', 'Préface', 'Table des matières & Achevé d’imprimer', 'Notes'],
}
esc = lambda text: html.escape(text, quote=True)


class Renderer:
    def __init__(self, lang):
        self.lang, self.passage = lang, 0
        self.refs = set()
        self.source_prefix, self.source_count, self.translation_only = '', 0, False

    def anchor(self):
        self.passage += 1
        return f'passage-{self.lang}-{self.passage:05d}'

    def inline(self, text):
        out, stack = [], []
        for token in re.split(r'(\*\*|\*|\[\^[^\]]+\])', text):
            if token in ('*', '**'):
                tag = 'em' if token == '*' else 'strong'
                if stack and stack[-1] == token:
                    stack.pop()
                    out.append(f'</{tag}>')
                else:
                    stack.append(token)
                    out.append(f'<{tag}>')
            elif token.startswith('[^') and token.endswith(']'):
                key = token[2:-1]
                assert key not in self.refs, f'Duplicate footnote reference: {key}'
                self.refs.add(key)
                number = int(key.rsplit('-', 1)[1])
                label = 'Note' if self.lang == 'fr' else 'Footnote'
                out.append(f'<sup class="note-ref" id="ref-{self.lang}-{esc(key)}"><a href="#note-{self.lang}-{esc(key)}" aria-label="{label} {number}">{number}</a></sup>')
            else:
                out.append(esc(token))
        assert not stack, f'Unbalanced emphasis: {text[:100]}'
        return ''.join(out)

    def source_attr(self, depth=0):
        if depth:
            return ''
        if self.translation_only:
            return ' data-source-unavailable="true"'
        if self.source_prefix:
            self.source_count += 1
            return f' data-source-key="{self.source_prefix}-{self.source_count:03d}"'
        return ''

    def render(self, text, depth=0):
        out = []
        for block in re.split(r'\n[ \t]*\n', text.strip('\n')):
            if not block.strip():
                continue
            lines = block.splitlines()
            if all(line.startswith('>') for line in lines):
                inner = '\n'.join(re.sub(r'^> ?', '', line) for line in lines)
                source = self.source_attr(depth)
                out.append(f'<blockquote{source}>{self.render(inner, depth + 1)}</blockquote>')
            elif block.strip() == '---':
                out.append('<hr>')
            elif len(lines) == 1 and (m := re.fullmatch(r'(#{1,2}) (.+)', block)):
                tag = 'h2' if len(m[1]) == 1 else 'h3'
                title_id = f'{self.lang}-translators-note' if m[2] == 'Translator’s Note' else self.anchor()
                if m[2] == 'Translator’s Note':
                    self.translation_only = True
                out.append(f'<{tag} id="{title_id}"{self.source_attr(depth)}>{self.inline(m[2])}</{tag}>')
            elif all(re.match(r'^[IVX]+\. — .*\.{2,} \d+\s*$', line) for line in lines):
                for line in lines:
                    roman, title, page = re.fullmatch(r'([IVX]+)\. — (.*?)\s*\.{2,}\s*(\d+)\s*', line).groups()
                    out.append(f'<p class="toc-line" id="{self.anchor()}"{self.source_attr(depth)}><a href="#{self.lang}-chapter-{roman.lower()}">{roman}. — {self.inline(title)}</a><span class="toc-leader" aria-hidden="true"></span><span class="toc-page">{page}</span></p>')
            else:
                body = ''.join(self.inline(line.rstrip()) + ('<br>\n' if line.endswith('  ') else '\n') for line in lines).rstrip('\n')
                out.append(f'<p id="{self.anchor()}"{self.source_attr(depth)}>{body}</p>')
        return '\n'.join(out)

    def notes(self, text):
        out, definitions = [], set()
        for block in re.split(r'\n\s*\n', text.strip()):
            key, body = re.fullmatch(r'\[\^([^\]]+)\]: (.+)', block, re.S).groups()
            assert key not in definitions
            definitions.add(key)
            number = int(key.rsplit('-', 1)[1])
            label = 'Retour au texte' if self.lang == 'fr' else 'Back to text'
            out.append(f'<li id="note-{self.lang}-{esc(key)}" data-source-key="{esc(key)}"><p id="{self.anchor()}">{self.inline(body)} <a class="backref" href="#ref-{self.lang}-{esc(key)}" aria-label="{label} {number}">↩</a></p></li>')
        assert definitions == self.refs, (definitions, self.refs)
        assert len(definitions) == 12
        return '<ol class="notes-list">\n' + '\n'.join(out) + '\n</ol>'


def convert(text, lang):
    starts = list(re.finditer(r'^# (PREFACE|I|II|III|IV|V|VI|VII|VIII|IX|X|TABLE OF CONTENTS|TABLE DES MATIERES|FOOTNOTES|NOTES)$', text, re.M))
    assert len(starts) == 13
    parts = [('front-matter', LABELS[lang][0], text[:starts[0].start()])]
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        body = text[match.end():end].strip('\n')
        heading = match[1]
        if heading == 'PREFACE':
            key, title = 'preface', LABELS[lang][1]
        elif heading in ROMANS:
            n = ROMANS.index(heading)
            key, title = 'chapter-' + heading.lower(), f'{heading}. {TITLES[lang][n]}'
            assert body.startswith('## ')
            body = body.split('\n', 1)[1].lstrip('\n')
        elif heading.startswith('TABLE'):
            key, title = 'contents', LABELS[lang][2]
        else:
            key, title = 'footnotes', LABELS[lang][3]
        parts.append((key, title, body))
    renderer, out, nav = Renderer(lang), [f'<div class="language-view" data-lang="{lang}">'], []
    for key, title, body in parts:
        renderer.source_prefix = key if key in {'front-matter', 'preface', 'contents'} else ''
        renderer.source_count, renderer.translation_only = 0, False
        sid = f'{lang}-{key}'
        nav.append({'id': sid, 'title': title, 'level': 1})
        out.append(f'<section class="book-section" id="{sid}" data-key="{key}" data-title="{esc(title)}" lang="{lang}" dir="ltr">')
        if key != 'front-matter':
            out.append(f'<h2 id="{renderer.anchor()}" data-source-key="{key}-heading">{esc(title)}</h2>')
        out.append(renderer.notes(body) if key == 'footnotes' else renderer.render(body))
        out.append('</section>')
        if key == 'front-matter' and lang == 'en':
            nav.append({'id': 'en-translators-note', 'title': 'Translator’s Note', 'level': 2})
    out.append('</div>')
    return '\n'.join(out), nav


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    sources = {}
    for lang, suffix in [('en', 'Complete English Translation.md'), ('fr', 'Complete French Original.md')]:
        matches = list(args.source.glob('*' + suffix))
        assert len(matches) == 1, f'Expected exactly one {suffix}'
        sources[lang] = matches[0]
    folder = ROOT / SLUG
    folder.mkdir(exist_ok=True)
    content, nav = [], {}
    for lang, path in sources.items():
        shutil.copyfile(path, folder / FILES[lang])
        fragment, nav[lang] = convert(path.read_text(encoding='utf-8'), lang)
        content.append(fragment)
    (folder / 'index.html').write_text('<!-- BOOK-CONTENT:START -->\n' + '\n'.join(content) + '\n<!-- BOOK-CONTENT:END -->\n', encoding='utf-8')
    library = json.loads((ROOT / 'library.json').read_text())
    ids = [json.loads((ROOT / reader / 'book.json').read_text())['searchId'] for book in library['books'] for reader in book['readers'] if reader != SLUG]
    version = hashlib.sha256(b''.join(sources[lang].read_bytes() for lang in ['en', 'fr'])).hexdigest()[:16]
    book = {
        'searchId': max(ids) + 1, 'slug': SLUG, 'path': SLUG,
        'pageTitle': 'The City of Isis — Pierre Rossi',
        'description': 'Pierre Rossi’s The City of Isis: The True History of the Arabs, in English with the complete French original alongside.',
        'languages': ['en', 'fr'], 'langKey': 'minimal-library-lang-' + SLUG,
        'title': {'en': 'The City of Isis', 'fr': 'La Cité d’Isis'},
        'subtitle': {'en': 'The True History of the Arabs', 'fr': 'Histoire vraie des Arabes'},
        'author': {'en': 'Pierre Rossi', 'fr': 'Pierre Rossi'},
        'edition': {'en': 'French edition · Nouvelles Éditions Latines, 1976', 'fr': 'Édition originale · Nouvelles Éditions Latines, 1976'},
        'downloads': FILES, 'home': {'href': '../', 'label': 'Library'},
        'review': {'slug': SLUG, 'title': 'The City of Isis', 'sourceLanguage': 'fr', 'version': version,
                   'englishMarkdown': FILES['en'], 'sourceMarkdown': FILES['fr']},
        'nav': nav,
    }
    (folder / 'book.json').write_text(json.dumps(book, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Imported English and French: {len(nav["en"])} / {len(nav["fr"])} contents entries; 12 footnotes each.')


if __name__ == '__main__':
    main()
