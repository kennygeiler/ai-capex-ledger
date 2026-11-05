// Kenny's Data Emporium: everything more than one page uses. Plain script, globals; app.html loads it first.
const $ = (s, r = document) => r.querySelector(s);
const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k.startsWith('on')) el.addEventListener(k.slice(2), v); else if (k === 'class') el.className = v; else el.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat(Infinity)) if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
  return el;
};
// every href built from stored data goes through this: a web address, the in-app viewer or a page route, else no link
const safeHref = (u) => (typeof u === 'string' && (/^https?:\/\//i.test(u) || /^\/filing\/[0-9-]+(\?|$)/.test(u) || /^#[a-z]/.test(u)) ? u : null);
const int = (n) => (n == null || n === '' ? '—' : Number(n).toLocaleString('en-US'));
const plural = (n, one, many) => `${int(n)} ${n === 1 ? one : many || one + 's'}`;
// the one money format (ledger/web/cards.py money, the same cases tested on both): $513,983M, $1.8M, $450,000, $0, —
const usd = (n) => {
  if (n == null || n === '') return '—';
  const x = Number(n), a = Math.floor(Math.abs(x) + 0.5), sign = x < 0 && a ? '−' : '';
  if (a >= 1e6 && a % 1e6 === 0) return `${sign}$${(a / 1e6).toLocaleString('en-US')}M`;
  if (a >= 1e6) { const t = Math.floor((a + 5e4) / 1e5); return `${sign}$${Math.floor(t / 10).toLocaleString('en-US')}.${t % 10}M`; }
  return `${sign}$${a.toLocaleString('en-US')}`;
};
// the figure to the dollar (cards.exact), where two different figures would print the same in usd
const usdExact = (n) => { if (n == null || n === '') return '—'; const x = Number(n), a = Math.floor(Math.abs(x) + 0.5); return `${x < 0 && a ? '−' : ''}$${a.toLocaleString('en-US')}`; };
const day = (s) => (s ? new Date(String(s).slice(0, 10) + 'T00:00:00Z').toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC'}) : '—');
const when = (s) => (s ? new Date(s).toLocaleString('en-US', {month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'}) : '—');
// One name per field, every page (trail, Reconcile, Dataset, Explore, gold, evidence)
const FIELDS = {revenue: 'Revenue', capex: 'Capex', opex: 'Opex', cost_of_revenue: 'Cost of revenue', operating_income: 'Operating income', segment_capex: 'Segment capex', segment_revenue: 'Segment revenue',
  ppe_category: 'PP&E by category', finance_lease_liability: 'Finance lease liabilities', purchase_commitments: 'Purchase commitments'};
const LABEL = {...FIELDS, cost_of_revenue_part: 'Cost line'};

// every write is JSON: a body gets Content-Type application/json unless the caller set one (the server refuses a write without it, 403)
const withJson = (opts) => (opts && opts.body != null && !Object.keys(opts.headers || {}).some((k) => k.toLowerCase() === 'content-type') ? {...opts, headers: {...(opts.headers || {}), 'Content-Type': 'application/json'}} : opts);
async function api(path, opts) {
  const r = await fetch(path, withJson(opts));
  const d = await r.json();
  if (!r.ok) { const e = new Error(d.error || r.statusText); e.status = r.status; throw e; }  // 409: the record changed since the page loaded
  return d;
}
let me = 'Kenny Geiler';
try { me = localStorage.getItem('datahq-me') || me; } catch {}
$('#me').value = me;
$('#me').addEventListener('input', (e) => { me = e.target.value; try { localStorage.setItem('datahq-me', me); } catch {} });
let NAMES = {}, SCOPE = [];
// the jump box offers the scope only (T2); a ticker typed from outside it still navigates, an explicit ask
api('/api/data?t=&f=none').then((d) => { SCOPE = d.scope || Object.keys(d.names); NAMES = Object.fromEntries(SCOPE.filter((t) => d.names[t]).map((t) => [t, d.names[t]])); $('#tickers').replaceChildren(...Object.entries(NAMES).map(([t, n]) => h('option', {value: t}, n))); });
$('#jump').addEventListener('change', (e) => { const v = e.target.value.trim().toUpperCase(); const t = NAMES[v] ? v : Object.keys(NAMES).find((k) => NAMES[k].toUpperCase() === v) || (/^[A-Z.\-]{1,6}$/.test(v) ? v : null); if (t) { e.target.value = ''; go(`data?ticker=${t}`); } });

// `page`: rows per page (V4: Dataset Rows draws at most 100 at a time), a pager under the table; a sort reorders every row
// and goes back to the first page
const PAGE_ROWS = 100;
function table(cols, rows, {key, onRow, detail, page} = {}) {
  const tb = h('tbody');
  let list = rows, at = 0;
  const pager = page && rows.length > page ? h('div', {class: 'pager small text-secondary', role: 'navigation', 'aria-label': 'Pages'}) : null;
  const draw = () => {
    tb.replaceChildren();
    const shown = pager ? list.slice(at, at + page) : list;
    for (const r of shown) {
      const tr = h('tr', {class: onRow || detail ? 'click' : null, tabindex: onRow || detail ? 0 : null, role: onRow || detail ? 'button' : null, onkeydown: onRow || detail ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tr.click(); } } : null}, cols.map((c) => h('td', {class: [c.n && 'n', c.wide && 'wide'].filter(Boolean).join(' ') || null}, c.f ? c.f(r) : r[c.k] ?? '—')));
      tb.append(tr);
      if (onRow) tr.addEventListener('click', () => onRow(r));
      if (detail) tr.addEventListener('click', () => {
        const next = tr.nextElementSibling;
        if (next && next.classList.contains('detail')) { next.remove(); tr.classList.remove('open'); return; }
        tr.classList.add('open');
        tr.after(h('tr', {class: 'detail'}, h('td', {colspan: cols.length}, detail(r))));
      });
    }
    if (pager) {
      const last = Math.max(0, Math.ceil(list.length / page) - 1), n = Math.floor(at / page);
      const to = (i) => { at = Math.min(last, Math.max(0, i)) * page; draw(); tb.closest('.card').scrollIntoView({block: 'start'}); };
      pager.replaceChildren(h('span', {}, `Rows ${int(at + 1)}–${int(Math.min(list.length, at + page))} of ${int(list.length)}`),
        h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary', disabled: n === 0 || null, onclick: () => to(n - 1)}, 'Previous'),
        h('span', {}, `Page ${int(n + 1)} of ${int(last + 1)}`),
        h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary', disabled: n === last || null, onclick: () => to(n + 1)}, 'Next'));
    }
  };
  let sort = null, dir = 1;
  const head = h('tr', {}, cols.map((c) => {
    const th = h('th', {class: [c.n && 'n', c.wide && 'wide'].filter(Boolean).join(' ') || null});
    if (c.sort === false) th.append(c.t);
    else th.append(h('button', {type: 'button', class: 'btn btn-link btn-sm p-0 align-baseline', style: 'color:inherit', onclick: () => {
      dir = sort === c ? -dir : (c.n ? -1 : 1); sort = c;
      const v = c.s || ((r) => r[c.k]);
      list = [...rows].sort((a, b) => { const x = v(a), y = v(b); if (x == null || x === '') return 1; if (y == null || y === '') return -1; return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * dir; });
      at = 0; draw();
    }}, c.t));
    return th;
  }));
  draw();
  return h('div', {class: 'card'}, h('div', {class: 'table-responsive'}, h('table', {class: 'table table-sm table-vcenter card-table table-hover'}, h('thead', {}, head), tb)), pager || '');
}


function sources(v) {
  const wrap = h('div', {});
  if (v.decision) wrap.append(h('div', {class: 'src'}, h('div', {}, `Decision: ${v.decision.kind} · ${v.decision.reviewer}`), h('div', {class: 'muted'}, v.decision.reason)));
  if (v.why) wrap.append(h('div', {class: 'src'}, h('div', {class: 'muted'}, '10-K text: ', v.why.text.slice(0, 400)), h('a', {href: safeHref(v.why.url), target: '_blank', rel: 'noopener'}, 'Open in 10-K ↗')));
  for (const s of v.sources) {
    wrap.append(h('div', {class: 'src'},
      h('div', {}, `${LABEL[s.field] || s.field}: `, h('b', {}, s.cell), ` · Line “${s.row}” · Column “${s.col.replaceAll(' | ', ' ')}”`),
      h('div', {class: 'muted small'}, `10-K filed ${day(s.filed)} · ${s.unit || 'unit from the document'}`, s.notes ? ` · ${s.notes}` : ''),
      // the cited cell's crop, the same picture rules as the trail (crops.brief over crops.state)
      h('div', {class: 'cites', style: 'max-width:16rem'}, citeCell({crop: s.crop || {state: 'none'}, viewer: (s.crop || {}).viewer, link: s.deep, form: s.form, filed: String(s.filed || '').slice(0, 10), row: s.row, column: s.col.replaceAll(' | ', ' '), cell: s.cell}, LABEL[s.field] || s.field))));
  }
  if (!v.sources.length) wrap.append(h('p', {class: 'muted'}, 'No citation'));
  return wrap;
}

// ── Shared ──────────────────────────────────────────────────────────────────
let hqCache = null;
const hq = async (fresh) => (hqCache = !fresh && hqCache ? hqCache : await api('/api/hq'));
const pct = (x) => (x == null ? '—' : x < .001 ? '<0.1%' : `${(100 * x).toFixed(x < .1 ? 1 : 0)}%`);
const fig = (l, n, s, bad) => h('div', {class: 'fig'}, h('div', {class: 'l'}, l), h('div', {class: 'n' + (bad ? ' bad' : '')}, n), h('div', {class: 's' + (bad ? ' bad' : '')}, s));
const INDUSTRY = {hyperscaler: 'Hyperscaler', neocloud: 'Neocloud', miner_to_hpc: 'Miner to HPC', chip_seller: 'Chip design', chip_equipment: 'Chip equipment', component_supplier: 'Memory, networking, servers', datacenter_build: 'Data-center build', datacenter_landlord: 'Data-center landlord', power: 'Power producer', ai_software: 'AI software', other: 'Adopters and other'};
// ── Data-first pieces: a cell with intensity, a mini bar, year bars, a dot plot ──────────────────────────────────
// One row per year: a dark AI part inside a light whole, labelled with both.
// ── Data: the dataset as a grid, provenance one click deep ──────────────────
const KINDS = {spent: 'spent', committed: 'committed', derived: 'derived', planned: 'planned'};
const ALL_KINDS = Object.keys(KINDS);
const parseQ = (s) => Object.fromEntries(new URLSearchParams(s));
// ── state words (ledger/core/states.py via /pages/_states.js). Every page reads them through these three, never STATES
// directly: if _states.js did not load, the page still renders, with the state's own name and no colour. ── states-helpers
const stateData = () => (typeof STATES === 'undefined' ? null : STATES);
// [tone, word] for a state; an undeclared state reads as the machine's absent state (never a good one)
function stateWord(m, s) {
  const d = stateData(), a = typeof STATE_ABSENT === 'undefined' ? {} : STATE_ABSENT;
  return (d && d[m] && (d[m][s] || d[m][a[m]])) || ['text-secondary', String(s)];
}
const stateKnown = (m, s) => { const d = stateData(); return !!(d && d[m] && d[m][s]); };
// the page group words of a machine ({checked: 'Checked', ...}); without the declarations, each group's own name
function stateGroups(m = 'row') {
  const g = typeof STATE_GROUPS === 'undefined' ? null : STATE_GROUPS[m];
  return g || {checked: 'checked', done: 'done', explained: 'explained', open: 'open', blocked: 'blocked'};
}
// ── end states-helpers
const checkWord = (label) => stateWord('check', label)[1];
// a company's open items by bucket (states.buckets, the API's `counts`), each in its row word and tone, zeros left out:
// "Needs review 7 · Proposed 4". The Proof board, the trail and Reconcile's header say the same numbers with these words.
const OPEN_BUCKETS = ['bad', 'wait', 'blocked'];
const bucketParts = (counts) => OPEN_BUCKETS.filter((b) => (counts || {})[b]).map((b) => [b, counts[b]]);
function bucketLine(counts) {
  return bucketParts(counts).map(([b, n], i) => { const [cls, word] = stateWord('row', b); return [i ? h('span', {class: 'text-secondary'}, ' · ') : '', h('span', {class: cls + ' fw-medium text-nowrap'}, `${word} ${int(n)}`)]; });
}  // a value's reconcile label in states.CHECK's words

// the drawer
let drawerOpener = null;
function drawer(...kids) {
  closeDrawer();
  drawerOpener = document.activeElement;
  const box = h('div', {class: 'drawer', role: 'dialog', 'aria-modal': 'false', 'aria-label': 'Details'}, h('button', {type: 'button', class: 'btn-close close', 'aria-label': 'Close', onclick: closeDrawer}), ...kids);
  skin(box);
  document.body.append(box);
  box.querySelector('.close').focus();
  return box;
}
function closeDrawer() { const had = document.querySelector('.drawer'); document.querySelectorAll('.drawer').forEach((d) => d.remove()); if (had && drawerOpener && drawerOpener.isConnected) { drawerOpener.focus(); } drawerOpener = null; }
window.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawer(); if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('td.cell')) { e.preventDefault(); e.target.click(); } });

// a card with a title and a table; cols: {t, k|f, num, w}
function dtable(title, cols, rows, {foot, note} = {}) {
  const tbl = h('table', {class: 'table table-sm table-vcenter card-table'},
    h('thead', {}, h('tr', {}, cols.map((c) => h('th', {class: c.num ? 'num' : null, style: c.w ? `width:${c.w}` : null}, c.t)))),
    h('tbody', {}, rows.map((r) => h('tr', {class: r._cls || null}, cols.map((c) => h('td', {class: [c.num && 'num', c.strong && 'fw-semibold'].filter(Boolean).join(' ') || null}, c.f ? c.f(r) : r[c.k] ?? '—'))))),
    foot ? h('tfoot', {}, h('tr', {}, foot.map((x, i) => h('td', {class: (cols[i] && cols[i].num ? 'num ' : '') + 'fw-semibold'}, x)))) : '');
  return h('div', {class: 'card'}, h('div', {class: 'card-header py-2'}, h('h3', {class: 'card-title m-0'}, title), note ? h('span', {class: 'ms-auto text-secondary small'}, note) : ''), h('div', {class: 'table-responsive'}, tbl));
}

// one name per stage, the Proof board and the trail alike (proof.STAGE_LABEL says the same)
const STAGE_LABEL_UI = {ingest: 'Filings', values: 'Statement figures', facts: 'Note figures', statements: 'AI disclosures', mapping: 'Category mapping', planned: 'Guidance and projects', release: 'Release'};

const TABLES = [
  ['taxonomy', 'All rows', 'All measures'],
  ['values', 'Values', 'Income and cash-flow statement figures'],
  ['facts', 'Facts', 'Note figures'],
  ['statements', 'Statements', 'Quoted statements'],
  ['projects', 'Projects', 'Named projects'],
  ['companies', 'Companies', 'Companies, industry and SIC code'],
];
const RAW_NUM = new Set(['value', 'value_high', 'change_from_prior', 'share', 'amount_low', 'amount_high', 'amount_mid', 'xbrl', 'capacity_mw', 'scale', 'sic', 'gpus']);

// ── Navigation and the kit's theme ──────────────────────────────────────────
function go(hash) { location.hash = hash; }
// the kit's theme follows the system; its classes land on every control the pages build by hand
const syncTheme = () => { document.documentElement.setAttribute('data-bs-theme', matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); };
syncTheme(); matchMedia('(prefers-color-scheme: dark)').addEventListener('change', syncTheme);
function skin(root) {
  root.querySelectorAll('select:not(.form-select)').forEach((el) => el.classList.add('form-select', 'form-select-sm', 'w-auto', 'd-inline-block'));
  root.querySelectorAll('input[type=text]:not(.form-control), textarea:not(.form-control)').forEach((el) => el.classList.add('form-control', 'form-control-sm'));
  root.querySelectorAll('input[type=text].form-control:not(.w-auto)').forEach((el) => { if (!el.style.flex && !el.style.width) el.classList.add('w-auto', 'd-inline-block'); });
  root.querySelectorAll('input[type=checkbox]:not(.form-check-input)').forEach((el) => el.classList.add('form-check-input'));
  root.querySelectorAll('button.btn:not(.btn-primary):not(.btn-outline-secondary):not(.btn-ghost-secondary):not(.btn-link):not(.seg > .btn)').forEach((el) => el.classList.add('btn-primary', 'btn-sm'));
  root.querySelectorAll('.btn-group[role=group]:not(.seg)').forEach((el) => el.classList.add('seg'));  // every either/or choice is the one segmented control (V3)
  root.querySelectorAll('button:not(.btn):not(.btn-close):not(.badge)').forEach((el) => el.classList.add('btn', 'btn-link', 'btn-sm', 'p-0', 'align-baseline'));
  root.querySelectorAll('button.badge').forEach((el) => el.classList.add('bg-secondary-lt', 'border-0'));
  root.querySelectorAll('table:not(.table)').forEach((el) => el.classList.add('table', 'table-sm', 'table-vcenter'));
  root.querySelectorAll('section:not(.card):not(.figs):not(.hrow)').forEach((el) => { if (el.querySelector(':scope > .sechead, :scope > h2')) el.classList.add('card'); });
  root.querySelectorAll('section.card > h2:first-child').forEach((el) => { const head = h('div', {class: 'sechead'}); el.replaceWith(head); head.append(el); });
  root.querySelectorAll('section.card > .card').forEach((el) => { el.classList.remove('card'); el.classList.add('card-table-wrap'); });
  fitTables(root);
}
// V4: a table that fits its card lets its sticky header follow the page (.fit: no scroll box of its own); a wider one
// scrolls inside the card at most a viewport tall, its header pinned there (.wide). Measured again on resize.
function fitTables(root = document) {
  root.querySelectorAll('.table-responsive').forEach((el) => {
    if (!el.isConnected) return;
    el.classList.remove('fit', 'wide');
    const t = el.querySelector(':scope > table');
    el.classList.add(t && t.scrollWidth > el.clientWidth + 1 ? 'wide' : 'fit');
  });
}
let fitTimer;
window.addEventListener('resize', () => { clearTimeout(fitTimer); fitTimer = setTimeout(() => fitTables(), 150); });

// ── The category-mapping decision card (ledger/review/mapcard.py): the same on the trail and in Reconcile ──────────────
// D is mapcard.decisions' card; `actions` (Reconcile only) is a node placed under it. Labels, values, statuses.
const MAP_STATE = {checked: 'text-green', open: 'text-orange', blocked: 'text-red'};
const MAP_TAG = {same: 'text-green', differs: 'text-red', ambiguous: 'text-orange', inconsistent: 'text-orange'};
function mappingDecision(D, actions) {
  const L = D.line || {}, P = D.proposed, T = D.tag || {};
  const item = (title, ...body) => h('div', {class: 'datagrid-item'}, h('div', {class: 'datagrid-title'}, title), h('div', {class: 'datagrid-content', style: 'overflow-wrap:anywhere'}, body));
  const series = (L.series || []).map((s) => `${s.period} ${usd(s.value)}`).join(' · ');
  const def = (m) => h('details', {class: 'mt-1'}, h('summary', {class: 'small', style: 'cursor:pointer', title: m.definition}, `${m.label} · `, h('span', {class: 'font-monospace small'}, m.member), h('span', {class: 'text-secondary'}, ` · ${m.why}`)), h('div', {class: 'small text-secondary mt-1'}, m.definition));
  return h('div', {class: 'mapcard'},
    h('div', {class: 'd-flex align-items-baseline flex-wrap gap-2 mb-2'}, h('span', {class: 'fw-semibold'}, D.name),
      h('span', {class: (MAP_STATE[D.state.state] || 'text-secondary') + ' small fw-medium'}, D.state.label)),
    h('div', {class: 'datagrid', style: '--tblr-datagrid-item-width: 16rem'},
      item('Company line', L.latest ? [h('span', {class: 'fw-medium'}, usd(L.latest.value)), ` ${L.latest.period}`] : '—',
        L.link ? h('a', {href: safeHref(L.link), target: '_blank', rel: 'noopener', class: 'ms-2 small'}, 'Open ↗') : '',
        series ? h('div', {class: 'small text-secondary'}, series) : ''),
      item('Proposed', P ? [h('span', {class: 'fw-medium'}, P.label || P.member), ' ', h('span', {class: 'font-monospace small text-secondary'}, P.member),
        P.definition ? h('div', {class: 'small mt-1'}, P.definition) : '', P.definition ? h('div', {class: 'small text-secondary'}, `Source: ${D.source}`) : ''] : h('span', {class: 'text-secondary'}, 'None')),
      item('Company’s own tag', h('span', {class: MAP_TAG[T.status] || 'text-secondary'}, T.text),
        T.definition && T.status === 'differs' ? h('div', {class: 'small mt-1'}, T.definition) : '',
        T.accession ? h('div', {class: 'small text-secondary'}, `XBRL instance ${T.accession} · ${T.period_end}`) : ''),
      item('Basis', D.basis ? `“${D.basis}”` : '—', h('div', {class: 'small text-secondary'}, [D.by, D.at].filter(Boolean).join(' · '), D.confirmed_by ? ` · confirmed ${D.confirmed_by} ${D.confirmed_at || ''}` : '')),
      item('Alternatives', (D.alternatives || []).length ? D.alternatives.map(def) : h('span', {class: 'text-secondary'}, 'None')),
      item('Affects', D.affects ? D.affects.text : '—')),
    actions || '');
}

// ── A cited cell's crop (ledger/checks/crops.py cells/brief): the server decides the state; every page says it with these words ──
const cropWord = (s) => stateWord('crop', s);  // states.CROP: the server decides the state (crops.state), every page says it with these words
const SEC_LINK = /^https:\/\/www\.sec\.gov\//;  // only an SEC address becomes a link
const cropState = (c) => { const [cls, word] = cropWord(c.state); return h('span', {class: cls}, word, c.state === 'not_located' && c.reason ? h('span', {class: 'text-secondary'}, ` · ${c.reason}`) : ''); };
// the crop, full size, over the page: the cell boxed in red, its filing, Open in filing; Esc or a click outside closes it
function cropBox(src, caption, links) {
  const close = () => { box.remove(); document.removeEventListener('keydown', esc); if (opener && opener.isConnected) opener.focus(); };
  const esc = (e) => { if (e.key === 'Escape') close(); };
  const opener = document.activeElement;
  const box = h('div', {class: 'cropbox', role: 'dialog', 'aria-modal': 'true', 'aria-label': caption, onclick: (e) => { if (e.target === box) close(); }},
    h('figure', {class: 'cropbox-fig'}, h('div', {class: 'd-flex align-items-baseline gap-3 mb-2'}, h('figcaption', {class: 'small'}, caption), h('span', {class: 'ms-auto d-flex gap-3 small'}, links),
      h('button', {type: 'button', class: 'btn-close', 'aria-label': 'Close', onclick: close})), h('img', {src, alt: caption})));
  document.addEventListener('keydown', esc);
  document.body.append(box);
  box.querySelector('.btn-close').focus();
}
// one cited cell in a row: the thumbnail (or the crop's state when there is no current crop) over one line, Form date · Open · sec.gov
function citeCell(w, what) {
  const c = w.crop || {state: 'none'};
  const caption = [what, what && w.row && what.includes(w.row) ? '' : w.row, w.column, w.cell].filter(Boolean).join(' · ');
  const links = [w.viewer ? h('a', {href: safeHref(w.viewer), target: '_blank', rel: 'noopener', title: 'Open in filing, the cell outlined'}, 'Open') : '', SEC_LINK.test(w.link || '') ? h('a', {href: safeHref(w.link), target: '_blank', rel: 'noopener noreferrer'}, 'sec.gov ↗') : ''];
  const thumb = c.state === 'located' && c.url
    ? h('button', {type: 'button', class: 'crop-thumb', title: caption, onclick: () => cropBox(c.url, caption, [w.viewer ? h('a', {href: safeHref(w.viewer), target: '_blank', rel: 'noopener'}, 'Open in filing') : '', links[1] ? links[1].cloneNode(true) : ''])}, h('img', {src: c.url, alt: caption, loading: 'lazy', onload: (e) => focusCell(e.target), onerror: (e) => cropFailed(e.target.parentElement, w.viewer)}))
    : h('div', {class: 'crop-none small'}, cropState(c));
  return h('div', {class: 'cite'}, w.role ? h('div', {class: 'cite-role small fw-medium'}, w.role) : '', thumb, w.mark ? h('div', {class: 'cite-mark small fw-medium text-orange'}, w.mark) : '',
    h('div', {class: 'cite-line small'}, `${w.form || '10-K'} ${w.filed || ''}`.trim(), links.map((l) => (l ? [' · ', l] : ''))));
}
// a fact whose readings disagree across filings (ledger/checks/ties.py restatement): the server's line, exact figures as filed,
// and the pair to compare. Shown whatever the row's state; the words come from the server (states.RESTATED, SUPERSEDED).
function restatedLine(r, compare) {
  if (!r) return '';
  const link = compare && r.compare ? [' · ', h('a', {href: `#evidence/compare?a=${encodeURIComponent(r.compare.a)}&b=${encodeURIComponent(r.compare.b)}`}, 'Compare filings')] : '';
  return h('div', {class: 'small text-orange restated'}, r.line, link);
}
// a figure calculated from several cells (ledger/checks/calc.py): the formula with its result, the arithmetic on the real
// inputs, and each cross-check (the filing's own total, SEC XBRL) in states.CROSSCHECK's tone. The trail and the gold set.
function calcBlock(c) {
  if (!c) return '';
  return h('div', {class: 'calc small mb-2'}, h('div', {class: 'fw-medium'}, c.line), h('div', {class: 'text-secondary money-line'}, c.arithmetic),
    c.holds ? '' : h('div', {class: stateWord('crosscheck', 'differs')[0]}, `Stored value ${usd(c.value)}`),
    (c.checks || []).map((x) => h('div', {class: stateWord('crosscheck', x.state)[0]}, x.text)));
}
// V7: the cited figure renders at no less than FIG_PX css px in a thumbnail (11 px asked; 11.5 kept) and EV_FIG_PX on Evidence (12 asked)
const FIG_PX = 11.5, EV_FIG_PX = 12.5;
const DIGIT_EM = 0.72;  // a figure's digits stand about 0.72 em tall: font size = ink height / DIGIT_EM
// The crop's own marks, found by colour on a downsampled copy: the cited cell boxed in red (#dc2626), its column header in
// blue (#2563eb), and the cited figure's ink height inside the red box (natural px). Null when the canvas cannot read it.
function cropMarks(img) {
  const W = img.naturalWidth, H = img.naturalHeight;
  if (!W || !H) return null;
  const k = Math.max(1, Math.floor(W / 700)), cw = Math.ceil(W / k), ch = Math.ceil(H / k);
  const cv = document.createElement('canvas'); cv.width = cw; cv.height = ch;
  const g = cv.getContext('2d', {willReadFrequently: true}); g.drawImage(img, 0, 0, cw, ch);
  const px = g.getImageData(0, 0, cw, ch).data;
  const at = (x, y) => (y * cw + x) * 4;
  const box = (test) => { let x0 = cw, y0 = ch, x1 = -1, y1 = -1; for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) { const i = at(x, y); if (test(px[i], px[i + 1], px[i + 2])) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } } return x1 < 0 ? null : {x0, y0, x1, y1}; };
  const red = box((r, gg, b) => r > 190 && gg < 80 && b < 80);
  const blue = red ? box((r, gg, b) => r < 90 && gg > 70 && gg < 140 && b > 200) : null;
  const plain = (i) => px[i] + px[i + 1] + px[i + 2] < 330 && Math.max(px[i], px[i + 1], px[i + 2]) - Math.min(px[i], px[i + 1], px[i + 2]) < 40;
  let inkH = null;
  if (red) {  // the figure's digit height inside the box's 3 px border: per ink column its top-to-bottom run, the median taken,
    // so a $ sign, parentheses or a footnote mark (taller or higher than the digits) do not count; the row's yellow tint
    // shifts the ink's hue, so dark and not red is enough
    const b = Math.ceil(8 / k), fig = (i) => px[i] + px[i + 1] + px[i + 2] < 330 && !(px[i] > 150 && px[i + 1] < 110);
    const hs = [];
    for (let x = red.x0 + b; x <= red.x1 - b; x++) {
      let y0 = -1, y1 = -1;
      for (let y = red.y0 + b; y <= red.y1 - b; y++) if (fig(at(x, y))) { if (y0 < 0) y0 = y; y1 = y; }
      if (y0 >= 0) hs.push(y1 - y0 + 1);
    }
    if (hs.length) { hs.sort((p, q) => p - q); inkH = hs[Math.floor(hs.length * 0.6)] * k; }
  }
  return {W, H, k, cw, ch, px, at, plain, red, blue, inkH};
}
// the least scale (css px per natural px) at which the cited figure reads at `px`; a figure whose ink is not found is drawn at
// the filing's own size (the crops are taken at device scale 2)
const legibleScale = (m, px = FIG_PX) => (m && m.inkH ? px * DIGIT_EM / m.inkH : 0.5);
// the thumbnail: the cited row with the row above and below, its label and the column header, at a size the figure reads
// (V7). The columns and rows in between are folded out (a grey seam marks each fold); the full crop is one click away (cropBox).
function focusCell(img) {
  if (img.dataset.folded) return;
  img.dataset.folded = '1';
  try {
    const frame = img.parentElement, fw = frame.clientWidth;
    const m = cropMarks(img);
    if (!m || !fw) return;
    const {W, H, k, cw, ch, px, at, plain, red, blue} = m;
    if (!red) return;  // no box found: the whole crop, contained
    // the label: dark columns on the cell's row, left of the box, split where a gap wider than ~15 px opens
    const dark = [];
    for (let x = 0; x < red.x0; x++) { let d = false; for (let y = red.y0 + 2; y <= red.y1 - 2 && !d; y++) { const i = at(x, y); d = px[i] + px[i + 1] + px[i + 2] < 330; } if (d) dark.push(x); }
    let label = null;
    if (dark.length) { let a = dark[0], b = a; for (const x of dark) { if (x - b > Math.ceil(30 / k)) break; b = x; } label = [a, b]; }
    const merge = (bands) => bands.sort((p, q) => p[0] - q[0]).reduce((out, b) => { const l = out[out.length - 1]; if (l && b[0] <= l[1] + 4) l[1] = Math.max(l[1], b[1]); else out.push([...b]); return out; }, []);
    const clampX = (v) => Math.max(0, Math.min(W, v)), clampY = (v) => Math.max(0, Math.min(H, v));
    const pad = Math.max(16, (red.x1 - red.x0) * k * 0.3), rowH = (red.y1 - red.y0 + 1) * k;
    // rows: the column header (its blue box) and the cited row with one row above and one below
    // a neighbour row is taken whole: from the cited row outward, past the blank run, through the next line of text, to the
    // blank run after it (dark pixels in the cell's column; the boxes are coloured and do not count)
    const c0 = Math.min(red.x0, blue ? blue.x0 : red.x0), c1 = Math.max(red.x1, blue ? blue.x1 : red.x1);
    const inkRow = (y) => { for (let x = c0; x <= c1; x++) { const i = at(x, y); if (px[i] + px[i + 1] + px[i + 2] < 330 && !(px[i] > 150 && px[i + 1] < 110) && !(px[i + 2] > 180 && px[i] < 120)) return true; } return false; };
    const neighbour = (from, dir) => {  // downsampled y of the far edge of the next text line, or null when none is near
      const lim = Math.ceil(2.5 * rowH / k); let y = from, n = 0;
      while (y >= 0 && y < ch && n < lim && !inkRow(y)) { y += dir; n++; }
      if (y < 0 || y >= ch || n >= lim) return null;
      while (y >= 0 && y < ch && n < 2 * lim && inkRow(y)) { y += dir; n++; }
      return Math.max(0, Math.min(ch - 1, y + dir));
    };
    const up = neighbour(red.y0 - 1, -1), down = neighbour(red.y1 + 1, 1);
    const ys = merge([blue ? [clampY(blue.y0 * k - 4), clampY((blue.y1 + 1) * k + 4)] : [0, 0],
      [clampY(up !== null && (!blue || up > blue.y1) ? up * k : red.y0 * k - 4), clampY(down !== null ? (down + 1) * k : (red.y1 + 1) * k + 4)]].filter((b) => b[1] > b[0]));
    // Column boundaries: a band's edge never cuts a neighbour's figure. `ink` marks every x where the rows shown carry dark,
    // uncoloured text (the red and blue boxes are coloured; a rule line across the table is skipped); an edge padded out
    // from the kept range stops in the middle of the blank run before the first ink, so a neighbouring value is either
    // whole outside the band or not shown at all, never a sliver.
    const ink = new Uint8Array(cw);
    for (const [a, b] of ys) {
      for (let y = Math.floor(a / k); y < Math.min(ch, Math.ceil(b / k)); y++) {
        let n = 0; for (let x = 0; x < cw; x++) if (plain(at(x, y))) n++;
        if (n > cw * 0.5) continue;  // a rule line, not text
        for (let x = 0; x < cw; x++) if (!ink[x] && plain(at(x, y))) ink[x] = 1;
      }
    }
    const edge = (from, dir, reach) => {  // from the kept range's edge outward, at most `reach` (downsampled px): where to cut
      let x = from + dir, n = 0;
      while (x >= 0 && x < cw && n < reach && !ink[x]) { x += dir; n++; }
      if (x < 0 || x >= cw || n >= reach) return from + dir * n;  // no ink within reach: the full pad
      return from + dir * Math.floor(n / 2);  // ink at x: cut in the middle of the blank run before it
    };
    const keep0 = Math.min(red.x0, blue ? blue.x0 : red.x0), keep1 = Math.max(red.x1, blue ? blue.x1 : red.x1), reach = Math.ceil(pad / k);
    const cellBand = [clampX(edge(keep0, -1, reach) * k), clampX((edge(keep1, 1, reach) + 1) * k)];
    // the label column ends at the first blank run (about 12 px) past the cell's own label, so a longer label on a row
    // above or below shows whole rather than cut mid-word; when that run is far (a label wider than three of the cited
    // one), the band stops before the next ink instead
    const gutter = (from, dir, limit) => {  // the middle of the first blank run of g px from `from` towards `limit` (exclusive), or null
      const g = Math.max(2, Math.ceil(12 / k)); let run = 0;
      for (let x = from + dir; dir > 0 ? x < limit : x > limit; x += dir) { run = ink[x] ? 0 : run + 1; if (run >= g) return x - dir * (g - 1 - Math.floor(g / 2)); }
      return null;
    };
    const lw = label ? label[1] - label[0] + 1 : 0;
    const lend = label ? gutter(label[1], 1, keep0) : null, lbeg = label ? gutter(label[0], -1, -1) : null;
    const labelBand = label ? [clampX((lbeg !== null && label[0] - lbeg <= 2 * lw ? lbeg : lbeg === null ? 0 : edge(label[0], -1, Math.ceil(10 / k))) * k),
      clampX(((lend !== null && lend - label[1] <= 2 * lw ? lend : edge(label[1], 1, Math.ceil(14 / k))) + 1) * k)] : null;
    const gap = 6, span = (bands) => bands.reduce((n, b) => n + b[1] - b[0], 0) + gap * (bands.length - 1);
    const CH = span(ys), maxH = 128, need = legibleScale(m);
    // the scale: the frame's fit, never under what the figure needs to read, never over 1:1 with the filing
    const scaleFor = (bands) => Math.min(Math.max(Math.min(fw / span(bands), maxH / CH), need), Math.max(need, 0.5));
    let xs = merge([labelBand, cellBand].filter(Boolean)), sc = scaleFor(xs);
    if (span(xs) * sc > fw && labelBand) { xs = [cellBand]; sc = scaleFor(xs); }  // too wide at a legible size: the label goes (it is in the caption)
    if (span(xs) * sc > fw) {  // still too wide: a window on the cell, as wide as the frame
      const w = fw / sc, c = (Math.max(red.x0 * k, cellBand[0]) + Math.min((red.x1 + 1) * k, cellBand[1])) / 2;
      const x0 = Math.max(0, Math.min(W - w, c - w / 2));
      xs = [[x0, Math.min(W, x0 + w)]];
    }
    const CW = span(xs);
    const out = document.createElement('canvas'); out.width = CW; out.height = CH;
    const o = out.getContext('2d'); o.fillStyle = '#e5e7eb'; o.fillRect(0, 0, CW, CH);
    let dy = 0;
    for (const [y0, y1] of ys) { let dx = 0; for (const [x0, x1] of xs) { o.drawImage(img, x0, y0, x1 - x0, y1 - y0, dx, dy, x1 - x0, y1 - y0); dx += x1 - x0 + gap; } dy += y1 - y0 + gap; }
    Object.assign(out.style, {display: 'block', width: `${CW * sc}px`, height: `${CH * sc}px`, margin: '0 auto'});
    out.setAttribute('role', 'img'); out.setAttribute('aria-label', img.alt);
    if (m.inkH) out.dataset.figPx = (m.inkH / DIGIT_EM * sc).toFixed(1);  // the cited figure's rendered size, for the layout check
    img.style.display = 'none';
    frame.style.height = `${Math.ceil(CH * sc)}px`;  // the frame takes the strip's height: no empty band, no overlap
    frame.append(out);
  } catch (e) { /* a picture the canvas cannot read stays whole */ }
}
// V7: a full crop (Evidence) drawn at least as large as its cited figure needs to read; a crop wider than its column then
// scrolls sideways inside its frame, opened at the cell
function legibleCrop(img) {
  try {
    const m = cropMarks(img), frame = img.closest('.ev-frame');
    if (!m || !frame) return;
    const shown = img.clientWidth / m.W, need = legibleScale(m, EV_FIG_PX), sc = Math.max(shown, need);
    if (need > shown) { img.style.width = `${Math.ceil(m.W * need)}px`; img.style.maxWidth = 'none'; }
    if (m.inkH) img.dataset.figPx = (m.inkH / DIGIT_EM * sc).toFixed(1);
    if (m.red) frame.scrollLeft = Math.max(0, ((m.red.x0 + m.red.x1) / 2) * m.k * sc - frame.clientWidth / 2);
  } catch (e) { /* a picture the canvas cannot read stays as drawn */ }
}
// V7: a crop that does not load is never an empty frame: it says so, with the way to the filing
function cropFailed(frame, viewer) {
  frame.replaceWith(h('div', {class: 'crop-none small text-secondary'}, 'Crop unavailable', viewer ? [' · ', h('a', {href: safeHref(viewer), target: '_blank', rel: 'noopener'}, 'Open in filing')] : ''));
}
