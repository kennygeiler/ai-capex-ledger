// ── Proof: the pipeline proves every number it produces, shown on the proven set first (docs/PROOF.md) ──
const cnt = (n, cls) => h('span', {class: 'badge ' + cls}, int(n));
// what explained a stage's items, by name, for the hover: "label:no_reference ×30, rule:restated_between_filings ×5"
function byHover(items) {
  const n = new Map();
  for (const i of items || []) n.set(i.by || '(none)', (n.get(i.by || '(none)') || 0) + 1);
  return [...n].sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ×${v}`).join(', ');
}
function stageCell(st) {
  const blocked = st.blocked || 0, open = st.open.length;  // open counts blocked too (docs/PROOF.md); blocked is named on its own beside it
  const title = st.explained_items && st.explained_items.length ? `explained by ${byHover(st.explained_items)}` : 'explained by a rule, a definition or a decision';
  return h('td', {class: 'num'}, h('span', {class: 'text-green fw-semibold', title: 'checked against something independent'}, int(st.checked)), h('span', {class: 'text-secondary'}, ' · '),
    h('span', {class: 'text-azure', title}, int(st.explained)), h('span', {class: 'text-secondary'}, ' · '),
    open ? h('span', {class: 'badge bg-red-lt', title: 'open: needs a rule or a definition (blocked counted in)'}, int(open)) : h('span', {class: 'text-secondary', title: 'open'}, '0'),
    blocked ? [h('span', {class: 'text-secondary'}, ' · '), h('span', {class: 'badge bg-red-lt', title: 'blocked: refuses the release'}, `${int(blocked)} blocked`)] : '');
}
async function proofPage(view) {
  const [b, g] = await Promise.all([api('/api/v1/proof'), api('/api/v1/golden').catch(() => ({ok: null}))]);
  const proven = b.proven.filter((c) => c.proven).length;
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'}, h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Proof'),
    h('div', {class: 'text-secondary small'}, h('b', {class: 'text-body'}, `${proven} of ${b.proven.length}`), ' proven. Every number is ', h('span', {class: 'text-green'}, 'checked'), ' against something independent, ', h('span', {class: 'text-azure'}, 'explained'), ' by a rule or a definition on file, or ', h('span', {class: 'text-red'}, 'open'), '. Proven means nothing open at any stage.')),
    h('div', {class: 'col-auto'}, g.ok == null ? h('span', {class: 'badge bg-secondary-lt'}, 'golden: not run') : h('span', {class: 'badge ' + (g.ok ? 'bg-green-lt' : 'bg-red-lt')}, g.ok ? `golden: equal, ${day(g.at)}` : `golden: differs, ${day(g.at)}`))));
  const table_ = h('div', {class: 'card'}, h('div', {class: 'table-responsive'}, h('table', {class: 'table table-vcenter card-table'},
    h('thead', {}, h('tr', {}, h('th', {}, 'Company'), b.stages.map((s) => h('th', {class: 'num'}, s.label)), h('th', {}, ''))),
    h('tbody', {}, b.proven.map((c) => h('tr', {class: 'item', tabindex: 0, onclick: () => go('proof/' + c.ticker), onkeydown: (e) => { if (e.key === 'Enter') go('proof/' + c.ticker); }},
      h('td', {}, h('div', {}, h('a', {href: '#proof/' + c.ticker, onclick: (e) => e.stopPropagation()}, c.name), ' ', h('span', {class: 'text-secondary small'}, c.ticker)), h('div', {class: 'text-secondary small'}, INDUSTRY[c.layer] || c.layer, '. ', c.why)),
      b.stages.map((s) => stageCell(c.stages[s.id])),
      h('td', {}, c.proven ? h('span', {class: 'badge bg-green-lt'}, 'proven') : h('span', {class: 'badge bg-red-lt'}, `${int(c.open)} open`))))))));
  const legend = h('p', {class: 'text-secondary small mt-2'}, 'Each cell: checked · explained · open, and blocked when any. Hover an explained count for what explained it. Click a company for its trail; open items say what rule or definition is missing.');
  // T56: rows by the strongest answer key that vouches for them, graded by independence (status.KEY_GRADE); `none` is every row no key vouches for, so a row counts once
  const grades = b.key_grade || [];
  const keyCols = [{t: 'Company', f: (c) => c.ticker}, ...grades.map((g) => ({t: g.label, num: 1, f: (c) => h('span', {title: g.why}, int(c.keys[g.id]))})),
    {t: 'no key', num: 1, f: (c) => h('span', {title: 'a quote, a located table, a mapping, an explanation or an open item: nothing independent vouches for the number'}, int(c.keys.none))}, {t: 'Rows', num: 1, f: (c) => int(c.keys.rows)}];
  const keyRows = [...b.proven, {ticker: 'All', keys: b.keys}];
  const keyTable = dtable('Rows by answer key', keyCols, keyRows, {note: 'strongest key per row, left is strongest'});
  const keyWhy = h('p', {class: 'text-secondary small mt-2'}, grades.map((g, i) => [i ? ' ' : '', h('b', {class: 'text-body'}, g.label), ': ', g.why, '.']));
  const rel = await api('/api/outputs').catch(() => ({releases: []}));
  // T7: what a signature meant, from the checklist SIGNOFF.json carries; a release signed before the checklist says so
  const atSigning = (r, f, say = false) => (r.checklist ? f(r.checklist) : say ? h('span', {class: 'text-secondary'}, 'before the checklist') : h('span', {class: 'text-secondary'}, '—'));
  const releases = dtable('Releases', [{t: 'Version', k: 'version'}, {t: 'Signed', f: (r) => (r.signed_by ? [`${r.signed_by}, ${day(r.signed_at)}`, r.published === false ? h('span', {class: 'text-red'}, ', not published') : ''] : h('span', {class: 'text-secondary'}, 'not signed'))}, {t: 'Values', num: 1, f: (r) => int(r.rows.length)},
    {t: 'Open at signing', num: 1, f: (r) => atSigning(r, (c) => int(c.open), true)}, {t: 'Unmapped at signing', num: 1, f: (r) => atSigning(r, (c) => int(c.unmapped))}, {t: 'In scope', f: (r) => atSigning(r, (c) => `${int(c.scope.length)}: ${c.scope.join(', ')}`)},
    {t: 'Packet', f: (r) => (r.packet ? h('a', {href: `/packet/${r.version}.zip`}, 'zip') : '')}], [...rel.releases].reverse().slice(0, 6), {note: h('a', {href: '#release'}, 'the next release’s checklist')});
  const golden = h('details', {class: 'card mt-3'}, h('summary', {class: 'card-header py-2', style: 'cursor:pointer'}, h('h3', {class: 'card-title m-0'}, 'Golden test'), h('span', {class: 'ms-3 text-secondary small'}, g.ok == null ? 'not run yet' : `${g.ok ? 'equal' : 'differs'}, ${when(g.at)}${g.tickers ? ', ' + g.tickers.join(', ') : ''}`)),
    h('div', {class: 'card-body py-2'}, h('p', {class: 'small text-secondary'}, 'The code stages run on the frozen inputs for the proven set and must reproduce the expected tables. Any change to a parser, a rule, a loader or the taxonomy has to pass it, or change the expectation on purpose.'),
      h('pre', {class: 'raw'}, 'uv run python -m ledger golden --check\nuv run python -m ledger golden --freeze   # change the expectation on purpose, then commit with the reason'),
      g.steps ? h('div', {class: 'mt-2'}, dtable('Last run', [{t: 'Step', k: 'step'}, {t: 'Exit', num: 1, k: 'exit'}], g.steps)) : '',
      g.diffs && Object.keys(g.diffs).length ? h('div', {class: 'mt-2'}, dtable('Differences', [{t: 'Table', k: 'name'}, {t: 'Only in the run', num: 1, k: 'n_only_in_run'}, {t: 'Only in expected', num: 1, k: 'n_only_in_expected'}], Object.entries(g.diffs).map(([k, v]) => ({name: k, ...v})))) : ''));
  view.append(head, table_, legend, h('div', {class: 'mt-3'}, keyTable), keyWhy, h('div', {class: 'mt-3'}, releases), golden);
}
