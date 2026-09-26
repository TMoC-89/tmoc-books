/* The Library — book reader.
   One script for every book. Book-specific facts come from the JSON in #book-data,
   which tools/build.py writes into each page. No dependencies. */
(() => {
  'use strict';

  const root = document.documentElement;
  const body = document.body;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const book = JSON.parse($('#book-data').textContent);
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} },
    del(k) { try { localStorage.removeItem(k); } catch {} },
    json(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch { return null; } },
  };
  const KEYS = {
    theme: 'minimal-library-theme',
    size: 'minimal-library-reader-size',
    lang: book.langKey,
    progress: `library-progress:${book.slug}`,
    recent: 'library-recent',
    sidebar: 'library-sidebar-collapsed',
  };
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const mobile = matchMedia('(max-width: 960px)');
  const bar = () => $('.topbar').getBoundingClientRect().height;
  const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  let lang = book.languages.includes(root.dataset.lang) ? root.dataset.lang : book.languages[0];

  /* ---------------------------------------------------------------- theme & text size */
  const themeButtons = $$('[data-theme-choice]');
  function applyTheme(choice) {
    const system = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    root.dataset.theme = choice === 'auto' ? system : choice;
    themeButtons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.themeChoice === choice)));
    const meta = $('meta[name="theme-color"]');
    if (meta) meta.content = root.dataset.theme === 'dark' ? '#171916' : '#f5f2eb';
  }
  let themeChoice = store.get(KEYS.theme) || 'auto';
  applyTheme(themeChoice);
  themeButtons.forEach(b => b.addEventListener('click', () => {
    themeChoice = b.dataset.themeChoice;
    if (themeChoice === 'auto') store.del(KEYS.theme); else store.set(KEYS.theme, themeChoice);
    applyTheme(themeChoice);
  }));
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (themeChoice === 'auto') applyTheme('auto'); });

  // Lazy rendering of long books is only switched on where it is measured to help (Chromium; see reader.css).
  const lazy = root.classList.contains('lazy-render');
  const SIZE_MIN = 15, SIZE_MAX = 28, SIZE_DEFAULT = 19;
  const sizeRange = $('#size-range'), sizeValue = $('#size-value');
  let size = Number(store.get(KEYS.size)) || SIZE_DEFAULT;
  function applySize(next, save) {
    size = Math.max(SIZE_MIN, Math.min(SIZE_MAX, Math.round(next)));
    root.style.setProperty('--reader-size', size + 'px');
    if (sizeRange) sizeRange.value = String(size);
    if (sizeValue) sizeValue.textContent = String(size);
    if (save) { if (size === SIZE_DEFAULT) store.del(KEYS.size); else store.set(KEYS.size, size); }
  }
  /* Changing the size re-flows the whole book, so at most one change is applied per frame
     (the slider fires many events) and the reading position is restored once, after the last. */
  let sizeAnchor = null, sizeTarget = size, sizeFrame = 0, sizeIdle = 0;
  function resizeKeepingPlace(next) {
    if (!sizeAnchor) sizeAnchor = readingAnchor() || { none: true };
    sizeTarget = Math.max(SIZE_MIN, Math.min(SIZE_MAX, Math.round(next)));
    if (!sizeFrame) sizeFrame = requestAnimationFrame(() => { sizeFrame = 0; applySize(sizeTarget, true); });
    clearTimeout(sizeIdle);
    sizeIdle = setTimeout(() => {
      const anchor = sizeAnchor;
      sizeAnchor = null;
      if (lazy) { $$('.book-section[data-rendered]').forEach(x => x.removeAttribute('data-rendered')); estimateSections(); }
      if (anchor && !anchor.none) restoreAnchor(anchor);
    }, 160);
  }
  applySize(size, false);
  $('#size-down')?.addEventListener('click', () => resizeKeepingPlace(sizeTarget - 1));
  $('#size-up')?.addEventListener('click', () => resizeKeepingPlace(sizeTarget + 1));
  // While the slider is being dragged only the number changes; the text re-flows when the thumb rests.
  let dragIdle = 0;
  sizeRange?.addEventListener('input', () => {
    if (sizeValue) sizeValue.textContent = sizeRange.value;
    clearTimeout(dragIdle);
    dragIdle = setTimeout(() => resizeKeepingPlace(Number(sizeRange.value)), lazy ? 60 : 250);
  });
  sizeRange?.addEventListener('change', () => { clearTimeout(dragIdle); resizeKeepingPlace(Number(sizeRange.value)); });

  /* Settings popover */
  const settingsBtn = $('#settings-toggle'), settings = $('#settings');
  function closeSettings(focus) {
    if (!settings || settings.hidden) return;
    settings.hidden = true; settingsBtn.setAttribute('aria-expanded', 'false');
    if (focus) settingsBtn.focus();
  }
  settingsBtn?.addEventListener('click', e => {
    e.stopPropagation();
    const open = settings.hidden;
    settings.hidden = !open; settingsBtn.setAttribute('aria-expanded', String(open));
    if (open) (settings.querySelector('[aria-pressed="true"]') || settings.querySelector('button'))?.focus();
  });
  document.addEventListener('click', e => { if (settings && !settings.hidden && !settings.contains(e.target) && !settingsBtn.contains(e.target)) closeSettings(false); });

  /* ---------------------------------------------------------------- sections */
  const views = new Map($$('.language-view').filter(v => book.languages.includes(v.dataset.lang)).map(v => [v.dataset.lang, v]));
  const sectionCache = new Map();
  function sections(l = lang) {
    if (!sectionCache.has(l)) {
      const view = views.get(l);
      const list = view ? $$(':scope > .book-section', view).map((el, i) => ({ el, key: el.dataset.key || el.id, title: el.dataset.title || '', index: i })) : [];
      let total = 0;
      for (const s of list) { s.chars = Math.max(1, Number(s.el.dataset.chars) || s.el.textContent.length); s.before = total; total += s.chars; }
      list.total = total || 1;
      sectionCache.set(l, list);
    }
    return sectionCache.get(l);
  }

  /* Estimated heights let the browser skip laying out chapters that are far off screen
     (content-visibility in reader.css). They self-correct from chapters already rendered. */
  function estimateSections() {
    if (!lazy) return;
    const secs = sections();
    if (!secs.length) return;
    const measured = secs.filter(s => s.el.dataset.rendered === '1').map(s => s.el.offsetHeight / s.chars).filter(x => x > 0);
    let perChar;
    if (measured.length) perChar = measured.sort((a, b) => a - b)[measured.length >> 1];
    else {
      const width = Math.max(260, Math.min(secs[0].el.clientWidth || 700, 760));
      const glyph = size * (lang === 'ar' ? .42 : .47);
      perChar = (size * (lang === 'ar' ? 2.05 : 1.78)) / (width / glyph);
    }
    for (const s of secs) if (s.el.dataset.rendered !== '1') s.el.style.setProperty('--est', Math.round(s.chars * perChar + 160) + 'px');
  }
  if (lazy) document.addEventListener('contentvisibilityautostatechange', e => {
    if (!e.skipped && e.target.classList?.contains('book-section')) e.target.dataset.rendered = '1';
  }, { capture: true });

  /* ---------------------------------------------------------------- table of contents */
  let navIndex = null;
  function buildNavIndex() {
    const idx = new Map();
    for (const toc of $$('.toc')) {
      const bySection = new Map(), sectionLinks = new Map();
      for (const a of $$('a[href^="#"]', toc)) {
        const target = document.getElementById(decodeURIComponent(a.hash.slice(1)));
        const sec = target?.closest('.book-section');
        if (!sec) continue;
        if (target === sec || target === sec.firstElementChild) { if (!sectionLinks.has(sec)) sectionLinks.set(sec, a); continue; }
        if (!bySection.has(sec)) bySection.set(sec, new Map());
        bySection.get(sec).set(target, a); // a later (deeper) link to the same target wins
      }
      idx.set(toc.dataset.l, { bySection, sectionLinks });
    }
    return idx;
  }
  function setExpanded(li, open) {
    const btn = li.querySelector(':scope > .toc-row > .toc-toggle');
    const list = li.querySelector(':scope > ol');
    if (!btn || !list) return;
    btn.setAttribute('aria-expanded', String(open));
    list.hidden = !open;
  }
  $$('.toc-toggle').forEach(btn => btn.addEventListener('click', () => setExpanded(btn.closest('li'), btn.getAttribute('aria-expanded') !== 'true')));

  const sidebar = $('.sidebar');
  let activeLink = null;
  function markActive(a) {
    if (a === activeLink) return;
    for (const x of $$('.toc a.active')) { x.classList.remove('active'); x.removeAttribute('aria-current'); }
    for (const x of $$('.toc li.has-active')) x.classList.remove('has-active');
    activeLink = a;
    if (!a) return;
    a.classList.add('active');
    a.setAttribute('aria-current', 'location');
    let li = a.closest('li')?.parentElement?.closest('li');
    while (li) { li.classList.add('has-active'); setExpanded(li, true); li = li.parentElement?.closest('li'); }
    if (sidebar && (!mobile.matches || body.classList.contains('nav-open'))) {
      const r = a.getBoundingClientRect(), s = sidebar.getBoundingClientRect();
      if (r.top < s.top + 60 || r.bottom > s.bottom - 40) sidebar.scrollTop += r.top - s.top - s.height * .35;
    }
  }

  /* ---------------------------------------------------------------- scroll spy & progress */
  const current = $('.bar-title .current');
  const progressBar = $('#progress');
  let spyFrame = 0, lastSaved = 0;

  const marker = () => bar() + Math.min(160, innerHeight * .2);
  function locate() {
    const secs = sections();
    const m = marker();
    if (!secs.length || secs[0].el.getBoundingClientRect().top > m) return null;
    let lo = 0, hi = secs.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (secs[mid].el.getBoundingClientRect().top <= m) lo = mid; else hi = mid - 1;
    }
    const s = secs[lo];
    const r = s.el.getBoundingClientRect();
    return { s, frac: Math.max(0, Math.min(1, (m - r.top) / Math.max(1, r.height))) };
  }
  function spy() {
    spyFrame = 0;
    if (body.classList.contains('review-mode')) return;
    const hit = locate();
    const secs = sections();
    if (!hit) {
      markActive(null);
      setCurrent('');
      if (progressBar) progressBar.style.transform = 'scaleX(0)';
      return;
    }
    navIndex ||= buildNavIndex();
    const nav = navIndex.get(lang) || navIndex.get('en');
    let link = nav?.sectionLinks.get(hit.s.el) || null, sub = null;
    const inner = nav?.bySection.get(hit.s.el);
    if (inner) {
      const m = marker();
      for (const [target, a] of inner) { if (target.getBoundingClientRect().top <= m) sub = a; else break; }
    }
    if (!link && !sub) for (let i = hit.s.index - 1; i >= 0 && !link; i--) link = nav?.sectionLinks.get(secs[i].el) || null;
    markActive(sub || link);
    const secTitle = hit.s.title || link?.textContent.trim() || '';
    const subTitle = sub ? (sub.dataset.title || sub.textContent.trim()) : '';
    setCurrent(subTitle && subTitle !== secTitle ? `${secTitle} · ${subTitle}` : secTitle);
    const doc = document.documentElement;
    const atEnd = doc.scrollTop + innerHeight >= doc.scrollHeight - 4;
    const p = atEnd ? 1 : (hit.s.before + hit.frac * hit.s.chars) / secs.total;
    if (progressBar) progressBar.style.transform = `scaleX(${p.toFixed(4)})`;
    const now = Date.now();
    if (now - lastSaved > 1500) { lastSaved = now; saveProgress(hit, p); }
  }
  function setCurrent(text) {
    if (!current || current.textContent === text) return;
    current.textContent = text;
    current.title = text;
    current.dir = lang === 'ar' && text ? 'rtl' : 'ltr';
  }
  const scheduleSpy = () => { if (!spyFrame) spyFrame = requestAnimationFrame(spy); };
  addEventListener('scroll', scheduleSpy, { passive: true });
  addEventListener('resize', scheduleSpy);

  /* ---------------------------------------------------------------- reading position */
  function readingAnchor() {
    const hit = locate();
    if (!hit) return null;
    // The last element with an id whose top is above the marker (ids follow reading order).
    const m = marker();
    const els = hit.s.el.querySelectorAll('[id]');
    let lo = 0, hi = els.length - 1, el = null;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      const top = els[mid].getBoundingClientRect().top;
      if (top <= m + 2 && els[mid].offsetParent !== null) { el = els[mid]; lo = mid + 1; } else hi = mid - 1;
    }
    const offset = el ? el.getBoundingClientRect().top - m : 0;
    return { key: hit.s.key, frac: hit.frac, id: el?.id || null, offset, lang };
  }
  /* Blocks far from the viewport render lazily, so their real heights only settle after they
     are on screen. Place an element, then keep correcting for a few frames until it holds still. */
  let settleId = 0;
  function settle(el, desiredTop) {
    const id = ++settleId;
    let frames = 0, still = 0;
    el.scrollIntoView({ block: 'start' });
    const step = () => {
      if (id !== settleId) return;
      const delta = el.getBoundingClientRect().top - desiredTop();
      if (Math.abs(delta) > 1) { scrollTo({ top: scrollY + delta, behavior: 'auto' }); still = 0; } else still++;
      if (++frames < 30 && still < 3) requestAnimationFrame(step); else scheduleSpy();
    };
    requestAnimationFrame(step);
  }
  addEventListener('wheel', () => settleId++, { passive: true });
  addEventListener('touchstart', () => settleId++, { passive: true });
  addEventListener('keydown', e => { if (/^(Arrow|Page|Home|End| )/.test(e.key)) settleId++; });

  function restoreAnchor(a) {
    const target = a.id && document.getElementById(a.id);
    if (target && views.get(lang)?.contains(target)) { settle(target, () => marker() + (a.offset || 0)); return; }
    const s = sections().find(x => x.key === a.key);
    if (!s) return;
    // Bring the chapter on screen so it renders, then place the reader at the same fraction of it.
    scrollTo({ top: scrollY + s.el.getBoundingClientRect().top - bar(), behavior: 'auto' });
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const r = s.el.getBoundingClientRect();
      const y = r.top + a.frac * r.height;
      const probe = [...s.el.children].find(c => c.getBoundingClientRect().bottom > y) || s.el;
      const off = probe.getBoundingClientRect().top - y;
      settle(probe, () => marker() + off);
    }));
  }
  function saveProgress(hit, pct) {
    if (body.classList.contains('review-mode')) return;
    const anchor = readingAnchor();
    if (!anchor) return;
    const record = { ...anchor, title: hit.s.title, pct: Math.round(pct * 1000) / 10, t: Date.now() };
    store.set(KEYS.progress, JSON.stringify(record));
    const recent = (store.json(KEYS.recent) || []).filter(r => r && r.slug !== book.slug);
    recent.unshift({ slug: book.slug, path: book.path, title: book.shortTitle, section: hit.s.title, lang, pct: record.pct, t: record.t });
    store.set(KEYS.recent, JSON.stringify(recent.slice(0, 8)));
  }

  /* Cover: offer to continue where the reader left off. */
  function setupResume() {
    const btn = $('#resume-btn');
    const saved = store.json(KEYS.progress);
    if (!btn || !saved || !saved.key || (saved.pct || 0) < .2) return;
    btn.hidden = false;
    $('.where', btn).textContent = saved.title || '';
    btn.title = `${saved.title || ''} · ${Math.round(saved.pct)}%`;
    const resume = () => {
      if (saved.lang && saved.lang !== lang && book.languages.includes(saved.lang)) applyLang(saved.lang, false);
      restoreAnchor(saved);
    };
    btn.addEventListener('click', e => { e.preventDefault(); resume(); });
    if (location.hash === '#resume') {
      try { history.replaceState(null, '', location.pathname + location.search); } catch {}
      requestAnimationFrame(resume);
    }
  }

  /* ---------------------------------------------------------------- language switch */
  const langBtn = $('#lang-toggle');
  function applyLang(next, keepPlace) {
    if (!book.languages.includes(next)) return;
    const place = keepPlace ? readingAnchor() : null;
    const y = scrollY;
    lang = next;
    root.dataset.lang = next;
    root.lang = next;
    store.set(KEYS.lang, next);
    if (langBtn) {
      const other = book.languages.find(l => l !== next);
      const label = other === 'ar' ? 'Read the Arabic original' : 'Read the English translation';
      langBtn.setAttribute('aria-label', label);
      langBtn.title = label;
    }
    if (current) current.dataset.fallback = book.titles[next] || book.titles.en;
    document.title = book.documentTitles[next] || book.documentTitles.en;
    activeLink = null;
    navIndex = null;
    estimateSections();
    if (place) restoreAnchor({ key: place.key, frac: place.frac });
    else if (keepPlace) scrollTo({ top: y, behavior: 'auto' });
    scheduleSpy();
  }
  langBtn?.addEventListener('click', () => {
    closeSettings(false); closeNav();
    applyLang(book.languages.find(l => l !== lang) || 'en', true);
    showToast(lang === 'ar' ? 'النص العربي الأصلي' : 'English translation');
  });

  /* ---------------------------------------------------------------- sidebar */
  const menuBtn = $('#menu-toggle'), backdrop = $('.sidebar-backdrop');
  function sidebarOpen() { return mobile.matches ? body.classList.contains('nav-open') : !root.classList.contains('sidebar-collapsed'); }
  function syncSidebarA11y() {
    const open = sidebarOpen();
    menuBtn?.setAttribute('aria-expanded', String(open));
    menuBtn?.setAttribute('aria-label', open ? 'Hide contents' : 'Show contents');
    if (menuBtn) menuBtn.title = menuBtn.getAttribute('aria-label');
    if (sidebar) sidebar.inert = !open;
  }
  function openNav() {
    if (mobile.matches) {
      body.classList.add('nav-open');
      requestAnimationFrame(() => {
        const a = sidebar.querySelector('.toc a.active');
        if (a) sidebar.scrollTop = a.offsetTop - sidebar.clientHeight * .3;
        (a || sidebar.querySelector('a'))?.focus({ preventScroll: true });
      });
    } else { root.classList.remove('sidebar-collapsed'); store.del(KEYS.sidebar); }
    syncSidebarA11y();
  }
  function closeNav(returnFocus) {
    if (mobile.matches && body.classList.contains('nav-open')) {
      body.classList.remove('nav-open');
      if (returnFocus) menuBtn?.focus();
    }
    syncSidebarA11y();
  }
  menuBtn?.addEventListener('click', () => {
    if (sidebarOpen()) {
      if (mobile.matches) closeNav(true);
      else { root.classList.add('sidebar-collapsed'); store.set(KEYS.sidebar, '1'); syncSidebarA11y(); }
    } else openNav();
  });
  backdrop?.addEventListener('click', () => closeNav(true));
  mobile.addEventListener('change', () => { body.classList.remove('nav-open'); syncSidebarA11y(); });
  syncSidebarA11y();

  /* In-page links: smooth for short hops, instant for long jumps; switch language if needed. */
  function goTo(id, opts = {}) {
    const target = document.getElementById(id);
    if (!target) return false;
    const view = target.closest('.language-view');
    if (view && view.dataset.lang !== lang && book.languages.includes(view.dataset.lang)) applyLang(view.dataset.lang, false);
    const top = () => scrollY + target.getBoundingClientRect().top - bar() - 16;
    const far = Math.abs(top() - scrollY) > innerHeight * 3;
    if (far || reducedMotion.matches || opts.instant) settle(target, () => bar() + 16);
    else scrollTo({ top: top(), behavior: 'smooth' });
    if (opts.focus !== false) {
      if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
      target.focus({ preventScroll: true });
    }
    if (opts.history !== false) try { history.pushState(null, '', '#' + id); } catch {}
    return true;
  }
  document.addEventListener('click', e => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const a = e.target.closest('a[href^="#"]');
    if (!a || a.closest('.note-pop')) return;
    const id = decodeURIComponent(a.hash.slice(1));
    if (!id) return;
    if (isNoteRef(a) && openNote(a)) { e.preventDefault(); return; }
    if (id === 'top') {
      e.preventDefault(); closeNav();
      scrollTo({ top: 0, behavior: reducedMotion.matches ? 'auto' : 'smooth' });
      try { history.pushState(null, '', location.pathname + location.search); } catch {}
      return;
    }
    if (goTo(id)) { e.preventDefault(); closeNote(); if (a.closest('.sidebar')) closeNav(); }
  });
  addEventListener('popstate', () => {
    const id = decodeURIComponent(location.hash.slice(1));
    if (id) goTo(id, { history: false, focus: false });
  });

  /* ---------------------------------------------------------------- note previews */
  let notePop = null, noteRef = null;
  function isNoteRef(a) {
    if (a.matches('.backref, .footnote-back, [role="doc-backlink"]')) return false;
    return !!a.closest('sup, .note-ref, .footnote-ref') || a.getAttribute('role') === 'doc-noteref';
  }
  function openNote(a) {
    const target = document.getElementById(decodeURIComponent(a.hash.slice(1)));
    if (!target) return false;
    if (noteRef === a && notePop) { closeNote(); return true; }
    closeNote();
    const holder = target.closest('li, .gloss-footnote, .footnote') || target;
    const clone = holder.cloneNode(true);
    clone.querySelectorAll('.backref, .footnote-back, [role="doc-backlink"], .note-number, .gloss-footnote-number').forEach(n => n.remove());
    clone.querySelectorAll('[id]').forEach(n => n.removeAttribute('id'));
    const rtl = !!target.closest('.language-view[data-lang="ar"]');
    const n = a.textContent.trim();
    notePop = document.createElement('div');
    notePop.className = 'note-pop';
    notePop.setAttribute('role', 'dialog');
    notePop.setAttribute('aria-label', rtl ? `حاشية ${n}` : `Note ${n}`);
    notePop.dir = rtl ? 'rtl' : 'ltr';
    notePop.innerHTML = `<div class="note-pop-head"><span>${rtl ? 'حاشية' : 'Note'} ${escapeHtml(n)}</span><a class="note-jump" href="#${escapeHtml(holder.id || target.id)}">${rtl ? 'انتقل إلى الحواشي' : 'Go to note'}</a></div><div class="note-pop-body">${clone.innerHTML}</div>`;
    body.append(notePop);
    noteRef = a;
    a.setAttribute('aria-expanded', 'true');
    positionNote();
    notePop.tabIndex = -1;
    notePop.focus({ preventScroll: true });
    return true;
  }
  function positionNote() {
    if (!notePop || !noteRef || matchMedia('(max-width: 640px)').matches) return;
    const r = noteRef.getBoundingClientRect(), w = notePop.offsetWidth, h = notePop.offsetHeight;
    const left = Math.min(innerWidth - w - 12, Math.max(12, r.left + r.width / 2 - w / 2));
    let top = r.bottom + 10;
    if (top + h > innerHeight - 12 && r.top - h - 10 > bar()) top = r.top - h - 10;
    notePop.style.left = left + scrollX + 'px';
    notePop.style.top = top + scrollY + 'px';
  }
  function closeNote() {
    if (!notePop) return null;
    notePop.remove(); notePop = null;
    const ref = noteRef; noteRef = null;
    ref?.removeAttribute('aria-expanded');
    return ref;
  }
  document.addEventListener('click', e => {
    if (!notePop) return;
    if (notePop.contains(e.target)) {
      const jump = e.target.closest('.note-jump');
      if (jump) { e.preventDefault(); const id = decodeURIComponent(jump.hash.slice(1)); closeNote(); goTo(id); }
      return;
    }
    if (!e.target.closest('sup, .note-ref, .footnote-ref')) closeNote();
  }, true);
  addEventListener('resize', positionNote);

  /* ---------------------------------------------------------------- facsimile lightbox */
  document.addEventListener('click', e => {
    const b = e.target.closest('.facsimile-zoom');
    if (!b) return;
    e.preventDefault();
    const caption = b.dataset.facsimileCaption || 'Facsimile';
    const box = document.createElement('div');
    box.className = 'lightbox';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    box.setAttribute('aria-label', caption);
    box.innerHTML = '<figure><button class="icon-btn" type="button" aria-label="Close"><svg class="i" aria-hidden="true"><use href="#i-close"/></svg></button><img alt=""><figcaption></figcaption></figure>';
    $('img', box).src = b.dataset.facsimileSrc || $('img', b).src;
    $('img', box).alt = caption;
    $('figcaption', box).textContent = caption;
    const close = () => { box.remove(); body.style.overflow = ''; document.removeEventListener('keydown', onKey, true); b.focus(); };
    const onKey = ev => { if (ev.key === 'Escape') { ev.stopPropagation(); close(); } };
    box.addEventListener('click', ev => { if (ev.target === box || ev.target.closest('.icon-btn')) close(); });
    document.addEventListener('keydown', onKey, true);
    body.append(box);
    body.style.overflow = 'hidden';
    $('.icon-btn', box).focus();
  });

  /* ---------------------------------------------------------------- keyboard */
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    if (notePop) { closeNote()?.focus(); return; }
    if (settings && !settings.hidden) { closeSettings(true); return; }
    if (body.classList.contains('nav-open')) closeNav(true);
  });

  /* ---------------------------------------------------------------- toast */
  let toastTimer = 0;
  function showToast(text) {
    let t = $('.toast');
    if (!t) { t = document.createElement('div'); t.className = 'toast'; t.setAttribute('role', 'status'); body.append(t); }
    t.textContent = text;
    t.dir = /[\u0600-\u06ff]/.test(text) ? 'rtl' : 'ltr';
    requestAnimationFrame(() => t.classList.add('show'));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 1600);
  }

  /* ---------------------------------------------------------------- reviewer (loaded on demand) */
  let reviewerLoading = null;
  function loadReviewer() {
    if (window.LibraryReviewer) return Promise.resolve(window.LibraryReviewer);
    reviewerLoading ||= new Promise((resolve, reject) => {
      const css = document.createElement('link');
      css.rel = 'stylesheet'; css.href = book.assets.reviewerCss;
      document.head.append(css);
      const s = document.createElement('script');
      s.src = book.assets.reviewerJs;
      s.onload = () => resolve(window.LibraryReviewer);
      s.onerror = () => { reviewerLoading = null; reject(new Error('Reviewer Mode could not load. Please try again.')); };
      document.head.append(s);
    });
    return reviewerLoading;
  }
  const readerApi = {
    get lang() { return lang; },
    setLang: l => applyLang(l, false),
    setCurrent,
    closeNav,
    toast: showToast,
    saveAnchor: () => readingAnchor(),
    restore: a => restoreAnchor(a),
    afterExit() { navIndex = null; activeLink = null; scheduleSpy(); },
  };
  async function enterReview(opts) {
    const btn = $('#review-enter');
    btn?.setAttribute('aria-busy', 'true');
    try {
      const R = await loadReviewer();
      await R.enter(Object.assign({ book, api: readerApi }, opts || {}));
    } catch (err) { showToast(err.message || 'Reviewer Mode could not load.'); }
    finally { btn?.removeAttribute('aria-busy'); }
  }
  $('#review-enter')?.addEventListener('click', () => enterReview());

  /* ---------------------------------------------------------------- arriving from search */
  // Same normalisation as the search index (tools/search_index.py), so highlights match results.
  const AR_PREFIXES = ['وبال', 'وكال', 'وفال', 'ولل', 'فبال', 'فال', 'وال', 'بال', 'كال', 'لل', 'ال', 'و', 'ف', 'ب', 'ل', 'ك'];
  const stem = w => { if (/[\u0600-\u06ff]/.test(w)) for (const p of AR_PREFIXES) if (w.startsWith(p) && w.length - p.length >= 3) return w.slice(p.length); return w; };
  const fold = s => stem(s.normalize('NFKD').replace(/\p{M}/gu, '').replace(/\u0640/g, '').replace(/[أإآٱ]/g, 'ا')
    .replace(/ى/g, 'ي').replace(/ة/g, 'ه').replace(/ؤ/g, 'و').replace(/ئ/g, 'ي').toLowerCase());
  function highlightTerms(el, query) {
    const terms = [...new Set((query || '').match(/[\p{L}\p{N}\p{M}]{2,}/gu) || [])].map(fold).filter(t => t.length >= 2);
    if (!terms.length) return;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      const text = node.data;
      const hits = [...text.matchAll(/[\p{L}\p{N}\p{M}\u0640]+/gu)].filter(m => {
        const w = fold(m[0]);
        return terms.some(t => w === t || (t.length >= 4 && w.startsWith(t)));
      });
      if (!hits.length) continue;
      const frag = document.createDocumentFragment();
      let pos = 0;
      for (const m of hits) {
        frag.append(text.slice(pos, m.index));
        const mark = document.createElement('mark');
        mark.className = 'search-hit';
        mark.textContent = m[0];
        frag.append(mark);
        pos = m.index + m[0].length;
      }
      frag.append(text.slice(pos));
      node.replaceWith(frag);
    }
  }
  function fromSearch() {
    const params = new URLSearchParams(location.search);
    const passage = params.get('passage'), l = params.get('lang'), q = params.get('q');
    if (!passage) return false;
    const back = $('#search-return');
    if (back) {
      const url = new URL(book.root + 'search/', location.href);
      if (q) url.searchParams.set('q', q);
      back.href = url.href;
      back.hidden = false;
    }
    if (l && !book.languages.includes(l)) { enterReview({ revealSource: passage }); return true; }
    if (l && l !== lang) applyLang(l, false);
    const target = document.getElementById(passage);
    if (!target) return false;
    requestAnimationFrame(() => {
      goTo(passage, { instant: true, history: false });
      target.classList.add('search-destination');
      if (q) highlightTerms(target, q);
    });
    return true;
  }

  /* ---------------------------------------------------------------- start */
  applyLang(lang, false);
  setupResume();
  const params = new URLSearchParams(location.search);
  if (params.get('review') === '1') enterReview();
  else if (!fromSearch()) {
    const id = decodeURIComponent(location.hash.slice(1));
    if (id && id !== 'top' && id !== 'resume' && document.getElementById(id)) requestAnimationFrame(() => goTo(id, { instant: true, history: false, focus: false }));
  }
  scheduleSpy();
})();
