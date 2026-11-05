// ── Rules: the agents first (charter, prompt history, runs per company), then every rule, guard and definition, and what is open on the proven set ──
// V15: one card per agent, nothing bordered inside it: the charter beside the score (value cells, V11), then the runs per
// company across the card's width (V10: it fits, no clipped column), the planted errors by kind and the prompt history folded
function agentCard(a) {
  const blocks = (a.charter_blocks || []).slice(1);  // the first block is the title, the card header carries it
  const first = blocks.find((b) => b.kind !== 'heading');
  const charter = blocks.length ? h('div', {class: 'charter', style: 'max-width:72ch'}, first ? h('p', {class: 'mb-2'}, first.text) : '',
    h('details', {}, h('summary', {class: 'text-secondary small', style: 'cursor:pointer'}, 'Full charter'), blocks.map((b) => (b.kind === 'heading' ? h('h4', {class: 'mt-3 mb-1'}, b.text) : h('p', {class: 'mb-2 small'}, b.text))))) : h('p', {class: 'text-secondary'}, 'No charter');
  const r = a.runs || {companies: [], total: {}};
  const runs = dtable('Runs per company', [{t: 'Company', k: 'ticker', strong: 1}, {t: 'Documents', num: 1, f: (x) => int(x.read)}, {t: 'Calls', num: 1, f: (x) => int(x.calls)}, {t: 'Input tokens', num: 1, f: (x) => int(x.input_tokens)}, {t: 'Output tokens', num: 1, f: (x) => int(x.output_tokens)}, {t: 'Time (s)', num: 1, f: (x) => int(Math.round(x.seconds))}, {t: 'Attempts', num: 1, f: (x) => int(x.attempts)}, {t: 'Failed', num: 1, f: (x) => (x.failed ? h('span', {class: 'text-danger'}, int(x.failed)) : '0')}], r.companies,
    {bare: true, foot: [`All ${int(r.companies.length)}`, int(r.total.read), int(r.total.calls), int(r.total.input_tokens), int(r.total.output_tokens), int(Math.round(r.total.seconds || 0)), int(r.total.attempts), int(r.total.failed)]});
  const sc = r.score;
  const history = dtable('', [{t: 'When', f: (x) => day(x.at)}, {t: 'By', k: 'by'}, {t: 'Change', f: (x) => h('span', {class: 'brk'}, x.change)}], a.history || [], {bare: true});
  const fold = (title, note, body) => h('details', {class: 'fold mt-3'}, h('summary', {}, h('span', {class: 'fw-semibold'}, title), note ? h('span', {class: 'text-secondary small ms-2'}, note) : ''), h('div', {class: 'mt-2'}, body));
  return h('div', {class: 'card mb-3', id: `agent-${a.id}`},
    h('div', {class: 'card-header'}, h('div', {class: 'me-4', style: 'min-width:0'}, h('h2', {class: 'card-title m-0'}, a.name), h('div', {class: 'text-secondary small agent-job'}, a.job)),
      h('div', {class: 'ms-auto text-end small flex-shrink-0'}, h('div', {}, h('span', {class: 'text-secondary'}, 'Model '), a.llm.model), h('div', {}, h('span', {class: 'text-secondary'}, 'Prompt '), a.prompt))),
    h('div', {class: 'card-body'}, h('div', {class: 'row g-4 mb-3'},
      h('div', {class: 'col-lg-5'}, h('h3', {class: 'mb-2'}, 'Charter'), charter),
      h('div', {class: 'col-lg-7'}, scoreBlock(sc))),
      runs,
      sc && sc.faults && sc.faults.by_kind ? fold('Planted errors by kind', `${int(Object.keys(sc.faults.by_kind).length)} kinds`, faultsByKind(sc.faults)) : '',
      (a.history || []).length ? fold('Prompt and model history', `${plural((a.history || []).length, 'change')} · versions ${(a.versions || []).map((v) => v.split('@').pop()).join(', ')}`, history) : ''));
}

// Wilson score interval on k of n at 95% (z = 1.96), as [low, high] fractions; null when n is 0. The same formula as
// ledger/core/stats.py wilson(), so the page can show a share's interval from the counts alone.
function wilson(k, n, z = 1.96) {
  if (!n) return null;
  const p = k / n, z2 = z * z, d = 1 + z2 / n;
  const c = (p + z2 / (2 * n)) / d, half = (z * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / d;
  return [Math.max(0, c - half), Math.min(1, c + half)];
}
const pct1 = (f) => `${(100 * f).toFixed(1)}%`;  // one decimal, unlike _shared's pct: the interval's ends need it
// " (98.6%, 95% interval 92.4–99.8%)" for {agree, of, interval?}; '' when of is 0
function shareText(tw) {
  if (!tw.of) return '';
  const iv = wilson(tw.agree, tw.of);  // always from the counts: the API's 4-dp `interval` is informational, one display path
  return ` · ${pct1(tw.agree / tw.of)} (95% CI ${(100 * iv[0]).toFixed(1)}–${pct1(iv[1])})`;
}

// the score (T49): counts with their denominators, each in its own labelled value cell (V11: no figure only inside a
// sentence); the twin's share is written with its interval (T53) so the number is never read as more exact than its n allows
function scoreBlock(sc) {
  if (!sc) return h('div', {}, h('h3', {class: 'mb-2'}, 'Score'), h('p', {class: 'text-secondary m-0'}, 'Not measured'));
  const of = (a, n) => `${int(a)} of ${int(n)}`;
  const item = (title, value, sub) => h('div', {class: 'datagrid-item'}, h('div', {class: 'datagrid-title'}, title), h('div', {class: 'datagrid-content fw-medium'}, value), sub ? h('div', {class: 'small text-secondary'}, sub) : '');
  const group = (title, ...items) => h('div', {class: 'score-group'}, h('div', {class: 'small text-secondary mb-1'}, title), h('div', {class: 'datagrid'}, items));
  const G = stateGroups(), done = sc.done || 0;  // the page groups of states.ROW
  const outputs = group(`Outputs · ${STAGE_LABEL_UI[sc.stage] || sc.stage}`, item(G.checked, int(sc.checked - done)), done ? item(G.done, int(done)) : '', item(G.explained, int(sc.explained)), item(G.open, int(sc.open)), item(G.blocked, int(sc.blocked)), item('Outputs', int(sc.outputs)));
  // the twin's share with its Wilson 95% interval (T53), computed on the page from agree / of (the same formula as the API's
  // `interval`, so the two never disagree after rounding); nothing when `of` is 0: no share, no interval
  const twin = sc.twin ? item('Matches SEC XBRL', of(sc.twin.agree, sc.twin.of), shareText(sc.twin).replace(/^ · /, '')) : item('Matches SEC XBRL', 'No SEC XBRL counterpart');
  // escaped is the number that matters most, so it is always written, zero included; with XBRL off (T67) the same trials ran
  // without xbrl_reconcile, so the gap between the two caught counts is what the catch rate owes to XBRL
  const f = sc.faults, off = f && f.xbrl_off;
  const faults = f ? [item('Caught', of(f.caught, f.planted)), item('Missed', int(f.escaped)), f.no_effect ? item('No effect', int(f.no_effect)) : '',
    off ? [item('Caught without SEC XBRL', int(off.caught)), item('Missed without SEC XBRL', int(off.escaped))] : ''] : [item('Planted errors', 'Not measured')];
  return h('div', {class: 'score'}, h('h3', {class: 'mb-2', title: sc.note || ''}, 'Score'), outputs, group('SEC XBRL', twin), group('Planted errors', faults));
}

// per fault kind (T67): planted, caught, escaped and no effect with XBRL counted, then caught and escaped with it off;
// plain counts in the kit's table, every number next to its denominator (planted), a kind with no XBRL-off row shows —
function faultsByKind(f) {
  const off = f.xbrl_off && f.xbrl_off.by_kind ? f.xbrl_off.by_kind : {};
  const kinds = Object.keys(f.by_kind);
  const cell = (n) => h('td', {class: 'num'}, int(n));
  const row = (k, c, o, cls) => h('tr', {class: cls || null}, h('td', {class: 'small'}, k.replaceAll('_', ' ')), cell(c.planted), cell(c.caught), cell(c.xbrl_only), cell(c.escaped), cell(c.no_effect),
    cell(o ? o.caught : null), cell(o ? o.escaped : null));
  const th = (t, num) => h('th', {class: num ? 'num' : null}, t);
  return h('div', {class: 'table-responsive'}, h('table', {class: 'table table-sm table-vcenter card-table'},
      h('thead', {}, h('tr', {}, th('Kind'), th('Planted', 1), th('Caught', 1), th('SEC XBRL only', 1), th('Missed', 1), th('No effect', 1), th('Caught without SEC XBRL', 1), th('Missed without SEC XBRL', 1))),
      h('tbody', {}, kinds.map((k) => row(k, f.by_kind[k], off[k]))),
      h('tfoot', {}, row('All', f, f.xbrl_off, 'fw-semibold'))));
}

async function rulesPage(view) {
  const [r, readers] = await Promise.all([api('/api/v1/rules'), api('/api/agents').catch(() => ({}))]);
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'}, h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Rules'))));
  const live = Object.values(readers).filter((a) => !a.retired);
  const agents = h('div', {class: 'mb-4'}, h('h2', {class: 'mb-3'}, `Agents · ${live.length}`), live.map(agentCard));
  const KIND = {rule: 'Rule', guard: 'Guard', definition: 'Definition', mapping: 'Mapping'};
  // V15: the rules in pages of 25, sortable (the shared table); the items to review folded per need, their count on the line
  const tbl = table([{t: 'Kind', f: (x) => KIND[x.kind] || x.kind, s: (x) => KIND[x.kind] || x.kind}, {t: 'Rule', f: (x) => h('span', {title: x.id}, x.id.replaceAll('_', ' ')), s: (x) => x.id}, {t: 'Description', sort: false, f: (x) => h('span', {class: 'small brk'}, x.what)}, {t: 'Severity', k: 'severity', f: (x) => x.severity || '—'}, {t: 'Hits', n: 1, k: 'fired', f: (x) => int(x.fired)}, {t: 'Failure type', k: 'type', f: (x) => (x.type ? `#${x.type}` : '')}], r.rules, {page: 25});
  tbl.prepend(h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, 'Rules'), h('span', {class: 'ms-2 text-secondary small'}, int(r.rules.length))));
  const open = r.open_by_need.length ? r.open_by_need.map((g) => h('details', {class: 'fold mb-2'}, h('summary', {}, h('span', {class: 'fw-semibold'}, g.needs), h('span', {class: 'text-secondary small ms-2'}, plural(g.items.length, 'item'))),
    h('div', {class: 'mt-2'}, dtable(g.needs, [{t: 'Company', k: 'ticker'}, {t: 'Stage', f: (o) => STAGE_LABEL_UI[o.stage] || o.stage}, {t: 'Item', k: 'what'}, {t: 'Detail', f: (o) => h('span', {class: 'text-secondary small brk'}, o.detail || '')}], g.items)))) : [h('div', {class: 'card'}, h('div', {class: 'card-body text-secondary'}, 'No items to review'))];
  view.append(head, agents, tbl, h('h2', {class: 'mt-4 mb-2'}, `To review · ${int(r.open)}`), ...open);
}
