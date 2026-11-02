// ── Routing ─────────────────────────────────────────────────────────────────
async function route() {
  const raw = location.hash.slice(1) || 'proof';
  const [path, qs] = raw.split('?');
  const [page, arg] = path.split('/');
  const tab = {company: 'data', tables: 'data', views: 'explore', evidence: 'proof'}[page] || page;
  document.querySelectorAll('header [data-nav]').forEach((a) => a.classList.toggle('active', a.dataset.nav === tab));
  const view = $('#view');
  view.replaceChildren(h('h1', {class: 'sr'}, `Kenny's Data Emporium, ${page === 'proof' && arg ? `Company trail ${arg}` : ({proof: 'Proof', rules: 'Rules', reconcile: 'Reconcile', data: 'Dataset', company: 'Company', explore: 'Explore', release: 'Release', gaps: 'Known gaps', evidence: 'Evidence'})[page] || 'Data'}`));
  try {
    if (page === 'proof' && arg) await trailPage(view, arg);
    else if (page === 'proof') await proofPage(view);
    else if (page === 'rules') await rulesPage(view);
    else if (page === 'company') await dataPage(view, `ticker=${arg || ''}`);
    else if (page === 'reconcile') await reconcilePage(view, qs);
    else if (page === 'views' || page === 'explore') await explorePage(view, arg, qs);
    else if (page === 'data') await dataPage(view, qs);
    else if (page === 'release') await releasePage(view, qs);
    else if (page === 'gaps') await gapsPage(view);
    else if (page === 'evidence') await evidencePage(view, arg, qs);
    else if (page === 'tables') { go('data?' + new URLSearchParams({list: arg || 'taxonomy', ...parseQ(qs || '')}).toString()); return; }
    else await proofPage(view);
  } catch (e) {
    view.replaceChildren(h('p', {class: 'msg bad'}, e.message));
  }
  skin(view);
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', route);
route();
// T29, the first line: what this copy shows. Scope, the last run, read-only or local; one line under the nav.
hq().then((d) => {
  if (d.readonly) $('#me').closest('span').replaceWith(h('span', {class: 'text-azure small'}, 'Read-only'));
  const hl = (d.health && d.health[0]) || {};
  const n = hl.companies != null ? hl.companies : (SCOPE.length || null);
  const line = h('div', {class: 'container-xl text-secondary small py-1', id: 'scopeline'},
    h('a', {href: '#data', class: 'text-reset'}, n == null ? '…' : `${int(n)} companies`), ' · ', `Data as of ${day(hl.run_at)}`, d.readonly ? ' · Read-only' : '');
  $('header').after(line);
}).catch(() => {});
