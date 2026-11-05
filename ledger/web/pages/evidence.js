// ── Evidence: one cited cell, what we extracted next to the filing itself (a crop of the stored 10-K, the cell boxed),
// or two readings of the same item from two filings side by side. The server computes every state (ledger/checks/crops.py
// cells, /api/v1/evidence/<id>; the words are states.CROP via _shared.js cropWord); the page never shows a crop that is not current. ────────────────────
const evPeriod = (e) => (e.period_start ? `${day(e.period_start)} – ${day(e.period_end)}` : `${e.months ? e.months + ' months to ' : ''}${day(e.period_end)}`);
const evWhat = (e) => [FIELDS[e.field] || e.field, e.dimension].filter(Boolean).join(' · ');
const evState = (e) => { const [cls, word] = cropWord(e.state); return h('span', {class: cls + ' fw-medium'}, word); };
const evKv = (k, v) => h('div', {class: 'ev-kv'}, h('div', {class: 'text-secondary small'}, k), h('div', {class: 'brk'}, v));

function evFiling(e) {
  const crop = e.crop || {};
  return h('div', {class: 'ev-side'},
    h('div', {class: 'hrow'}, evState(e), e.reason ? h('span', {class: 'text-secondary small'}, e.reason) : '', e.mark ? h('span', {class: 'text-orange fw-medium small'}, e.mark) : ''),
    e.state === 'located' && crop.url
      ? h('div', {class: 'ev-frame'}, h('a', {href: safeHref(e.viewer), target: '_blank', rel: 'noopener', title: 'Open in filing'}, h('img', {class: 'ev-crop', src: crop.url, alt: `${e.row_label}, ${e.column_label}: ${e.cell_text}, boxed in the filing`,
          onload: (ev) => legibleCrop(ev.target), onerror: (ev) => cropFailed(ev.target.closest('.ev-frame'), e.viewer)})))
      : h('p', {class: 'msg'}, '—'),
    h('div', {class: 'small text-secondary'}, crop.at ? `Page shows ${crop.seen || '—'} · cropped ${when(crop.at)}` : '', crop.hidden ? ` · ${int(crop.hidden)} rows folded` : ''),
    h('div', {class: 'hrow mt-1'}, h('a', {class: 'btn btn-outline-secondary btn-sm', href: safeHref(e.viewer), target: '_blank', rel: 'noopener'}, 'Open in filing'),
      SEC_LINK.test(e.sec_url || '') ? h('a', {class: 'small', href: safeHref(e.sec_url), target: '_blank', rel: 'noopener noreferrer'}, 'sec.gov ↗') : ''));
}

function evExtracted(e) {
  return h('div', {class: 'ev-side'},
    h('div', {class: 'ev-value'}, usdExact(e.value)),
    evKv('Cited cell', h('span', {class: 'mono'}, e.cell_text)), evKv('Row', e.row_label), evKv('Column', e.column_label.split('|').map((s) => s.trim()).join(' · ')),
    evKv('Units', e.scale > 1 ? `stated × ${int(e.scale)}` : 'as stated'), evKv('Period', evPeriod(e)),
    evKv('Filing', `${e.form} · ${e.accession} · filed ${day(e.filed)}`), evKv('Source', e.kind === 'note' ? 'Notes to the financial statements' : 'Financial statements'));
}

async function evidencePage(view, arg, qs) {
  if (arg === 'compare') return evidenceCompare(view, parseQ(qs || ''));
  const e = await api('/api/v1/evidence/' + encodeURIComponent(decodeURIComponent(arg || '')));
  view.append(h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
      h('div', {class: 'col'}, h('h1', {class: 'page-title'}, evWhat(e), h('span', {class: 'text-secondary ms-2 fw-normal'}, e.ticker)),
        h('div', {class: 'text-secondary small mt-1'}, evPeriod(e)), restatedLine(e.restatement, true)),
      h('div', {class: 'col-auto'}, h('a', {href: `#proof/${e.ticker}`, class: 'small'}, 'Company trail')))),
    h('div', {class: 'ev-grid'}, h('section', {}, h('h2', {}, 'Extracted'), evExtracted(e)), h('section', {}, h('h2', {}, 'Filing'), evFiling(e))));
}

async function evidenceCompare(view, q) {
  if (!q.a || !q.b) throw new Error('Two readings are needed: #evidence/compare?a=<id>&b=<id>');
  const [a, b] = await Promise.all([q.a, q.b].map((id) => api('/api/v1/evidence/' + encodeURIComponent(id))));
  const differ = a.value !== b.value;
  const fmt = differ && usd(a.value) === usd(b.value) ? usdExact : usd;  // two different readings never print the same
  const side = (e, n) => h('section', {},
    h('h2', {}, `Filing ${n} · ${e.form} filed ${day(e.filed)}`), h('div', {class: 'text-secondary small mb-2 mono'}, e.accession),
    h('div', {class: 'ev-value'}, fmt(e.value), h('span', {class: 'text-secondary small fw-normal ms-2'}, `cited ${e.cell_text}`)),
    evFiling(e));
  view.append(h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
      h('div', {class: 'col'}, h('h1', {class: 'page-title'}, evWhat(a), h('span', {class: 'text-secondary ms-2 fw-normal'}, a.ticker)),
        h('div', {class: 'small mt-1'}, differ ? h('span', {class: 'text-orange fw-medium'}, 'Readings differ') : h('span', {class: 'text-green fw-medium'}, 'Readings agree'),
          h('span', {class: 'text-secondary'}, ` · ${a.row_label} · ${evPeriod(a)}${evPeriod(a) !== evPeriod(b) ? ' and ' + evPeriod(b) : ''}`)), restatedLine(a.restatement || b.restatement)))),
    h('div', {class: 'ev-grid ev-wide'}, side(a, 'A'), side(b, 'B')));
}
