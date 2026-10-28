// Loads the cleaned EDGAR dataset (data/clean/viz.json) and builds the lookups every page uses.
// The standalone build inlines the data as window.__DATA__; the dev server serves /data/clean/viz.json.
/* eslint-disable @typescript-eslint/no-explicit-any */
declare global { interface Window { __DATA__?: any } }

export type Fact = Record<string, any> & {
  id: number; ticker: string; metric: string; period_type: "quarter" | "year"; cal_q?: string; fy_key?: string; value: number; method: string;
}
export type Company = Record<string, any> & { ticker: string; name: string; cik: number; sets: string[]; group: string; sector: string }
export type Issue = { ticker: string; metric: string; cal_q?: string; check: string; severity: "error" | "warn" | "info"; message: string }

const raw: any = window.__DATA__ ?? (await fetch("/data/clean/viz.json").then((r) => r.json()))
export const D = raw
export const FACTS: Fact[] = raw.facts.map((a: any[], i: number) => ({ ...Object.fromEntries(raw.fact_cols.map((c: string, j: number) => [c, a[j]])), id: i }))
export const META = raw.meta, PULL = raw.pull
export const COS: Company[] = raw.companies
export const ISSUES: Issue[] = raw.issues
export const TRACES: Record<string, any> = raw.traces
export const WINDOW: string[] = META.window
export const YEARS: string[] = META.years
export const ALLQ = [...new Set(FACTS.filter((f) => f.period_type === "quarter").map((f) => f.cal_q!))].sort()
export const ALLY = [...new Set(FACTS.filter((f) => f.period_type === "year").map((f) => f.fy_key!))].sort()
export const coBy = new Map(COS.map((c) => [c.ticker, c]))
export const cikBy = new Map(COS.map((c) => [String(c.cik), c.ticker]))
export const pk = (f: Fact) => (f.period_type === "quarter" ? f.cal_q! : f.fy_key!)
export const key = (t: string, m: string, p: string) => `${t}|${m}|${p}`
export const fidx = new Map(FACTS.map((f) => [key(f.ticker, f.metric, pk(f)), f]))
export const issueIdx = new Map<string, Issue[]>()
export const coverageIdx = new Map<string, string>()
for (const i of ISSUES) {
  if (!i.cal_q) continue
  const k = key(i.ticker, i.metric, i.cal_q)
  if (i.check === "coverage") coverageIdx.set(k, i.message)
  else issueIdx.set(k, [...(issueIdx.get(k) ?? []), i])
}

export const METRICS: Record<string, { label: string; unit: "usd" | "ratio"; num?: string; den?: string }> = {
  revenue: { label: "Revenue", unit: "usd" },
  capex: { label: "Capex", unit: "usd" },
  opex: { label: "Opex (excl. cost of revenue)", unit: "usd" },
  total_costs: { label: "Total operating costs", unit: "usd" },
  capex_to_revenue: { label: "Capex ÷ revenue", unit: "ratio", num: "capex", den: "revenue" },
  opex_to_revenue: { label: "Opex ÷ revenue", unit: "ratio", num: "opex", den: "revenue" },
}
export const METHOD: Record<string, string> = {
  reported: "As filed", ytd_diff: "YTD difference", q4_derived: "10-K minus 9 months", fy_minus_quarters: "Full year minus 3 quarters",
  derived: "Computed", reported_operating_expenses: "Reported OperatingExpenses", reported_costs_and_expenses: "Reported CostsAndExpenses",
  sga_plus_rnd: "SG&A + R&D", noninterest_expense: "Non-interest expense (bank)", no_cost_of_revenue_line: "Total costs (no cost-of-revenue line)",
}
export const UNIS = { ai: "AI set (19)", sp100: "S&P 100", all: `All (${COS.length})` } as const
export const inUni = (c: Company, uni: string) => uni === "all" || (uni === "ai" ? c.sets.includes("AI set") : c.sets.includes("S&P 100"))
export const groupOf = (c: Company, uni: string) => (uni === "ai" ? c.group : uni === "sp100" ? c.sector : c.sets.includes("AI set") ? c.group : c.sector)
