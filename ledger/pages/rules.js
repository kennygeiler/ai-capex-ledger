// ── Rules: the agents first (charter, prompt history, runs per company), then every rule, guard and definition, and what is open on the proven set ──
function agentCard(a) {
  const blocks = (a.charter_blocks || []).slice(1);  // the first block is the title, the card header carries it
  const charter = h('div', {class: 'charter', style: 'max-width:72ch'}, blocks.length ? blocks.map((b) => (b.kind === 'heading' ? h('h4', {class: 'mt-3 mb-1'}, b.text) : h('p', {class: 'mb-2'}, b.text))) : h('p', {class: 'text-secondary'}, `No charter on file at ${a.charter || `agents/charters/${a.id}.md`}.`));
  const r = a.runs || {companies: [], total: {}};
  const runs = dtable(`Runs per company`, [{t: 'Company', k: 'ticker', strong: 1}, {t: 'Read', num: 1, f: (x) => int(x.read)}, {t: 'Calls', num: 1, f: (x) => int(x.calls)}, {t: 'In tokens', num: 1, f: (x) => int(x.input_tokens)}, {t: 'Out tokens', num: 1, f: (x) => int(x.output_tokens)}, {t: 'Seconds', num: 1, f: (x) => int(Math.round(x.seconds))}, {t: 'Attempts', num: 1, f: (x) => int(x.attempts)}, {t: 'Failed', num: 1, f: (x) => (x.failed ? h('span', {class: 'text-danger'}, int(x.failed)) : '0')}], r.companies,
    {foot: ['All six', int(r.total.read), int(r.total.calls), int(r.total.input_tokens), int(r.total.output_tokens), int(Math.round(r.total.seconds || 0)), int(r.total.attempts), int(r.total.failed)], note: r.subject ? `one ${r.subject} per row of the runs table` : ''});
  const history = dtable('Prompt and model history', [{t: 'When', f: (x) => day(x.at)}, {t: 'By', k: 'by'}, {t: 'Change', f: (x) => h('span', {class: 'brk'}, x.change)}], a.history || [], {note: `on file: ${(a.versions || []).join(', ')}`});
  return h('div', {class: 'card mb-3', id: `agent-${a.id}`},
    h('div', {class: 'card-header'}, h('div', {class: 'me-4', style: 'min-width:0'}, h('h2', {class: 'card-title m-0'}, a.name), h('div', {class: 'text-secondary small', style: 'white-space:normal'}, a.job)),
      h('div', {class: 'ms-auto text-end small flex-shrink-0'}, h('div', {}, 'model ', h('span', {class: 'font-monospace'}, a.llm.model)), h('div', {}, 'prompt in use ', h('span', {class: 'font-monospace'}, a.prompt)), h('div', {class: 'text-secondary'}, `step ${r.step || '—'} · ${a.llm.runs_on}`))),
    h('div', {class: 'card-body'}, h('div', {class: 'row g-4'},
      h('div', {class: 'col-lg-6'}, h('h3', {class: 'mb-2'}, 'Charter'), h('div', {class: 'text-secondary small mb-2'}, `${a.charter || `agents/charters/${a.id}.md`}, written from the code`), charter),
      h('div', {class: 'col-lg-6'}, runs, r.note ? h('div', {class: 'text-secondary small mt-2 mb-3'}, r.note) : '', h('div', {class: 'mt-3'}, history)))));
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
