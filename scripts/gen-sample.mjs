// Writes data/sample.json: stub data in the exact shape part 2 (the EDGAR pipeline)
// must produce. Values are invented, rough-magnitude placeholders for layout work.
// Run: node scripts/gen-sample.mjs
import { writeFileSync, mkdirSync } from "node:fs";

// Calendar quarters shown in the UI (8 quarters).
const QUARTERS = ["2024Q3", "2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2"];

// role: "spender" = buys AI infrastructure (capex story); "seller" = sells into it (revenue story).
// fyEnd: fiscal-year-end month (1-12). Used to label fiscal quarters and pick the derivation method.
// start/end: [revenue, capex] per quarter in $B at first and last quarter; linear + noise in between.
const COMPANIES = [
  { ticker: "MSFT", name: "Microsoft", cik: "0000789019", role: "spender", fyEnd: 6, revTag: "RevenueFromContractWithCustomerExcludingAssessedTax", start: [65, 20], end: [80, 33], leases: 0.35, opexRatio: 0.18 },
  { ticker: "GOOGL", name: "Alphabet", cik: "0001652044", role: "spender", fyEnd: 12, revTag: "RevenueFromContractWithCustomerExcludingAssessedTax", start: [88, 13], end: [104, 26], leases: 0, opexRatio: 0.26 },
  { ticker: "AMZN", name: "Amazon", cik: "0001018724", role: "spender", fyEnd: 12, revTag: "RevenueFromContractWithCustomerExcludingAssessedTax", start: [158, 25], end: [184, 36], leases: 0.12, opexRatio: 0.9 },
  { ticker: "META", name: "Meta", cik: "0001326801", role: "spender", fyEnd: 12, revTag: "Revenues", start: [40, 9], end: [50, 20], leases: 0, opexRatio: 0.38 },
  { ticker: "ORCL", name: "Oracle", cik: "0001341439", role: "spender", fyEnd: 5, revTag: "RevenueFromContractWithCustomerExcludingAssessedTax", start: [13.3, 2.8], end: [17, 10], leases: 0, opexRatio: 0.55 },
  { ticker: "CRWV", name: "CoreWeave", cik: "0001769628", role: "spender", fyEnd: 12, revTag: "Revenues", start: [1.0, 3.0], end: [2.2, 6.5], leases: 0, opexRatio: 0.7, listedFrom: "2025Q1" },
  { ticker: "TSLA", name: "Tesla", cik: "0001318605", role: "spender", fyEnd: 12, revTag: "Revenues", start: [25, 2.3], end: [24, 2.6], leases: 0, opexRatio: 0.12 },
  { ticker: "NVDA", name: "Nvidia", cik: "0001045810", role: "seller", fyEnd: 1, revTag: "Revenues", start: [30, 0.8], end: [58, 1.6], leases: 0, opexRatio: 0.09 },
  { ticker: "AMD", name: "AMD", cik: "0000002488", role: "seller", fyEnd: 12, revTag: "RevenueFromContractWithCustomerExcludingAssessedTax", start: [6.8, 0.15], end: [8.8, 0.25], leases: 0, opexRatio: 0.4 },
  { ticker: "MU", name: "Micron", cik: "0000723125", role: "seller", fyEnd: 8, revTag: "RevenueFromContractWithCustomerExcludingAssessedTax", start: [7.7, 2.0], end: [11, 3.4], leases: 0, opexRatio: 0.13 },
];

// Listed in the UI as pending: no SEC filings found yet (to confirm in part 2).
const PENDING = [{ ticker: "SPACEX", name: "SpaceX", role: "spender", reason: "No 10-Q or 10-K on EDGAR as of this stub. Part 2 checks again." }];

// Deterministic noise so the file is stable between runs.
let seed = 42;
const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const round = (n) => Math.round(n * 100) / 100;

// Which fiscal quarter (1-4) a calendar quarter falls into, given a fiscal-year-end month.
function fiscalOf(calQ, fyEnd) {
  const [y, q] = [Number(calQ.slice(0, 4)), Number(calQ.slice(5))];
  const endMonth = q * 3; // last month of the calendar quarter
  // months since fiscal year start (fiscal year starts the month after fyEnd)
  const monthsIn = ((endMonth - fyEnd + 12 - 1) % 12) + 1; // 1..12
  const fq = Math.ceil(monthsIn / 3);
  const fy = endMonth > fyEnd ? y + 1 : y;
  return { fq, fy: fyEnd === 12 ? y : fy };
}

const facts = [];
for (const c of COMPANIES) {
  QUARTERS.forEach((cq, i) => {
    if (c.listedFrom && cq < c.listedFrom) return;
    const t = i / (QUARTERS.length - 1);
    const lerp = (a, b) => a + (b - a) * t;
    const rev = lerp(c.start[0], c.end[0]) * (0.97 + rand() * 0.06);
    const capex = lerp(c.start[1], c.end[1]) * (0.92 + rand() * 0.16);
    const opex = rev * c.opexRatio * (0.96 + rand() * 0.08);
    const { fq, fy } = fiscalOf(cq, c.fyEnd);
    const isQ4 = fq === 4;
    const form = isQ4 ? "10-K" : "10-Q";
    const accession = `sample-${c.cik}-${cq}`;
    const base = { ticker: c.ticker, calQ: cq, fiscal: `FY${fy} Q${fq}`, form, accession, unit: "USD_B" };
    facts.push({ ...base, metric: "revenue", value: round(rev), tag: c.revTag, method: isQ4 ? "q4_derived" : "reported" });
    facts.push({ ...base, metric: "capex", value: round(capex), tag: "PaymentsToAcquirePropertyPlantAndEquipment", method: isQ4 ? "q4_derived" : fq === 1 ? "reported" : "ytd_diff" });
    if (c.leases) facts.push({ ...base, metric: "capex_finance_leases", value: round(capex * c.leases), tag: "FinanceLeasePrincipalPayments", method: fq === 1 ? "reported" : "ytd_diff" });
    facts.push({ ...base, metric: "opex", value: round(opex), tag: "OperatingExpenses", method: isQ4 ? "q4_derived" : "reported" });
  });
}

const out = {
  meta: {
    sample: true,
    note: "Invented placeholder values. Shape matches the part-2 EDGAR output; numbers are not real.",
    generated: new Date().toISOString().slice(0, 10),
    unit: "USD_B",
    quarters: QUARTERS,
    methods: {
      reported: "Taken as filed for that quarter.",
      ytd_diff: "Cash-flow lines are year-to-date in 10-Qs; this quarter = YTD minus the prior quarter's YTD.",
      q4_derived: "No 10-Q for Q4; this quarter = 10-K full year minus Q1 to Q3.",
    },
  },
  companies: COMPANIES.map(({ ticker, name, cik, role, fyEnd, listedFrom }) => ({ ticker, name, cik, role, fyEnd, listedFrom: listedFrom ?? null })),
  pending: PENDING,
  facts,
};

mkdirSync(new URL("../data/", import.meta.url), { recursive: true });
writeFileSync(new URL("../data/sample.json", import.meta.url), JSON.stringify(out, null, 1));
console.log(`wrote ${facts.length} facts for ${COMPANIES.length} companies`);
