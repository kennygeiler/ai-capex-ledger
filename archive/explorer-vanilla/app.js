// Capex Ledger Explorer: a data tool over the cleaned EDGAR dataset (data/clean/viz.json).
// standalone.html inlines the data as window.__DATA__.
const D = window.__DATA__ ?? (await fetch("../data/clean/viz.json").then((r) => r.json()));
D.facts = D.facts.map((a) => Object.fromEntries(D.fact_cols.map((c, i) => [c, a[i]])));
const META = D.meta, PULL = D.pull, COS = D.companies;
const WINDOW = META.window, YEARS = META.years;
const ALLQ = [...new Set(D.facts.filter((f) => f.period_type === "quarter").map((f) => f.cal_q))].sort();
const ALLY = [...new Set(D.facts.filter((f) => f.period_type === "year").map((f) => f.fy_key))].sort();
const coBy = new Map(COS.map((c) => [c.ticker, c]));
const cikBy = new Map(COS.map((c) => [String(c.cik), c.ticker]));
D.facts.forEach((f, i) => (f.id = i));
const pk = (f) => (f.period_type === "quarter" ? f.cal_q : f.fy_key);
const key = (t, m, p) => `${t}|${m}|${p}`;
const fidx = new Map(D.facts.map((f) => [key(f.ticker, f.metric, pk(f)), f]));
const issueIdx = new Map(), coverageIdx = new Map();
for (const i of D.issues) {
  if (!i.cal_q) continue;
  const k = key(i.ticker, i.metric, i.cal_q);
  if (i.check === "coverage") coverageIdx.set(k, i.message);
  else issueIdx.set(k, [...(issueIdx.get(k) ?? []), i]);
}

const METRICS = {
  revenue: { label: "Revenue", unit: "usd" },
  capex: { label: "Capex", unit: "usd" },
  opex: { label: "Opex (excl. cost of revenue)", unit: "usd" },
  total_costs: { label: "Total operating costs", unit: "usd" },
  capex_to_revenue: { label: "Capex ÷ revenue", unit: "ratio", num: "capex", den: "revenue" },
  opex_to_revenue: { label: "Opex ÷ revenue", unit: "ratio", num: "opex", den: "revenue" },
};
const CHARTS = { line: "Lines", bars: "Bars", multiples: "Small multiples", heat: "Heat table" };
const METHOD = {
  reported: "As filed", ytd_diff: "YTD difference", q4_derived: "10-K minus 9 months", fy_minus_quarters: "Full year minus 3 quarters",
  derived: "Computed", reported_operating_expenses: "Reported OperatingExpenses", reported_costs_and_expenses: "Reported CostsAndExpenses",
  sga_plus_rnd: "SG&A + R&D", noninterest_expense: "Non-interest expense (bank)", no_cost_of_revenue_line: "Total costs (no cost-of-revenue line)",
};

// ───────── State (in the URL) ─────────
const DEFAULT = {
  tab: "explore", per: "q", uni: "ai", q: "", cos: "MSFT.0,GOOGL.1,AMZN.2,META.3,ORCL.4,CRWV.5", metric: "capex", tf: "value", chart: "line",
  qf: WINDOW[0], qt: WINDOW.at(-1), yf: YEARS[0], yt: YEARS.at(-1), scale: "linear", mscale: "shared",
  sev: "warn", chk: "all", tk: "all", fco: "MSFT", fm: "capex", fq: "", dco: "VZ", net: "network",
};
const state = { ...DEFAULT };
for (const [k, v] of new URLSearchParams(location.search)) if (k in DEFAULT) state[k] = v;
const sel = () => (state.cos ? state.cos.split(",").filter(Boolean).map((s) => { const [t, n] = s.split("."); return { t, slot: +n }; }).filter((s) => coBy.has(s.t)) : []);
const slotOf = (t) => sel().find((s) => s.t === t)?.slot ?? -1;
const colorOf = (t) => { const s = slotOf(t); return s >= 0 && s < 8 ? `var(--s${s + 1})` : "var(--other)"; };
function setState(patch) {
  Object.assign(state, patch);
  const url = new URL(location);
  for (const k of Object.keys(DEFAULT)) state[k] === DEFAULT[k] ? url.searchParams.delete(k) : url.searchParams.set(k, state[k]);
  history.replaceState(null, "", url);
  render();
}
function withCos(list) { return list.map((x) => `${x.t}.${x.slot}`).join(","); }
function addCos(cur, ts) {
  for (const t of ts) { if (cur.some((x) => x.t === t)) continue; const used = new Set(cur.map((x) => x.slot)); cur.push({ t, slot: [0, 1, 2, 3, 4, 5, 6, 7].find((n) => !used.has(n)) ?? 9 }); }
  return cur;
}
const ANNUAL = () => state.per === "y";
const PERIODS = () => (ANNUAL() ? ALLY.filter((y) => y >= state.yf && y <= state.yt) : ALLQ.filter((q) => q >= state.qf && q <= state.qt));
const ALLP = () => (ANNUAL() ? ALLY : ALLQ);
const TRANSFORMS = () => (ANNUAL()
  ? { value: "Value", index: "Indexed, first year = 100", pop: "Change on previous year" }
  : { value: "Value", index: "Indexed, first quarter = 100", pop: "Change on previous quarter", yoy: "Change on same quarter last year" });

// ───────── Values ─────────
function base(t, m, p) {
  const M = METRICS[m];
  if (M.num) {
    const a = fidx.get(key(t, M.num, p)), b = fidx.get(key(t, M.den, p));
    return a && b && b.value ? { v: a.value / b.value, facts: [a, b] } : null;
  }
  const f = fidx.get(key(t, m, p));
  return f ? { v: f.value, facts: [f] } : null;
}
function cell(t, p) {
  const m = state.metric, b = base(t, m, p);
  if (!b) return null;
  const all = ALLP(), i = all.indexOf(p);
  const tf = TRANSFORMS()[state.tf] ? state.tf : "value";
  if (tf === "value") return b;
  if (tf === "index") {
    const first = PERIODS().map((x) => base(t, m, x)).find((x) => x && x.v);
    return first && first.v > 0 ? { v: (b.v / first.v) * 100, facts: [...b.facts, ...first.facts], ref: first } : null;
  }
  const prev = base(t, m, all[i - (tf === "yoy" ? 4 : 1)]);
  return prev && prev.v > 0 ? { v: b.v / prev.v - 1, facts: [...b.facts, ...prev.facts], ref: prev } : null;
}
const outUnit = () => { const tf = TRANSFORMS()[state.tf] ? state.tf : "value"; return tf === "value" ? METRICS[state.metric].unit : tf === "index" ? "index" : "pct"; };

// ───────── Formatting ─────────
const usd = (v, digits = 1) => {
  const a = Math.abs(v), s = v < 0 ? "−" : "";
  if (a >= 1e9) return `${s}$${(a / 1e9).toFixed(a >= 1e11 ? 0 : digits)}B`;
  if (a >= 1e6) return `${s}$${(a / 1e6).toFixed(a >= 1e8 ? 0 : digits)}M`;
  return `${s}$${Math.round(a).toLocaleString()}`;
};
const fmt = (v, unit = outUnit()) => {
  if (v == null || !isFinite(v)) return "–";
  if (unit === "usd") return usd(v);
  if (unit === "ratio") return `${(v * 100).toFixed(1)}%`;
  if (unit === "index") return v.toFixed(0);
  const p = v * 100;
  return `${p > 0.05 ? "+" : p < -0.05 ? "−" : ""}${Math.abs(p).toFixed(1)}%`;
};
const axisFmt = (v, unit = outUnit()) => (unit === "usd" ? (v === 0 ? "0" : usd(v, 0)) : unit === "index" ? `${Math.round(v)}` : `${Math.round(v * 100)}%`);
const qLabel = (q) => (q?.startsWith("FY") ? q : `Q${q.slice(5)} ’${q.slice(2, 4)}`);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const edgarUrl = (cik, accn) => `https://www.sec.gov/Archives/edgar/data/${cik}/${accn.replace(/-/g, "")}/${accn}-index.htm`;
const bytes = (n) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1e3)} KB`);

// ───────── Tooltip / toast ─────────
const tipEl = document.getElementById("tip");
const tip = {
  show(html, e) {
    tipEl.innerHTML = html; tipEl.setAttribute("data-show", "");
    const r = tipEl.getBoundingClientRect(), p = 14;
    let x = e.clientX + p, y = e.clientY + p;
    if (x + r.width > innerWidth - 8) x = e.clientX - r.width - p;
    if (y + r.height > innerHeight - 8) y = e.clientY - r.height - p;
    tipEl.style.left = `${x}px`; tipEl.style.top = `${y}px`;
  },
  hide() { tipEl.removeAttribute("data-show"); },
};
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg; el.setAttribute("data-show", "");
  clearTimeout(toast.t); toast.t = setTimeout(() => el.removeAttribute("data-show"), 1600);
}

// ───────── Scales and charts ─────────
function niceTicks(lo, hi, n = 5) {
  if (lo === hi) { lo -= 1; hi += 1; }
  const raw = (hi - lo) / n, mag = 10 ** Math.floor(Math.log10(raw)), f = raw / mag;
  const step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * mag;
  const a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, out = [];
  for (let t = a; t <= b + step * 1e-6; t += step) out.push(+t.toPrecision(12));
  return out;
}
function yScale(vals, top, bottom, { zero = true, log = false } = {}) {
  const v = vals.filter((x) => x != null && isFinite(x));
  if (!v.length) return { y: () => bottom, ticks: [0] };
  if (log) {
    const pos = v.filter((x) => x > 0);
    const lo = 10 ** Math.floor(Math.log10(Math.min(...pos))), hi = 10 ** Math.ceil(Math.log10(Math.max(...pos)));
    const ticks = []; for (let t = lo; t <= hi * 1.0001; t *= 10) ticks.push(t);
    return { y: (x) => bottom - ((Math.log10(Math.max(x, lo)) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo) || 1)) * (bottom - top), ticks };
  }
  let lo = Math.min(...v), hi = Math.max(...v);
  if (zero) { lo = Math.min(0, lo); hi = Math.max(0, hi); }
  const ticks = niceTicks(lo, hi), a = ticks[0], b = ticks.at(-1);
  return { y: (x) => bottom - ((x - a) / (b - a || 1)) * (bottom - top), ticks };
}
function barPath(x, y0, w, y1) {
  if (Math.abs(y1 - y0) < 0.5) return "";
  const up = y1 < y0, r = Math.min(2, Math.abs(y0 - y1), w / 2);
  return up ? `M${x},${y0}V${y1 + r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 + r}V${y0}Z`
            : `M${x},${y0}V${y1 - r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 - r}V${y0}Z`;
}
const gridSvg = (sc, left, W, unit) => sc.ticks.map((t) => `<line class="${t === 0 ? "zero" : "grid"}" x1="${left}" x2="${W}" y1="${sc.y(t)}" y2="${sc.y(t)}"/><text x="${left - 8}" y="${sc.y(t) + 4}" text-anchor="end">${axisFmt(t, unit)}</text>`).join("");
const tipRows = (data, i, hot) => data.filter((d) => d.pts[i]).sort((a, b) => b.pts[i].v - a.pts[i].v)
  .map((d) => `<div class="row ${d.t === hot ? "hot" : ""}"><span><span class="sw" style="background:${colorOf(d.t)}"></span>${d.t}</span><span>${fmt(d.pts[i].v)}</span></div>`).join("");

function lineChart(el) {
  const ps = PERIODS(), S = sel(), W = Math.max(320, el.clientWidth), H = 400, left = 58, right = 64, top = 12, bottom = 28;
  const data = S.map((s) => ({ ...s, pts: ps.map((p) => cell(s.t, p)) }));
  const log = state.scale === "log" && state.tf === "value" && data.every((d) => d.pts.every((p) => !p || p.v > 0));
  const sc = yScale(data.flatMap((d) => d.pts.map((p) => p?.v)), top, H - bottom, { zero: state.tf !== "index", log });
  const x = (i) => left + (ps.length === 1 ? (W - left - right) / 2 : (i / (ps.length - 1)) * (W - left - right));
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${esc(METRICS[state.metric].label)} by period">${gridSvg(sc, left, W - right + 8, outUnit())}`;
  ps.forEach((p, i) => { if (ps.length <= 12 || i % 2 === (ps.length - 1) % 2) s += `<text x="${x(i)}" y="${H - 8}" text-anchor="middle">${qLabel(p)}</text>`; });
  s += `<line class="cross" id="cross" x1="0" x2="0" y1="${top}" y2="${H - bottom}" style="display:none"/>`;
  const ends = [];
  data.forEach((d) => {
    let path = "", pen = false;
    d.pts.forEach((p, i) => { if (p) { path += `${pen ? "L" : "M"}${x(i).toFixed(1)},${sc.y(p.v).toFixed(1)}`; pen = true; } else pen = false; });
    s += `<path class="series ln" data-t="${d.t}" d="${path}" stroke="${colorOf(d.t)}"/>`;
    d.pts.forEach((p, i) => { if (p) s += `<circle class="series" data-t="${d.t}" cx="${x(i)}" cy="${sc.y(p.v)}" r="2.5" fill="${colorOf(d.t)}"/>`; });
    const li = d.pts.map((p, i) => (p ? i : -1)).filter((i) => i >= 0).at(-1);
    if (li != null) ends.push({ t: d.t, y: sc.y(d.pts[li].v), x: x(li) });
  });
  ends.sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + 13);
  if (ends.length <= 12) ends.forEach((e) => (s += `<text class="lbl" x="${e.x + 8}" y="${e.y + 4}">${e.t}</text>`));
  const w = (W - left - right) / Math.max(1, ps.length - 1);
  ps.forEach((p, i) => (s += `<rect class="hit" data-i="${i}" x="${x(i) - w / 2}" y="${top}" width="${w}" height="${H - top - bottom}"/>`));
  el.innerHTML = s + "</svg>";
  const cross = el.querySelector("#cross");
  el.querySelectorAll(".hit").forEach((h) => {
    const i = +h.dataset.i;
    h.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect(), svgY = (e.clientY - r.top) * (H / r.height);
      const hot = data.filter((d) => d.pts[i]).map((d) => ({ d, dist: Math.abs(sc.y(d.pts[i].v) - svgY) })).sort((a, b) => a.dist - b.dist)[0]?.d;
      cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.style.display = "";
      el.querySelectorAll(".series").forEach((p) => p.classList.toggle("dim", hot && p.dataset.t !== hot.t));
      tip.show(`<div class="t">${qLabel(ps[i])}</div>${tipRows(data, i, hot?.t) || "No data"}<div class="sub">Click for ${hot ? hot.t : "the"} filing lineage</div>`, e);
      h.dataset.t = hot?.t ?? "";
    });
    h.addEventListener("pointerleave", () => { cross.style.display = "none"; el.querySelectorAll(".series").forEach((p) => p.classList.remove("dim")); tip.hide(); });
    h.addEventListener("click", () => h.dataset.t && openCell(h.dataset.t, ps[i]));
  });
}
function barChart(el) {
  const ps = PERIODS(), S = sel(), W = Math.max(320, el.clientWidth), H = 400, left = 58, top = 12, bottom = 28;
  const data = S.map((s) => ({ ...s, pts: ps.map((p) => cell(s.t, p)) }));
  const sc = yScale(data.flatMap((d) => d.pts.map((p) => p?.v)), top, H - bottom, { zero: true });
  const band = (W - left) / ps.length, bw = Math.max(2, Math.min(18, (band * 0.8) / Math.max(1, S.length) - 2));
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img">${gridSvg(sc, left, W, outUnit())}`;
  ps.forEach((p, i) => {
    const gx = left + band * i + (band - (bw + 2) * S.length) / 2;
    data.forEach((d, k) => { const c = d.pts[i]; if (c) s += `<path class="series" data-t="${d.t}" d="${barPath(gx + k * (bw + 2), sc.y(0), bw, sc.y(c.v))}" fill="${colorOf(d.t)}"/>`; });
    if (ps.length <= 12 || i % 2 === (ps.length - 1) % 2) s += `<text x="${left + band * i + band / 2}" y="${H - 8}" text-anchor="middle">${qLabel(p)}</text>`;
    data.forEach((d, k) => (s += `<rect class="hit" data-i="${i}" data-t="${d.t}" x="${gx + k * (bw + 2) - 1}" y="${top}" width="${bw + 2}" height="${H - top - bottom}"/>`));
  });
  el.innerHTML = s + "</svg>";
  el.querySelectorAll(".hit").forEach((h) => {
    const i = +h.dataset.i, t = h.dataset.t;
    h.addEventListener("pointermove", (e) => { el.querySelectorAll(".series").forEach((p) => p.classList.toggle("dim", p.dataset.t !== t)); tip.show(`<div class="t">${qLabel(ps[i])}</div>${tipRows(data, i, t)}<div class="sub">Click for ${t} filing lineage</div>`, e); });
    h.addEventListener("pointerleave", () => { el.querySelectorAll(".series").forEach((p) => p.classList.remove("dim")); tip.hide(); });
    h.addEventListener("click", () => openCell(t, ps[i]));
  });
}
function multiples(el) {
  const ps = PERIODS(), S = sel(), all = S.flatMap((s) => ps.map((p) => cell(s.t, p)?.v));
  el.innerHTML = `<div class="multiples">${S.map((s) => {
    const last = [...ps].reverse().map((p) => cell(s.t, p)).find(Boolean);
    return `<div><h4>${s.t} <span class="muted" style="font-weight:400">${esc(coBy.get(s.t).name)}</span></h4><div class="m-sub">Latest ${last ? fmt(last.v) : "–"}</div><div class="chart" data-m="${s.t}"></div></div>`;
  }).join("")}</div>`;
  S.forEach((s) => {
    const box = el.querySelector(`[data-m="${s.t}"]`), W = Math.max(200, box.clientWidth), H = 150, left = 50, top = 6, bottom = 20;
    const pts = ps.map((p) => cell(s.t, p));
    const sc = yScale(state.mscale === "shared" ? all : pts.map((p) => p?.v), top, H - bottom, { zero: true });
    const band = (W - left) / ps.length, bw = Math.min(16, band * 0.62);
    let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${gridSvg({ ...sc, ticks: sc.ticks.filter((_, i, a) => a.length <= 4 || i % 2 === 0) }, left, W, outUnit())}`;
    pts.forEach((p, i) => {
      const x0 = left + band * i + (band - bw) / 2;
      if (p) svg += `<path class="series" d="${barPath(x0, sc.y(0), bw, sc.y(p.v))}" fill="${colorOf(s.t)}"/>`;
      if (i === 0 || i === ps.length - 1) svg += `<text x="${x0 + bw / 2}" y="${H - 5}" text-anchor="middle">${qLabel(ps[i])}</text>`;
      svg += `<rect class="hit" data-i="${i}" x="${left + band * i}" y="${top}" width="${band}" height="${H - top - bottom}"/>`;
    });
    box.innerHTML = svg + "</svg>";
    box.querySelectorAll(".hit").forEach((h) => {
      const i = +h.dataset.i;
      h.addEventListener("pointermove", (e) => tip.show(`<div class="t">${s.t} ${qLabel(ps[i])}</div><div class="row"><span>${esc(METRICS[state.metric].label)}</span><span>${fmt(pts[i]?.v)}</span></div><div class="sub">Click for filing lineage</div>`, e));
      h.addEventListener("pointerleave", () => tip.hide());
      h.addEventListener("click", () => openCell(s.t, ps[i]));
    });
  });
}

// ───────── Pivot table ─────────
function heatStyle(v, lo, hi) {
  if (v == null) return "";
  if (outUnit() === "pct") {
    const k = Math.min(1, Math.abs(v) / 0.5) * 85;
    return `background: color-mix(in oklab, var(${v >= 0 ? "--div-pos" : "--div-neg"}) ${k.toFixed(0)}%, var(--div-neutral))`;
  }
  const k = hi > lo ? ((v - lo) / (hi - lo)) * 100 : 50;
  return `background: color-mix(in oklab, var(--seq-hi) ${k.toFixed(0)}%, var(--seq-lo))`;
}
function pivot() {
  const ps = PERIODS(), S = sel(), heat = state.chart === "heat";
  const vals = S.flatMap((s) => ps.map((p) => cell(s.t, p)?.v)).filter((v) => v != null);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const body = S.map((s) => {
    let n = 0;
    const tds = ps.map((p) => {
      const c = cell(s.t, p);
      if (!c) {
        const m = METRICS[state.metric].num ?? state.metric;
        const reason = coverageIdx.get(key(s.t, m, p)) ?? (ANNUAL() ? "No 10-K full-year value for this fiscal year." : "No value for this quarter.");
        return `<td class="missing" title="${esc(reason)}">–</td>`;
      }
      n++;
      const derived = c.facts.some((f) => f.method !== "reported");
      const iss = c.facts.flatMap((f) => issueIdx.get(key(f.ticker, f.metric, f.cal_q)) ?? []);
      const flag = iss.some((i) => i.severity === "error") ? "flag-error" : iss.some((i) => i.severity === "warn") ? "flag-warn" : "";
      const xml = c.facts.some((f) => f.source_api === "xbrl_instance");
      return `<td class="cell ${derived ? "derived" : ""} ${flag} ${heat ? "heatcell" : ""}" data-cell="${s.t}|${p}" style="${heat ? heatStyle(c.v, lo, hi) : ""}" ${xml ? 'title="Parsed from the filing\'s XBRL instance XML"' : ""}><span>${fmt(c.v)}${xml ? "<sup>x</sup>" : ""}</span></td>`;
    }).join("");
    return `<tr><td><span class="sw" style="background:${colorOf(s.t)}"></span><strong>${s.t}</strong> <span class="muted">${esc(coBy.get(s.t).name)}</span></td>${tds}<td class="muted">${n}/${ps.length}</td></tr>`;
  }).join("");
  const foot = state.tf === "value" && METRICS[state.metric].unit === "usd" && S.length > 1
    ? `<tfoot><tr><td>Selected total</td>${ps.map((p) => { const xs = S.map((s) => cell(s.t, p)?.v); const sum = xs.reduce((a, b) => a + (b ?? 0), 0); return `<td>${xs.some((v) => v == null) ? `<span class="muted" title="Some companies have no value for this period">${fmt(sum)}*</span>` : fmt(sum)}</td>`; }).join("")}<td></td></tr></tfoot>` : "";
  return `<div class="pivot-scroll"><table class="pivot"><thead><tr><th>Company</th>${ps.map((p) => `<th>${qLabel(p)}</th>`).join("")}<th>Coverage</th></tr></thead><tbody>${body}</tbody>${foot}</table></div>`;
}

// ───────── Lineage drawer ─────────
const drawer = document.getElementById("drawer"), scrim = document.getElementById("scrim");
let lastFocus = null;
function factBlock(f) {
  const c = coBy.get(f.ticker);
  const src = (f.sources ?? []).map((x) => x.metric
    ? `<li>${esc(x.metric.replace(/_/g, " "))}: <code>${esc(x.concept)}</code> ${usd(x.val)} <span class="muted">(${esc(x.accn)})</span></li>`
    : `<li>${x.start} to ${x.end}: ${usd(x.val)} <span class="muted">${x.form} filed ${x.filed}${x.src === "xbrl_instance" ? ", parsed from instance XML" : ""},</span> <a href="${edgarUrl(c.cik, x.accn)}" target="_blank" rel="noopener"><code>${x.accn}</code></a></li>`).join("");
  const iss = f.cal_q ? issueIdx.get(key(f.ticker, f.metric, f.cal_q)) ?? [] : [];
  return `<div class="fact">
    <h3>${esc(METRICS[f.metric]?.label ?? f.metric)}, ${qLabel(pk(f))}: ${usd(f.value, 2)}</h3>
    <dl>
      <dt>Method</dt><dd>${METHOD[f.method] ?? f.method}. <span class="muted">${esc(META.methods[f.method] ?? "")}</span></dd>
      <dt>XBRL concept</dt><dd><code>${esc(f.concept)}</code></dd>
      <dt>Read from</dt><dd>${f.source_api === "xbrl_instance" ? "The filing's XBRL instance XML (companyfacts API had not caught up)" : f.source_api === "derived" ? "Computed from the facts below" : "SEC companyfacts API"}</dd>
      <dt>Period</dt><dd>${f.period_start} to ${f.period_end} (${f.days} days${f.days_outside_cal_q ? `, ${f.days_outside_cal_q} outside ${qLabel(f.cal_q)}` : ""})</dd>
      <dt>Fiscal</dt><dd>FY${f.fiscal_year}${f.fiscal_quarter ? ` Q${f.fiscal_quarter}` : ""}</dd>
      <dt>Filing</dt><dd>${f.form}, filed ${f.filed}, <a href="${edgarUrl(c.cik, f.accession)}" target="_blank" rel="noopener"><code>${f.accession}</code></a></dd>
      <dt>Exact value</dt><dd>$${Number(f.value).toLocaleString("en-US")}</dd>
      ${f.vintages ? `<dt>Vintages</dt><dd>Carried in ${f.vintages} filing${f.vintages > 1 ? "s" : ""}${f.restated && f.original_value != null ? `; restated from $${Number(f.original_value).toLocaleString("en-US")}` : f.restated ? "; a source was restated" : ""}</dd>` : ""}
      ${f.basis_conflict ? `<dt>Basis</dt><dd>Full year minus nine months mixed two bases; used full year minus the three restated quarters.</dd>` : ""}
    </dl>
    ${src ? `<div class="muted">Built from</div><ul>${src}</ul>` : ""}
    ${iss.length ? `<div class="muted" style="margin-top:8px">Checks</div><ul>${iss.map((i) => `<li><span class="sev-${i.severity}">${i.severity}</span> ${esc(i.check)}: ${esc(i.message)}</li>`).join("")}</ul>` : ""}
    ${f.cal_q && D.traces[key(f.ticker, f.metric, f.cal_q)] ? `<p style="margin-top:8px"><button class="btn" data-trace="${f.ticker}|${f.metric}|${f.cal_q}">See the raw facts and parsing steps</button></p>` : ""}
  </div>`;
}
function openCell(t, p) {
  const c = cell(t, p), co = coBy.get(t), M = METRICS[state.metric];
  if (!drawer.hasAttribute("data-open")) lastFocus = document.activeElement;
  const tf = TRANSFORMS()[state.tf] ? state.tf : "value";
  const formula = !c ? "" : tf === "value" && M.num ? `${M.label}: ${usd(c.facts[0].value)} ÷ ${usd(c.facts[1].value)}`
    : tf === "value" ? "" : `${fmt(base(t, state.metric, p).v, M.unit)} against ${fmt(c.ref.v, M.unit)} (${TRANSFORMS()[tf].toLowerCase()})`;
  const uniq = c ? [...new Map(c.facts.map((f) => [f.id, f])).values()] : [];
  drawer.innerHTML = `<button class="close" data-close aria-label="Close">✕</button>
    <h2 id="drawer-title">${esc(co.name)} (${t}), ${qLabel(p)}</h2>
    <div class="muted">${esc(M.label)}, ${TRANSFORMS()[tf].toLowerCase()}</div>
    <div class="big">${c ? fmt(c.v) : "No value"}</div>
    ${formula ? `<div class="muted">${esc(formula)}</div>` : ""}
    ${!c ? `<p style="margin-top:10px">${esc(coverageIdx.get(key(t, M.num ?? state.metric, p)) ?? "No fact for this period.")}</p>` : ""}
    ${uniq.map(factBlock).join("")}`;
  drawer.setAttribute("data-open", ""); scrim.setAttribute("data-open", "");
  tip.hide(); drawer.focus();
}
function closeDrawer() { drawer.removeAttribute("data-open"); scrim.removeAttribute("data-open"); lastFocus?.focus?.(); }
drawer.addEventListener("click", (e) => {
  if (e.target.closest("[data-close]")) return closeDrawer();
  const tr = e.target.closest("[data-trace]");
  if (tr) { const [t, m, q] = tr.dataset.trace.split("|"); closeDrawer(); setState({ tab: "found", fco: t, fm: m, fq: q }); setTimeout(() => document.getElementById("parse")?.scrollIntoView(), 50); }
});
scrim.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && drawer.hasAttribute("data-open")) closeDrawer(); });

// ───────── CSV ─────────
function download(name, text) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" })); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
const csvRow = (xs) => xs.map((x) => (x == null ? "" : /[",\n]/.test(String(x)) ? `"${String(x).replace(/"/g, '""')}"` : x)).join(",");
function viewCsv() {
  const rows = [["ticker", "name", "period", "metric", "transform", "value", "methods", "accessions"]];
  for (const s of sel()) for (const p of PERIODS()) {
    const c = cell(s.t, p);
    rows.push([s.t, coBy.get(s.t).name, p, state.metric, state.tf, c?.v ?? "", c ? [...new Set(c.facts.map((f) => f.method))].join("|") : "", c ? [...new Set(c.facts.map((f) => f.accession))].join("|") : ""]);
  }
  return rows.map(csvRow).join("\n");
}
function factsCsv() {
  const cols = ["ticker", "period_type", "metric", "cal_q", "fy_key", "value", "method", "source_api", "concept", "period_start", "period_end", "fiscal_year", "fiscal_quarter", "form", "filed", "accession", "restated", "in_window"];
  return [cols, ...D.facts.map((f) => cols.map((c) => f[c]))].map(csvRow).join("\n");
}

// ───────── Shared page bits ─────────
const root = document.getElementById("root");
const segBtns = (k, opts) => `<div class="seg">${Object.entries(opts).map(([v, l]) => `<button data-set="${k}=${v}" data-fk="${k}-${v}" aria-pressed="${state[k] === v}">${l}</button>`).join("")}</div>`;
const UNIS = { ai: "AI set (19)", sp100: "S&P 100", all: `All (${COS.length})` };
const inUni = (c) => state.uni === "all" || (state.uni === "ai" ? c.sets.includes("AI set") : c.sets.includes("S&P 100"));
function topBar() {
  const tabs = { explore: "Explore", quality: "Data quality", found: "How it was found & parsed", admin: "Admin", sources: "Method" };
  return `<header class="top"><span class="brand">Capex Ledger</span>
    <nav class="tabs" role="tablist">${Object.entries(tabs).map(([k, v]) => `<button role="tab" data-set="tab=${k}" data-fk="tab-${k}" aria-selected="${state.tab === k}">${v}</button>`).join("")}</nav>
    <span class="stamp">SEC EDGAR, pulled ${PULL.finished_at.slice(0, 16).replace("T", " ")} UTC. ${COS.length} companies.</span></header>`;
}

// ───────── Explore ─────────
function explorePage() {
  const S = sel(), selected = new Set(S.map((s) => s.t)), ps = PERIODS(), TF = TRANSFORMS();
  if (!TF[state.tf]) state.tf = "value";
  const pool = COS.filter(inUni).filter((c) => !state.q || `${c.ticker} ${c.name} ${c.legal_name}`.toLowerCase().includes(state.q.toLowerCase()));
  const grpOf = (c) => (state.uni === "ai" ? c.group : state.uni === "sp100" ? c.sector : c.sets.includes("AI set") ? c.group : c.sector);
  const groups = [...new Set(pool.map(grpOf))];
  const over8 = S.length > 8 && (state.chart === "line" || state.chart === "bars");
  const all = ALLP(), [fk, tk] = ANNUAL() ? ["yf", "yt"] : ["qf", "qt"];
  const side = `<aside class="side">
    <div class="ctl"><h3>Periods</h3>${segBtns("per", { q: "Quarterly (10-Q)", y: "Annual (10-K)" })}</div>
    <div class="ctl"><h3>Metric</h3><select data-sel="metric" data-fk="metric">${Object.entries(METRICS).map(([k, m]) => `<option value="${k}" ${state.metric === k ? "selected" : ""}>${m.label}</option>`).join("")}</select></div>
    <div class="ctl"><h3>Show as</h3><select data-sel="tf" data-fk="tf">${Object.entries(TF).map(([k, l]) => `<option value="${k}" ${state.tf === k ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    <div class="ctl"><h3>Chart</h3>${segBtns("chart", CHARTS)}</div>
    ${state.chart === "line" ? `<div class="ctl"><h3>Y axis</h3>${segBtns("scale", { linear: "Linear", log: "Log" })}</div>` : ""}
    ${state.chart === "multiples" ? `<div class="ctl"><h3>Scale</h3>${segBtns("mscale", { shared: "Shared", own: "Own per company" })}</div>` : ""}
    <div class="ctl"><h3>${ANNUAL() ? "Fiscal years" : "Quarters"}</h3><div class="row2">
      <select data-sel="${fk}" data-fk="${fk}" aria-label="From">${all.filter((p) => p <= state[tk]).map((p) => `<option value="${p}" ${state[fk] === p ? "selected" : ""}>${qLabel(p)}</option>`).join("")}</select>
      <select data-sel="${tk}" data-fk="${tk}" aria-label="To">${all.filter((p) => p >= state[fk]).map((p) => `<option value="${p}" ${state[tk] === p ? "selected" : ""}>${qLabel(p)}${!ANNUAL() && p > WINDOW.at(-1) ? " (partial)" : ""}</option>`).join("")}</select></div>
      <p class="note" style="margin-top:4px">${ANNUAL() ? "Fiscal years as each company defines them (Nvidia's FY ends in January, Microsoft's in June)." : "Calendar quarters; fiscal quarters are mapped by most days."}</p></div>
    <div class="ctl cos"><h3>Companies (${S.length} selected)</h3>
      ${segBtns("uni", UNIS)}
      <input type="search" class="search" data-sel="q" data-fk="q" placeholder="Search ticker or name" value="${esc(state.q)}" aria-label="Search companies">
      <div class="co-list">${groups.map((g) => `<div class="group-h"><span>${esc(g)}</span><span><button data-grp="${esc(g)}" data-on="1">all</button> <button data-grp="${esc(g)}" data-on="0">none</button></span></div>
        ${pool.filter((c) => grpOf(c) === g).map((c) => `<label class="co"><input type="checkbox" data-co="${c.ticker}" data-fk="co-${c.ticker}" ${selected.has(c.ticker) ? "checked" : ""}>
          <span class="chip" style="background:${selected.has(c.ticker) ? colorOf(c.ticker) : "transparent"}"></span><span class="tk">${c.ticker}</span><span class="nm" title="${esc(c.legal_name ?? c.name)}">${esc(c.name)}</span></label>`).join("")}`).join("") || `<p class="note">No match.</p>`}</div>
      <p class="note" style="margin-top:6px"><button class="linkish" data-clear>Clear selection</button></p>
      ${over8 ? `<p class="note warn">Over 8 companies: extra series turn grey. Small multiples or the heat table read better.</p>` : ""}
    </div>
  </aside>`;
  const legend = state.chart === "line" || state.chart === "bars" ? `<div class="legend">${S.map((s) => `<span><span class="sw" style="background:${colorOf(s.t)}"></span>${s.t}</span>`).join("")}</div>` : "";
  const main = `<section class="main">
    <div class="headline"><div><h1>${esc(METRICS[state.metric].label)}${state.tf !== "value" ? `, ${esc(TF[state.tf].toLowerCase())}` : ""}</h1>
      <div class="sub">${S.length} companies, ${qLabel(ps[0] ?? "")} to ${qLabel(ps.at(-1) ?? "")}, ${ANNUAL() ? "fiscal years from 10-K filings" : "calendar quarters from 10-Q and 10-K filings"}. Click any point, bar or cell for its filings.</div></div>
      <div class="actions"><button class="btn" data-act="copy" data-fk="a-copy">Copy link</button><button class="btn" data-act="csv-view" data-fk="a-csv">Download this view</button><button class="btn" data-act="csv-all" data-fk="a-all">Download all facts</button></div></div>
    ${S.length === 0 ? `<p style="margin-top:40px" class="muted">Pick at least one company on the left.</p>` : `
    ${state.chart !== "heat" ? `${legend}<div class="chart-box chart" id="chart"></div>` : ""}
    <div class="table-head"><h2>${state.chart === "heat" ? "Heat table" : "Values"}</h2>
      <div class="key"><span><span style="text-decoration:underline dotted;text-underline-offset:3px">1.2</span> derived</span><span><sup>x</sup> parsed from instance XML</span><span><strong style="color:var(--warn)">!</strong> check flagged</span><span>– no value (hover for why)</span></div></div>
    ${pivot()}`}
  </section>`;
  return `<div class="explore">${side}${main}</div>`;
}

// ───────── Data quality ─────────
function qualityPage() {
  const Q = META.quality, list0 = COS.filter(inUni), tset = new Set(list0.map((c) => c.ticker));
  const checks = [...new Set(D.issues.map((i) => i.check))].sort();
  const list = D.issues.filter((i) => tset.has(i.ticker) && (state.sev === "all" || i.severity === state.sev) && (state.chk === "all" || i.check === state.chk) && (state.tk === "all" || i.ticker === state.tk));
  const covCell = (n, of) => `<span class="cov" style="background: color-mix(in oklab, var(--warn) ${n >= of ? 0 : 20 + (of - n) * (60 / of)}%, transparent)">${n}/${of}</span>`;
  const full = (m) => list0.filter((c) => c.coverage[m] === 8).length;
  return `<div class="page">
    <h2>Data quality</h2>
    <p class="lede">Every check the pipeline ran, and every gap with its reason. Quarters ${qLabel(WINDOW[0])} to ${qLabel(WINDOW.at(-1))}; fiscal years ${YEARS[0]} to ${YEARS.at(-1)}.</p>
    <div style="margin:10px 0">${segBtns("uni", UNIS)}</div>
    <div class="tiles">
      <div class="tile"><div class="n">${list0.length}</div><div class="l">companies</div></div>
      <div class="tile"><div class="n">${full("revenue")}</div><div class="l">with revenue for all 8 quarters</div></div>
      <div class="tile"><div class="n">${full("capex")}</div><div class="l">with capex for all 8</div></div>
      <div class="tile"><div class="n">${full("opex")}</div><div class="l">with opex for all 8</div></div>
      <div class="tile"><div class="n">${Q.tiling_checks - Q.tiling_failures}/${Q.tiling_checks}</div><div class="l">quarter sets that add up to filed totals</div></div>
      <div class="tile"><div class="n">${Q.errors}</div><div class="l">errors</div></div>
      <div class="tile"><div class="n">${Q.warnings}</div><div class="l">warnings</div></div>
    </div>
    <h2>Coverage: quarters of 8 · fiscal years of 5</h2>
    <div style="overflow-x:auto"><table class="plain"><thead><tr><th>Company</th><th>Sector</th><th>Revenue</th><th>Capex</th><th>Opex</th><th>Revenue tag</th><th>Capex tag</th><th>FY ends</th></tr></thead><tbody>
      ${list0.map((c) => `<tr><td><strong>${c.ticker}</strong> <span class="muted">${esc(c.name)}</span></td><td class="muted">${esc(c.sector)}</td>
        ${["revenue", "capex", "opex"].map((m) => `<td>${covCell(c.coverage[m], 8)} ${covCell(c.coverage_annual[m], 5)}</td>`).join("")}
        <td><code>${esc(c.concepts.revenue[0] ?? "–")}</code></td><td><code>${esc(c.concepts.capex[0] ?? "–")}</code></td><td>${c.fiscal_year_end ? `${c.fiscal_year_end.slice(0, 2)}/${c.fiscal_year_end.slice(2)}` : "–"}</td></tr>`).join("")}
    </tbody></table></div>
    <h2>Issues (${list.length})</h2>
    <div class="filters">
      <select data-sel="sev" aria-label="Severity"><option value="all">All severities</option>${["error", "warn", "info"].map((s) => `<option value="${s}" ${state.sev === s ? "selected" : ""}>${s}</option>`).join("")}</select>
      <select data-sel="chk" aria-label="Check"><option value="all">All checks</option>${checks.map((c) => `<option value="${c}" ${state.chk === c ? "selected" : ""}>${c}</option>`).join("")}</select>
      <select data-sel="tk" aria-label="Company"><option value="all">All companies</option>${list0.map((c) => `<option value="${c.ticker}" ${state.tk === c.ticker ? "selected" : ""}>${c.ticker}</option>`).join("")}</select>
    </div>
    <div style="overflow-x:auto"><table class="plain"><thead><tr><th>Severity</th><th>Check</th><th>Company</th><th>Metric</th><th>Quarter</th><th>Detail</th></tr></thead><tbody>
      ${list.slice(0, 400).map((i) => `<tr><td class="sev-${i.severity}">${i.severity}</td><td>${esc(i.check)}</td><td>${i.ticker}</td><td>${esc(i.metric)}</td><td>${i.cal_q ? qLabel(i.cal_q) : "–"}</td><td>${esc(i.message)}</td></tr>`).join("") || `<tr><td colspan="6" class="muted">Nothing matches.</td></tr>`}
    </tbody></table></div>
    <h2>Left out</h2>
    <ul>${META.excluded.map((e) => `<li><strong>${e.ticker}</strong> (${esc(e.name)}): ${esc(e.reason)}</li>`).join("")}</ul>
  </div>`;
}

// ───────── How it was found & parsed ─────────
function foundPage() {
  // A. Which tag each company uses, across the whole set.
  const famMetric = { revenue: "revenue", capex: "capex" };
  const usage = Object.fromEntries(Object.keys(famMetric).map((m) => {
    const by = {};
    for (const c of COS) { const t = c.concepts[m][0] ?? "(none found)"; (by[t] ??= []).push(c.ticker); }
    return [m, Object.entries(by).sort((a, b) => b[1].length - a[1].length)];
  }));
  const opexBy = {};
  for (const f of D.facts) if (f.metric === "opex" && f.period_type === "quarter" && f.cal_q === WINDOW.at(-1)) (opexBy[f.method] ??= []).push(f.ticker);
  const noOpex = COS.filter((c) => !c.coverage.opex).map((c) => c.ticker);
  const usageTable = (rows) => `<table class="plain"><thead><tr><th>Tag (XBRL concept)</th><th>Companies</th><th>Which</th></tr></thead><tbody>${rows.map(([t, list]) => `<tr><td><code>${esc(t)}</code></td><td>${list.length}</td><td class="muted">${list.join(", ")}</td></tr>`).join("")}</tbody></table>`;

  // B. One company's discovery scan.
  const dc = coBy.get(state.dco) ?? COS[0];
  const fams = { revenue: "Revenue", capex: "Capex", cost_of_revenue: "Cost of revenue", operating: "Operating costs and income" };
  const usedFor = { revenue: dc.concepts.revenue, capex: dc.concepts.capex, cost_of_revenue: dc.concepts.cost_of_revenue, operating: [...dc.concepts.operating_income, ...dc.concepts.costs_and_expenses, ...dc.concepts.opex_reported, ...(dc.concepts.sga ?? []), ...(dc.concepts.noninterest_expense ?? [])] };
  const discTables = Object.entries(fams).map(([fam, label]) => {
    const hits = dc.discovery?.[fam] ?? [];
    return `<h3>${label}</h3>${hits.length ? `<table class="plain"><thead><tr><th>Concept found</th><th>Taxonomy label</th><th>Quarters, last 3 years</th><th>Quarters, all</th><th>Latest period</th><th>Status</th></tr></thead><tbody>
      ${hits.map((h, i) => { const rank = usedFor[fam].indexOf(h.concept); const status = rank === 0 && h.quarters_recent ? "<strong>Used (ranked first)</strong>" : rank > 0 ? `Candidate, rank ${rank + 1}` : h.candidate ? "Candidate, no data" : "Found by scan, not a candidate"; return `<tr><td><code>${esc(h.concept)}</code></td><td>${esc(h.label)}</td><td>${h.quarters_recent}</td><td>${h.quarters_all}</td><td>${h.last_period_end ?? "–"}</td><td>${status}</td></tr>`; }).join("")}
    </tbody></table>` : `<p class="muted">No us-gaap concept matched. If the company reports this line, it uses its own extension tag, which the companyfacts API leaves out.</p>`}`;
  }).join("");
  const fills = (dc.gap_fills ?? []).filter((g) => g.status);
  const fillsHtml = fills.length ? `<h3>Filings parsed from instance XML</h3><table class="plain"><thead><tr><th>Form</th><th>Period</th><th>Filed</th><th>Facts read</th><th>File</th></tr></thead><tbody>${fills.map((g) => `<tr><td>${g.form ?? ""}</td><td>${g.period ?? ""}</td><td>${g.filed ?? ""}</td><td>${g.facts ?? ""} facts, ${g.concepts ?? ""} concepts</td><td>${g.url ? `<a href="${g.url}" target="_blank" rel="noopener">${esc(g.url.split("/").pop())}</a>` : esc(g.status)}</td></tr>`).join("")}</tbody></table>` : "";

  // C. Parse trace for one number.
  const traceCos = [...new Set(Object.keys(D.traces).map((k) => k.split("|")[0]))];
  const tco = traceCos.includes(state.fco) ? state.fco : traceCos[0];
  const tms = ["revenue", "capex", "cost_of_revenue", "operating_income"].filter((m) => Object.keys(D.traces).some((k) => k.startsWith(`${tco}|${m}|`)));
  const tm = tms.includes(state.fm) ? state.fm : tms[0];
  const tqs = WINDOW.filter((q) => D.traces[key(tco, tm, q)]);
  const tq = tqs.includes(state.fq) ? state.fq : [...tqs].reverse().find((q) => D.traces[key(tco, tm, q)].method !== "reported") ?? tqs.at(-1);
  const tr = D.traces[key(tco, tm, tq)];
  const row = D.facts.find((f) => f.ticker === tco && f.metric === tm && f.cal_q === tq) ?? null;
  const co = coBy.get(tco);
  let arith = "";
  const $ = (v) => `$${Number(v).toLocaleString("en-US")}`;
  if (tr && tr.steps.length === 2) arith = `${$(tr.steps[0].value)} (${tr.steps[0].start} to ${tr.steps[0].end}) − ${$(tr.steps[1].value)} (${tr.steps[1].start} to ${tr.steps[1].end}) = <strong>${$(tr.steps[0].value - tr.steps[1].value)}</strong>`;
  else if (tr && tr.steps.length > 2) arith = `${$(tr.steps[0].value)} (full year) − ${tr.steps.slice(1).map((s) => $(s.value)).join(" − ")} = <strong>${$(tr.steps[0].value - tr.steps.slice(1).reduce((a, s) => a + s.value, 0))}</strong>`;
  else if (tr) arith = `Taken as filed: <strong>${$(tr.steps[0].value)}</strong>`;
  const parse = !tr ? `<p class="muted">No trace for this selection.</p>` : `
    <p class="lede">Concept <code>${esc(tr.concept)}</code>, taxonomy label "${esc(tr.label)}". ${esc(tr.description)}</p>
    <h3>Step 1. Raw facts returned for this concept and period${tr.steps.length > 1 ? "s" : ""}</h3>
    <p class="note">Each row is one filing that reported the period. Comparatives in later filings repeat it, and restatements change it. The latest filing is used.</p>
    ${tr.steps.map((s) => `<div style="margin:8px 0 14px"><div class="muted">${s.start} to ${s.end}</div><table class="plain"><thead><tr><th>Value</th><th>Form</th><th>Filing's FY / period</th><th>Filed</th><th>Accession</th><th>Frame</th><th></th></tr></thead><tbody>
      ${s.vintages.map((v) => `<tr${v.chosen ? ' style="font-weight:600"' : ""}><td>$${Number(v.val).toLocaleString("en-US")}</td><td>${v.form}</td><td>${v.fy ?? ""} ${v.fp ?? ""}</td><td>${v.filed}</td><td><a href="${edgarUrl(co.cik, v.accn)}" target="_blank" rel="noopener"><code>${v.accn}</code></a></td><td>${v.frame ?? ""}</td><td>${v.chosen ? "used" : ""}</td></tr>`).join("")}
    </tbody></table></div>`).join("")}
    <h3>Step 2. Arithmetic (${METHOD[tr.method] ?? tr.method})</h3>
    <p>${arith}</p><p class="note">${esc(META.methods[tr.method] ?? "")}</p>
    ${row ? `<h3>Step 3. Calendar placement</h3>
    <p>Fiscal period ${row.period_start} to ${row.period_end} (${row.days} days) is FY${row.fiscal_year} Q${row.fiscal_quarter} for ${esc(co.name)} (fiscal year ends ${co.fiscal_year_end?.slice(0, 2)}/${co.fiscal_year_end?.slice(2)}). ${row.days_outside_cal_q ? `${row.days - row.days_outside_cal_q} of its days fall in ${qLabel(row.cal_q)}, so it is placed there.` : `It matches ${qLabel(row.cal_q)} exactly.`}</p>
    <h3>Step 4. Clean row</h3>
    <pre class="cmd">${esc(JSON.stringify({ ticker: row.ticker, metric: row.metric, cal_q: row.cal_q, value: row.value, method: row.method, concept: row.concept, period: `${row.period_start}..${row.period_end}`, fiscal: `FY${row.fiscal_year} Q${row.fiscal_quarter}`, form: row.form, accession: row.accession, filed: row.filed, vintages: row.vintages, restated: row.restated }, null, 1))}</pre>` : ""}`;

  return `<div class="page">
    <h2>How each company's label was found</h2>
    <p class="lede">Companies tag the same line item with different XBRL concepts, and change tags over time. The pipeline doesn't guess. For every company it:</p>
    <ol>
      <li>Scans the company's full list of us-gaap concepts against search patterns for each line item (<code>${esc(META.discovery_patterns.revenue)}</code> for revenue, and similar).</li>
      <li>For every match, builds discrete quarters and counts how many the concept covers in the last three years.</li>
      <li>Ranks the candidate tags by that recent coverage (then by a fixed priority), and takes each quarter from the best-ranked tag that has it. Matches outside the candidate list are shown, so a missed tag is visible.</li>
    </ol>
    <h3>Revenue: which tag each company uses</h3>${usageTable(usage.revenue)}
    <h3>Capex: which tag each company uses</h3>${usageTable(usage.capex)}
    <h3>Opex: which route each company needs (${qLabel(WINDOW.at(-1))})</h3>
    <table class="plain"><thead><tr><th>Route</th><th>Companies</th><th>Which</th></tr></thead><tbody>
      ${Object.entries(opexBy).sort((a, b) => b[1].length - a[1].length).map(([m, l]) => `<tr><td>${METHOD[m] ?? m}<div class="note">${esc(META.methods[m] ?? "")}</div></td><td>${l.length}</td><td class="muted">${l.join(", ")}</td></tr>`).join("")}
      ${noOpex.length ? `<tr><td>No route has data</td><td>${noOpex.length}</td><td class="muted">${noOpex.join(", ")}</td></tr>` : ""}
    </tbody></table>

    <h2 style="margin-top:36px">The scan for one company</h2>
    <div class="filters"><select data-sel="dco" aria-label="Company">${COS.map((c) => `<option value="${c.ticker}" ${dc.ticker === c.ticker ? "selected" : ""}>${c.ticker} ${esc(c.name)}</option>`).join("")}</select>
      <span class="note" style="align-self:center">${dc.n_concepts} us-gaap concepts in ${esc(dc.legal_name ?? dc.name)}'s filings.</span></div>
    ${discTables}${fillsHtml}

    <h2 style="margin-top:36px" id="parse">How one number was parsed</h2>
    <p class="lede">Pick a number. Each step below uses the facts exactly as the API returned them. Traces are kept for the AI set; the full set's raw files are in <code>data/raw/</code>.</p>
    <div class="filters">
      <select data-sel="fco" aria-label="Company">${traceCos.map((t) => `<option value="${t}" ${t === tco ? "selected" : ""}>${t} ${esc(coBy.get(t).name)}</option>`).join("")}</select>
      <select data-sel="fm" aria-label="Metric">${tms.map((m) => `<option value="${m}" ${m === tm ? "selected" : ""}>${m.replace(/_/g, " ")}</option>`).join("")}</select>
      <select data-sel="fq" aria-label="Quarter">${tqs.map((q) => `<option value="${q}" ${q === tq ? "selected" : ""}>${qLabel(q)} (${METHOD[D.traces[key(tco, tm, q)].method]})</option>`).join("")}</select>
    </div>
    ${parse}
  </div>`;
}

// ───────── Admin ─────────
function adminPage() {
  const P = PULL, logs = P.log.filter((x) => state.net === "all" || x.source === state.net);
  const tickerOf = (url) => { const m = url.match(/CIK0*(\d+)|\/data\/(\d+)\//); return m ? cikBy.get(m[1] ?? m[2]) ?? "" : url.includes("company_tickers") ? "*" : ""; };
  const endpoints = [
    ["https://www.sec.gov/files/company_tickers.json", "Ticker → CIK lookup for every SEC registrant. Resolves the 113 tickers at run time."],
    ["https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json", "Every XBRL fact a company has filed, by concept, with period, value, form, accession and filing date. The main source."],
    ["https://data.sec.gov/submissions/CIK##########.json", "Filing history: forms, filing dates, report periods, fiscal year end, SIC code, exchanges."],
    ["https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json → *_htm.xml", "Fallback: a filing's own XBRL instance XML, parsed when companyfacts hasn't caught up with a new 10-Q/10-K."],
  ];
  return `<div class="page">
    <h2>Last data pull</h2>
    <div class="tiles">
      <div class="tile"><div class="n">${P.finished_at.slice(0, 16).replace("T", " ")}</div><div class="l">finished (UTC)</div></div>
      <div class="tile"><div class="n">${P.seconds}s</div><div class="l">run time</div></div>
      <div class="tile"><div class="n">${P.network_requests}</div><div class="l">network requests</div></div>
      <div class="tile"><div class="n">${P.cache_reads}</div><div class="l">cache reads (under 24h old)</div></div>
      <div class="tile"><div class="n">${bytes(P.bytes_downloaded)}</div><div class="l">downloaded this run</div></div>
      <div class="tile"><div class="n">${P.http_errors}</div><div class="l">HTTP errors</div></div>
      <div class="tile"><div class="n">${P.failures.length}</div><div class="l">companies failed</div></div>
    </div>
    <p class="lede">Rate limit: ${esc(P.rate_limit)} (SEC allows 10). User-Agent: ${esc(P.user_agent)}. Raw responses are kept unchanged in <code>data/raw/</code> with their SHA-256, so any number can be re-derived offline.</p>
    <pre class="cmd">python3 -m pipeline.run             # refresh anything older than 24h
python3 -m pipeline.run --refresh   # re-download everything
node scripts/build-standalone.mjs   # rebuild this page</pre>
    ${P.failures.length ? `<h3>Failures</h3><ul>${P.failures.map((f) => `<li>${f.ticker} (${f.stage}): ${esc(f.error)}</li>`).join("")}</ul>` : ""}

    <h2>API connections</h2>
    <table class="plain"><thead><tr><th>Endpoint</th><th>What it gives</th></tr></thead><tbody>${endpoints.map(([u, d]) => `<tr><td><code>${esc(u)}</code></td><td>${esc(d)}</td></tr>`).join("")}</tbody></table>

    <h2>Company freshness</h2>
    <div style="overflow-x:auto"><table class="plain"><thead><tr><th>Company</th><th>CIK</th><th>Latest 10-Q / 10-K</th><th>Period</th><th>Filed</th><th>Latest quarter in data</th><th>Read from</th><th>Raw file fetched</th></tr></thead><tbody>
      ${COS.map((c) => {
        const f = c.recent_filings[0] ?? {};
        const lastQ = D.facts.filter((x) => x.ticker === c.ticker && x.metric === "revenue" && x.period_type === "quarter").map((x) => x.cal_q).sort().at(-1);
        const raw = META.raw_files.find((r) => r.ticker === c.ticker && r.kind === "companyfacts");
        const xml = (c.gap_fills ?? []).filter((g) => g.status === "parsed").length;
        return `<tr><td><strong>${c.ticker}</strong> <span class="muted">${esc(c.name)}</span></td><td>${c.cik}</td><td>${f.form ?? "–"}</td><td>${f.period ?? "–"}</td><td>${f.filed ?? "–"}</td><td>${lastQ ? qLabel(lastQ) : "–"}</td><td>${xml ? `companyfacts + ${xml} instance XML` : "companyfacts"}</td><td class="muted">${raw ? raw.fetched_at.slice(0, 16).replace("T", " ") : "–"}</td></tr>`;
      }).join("")}
    </tbody></table></div>

    <h2>Request log (${logs.length})</h2>
    <div class="filters">${segBtns("net", { network: "Network only", cache: "Cache reads", all: "All" })}</div>
    <div style="overflow-x:auto"><table class="plain"><thead><tr><th>Time (UTC)</th><th>Source</th><th>Status</th><th>ms</th><th>Size</th><th>Company</th><th>URL</th></tr></thead><tbody>
      ${logs.map((x) => `<tr><td class="muted">${x.at.slice(11, 19)}</td><td>${x.source}${x.attempt > 1 ? ` (try ${x.attempt})` : ""}</td><td class="${x.error ? "sev-error" : ""}">${x.status ?? "–"}${x.error ? ` ${esc(x.error)}` : ""}</td><td>${x.ms}</td><td>${bytes(x.bytes)}</td><td>${tickerOf(x.url)}</td><td><code>${esc(x.url.replace("https://", ""))}</code></td></tr>`).join("") || `<tr><td colspan="7" class="muted">Nothing in this view. The last run read everything from cache; switch to "All".</td></tr>`}
    </tbody></table></div>
    <h2>Raw files</h2>
    <div style="overflow-x:auto"><table class="plain"><thead><tr><th>Company</th><th>File</th><th>Fetched</th><th>Size</th><th>SHA-256</th></tr></thead><tbody>
      ${META.raw_files.map((r) => `<tr><td>${r.ticker}</td><td><a href="${r.url}" target="_blank" rel="noopener">${esc(r.kind)}</a></td><td class="muted">${r.fetched_at}</td><td>${bytes(r.bytes)}</td><td><code>${r.sha256.slice(0, 16)}…</code></td></tr>`).join("")}
    </tbody></table></div>
  </div>`;
}

// ───────── Method ─────────
function sourcesPage() {
  return `<div class="page">
    <h2>How the data is made</h2>
    <p class="lede">${esc(META.source)}, with a fallback to each filing's XBRL instance XML. One command rebuilds everything.</p>
    <ol>
      <li><strong>Ingest.</strong> Resolve tickers to CIKs, then pull companyfacts and submissions for each company (Admin tab has every call).</li>
      <li><strong>Fill gaps.</strong> If a recent 10-Q/10-K is on EDGAR but not yet in companyfacts, parse that filing's instance XML (non-dimensional USD facts only).</li>
      <li><strong>Vintages.</strong> One period appears in many filings. Keep the latest-filed value; record the first and the count.</li>
      <li><strong>Discrete quarters.</strong> Three-month facts as filed; year-to-date cash-flow lines differenced; Q4 = 10-K year minus nine months.</li>
      <li><strong>Cleaning.</strong> Drop "quarters" that carry a full-year value (a filer error in four Oracle 10-Ks). Rebuild Q4 from restated quarters when the nine-month figure is on an older basis. Merge a predecessor CIK's history after a reorganization (ExxonMobil, 2026).</li>
      <li><strong>Calendar alignment.</strong> ${esc(META.calendar_rule)} When two fiscal quarters share a calendar quarter (Costco's 12/12/12/16-week year), the later one moves to its next-best quarter if no other period claims it.</li>
      <li><strong>Tag choice and metrics.</strong> See "How it was found & parsed" and the definitions below.</li>
      <li><strong>Checks.</strong> Signs, quarter length, jumps above 3×, quarters adding up to filed totals, restatements, tag switches, coverage with a reason for every gap.</li>
    </ol>
    <h2>Metrics</h2>
    <dl class="defs">${Object.entries(META.metrics).filter(([k]) => METRICS[k]).map(([k, v]) => `<dt>${esc(METRICS[k].label)}</dt><dd>${esc(v)}</dd>`).join("")}
      <dt>Ratios</dt><dd>Capex ÷ revenue and opex ÷ revenue are computed in the explorer from same-period values.</dd></dl>
    <h2>Methods</h2>
    <dl class="defs">${Object.entries(META.methods).map(([k, v]) => `<dt>${esc(METHOD[k] ?? k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>
    <h2>Tags tried, in priority order</h2>
    <dl class="defs">${Object.entries(META.concept_candidates).map(([k, v]) => `<dt>${esc(k.replace(/_/g, " "))}</dt><dd>${v.map((c) => `<code>${c}</code>`).join(", ")}</dd>`).join("")}</dl>
  </div>`;
}

function render() {
  const fk = document.activeElement?.getAttribute?.("data-fk"), y = scrollY;
  const caret = document.activeElement?.selectionStart;
  root.innerHTML = topBar() + ({ quality: qualityPage, found: foundPage, admin: adminPage, sources: sourcesPage }[state.tab] ?? explorePage)();
  const ch = root.querySelector("#chart");
  if (ch && sel().length) (state.chart === "line" ? lineChart : state.chart === "bars" ? barChart : multiples)(ch);
  if (fk) { const el = root.querySelector(`[data-fk="${fk}"]`); el?.focus({ preventScroll: true }); if (caret != null && el?.setSelectionRange) el.setSelectionRange(caret, caret); }
  scrollTo(0, y);
}

// ───────── Events ─────────
root.addEventListener("click", (e) => {
  const c = e.target.closest("[data-cell]");
  if (c) { const [t, p] = c.dataset.cell.split("|"); return openCell(t, p); }
  const s = e.target.closest("[data-set]");
  if (s) { const [k, v] = s.dataset.set.split("="); return setState({ [k]: v }); }
  if (e.target.closest("[data-clear]")) return setState({ cos: "" });
  const g = e.target.closest("[data-grp]");
  if (g) {
    const grpOf = (c) => (state.uni === "ai" ? c.group : state.uni === "sp100" ? c.sector : c.sets.includes("AI set") ? c.group : c.sector);
    const members = COS.filter(inUni).filter((c) => grpOf(c) === g.dataset.grp).map((c) => c.ticker);
    const cur = sel().filter((x) => !members.includes(x.t));
    return setState({ cos: withCos(g.dataset.on === "1" ? addCos(cur, members) : cur) });
  }
  const a = e.target.closest("[data-act]");
  if (a) {
    if (a.dataset.act === "copy") navigator.clipboard?.writeText(location.href).then(() => toast("Link copied"), () => toast("Copy failed"));
    if (a.dataset.act === "csv-view") download(`capex-ledger_${state.metric}_${state.per === "y" ? "annual" : "quarterly"}.csv`, viewCsv());
    if (a.dataset.act === "csv-all") download("capex-ledger_facts.csv", factsCsv());
  }
});
root.addEventListener("change", (e) => {
  const co = e.target.closest("[data-co]");
  if (co) { const cur = sel().filter((x) => x.t !== co.dataset.co); return setState({ cos: withCos(co.checked ? addCos(cur, [co.dataset.co]) : cur) }); }
  const s = e.target.closest("select[data-sel]");
  if (s) setState({ [s.dataset.sel]: s.value });
});
root.addEventListener("input", (e) => { const s = e.target.closest("input[data-sel]"); if (s) setState({ [s.dataset.sel]: s.value }); });
let rz;
addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(render, 200); });
render();
