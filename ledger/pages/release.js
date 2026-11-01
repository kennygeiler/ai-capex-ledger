// ── Release: the checklist a person signs from (T5, T6, T8; docs/PROOF.md). Every line is something that could make
// the signature wrong, with its count and the page that fixes it. The server builds it (ledger/checklist.py); the
// page renders it as it is and recomputes nothing. ───────────────────────────────────────────────────────────────
const LINE_STATE = {pass: ['passes', 'bg-green-lt'], fail: ['fails', 'bg-red-lt'], info: ['info', 'bg-secondary-lt'], not_run: ['not run', 'bg-secondary-lt']};
const stateBadge = (l) => { const [word, cls] = LINE_STATE[l.state] || LINE_STATE.info; return h('span', {class: 'badge ' + cls}, word); };

// what a line's detail holds, as a table whose columns are the detail's own keys
function lineDetail(l) {
  if (!l.detail || !l.detail.length) return h('p', {class: 'text-secondary small m-0'}, l.state === 'pass' ? 'Nothing to show: the line passes.' : 'Nothing to show.');
  const keys = [...new Set(l.detail.flatMap((r) => Object.keys(r)))];
  const cols = keys.map((k) => ({t: k.replaceAll('_', ' '), k, num: typeof l.detail[0][k] === 'number', f: (r) => (Array.isArray(r[k]) ? (r[k].length ? r[k].join(', ') : '—') : typeof r[k] === 'number' ? int(r[k]) : r[k] == null || r[k] === '' ? '—' : String(r[k]))}));
  return dtable(l.label, cols, l.detail);
}

function gatesTable(g) {
  const gates = Object.keys(g.table), cos = Object.keys(g.table[gates[0]] || {});
  const rows = cos.map((t) => ({ticker: t, ...Object.fromEntries(gates.map((x) => [x, g.table[x][t].length])), fails: gates.some((x) => g.table[x][t].length)}));
  return dtable('Gates per company', [{t: 'Company', f: (r) => h('a', {href: '#proof/' + r.ticker}, r.ticker)}, ...gates.map((x) => ({t: x, num: 1, f: (r) => (r[x] ? h('span', {class: 'badge bg-red-lt'}, int(r[x])) : h('span', {class: 'text-secondary'}, '·'))})),
    {t: 'Result', f: (r) => (r.fails ? h('span', {class: 'text-red'}, 'fails') : h('span', {class: 'text-green'}, 'passes'))}], rows, {note: 'the count of failing items per gate; · passes'});
}

function diffTable(cl) {
  const rows = Object.entries(cl.diff || {}).map(([k, x]) => ({list: k + '.csv', ...x}));
  if (!rows.length) return h('p', {class: 'text-secondary small'}, cl.previous ? 'No lists to compare.' : 'First release: nothing to diff against.');
  return dtable(`Rows against ${cl.previous}`, [{t: 'List', k: 'list'}, {t: 'Rows', num: 1, f: (r) => int(r.rows)}, {t: 'Added', num: 1, f: (r) => int(r.added)}, {t: 'Removed', num: 1, f: (r) => int(r.removed)}, {t: 'Changed', num: 1, f: (r) => int(r.changed)},
    {t: 'Key', f: (r) => r.key.join(' + ')}, {t: 'Columns', f: (r) => [r.columns_added.length ? `+${r.columns_added.length}` : '', r.columns_removed.length ? `−${r.columns_removed.length}` : ''].filter(Boolean).join(' ') || '—'}], rows,
    {note: 'a row is changed when a column both releases carry differs; DIFF.md lists the examples'});
}

async function releasePage(view, qs) {
  const q = parseQ(qs || '');
  const cl = await api('/api/v1/release/checklist' + (q.version ? `?version=${encodeURIComponent(q.version)}` : ''));
  const required = cl.lines.filter((l) => l.required), green = required.filter((l) => l.ok).length;
  const canSign = cl.ok && !!(me || '').trim();
  const why = !cl.ok ? `${required.length - green} required line${required.length - green === 1 ? '' : 's'} red` : !(me || '').trim() ? 'type your name in the signer box first' : `signs ${cl.version} as ${me}, then publishes it`;
  const status = h('div', {class: 'text-secondary small', id: 'signmsg', role: 'status', 'aria-live': 'polite'}, why);
  const button = h('button', {type: 'button', class: 'btn btn-primary', disabled: !canSign, title: why, onclick: async () => {
    if (!confirm(`Sign ${cl.version} as ${me}? This writes releases/${cl.version}/, records the checklist as it is now in SIGNOFF.json, and publishes the signed files to production.`)) return;
    button.disabled = true;
    status.textContent = `Signing ${cl.version}…`;
    try {
      const r = await api('/api/release/sign', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({version: cl.version, by: me})});
      status.replaceChildren(h('span', {class: 'text-green'}, `${r.version} signed by ${r.signed_by}, ${when(r.signed_at)} (${r.hash.slice(0, 12)})`), ' · ',
        r.published ? `published: ${Object.entries(r.rows || {}).map(([k, v]) => `${int(v)} ${k}`).join(', ')}` : h('span', {class: 'text-red'}, `not published: ${r.publish_error}; run ledger publish ${r.version}`));
      setTimeout(() => go('proof'), 2500);
    } catch (e) {
      status.replaceChildren(h('span', {class: 'text-red'}, e.message));
      button.disabled = !canSign;
    }
  }}, `Sign ${cl.version}`);
  const head = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Release'),
      h('div', {class: 'text-secondary small'}, h('b', {class: 'text-body'}, cl.version), cl.previous ? ` against ${cl.previous}` : ', the first release', `. ${cl.scope.length} companies in scope: ${cl.scope.join(', ')}. `,
        h('b', {class: 'text-body'}, `${green} of ${required.length}`), ' required lines green. Each line counts what could make the signature wrong and links to the page that fixes it; the packet is built in memory until you sign.')),
    h('div', {class: 'col-auto text-end'}, button, status)));
  const lines = table([
    {t: 'State', f: stateBadge, s: (l) => ({fail: 0, not_run: 1, info: 2, pass: 3})[l.state]},
    {t: 'Line', k: 'label', f: (l) => h('span', {class: l.required ? '' : 'text-secondary'}, l.label)},
    {t: 'Count', n: 1, k: 'count', f: (l) => (l.state === 'not_run' ? '—' : int(l.count))},
    {t: 'Required', k: 'required', f: (l) => (l.required ? 'yes' : h('span', {class: 'text-secondary'}, 'informs'))},
    {t: 'Note', k: 'note', f: (l) => h('span', {class: 'text-secondary small'}, l.note)},
    {t: 'Fix on', sort: false, f: (l) => (l.link ? h('a', {href: '#' + l.link, onclick: (e) => e.stopPropagation()}, l.link.split('?')[0].split('/')[0]) : '')},
  ], cl.lines, {detail: lineDetail});
  const files = cl.lines.find((l) => l.id === 'packet');
  const packet = dtable(`Packet ${cl.version}`, [{t: 'File', k: 'file'}, {t: 'Rows', num: 1, f: (r) => (r.rows == null ? '—' : int(r.rows))}, {t: 'Bytes', num: 1, f: (r) => int(r.bytes)}], files ? files.detail : [],
    {note: `hash ${cl.hash.slice(0, 12)}`});
  const checks = h('div', {class: 'row g-3 mt-1'}, h('div', {class: 'col-12 col-xl-7'}, gatesTable(cl.gates)), h('div', {class: 'col-12 col-xl-5'}, packet));
  view.append(head, lines, h('p', {class: 'text-secondary small mt-2'}, 'A line opens to its items. Required lines must all pass before the Sign button enables; the rest inform. Golden reads reports/golden.json, the test run reports/tests.json ({ok, count, failures, at}); either absent reads "not run".'),
    checks, h('div', {class: 'mt-3'}, diffTable(cl)));
}
