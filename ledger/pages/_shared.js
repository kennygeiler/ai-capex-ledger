// DATAHQ: everything more than one page uses. Plain script, globals; app.html loads it first.
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
const int = (n) => (n == null || n === '' ? '—' : Number(n).toLocaleString('en-US'));
const usd = (n) => {
  if (n == null || n === '') return '—';
  const m = Number(n) / 1e6;
  return (m < 0 ? '−' : '') + '$' + Math.abs(m).toLocaleString('en-US', {maximumFractionDigits: Math.abs(m) >= 100 ? 0 : 1}) + 'M';
};
const day = (s) => (s ? new Date(String(s).slice(0, 10) + 'T00:00:00Z').toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC'}) : '—');
const when = (s) => (s ? new Date(s).toLocaleString('en-US', {month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'}) : '—');
const compact = (n) => new Intl.NumberFormat('en', {notation: 'compact', maximumFractionDigits: 1}).format(n || 0);
const LABEL = {revenue: 'Revenue', capex: 'Capex', opex: 'Opex', cost_of_revenue: 'Cost of revenue', cost_of_revenue_part: 'Cost line', operating_income: 'Operating income'};
const XBRL = {agree: 'matches SEC data', definition_gap: 'differs from SEC data, explained by code', unresolved: 'differs from SEC data, decided by a person', not_reported: 'not reported'};

async function api(path, opts) {
  const r = await fetch(path, opts);
  const d = await r.json();
  if (!r.ok) throw new Error(d.error || r.statusText);
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

function table(cols, rows, {key, onRow, detail} = {}) {
  const tb = h('tbody');
  const draw = (list) => {
    tb.replaceChildren();
    for (const r of list) {
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
  };
  let sort = null, dir = 1;
  const head = h('tr', {}, cols.map((c) => {
    const th = h('th', {class: [c.n && 'n', c.wide && 'wide'].filter(Boolean).join(' ') || null});
    if (c.sort === false) th.append(c.t);
    else th.append(h('button', {type: 'button', style: 'color:inherit', onclick: () => {
      dir = sort === c ? -dir : (c.n ? -1 : 1); sort = c;
      const v = c.s || ((r) => r[c.k]);
      draw([...rows].sort((a, b) => { const x = v(a), y = v(b); if (x == null || x === '') return 1; if (y == null || y === '') return -1; return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * dir; }));
    }}, c.t));
    return th;
  }));
  draw(rows);
  return h('div', {class: 'card'}, h('div', {class: 'table-responsive'}, h('table', {class: 'table table-sm table-vcenter card-table table-hover'}, h('thead', {}, head), tb)));
}

const FACT = {segment_capex: 'Segment capex', segment_revenue: 'Segment revenue', ppe_category: 'PP&E by category', finance_lease_liability: 'Finance lease liabilities', purchase_commitments: 'Purchase commitments'};
const SOURCE = {mdna: '10-K MD&A', earnings_release: 'earnings release', transcript: 'call transcript', cfo_commentary: 'CFO commentary'};
const AI_CLASS = {explicit_amount: 'amount', explicit_share: 'share', qualitative: 'words only'};

function sources(v) {
  const wrap = h('div', {});
  if (v.decision) wrap.append(h('div', {class: 'src'}, h('div', {}, `${v.decision.reviewer} decided: ${v.decision.kind}`), h('div', {class: 'muted'}, v.decision.reason)));
  if (v.why) wrap.append(h('div', {class: 'src'}, h('div', {class: 'muted'}, 'The 10-K says: ', v.why.text.slice(0, 400)), h('a', {href: v.why.url, target: '_blank', rel: 'noopener'}, 'Open that passage')));
  for (const s of v.sources) {
    wrap.append(h('div', {class: 'src'},
      h('div', {}, `${LABEL[s.field] || s.field}: `, h('b', {}, s.cell), ` in row “${s.row}”, column “${s.col.replaceAll(' | ', ' ')}”`),
      h('div', {class: 'muted small'}, `10-K filed ${day(s.filed)}, table ${s.table_id}, ${s.unit || 'unit from the document'}, prompt ${s.prompt}`, s.notes ? `, ${s.notes}` : ''),
      h('div', {class: 'small' + (s.machine && !s.machine.match ? ' bad' : ' muted')}, s.machine ? (s.machine.match ? 'Confirmed on the rendered 10-K' : `Rendered 10-K shows ${s.machine.seen}`) : 'Not re-read'),
      s.machine?.img && h('img', {src: '/' + s.machine.img, alt: `Screenshot of the cited cell ${s.cell}`, loading: 'lazy'}),
      h('a', {href: s.deep, target: '_blank', rel: 'noopener', class: 'small'}, 'Open the 10-K at This Row')));
  }
  if (!v.sources.length) wrap.append(h('p', {class: 'muted'}, 'No citation.'));
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
const FIELDS = {capex: 'Capex', revenue: 'Revenue', opex: 'Opex', segment_capex: 'Segment capex', segment_revenue: 'Segment revenue', ppe_category: 'PP&E by category', finance_lease_liability: 'Finance lease liabilities', purchase_commitments: 'Purchase commitments'};
const KINDS = {spent: 'spent', committed: 'committed', derived: 'derived', planned: 'planned'};
const ALL_KINDS = Object.keys(KINDS);
const parseQ = (s) => Object.fromEntries(new URLSearchParams(s));
const CHECK = {agree: 'agrees with XBRL', definition_gap: 'definition gap, explained', unresolved: 'differs from XBRL', no_reference: 'no tagged counterpart', not_reported: 'not reported'};

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

const STAGE_LABEL_UI = {ingest: 'Ingest', values: 'Values', facts: 'Facts', statements: 'Statements', mapping: 'Mapping', planned: 'Planned', release: 'Release'};

const TABLES = [
  ['taxonomy', 'Taxonomy rows', 'one shape for spent, committed, derived, planned and company-stated AI; docs/TAXONOMY.md'],
  ['values', 'Values', 'the cash-flow and income lines read from each 10-K, with the check against XBRL'],
  ['facts', 'Facts', 'segments, PP&E by asset type, finance leases and purchase commitments'],
  ['statements', 'Statements', 'guidance and AI statements, quoted, with the source text'],
  ['projects', 'Projects', 'named projects, the latest mention of each'],
  ['companies', 'Companies', 'the tracked set with layer, role and the SEC’s SIC code'],
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
  root.querySelectorAll('button.btn:not(.btn-primary):not(.btn-outline-secondary):not(.btn-ghost-secondary):not(.btn-link)').forEach((el) => el.classList.add('btn-primary', 'btn-sm'));
  root.querySelectorAll('button:not(.btn):not(.btn-close):not(.badge)').forEach((el) => el.classList.add('btn', 'btn-link', 'btn-sm', 'p-0', 'align-baseline'));
  root.querySelectorAll('button.badge').forEach((el) => el.classList.add('bg-secondary-lt', 'border-0'));
  root.querySelectorAll('table:not(.table)').forEach((el) => el.classList.add('table', 'table-sm', 'table-vcenter'));
  root.querySelectorAll('section:not(.card):not(.figs):not(.hrow)').forEach((el) => { if (el.querySelector(':scope > .sechead, :scope > h2')) el.classList.add('card'); });
  root.querySelectorAll('section.card > h2:first-child').forEach((el) => { const head = h('div', {class: 'sechead'}); el.replaceWith(head); head.append(el); });
  root.querySelectorAll('section.card > .card').forEach((el) => { el.classList.remove('card'); el.classList.add('card-table-wrap'); });
}
