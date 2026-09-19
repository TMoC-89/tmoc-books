/* Approximate structural alignment. Original text and exported source stay intact. */
(() => {
  const heading=u=>/^h[1-4]$/.test(u.tag);
  function intervals(units){const body=units.filter(u=>!heading(u)),weights=body.map(u=>Math.max(1,(u.text.match(/\S+/g)||[]).length));const total=weights.reduce((a,b)=>a+b,0)||1;let offset=0;return new Map(body.map((u,i)=>{const start=offset/total;offset+=weights[i];return [u.localIndex,{start,end:offset/total}]}))}
  window.LibraryAlignment={
    prepare(en,source){return {en:intervals(en),source:intervals(source)}},
    render(unit,mapped,context,language){
      if(language!=='ar'||!mapped.length)return {html:mapped.map(u=>u.html).join(''),label:''};
      const e=context.en.get(unit.localIndex);
      return {label:'Approximate source span',html:mapped.map(u=>{
        const s=context.source.get(u.localIndex);let start=0,end=1;
        if(e&&s){const width=s.end-s.start;start=Math.max(0,Math.min(1,(e.start-s.start)/width));end=Math.max(start,Math.min(1,(e.end-s.start)/width));}
        return `<div class="aligned-source-unit" data-alignment-start="${start}" data-alignment-end="${end}">${u.html}</div>`;
      }).join('')};
    }
  };
  function mark(el){
    const start=Number(el.dataset.alignmentStart),end=Number(el.dataset.alignmentEnd);delete el.dataset.alignmentStart;delete el.dataset.alignmentEnd;
    const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT),nodes=[];let text='',node;
    while((node=walker.nextNode())){nodes.push({node,start:text.length});text+=node.data;}
    const words=[...text.matchAll(/\S+/g)];if(!words.length||end<=start)return;
    const first=Math.min(words.length-1,Math.floor(start*words.length)),last=Math.min(words.length-1,Math.max(first,Math.ceil(end*words.length)-1));
    const a=words[first].index,b=words[last].index+words[last][0].length;
    for(const item of nodes){const left=Math.max(0,a-item.start),right=Math.min(item.node.length,b-item.start);if(right<=left)continue;const fragment=document.createDocumentFragment();fragment.append(document.createTextNode(item.node.data.slice(0,left)));const mark=document.createElement('mark');mark.className='source-alignment';mark.textContent=item.node.data.slice(left,right);fragment.append(mark,document.createTextNode(item.node.data.slice(right)));item.node.replaceWith(fragment)}
  }
  function setup(){
    const workspace=document.getElementById('reviewer-workspace');if(!workspace)return;
    const observer='IntersectionObserver' in window?new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){observer.unobserve(entry.target);pending.delete(entry.target);mark(entry.target)}},{rootMargin:'400px'}):null;
    const pending=new Set();
    function add(root){if(!(root instanceof Element))return;const elements=[...(root.matches('[data-alignment-start]')?[root]:[]),...root.querySelectorAll('[data-alignment-start]')];for(const el of elements){if(pending.has(el))continue;pending.add(el);if(observer)observer.observe(el);else mark(el)}}
    add(workspace);
    new MutationObserver(changes=>{for(const el of pending)if(!el.isConnected){observer?.unobserve(el);pending.delete(el)}for(const change of changes)for(const node of change.addedNodes)add(node)}).observe(workspace,{childList:true,subtree:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
})();
