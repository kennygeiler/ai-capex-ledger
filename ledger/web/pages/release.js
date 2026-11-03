// ── Release: the checklist a person signs from (T5, T6, T8; docs/PROOF.md). Every line is something that could make
// the signature wrong, with its count and the page that fixes it. The server builds it (ledger/release/checklist.py); the
// page renders it as it is and recomputes nothing. ───────────────────────────────────────────────────────────────
const stateBadge = (l) => { const [cls, word] = stateWord('line', l.state); return h('span', {class: cls + ' fw-medium'}, word); };  // states.LINE
const PAGE_NAME = {proof: 'Proof', reconcile: 'Reconcile', data: 'Dataset', gaps: 'Known gaps', release: 'Release', rules: 'Rules'};

// what a line's detail holds, as a table whose columns are the detail's own keys
function lineDetail(l) {
  if (!l.detail || !l.detail.length) return h('p', {class: 'text-secondary small m-0'}, 'No items');
  const keys = [...new Set(l.detail.flatMap((r) => Object.keys(r)))];
  const cols = keys.map((k) => ({t: k.replaceAll('_', ' '), k, num: typeof l.detail[0][k] === 'number', f: (r) => (Array.isArray(r[k]) ? (r[k].length ? r[k].join(', ') : '—') : typeof r[k] === 'number' ? int(r[k]) : r[k] == null || r[k] === '' ? '—' : String(r[k]))}));
  return dtable(l.label, cols, l.detail);
}

function gatesTable(g) {
  const gates = Object.keys(g.table), cos = Object.keys(g.table[gates[0]] || {});
  const rows = cos.map((t) => ({ticker: t, ...Object.fromEntries(gates.map((x) => [x, g.table[x][t].length])), fails: gates.some((x) => g.table[x][t].length)}));
  return dtable('Release checks by company', [{t: 'Company', f: (r) => h('a', {href: '#proof/' + r.ticker}, r.ticker)}, ...gates.map((x) => ({t: x, num: 1, f: (r) => (r[x] ? h('span', {class: 'text-red fw-medium'}, int(r[x])) : h('span', {class: 'text-secondary'}, '·'))})),
    {t: 'Result', f: (r) => (r.fails ? h('span', {class: 'text-red'}, 'Fail') : h('span', {class: 'text-green'}, 'Pass'))}], rows);
}

function diffTable(cl) {
  const rows = Object.entries(cl.diff || {}).map(([k, x]) => ({list: k + '.csv', ...x}));
  if (!rows.length) return h('p', {class: 'text-secondary small'}, cl.previous ? '—' : 'First release');
  return dtable(`Changes since ${cl.previous}`, [{t: 'List', k: 'list'}, {t: 'Rows', num: 1, f: (r) => int(r.rows)}, {t: 'Added', num: 1, f: (r) => int(r.added)}, {t: 'Removed', num: 1, f: (r) => int(r.removed)}, {t: 'Changed', num: 1, f: (r) => int(r.changed)},
    {t: 'Columns', f: (r) => [r.columns_added.length ? `+${r.columns_added.length}` : '', r.columns_removed.length ? `−${r.columns_removed.length}` : ''].filter(Boolean).join(' ') || '—'}], rows);
}

async function releasePage(view, qs) {
  const q = parseQ(qs || '');
  const cl = await api('/api/v1/release/checklist' + (q.version ? `?version=${encodeURIComponent(q.version)}` : ''));
  const required = cl.lines.filter((l) => l.required), green = required.filter((l) => l.ok).length;
  const canSign = cl.ok && !!(me || '').trim();
  const why = !cl.ok ? `${required.length - green} required check${required.length - green === 1 ? '' : 's'} failing` : !(me || '').trim() ? 'Enter a signer name' : `Signs and publishes ${cl.version}`;
  const status = h('div', {class: 'text-secondary small', id: 'signmsg', role: 'status', 'aria-live': 'polite'}, why);
  const button = h('button', {type: 'button', class: 'btn btn-primary', disabled: !canSign, title: why, onclick: async () => {
    if (!confirm(`Sign and publish ${cl.version} as ${me}?`)) return;
    button.disabled = true;
    status.textContent = `Signing ${cl.version}…`;
    try {
      const r = await api('/api/release/sign', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({version: cl.version, by: me})});
      status.replaceChildren(h('span', {class: 'text-green'}, `${r.version} signed by ${r.signed_by} · ${when(r.signed_at)} · ${r.hash.slice(0, 8)}`), ' · ',
        r.published ? `Published: ${Object.entries(r.rows || {}).map(([k, v]) => `${int(v)} ${k}`).join(', ')}` : h('span', {class: 'text-red'}, `Signed, not published: ${r.publish_error}`));
      if (r.published) setTimeout(() => go('proof'), 2500);  // a failed publish stays on screen
    } catch (e) {
      status.replaceChildren(h('span', {class: 'text-red'}, e.message));
      button.disabled = !canSign;
    }
  }}, `Sign ${cl.version}`);
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Release'),
      h('div', {class: 'text-secondary small'}, h('b', {class: 'text-body'}, cl.version), cl.previous ? ` · Compared with ${cl.previous}` : ' · First release', ` · ${cl.scope.length} companies · `,
        h('b', {class: 'text-body'}, `${green} of ${required.length}`), ' required checks pass')),
    h('div', {class: 'col-auto text-end'}, button, status)));
  const lines = table([
    {t: 'State', f: stateBadge, s: (l) => ({fail: 0, not_run: 1, info: 2, pass: 3})[l.state]},
    {t: 'Check', k: 'label', f: (l) => h('span', {class: l.required ? '' : 'text-secondary'}, l.label)},
    {t: 'Count', n: 1, k: 'count', f: (l) => (l.state === 'not_run' ? '—' : int(l.count))},
    {t: 'Required', k: 'required', f: (l) => (l.required ? 'Required' : h('span', {class: 'text-secondary'}, 'Optional'))},
    {t: 'Details', k: 'note', f: (l) => h('span', {class: 'text-secondary small d-block text-truncate', style: 'max-width:26rem', title: l.note}, l.note)},
    {t: 'Fix in', sort: false, f: (l) => { if (!l.link) return ''; const pg = l.link.split('?')[0].split('/')[0]; return h('a', {href: '#' + l.link, onclick: (e) => e.stopPropagation()}, PAGE_NAME[pg] || pg); }},
  ], cl.lines, {detail: lineDetail});
  const files = cl.lines.find((l) => l.id === 'packet');
  const packet = dtable(`Packet ${cl.version}`, [{t: 'File', k: 'file'}, {t: 'Rows', num: 1, f: (r) => (r.rows == null ? '—' : int(r.rows))}, {t: 'Bytes', num: 1, f: (r) => int(r.bytes)}], files ? files.detail : [],
    {note: `Fingerprint ${cl.hash.slice(0, 8)}`});
  const checks = h('div', {class: 'row g-3 mt-1'}, h('div', {class: 'col-12 col-xl-7'}, gatesTable(cl.gates)), h('div', {class: 'col-12 col-xl-5'}, packet));
  view.append(head, lines,
    checks, h('div', {class: 'mt-3'}, diffTable(cl)));
}
