// ── Explore: charts you can change. A measure, an x, a series, a type; Plotly for hover, zoom and legend toggles. ──
const COLORS = ['#2f5bd3', '#d9822b', '#2a9d8f', '#c43d6b', '#7a5cc4', '#6b8e23', '#8c6d46', '#3d8fc4'];  // fixed order: a colour follows its entity (colorOf)
const EXM = {taxonomy: {label: 'All measures', value: (r) => r.value, alt: {change: (r) => r.change_from_prior}, x: 'fiscal_year'},  // schema v11: the derived change has its own column
  values: {label: 'Statement figures', value: (r) => r.value, fieldDefault: 'capex'},
  facts: {label: 'Note figures', value: (r) => r.value, fieldDefault: 'segment_capex'},
  statements: {label: 'Quoted statements', value: (r) => r.amount_mid, fieldDefault: 'capex'},
  projects: {label: 'Named projects', value: (r) => (r.amount_low != null && r.amount_high != null ? (r.amount_low + r.amount_high) / 2 : null)}};
const EX_AXES = {period: 'year', fiscal_year: 'fiscal year', ticker: 'company', layer: 'layer', field: 'field', measure: 'measure', category: 'category', standard_type: 'standard type', kind: 'kind', dimension: 'dimension', status: 'status', scope: 'scope', source: 'source', source_kind: 'source kind', period_kind: 'period kind', check: 'check'};
const EX_TYPES = {bars: 'bars', stacked: 'stacked bars', lines: 'lines', share: 'share of total'};
// V20: a series' colour is fixed by what it is, never by the order a browser first saw it: a company by its place in the
// scope (alphabetical), an industry by its place in INDUSTRY, any other value by its place among that column's values
const colorOf = (dim, name, values) => {
  if (name === 'Other') return '#9aa39d';
  const order = dim === 'ticker' ? [...SCOPE].sort() : dim === 'layer' ? Object.keys(INDUSTRY) : values;
  let i = order.indexOf(name);
  if (i < 0) { i = 0; for (const ch of String(name)) i = (i * 31 + ch.charCodeAt(0)) >>> 0; i = (dim === 'ticker' ? SCOPE.length : order.length) + i; }
  return COLORS[i % COLORS.length];
};
// the list request behind the chart, and its JSON / CSV export: every filter the controls hold (Measure, Category, Standard type on the taxonomy; Field, Kind, Layer, Tickers; From / To), server side
const listUrl = (st) => { const p = new URLSearchParams(); for (const k of ['field', 'kind', 'layer', 'ticker', 'from', 'to']) if (st[k]) p.set(k, st[k]); if (st.measure === 'taxonomy') for (const [k, q_] of [['tmeasure', 'measure'], ['category', 'category'], ['standard_type', 'standard_type']]) if (st[k]) p.set(q_, st[k]); return `/api/v1/${st.measure}?${p}`; };
// F-BF10: the one test of "year complete for the set": {year: {n, of, complete}}, n the companies with a row that year, of the companies with a row in any year of the chart
const yearCoverage = (rows, key) => { const all = new Set(), by = {}; for (const r of rows) { if (!r.ticker) continue; all.add(r.ticker); if (r[key] != null) (by[r[key]] = by[r[key]] || new Set()).add(r.ticker); } return Object.fromEntries(Object.entries(by).map(([y, s]) => [y, {n: s.size, of: all.size, complete: s.size === all.size}])); };
async function explorePage(view, arg, qs) {
  const {rows: saved} = await api('/api/v1/views');
  const q = parseQ(qs || '');
  let st = {measure: 'taxonomy', field: '', kind: '', layer: '', ticker: '', tmeasure: 'spent', category: 'capex', standard_type: '', from: '', to: '', x: 'fiscal_year', series: 'layer', type: 'stacked', value: ''};
  const current = arg ? saved.find((v) => v.id === arg) : null;
  if (current) st = {...st, measure: current.measure, field: current.filters.field || '', kind: current.filters.kind || '', layer: current.filters.layer || '', ticker: current.filters.ticker || '', tmeasure: current.filters.measure || '', category: current.filters.category || '', standard_type: current.filters.standard_type || '',
    ...(current.chart ? {x: current.chart.x, series: current.chart.series || '', type: current.chart.type, value: current.chart.value || ''} : {x: current.group || 'period', series: current.group ? '' : 'ticker', type: current.show === 'lines' ? 'lines' : 'bars'})};
  else if (Object.keys(q).length) st = {...st, ...q};
  if (st.field === '' && !current && !Object.keys(q).length) st.field = EXM[st.measure].fieldDefault || '';
  const list = h('div', {class: 'viewlist'}, saved.map((v) => h('a', {href: '#explore/' + v.id, class: 'viewrow' + (current && v.id === current.id ? ' on' : '')}, h('span', {}, v.name), h('span', {class: 'muted small'}, `${v.measure}${v.filters.category ? ' · ' + v.filters.category.replace(/_/g, ' ') : v.filters.measure ? ' · ' + v.filters.measure.replace('_', ' ') : ''}${v.chart ? `, ${v.chart.x.replace('_', ' ')} by ${v.chart.series || 'total'}` : ''}`))));
  const left = h('div', {}, h('div', {class: 'hrow'}, h('span', {class: 'muted small'}, `${saved.length} saved view${saved.length === 1 ? '' : 's'}`), h('a', {href: '#explore', class: 'small'}, 'New')), list);
  const body = h('div', {class: 'exbody'});
  view.append(h('div', {class: 'views'}, left, body));
  const fetchRows = async () => (await api(listUrl(st))).rows;  // the chart's rows and the JSON / CSV export are one request (F-BF7)
  let all = await api(`/api/v1/${st.measure}`), rows = all.rows;
  const distinct = (c) => [...new Set(rows.map((r) => r[c]).filter((v) => v != null && v !== ''))].sort();
  const setState = (patch) => { st = {...st, ...patch}; go('explore?' + new URLSearchParams(Object.fromEntries(Object.entries(st).filter(([, v]) => v))).toString()); };
  // V20: every control has its label on screen (above it); the chart's own choices share a line with the output (count,
  // JSON, CSV, Save as view) at its end. The blank option is "All"; the label says all of what.
  const sel = (label, key, opts, {blank} = {}) => h('label', {class: 'exf'}, h('span', {class: 'exl'}, label), h('select', {class: 'form-select form-select-sm', onchange: (e) => setState({[key]: e.target.value, ...(key === 'measure' ? {field: EXM[e.target.value].fieldDefault || '', kind: '', value: '', tmeasure: e.target.value === 'taxonomy' ? 'spent' : '', category: e.target.value === 'taxonomy' ? 'capex' : '', standard_type: '', x: EXM[e.target.value].x || 'period'} : {})})},
    blank ? h('option', {value: '', selected: !st[key] || null}, blank) : '', opts.map(([v, t]) => h('option', {value: v, selected: st[key] === v || null}, t))));
  const years = distinct(st.measure === 'taxonomy' ? 'fiscal_year' : 'period');
  const words = (x) => { const w = String(x).replaceAll('_', ' '); return w.charAt(0).toUpperCase() + w.slice(1); };
  // three whole lines, never a ragged wrap: what is counted, which companies and years, then the chart and its output (V20)
  const controls = h('div', {}, h('div', {class: 'exc'},
    sel('Data', 'measure', Object.entries(EXM).map(([k, m]) => [k, m.label])),
    st.measure === 'taxonomy' ? [sel('Measure', 'tmeasure', distinct('measure').map((m) => [m, words(m)]), {blank: 'All'}), sel('Category', 'category', distinct('category').map((c) => [c, words(c)]), {blank: 'All'}), sel('Asset type', 'standard_type', distinct('standard_type').map((c) => [c, memberLabel(c)]), {blank: 'All'})] : '',
    rows.some((r) => 'field' in r) ? sel('Field', 'field', distinct('field').map((f) => [f, LABEL[f] || words(f)]), {blank: 'All'}) : '',
    rows.some((r) => 'kind' in r) ? sel('Kind', 'kind', distinct('kind').map((k) => [k, words(k)]), {blank: 'All'}) : '',
    EXM[st.measure].alt ? sel('Value', 'value', Object.keys(EXM[st.measure].alt).map((k) => [k, k === 'change' ? 'Change from prior year' : words(k)]), {blank: 'As reported'}) : '',
  ), h('div', {class: 'exc'},
    sel('Industry', 'layer', distinct('layer').map((l) => [l, INDUSTRY[l] || l]), {blank: 'All'}),
    h('label', {class: 'exf'}, h('span', {class: 'exl'}, 'Tickers'), h('input', {type: 'text', class: 'form-control form-control-sm', name: 'tickers', value: st.ticker, placeholder: 'MSFT, GOOGL', spellcheck: 'false', autocapitalize: 'characters', autocomplete: 'off', style: 'width:8.5rem', onchange: (e) => setState({ticker: e.target.value.toUpperCase().replace(/\s/g, '')})})),
    years.length ? h('div', {class: 'exf exyears'}, sel('From', 'from', years.map((y) => [y, y]), {blank: 'First'}), sel('To', 'to', years.map((y) => [y, y]), {blank: 'Last'})) : ''));
  const chartControls = [
    sel('X axis', 'x', Object.entries(EX_AXES).filter(([a]) => rows.some((r) => r[a] != null)).map(([a, t]) => [a, words(t)])),
    sel('Series', 'series', Object.entries(EX_AXES).filter(([a]) => a !== st.x && rows.some((r) => r[a] != null)).map(([a, t]) => [a, words(t)]), {blank: 'One series'}),
    sel('Chart', 'type', Object.entries(EX_TYPES).map(([k, t]) => [k, words(t)]))];
  body.append(h('div', {class: 'sechead'}, h('h2', {}, current ? current.name : 'Explore'), current && current.note ? h('span', {class: 'muted small'}, current.note) : ''), controls);
  rows = await fetchRows();
  const m = EXM[st.measure];
  const val = st.value && m.alt && m.alt[st.value] ? m.alt[st.value] : m.value;
  const isShare = false;
  const pts = rows.filter((r) => val(r) != null && r[st.x] != null);
  const xs = [...new Set(pts.map((r) => String(r[st.x])))].sort((a, b) => (st.x === 'period' || st.x === 'fiscal_year' ? a.localeCompare(b) : 0));
  const sums = {};
  for (const r of pts) { const s = st.series ? String(r[st.series] ?? '—') : 'total'; sums[s] = (sums[s] || 0) + Math.abs(val(r)); }
  let seriesNames = Object.keys(sums).sort((a, b) => sums[b] - sums[a]);
  const folded = seriesNames.length > 8 ? new Set(seriesNames.slice(8)) : new Set();
  if (folded.size) seriesNames = [...seriesNames.slice(0, 8), 'Other'];
  const nameOf = (r) => { const s = st.series ? String(r[st.series] ?? '—') : 'total'; return folded.has(s) ? 'Other' : s; };
  if (st.x !== 'period' && st.x !== 'fiscal_year') xs.sort((a, b) => pts.filter((r) => String(r[st.x]) === b).reduce((s, r) => s + val(r), 0) - pts.filter((r) => String(r[st.x]) === a).reduce((s, r) => s + val(r), 0));
  const cell = {};
  for (const r of pts) { const k = `${nameOf(r)}|${r[st.x]}`; cell[k] = cell[k] || {sum: 0, rows: []}; cell[k].sum += val(r); cell[k].rows.push(r); }
  if (isShare) for (const c of Object.values(cell)) c.sum = c.sum / c.rows.length;
  const totals = Object.fromEntries(xs.map((x) => [x, seriesNames.reduce((s, n) => s + ((cell[`${n}|${x}`] || {}).sum || 0), 0)]));
  const big = Math.max(0, ...Object.values(cell).map((c) => Math.abs(c.sum))) >= 1e9;
  const unit = isShare ? 0.01 : big ? 1e9 : 1e6, suffix = isShare ? '%' : big ? 'B' : 'M';
  const fmtv = (v) => (v == null ? '—' : isShare ? pct(v) : usdIn(v, suffix));  // V16: the axis's unit governs the tooltip and the Data table
  const plot = h('div', {class: 'plot', role: 'figure', 'aria-label': `${m.label} by ${EX_AXES[st.x]}${st.series ? ' and ' + EX_AXES[st.series] : ''}`});
  const under = h('div', {});
  const url = listUrl(st);
  const delMsg = h('span', {class: 'small bad', role: 'status'});
  const saveRow = h('div', {class: 'exc exout'}, chartControls, h('span', {class: 'ms-auto muted small'}, `${int(pts.length)} row${pts.length === 1 ? '' : 's'}${folded.size ? `, ${folded.size} smaller series folded into Other` : ''}`),
    h('a', {href: url, target: '_blank', rel: 'noopener', class: 'small'}, 'JSON'), h('a', {href: url + '&format=csv', class: 'small'}, 'CSV'),
    h('button', {type: 'button', class: 'btn btn-primary btn-sm', onclick: () => saveView()}, current ? 'Save changes' : 'Save as view'),
    current ? h('button', {type: 'button', class: 'btn btn-link btn-sm p-0 align-baseline small', 'aria-live': 'polite', onclick: async (e) => { const b = e.currentTarget; if (b.dataset.armed) { delete b.dataset.armed; b.disabled = true; try { await api(`/api/v1/views/${current.id}/delete`, {method: 'POST', body: JSON.stringify({by: me})}); go('#explore'); } catch (err) { delMsg.textContent = err.message; b.disabled = false; b.textContent = 'Delete'; } } else { delMsg.textContent = ''; b.dataset.armed = '1'; b.textContent = 'Confirm delete'; setTimeout(() => { if (b.dataset.armed) { delete b.dataset.armed; b.textContent = 'Delete'; } }, 5000); } }}, 'Delete') : '', delMsg);
  body.append(saveRow, plot, under);
  if (!pts.length) { plot.replaceChildren(h('p', {class: 'msg'}, 'No rows match')); return; }
  const css = getComputedStyle(document.documentElement);
  const fg = css.getPropertyValue('--fg').trim(), muted = css.getPropertyValue('--muted').trim(), faint = css.getPropertyValue('--faint').trim(), bg = css.getPropertyValue('--bg').trim();
  // a year fewer companies have filed is drawn hatched and lighter and labelled with its count, never as a complete bar
  const cov = st.x === 'fiscal_year' || st.x === 'period' ? yearCoverage(pts, st.x) : {};
  const partial = (x) => !!cov[x] && !cov[x].complete;
  const xLabel = (x) => (partial(x) ? `${x} · ${cov[x].n} of ${cov[x].of} companies` : st.x === 'layer' ? INDUSTRY[x] || x : st.x === 'standard_type' ? memberLabel(x) : st.x === 'ticker' && NAMES[x] ? `${NAMES[x]} ${x}` : x);
  const disp = (n) => (st.series === 'layer' ? INDUSTRY[n] || n : st.series === 'standard_type' ? memberLabel(n) : st.series === 'ticker' && NAMES[n] ? `${NAMES[n]} ${n}` : n);
  const seriesAll = st.series ? [...new Set(all.rows.map((r) => String(r[st.series] ?? '—')))].sort() : [];  // every value the column holds, filters or not: a value keeps its colour
  const traces = seriesNames.map((n) => {
    const ys = xs.map((x) => { const c = cell[`${n}|${x}`]; if (!c) return null; return st.type === 'share' ? (totals[x] ? 100 * c.sum / totals[x] : null) : c.sum / unit; });
    const custom = xs.map((x) => { const c = cell[`${n}|${x}`]; const f = partial(x) ? `<br>${cov[x].n} of ${cov[x].of} companies` : ''; return c ? [fmtv(c.sum), plural(c.rows.length, 'row'), totals[x] && !isShare ? pct(c.sum / totals[x]) : '—', f] : ['—', '0 rows', '—', f]; });
    const base = {name: disp(n), x: xs, y: ys, customdata: custom, marker: {color: colorOf(st.series, n, seriesAll)}, line: {color: colorOf(st.series, n, seriesAll), width: 2}, hovertemplate: `<b>%{customdata[0]}</b> ${st.series ? disp(n) : ''}${st.series && seriesNames.length > 1 ? ', %{customdata[2]} of the ' + EX_AXES[st.x] : ''}<br>%{customdata[1]}%{customdata[3]}<extra></extra>`};
    const faded = xs.map((x) => (partial(x) ? 0.55 : 1));
    return st.type === 'lines' ? {...base, type: 'scatter', mode: 'lines+markers', marker: {color: colorOf(st.series, n, seriesAll), size: 7, opacity: faded, symbol: xs.map((x) => (partial(x) ? 'circle-open' : 'circle'))}, connectgaps: false}
      : {...base, type: 'bar', marker: {color: colorOf(st.series, n, seriesAll), opacity: faded, pattern: {shape: xs.map((x) => (partial(x) ? '/' : '')), fillmode: 'overlay', fgcolor: bg, solidity: 0.3}}};
  });
  const layout = {paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: {family: css.getPropertyValue('--font'), color: muted, size: 12}, margin: {l: 56, r: 16, t: 8, b: 40}, height: 400,
    barmode: st.type === 'bars' ? 'group' : 'stack', bargap: .25, bargroupgap: .06, hovermode: st.type === 'lines' ? 'x unified' : 'closest', showlegend: seriesNames.length > 1 || !!st.series,
    legend: {orientation: 'h', y: -0.14, font: {color: fg}, traceorder: st.type === 'lines' || st.type === 'bars' ? 'normal' : 'reversed'}, xaxis: {type: 'category', showgrid: false, linecolor: faint, tickfont: {color: muted}, categoryorder: 'array', categoryarray: xs, tickvals: xs, ticktext: xs.map((x) => xLabel(x).replace(' · ', '<br>')), automargin: true, tickangle: xs.some((x) => !partial(x) && xLabel(x).length > 12) ? -30 : 0},
    yaxis: {gridcolor: faint, zerolinecolor: faint, tickprefix: st.type === 'share' || isShare ? '' : '$', ticksuffix: st.type === 'share' ? '%' : suffix, tickformat: ',.0f', fixedrange: false, rangemode: 'tozero',
      title: {text: st.type === 'share' ? 'share of the total, %' : `${st.measure === 'taxonomy' ? (st.category || st.tmeasure || 'taxonomy rows').replace(/_/g, ' ') + (st.value === 'change' ? ', change from the prior year' : '') : EXM[st.measure].label}${st.field ? ', ' + (LABEL[st.field] || st.field) : ''}, $${suffix === 'B' ? 'billion' : 'million'}`, font: {color: muted, size: 11}}},
    hoverlabel: {bgcolor: bg, bordercolor: faint, font: {color: fg, family: css.getPropertyValue('--font')}}, dragmode: 'zoom'};
  await scopeReady;  // a company's colour is its place in the scope
  if (!await plotlyReady()) { plot.replaceChildren(h('p', {class: 'msg bad'}, 'Chart unavailable')); showRows(pts); return; }
  const gaps = xs.filter(partial);
  if (gaps.length) plot.before(h('p', {class: 'small text-orange m-0', id: 'partial-years'}, `Incomplete: ${gaps.map(xLabel).join(', ')}`));
  await Plotly.newPlot(plot, traces, layout, {displayModeBar: 'hover', displaylogo: false, responsive: true, modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d', 'toImage'], scrollZoom: false});
  // the plotted numbers, as a table a person can copy
  const numbers = h('details', {class: 'mt-2'}, h('summary', {class: 'muted small', style: 'cursor:pointer'}, 'Data'),
    h('div', {class: 'mt-2'}, table([{t: st.series ? EX_AXES[st.series] : 'series', sort: false, f: (n) => disp(n)}, ...xs.map((x) => ({t: xLabel(x), n: 1, sort: false, f: (n) => { const c = cell[`${n}|${x}`]; return c ? (st.type === 'share' && totals[x] ? pct(c.sum / totals[x]) : h('span', {title: usdExact(c.sum)}, fmtv(c.sum))) : '—'; }}))], seriesNames)));
  under.before(numbers);
  plot.on('plotly_click', (ev) => { const p = ev.points[0]; const n = seriesNames[p.curveNumber]; const c = cell[`${n}|${p.x}`]; if (c) showRows(c.rows, `${n === 'total' ? '' : disp(n) + ', '}${xLabel(p.x)}`); });
  showRows(null);
  function showRows(list, title) {
    if (!list) { under.replaceChildren(h('p', {class: 'muted small', style: 'margin-top:.6rem'}, h('button', {type: 'button', class: 'btn btn-link btn-sm p-0 align-baseline small', title: 'Click a bar or point for its rows · drag to zoom · double-click to reset', onclick: () => showRows(pts, 'Every row')}, 'Show rows'))); return; }
    const cols = [{t: 'Company', k: 'ticker', f: (r) => h('a', {href: `#proof/${r.ticker}`}, NAMES[r.ticker] || r.ticker)}, {t: 'Year', f: (r) => r.period || r.fiscal_year || '—'}];
    for (const c of ['measure', 'category', 'reported_name', 'standard_type', 'field', 'kind', 'project_kind', 'relation', 'dimension', 'status', 'check', 'check_method', 'source_kind', 'source']) if (list.some((r) => r[c] != null)) cols.push({t: c.replaceAll('_', ' '), k: c, f: (r) => r[c] ?? '—'});
    cols.push({t: 'Value', n: 1, f: (r) => (val(r) == null ? '—' : h('span', {title: usdExact(val(r))}, usdIn(val(r), 'M'))), s: (r) => val(r)});  // one unit for the column
    if (list.some((r) => r.basis || r.quote)) cols.push({t: 'Basis', sort: false, f: (r) => { const b = r.basis || r.quote || ''; return h('span', {class: 'small brk', title: b.length > 160 ? b : null}, b.length > 160 ? b.slice(0, 159).trimEnd() + '…' : b); }, wide: 1});  // V10: a cut ends in an ellipsis
    under.replaceChildren(h('div', {class: 'sechead', style: 'margin-top:1rem'}, h('h2', {}, title || 'Rows'), h('span', {class: 'muted small'}, `${int(list.length)} row${list.length === 1 ? '' : 's'}${list.length > 300 ? ' · first 300' : ''}`)), table(cols, list.slice(0, 300)));
  }
  function saveView() {
    const name = h('input', {type: 'text', name: 'view-name', autocomplete: 'off', value: current ? current.name : '', placeholder: 'e.g. Capex by industry, FY2022–FY2026'});
    const note = h('input', {type: 'text', name: 'view-note', autocomplete: 'off', value: current ? current.note || '' : '', placeholder: 'e.g. Spent, cash-flow line'});
    const msg = h('p', {class: 'msg small'});
    drawer(h('h3', {}, current ? 'Save changes' : 'Save as view'), h('div', {class: 'form'}, h('label', {}, 'Name', name), h('label', {}, 'Note', note)),
      h('div', {class: 'hrow', style: 'margin-top:1rem'}, h('button', {type: 'button', class: 'btn btn-primary btn-sm', onclick: async () => {
        const filters = Object.fromEntries(['field', 'kind', 'layer', 'ticker'].filter((k) => st[k]).map((k) => [k, st[k]]));
    if (st.measure === 'taxonomy') for (const [k, q_] of [['tmeasure', 'measure'], ['category', 'category'], ['standard_type', 'standard_type']]) if (st[k]) filters[q_] = st[k];
        try {
          const out = await api('/api/v1/views', {method: 'POST', body: JSON.stringify({view: {id: current ? current.id : undefined, name: name.value, measure: st.measure, filters, group: null, show: 'chart', chart: {x: st.x, series: st.series, type: st.type, value: st.value}, note: note.value}, by: me})});
          closeDrawer(); go('#explore/' + out.id); if (location.hash === '#explore/' + out.id) route();
        } catch (e) { msg.textContent = e.message; msg.classList.add('bad'); }
      }}, 'Save'), msg));
    name.focus();
  }
}
