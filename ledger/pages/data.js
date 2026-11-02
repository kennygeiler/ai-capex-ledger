// ── Dataset: Rows is the page (every list, every row); Grid is the company-by-year view of one field ──
const dataSwitch = (q, which) => h('div', {class: 'btn-group', role: 'group', 'aria-label': 'View'},
  h('a', {href: '#data' + (q.list || q.ticker || (q.t && !q.t.includes(',')) ? '?' + new URLSearchParams(Object.fromEntries(Object.entries({list: q.list, ticker: q.ticker || (q.t && !q.t.includes(',') ? q.t : '')}).filter(([, v]) => v))).toString() : ''), class: 'btn btn-sm' + (which === 'rows' ? ' active' : ''), 'aria-current': which === 'rows' ? 'page' : null}, 'Rows'),
  h('a', {href: '#data?' + new URLSearchParams(Object.fromEntries(Object.entries({view: 'grid', t: q.t || q.ticker, f: q.f, k: q.k}).filter(([, v]) => v))).toString(), class: 'btn btn-sm' + (which === 'grid' ? ' active' : ''), 'aria-current': which === 'grid' ? 'page' : null}, 'Grid'));
async function dataPage(view, qs) {
  const q = parseQ(qs || '');
  if (q.view !== 'grid') return rowsView(view, q);
  const [hqd, meta] = await Promise.all([hq(), api('/api/data?t=&f=')]);
  const all = Object.keys(meta.names).sort();
  const sel = {
    t: q.t ? q.t.split(',') : all.filter((t) => (!q.role || meta.roles[t] === q.role) && (!q.ind || meta.industries[t] === q.ind)),
    f: (q.f || 'capex').split(','), k: q.k ? q.k.split(',') : ALL_KINDS, y: q.y ? q.y.split(',') : null};
  const setQ = () => { const p = new URLSearchParams(); p.set('view', 'grid'); p.set('t', sel.t.join(',')); p.set('f', sel.f.join(',')); if (sel.y) p.set('y', sel.y.join(',')); if (sel.k.length < ALL_KINDS.length) p.set('k', sel.k.join(',')); location.hash = 'data?' + p.toString(); };

  // one line of controls: field, companies (a group or a custom list), kind, years hidden unless set
  const GROUPS = [['all', 'All companies'], ['buyer', 'Buyers'], ['seller', 'Sellers'], ...Object.keys(INDUSTRY).map((k) => ['ind:' + k, INDUSTRY[k]]), ['custom', 'Custom…']];
  const groupOf = () => { const set = new Set(sel.t); if (set.size === all.length) return 'all'; for (const r of ['buyer', 'seller']) if (all.filter((t) => meta.roles[t] === r).every((t) => set.has(t)) && [...set].every((t) => meta.roles[t] === r)) return r; for (const k of Object.keys(INDUSTRY)) if (all.filter((t) => meta.industries[t] === k).every((t) => set.has(t)) && [...set].every((t) => meta.industries[t] === k)) return 'ind:' + k; return 'custom'; };
  const groupSel = h('select', {'aria-label': 'Companies', onchange: (e) => { const v = e.target.value; if (v === 'custom') { openPicker(); return; } sel.t = all.filter((t) => v === 'all' || meta.roles[t] === v || (v.startsWith('ind:') && meta.industries[t] === v.slice(4))); setQ(); }},
    GROUPS.map(([k, v]) => h('option', {value: k, selected: groupOf() === k || null}, v)));
  const fieldSel = h('select', {'aria-label': 'Field', onchange: (e) => { sel.f = [e.target.value]; setQ(); }}, Object.entries(FIELDS).map(([k, v]) => h('option', {value: k, selected: sel.f[0] === k || null}, v)));
  const kindSel = h('select', {'aria-label': 'Kind', onchange: (e) => { sel.k = e.target.value === 'all' ? ALL_KINDS : [e.target.value]; setQ(); }},
    [['all', 'Every measure'], ['spent', 'Spent'], ['committed', 'Committed'], ['derived', 'Derived'], ['planned', 'Planned']].map(([k, v]) => h('option', {value: k, selected: (sel.k.length === ALL_KINDS.length ? 'all' : sel.k[0]) === k || null}, v)));
  function openPicker() {
    drawer(h('h3', {}, 'Companies'), h('div', {class: 'controls'}, Object.entries(groups).map(([ind, ts]) => h('div', {}, h('div', {class: 'muted small', style: 'margin-bottom:.2rem'}, INDUSTRY[ind] || ind),
      h('div', {class: 'picks'}, ts.map((t) => h('label', {}, h('input', {type: 'checkbox', checked: sel.t.includes(t) || null, onchange: (e) => { sel.t = e.target.checked ? [...sel.t, t] : sel.t.filter((x) => x !== t); }}), ' ', t)))))),
      h('div', {class: 'hrow', style: 'margin-top:1rem'}, h('button', {type: 'button', class: 'btn', onclick: () => { closeDrawer(); setQ(); }}, 'Apply')));
  }
  const groups = {};
  for (const t of all) (groups[meta.industries[t]] ||= []).push(t);

  // data for the selection
  const d = await api('/api/data?' + new URLSearchParams({t: sel.t.join(','), f: sel.f.join(','), k: sel.k.join(',')}).toString());
  const rows = q.check ? d.rows.filter((r) => q.check.split(',').includes(r.check) || (q.check.includes('flag') && r.flag)) : d.rows;
  const years = [...new Set(rows.map((r) => r.period))].sort().filter((y) => !sel.y || sel.y.includes(y));
  const changed = new Set((hqd.since?.changed || []).map((c) => c.key));
  const seriesKey = (r) => `${r.ticker}|${r.field}|${r.dimension}`;
  const series = new Map();
  for (const r of rows) { if (!years.includes(r.period)) continue; const k = seriesKey(r); if (!series.has(k)) series.set(k, {ticker: r.ticker, field: r.field, dimension: r.dimension, y: {}}); series.get(k).y[r.period] = r; }
  const list = [...series.values()].sort((a, b) => Math.max(0, ...Object.values(b.y).map((r) => r.value)) - Math.max(0, ...Object.values(a.y).map((r) => r.value)));
  const maxV = Math.max(1, ...rows.map((r) => r.value));

  // panel
  async function showProv(r) {
    const p = r.prov;
    const bits = [h('h3', {style: 'margin:0 0 .4rem'}, `${d.names[r.ticker]}, ${FIELDS[r.field] || r.field}${r.dimension ? ', ' + r.dimension : ''}, ${r.period}`),
      h('div', {class: 'figs', style: 'margin-bottom:1rem'}, fig('Value', usd(r.value), r.range ? `${usd(r.range[0])} – ${usd(r.range[1])}` : KINDS[r.kind]),
        fig('Verification', r.check ? CHECK[r.check] || r.check : '—', `${p.table} table`)),
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
    let k = 'u', why = 'Unverified · citation only';
    if (r.check === 'agree') { k = 't'; why = 'Verified · matches SEC XBRL'; }
    else if (r.check === 'unresolved') { k = 'd'; why = 'Differs from SEC XBRL'; }
    else if (r.check === 'definition_gap') { k = 'u'; why = 'Unverified · definition'; }
    const marks = [h('span', {class: 'mk ' + k, title: why, 'aria-label': why}, k === 'x' ? '✗' : k === 'd' ? '≠' : k === 'u' ? '○' : '✓')];
    if (r.status) marks.push(h('span', {class: 'badge bg-' + ({fix_pending: 'yellow', accepted: 'green', explained: 'azure', blocks: 'red'})[r.status] + '-lt ms-1', title: ({fix_pending: 'Fix pending', accepted: 'Accepted', explained: 'Explained', blocks: 'Blocks release'})[r.status] || r.status}, ({fix_pending: 'Fix', accepted: 'Accepted', explained: 'Explained', blocks: 'Blocks release'})[r.status] || r.status));
    return marks;
  }
  // grid
  const grid = h('div', {class: 'scroll'}, h('table', {class: 'heat'},
    h('thead', {}, h('tr', {}, h('th', {}, 'Company'), sel.f.length > 1 ? h('th', {}, 'Field') : '', list.some((s) => s.dimension) ? h('th', {}, 'Segment or category') : '', years.map((y) => h('th', {class: 'n'}, y.slice(2))))),
    h('tbody', {}, list.map((s) => h('tr', {}, h('td', {}, h('a', {href: `#data?view=grid&t=${s.ticker}&f=${sel.f.join(',')}`}, d.names[s.ticker]), ' ', h('span', {class: 'muted small'}, s.ticker)),
      sel.f.length > 1 ? h('td', {class: 'muted small'}, FIELDS[s.field] || s.field) : '', list.some((x) => x.dimension) ? h('td', {class: 'small'}, s.dimension || '') : '',
      years.map((y) => {
        const r = s.y[y];
        if (!r) return h('td', {class: 'n muted'}, '');
        const c = h('td', {class: 'n c', role: 'button'}, h('div', {}, usd(r.value), mark(r)));
        c.classList.add('cell'); c.tabIndex = 0;
        if (changed.has(`${r.ticker}|${r.field}|${r.period}`)) c.classList.add('moved');
        c.addEventListener('click', () => showProv(r));
        return c;
      }))))));


  function exportCsv() {
    const cols = ['ticker', 'company', 'field', 'dimension', 'period', 'kind', 'value', 'check', 'basis', 'source_url', 'provenance'];
    const esc = (v) => { const s = v == null ? '' : String(v); return /[",\n]/.test(s) ? '"' + s.replaceAll('"', '""') + '"' : s; };
    const out = rows.filter((r) => years.includes(r.period)).map((r) => [r.ticker, d.names[r.ticker], r.field, r.dimension, r.period, r.kind, r.value, r.check ?? '', r.basis, r.prov.url ?? '', r.prov.inputs || r.prov.extractions || r.prov.text || '']);
    const csv = [cols.join(','), ...out.map((x) => x.map(esc).join(','))].join('\n') + '\n';
    const a = h('a', {href: URL.createObjectURL(new Blob([csv], {type: 'text/csv'})), download: `capex-ledger-${sel.f.join('-')}.csv`});
    document.body.append(a); a.click(); a.remove();
  }

  view.append(h('div', {class: 'stack', style: 'gap:1rem'},
    h('div', {class: 'hrow'}, dataSwitch(q, 'grid'), fieldSel, groupSel, kindSel, h('button', {type: 'button', class: 'btn', onclick: exportCsv}, 'Export CSV'),
      h('span', {class: 'muted small'}, `${list.length} rows · USD · ✓ Verified · ○ Unverified · ≠ Differs from SEC XBRL`)),
    grid));
}

// ── Dataset, rows view: the raw rows of every list, as the read API and the release files carry them ──
async function rowsView(view, q) {
  const name = TABLES.some(([k]) => k === q.list) ? q.list : 'taxonomy';
  const ticker = (q.ticker || (q.t && !q.t.includes(',') ? q.t : '') || '').toUpperCase();
  const hasValue = name === 'taxonomy' && (q.has_value === 'true' || q.has_value === 'false') ? q.has_value : '';  // T15: the valueless rows under their own filter
  const setQ = (patch) => { const p = {list: name, ticker, has_value: hasValue, ...patch}; go('data?' + new URLSearchParams(Object.fromEntries(Object.entries(p).filter(([, v]) => v))).toString()); };
  const qs = new URLSearchParams(Object.fromEntries(Object.entries({ticker, has_value: hasValue}).filter(([, v]) => v))).toString();
  const d = await api(`/api/v1/${name}` + (qs ? `?${qs}` : ''));
  const cols = [...new Set(d.rows.flatMap((r) => Object.keys(r)))];
  const csv = `/api/v1/${name}.csv` + (qs ? `?${qs}` : '');

  const side = h('div', {class: 'list-group list-group-transparent mb-3'}, TABLES.map(([k, label, what]) =>
    h('a', {href: `#data?list=${k}` + (ticker ? `&ticker=${ticker}` : ''), class: 'list-group-item list-group-item-action d-block' + (k === name ? ' active' : '')}, h('div', {}, label), h('div', {class: 'text-secondary small brk'}, what))));
  const tickSel = h('select', {'aria-label': 'Company', onchange: (e) => setQ({ticker: e.target.value})},
    h('option', {value: ''}, 'Every company'), Object.entries(NAMES).map(([t, n]) => h('option', {value: t, selected: t === ticker || null}, `${n} ${t}`)));
  const search = h('input', {type: 'text', placeholder: 'Find in rows', 'aria-label': 'Find in rows', style: 'width:16rem'});
  const count = h('span', {class: 'text-secondary small'});
  const head = h('div', {class: 'page-header mb-3'}, h('div', {class: 'row align-items-center g-2'},
    h('div', {class: 'col'}, h('div', {class: 'hrow mb-2'}, dataSwitch({...q, list: name, ticker}, 'rows'), h('h2', {class: 'm-0'}, TABLES.find(([k]) => k === name)[1])), h('div', {class: 'text-secondary small'}, `${int(d.rows.length)} rows · USD`)),
    h('div', {class: 'col-auto'}, h('a', {href: csv, class: 'btn btn-outline-secondary btn-sm'}, 'CSV'), ' ', h('a', {href: `/api/v1/${name}` + (qs ? `?${qs}` : ''), target: '_blank', rel: 'noopener', class: 'btn btn-outline-secondary btn-sm'}, 'JSON'))));
  const valueSel = name === 'taxonomy' ? h('select', {'aria-label': 'Rows with a value', onchange: (e) => setQ({has_value: e.target.value})},
    [['', 'Every row'], ['true', 'With a value'], ['false', 'Without a value']].map(([v, t]) => h('option', {value: v, selected: v === hasValue || null}, t))) : '';
  const controls = h('div', {class: 'hrow mb-2', style: 'gap:.5rem;align-items:center'}, tickSel, valueSel, search, count);

  const fmt = (k, v) => v == null || v === '' ? h('span', {class: 'text-secondary'}, '—') : typeof v === 'boolean' ? (v ? 'yes' : 'no') : typeof v === 'number' ? (Number.isInteger(v) ? v.toLocaleString('en-US') : v.toLocaleString('en-US', {maximumFractionDigits: 4})) : k === 'ticker' ? h('a', {href: `#proof/${v}`}, v) : /^https?:/.test(String(v)) ? h('a', {href: v, target: '_blank', rel: 'noopener'}, 'open') : String(v).length > 90 ? h('span', {title: String(v)}, String(v).slice(0, 90) + '…') : String(v);
  const tcols = cols.map((k) => ({t: k, k, n: RAW_NUM.has(k) ? 1 : 0, f: (r) => fmt(k, r[k])}));
  const detail = (r) => h('dl', {class: 'row mb-0 small'}, cols.flatMap((k) => [h('dt', {class: 'col-2 font-monospace text-secondary'}, k), h('dd', {class: 'col-10 brk'}, r[k] == null || r[k] === '' ? '—' : String(r[k]))]));
  const holder = h('div', {});
  const draw = () => {
    const needle = search.value.trim().toLowerCase();
    const rows = needle ? d.rows.filter((r) => JSON.stringify(r).toLowerCase().includes(needle)) : d.rows;
    count.textContent = `${int(rows.length)} rows${rows.length !== d.rows.length ? ` of ${int(d.rows.length)}` : ''}`;
    const tbl = table(tcols, rows, {detail}); tbl.classList.add('raw');
    holder.replaceChildren(rows.length ? tbl : h('div', {class: 'card'}, h('div', {class: 'card-body text-secondary'}, 'No rows.')));
  };
  let t; search.addEventListener('input', () => { clearTimeout(t); t = setTimeout(draw, 150); });
  draw();
  view.append(head, h('div', {class: 'row g-3'}, h('div', {class: 'col-12 col-md-3 col-xl-2'}, side), h('div', {class: 'col-12 col-md-9 col-xl-10', style: 'min-width:0'}, controls, holder)));
}
