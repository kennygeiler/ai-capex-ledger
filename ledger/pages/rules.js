// ── Rules: every rule, guard and definition, and what is open on the proven set ──
async function rulesPage(view) {
  const r = await api('/api/v1/rules');
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'}, h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Rules'),
    h('div', {class: 'text-secondary small'}, 'Every rule, guard and definition, with what it closed on the proven set in the latest run. Below, the open items grouped by what is missing: that list is the work.'))));
  const KINDB = {rule: 'bg-secondary-lt', guard: 'bg-azure-lt', definition: 'bg-green-lt', mapping: 'bg-green-lt'};
  const tbl = dtable('In force', [{t: 'Kind', f: (x) => h('span', {class: 'badge ' + KINDB[x.kind]}, x.kind)}, {t: 'Id', f: (x) => h('span', {class: 'font-monospace small'}, x.id)}, {t: 'What', f: (x) => h('span', {class: 'small brk'}, x.what)}, {t: 'Severity', f: (x) => x.severity || (x.where ? x.where : '')}, {t: 'Fired or closed', num: 1, f: (x) => int(x.fired)}, {t: 'Type', f: (x) => (x.type ? `type ${x.type}` : '')}], r.rules);
  const open = r.open_by_need.length ? r.open_by_need.map((g) => dtable(`Needs ${g.needs}`, [{t: 'Company', k: 'ticker'}, {t: 'Stage', k: 'stage'}, {t: 'What', k: 'what'}, {t: 'Detail', f: (o) => h('span', {class: 'text-secondary small brk'}, o.detail || '')}], g.items)) : [h('div', {class: 'card'}, h('div', {class: 'card-body text-secondary'}, 'Nothing open on the proven set.'))];
  const readers = await api('/api/agents').catch(() => ({}));
  const agents = dtable('The readers', [{t: 'Agent', k: 'name'}, {t: 'Model', f: (a) => h('span', {class: 'font-monospace small'}, a.llm.model)}, {t: 'Prompt in use', f: (a) => h('span', {class: 'font-monospace small'}, a.prompt)}, {t: 'Decides', f: (a) => h('span', {class: 'small text-secondary'}, a.decides.join('; '))}], Object.values(readers).filter((a) => !a.retired), {note: 'prompts are files under agents/prompts, versioned, never edited in place'});
  view.append(head, tbl, h('h2', {class: 'mt-4 mb-2'}, `Open on the proven set: ${int(r.open)}`), ...open.map((x) => h('div', {class: 'mb-3'}, x)), h('div', {class: 'mt-4'}, agents));
}
