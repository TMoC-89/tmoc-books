/* All corpus parsing and ranking runs off the UI thread. Only matching partitions are fetched. */
const cache = new Map();
let manifestPromise, active = 0;
const normalize = value => value.normalize('NFKD').replace(/\p{M}|\u0640/gu, '').replace(/[أإآٱ]/g,'ا').toLowerCase();
const tokenize = value => normalize(value).match(/[\p{L}\p{N}]+/gu) || [];
const bucket = term => [...term].slice(0,2).map(c=>c.codePointAt(0).toString(16)).join('-');
async function json(url) {
  if (!cache.has(url)) cache.set(url, fetch(url).then(r=>{if(!r.ok)throw Error('A search file could not be loaded. Please try again.');return r.json()}).catch(e=>{cache.delete(url);throw e}));
  const result=cache.get(url);cache.delete(url);cache.set(url,result);
  while(cache.size>96)cache.delete(cache.keys().next().value);
  return result;
}
function manifest() { return manifestPromise ||= json('data/manifest.json'); }
function querySpec(query) {
  const phrases = [...query.matchAll(/["“]([^"”]+)["”]/g)].map(m=>tokenize(m[1]).join(' ')).filter(Boolean);
  const terms = [...new Set(tokenize(query))];
  return {terms, phrases};
}
function ranges(text, expansions) {
  const output=[];let normalized='',map=[];
  for(let pos=0;pos<text.length;) {
    const c=String.fromCodePoint(text.codePointAt(pos)),n=normalize(c);
    for(const unit of n){normalized+=unit;for(let i=0;i<unit.length;i++)map.push([pos,pos+c.length]);}
    pos+=c.length;
  }
  for(const m of normalized.matchAll(/[\p{L}\p{N}]+/gu)) if(expansions.has(m[0]))output.push([map[m.index][0],map[m.index+m[0].length-1][1]]);
  return output;
}
function excerpt(text, hits) {
  const first=hits[0]?.[0]||0;
  let start=Math.max(0,first-115),end=Math.min(text.length,start+360);
  if(start>0){const boundary=text.lastIndexOf('. ',first);if(boundary>=start)start=boundary+2;else{const space=text.indexOf(' ',start);if(space<first)start=space+1;}}
  end=Math.min(text.length,Math.max(start+360,(hits[0]?.[1]||0)+80));
  if(end<text.length){const space=text.lastIndexOf(' ',end);if(space>first)end=space;}
  const prefix=start>0?'… ':'';const suffix=end<text.length?' …':'';
  return {text:prefix+text.slice(start,end)+suffix,highlights:hits.filter(([a,b])=>a>=start&&b<=end).map(([a,b])=>[a-start+prefix.length,b-start+prefix.length])};
}
async function search(message) {
  const {id,q,book,language}=message;active=id;
  const m=await manifest();if(active!==id)return;
  const spec=querySpec(q);
  const indexedTerms=spec.terms.filter(t=>t.length>=2);
  if(!indexedTerms.length) { postMessage({id,type:'results',results:[],total:0,books:m.books,message:'Include a word with at least two letters.'});return; }
  const known=new Set(m.buckets);
  const partitions=await Promise.all([...new Set(indexedTerms.map(bucket))].map(async key=>[key,known.has(key)?await json(`data/terms/${key}.json?v=${m.version}`):{}]));
  if(active!==id)return;
  const lookup=new Map(partitions),variants=[],expanded=new Set();let candidates=null;
  for(const term of indexedTerms) {
    const dict=lookup.get(bucket(term));const forms=Object.keys(dict).filter(t=>t===term || (!spec.phrases.length && term.length>=4 && t.startsWith(term))).sort((a,b)=>a.length-b.length).slice(0,40);
    forms.forEach(t=>expanded.add(t));variants.push(new Set(forms));const ids=new Set(forms.flatMap(t=>dict[t]));
    candidates=candidates===null?ids:new Set([...candidates].filter(x=>ids.has(x)));
  }
  const ids=[...candidates].filter(id=>{const meta=m.chunkMeta?.[id];return !meta || ((book==='all'||meta[0]===Number(book))&&(language==='all'||meta[1].includes(language)))}).sort((a,b)=>a-b),matches=new Map();let cursor=0,done=0;
  postMessage({id,type:'progress',done:0,total:ids.length});
  async function runner() {
    while(cursor<ids.length && active===id) {
      const cid=ids[cursor++],records=await json(`data/passages/${cid}.json?v=${m.version}`);
      if(active!==id)return;
      for(const r of records) {
        if(book!=='all' && r[0]!==Number(book))continue;
        if(language!=='all' && r[1]!==language)continue;
        const words=tokenize(r[4]),wordsSet=new Set(words);
        if(!variants.every(v=>[...v].some(t=>wordsSet.has(t))))continue;
        if(!spec.terms.filter(t=>t.length<2).every(t=>wordsSet.has(t)))continue;
        const joined=words.join(' ');
        if(!spec.phrases.every(p=>(' '+joined+' ').includes(' '+p+' ')))continue;
        const hits=ranges(r[4],expanded);if(!hits.length)continue;
        let score=spec.terms.reduce((n,t)=>n+(wordsSet.has(t)?30:12),0)+Math.min(hits.length,8)*2;
        if(joined.includes(spec.terms.join(' ')))score+=24;
        if(spec.terms.some(t=>tokenize(r[2]).includes(t)))score+=8;
        score+=Math.max(0,8-r[4].length/250);
        const key=`${r[0]}:${r[1]}:${r[3]}`;
        if(!matches.has(key)||matches.get(key).score<score)matches.set(key,{book:r[0],language:r[1],section:r[2],anchor:r[3],score,...excerpt(r[4],hits)});
      }
      done++;
      if(done%8===0)postMessage({id,type:'progress',done,total:ids.length});
    }
  }
  await Promise.all(Array.from({length:Math.min(4,ids.length)},runner));
  if(active!==id)return;
  const results=[...matches.values()].sort((a,b)=>b.score-a.score||a.book-b.book||a.anchor.localeCompare(b.anchor));
  postMessage({id,type:'results',results:results.slice(0,500),total:results.length,books:m.books});
}
self.onmessage=e=>{
  if(e.data.type==='init'){manifest().then(m=>postMessage({type:'ready',books:m.books,passages:m.passages})).catch(err=>postMessage({type:'error',message:err.message}));return;}
  if(e.data.type==='cancel'){active=e.data.id;return;}
  search(e.data).catch(err=>{if(e.data.id===active)postMessage({id:e.data.id,type:'error',message:err.message})});
};
