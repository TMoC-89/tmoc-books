(() => {
  const root = document.documentElement;
  const themeButton = document.getElementById('theme-toggle');
  const applyTheme = () => {
    const dark = root.dataset.theme === 'dark';
    themeButton.textContent = dark ? '☀︎' : '☾';
    themeButton.title = dark ? 'Use light mode' : 'Use dark mode';
    themeButton.setAttribute('aria-label', themeButton.title);
  };
  applyTheme();
  themeButton.hidden = false;
  themeButton.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('minimal-library-theme', root.dataset.theme); } catch {}
    applyTheme();
  });
  const systemTheme = matchMedia('(prefers-color-scheme: dark)');
  systemTheme.addEventListener('change', e => {
    try { if (localStorage.getItem('minimal-library-theme')) return; } catch {}
    root.dataset.theme = e.matches ? 'dark' : 'light';
    applyTheme();
  });

  const buttons=[...document.querySelectorAll('[data-filter]')];
  const shelves=[...document.querySelectorAll('.shelf')];
  buttons.forEach(button=>button.addEventListener('click',()=>{
    const filter=button.dataset.filter;let count=0;
    shelves.forEach(shelf=>{shelf.hidden=filter!=='all'&&shelf.dataset.language!==filter;if(!shelf.hidden)count+=shelf.querySelectorAll('.book-card').length});
    buttons.forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
    document.getElementById('collection').classList.toggle('is-filtered',filter!=='all');
    const status=document.getElementById('result-count');status.classList.toggle('sr-only',filter==='all');status.textContent=`${count} ${count===1?'work':'works'}${filter==='all'?'':` translated from ${button.textContent.trim().replace(/\s+\d+$/,'')}`}`;
  }));
  document.querySelector('.browse-tools').hidden=false;
})();
