/* The Library — search page controller. The heavy lifting happens in search-worker.js. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const query = $('#query'), work = $('#work-filter'), language = $('#language-filter');
  const list = $('#results-list'), status = $('#result-summary'), title = $('#results-title');
  const progress = $('#search-progress'), message = $('#search-message'), intro = $('#search-intro');
  const more = $('#load-more'), clear = $('#clear-query'), results = $('#search-results');
  const NAMES = { en: 'English', ar: 'Arabic', fr: 'French', de: 'German' };
  let worker = null, serial = 0, books = [], shown = 0, total = 0, timer = 0, facets = null;

  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const icon = name => { const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); s.setAttribute('class', 'i'); s.setAttribute('aria-hidden', 'true'); const u = document.createElementNS('http://www.w3.org/2000/svg', 'use'); u.setAttribute('href', '#i-' + name); s.append(u); return s; };

  function urlState(push) {
    const u = new URL(location.href);
    u.search = '';
    const q = query.value.trim();
    if (q) u.searchParams.set('q', q);
    if (work.value !== 'all') u.searchParams.set('work', work.value);
    if (language.value !== 'all') u.searchParams.set('lang', language.value);
    if (u.href !== location.href) history[push ? 'pushState' : 'replaceState']({}, '', u);
  }
  function readState() {
    const p = new URLSearchParams(location.search);
    query.value = (p.get('q') || '').slice(0, 120);
    work.dataset.want = p.get('work') || 'all';
    work.value = work.dataset.want;
    if (!work.value) work.value = 'all';
    language.value = p.get('lang') || 'all';
    if (!language.value) language.value = 'all';
    clear.hidden = !query.value;
  }
  function say(text) { message.textContent = text; message.hidden = false; }

  function highlighted(text, ranges) {
    const f = document.createDocumentFragment();
    let pos = 0;
    for (const [a, b] of ranges) { f.append(text.slice(pos, a)); f.append(el('mark', '', text.slice(a, b))); pos = b; }
    f.append(text.slice(pos));
    return f;
  }
  function resultItem(r, n) {
    const b = books[r.book] || { title: '', author: '', url: '../' };
    const li = el('li', 'result');
    li.append(el('span', 'result-no', String(n).padStart(2, '0')));
    const meta = el('div', 'result-meta');
    meta.append(el('strong', '', b.title), el('span', '', b.author), el('span', 'result-lang', NAMES[r.lang] || r.lang));
    const quote = el('blockquote');
    quote.lang = r.lang; quote.dir = r.lang === 'ar' ? 'rtl' : 'ltr';
    quote.append(highlighted(r.text, r.highlights));
    const foot = el('div', 'result-foot');
    const section = el('span', 'result-section', r.section);
    section.dir = 'auto';
    const url = new URL(b.url, location.href);
    url.searchParams.set('lang', r.lang);
    url.searchParams.set('q', query.value.trim());
    url.searchParams.set('passage', r.anchor);
    url.hash = r.anchor;
    const source = r.lang === 'de';
    const a = el('a', '', source ? 'View in Reviewer Mode' : 'Read in context');
    a.href = url.href;
    a.setAttribute('aria-label', `${source ? 'View in Reviewer Mode' : 'Read in context'}: ${b.title}, ${r.section}`);
    a.append(icon('arrow-up-right'));
    foot.append(section, a);
    li.append(meta, quote, foot);
    return li;
  }
  function renderFacets(perBook) {
    facets?.remove();
    const ids = Object.keys(perBook).map(Number).sort((x, y) => perBook[y] - perBook[x]);
    if (work.value === 'all' && ids.length < 2) { facets = null; return; }
    facets = el('div', 'facets');
    facets.setAttribute('role', 'group');
    facets.setAttribute('aria-label', 'Narrow to one work');
    const chip = (label, value, count) => {
      const b = el('button', '', label);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(work.value === String(value)));
      if (count != null) b.append(el('span', '', String(count)));
      b.addEventListener('click', () => { work.value = String(value); run(true); });
      return b;
    };
    facets.append(chip('All works', 'all'));
    for (const id of ids) facets.append(chip(books[id]?.title || '', id, perBook[id]));
    list.before(facets);
  }
  function summary(d) {
    const n = d.total, count = Object.keys(d.perBook).length;
    if (!n) return '';
    const approx = d.approximate ? 'At least ' : '';
    return `${approx}${n.toLocaleString()} ${n === 1 ? 'passage' : 'passages'}` + (work.value === 'all' ? ` in ${count} ${count === 1 ? 'work' : 'works'}` : '');
  }

  function run(push) {
    clearTimeout(timer);
    urlState(push);
    const q = query.value.trim();
    clear.hidden = !q;
    serial++;
    worker?.postMessage({ type: 'cancel', id: serial });
    list.replaceChildren(); facets?.remove(); facets = null;
    message.hidden = true; more.hidden = true; progress.hidden = true;
    shown = 0; total = 0;
    intro.hidden = !!q;
    results.setAttribute('aria-busy', 'false');
    if (!q) { title.textContent = 'A place to begin'; document.title = 'Search — The Library'; status.textContent = ''; return; }
    title.textContent = /^["“].*["”]$/.test(q) ? `Passages for ${q}` : `Passages for “${q}”`;
    document.title = `${q} — Search — The Library`;
    if (!worker) { say('Search could not start. Please reload the page.'); return; }
    status.textContent = 'Searching…';
    progress.hidden = false;
    progress.firstElementChild.style.width = '12%';
    results.setAttribute('aria-busy', 'true');
    worker.postMessage({ type: 'search', id: serial, q, book: work.value, lang: language.value, offset: 0 });
  }
  function loadMore() {
    more.disabled = true;
    worker.postMessage({ type: 'search', id: serial, q: query.value.trim(), book: work.value, lang: language.value, offset: shown });
  }

  function onResults(d) {
    progress.hidden = true;
    results.setAttribute('aria-busy', 'false');
    more.disabled = false;
    if (d.books) books = d.books;
    total = d.total;
    status.textContent = summary(d);
    if (!d.total) { say(d.message || 'No passages found. Try fewer words, another spelling, or all works and languages.'); return; }
    if (d.mode === 'overview') {
      renderFacets(d.perBook);
      let n = 0;
      for (const g of d.groups) {
        const head = el('li', 'result-group');
        const h = el('h3', 'group-title', books[g.book]?.title || '');
        const btn = el('button', 'group-more', g.count > g.items.length ? `All ${g.count} in this work` : `${g.count} ${g.count === 1 ? 'passage' : 'passages'}`);
        btn.type = 'button';
        btn.disabled = g.count <= g.items.length;
        btn.addEventListener('click', () => { work.value = String(g.book); run(true); results.focus({ preventScroll: false }); });
        head.append(h, btn);
        list.append(head);
        for (const r of g.items) list.append(resultItem(r, ++n));
      }
      shown = n;
      more.hidden = true;
      return;
    }
    if (d.offset === 0) renderFacets(d.perBook);
    const frag = document.createDocumentFragment();
    d.items.forEach((r, i) => frag.append(resultItem(r, d.offset + i + 1)));
    list.append(frag);
    shown = d.offset + d.items.length;
    more.hidden = shown >= total;
    more.textContent = `More passages (${(total - shown).toLocaleString()} more)`;
  }

  try {
    worker = new Worker(window.SEARCH_WORKER || 'search-worker.js');
    worker.addEventListener('message', e => {
      const d = e.data;
      if (d.type === 'ready') {
        books = d.books;
        for (const b of books) { const o = el('option', '', b.title); o.value = String(b.id); work.append(o); }
        work.value = work.dataset.want || 'all';
        if (!work.value) work.value = 'all';
        if (query.value.trim()) run(false);
        return;
      }
      if (d.id !== undefined && d.id !== serial) return;
      if (d.type === 'progress') { progress.firstElementChild.style.width = `${Math.max(12, (d.done / Math.max(1, d.total)) * 100)}%`; return; }
      if (d.type === 'error') { progress.hidden = true; results.setAttribute('aria-busy', 'false'); status.textContent = 'Search interrupted'; say(d.message + ' Your search is kept above.'); return; }
      if (d.type === 'results') onResults(d);
    });
    worker.addEventListener('error', () => { progress.hidden = true; status.textContent = 'Search unavailable'; say('Search is unavailable right now. Please reload the page — every book can still be read from the collection.'); });
  } catch {
    say('This browser could not start search. Please open the site over http(s) in a current browser.');
  }

  readState();
  worker?.postMessage({ type: 'init' });
  $('#search-form').addEventListener('submit', e => { e.preventDefault(); run(true); query.blur(); });
  query.addEventListener('input', () => { clear.hidden = !query.value; clearTimeout(timer); timer = setTimeout(() => run(false), 450); });
  clear.addEventListener('click', () => { query.value = ''; run(true); query.focus(); });
  work.addEventListener('change', () => run(true));
  language.addEventListener('change', () => run(true));
  more.addEventListener('click', loadMore);
  document.querySelectorAll('[data-query]').forEach(b => b.addEventListener('click', () => { query.value = b.dataset.query; run(true); }));
  addEventListener('popstate', () => { readState(); run(false); });
  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement !== query && !/input|select|textarea/i.test(document.activeElement?.tagName || '')) { e.preventDefault(); query.focus(); query.select(); }
  });
  if (!query.value && matchMedia('(hover: hover) and (pointer: fine)').matches) query.focus();
})();
