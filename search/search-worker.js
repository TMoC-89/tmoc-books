/* The Library — search worker. Runs off the main thread.
   Finds matching passages from the term index, then fetches only the passage files needed
   to show excerpts. Text normalisation mirrors tools/search_index.py. */
'use strict';

let manifestPromise = null;
const cache = new Map();
const CACHE_MAX = 160;
let current = 0;

function fetchJson(url) {
  if (cache.has(url)) { const v = cache.get(url); cache.delete(url); cache.set(url, v); return v; }
  const p = fetch(url).then(r => { if (!r.ok) throw new Error('Part of the search index could not be loaded. Please try again.'); return r.json(); });
  p.catch(() => cache.delete(url));
  cache.set(url, p);
  while (cache.size > CACHE_MAX) cache.delete(cache.keys().next().value);
  return p;
}
const manifest = () => (manifestPromise ||= fetchJson('data/manifest.json').then(m => {
  if (m.schema !== 2) throw new Error('The search index is out of date. Please reload the page.');
  m.bucketSet = new Set(m.buckets); m.stopSet = new Set(m.stop); return m;
}));

const normalise = s => s.normalize('NFKD').replace(/\p{M}/gu, '').replace(/\u0640/g, '')
  .replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه').replace(/ؤ/g, 'و').replace(/ئ/g, 'ي').toLowerCase();
const ARABIC = /[\u0600-\u06ff]/;
let prefixes = [];
const stem = w => { if (ARABIC.test(w)) for (const p of prefixes) if (w.startsWith(p) && w.length - p.length >= 3) return w.slice(p.length); return w; };
const terms = text => (normalise(text).match(/[\p{L}\p{N}]+/gu) || []).map(stem);
const hex = t => [...t].map(c => c.codePointAt(0).toString(16));
function bucketFor(m, t) {
  const h = hex(t);
  if (h.length >= 3 && m.bucketSet.has(h.slice(0, 3).join('-'))) return h.slice(0, 3).join('-');
  const k = h.slice(0, 2).join('-');
  return m.bucketSet.has(k) ? k : null;
}
function decode(s) {
  const out = []; let prev = 0;
  for (const part of s.split(',')) { prev += parseInt(part, 36); out.push(prev); }
  return out;
}
function rangeOf(m, id) {
  let lo = 0, hi = m.ranges.length - 1;
  while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (m.ranges[mid][0] <= id) lo = mid; else hi = mid - 1; }
  return m.ranges[lo];
}
function parseQuery(m, q) {
  const phrases = [...q.matchAll(/["“”„]([^"“”„]+)["“”„]/g)].map(x => terms(x[1])).filter(p => p.length > 1);
  const all = [...new Set(terms(q))];
  const indexed = all.filter(t => t.length >= 2 && !m.stopSet.has(t));
  return { phrases, all, indexed };
}

async function candidates(m, spec) {
  const lists = [], expanded = new Set();
  for (const t of spec.indexed) {
    const key = bucketFor(m, t);
    const dict = key ? await fetchJson(`data/terms/${key}.json?v=${m.version}`) : {};
    let forms = Object.keys(dict).filter(k => k === t || (!spec.phrases.length && t.length >= 4 && k.startsWith(t)));
    forms.sort((a, b) => a.length - b.length);
    forms = forms.slice(0, 60);
    forms.forEach(f => expanded.add(f));
    const ids = new Set();
    for (const f of forms) for (const id of decode(dict[f])) ids.add(id);
    lists.push(ids);
  }
  lists.sort((a, b) => a.size - b.size);
  let result = lists.length ? [...lists[0]] : [];
  for (const l of lists.slice(1)) result = result.filter(id => l.has(id));
  result.sort((a, b) => a - b);
  return { ids: result, expanded };
}

async function passage(m, id) {
  const chunk = await fetchJson(`data/passages/${Math.floor(id / m.chunk)}.json?v=${m.version}`);
  const [section, anchor, text] = chunk[id % m.chunk];
  const r = rangeOf(m, id);
  return { id, book: r[2], lang: r[3], section, anchor, text };
}

function matchesPhrases(text, phrases) {
  if (!phrases.length) return true;
  const hay = ' ' + terms(text).join(' ') + ' ';
  return phrases.every(p => hay.includes(' ' + p.join(' ') + ' '));
}

function highlight(text, wanted) {
  const hits = [];
  for (const m of text.matchAll(/[\p{L}\p{N}\p{M}\u0640]+/gu)) {
    const w = stem(normalise(m[0]).replace(/[^\p{L}\p{N}]/gu, ''));
    if (wanted(w)) hits.push([m.index, m.index + m[0].length]);
  }
  return hits;
}
function excerpt(text, hits) {
  const LEN = 320;
  if (text.length <= LEN + 60) return { text, highlights: hits };
  const first = hits[0]?.[0] ?? 0;
  let start = Math.max(0, first - 110);
  if (start > 0) {
    const stop = Math.max(text.lastIndexOf('. ', first), text.lastIndexOf('، ', first), text.lastIndexOf('; ', first));
    if (stop >= start - 60 && stop < first) start = stop + 2;
    else { const sp = text.indexOf(' ', start); if (sp > 0 && sp < first) start = sp + 1; }
  }
  let end = Math.min(text.length, start + LEN);
  if (end < text.length) { const sp = text.lastIndexOf(' ', end); if (sp > first) end = sp; }
  const pre = start > 0 ? '… ' : '', post = end < text.length ? ' …' : '';
  return {
    text: pre + text.slice(start, end) + post,
    highlights: hits.filter(([a, b]) => a >= start && b <= end).map(([a, b]) => [a - start + pre.length, b - start + pre.length]),
  };
}

async function run(msg) {
  const id = msg.id;
  current = id;
  const m = await manifest();
  prefixes = m.arPrefixes || [];
  const spec = parseQuery(m, msg.q);
  const reply = o => { if (current === id) postMessage(Object.assign({ id, type: 'results' }, o)); };
  if (!spec.indexed.length) {
    const tooCommon = spec.all.some(t => m.stopSet.has(t));
    return reply({ total: 0, perBook: {}, items: [], message: tooCommon ? 'Those words are too common to search on their own. Add a more distinctive word, or search for a “quoted phrase” with one.' : 'Type a word with at least two letters.' });
  }
  const { ids: raw, expanded } = await candidates(m, spec);
  if (current !== id) return;
  const inScope = pid => { const r = rangeOf(m, pid); return (msg.book === 'all' || r[2] === Number(msg.book)) && (msg.lang === 'all' || r[3] === msg.lang); };
  let ids = raw.filter(inScope);
  let approximate = false;

  if (spec.phrases.length && ids.length) {
    // Phrases need the text itself: fetch passage files (bounded) and keep true matches.
    const chunks = [...new Set(ids.map(x => Math.floor(x / m.chunk)))];
    const LIMIT = 300;
    if (chunks.length > LIMIT) approximate = true;
    const todo = chunks.slice(0, LIMIT), ok = new Set();
    let next = 0, done = 0;
    const worker = async () => {
      while (next < todo.length && current === id) {
        const c = todo[next++];
        const rows = await fetchJson(`data/passages/${c}.json?v=${m.version}`);
        for (const pid of ids) if (Math.floor(pid / m.chunk) === c && matchesPhrases(rows[pid % m.chunk][2], spec.phrases)) ok.add(pid);
        if (++done % 10 === 0) postMessage({ id, type: 'progress', done, total: todo.length });
      }
    };
    await Promise.all(Array.from({ length: Math.min(6, todo.length) }, worker));
    if (current !== id) return;
    ids = ids.filter(pid => ok.has(pid));
  }

  const perBook = {};
  for (const pid of ids) { const b = rangeOf(m, pid)[2]; perBook[b] = (perBook[b] || 0) + 1; }
  const wanted = w => expanded.has(w) || spec.phrases.some(p => p.includes(w));
  const build = async pid => {
    const p = await passage(m, pid);
    const ex = excerpt(p.text, highlight(p.text, wanted));
    return { id: p.id, book: p.book, lang: p.lang, section: p.section, anchor: p.anchor, text: ex.text, highlights: ex.highlights };
  };

  if (msg.book === 'all') {
    const order = Object.keys(perBook).map(Number).sort((a, b) => perBook[b] - perBook[a] || a - b);
    const groups = [];
    for (const b of order) {
      const first = ids.filter(pid => rangeOf(m, pid)[2] === b).slice(0, 3);
      groups.push({ book: b, count: perBook[b], items: await Promise.all(first.map(build)) });
      if (current !== id) return;
    }
    return reply({ mode: 'overview', total: ids.length, perBook, groups, approximate, books: m.books });
  }
  const offset = msg.offset || 0;
  const items = await Promise.all(ids.slice(offset, offset + 20).map(build));
  reply({ mode: 'list', total: ids.length, perBook, items, offset, approximate, books: m.books });
}

self.onmessage = e => {
  const msg = e.data;
  if (msg.type === 'init') {
    manifest().then(m => postMessage({ type: 'ready', books: m.books, languages: m.languages })).catch(err => postMessage({ type: 'error', message: err.message }));
    return;
  }
  if (msg.type === 'cancel') { current = msg.id; return; }
  run(msg).catch(err => { if (current === msg.id) postMessage({ id: msg.id, type: 'error', message: err.message }); });
};
