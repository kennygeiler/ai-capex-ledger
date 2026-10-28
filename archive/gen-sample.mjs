// Writes data/sample.json: stub data in contract v2, the shape the EDGAR pipeline
// (plan step 1-2) must produce. Values are invented, rough-magnitude placeholders.
// Run: node scripts/gen-sample.mjs
import { writeFileSync, mkdirSync } from "node:fs";

const QUARTERS = ["2024Q3", "2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2"];
const B = 1e9;

// role: "buyer" (capex story) | "seller" (data-center revenue story)
// fyEnd: fiscal-year-end month. flags: "not_ai_core" (hidden by default), "segment_not_ai" (partial seller).
// series: [start, end] per quarter in $B; shape: optional per-quarter multipliers to plant signals.
const COMPANIES = [
  { ticker: "MSFT", name: "Microsoft", cik: "0000789019", role: "buyer", fyEnd: 6,
    revenue: [65, 80], capex: [20, 33], ocf: [34, 44], rou: [4.5, 9], revTag: "RevenueFromContractWithCustomerExcludingAssessedTax" },
  { ticker: "GOOGL", name: "Alphabet", cik: "0001652044", role: "buyer", fyEnd: 12,
    revenue: [88, 104], capex: [13, 26], ocf: [30, 38], revTag: "RevenueFromContractWithCustomerExcludingAssessedTax" },
  { ticker: "AMZN", name: "Amazon", cik: "0001018724", role: "buyer", fyEnd: 12,
    revenue: [158, 184], capex: [25, 36], ocf: [26, 34], rou: [1.5, 2.5], revTag: "RevenueFromContractWithCustomerExcludingAssessedTax",
    shape: { capex: [1, 1, 1, 1, 1, 0.9, 1, 1] } }, // a QoQ dip to show a rollover cell
  { ticker: "META", name: "Meta", cik: "0001326801", role: "buyer", fyEnd: 12,
    revenue: [40, 50], capex: [9, 20], ocf: [24, 28], revTag: "Revenues",
    shape: { capex: [1, 1, 1, 1, 1.05, 1.08, 1, 0.94] } }, // growth slowing late
  { ticker: "ORCL", name: "Oracle", cik: "0001341439", role: "buyer", fyEnd: 5,
    revenue: [13.3, 17], capex: [2.8, 10], ocf: [5, 6], rou: [0.3, 1.8], revTag: "RevenueFromContractWithCustomerExcludingAssessedTax" },
  { ticker: "CRWV", name: "CoreWeave", cik: "0001769628", role: "buyer", fyEnd: 12, listedFrom: "2025Q1",
    revenue: [1.0, 2.2], capex: [3.0, 6.5], ocf: [0.6, 1.2], rou: [0.4, 0.9], revTag: "Revenues" },
  { ticker: "TSLA", name: "Tesla", cik: "0001318605", role: "buyer", fyEnd: 12, flags: ["not_ai_core"],
    revenue: [25, 24], capex: [2.3, 2.6], ocf: [3.0, 3.2], revTag: "Revenues" },
  { ticker: "NVDA", name: "Nvidia", cik: "0001045810", role: "seller", fyEnd: 1,
    revenue: [30, 58], dc: [26, 51], revTag: "Revenues", dcMember: "nvda:DataCenterMember" },
  { ticker: "AMD", name: "AMD", cik: "0000002488", role: "seller", fyEnd: 12,
    revenue: [6.8, 8.8], dc: [3.5, 4.8], revTag: "RevenueFromContractWithCustomerExcludingAssessedTax", dcMember: "amd:DataCenterSegmentMember" },
  { ticker: "MU", name: "Micron", cik: "0000723125", role: "seller", fyEnd: 8,
    revenue: [7.7, 11], dc: [3.0, 6.0], revTag: "RevenueFromContractWithCustomerExcludingAssessedTax", dcMember: "mu:CloudMemoryBusinessUnitMember" },
  { ticker: "AVGO", name: "Broadcom", cik: "0001730168", role: "seller", fyEnd: 10, flags: ["segment_not_ai"],
    revenue: [13, 17], dc: [7.3, 10.5], revTag: "RevenueFromContractWithCustomerExcludingAssessedTax", dcMember: "avgo:SemiconductorSolutionsMember" },
];

const PENDING = [{ ticker: "SPACEX", name: "SpaceX", role: "buyer", reason: "No 10-Q or 10-K on EDGAR as of this stub. Plan step 2 checks again." }];

const TAGS = {
  capex: "PaymentsToAcquirePropertyPlantAndEquipment",
  ocf: "NetCashProvidedByUsedInOperatingActivities",
  rou: "RightOfUseAssetObtainedInExchangeForFinanceLeaseLiability",
};

let seed = 7;
const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);

const qEnd = (cq) => { const y = +cq.slice(0, 4), q = +cq.slice(5); return new Date(Date.UTC(y, q * 3, 0)); };
const iso = (d) => d.toISOString().slice(0, 10);
function fiscalOf(cq, fyEnd) {
  const y = +cq.slice(0, 4), endMonth = +cq.slice(5) * 3;
  const monthsIn = ((endMonth - fyEnd + 11) % 12) + 1;
  return { fp: `Q${Math.ceil(monthsIn / 3)}`, fy: fyEnd === 12 || endMonth <= fyEnd ? y : y + 1 };
}

const facts = [];
let n = 0;
for (const c of COMPANIES) {
  QUARTERS.forEach((cq, i) => {
    if (c.listedFrom && cq < c.listedFrom) return;
    const t = i / (QUARTERS.length - 1);
    const lerp = ([a, b]) => a + (b - a) * t;
    const { fp, fy } = fiscalOf(cq, c.fyEnd);
    const end = qEnd(cq), start = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth() - 2, 1));
    const filed = new Date(end.getTime() + (fp === "Q4" ? 58 : 38) * 864e5);
    const form = fp === "Q4" ? "10-K" : "10-Q";
    const acc = `SAMPLE-${c.cik.slice(-7)}-${cq.slice(2, 4)}-${String(100 + i).padStart(6, "0")}`;
    const prevAcc = `SAMPLE-${c.cik.slice(-7)}-${QUARTERS[Math.max(0, i - 1)].slice(2, 4)}-${String(99 + i).padStart(6, "0")}`;
    const base = { ticker: c.ticker, calQ: cq, periodStart: iso(start), periodEnd: iso(end), fy, fp, form, accession: acc, filed: iso(filed), unit: "USD" };

    // Flow items from the cash-flow statement are YTD in 10-Qs; Q4 comes from the 10-K.
    const flowMethod = fp === "Q4" ? "q4_derived" : fp === "Q1" ? "reported" : "ytd_diff";
    const derivedFrom = (v) =>
      flowMethod === "reported" ? [] :
      flowMethod === "ytd_diff" ? [{ accession: acc, span: "YTD to this quarter", value: Math.round(v * 2.1) }, { accession: prevAcc, span: "YTD to prior quarter", value: Math.round(v * 1.1) }] :
      [{ accession: acc, span: "Full fiscal year (10-K)", value: Math.round(v * 3.9) }, { accession: prevAcc, span: "Nine months (prior 10-Q)", value: Math.round(v * 2.9) }];

    const add = (metric, valB, tag, method, extra = {}) => {
      const value = Math.round(valB * B);
      facts.push({ id: `f${++n}`, ...base, metric, value, tag, dimension: null, method, derivedFrom: method === "reported" ? [] : derivedFrom(value), ...extra });
    };
    const mult = (k) => c.shape?.[k]?.[i] ?? 1;

    add("revenue", lerp(c.revenue) * (0.97 + rand() * 0.06), c.revTag, fp === "Q4" ? "q4_derived" : "reported");
    if (c.capex) add("capex", lerp(c.capex) * mult("capex") * (0.95 + rand() * 0.1), TAGS.capex, flowMethod);
    if (c.ocf) add("ocf", lerp(c.ocf) * (0.9 + rand() * 0.2), TAGS.ocf, flowMethod);
    if (c.rou) add("lease_rou", lerp(c.rou) * (0.85 + rand() * 0.3), TAGS.rou, flowMethod);
    if (c.dc) add("revenue_dc", lerp(c.dc) * (0.96 + rand() * 0.08), c.revTag, fp === "Q4" ? "q4_derived" : "reported",
      { dimension: { axis: c.ticker === "NVDA" ? "srt:ProductOrServiceAxis" : "us-gaap:StatementBusinessSegmentsAxis", member: c.dcMember } });
  });
}

const out = {
  meta: {
    contract: "v2",
    sample: true,
    note: "Invented placeholder values in contract v2 shape. Not real figures.",
    generated: new Date().toISOString().slice(0, 10),
    unit: "USD (whole dollars)",
    quarters: QUARTERS,
    calendarRule: "A fact belongs to the calendar quarter that contains its period-end date.",
    methods: {
      reported: "Taken as filed for that quarter.",
      ytd_diff: "Cash-flow lines are year-to-date in 10-Qs; this quarter = YTD minus the prior quarter's YTD.",
      q4_derived: "No 10-Q for Q4; this quarter = 10-K full year minus the first nine months.",
    },
    metrics: {
      revenue: "Total revenue.",
      revenue_dc: "Data-center segment revenue (sellers). Broadcom's is its whole semiconductor segment, which is wider than AI.",
      capex: "Cash paid for property and equipment.",
      lease_rou: "New finance-lease assets signed this quarter (non-cash). Shown as its own layer, never folded into capex silently.",
      ocf: "Cash from operations.",
    },
    notCovered: ["Foundry (TSMC files no quarterly XBRL)", "Networking", "Power and cooling", "Construction and land", "Timing between order and delivery"],
  },
  companies: COMPANIES.map(({ ticker, name, cik, role, fyEnd, listedFrom, flags }) => ({ ticker, name, cik, role, fyEnd, listedFrom: listedFrom ?? null, flags: flags ?? [] })),
  pending: PENDING,
  facts,
};

mkdirSync(new URL("../data/", import.meta.url), { recursive: true });
writeFileSync(new URL("../data/sample.json", import.meta.url), JSON.stringify(out, null, 1));
console.log(`wrote ${facts.length} facts for ${COMPANIES.length} companies (contract v2)`);
