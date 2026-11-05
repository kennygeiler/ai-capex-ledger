// ── Company trail: per item, the value, its cited source (the crop of the cell) and its verification ────────────────
// The card comes from the API (ledger/web/cards.py); the crop's state from ledger/checks/crops.py (the gold set and Reconcile read
// the same). The page never shows the internal words (by, located, twin, reason).
const TRAIL_STAGE_HELP = {
  ingest: '10-K filings from SEC EDGAR; statement tables located',
  values: 'Income statement and cash-flow statement; one cited cell per figure',
  facts: 'Notes: segments, asset categories, leases, commitments',
  statements: 'Company statements on AI spending, verbatim',
  mapping: 'Reported asset categories mapped to US GAAP members',
  planned: 'Guidance and named projects, verbatim',
  release: 'Items blocking release'};
// The ladder (T92): the row's word and colour come from ledger/core/states.py (STATES.row, /pages/_states.js); the card's tone is its state.
const rowWord = (tone) => stateWord('row', tone);
const TRAIL_RULE = {jump: 'Large year-over-year change', restated: 'Restated', row_switch: 'Line renamed', capex_intensity: 'Capex high vs revenue', opex_over_revenue: 'Opex above revenue'};

function trailWhat(it, stage) {
  const r = it.ref || {}, s = it.show || {};
  if (stage === 'facts' && r.finding) return [FIELDS[r.field] || r.field, r.period, r.finding === 'segment_basis_mixed' ? 'Segment basis' : 'Parts vs total'].filter(Boolean).join(' · ');
  if (stage === 'values' && s.rule) return [FIELDS[r.field] || r.field, r.period, TRAIL_RULE[s.rule] || s.rule.replaceAll('_', ' ')].filter(Boolean).join(' · ');
  if ((stage === 'values' || stage === 'facts') && r.field) return [FIELDS[r.field] || r.field, r.dimension, r.period].filter(Boolean).join(' · ');
  if (stage === 'statements' && s.field) return [FIELDS[s.field] || s.field, s.period, s.kind === 'outlook' ? 'Outlook' : 'Actual'].join(' · ');
  if (stage === 'planned' && s.name) return [s.category === 'project' ? 'Project' : 'Guidance', s.name, s.fiscal_year].filter(Boolean).join(' · ');
  if (stage === 'mapping') return it.name || it.what;
  if (s.note) return s.note;
  return it.what;
}

// Source: one line per filing, the crop above it; two filings that disagree sit side by side
function trailSource(c, what) {
  const where = c.where || [];
  if (!where.length) return h('span', {class: 'text-secondary'}, '—');
  return h('div', {}, calcBlock(c.calc), h('div', {class: 'cites'}, where.map((w) => (w.crop
    ? citeCell(w, what)
    : h('div', {class: 'cite-line small'}, w.viewer ? [w.label, ' · ', h('a', {href: safeHref(w.viewer), target: '_blank', rel: 'noopener', title: 'Open in filing, the cell outlined'}, 'Open'), SEC_LINK.test(w.link || '') ? [' · ', h('a', {href: safeHref(w.link), target: '_blank', rel: 'noopener noreferrer'}, 'sec.gov ↗')] : '']
      : [w.label, w.link ? [' · ', h('a', {href: safeHref(w.link), target: '_blank', rel: 'noopener noreferrer'}, 'Open ↗')] : ''])))));
}

// Verification: the status word and one short line; the long form opens under it
function trailVerify(c, ticker) {
  const [cls, word] = rowWord(c.how.tone);
  const line = h('div', {class: 'small'}, h('span', {class: cls + ' fw-medium'}, word), c.how.text ? h('span', {class: 'text-secondary'}, ` · ${c.how.text}`) : '');
  const more = [restatedLine(c.restatement), c.compare ? h('div', {class: 'small'}, h('a', {href: `#evidence/compare?a=${encodeURIComponent(c.compare.a)}&b=${encodeURIComponent(c.compare.b)}`}, 'Compare filings')) : ''];
  const tie = tieParts(c.how.detail);  // V11: a tie's parts as a list of values, the count and tolerance as cells
  const detail = tie ? h('div', {class: 'small mt-1'}, valueCells([['Parts', tie.n.split(' ')[0]], ['Tolerance', tie.tolerance]], 'compact'), h('div', {class: 'readings mt-1'}, tie.parts.map(([k, v]) => [h('span', {class: 'text-secondary'}, k), h('span', {class: 'num'}, v)])))
    : h('div', {class: 'small text-secondary mt-1'}, c.how.detail);
  return [c.how.detail ? h('details', {class: 'why'}, h('summary', {}, line), detail) : line, more];
}

function trailRow(it, stage, ticker, withValue = true) {
  const c = it.card || {how: {tone: 'unknown', text: it.reason || ''}, where: []};
  const [cls] = rowWord(c.how.tone);
  const what = trailWhat(it, stage);
  return h('tr', {},
    h('td', {}, h('span', {class: cls, 'aria-hidden': 'true'}, '● '), what),
    withValue ? h('td', {class: 'num'}, c.found ? (stage === 'statements' || stage === 'planned' ? c.found : h('span', {class: 'money'}, c.found)) : h('span', {class: 'text-secondary'}, '—')) : '',
    h('td', {}, trailSource(c, what)),
    h('td', {}, trailVerify(c, ticker)));
}

function trailTable(items, stage, ticker) {
  const quote = stage === 'statements' || stage === 'planned';  // a quote is the value: it wraps, the rest of the row narrows
  const withValue = items.some((it) => (it.card || {}).found);  // V9: a Value column that would be "—" in every row is left out (Filings)
  return h('div', {class: 'table-responsive'}, h('table', {class: 'table table-vcenter card-table trail' + (quote ? ' trail-quote' : '') + (withValue ? '' : ' no-value')},
    h('colgroup', {}, h('col', {class: 'c-item'}), withValue ? h('col', {class: 'c-value'}) : '', h('col', {class: 'c-source'}), h('col', {class: 'c-verify'})),
    h('thead', {}, h('tr', {}, h('th', {}, 'Item'), withValue ? h('th', {class: 'num'}, 'Value') : '', h('th', {}, 'Source'), h('th', {}, 'Verification'))),
    h('tbody', {}, items.map((it) => trailRow(it, stage, ticker, withValue)))));
}

function stageCard(id, st, waiting, body) {
  const tally = waiting.length ? bucketLine(st.counts) : h('span', {class: 'text-green'}, 'Complete');  // the stage's own buckets, in the words the company's count uses
  return h('div', {class: 'card mb-3'},
    h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0', title: TRAIL_STAGE_HELP[id] || ''}, STAGE_LABEL_UI[id] || id),
      h('span', {class: 'ms-3 small'}, `${plural(st.items, 'item')} · `, tally)),
    body.length ? h('div', {class: 'card-body p-0'}, body) : '');
}

async function trailPage(view, ticker) {
  const c = await api('/api/v1/proof/' + encodeURIComponent(ticker));
  const unfiled = c.filing_state && c.filing_state !== 'filed';  // states.company: nothing read is never Proven or Ready for release (F-BF15)
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('h1', {class: 'page-title'}, c.name, h('span', {class: 'text-secondary ms-2 fw-normal'}, c.ticker)),
      // V6: the state key, one line at 1600, each dot and its word one unit that never wraps apart; what a state means shows on hover and focus
      h('div', {class: 'state-key small mt-1'}, [['ok', 'SEC XBRL or the quoted source'], ['corroborated', 'Ties to totals or confirmed in 2 filings'], ['company', 'The company’s own XBRL tags this category'],
        ['done', 'Located or confirmed; not an independent check'], ['info', 'Citation only'], ['wait', ''], ['bad', 'Open item'], ['blocked', '']].map(([s, title]) => {
          const [cls, word] = rowWord(s);
          // the meaning shows on hover and on keyboard focus (data-tip, app.html) and is read with the word
          return h('span', {class: cls, tabindex: title ? 0 : null, 'data-tip': title || null, 'aria-label': title ? `${word}: ${title}` : null}, h('span', {'aria-hidden': 'true'}, '● '), word);
        }), c.in_proven_set ? '' : h('span', {class: 'text-secondary'}, 'Not in scope'))),
    h('div', {class: 'col-auto'}, unfiled ? h('span', {class: stateWord('company', c.filing_state)[0] + ' fw-medium'}, stateWord('company', c.filing_state)[1])
      : c.proven ? h('span', {class: 'text-green fw-medium'}, 'Proven') : bucketLine(c.counts),
      h('a', {href: `#reconcile?scope=${c.ticker}`, class: 'small ms-3'}, 'Reconcile'), h('a', {href: `#data?ticker=${c.ticker}`, class: 'small ms-2'}, 'Dataset'))));
  const waitingTotal = Object.values(c.stages).reduce((n, st) => n + (st.open || []).length, 0);
  const s = c.summary || {}, S = c.status || {};
  const hours = S.sec_checked_hours_ago;
  // the state is the server's (states.edgar, the one the claims register reads); the page only adds the age
  const [secCls, secWord] = stateWord('edgar', S.sec_check), fresh = h('span', {class: secCls},
    S.sec_check === 'fresh' ? `${secWord} ${hours}h ago` : S.sec_check === 'stale' ? `${stateWord('edgar', 'fresh')[1]} ${Math.round(hours / 24)}d ago · ${secWord}` : secWord);
  const tile = (title, ...lines) => h('div', {class: 'col-md-4'}, h('div', {class: 'text-secondary small text-uppercase mb-1'}, title), ...lines.map((l) => h('div', {class: 'small'}, l)));
  const kv = (label, n, cls) => (n ? h('span', {class: 'd-flex justify-content-between', style: 'max-width:15rem'}, h('span', {class: cls || 'text-secondary'}, label), h('span', {class: 'num'}, int(n))) : '');
  const since = S.since;
  const sinceLines = !S.shipped ? ['—'] : (since && (since.added.length + since.changed.length + since.removed.length))
    ? [since.added.length ? `${int(since.added.length)} added` : '', since.changed.length ? `${int(since.changed.length)} changed` : '', since.removed.length ? `${int(since.removed.length)} removed` : '',
       h('details', {}, h('summary', {class: 'text-secondary', style: 'cursor:pointer'}, 'Details'), h('div', {class: 'text-secondary'}, [...since.added.map((x) => '+ ' + x), ...since.changed.map((x) => '~ ' + x), ...since.removed.map((x) => '− ' + x)].map((x) => h('div', {}, x))))].filter(Boolean)
    : ['None'];
  const why = h('div', {class: 'card mb-3'}, h('div', {class: 'card-body py-3'},
    h('div', {class: 'd-flex align-items-baseline flex-wrap gap-2 mb-2'}, h('h3', {class: 'card-title m-0'}, unfiled ? stateWord('company', c.filing_state)[1] : waitingTotal ? 'Before release' : 'Ready for release'),
      h('span', {class: 'text-secondary small'}, `As of ${S.as_of || ''}`), waitingTotal ? h('a', {href: `#reconcile?scope=${c.ticker}`, class: 'small ms-auto'}, 'Review in Reconcile →') : ''),
    h('div', {class: 'row g-3'},
      tile('Coverage',
        s.newest ? (s.newest.url ? h('a', {href: safeHref(s.newest.url), target: '_blank', rel: 'noopener'}, `Through ${s.newest.form} · FY ending ${s.newest.period}`) : `Through ${s.newest.form} · FY ending ${s.newest.period}`) : 'No filings',
        s.newest ? `Filed ${s.newest.filed}` : '', S.next_expected ? `Next 10-K expected ~${S.next_expected}` : '',
        s.unread && s.unread.length ? h('span', {class: 'text-orange fw-medium'}, `${plural(s.unread.length, 'new filing')} not read`) : '', fresh),
      tile('Verification',
        kv('Figures', S.figures, 'text-body fw-medium'), kv('Match SEC XBRL', S.matched, 'text-green'), kv('Tie to totals', S.tied, 'text-teal'),
        kv('Confirmed in 2 filings', S.second_reading, 'text-teal'), kv('Citation only', S.reading_only, 'text-azure'),
        ...bucketParts(c.counts).map(([b, n]) => kv(stateWord('row', b)[1], n, stateWord('row', b)[0])), kv('Quotes verified', S.quotes)),
      // V9: the release and the changes since it share one column (a whole column held "None")
      tile('Last release', S.shipped ? S.shipped.version : 'None', S.shipped ? `Signed ${S.shipped.signed_at} · ${S.shipped.signed_by}` : '',
        S.shipped ? h('div', {class: 'mt-2'}, h('div', {class: 'text-secondary small text-uppercase mb-1'}, 'Changes since release'), ...sinceLines.map((l) => h('div', {class: 'small'}, l))) : ''))));
  const order = (it) => ({open: 0, blocked: 0, explained: 1, checked: 2})[it.state] ?? 1;
  const cards = Object.entries(c.stages).map(([id, st]) => {
    const all = [...(st.all || [])].sort((a, b) => order(a) - order(b));
    const waiting = all.filter((i) => order(i) === 0), rest = all.filter((i) => order(i) > 0);
    const body = [];
    if (id === 'mapping') {  // one decision card per category (ledger/review/mapcard.py), the same card Reconcile shows with its actions
      const list = (items) => h('div', {class: 'list-group list-group-flush'}, items.map((i) => h('div', {class: 'list-group-item py-3'}, i.decision ? mappingDecision(i.decision,
        order(i) === 0 || i.by === 'mapping:filer_tag' ? h('div', {class: 'mt-2'}, h('a', {href: `#reconcile?scope=${c.ticker}&cause=asset_types`, class: 'small'}, order(i) === 0 ? 'Decide in Reconcile →' : 'Confirm or override in Reconcile →')) : '') : trailTable([i], id, c.ticker))));
      if (waiting.length) body.push(list(waiting));
      if (rest.length) body.push(waiting.length ? h('details', {class: 'px-3 py-2'}, h('summary', {class: 'text-secondary small', style: 'cursor:pointer'}, tallyLine(rest)), list(rest)) : list(rest));
      return stageCard(id, st, waiting, body);
    }
    if (waiting.length) body.push(trailTable(waiting, id, c.ticker));
    if (rest.length) {
      body.push(waiting.length || rest.length > 12
        ? h('details', {class: 'px-3 py-2'}, h('summary', {class: 'text-secondary small', style: 'cursor:pointer'}, tallyLine(rest)), trailTable(rest, id, c.ticker))
        : trailTable(rest, id, c.ticker));
    }
    return stageCard(id, st, waiting, body);
  });
  view.append(head, why, ...cards);
}
// "12 verified · 3 corroborated · 2 match company tag · 1 done · 4 unverified", by each item's tone, zero parts left out
function tallyLine(items) {
  const n = (tone) => items.filter((i) => ((i.card && i.card.how) || {}).tone === tone).length;
  return [[n('ok'), 'verified'], [n('corroborated'), 'corroborated'], [n('company'), 'match company tag'], [n('done'), 'done'], [n('info'), 'unverified'], [n('unknown'), 'not checked']]
    .filter(([k]) => k).map(([k, w]) => `${int(k)} ${w}`).join(' · ');
}
