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
// T82: golden's tables and the gold verdicts are two lines, never one: equal tables with nothing verified is not a gold pass
const tablesOk = (g) => (g.tables_ok != null ? g.tables_ok : g.ok && !(g.gold && g.gold.failures && g.gold.failures.length));
const goldState = (x) => (!x ? 'not run' : x.state === 'fail' ? `${int(x.failures.length)} failing` : x.state === 'pass' ? `pass, ${int(x.checked)} verdicts hold` : `unverified ${int(x.unverified)} of ${int(x.items)}`);
const goldBadge = (x) => h('a', {href: '#gold', class: 'badge ' + (!x ? 'bg-secondary-lt' : x.state === 'fail' ? 'bg-red-lt' : x.state === 'pass' ? 'bg-green-lt' : 'bg-yellow-lt'), title: x && x.failures && x.failures.length ? x.failures.slice(0, 5).join('\n') : 'the gold set: a person’s verdicts checked against the tables golden produced',
  onclick: (e) => { e.preventDefault(); const el = document.getElementById('gold'); if (el) el.scrollIntoView(); }}, `gold: ${goldState(x)}`);
async function proofPage(view) {
  const [b, g] = await Promise.all([api('/api/v1/proof'), api('/api/v1/golden').catch(() => ({ok: null}))]);
  const proven = b.proven.filter((c) => c.proven).length;
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'}, h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Proof'),
    h('div', {class: 'text-secondary small'}, h('b', {class: 'text-body'}, `${proven} of ${b.proven.length}`), ' proven. Every number is ', h('span', {class: 'text-green'}, 'checked'), ' against something independent, ', h('span', {class: 'text-azure'}, 'explained'), ' by a rule or a definition on file, or ', h('span', {class: 'text-red'}, 'open'), '. Proven means nothing open at any stage.')),
    h('div', {class: 'col-auto'}, g.ok == null ? h('span', {class: 'badge bg-secondary-lt'}, 'golden: not run') : [h('span', {class: 'badge ' + (tablesOk(g) ? 'bg-green-lt' : 'bg-red-lt')}, tablesOk(g) ? `golden: equal, ${day(g.at)}` : `golden: differs, ${day(g.at)}`), ' ', goldBadge(g.gold)])));
  const table_ = h('div', {class: 'card'}, h('div', {class: 'table-responsive'}, h('table', {class: 'table table-vcenter card-table'},
    h('thead', {}, h('tr', {}, h('th', {}, 'Company'), b.stages.map((s) => h('th', {class: 'num'}, s.label)), h('th', {}, ''))),
    h('tbody', {}, b.proven.map((c) => h('tr', {class: 'item', tabindex: 0, onclick: () => go('proof/' + c.ticker), onkeydown: (e) => { if (e.key === 'Enter') go('proof/' + c.ticker); }},
      h('td', {}, h('div', {}, h('a', {href: '#proof/' + c.ticker, onclick: (e) => e.stopPropagation()}, c.name), ' ', h('span', {class: 'text-secondary small'}, c.ticker)), h('div', {class: 'text-secondary small'}, INDUSTRY[c.layer] || c.layer)),
      b.stages.map((s) => stageCell(c.stages[s.id])),
      h('td', {}, c.proven ? h('span', {class: 'badge bg-green-lt'}, 'proven') : h('span', {class: 'badge bg-red-lt'}, `${int(c.open)} open`))))))));
  const legend = h('p', {class: 'text-secondary small mt-2'}, 'Each cell: checked · explained · open, and blocked when any. Hover an explained count for what explained it. Click a company for its trail; open items say what rule or definition is missing.');
  // T56: rows by the strongest answer key that vouches for them, graded by independence (status.KEY_GRADE); `none` is every row no key vouches for, so a row counts once
  const grades = b.key_grade || [];
  const NO_KEY = 'a quote, a located table, a mapping, an explanation or an open item: nothing independent vouches for the number';
  const keyCols = [{t: 'Company', f: (c) => c.ticker}, ...grades.map((g) => ({t: g.label, num: 1, f: (c) => h('span', {title: g.why}, int(c.keys[g.id]))})),
    {t: 'no key', num: 1, f: (c) => h('span', {title: NO_KEY}, int(c.keys.none))}, {t: 'Rows', num: 1, f: (c) => int(c.keys.rows)}];
  const keyRows = [...b.proven, {ticker: 'All', keys: b.keys}];
  const keyTable = dtable('Rows by answer key', keyCols, keyRows, {note: 'strongest key per row, left is strongest'});
  const keyWhy = h('p', {class: 'text-secondary small mt-2'}, grades.map((g, i) => [i ? ' ' : '', h('b', {class: 'text-body'}, g.label), ': ', g.why, '.']), ' ', h('b', {class: 'text-body'}, 'no key'), ': ', NO_KEY, '.');
  const rel = await api('/api/outputs').catch(() => ({releases: []}));
  // T7: what a signature meant, from the checklist SIGNOFF.json carries; a release signed before the checklist says so
  const atSigning = (r, f, say = false) => (r.checklist ? f(r.checklist) : say ? h('span', {class: 'text-secondary'}, 'before the checklist') : h('span', {class: 'text-secondary'}, '—'));
  const releases = dtable('Releases', [{t: 'Version', k: 'version'}, {t: 'Signed', f: (r) => (r.signed_by ? [`${r.signed_by}, ${day(r.signed_at)}`, r.published === false ? h('span', {class: 'text-red'}, ', not published') : ''] : h('span', {class: 'text-secondary'}, 'not signed'))}, {t: 'Values', num: 1, f: (r) => int(r.rows.length)},
    {t: 'Open at signing', num: 1, f: (r) => atSigning(r, (c) => int(c.open), true)}, {t: 'No entry at signing', num: 1, f: (r) => atSigning(r, (c) => int(c.unmapped))}, {t: 'In scope', f: (r) => atSigning(r, (c) => `${int(c.scope.length)}: ${c.scope.join(', ')}`)},
    {t: 'Packet', f: (r) => (r.packet ? h('a', {href: `/packet/${r.version}.zip`}, 'zip') : '')}], [...rel.releases].reverse().slice(0, 6), {note: h('a', {href: '#release'}, 'the next release’s checklist')});
  const golden = h('details', {class: 'card mt-3'}, h('summary', {class: 'card-header py-2', style: 'cursor:pointer'}, h('h3', {class: 'card-title m-0'}, 'Golden test'), h('span', {class: 'ms-3 text-secondary small'}, g.ok == null ? 'not run yet' : `tables ${tablesOk(g) ? 'equal' : 'differ'}, ${when(g.at)}${g.tickers ? ', ' + g.tickers.join(', ') : ''}${g.gold ? `; gold ${goldState(g.gold)}` : ''}`)),
    h('div', {class: 'card-body py-2'}, h('p', {class: 'small text-secondary'}, 'The code stages run on the frozen inputs for the proven set and must reproduce the expected tables. Any change to a parser, a rule, a loader or the taxonomy has to pass it, or change the expectation on purpose.'),
      h('pre', {class: 'raw'}, 'uv run python -m ledger golden --check\nuv run python -m ledger golden --freeze   # change the expectation on purpose, then commit with the reason'),
      g.steps ? h('div', {class: 'mt-2'}, dtable('Last run', [{t: 'Step', k: 'step'}, {t: 'Exit', num: 1, k: 'exit'}], g.steps)) : '',
      g.diffs && Object.keys(g.diffs).length ? h('div', {class: 'mt-2'}, dtable('Differences', [{t: 'Table', k: 'name'}, {t: 'Only in the run', num: 1, k: 'n_only_in_run'}, {t: 'Only in expected', num: 1, k: 'n_only_in_expected'}], Object.entries(g.diffs).map(([k, v]) => ({name: k, ...v})))) : ''));
  view.append(head, table_, legend, h('div', {class: 'mt-3'}, keyTable), keyWhy, failureTypes(), h('div', {class: 'mt-3'}, releases), golden, goldSet());
  failureTypes.draw();
  goldSet.draw();
}
// ── T82: the gold set. A hand-verified sample per proven company (gold/<TICKER>.json): golden says nothing changed, gold says
// the numbers a person checked are still right. One verdict per item, written under the signer box's name (config.PEOPLE).
const GOLD_WORD = {right: 'Right', wrong: 'Wrong', cant_say: 'Can’t say'};
const GOLD_HELP = {right: 'the filing shows this number at this cell, for this field and year', wrong: 'the filing shows something else, or this is the wrong cell; say what in the note', cant_say: 'the filing does not settle it; say why in the note'};
const GOLD_BADGE = {right: 'bg-green-lt', wrong: 'bg-red-lt', cant_say: 'bg-secondary-lt'};
const goldNeedsMe = new Set();
document.addEventListener('input', (e) => { if (e.target.id === 'me') for (const b of goldNeedsMe) b.disabled = !(me || '').trim(); });
const goldUsd = (n) => (n == null ? 'blank' : (n < 0 ? '−$' : '$') + int(Math.abs(n)));  // the exact figure, so it can be read against the cell (in thousands or millions)
const goldRate = (r) => {
  if (!r.n) return `no verdicts yet, ${int(r.unverified)} of ${int(r.items)} unverified`;
  const [lo, hi] = r.interval;
  return `${int(r.wrong)} wrong of ${int(r.n)} (${(100 * r.rate).toFixed(1)}%, 95% interval ${(100 * lo).toFixed(1)}–${(100 * hi).toFixed(1)}%), ${int(r.cant_say)} can’t say, ${int(r.unverified)} unverified`;
};
function goldSet() {
  const wrap = h('div', {class: 'mt-3', id: 'gold'});
  goldSet.draw = async (ticker) => {
    goldNeedsMe.clear();  // the buttons of the last draw are gone
    let g;
    try { g = await api('/api/v1/gold' + (ticker ? `?t=${encodeURIComponent(ticker)}` : '')); } catch (e) { wrap.replaceChildren(h('p', {class: 'text-secondary small'}, `Gold set: ${e.message}`)); return; }
    const probs = (g.problems || []).length ? h('div', {class: 'text-red small mb-2'}, h('b', {}, 'Gold files with problems: '), g.problems.join('; ')) : '';
    if (!g.companies.length) { wrap.replaceChildren(probs, h('p', {class: 'text-secondary small'}, 'Gold set: no gold/ files yet. ', h('code', {}, 'uv run python -m ledger gold --draw'))); return; }
    const t = g.ticker || null;
    const head = h('div', {class: 'mb-2'}, h('h2', {class: 'h3 m-0'}, 'Gold set'),
      h('div', {class: 'text-secondary small'}, 'About 10 values and 10 facts per company, drawn at random with the release version in the seed, untagged facts (no XBRL twin) oversampled. Open the filing at the row, compare, and give a verdict under your name. ',
        h('code', {}, 'ledger golden --check'), ' fails when a “right” number changes, a “wrong” one still ships or changes, or a row is gone; items with no verdict show as unverified, never as a pass.'),
      h('div', {class: 'small mt-1'}, h('b', {}, 'Error rate, all companies: '), goldRate(g.all), g.all.untagged.n ? `; untagged facts ${int(g.all.untagged.wrong)} wrong of ${int(g.all.untagged.n)}` : ''));
    const picker = h('div', {class: 'btn-group flex-wrap mb-2', role: 'group', 'aria-label': 'Company'}, g.companies.map((c) => {
      const done = c.rate.items - c.rate.unverified;
      return h('button', {type: 'button', class: 'btn btn-sm ' + (c.ticker === t ? 'btn-primary' : 'btn-outline-secondary'), 'aria-pressed': String(c.ticker === t), title: goldRate(c.rate) + `; drawn for ${c.release}`, onclick: () => goldSet.draw(c.ticker)},
        c.ticker, h('span', {class: 'ms-1 ' + (c.ticker === t ? '' : 'text-secondary')}, `${done}/${c.rate.items}`));
    }));
    if (!t) { wrap.replaceChildren(head, probs, picker, h('p', {class: 'text-secondary small'}, 'Pick a company to see its items.')); return; }
    const co = g.companies.find((c) => c.ticker === t);
    const claim = (it) => h('div', {}, h('div', {class: 'fw-semibold'}, `${FIELDS[it.field] || it.field}${it.dimension ? ': ' + it.dimension : ''}`),
      h('div', {class: 'text-secondary small'}, it.period, ' · ', it.kind, it.untagged ? [' · ', h('span', {class: 'text-orange', title: 'no XBRL counterpart: nothing independent vouches for this number'}, 'untagged')] : it.xbrl != null ? ` · XBRL ${goldUsd(it.xbrl)}` : ''));
    const value = (it) => {
      const lv = it.live, moved = lv && lv.value !== it.value;
      return h('div', {}, h('div', {class: 'num text-nowrap'}, goldUsd(it.value)),
        !lv ? h('div', {class: 'text-secondary small'}, 'live: database busy') : lv.gone ? h('div', {class: 'text-red small'}, 'live: row gone') : moved ? h('div', {class: 'text-red small'}, `live now ${goldUsd(lv.value)}`) : lv.open ? h('div', {class: 'text-yellow small'}, 'live: open') : '');
    };
    const cited = (it) => h('div', {}, it.cites.length ? it.cites.map((c) => h('div', {class: 'small'},
      h('b', {}, c.cell_text || '—'), ` in “${c.row || '?'}”, “${(c.column || '?').replaceAll(' | ', ' ')}”`,
      h('div', {class: 'text-secondary'}, `table ${c.table || '?'}, ${c.accession}`, ' · ',
        c.url ? h('a', {href: c.url, target: '_blank', rel: 'noopener'}, 'open the filing at this row') : 'no link',
        c.img ? [' · ', h('a', {href: c.img, target: '_blank', rel: 'noopener', title: c.rendered_match ? 'the rendered 10-K shows the cited text here' : 'the rendered re-read did not confirm this cell'}, 'screenshot')] : ''))) : h('span', {class: 'text-secondary small'}, 'no citation'));
    const verdict = (it) => {
      const note = h('input', {type: 'text', class: 'form-control form-control-sm', placeholder: 'note (needed for wrong or can’t say)', value: it.note || '', 'aria-label': `Note on ${it.id}`});
      const msg = h('div', {class: 'small', role: 'status'}, it.verdict ? h('span', {class: 'badge ' + GOLD_BADGE[it.verdict]}, `${GOLD_WORD[it.verdict]}, ${it.by}, ${day(it.at)}`) : h('span', {class: 'text-secondary'}, 'no verdict'));
      const btns = g.verdicts.map((v) => {
        const b = h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary' + (it.verdict === v ? ' active' : ''), 'aria-pressed': String(it.verdict === v), title: (me || '').trim() ? GOLD_HELP[v] : 'type your name in the signer box first', onclick: async () => {
          if (v !== 'right' && !note.value.trim()) { msg.replaceChildren(h('span', {class: 'text-red'}, `Say what the filing shows, then press ${GOLD_WORD[v]}.`)); note.focus(); return; }
          btns.forEach((x) => { x.disabled = true; });
          try {
            const out = await api('/api/gold/verdict', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ticker: t, id: it.id, verdict: v, note: note.value, by: me})});
            Object.assign(it, out);
            await goldSet.draw(t);
          } catch (e) { msg.replaceChildren(h('span', {class: 'text-red'}, e.message)); btns.forEach((x) => { x.disabled = !(me || '').trim(); }); }
        }}, GOLD_WORD[v]);
        b.disabled = !(me || '').trim(); goldNeedsMe.add(b);
        return b;
      });
      return h('div', {style: 'min-width:16rem'}, h('div', {class: 'btn-group mb-1', role: 'group', 'aria-label': `Verdict on ${it.id}`}, btns), note, msg);
    };
    const tbl = dtable(`${t}: ${int(co.rate.items)} items, drawn for ${co.release}`, [{t: 'Claim', f: claim}, {t: 'Value', num: 1, f: value}, {t: 'Cited cell', f: cited}, {t: 'Verdict', f: verdict}],
      g.items.map((it) => ({...it, _cls: it.live && it.live.value !== it.value ? 'table-danger' : null})), {note: goldRate(co.rate)});
    wrap.replaceChildren(head, probs, picker, co.note ? h('p', {class: 'text-secondary small'}, co.note) : '', tbl);
  };
  return wrap;
}
// T54: the failure types as data. Two bar charts (one hue, a bar is a NUMBER OF TYPES, never instances) and the same numbers as tables,
// so the section reads without colour or without Plotly. `none` is a bar of its own: a known way to be wrong that nothing guards.
const NO_CHECK = 'no check: a known way to be wrong that nothing guards';
function failureTypes() {
  const wrap = h('div', {class: 'mt-3'});  // width bounded by the page container, like the tables above
  failureTypes.draw = async () => {
    let f;
    try { f = await api('/api/v1/failures'); } catch (e) { wrap.append(h('p', {class: 'text-secondary small'}, `Failure types: ${e.message}`)); return; }
    const total = f.total;
    const ofTotal = (n) => `${int(n)} of ${int(total)}`;
    const head = h('div', {class: 'mb-2'}, h('h2', {class: 'h3 m-0'}, 'Failure types'),
      h('div', {class: 'text-secondary small'}, `${int(total)} failure types from docs/INGESTION.md, coded in taxonomy/failures.yaml; bar = number of types, not how often each was seen.`));
    const chart = (title, rows, key, label, aria) => {
      const plot = h('div', {class: 'plot', role: 'figure', 'aria-label': aria, style: `min-height:0;height:${28 * rows.length + 48}px`});
      const tbl = dtable(title, [{t: label, f: (r) => (key === 'check' && r[key] === 'none' ? h('span', {title: NO_CHECK}, 'none (no check)') : key === 'check' ? h('code', {}, r[key]) : r[key])},
        {t: 'Types', num: 1, f: (r) => ofTotal(r.types)}, {t: 'Share', num: 1, f: (r) => pct(r.types / total)}], rows, {foot: ['All', ofTotal(total), pct(1)]});
      return {plot, tbl, node: h('div', {class: 'col-lg-6'}, h('div', {class: 'card'}, h('div', {class: 'card-body py-2'}, h('div', {class: 'fw-semibold'}, title), plot)), h('div', {class: 'mt-2'}, tbl))};
    };
    const byClass = chart('Types per cause class', f.by_class, 'class', 'Cause class', `${total} failure types by cause class, number of types per class`);
    const byCheck = chart('What catches them: types per check', f.by_check, 'check', 'Check', `${total} failure types by the check that catches them; none is its own bar`);
    const typeRows = [...f.types].sort((a, b) => (a.class === b.class ? a.id - b.id : (f.by_class.findIndex((x) => x.class === a.class) - f.by_class.findIndex((x) => x.class === b.class))));
    const list = h('details', {class: 'mt-2'}, h('summary', {class: 'text-secondary small', style: 'cursor:pointer'}, `The ${int(total)} types, by cause class`),
      h('div', {class: 'mt-2'}, dtable('Failure types', [{t: 'Id', num: 1, k: 'id'}, {t: 'Type', k: 'name'}, {t: 'Cause class', k: 'class'}, {t: 'Origin', k: 'origin'},
        {t: 'Check', f: (r) => (r.check === 'none' ? h('span', {class: 'text-secondary', title: NO_CHECK}, 'none') : h('code', {}, r.check))},
        {t: 'Companies seen', num: 1, f: (r) => (r.count == null ? h('span', {class: 'text-secondary', title: 'count seen is null in taxonomy/failures.yaml: not counted, not inferred'}, 'not counted') : int(r.count))}], typeRows, {note: 'count seen = companies named in INGESTION, as coded; null stays null'})));
    const why = h('p', {class: 'text-secondary small mt-2'}, h('b', {class: 'text-body'}, 'none'), `: ${NO_CHECK}. `, `${ofTotal(f.none)} types have no check in code today: a contract, the evidence re-read, a count or an eye caught them. Each is a finding; the list says which.`);
    wrap.append(head, h('div', {class: 'row g-3'}, byClass.node, byCheck.node), why, list);
    if (!window.Plotly) { for (const c of [byClass, byCheck]) c.plot.replaceChildren(h('p', {class: 'text-secondary small m-0'}, 'The chart library did not load (offline?). The numbers are in the table.')); return; }
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
    const both = () => Promise.all([draw(byClass, f.by_class, 'class', (x) => x), draw(byCheck, f.by_check, 'check', (x) => (x === 'none' ? 'none (no check)' : x))]);
    await both();
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (wrap.isConnected) both(); });  // the kit's theme follows the system; redraw with the new ink
  };
  return wrap;
}
