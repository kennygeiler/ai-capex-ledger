// ── Explore: charts you can change. A measure, an x, a series, a type; Plotly for hover, zoom and legend toggles. ──
const COLORS = ['#2f5bd3', '#d9822b', '#2a9d8f', '#c43d6b', '#7a5cc4', '#6b8e23', '#8c6d46', '#3d8fc4'];  // fixed order: a colour follows its entity
const EXM = {taxonomy: {label: 'Taxonomy rows (spent, committed, derived, planned, company-stated AI)', value: (r) => r.value, alt: {change: (r) => r.value_high}, x: 'fiscal_year'},
  values: {label: 'Values from the statements', value: (r) => r.value, fieldDefault: 'capex'},
  facts: {label: 'Facts from the notes', value: (r) => r.value, fieldDefault: 'segment_capex'},
  statements: {label: 'What companies said', value: (r) => r.amount_mid, fieldDefault: 'capex'},
  projects: {label: 'Named projects', value: (r) => (r.amount_low != null && r.amount_high != null ? (r.amount_low + r.amount_high) / 2 : null)}};
const EX_AXES = {period: 'year', fiscal_year: 'fiscal year', ticker: 'company', layer: 'layer', group: 'group', field: 'field', measure: 'measure', category: 'category', standard_type: 'standard type', kind: 'kind', dimension: 'dimension', status: 'status', scope: 'scope', source: 'source'};
const EX_TYPES = {bars: 'bars', stacked: 'stacked bars', lines: 'lines', share: 'share of total'};
const colorReg = (() => { let m = {}; try { m = JSON.parse(localStorage.getItem('datahq-colors') || '{}'); } catch {} return (name) => { if (name === 'Other') return '#9aa39d'; if (m[name] == null) { m[name] = Object.keys(m).length; try { localStorage.setItem('datahq-colors', JSON.stringify(m)); } catch {} } return COLORS[m[name] % COLORS.length]; }; })();
async function explorePage(view, arg, qs) {
  const {rows: saved} = await api('/api/v1/views');
  const q = parseQ(qs || '');
  let st = {measure: 'taxonomy', field: '', kind: '', layer: '', ticker: '', tmeasure: 'spent', category: 'capex', standard_type: '', from: '', to: '', x: 'fiscal_year', series: 'group', type: 'stacked', value: ''};
  const current = arg ? saved.find((v) => v.id === arg) : null;
  if (current) st = {...st, measure: current.measure, field: current.filters.field || '', kind: current.filters.kind || '', layer: current.filters.layer || '', ticker: current.filters.ticker || '', tmeasure: current.filters.measure || '', category: current.filters.category || '', standard_type: current.filters.standard_type || '',
    ...(current.chart ? {x: current.chart.x, series: current.chart.series || '', type: current.chart.type, value: current.chart.value || ''} : {x: current.group || 'period', series: current.group ? '' : 'ticker', type: current.show === 'lines' ? 'lines' : 'bars'})};
  else if (Object.keys(q).length) st = {...st, ...q};
  if (st.field === '' && !current && !Object.keys(q).length) st.field = EXM[st.measure].fieldDefault || '';
  const list = h('div', {class: 'viewlist'}, saved.map((v) => h('a', {href: '#explore/' + v.id, class: 'viewrow' + (current && v.id === current.id ? ' on' : '')}, h('span', {}, v.name), h('span', {class: 'muted small'}, `${v.measure}${v.filters.category ? ' · ' + v.filters.category.replace(/_/g, ' ') : v.filters.measure ? ' · ' + v.filters.measure.replace('_', ' ') : ''}${v.chart ? `, ${v.chart.x.replace('_', ' ')} by ${v.chart.series || 'total'}` : ''}`))));
  const left = h('div', {}, h('div', {class: 'hrow'}, h('span', {class: 'muted small'}, `${saved.length} saved view${saved.length === 1 ? '' : 's'}`), h('a', {href: '#explore', class: 'small'}, 'New')), list);
  const body = h('div', {class: 'exbody'});
  view.append(h('div', {class: 'views'}, left, body));
  const fetchRows = async () => {
    const p = new URLSearchParams();
    for (const k of ['field', 'kind', 'layer', 'ticker']) if (st[k]) p.set(k, st[k]);
    for (const [k, q_] of [['tmeasure', 'measure'], ['category', 'category'], ['standard_type', 'standard_type']]) if (st.measure === 'taxonomy' && st[k]) p.set(q_, st[k]);
    const d = await api(`/api/v1/${st.measure}?${p}`);
    return d.rows.filter((r) => (!st.from || !(r.period || r.fiscal_year) || (r.period || r.fiscal_year) >= st.from) && (!st.to || !(r.period || r.fiscal_year) || (r.period || r.fiscal_year) <= st.to));
  };
  let all = await api(`/api/v1/${st.measure}`), rows = all.rows;
  const distinct = (c) => [...new Set(rows.map((r) => r[c]).filter((v) => v != null && v !== ''))].sort();
  const setState = (patch) => { st = {...st, ...patch}; go('explore?' + new URLSearchParams(Object.fromEntries(Object.entries(st).filter(([, v]) => v))).toString()); };
  const sel = (label, key, opts, {blank} = {}) => h('select', {'aria-label': label, onchange: (e) => setState({[key]: e.target.value, ...(key === 'measure' ? {field: EXM[e.target.value].fieldDefault || '', kind: '', value: '', tmeasure: e.target.value === 'taxonomy' ? 'spent' : '', category: e.target.value === 'taxonomy' ? 'capex' : '', standard_type: '', x: EXM[e.target.value].x || 'period'} : {})})},
    blank ? h('option', {value: '', selected: !st[key] || null}, blank) : '', opts.map(([v, t]) => h('option', {value: v, selected: st[key] === v || null}, t)));
  const years = distinct(st.measure === 'taxonomy' ? 'fiscal_year' : 'period');
  const controls = h('div', {class: 'hrow exc'},
    sel('Measure', 'measure', Object.entries(EXM).map(([k, m]) => [k, m.label])),
    st.measure === 'taxonomy' ? [sel('Measure', 'tmeasure', distinct('measure').map((m) => [m, m.replace('_', ' ')]), {blank: 'every measure'}), sel('Category', 'category', distinct('category').map((c) => [c, c.replace(/_/g, ' ')]), {blank: 'every category'}), sel('Standard type', 'standard_type', distinct('standard_type').map((c) => [c, c.replace('Member', '')]), {blank: 'every asset type'})] : '',
    rows.some((r) => 'field' in r) ? sel('Field', 'field', distinct('field').map((f) => [f, LABEL[f] || f]), {blank: 'every field'}) : '',
    rows.some((r) => 'kind' in r) ? sel('Kind', 'kind', distinct('kind').map((k) => [k, k]), {blank: 'every kind'}) : '',
    EXM[st.measure].alt ? sel('Value', 'value', Object.keys(EXM[st.measure].alt).map((k) => [k, k === 'change' ? 'change from the prior year' : k]), {blank: 'the value as reported'}) : '',
    sel('Layer', 'layer', distinct('layer').map((l) => [l, INDUSTRY[l] || l]), {blank: 'every layer'}),
    h('input', {type: 'text', name: 'tickers', value: st.ticker, placeholder: 'e.g. MSFT, GOOGL', 'aria-label': 'Tickers, comma-separated', spellcheck: 'false', autocapitalize: 'characters', autocomplete: 'off', style: 'width:12rem', onchange: (e) => setState({ticker: e.target.value.toUpperCase().replace(/\s/g, '')})}),
    years.length ? [sel('From', 'from', years.map((y) => [y, y]), {blank: 'from'}), sel('To', 'to', years.map((y) => [y, y]), {blank: 'to'})] : '',
    h('span', {class: 'muted small'}, 'then'),
    sel('X axis', 'x', Object.entries(EX_AXES).filter(([a]) => rows.some((r) => r[a] != null)).map(([a, t]) => [a, `x: ${t}`])),
    sel('Series', 'series', Object.entries(EX_AXES).filter(([a]) => a !== st.x && rows.some((r) => r[a] != null)).map(([a, t]) => [a, `series: ${t}`]), {blank: 'one series'}),
    sel('Chart type', 'type', Object.entries(EX_TYPES)));
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
  const fmtv = (v) => (v == null ? '—' : isShare ? pct(v) : usd(v));
  const plot = h('div', {class: 'plot', role: 'figure', 'aria-label': `${m.label} by ${EX_AXES[st.x]}${st.series ? ' and ' + EX_AXES[st.series] : ''}`});
  const under = h('div', {});
  const q2 = new URLSearchParams(); for (const k of ['field', 'kind', 'layer', 'ticker']) if (st[k]) q2.set(k, st[k]);
  const url = `/api/v1/${st.measure}?${q2}`;
  const saveRow = h('div', {class: 'hrow', style: 'gap:1rem'}, h('span', {class: 'muted small'}, `${int(pts.length)} row${pts.length === 1 ? '' : 's'}${folded.size ? `, ${folded.size} smaller series folded into Other` : ''}`),
    h('a', {href: url, target: '_blank', rel: 'noopener', class: 'small'}, 'JSON'), h('a', {href: url + '&format=csv', class: 'small'}, 'CSV'),
    h('button', {type: 'button', class: 'btn', onclick: () => saveView()}, current ? 'Save changes' : 'Save as view'),
    current ? h('button', {type: 'button', class: 'small', 'aria-live': 'polite', onclick: async (e) => { const b = e.currentTarget; if (b.dataset.armed) { await api(`/api/v1/views/${current.id}/delete`, {method: 'POST', body: JSON.stringify({by: me})}); go('#explore'); } else { b.dataset.armed = '1'; b.textContent = 'Click again to delete this view'; setTimeout(() => { delete b.dataset.armed; b.textContent = 'Delete'; }, 5000); } }}, 'Delete') : '');
  body.append(saveRow, plot, under);
  if (!pts.length) { plot.replaceChildren(h('p', {class: 'msg'}, 'No rows match. Widen the filters, or run the step that fills this list.')); return; }
  const css = getComputedStyle(document.documentElement);
  const fg = css.getPropertyValue('--fg').trim(), muted = css.getPropertyValue('--muted').trim(), faint = css.getPropertyValue('--faint').trim(), bg = css.getPropertyValue('--bg').trim();
  const xLabel = (x) => (st.x === 'layer' || st.x === 'group' ? INDUSTRY[x] || x : st.x === 'standard_type' ? x.replace('Member', '') : st.x === 'ticker' && NAMES[x] ? `${NAMES[x]} ${x}` : x);
  const disp = (n) => (st.series === 'layer' || st.series === 'group' ? INDUSTRY[n] || n : st.series === 'standard_type' ? n.replace('Member', '') : st.series === 'ticker' && NAMES[n] ? `${NAMES[n]} ${n}` : n);
  const traces = seriesNames.map((n) => {
    const ys = xs.map((x) => { const c = cell[`${n}|${x}`]; if (!c) return null; return st.type === 'share' ? (totals[x] ? 100 * c.sum / totals[x] : null) : c.sum / unit; });
    const custom = xs.map((x) => { const c = cell[`${n}|${x}`]; return c ? [fmtv(c.sum), c.rows.length, totals[x] && !isShare ? pct(c.sum / totals[x]) : '—'] : ['—', 0, '—']; });
    const base = {name: disp(n), x: xs, y: ys, customdata: custom, marker: {color: colorReg(n)}, line: {color: colorReg(n), width: 2}, hovertemplate: `<b>%{customdata[0]}</b> ${st.series ? disp(n) : ''}${st.series && seriesNames.length > 1 ? ', %{customdata[2]} of the ' + EX_AXES[st.x] : ''}<br>%{customdata[1]} row(s)<extra></extra>`};
    return st.type === 'lines' ? {...base, type: 'scatter', mode: 'lines+markers', marker: {color: colorReg(n), size: 7}, connectgaps: false} : {...base, type: 'bar'};
  });
  const layout = {paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: {family: css.getPropertyValue('--font'), color: muted, size: 12}, margin: {l: 56, r: 16, t: 8, b: 40}, height: 400,
    barmode: st.type === 'bars' ? 'group' : 'stack', bargap: .25, bargroupgap: .06, hovermode: st.type === 'lines' ? 'x unified' : 'closest', showlegend: seriesNames.length > 1 || !!st.series,
    legend: {orientation: 'h', y: -0.14, font: {color: fg}, traceorder: st.type === 'lines' || st.type === 'bars' ? 'normal' : 'reversed'}, xaxis: {type: 'category', showgrid: false, linecolor: faint, tickfont: {color: muted}, categoryorder: 'array', categoryarray: xs, tickvals: xs, ticktext: xs.map(xLabel), automargin: true, tickangle: xs.some((x) => xLabel(x).length > 12) ? -30 : 0},
    yaxis: {gridcolor: faint, zerolinecolor: faint, tickprefix: st.type === 'share' || isShare ? '' : '$', ticksuffix: st.type === 'share' ? '%' : suffix, tickformat: ',.0f', fixedrange: false, rangemode: 'tozero',
      title: {text: st.type === 'share' ? 'share of the total, %' : `${st.measure === 'taxonomy' ? (st.category || st.tmeasure || 'taxonomy rows').replace(/_/g, ' ') + (st.value === 'change' ? ', change from the prior year' : '') : EXM[st.measure].label}${st.field ? ', ' + (LABEL[st.field] || st.field) : ''}, $${suffix === 'B' ? 'billion' : 'million'}`, font: {color: muted, size: 11}}},
    hoverlabel: {bgcolor: bg, bordercolor: faint, font: {color: fg, family: css.getPropertyValue('--font')}}, dragmode: 'zoom'};
  if (!window.Plotly) { plot.replaceChildren(h('p', {class: 'msg bad'}, 'The chart library did not load (offline?). The rows are below.')); showRows(pts); return; }
  await Plotly.newPlot(plot, traces, layout, {displayModeBar: 'hover', displaylogo: false, responsive: true, modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d', 'toImage'], scrollZoom: false});
  // the plotted numbers, as a table a person can copy
  const numbers = h('details', {class: 'mt-2'}, h('summary', {class: 'muted small', style: 'cursor:pointer'}, 'The numbers in the chart'),
    h('div', {class: 'mt-2'}, table([{t: st.series ? EX_AXES[st.series] : 'series', sort: false, f: (n) => disp(n)}, ...xs.map((x) => ({t: xLabel(x), n: 1, sort: false, f: (n) => { const c = cell[`${n}|${x}`]; return c ? (st.type === 'share' && totals[x] ? pct(c.sum / totals[x]) : fmtv(c.sum)) : '—'; }}))], seriesNames)));
  under.before(numbers);
  plot.on('plotly_click', (ev) => { const p = ev.points[0]; const n = seriesNames[p.curveNumber]; const c = cell[`${n}|${p.x}`]; if (c) showRows(c.rows, `${n === 'total' ? '' : disp(n) + ', '}${xLabel(p.x)}`); });
  showRows(null);
  function showRows(list, title) {
    if (!list) { under.replaceChildren(h('p', {class: 'muted small', style: 'margin-top:.6rem'}, 'Click a bar or point for the rows behind it, or ', h('button', {type: 'button', class: 'small', onclick: () => showRows(pts, 'Every row')}, 'show every row'), '. Drag to zoom, double-click to reset, click a legend entry to hide a series.')); return; }
    const cols = [{t: 'Company', k: 'ticker', f: (r) => h('a', {href: `#proof/${r.ticker}`}, NAMES[r.ticker] || r.ticker)}, {t: 'Year', f: (r) => r.period || r.fiscal_year || '—'}];
    for (const c of ['measure', 'category', 'reported_name', 'standard_type', 'field', 'kind', 'dimension', 'status', 'check', 'source']) if (list.some((r) => r[c] != null)) cols.push({t: c.replace('_', ' '), k: c, f: (r) => r[c] ?? '—'});
    cols.push({t: 'Value', n: 1, f: (r) => fmtv(val(r)), s: (r) => val(r)});
    if (list.some((r) => r.basis || r.quote)) cols.push({t: 'Basis', sort: false, f: (r) => h('span', {class: 'small brk'}, (r.basis || r.quote || '').slice(0, 160)), wide: 1});
    under.replaceChildren(h('div', {class: 'sechead', style: 'margin-top:1rem'}, h('h2', {}, title || 'Rows'), h('span', {class: 'muted small'}, `${int(list.length)} row${list.length === 1 ? '' : 's'}${list.length > 300 ? ', first 300 shown; the CSV has them all' : ''}`)), table(cols, list.slice(0, 300)));
  }
  function saveView() {
    const name = h('input', {type: 'text', name: 'view-name', autocomplete: 'off', value: current ? current.name : '', placeholder: 'e.g. AI capex by layer, 2022 to 2026'});
    const note = h('input', {type: 'text', name: 'view-note', autocomplete: 'off', value: current ? current.note || '' : '', placeholder: 'e.g. hyperscalers carry nine tenths of it'});
    const msg = h('p', {class: 'msg small'});
    drawer(h('h3', {}, current ? 'Save changes' : 'Save as view'), h('div', {class: 'form'}, h('label', {}, 'Name', name), h('label', {}, 'Note', note)),
      h('p', {class: 'muted small', style: 'margin-top:.6rem'}, 'Saved views are queries another system can call: /api/v1/views/<id>/data.'),
      h('div', {class: 'hrow', style: 'margin-top:1rem'}, h('button', {type: 'button', class: 'btn', onclick: async () => {
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
