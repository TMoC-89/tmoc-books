#!/usr/bin/env python3
"""Import the nine-volume Arabic/English Four Journeys edition.

Usage:
    python3 tools/import_four_journeys.py /path/to/Arabic-and-English-folder
    python3 tools/build.py

Input: Arabic/Asfar_Volume_01_Arabic.md ... 09, and matching English/ files.
The site uses the established bilingual reader and Reviewer Mode, section pairing,
notes at the end, full-text search and offline Markdown downloads.
The source Markdown is copied byte-for-byte (the editorial corrections belong in it).
"""
import hashlib
import html
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

from import_en_islam_iranien import Renderer, LABELS, parse_blocks, plain

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'four-journeys'
ROMAN = 'I II III IV V VI VII VIII IX'.split()
TITLE_EN = 'The Four Journeys of the Intellect'
TITLE_AR = 'الحكمة المتعالية في الأسفار العقلية الأربعة'
AUTHOR_AR = 'صدر الدين محمد الشيرازي'
AUTHOR_EN = 'Mulla Sadra'
ARCHIVE = 'The Four Journeys - Complete Bilingual Markdown.zip'
LABELS['ar'] = {'note':'حاشية','back':'العودة إلى المتن'}

# Index of the English ### heading that corresponds to each Arabic ### heading.
# The English translation occasionally promotes a short discussion to ###, without
# an equivalent Arabic heading. Those stay inside their parent section, not split off.
PAIRED = {
    1: [0, 1, 2, 4, 13, 14],
    4: [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
    5: [0, 5, 6, 7, 8, 9, 10],
    6: [0, 1, 2, 3, 5, 7, 8, 9],
}
VOLUME_SUBTITLES = [
    'General Questions: Existence and Essence',
    'Essence, Unity, and Causation',
    'Potentiality, Change, Time, and Intellect',
    'Natural Philosophy: Quantity and Quality',
    'Natural Philosophy: Substances and Accidents',
    'Knowledge of God',
    'Divine Speech, Providence, and Creation',
    'The Soul and the Afterlife',
    'The Soul and the Afterlife',
]
BLURBS = [
    'The first journey begins with existence: its meaning, reality, necessity, possibility, and the way things come to be.',
    'The inquiry continues through essence, unity, multiplicity, causes, and the relations between things.',
    'Potential and actual being, change and motion, time and eternity, and intellect and what it understands.',
    'A study of natural philosophy: quantity, quality, relation, and the categories through which things are described.',
    'Bodies, matter and form, the kinds of physical things, and the principles of natural change.',
    'The third journey begins: arguments about the Necessary Being, oneness, divine attributes, knowledge, and power.',
    'The inquiry into divine speech, providence, mercy, creation, and the lasting generosity of the first principle.',
    'The fourth journey begins with the soul: its powers, perception, and its relation to the body and intellect.',
    'The final volume examines the soul after death, spiritual happiness, resurrection, and the world to come.',
]
# Printed Arabic footnote V06-168 ('السيب: العطاء') has no corresponding
# term or reference in the supplied main text. It is retained as an identified
# unlinked note, rather than attaching it to an unrelated passage.
UNLINKED = {'V06-168'}


def load_notes(text, lang, vol):
    head = '## Notes' if lang == 'en' else '## الحواشي'
    assert text.count('\n' + head + '\n') == 1, (vol,lang,'expected notes heading')
    before, after = text.split('\n'+head+'\n', 1)
    pattern = re.compile(r'^\[\^([^\]]+)\]:[ \t]*', re.M)
    found = list(pattern.finditer(after))
    notes = {}
    for k, m in enumerate(found):
        key = m.group(1)
        assert key not in notes, (vol,lang,'duplicate',key)
        end = found[k+1].start() if k+1 < len(found) else len(after)
        # The four-space indentation on continuation lines belongs to the note.
        value = after[m.end():end].strip('\n')
        value = re.sub(r'(?m)^ {4}', '', value).strip()
        notes[key] = value
    assert len(notes) > 0
    assert all(re.fullmatch(fr'V{vol:02}-\d+',k) for k in notes)
    return before.strip(), notes


def convert(text, lang, vol):
    body, notes = load_notes(text, lang, vol)
    blocks = parse_blocks(body.splitlines())
    markers = [i for i,b in enumerate(blocks) if b['type']=='h' and b['level']==3]
    assert markers, (vol,lang,'no section headings')
    if lang=='en':
        selected = PAIRED.get(vol,list(range(len(markers))))
        markers = [markers[j] for j in selected]
    # Arabic is the reference for section starts, both languages get identical
    # keys; their smaller headings and paragraphs can vary without breaking the pairing.
    chunks = []
    starts = [0]+markers+[len(blocks)]
    for i in range(len(starts)-1):
        chunks.append(blocks[starts[i]:starts[i+1]])
    assert len(chunks)==len(markers)+1
    renderer = Renderer(lang, None, notes)
    # Notes and navigation stay separate so there are no note paragraphs inside body.
    navigation, sections = [], []
    for i, chunk in enumerate(chunks):
        key = 'front-matter' if i==0 else f'part-{i:02d}'
        title = ('Front matter' if lang=='en' else 'المقدمة والفهرس') if i==0 else plain(chunk[0]['text'])
        def heading(b):
            t=plain(b['text'])
            h=min(4,max(2,b['level']-1))
            if b['level']==1: h=2
            if b['level']==2: h=2
            hid=renderer.anchor()
            # full navigable outline, without treating decorative introduction headings as chapters
            if b['level']>=3:
                lvl = 1 if b['level']==3 else 2
                navigation.append({'id':hid,'title':t,'level':lvl})
            elif b['level']==2 and ('Contents' in t or 'المحتويات' in t):
                navigation.append({'id':hid,'title':t,'level':1})
            meta=' data-source-key="major"' if b['level']==3 and b is chunk[0] else ''
            return f'<h{h} id="{hid}"{meta}>{renderer.text(b["text"])}</h{h}>'
        renderer.flat_lists = i==0
        section_html = renderer.blocks(chunk, heading=heading)
        renderer.flat_lists = False
        sections.append((key,title,section_html,'front-matter' if i==0 else 'chapter'))
    referenced = set(renderer.refs)
    assert referenced <= set(notes), (vol,lang,'undefined footnote')
    unlinked=set(notes)-referenced
    assert unlinked == (UNLINKED if vol==6 else set()), (vol,lang,'unexpected unlinked',unlinked)
    # Render each note explicitly at the end even if the printed source lacks an anchor.
    note_items = []
    for key, content in notes.items():
        num = int(key.rsplit('-',1)[1])
        back = (f' <a class="backref" href="#ref-{lang}-{html.escape(key)}" '
                f'aria-label="{"Back to text" if lang=="en" else "العودة إلى المتن"} {num}">↩</a>') if key in referenced else ''
        flag = ('<p class="note-editorial-label">No matching term in the digitized text · preserved for completeness</p>'
                if lang=='en' else '<p class="note-editorial-label">مصطلح دون موضع واضح في المتن الرقمي · أُبقي على الحاشية للاكتمال</p>') if key in unlinked else ''
        note_blocks = parse_blocks(content.splitlines())
        note_html=renderer.blocks(note_blocks)
        # A separate back link avoids attaching it to only the last paragraph.
        note_items.append(f'<li id="note-{lang}-{key}" value="{num}" data-source-key="{key}">{flag}{note_html}{back}</li>')
    title='Notes' if lang=='en' else 'الحواشي'
    notes_html=f'<h2 id="{lang}-notes-head" data-source-key="heading">{title}</h2><ol class="notes-list">'+ '\n'.join(note_items) +'</ol>'
    sections.append(('notes',title,notes_html,'notes'))
    navigation.append({'id':f'{lang}-notes-head','title':title,'level':1})
    out=[f'<div class="language-view" data-lang="{lang}">']
    for key,title,inner,cls in sections:
        direction = 'rtl' if lang=='ar' else 'ltr'
        out.append(f'<section class="book-section {cls}" id="{lang}-{key}" data-key="{key}" '
                   f'data-title="{html.escape(title,quote=True)}" lang="{lang}" dir="{direction}">\n{inner}\n</section>')
    out.append('</div>')
    return '\n'.join(out),navigation,notes,referenced,[(x[0],x[1]) for x in sections]


def main():
    if len(sys.argv)!=2:
        sys.exit('Usage: python3 tools/import_four_journeys.py /path/to/bilingual-markdown-folder')
    source=Path(sys.argv[1]);assert source.is_dir()
    lib_path=ROOT/'library.json';lib=json.loads(lib_path.read_text(encoding='utf8'))
    target=ROOT/SLUG;target.mkdir(exist_ok=True)
    roman=ROMAN
    reports=[]
    with zipfile.ZipFile(target/ARCHIVE,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for n in range(1,10):
            vol_dir=target/f'volume-{n}';vol_dir.mkdir(exist_ok=True)
            outputs=[];navs={};metadata={};notesets={};refsets={};sections={}
            for lang,source_lang in [('en','English'),('ar','Arabic')]:
                src=source/source_lang/f'Asfar_Volume_{n:02}_{source_lang}.md'
                assert src.is_file(),src
                outfile = f'Volume {roman[n-1]} - {source_lang}.md'
                shutil.copyfile(src,vol_dir/outfile)
                z.write(src,f'{source_lang}/{src.name}')
                contents=src.read_text(encoding='utf8')
                rendered,nav,notes,refs,sect=convert(contents,lang,n)
                outputs.append(rendered);navs[lang]=nav;notesets[lang]=set(notes);refsets[lang]=refs;sections[lang]=sect
                metadata[lang]={'file':outfile,'sha':hashlib.sha256(contents.encode()).hexdigest()}
            assert notesets['en']==notesets['ar'],(n,'note ids disagree')
            assert refsets['en']==refsets['ar'],(n,'reference ids disagree')
            assert [a for a,b in sections['en']]==[a for a,b in sections['ar']],(n,'section keys disagree')
            # English first, Arabic second: the site's established reader defaults to English.
            raw='\n'.join(outputs)
            (vol_dir/'index.html').write_text('<!-- BOOK-CONTENT:START -->\n'+raw+'\n<!-- BOOK-CONTENT:END -->',encoding='utf8')
            edition={
                'searchId': 15+n, 'slug':f'{SLUG}-volume-{n}', 'path':f'{SLUG}/volume-{n}',
                'pageTitle':f'{TITLE_EN} — Volume {roman[n-1]}',
                'description':f'Mulla Sadra’s {TITLE_EN}, Volume {roman[n-1]}. Complete English translation with the original Arabic.',
                'languages':['en','ar'], 'langKey':f'minimal-library-lang-{SLUG}',
                'title':{'en':TITLE_EN,'ar':TITLE_AR},
                'subtitle':{'en':VOLUME_SUBTITLES[n-1],
                            'ar':next((x[3:].strip() for x in (source/'Arabic'/f'Asfar_Volume_{n:02}_Arabic.md').read_text().splitlines() if x.startswith('## ') and x!='## المحتويات'),'')},
                'author':{'en':AUTHOR_EN,'ar':AUTHOR_AR},
                'edition':{'en':f'Volume {roman[n-1]} of IX · Arabic original and English translation',
                           'ar':f'المجلد {n} من ٩ · النص العربي والترجمة الإنجليزية'},
                'downloads':{'en':metadata['en']['file'],'ar':metadata['ar']['file']},
                'home':{'href':'../','label':'All nine volumes'},
                'series':{'work':SLUG,'volume':n},
                'review':{'slug':f'{SLUG}-volume-{n}',
                          'title':f'{TITLE_EN} — Volume {roman[n-1]}',
                          'sourceLanguage':'ar',
                          'version':hashlib.sha256((metadata['en']['sha']+metadata['ar']['sha']).encode()).hexdigest()[:16],
                          'englishMarkdown':metadata['en']['file'],
                          'sourceMarkdown':metadata['ar']['file']},
                'nav':navs,
            }
            (vol_dir/'book.json').write_text(json.dumps(edition,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
            reports.append({'volume':n,'notes':len(notesets['en']),'unlinked':sorted(notesets['en']-refsets['en']),
                            'sections':len(sections['en'])})
    entry={
        'no':11,'shelf':'arabic','href':f'{SLUG}/','series':SLUG,'tag':'Latest addition',
        'title':TITLE_EN, 'subtitle':'The Transcendent Wisdom of the Four Intellectual Journeys',
        'originalTitle':{'lang':'ar','text':TITLE_AR},'author':'Mulla Sadra',
        'readers':[f'{SLUG}/volume-{n}' for n in range(1,10)],
        'description':'Mulla Sadra’s monumental nine-volume work on existence, God, nature, the soul and the afterlife, in English with the original Arabic alongside.'
    }
    for b in lib['books']:b.pop('tag',None)
    lib['books']=[b for b in lib['books'] if b.get('href')!=entry['href']]
    lib['books'].insert(0,entry)
    series={
        'title':TITLE_EN,'shortTitle':'The Four Journeys','subtitle':'The Transcendent Wisdom of the Four Intellectual Journeys',
        'originalTitle':{'lang':'ar','text':TITLE_AR},'author':'Mulla Sadra',
        'authorAr':AUTHOR_AR,'edition':'Nine-volume bilingual edition',
        'zip':ARCHIVE,
        'lead':'Mulla Sadra’s great philosophical work, The Transcendent Wisdom in the Four Intellectual Journeys, traces the path from the questions of existence and causation to the nature of God, the world, the soul and the afterlife. Read all nine volumes in English or switch to the original Arabic at any point. Every volume has its own table of contents and endnotes; the complete bilingual Markdown is available to download.',
        'volumes':[
            {'n':n,'roman':roman[n-1],'path':f'{SLUG}/volume-{n}',
             'title':VOLUME_SUBTITLES[n-1],
             'original':json.loads((target/f'volume-{n}'/'book.json').read_text())['subtitle']['ar'],
             'blurb':BLURBS[n-1]} for n in range(1,10)]
    }
    lib['series'][SLUG]=series
    lib_path.write_text(json.dumps(lib,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(reports,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
