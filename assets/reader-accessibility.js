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

(() => {
  const controls = document.querySelector('.topbar .controls');
  const down = document.getElementById('font-down');
  const up = document.getElementById('font-up');
  if (!controls || !down || !up || document.querySelector('.font-size-mobile')) return;

  const min = 16;
  const max = 26;
  const getSize = () => {
    const stored = Number(localStorage.getItem('minimal-library-reader-size'));
    if (Number.isFinite(stored) && stored >= min && stored <= max) return stored;
    const css = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--reader-size'));
    return Number.isFinite(css) ? Math.max(min, Math.min(max, Math.round(css))) : 19;
  };

  const wrap = document.createElement('div');
  wrap.className = 'font-size-mobile';
  const popoverId = 'mobile-font-size-popover';
  wrap.innerHTML = `<button class="icon-btn font-size-mobile-toggle" type="button" aria-label="Font size" title="Font size" aria-expanded="false" aria-controls="${popoverId}">A</button><div class="font-size-popover" id="${popoverId}"><button class="font-size-label" type="button" aria-label="Decrease font size">A−</button><span class="font-size-range"><input type="range" min="${min}" max="${max}" step="1" aria-label="Font size"><span class="font-size-default-notch" aria-hidden="true"></span></span><button class="font-size-label" type="button" aria-label="Increase font size">A+</button></div>`;
  controls.insertBefore(wrap, controls.firstChild);

  const toggle = wrap.querySelector('.font-size-mobile-toggle');
  const minus = wrap.querySelector('.font-size-label:first-of-type');
  const plus = wrap.querySelector('.font-size-label:last-of-type');
  const slider = wrap.querySelector('input[type="range"]');
  const sync = () => { slider.value = String(getSize()); };
  const close = () => {
    wrap.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
  };

  sync();
  // Keep slider/button interaction inside the popover so the outside-click
  // handler only closes it when the user clicks or taps elsewhere.
  wrap.addEventListener('click', event => event.stopPropagation());
  toggle.addEventListener('click', event => {
    event.stopPropagation();
    const open = !wrap.classList.contains('open');
    wrap.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
    if (open) {
      sync();
      slider.focus();
    }
  });
  minus.addEventListener('click', () => down.click());
  plus.addEventListener('click', () => up.click());
  slider.addEventListener('input', () => {
    const target = Number(slider.value);
    let current = getSize();
    while (current < target) { up.click(); current += 1; }
    while (current > target) { down.click(); current -= 1; }
  });
  down.addEventListener('click', event => {
    event.stopPropagation();
    requestAnimationFrame(sync);
  });
  up.addEventListener('click', event => {
    event.stopPropagation();
    requestAnimationFrame(sync);
  });
  document.addEventListener('click', event => {
    if (!wrap.contains(event.target)) close();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && wrap.classList.contains('open')) {
      close();
      toggle.focus();
    }
  });
  matchMedia('(min-width: 601px)').addEventListener('change', event => {
    if (event.matches) close();
  });
})();
