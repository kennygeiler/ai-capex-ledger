// ── Rules: the agents first (charter, prompt history, runs per company), then every rule, guard and definition, and what is open on the proven set ──
function agentCard(a) {
  const blocks = (a.charter_blocks || []).slice(1);  // the first block is the title, the card header carries it
  const charter = h('div', {class: 'charter', style: 'max-width:72ch'}, blocks.length ? blocks.map((b) => (b.kind === 'heading' ? h('h4', {class: 'mt-3 mb-1'}, b.text) : h('p', {class: 'mb-2'}, b.text))) : h('p', {class: 'text-secondary'}, `No charter on file at ${a.charter || `agents/charters/${a.id}.md`}.`));
  const r = a.runs || {companies: [], total: {}};
  const runs = dtable(`Runs per company`, [{t: 'Company', k: 'ticker', strong: 1}, {t: 'Read', num: 1, f: (x) => int(x.read)}, {t: 'Calls', num: 1, f: (x) => int(x.calls)}, {t: 'In tokens', num: 1, f: (x) => int(x.input_tokens)}, {t: 'Out tokens', num: 1, f: (x) => int(x.output_tokens)}, {t: 'Seconds', num: 1, f: (x) => int(Math.round(x.seconds))}, {t: 'Attempts', num: 1, f: (x) => int(x.attempts)}, {t: 'Failed', num: 1, f: (x) => (x.failed ? h('span', {class: 'text-danger'}, int(x.failed)) : '0')}], r.companies,
    {foot: ['All six', int(r.total.read), int(r.total.calls), int(r.total.input_tokens), int(r.total.output_tokens), int(Math.round(r.total.seconds || 0)), int(r.total.attempts), int(r.total.failed)], note: r.subject ? `one ${r.subject} per row of the runs table` : ''});
  const score = scoreBlock(r.score);
  const history = dtable('Prompt and model history', [{t: 'When', f: (x) => day(x.at)}, {t: 'By', k: 'by'}, {t: 'Change', f: (x) => h('span', {class: 'brk'}, x.change)}], a.history || [], {note: `on file: ${(a.versions || []).join(', ')}`});
  return h('div', {class: 'card mb-3', id: `agent-${a.id}`},
    h('div', {class: 'card-header'}, h('div', {class: 'me-4', style: 'min-width:0'}, h('h2', {class: 'card-title m-0'}, a.name), h('div', {class: 'text-secondary small', style: 'white-space:normal'}, a.job)),
      h('div', {class: 'ms-auto text-end small flex-shrink-0'}, h('div', {}, 'model ', h('span', {class: 'font-monospace'}, a.llm.model)), h('div', {}, 'prompt in use ', h('span', {class: 'font-monospace'}, a.prompt)), h('div', {class: 'text-secondary'}, `step ${r.step || '—'} · ${a.llm.runs_on}`))),
    h('div', {class: 'card-body'}, h('div', {class: 'row g-4'},
      h('div', {class: 'col-lg-6'}, h('h3', {class: 'mb-2'}, 'Charter'), h('div', {class: 'text-secondary small mb-2'}, `${a.charter || `agents/charters/${a.id}.md`}, written from the code`), charter),
      h('div', {class: 'col-lg-6'}, score, runs, r.note ? h('div', {class: 'text-secondary small mt-2 mb-3'}, r.note) : '', h('div', {class: 'mt-3'}, history)))));
}

// Wilson score interval on k of n at 95% (z = 1.96), as [low, high] fractions; null when n is 0. The same formula as
// ledger/stats.py wilson(), so the page can show a share's interval from the counts alone.
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
  return ` (${pct1(tw.agree / tw.of)}, 95% interval ${(100 * iv[0]).toFixed(1)}–${pct1(iv[1])})`;
}

// the score (T49): counts with their denominators, in the kit's datagrid; the shares are the reader's to compute,
// but the twin's share is written with its interval (T53) so the number is never read as more exact than its n allows
function scoreBlock(sc) {
  if (!sc) return '';
  const of = (a, n) => `${int(a)} of ${int(n)}`;
  const n = sc.outputs;
  const states = [`checked ${of(sc.checked, n)}`, `explained ${of(sc.explained, n)}`, `open ${of(sc.open, n)}`, `blocked ${of(sc.blocked, n)}`].join(' · ');
  // the twin's share with its Wilson 95% interval (T53), in text, computed on the page from agree / of (the same formula
  // as the API's `interval`, so the two never disagree after rounding); nothing when `of` is 0: no share, no interval
  const twin = sc.twin ? `agrees with the twin ${of(sc.twin.agree, sc.twin.of)}${shareText(sc.twin)}` : 'no twin for this reader';
  // escaped is the number that matters most, so it is always written, zero included; with XBRL off (T67) the same
  // trials ran without xbrl_reconcile, so the gap between the two caught counts is what the catch rate owes to XBRL
  const f = sc.faults, off = f && f.xbrl_off;
  const faults = f ? `caught ${of(f.caught, f.planted)} planted faults · ${int(f.escaped)} escaped` + (f.no_effect ? ` · ${int(f.no_effect)} reached no released value` : '')
    + (off ? ` · with XBRL off: ${of(off.caught, off.planted)} caught, ${int(off.escaped)} escaped` : '')
    : (sc.faults_note || 'not measured');
  const item = (title, text) => h('div', {class: 'datagrid-item'}, h('div', {class: 'datagrid-title'}, title), h('div', {class: 'datagrid-content'}, text));
  return h('div', {class: 'mb-3'}, h('h3', {class: 'mb-2'}, `Score on the ${sc.companies === 6 ? 'six' : int(sc.companies)}`),
    h('div', {class: 'datagrid'}, item(`Outputs, ${STAGE_LABEL_UI[sc.stage] || sc.stage} stage`, states), item('Twin', twin), item('Planted faults', faults)),
    h('div', {class: 'text-secondary small mt-2'}, sc.note + (f ? `; faults: ${sc.faults_note}` : '')),
    f && f.by_kind ? faultsByKind(f) : '');
}

// per fault kind (T67): planted, caught, escaped and no effect with XBRL counted, then caught and escaped with it off;
// plain counts in the kit's table, every number next to its denominator (planted), a kind with no XBRL-off row shows —
function faultsByKind(f) {
  const off = f.xbrl_off && f.xbrl_off.by_kind ? f.xbrl_off.by_kind : {};
  const kinds = Object.keys(f.by_kind);
  const cell = (n) => h('td', {class: 'num'}, int(n));
  const row = (k, c, o, cls) => h('tr', {class: cls || null}, h('td', {class: 'font-monospace small'}, k), cell(c.planted), cell(c.caught), cell(c.xbrl_only), cell(c.escaped), cell(c.no_effect),
    cell(o ? o.caught : null), cell(o ? o.escaped : null));
  const th = (t, num) => h('th', {class: num ? 'num' : null}, t);
  return h('div', {class: 'card mt-3'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, 'Planted faults by kind'),
      h('span', {class: 'ms-auto text-secondary small'}, 'caught = a rule or XBRL fired; of which XBRL only = nothing but xbrl_reconcile fired; XBRL off = the same trials without that rule')),
    h('div', {class: 'table-responsive'}, h('table', {class: 'table table-sm table-vcenter card-table'},
      h('thead', {}, h('tr', {}, th('Kind'), th('Planted', 1), th('Caught', 1), th('of which XBRL only', 1), th('Escaped', 1), th('No effect', 1), th('XBRL off: caught', 1), th('XBRL off: escaped', 1))),
      h('tbody', {}, kinds.map((k) => row(k, f.by_kind[k], off[k]))),
      h('tfoot', {}, row('all kinds', f, f.xbrl_off, 'fw-semibold')))));
}

async function rulesPage(view) {
  const [r, readers] = await Promise.all([api('/api/v1/rules'), api('/api/agents').catch(() => ({}))]);
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'}, h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Rules'),
    h('div', {class: 'text-secondary small'}, 'The agents first: each one’s charter, who changed its prompt and when, and what it ran on the proven set. Then every rule, guard and definition, with what it closed in the latest run, and the open items grouped by what is missing: that list is the work.'))));
  const live = Object.values(readers).filter((a) => !a.retired);
  const agents = h('div', {class: 'mb-4'}, h('h2', {class: 'mb-1'}, `The agents: ${live.length}`), h('div', {class: 'text-secondary small mb-3'}, 'One owner per method. Prompts are files under agents/prompts, versioned, never edited in place; the runs come from the runs table, one row per filing or text.'), live.map(agentCard));
  const KINDB = {rule: 'bg-secondary-lt', guard: 'bg-azure-lt', definition: 'bg-green-lt', mapping: 'bg-green-lt'};
  const tbl = dtable('In force', [{t: 'Kind', f: (x) => h('span', {class: 'badge ' + KINDB[x.kind]}, x.kind)}, {t: 'Id', f: (x) => h('span', {class: 'font-monospace small'}, x.id)}, {t: 'What', f: (x) => h('span', {class: 'small brk'}, x.what)}, {t: 'Severity', f: (x) => x.severity || (x.where ? x.where : '')}, {t: 'Fired or closed', num: 1, f: (x) => int(x.fired)}, {t: 'Type', f: (x) => (x.type ? `type ${x.type}` : '')}], r.rules);
  const open = r.open_by_need.length ? r.open_by_need.map((g) => dtable(`Needs ${g.needs}`, [{t: 'Company', k: 'ticker'}, {t: 'Stage', k: 'stage'}, {t: 'What', k: 'what'}, {t: 'Detail', f: (o) => h('span', {class: 'text-secondary small brk'}, o.detail || '')}], g.items)) : [h('div', {class: 'card'}, h('div', {class: 'card-body text-secondary'}, 'Nothing open on the proven set.'))];
  view.append(head, agents, tbl, h('h2', {class: 'mt-4 mb-2'}, `Open on the proven set: ${int(r.open)}`), ...open.map((x) => h('div', {class: 'mb-3'}, x)));
}
