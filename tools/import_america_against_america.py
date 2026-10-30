#!/usr/bin/env python3
"""Prepare Wang Huning's America Against America as a reviewed English/Chinese reader.

Input: two complete Markdown files, one English and one Chinese. Paragraphs are
not shortened, retranslated or automatically merged: the 1991 Chinese text and
English and Chinese versions have different paragraph boundaries.

Each numbered section receives the same stable key in both languages. The
chapter + section outline is explicitly reviewed and hashed in contents.json,
following the improved Four Journeys edition. The importer can be rerun; it
writes download Markdown files, book content, metadata and the outline review.
"""
import argparse
import hashlib
import html
import json
import re
import shutil
import zipfile
from pathlib import Path
from import_en_islam_iranien import Renderer, parse_blocks, plain, LABELS

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'america-against-america'
LABELS['zh'] = {'note': '注释', 'back': '返回正文'}
CJK_SECTION = re.compile(r'(?m)^## ([1-9][0-9]*)[\s\u3000.、．]+([^\n]+)$')
CHAPTER = re.compile(r'^Chapter ([1-9][0-9]*)\s*(?:[—–-]|:)\s+')
CJK_CHAPTER = re.compile(r'^([一二三四五六七八九十]+)[、\s\u3000]+')


def clean_source(text, lang):
    text = text.lstrip('\ufeff').replace('\r\n','\n').replace('\r','\n')
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()+'\n'
    if lang == 'zh':
        # Only normalize heading numbering: no words or punctuation in prose change.
        text = CJK_SECTION.sub(lambda m: f'## {m.group(1)}. {m.group(2).strip()}', text)
        text = re.sub(r'(?m)^# ([一二三四五六七八九十]+)[\s\u3000]+([^\n]+)$',r'# \1、\2', text)
    else:
        text = re.sub(r'(?m)^(# |\s*- )Chapter (\d+) — ', r'\1Chapter \2: ', text)
    return text


def split_chapters(text, lang):
    blocks=parse_blocks(text.splitlines())
    heads=[(i,b) for i,b in enumerate(blocks) if b['type']=='h']
    assert heads and heads[0][1]['level']==1
    ch=[(i,b) for i,b in heads if b['level']==1]
    assert len(ch)==12,(lang,len(ch))
    assert (len([1 for _,b in heads if b['level']==2])==87),lang
    front=blocks[:ch[1][0]]
    start_pref=next(i for i,b in enumerate(front) if b['type']=='h' and b['level']==2 and (plain(b['text']) in ('Preface','序')))
    start_toc=next(i for i,b in enumerate(front) if b['type']=='h' and b['level']==2 and (plain(b['text']) in ('Contents','目录')))
    assert 0<start_pref<start_toc
    sections=[('opening',front[:start_pref]),('preface',front[start_pref:start_toc]),('contents',front[start_toc:])]
    chapters=[]
    for c in range(1,12):
        a=ch[c][0];b=ch[c+1][0] if c+1<len(ch) else len(blocks)
        chunk=blocks[a:b]
        assert chunk[0]['type']=='h' and chunk[0]['level']==1
        m=CHAPTER.match(plain(chunk[0]['text'])) if lang=='en' else CJK_CHAPTER.match(plain(chunk[0]['text']))
        assert m,(lang,c,chunk[0]['text'])
        if lang=='en':assert int(m.group(1))==c
        positions=[i for i,v in enumerate(chunk) if v['type']=='h' and v['level']==2]
        assert positions and positions[0]==1,(lang,c,'section headings')
        numbers=[]
        for pos in positions:
            mm=re.match(r'^(\d+)[.\s\u3000]+',plain(chunk[pos]['text']))
            assert mm,(lang,c,chunk[pos]['text'])
            numbers.append(int(mm.group(1)))
        assert numbers==list(range(1,len(numbers)+1)),(lang,c,numbers)
        for j,pos in enumerate(positions):
            end=positions[j+1] if j+1<len(positions) else len(chunk)
            sub=([chunk[0]] if j==0 else [])+chunk[pos:end]
            sections.append((f'chapter-{c:02}-section-{j+1:02}',sub))
        chapters.append(len(positions))
    assert len(sections)==88,(lang,len(sections))
    return sections,chapters


def render(text,lang):
    sections,counts=split_chapters(text,lang)
    r=Renderer(lang,None,{})
    parts=[f'<div class="language-view" data-lang="{lang}">']
    nav=[]
    opening={'en':('Opening pages','Preface','Printed contents'),
             'zh':('书名与版本信息','序','原书目录')}[lang]
    for key,blocks in sections:
        titles=[]
        def heading(b):
            label=plain(b['text']);tag='h2' if b['level']==1 else 'h3'
            hid=r.anchor()
            if key=='opening':
                # The book title also appears on its cover, not in the sidebar twice.
                return f'<h2 id="{hid}">{r.text(b["text"])}</h2>'
            level=1 if (b['level']==1 or key in {'preface','contents'}) else 2
            kind='chapter' if b['level']==1 else ('section' if level==2 else 'division')
            nav.append({'id':hid,'title':label,'level':level})
            titles.append(label)
            source_key='chapter-heading' if b['level']==1 else 'section-heading'
            return f'<{tag} id="{hid}" data-source-key="{source_key if level==1 else "section-heading"}">{r.text(b["text"])}</{tag}>'
        content=r.blocks(blocks,heading=heading)
        title=(opening[{'opening':0,'preface':1,'contents':2}[key]] if key in {'opening','preface','contents'}
               else next((x for x in reversed(titles) if not CHAPTER.match(x) and not CJK_CHAPTER.match(x)),titles[-1] if titles else key))
        cls=' title-pages' if key=='opening' else ' printed-contents' if key=='contents' else ''
        parts.append(f'<section class="book-section{cls}" id="{lang}-{key}" data-key="{key}" data-title="{html.escape(title,quote=True)}" lang="{lang}" dir="ltr">\n{content}\n</section>')
    parts.append('</div>')
    assert not r.refs,(lang,'unexpected footnotes')
    assert len(nav)==98,(lang,len(nav)) # 2 front matter, 11 chapter headings, 85 sections
    return '\n'.join(parts),nav,counts


def reviewed_nav(nav):
    entries=[{'id':'', 'level':1,'kind':'opening','label':''}]
    entries=[]
    for item in nav:
        text=item['title'];isfront=text in ('Preface','Contents','序','目录')
        kind='opening' if isfront else 'chapter' if item['level']==1 else 'section'
        entry={'id':item['id'],'level':item['level'],'kind':kind,'label':text}
        entries.append(entry)
    return {'sourceHash':hashlib.sha256(json.dumps(nav,ensure_ascii=False).encode()).hexdigest(), 'entries':entries}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('english',type=Path);ap.add_argument('chinese',type=Path);args=ap.parse_args()
    target=ROOT/SLUG;target.mkdir(exist_ok=True)
    sources={'en':args.english,'zh':args.chinese};downloads={'en':'America Against America - English.md','zh':'美国反对美国 - 中文.md'}
    rendered={};nav={};chapter_counts={}
    for lang,path in sources.items():
        raw=path.read_text(encoding='utf-8-sig')
        cleaned=clean_source(raw,lang)
        (target/downloads[lang]).write_text(cleaned,encoding='utf-8')
        rendered[lang],nav[lang],chapter_counts[lang]=render(cleaned,lang)
    assert chapter_counts['en']==chapter_counts['zh'],(chapter_counts['en'],chapter_counts['zh'])
    assert chapter_counts['en']==[8,8,10,7,7,7,8,6,7,7,10]
    assert all(('chapter-%02d-section-%02d'%(c,j)) in rendered['en'] for c,num in enumerate(chapter_counts['en'],1) for j in range(1,num+1))
    (target/'index.html').write_text('<!-- BOOK-CONTENT:START -->\n'+rendered['en']+'\n'+rendered['zh']+'\n<!-- BOOK-CONTENT:END -->\n',encoding='utf-8')
    book={
      'searchId':25, 'slug':SLUG,'path':SLUG,'pageTitle':'America Against America — Wang Huning',
      'description':"Wang Huning’s America Against America, an eleven-chapter study of American society and politics based on his 1988–89 visit, in English and the original Chinese.",
      'languages':['en','zh'],'langKey':'minimal-library-lang-america-against-america',
      'title':{'en':'America Against America','zh':'美国反对美国'},
      'subtitle':{'en':'An Observer’s Study of American Society, 1988–1989','zh':'1988—1989年美国社会观察'},
      'author':{'en':'Wang Huning','zh':'王沪宁'},
      'edition':{'en':'English · Chinese original published 1991',
                 'zh':'中文原著 · 上海文艺出版社，1991年 · 英文版'},
      'downloads':downloads,'bilingualZip':'America Against America - Complete Bilingual Markdown.zip','home':{'href':'../','label':'Library'},
      'review':{'slug':SLUG,'title':'America Against America','sourceLanguage':'zh',
                'sourceLabel':'Chinese original','version':hashlib.sha256((target/downloads['en']).read_bytes()+(target/downloads['zh']).read_bytes()).hexdigest()[:16],
                'englishMarkdown':downloads['en'],'sourceMarkdown':downloads['zh']},
      'nav':nav,'contentsFile':'contents.json',
    }
    (target/'book.json').write_text(json.dumps(book,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    contents={'version':1,'initiallyCollapsed':True,'languages':{l:reviewed_nav(n) for l,n in nav.items()}}
    (target/'contents.json').write_text(json.dumps(contents,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    library=ROOT/'library.json';data=json.loads(library.read_text(encoding='utf-8'))
    data['shelves'].append({'id':'chinese','label':'From the Chinese','region':'East Asia','language':'Chinese'}) if not any(x['id']=='chinese' for x in data['shelves']) else None
    for b in data['books']:b.pop('tag',None)
    card={'no':12,'shelf':'chinese','href':SLUG+'/', 'tag':'Latest addition',
          'title':'America Against America','subtitle':'An Examination of American Society and Its Contradictions',
          'originalTitle':{'lang':'zh','text':'美国反对美国'},'author':'Wang Huning','readers':[SLUG],
          'description':'An eleven-chapter study of American life, politics, institutions, and the forces that contradict one another, translated from the 1991 Chinese book.'}
    data['books']=[card]+[b for b in data['books'] if b['href']!=SLUG+'/']
    library.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with zipfile.ZipFile(target/'America Against America - Complete Bilingual Markdown.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for l in ['en','zh']:z.write(target/downloads[l],downloads[l])
    print('Imported: 11 chapters, 85 sections, 98 curated contents links per language; bilingual Markdown ZIP ready.')

if __name__=='__main__': main()
