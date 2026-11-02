// ── Company trail: per item, the value, its cited source and its verification ──────────────────────────────────
// The card comes from the API (ledger/cards.py); the page never shows the internal words (by, located, twin, reason).
const TRAIL_STAGE = {ingest: 'Filings', values: 'Financial statement figures', facts: 'Note figures', statements: 'AI disclosures',
  mapping: 'Category mapping', planned: 'Guidance and projects', release: 'Release'};
const TRAIL_STAGE_HELP = {
  ingest: '10-K filings retrieved from SEC EDGAR; statement tables located.',
  values: 'Income statement and cash-flow statement. One cited cell per figure.',
  facts: 'Notes to the financial statements: segments, asset categories, leases, commitments.',
  statements: 'Company statements on AI spending, quoted verbatim.',
  mapping: 'Reported asset categories mapped to US GAAP members. Reviewer confirmation required.',
  planned: 'Forward-looking guidance and named projects, quoted verbatim.',
  release: 'Items blocking release.'};
const TRAIL_FIELD = {revenue: 'Revenue', capex: 'Capital spending', opex: 'Operating costs', cost_of_revenue: 'Cost of revenue', operating_income: 'Operating income',
  segment_capex: 'Capex by segment', segment_revenue: 'Revenue by segment', ppe_category: 'Property', finance_lease_liability: 'Finance leases', purchase_commitments: 'Purchase commitments'};
// The ladder (T92): Verified against SEC XBRL; Corroborated by a tie to the reported total or a second filing; Unverified, citation only.
const TRAIL_TONE = {ok: ['text-green', 'Verified'], corroborated: ['text-teal', 'Corroborated'], info: ['text-azure', 'Unverified'], wait: ['text-orange', 'Needs review'], bad: ['text-red', 'Needs review']};

function trailWhat(it, stage) {
  const r = it.ref || {};
  if (stage === 'facts' && r.finding) return [TRAIL_FIELD[r.field] || r.field, r.period, 'parts against total'].filter(Boolean).join(' · ');
  if ((stage === 'values' || stage === 'facts') && r.field) return [TRAIL_FIELD[r.field] || r.field, r.dimension, r.period].filter(Boolean).join(' · ');
  if (stage === 'mapping') return it.name || it.what;
  return it.what;
}

function trailRow(it, stage) {
  const c = it.card || {how: {tone: 'info', text: it.reason || ''}, where: []};
  const [cls, word] = TRAIL_TONE[c.how.tone] || TRAIL_TONE.info;
  const where = (c.where || []).map((w) => h('div', {class: 'small mb-1'}, w.label,
    w.link ? h('a', {href: w.link, target: '_blank', rel: 'noopener', class: 'ms-2'}, 'Open ↗') : '',
    w.shot ? h('a', {href: w.shot, target: '_blank', rel: 'noopener', class: 'ms-2'}, 'Screenshot ↗') : ''));
  return h('tr', {},
    h('td', {class: 'text-nowrap'}, h('span', {class: cls}, '● '), trailWhat(it, stage)),
    h('td', {class: 'brk'}, c.found ? h('span', {class: 'fw-medium'}, c.found) : h('span', {class: 'text-secondary'}, '—')),
    h('td', {class: 'brk'}, where.length ? where : h('span', {class: 'text-secondary small'}, '—')),
    h('td', {class: 'brk small'}, h('span', {class: cls + ' fw-medium'}, word), c.how.text ? h('span', {class: 'text-secondary'}, ' · ' + c.how.text) : ''));
}

function trailTable(items, stage) {
  return h('div', {class: 'table-responsive'}, h('table', {class: 'table table-vcenter card-table'},
    h('thead', {}, h('tr', {}, h('th', {}, 'Item'), h('th', {}, 'Value'), h('th', {}, 'Source'), h('th', {}, 'Verification'))),
    h('tbody', {}, items.map((it) => trailRow(it, stage)))));
}

async function trailPage(view, ticker) {
  const c = await api('/api/v1/proof/' + encodeURIComponent(ticker));
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('h1', {class: 'page-title'}, c.name, h('span', {class: 'text-secondary ms-2 fw-normal'}, c.ticker)),
      h('div', {class: 'small mt-1'}, h('span', {class: 'text-green'}, '● Verified'), h('span', {class: 'text-secondary'}, ' SEC XBRL or the quoted source  '),
        h('span', {class: 'text-teal ms-2'}, '● Corroborated'), h('span', {class: 'text-secondary'}, ' ties to totals or confirmed in 2 filings  '),
        h('span', {class: 'text-azure ms-2'}, '● Unverified'), h('span', {class: 'text-secondary'}, ' citation only  '), h('span', {class: 'text-orange ms-2'}, '● Needs review'), c.in_proven_set ? '' : h('span', {class: 'text-secondary ms-2'}, '· Outside proven set'))),
    h('div', {class: 'col-auto'}, c.proven ? h('span', {class: 'text-green fw-medium'}, 'Proven') : h('span', {class: 'text-orange fw-medium'}, `${int(c.open)} to review`),
      h('a', {href: `#reconcile?scope=${c.ticker}`, class: 'small ms-3'}, 'Reconcile'), h('a', {href: `#data?ticker=${c.ticker}`, class: 'small ms-2'}, 'Dataset'))));
  const waitingTotal = Object.values(c.stages).reduce((n, st) => n + (st.open || []).length, 0);
  const s = c.summary || {}, S = c.status || {};
  const hours = S.sec_checked_hours_ago;
  const fresh = hours == null ? h('span', {class: 'text-orange'}, 'EDGAR never checked')
    : hours <= 48 ? h('span', {class: 'text-secondary'}, `EDGAR checked ${hours}h ago`)
    : h('span', {class: 'text-orange'}, `EDGAR checked ${Math.round(hours / 24)}d ago · stale`);
  const tile = (title, ...lines) => h('div', {class: 'col-md-3'}, h('div', {class: 'text-secondary small text-uppercase mb-1'}, title), ...lines.map((l) => h('div', {class: 'small'}, l)));
  const since = S.since;
  const sinceLines = !S.shipped ? ['—'] : (since && (since.added.length + since.changed.length + since.removed.length))
    ? [since.added.length ? `${int(since.added.length)} added` : '', since.changed.length ? `${int(since.changed.length)} changed` : '', since.removed.length ? `${int(since.removed.length)} removed` : '',
       h('details', {}, h('summary', {class: 'text-secondary', style: 'cursor:pointer'}, 'Details'), h('div', {class: 'text-secondary'}, [...since.added.map((x) => '+ ' + x), ...since.changed.map((x) => '~ ' + x), ...since.removed.map((x) => '− ' + x)].map((x) => h('div', {}, x))))].filter(Boolean)
    : ['None'];
  const why = h('div', {class: 'card mb-3'}, h('div', {class: 'card-body py-3'},
    h('div', {class: 'd-flex align-items-baseline flex-wrap gap-2'}, h('h3', {class: 'card-title m-0'}, waitingTotal ? `${int(waitingTotal)} item${waitingTotal === 1 ? '' : 's'} to review before release` : 'Proven · no items to review'),
      h('span', {class: 'text-secondary small'}, `As of ${S.as_of || ''}`), waitingTotal ? h('a', {href: `#reconcile?scope=${c.ticker}`, class: 'small ms-auto'}, 'Review in Reconcile →') : ''),
    h('div', {class: 'row g-3'},
      tile('Coverage',
        s.newest ? (s.newest.url ? h('a', {href: s.newest.url, target: '_blank', rel: 'noopener'}, `Through ${s.newest.form} FY ${s.newest.period}`) : `Through ${s.newest.form} FY ${s.newest.period}`) : 'No filings',
        s.newest ? `Filed ${s.newest.filed}` : '', S.next_expected ? `Next 10-K expected ~${S.next_expected}` : '',
        s.unread && s.unread.length ? h('span', {class: 'text-orange fw-medium'}, `${int(s.unread.length)} new filing${s.unread.length === 1 ? '' : 's'} not ingested`) : '', fresh),
      tile('Verification',
        h('span', {}, h('b', {}, int(S.figures)), ' figures'),
        h('span', {class: 'text-green'}, `${int(S.matched)} XBRL`),
        h('span', {class: 'text-teal'}, `${int(S.tied)} tie to totals`),
        h('span', {class: 'text-teal'}, `${int(S.second_reading)} confirmed in 2 filings`),
        h('span', {class: 'text-azure'}, `${int(S.reading_only)} citation only`),
        h('span', {class: S.waiting ? 'text-orange' : 'text-secondary'}, `${int(S.waiting)} to review`),
        h('span', {class: 'text-secondary'}, `${int(S.quotes)} quotes verified`)),
      tile('Last release', S.shipped ? S.shipped.version : 'None', S.shipped ? `Signed ${S.shipped.signed_at} · ${S.shipped.signed_by}` : ''),
      tile('Changes since release', ...sinceLines))));
  const order = (it) => ({open: 0, blocked: 0, explained: 1, checked: 2})[it.state] ?? 1;
  const cards = Object.entries(c.stages).map(([id, st]) => {
    const all = [...(st.all || [])].sort((a, b) => order(a) - order(b));
    const waiting = all.filter((i) => order(i) === 0), rest = all.filter((i) => order(i) > 0);
    const body = [];
    if (waiting.length) body.push(trailTable(waiting, id));
    if (rest.length) {
      const corr = rest.filter((i) => i.card && i.card.how && i.card.how.tone === 'corroborated').length;
      const sum = `${int(st.checked - corr)} verified · ${corr ? `${int(corr)} corroborated · ` : ''}${int(st.explained)} unverified`;
      body.push(waiting.length || rest.length > 12
        ? h('details', {class: 'px-3 py-2'}, h('summary', {class: 'text-secondary small', style: 'cursor:pointer'}, `${sum}`), trailTable(rest, id))
        : trailTable(rest, id));
    }
    const tally = waiting.length ? h('span', {class: 'text-orange'}, `${int(waiting.length)} to review`) : h('span', {class: 'text-green'}, 'complete');
    return h('div', {class: 'card mb-3'},
      h('div', {class: 'card-header py-2 d-block'}, h('div', {class: 'd-flex align-items-baseline'}, h('h3', {class: 'card-title m-0'}, TRAIL_STAGE[id] || id),
        h('span', {class: 'ms-3 small'}, `${int(st.items)} items · `, tally)), h('div', {class: 'text-secondary small mt-1'}, TRAIL_STAGE_HELP[id] || '')),
      body.length ? h('div', {class: 'card-body p-0'}, body) : '');
  });
  view.append(head, why, ...cards);
}
