// ── Evidence: one cited cell, what we extracted next to the filing itself (a crop of the stored 10-K, the cell boxed),
// or two readings of the same item from two filings side by side. The server computes every state (ledger/crops.py
// state, /api/v1/evidence/<id>); the page renders it and never shows a crop that is not current. ────────────────────
const EVIDENCE_STATE = {located: ['text-green', 'Cell located'], not_located: ['text-red', 'Cell not located'], stale: ['text-orange', 'Crop out of date'],
  missing: ['text-orange', 'Crop file missing'], none: ['text-secondary', 'No crop yet']};
const EV_FIELD = {revenue: 'Revenue', capex: 'Capital spending', opex: 'Operating costs', cost_of_revenue: 'Cost of revenue', operating_income: 'Operating income',
  segment_capex: 'Capex by segment', segment_revenue: 'Revenue by segment', ppe_category: 'Property', finance_lease_liability: 'Finance leases', purchase_commitments: 'Purchase commitments'};

const SEC_LINK = /^https:\/\/www\.sec\.gov\//;  // only an SEC address becomes a link
const evPeriod = (e) => (e.period_start ? `${day(e.period_start)} – ${day(e.period_end)}` : `${e.months ? e.months + ' months to ' : ''}${day(e.period_end)}`);
const evWhat = (e) => [EV_FIELD[e.field] || e.field, e.dimension].filter(Boolean).join(' · ');
const evState = (e) => { const [cls, word] = EVIDENCE_STATE[e.state] || EVIDENCE_STATE.none; return h('span', {class: cls + ' fw-medium'}, word); };
const evKv = (k, v) => h('div', {class: 'ev-kv'}, h('div', {class: 'text-secondary small'}, k), h('div', {class: 'brk'}, v));

function evFiling(e) {
  const crop = e.crop || {};
  return h('div', {class: 'ev-side'},
    h('div', {class: 'hrow'}, evState(e), e.reason ? h('span', {class: 'text-secondary small'}, e.reason) : ''),
    e.state === 'located' && crop.url
      ? h('a', {href: e.viewer, target: '_blank', rel: 'noopener', title: 'Open in filing'}, h('img', {class: 'ev-crop', src: crop.url, alt: `${e.row_label}, ${e.column_label}: ${e.cell_text}, boxed in the filing`}))
      : h('p', {class: 'msg'}, 'No crop'),
    h('div', {class: 'small text-secondary'}, crop.at ? `Page shows ${crop.seen || '—'} · cropped ${when(crop.at)}` : '', crop.hidden ? ` · ${int(crop.hidden)} rows between header and cell folded` : ''),
    h('div', {class: 'hrow mt-1'}, h('a', {class: 'btn btn-primary btn-sm', href: e.viewer, target: '_blank', rel: 'noopener'}, 'Open in filing'),
      SEC_LINK.test(e.sec_url || '') ? h('a', {class: 'small', href: e.sec_url, target: '_blank', rel: 'noopener noreferrer'}, 'sec.gov ↗') : ''));
}

function evExtracted(e) {
  return h('div', {class: 'ev-side'},
    h('div', {class: 'ev-value'}, usd(e.value)),
    evKv('Cited cell', h('span', {class: 'mono'}, e.cell_text)), evKv('Row', e.row_label), evKv('Column', e.column_label.split('|').map((s) => s.trim()).join(' · ')),
    evKv('Units', e.scale > 1 ? `stated × ${int(e.scale)}` : 'as stated'), evKv('Period', evPeriod(e)),
    evKv('Filing', `${e.form} · ${e.accession} · filed ${day(e.filed)}`), evKv('Source', e.kind === 'note' ? 'Notes to the financial statements' : 'Financial statements'));
}

async function evidencePage(view, arg, qs) {
  if (arg === 'compare') return evidenceCompare(view, parseQ(qs || ''));
  const e = await api('/api/v1/evidence/' + encodeURIComponent(decodeURIComponent(arg || '')));
  view.append(h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
      h('div', {class: 'col'}, h('h1', {class: 'page-title'}, evWhat(e), h('span', {class: 'text-secondary ms-2 fw-normal'}, e.ticker)),
        h('div', {class: 'text-secondary small mt-1'}, evPeriod(e))),
      h('div', {class: 'col-auto'}, h('a', {href: `#proof/${e.ticker}`, class: 'small'}, 'Proof')))),
    h('div', {class: 'ev-grid'}, h('section', {}, h('h2', {}, 'Extracted'), evExtracted(e)), h('section', {}, h('h2', {}, 'Filing'), evFiling(e))));
}

async function evidenceCompare(view, q) {
  if (!q.a || !q.b) throw new Error('Two readings are needed: #evidence/compare?a=<id>&b=<id>');
  const [a, b] = await Promise.all([q.a, q.b].map((id) => api('/api/v1/evidence/' + encodeURIComponent(id))));
  const differ = a.value !== b.value;
  const side = (e, n) => h('section', {},
    h('h2', {}, `Filing ${n} · ${e.form} filed ${day(e.filed)}`), h('div', {class: 'text-secondary small mb-2 mono'}, e.accession),
    h('div', {class: 'ev-value'}, usd(e.value), h('span', {class: 'text-secondary small fw-normal ms-2'}, `cited ${e.cell_text}`)),
    evFiling(e));
  view.append(h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
      h('div', {class: 'col'}, h('h1', {class: 'page-title'}, evWhat(a), h('span', {class: 'text-secondary ms-2 fw-normal'}, a.ticker)),
        h('div', {class: 'small mt-1'}, differ ? h('span', {class: 'text-orange fw-medium'}, 'Readings differ') : h('span', {class: 'text-green fw-medium'}, 'Readings agree'),
          h('span', {class: 'text-secondary'}, ` · ${a.row_label} · ${evPeriod(a)}${evPeriod(a) !== evPeriod(b) ? ' and ' + evPeriod(b) : ''}`))))),
    h('div', {class: 'ev-grid ev-wide'}, side(a, 'A'), side(b, 'B')));
}
