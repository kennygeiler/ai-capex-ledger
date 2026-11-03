// ── Proof: the pipeline proves every number it produces, shown on the proven set first (docs/PROOF.md) ──
// what explained a stage's items, in words, for the hover: "Citation only ×30 · Restated in a later 10-K ×5"
const BY_TEXT = {'label:no_reference': 'Citation only', 'label:not_reported': 'Not reported', 'rule:restated_between_filings': 'Restated in a later 10-K', 'rule:part_year': 'Part-year amount',
  'rule:program_words': 'Program, not annual guidance', 'rule:amendment_without_statements': 'Amendment without statements'};
const byText = (by) => BY_TEXT[by] || (by.startsWith('definition:') ? 'Definition' : by.startsWith('resolution:') ? 'Decision' : by.startsWith('rule:') ? 'Rule' : 'Unverified');
function byHover(items) {
  const n = new Map();
  for (const i of items || []) { const k = byText(i.by || ''); n.set(k, (n.get(k) || 0) + 1); }
  return [...n].sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ×${v}`).join(' · ');
}
function stageCell(st) {
  const blocked = st.blocked || 0, open = st.open.length;  // open counts blocked too (docs/PROOF.md); blocked is named on its own beside it
  // the counts are the page groups of states.ROW (stateGroups(), ledger/core/states.py): Checked is Verified,
  // Corroborated and Matches company tag; Located/Done (statements located, no blocking items, a confirmation) is its own
  // count, never under Checked or Verified (F10)
  const G = stateGroups(), S = (s) => stateWord('row', s)[0], title = st.explained_items && st.explained_items.length ? byHover(st.explained_items) : G.explained;
  const done = st.done || 0;
  return h('td', {class: 'num'}, h('span', {class: S('ok') + ' fw-semibold', title: G.checked}, int(st.checked - done)), h('span', {class: 'text-secondary'}, ' · '),
    done ? [h('span', {class: S('done'), title: G.done}, int(done)), h('span', {class: 'text-secondary'}, ' · ')] : '',
    h('span', {class: S('info'), title}, int(st.explained)), h('span', {class: 'text-secondary'}, ' · '),
    open ? h('span', {class: S('bad') + ' fw-semibold', title: G.open}, int(open)) : h('span', {class: 'text-secondary', title: G.open}, '0'),
    blocked ? [h('span', {class: 'text-secondary'}, ' · '), h('span', {class: S('blocked'), title: G.blocked}, `${int(blocked)} block release`)] : '');
}
// T82: the regression test's tables and the hand check's verdicts are two lines, never one: equal tables with nothing checked is not a pass
const tablesOk = (g) => (g.tables_ok != null ? g.tables_ok : g.ok && !(g.gold && g.gold.failures && g.gold.failures.length));
const goldState = (x) => (!x ? 'not run' : x.state === 'fail' ? `${int(x.failures.length)} failing` : x.state === 'pass' ? `all ${int(x.items)} hold` : `${int(x.items - x.unverified)} of ${int(x.items)} checked`);
const goldTone = (x) => (!x ? 'text-secondary' : x.state === 'fail' ? 'text-red' : x.state === 'pass' ? 'text-green' : 'text-orange');
const KEY_WORD = {twin: 'SEC XBRL', second_source: 'Other company document', tie: 'Ties to total', later_truth: 'Later actual', second_reading: 'Later filing'};
async function proofPage(view) {
  const [b, g] = await Promise.all([api('/api/v1/proof'), api('/api/v1/golden').catch(() => ({ok: null}))]);
  const proven = b.proven.filter((c) => c.proven).length;
  // the regression test says nothing changed since the freeze, never that a number is right; the hand check sits beside it
  const FROZEN = 'Nothing changed since the freeze; not a correctness check';
  const regression = g.ok == null ? h('span', {class: 'text-secondary', title: FROZEN}, 'Tables: not compared')
    : h('span', {class: tablesOk(g) ? 'text-secondary' : 'text-red', title: FROZEN}, `${tablesOk(g) ? 'Tables unchanged' : 'Tables changed'} · ${day(g.at)}`);
  const hand = h('a', {href: '#gold', class: goldTone(g.gold), title: g.gold && g.gold.failures && g.gold.failures.length ? g.gold.failures.slice(0, 5).join('\n') : 'Hand-checked sample',
    onclick: (e) => { e.preventDefault(); const el = document.getElementById('gold'); if (el) el.scrollIntoView(); }}, `Hand check: ${goldState(g.gold)}`);
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'}, h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Proof'),
    h('div', {class: 'small'}, h('b', {}, `${proven} of ${b.proven.length} proven`))),
    h('div', {class: 'col-auto small d-flex gap-3'}, regression, hand)));
  const table_ = h('div', {class: 'card'}, h('div', {class: 'table-responsive'}, h('table', {class: 'table table-vcenter card-table'},
    h('thead', {}, h('tr', {}, h('th', {}, 'Company'), b.stages.map((s) => h('th', {class: 'num'}, s.label)), h('th', {}, ''))),
    h('tbody', {}, b.proven.map((c) => h('tr', {class: 'item', tabindex: 0, onclick: () => go('proof/' + c.ticker), onkeydown: (e) => { if (e.key === 'Enter') go('proof/' + c.ticker); }},
      h('td', {}, h('div', {}, h('a', {href: '#proof/' + c.ticker, onclick: (e) => e.stopPropagation()}, c.name), ' ', h('span', {class: 'text-secondary small'}, c.ticker)), h('div', {class: 'text-secondary small'}, INDUSTRY[c.layer] || c.layer)),
      b.stages.map((s) => stageCell(c.stages[s.id])),
      h('td', {class: 'text-nowrap'}, c.proven ? h('span', {class: 'text-green fw-medium'}, 'Proven') : h('span', {class: 'text-orange fw-medium'}, `${int(c.open)} to review`))))))));
  const legend = h('p', {class: 'small mt-2'}, [['ok', 'checked'], ['done', 'done'], ['info', 'explained'], ['bad', 'open']].map(([s, g], i) => [i ? h('span', {class: 'text-secondary'}, ' · ') : '', h('span', {class: stateWord('row', s)[0]}, '● ' + stateGroups()[g])]));
  // T56: rows by the strongest answer key that vouches for them, graded by independence (status.KEY_GRADE); `none` is every row no key vouches for, so a row counts once
  const grades = b.key_grade || [];
  const keyCols = [{t: 'Company', f: (c) => c.ticker}, ...grades.map((g) => ({t: h('span', {title: g.why}, KEY_WORD[g.id] || g.label), num: 1, f: (c) => int(c.keys[g.id])})),
    {t: 'Citation only', num: 1, f: (c) => int(c.keys.none)}, {t: 'Rows', num: 1, f: (c) => int(c.keys.rows)}];
  const keyRows = [...b.proven, {ticker: 'All', keys: b.keys}];
  const keyTable = dtable('Verification source', keyCols, keyRows, {note: 'Strongest first'});
  const rel = await api('/api/outputs').catch(() => ({releases: []}));
  // T7: what a signature meant, from the checklist SIGNOFF.json carries; a release signed before the checklist shows —
  const atSigning = (r, f) => (r.checklist ? f(r.checklist) : h('span', {class: 'text-secondary'}, '—'));
  const releases = dtable('Releases', [{t: 'Version', k: 'version'}, {t: 'Signed', f: (r) => (r.signed_by ? [`${r.signed_by}, ${day(r.signed_at)}`, r.published === false ? h('span', {class: 'text-red'}, ' · not published') : ''] : h('span', {class: 'text-secondary'}, 'Not signed'))}, {t: 'Values', num: 1, f: (r) => int(r.rows.length)},
    {t: 'To review at signing', num: 1, f: (r) => atSigning(r, (c) => int(c.open))}, {t: 'Unmapped at signing', num: 1, f: (r) => atSigning(r, (c) => int(c.unmapped))}, {t: 'Companies', f: (r) => atSigning(r, (c) => `${int(c.scope.length)}: ${c.scope.join(', ')}`)},
    {t: 'Packet', f: (r) => (r.packet ? h('a', {href: `/packet/${r.version}.zip`}, 'Download') : '')}], [...rel.releases].reverse().slice(0, 6), {note: h('a', {href: '#release'}, 'Next release')});
  const golden = h('details', {class: 'card mt-3'}, h('summary', {class: 'card-header py-2', style: 'cursor:pointer'}, h('h3', {class: 'card-title m-0'}, 'Regression test'),
      h('span', {class: 'ms-3 text-secondary small', title: FROZEN}, g.ok == null ? 'Not compared' : `${tablesOk(g) ? 'Tables unchanged' : 'Tables changed'} · ${when(g.at)}${g.gold ? ` · Hand check: ${goldState(g.gold)}` : ''}`)),
    h('div', {class: 'card-body py-2'},
      g.steps ? dtable('Steps', [{t: 'Step', k: 'step'}, {t: 'Result', num: 1, f: (x) => (x.exit === 0 ? h('span', {class: 'text-green'}, 'Pass') : h('span', {class: 'text-red'}, `Fail (${x.exit})`))}], g.steps) : '',
      g.diffs && Object.keys(g.diffs).length ? h('div', {class: 'mt-2'}, dtable('Differences', [{t: 'Table', k: 'name'}, {t: 'Added', num: 1, k: 'n_only_in_run'}, {t: 'Missing', num: 1, k: 'n_only_in_expected'}], Object.entries(g.diffs).map(([k, v]) => ({name: k, ...v})))) : ''));
  view.append(head, table_, legend, h('div', {class: 'mt-3'}, keyTable), failureTypes(), h('div', {class: 'mt-3'}, releases), golden, goldSet());
  failureTypes.draw();
  goldSet.draw();
}
// ── T82: the gold set. A hand-verified sample per proven company (gold/<TICKER>.json): golden says nothing changed, gold says
// the numbers a person checked are still right. One verdict per item, written under the signer box's name (config.PEOPLE).
const goldWord = (v) => stateWord('gold', v)[1];  // states.GOLD, read when a row renders, never at load
const GOLD_HELP = {right: 'The filing shows this number at this cell', wrong: 'The filing shows something else; note what', cant_say: 'The filing does not settle it; note why'};
const verdictTone = (v) => stateWord('gold', v)[0];
const goldNeedsMe = new Set();
document.addEventListener('input', (e) => { if (e.target.id === 'me') for (const b of goldNeedsMe) b.disabled = !(me || '').trim(); });
const goldMoney = (n) => (n == null ? 'Not reported' : usd(n));  // the app's one money format; the exact dollars in the hover
const goldGroup = (g) => stateWord('gold_group', g);  // states.GOLD_GROUP: the group's word and tone
// counts first; the error rate only once a verdict exists (n > 0), with its interval
const goldRate = (r) => {
  const counts = `${int(r.n - r.wrong)} right · ${int(r.wrong)} wrong · ${int(r.cant_say)} can’t say · ${int(r.unverified)} unchecked`;
  if (!r.n) return counts;
  const [lo, hi] = r.interval;
  return `${counts} · error rate ${(100 * r.rate).toFixed(1)}% (95% CI ${(100 * lo).toFixed(1)}–${(100 * hi).toFixed(1)}%)`;
};
function goldSet() {
  const wrap = h('div', {class: 'mt-3', id: 'gold'});
  goldSet.draw = async (ticker) => {
    goldNeedsMe.clear();  // the buttons of the last draw are gone
    let g;
    try { g = await api('/api/v1/gold' + (ticker ? `?t=${encodeURIComponent(ticker)}` : '')); } catch (e) { wrap.replaceChildren(h('p', {class: 'text-secondary small'}, 'Hand check unavailable')); return; }
    const probs = (g.problems || []).length ? h('div', {class: 'text-red small mb-2'}, h('b', {}, 'Hand-check files with errors: '), g.problems.join('; ')) : '';
    if (!g.companies.length) { wrap.replaceChildren(probs, h('p', {class: 'text-secondary small'}, 'No hand-check sample yet')); return; }
    const t = g.ticker || null;
    // the headline is the group no machine checks (gold.rates headline); the others and the overall follow, the same numbers as the API
    const byGroup = Object.fromEntries((g.groups || []).map((x) => [x.id, x.rate]));
    const groupLine = (id, strong) => h('div', {class: 'small' + (strong ? ' fw-medium' : '')}, h('span', {class: goldGroup(id)[0]}, goldGroup(id)[1]), `: ${goldRate(byGroup[id])}`);
    const head = h('div', {class: 'mb-2'}, h('h2', {class: 'h3 m-0'}, 'Hand check'),
      h('div', {class: 'text-secondary small'}, '20 items per company · random sample · Unchecked never passes'),
      h('div', {class: 'mt-1'}, g.headline && byGroup[g.headline] ? groupLine(g.headline, true) : '',
        (g.groups || []).filter((x) => x.id !== g.headline).map((x) => groupLine(x.id)),
        h('div', {class: 'small'}, h('span', {class: 'text-secondary'}, 'All'), `: ${goldRate(g.all)}`)));
    const picker = h('div', {class: 'btn-group flex-wrap mb-2', role: 'group', 'aria-label': 'Company'}, g.companies.map((c) => {
      const done = c.rate.items - c.rate.unverified;
      return h('button', {type: 'button', class: 'btn btn-sm ' + (c.ticker === t ? 'btn-primary' : 'btn-outline-secondary'), 'aria-pressed': String(c.ticker === t), title: goldRate(c.rate), onclick: () => goldSet.draw(c.ticker)},
        c.ticker, h('span', {class: 'ms-1 ' + (c.ticker === t ? '' : 'text-secondary')}, `${done}/${c.rate.items}`));
    }));
    if (!t) { wrap.replaceChildren(head, probs, picker); return; }
    const co = g.companies.find((c) => c.ticker === t);
    const claimName = (it) => [FIELDS[it.field] || it.field, it.dimension, it.period].filter(Boolean).join(' · ');
    const claim = (it) => h('div', {}, h('div', {class: 'fw-semibold'}, claimName(it)),
      h('div', {class: 'text-secondary small'}, it.kind === 'fact' ? 'Note figure' : 'Statement figure', it.untagged ? ' · Not in SEC XBRL' : it.xbrl != null ? ` · SEC XBRL ${goldMoney(it.xbrl)}` : ''));
    const value = (it) => {
      const lv = it.live, moved = lv && lv.value !== it.value;
      return h('div', {}, h('div', {class: 'money', title: it.value == null ? null : `$${int(it.value)}`}, goldMoney(it.value)),
        !lv ? h('div', {class: 'text-secondary small'}, 'Current value unavailable') : lv.gone ? h('div', {class: 'text-red small'}, 'Removed from dataset') : moved ? h('div', {class: 'text-red small'}, `Now ${goldMoney(lv.value)}`) : lv.open ? h('div', {class: stateWord('row', 'bad')[0] + ' small'}, stateWord('row', 'bad')[1]) : '');
    };
    // the cited cell, as the trail shows it: the crop (cell boxed in red; click for full size) or its state, then Open in filing
    const cited = (it) => (it.cites.length ? h('div', {}, calcBlock(it.calc), h('div', {class: 'cites'}, it.cites.map((c) => {
      const E = c.evidence;
      if (!E) return h('div', {class: 'cite-line small'}, h('span', {class: 'text-secondary'}, 'Crop unavailable'), SEC_LINK.test(c.url || '') ? [' · ', h('a', {href: safeHref(c.url), target: '_blank', rel: 'noopener noreferrer'}, 'sec.gov ↗')] : '');
      return citeCell({role: c.role, crop: {state: E.state, reason: E.reason, url: E.url}, viewer: E.viewer, link: c.url, form: E.form, filed: E.filed, row: c.row, column: (c.column || '').replaceAll(' | ', ' '), cell: c.cell_text}, claimName(it));
    }))) : h('span', {class: 'text-secondary small'}, '—'));
    const verdict = (it) => {
      const note = h('input', {type: 'text', class: 'form-control form-control-sm', placeholder: 'Note (required for Wrong / Can’t say)', value: it.note || '', 'aria-label': `Note on ${it.id}`});
      const msg = h('div', {class: 'small', role: 'status'}, it.verdict ? h('span', {class: verdictTone(it.verdict) + ' fw-medium'}, `${goldWord(it.verdict)} · ${it.by} · ${day(it.at)}`) : h('span', {class: stateWord('gold', 'unchecked')[0]}, stateWord('gold', 'unchecked')[1]));
      const btns = g.verdicts.map((v) => {
        const b = h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary' + (it.verdict === v ? ' active' : ''), 'aria-pressed': String(it.verdict === v), title: (me || '').trim() ? GOLD_HELP[v] : 'Enter a signer name', onclick: async () => {
          if (v !== 'right' && !note.value.trim()) { msg.replaceChildren(h('span', {class: 'text-red'}, 'Note required')); note.focus(); return; }
          btns.forEach((x) => { x.disabled = true; });
          try {
            const out = await api('/api/gold/verdict', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ticker: t, id: it.id, verdict: v, note: note.value, by: me})});
            Object.assign(it, out);
            await goldSet.draw(t);
          } catch (e) { msg.replaceChildren(h('span', {class: 'text-red'}, e.message)); btns.forEach((x) => { x.disabled = !(me || '').trim(); }); }
        }}, goldWord(v));
        b.disabled = !(me || '').trim(); goldNeedsMe.add(b);
        return b;
      });
      return h('div', {}, h('div', {class: 'btn-group mb-1', role: 'group', 'aria-label': `Verdict on ${it.id}`}, btns), note, msg);
    };
    // the items arrive hard first (gold.ordered); a header row opens each group with that group's numbers for this company
    const coGroups = Object.fromEntries(((co.rates || {}).groups || []).map((x) => [x.id, x.rate]));
    const rows = [];
    for (const it of g.items) {
      if (!rows.length || rows[rows.length - 1].group !== it.group) {
        const [tone, word] = goldGroup(it.group), r = coGroups[it.group];
        rows.push({group: it.group, tr: h('tr', {class: 'gold-group'}, h('th', {colspan: 4, class: 'small'}, h('span', {class: tone + ' fw-semibold'}, word), r ? h('span', {class: 'text-secondary fw-normal ms-2'}, goldRate(r)) : ''))});
      }
      rows.push({group: it.group, tr: h('tr', {class: it.live && it.live.value !== it.value ? 'table-danger' : null},
        h('td', {}, claim(it)), h('td', {class: 'num'}, value(it)), h('td', {}, cited(it)), h('td', {}, verdict(it)))});
    }
    const tbl = h('div', {class: 'card'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, `${t} · ${plural(co.rate.items, 'item')}`), h('span', {class: 'ms-auto text-secondary small'}, goldRate(co.rate))),
      h('div', {class: 'table-responsive'}, h('table', {class: 'table table-vcenter card-table trail gold'},
        h('colgroup', {}, h('col', {class: 'c-item'}), h('col', {class: 'c-value'}), h('col', {class: 'c-source'}), h('col', {class: 'c-verify'})),
        h('thead', {}, h('tr', {}, h('th', {}, 'Item'), h('th', {class: 'num'}, 'Value'), h('th', {}, 'Source'), h('th', {}, 'Check'))), h('tbody', {}, rows.map((x) => x.tr)))));
    wrap.replaceChildren(head, probs, picker, co.note ? h('p', {class: 'text-secondary small'}, co.note) : '', tbl);
  };
  return wrap;
}
// T54: the failure types as data. Two bar charts (one hue, a bar is a NUMBER OF TYPES, never instances) and the same numbers as tables,
// so the section reads without colour or without Plotly. `none` is a bar of its own: a known way to be wrong that nothing guards.
const NO_CHECK = 'No automated check';
function failureTypes() {
  const wrap = h('div', {class: 'mt-3'});  // width bounded by the page container, like the tables above
  failureTypes.draw = async () => {
    let f;
    try { f = await api('/api/v1/failures'); } catch (e) { wrap.append(h('p', {class: 'text-secondary small'}, 'Failure types unavailable')); return; }
    const total = f.total;
    const ofTotal = (n) => `${int(n)} of ${int(total)}`;
    const head = h('div', {class: 'mb-2'}, h('h2', {class: 'h3 m-0'}, 'Failure types'),
      h('div', {class: 'text-secondary small'}, `${int(total)} known failure types · bars count types, not occurrences`));
    const chart = (title, rows, key, label, aria) => {
      const plot = h('div', {class: 'plot', role: 'figure', 'aria-label': aria, style: `min-height:0;height:${28 * rows.length + 48}px`});
      const tbl = dtable(title, [{t: label, f: (r) => (key === 'check' && r[key] === 'none' ? 'No check' : r[key])},
        {t: 'Types', num: 1, f: (r) => ofTotal(r.types)}, {t: 'Share', num: 1, f: (r) => pct(r.types / total)}], rows, {foot: ['All', ofTotal(total), pct(1)]});
      return {plot, tbl, node: h('div', {class: 'col-lg-6'}, h('div', {class: 'card'}, h('div', {class: 'card-body py-2'}, h('div', {class: 'fw-semibold'}, title), plot)), h('div', {class: 'mt-2'}, tbl))};
    };
    const byClass = chart('Types per cause class', f.by_class, 'class', 'Cause class', `${total} failure types by cause class, number of types per class`);
    const byCheck = chart('Types per check', f.by_check, 'check', 'Check', `${total} failure types by the check that catches them`);
    const typeRows = [...f.types].sort((a, b) => (a.class === b.class ? a.id - b.id : (f.by_class.findIndex((x) => x.class === a.class) - f.by_class.findIndex((x) => x.class === b.class))));
    const list = h('details', {class: 'mt-2'}, h('summary', {class: 'text-secondary small', style: 'cursor:pointer'}, `All ${int(total)} types`),
      h('div', {class: 'mt-2'}, dtable('Failure types', [{t: 'Id', num: 1, k: 'id'}, {t: 'Type', k: 'name'}, {t: 'Cause class', k: 'class'}, {t: 'Origin', k: 'origin'},
        {t: 'Check', f: (r) => (r.check === 'none' ? h('span', {class: 'text-secondary'}, 'No check') : r.check)},
        {t: 'Companies seen', num: 1, f: (r) => (r.count == null ? h('span', {class: 'text-secondary'}, 'Not counted') : int(r.count))}], typeRows)));
    const why = h('p', {class: 'text-secondary small mt-2'}, `${NO_CHECK}: ${ofTotal(f.none)}`);
    wrap.append(head, h('div', {class: 'row g-3'}, byClass.node, byCheck.node), why, list);
    if (!window.Plotly) { for (const c of [byClass, byCheck]) c.plot.replaceChildren(h('p', {class: 'text-secondary small m-0'}, 'Chart unavailable')); return; }
    const draw = (c, rows, key, nameOf) => {
      const css = getComputedStyle(document.documentElement);  // read at draw time: a theme change redraws with the new ink
      const fg = css.getPropertyValue('--fg').trim(), muted = css.getPropertyValue('--muted').trim(), faint = css.getPropertyValue('--faint').trim(), bg = css.getPropertyValue('--bg').trim(), accent = css.getPropertyValue('--accent').trim();
      const names = rows.map((r) => nameOf(r[key]));
      const trace = {type: 'bar', orientation: 'h', x: rows.map((r) => r.types), y: names, text: rows.map((r) => ofTotal(r.types)), textposition: 'outside', textfont: {color: fg, size: 11}, cliponaxis: false,
        marker: {color: accent}, hovertemplate: `%{y}: %{text} types<extra></extra>`};
      const layout = {paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: {family: css.getPropertyValue('--font'), color: muted, size: 12}, margin: {l: 8, r: 56, t: 4, b: 28}, height: 28 * rows.length + 48, bargap: .45, showlegend: false,
        xaxis: {gridcolor: faint, zerolinecolor: faint, tickfont: {color: muted}, range: [0, total], tickformat: ',d', fixedrange: true, title: {text: `number of types, of ${int(total)}`, font: {color: muted, size: 11}}},
        yaxis: {type: 'category', autorange: 'reversed', automargin: true, tickfont: {color: fg}, fixedrange: true, ticksuffix: '  '},
        hoverlabel: {bgcolor: bg, bordercolor: faint, font: {color: fg, family: css.getPropertyValue('--font')}}, dragmode: false};
      return Plotly.newPlot(c.plot, [trace], layout, {displayModeBar: false, responsive: true});
    };
    // check ids as in code (period_length), the same in the bar and in the row, so a reader matches one to the other
    const both = () => Promise.all([draw(byClass, f.by_class, 'class', (x) => x), draw(byCheck, f.by_check, 'check', (x) => (x === 'none' ? 'No check' : x))]);
    await both();
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (wrap.isConnected) both(); });  // the kit's theme follows the system; redraw with the new ink
  };
  return wrap;
}
