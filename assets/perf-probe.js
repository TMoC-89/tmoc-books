/* The Library — performance probe. Only loaded when a page is opened with ?perf=1 (it then stays on
   for the rest of the browser tab). Records how long each tap takes and where the time goes, so
   slowdowns on real phones can be diagnosed. Nothing is sent anywhere: "Copy report" copies the
   measurements to the clipboard for pasting into a message. Turn off with ?perf=0. */
(() => {
  'use strict';
  if (window.__libraryProbe) return;
  window.__libraryProbe = true;
  const t0 = performance.now();
  const interactions = [], frames = [];
  const round = n => Math.round(n);
  const describe = node => {
    const el = node?.closest?.('button, a, input, label, [role]') || node;
    if (!el || !el.tagName) return '';
    const id = el.id ? '#' + el.id : '';
    const cls = typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return (el.tagName.toLowerCase() + id + cls).slice(0, 60);
  };

  try {
    new PerformanceObserver(list => {
      for (const e of list.getEntries()) {
        if (!e.interactionId || e.duration < 40) continue;
        const prev = interactions.find(x => x.id === e.interactionId);
        const rec = {
          id: e.interactionId, at: round(e.startTime), event: e.name, target: describe(e.target), total: round(e.duration),
          wait: round(e.processingStart - e.startTime), handlers: round(e.processingEnd - e.processingStart),
          paint: round(e.startTime + e.duration - e.processingEnd),
        };
        if (prev) { if (rec.total > prev.total) Object.assign(prev, rec); } else interactions.push(rec);
      }
      render();
    }).observe({ type: 'event', buffered: true, durationThreshold: 40 });
  } catch {}
  try {
    new PerformanceObserver(list => {
      for (const f of list.getEntries()) {
        if (f.duration < 100) continue;
        const end = f.startTime + f.duration;
        const scripts = (f.scripts || []).map(s => ({
          ms: round(s.duration), forcedLayout: round(s.forcedStyleAndLayoutDuration || 0), invoker: (s.invoker || '').slice(0, 60),
          fn: s.sourceFunctionName || '', src: (s.sourceURL || '').split('/').pop().split('?')[0] + (s.sourceCharPosition >= 0 ? ':' + s.sourceCharPosition : ''),
        })).sort((a, b) => b.ms - a.ms).slice(0, 4);
        frames.push({
          at: round(f.startTime), ms: round(f.duration), blocking: round(f.blockingDuration || 0),
          script: scripts.reduce((a, s) => a + s.ms, 0),
          styleLayout: f.styleAndLayoutStart ? round(end - f.styleAndLayoutStart) : null,
          render: f.renderStart ? round(end - f.renderStart) : null,
          scripts,
        });
      }
      render();
    }).observe({ type: 'long-animation-frame', buffered: true });
  } catch {}

  const box = document.createElement('div');
  box.setAttribute('role', 'status');
  box.style.cssText = 'position:fixed;left:6px;right:6px;bottom:6px;z-index:9999;max-height:38vh;overflow:auto;padding:8px 10px;border-radius:8px;background:rgba(20,20,18,.92);color:#f3f1ea;font:11px/1.45 ui-monospace,Menlo,monospace;box-shadow:0 6px 24px rgba(0,0,0,.35)';
  box.innerHTML = '<div style="display:flex;gap:8px;align-items:center;margin-bottom:4px"><strong style="flex:1">Performance probe</strong><button type="button" data-copy style="font:inherit;padding:4px 8px;border-radius:5px;border:0;background:#e3a58f;color:#1a1a17">Copy report</button><button type="button" data-hide style="font:inherit;padding:4px 8px;border-radius:5px;border:1px solid #666;background:none;color:inherit">Hide</button></div><div data-out>Tap around; slow taps (40 ms+) appear here.</div>';
  const out = box.querySelector('[data-out]');
  let raf = 0;
  function render() {
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      const rows = interactions.slice(-6).reverse().map(i => `${(i.at / 1000).toFixed(1)}s ${i.event} ${i.target}: <b>${i.total} ms</b> (wait ${i.wait}, code ${i.handlers}, draw ${i.paint})`);
      const long = frames.filter(f => f.ms >= 250).slice(-3).reverse().map(f => `frame ${(f.at / 1000).toFixed(1)}s: ${f.ms} ms (script ${f.script}, style+layout ${f.styleLayout ?? '?'}) ${f.scripts[0] ? f.scripts[0].invoker + ' ' + f.scripts[0].fn : ''}`);
      out.innerHTML = (rows.join('<br>') || 'No slow taps yet.') + (long.length ? '<br><span style="opacity:.75">' + long.join('<br>') + '</span>' : '');
    });
  }
  function report() {
    const d = document.documentElement;
    return JSON.stringify({
      page: location.pathname + location.search, at: new Date().toISOString(), probeStartedMs: round(t0),
      ua: navigator.userAgent, brands: navigator.userAgentData?.brands?.map(b => b.brand + ' ' + b.version).join(', '),
      mobile: navigator.userAgentData?.mobile, cores: navigator.hardwareConcurrency, memoryGB: navigator.deviceMemory,
      viewport: innerWidth + 'x' + innerHeight + '@' + devicePixelRatio, lazy: d.classList.contains('lazy-render'),
      theme: d.dataset.theme, lang: d.dataset.lang, size: getComputedStyle(d).getPropertyValue('--reader-size').trim(),
      nodes: document.getElementsByTagName('*').length, scroll: round(scrollY) + '/' + round(d.scrollHeight),
      interactions, frames: frames.slice(-40),
    }, null, 1);
  }
  box.addEventListener('click', async e => {
    if (e.target.closest('[data-hide]')) { box.remove(); return; }
    if (!e.target.closest('[data-copy]')) return;
    const text = report();
    try { await navigator.clipboard.writeText(text); e.target.textContent = 'Copied'; }
    catch {
      const ta = document.createElement('textarea'); ta.value = text; ta.style.cssText = 'position:fixed;inset:10% 5%;z-index:10000;font:11px monospace';
      document.body.append(ta); ta.select(); e.target.textContent = 'Select all + copy';
    }
  });
  const mount = () => document.body.append(box);
  if (document.body) mount(); else addEventListener('DOMContentLoaded', mount);
  window.libraryPerfReport = report;
})();
