(() => {
  const menu = document.getElementById('menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  if (!menu || !sidebar) return;
  const mobile = matchMedia('(max-width: 900px)');
  sidebar.id ||= 'reader-navigation';
  menu.setAttribute('aria-controls', sidebar.id);
  const isOpen = () => document.body.classList.contains('nav-open') || document.body.classList.contains('menu-open');
  const sync = () => {
    sidebar.inert = mobile.matches && !isOpen();
    menu.setAttribute('aria-label', isOpen() ? 'Close contents' : 'Open contents');
    menu.setAttribute('aria-expanded', String(isOpen()));
  };
  new MutationObserver(sync).observe(document.body, {attributes:true, attributeFilter:['class']});
  mobile.addEventListener('change', sync);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && mobile.matches && isOpen()) {
      menu.click();
      menu.focus();
    }
  });
  // Keep keyboard focus out of the closed drawer after following a chapter link.
  sidebar.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (!link || !mobile.matches) return;
    const target = document.getElementById(decodeURIComponent(link.hash.slice(1)));
    if (target) {
      target.setAttribute('tabindex', '-1');
      target.focus({preventScroll:true});
    }
  });
  const download = document.getElementById('download-link');
  if (download && !download.hasAttribute('aria-label')) download.setAttribute('aria-label','Download Markdown');
  sync();
})();
