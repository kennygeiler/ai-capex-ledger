// Capex Ledger: merged screen (Mirror + acceleration strip + ranked table + inline Desk + lineage drawer).
// Reads contract v2 (see README). standalone.html inlines the data as window.__DATA__.
const D = window.__DATA__ ?? (await fetch("../data/sample.json").then((r) => r.json()));

const ALLQ = D.meta.quarters;
const LAST4 = ALLQ.slice(-4);
const PREV4 = ALLQ.slice(-8, -4);
const COS = D.companies;
const SELLERS = COS.filter((c) => c.role === "seller");
const byId = new Map(D.facts.map((f) => [f.id, f]));
const byKey = new Map(D.facts.map((f) => [`${f.ticker}|${f.metric}|${f.calQ}`, f]));
const coBy = new Map(COS.map((c) => [c.ticker, c]));

const fact = (t, m, q) => byKey.get(`${t}|${m}|${q}`) ?? null;
const val = (t, m, q) => fact(t, m, q)?.value ?? null;
const ids = (...fs) => fs.flat().filter(Boolean).map((f) => f.id).join(",");

const METRIC = { revenue: "Revenue", revenue_dc: "Data-center revenue", capex: "Capex", lease_rou: "New finance leases", ocf: "Operating cash flow" };
const METHOD = { reported: "As filed", ytd_diff: "YTD difference", q4_derived: "10-K minus 9 months" };
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

// ───────── Formatting ─────────
const fmt = (d) => {
  if (d == null) return "–";
  const b = d / 1e9, a = Math.abs(b), s = b < 0 ? "−" : "";
  return `${s}$${a >= 100 ? Math.round(a) : a >= 10 ? a.toFixed(1) : a.toFixed(2)}B`;
};
const pct = (r, signed = true) => {
  if (r == null || !isFinite(r)) return "–";
  const n = Math.round(Math.abs(r) * 100);
  return `${n === 0 ? "" : signed && r > 0 ? "+" : r < 0 ? "−" : ""}${n}%`;
};
const times = (r) => (r == null || !isFinite(r) ? "–" : `${r.toFixed(1)}×`);
const qLabel = (q) => `Q${q.slice(5)} ’${q.slice(2, 4)}`;
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

// ───────── State (all of it lives in the URL) ─────────
const DEFAULT = { range: "8", leases: "1", tsla: "0", sort: "cxocf", dir: "desc", co: "", scale: "own", mf: "all", mm: "all" };
const state = { ...DEFAULT };
for (const [k, v] of new URLSearchParams(location.search)) if (k in DEFAULT) state[k] = v;
function setState(patch) {
  Object.assign(state, patch);
  const url = new URL(location);
  for (const k of Object.keys(DEFAULT)) state[k] === DEFAULT[k] ? url.searchParams.delete(k) : url.searchParams.set(k, state[k]);
  history.replaceState(null, "", url);
  render();
}

const Q = () => (state.range === "4" ? LAST4 : ALLQ);
const leasesOn = () => state.leases === "1";
const buyers = () => COS.filter((c) => c.role === "buyer" && (state.tsla === "1" || !c.flags.includes("not_ai_core")));

// Spend for one quarter: cash capex, plus new finance leases when that layer is on.
const spendQ = (t, q) => {
  const cx = val(t, "capex", q);
  if (cx == null) return null;
  return cx + (leasesOn() ? val(t, "lease_rou", q) ?? 0 : 0);
};
const sumOver = (fn, qs) => {
  const xs = qs.map(fn);
  return xs.every((x) => x == null) ? null : xs.reduce((a, b) => a + (b ?? 0), 0);
};
const complete = (fn, qs) => qs.every((q) => fn(q) != null);

function buyerStats(c) {
  const t = c.ticker;
  const s = (q) => spendQ(t, q);
  const spend = sumOver(s, LAST4);
  const prev = complete(s, PREV4) ? sumOver(s, PREV4) : null;
  const cx = sumOver((q) => val(t, "capex", q), LAST4);
  const rou = sumOver((q) => val(t, "lease_rou", q), LAST4) ?? 0;
  const ocf = sumOver((q) => val(t, "ocf", q), LAST4);
  const yoyAt = (i) => { const a = s(ALLQ[i]), b = s(ALLQ[i - 4]); return a != null && b ? a / b - 1 : null; };
  const yNow = yoyAt(7), yPrev = yoyAt(6);
  const st = {
    spend, yoy: prev ? spend / prev - 1 : null, cxOcf: ocf ? spend / ocf : null,
    leaseShare: cx ? rou / (cx + rou) : null, fcf: ocf != null ? ocf - cx - rou : null,
    yNow, slowing: yNow != null && yPrev != null && yNow < yPrev - 0.02,
    speeding: yNow != null && yPrev != null && yNow > yPrev + 0.02,
  };
  st.flags = [
    st.cxOcf > 1 && "Spends more than operations bring in",
    st.slowing && "Growth slowing",
    c.listedFrom && `Listed ${qLabel(c.listedFrom)}`,
    c.flags.includes("not_ai_core") && "Mostly non-AI capex",
  ].filter(Boolean);
  st.factIds = {
    spend: ids(LAST4.map((q) => [fact(t, "capex", q), leasesOn() && fact(t, "lease_rou", q)])),
    ocf: ids(LAST4.map((q) => fact(t, "ocf", q))),
    lease: ids(LAST4.map((q) => [fact(t, "capex", q), fact(t, "lease_rou", q)])),
    fcf: ids(LAST4.map((q) => [fact(t, "ocf", q), fact(t, "capex", q), fact(t, "lease_rou", q)])),
  };
  return st;
}

function sellerStats(c) {
  const t = c.ticker;
  const dc = (q) => val(t, "revenue_dc", q);
  const ttm = sumOver(dc, LAST4), prev = complete(dc, PREV4) ? sumOver(dc, PREV4) : null;
  const rev = sumOver((q) => val(t, "revenue", q), LAST4);
  return { ttm, yoy: prev ? ttm / prev - 1 : null, share: rev ? ttm / rev : null, factIds: ids(LAST4.map((q) => fact(t, "revenue_dc", q))) };
}

// ───────── Tooltip, toast ─────────
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
const rows = (pairs) => pairs.map(([a, b]) => `<div class="row"><span>${a}</span><span>${b}</span></div>`).join("");
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg; el.setAttribute("data-show", "");
  clearTimeout(toast.t); toast.t = setTimeout(() => el.removeAttribute("data-show"), 1600);
}

// ───────── SVG helpers ─────────
function niceStep(span, n = 3) {
  const raw = span / n, mag = 10 ** Math.floor(Math.log10(raw)), f = raw / mag;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * mag;
}
// Bar with only the data end rounded (2px), anchored at y0.
function barPath(x, y0, w, y1) {
  if (Math.abs(y1 - y0) < 0.5) return "";
  const up = y1 < y0, r = Math.min(2, Math.abs(y0 - y1), w / 2);
  return up
    ? `M${x},${y0}V${y1 + r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 + r}V${y0}Z`
    : `M${x},${y0}V${y1 - r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 - r}V${y0}Z`;
}
const axisLabel = (t) => (t === 0 ? "0" : `${t < 0 ? "−" : ""}$${+Math.abs(t / 1e9).toFixed(1)}B`);

/** Bars over quarters. values in dollars (null = no filing). values2 stacks a hatched layer on top. */
function bars(el, { qs, values, values2, color, hatch, height = 130, yMin, yMax, labelEvery = 2, tipFn, factFn }) {
  const W = Math.max(200, el.clientWidth), left = 44, bottom = 22, top = 8, H = height, ih = H - top - bottom;
  const tops = values.map((v, i) => (v ?? 0) + (values2?.[i] ?? 0));
  const hi = yMax ?? Math.max(0, ...tops), lo = yMin ?? Math.min(0, ...values.filter((v) => v != null));
  const step = niceStep((hi - lo) || 1);
  const top_ = Math.ceil(hi / step) * step || step, bot_ = Math.floor(lo / step) * step;
  const y = (v) => top + ih - ((v - bot_) / (top_ - bot_)) * ih;
  const band = (W - left) / qs.length, bw = Math.min(22, band * 0.6);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img">`;
  for (let t = bot_; t <= top_ + 1e-6; t += step) {
    s += `<line class="${Math.abs(t) < 1e-6 ? "zero" : "grid"}" x1="${left}" x2="${W}" y1="${y(t)}" y2="${y(t)}"/>`;
    s += `<text x="${left - 8}" y="${y(t) + 4}" text-anchor="end">${axisLabel(t)}</text>`;
  }
  qs.forEach((q, i) => {
    const x = left + band * i + (band - bw) / 2, v = values[i];
    if (v != null) {
      s += `<path class="bar" data-i="${i}" d="${barPath(x, y(0), bw, y(v))}" fill="${v < 0 ? "var(--div-neg)" : color}"/>`;
      if (values2?.[i]) s += `<path class="bar" data-i="${i}" d="${barPath(x, y(v), bw, y(v + values2[i]))}" fill="url(#${hatch})"/>`;
    }
    if ((qs.length - 1 - i) % labelEvery === 0) s += `<text x="${x + bw / 2}" y="${H - 6}" text-anchor="middle">${qLabel(q)}</text>`;
    s += `<rect class="hit" data-i="${i}" ${factFn ? `data-facts="${factFn(i)}"` : ""} x="${left + band * i}" y="${top}" width="${band}" height="${ih}"/>`;
  });
  el.innerHTML = s + "</svg>";
  el.classList.add("chart");
  hover(el, tipFn);
}
function hover(el, tipFn) {
  if (!tipFn) return;
  const marks = [...el.querySelectorAll(".bar")];
  el.querySelectorAll(".hit").forEach((h) => {
    const i = +h.dataset.i;
    h.addEventListener("pointermove", (e) => { marks.forEach((b) => b.classList.toggle("dim", +b.dataset.i !== i)); tip.show(tipFn(i), e); });
    h.addEventListener("pointerleave", () => { marks.forEach((b) => b.classList.remove("dim")); tip.hide(); });
  });
}
function sparkline(values, color, w = 72, h = 20) {
  const pts = values.map((v, i) => [i, v]).filter(([, v]) => v != null);
  if (pts.length < 2) return "";
  const max = Math.max(...pts.map((p) => p[1])), min = Math.min(...pts.map((p) => p[1]));
  const x = (i) => (i / (values.length - 1)) * (w - 2) + 1, y = (v) => h - 2 - ((v - min) / (max - min || 1)) * (h - 4);
  const d = pts.map(([i, v], k) => `${k ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><path d="${d}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/></svg>`;
}

// ───────── Mirror: sellers' data-center revenue above zero, buyers' spend below ─────────
const SELLER_FILL = { NVDA: "var(--seller)", AMD: "var(--seller-2)", MU: "var(--seller-3)", AVGO: "url(#hatch-seller)" };
function drawMirror(el) {
  const qs = Q(), B = buyers();
  const data = qs.map((q) => {
    const cash = B.reduce((a, c) => a + (val(c.ticker, "capex", q) ?? 0), 0);
    const lease = leasesOn() ? B.reduce((a, c) => a + (val(c.ticker, "lease_rou", q) ?? 0), 0) : 0;
    const segs = SELLERS.map((c) => ({ t: c.ticker, v: val(c.ticker, "revenue_dc", q) ?? 0 }));
    const sold = segs.reduce((a, s) => a + s.v, 0);
    const facts = [...B.map((c) => fact(c.ticker, "capex", q)), ...(leasesOn() ? B.map((c) => fact(c.ticker, "lease_rou", q)) : []), ...SELLERS.map((c) => fact(c.ticker, "revenue_dc", q))];
    return { q, cash, lease, spend: cash + lease, segs, sold, gap: Math.max(0, cash + lease - sold), ids: ids(facts) };
  });
  const W = Math.max(320, el.clientWidth), H = 380, left = 52, xLab = 24, top = 18, bottom = 18;
  const lim0 = Math.max(...data.map((d) => Math.max(d.spend, d.sold)));
  const step = niceStep(lim0 * 1.05), lim = Math.ceil((lim0 * 1.05) / step) * step;
  const half = (H - top - bottom - xLab) / 2, mid = top + half;
  const y = (v) => mid - (v / lim) * half;
  const band = (W - left) / qs.length, bw = Math.min(30, band * 0.56);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Sellers' data-center revenue above zero, buyers' spend below, by quarter">`;
  for (let t = -lim; t <= lim + 1e-6; t += step) {
    s += `<line class="${Math.abs(t) < 1e-6 ? "zero" : "grid"}" x1="${left}" x2="${W}" y1="${y(t)}" y2="${y(t)}"/>`;
    s += `<text x="${left - 8}" y="${y(t) + 4}" text-anchor="end">${axisLabel(Math.abs(t))}</text>`;
  }
  data.forEach((d, i) => {
    const x = left + band * i + (band - bw) / 2;
    let acc = 0;
    d.segs.forEach((g) => { s += `<path class="bar" data-i="${i}" d="${barPath(x, y(acc), bw, y(acc + g.v))}" fill="${SELLER_FILL[g.t]}"/>`; acc += g.v; });
    if (d.gap > 0) s += `<rect class="bar" data-i="${i}" x="${x + 0.5}" y="${y(d.spend)}" width="${bw - 1}" height="${y(d.sold) - y(d.spend)}" fill="none" stroke="var(--muted)" stroke-width="1" rx="2"/>`;
    s += `<path class="bar" data-i="${i}" d="${barPath(x, y(0), bw, y(-d.cash))}" fill="var(--buyer)"/>`;
    if (d.lease) s += `<path class="bar" data-i="${i}" d="${barPath(x, y(-d.cash), bw, y(-d.spend))}" fill="url(#hatch-buyer)"/>`;
    s += `<text x="${x + bw / 2}" y="${H - 6}" text-anchor="middle">${qLabel(d.q)}</text>`;
    s += `<rect class="hit" data-i="${i}" data-facts="${d.ids}" data-title="Everything behind ${qLabel(d.q)}" x="${left + band * i}" y="${top}" width="${band}" height="${H - top - xLab}"/>`;
  });
  const L = data.at(-1), lx = left + band * (data.length - 1) + band / 2;
  s += `<text class="ink" x="${lx}" y="${y(L.spend) - 6}" text-anchor="middle">gap ${fmt(L.gap)}</text>`;
  s += `<text class="ink" x="${lx}" y="${y(-L.spend) + 15}" text-anchor="middle">${fmt(L.spend)}</text>`;
  el.innerHTML = s + "</svg>";
  el.classList.add("chart");
  hover(el, (i) => {
    const d = data[i];
    return `<div class="t">${qLabel(d.q)}</div>${rows([
      ["Sellers' data-center revenue", fmt(d.sold)],
      ...d.segs.map((g) => [`&nbsp;&nbsp;${g.t}${g.t === "AVGO" ? " (segment)" : ""}`, fmt(g.v)]),
      ["Buyers' capex", fmt(d.cash)],
      ...(leasesOn() ? [["New finance leases", fmt(d.lease)]] : []),
      ["Gap", fmt(d.gap)],
    ])}<div class="sub">Click for every filing behind this quarter</div>`;
  });
}

// ───────── Acceleration strip: QoQ change in each buyer's spend ─────────
function heatCell(r) {
  if (r == null) return "";
  const k = Math.min(1, Math.abs(r) / 0.3) * 85;
  return `background: color-mix(in oklab, var(${r >= 0 ? "--div-pos" : "--div-neg"}) ${k.toFixed(0)}%, var(--div-neutral))`;
}
function heatmap() {
  const qs = Q().filter((q) => ALLQ.indexOf(q) > 0);
  const head = qs.map((q) => `<th scope="col">Q${q.slice(5)}<br>’${q.slice(2, 4)}</th>`).join("");
  const body = buyers().map((c) => {
    const st = buyerStats(c);
    const cells = qs.map((q) => {
      const i = ALLQ.indexOf(q), a = spendQ(c.ticker, q), b = i > 0 ? spendQ(c.ticker, ALLQ[i - 1]) : null;
      if (a == null || b == null) return `<td class="empty">–</td>`;
      const r = a / b - 1;
      const fs = ids([fact(c.ticker, "capex", q), fact(c.ticker, "capex", ALLQ[i - 1]), ...(leasesOn() ? [fact(c.ticker, "lease_rou", q), fact(c.ticker, "lease_rou", ALLQ[i - 1])] : [])]);
      return `<td><button data-facts="${fs}" data-title="${c.ticker} ${qLabel(q)} vs ${qLabel(ALLQ[i - 1])}: ${pct(r)}" style="${heatCell(r)}" aria-label="${c.name} ${qLabel(q)}: ${pct(r)} on the quarter before">${pct(r)}</button></td>`;
    }).join("");
    const trend = st.yNow == null ? "–" : `${pct(st.yNow)} ${st.slowing ? "slowing" : st.speeding ? "speeding up" : "steady"}`;
    return `<tr><th scope="row" class="rowh">${c.ticker}</th>${cells}<td class="trend">${trend}</td></tr>`;
  }).join("");
  return `<table class="heat"><thead><tr><th class="rowh"></th>${head}<th class="trend">Year on year</th></tr></thead><tbody>${body}</tbody></table>
    <div class="heat-scale"><span>Cut</span><span class="bar"></span><span>Faster</span><span>, ±30% or more at full colour</span></div>`;
}

// ───────── Inline Desk ─────────
function desk(c) {
  const t = c.ticker, qs = Q(), isBuyer = c.role === "buyer";
  const panels = isBuyer
    ? [
        { key: "spend", label: leasesOn() ? "Capex + new finance leases" : "Capex", values: qs.map((q) => val(t, "capex", q)), values2: leasesOn() ? qs.map((q) => val(t, "lease_rou", q)) : null, color: "var(--buyer)", hatch: "hatch-buyer", facts: (q) => [fact(t, "capex", q), leasesOn() && fact(t, "lease_rou", q)] },
        { key: "ocf", label: "Operating cash flow", values: qs.map((q) => val(t, "ocf", q)), color: "var(--muted)", facts: (q) => [fact(t, "ocf", q)] },
        { key: "fcf", label: "Cash left after capex & leases", values: qs.map((q) => { const o = val(t, "ocf", q), x = val(t, "capex", q); return o == null || x == null ? null : o - x - (val(t, "lease_rou", q) ?? 0); }), color: "var(--muted)", facts: (q) => [fact(t, "ocf", q), fact(t, "capex", q), fact(t, "lease_rou", q)] },
        { key: "rev", label: "Revenue", values: qs.map((q) => val(t, "revenue", q)), color: "var(--muted)", facts: (q) => [fact(t, "revenue", q)] },
      ]
    : [
        { key: "dc", label: c.flags.includes("segment_not_ai") ? "Semiconductor segment revenue" : "Data-center revenue", values: qs.map((q) => val(t, "revenue_dc", q)), color: c.flags.includes("segment_not_ai") ? "url(#hatch-seller)" : "var(--seller)", facts: (q) => [fact(t, "revenue_dc", q)] },
        { key: "rev", label: "Total revenue", values: qs.map((q) => val(t, "revenue", q)), color: "var(--muted)", facts: (q) => [fact(t, "revenue", q)] },
      ];
  const shared = state.scale === "shared";
  const all = panels.flatMap((p) => p.values.map((v, i) => (v ?? 0) + (p.values2?.[i] ?? 0)));
  const sharedMax = Math.max(0, ...all), sharedMin = Math.min(0, ...panels.flatMap((p) => p.values.filter((v) => v != null)));
  const metrics = [...new Set(D.facts.filter((f) => f.ticker === t).map((f) => f.metric))];
  const factRows = D.facts
    .filter((f) => f.ticker === t && qs.includes(f.calQ) && (state.mf === "all" || f.metric === state.mf) && (state.mm === "all" || f.method === state.mm))
    .sort((a, b) => (a.calQ < b.calQ ? 1 : a.calQ > b.calQ ? -1 : a.metric.localeCompare(b.metric)));
  const html = `
    <div class="desk">
      <div class="desk-head">
        <div><h3>${c.name}</h3>
          <div class="meta">${c.ticker}, CIK ${c.cik}, fiscal year ends ${MONTHS[c.fyEnd - 1]}${c.listedFrom ? `, listed ${qLabel(c.listedFrom)}` : ""}</div></div>
        <div class="controls">
          <div class="seg" role="group" aria-label="Chart scale">
            <button data-set="scale=own" data-fk="scale-own" aria-pressed="${!shared}">Own scale per chart</button>
            <button data-set="scale=shared" data-fk="scale-shared" aria-pressed="${shared}">One shared scale</button>
          </div>
          <button class="linkbtn" data-set="co=" data-fk="close-desk">Close</button>
        </div>
      </div>
      <div class="desk-panels">${panels.map((p, k) => {
        const last = (p.values.at(-1) ?? 0) + (p.values2?.at(-1) ?? 0);
        const yearAgo = ALLQ.indexOf(qs.at(-1)) >= 4 ? (() => { const i = qs.length - 5; return i >= 0 ? (p.values[i] ?? 0) + (p.values2?.[i] ?? 0) : null; })() : null;
        return `<div><h4>${p.label}</h4><div class="big">${fmt(last)}</div>
          <div class="sub">${qLabel(qs.at(-1))}${yearAgo > 0 && last > 0 ? `, ${pct(last / yearAgo - 1)} on a year before` : yearAgo != null ? `, ${fmt(yearAgo)} a year before` : ""}</div><div data-panel="${k}"></div></div>`;
      }).join("")}</div>
      <div class="facts-tools">
        <strong style="font-weight:600">Every figure and where it came from</strong>
        <label>Metric <select data-sel="mf" data-fk="mf"><option value="all">All</option>${metrics.map((m) => `<option value="${m}" ${state.mf === m ? "selected" : ""}>${METRIC[m]}</option>`).join("")}</select></label>
        <label>Method <select data-sel="mm" data-fk="mm"><option value="all">All</option>${Object.entries(METHOD).map(([k, v]) => `<option value="${k}" ${state.mm === k ? "selected" : ""}>${v}</option>`).join("")}</select></label>
        <span class="muted">${factRows.length} facts. Click a row for its lineage.</span>
      </div>
      <div class="facts-scroll"><table class="facts">
        <thead><tr><th>Quarter</th><th>Fiscal</th><th>Metric</th><th class="r">Value</th><th>Method</th><th>Form</th><th>Filed</th><th>XBRL tag</th></tr></thead>
        <tbody>${factRows.map((f) => `<tr data-facts="${f.id}" tabindex="0">
          <td data-label="">${qLabel(f.calQ)}</td><td data-label="" class="muted">FY${f.fy} ${f.fp}</td><td data-label="">${METRIC[f.metric]}</td>
          <td class="r" data-label="">${fmt(f.value)}</td><td data-label=""><span class="method" data-m="${f.method}">${METHOD[f.method]}</span></td>
          <td data-label="">${f.form}</td><td data-label="" class="muted">${f.filed}</td><td class="wide"><code>${f.tag}</code></td></tr>`).join("")}</tbody>
      </table></div>
    </div>`;
  const draw = (root) => panels.forEach((p, k) => {
    const el = root.querySelector(`[data-panel="${k}"]`);
    if (!el) return;
    bars(el, {
      qs, values: p.values, values2: p.values2, color: p.color, hatch: p.hatch, height: 130,
      yMax: shared ? sharedMax : undefined, yMin: shared ? sharedMin : undefined, labelEvery: qs.length > 4 ? 3 : 1,
      factFn: (i) => ids(p.facts(qs[i])),
      tipFn: (i) => `<div class="t">${p.label}, ${qLabel(qs[i])}</div>${rows([["Value", fmt((p.values[i] ?? 0) + (p.values2?.[i] ?? 0))], ...(p.values2 ? [["of which new leases", fmt(p.values2[i])]] : [])])}<div class="sub">Click for lineage</div>`,
    });
  });
  return { html, draw };
}

// ───────── Lineage drawer ─────────
const drawer = document.getElementById("drawer"), scrim = document.getElementById("scrim");
let lastFocus = null, drawerStack = [], drawerMeta = {};
function factDetail(f) {
  const c = coBy.get(f.ticker);
  const cikNum = String(+c.cik);
  const link = D.meta.sample
    ? `<code>${f.accession}</code><div class="muted small">Sample accession, so no EDGAR link yet.</div>`
    : `<a href="https://www.sec.gov/Archives/edgar/data/${cikNum}/${f.accession.replace(/-/g, "")}/" target="_blank" rel="noopener"><code>${f.accession}</code></a>`;
  const from = f.derivedFrom?.length
    ? `<h3>Computed from</h3><ul>${f.derivedFrom.map((d) => `<li><span>${d.span}<br><code class="muted">${d.accession}</code></span><span>${fmt(d.value)}</span></li>`).join("")}</ul>
       <p class="muted small" style="margin-top:8px">${fmt(f.derivedFrom[0].value)} − ${fmt(f.derivedFrom[1].value)} = ${fmt(f.value)} (sample figures do not reconcile exactly).</p>`
    : "";
  return `${drawerStack.length > 1 ? `<button class="linkbtn" data-back style="margin-bottom:12px">Back to list</button>` : ""}
    <h2 id="drawer-title">${c.name}: ${METRIC[f.metric]}, ${qLabel(f.calQ)}</h2>
    <div class="val">${fmt(f.value)}</div>
    <p class="muted">${METHOD[f.method]}. ${D.meta.methods[f.method]}</p>
    <dl>
      <dt>Fiscal period</dt><dd>FY${f.fy} ${f.fp}</dd>
      <dt>Period</dt><dd>${f.periodStart} to ${f.periodEnd}</dd>
      <dt>Calendar quarter</dt><dd>${qLabel(f.calQ)}</dd>
      <dt>Form</dt><dd>${f.form}, filed ${f.filed}</dd>
      <dt>XBRL tag</dt><dd><code>${f.tag}</code></dd>
      <dt>Dimension</dt><dd>${f.dimension ? `<code>${f.dimension.axis}</code> = <code>${f.dimension.member}</code>` : "None (company total)"}</dd>
      <dt>Accession</dt><dd>${link}</dd>
      <dt>Exact value</dt><dd>$${f.value.toLocaleString("en-US")}</dd>
    </dl>${from}
    <p class="muted small">${D.meta.metrics[f.metric] ?? ""}</p>`;
}
function factList(list, title, sum) {
  const total = list.reduce((a, f) => a + f.value, 0);
  return `<h2 id="drawer-title">${title ? esc(title) : `${list.length} filings behind this number`}</h2>
    <p class="muted" style="margin-top:6px">${sum ? `Sum of listed values: ${fmt(total)}. ` : `${list.length} filings. `}Click one for its full lineage.</p>
    <ul>${list.map((f) => `<li><button data-open="${f.id}">${f.ticker}, ${METRIC[f.metric]}, ${qLabel(f.calQ)}</button><span>${fmt(f.value)}</span></li>`).join("")}</ul>`;
}
function paintDrawer() {
  const top = drawerStack.at(-1);
  drawer.innerHTML = `<button class="close" data-close aria-label="Close">✕</button>${top.length === 1 ? factDetail(top[0]) : factList(top, drawerMeta.title, drawerMeta.sum)}`;
}
function openDrawer(idStr, title = "", sum = false) {
  drawerMeta = { title, sum };
  const list = idStr.split(",").map((i) => byId.get(i)).filter(Boolean);
  if (!list.length) return;
  if (!drawer.hasAttribute("data-open")) lastFocus = document.activeElement;
  drawerStack = [list];
  paintDrawer();
  drawer.setAttribute("data-open", ""); scrim.setAttribute("data-open", "");
  tip.hide();
  drawer.focus();
}
function closeDrawer() {
  drawer.removeAttribute("data-open"); scrim.removeAttribute("data-open");
  lastFocus?.focus?.();
}
drawer.addEventListener("click", (e) => {
  if (e.target.closest("[data-close]")) return closeDrawer();
  if (e.target.closest("[data-back]")) { drawerStack.pop(); return paintDrawer(); }
  const o = e.target.closest("[data-open]");
  if (o) { drawerStack.push([byId.get(o.dataset.open)]); paintDrawer(); }
});
scrim.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && drawer.hasAttribute("data-open")) closeDrawer(); });

// ───────── Page ─────────
const root = document.getElementById("root");
const SORTS = {
  co: (c) => c.name, spend: (c, s) => s.spend, yoy: (c, s) => s.yoy, cxocf: (c, s) => s.cxOcf, lease: (c, s) => s.leaseShare, fcf: (c, s) => s.fcf,
};

function render() {
  const keepY = scrollY;
  const fk = document.activeElement?.getAttribute?.("data-fk");
  const B = buyers();
  const stats = new Map(B.map((c) => [c.ticker, buyerStats(c)]));
  const total = B.reduce((a, c) => a + (stats.get(c.ticker).spend ?? 0), 0);
  const prevTotal = B.reduce((a, c) => a + (sumOver((q) => spendQ(c.ticker, q), PREV4) ?? 0), 0);
  const sellerNow = SELLERS.reduce((a, c) => a + (sellerStats(c).ttm ?? 0), 0);
  const sellerPrev = SELLERS.reduce((a, c) => a + (sumOver((q) => val(c.ticker, "revenue_dc", q), PREV4) ?? 0), 0);

  // Ranked buyers
  const dir = state.dir === "asc" ? 1 : -1, key = SORTS[state.sort] ? state.sort : "cxocf";
  const ranked = [...B].sort((a, b) => {
    const va = SORTS[key](a, stats.get(a.ticker)), vb = SORTS[key](b, stats.get(b.ticker));
    if (va == null) return 1; if (vb == null) return -1;
    return (typeof va === "string" ? va.localeCompare(vb) : va - vb) * dir;
  });
  const th = (k, label, cls = "") => `<th class="${cls}"><button data-sort="${k}" data-fk="sort-${k}" ${state.sort === k ? `aria-sort="${state.dir === "asc" ? "ascending" : "descending"}"` : ""}>${label}${state.sort === k ? (state.dir === "asc" ? " ↑" : " ↓") : ""}</button></th>`;
  const openCo = state.co && coBy.get(state.co);
  const deskView = openCo ? desk(openCo) : null;
  const deskRow = (t, span) => (openCo && openCo.ticker === t ? `<tr class="desk-row"><td colspan="${span}">${deskView.html}</td></tr>` : "");

  const buyerRows = ranked.map((c) => {
    const s = stats.get(c.ticker), open = state.co === c.ticker;
    return `<tr class="row" data-co="${c.ticker}" tabindex="0" aria-expanded="${open}">
      <td class="toggle-cell" aria-hidden="true">${open ? "−" : "+"}</td>
      <td class="co"><strong>${c.ticker}</strong> <span class="muted">${c.name}</span></td>
      <td class="r" data-label="${leasesOn() ? "Capex + leases, 4Q" : "Capex, 4Q"}"><button class="num-btn" data-sum="1" data-title="${c.ticker} ${leasesOn() ? "capex + new leases" : "capex"}, last four quarters" data-facts="${s.factIds.spend}">${fmt(s.spend)}</button></td>
      <td class="r" data-label="Vs prior year">${pct(s.yoy)}</td>
      <td class="r" data-label="Capex ÷ operating cash"><button class="num-btn" data-title="${c.ticker}: spend and operating cash, last four quarters" data-facts="${s.factIds.spend},${s.factIds.ocf}">${times(s.cxOcf)}</button></td>
      <td class="r" data-label="New leases, share"><button class="num-btn" data-title="${c.ticker}: capex and new leases, last four quarters" data-facts="${s.factIds.lease}">${s.leaseShare ? pct(s.leaseShare, false) : "0%"}</button></td>
      <td class="r ${s.fcf < 0 ? "neg" : ""}" data-label="Cash left after"><button class="num-btn" data-title="${c.ticker}: operating cash, capex and leases, last four quarters" data-facts="${s.factIds.fcf}">${fmt(s.fcf)}</button></td>
      <td class="flags flags-cell" data-label="${s.flags.length ? "Flags" : ""}">${s.flags.map((f) => `<span>${f}</span>`).join("")}</td>
      <td class="spark">${sparkline(ALLQ.map((q) => spendQ(c.ticker, q)), "var(--buyer)")}</td>
    </tr>${deskRow(c.ticker, 9)}`;
  }).join("");

  const sellerRows = SELLERS.map((c) => {
    const s = sellerStats(c), open = state.co === c.ticker;
    const note = c.flags.includes("segment_not_ai") ? "Whole semiconductor segment, wider than AI" : c.ticker === "MU" ? "Segments reorganised in 2025; restatement bridge pending" : "";
    return `<tr class="row" data-co="${c.ticker}" tabindex="0" aria-expanded="${open}">
      <td class="toggle-cell" aria-hidden="true">${open ? "−" : "+"}</td>
      <td class="co"><strong>${c.ticker}</strong> <span class="muted">${c.name}</span></td>
      <td class="r" data-label="Data-center revenue, 4Q"><button class="num-btn" data-sum="1" data-title="${c.ticker} data-center revenue, last four quarters" data-facts="${s.factIds}">${fmt(s.ttm)}</button></td>
      <td class="r" data-label="Vs prior year">${pct(s.yoy)}</td>
      <td class="r" data-label="Share of revenue">${pct(s.share, false)}</td>
      <td class="flags-cell muted small" data-label="${note ? "Note" : ""}">${note}</td>
      <td class="spark">${sparkline(ALLQ.map((q) => val(c.ticker, "revenue_dc", q)), "var(--seller)")}</td>
    </tr>${deskRow(c.ticker, 7)}`;
  }).join("");

  // Concentration
  const shares = B.map((c) => ({ c, v: stats.get(c.ticker).spend ?? 0 })).sort((a, b) => b.v - a.v);
  const top3 = shares.slice(0, 3).reduce((a, s) => a + s.v, 0) / total;
  const conc = shares.map((s, i) => {
    const p = s.v / total;
    const label = p > 0.09 ? `${s.c.ticker} ${pct(p, false)}` : p > 0.04 ? s.c.ticker : "";
    return `<button data-co="${s.c.ticker}" data-fk="conc-${s.c.ticker}" style="flex: ${p} 1 0; background: color-mix(in oklab, var(--buyer) ${100 - i * 12}%, var(--paper))" title="${s.c.name}: ${pct(p, false)} (${fmt(s.v)})" aria-label="${s.c.name}: ${pct(p, false)} of combined spend">${label}</button>`;
  }).join("");

  root.innerHTML = `
  <header class="mast"><div class="wrap">
    <span class="wordmark">Capex Ledger</span>
    <div class="controls">
      <div class="seg" role="group" aria-label="Range">
        <button data-set="range=4" data-fk="range-4" aria-pressed="${state.range === "4"}">Last 4Q</button>
        <button data-set="range=8" data-fk="range-8" aria-pressed="${state.range === "8"}">Last 8Q</button>
      </div>
      <label class="check"><input type="checkbox" data-toggle="leases" data-fk="leases" ${leasesOn() ? "checked" : ""}> New finance leases</label>
      <label class="check"><input type="checkbox" data-toggle="tsla" data-fk="tsla" ${state.tsla === "1" ? "checked" : ""}> Include Tesla</label>
      <button class="linkbtn" data-copy data-fk="copy">Copy link to this view</button>
    </div>
  </div></header>

  <div class="wrap">
    <section class="hero">
      <h1>Who pays for AI. Who gets paid.</h1>
      <p>In the last four quarters ${B.length} buyers spent ${fmt(total)} on capex${leasesOn() ? " and new finance leases" : ""}, ${pct(total / prevTotal - 1)} on the year before. Chip sellers' data-center revenue grew ${pct(sellerNow / sellerPrev - 1)}.</p>
    </section>

    <div class="fold">
      <section class="panel" aria-labelledby="mirror-h">
        <h2 id="mirror-h">Spend below the line, booked revenue above</h2>
        <p class="lede">The outline is spend these four sellers did not book. Click any quarter for the filings behind it.</p>
        <div class="legend">
          <span><span class="sw buyer"></span>Buyers' capex</span>
          ${leasesOn() ? `<span><span class="sw buyer-hatch"></span>New finance leases</span>` : ""}
          <span><span class="sw seller"></span>Data-center revenue (NVDA, AMD, MU, darkest first)</span>
          <span><span class="sw seller-hatch"></span>Broadcom semiconductor segment, wider than AI</span>
          <span><span class="sw gap"></span>Gap</span>
        </div>
        <div id="mirror"></div>
        <p class="caption"><strong>Totals, not transactions.</strong> Filings don't say who buys from whom. The gap also holds what these sellers don't cover: ${D.meta.notCovered.join(", ").toLowerCase()}.</p>
      </section>
      <section class="panel" aria-labelledby="heat-h">
        <h2 id="heat-h">Is spending speeding up?</h2>
        <p class="lede">Change in each buyer's ${leasesOn() ? "capex plus new leases" : "capex"} on the quarter before. Click a cell for its filings.</p>
        <div style="margin-top:14px">${heatmap()}</div>
      </section>
    </div>

    <section class="section" aria-labelledby="conc-h">
      <div class="section-head"><h2 id="conc-h">Who the cycle rests on</h2>
        <p>Share of combined spend, last four quarters. The top three account for ${pct(top3, false)}. Click a company to open its filings.</p></div>
      <div class="conc">${conc}</div>
    </section>

    <section class="section" aria-labelledby="rank-h">
      <div class="section-head"><h2 id="rank-h">Who's stretching</h2>
        <p>Above 1.0× means spending more than operations bring in. Click a row to open the company; click a number to see the filings behind it.</p></div>
      <div style="overflow-x:auto"><table class="rank">
        <thead><tr><th class="toggle-cell"></th>${th("co", "Company")}${th("spend", leasesOn() ? "Capex + leases, 4Q" : "Capex, 4Q", "r")}${th("yoy", "Vs prior year", "r")}${th("cxocf", "Capex ÷ operating cash", "r")}${th("lease", "New leases, share", "r")}${th("fcf", "Cash left after", "r")}<th>Flags</th><th>8 quarters</th></tr></thead>
        <tbody>${buyerRows}</tbody>
      </table></div>
    </section>

    <section class="section" aria-labelledby="sell-h">
      <div class="section-head"><h2 id="sell-h">What the sellers book</h2>
        <p>Data-center segment revenue, read from each filing's segment breakdown.</p></div>
      <div style="overflow-x:auto"><table class="rank">
        <thead><tr><th class="toggle-cell"></th><th>Company</th><th class="r">Data-center revenue, 4Q</th><th class="r">Vs prior year</th><th class="r">Share of revenue</th><th>Note</th><th>8 quarters</th></tr></thead>
        <tbody>${sellerRows}</tbody>
      </table></div>
    </section>

    <section class="section" aria-labelledby="method-h">
      <div class="section-head"><h2 id="method-h">How each number was made</h2>
        <p>Every figure carries its filing, XBRL tag, period and method. ${esc(D.meta.calendarRule)}</p></div>
      <dl class="methods">
        ${Object.entries(D.meta.methods).map(([k, v]) => `<div><dt>${METHOD[k]}</dt><dd>${v}</dd></div>`).join("")}
        ${Object.entries(D.meta.metrics).map(([k, v]) => `<div><dt>${METRIC[k]}</dt><dd>${v}</dd></div>`).join("")}
        ${D.pending.map((p) => `<div><dt>Not yet in the data: ${p.name}</dt><dd>${p.reason}</dd></div>`).join("")}
        <div><dt>Tesla</dt><dd>Off by default: most of its capex is factories and cars, not AI. Turn it on in the bar above.</dd></div>
      </dl>
    </section>
    <footer class="foot">Capex Ledger. Source: SEC EDGAR XBRL filings. ${D.meta.sample ? `Sample data (contract ${D.meta.contract}), generated ${D.meta.generated}.` : ""}</footer>
  </div>`;

  drawMirror(root.querySelector("#mirror"));
  if (deskView) deskView.draw(root);
  if (fk) root.querySelector(`[data-fk="${fk}"]`)?.focus({ preventScroll: true });
  window.scrollTo(0, keepY);
}

// ───────── Events (delegated) ─────────
root.addEventListener("click", (e) => {
  const f = e.target.closest("[data-facts]");
  if (f) return openDrawer(f.dataset.facts, f.dataset.title, f.dataset.sum === "1");
  const set = e.target.closest("[data-set]");
  if (set) { const [k, v] = set.dataset.set.split("="); return setState({ [k]: v }); }
  const sort = e.target.closest("[data-sort]");
  if (sort) { const k = sort.dataset.sort; return setState(state.sort === k ? { dir: state.dir === "asc" ? "desc" : "asc" } : { sort: k, dir: k === "co" ? "asc" : "desc" }); }
  if (e.target.closest("[data-copy]")) {
    navigator.clipboard?.writeText(location.href).then(() => toast("Link copied"), () => toast("Copy failed"));
    return;
  }
  const co = e.target.closest("[data-co]");
  if (co && !e.target.closest(".desk")) {
    const t = co.dataset.co;
    return setState({ co: state.co === t ? "" : t, mf: "all", mm: "all" });
  }
});
root.addEventListener("change", (e) => {
  const tg = e.target.closest("[data-toggle]");
  if (tg) return setState({ [tg.dataset.toggle]: tg.checked ? "1" : "0" });
  const sel = e.target.closest("[data-sel]");
  if (sel) setState({ [sel.dataset.sel]: sel.value });
});
root.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const el = e.target;
  if (el.matches?.("tr[data-co]")) { e.preventDefault(); setState({ co: state.co === el.dataset.co ? "" : el.dataset.co, mf: "all", mm: "all" }); }
  else if (el.matches?.("tr[data-facts]")) { e.preventDefault(); openDrawer(el.dataset.facts); }
});
let rz;
addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(render, 200); });

render();
