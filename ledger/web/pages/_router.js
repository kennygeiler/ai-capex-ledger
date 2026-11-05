// ── Routing ─────────────────────────────────────────────────────────────────
// F-VS4: each route draws into its own container, and a newer route detaches it. A page whose await resumes after the
// reader moved on appends into a container no longer on the page, never into the next page; `routeGen` tells the
// router not to skin or scroll for it.
let routeGen = 0;
// Back keeps the place (report #10, #12): each history entry keeps its scroll in history.state.y as the reader scrolls; a
// hashchange onto an entry that has one (Back, Forward) returns there, a new link starts at the top, and a page may name
// an element to land on (data-land, a Docs heading asked for with ?at=)
const landAt = (ev, view) => { const y = ev && ev.type === 'hashchange' && history.state ? history.state.y : null; return y != null ? {y} : view.querySelector('[data-land]') ? {el: view.querySelector('[data-land]')} : {y: 0}; };
let keepT = null;
window.addEventListener('scroll', () => { clearTimeout(keepT); keepT = setTimeout(() => { try { history.replaceState({...(history.state || {}), y: Math.round(window.scrollY)}, ''); } catch (e) { /* a sandboxed frame: no memory, the top as before */ } }, 150); }, {passive: true});
async function route(ev) {
  const gen = ++routeGen;
  const raw = location.hash.slice(1) || 'proof';
  const [path, qs] = raw.split('?');
  const [page, arg] = path.split('/');
  const tab = {company: 'data', tables: 'data', views: 'explore', evidence: 'proof'}[page] || page;
  document.querySelectorAll('header [data-nav]').forEach((a) => a.classList.toggle('active', a.dataset.nav === tab));
  const view = h('div', {class: 'route'});
  $('#view').replaceChildren(h('h1', {class: 'sr'}, `Kenny's Data Emporium, ${page === 'proof' && arg ? `Company trail ${arg}` : ({proof: 'Proof', rules: 'Rules', reconcile: 'Reconcile', data: 'Dataset', company: 'Company', explore: 'Explore', release: 'Release', gaps: 'Known gaps', docs: 'Docs', evidence: 'Evidence'})[page] || 'Data'}`), view);
  try {
    if (page === 'proof' && arg) await trailPage(view, arg);
    else if (page === 'proof') await proofPage(view, qs);
    else if (page === 'rules') await rulesPage(view);
    else if (page === 'company') await dataPage(view, `ticker=${arg || ''}`);
    else if (page === 'reconcile') await reconcilePage(view, qs);
    else if (page === 'views' || page === 'explore') await explorePage(view, arg, qs);
    else if (page === 'data') await dataPage(view, qs);
    else if (page === 'release') await releasePage(view, qs);
    else if (page === 'gaps') await gapsPage(view);
    else if (page === 'docs') await docsPage(view, arg, qs);
    else if (page === 'evidence') await evidencePage(view, arg, qs);
    else if (page === 'tables') { go('data?' + new URLSearchParams({list: arg || 'taxonomy', ...parseQ(qs || '')}).toString()); return; }
    else await proofPage(view);
  } catch (e) {
    view.replaceChildren(h('p', {class: 'msg bad'}, e.message));
  }
  if (gen !== routeGen || !view.isConnected) return;  // a newer route owns the page
  skin(view);
  const at = landAt(ev, view);
  if (at.el) at.el.scrollIntoView({behavior: 'instant'}); else window.scrollTo({top: at.y, behavior: 'instant'});  // the page's smooth scroll is for the reader's own moves
}
window.addEventListener('hashchange', route);
route();
// report #14: on the read-only copy, which release it serves and its code, and what makes it stale: an older release than
// the latest signed one, or code other than the checkout's (claims.copy_status, from the deploy record; nothing fetched)
const copyLine = (c) => {
  if (!c) return [];
  if (!c.recorded) return [' · ', h('span', {class: 'text-orange'}, 'Deploy not recorded')];
  return [` · Serves ${c.release || '—'}`, c.commit ? ` · Code ${String(c.commit).slice(0, 7)}` : '',
    c.older ? [' · ', h('span', {class: 'text-orange'}, `Older than ${c.latest_signed}`)] : '',
    c.code === 'differs' ? [' · ', h('span', {class: 'text-orange'}, `Code differs from ${c.head}`)] : ''];
};
// T29, the first line: what this copy shows. Scope, the last run, read-only or local; one line under the nav.
hq().then((d) => {
  if (d.readonly) { $('#me').closest('span').replaceWith(h('span', {class: 'text-azure small'}, 'Read-only')); document.body.classList.add('readonly'); }  // F-VT4: every [data-write] hides
  const hl = (d.health && d.health[0]) || {};
  const n = hl.companies != null ? hl.companies : (SCOPE.length || null);
  // V5: the line sits in the page's container (app.html), on the H1's left edge; its height is reserved before this lands
  $('#scopeline').replaceChildren(h('a', {href: '#data', class: 'text-reset'}, n == null ? '…' : `${int(n)} companies`), ' · ', `Data as of ${day(hl.run_at)}`, ...(d.readonly ? [' · Read-only', ...copyLine(d.copy)].flat(Infinity).filter((x) => x !== '') : []));
}).catch(() => {});
