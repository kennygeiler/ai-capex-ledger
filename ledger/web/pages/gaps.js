// ── Gaps: the claims register (claims/claims.yaml, ledger/release/claims.py). Each claim the product makes, where, its computed
// status and its gaps; then the open review findings. The server computes every status; the page renders it. ──────
const CLAIM_STATE = {stub: 'text-red', stale: 'text-orange', partial: 'text-yellow', planned: 'text-secondary', proven: 'text-green'};
const CLAIM_WORD = {proven: 'Holds', partial: 'Partial', stub: 'Not built', stale: 'Out of date', planned: 'Planned'};
const CLAIM_ORDER = {stub: 0, stale: 1, partial: 2, planned: 3, proven: 4};
const SEVERITY = {high: ['text-red', 0], medium: ['text-orange', 1], low: ['text-secondary', 2]};
const PAGE_WORD = {trail: 'Company trail', proof: 'Proof', reconcile: 'Reconcile', release: 'Release', rules: 'Rules', data: 'Dataset', explore: 'Explore', gaps: 'Known gaps', evidence: 'Evidence'};
const pagesOnly = (where) => [...new Set(where.filter((w) => w.startsWith('ledger/web/pages/')).map((w) => w.replace('ledger/web/pages/', '').replace(/\.js$/, '')).filter((w) => PAGE_WORD[w]).map((w) => PAGE_WORD[w]))];

function claimWhy(r) {
  const why = (r.reasons || []).filter((x) => x.status !== 'proven' && x.phrase !== 'gaps listed');
  return h('div', {class: 'small'}, why.length ? h('ul', {class: 'plain'}, why.map((x) => h('li', {}, x.phrase))) : h('span', {class: 'text-secondary'}, '—'));
}

async function gapsPage(view) {
  const d = await api('/api/v1/claims');
  const c = d.counts, ao = d.append_only || {};
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Known gaps'),
      h('div', {class: 'text-secondary small'}, ['proven', 'partial', 'stub', 'stale', 'planned'].map((s, i) => [i ? ' · ' : '', h('b', {class: 'text-body'}, int(c[s])), ` ${CLAIM_WORD[s]}`]),
        ' · ', h('b', {class: 'text-body'}, int(c.open_findings)), ' open issues'),
      ao.enforced === false || (ao.problems && ao.problems.length) ? h('div', {class: 'small ' + (ao.enforced === false ? 'text-orange' : 'text-red')}, ao.enforced === false ? 'Issue log append-only: not enforced here' : 'Issue log edited') : ''),
    h('div', {class: 'col-auto text-secondary small'}, `Updated ${when(d.at)}`)));
  const problems = (d.problems || []).length
    ? h('div', {class: 'alert alert-danger small'}, h('b', {}, `Unregistered claims · ${int(d.problems.length)}`), h('ul', {class: 'plain'}, d.problems.map((p) => h('li', {}, `${p.kind}: ${p.what} · ${p.where}`))))
    : '';
  const claims = table([
    {t: 'Claim', k: 'claim', f: (r) => h('span', {class: 'fw-medium'}, r.claim), wide: 1},
    {t: 'Where', k: 'where', f: (r) => h('span', {class: 'text-secondary small'}, pagesOnly(r.where).join(', ') || '—')},
    {t: 'Status', k: 'status', s: (r) => CLAIM_ORDER[r.status], f: (r) => h('span', {class: (CLAIM_STATE[r.status] || '') + ' fw-medium text-nowrap', title: r.worse || r.better ? `Declared ${CLAIM_WORD[r.declared] || r.declared}` : null}, CLAIM_WORD[r.status] || r.status)},
    {t: 'Gaps', k: 'gaps', s: (r) => r.gaps.length + r.facts.length, f: (r) => (r.gaps.length + r.facts.length ? h('ul', {class: 'plain small'}, [...r.facts, ...r.gaps].map((g) => h('li', {}, g))) : h('span', {class: 'text-secondary'}, '—'))},
  ], d.claims, {detail: claimWhy});
  const fs = [...d.findings].sort((a, b) => SEVERITY[a.severity][1] - SEVERITY[b.severity][1]);
  const findings = table([
    {t: 'Severity', k: 'severity', s: (r) => SEVERITY[r.severity][1], f: (r) => h('span', {class: SEVERITY[r.severity][0] + ' fw-medium'}, r.severity[0].toUpperCase() + r.severity.slice(1))},
    {t: 'Issue', k: 'text', wide: 1, f: (r) => h('span', {}, r.text)},
    {t: 'Claim', k: 'claim', f: (r) => ((d.claims.find((x) => x.id === r.claim) || {}).claim || r.claim)},
  ], fs, {detail: (r) => h('div', {class: 'small text-secondary'}, `Logged ${day(r.at)} · ${r.id}`)});
  view.append(head, problems, h('h2', {class: 'mt-2'}, `Claims · ${int(d.claims.length)}`), claims,
    h('h2', {class: 'mt-4'}, `Open issues · ${int(fs.length)}`), findings);
}
