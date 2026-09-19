(() => {
  const $=s=>document.querySelector(s), query=$('#query'),work=$('#work-filter'),language=$('#language-filter');
  const list=$('#results-list'),status=$('#result-summary'),title=$('#results-title'),progress=$('#search-progress'),message=$('#search-message');
  let worker,serial=0,results=[],books=[],shown=0,timer;
  const names={en:'English',ar:'Arabic',de:'German'};
  function theme(){const dark=document.documentElement.dataset.theme==='dark';$('#search-theme').textContent=dark?'☀︎':'☾';$('#search-theme').setAttribute('aria-label',dark?'Use light mode':'Use dark mode')}
  theme();$('#search-theme').addEventListener('click',()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark';try{localStorage.setItem('minimal-library-theme',document.documentElement.dataset.theme)}catch{}theme()});
  function urlState(push=false){const u=new URL(location.href);u.search='';if(query.value.trim())u.searchParams.set('q',query.value.trim());if(work.value!=='all')u.searchParams.set('work',work.value);if(language.value!=='all')u.searchParams.set('lang',language.value);if(u.href!==location.href)history[push?'pushState':'replaceState']({},'',u)}
  function readState(){const p=new URLSearchParams(location.search);query.value=(p.get('q')||'').slice(0,120);work.value=p.get('work')||'all';if(!work.value)work.value='all';language.value=p.get('lang')||'all';if(!language.value)language.value='all'}
  function showMessage(text){message.textContent=text;message.hidden=false}
  function highlighted(text,ranges){const f=document.createDocumentFragment();let pos=0;for(const [start,end]of ranges){f.append(document.createTextNode(text.slice(pos,start)));const mark=document.createElement('mark');mark.textContent=text.slice(start,end);f.append(mark);pos=end}f.append(document.createTextNode(text.slice(pos)));return f}
  function element(tag,className,text){const el=document.createElement(tag);if(className)el.className=className;if(text!==undefined)el.textContent=text;return el}
  function renderMore(){const next=results.slice(shown,shown+20),fragment=document.createDocumentFragment();
    next.forEach((r,index)=>{const b=books[r.book];const card=element('article','quote-card');card.append(element('span','quote-number',String(shown+index+1).padStart(2,'0')));const byline=element('div','quote-attribution');byline.append(element('strong','',b.title),element('span','',b.author),element('span','quote-language',names[r.language]||r.language));const quote=element('blockquote');quote.lang=r.language;quote.dir=r.language==='ar'?'rtl':'ltr';quote.append(highlighted(r.text,r.highlights));const footer=element('div','quote-footer'),section=element('span','quote-section',r.section);section.dir='auto';const link=element('a','',r.language==='de'?'View source':'Read passage');const url=new URL(b.url,location.href);url.searchParams.set('lang',r.language);url.searchParams.set('q',query.value.trim());url.searchParams.set('passage',r.anchor);if(r.language==='de')url.searchParams.set('review','1');url.hash=r.anchor;link.href=url.href;link.setAttribute('aria-label',`${r.language==='de'?'View source':'Read passage'} in ${b.title}: ${r.section}`);const arrow=element('span','','↗');arrow.setAttribute('aria-hidden','true');link.append(arrow);footer.append(section,link);card.append(byline,quote,footer);fragment.append(card)});
    list.append(fragment);shown+=next.length;$('#load-more').hidden=shown>=results.length;$('#load-more').textContent=`More passages (${results.length-shown} remaining) ↓`;
  }
  function run(push=false){clearTimeout(timer);urlState(push);const q=query.value.trim();serial++;results=[];shown=0;list.replaceChildren();message.hidden=true;$('#load-more').hidden=true;$('#search-intro').hidden=!!q;progress.hidden=true;$('#search-results').setAttribute('aria-busy','false');worker?.postMessage({type:'cancel',id:serial});
    if(!q){worker?.postMessage({type:'cancel',id:serial});title.textContent='A place to begin';document.title='Search — The Library';status.textContent='';return}
    title.textContent=`Passages for “${q}”`;document.title=`${q} — Search The Library`;
    if(q.length<2){showMessage('Type at least two letters to search.');status.textContent='';return}
    if(!worker){showMessage('Search could not start. Please reload this page.');return}
    status.textContent='Searching the texts…';progress.hidden=false;progress.firstElementChild.style.width='8%';$('#search-results').setAttribute('aria-busy','true');worker.postMessage({id:serial,q,book:work.value,language:language.value});
  }
  try{worker=new Worker('search-worker.js?v=2e87b3267c')}catch{showMessage('This browser could not start search. Please use a current browser and open the site over HTTP or HTTPS.')}
  if(worker){worker.addEventListener('message',e=>{const data=e.data;
    if(data.type==='ready'){books=data.books;const saved=new URLSearchParams(location.search).get('work')||'all';for(const b of books){const opt=element('option','',b.title);opt.value=b.id;work.append(opt)}work.value=saved;if(!work.value)work.value='all';if(query.value.trim())run();return}
    if(data.id!==undefined && data.id!==serial)return;
    if(data.type==='progress'){progress.firstElementChild.style.width=`${data.total?Math.max(8,data.done/data.total*100):95}%`;return}
    progress.hidden=true;$('#search-results').setAttribute('aria-busy','false');
    if(data.type==='error'){status.textContent='Search interrupted';showMessage(data.message+' Your query is kept above.');return}
    if(data.type==='results'){books=data.books;results=data.results;const count=new Set(results.map(r=>r.book)).size;status.textContent=`${data.total.toLocaleString()} ${data.total===1?'passage':'passages'}${data.total?` · ${count} ${count===1?'volume':'volumes'} · Best matches first`:''}`;if(data.total>results.length)status.textContent+=` · Showing the best ${results.length}`;if(!data.total)showMessage(data.message||'No matching passages. Try fewer words, another spelling, or all works and languages.');else renderMore()}
  });worker.addEventListener('error',()=>{progress.hidden=true;status.textContent='Search unavailable';$('#search-results').setAttribute('aria-busy','false');showMessage('Please reload and try again. Your books remain available from the collection.');});}
  readState();worker?.postMessage({type:'init'});
  $('#search-form').addEventListener('submit',e=>{e.preventDefault();run(true)});
  query.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>run(false),400)});
  work.addEventListener('change',()=>run(true));language.addEventListener('change',()=>run(true));
  $('#load-more').addEventListener('click',renderMore);document.querySelectorAll('[data-query]').forEach(button=>button.addEventListener('click',()=>{query.value=button.dataset.query;run(true)}));
  window.addEventListener('popstate',()=>{readState();run()});
})();
