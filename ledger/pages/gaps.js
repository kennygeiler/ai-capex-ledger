// ── Gaps: the claims register (claims/claims.yaml, ledger/claims.py). Each claim the product makes, where, its computed
// status and its gaps; then the open review findings. The server computes every status; the page renders it. ──────
const CLAIM_STATE = {stub: 'bg-red-lt', stale: 'bg-orange-lt', partial: 'bg-yellow-lt', planned: 'bg-secondary-lt', proven: 'bg-green-lt'};
const CLAIM_ORDER = {stub: 0, stale: 1, partial: 2, planned: 3, proven: 4};
const SEVERITY = {high: ['bg-red-lt', 0], medium: ['bg-orange-lt', 1], low: ['bg-secondary-lt', 2]};
const pagesOnly = (where) => where.filter((w) => !w.startsWith('ledger/') || w.startsWith('ledger/pages/')).map((w) => w.replace('ledger/pages/', '').replace('.js', ''));

function claimWhy(r) {
  const why = (r.reasons || []).filter((x) => x.status !== 'proven' && x.phrase !== 'gaps listed');
  return h('div', {class: 'small'},
    why.length ? h('ul', {class: 'plain'}, why.map((x) => h('li', {}, x.phrase))) : h('span', {class: 'text-secondary'}, 'Declared status stands'),
    h('details', {class: 'words mt-2'}, h('summary', {}, 'Backing'),
      h('div', {class: 'text-secondary mono'}, 'Declared: ', r.declared),
      h('div', {class: 'text-secondary mono'}, 'Where: ', r.where.join(', ')),
      h('div', {class: 'text-secondary mono'}, 'Functions: ', (r.backed_by.functions || []).join(', ') || '—'),
      h('div', {class: 'text-secondary mono'}, 'Tests: ', (r.backed_by.tests || []).join(', ') || '—'),
      why.filter((x) => x.detail).length ? h('div', {class: 'text-secondary mono'}, 'Detail: ', why.filter((x) => x.detail).map((x) => x.detail).join('; ')) : '',
      r.open_findings && r.open_findings.length ? h('div', {class: 'text-secondary mono'}, 'Open findings: ', r.open_findings.join(', ')) : ''));
}

async function gapsPage(view) {
  const d = await api('/api/v1/claims');
  const c = d.counts, ao = d.append_only || {}, sc = d.scanned || {};
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Known gaps'),
      h('div', {class: 'text-secondary small'}, ['proven', 'partial', 'stub', 'stale', 'planned'].map((s, i) => [i ? ' · ' : '', h('b', {class: 'text-body'}, int(c[s])), ` ${s}`]),
        ' · ', h('b', {class: 'text-body'}, int(c.open_findings)), ' open findings'),
      h('div', {class: 'text-secondary small'}, `Scanned ${int(sc.pages)} pages · ${int(sc.strings)} labels · `,
        h('span', {class: ao.enforced === false ? 'text-orange' : ao.problems && ao.problems.length ? 'text-red' : ''}, ao.enforced === false ? 'Findings log append-only: not enforced here' : `Findings log append-only: ${ao.problems && ao.problems.length ? 'edited' : 'checked'}`))),
    h('div', {class: 'col-auto text-secondary small'}, `Computed ${when(d.at)}`)));
  const problems = (d.problems || []).length
    ? h('div', {class: 'alert alert-danger small'}, h('b', {}, `Register incomplete · ${int(d.problems.length)}`), h('ul', {class: 'plain'}, d.problems.map((p) => h('li', {}, `${p.kind}: ${p.what} · ${p.where}`))))
    : '';
  const claims = table([
    {t: 'Claim', k: 'claim', f: (r) => h('span', {class: 'fw-medium'}, r.claim), wide: 1},
    {t: 'Where', k: 'where', f: (r) => h('span', {class: 'text-secondary small'}, pagesOnly(r.where).join(', ') || '—')},
    {t: 'Status', k: 'status', s: (r) => CLAIM_ORDER[r.status], f: (r) => h('span', {class: 'badge ' + (CLAIM_STATE[r.status] || '')}, r.status, r.worse || r.better ? ` · declared ${r.declared}` : '')},
    {t: 'Gaps', k: 'gaps', s: (r) => r.gaps.length + r.facts.length, f: (r) => (r.gaps.length + r.facts.length ? h('ul', {class: 'plain small'}, [...r.facts, ...r.gaps].map((g) => h('li', {}, g))) : h('span', {class: 'text-secondary'}, '—'))},
    {t: 'Ticket', k: 'ticket', f: (r) => (r.ticket === 'none' ? h('span', {class: 'text-secondary'}, '—') : r.ticket)},
  ], d.claims, {detail: claimWhy});
  const fs = [...d.findings].sort((a, b) => SEVERITY[a.severity][1] - SEVERITY[b.severity][1]);
  const findings = table([
    {t: 'Severity', k: 'severity', s: (r) => SEVERITY[r.severity][1], f: (r) => h('span', {class: 'badge ' + SEVERITY[r.severity][0]}, r.severity)},
    {t: 'Finding', k: 'text', wide: 1, f: (r) => h('span', {}, r.text)},
    {t: 'Claim', k: 'claim', f: (r) => ((d.claims.find((x) => x.id === r.claim) || {}).claim || r.claim)},
    {t: 'Ticket', k: 'ticket', f: (r) => (r.ticket === 'none' ? h('span', {class: 'text-secondary'}, '—') : r.ticket)},
  ], fs, {detail: (r) => h('div', {class: 'small text-secondary mono'}, `${r.id} · ${r.source} · ${r.at} · ${r.where}`)});
  view.append(head, problems, h('h2', {class: 'mt-2'}, `Claims · ${int(d.claims.length)}`), claims,
    h('h2', {class: 'mt-4'}, `Open findings · ${int(fs.length)}`), findings);
}
