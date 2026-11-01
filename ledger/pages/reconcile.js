// ── Reconcile: the workbench, on Tabler (dashboard UI kit) inside its own shadow root so the kit's reset touches nothing else. ──
// One card per cause; one row per item with ours, reference, a gap bar, delta and decision; Enter opens the evidence as
// aligned diff tables (this year, the computation, every year) with a status badge per line, and the decision form.
const CAUSE_ORDER = ['to_confirm', 'blocked', 'fact_differs', 'fact_changed', 'finding_unconfirmed', 'new_filing'];
const RES_LABEL = {accept: 'Accept', explain: 'Explain', fix: 'Fix', blocks: 'Blocks'};
const RES_HELP = {accept: 'the number is right as it stands', explain: 'right, with the reason kept beside it', fix: 'wrong, stays open until a run fixes it', blocks: 'nothing ships until this is settled'};
const RES_BADGE = {accept: 'bg-green-lt', explain: 'bg-azure-lt', fix: 'bg-yellow-lt', blocks: 'bg-red-lt'};
// the one definition of open (status.state, docs/PROOF.md): every row carries state and by; the page only shows them
const STATE_BADGE = {checked: 'bg-green-lt', explained: 'bg-azure-lt', open: 'bg-yellow-lt', blocked: 'bg-red-lt', 'to confirm': 'bg-orange-lt'};
const STATE_HELP = {checked: 'agrees with an independent check', explained: 'something on file says why, by name', open: 'nothing on file applies; a person decides', blocked: 'refuses the release until settled', 'to confirm': 'a run decided; a person confirms or overturns'};
const BY_WORD = {rule: 'rule', definition: 'definition', label: 'label', resolution: 'resolution', mapping: 'mapping', xbrl: 'XBRL', quote: 'quote', located: 'located'};
const byText = (by) => { if (!by) return ''; const [k, ...rest] = by.split(':'); const v = rest.join(':'); return v ? `${BY_WORD[k] || k}: ${v}` : BY_WORD[k] || k; };
const stateCell = (r) => [h('span', {class: 'badge ' + (STATE_BADGE[r.state] || 'bg-secondary-lt'), title: STATE_HELP[r.state] || r.state}, r.state), r.by ? h('div', {class: 'text-secondary small font-monospace', style: 'font-size:.72rem'}, byText(r.by)) : ''];
let FOCUS_KEY = null;  // the row to focus after a save re-renders the page
const num = (r, v) => (v == null ? '—' : r.measure === 'share' ? pct(v) : usd(v));
const signed = (r, v) => (v == null ? '—' : (v < 0 ? '−' : '+') + (r.measure === 'share' ? `${(100 * Math.abs(v)).toFixed(1)} pts` : usd(Math.abs(v))));
const pctSigned = (x) => (x == null ? '—' : `${x < 0 ? '−' : '+'}${(100 * Math.abs(x)).toFixed(Math.abs(x) < .1 ? 1 : 0)}%`);
// a gap bar: one scale, ours as a bar, the stated figure as a tick with a band for where it allows
function gapBar(r, large) {
  const share = r.measure === 'share';
  const max = share ? 1 : Math.max(Math.abs(r.ours || 0), Math.abs(r.reference || 0)) * 1.15 || 1;
  const p = (v) => `${(100 * Math.max(0, Math.min(1, Math.abs(v) / max))).toFixed(1)}%`;
  const ref = r.reference, ours = r.ours;
  const from = r.relation === 'ge' ? ref : r.relation === 'le' ? 0 : ref * 0.9, to = r.relation === 'ge' ? max : r.relation === 'le' ? ref : ref * 1.1;
  const inside = ours != null && ref != null && (r.relation === 'ge' ? ours >= ref : r.relation === 'le' ? ours <= ref : Math.abs(ours - ref) <= 0.1 * Math.abs(ref));
  const el = h('div', {class: 'gg' + (large ? ' lg' : ''), role: 'img', 'aria-label': `Ours ${num(r, ours)} against ${({ge: 'at least ', le: 'at most '})[r.relation] || ''}${num(r, ref)}`});
  if (ref != null) el.append(h('div', {class: 'band', style: `left:${p(from)};width:calc(${p(to)} - ${p(from)})`}), h('div', {class: 'tick', style: `left:${p(ref)}`}));
  if (ours != null) el.append(h('div', {class: 'ours', style: `width:${p(ours)}`}));
  if (ours != null && ref != null && !inside) { const a = Math.min(ours, ref), b = Math.max(ours, ref); el.append(h('div', {class: 'gap', style: `left:${p(a)};width:calc(${p(b)} - ${p(a)})`})); }
  return el;
}
const badge = (text, cls) => h('span', {class: 'badge ' + (cls || 'bg-secondary-lt')}, text);
const checkBadge = (label) => (label == null ? '' : label === 'agree' ? badge('SEC agrees', 'bg-green-lt') : label === 'not_reported' ? badge('not reported', 'bg-secondary-lt') : label === 'no_reference' ? badge('no tag', 'bg-secondary-lt') : label === 'definition_gap' ? badge('explained', 'bg-azure-lt') : badge('differs from SEC', 'bg-yellow-lt'));
const bar = (v, max, cls) => h('span', {class: 'bar ' + (cls || ''), style: `width:${Math.max(2, 44 * Math.abs(v || 0) / (max || 1)).toFixed(0)}px`});
async function reconcilePage(view, qs) {
  const q = parseQ(qs || '');
  const scope = q.scope || 'all', group = q.group || 'cause', fCause = q.cause || '', fLayer = q.layer || '', fField = q.field || '', withResolved = q.resolved === '1';
  const d = await api('/api/v1/reconcile?scope=' + encodeURIComponent(scope));
  const wrap = h('div', {class: 'stack', style: 'gap:.75rem'});
  view.append(wrap);
  const setQ = (patch) => { const p = {scope, group, cause: fCause, layer: fLayer, field: fField, kind: q.kind || '', resolved: withResolved ? '1' : '', ...patch}; go('reconcile?' + new URLSearchParams(Object.fromEntries(Object.entries(p).filter(([, v]) => v))).toString()); };
  const isOpen = (r) => !!r.open;  // the server's word (row.open: open or blocked), never recomputed here
  const toConfirm = (r) => r.cause === 'to_confirm';
  let rows = d.rows.filter((r) => withResolved || isOpen(r) || toConfirm(r));
  if (fCause) rows = rows.filter((r) => r.cause === fCause);
  if (fLayer) rows = rows.filter((r) => r.layer === fLayer);
  if (fField) rows = rows.filter((r) => (r.field || '') === fField);
  const hidden = d.rows.filter((r) => !isOpen(r) && !toConfirm(r)).length;
  const fKind = q.kind || '';
  if (fKind) rows = rows.filter((r) => (r.evidence && r.evidence.kind) === fKind);
  const kinds = [...new Set(d.rows.map((r) => r.evidence && r.evidence.kind).filter(Boolean))].sort();
  const KINDL = {restated: 'Restated', jump: 'Big move', row_switch: 'Line renamed', capex_intensity: 'Capex vs revenue', opex_over_revenue: 'Opex above revenue'};
  const causes = CAUSE_ORDER.filter((c) => d.rows.some((r) => r.cause === c)), layers = [...new Set(d.rows.map((r) => r.layer))].sort(), fields = [...new Set(d.rows.map((r) => r.field).filter(Boolean))].sort();
  const sel = (label, value, opts, key) => h('select', {class: 'form-select form-select-sm', 'aria-label': label, onchange: (e) => setQ({[key]: e.target.value})}, opts.map(([v, t]) => h('option', {value: v, selected: v === value || null}, t)));
  const openRows = rows.filter(isOpen);
  const nState = (s) => d.rows.filter((r) => r.state === s).length;
  const header = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Reconcile'), h('div', {class: 'text-secondary small'}, `${int(d.to_confirm)} to confirm, ${int(nState('open'))} open, ${int(nState('blocked'))} blocked, ${int(nState('explained'))} explained, ${usd(openRows.reduce((s, r) => s + (r.dollars || 0), 0))} at stake. Last run ${day(d.last_run)}${d.release ? `, signed ${d.release}` : ''}. Keys: j k move, Enter opens, a e f b decide, space selects.`))));
  const controls = h('div', {class: 'card mb-3'}, h('div', {class: 'card-body py-2'}, h('div', {class: 'row g-2 align-items-center'},
    h('div', {class: 'col-auto'}, sel('Scope', scope, [['all', 'All companies'], ...layers.map((l) => [l, INDUSTRY[l] || l]), ...Object.keys(d.names).sort().map((t) => [t, `${d.names[t]} (${t})`])], 'scope')),
    h('div', {class: 'col-auto'}, sel('Group by', group, [['cause', 'Grouped by cause'], ['company', 'Grouped by company']], 'group')),
    h('div', {class: 'col-auto'}, sel('Cause', fCause, [['', 'Every cause'], ...causes.map((c) => [c, d.causes.find((x) => x.cause === c)?.label || c])], 'cause')),
    h('div', {class: 'col-auto'}, sel('Layer', fLayer, [['', 'Every layer'], ...layers.map((l) => [l, INDUSTRY[l] || l])], 'layer')),
    h('div', {class: 'col-auto'}, sel('Field', fField, [['', 'Every field'], ...fields.map((f) => [f, LABEL[f] || f])], 'field')),
    kinds.length ? h('div', {class: 'col-auto'}, sel('Finding kind', fKind, [['', 'Every finding kind'], ...kinds.map((k) => [k, KINDL[k] || k.replaceAll('_', ' ')])], 'kind')) : '',
    h('div', {class: 'col-auto ms-auto'}, h('label', {class: 'form-check form-switch m-0'}, h('input', {class: 'form-check-input', type: 'checkbox', checked: withResolved || null, onchange: (e) => setQ({resolved: e.target.checked ? '1' : ''})}), h('span', {class: 'form-check-label small'}, `show ${int(hidden)} resolved`))))));
  const selected = new Set();
  let cur = -1;
  const trs = [];
  const bulk = h('div', {class: 'card mb-3', hidden: true});
  const groups = new Map();
  const keyOf = (r) => (group === 'cause' ? r.cause : r.ticker);
  const ordered = [...rows].sort((a, b) => (group === 'cause' ? CAUSE_ORDER.indexOf(a.cause) - CAUSE_ORDER.indexOf(b.cause) || b.dollars - a.dollars || a.ticker.localeCompare(b.ticker) : a.name.localeCompare(b.name) || CAUSE_ORDER.indexOf(a.cause) - CAUSE_ORDER.indexOf(b.cause) || b.dollars - a.dollars));
  for (const r of ordered) groups.set(keyOf(r), [...(groups.get(keyOf(r)) || []), r]);
  const cards = [];
  for (const [g, list] of groups) {
    const label = group === 'cause' ? list[0].cause_label.replace(/:.*$/, '') : `${list[0].name} ${list[0].ticker}`;
    const open = list.filter(isOpen);
    const tbody = h('tbody');
    for (const r of list) {
      const i = trs.length;
      const cb = h('input', {class: 'form-check-input m-0', type: 'checkbox', 'aria-label': `Select ${r.name} ${r.where}`, checked: selected.has(r.key) || null, onclick: (e) => { e.stopPropagation(); e.target.checked ? selected.add(r.key) : selected.delete(r.key); paint(); }});
      const first = group === 'cause' ? [h('a', {href: `#proof/${r.ticker}`, onclick: (e) => e.stopPropagation()}, r.name), ' ', h('span', {class: 'text-secondary small'}, r.ticker)] : [r.cause_label.replace(/:.*$/, '')];
      const where = [h('div', {}, r.field ? (LABEL[r.field] || r.field) : r.where, r.period ? ` ${r.period}` : ''), r.evidence.dimension ? h('div', {class: 'text-secondary small'}, r.evidence.dimension) : r.cause === 'finding_unconfirmed' && r.measure == null ? h('div', {class: 'text-secondary small'}, r.cause_label) : ''];
      const res = toConfirm(r) ? confirmCell(r, i) : [stateCell(r), r.resolution && r.resolution.by ? h('div', {class: 'text-secondary small'}, `${RES_LABEL[r.resolution.state] || r.resolution.state} by ${r.resolution.by}, ${day(r.resolution.at)}`) : ''];
      const tr = h('tr', {class: 'item', tabindex: 0, 'aria-expanded': 'false', onkeydown: (e) => keys(e, i), onclick: () => toggle(i), onfocus: () => { cur = i; paintCur(); }},
        h('td', {class: 'w-1'}, cb), h('td', {}, first), h('td', {}, where),
        h('td', {class: 'num'}, num(r, r.ours), r.ours_label ? h('div', {class: 'text-secondary small'}, r.ours_label) : ''),
        h('td', {class: 'num'}, r.reference == null ? h('span', {class: 'text-secondary'}, '—') : [({ge: '≥ ', le: '≤ '})[r.relation] || '', num(r, r.reference)], r.ref_label && r.reference != null ? h('div', {class: 'text-secondary small'}, r.ref_label) : ''),
        h('td', {class: 'w-1'}, r.ours != null && r.reference != null ? gapBar(r) : ''),
        h('td', {class: 'num'}, r.delta == null ? h('span', {class: 'text-secondary'}, r.ours != null || r.reference != null ? 'one side' : '—') : [h('span', {class: 'fw-semibold' + (r.cause === 'fact_differs' ? ' text-red' : '')}, signed(r, r.delta)), r.delta_pct != null && r.measure !== 'share' ? h('div', {class: 'text-secondary small'}, pctSigned(r.delta_pct)) : r.measure === 'share' && r.dollars ? h('div', {class: 'text-secondary small'}, `${usd(r.dollars)} at stake`) : '']),
        h('td', {}, res));
      trs.push({tr, r, detail: null});
      tbody.append(tr);
    }
    const confirmGroup = group === 'cause' && toConfirm(list[0]);
    cards.push(h('div', {class: 'card mb-3'},
      h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, label), h('span', {class: 'ms-2 text-secondary small'}, confirmGroup ? `${int(list.length)} decisions a run made; the release refuses until each is confirmed or overturned` : `${int(open.length)} open of ${int(list.length)}${list.some((r) => r.dollars) ? `, ${usd(list.reduce((s, r) => s + r.dollars, 0))} at stake` : ''}`),
        open.length > 1 ? h('button', {type: 'button', class: 'btn btn-sm btn-ghost-secondary ms-auto', onclick: () => { for (const r of open) selected.add(r.key); paint(); }}, `Select all ${int(open.length)}`) : ''),
      h('div', {class: 'table-responsive'}, h('table', {class: 'table table-vcenter card-table table-hover'},
        h('thead', {}, h('tr', {}, h('th', {class: 'w-1'}, h('span', {class: 'visually-hidden'}, 'Select')), h('th', {}, group === 'cause' ? 'Company' : 'Cause'), h('th', {}, 'Where'), h('th', {class: 'num'}, 'Ours'), h('th', {class: 'num'}, 'Reference'), h('th', {class: 'w-1'}, 'Gap'), h('th', {class: 'num'}, 'Delta'), h('th', {}, 'Decision'))),
        tbody))));
  }
  function paint() { for (const t of trs) t.tr.querySelector('input[type=checkbox]').checked = selected.has(t.r.key); bulk.hidden = selected.size === 0; const selRows = [...selected].map((k) => trs.find((t) => t.r.key === k).r); bulk.replaceChildren(h('div', {class: 'card-body py-2'}, h('div', {class: 'row g-2 align-items-center'}, h('div', {class: 'col-12 small text-secondary'}, h('b', {class: 'text-body'}, int(selected.size)), ' selected: ', selRows.map((r) => `${r.ticker} ${r.where}`).join('; ')), h('div', {class: 'col'}, resolutionForm(null, [...selected].map((k) => trs.find((t) => t.r.key === k).r), () => { selected.clear(); paint(); })), h('div', {class: 'col-auto'}, h('button', {type: 'button', class: 'btn btn-sm btn-ghost-secondary', onclick: () => { selected.clear(); paint(); }}, 'Clear'))))); }
  function paintCur() { trs.forEach((t, j) => t.tr.classList.toggle('cur', j === cur)); }
  function toggle(i, force) {
    const t = trs[i]; cur = i; paintCur();
    if (t.detail && force !== true) { t.detail.remove(); t.detail = null; t.tr.setAttribute('aria-expanded', 'false'); return; }
    if (t.detail) return;
    t.detail = h('tr', {class: 'ev'}, h('td', {colspan: 8}, evidence(t.r)));
    t.tr.after(t.detail); t.tr.setAttribute('aria-expanded', 'true');
  }
  function keys(e, i) {
    if (e.target.matches('input, select, textarea, button') || e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key;
    if (k === 'j' || k === 'ArrowDown') { e.preventDefault(); trs[Math.min(trs.length - 1, i + 1)].tr.focus(); }
    else if (k === 'k' || k === 'ArrowUp') { e.preventDefault(); trs[Math.max(0, i - 1)].tr.focus(); }
    else if (k === 'Enter' || k === 'o') { e.preventDefault(); toggle(i); }
    else if (k === ' ') { e.preventDefault(); const r = trs[i].r; selected.has(r.key) ? selected.delete(r.key) : selected.add(r.key); paint(); }
    else if (k === 'Escape' && trs[i].detail) { toggle(i); }
    else if ('aefb'.includes(k) && k) { e.preventDefault(); toggle(i, true); const btn = trs[i].detail.querySelector(`[data-state=${({a: 'accept', e: 'explain', f: 'fix', b: 'blocks'})[k]}]`); btn.click(); trs[i].detail.querySelector('input[type=text]').focus(); }
  }
  // T3: a decision a run made. Confirm records the proposed state on the same key, by me, reason "confirmed";
  // Overturn opens the normal decide flow (the evidence row with the form).
  function confirmCell(r, i) {
    const proposed = (r.evidence && r.evidence.proposed) || (r.resolution && r.resolution.state) || 'explain';
    const status = h('span', {class: 'text-secondary small', 'aria-live': 'polite'});
    const confirm = h('button', {type: 'button', class: 'btn btn-sm btn-primary', title: `Record ${RES_LABEL[proposed] || proposed} on this item as ${me}`, onclick: async (e) => {
      e.stopPropagation(); confirm.disabled = true; status.textContent = 'Saving…';
      try {
        await api('/api/resolve', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({key: r.key, hash: r.hash, state: proposed, reason: 'confirmed', by: me})});
        status.textContent = 'Confirmed.'; FOCUS_KEY = r.key; setTimeout(route, 250);
      } catch (err) { status.textContent = `Couldn’t save: ${err.message}.`; status.classList.add('text-red'); confirm.disabled = false; }
    }}, `Confirm ${RES_LABEL[proposed] || proposed}`);
    const overturn = h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary', title: 'Decide differently: opens the decision form', onclick: (e) => { e.stopPropagation(); toggle(i, true); const f = trs[i].detail.querySelector('input[type=text]'); if (f) f.focus(); }}, 'Overturn');
    return [h('div', {class: 'btn-list flex-nowrap'}, confirm, overturn), h('div', {class: 'text-secondary small mt-1'}, byText(r.by), r.resolution && r.resolution.at ? `, ${day(r.resolution.at)}` : ''), status];
  }
  function resolutionForm(r, many, done) {
    const items = many || [r];
    let state = r && r.resolution ? r.resolution.state : 'accept';
    const btns = Object.keys(RES_LABEL).map((s) => h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary' + (s === state ? ' active' : ''), 'data-state': s, 'aria-pressed': String(s === state), title: RES_HELP[s], onclick: (e) => { state = s; e.currentTarget.parentNode.querySelectorAll('.btn').forEach((b) => { b.classList.toggle('active', b.dataset.state === s); b.setAttribute('aria-pressed', String(b.dataset.state === s)); }); }}, RES_LABEL[s]));
    const reason = h('input', {type: 'text', class: 'form-control form-control-sm', name: 'reason', autocomplete: 'off', placeholder: many ? `Why, for all ${items.length}, e.g. accrual capex, cash basis differs` : 'e.g. includes finance leases, note 7', 'aria-label': 'Reason', value: r && r.resolution ? r.resolution.reason : '', onkeydown: (e) => { if (e.key === 'Enter') save.click(); }});
    const status = h('span', {class: 'text-secondary small', 'aria-live': 'polite'});
    const save = h('button', {type: 'button', class: 'btn btn-sm btn-primary', onclick: async () => {
      if (!reason.value.trim()) { reason.focus(); status.textContent = 'A reason is required.'; return; }
      save.disabled = true; status.textContent = 'Saving…';
      try {
        if (many) await api('/api/resolve/bulk', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({items: items.map((x) => ({key: x.key, hash: x.hash})), state, reason: reason.value, by: me})});
        else await api('/api/resolve', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({key: r.key, hash: r.hash, state, reason: reason.value, by: me})});
        status.classList.remove('text-red'); status.textContent = 'Saved.'; FOCUS_KEY = many ? items[0].key : r.key; if (done) done(); setTimeout(route, 250);
      } catch (e) { status.textContent = `Couldn’t save: ${e.message}. Try again.`; status.classList.add('text-red'); }
      finally { save.disabled = false; }
    }}, many ? `Save for ${items.length}` : 'Save');
    return h('div', {class: 'row g-2 align-items-center'}, h('div', {class: 'col-auto'}, h('div', {class: 'btn-group', role: 'group', 'aria-label': 'Decision'}, btns)), h('div', {class: 'col'}, h('div', {class: 'input-group input-group-sm'}, reason, save)), h('div', {class: 'col-12'}, status));
  }
  function definitionDrawer(r) {
    const E = r.evidence || {}, X = E.xbrl;
    const yaml = `definitions/companies.yaml\n\n${r.ticker}:\n  ${r.field}:\n    dimension: "${E.dimension || ''}"\n    use: cell            # cell | tag\n    why: ${X ? `the tag ${X.concept}${X.member ? ' / ' + X.member : ''} measures a wider line than the table` : '…'}\n    by: ${me}\n    at: ${new Date().toISOString().slice(0, 10)}`;
    drawer(h('h3', {}, 'Add a definition'), h('p', {class: 'small'}, 'A judgement made once per company and applied every run: which of the cell and the tag the dataset should carry for this fact, and why. Paste it into definitions/companies.yaml, then rerun notes and rules.'),
      h('pre', {class: 'raw', style: 'margin-top:.8rem'}, yaml), h('button', {type: 'button', class: 'btn', style: 'margin-top:.8rem', onclick: (e) => { navigator.clipboard?.writeText(yaml).then(() => { e.target.textContent = 'Copied'; }, () => {}); }}, 'Copy'));
  }
  function evidence(r) {
    const E = r.evidence || {}, S = r.series || [], cards = [];
    const col = (n, ...k) => h('div', {class: `col-12 col-xl-${n}`}, k);
    const yr = S.find((s) => s.period === r.period) || {};
    if (r.cause === 'fact_differs') {
      const c = E.cell;
      const X = E.xbrl, cellAcc = c ? c.accession : null;
      const lines = [{what: 'Cited cell', value: r.ours, src: c ? `${c.table_id}, “${c.row_label}”, filing ${c.accession}` : '', _cls: 'fw-semibold'},
        {what: 'XBRL tag', value: r.reference, src: X ? [h('span', {class: 'font-monospace'}, X.concept), X.member ? [' / ', h('span', {class: 'font-monospace'}, X.member)] : '', ` as of ${X.date}, filing ${X.accession}`, cellAcc && X.accession !== cellAcc ? h('div', {class: 'text-body mt-1'}, h('span', {class: 'fw-semibold'}, 'Different filings: '), 'the cell is from a later 10-K than the tag; a restatement, not a disagreement.') : ''] : 'the filing’s own data; concept not found in the instance'}, E.release_value != null ? {what: `In ${d.release}`, value: Number(E.release_value), src: 'signed'} : null, {what: 'Delta', value: r.delta, src: pctSigned(r.delta_pct), _cls: 'text-red'}].filter(Boolean);
      const maxL = Math.max(1, ...lines.filter((l) => l.what !== 'Delta').map((l) => Math.abs(l.value || 0)));
      cards.push(col(4, dtable(`${r.period}: the cited cell against the filing’s tag`, [{t: '', f: (x) => [h('div', {}, x.what), x.src ? h('div', {class: 'text-secondary small fw-normal'}, x.src) : '']}, {t: 'Amount', num: 1, f: (x) => (x.what === 'Delta' ? signed(r, x.value) : [bar(x.value, maxL, x.what === 'Cited cell' ? '' : 'ref'), usd(x.value)])}], lines),
        h('div', {class: 'card mt-3'}, h('div', {class: 'card-body py-2'}, gapBar(r, true), h('div', {class: 'd-flex justify-content-between small text-secondary'}, h('span', {}, 'cell ', h('b', {class: 'text-primary'}, usd(r.ours))), h('span', {}, 'tag ', h('b', {}, usd(r.reference))))))));
      cards.push(col(4, h('div', {class: 'card'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, 'The cell')), h('div', {class: 'card-body py-2'}, c ? h('div', {class: 'datagrid'},
          h('div', {class: 'datagrid-item'}, h('div', {class: 'datagrid-title'}, 'Cell'), h('div', {class: 'datagrid-content fw-semibold'}, c.cell_text)),
          h('div', {class: 'datagrid-item'}, h('div', {class: 'datagrid-title'}, 'Row'), h('div', {class: 'datagrid-content'}, c.row_label)),
          h('div', {class: 'datagrid-item'}, h('div', {class: 'datagrid-title'}, 'Column'), h('div', {class: 'datagrid-content'}, (c.column_label || '').replaceAll(' | ', ' '))),
          h('div', {class: 'datagrid-item'}, h('div', {class: 'datagrid-title'}, 'Table'), h('div', {class: 'datagrid-content'}, c.table_id))) : h('p', {class: 'text-secondary small m-0'}, 'No citation on record.'),
          E.png ? h('img', {src: E.png, alt: `Screenshot of the cited cell ${c ? c.cell_text : ''}`, loading: 'lazy', class: 'shot mt-2'}) : '',
          h('div', {class: 'mt-2'}, E.url ? h('a', {href: E.url, target: '_blank', rel: 'noopener', class: 'small me-3'}, 'Open the 10-K') : '', h('a', {href: `#proof/${r.ticker}`, class: 'small'}, 'The company\'s trail')))),
        
        h('div', {class: 'mt-3'}, h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary', onclick: () => definitionDrawer(r)}, 'Add a definition'))));
      const maxY = Math.max(1e-9, ...S.flatMap((s) => [Math.abs(s.value || 0), Math.abs(s.reference || 0)]));
      cards.push(col(4, dtable('Every year, cell against tag', [{t: 'Year', k: 'period', w: '4rem'}, {t: 'Cell', num: 1, f: (s) => (s.value == null ? '—' : [bar(s.value, maxY), usd(s.value)])}, {t: 'Tag', num: 1, f: (s) => (s.reference == null ? h('span', {class: 'text-secondary'}, '—') : [bar(s.reference, maxY, 'ref'), usd(s.reference)])}, {t: 'Delta', num: 1, f: (s) => (s.reference == null || s.value == null ? '' : h('span', {class: s.label === 'unresolved' ? 'text-red' : ''}, signed({measure: 'usd'}, s.value - s.reference)))}, {t: '', f: (s) => checkBadge(s.label)}], S.map((s) => ({...s, _cls: s.period === r.period ? 'table-active' : null})))));
    } else if (r.cause === 'fact_changed') {
      const before = {what: E.release || 'Release', value: r.reference};
      const after = {what: 'Now', value: r.ours, _cls: 'fw-semibold'};
      const maxL = Math.max(1, Math.abs(before.value || 0), Math.abs(after.value || 0));
      cards.push(col(5, dtable(`${r.period}: before and after`, [{t: '', k: 'what'}, {t: 'Amount', num: 1, f: (x) => (x.what === 'Delta' ? signed(r, x.value) : [bar(x.value, maxL, x === before ? 'ref' : ''), usd(x.value)])}], [before, after, {what: 'Delta', value: r.delta, _cls: 'text-red'}])));
      cards.push(col(3, h('a', {href: `#proof/${r.ticker}`, class: 'small'}, 'The company\'s trail')));
    } else if (r.cause === 'finding_unconfirmed' || r.cause === 'blocked') {
      if (r.measure) {
        const maxL = Math.max(1, Math.abs(r.ours || 0), Math.abs(r.reference || 0));
        cards.push(col(4, dtable(r.cause_label.replace(/:.*$/, ''), [{t: '', k: 'what'}, {t: 'Amount', num: 1, f: (x) => (x.what === 'Delta' ? [signed(r, x.value), E.kind === 'jump' && E.size != null ? h('span', {class: 'text-secondary small'}, ` ${Number(E.size).toFixed(1)}×`) : ''] : [bar(x.value, maxL, x.what === r.ours_label ? '' : 'ref'), usd(x.value)])}], [{what: r.ref_label || 'before', value: r.reference}, {what: r.ours_label || 'after', value: r.ours, _cls: 'fw-semibold'}, {what: 'Delta', value: r.delta, _cls: 'text-red'}])));
      }
      if (S.length > 1) { const maxY = Math.max(1e-9, ...S.map((s) => Math.abs(s.value || 0))); cards.push(col(4, dtable(`${LABEL[r.field] || r.field} by year`, [{t: 'Year', k: 'period', w: '4rem'}, {t: 'Value', num: 1, f: (s) => (s.value == null ? '—' : [bar(s.value, maxY), usd(s.value)])}, {t: '', f: (s) => checkBadge(s.label)}], S.map((s) => ({...s, _cls: s.period === r.period ? 'table-active' : null}))))); }
      cards.push(col(4, h('details', {class: 'words', open: true}, h('summary', {}, 'The finding, in words'), h('div', {class: 'small'}, E.message || '')), h('div', {class: 'mt-2'}, h('a', {href: `#data?view=grid&t=${r.ticker}&f=${r.field || 'capex'},capex`, class: 'small'}, 'The dataset, with every citation'))));
    } else if (toConfirm(r)) {
      const p = r.resolution || {};
      cards.push(col(8, h('div', {class: 'card'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, `The run proposed: ${RES_LABEL[E.proposed] || E.proposed}`), h('span', {class: 'ms-2 small text-secondary'}, `${p.by || ''}, ${day(p.at)}`)),
        h('div', {class: 'card-body py-2'}, h('p', {class: 'm-0'}, E.message || p.reason || ''), h('p', {class: 'text-secondary small mt-2 mb-0'}, 'Confirm records the same state under your name; a different decision below overturns it. Either way the item leaves this group and the release gate G6 counts one fewer.')),
        h('div', {class: 'card-footer py-2'}, h('a', {href: `#proof/${r.ticker}`, class: 'small'}, 'The company\'s trail')))));
    } else if (r.cause === 'new_filing') {
      cards.push(col(6, h('div', {class: 'card'}, h('div', {class: 'card-body'}, `${E.form} filed ${day(E.filed)}. `, h('a', {href: E.url, target: '_blank', rel: 'noopener'}, 'Open at the SEC'), ' · ', h('a', {href: '#run'}, 'Run it')))));
    }
    const decision = h('div', {class: 'col-12'}, h('div', {class: 'card'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, toConfirm(r) ? 'Overturn: your own decision' : 'Decision'), r.resolution && !toConfirm(r) ? h('span', {class: 'ms-2 small text-secondary'}, `${RES_LABEL[r.resolution.state]} by ${r.resolution.by}, ${day(r.resolution.at)}: ${r.resolution.reason}`) : ''), h('div', {class: 'card-body py-2'}, resolutionForm(r))));
    return h('div', {class: 'row g-3'}, cards, decision);
  }
  wrap.append(header, controls, bulk, ...(cards.length ? cards : [h('div', {class: 'card'}, h('div', {class: 'card-body text-secondary'}, 'Nothing open for this scope.'))]),
    d.noise ? h('p', {class: 'text-secondary small'}, `${int(d.noise)} more facts differ from the filing’s tag but feed no attribution; they stay out of the queue.`) : '');
  if (trs.length) { cur = Math.max(0, trs.findIndex((t) => t.r.key === FOCUS_KEY)); paintCur(); if (FOCUS_KEY) { trs[cur].tr.focus({preventScroll: true}); trs[cur].tr.scrollIntoView({block: 'center'}); } FOCUS_KEY = null; }
}
