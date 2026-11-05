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
// V6: every stage cell carries the same four parts in the same order, zeros included, and the board's sub-header names them
// (Checked · Located/Done · Unverified · To review): the counts are the page groups of states.ROW (stateGroups(),
// ledger/core/states.py): Checked is Verified, Corroborated and Matches company tag; Located/Done (statements located, no
// blocking items, a confirmation) is its own count, never under Checked or Verified (F10). Open counts blocked too
// (docs/PROOF.md); blocked is named on its own after the four, with its word. Each part has its word on hover, the cell
// all of them in its accessible name.
const STAGE_PARTS = ['checked', 'done', 'explained', 'open'];
const stageParts = (st) => { const done = st.done || 0; return {checked: st.checked - done, done, explained: st.explained, open: st.open.length}; };
function stageCell(st, label) {
  const G = stateGroups(), S = (s) => stateWord('row', s)[0], n = stageParts(st), blocked = st.blocked || 0;
  const tone = {checked: S('ok') + ' fw-semibold', done: S('done'), explained: S('info'), open: S('bad') + ' fw-semibold'};
  const title = {explained: st.explained_items && st.explained_items.length ? byHover(st.explained_items) : G.explained};
  const name = [label, ...STAGE_PARTS.map((p) => `${int(n[p])} ${G[p]}`), blocked ? `${int(blocked)} ${G.blocked}` : ''].filter(Boolean).join(', ');
  return h('td', {class: 'num stage', 'aria-label': name},
    STAGE_PARTS.map((p, i) => [i ? h('span', {class: 'text-secondary', 'aria-hidden': 'true'}, ' · ') : '', h('span', {class: (n[p] ? tone[p] : 'text-secondary') + ' part', title: title[p] || G[p], 'aria-hidden': 'true'}, int(n[p]))]),
    blocked ? [h('span', {class: 'text-secondary'}, ' · '), h('span', {class: S('blocked'), title: G.blocked}, `${int(blocked)} block release`)] : '');
}
// T82: the regression test's tables and the hand check's verdicts are two lines, never one: equal tables with nothing checked is not a pass
const tablesOk = (g) => g.tables_ok === true;  // /api/v1/golden: tables_ok covers the tables only, regression_at is that run's date (F-BF16)
const goldState = (x) => (!x ? 'not run' : x.state === 'fail' ? `${int(x.failures.length)} failing` : x.state === 'pass' ? `all ${int(x.items)} hold` : `${int(x.items - x.unverified)} of ${int(x.items)} checked`);
const goldTone = (x) => (!x ? 'text-secondary' : x.state === 'fail' ? 'text-red' : x.state === 'pass' ? 'text-green' : 'text-orange');
const KEY_WORD = {twin: 'SEC XBRL', second_source: 'Other company document', tie: 'Ties to total', later_truth: 'Later actual', second_reading: 'Later filing'};
async function proofPage(view, qs) {
  const q = parseQ(qs || '');  // ?gold=TICKER&item=ID: the Release page's Hand check Fix in, opened at that company's first unchecked item (F-BF11)
  const [b, g] = await Promise.all([api('/api/v1/proof'), api('/api/v1/golden').catch(() => ({tables_ok: null}))]);
  const proven = b.proven.filter((c) => c.proven).length;
  // the regression test says nothing changed since the freeze, never that a number is right; the hand check sits beside it
  const FROZEN = 'Nothing changed since the freeze; not a correctness check';
  const regression = g.tables_ok == null ? h('span', {class: 'text-secondary', title: FROZEN}, 'Tables: not compared')
    : h('span', {class: tablesOk(g) ? 'text-secondary' : 'text-red', title: [FROZEN, ...Object.keys(g.diffs || {}).map((k) => `Changed: ${k}`)].join('\n')}, `${tablesOk(g) ? 'Tables unchanged' : 'Tables changed'} · ${day(g.regression_at)}`);  // the one regression line (the card that repeated it is gone, report #11)
  // the hand check is read live; when the live read fails the API falls back to the last check's, and the page says so (F-BF16)
  const notLive = g.gold_live === false;
  const hand = h('a', {href: '#gold', class: notLive ? 'text-orange' : goldTone(g.gold), title: notLive ? g.gold_error || '' : g.gold && g.gold.failures && g.gold.failures.length ? g.gold.failures.slice(0, 5).join('\n') : 'Hand-checked sample',
    onclick: (e) => { e.preventDefault(); const el = document.getElementById('gold'); if (el) el.scrollIntoView(); }}, `Hand check: ${goldState(g.gold)}${notLive ? ' · Not live' : ''}`);
  // V6: the headline is the page's largest status, beside the H1
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'}, h('div', {class: 'col d-flex align-items-baseline flex-wrap', style: 'gap:.25rem 1.25rem'}, h('h1', {class: 'page-title'}, 'Proof'),
    h('span', {class: 'proof-headline'}, `${proven} of ${b.proven.length} proven`)),
    h('div', {class: 'col-auto small d-flex gap-3'}, regression, hand)));
  // the sub-header names the four parts of every stage cell, in their order and tone, above the numbers (V6)
  const parts = h('tr', {class: 'proof-legend'}, h('th', {}), h('th', {colspan: b.stages.length, class: 'text-center'},
    [['ok', 'checked'], ['done', 'done'], ['info', 'explained'], ['bad', 'open']].map(([s, g], i) => [i ? h('span', {class: 'text-secondary'}, ' · ') : '', h('span', {class: stateWord('row', s)[0] + ' text-nowrap'}, stateGroups()[g])])), h('th', {}));
  const table_ = h('div', {class: 'card'}, h('div', {class: 'table-responsive'}, h('table', {class: 'table table-vcenter card-table proof-board'},
    h('thead', {}, h('tr', {}, h('th', {}, 'Company'), b.stages.map((s) => h('th', {class: 'num'}, s.label)), h('th', {}, 'Status')), parts),
    h('tbody', {}, b.proven.map((c) => h('tr', {class: 'item', tabindex: 0, onclick: () => go('proof/' + c.ticker), onkeydown: (e) => { if (e.key === 'Enter') go('proof/' + c.ticker); }},
      h('td', {}, h('div', {class: 'text-nowrap'}, h('a', {href: '#proof/' + c.ticker, onclick: (e) => e.stopPropagation()}, c.name), ' ', h('span', {class: 'text-secondary small'}, c.ticker)), h('div', {class: 'text-secondary small text-nowrap'}, INDUSTRY[c.layer] || c.layer)),
      b.stages.map((s) => stageCell(c.stages[s.id], s.label)),
      h('td', {}, c.proven ? h('span', {class: 'text-green fw-medium'}, 'Proven') : bucketLine(c.counts))))))));
  // T56: rows by the strongest answer key that vouches for them, graded by independence (status.KEY_GRADE); `none` is every row no key vouches for, so a row counts once
  const grades = b.key_grade || [];
  const keyCols = [{t: 'Company', f: (c) => c.ticker}, ...grades.map((g) => ({t: h('span', {title: g.why}, KEY_WORD[g.id] || g.label), num: 1, f: (c) => int(c.keys[g.id])})),
    {t: 'Citation only', num: 1, f: (c) => int(c.keys.none)}, {t: 'Rows', num: 1, f: (c) => int(c.keys.rows)}];
  const keyRows = [...b.proven, {ticker: 'All', keys: b.keys}];
  // DI6: the trail carries each company's verification counts; here the cross-company table folds under the board
  const keyTable = h('details', {class: 'fold mt-3'}, h('summary', {}, h('span', {class: 'fw-semibold'}, 'Verification source'), h('span', {class: 'text-secondary small ms-2'}, 'Strongest first')),
    h('div', {class: 'mt-2'}, dtable('Verification source', keyCols, keyRows)));
  // report #11: Proof is the board, what is open and the hand check. Failure types are on Rules, releases and their
  // packets on Release, and the regression test's line is the one in the header (it was repeated in a card here)
  view.append(head, table_, goldSet(), keyTable);
  if ('gold' in q) goldSet.draw(q.gold || undefined, {focus: q.item || 'unchecked'});
  else goldSet.draw();
}
// ── T82: the gold set. A hand-verified sample per proven company (gold/<TICKER>.json): golden says nothing changed, gold says
// the numbers a person checked are still right. One verdict per item, written under the signer box's name (config.PEOPLE).
const goldWord = (v) => stateWord('gold', v)[1];  // states.GOLD, read when a row renders, never at load
const GOLD_HELP = {right: 'The filing shows this number at this cell', wrong: 'The filing shows something else; note what', cant_say: 'The filing does not settle it; note why'};
const verdictTone = (v) => stateWord('gold', v)[0];
const goldNeedsMe = new Set();
const noteShown = (it) => !!((it.note || '').trim() || it.verdict === 'wrong' || it.verdict === 'cant_say');  // V4: hidden for Right and unchecked items
document.addEventListener('input', (e) => { if (e.target.id === 'me') for (const b of goldNeedsMe) b.disabled = !(me || '').trim(); });
const goldMoney = (n) => (n == null ? 'Not reported' : usdExact(n));  // the hand check compares figures by eye: always to the dollar
// The value as the filing prints it: the cited cell's figure and its scale, when every cite shows the same figure and
// value = figure × 1, 1,000, 1,000,000 or 1,000,000,000. Otherwise null (calculated or rescaled figures show dollars only).
const GOLD_SCALE = [[1, 'dollars'], [1e3, 'thousands'], [1e6, 'millions'], [1e9, 'billions']];
const asFiled = (it) => {
  if (it.value == null || it.calc || !it.cites.length) return null;
  const texts = [...new Set(it.cites.map((c) => String(c.cell_text || '').replace(/[^0-9.]/g, '')))];
  if (texts.length !== 1 || !texts[0]) return null;
  const n = Number(texts[0]);
  if (!(n > 0)) return null;
  const hit = GOLD_SCALE.find(([k]) => Math.abs(Math.abs(it.value) - n * k) < 0.5);
  return hit ? {figure: (it.value < 0 ? '−' : '') + n.toLocaleString('en-US', {maximumFractionDigits: 3}), scale: hit[1]} : null;
};
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
  goldSet.draw = async (ticker, {focus} = {}) => {
    goldNeedsMe.clear();  // the buttons of the last draw are gone
    let g;
    try { g = await api('/api/v1/gold' + (ticker ? `?t=${encodeURIComponent(ticker)}` : '')); } catch (e) { wrap.replaceChildren(h('p', {class: 'text-secondary small'}, 'Hand check unavailable')); return; }
    const probs = (g.problems || []).length ? h('div', {class: 'text-red small mb-2'}, h('b', {}, 'Hand-check files with errors: '), g.problems.join('; ')) : '';
    if (!g.companies.length) { wrap.replaceChildren(probs, h('p', {class: 'text-secondary small'}, 'No hand-check sample yet')); return; }
    const t = g.ticker || null;
    // the headline is the group no machine checks (gold.rates headline); the others and the overall follow, the same numbers as the API
    const byGroup = Object.fromEntries((g.groups || []).map((x) => [x.id, x.rate]));
    // V6: the summary is a table, one row per check source (the headline group first), the same numbers as goldRate
    const sumRow = (label, r, strong) => h('tr', {class: strong ? 'fw-medium' : null}, h('td', {}, label), h('td', {class: 'num'}, int(r.n - r.wrong)), h('td', {class: 'num'}, int(r.wrong)),
      h('td', {class: 'num'}, int(r.cant_say)), h('td', {class: 'num'}, int(r.unverified)),
      h('td', {class: 'num'}, r.n ? [`${(100 * r.rate).toFixed(1)}%`, h('span', {class: 'text-secondary fw-normal'}, ` · 95% CI ${(100 * r.interval[0]).toFixed(1)}–${(100 * r.interval[1]).toFixed(1)}%`)] : h('span', {class: 'text-secondary'}, '—')));
    const sumRows = [g.headline && byGroup[g.headline] ? sumRow(h('span', {class: goldGroup(g.headline)[0]}, goldGroup(g.headline)[1]), byGroup[g.headline], true) : '',
      ...(g.groups || []).filter((x) => x.id !== g.headline && x.rate.items).map((x) => sumRow(h('span', {class: goldGroup(x.id)[0]}, goldGroup(x.id)[1]), x.rate)),
      sumRow('All', g.all)];
    const summary = h('div', {class: 'card mt-2', style: 'max-width:56rem'}, h('div', {class: 'table-responsive'}, h('table', {class: 'table table-sm card-table gold-summary'},
      h('thead', {}, h('tr', {}, h('th', {}, 'Check source'), h('th', {class: 'num'}, 'Right'), h('th', {class: 'num'}, 'Wrong'), h('th', {class: 'num'}, 'Can’t say'), h('th', {class: 'num'}, 'Unchecked'), h('th', {class: 'num'}, 'Error rate'))),
      h('tbody', {}, sumRows))));
    const head = h('div', {class: 'mb-2'}, h('h2', {class: 'h3 m-0'}, 'Hand check'),
      h('div', {class: 'text-secondary small'}, '20 items per company · random sample · Unchecked never passes'), summary,
      g.groups_live === false ? h('div', {class: 'small text-orange mt-1'}, 'Groups as drawn · live tables unavailable') : '');
    const picker = h('div', {class: 'btn-group seg mb-2', role: 'group', 'aria-label': 'Company'}, g.companies.map((c) => {
      const done = c.rate.items - c.rate.unverified;
      return h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary' + (c.ticker === t ? ' active' : ''), 'aria-pressed': String(c.ticker === t), title: goldRate(c.rate), onclick: () => goldSet.draw(c.ticker)},
        c.ticker, h('span', {class: 'ms-1 text-secondary'}, `${done}/${c.rate.items}`));
    }));
    if (!t) { wrap.replaceChildren(head, probs, picker); fitTables(wrap); if (focus) wrap.scrollIntoView(); return; }
    const co = g.companies.find((c) => c.ticker === t);
    const claimName = (it) => [FIELDS[it.field] || it.field, it.dimension, it.period].filter(Boolean).join(' · ');
    const claim = (it) => h('div', {}, h('div', {class: 'fw-semibold'}, claimName(it)),
      h('div', {class: 'text-secondary small'}, it.kind === 'fact' ? 'Note figure' : 'Statement figure', it.untagged ? ' · Not in SEC XBRL' : it.xbrl != null ? ` · SEC XBRL ${goldMoney(it.xbrl)}` : ''),
      it.group_note ? h('div', {class: 'small text-orange'}, it.group_note) : '', restatedLine(it.restatement, true));
    const value = (it) => {
      const lv = it.live, moved = lv && lv.value !== it.value;
      const f = asFiled(it);
      return h('div', {}, h('div', {class: 'money'}, f ? f.figure : goldMoney(it.value)),
        f ? [h('div', {class: 'text-secondary small'}, `In ${f.scale}`), h('div', {class: 'text-secondary small money gold-exact'}, goldMoney(it.value))] : '',
        !lv ? h('div', {class: 'text-secondary small'}, 'Current value unavailable') : lv.gone ? h('div', {class: 'text-red small'}, 'Removed from dataset') : moved ? h('div', {class: 'text-red small'}, `Now ${goldMoney(lv.value)}`) : lv.open ? h('div', {class: stateWord('row', 'bad')[0] + ' small'}, stateWord('row', 'bad')[1]) : '');
    };
    // the cited cell, as the trail shows it: the crop (cell boxed in red; click for full size) or its state, then Open in filing
    const cited = (it) => (it.cites.length ? h('div', {}, calcBlock(it.calc), h('div', {class: 'cites'}, it.cites.map((c) => {
      const E = c.evidence;
      if (!E) return h('div', {class: 'cite-line small'}, h('span', {class: 'text-secondary'}, 'Crop unavailable'), SEC_LINK.test(c.url || '') ? [' · ', h('a', {href: safeHref(c.url), target: '_blank', rel: 'noopener noreferrer'}, 'sec.gov ↗')] : '');
      return citeCell({role: c.role, mark: c.mark, crop: {state: E.state, reason: E.reason, url: E.url}, viewer: E.viewer, link: c.url, form: E.form, filed: E.filed, row: c.row, column: (c.column || '').replaceAll(' | ', ' '), cell: c.cell_text}, claimName(it));
    }))) : h('span', {class: 'text-secondary small'}, '—'));
    const verdict = (it) => {
      // V4: the note box shows only once it is needed: a Wrong or Can't say verdict, or a note already written
      const note = h('input', {type: 'text', class: 'form-control form-control-sm', placeholder: 'Note (required for Wrong / Can’t say)', value: it.note || '', 'aria-label': `Note on ${it.id}`, hidden: !noteShown(it)});
      const msg = h('div', {class: 'small', role: 'status'}, it.verdict ? h('span', {class: verdictTone(it.verdict) + ' fw-medium'}, `${goldWord(it.verdict)} · ${it.by} · ${day(it.at)}`) : h('span', {class: stateWord('gold', 'unchecked')[0]}, stateWord('gold', 'unchecked')[1]));
      const btns = g.verdicts.map((v) => {
        const b = h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary' + (it.verdict === v ? ' active' : ''), 'aria-pressed': String(it.verdict === v), title: (me || '').trim() ? GOLD_HELP[v] : 'Enter a signer name', onclick: async () => {
          if (v !== 'right' && !note.value.trim()) { note.hidden = false; msg.replaceChildren(h('span', {class: 'text-red'}, 'Note required')); note.focus(); return; }
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
      return h('div', {}, writes(h('div', {class: 'btn-group seg mb-1', role: 'group', 'aria-label': `Verdict on ${it.id}`}, btns)), writes(note), msg);
    };
    // the items arrive hard first (gold.ordered); a header row opens each group with that group's numbers for this company
    const coGroups = Object.fromEntries(((co.rates || {}).groups || []).map((x) => [x.id, x.rate]));
    const rows = [];
    for (const it of g.items) {
      if (!rows.length || rows[rows.length - 1].group !== it.group) {
        const [tone, word] = goldGroup(it.group), r = coGroups[it.group];
        rows.push({group: it.group, tr: h('tr', {class: 'gold-group'}, h('th', {colspan: 4, class: 'small'}, h('span', {class: tone + ' fw-semibold'}, word), r ? h('span', {class: 'text-secondary fw-normal ms-2'}, goldRate(r)) : ''))});
      }
      rows.push({group: it.group, tr: h('tr', {class: it.live && it.live.value !== it.value ? 'table-danger' : null, 'data-item': it.id, 'data-unchecked': it.verdict ? null : '1'},
        h('td', {}, claim(it)), h('td', {class: 'num'}, value(it)), h('td', {}, cited(it)), h('td', {}, verdict(it)))});
    }
    const tbl = h('div', {class: 'card'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, `${t} · ${plural(co.rate.items, 'item')}`), h('span', {class: 'ms-auto text-secondary small'}, goldRate(co.rate))),
      h('div', {class: 'table-responsive'}, h('table', {class: 'table table-vcenter card-table trail gold'},
        h('colgroup', {}, h('col', {class: 'c-item'}), h('col', {class: 'c-value'}), h('col', {class: 'c-source'}), h('col', {class: 'c-verify'})),
        h('thead', {}, h('tr', {}, h('th', {}, 'Item'), h('th', {class: 'num'}, 'Value'), h('th', {}, 'Source'), h('th', {}, 'Check'))), h('tbody', {}, rows.map((x) => x.tr)))));
    wrap.replaceChildren(head, probs, picker, co.note ? h('p', {class: 'text-secondary small'}, co.note) : '', tbl);
    fitTables(wrap);  // drawn after the router's skin(): its wrappers get .fit or .wide here, or the sticky header is dead
    if (focus) {  // the item asked for, else the company's first unchecked item, else the table
      const rowsEl = [...tbl.querySelectorAll('tr[data-item]')];
      const el = rowsEl.find((r) => r.dataset.item === focus) || rowsEl.find((r) => r.dataset.unchecked) || tbl;
      el.classList.add('table-active');
      el.scrollIntoView({block: 'center'});
    }
  };
  return wrap;
}
