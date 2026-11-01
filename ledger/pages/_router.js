// ── Routing ─────────────────────────────────────────────────────────────────
async function route() {
  const raw = location.hash.slice(1) || 'proof';
  const [path, qs] = raw.split('?');
  const [page, arg] = path.split('/');
  const tab = {company: 'data', tables: 'data', views: 'explore', flow: 'proof', status: 'proof', golden: 'proof', releases: 'proof', agents: 'rules', attribution: 'rules', run: 'proof'}[page] || page;
  document.querySelectorAll('header [data-nav]').forEach((a) => a.classList.toggle('active', a.dataset.nav === tab));
  const view = $('#view');
  view.replaceChildren(h('h1', {class: 'sr'}, `DATAHQ, ${({proof: 'Proof', rules: 'Rules', reconcile: 'Reconcile', data: 'Dataset', company: 'Company', explore: 'Explore'})[page] || 'Data'}`));
  try {
    if (page === 'proof' && arg) await trailPage(view, arg);
    else if (page === 'proof') await proofPage(view);
    else if (page === 'rules') await rulesPage(view);
    else if (page === 'company') await dataPage(view, `ticker=${arg || ''}`);
    else if (page === 'reconcile') await reconcilePage(view, qs);
    else if (page === 'views' || page === 'explore') await explorePage(view, arg, qs);
    else if (page === 'data' || page === 'insights') await dataPage(view, qs);
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
hq().then((d) => { if (d.readonly) $('#me').closest('span').replaceWith(h('span', {class: 'badge bg-azure-lt', title: 'Every page reads; decisions, views and prompts change in a checkout of the repository'}, 'read-only copy')); }).catch(() => {});
