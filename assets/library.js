/* The Library — collection pages: theme switch, shelf filters and "continue reading". */
(() => {
  'use strict';
  const root = document.documentElement;
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} },
    json(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch { return null; } },
  };
  const THEME = 'minimal-library-theme';

  /* Theme: the header button flips light/dark and remembers the choice. */
  const toggle = $('#theme-toggle');
  function paintToggle() {
    if (!toggle) return;
    const dark = root.dataset.theme === 'dark';
    toggle.innerHTML = `<svg class="i" aria-hidden="true"><use href="#i-${dark ? 'sun' : 'moon'}"/></svg>`;
    const label = dark ? 'Switch to light theme' : 'Switch to dark theme';
    toggle.setAttribute('aria-label', label);
    toggle.title = label;
  }
  paintToggle();
  toggle?.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    store.set(THEME, root.dataset.theme);
    paintToggle();
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    const saved = store.get(THEME);
    if (saved === 'light' || saved === 'dark') return;
    root.dataset.theme = e.matches ? 'dark' : 'light';
    paintToggle();
  });

  /* Shelf filters on the collection page. */
  const filters = $('.filters');
  if (filters) {
    const buttons = $$('[data-filter]', filters), shelves = $$('.shelf'), wrap = $('.shelves'), status = $('#result-count');
    filters.hidden = false;
    buttons.forEach(b => b.addEventListener('click', () => {
      const f = b.dataset.filter;
      let n = 0;
      shelves.forEach(s => { s.hidden = f !== 'all' && s.dataset.shelf !== f; if (!s.hidden) n += $$('.book-card', s).length; });
      buttons.forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      wrap.classList.toggle('filtered', f !== 'all');
      status.textContent = f === 'all' ? `Showing all ${n} works` : `${n} ${n === 1 ? 'work' : 'works'} translated from ${b.firstChild.textContent.trim()}`;
    }));
  }

  /* Reading progress saved by the reader: a "continue" strip and a meter on each card. */
  const recent = (store.json('library-recent') || []).filter(r => r && r.slug && r.path && typeof r.pct === 'number');
  const base = new URL((document.querySelector('.wordmark') || document.querySelector('a[href]'))?.href || location.href, location.href);
  const bySlug = new Map(recent.map(r => [r.slug, r]));
  const escapeHtml = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  for (const card of $$('[data-progress-key]')) {
    const hits = card.dataset.progressKey.split(',').map(k => bySlug.get(k)).filter(Boolean).sort((a, b) => b.t - a.t);
    const r = hits[0];
    if (!r || r.pct < 1) continue;
    const box = $('.card-progress', card);
    box.hidden = false;
    box.innerHTML = `<span>${r.pct >= 99 ? 'Finished' : `${Math.round(r.pct)}% read`}${r.section ? ' · ' + escapeHtml(r.section) : ''}</span><span class="meter"><i style="width:${Math.min(100, r.pct)}%"></i></span>`;
  }
  const strip = $('#continue');
  const list = strip && $('.continue-list', strip);
  const unfinished = recent.filter(r => r.pct >= 1 && r.pct < 99).slice(0, 3);
  if (list && unfinished.length) {
    list.innerHTML = unfinished.map(r => {
      const href = new URL(r.path.replace(/\/?$/, '/') + '#resume', base).href;
      const rtl = /[\u0600-\u06ff]/.test(r.section || '');
      return `<li><a class="continue-card" href="${escapeHtml(href)}"><strong>${escapeHtml(r.title)}</strong><span class="where"${rtl ? ' dir="rtl"' : ''}>${escapeHtml(r.section || '')}</span><span class="meter" aria-label="${Math.round(r.pct)}% read"><i style="width:${r.pct}%"></i></span></a></li>`;
    }).join('');
    strip.hidden = false;
  }
})();
