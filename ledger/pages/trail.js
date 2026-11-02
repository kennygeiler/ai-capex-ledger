// ── Company trail: every number with what we found, where it is in the filing, and how we know ──────────────────────
// The card comes from the API (ledger/cards.py); the page never shows the internal words (by, located, twin, reason).
const TRAIL_STAGE = {ingest: 'Reports found', values: 'Figures from the financial statements', facts: 'Figures from the notes', statements: 'What the company said about AI',
  mapping: 'Category labels', planned: 'Plans and projects', release: 'Release'};
const TRAIL_STAGE_HELP = {
  ingest: 'Each annual report downloaded from the SEC, and whether the income statement and cash-flow statement were found in it.',
  values: 'Each figure read from the primary financial statements (income statement, cash-flow statement), one cell of the report per figure, per year.',
  facts: 'Each figure read from the notes to the financial statements (breakdowns by segment or category, leases, commitments), one cell per figure.',
  statements: 'Sentences where the company talks about AI spending, quoted word for word.',
  mapping: 'The company’s own names for its property categories, matched to a standard accounting category. A match counts only once a person confirms it.',
  planned: 'Guidance and named projects, quoted word for word.',
  release: 'Anything that would stop this company from being released.'};
const TRAIL_FIELD = {revenue: 'Revenue', capex: 'Capital spending', opex: 'Operating costs', cost_of_revenue: 'Cost of revenue', operating_income: 'Operating income',
  segment_capex: 'Capex by segment', segment_revenue: 'Revenue by segment', ppe_category: 'Property', finance_lease_liability: 'Finance leases', purchase_commitments: 'Purchase commitments'};
const TRAIL_TONE = {ok: ['text-green', 'Checked'], info: ['text-azure', 'Explained'], wait: ['text-orange', 'Waiting for you'], bad: ['text-red', 'Needs a person']};

function trailWhat(it, stage) {
  const r = it.ref || {};
  if ((stage === 'values' || stage === 'facts') && r.field) return [TRAIL_FIELD[r.field] || r.field, r.dimension, r.period].filter(Boolean).join(' · ');
  if (stage === 'mapping') return it.name || it.what;
  return it.what;
}

function trailRow(it, stage) {
  const c = it.card || {how: {tone: 'info', text: it.reason || ''}, where: []};
  const [cls, word] = TRAIL_TONE[c.how.tone] || TRAIL_TONE.info;
  const where = (c.where || []).map((w) => h('div', {class: 'small mb-1'}, w.label,
    w.link ? h('a', {href: w.link, target: '_blank', rel: 'noopener', class: 'ms-2'}, 'open in the filing ↗') : '',
    w.shot ? h('a', {href: w.shot, target: '_blank', rel: 'noopener', class: 'ms-2'}, 'screenshot ↗') : ''));
  return h('tr', {},
    h('td', {class: 'text-nowrap'}, h('span', {class: cls}, '● '), trailWhat(it, stage)),
    h('td', {class: 'brk'}, c.found ? h('span', {class: 'fw-medium'}, c.found) : h('span', {class: 'text-secondary'}, '—')),
    h('td', {class: 'brk'}, where.length ? where : h('span', {class: 'text-secondary small'}, '—')),
    h('td', {class: 'brk small'}, h('span', {class: cls + ' fw-medium'}, word + '. '), c.how.text));
}

function trailTable(items, stage) {
  return h('div', {class: 'table-responsive'}, h('table', {class: 'table table-vcenter card-table'},
    h('thead', {}, h('tr', {}, h('th', {}, 'What'), h('th', {}, 'We found'), h('th', {}, 'Where it is in the filing'), h('th', {}, 'How we know'))),
    h('tbody', {}, items.map((it) => trailRow(it, stage)))));
}

async function trailPage(view, ticker) {
  const c = await api('/api/v1/proof/' + encodeURIComponent(ticker));
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('h1', {class: 'page-title'}, c.name, h('span', {class: 'text-secondary ms-2 fw-normal'}, c.ticker)),
      h('div', {class: 'text-secondary small mt-1', style: 'max-width:60rem'}, 'Every number below shows what we found, where it is in the filing (open it and look), and how we know it is right. ',
        h('span', {class: 'text-green'}, 'Checked'), ' means it matched something outside the filing. ', h('span', {class: 'text-azure'}, 'Explained'), ' means nothing outside confirms it and a written reason says why. ',
        h('span', {class: 'text-orange'}, 'Waiting for you'), ' means a person has to decide.', c.in_proven_set ? '' : ' Not in the proven set.')),
    h('div', {class: 'col-auto'}, c.proven ? h('span', {class: 'text-green fw-medium'}, 'Proven') : h('span', {class: 'text-red fw-medium'}, `${int(c.open)} waiting`),
      h('a', {href: `#reconcile?scope=${c.ticker}`, class: 'small ms-3'}, 'Reconcile'), h('a', {href: `#data?ticker=${c.ticker}`, class: 'small ms-2'}, 'Dataset'))));
  const waitingTotal = Object.values(c.stages).reduce((n, st) => n + (st.open || []).length, 0);
  const s = c.summary || {};
  const why = h('div', {class: 'card mb-3'}, h('div', {class: 'card-body py-3'},
    h('h3', {class: 'card-title mb-1'}, waitingTotal ? `${int(waitingTotal)} decision${waitingTotal === 1 ? '' : 's'} needed before ${c.name} can ship` : `${c.name} is proven: nothing is waiting`),
    h('div', {class: 'text-secondary'}, 'This page is everything the ledger has read for ', c.name, ', with the evidence for each item, so you can stand behind it before a release. ',
      waitingTotal ? 'The items waiting for you are at the top of each section below; decide them in ' : 'Spot-check any item by opening the filing at its row, or go to ',
      h('a', {href: `#reconcile?scope=${c.ticker}`}, 'Reconcile'), '.'),
    h('div', {class: 'small mt-2'},
      s.newest ? ['Newest report read: ', s.newest.url ? h('a', {href: s.newest.url, target: '_blank', rel: 'noopener'}, `${s.newest.form} for the year ending ${s.newest.period}`) : `${s.newest.form} for the year ending ${s.newest.period}`, `, filed ${s.newest.filed}. `] : 'No report read yet. ',
      s.unread && s.unread.length ? h('span', {class: 'text-orange fw-medium'}, `${int(s.unread.length)} newer report${s.unread.length === 1 ? '' : 's'} at the SEC not read yet (${s.unread.map((u) => `${u.form} ${u.period}`).join(', ')}). `) : '',
      s.watched_at ? h('span', {class: 'text-secondary'}, `SEC last checked for new reports ${s.watched_at}.`) : h('span', {class: 'text-secondary'}, 'The SEC has not been checked for new reports.'))));
  const order = (it) => ({open: 0, blocked: 0, explained: 1, checked: 2})[it.state] ?? 1;
  const cards = Object.entries(c.stages).map(([id, st]) => {
    const all = [...(st.all || [])].sort((a, b) => order(a) - order(b));
    const waiting = all.filter((i) => order(i) === 0), rest = all.filter((i) => order(i) > 0);
    const body = [];
    if (waiting.length) body.push(trailTable(waiting, id));
    if (rest.length) {
      const sum = `${int(st.checked)} checked, ${int(st.explained)} explained`;
      body.push(waiting.length || rest.length > 12
        ? h('details', {class: 'px-3 py-2'}, h('summary', {class: 'text-secondary small', style: 'cursor:pointer'}, `Show ${sum}`), trailTable(rest, id))
        : trailTable(rest, id));
    }
    const tally = waiting.length ? h('span', {class: 'text-orange'}, `${int(waiting.length)} waiting`) : h('span', {class: 'text-green'}, 'nothing waiting');
    return h('div', {class: 'card mb-3'},
      h('div', {class: 'card-header py-2 d-block'}, h('div', {class: 'd-flex align-items-baseline'}, h('h3', {class: 'card-title m-0'}, TRAIL_STAGE[id] || id),
        h('span', {class: 'ms-3 small'}, `${int(st.items)} items · `, tally)), h('div', {class: 'text-secondary small mt-1'}, TRAIL_STAGE_HELP[id] || '')),
      body.length ? h('div', {class: 'card-body p-0'}, body) : '');
  });
  view.append(head, why, ...cards);
}
