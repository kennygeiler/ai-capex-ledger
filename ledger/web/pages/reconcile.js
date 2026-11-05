// ── Reconcile: the workbench, on Tabler (dashboard UI kit) inside its own shadow root so the kit's reset touches nothing else. ──
// One card per cause; one row per item with ours, reference, a gap bar, delta and decision; Enter opens the evidence as
// aligned diff tables (this year, the computation, every year) with a status badge per line, and the decision form.
const CAUSE_ORDER = ['to_confirm', 'blocked', 'fact_differs', 'fact_changed', 'value_missing', 'finding_unconfirmed', 'new_filing', 'asset_types', 'asset_types_match'];
// Category mapping is two cards: Proposed (needs a person) and Matches company tag (the company's own XBRL tag already agrees)
const isMatch = (r) => r.cause === 'asset_types' && r.verification === 'company';
const causeKey = (r) => (isMatch(r) ? 'asset_types_match' : r.cause);
// what the page showed for a mapping entry; the server refuses a write against anything else (409)
const expectedOf = (r) => (r.evidence.mapping === 'unmapped' || !r.evidence.proposal ? null : {standard_type: r.evidence.proposal.standard_type, at: r.evidence.proposal.at || null});
// "Approve all N": one item per matching category, each confirming the member shown, with the entry the page showed
const bulkApproveItems = (rows) => rows.filter((r) => isMatch(r) && r.evidence.proposal && expectedOf(r)).map((r) => ({ticker: r.ticker, reported_name: r.evidence.reported_name, standard_type: r.evidence.proposal.standard_type, evidence: r.evidence.proposal.evidence || r.evidence.reported_name, expected: expectedOf(r)}));
// what an Approve all wrote, from the server's reply: "Approved 18 of 18: AMZN Land, …"
const bulkResult = (out, n) => `Approved ${out.approved} of ${n}` + ((out.items || []).length ? `: ${out.items.map((x) => `${x.ticker} ${x.reported_name}`).join(', ')}` : '');
// Choose another starts empty, or on the company's own tag when it differs from the proposal and is on the list; never the first option
const bare = (m) => String(m || '').replace(/^us-gaap:/, '');
const chooseDefault = (tag, members) => (tag && tag.status === 'differs' && members.map(bare).includes(bare(tag.member)) ? bare(tag.member) : '');
// after a save, the next row in the list that was not saved (else the one before it), so the reader keeps their place
const nextKey = (order, saved) => { const s = new Set(saved), last = Math.max(-1, ...order.map((k, i) => (s.has(k) ? i : -1))); return order.slice(last + 1).find((k) => !s.has(k)) || [...order.slice(0, Math.max(0, last))].reverse().find((k) => !s.has(k)) || null; };
// T33: Approve and "Write as" need a name in the signer box, as Sign does; one listener keeps every such button in step
const NEEDS_ME = new Set();  // the page lives in a shadow root, so the buttons are kept here, not queried from the document
// F-BF13: a name on config.PEOPLE (the reconcile feed's `people`), as the server checks every write; any other name disables, as Sign does
let SIGNERS = [];
const isSigner = (name) => SIGNERS.includes((name || '').trim());
const signerWhy = (name) => (!(name || '').trim() ? 'Enter a signer name' : 'Not on the signer list');
const needsMe = (btn) => { btn.disabled = !isSigner(me); NEEDS_ME.add(btn); return btn; };
document.addEventListener('input', (e) => { if (e.target.id === 'me') for (const b of NEEDS_ME) b.disabled = !isSigner(me); });
const RES_LABEL = {accept: 'Accept', explain: 'Explain', fix: 'Fix', blocks: 'Block release'};
const RES_HELP = {accept: 'Right as it stands', explain: 'Right, with the reason kept', fix: 'Wrong; stays open until re-read', blocks: 'Blocks release until settled'};
const RES_BADGE = {accept: 'bg-green-lt', explain: 'bg-azure-lt', fix: 'bg-yellow-lt', blocks: 'bg-red-lt'};
// the one definition of open (status.state, docs/PROOF.md): every row carries state, by and verification (states.row, the
// word the trail and Proof use for the same row); the page only shows them, in ledger/core/states.py's words (/pages/_states.js)
const stateCell = (r) => { const [cls, word] = stateWord('row', r.verification); return h('span', {class: cls + ' fw-medium text-nowrap'}, word); };
let FOCUS_KEY = null;  // the row to focus after a save re-renders the page
const num = (r, v) => (v == null ? '—' : r.measure === 'share' ? pct(v) : usdExact(v));
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
const memberWords = (m) => { if (!m) return ''; const w = m.split(':').pop().replace(/Member$/, '').replace(/([a-z0-9])([A-Z])|([A-Z])([A-Z][a-z])/g, '$1$3 $2$4').split(' '); return [w[0], ...w.slice(1).map((x) => (x.length > 1 && x === x.toUpperCase() ? x : x.toLowerCase()))].join(' '); };
const tone = (text, cls) => h('span', {class: cls + ' small text-nowrap'}, text);
const checkBadge = (label) => { if (label == null) return ''; const [cls, word] = stateWord('check', label); return tone(word, cls); };  // states.CHECK, the Dataset's words
const bar = (v, max, cls) => h('span', {class: 'bar ' + (cls || ''), style: `width:${Math.max(2, 44 * Math.abs(v || 0) / (max || 1)).toFixed(0)}px`});
// F-BF4: a row is selectable for one bulk decision only when /api/resolve/bulk takes its key (workbench sets `bulk`); a category mapping never is
const bulkable = (r) => !!r.bulk && r.cause !== 'asset_types';
const bulkKeys = (rows) => rows.filter(bulkable).map((r) => r.key);
async function reconcilePage(view, qs) {
  NEEDS_ME.clear();  // the last render's buttons are gone with it
  const q = parseQ(qs || '');
  const scope = q.scope || q.t || 'all', group = q.group || 'cause', fCause = q.cause || '', fLayer = q.layer || '', fField = q.field || '', withResolved = q.resolved === '1';  // ?t=MU is ?scope=MU: any one ticker the database holds, in scope or not
  const d = await api('/api/v1/reconcile?scope=' + encodeURIComponent(scope));
  SIGNERS = d.people || []; NEEDS_ME.clear();  // the buttons of the last render are gone
  const wrap = h('div', {class: 'stack', style: 'gap:.75rem'});
  view.append(wrap);
  const setQ = (patch) => { const p = {scope, group, cause: fCause, layer: fLayer, field: fField, kind: q.kind || '', resolved: withResolved ? '1' : '', ...patch}; go('reconcile?' + new URLSearchParams(Object.fromEntries(Object.entries(p).filter(([, v]) => v))).toString()); };
  const isOpen = (r) => !!r.open;  // the server's word (row.open: open or blocked), never recomputed here
  const toConfirm = (r) => r.cause === 'to_confirm';
  const isAsset = (r) => r.cause === 'asset_types';  // T33: an unmapped asset type with the mapper's proposal; T63: or an entry no person confirmed. Approve, Edit or Reject
  // the company's own tag (mapcard.decisions' card, ledger/checks/filertag.py): a different us-gaap member is a conflict
  const filerNote = (r) => { const T = (r.evidence.decision || {}).tag; if (!T) return ''; return T.status === 'differs' ? h('span', {class: 'small text-red', title: T.text}, `Company tags ${T.member.replace('us-gaap:', '')}`) : h('span', {class: 'small text-secondary'}, T.text); };
  let rows = d.rows.filter((r) => withResolved || isOpen(r) || toConfirm(r) || isAsset(r));  // an asset type the company's own tag matches stays listed, after the open ones, so a person can override it
  if (fCause) rows = rows.filter((r) => r.cause === fCause);
  if (fLayer) rows = rows.filter((r) => r.layer === fLayer);
  if (fField) rows = rows.filter((r) => (r.field || '') === fField);
  const hidden = d.rows.filter((r) => !isOpen(r) && !toConfirm(r) && !isAsset(r)).length;
  const fKind = q.kind || '';
  if (fKind) rows = rows.filter((r) => (r.evidence && r.evidence.kind) === fKind);
  const kinds = [...new Set(d.rows.map((r) => r.evidence && r.evidence.kind).filter(Boolean))].sort();
  const KINDL = {restated: 'Restated', jump: 'Large year-over-year change', row_switch: 'Line renamed', capex_intensity: 'Capex high vs revenue', opex_over_revenue: 'Opex above revenue'};
  const causes = CAUSE_ORDER.filter((c) => d.rows.some((r) => r.cause === c)), layers = [...new Set(d.rows.map((r) => r.layer))].sort(), fields = [...new Set(d.rows.map((r) => r.field).filter(Boolean))].sort();
  const sel = (label, value, opts, key) => h('select', {class: 'form-select form-select-sm', 'aria-label': label, onchange: (e) => setQ({[key]: e.target.value})}, opts.map(([v, t]) => h('option', {value: v, selected: v === value || null}, t)));
  const openRows = rows.filter(isOpen);
  const nState = (s) => Object.values(d.by_company || {}).reduce((n, c) => n + (c[s] || 0), 0);  // the one per-company count (states.buckets), summed over the scope
  const stat = (label, n, cls, always) => (n || always ? h('span', {class: 'me-3'}, h('span', {class: 'text-secondary'}, label + ' '), h('span', {class: (cls || '') + ' fw-medium'}, int(n))) : '');
  const header = h('div', {class: 'page-header'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('h1', {class: 'page-title'}, 'Reconcile'), h('div', {class: 'small mt-1'},
      ...OPEN_BUCKETS.map((s, i) => { const [cls, word] = stateWord('row', s); return stat(word, nState(s), cls, i === 0); }),  // the one per-company count's buckets (states.buckets), as Proof and Release say them
      (() => { const [cls, word] = stateWord('row', 'info'); return stat(word, (d.by_state || {}).info || 0, cls); })(),  // explained rows: an info stat, never part of the open buckets
      h('span', {class: 'text-secondary me-3'}, `Last run ${day(d.last_run)}`), d.release ? h('span', {class: 'text-secondary me-3'}, `Last release ${d.release}`) : '',
      h('span', {class: 'text-secondary', title: 'j k move · Enter opens · a e f b decide · space selects'}, 'Keyboard')))));
  const controls = h('div', {class: 'card mb-3'}, h('div', {class: 'card-body py-2'}, h('div', {class: 'row g-2 align-items-center'},
    h('div', {class: 'col-auto'}, sel('Scope', scope, [['all', 'All companies'], ...layers.map((l) => [l, INDUSTRY[l] || l]), ...[...new Set([...(d.scope_tickers || []), ...(scope !== 'all' && d.names[scope] ? [scope] : [])])].sort().map((t) => [t, `${d.names[t] || t} (${t})`])], 'scope')),
    h('div', {class: 'col-auto'}, sel('Group by', group, [['cause', 'Grouped by cause'], ['company', 'Grouped by company']], 'group')),
    h('div', {class: 'col-auto'}, sel('Cause', fCause, [['', 'Every cause'], ...causes.map((c) => [c, d.causes.find((x) => x.cause === c)?.label || c])], 'cause')),
    h('div', {class: 'col-auto'}, sel('Industry', fLayer, [['', 'Every industry'], ...layers.map((l) => [l, INDUSTRY[l] || l])], 'layer')),
    h('div', {class: 'col-auto'}, sel('Field', fField, [['', 'Every field'], ...fields.map((f) => [f, LABEL[f] || f])], 'field')),
    kinds.length ? h('div', {class: 'col-auto'}, sel('Check', fKind, [['', 'Every check'], ...kinds.map((k) => [k, KINDL[k] || k.replaceAll('_', ' ')])], 'kind')) : '',
    h('div', {class: 'col-auto ms-auto'}, h('label', {class: 'form-check form-switch m-0'}, h('input', {class: 'form-check-input', type: 'checkbox', checked: withResolved || null, onchange: (e) => setQ({resolved: e.target.checked ? '1' : ''})}), h('span', {class: 'form-check-label small'}, `Show ${int(hidden)} settled`))))));
  const selected = new Set();
  let cur = -1;
  const trs = [];
  const bulk = h('div', {class: 'card bulkbar', hidden: true});  // V8: fixed over the page bottom, never in the flow above the rows
  const groups = new Map();
  // "Approve all N" on Matches company tag: shows the list it will approve, one confirm, then each through the same writer
  // as a row's Approve (POST /api/mapping/bulk → mapper.approve with its `expected`); stops at the first refusal and says so
  const approveAllPanel = h('div', {class: 'card-body py-2', hidden: true});
  function approveAllButton(list) {
    const items = bulkApproveItems(list);
    if (!items.length) return '';
    const btn = needsMe(h('button', {type: 'button', class: 'btn btn-sm btn-outline-primary ms-auto', title: isSigner(me) ? 'Approve every category the company’s tag matches' : signerWhy(me), onclick: () => {
      const status = h('span', {class: 'text-secondary small', 'aria-live': 'polite'});
      const go_ = needsMe(h('button', {type: 'button', class: 'btn btn-sm btn-primary', onclick: async () => {
        go_.disabled = true; status.classList.remove('text-red'); status.textContent = 'Saving…';
        try {
          const out = await api('/api/mapping/bulk', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({items, by: me})});
          status.textContent = bulkResult(out, items.length); setTimeout(route, 1200);
        } catch (err) {  // the server checks everything before it writes and writes all or none: the message says Approved 0 of N and why
          status.classList.add('text-red'); status.replaceChildren(`${err.message}.`, ' ', h('button', {type: 'button', class: 'btn btn-sm btn-link p-0 align-baseline', onclick: route}, 'Reload'));
        }
      }}, `Approve ${int(items.length)}`));
      approveAllPanel.replaceChildren(
        h('table', {class: 'table table-sm mb-2'}, h('thead', {}, h('tr', {}, h('th', {}, 'Company'), h('th', {}, 'Category'), h('th', {}, 'Member'))),
          h('tbody', {}, items.map((x) => h('tr', {}, h('td', {}, x.ticker), h('td', {}, x.reported_name), h('td', {title: x.standard_type}, memberWords(x.standard_type)))))),
        h('div', {class: 'd-flex align-items-center', style: 'gap:.5rem'}, go_, h('button', {type: 'button', class: 'btn btn-sm btn-ghost-secondary', onclick: () => { approveAllPanel.hidden = true; }}, 'Cancel'), status));
      approveAllPanel.hidden = false; go_.focus();
    }}, `Approve all ${int(items.length)}`));
    return btn;
  }
  const keyOf = (r) => (group === 'cause' ? causeKey(r) : r.ticker);
  const ordered = [...rows].sort((a, b) => (group === 'cause' ? CAUSE_ORDER.indexOf(causeKey(a)) - CAUSE_ORDER.indexOf(causeKey(b)) || (isAsset(a) && isAsset(b) ? Number(b.open) - Number(a.open) : 0) || b.dollars - a.dollars || a.ticker.localeCompare(b.ticker) : a.name.localeCompare(b.name) || CAUSE_ORDER.indexOf(a.cause) - CAUSE_ORDER.indexOf(b.cause) || b.dollars - a.dollars));
  for (const r of ordered) groups.set(keyOf(r), [...(groups.get(keyOf(r)) || []), r]);
  const cards = [];
  for (const [g, list] of groups) {
    const label = group === 'cause' ? (g === 'asset_types' ? 'Category mapping · Proposed' : g === 'asset_types_match' ? 'Category mapping · Matches company tag' : (d.causes.find((x) => x.cause === g) || {}).label || list[0].cause_label) : `${list[0].name} ${list[0].ticker}`;
    const open = list.filter(isOpen);
    const selectable = bulkKeys(open);
    const tbody = h('tbody');
    const assetCard = group === 'cause' && (g === 'asset_types' || g === 'asset_types_match');  // a mapping card: no Dataset, SEC XBRL, Gap or Difference columns, always — on its rows
    for (const r of list) {
      const i = trs.length;
      const cb = !bulkable(r) ? '' : h('input', {class: 'form-check-input m-0', type: 'checkbox', 'aria-label': `Select ${r.name} ${r.where}`, checked: selected.has(r.key) || null, onclick: (e) => { e.stopPropagation(); e.target.checked ? selected.add(r.key) : selected.delete(r.key); paint(); }});  // a mapping is approved one at a time, never in bulk (bulkable)
      const first = group === 'cause' ? [h('a', {href: `#proof/${r.ticker}`, onclick: (e) => e.stopPropagation()}, r.name), ' ', h('span', {class: 'text-secondary small'}, r.ticker)] : [r.cause_label];
      const where = [h('div', {}, r.field ? (LABEL[r.field] || r.field) : r.where, r.period ? ` ${r.period}` : ''), r.cause === 'finding_unconfirmed' ? h('div', {class: 'text-secondary small'}, [r.evidence.dimension, group === 'company' ? '' : r.cause_label].filter(Boolean).join(' · ')) : r.evidence.dimension ? h('div', {class: 'text-secondary small'}, r.evidence.dimension) : ''];
      const res = toConfirm(r) ? confirmCell(r, i) : isAsset(r) ? mappingCell(r, i) : [stateCell(r), r.resolution && r.resolution.by ? h('div', {class: 'text-secondary small'}, `${RES_LABEL[r.resolution.state] || r.resolution.state} · ${r.resolution.by} · ${day(r.resolution.at)}`) : ''];
      const P = isAsset(r) ? r.evidence.proposal : null;
      const ours = isAsset(r) ? [P ? [h('span', {style: 'overflow-wrap:anywhere', title: P.standard_type}, memberWords(P.standard_type)), ' ', r.evidence.mapping === 'verified' ? h('span', {class: 'small text-green'}, 'Matches company’s own tag') : P.confidence ? h('span', {class: 'text-secondary small'}, `Confidence ${P.confidence}`) : h('span', {class: 'small text-orange'}, 'Proposed')] : h('span', {class: 'text-secondary small'}, 'No proposal'), h('div', {class: 'small'}, filerNote(r), P && filerNote(r) ? h('span', {class: 'text-secondary'}, ' · ') : '', P ? h('span', {class: 'text-secondary', title: P.evidence}, `“${P.evidence}”`) : '')] : [num(r, r.ours), r.ours_label ? h('div', {class: 'text-secondary small'}, r.ours_label) : ''];
      const tr = h('tr', {class: 'item', tabindex: 0, 'aria-expanded': 'false', onkeydown: (e) => keys(e, i), onclick: () => toggle(i), onfocus: () => { cur = i; paintCur(); }},
        h('td', {class: 'w-1'}, cb), h('td', {}, first), h('td', {}, where),
        isAsset(r) ? h('td', {colspan: assetCard ? null : 4}, ours) : [h('td', {class: 'num'}, ours),
        h('td', {class: 'num'}, r.reference == null ? h('span', {class: 'text-secondary'}, '—') : [({ge: '≥ ', le: '≤ '})[r.relation] || '', num(r, r.reference)], r.ref_label && r.reference != null ? h('div', {class: 'text-secondary small'}, r.ref_label) : ''),
        h('td', {class: 'w-1'}, r.ours != null && r.reference != null ? gapBar(r) : ''),
        h('td', {class: 'num'}, r.delta == null ? h('span', {class: 'text-secondary'}, '—') : [h('span', {class: 'fw-semibold' + (r.cause === 'fact_differs' ? ' text-red' : '')}, signed(r, r.delta)), r.delta_pct != null && r.measure !== 'share' ? h('div', {class: 'text-secondary small'}, pctSigned(r.delta_pct)) : ''])],
        h('td', {}, res));
      trs.push({tr, r, detail: null});
      tbody.append(tr);
    }
    const confirmGroup = group === 'cause' && toConfirm(list[0]);
    const assetGroup = group === 'cause' && g === 'asset_types', matchGroup = group === 'cause' && g === 'asset_types_match';
    cards.push(h('div', {class: 'card mb-3'},
      h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, label), h('span', {class: 'ms-2 text-secondary small'}, confirmGroup ? `${int(list.length)} proposed` : assetGroup ? [`${int(list.filter((r) => r.verification === 'wait').length)} proposed`, list.some((r) => r.verification === 'bad') ? ` · ${int(list.filter((r) => r.verification === 'bad').length)} unmapped` : '', list.some((r) => r.evidence.mismatch) ? ` · ${int(list.filter((r) => r.evidence.mismatch).length)} differ from company tag` : ''] : matchGroup ? `${int(list.length)} categories` : (list.some((r) => OPEN_BUCKETS.includes(r.verification)) ? [bucketLine(list.reduce((n, r) => ({...n, [r.verification]: (n[r.verification] || 0) + 1}), {})), ` of ${int(list.length)}`] : `${int(list.length)} settled`)),  // this card's own buckets, in the words of the company count
        selectable.length > 1 ? h('button', {type: 'button', class: 'btn btn-sm btn-ghost-secondary ms-auto', onclick: () => { for (const k of selectable) selected.add(k); paint(); }}, `Select all ${int(selectable.length)}`) : '',
        matchGroup ? approveAllButton(list) : ''),
      matchGroup ? approveAllPanel : '',
      h('div', {class: 'table-responsive'}, h('table', {class: 'table table-vcenter card-table table-hover rec'},
        h('colgroup', {}, (assetCard ? ['2.25rem', '10rem', '22%', null, '17rem'] : ['2.25rem', '10rem', null, '9.75rem', '9.75rem', '6.5rem', '7rem', list.some(isAsset) ? '17rem' : confirmGroup || list.some(toConfirm) ? '14rem' : '9rem']).map((w) => h('col', {style: w ? `width:${w}` : null}))),
        h('thead', {}, h('tr', {}, h('th', {}, h('span', {class: 'visually-hidden'}, 'Select')), h('th', {}, group === 'cause' ? 'Company' : 'Cause'), h('th', {}, assetCard ? 'Category' : 'Item'),
          assetCard ? h('th', {}, 'Proposed') : [h('th', {class: 'num'}, 'Dataset'), h('th', {class: 'num'}, group === 'cause' && (g === 'fact_differs' || g === 'value_missing') ? 'SEC XBRL' : 'Compared with'), h('th', {}, 'Gap'), h('th', {class: 'num'}, 'Difference')], h('th', {}, 'Decision'))),
        tbody))));
  }
  function paint() { wrap.querySelectorAll('.decision-panel').forEach((x) => { x.hidden = selected.size > 0; }); for (const t of trs) { const c = t.tr.querySelector('input[type=checkbox]'); if (c) c.checked = selected.has(t.r.key); } bulk.hidden = selected.size === 0; const selRows = [...selected].map((k) => trs.find((t) => t.r.key === k).r); bulk.replaceChildren(h('div', {class: 'card-body py-2'}, h('div', {class: 'row g-2 align-items-center'}, h('div', {class: 'col-12 small text-secondary'}, h('b', {class: 'text-body'}, int(selected.size)), ' selected'), h('div', {class: 'col'}, resolutionForm(null, [...selected].map((k) => trs.find((t) => t.r.key === k).r), () => { selected.clear(); paint(); })), h('div', {class: 'col-auto'}, h('button', {type: 'button', class: 'btn btn-sm btn-ghost-secondary', onclick: () => { selected.clear(); paint(); }}, 'Clear'))))); }
  function paintCur() { trs.forEach((t, j) => t.tr.classList.toggle('cur', j === cur)); }
  function toggle(i, force) {
    const t = trs[i]; cur = i; paintCur();
    const acts = (x, show) => { const a = x.tr.querySelector('.row-actions'); if (a) a.hidden = !show; };  // a mapping row's buttons hide while its card (with the same actions) is open
    if (t.detail && force !== true) { t.detail.remove(); t.detail = null; t.tr.setAttribute('aria-expanded', 'false'); acts(t, true); return; }
    if (t.detail) return;
    for (const o of trs) if (o !== t && o.detail) { o.detail.remove(); o.detail = null; o.tr.setAttribute('aria-expanded', 'false'); acts(o, true); }  // one Decision panel at a time
    t.detail = h('tr', {class: 'ev'}, h('td', {colspan: t.tr.closest('table').querySelectorAll('thead th').length}, evidence(t.r)));  // the table's own column count: a wider span would add columns and move every header (V8)
    t.tr.after(t.detail); t.tr.setAttribute('aria-expanded', 'true'); acts(t, false);
  }
  function keys(e, i) {
    if (e.target.matches('input, select, textarea, button') || e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key;
    if (k === 'j' || k === 'ArrowDown') { e.preventDefault(); trs[Math.min(trs.length - 1, i + 1)].tr.focus(); }
    else if (k === 'k' || k === 'ArrowUp') { e.preventDefault(); trs[Math.max(0, i - 1)].tr.focus(); }
    else if (k === 'Enter' || k === 'o') { e.preventDefault(); toggle(i); }
    else if (k === ' ') { e.preventDefault(); const r = trs[i].r; if (!bulkable(r)) return; selected.has(r.key) ? selected.delete(r.key) : selected.add(r.key); paint(); }
    else if (k === 'Escape' && trs[i].detail) { toggle(i); }
    else if ('aefb'.includes(k) && k && !isAsset(trs[i].r)) { e.preventDefault(); toggle(i, true); const btn = trs[i].detail.querySelector(`[data-state=${({a: 'accept', e: 'explain', f: 'fix', b: 'blocks'})[k]}]`); btn.click(); trs[i].detail.querySelector('input[type=text]').focus(); }
  }
  // T3: a decision a run made. Confirm records the proposed state on the same key, by me, reason "confirmed";
  // Overturn opens the normal decide flow (the evidence row with the form).
  function confirmCell(r, i) {
    const proposed = (r.evidence && r.evidence.proposed) || (r.resolution && r.resolution.state) || 'explain';
    const status = h('span', {class: 'text-secondary small', 'aria-live': 'polite'});
    const confirm = h('button', {type: 'button', class: 'btn btn-sm btn-outline-primary', title: 'Confirm', onclick: async (e) => {
      e.stopPropagation(); confirm.disabled = true; status.textContent = 'Saving…';
      try {
        await api('/api/resolve', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({key: r.key, hash: r.hash, state: proposed, reason: 'confirmed', by: me})});
        status.textContent = 'Confirmed.'; FOCUS_KEY = nextKey(trs.map((t) => t.r.key), [r.key]); setTimeout(route, 250);
      } catch (err) { status.textContent = `Couldn’t save: ${err.message}.`; status.classList.add('text-red'); confirm.disabled = false; }
    }}, `Confirm ${RES_LABEL[proposed] || proposed}`);
    const overturn = h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary', title: 'Change decision', onclick: (e) => { e.stopPropagation(); toggle(i, true); const f = trs[i].detail.querySelector('input[type=text]'); if (f) f.focus(); }}, 'Overturn');
    if (r.resolution && r.resolution.by) confirm.title = `Proposed by ${r.resolution.by} · ${day(r.resolution.at)}`;
    return [h('div', {class: 'btn-list flex-nowrap'}, confirm, overturn), status];
  }
  // T33: an unmapped asset type. Approve writes the proposed member with the mapper's evidence under my name; Edit opens the
  // form with the member select; Reject logs the proposed member so the next run proposes another. No animation: a
  // person does this five times a company, and the row re-renders from the server's truth.
  async function postMapping(path, body, status, after) {
    status.classList.remove('text-red'); status.textContent = 'Saving…';
    const k = trs.find((t) => t.r.ticker === body.ticker && t.r.evidence && t.r.evidence.reported_name === body.reported_name);
    if (k) FOCUS_KEY = nextKey(trs.map((t) => t.r.key), [k.r.key]);
    try {
      await api(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
      status.textContent = after; setTimeout(route, 250);
      return true;
    } catch (err) {
      status.classList.add('text-red');
      if (err.status === 409) { status.textContent = 'Changed since loaded. Reloading.'; setTimeout(route, 800); return false; }  // a stale Approve: the page reloads the truth
      status.textContent = `Couldn’t save: ${err.message}.`; return false;
    }
  }
  function mappingCell(r, i) {
    const P = r.evidence.proposal;
    const status = h('span', {class: 'text-secondary small', 'aria-live': 'polite'});
    const btns = [];
    if (P) {
      const entry = r.evidence.mapping !== 'unmapped';
      const approve = needsMe(h('button', {type: 'button', class: 'btn btn-sm btn-outline-primary', title: isSigner(me) ? 'Approve this category' : signerWhy(me), onclick: async (e) => {  // one primary per page section: a matching row's Approve is not one
        e.stopPropagation(); approve.disabled = true;
        const ok = await postMapping('/api/mapping', {ticker: r.ticker, reported_name: r.evidence.reported_name, standard_type: P.standard_type, evidence: P.evidence || r.evidence.reported_name, by: me, expected: expectedOf(r)}, status, entry ? 'Confirmed.' : 'Mapped.');
        if (!ok) approve.disabled = !isSigner(me);
      }}, 'Approve'));
      const reject = needsMe(h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary', title: 'Reject this category', onclick: async (e) => {
        e.stopPropagation(); reject.disabled = true;
        const ok = await postMapping('/api/mapping/reject', {ticker: r.ticker, reported_name: r.evidence.reported_name, standard_type: P.standard_type, by: me, reason: 'rejected on Reconcile'}, status, 'Rejected.');
        if (!ok) reject.disabled = !isSigner(me);
      }}, 'Reject'));
      btns.push(approve, reject);
    }
    const edit = h('button', {type: 'button', class: 'btn btn-sm ' + (P ? 'btn-outline-secondary' : 'btn-outline-primary'), title: 'Choose a category', onclick: (e) => { e.stopPropagation(); toggle(i, true); const s = trs[i].detail.querySelector('select'); if (s) s.focus(); }}, P ? 'Choose another' : 'Map');
    btns.push(edit);
    return [h('div', {class: 'btn-list flex-nowrap row-actions'}, btns), status];
  }
  // The decision card's actions (the card is mapcard.decisions', shared with the trail): Approve · Choose another · Reject,
  // through the same routes as the row's buttons (POST /api/mapping, /api/mapping/reject); the person check is the server's.
  function mappingActions(r) {
    const P = r.evidence.proposal, D = r.evidence.decision || {};
    const status = h('span', {class: 'text-secondary small', 'aria-live': 'polite'});
    const rejected = r.evidence.rejected || [];
    const opts = (D.members || (d.members || []).map((m) => ({member: m, label: m}))).filter((m) => !rejected.includes(m.member) && (!P || m.member !== P.standard_type));
    const pre = chooseDefault(D.tag, opts.map((m) => m.member));
    const select = h('select', {class: 'form-select form-select-sm', 'aria-label': 'Standard category'}, h('option', {value: '', selected: !pre || null}, 'Choose a category'),
      opts.map((m) => h('option', {value: m.member, title: m.member, selected: bare(m.member) === pre || null}, m.label)));
    const evidence = (P && P.evidence) || r.evidence.reported_name;
    const btns = [];
    if (P) {
      const approve = needsMe(h('button', {type: 'button', class: 'btn btn-sm btn-primary', title: isSigner(me) ? 'Approve this category' : signerWhy(me), onclick: async () => {
        approve.disabled = true;
        if (!await postMapping('/api/mapping', {ticker: r.ticker, reported_name: r.evidence.reported_name, standard_type: P.standard_type, evidence, by: me, expected: expectedOf(r)}, status, 'Confirmed.')) approve.disabled = !isSigner(me);
      }}, 'Approve'));
      btns.push(approve);
    }
    const choose = needsMe(h('button', {type: 'button', class: 'btn btn-sm btn-outline-primary', title: isSigner(me) ? 'Choose a category' : signerWhy(me), onclick: async () => {
      if (!select.value) { select.focus(); status.textContent = 'Choose a category'; return; }
      choose.disabled = true;
      if (!await postMapping('/api/mapping', {ticker: r.ticker, reported_name: r.evidence.reported_name, standard_type: select.value, evidence, by: me, expected: expectedOf(r)}, status, 'Mapped.')) choose.disabled = !isSigner(me);
    }}, P ? 'Choose another' : 'Map'));
    btns.push(h('div', {class: 'input-group input-group-sm flex-nowrap', style: 'width:auto;max-width:30rem'}, select, choose));
    if (P) {
      const reject = needsMe(h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary', title: 'Reject this category', onclick: async () => {
        reject.disabled = true;
        if (!await postMapping('/api/mapping/reject', {ticker: r.ticker, reported_name: r.evidence.reported_name, standard_type: P.standard_type, by: me, reason: 'rejected on Reconcile'}, status, 'Rejected.')) reject.disabled = !isSigner(me);
      }}, 'Reject'));
      btns.push(reject);
    }
    return h('div', {class: 'mt-3'}, h('div', {class: 'd-flex flex-wrap align-items-center', style: 'gap:.5rem'}, btns), status);
  }
  // T36: an explanation written once. The server decides what an item may become (row.encode, judgement.offers): a rule
  // names the finding's rule, its field and the whole lines the company reads it from; a definition names the company and
  // the kind. The page sends only the key, the reason and the name; POST /api/judgement writes rules/ or definitions/.
  const canEncode = (r) => !!(r && r.encode && ['rule', 'definition'].some((k) => r.encode[k] && !r.encode[k].why_not));
  function encodePanel(r, why) {
    const E = r.encode, parts = [];
    for (const as of ['rule', 'definition']) {
      const o = E[as];
      if (!o || o.why_not) continue;
      const text = h('input', {type: 'text', class: 'form-control form-control-sm', autocomplete: 'off', 'aria-label': `Why, kept on the ${as}`, placeholder: as === 'rule' ? 'Reason (applies to every company)' : 'Reason (this company)', value: why || (r.resolution && r.resolution.reason) || '', onkeydown: (e) => { if (e.key === 'Enter') btn.click(); }});
      const status = h('span', {class: 'text-secondary small', 'aria-live': 'polite'});
      const what = as === 'rule'
        ? [h('span', {class: 'text-secondary'}, 'Applies to: '), 'every company reading ', o.row_labels.map((l, j) => [j ? ', ' : '', `“${l}”`])]
        : [h('span', {class: 'text-secondary'}, 'Applies to: '), r.ticker, o.lines ? [' · ', o.lines.map((l, j) => [j ? ' + ' : '', `“${l}”`])] : ` · ${(o.periods || []).join(', ')}`];
      const btn = needsMe(h('button', {type: 'button', class: 'btn btn-sm btn-outline-primary', title: isSigner(me) ? (as === 'rule' ? 'Save as rule' : 'Save as definition') : signerWhy(me), onclick: async () => {
        if (!text.value.trim()) { text.focus(); status.textContent = 'Reason required'; return; }
        btn.disabled = true; status.classList.remove('text-red'); status.textContent = 'Writing…';
        try {
          const out = await api('/api/judgement', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({key: r.key, as, why: text.value, by: me})});
          status.textContent = `Saved to ${out.file}. Applies on the next run.`;
        } catch (e) { status.textContent = `Couldn’t write: ${e.message}.`; status.classList.add('text-red'); btn.disabled = !isSigner(me); }
      }}, as === 'rule' ? 'Make this a rule' : 'Make this a definition'));
      parts.push(h('div', {class: 'col-12'}, h('div', {class: 'small mb-1'}, what), h('div', {class: 'input-group input-group-sm'}, text, btn), status));
    }
    return h('div', {class: 'row g-2'}, parts);
  }
  function resolutionForm(r, many, done) {
    const items = many || [r];
    let state = r && r.resolution ? r.resolution.state : 'accept';
    const btns = Object.keys(RES_LABEL).map((s) => h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary' + (s === state ? ' active' : ''), 'data-state': s, 'aria-pressed': String(s === state), title: RES_HELP[s], onclick: (e) => { state = s; e.currentTarget.parentNode.querySelectorAll('.btn').forEach((b) => { b.classList.toggle('active', b.dataset.state === s); b.setAttribute('aria-pressed', String(b.dataset.state === s)); }); }}, RES_LABEL[s]));
    const reason = h('input', {type: 'text', class: 'form-control form-control-sm', name: 'reason', autocomplete: 'off', placeholder: many ? `Why, for all ${items.length}, e.g. accrual capex, cash basis differs` : 'e.g. includes finance leases, note 7', 'aria-label': 'Reason', value: r && r.resolution ? r.resolution.reason : '', onkeydown: (e) => { if (e.key === 'Enter') save.click(); }});
    const status = h('span', {class: 'text-secondary small', 'aria-live': 'polite'});
    const save = h('button', {type: 'button', class: 'btn btn-sm btn-primary', onclick: async () => {
      if (!reason.value.trim()) { reason.focus(); status.textContent = 'Reason required'; return; }
      save.disabled = true; status.textContent = 'Saving…';
      try {
        if (many) await api('/api/resolve/bulk', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({items: items.map((x) => ({key: x.key, hash: x.hash})), state, reason: reason.value, by: me})});
        else await api('/api/resolve', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({key: r.key, hash: r.hash, state, reason: reason.value, by: me})});
        status.classList.remove('text-red'); FOCUS_KEY = nextKey(trs.map((t) => t.r.key), items.map((x) => x.key)); if (done) done();
        if (!many && (state === 'accept' || state === 'explain') && canEncode(r)) {  // T36: offer to write it once before the row leaves the list
          status.replaceChildren(h('div', {class: 'mb-2'}, 'Saved. Apply to every company?'), encodePanel(r, reason.value), h('button', {type: 'button', class: 'btn btn-sm btn-ghost-secondary mt-2', onclick: route}, 'Done'));
        } else { status.textContent = 'Saved.'; setTimeout(route, 250); }
      } catch (e) { status.textContent = `Couldn’t save: ${e.message}. Try again.`; status.classList.add('text-red'); }
      finally { save.disabled = false; }
    }}, many ? `Save for ${items.length}` : 'Save');
    return h('div', {class: 'row g-2 align-items-center'}, h('div', {class: 'col-auto'}, h('div', {class: 'btn-group seg', role: 'group', 'aria-label': 'Decision'}, btns)), h('div', {class: 'col'}, h('div', {class: 'input-group input-group-sm'}, reason, save)), h('div', {class: 'col-12'}, status));
  }
  function evidence(r) {
    const E = r.evidence || {}, S = r.series || [], cards = [];
    const col = (n, ...k) => h('div', {class: `col-12 col-xl-${n}`}, k);
    if (E.restatement) cards.push(col(12, restatedLine(E.restatement, true)));  // the readings disagree across filings (ties.restatement), whatever the state
    if (E.basis) {  // segment_basis_mixed: the year's segments, the filing each comes from, and the cutover that restated the series
      const B = E.basis, C = B.cutover || {};
      cards.push(col(8, dtable(`${r.period} · segments by filing`, [{t: 'Segment', k: 'dimension'}, {t: 'As filed', num: 1, k: 'cell_text'}, {t: 'From', f: (x) => `${x.form} ${x.filed}`},
        {t: 'Basis', f: (x) => (x.mixed ? h('span', {class: 'text-orange'}, `Before ${C.form || '10-K'} ${C.filed || ''}`) : 'Current')}, {t: '', f: (x) => (x.restated ? h('span', {class: 'small text-secondary'}, x.restated) : '')}], B.rows)));
    }
    const yr = S.find((s) => s.period === r.period) || {};
    if (r.cause === 'fact_differs') {
      const c = E.cell;
      const X = E.xbrl, cellAcc = c ? c.accession : null;
      const lines = [{what: 'Cited', value: r.ours, src: c ? `“${c.row_label}”` : '', _cls: 'fw-semibold'},
        {what: 'SEC XBRL', value: r.reference, src: X ? [h('span', {title: `${X.concept}${X.member ? ' / ' + X.member : ''} · ${X.accession}`}, [memberWords(X.concept), X.member ? memberWords(X.member) : '', X.date].filter(Boolean).join(' · ')), cellAcc && X.accession !== cellAcc ? h('div', {class: 'text-body mt-1'}, 'Restated in a later 10-K') : ''] : 'Not found in SEC XBRL'}, E.release_value != null ? {what: `In ${d.release}`, value: Number(E.release_value), src: 'Last release'} : null, {what: 'Difference', value: r.delta, src: pctSigned(r.delta_pct), _cls: 'text-red'}].filter(Boolean);
      const maxL = Math.max(1, ...lines.filter((l) => l.what !== 'Difference').map((l) => Math.abs(l.value || 0)));
      cards.push(col(4, dtable(`${r.period} · Cited vs SEC XBRL`, [{t: '', f: (x) => [h('div', {}, x.what), x.src ? h('div', {class: 'text-secondary small fw-normal'}, x.src) : '']}, {t: 'Amount', num: 1, f: (x) => (x.what === 'Difference' ? signed(r, x.value) : [bar(x.value, maxL, x.what === 'Cited' ? '' : 'ref'), usd(x.value)])}], lines),
        h('div', {class: 'card mt-3'}, h('div', {class: 'card-body py-2'}, gapBar(r, true), h('div', {class: 'd-flex justify-content-between small text-secondary'}, h('span', {}, 'Cited ', h('b', {class: 'text-primary'}, usd(r.ours))), h('span', {}, 'SEC XBRL ', h('b', {}, usd(r.reference))))))));
      cards.push(col(4, h('div', {class: 'card'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, 'Source')), h('div', {class: 'card-body py-2'}, c ? h('div', {class: 'datagrid'},
          h('div', {class: 'datagrid-item'}, h('div', {class: 'datagrid-title'}, 'Value'), h('div', {class: 'datagrid-content fw-semibold'}, c.cell_text)),
          h('div', {class: 'datagrid-item'}, h('div', {class: 'datagrid-title'}, 'Line'), h('div', {class: 'datagrid-content'}, c.row_label)),
          h('div', {class: 'datagrid-item'}, h('div', {class: 'datagrid-title'}, 'Column'), h('div', {class: 'datagrid-content'}, (c.column_label || '').replaceAll(' | ', ' ')))) : h('p', {class: 'text-secondary small m-0'}, 'No citation'),
          c && E.crop ? h('div', {class: 'cites mt-2'}, citeCell({crop: {state: E.crop.state, reason: E.crop.reason, url: E.crop.url}, viewer: E.crop.viewer, link: E.url, form: E.crop.form, filed: E.crop.filed, row: c.row_label, column: (c.column_label || '').replaceAll(' | ', ' '), cell: c.cell_text}, r.where)) : '',
          h('div', {class: 'mt-2'}, h('a', {href: `#proof/${r.ticker}`, class: 'small'}, 'Company trail')))),
));
      const maxY = Math.max(1e-9, ...S.flatMap((s) => [Math.abs(s.value || 0), Math.abs(s.reference || 0)]));
      cards.push(col(4, dtable('By year', [{t: 'Year', k: 'period', w: '4rem'}, {t: 'Cited', num: 1, f: (s) => (s.value == null ? '—' : [bar(s.value, maxY), usd(s.value)])}, {t: 'SEC XBRL', num: 1, f: (s) => (s.reference == null ? h('span', {class: 'text-secondary'}, '—') : [bar(s.reference, maxY, 'ref'), usd(s.reference)])}, {t: 'Difference', num: 1, f: (s) => (s.reference == null || s.value == null ? '' : h('span', {class: s.label === 'unresolved' ? 'text-red' : ''}, signed({measure: 'usd'}, s.value - s.reference)))}, {t: '', f: (s) => checkBadge(s.label)}], S.map((s) => ({...s, _cls: s.period === r.period ? 'table-active' : null})))));
    } else if (r.cause === 'fact_changed') {
      const before = {what: E.release || 'Release', value: r.reference};
      const after = {what: 'Now', value: r.ours, _cls: 'fw-semibold'};
      const maxL = Math.max(1, Math.abs(before.value || 0), Math.abs(after.value || 0));
      cards.push(col(5, dtable(`${r.period} · Last release vs now`, [{t: '', k: 'what'}, {t: 'Amount', num: 1, f: (x) => (x.what === 'Difference' ? signed(r, x.value) : [bar(x.value, maxL, x === before ? 'ref' : ''), usd(x.value)])}], [before, after, {what: 'Difference', value: r.delta, _cls: 'text-red'}])));
      cards.push(col(3, h('a', {href: `#proof/${r.ticker}`, class: 'small'}, 'Company trail')));
    } else if (r.cause === 'value_missing') {
      cards.push(col(5, dtable(`${r.period} · Not extracted`, [{t: '', k: 'what'}, {t: 'Amount', num: 1, f: (x) => (x.value == null ? '—' : usd(x.value))}], [{what: 'Cited', value: null}, {what: 'SEC XBRL', value: r.reference, _cls: 'fw-semibold'}])));
      cards.push(col(3, h('a', {href: `#proof/${r.ticker}`, class: 'small'}, 'Company trail')));
    } else if (r.cause === 'finding_unconfirmed' || r.cause === 'blocked') {
      if (r.measure) {
        const maxL = Math.max(1, Math.abs(r.ours || 0), Math.abs(r.reference || 0));
        cards.push(col(4, dtable(r.cause_label, [{t: '', k: 'what'}, {t: 'Amount', num: 1, f: (x) => (x.what === 'Difference' ? [signed(r, x.value), E.kind === 'jump' && E.size != null ? h('span', {class: 'text-secondary small'}, ` ${Number(E.size).toFixed(1)}×`) : ''] : [bar(x.value, maxL, x.what === r.ours_label ? '' : 'ref'), usd(x.value)])}], [{what: r.ref_label || 'Before', value: r.reference}, {what: r.ours_label || 'After', value: r.ours, _cls: 'fw-semibold'}, {what: 'Difference', value: r.delta, _cls: 'text-red'}])));
      }
      if (S.length > 1) { const maxY = Math.max(1e-9, ...S.map((s) => Math.abs(s.value || 0))); cards.push(col(4, dtable(`${LABEL[r.field] || r.field} by year`, [{t: 'Year', k: 'period', w: '4rem'}, {t: 'Value', num: 1, f: (s) => (s.value == null ? '—' : [bar(s.value, maxY), usd(s.value)])}, {t: '', f: (s) => checkBadge(s.label)}], S.map((s) => ({...s, _cls: s.period === r.period ? 'table-active' : null}))))); }
      cards.push(col(4, h('details', {class: 'words', open: true}, h('summary', {}, 'Details'), h('div', {class: 'small'}, E.message || '')), h('div', {class: 'mt-2'}, h('a', {href: `#data?view=grid&t=${r.ticker}&f=${r.field || 'capex'},capex`, class: 'small'}, 'Open in Dataset'))));
    } else if (toConfirm(r)) {
      const p = r.resolution || {};
      cards.push(col(8, h('div', {class: 'card'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, `Proposed: ${RES_LABEL[E.proposed] || E.proposed}`), h('span', {class: 'ms-2 small text-secondary'}, `${p.by || ''}, ${day(p.at)}`)),
        h('div', {class: 'card-body py-2'}, h('p', {class: 'm-0'}, E.message || p.reason || '')),
        h('div', {class: 'card-footer py-2'}, h('a', {href: `#proof/${r.ticker}`, class: 'small'}, 'Company trail')))));
    } else if (r.cause === 'new_filing') {
      cards.push(col(6, h('div', {class: 'card'}, h('div', {class: 'card-body'}, `${E.form} · Filed ${day(E.filed)} · `, h('a', {href: safeHref(E.url), target: '_blank', rel: 'noopener'}, 'Open in EDGAR ↗')))));
    } else if (isAsset(r)) {
      const N = E.note;
      cards.push(col(8, h('div', {class: 'card'}, h('div', {class: 'card-body py-3'}, E.decision ? mappingDecision(E.decision, mappingActions(r)) : mappingActions(r),
        E.rejected && E.rejected.length ? h('p', {class: 'small text-secondary mt-2 mb-0'}, `Rejected: ${E.rejected.map(memberWords).join(', ')}`) : '',
        E.reproposed && E.reproposed.length ? h('p', {class: 'small text-orange mt-1 mb-0'}, `Proposed again after rejection: ${E.reproposed.map(memberWords).join(', ')}`) : ''))));
      cards.push(col(4, h('div', {class: 'card'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, 'Note wording')),
        h('div', {class: 'card-body py-2'}, h('p', {class: 'm-0 small'}, N && N.before ? `…${N.before}` : 'Note text unavailable'), h('div', {class: 'mt-2'}, h('a', {href: `#proof/${r.ticker}`, class: 'small'}, 'Company trail'))))));
    }
    const decision = isAsset(r)
      ? ''
      : h('div', {class: 'col-12 decision-panel', hidden: selected.size > 0}, h('div', {class: 'card'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, toConfirm(r) ? 'Change decision' : 'Decision'), r.resolution && !toConfirm(r) ? h('span', {class: 'ms-2 small text-secondary'}, `${RES_LABEL[r.resolution.state]} · ${r.resolution.by} · ${day(r.resolution.at)} · ${r.resolution.reason}`) : ''), h('div', {class: 'card-body py-2'}, resolutionForm(r))));
    const once = canEncode(r) ? h('div', {class: 'col-12'}, h('div', {class: 'card'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, 'Apply everywhere')), h('div', {class: 'card-body py-2'}, encodePanel(r)))) : '';
    return h('div', {class: 'row g-3'}, cards, decision, once);
  }
  wrap.append(header, controls, bulk, ...(cards.length ? cards : [h('div', {class: 'card'}, h('div', {class: 'card-body text-secondary'}, 'No items to review'))]));
  if (trs.length) { const at = trs.findIndex((t) => t.r.key === FOCUS_KEY); cur = Math.max(0, at); paintCur(); if (FOCUS_KEY && at >= 0) { trs[cur].tr.focus({preventScroll: true}); trs[cur].tr.scrollIntoView({block: 'center'}); } FOCUS_KEY = null; }
}
