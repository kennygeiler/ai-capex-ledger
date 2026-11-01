// ── Company trail: one company's stages, open and explained items ────────────
// T56: the strongest answer key behind a `by`, one word beside it; the words come from the API's key_grade (status.KEY_LABEL), nothing when no key vouches for the row
async function trailPage(view, ticker) {
  const c = await api('/api/v1/proof/' + encodeURIComponent(ticker));
  const KEY_WORD = Object.fromEntries((c.key_grade || []).map((g) => [g.id, g.label]));  // the trail ships the same list the board does
  const byWithKey = (o) => [o.by, o.key ? h('span', {class: 'text-secondary'}, ` (${KEY_WORD[o.key] || o.key})`) : ''];
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('h1', {class: 'page-title'}, c.name, h('span', {class: 'text-secondary ms-2 fw-normal'}, c.ticker)), h('div', {class: 'text-secondary small'}, `${INDUSTRY[c.layer] || c.layer}. ${c.why || ''} ${c.in_proven_set ? '' : 'Not in the proven set.'}`)),
    h('div', {class: 'col-auto'}, c.proven ? h('span', {class: 'badge bg-green-lt'}, 'proven') : h('span', {class: 'badge bg-red-lt'}, `${int(c.open)} open`), ' ', h('a', {href: `#data?ticker=${c.ticker}`, class: 'small ms-2'}, 'Dataset'), h('a', {href: `#reconcile?scope=${c.ticker}`, class: 'small ms-2'}, 'Reconcile'))));
  const cards = Object.entries(c.stages).map(([id, st]) => {
    const extra = id === 'mapping' ? ` ${int(st.derived_rows)} derived rows, ${int(st.committed_rows)} committed rows, ${int(st.company_stated_ai)} company-stated AI figures.` : id === 'planned' ? ` ${int(st.guidance)} guidance statements, ${int(st.projects)} projects.` : '';
    const body = [];
    const checked = (st.all || []).filter((i) => i.state === 'checked');
    const keyed = st.keys ? Object.entries(KEY_WORD).filter(([k]) => st.keys[k]).map(([k, w]) => `${int(st.keys[k])} ${w}`).join(', ') : '';
    if (st.open.length) body.push(dtable('Open', [{t: 'What', k: 'what'}, {t: 'Detail', f: (o) => h('span', {class: 'text-secondary small brk'}, o.detail || '')}, {t: 'Needs', f: (o) => h('span', {class: 'badge bg-red-lt'}, o.needs)}], st.open));
    if (st.explained_items && st.explained_items.length) body.push(h('details', {class: 'mt-2', open: st.open.length ? null : null}, h('summary', {class: 'text-secondary small', style: 'cursor:pointer'}, `${int(st.explained_items.length)} explained`),
      h('div', {class: 'mt-2'}, dtable('Explained', [{t: 'What', k: 'what'}, {t: 'By', f: (o) => h('span', {class: 'badge bg-azure-lt'}, o.by)}, {t: 'Detail', f: (o) => h('span', {class: 'text-secondary small brk'}, o.detail || '')}], st.explained_items))));
    if (checked.length) body.push(h('details', {class: 'mt-2'}, h('summary', {class: 'text-secondary small', style: 'cursor:pointer'}, `${int(checked.length)} checked${keyed ? ` (${keyed})` : ''}`),
      h('div', {class: 'mt-2'}, dtable('Checked', [{t: 'What', k: 'what'}, {t: 'By', f: byWithKey}, {t: 'Reason', f: (o) => h('span', {class: 'text-secondary small brk'}, o.reason || '')}], checked))));
    return h('div', {class: 'card mb-3'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, STAGE_LABEL_UI[id] || id), h('span', {class: 'ms-3 text-secondary small'}, `${int(st.items)} items: `, h('span', {class: 'text-green'}, `${int(st.checked)} checked`), keyed ? h('span', {class: 'text-secondary'}, ` (${keyed})`) : '', ', ', h('span', {class: 'text-azure'}, `${int(st.explained)} explained`), ', ', h('span', {class: st.open.length ? 'text-red' : 'text-secondary'}, `${int(st.open.length)} open`), '.', extra)),
      body.length ? h('div', {class: 'card-body py-2'}, body) : '');
  });
  const defs = c.definitions.length ? h('p', {class: 'text-secondary small'}, 'Definitions on file: ', c.definitions.join(', ')) : '';
  view.append(head, defs, ...cards);
}
