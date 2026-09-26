/* The Library — Reviewer Mode.
   Loaded on demand by reader.js. Reviewers read the published English beside the source
   text, mark passages, propose corrections and export a JSON review file. Drafts stay in
   this browser (localStorage). Block ids and draft keys are stable across site rebuilds:
   `${slug}:${sectionKey}:${nnnn}` and `tmoc-review-draft:${slug}:${version}`. */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const safeStore = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); return true; } catch { return false; } },
  };
  const root = document.documentElement, body = document.body;
  const LANG_NAMES = { ar: 'Arabic original', de: 'German original', fr: 'French original' };

  /* ---------- approximate structural alignment (formerly review-alignment.js) ---------- */
  const isHeading = u => /^h[1-4]$/.test(u.tag);
  function intervalMap(units) {
    const bodyUnits = units.filter(u => !isHeading(u)), weights = bodyUnits.map(u => Math.max(1, (u.text.match(/\S+/g) || []).length));
    const total = weights.reduce((a, b) => a + b, 0) || 1;
    let offset = 0;
    return new Map(bodyUnits.map((u, i) => { const start = offset / total; offset += weights[i]; return [u.localIndex, { start, end: offset / total }]; }));
  }
  const Alignment = {
    prepare(en, source) { return { en: intervalMap(en), source: intervalMap(source) }; },
    render(unit, mapped, context, language) {
      if (language !== 'ar' || !mapped.length) return { html: mapped.map(u => u.html).join(''), label: '' };
      const e = context.en.get(unit.localIndex);
      return {
        label: 'Approximate source span',
        html: mapped.map(u => {
          const s = context.source.get(u.localIndex);
          let start = 0, end = 1;
          if (e && s) { const width = s.end - s.start; start = Math.max(0, Math.min(1, (e.start - s.start) / width)); end = Math.max(start, Math.min(1, (e.end - s.start) / width)); }
          return `<div class="aligned-source-unit" data-alignment-start="${start}" data-alignment-end="${end}">${u.html}</div>`;
        }).join(''),
      };
    },
  };
  function markSpan(el) {
    const start = Number(el.dataset.alignmentStart), end = Number(el.dataset.alignmentEnd);
    delete el.dataset.alignmentStart; delete el.dataset.alignmentEnd;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), nodes = [];
    let text = '', node;
    while ((node = walker.nextNode())) { nodes.push({ node, start: text.length }); text += node.data; }
    const words = [...text.matchAll(/\S+/g)];
    if (!words.length || end <= start) return;
    const first = Math.min(words.length - 1, Math.floor(start * words.length));
    const last = Math.min(words.length - 1, Math.max(first, Math.ceil(end * words.length) - 1));
    const a = words[first].index, b = words[last].index + words[last][0].length;
    for (const item of nodes) {
      const left = Math.max(0, a - item.start), right = Math.min(item.node.length, b - item.start);
      if (right <= left) continue;
      const frag = document.createDocumentFragment();
      frag.append(document.createTextNode(item.node.data.slice(0, left)));
      const mark = document.createElement('mark');
      mark.className = 'source-alignment';
      mark.textContent = item.node.data.slice(left, right);
      frag.append(mark, document.createTextNode(item.node.data.slice(right)));
      item.node.replaceWith(frag);
    }
  }
  const spanObserver = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
    for (const entry of entries) if (entry.isIntersecting) { spanObserver.unobserve(entry.target); markSpan(entry.target); }
  }, { rootMargin: '400px' }) : null;
  function observeSpans(scope) { for (const el of $$('[data-alignment-start]', scope)) { if (spanObserver) spanObserver.observe(el); else markSpan(el); } }

  /* ---------- helpers ---------- */
  function escapeHtml(s = '') { return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  function slugify(s = '') { return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 70) || 'section'; }
  function hashText(s = '') { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0).toString(16).padStart(8, '0'); }
  function cleanClone(el) {
    const c = el.cloneNode(true);
    $$('.note-ref,.footnote,.backref,.chapter-pager', c).forEach(n => n.remove());
    $$('[id]', c).forEach(n => n.removeAttribute('id'));
    $$('a', c).forEach(a => { a.setAttribute('target', '_blank'); a.setAttribute('rel', 'noopener'); });
    $$('mark.search-hit', c).forEach(m => m.replaceWith(m.textContent));
    c.classList?.remove('search-destination');
    c.removeAttribute?.('tabindex');
    return c;
  }
  function cleanText(el) {
    const c = cleanClone(el);
    return (c.innerText || c.textContent || '').replace(/ /g, ' ').replace(/[ \t]+\n/g, '\n').replace(/\n[ \t]+/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  }
  const cleanHtml = el => cleanClone(el).outerHTML;
  function unitElements(sec) {
    const out = [];
    for (const el of [...sec.children]) {
      const t = el.tagName?.toLowerCase();
      if (['h1', 'h2', 'h3', 'h4', 'p', 'blockquote', 'table'].includes(t) || (t === 'div' && el.classList.contains('gloss-footnote'))) out.push(el);
      else if (['ul', 'ol'].includes(t)) { const lis = [...el.children].filter(x => x.tagName?.toLowerCase() === 'li'); if (lis.length) out.push(...lis); else out.push(el); }
    }
    return out.filter(el => !el.classList?.contains('chapter-pager'));
  }
  function reviewUnits(sec) {
    const els = unitElements(sec);
    const dateCount = els.filter(el => el.dataset?.journalDate).length;
    const make = (members, i) => ({ el: members[0], lastEl: members[members.length - 1], members, localIndex: i, tag: members.length > 1 ? 'div' : members[0].tagName.toLowerCase(), text: members.map(cleanText).filter(Boolean).join('\n\n'), html: members.map(cleanHtml).join(''), originId: members.find(x => x.id)?.id || '' });
    if (dateCount < 3) return els.map((el, i) => make([el], i));
    const groups = []; let current = null;
    for (const el of els) { if (el.dataset?.journalDate) { current = [el]; groups.push(current); } else if (current) current.push(el); else groups.push([el]); }
    return groups.map(make);
  }
  const wordWeight = text => Math.max(1, (text.match(/\S+/g) || []).length);
  function sourceIntervals(units) {
    const total = units.reduce((n, u) => n + wordWeight(u.text), 0) || 1; let acc = 0;
    return units.map(u => { const w = wordWeight(u.text), o = { ...u, start: acc / total, end: (acc + w) / total, mid: (acc + w / 2) / total }; acc += w; return o; });
  }
  function buildSourceMap(enUnits, srcUnits) {
    const result = new Map();
    if (!srcUnits.length) return result;
    const withDates = units => { let current = ''; return units.map(u => { const own = u.el?.dataset?.journalDate || ''; if (own) current = own; return { ...u, date: current, isDate: !!own }; }); };
    const E = withDates(enUnits), S = withDates(srcUnits);
    const sourceKeyMap = new Map(S.filter(u => u.el?.dataset?.sourceKey).map(u => [u.el.dataset.sourceKey, u]));
    for (const e of E) { const k = e.el?.dataset?.sourceKey; if (k && sourceKeyMap.has(k)) result.set(e.localIndex, [sourceKeyMap.get(k)]); }
    const group = list => { const m = new Map(); for (const u of list) { if (!u.date) continue; if (!m.has(u.date)) m.set(u.date, []); m.get(u.date).push(u); } return m; };
    const sByDate = group(S), eByDate = group(E);
    const mapProportional = (eg, sg) => {
      const eb = eg.filter(u => !u.isDate), sb = sg.filter(u => !u.isDate);
      if (!eb.length || !sb.length) return;
      const ei = sourceIntervals(eb), si = sourceIntervals(sb);
      for (const e of ei) {
        let hits = si.filter(x => Math.min(e.end, x.end) - Math.max(e.start, x.start) > 0.00001);
        if (!hits.length) hits = [si.reduce((a, b) => Math.abs(b.mid - e.mid) < Math.abs(a.mid - e.mid) ? b : a, si[0])];
        result.set(e.localIndex, hits);
      }
    };
    for (const [date, eg] of eByDate) {
      const sg = sByDate.get(date); if (!sg) continue;
      const ed = eg.filter(u => u.isDate), sd = sg.filter(u => u.isDate);
      if (ed.length && sd.length) ed.forEach((e, i) => result.set(e.localIndex, [sd[Math.min(i, sd.length - 1)]]));
      mapProportional(eg, sg);
    }
    const srcHeadings = S.filter(isHeading), enHeadCount = {};
    const enBody = E.filter(u => !isHeading(u)), srcBody = S.filter(u => !isHeading(u));
    const eInt = sourceIntervals(enBody), sInt = sourceIntervals(srcBody), bodyLookup = new Map(eInt.map(x => [x.localIndex, x]));
    for (const e of E) {
      if (result.has(e.localIndex)) continue;
      if (isHeading(e)) {
        const k = e.tag; enHeadCount[k] = (enHeadCount[k] || 0) + 1;
        const candidates = srcHeadings.filter(x => x.tag === k);
        const hit = candidates[enHeadCount[k] - 1] || srcHeadings[Math.min(srcHeadings.length - 1, enHeadCount[k] - 1)];
        if (hit) result.set(e.localIndex, [hit]);
        continue;
      }
      const ei = bodyLookup.get(e.localIndex);
      if (!ei || !sInt.length) continue;
      let hits = sInt.filter(x => Math.min(ei.end, x.end) - Math.max(ei.start, x.start) > 0.00001);
      if (!hits.length) hits = [sInt.reduce((a, b) => Math.abs(b.mid - ei.mid) < Math.abs(a.mid - ei.mid) ? b : a, sInt[0])];
      result.set(e.localIndex, hits);
    }
    return result;
  }
  function tokenize(s) { return s.match(/\s+|[^\s]+/g) || []; }
  function wordDiff(oldText, newText) {
    if (oldText === newText) return [{ type: 'same', text: newText }];
    const a = tokenize(oldText), b = tokenize(newText);
    if (a.length * b.length > 180000) {
      let p = 0; while (p < a.length && p < b.length && a[p] === b[p]) p++;
      let ae = a.length - 1, be = b.length - 1; while (ae >= p && be >= p && a[ae] === b[be]) { ae--; be--; }
      const out = [];
      if (p) out.push({ type: 'same', text: a.slice(0, p).join('') });
      if (ae >= p) out.push({ type: 'del', text: a.slice(p, ae + 1).join('') });
      if (be >= p) out.push({ type: 'add', text: b.slice(p, be + 1).join('') });
      if (ae < a.length - 1) out.push({ type: 'same', text: a.slice(ae + 1).join('') });
      return out;
    }
    const dp = Array.from({ length: a.length + 1 }, () => new Uint16Array(b.length + 1));
    for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--) dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    let i = 0, j = 0; const out = [];
    const push = (type, text) => { if (!text) return; const last = out[out.length - 1]; if (last && last.type === type) last.text += text; else out.push({ type, text }); };
    while (i < a.length && j < b.length) { if (a[i] === b[j]) { push('same', a[i]); i++; j++; } else if (dp[i + 1][j] >= dp[i][j + 1]) push('del', a[i++]); else push('add', b[j++]); }
    while (i < a.length) push('del', a[i++]);
    while (j < b.length) push('add', b[j++]);
    return out;
  }

  /* ---------- state ---------- */
  let CFG = null, api = null, workspace, saveState, modal, draftKey;
  let mode = false, stage = 'select', dataBuilt = false, blockList = [], blockMap = new Map(), sectionList = [], navCleanup = null, saveTimer = null;
  let previous = null;
  let draft = { selected: [], edits: {}, notes: {}, createdAt: null, updatedAt: null };
  const countEl = $('#review-count'), actionBtn = $('#review-action'), exitBtn = $('#review-exit'), sidebar = $('.sidebar');
  const srcLang = () => CFG.sourceLang || CFG.sourceLanguage || '';
  const srcDir = () => CFG.sourceDir || (CFG.sourceLanguage === 'ar' ? 'rtl' : 'ltr');
  const srcName = () => CFG.sourceLabel || LANG_NAMES[CFG.sourceLanguage] || 'Original text';

  function ensureChrome() {
    workspace = $('#reviewer-workspace');
    if (!workspace) { workspace = document.createElement('div'); workspace.id = 'reviewer-workspace'; workspace.className = 'reviewer-workspace'; $('.main').append(workspace); }
    workspace.setAttribute('aria-live', 'polite');
    saveState = $('#review-save-state');
    if (!saveState) { saveState = document.createElement('div'); saveState.id = 'review-save-state'; saveState.className = 'review-save-state'; saveState.setAttribute('role', 'status'); body.append(saveState); }
    modal = $('#review-submit-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'review-submit-modal'; modal.className = 'review-submit-modal'; modal.hidden = true;
      modal.innerHTML = `<div class="review-submit-sheet" role="dialog" aria-modal="true" aria-labelledby="review-submit-title"><h2 id="review-submit-title">Submit review</h2><p>This creates a self-contained JSON file with the published text, your proposed wording, source context, notes and stable passage identifiers. Send the file to the editors.</p><div class="review-summary-grid"><div class="review-summary-stat"><strong id="review-summary-selected">0</strong><span>Selected</span></div><div class="review-summary-stat"><strong id="review-summary-changed">0</strong><span>Edited</span></div><div class="review-summary-stat"><strong id="review-summary-notes">0</strong><span>Notes</span></div></div><div class="review-modal-actions"><button class="review-mini-btn" type="button" data-review-cancel-submit>Keep editing</button><button class="review-mini-btn review-download-btn" type="button" id="review-download-final">Download review file</button></div></div>`;
      body.append(modal);
      modal.addEventListener('click', e => {
        if (e.target === modal || e.target.closest('[data-review-cancel-submit]')) hideSubmit();
        if (e.target.closest('#review-download-final')) { downloadJson('submission'); hideSubmit(); }
      });
    }
  }

  async function loadSourceStore() {
    const s = CFG.store;
    if (!s || $(`.language-view[data-lang="${s.lang}"]`)) return;
    const res = await fetch(s.file);
    if (!res.ok) throw new Error('The source text could not be loaded. Please try again.');
    const holder = document.createElement('div');
    holder.id = 'review-source-store';
    holder.hidden = true;
    holder.innerHTML = await res.text();
    $('.main').append(holder);
  }

  function getEnSections() { const v = $('.language-view[data-lang="en"]'); return v ? $$(':scope > .book-section', v) : []; }
  function getSourceSection(key, index) {
    if (!CFG.sourceLanguage) return null;
    const view = $(`.language-view[data-lang="${CFG.sourceLanguage}"]`);
    if (!view) return null;
    return $(`.book-section[data-key="${CSS.escape(key)}"]`, view) || $$(':scope > .book-section', view)[index] || null;
  }
  function buildData() {
    if (dataBuilt) return;
    dataBuilt = true;
    let globalIndex = 0;
    sectionList = getEnSections().map((sec, si) => {
      const key = sec.dataset.key || sec.id || `section-${si + 1}`;
      const title = sec.dataset.title || sec.querySelector('h1,h2,h3')?.textContent?.trim() || `Section ${si + 1}`;
      const srcSec = getSourceSection(key, si);
      const enUnits = reviewUnits(sec), srcUnits = srcSec ? reviewUnits(srcSec) : [];
      const srcMap = buildSourceMap(enUnits, srcUnits), alignment = Alignment.prepare(enUnits, srcUnits);
      const textUnits = enUnits.filter(u => u.text);
      const facsimiles = $$('figure.facsimile', sec).map(f => ({ html: f.outerHTML, afterBlock: textUnits.filter(u => !!(u.lastEl.compareDocumentPosition(f) & Node.DOCUMENT_POSITION_FOLLOWING)).length }));
      const blocks = textUnits.map((u, bi) => {
        globalIndex++;
        const mapped = srcMap.get(u.localIndex) || [];
        const aligned = Alignment.render(u, mapped, alignment, CFG.sourceLanguage);
        const id = `${CFG.slug}:${key}:${String(bi + 1).padStart(4, '0')}`;
        const b = {
          id, sectionKey: key, sectionTitle: title, sectionIndex: si, blockIndex: bi, globalIndex, tag: u.tag,
          publishedText: u.text, publishedHtml: u.html, publishedFingerprint: hashText(u.text),
          sourceText: mapped.map(x => x.text).filter(Boolean).join('\n\n'), sourceHtml: aligned.html, sourceAlignment: aligned.label,
          sourceOriginIds: [...new Set(mapped.flatMap(x => (x.members || [x.el]).flatMap(el => [el.id, ...[...el.querySelectorAll('[id]')].map(n => n.id)])).filter(Boolean))],
          originId: u.originId,
        };
        blockMap.set(id, b);
        return b;
      });
      return { key, title, index: si, originId: sec.id || '', blocks, sourceAvailable: !!srcSec, facsimiles };
    });
    blockList = sectionList.flatMap(s => s.blocks);
    loadDraft();
  }
  function loadDraft() {
    const raw = safeStore.get(draftKey);
    if (raw) { try { const d = JSON.parse(raw); draft = { selected: Array.isArray(d.selected) ? d.selected : [], edits: d.edits || {}, notes: d.notes || {}, createdAt: d.createdAt || null, updatedAt: d.updatedAt || null }; } catch {} }
    draft.selected = draft.selected.filter(id => blockMap.has(id));
    if (!draft.createdAt) draft.createdAt = new Date().toISOString();
  }
  function saveDraft(show = true) {
    draft.updatedAt = new Date().toISOString();
    const ok = safeStore.set(draftKey, JSON.stringify(draft));
    if (show) {
      saveState.textContent = ok ? 'Saved on this device' : 'Could not save — export a draft to keep your work';
      saveState.classList.add('show');
      clearTimeout(saveTimer);
      saveTimer = setTimeout(() => saveState.classList.remove('show'), ok ? 1100 : 4000);
    }
  }
  const selectedSet = () => new Set(draft.selected);
  function updateCount() {
    const n = draft.selected.length;
    countEl.querySelector('.review-count-number').textContent = String(n);
    countEl.setAttribute('aria-label', `${n} passage${n === 1 ? '' : 's'} selected`);
    const label = actionBtn.querySelector('.review-action-label');
    if (stage === 'edit') { label.textContent = 'Back to selection'; actionBtn.disabled = false; }
    else { label.textContent = 'Review selected'; actionBtn.disabled = n === 0; }
  }
  let anchorCache = null;
  function sectionAnchors() {
    if (anchorCache) return anchorCache;
    const map = new Map();
    for (const sec of sectionList) {
      map.set(sec.key, `review-section-${slugify(sec.key)}`);
      if (sec.originId) map.set(sec.originId, `review-section-${slugify(sec.key)}`);
      for (const b of sec.blocks) if (b.originId) map.set(b.originId, `review-block-${b.globalIndex}`);
    }
    return (anchorCache = map);
  }
  function renderBlockHtml(b, sourceAvailable, sel) {
    const selected = sel.has(b.id), source = sourceAvailable && CFG.sourceLanguage;
    return `<article class="review-card${selected ? ' selected' : ''}${source ? '' : ' single'}" id="review-block-${b.globalIndex}" data-review-id="${escapeHtml(b.id)}" data-section-key="${escapeHtml(b.sectionKey)}"${b.originId ? ` data-origin-id="${escapeHtml(b.originId)}"` : ''}><div class="review-panel"><button class="review-flag" type="button" aria-pressed="${selected}" aria-label="${selected ? 'Remove' : 'Mark'} this passage for review" title="${selected ? 'Remove from review' : 'Mark for review'}">${selected ? '✓' : '!'}</button><div class="review-text">${b.publishedHtml}</div><span class="review-block-meta">Passage ${b.blockIndex + 1}</span></div>${source ? `<div class="review-source-panel" data-source-origin-ids="${escapeHtml(b.sourceOriginIds.join(' '))}" dir="${srcDir()}" lang="${srcLang()}">${b.sourceAlignment ? `<span class="source-alignment-label" dir="ltr" lang="en">${b.sourceAlignment}</span>` : ''}<div class="review-text">${b.sourceHtml || '<span class="review-empty-source">Source context is not available for this passage.</span>'}</div></div>` : ''}</article>`;
  }
  function renderSelection(preserveY = false) {
    buildData();
    stage = 'select';
    const sel = selectedSet();
    const shading = CFG.sourceLanguage === 'ar' ? ' Shading in the Arabic marks an approximate span based on passage lengths and structure; it is not a verified word-for-word alignment.' : '';
    const parts = [`<div class="review-intro"><p class="review-kicker">Reviewer Mode</p><h1>${escapeHtml(CFG.title)}</h1><p>Read the published English beside the ${escapeHtml(srcName().toLowerCase())} and mark only the passages that need attention. Your selections and edits are saved on this device. ${CFG.sourceLanguage ? `Where paragraph boundaries differ, the source column keeps the surrounding context.${shading}` : 'The original-language text is not currently available for this edition.'}</p><div class="review-intro-actions"><button class="review-mini-btn primary" type="button" data-review-open-edit ${draft.selected.length ? '' : 'disabled'}>Review selected passages</button><button class="review-mini-btn" type="button" data-review-export-draft>Export draft</button></div></div>`];
    for (const s of sectionList) {
      let cards = (s.facsimiles || []).filter(f => f.afterBlock === 0).map(f => `<div class="review-facsimile">${f.html}</div>`).join('');
      s.blocks.forEach((b, i) => {
        cards += renderBlockHtml(b, s.sourceAvailable, sel);
        cards += (s.facsimiles || []).filter(f => f.afterBlock === i + 1).map(f => `<div class="review-facsimile">${f.html}</div>`).join('');
      });
      parts.push(`<section class="review-section${s.sourceAvailable ? '' : ' source-unavailable'}" id="review-section-${slugify(s.key)}" data-section-key="${escapeHtml(s.key)}"><div class="review-section-title"><h2>${escapeHtml(s.title)}</h2><span>${s.blocks.length} passage${s.blocks.length === 1 ? '' : 's'}</span></div><div class="review-column-labels"><span>Published English</span><span>${escapeHtml(srcName())}</span></div>${cards}</section>`);
    }
    workspace.innerHTML = parts.join('');
    workspace.dataset.stage = 'select';
    observeSpans(workspace);
    setupReviewNav();
    updateCount();
    if (!preserveY) scrollTo({ top: 0, behavior: 'auto' });
  }
  const editValue = b => Object.prototype.hasOwnProperty.call(draft.edits, b.id) ? draft.edits[b.id] : b.publishedText;
  const noteValue = b => draft.notes[b.id] || '';
  const isChanged = b => editValue(b) !== b.publishedText;
  function renderEditCard(b) {
    const changed = isChanged(b), note = noteValue(b), source = !!(CFG.sourceLanguage && b.sourceText);
    return `<article class="review-edit-card${changed ? ' changed' : ''}${source ? '' : ' no-source'}" id="review-edit-${b.globalIndex}" data-review-id="${escapeHtml(b.id)}" data-section-key="${escapeHtml(b.sectionKey)}"><div class="review-edit-card-head"><div class="review-breadcrumb">${escapeHtml(b.sectionTitle)} · passage ${b.blockIndex + 1}</div><span class="review-status">${changed ? 'Edited' : 'Unchanged'}</span></div><div class="review-edit-grid"><div class="review-editor"><label for="edit-${b.globalIndex}">Current / proposed English</label><textarea class="review-textarea" id="edit-${b.globalIndex}" spellcheck="true">${escapeHtml(editValue(b))}</textarea><div class="review-card-tools"><button type="button" class="review-reset">Reset to published translation</button><button type="button" class="review-remove">Remove from review</button></div><details class="review-note"${note ? ' open' : ''}><summary>${note ? 'Reviewer note' : 'Add note'}</summary><textarea class="review-note-input" aria-label="Reviewer note" placeholder="Optional context for this correction">${escapeHtml(note)}</textarea></details><div class="review-diff"><span class="review-diff-label">Change preview</span><div class="review-diff-text"></div></div></div>${source ? `<div class="review-source-edit" lang="${srcLang()}" dir="${srcDir()}"><span class="source-label">${escapeHtml(srcName())}</span>${b.sourceAlignment ? `<span class="source-alignment-label" dir="ltr" lang="en">${b.sourceAlignment}</span>` : ''}<div class="review-text">${b.sourceHtml}</div></div>` : ''}</div></article>`;
  }
  function renderEdit() {
    buildData();
    stage = 'edit';
    const selected = draft.selected.map(id => blockMap.get(id)).filter(Boolean).sort((a, b) => a.globalIndex - b.globalIndex);
    workspace.innerHTML = `<div class="review-edit-head"><div><p class="review-kicker">Reviewer Mode · Edit</p><h2>Selected passages</h2><p>Edit only what needs changing. Each field starts with the full published translation; additions show in green and removals in red.</p></div><div class="review-edit-actions"><button class="review-mini-btn" type="button" data-review-back>Back to selection</button><button class="review-mini-btn" type="button" data-review-export-draft>Export draft</button><button class="review-mini-btn primary" type="button" data-review-submit>Submit review</button></div></div>${selected.length ? `<div class="review-edit-list">${selected.map(renderEditCard).join('')}</div>` : '<div class="review-empty">No passages are selected yet.</div>'}`;
    workspace.dataset.stage = 'edit';
    observeSpans(workspace);
    updateCount();
    $$('.review-edit-card', workspace).forEach(updateEditCard);
    setupReviewNav();
    scrollTo({ top: 0, behavior: 'auto' });
  }
  function diffHtml(b, newText) {
    if (newText === b.publishedText) return '<span class="review-unchanged">No changes yet.</span>';
    return wordDiff(b.publishedText, newText).map(x => x.type === 'add' ? `<ins class="diff-add">${escapeHtml(x.text)}</ins>` : x.type === 'del' ? `<del class="diff-del">${escapeHtml(x.text)}</del>` : escapeHtml(x.text)).join('');
  }
  function updateEditCard(card) {
    const b = blockMap.get(card.dataset.reviewId); if (!b) return;
    const ta = $('.review-textarea', card), val = ta?.value ?? editValue(b), changed = val !== b.publishedText;
    card.classList.toggle('changed', changed);
    $('.review-status', card).textContent = changed ? 'Edited' : 'Unchanged';
    $('.review-diff-text', card).innerHTML = diffHtml(b, val);
    if (ta) { ta.style.height = 'auto'; ta.style.height = Math.min(Math.max(140, ta.scrollHeight + 2), innerHeight * .7) + 'px'; }
  }
  function scheduleSave() { clearTimeout(saveTimer); saveTimer = setTimeout(() => saveDraft(true), 420); }
  function toggleSelected(id) {
    const set = selectedSet();
    if (set.has(id)) set.delete(id); else set.add(id);
    draft.selected = blockList.filter(b => set.has(b.id)).map(b => b.id);
    saveDraft(false);
    updateCount();
    const card = workspace.querySelector(`[data-review-id="${CSS.escape(id)}"]`);
    if (card) {
      const on = set.has(id);
      card.classList.toggle('selected', on);
      const btn = $('.review-flag', card);
      if (btn) { btn.textContent = on ? '✓' : '!'; btn.setAttribute('aria-pressed', String(on)); btn.setAttribute('aria-label', `${on ? 'Remove' : 'Mark'} this passage for review`); btn.title = on ? 'Remove from review' : 'Mark for review'; }
    }
    const open = $('[data-review-open-edit]', workspace);
    if (open) open.disabled = !draft.selected.length;
  }
  function buildExport(kind = 'submission') {
    buildData();
    const items = draft.selected.map(id => blockMap.get(id)).filter(Boolean).sort((a, b) => a.globalIndex - b.globalIndex).map(b => ({
      blockId: b.id, sectionKey: b.sectionKey, sectionTitle: b.sectionTitle, blockIndex: b.blockIndex + 1, blockType: b.tag,
      publishedFingerprint: b.publishedFingerprint, publishedText: b.publishedText, proposedText: editValue(b), changed: isChanged(b),
      reviewerNote: noteValue(b), sourceLanguage: CFG.sourceLanguage, sourceText: b.sourceText || null,
      sourceMapping: CFG.sourceLanguage ? 'proportional source context; paragraph boundaries may differ' : null,
    }));
    return {
      schema: 'tmoc-translation-review/v1', kind, exportedAt: new Date().toISOString(),
      book: { slug: CFG.slug, title: CFG.title, version: CFG.version, englishMarkdown: CFG.englishMarkdown, sourceLanguage: CFG.sourceLanguage, sourceMarkdown: CFG.sourceMarkdown },
      summary: { selected: items.length, changed: items.filter(x => x.changed).length, notes: items.filter(x => x.reviewerNote).length },
      items,
    };
  }
  function downloadJson(kind = 'submission') {
    const payload = buildExport(kind), date = new Date().toISOString().slice(0, 10);
    const name = `${CFG.slug}-${kind === 'draft' ? 'review-draft' : 'review'}-${date}.json`;
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url; a.download = name; body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }
  function showSubmit() {
    const p = buildExport('submission');
    $('#review-summary-selected').textContent = p.summary.selected;
    $('#review-summary-changed').textContent = p.summary.changed;
    $('#review-summary-notes').textContent = p.summary.notes;
    modal.hidden = false;
    body.classList.add('review-modal-open');
    $('#review-download-final')?.focus();
  }
  function hideSubmit() { if (!modal) return; modal.hidden = true; body.classList.remove('review-modal-open'); }

  /* ---------- sidebar in review mode ---------- */
  const tocLinks = () => $$('.toc[data-l="en"] a, .toc:not([data-l]) a');
  function reviewNavTarget(a) {
    const anchors = sectionAnchors();
    const href = decodeURIComponent((a.getAttribute('href') || '').replace(/^#/, ''));
    const original = href && document.getElementById(href);
    if (original) {
      const sec = original.closest('.book-section');
      if (sec) {
        const k = sec.dataset.key || sec.id;
        if (stage === 'edit') return workspace.querySelector(`[data-section-key="${CSS.escape(k)}"]`);
        if (original !== sec && anchors.has(href)) return document.getElementById(anchors.get(href));
        return document.getElementById(anchors.get(k) || '');
      }
    }
    return anchors.has(href) ? document.getElementById(anchors.get(href)) : null;
  }
  function setupReviewNav() {
    navCleanup?.();
    const links = tocLinks(), targets = [];
    links.forEach(a => { const el = reviewNavTarget(a); if (el && !targets.some(x => x.el === el)) targets.push({ a, el }); });
    targets.sort((x, y) => (x.el.compareDocumentPosition(y.el) & Node.DOCUMENT_POSITION_FOLLOWING) ? -1 : 1);
    let raf = 0;
    const sync = () => {
      raf = 0;
      if (!targets.length) return;
      const marker = Math.max(72, innerHeight * .15);
      links.forEach(a => a.classList.remove('active'));
      if (targets[0].el.getBoundingClientRect().top > marker) { api.setCurrent('Reviewer Mode'); return; }
      let hit = targets[0];
      for (let i = 1; i < targets.length; i++) { if (targets[i].el.getBoundingClientRect().top <= marker) hit = targets[i]; else break; }
      hit.a.classList.add('active');
      api.setCurrent(`Reviewing · ${hit.a.dataset.title || hit.a.textContent.trim()}`);
    };
    const schedule = () => { if (!raf) raf = requestAnimationFrame(sync); };
    addEventListener('scroll', schedule, { passive: true });
    addEventListener('resize', schedule);
    navCleanup = () => { removeEventListener('scroll', schedule); removeEventListener('resize', schedule); if (raf) cancelAnimationFrame(raf); };
    sync();
  }
  sidebar?.addEventListener('click', e => {
    if (!mode) return;
    const a = e.target.closest('.toc a');
    if (!a) return;
    e.preventDefault(); e.stopImmediatePropagation();
    const target = reviewNavTarget(a);
    api.closeNav();
    if (target) scrollTo({ top: Math.max(0, target.getBoundingClientRect().top + scrollY - 72), behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, true);

  /* ---------- events ---------- */
  function wire() {
    exitBtn.addEventListener('click', exit);
    countEl.addEventListener('click', () => { if (draft.selected.length) stage === 'edit' ? renderSelection(true) : renderEdit(); });
    actionBtn.addEventListener('click', () => stage === 'edit' ? renderSelection(true) : renderEdit());
    workspace.addEventListener('click', e => {
      const flag = e.target.closest('.review-flag');
      if (flag) { toggleSelected(flag.closest('[data-review-id]').dataset.reviewId); return; }
      if (e.target.closest('[data-review-open-edit]')) { if (draft.selected.length) renderEdit(); return; }
      if (e.target.closest('[data-review-back]')) { renderSelection(false); return; }
      if (e.target.closest('[data-review-export-draft]')) { downloadJson('draft'); return; }
      if (e.target.closest('[data-review-submit]')) { showSubmit(); return; }
      const remove = e.target.closest('.review-remove');
      if (remove) { const card = remove.closest('.review-edit-card'); toggleSelected(card.dataset.reviewId); card.remove(); if (!draft.selected.length) renderEdit(); return; }
      const reset = e.target.closest('.review-reset');
      if (reset) {
        const card = reset.closest('.review-edit-card'), b = blockMap.get(card.dataset.reviewId), ta = $('.review-textarea', card);
        if (b && ta) { ta.value = b.publishedText; delete draft.edits[b.id]; updateEditCard(card); saveDraft(true); }
      }
    });
    workspace.addEventListener('input', e => {
      const card = e.target.closest('.review-edit-card'); if (!card) return;
      const b = blockMap.get(card.dataset.reviewId); if (!b) return;
      if (e.target.classList.contains('review-textarea')) { draft.edits[b.id] = e.target.value; updateEditCard(card); scheduleSave(); }
      else if (e.target.classList.contains('review-note-input')) {
        draft.notes[b.id] = e.target.value;
        const summary = $('.review-note summary', card);
        if (summary) summary.textContent = e.target.value.trim() ? 'Reviewer note' : 'Add note';
        scheduleSave();
      }
    });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && modal && !modal.hidden) { hideSubmit(); e.stopImmediatePropagation(); } }, true);
    addEventListener('beforeunload', () => { if (mode) saveDraft(false); });
  }

  function revealSource(anchor) {
    const target = $$('[data-source-origin-ids]', workspace).find(el => el.dataset.sourceOriginIds.split(' ').includes(anchor));
    if (!target) return;
    const card = target.closest('.review-card') || target;
    card.scrollIntoView({ block: 'center' });
    target.classList.add('search-destination');
  }

  let wired = false;
  async function enter(opts) {
    if (mode) return;
    api = opts.api;
    const b = opts.book;
    CFG = Object.assign({}, b.review, { store: b.sourceStore ? { lang: b.sourceStore.lang, file: b.sourceStore.file } : null });
    draftKey = `tmoc-review-draft:${CFG.slug}:${CFG.version}`;
    ensureChrome();
    if (!wired) { wire(); wired = true; }
    api.setCurrent('Loading Reviewer Mode…');
    await loadSourceStore();
    previous = { lang: api.lang, y: scrollY };
    mode = true;
    root.dataset.lang = 'en';
    root.lang = 'en';
    body.classList.add('review-mode');
    buildData();
    renderSelection(false);
    try { const u = new URL(location.href); u.searchParams.set('review', '1'); u.hash = ''; history.replaceState(null, '', u); } catch {}
    if (opts.revealSource) requestAnimationFrame(() => revealSource(opts.revealSource));
  }
  function exit() {
    if (!mode) return;
    mode = false;
    saveDraft(false);
    hideSubmit();
    navCleanup?.(); navCleanup = null;
    body.classList.remove('review-mode', 'nav-open');
    workspace.innerHTML = '';
    workspace.dataset.stage = '';
    $$('.toc a.active').forEach(a => a.classList.remove('active'));
    try { const u = new URL(location.href); u.searchParams.delete('review'); u.searchParams.delete('passage'); u.searchParams.delete('lang'); history.replaceState(null, '', u); } catch {}
    api.setLang(previous?.lang || 'en');
    scrollTo({ top: previous?.y || 0, behavior: 'auto' });
    api.setCurrent('');
    api.afterExit();
  }

  window.LibraryReviewer = { enter, exit, get active() { return mode; } };
})();
