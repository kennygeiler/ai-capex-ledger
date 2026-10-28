export const usd = (v: number, digits = 1) => {
  const a = Math.abs(v), s = v < 0 ? "−" : ""
  if (a >= 1e9) return `${s}$${(a / 1e9).toFixed(a >= 1e11 ? 0 : digits)}B`
  if (a >= 1e6) return `${s}$${(a / 1e6).toFixed(a >= 1e8 ? 0 : digits)}M`
  return `${s}$${Math.round(a).toLocaleString()}`
}
export type Unit = "usd" | "ratio" | "index" | "pct"
export const fmt = (v: number | null | undefined, unit: Unit) => {
  if (v == null || !isFinite(v)) return "–"
  if (unit === "usd") return usd(v)
  if (unit === "ratio") return `${(v * 100).toFixed(1)}%`
  if (unit === "index") return v.toFixed(0)
  const p = v * 100
  return `${p > 0.05 ? "+" : p < -0.05 ? "−" : ""}${Math.abs(p).toFixed(1)}%`
}
export const axisFmt = (v: number, unit: Unit) => (unit === "usd" ? (v === 0 ? "0" : usd(v, 0)) : unit === "index" ? `${Math.round(v)}` : `${Math.round(v * 100)}%`)
export const qLabel = (q?: string) => (!q ? "" : q.startsWith("FY") ? q : `Q${q.slice(5)} ’${q.slice(2, 4)}`)
export const edgarUrl = (cik: number | string, accn: string) => `https://www.sec.gov/Archives/edgar/data/${cik}/${accn.replace(/-/g, "")}/${accn}-index.htm`
export const bytes = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1e3)} KB`)
export const dollars = (v: number) => `$${Number(v).toLocaleString("en-US")}`
export const colorVar = (slot: number) => (slot >= 0 && slot < 8 ? `var(--s${slot + 1})` : "var(--other)")
