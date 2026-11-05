// ── Release: the checklist a person signs from (T5, T6, T8; docs/PROOF.md). Every line is something that could make
// the signature wrong, with its count and the page that fixes it. The server builds it (ledger/release/checklist.py); the
// page renders it as it is and recomputes nothing. ───────────────────────────────────────────────────────────────
const stateBadge = (l) => { const [cls, word] = stateWord('line', l.state); return h('span', {class: cls + ' fw-medium'}, word); };  // states.LINE
const PAGE_NAME = {proof: 'Proof', reconcile: 'Reconcile', data: 'Dataset', gaps: 'Known gaps', release: 'Release', rules: 'Rules'};

// what a line's detail holds, as a table whose columns are the detail's own keys
function lineDetail(l) {
  if (!l.detail || !l.detail.length) return h('p', {class: 'text-secondary small m-0'}, 'No items');
  // a row's `link` (the page that fixes that one item or company) is not a column: it makes the row's first cell a link (F-BF11)
  const keys = [...new Set(l.detail.flatMap((r) => Object.keys(r)))].filter((k) => k !== 'link');
  const text = (r, k) => (Array.isArray(r[k]) ? (r[k].length ? r[k].join(', ') : '—') : typeof r[k] === 'number' ? int(r[k]) : r[k] == null || r[k] === '' ? '—' : String(r[k]));
  const cols = keys.map((k, i) => ({t: k.replaceAll('_', ' '), k, num: typeof l.detail[0][k] === 'number', f: (r) => (i === 0 && r.link ? h('a', {href: '#' + r.link}, text(r, k)) : text(r, k))}));
  return dtable(l.label, cols, l.detail);
}

// review 4: the regression test's steps (pass or fail per step) and its differences (table, added, missing), the tables
// Proof's Regression test card held, sit under the Regression test line here; /api/v1/golden is the last `ledger golden --check`
const goldenSteps = (g) => ((g && g.steps) || []).map((x) => ({step: x.step, result: x.exit === 0 ? 'Pass' : `Fail (${x.exit})`}));
const goldenDiffs = (g) => Object.entries((g && g.diffs) || {}).map(([name, v]) => ({table: name, added: v.n_only_in_run, missing: v.n_only_in_expected}));
function regressionDetail(g) {
  const steps = goldenSteps(g), diffs = goldenDiffs(g);
  if (!steps.length && !diffs.length) return h('p', {class: 'text-secondary small m-0'}, 'No regression run on record');
  return h('div', {class: 'row g-3'},
    steps.length ? h('div', {class: 'col-md-6'}, dtable('Steps', [{t: 'Step', k: 'step'}, {t: 'Result', f: (x) => h('span', {class: x.result === 'Pass' ? 'text-green' : 'text-red'}, x.result)}], steps, {bare: true})) : '',
    h('div', {class: 'col-md-6'}, diffs.length ? dtable('Differences', [{t: 'Table', k: 'table'}, {t: 'Added', num: 1, f: (x) => int(x.added)}, {t: 'Missing', num: 1, f: (x) => int(x.missing)}], diffs, {bare: true}) : h('p', {class: 'text-secondary small m-0'}, 'No table differs from the freeze')));
}

// the lines in the order a signer acts on them: failing required lines first (fail, stale, not run), then one "N checks
// pass" row whose passing and informational lines stay folded until it is opened (docs/ux-flow/report.md #2)
const LINE_ORDER = {fail: 0, stale: 1, not_run: 2, pass: 3, info: 4};
const splitLines = (lines) => { const sorted = [...lines].sort((a, b) => (LINE_ORDER[a.state] ?? 0) - (LINE_ORDER[b.state] ?? 0)); return {act: sorted.filter((l) => l.state !== 'pass' && l.state !== 'info'), rest: sorted.filter((l) => l.state === 'pass' || l.state === 'info')}; };
const passSummary = (rest) => { const p = rest.filter((l) => l.state === 'pass').length, i = rest.length - p; return `${p} check${p === 1 ? '' : 's'} pass` + (i ? ` · ${i} informational` : ''); };

// {company, gate: items, result} per company from the packet's gate table, each gate named by its line's label
const gateRows = (cl) => { const g = cl.gates.table, ids = Object.keys(g), cos = Object.keys(g[ids[0]] || {}); return cos.map((t) => ({company: t, ...Object.fromEntries(ids.map((x) => [x, g[x][t].length])), result: ids.some((x) => g[x][t].length) ? 'fail' : 'pass'})); };
function gatesByCompany(cl) {
  const ids = Object.keys(cl.gates.table), name = (x) => (cl.lines.find((l) => l.id === 'gate_' + x) || {}).label || x;
  return h('table', {class: 'table table-sm mb-0'}, h('thead', {}, h('tr', {}, h('th', {}, 'Company'), ids.map((x) => h('th', {class: 'n'}, name(x))), h('th', {}, 'Result'))),
    h('tbody', {}, gateRows(cl).map((r) => h('tr', {}, h('td', {}, h('a', {href: '#proof/' + r.company}, r.company)), ids.map((x) => h('td', {class: 'n'}, r[x] ? h('span', {class: 'text-red fw-medium'}, int(r[x])) : h('span', {class: 'text-secondary'}, '0'))),
      h('td', {}, stateBadge({state: r.result}))))));
}

// [enabled, why] for the Sign button: every required line green and a signer on the people list (config.PEOPLE, sent with the checklist)
const signState = (cl, name) => { const n = (name || '').trim(), red = cl.lines.filter((l) => l.required && !l.ok).length; return red ? [false, `${red} required check${red === 1 ? '' : 's'} failing`] : !n ? [false, 'Enter a signer name'] : !(cl.people || []).includes(n) ? [false, 'Not on the signer list'] : [true, `Signs and publishes ${cl.version}`]; };

// the signed releases, newest first, and the one whose packet a reader downloads: the newest signed (report #8: the
// downloads moved here from Proof; one primary, the rest plain links)
const latestSigned = (rels) => [...rels].reverse().find((r) => r.signed_by && r.packet && r.published !== false) || null;  // signed, not published: no primary (it reads "not published"), as after a failed publish (review 6)
const packetHref = (v) => `/packet/${encodeURIComponent(v)}.zip`;
// after a signature the page stays on Release with the packet's download; a failed publish says so and offers none
const signedNext = (r) => (r.published ? {href: packetHref(r.version), label: `Download ${r.version}`} : null);
function releasesTable(rels) {
  const latest = latestSigned(rels);
  const atSigning = (r, f) => (r.checklist ? f(r.checklist) : h('span', {class: 'text-secondary'}, '—'));  // T7: what a signature meant; before the checklist, —
  const tbl = dtable('Releases', [{t: 'Version', k: 'version'}, {t: 'Signed', f: (r) => (r.signed_by ? [`${r.signed_by}, ${day(r.signed_at)}`, r.published === false ? h('span', {class: 'text-red'}, ' · not published') : ''] : h('span', {class: 'text-secondary'}, 'Not signed'))}, {t: 'Values', num: 1, f: (r) => int(r.rows.length)},
    {t: 'To review at signing', num: 1, f: (r) => atSigning(r, (c) => int(c.open))}, {t: 'Unmapped at signing', num: 1, f: (r) => atSigning(r, (c) => int(c.unmapped))}, {t: 'Companies', f: (r) => atSigning(r, (c) => `${int(c.scope.length)}: ${c.scope.join(', ')}`)},
    {t: 'Packet', f: (r) => (!r.packet ? '' : r === latest ? h('a', {href: packetHref(r.version), class: 'btn btn-sm btn-outline-primary'}, `Download ${r.version}`) : h('a', {href: packetHref(r.version)}, 'Download'))}], [...rels].reverse().slice(0, 6));
  return h('div', {class: 'mt-3', id: 'releases'}, tbl);
}

// one listener for the page's life, bound once: each render swaps in its own recheck, and an old button off the page is ignored
let releaseRecheck = null;
document.addEventListener('input', (e) => { if (e.target.id === 'me' && releaseRecheck) releaseRecheck(); });

async function releasePage(view, qs) {
  const q = parseQ(qs || '');
  const [cl, out, golden] = await Promise.all([api('/api/v1/release/checklist' + (q.version ? `?version=${encodeURIComponent(q.version)}` : '')), api('/api/outputs').catch(() => ({releases: []})), api('/api/v1/golden').catch(() => null)]);
  const releases = h('div', {}, releasesTable(out.releases || []));
  const required = cl.lines.filter((l) => l.required), green = required.filter((l) => l.ok).length;
  let [canSign, why] = signState(cl, me);
  const status = h('div', {class: 'text-secondary small', id: 'signmsg', role: 'status', 'aria-live': 'polite'}, why);
  // the Signer box is read on every keystroke: Sign enables and disables with the name, never fixed at render (F-BF5)
  releaseRecheck = () => { if (!button.isConnected || button.dataset.busy) return; [canSign, why] = signState(cl, me); button.disabled = !canSign; button.title = why; status.replaceChildren(why); };
  const button = writes(h('button', {type: 'button', class: 'btn btn-primary', disabled: !canSign, title: why, onclick: async () => {
    if (!confirm(`Sign and publish ${cl.version} as ${me}?`)) return;
    button.disabled = true; button.dataset.busy = '1';
    status.textContent = `Signing ${cl.version}…`;
    try {
      const r = await api('/api/release/sign', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({version: cl.version, by: me})});
      status.replaceChildren(h('span', {class: 'text-green'}, `${r.version} signed by ${r.signed_by} · ${when(r.signed_at)} · ${r.hash.slice(0, 8)}`), ' · ',
        r.published ? `Published: ${Object.entries(r.rows || {}).map(([k, v]) => `${int(v)} ${k}`).join(', ')}` : h('span', {class: 'text-red'}, `Signed, not published: ${r.publish_error}`));
      const next = signedNext(r);  // the page stays on Release: the packet's download sits where the signature landed
      if (next) status.append(' · ', h('a', {href: packetHref(r.version), class: 'btn btn-sm btn-primary'}, next.label));
      api('/api/outputs').then((o) => releases.replaceChildren(releasesTable(o.releases || []))).catch(() => {});  // every signature redraws the table, published or not (review 5)
    } catch (e) {
      status.replaceChildren(h('span', {class: 'text-red'}, e.message));
      delete button.dataset.busy;
      button.disabled = !signState(cl, me)[0];
    }
  }}, `Sign ${cl.version}`));
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Release'),
      h('div', {class: 'text-secondary small'}, h('b', {class: 'text-body'}, cl.version), cl.previous ? ` · Compared with ${cl.previous}` : ' · First release', ` · ${cl.scope.length} companies · `,
        h('b', {class: 'text-body'}, `${green} of ${required.length}`), ' required checks pass', ` · Fingerprint ${cl.hash.slice(0, 8)}`)),
    h('div', {class: 'col-auto text-end'}, button, status)));
  const {act, rest} = splitLines(cl.lines);
  const SUMMARY = {id: '_summary', summary: true};
  const nameOf = (l) => (l.summary ? h('span', {class: 'text-secondary text-nowrap'}, passSummary(rest)) : h('span', {class: l.required ? '' : 'text-secondary'}, l.label));
  const lines = table([
    {t: 'State', sort: false, f: (l) => (l.summary ? h('span', {class: 'text-secondary', 'aria-hidden': 'true'}, '▸') : stateBadge(l))},
    {t: 'Check', sort: false, f: nameOf},
    {t: 'Count', n: 1, sort: false, f: (l) => (l.summary ? '' : l.state === 'not_run' ? '—' : int(l.count))},
    {t: 'Required', sort: false, f: (l) => (l.summary ? '' : l.required ? 'Required' : h('span', {class: 'text-secondary'}, 'Optional'))},
    {t: 'Details', sort: false, f: (l) => (l.summary ? '' : h('span', {class: 'text-secondary small'}, l.note))},
    {t: 'Fix in', sort: false, f: (l) => { if (l.summary || !l.link || l.ok || l.state === 'info') return ''; const pg = l.link.split('?')[0].split('/')[0]; return h('a', {href: '#' + l.link, class: 'text-nowrap', onclick: (e) => e.stopPropagation()}, PAGE_NAME[pg] || pg); }},
  ], [...act, SUMMARY, ...rest], {detail: (l) => (l.summary ? '' : l.id === 'regression' ? regressionDetail(golden) : lineDetail(l))});
  // the gates per company, Pass or Fail each, folded with the passing lines (the facts the old by-company card held)
  const byCo = h('tr', {class: 'gates-by-company'}, h('td', {colspan: 6}, gatesByCompany(cl)));
  lines.querySelector('tbody').append(byCo);
  // the summary row opens and closes the passing lines (and any line detail opened under them); it never opens a detail of its own
  const trs = [...lines.querySelectorAll('tbody > tr')], sumTr = trs[act.length], restTrs = trs.slice(act.length + 1);  // the by-company row is the last of them
  const fold = (shut) => { for (const tr of restTrs) { tr.hidden = shut; const nx = tr.nextElementSibling; if (shut && nx && nx.classList.contains('detail')) { nx.remove(); tr.classList.remove('open'); } } sumTr.setAttribute('aria-expanded', String(!shut)); sumTr.firstChild.firstChild.textContent = shut ? '▸' : '▾'; };
  sumTr.onclick = () => { const nx = sumTr.nextElementSibling; if (nx && nx.classList.contains('detail')) { nx.remove(); sumTr.classList.remove('open'); } fold(!restTrs[0] || !restTrs[0].hidden); };  // runs after the table's own row handler, and takes back the empty detail it adds
  fold(true);
  view.append(head, lines, releases);
}
