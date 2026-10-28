// Capex Ledger prototype: four design directions over the same stub data.
// Part 2 swaps data/sample.json for the real EDGAR output (same shape).

// standalone.html inlines the data as window.__DATA__; the dev page fetches it.
const D = window.__DATA__ ?? (await fetch("../data/sample-v1.json").then((r) => r.json()));
const Q = D.meta.quarters;
const COS = D.companies;
const BUYERS = COS.filter((c) => c.role === "spender");
const SELLERS = COS.filter((c) => c.role === "seller");
const byKey = new Map(D.facts.map((f) => [`${f.ticker}|${f.metric}|${f.calQ}`, f]));

const fact = (t, m, q) => byKey.get(`${t}|${m}|${q}`) ?? null;
const val = (t, m, q) => fact(t, m, q)?.value ?? null;
const capex = (t, q, leases = false) => {
  const v = val(t, "capex", q);
  if (v == null) return null;
  return leases ? v + (val(t, "capex_finance_leases", q) ?? 0) : v;
};
const series = (t, m) => Q.map((q) => (m === "capex" ? capex(t, q) : val(t, m, q)));
const sum = (arr) => arr.reduce((a, b) => a + (b ?? 0), 0);
const ttm = (arr) => sum(arr.slice(-4));
const prevTtm = (arr) => sum(arr.slice(-8, -4));
const pct = (a, b) => (b ? (a / b - 1) * 100 : null);
const fmtB = (n) => (n == null ? "–" : `$${n >= 100 ? Math.round(n) : n.toFixed(1)}B`);
const fmtPct = (n, signed = true) => (n == null ? "–" : `${signed && n > 0 ? "+" : ""}${Math.round(n)}%`);
const qLabel = (q) => `Q${q.slice(5)} ’${q.slice(2, 4)}`;
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const roleVar = (role) => (role === "seller" ? "var(--seller)" : "var(--buyer)");
const METHOD_LABEL = { reported: "As filed", ytd_diff: "YTD difference", q4_derived: "10-K minus 9 months" };
const METRIC_LABEL = { revenue: "Revenue", capex: "Capex", capex_finance_leases: "Finance leases", opex: "Opex" };
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

// ───────── Tooltip ─────────
const tipEl = document.getElementById("tip");
const tip = {
  show(html, e) {
    tipEl.innerHTML = html;
    tipEl.setAttribute("data-show", "");
    const pad = 14;
    const r = tipEl.getBoundingClientRect();
    let x = e.clientX + pad;
    let y = e.clientY + pad;
    if (x + r.width > innerWidth - 8) x = e.clientX - r.width - pad;
    if (y + r.height > innerHeight - 8) y = e.clientY - r.height - pad;
    tipEl.style.left = `${x}px`;
    tipEl.style.top = `${y}px`;
  },
  hide() { tipEl.removeAttribute("data-show"); },
};
const tipRows = (rows) => rows.map(([a, b]) => `<div class="row"><span>${a}</span><span>${b}</span></div>`).join("");

// ───────── SVG chart helpers (hand-written, no chart library) ─────────
const NS = "http://www.w3.org/2000/svg";
function niceStep(max, n = 4) {
  const raw = max / n;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const f = raw / mag;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * mag;
}
// Bar with only the data end rounded (2px), anchored to the baseline.
function barPath(x, y0, w, y1) {
  const up = y1 < y0;
  const r = Math.min(2, Math.abs(y0 - y1), w / 2);
  if (up) return `M${x},${y0}V${y1 + r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 + r}V${y0}Z`;
  return `M${x},${y0}V${y1 - r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 - r}V${y0}Z`;
}

/** Vertical bars over the quarter axis. values may contain null (no filing that quarter). */
function bars(el, { values, color, height = 160, yMax, tipFn, showAxis = true, labelEvery = 1 }) {
  const W = Math.max(200, el.clientWidth);
  const left = showAxis ? 40 : 0, bottom = 22, top = 8;
  const H = height, ih = H - top - bottom, iw = W - left;
  const max = yMax ?? Math.max(...values.filter((v) => v != null)) * 1.1;
  const step = niceStep(max, 3);
  const top_ = Math.ceil(max / step) * step;
  const y = (v) => top + ih - (v / top_) * ih;
  const band = iw / values.length;
  const bw = Math.min(24, band * 0.62);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img">`;
  for (let t = 0; t <= top_ + 1e-9; t += step) {
    s += `<line class="grid" x1="${left}" x2="${W}" y1="${y(t)}" y2="${y(t)}"/>`;
    if (showAxis) s += `<text x="${left - 8}" y="${y(t) + 4}" text-anchor="end">${t === 0 ? "0" : `$${+t.toFixed(1)}B`}</text>`;
  }
  values.forEach((v, i) => {
    const x = left + band * i + (band - bw) / 2;
    if (v != null) s += `<path class="bar" data-i="${i}" d="${barPath(x, y(0), bw, y(v))}" fill="${color}"/>`;
    // Anchor labels to the latest quarter so the last two never collide.
    if ((values.length - 1 - i) % labelEvery === 0) s += `<text x="${x + bw / 2}" y="${H - 6}" text-anchor="middle">${qLabel(Q[i])}</text>`;
    s += `<rect class="hit" data-i="${i}" x="${left + band * i}" y="${top}" width="${band}" height="${ih}"/>`;
  });
  s += `</svg>`;
  el.innerHTML = s;
  el.classList.add("chart");
  wireHover(el, tipFn);
}

function wireHover(el, tipFn) {
  if (!tipFn) return;
  const barsEls = [...el.querySelectorAll(".bar")];
  el.querySelectorAll(".hit").forEach((h) => {
    const i = +h.dataset.i;
    h.addEventListener("pointermove", (e) => {
      barsEls.forEach((b) => b.classList.toggle("dim", +b.dataset.i !== i));
      tip.show(tipFn(i), e);
    });
    h.addEventListener("pointerleave", () => { barsEls.forEach((b) => b.classList.remove("dim")); tip.hide(); });
  });
}

function sparkline(values, color, w = 64, h = 20) {
  const pts = values.map((v, i) => [i, v]).filter(([, v]) => v != null);
  const max = Math.max(...pts.map(([, v]) => v)), min = Math.min(...pts.map(([, v]) => v));
  const x = (i) => (i / (values.length - 1)) * (w - 2) + 1;
  const y = (v) => h - 2 - ((v - min) / (max - min || 1)) * (h - 4);
  const d = pts.map(([i, v], k) => `${k ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><path d="${d}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/></svg>`;
}

const combinedTip = (group, metricFn, title) => (i) => {
  const rows = group
    .map((c) => [c.ticker, metricFn(c.ticker, Q[i])])
    .filter(([, v]) => v != null)
    .sort((a, b) => b[1] - a[1])
    .map(([t, v]) => [t, fmtB(v)]);
  const total = sum(group.map((c) => metricFn(c.ticker, Q[i])));
  return `<div class="tip-title">${title} ${qLabel(Q[i])}: ${fmtB(total)}</div>${tipRows(rows)}`;
};

// ───────── Variant 1: Report (editorial, stat-led, scroll) ─────────
function report(stage) {
  const combined = Q.map((q) => sum(BUYERS.map((c) => capex(c.ticker, q))));
  const total = ttm(combined);
  const growth = pct(total, prevTtm(combined));
  const capexMax = Math.max(...BUYERS.flatMap((c) => series(c.ticker, "capex").filter((v) => v != null))) * 1.08;
  const revMax = Math.max(...SELLERS.flatMap((c) => series(c.ticker, "revenue").filter((v) => v != null))) * 1.08;

  const tableRows = COS.map((c) => {
    const rev = series(c.ticker, "revenue"), cx = series(c.ticker, "capex");
    const derived = D.facts.filter((f) => f.ticker === c.ticker && f.method !== "reported").length;
    return `<tr>
      <td><strong>${c.ticker}</strong> <span class="muted">${c.name}</span></td>
      <td><span class="swatch ${c.role === "seller" ? "seller" : "buyer"}"></span>${c.role === "seller" ? "Seller" : "Buyer"}</td>
      <td class="r">${fmtB(ttm(rev))}</td>
      <td class="r">${fmtB(ttm(cx))}</td>
      <td class="r">${fmtPct((ttm(cx) / ttm(rev)) * 100, false)}</td>
      <td class="r">${c.listedFrom ? "–" : fmtPct(pct(ttm(cx), prevTtm(cx)))}</td>
      <td>${sparkline(cx, roleVar(c.role))}</td>
      <td class="r muted">${derived}</td>
    </tr>`;
  }).join("");

  stage.innerHTML = `
  <header class="mast"><div class="wrap">
    <span class="wordmark">Capex Ledger</span>
    <nav><a href="#r-buyers">Buyers</a><a href="#r-sellers">Sellers</a><a href="#r-table">Table</a><a href="#r-method">Method</a></nav>
  </div></header>
  <div class="wrap">
    <section class="report-hero">
      <div>
        <div class="hero-figure num">${fmtB(total)}</div>
        <h1 class="hero-head">Four quarters of AI buildout spending.</h1>
        <p class="hero-sub">Seven buyers' capital spending, read from their 10-Q and 10-K filings and lined up by calendar quarter. ${fmtPct(growth)} on the four quarters before.</p>
        <div class="hero-actions"><a class="btn" href="#r-method">Read the method</a></div>
      </div>
      <div><div id="r-hero-chart"></div><p class="caption">Combined capex by calendar quarter. Hover a bar for each company's share.</p></div>
    </section>

    <section class="section" id="r-buyers">
      <div class="section-head"><h2>Each buyer, on one scale</h2>
        <p class="muted">Same y-axis for all seven, so a short bar means a small spender. CoreWeave starts when it listed.</p></div>
      <div class="multiples">${BUYERS.map((c) => {
        const cx = series(c.ticker, "capex"), rev = series(c.ticker, "revenue");
        return `<div class="multiple"><h3>${c.name}</h3>
          <div class="stat"><span>${fmtB(ttm(cx))} last 4Q</span><span>${fmtPct((ttm(cx) / ttm(rev)) * 100, false)} of revenue</span></div>
          <div data-mult="${c.ticker}"></div></div>`;
      }).join("")}</div>
    </section>

    <section class="section" id="r-sellers">
      <div class="section-head"><h2>The sellers' side</h2>
        <p class="muted">Revenue at the three chip and memory makers, on one shared scale.</p></div>
      <div class="multiples">${SELLERS.map((c) => {
        const rev = series(c.ticker, "revenue");
        return `<div class="multiple"><h3>${c.name}</h3>
          <div class="stat"><span>${fmtB(ttm(rev))} last 4Q</span><span>${fmtPct(pct(ttm(rev), prevTtm(rev)))} year on year</span></div>
          <div data-sell="${c.ticker}"></div></div>`;
      }).join("")}</div>
    </section>

    <section class="section" id="r-table">
      <div class="section-head"><h2>All ten, last four quarters</h2>
        <p class="muted">Derived counts how many of a company's figures were computed rather than read straight off a filing.</p></div>
      <div class="table-scroll"><table>
        <thead><tr><th>Company</th><th>Role</th><th class="r">Revenue</th><th class="r">Capex</th><th class="r">Capex / revenue</th><th class="r">Capex vs prior year</th><th>Capex, 8Q</th><th class="r">Derived</th></tr></thead>
        <tbody>${tableRows}</tbody>
      </table></div>
    </section>

    <section class="section" id="r-method">
      <div class="section-head"><h2>How each number was made</h2>
        <p class="muted">Every figure carries its filing, its XBRL tag and one of three methods.</p></div>
      <dl class="methods">
        ${Object.entries(D.meta.methods).map(([k, v]) => `<div><dt>${METHOD_LABEL[k]}</dt><dd>${v}</dd></div>`).join("")}
        ${D.pending.map((p) => `<div><dt>Not yet in the data: ${p.name}</dt><dd>${p.reason}</dd></div>`).join("")}
      </dl>
    </section>
    <footer class="foot">Capex Ledger. Source: SEC EDGAR XBRL company facts (part 2). Sample data, generated ${D.meta.generated}.</footer>
  </div>`;

  bars(stage.querySelector("#r-hero-chart"), { values: combined, color: "var(--buyer)", height: 300, tipFn: combinedTip(BUYERS, (t, q) => capex(t, q), "Capex") });
  stage.querySelectorAll("[data-mult]").forEach((el) => {
    const t = el.dataset.mult;
    bars(el, { values: series(t, "capex"), color: "var(--buyer)", height: 120, yMax: capexMax, labelEvery: 4,
      tipFn: (i) => { const f = fact(t, "capex", Q[i]); return f ? `<div class="tip-title">${t} ${qLabel(Q[i])}</div>${tipRows([["Capex", fmtB(f.value)], ["Revenue", fmtB(val(t, "revenue", Q[i]))]])}<div class="sub">${f.fiscal}, ${METHOD_LABEL[f.method].toLowerCase()}</div>` : `<div class="tip-title">${t} ${qLabel(Q[i])}</div>Not listed yet`; } });
  });
  stage.querySelectorAll("[data-sell]").forEach((el) => {
    const t = el.dataset.sell;
    bars(el, { values: series(t, "revenue"), color: "var(--seller)", height: 120, yMax: revMax, labelEvery: 4,
      tipFn: (i) => { const f = fact(t, "revenue", Q[i]); return `<div class="tip-title">${t} ${qLabel(Q[i])}</div>${tipRows([["Revenue", fmtB(f.value)]])}<div class="sub">${f.fiscal}, ${METHOD_LABEL[f.method].toLowerCase()}</div>`; } });
  });
}

// ───────── Variant 2: Desk (dense analyst workbench, lineage first) ─────────
let deskTicker = "MSFT";
let deskLeases = false;
function desk(stage) {
  const railRow = (c) => {
    const cx = series(c.ticker, "capex");
    const metric = c.role === "seller" ? series(c.ticker, "revenue") : cx;
    return `<button class="rail-item" data-t="${c.ticker}" ${c.ticker === deskTicker ? 'aria-current="true"' : ""}>
      <span class="tk">${c.ticker}</span><span class="nm">${c.name}</span>
      <span class="v">${sparkline(metric, roleVar(c.role), 60, 18)}</span></button>`;
  };
  stage.innerHTML = `
  <header class="mast"><div class="wrap" style="max-width:none">
    <span class="wordmark">Capex Ledger</span>
    <nav><span class="muted">Use ↑ ↓ to move through companies</span></nav>
  </div></header>
  <div class="desk">
    <aside class="rail" aria-label="Companies">
      <div class="rail-group">Buyers, by capex</div>${BUYERS.map(railRow).join("")}
      <div class="rail-group">Sellers, by revenue</div>${SELLERS.map(railRow).join("")}
      <div class="rail-group">Pending</div>${D.pending.map((p) => `<button class="rail-item" disabled title="${p.reason}"><span class="tk">${p.ticker}</span><span class="nm">${p.name}</span><span class="v muted">no filings</span></button>`).join("")}
    </aside>
    <section class="desk-main" id="desk-main"></section>
  </div>`;

  const main = stage.querySelector("#desk-main");
  function draw() {
    const c = COS.find((x) => x.ticker === deskTicker);
    const hasLeases = D.facts.some((f) => f.ticker === c.ticker && f.metric === "capex_finance_leases");
    const L = hasLeases && deskLeases;
    const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const metrics = [
      { key: "revenue", label: "Revenue", values: series(c.ticker, "revenue"), color: c.role === "seller" ? "var(--seller)" : "var(--muted)" },
      { key: "capex", label: L ? "Capex incl. finance leases" : "Capex", values: Q.map((q) => capex(c.ticker, q, L)), color: c.role === "spender" ? "var(--buyer)" : "var(--muted)" },
      { key: "opex", label: "Opex", values: series(c.ticker, "opex"), color: "var(--muted)" },
    ];
    const rows = D.facts
      .filter((f) => f.ticker === c.ticker && (f.metric !== "capex_finance_leases" || L))
      .sort((a, b) => (a.calQ < b.calQ ? 1 : a.calQ > b.calQ ? -1 : a.metric.localeCompare(b.metric)));
    main.innerHTML = `
      <div class="desk-head">
        <div><h1>${c.name}</h1>
          <div class="meta"><span>${c.ticker}</span>, <span>CIK ${c.cik}</span>, <span>fiscal year ends ${months[c.fyEnd - 1]}</span>${c.listedFrom ? `, <span>listed ${qLabel(c.listedFrom)}</span>` : ""}</div></div>
        ${hasLeases ? `<label class="toggle"><input type="checkbox" id="lease" ${L ? "checked" : ""}> Include finance leases in capex</label>` : ""}
      </div>
      <div class="trio">${metrics.map((m, k) => {
        const last = m.values.at(-1), yoy = pct(last, m.values.at(-5));
        return `<div><h3>${m.label}</h3><div class="big num">${fmtB(last)}</div>
          <div class="delta">${qLabel(Q.at(-1))}, ${fmtPct(yoy)} on ${qLabel(Q.at(-5))}</div><div data-k="${k}"></div></div>`;
      }).join("")}</div>
      <div class="facts-head"><h2>Every figure and where it came from</h2><span class="muted small">${rows.length} facts</span></div>
      <div class="table-scroll"><table class="facts">
        <thead><tr><th>Quarter</th><th>Fiscal</th><th>Metric</th><th class="r">Value</th><th>Form</th><th>XBRL tag</th><th>Method</th><th>Accession</th></tr></thead>
        <tbody>${rows.map((f) => `<tr>
          <td>${qLabel(f.calQ)}</td><td class="muted">${f.fiscal}</td><td>${METRIC_LABEL[f.metric]}</td>
          <td class="r">${fmtB(f.value)}</td><td>${f.form}</td><td><code>${f.tag}</code></td>
          <td><span class="method" data-m="${f.method}" title="${D.meta.methods[f.method]}">${METHOD_LABEL[f.method]}</span></td>
          <td><code class="muted">${f.accession}</code></td></tr>`).join("")}</tbody>
      </table></div>`;
    main.querySelectorAll("[data-k]").forEach((el) => {
      const m = metrics[+el.dataset.k];
      bars(el, { values: m.values, color: m.color, height: 130, labelEvery: 2,
        tipFn: (i) => { const f = fact(c.ticker, m.key, Q[i]); return f ? `<div class="tip-title">${m.label} ${qLabel(Q[i])}</div>${tipRows([["Value", fmtB(m.values[i])], ["Form", f.form]])}<div class="sub">${f.fiscal}, ${METHOD_LABEL[f.method].toLowerCase()}</div>` : `<div class="tip-title">${qLabel(Q[i])}</div>No filing`; } });
    });
    main.querySelector("#lease")?.addEventListener("change", (e) => { deskLeases = e.target.checked; draw(); });
  }
  function select(t) {
    deskTicker = t;
    stage.querySelectorAll(".rail-item[data-t]").forEach((b) => (b.dataset.t === t ? b.setAttribute("aria-current", "true") : b.removeAttribute("aria-current")));
    draw();
  }
  stage.querySelectorAll(".rail-item[data-t]").forEach((b) => b.addEventListener("click", () => select(b.dataset.t)));
  const order = [...BUYERS, ...SELLERS].map((c) => c.ticker);
  const onKey = (e) => {
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.metaKey || e.ctrlKey || e.altKey) return;
    const i = order.indexOf(deskTicker);
    if (e.key === "ArrowDown") { e.preventDefault(); select(order[(i + 1) % order.length]); }
    if (e.key === "ArrowUp") { e.preventDefault(); select(order[(i - 1 + order.length) % order.length]); }
  };
  document.addEventListener("keydown", onKey);
  draw();
  return () => document.removeEventListener("keydown", onKey);
}

// ───────── Variant 3: Mirror (one argument: spend vs. booked revenue) ─────────
function mirror(stage) {
  const up = Q.map((q) => sum(SELLERS.map((c) => val(c.ticker, "revenue", q))));
  const down = Q.map((q) => sum(BUYERS.map((c) => capex(c.ticker, q))));
  stage.innerHTML = `
  <header class="mast"><div class="wrap"><span class="wordmark">Capex Ledger</span>
    <nav><a href="#m-chart">The mirror</a><a href="#m-slope">Intensity</a></nav></div></header>
  <div class="wrap">
    <section class="mirror-hero">
      <h1>Buyers spend it. Sellers book it.</h1>
      <p>Seven buyers' capital spending below the line, three chip and memory makers' revenue above it. Same dollars, one axis, eight quarters.</p>
    </section>
    <section id="m-chart" style="padding-bottom:40px">
      <div class="legend"><span><span class="swatch seller"></span>Sellers' revenue (Nvidia, AMD, Micron)</span><span><span class="swatch buyer"></span>Buyers' capex (seven companies)</span></div>
      <div id="mirror-chart"></div>
      <p class="caption">Totals, not transactions. Filings don't say who buys from whom, and not all capex is AI: buildings and land count too. The gap between the two sides is the story to test in part 2.</p>
    </section>
    <section class="section" id="m-slope">
      <div class="slope-wrap">
        <div><h2 style="font-size:28px;line-height:1.2">Capex as a share of revenue</h2>
          <p class="muted" style="margin-top:12px">How much of each dollar earned goes back into building. First quarter on the left, latest on the right. The steepest climb is in colour.</p>
          <p class="muted small" style="margin-top:12px">CoreWeave is left out: its capex runs at about three times its revenue, which would flatten the other six.</p></div>
        <div id="slope-chart" class="chart"></div>
      </div>
    </section>
    <footer class="foot">Sample data. Real figures arrive with the EDGAR pipeline.</footer>
  </div>`;

  // Mirror chart: diverging from a zero line, symmetric scale.
  const el = stage.querySelector("#mirror-chart");
  const W = Math.max(320, el.clientWidth), H = 420, left = 52, top = 10, bottom = 10, xLab = 26;
  const max = Math.max(...up, ...down) * 1.08;
  const step = niceStep(max, 3), lim = Math.ceil(max / step) * step;
  const mid = top + (H - top - bottom - xLab) / 2, half = (H - top - bottom - xLab) / 2;
  const y = (v) => mid - (v / lim) * half;
  const band = (W - left) / Q.length, bw = Math.min(28, band * 0.55);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Sellers' revenue above zero, buyers' capex below, by quarter">`;
  for (let t = -lim; t <= lim + 1e-9; t += step) {
    s += `<line class="grid" x1="${left}" x2="${W}" y1="${y(t)}" y2="${y(t)}" ${t === 0 ? 'style="stroke:var(--ink)"' : ""}/>`;
    s += `<text x="${left - 8}" y="${y(t) + 4}" text-anchor="end">${t === 0 ? "0" : `$${Math.abs(t)}B`}</text>`;
  }
  Q.forEach((q, i) => {
    const x = left + band * i + (band - bw) / 2;
    s += `<path class="bar" data-i="${i}" d="${barPath(x, y(0), bw, y(up[i]))}" fill="var(--seller)"/>`;
    s += `<path class="bar" data-i="${i}" d="${barPath(x, y(0), bw, y(-down[i]))}" fill="var(--buyer)"/>`;
    s += `<text x="${x + bw / 2}" y="${H - 6}" text-anchor="middle">${qLabel(q)}</text>`;
    s += `<rect class="hit" data-i="${i}" x="${left + band * i}" y="${top}" width="${band}" height="${H - top - xLab}"/>`;
  });
  // Direct labels on the latest quarter only.
  const lx = left + band * (Q.length - 1) + band / 2;
  s += `<text x="${lx}" y="${y(up.at(-1)) - 8}" text-anchor="middle" style="fill:var(--ink)">${fmtB(up.at(-1))}</text>`;
  s += `<text x="${lx}" y="${y(-down.at(-1)) + 16}" text-anchor="middle" style="fill:var(--ink)">${fmtB(down.at(-1))}</text>`;
  el.innerHTML = s + "</svg>";
  el.classList.add("chart");
  wireHover(el, (i) => {
    const sellers = combinedTip(SELLERS, (t, q) => val(t, "revenue", q), "Sellers' revenue")(i);
    const buyers = combinedTip(BUYERS, (t, q) => capex(t, q), "Buyers' capex")(i);
    return `${sellers}<div style="height:8px"></div>${buyers}`;
  });

  // Slope chart: capex / revenue, first quarter vs latest, per buyer.
  const sl = stage.querySelector("#slope-chart");
  const SW = Math.max(320, sl.clientWidth), SH = 340, padX = 90, padY = 24;
  // CoreWeave's capex runs ~3x its revenue; on the same scale it flattens everyone else.
  const pts = BUYERS.filter((c) => c.ticker !== "CRWV").map((c) => {
    const firstQ = Q.find((q) => val(c.ticker, "revenue", q) != null);
    return { c, firstQ, a: capex(c.ticker, firstQ) / val(c.ticker, "revenue", firstQ), b: capex(c.ticker, Q.at(-1)) / val(c.ticker, "revenue", Q.at(-1)) };
  });
  const smax = Math.max(...pts.flatMap((p) => [p.a, p.b])) * 1.1;
  const sy = (v) => SH - padY - (v / smax) * (SH - padY * 2);
  const x0 = padX, x1 = SW - padX;
  const lead = pts.reduce((m, p) => (p.b - p.a > m.b - m.a ? p : m));
  // Spread labels so none sit closer than 16px; marks stay at their true values.
  const spread = (key) => {
    const ord = [...pts].sort((p, q) => sy(q[key]) - sy(p[key]));
    let last = Infinity;
    ord.forEach((p) => { const y = Math.min(sy(p[key]), last - 16); p[key + "L"] = y; last = y; });
  };
  spread("a"); spread("b");
  let ss = `<svg viewBox="0 0 ${SW} ${SH}" width="${SW}" height="${SH}" role="img" aria-label="Capex as share of revenue, first versus latest quarter">`;
  ss += `<line class="grid" x1="${x0}" x2="${x0}" y1="${padY}" y2="${SH - padY}"/><line class="grid" x1="${x1}" x2="${x1}" y1="${padY}" y2="${SH - padY}"/>`;
  ss += `<text x="${x0}" y="${padY - 8}" text-anchor="middle">${qLabel(Q[0])}</text><text x="${x1}" y="${padY - 8}" text-anchor="middle">${qLabel(Q.at(-1))}</text>`;
  pts.sort((p, q) => (p === lead) - (q === lead)).forEach((p) => {
    const hot = p === lead, col = hot ? "var(--buyer)" : "var(--muted)";
    ss += `<line x1="${x0}" y1="${sy(p.a)}" x2="${x1}" y2="${sy(p.b)}" stroke="${col}" stroke-width="${hot ? 2.5 : 1.5}" opacity="${hot ? 1 : 0.6}"/>`;
    ss += `<circle cx="${x0}" cy="${sy(p.a)}" r="3.5" fill="${col}"/><circle cx="${x1}" cy="${sy(p.b)}" r="3.5" fill="${col}"/>`;
    ss += `<text x="${x0 - 10}" y="${p.aL + 4}" text-anchor="end" ${hot ? 'style="fill:var(--ink);font-weight:600"' : ""}>${p.c.ticker} ${Math.round(p.a * 100)}%</text>`;
    ss += `<text x="${x1 + 10}" y="${p.bL + 4}" ${hot ? 'style="fill:var(--ink);font-weight:600"' : ""}>${Math.round(p.b * 100)}% ${p.c.ticker}</text>`;
  });
  sl.innerHTML = ss + "</svg>";
}

// ───────── Picker harness (wiring from the prototype skill's PICKER.md, plus unmount cleanup) ─────────
const variants = [report, desk, mirror];
const stage = document.getElementById("stage");
const picker = document.querySelector(".proto-picker");
const highlight = picker.querySelector(".proto-picker-highlight");
const items = [...picker.querySelectorAll(".proto-picker-item:not(.proto-picker-replay)")];
let current = 0;
let unmount = null;

function moveHighlight() {
  const el = items[current];
  highlight.style.width = el.offsetWidth + "px";
  highlight.style.transform = `translateX(${el.offsetLeft}px)`;
}
function mount(i) {
  unmount?.(); unmount = null;
  tip.hide();
  stage.innerHTML = "";
  requestAnimationFrame(() => { unmount = variants[i](stage) ?? null; });
}
function setActive(i) {
  if (i < 0 || i >= variants.length) return;
  current = i;
  items.forEach((el, j) => {
    el.toggleAttribute("data-active", j === i);
    if (j === i) el.setAttribute("aria-current", "true");
    else el.removeAttribute("aria-current");
  });
  moveHighlight();
  const url = new URL(location);
  url.searchParams.set("v", i + 1);
  history.replaceState(null, "", url);
  window.scrollTo(0, 0);
  mount(i);
}
items.forEach((el, i) => el.addEventListener("click", () => setActive(i)));
let rz;
window.addEventListener("resize", () => { moveHighlight(); clearTimeout(rz); rz = setTimeout(() => mount(current), 200); });
document.addEventListener("keydown", (e) => {
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.target.isContentEditable) return;
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const num = parseInt(e.key, 10);
  if (num >= 1 && num <= variants.length) setActive(num - 1);
  else if (e.key === "ArrowRight") setActive((current + 1) % variants.length);
  else if (e.key === "ArrowLeft") setActive((current - 1 + variants.length) % variants.length);
  else if (e.key === "r" || e.key === "R") mount(current);
});
setActive((parseInt(new URLSearchParams(location.search).get("v"), 10) || 1) - 1);
requestAnimationFrame(() => requestAnimationFrame(() => picker.setAttribute("data-ready", "")));
