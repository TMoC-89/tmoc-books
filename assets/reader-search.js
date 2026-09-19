/* Search links choose the right language and land on the original passage. */
(() => {
  const params=new URLSearchParams(location.search),anchor=params.get('passage'),language=params.get('lang');
  if(!anchor)return;
  const root=document.documentElement;
  const side=document.querySelector('.sidebar');
  if(side){const link=document.createElement('a');link.className='search-return';const url=new URL(document.querySelector('.library-search-link').href);if(params.get('q'))url.searchParams.set('q',params.get('q'));link.href=url.href;link.textContent='← Back to search results';side.prepend(link)}
  function reveal(target){if(!target)return;target.classList.add('search-destination');target.setAttribute('tabindex','-1');const top=document.querySelector('.topbar')?.getBoundingClientRect().height||62;window.scrollTo({top:Math.max(0,target.getBoundingClientRect().top+scrollY-top-24),behavior:'instant'});target.focus({preventScroll:true})}
  if(language==='de'){
    const workspace=document.getElementById('reviewer-workspace');if(!workspace)return;
    const locate=()=>{const target=[...workspace.querySelectorAll('[data-source-origin-ids]')].find(el=>el.dataset.sourceOriginIds.split(' ').includes(anchor));if(target){requestAnimationFrame(()=>reveal(target));return true}return false};
    if(!locate()){const observer=new MutationObserver(()=>{if(locate())observer.disconnect()});observer.observe(workspace,{childList:true,subtree:true});}
  }else{
    if((language==='ar'||language==='en') && root.dataset.lang && root.dataset.lang!==language)document.getElementById('lang-toggle')?.click();
    requestAnimationFrame(()=>requestAnimationFrame(()=>reveal(document.getElementById(anchor))));
  }
})();
