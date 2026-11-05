// ── Dataset: Rows is the page (every list, every row); Grid is the company-by-year view of one field ──
// report #13: one Verification filter on every list and on the Grid, bound to the `check` parameter, in one vocabulary:
// the display words of ledger/core/states.py (states.CHECK for a reconcile label; for the taxonomy's own check words, the
// row word of the same rung, states.LADDER_CHECK and ROW). Values sharing a word are one option ("agree,verbatim").
const VERDICT_ROW = {corroborated: 'corroborated', explained: 'info', differs: 'bad', verbatim: 'ok', to_confirm: 'wait', unmapped: 'bad', not_checked: 'unknown'};
const verdictWord = (v) => (v === 'flag' ? checkWord('unresolved') : stateKnown('check', v) ? checkWord(v) : VERDICT_ROW[v] ? stateWord('row', VERDICT_ROW[v])[1] : String(v));
const verdictOf = (r) => (r.check !== undefined ? r.check : r.check_label);
const verdictOptions = (values, current) => {
  const m = new Map();
  for (const v of [...new Set(values.filter((x) => x != null && x !== ''))].sort()) { const w = verdictWord(v); m.set(w, [...(m.get(w) || []), v]); }
  const opts = [...m].map(([w, vs]) => [vs.join(','), w]);
  return current && !opts.some(([v]) => v === current) ? [...opts, [current, [...new Set(current.split(',').map(verdictWord))].join(' or ')]] : opts;  // an address from elsewhere keeps its filter, named
};
const verdictKeep = (r, check) => !check || check.split(',').includes(String(verdictOf(r))) || (check.split(',').includes('flag') && !!r.flag);
const verdictSel = (value, values, onchange) => h('select', {'aria-label': 'Verification', class: value ? 'is-set' : null, onchange: (e) => onchange(e.target.value)},
  [['', 'Every verification'], ...verdictOptions(values, value)].map(([v, t]) => h('option', {value: v, selected: v === value || null}, t)));
// Rows ↔ Grid keep the company and the Verification filter (STORY-055: the switch dropped them)
const switchQ = (q, which) => (which === 'grid' ? {view: 'grid', list: q.list, t: q.t || q.ticker, f: q.f, k: q.k, check: q.check} : {list: q.list, ticker: q.ticker || (q.t && !q.t.includes(',') ? q.t : ''), check: q.check});
const qHash = (o) => { const p = new URLSearchParams(Object.fromEntries(Object.entries(o).filter(([, v]) => v))).toString(); return '#data' + (p ? '?' + p : ''); };
const dataSwitch = (q, which) => h('div', {class: 'btn-group seg', role: 'group', 'aria-label': 'View'},
  h('a', {href: qHash(switchQ(q, 'rows')), class: 'btn btn-sm btn-outline-secondary' + (which === 'rows' ? ' active' : ''), 'aria-current': which === 'rows' ? 'page' : null}, 'Rows'),
  h('a', {href: qHash(switchQ(q, 'grid')), class: 'btn btn-sm btn-outline-secondary' + (which === 'grid' ? ' active' : ''), 'aria-current': which === 'grid' ? 'page' : null}, 'Grid'));
// the Dataset's page head, Rows and Grid alike: the H1 on the page's left edge (F-VS2), the count under it; at the right the
// exports, CSV last, then the Rows/Grid switch at the edge, so both sit at the same place on both views
const dataHead = (title, sub, ...right) => h('div', {class: 'page-header mb-3'}, h('div', {class: 'row align-items-center g-2'},
  h('div', {class: 'col'}, h('h1', {class: 'page-title'}, title), h('div', {class: 'text-secondary small mt-1'}, sub)),
  h('div', {class: 'col-auto d-flex align-items-center gap-2'}, right)));
async function dataPage(view, qs) {
  const q = parseQ(qs || '');
  if (q.view !== 'grid') return rowsView(view, q);
  const [hqd, meta] = await Promise.all([hq(), api('/api/data?t=&f=')]);
  const all = Object.keys(meta.names).sort();
  const sel = {
    t: q.t ? q.t.split(',') : all.filter((t) => (!q.role || meta.roles[t] === q.role) && (!q.ind || meta.industries[t] === q.ind)),
    f: (q.f || 'capex').split(','), k: q.k ? q.k.split(',') : ALL_KINDS, y: q.y ? q.y.split(',') : null, c: q.check || ''};
  const setQ = () => { const p = new URLSearchParams(); p.set('view', 'grid'); p.set('t', sel.t.join(',')); p.set('f', sel.f.join(',')); if (sel.y) p.set('y', sel.y.join(',')); if (sel.k.length < ALL_KINDS.length) p.set('k', sel.k.join(',')); if (sel.c) p.set('check', sel.c); if (q.list) p.set('list', q.list); location.hash = 'data?' + p.toString(); };  // every control keeps the others, Verification included

  // one line of controls: field, companies (a group or a custom list), kind, years hidden unless set
  const GROUPS = [['all', 'All companies'], ['buyer', 'Buyers'], ['seller', 'Sellers'], ...Object.keys(INDUSTRY).map((k) => ['ind:' + k, INDUSTRY[k]]), ['custom', 'Custom…']];
  const groupOf = () => { const set = new Set(sel.t); if (set.size === all.length) return 'all'; for (const r of ['buyer', 'seller']) if (all.filter((t) => meta.roles[t] === r).every((t) => set.has(t)) && [...set].every((t) => meta.roles[t] === r)) return r; for (const k of Object.keys(INDUSTRY)) if (all.filter((t) => meta.industries[t] === k).every((t) => set.has(t)) && [...set].every((t) => meta.industries[t] === k)) return 'ind:' + k; return 'custom'; };
  // V19: the select reads Custom only once a custom list is applied: choosing Custom… opens the picker and the select keeps
  // the group in force until Apply; a group other than all companies, a kind other than every measure, reads as set
  const groupSel = h('select', {'aria-label': 'Companies', class: groupOf() === 'all' ? null : 'is-set', onchange: (e) => { const v = e.target.value; if (v === 'custom') { e.target.value = groupOf(); openPicker(); return; } sel.t = all.filter((t) => v === 'all' || meta.roles[t] === v || (v.startsWith('ind:') && meta.industries[t] === v.slice(4))); setQ(); }},
    GROUPS.map(([k, v]) => h('option', {value: k, selected: groupOf() === k || null}, v)));
  const fieldSel = h('select', {'aria-label': 'Field', onchange: (e) => { sel.f = [e.target.value]; setQ(); }}, Object.entries(FIELDS).map(([k, v]) => h('option', {value: k, selected: sel.f[0] === k || null}, v)));
  const kindSel = h('select', {'aria-label': 'Kind', class: sel.k.length === ALL_KINDS.length ? null : 'is-set', onchange: (e) => { sel.k = e.target.value === 'all' ? ALL_KINDS : [e.target.value]; setQ(); }},
    [['all', 'Every measure'], ['spent', 'Spent'], ['committed', 'Committed'], ['derived', 'Derived'], ['planned', 'Planned']].map(([k, v]) => h('option', {value: k, selected: (sel.k.length === ALL_KINDS.length ? 'all' : sel.k[0]) === k || null}, v)));
  function openPicker() {
    let pick = [...sel.t];  // the list being picked; the page's own list changes only on Apply
    const boxes = () => [...document.querySelectorAll('.drawer .picks input[type=checkbox]')];
    const every = (on) => { for (const b of boxes()) b.checked = on; pick = on ? [...all] : []; };
    drawer(h('h3', {}, 'Companies'), h('div', {class: 'hrow mb-2'}, h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary', onclick: () => every(true)}, 'All'), h('button', {type: 'button', class: 'btn btn-sm btn-outline-secondary', onclick: () => every(false)}, 'None')), h('div', {class: 'controls'}, Object.entries(groups).map(([ind, ts]) => h('div', {}, h('div', {class: 'muted small', style: 'margin-bottom:.2rem'}, INDUSTRY[ind] || ind),
      h('div', {class: 'picks'}, ts.map((t) => h('label', {}, h('input', {type: 'checkbox', checked: sel.t.includes(t) || null, onchange: (e) => { pick = e.target.checked ? [...pick, t] : pick.filter((x) => x !== t); }}), ' ', t)))))),
      h('div', {class: 'hrow', style: 'margin-top:1rem'}, h('button', {type: 'button', class: 'btn btn-primary btn-sm', onclick: () => { if (!pick.length) return; sel.t = pick; closeDrawer(); setQ(); }}, 'Apply')));
  }
  const groups = {};
  for (const t of all) (groups[meta.industries[t]] ||= []).push(t);

  // data for the selection
  const d = await api('/api/data?' + new URLSearchParams({t: sel.t.join(','), f: sel.f.join(','), k: sel.k.join(',')}).toString());
  const rows = d.rows.filter((r) => verdictKeep(r, sel.c));
  const checkSel = verdictSel(sel.c, d.rows.map(verdictOf), (v) => { sel.c = v; setQ(); });
  // the export is the server's (/api/data?format=csv): the same rows the grid shows, the filters in the address
  const csvHref = '/api/data?' + new URLSearchParams(Object.fromEntries(Object.entries({format: 'csv', t: sel.t.join(','), f: sel.f.join(','), k: sel.k.join(','), y: sel.y ? sel.y.join(',') : '', check: sel.c}).filter(([, v]) => v))).toString();
  const years = [...new Set(rows.map((r) => r.period))].sort().filter((y) => !sel.y || sel.y.includes(y));
  const changed = new Set((hqd.since?.changed || []).map((c) => c.key));
  const seriesKey = (r) => `${r.ticker}|${r.field}|${r.dimension}`;
  const series = new Map();
  for (const r of rows) { if (!years.includes(r.period)) continue; const k = seriesKey(r); if (!series.has(k)) series.set(k, {ticker: r.ticker, field: r.field, dimension: r.dimension, y: {}}); series.get(k).y[r.period] = r; }
  const list = [...series.values()].sort((a, b) => Math.max(0, ...Object.values(b.y).map((r) => r.value)) - Math.max(0, ...Object.values(a.y).map((r) => r.value)));
  const maxV = Math.max(1, ...rows.map((r) => r.value));
  const gridUnit = rows.some((r) => Math.abs(r.value) >= 1e6) ? 'M' : null;  // V16: one unit for the grid's cells; the exact dollars on hover and in the drawer

  // panel
  async function showProv(r) {
    const p = r.prov;
    const bits = [h('h3', {style: 'margin:0 0 .4rem'}, `${d.names[r.ticker]}, ${FIELDS[r.field] || r.field}${r.dimension ? ', ' + r.dimension : ''}, ${r.period}`),
      h('div', {class: 'figs', style: 'margin-bottom:1rem'}, fig('Value', usdExact(r.value), r.range ? `${usd(r.range[0])} – ${usd(r.range[1])}` : KINDS[r.kind]),
        fig('Verification', r.check ? checkWord(r.check) : '—', `${p.table} table`)),
      p.inputs ? h('p', {class: 'muted small mono', style: 'margin-bottom:.6rem'}, p.inputs) : '',
      p.xbrl != null ? h('p', {class: 'muted small'}, `SEC XBRL: ${usd(p.xbrl)}`) : '',
      p.url ? h('p', {class: 'small'}, h('a', {href: safeHref(p.url), target: '_blank', rel: 'noopener'}, 'Open in 10-K ↗')) : ''];
    const box = drawer(...bits);
    if (p.table === 'values') {  // the cell, the cleaning and the screenshot, from the company's own data
      const c = await api('/api/company?t=' + r.ticker);
      const v = c.values.find((x) => x.field === r.field && x.period === r.period);
      if (v) box.append(sources(v));
    }
  }

  // the auditor's mark: traced (agrees with its source), untraced (checked, no source to agree with), differs
  function mark(r) {
    // the label's word from states.CHECK; a label the server did not declare reads "Not checked", never a pass (F22)
    const why = checkWord(r.check) + (r.check === 'agree' ? ' · matches SEC XBRL' : '');
    const k = r.check === 'agree' ? 't' : r.check === 'unresolved' || r.check === 'not_extracted' ? 'd' : stateKnown('check', r.check) ? 'u' : 'x';
    const marks = [h('span', {class: 'mk ' + k, title: why, 'aria-label': why}, k === 'x' ? '✗' : k === 'd' ? '≠' : k === 'u' ? '○' : '✓')];
    if (r.status) marks.push(h('span', {class: 'badge bg-' + ({fix_pending: 'yellow', accepted: 'green', explained: 'azure', blocks: 'red'})[r.status] + '-lt ms-1', title: ({fix_pending: 'Fix pending', accepted: 'Accepted', explained: 'Explained', blocks: 'Blocks release'})[r.status] || r.status}, ({fix_pending: 'Fix', accepted: 'Accepted', explained: 'Explained', blocks: 'Blocks release'})[r.status] || r.status));
    return marks;
  }
  // grid
  const grid = h('div', {class: 'scroll'}, h('table', {class: 'heat'},
    h('thead', {}, h('tr', {}, h('th', {}, 'Company'), sel.f.length > 1 ? h('th', {}, 'Field') : '', list.some((s) => s.dimension) ? h('th', {}, 'Segment or category') : '', years.map((y) => h('th', {class: 'n'}, y)))),  // V21: "FY2022", as Rows and Explore say it
    h('tbody', {}, list.map((s) => h('tr', {}, h('td', {}, h('a', {href: `#data?view=grid&t=${s.ticker}&f=${sel.f.join(',')}`}, d.names[s.ticker]), ' ', h('span', {class: 'muted small'}, s.ticker)),
      sel.f.length > 1 ? h('td', {class: 'muted small'}, FIELDS[s.field] || s.field) : '', list.some((x) => x.dimension) ? h('td', {class: 'small'}, s.dimension || '') : '',
      years.map((y) => {
        const r = s.y[y];
        if (!r) return h('td', {class: 'n muted'}, '');
        const c = h('td', {class: 'n c', role: 'button', title: usdExact(r.value)}, h('div', {}, usdIn(r.value, gridUnit), mark(r)));
        c.classList.add('cell'); c.tabIndex = 0;
        if (changed.has(`${r.ticker}|${r.field}|${r.period}`)) c.classList.add('moved');
        c.addEventListener('click', () => showProv(r));
        return c;
      }))))));


  // V9: no rows for the filters is said, with the filters by name, and there is nothing to export
  const sel_ = (el) => el.options[el.selectedIndex].text;
  const none = h('div', {class: 'card'}, h('div', {class: 'card-body text-secondary'}, `No rows for ${[['Field', sel_(fieldSel)], ['Companies', sel_(groupSel)], ['Kind', sel_(kindSel)], ['Verification', sel_(checkSel)]].map(([k, v]) => `${k} = ${v}`).join(' · ')}`));
  // V21: the same head as Rows: the title on the page's left edge, the count under it; the Rows/Grid switch and the CSV at the
  // right, in the same place on both views; the controls on the line under the head
  view.append(dataHead(`Grid · ${FIELDS[sel.f[0]] || sel.f[0]}`, `${int(list.length)} rows · USD`, list.length ? h('a', {href: csvHref, class: 'btn btn-outline-secondary btn-sm'}, 'CSV') : h('button', {type: 'button', class: 'btn btn-outline-secondary btn-sm', disabled: true}, 'CSV'), dataSwitch({...q, check: sel.c}, 'grid')),
    h('div', {class: 'stack', style: 'gap:1rem'},
      h('div', {class: 'hrow'}, fieldSel, groupSel, kindSel, checkSel, h('span', {class: 'muted small'}, '✓ Verified · ○ Unverified · ≠ Differs from SEC XBRL')),
      list.length ? h('div', {class: 'card grid-card'}, grid) : none));
}

// ── Dataset, rows view: the raw rows of every list, as the read API and the release files carry them ──
async function rowsView(view, q) {
  const name = TABLES.some(([k]) => k === q.list) ? q.list : 'taxonomy';
  const ticker = (q.ticker || (q.t && !q.t.includes(',') ? q.t : '') || '').toUpperCase();
  const hasValue = name === 'taxonomy' && (q.has_value === 'true' || q.has_value === 'false') ? q.has_value : '';  // T15: the valueless rows under their own filter
  const check = q.check || '';
  const setQ = (patch) => { const p = {list: name, ticker, has_value: hasValue, check, ...patch}; go('data?' + new URLSearchParams(Object.fromEntries(Object.entries(p).filter(([, v]) => v))).toString()); };
  const qs = new URLSearchParams(Object.fromEntries(Object.entries({ticker, has_value: hasValue}).filter(([, v]) => v))).toString();
  const d = await api(`/api/v1/${name}` + (qs ? `?${qs}` : ''));
  // V9: a column empty in every row the table holds (the list, or what Find kept) is left out; every page of the pager has the
  // same columns, and the key stays in the opened row, CSV and JSON
  const keys = [...new Set(d.rows.flatMap((r) => Object.keys(r)))];
  const filled = (rows) => keys.filter((k) => rows.some((r) => r[k] != null && r[k] !== ''));
  const hasVerdict = d.rows.some((r) => 'check' in r || 'check_label' in r);
  const listRows = check && hasVerdict ? d.rows.filter((r) => verdictKeep(r, check)) : d.rows;  // the server's `check` filter, applied the same way (api.column)
  const csvQ = new URLSearchParams(Object.fromEntries(Object.entries({ticker, has_value: hasValue, check: hasVerdict ? check : ''}).filter(([, v]) => v))).toString();
  const csv = `/api/v1/${name}.csv` + (csvQ ? `?${csvQ}` : '');

  const side = h('div', {class: 'list-group list-group-transparent sidelist mb-3'}, TABLES.map(([k, label, what]) =>
    h('a', {href: qHash({list: k, ticker, check}), class: 'list-group-item list-group-item-action d-block' + (k === name ? ' active' : ''), 'aria-current': k === name ? 'page' : null, title: what}, h('div', {}, label), h('div', {class: 'text-secondary small cut'}, what))));
  const tickSel = h('select', {'aria-label': 'Company', class: ticker ? 'is-set' : null, onchange: (e) => setQ({ticker: e.target.value})},
    h('option', {value: ''}, 'Every company'), Object.entries(NAMES).map(([t, n]) => h('option', {value: t, selected: t === ticker || null}, `${n} ${t}`)));
  const search = h('input', {type: 'text', placeholder: 'Find in rows', 'aria-label': 'Find in rows', style: 'width:16rem'});
  const count = h('span', {'aria-live': 'polite'});  // V18: the one row count, under the list's name; it follows Find ("129 rows of 617")
  const head = dataHead(TABLES.find(([k]) => k === name)[1], [count, ' · USD'], h('a', {href: csv, class: 'btn btn-outline-secondary btn-sm'}, 'CSV'), dataSwitch({...q, list: name, ticker, check}, 'rows'));  // one export: the CSV of the rows the filters keep (the JSON is the same address without .csv, docs/API.md)
  const valueSel = name === 'taxonomy' ? h('select', {'aria-label': 'Rows with a value', class: hasValue ? 'is-set' : null, onchange: (e) => setQ({has_value: e.target.value})},
    [['', 'Every row'], ['true', 'With a value'], ['false', 'Without a value']].map(([v, t]) => h('option', {value: v, selected: v === hasValue || null}, t))) : '';
  const checkSel = hasVerdict ? verdictSel(check, d.rows.map(verdictOf), (v) => setQ({check: v})) : '';
  const controls = h('div', {class: 'hrow mb-2', style: 'gap:.5rem;align-items:center'}, tickSel, valueSel, checkSel, search);

  const fmt = (k, v, r = {}) => v == null || v === '' ? h('span', {class: 'text-secondary'}, '—') : typeof v === 'boolean' ? (v ? 'yes' : 'no') : typeof v === 'number' && MONEY_KEYS.has(k) && (!r.unit || /^usd$/i.test(r.unit)) ? usdExact(v) : typeof v === 'number' ? (Number.isInteger(v) ? v.toLocaleString('en-US') : v.toLocaleString('en-US', {maximumFractionDigits: 4})) : k === 'ticker' ? h('a', {href: `#proof/${v}`}, v) : /^https?:/.test(String(v)) ? h('a', {href: v, target: '_blank', rel: 'noopener'}, 'open') : String(v).length > 90 ? h('span', {title: String(v)}, String(v).slice(0, 90) + '…') : String(v);
  const tcol = (k) => ({t: colName(k), k, n: RAW_NUM.has(k) ? 1 : 0, f: (r) => fmt(k, r[k], r)});
  // V10: an opened row lists its fields in the visible part of the box (the wrapper's width, never the 40-column table's)
  const detail = (r) => h('div', {class: 'datagrid row-detail small'}, keys.map((k) => h('div', {class: 'datagrid-item'}, h('div', {class: 'datagrid-title', title: k}, colName(k)), h('div', {class: 'datagrid-content brk'}, r[k] == null || r[k] === '' ? '—' : String(r[k])))));
  const holder = h('div', {});
  const draw = () => {
    const needle = search.value.trim().toLowerCase();
    const rows = needle ? listRows.filter((r) => JSON.stringify(r).toLowerCase().includes(needle)) : listRows;
    count.textContent = `${int(rows.length)} rows${rows.length !== d.rows.length ? ` of ${int(d.rows.length)}` : ''}`;
    const tbl = table(filled(rows).map(tcol), rows, {detail, page: PAGE_ROWS}); tbl.classList.add('raw');
    holder.replaceChildren(rows.length ? tbl : h('div', {class: 'card'}, h('div', {class: 'card-body text-secondary'}, 'No rows.')));
    fitTables(holder);
  };
  let t; search.addEventListener('input', () => { clearTimeout(t); t = setTimeout(draw, 150); });
  draw();
  view.append(head, h('div', {class: 'row g-3'}, h('div', {class: 'col-12 col-md-3 col-xl-2'}, side), h('div', {class: 'col-12 col-md-9 col-xl-10', style: 'min-width:0'}, controls, holder)));
}
