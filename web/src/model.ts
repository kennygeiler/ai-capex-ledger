// Value model: the metric for one company and period, after the chosen transform (index, change on prior period, YoY).
import { ALLQ, ALLY, coBy, fidx, key, METRICS, type Fact } from "./data"
import { parseSel, type State } from "./state"
import type { Unit } from "./lib/format"

export type Cell = { v: number; facts: Fact[]; ref?: Cell }

export const annual = (s: State) => s.per === "y"
export const allPeriods = (s: State) => (annual(s) ? ALLY : ALLQ)
export const periods = (s: State) => (annual(s) ? ALLY.filter((y) => y >= s.yf && y <= s.yt) : ALLQ.filter((q) => q >= s.qf && q <= s.qt))
export const transforms = (s: State): Record<string, string> => (annual(s)
  ? { value: "Value", index: "Indexed, first year = 100", pop: "Change on previous year" }
  : { value: "Value", index: "Indexed, first quarter = 100", pop: "Change on previous quarter", yoy: "Change on same quarter last year" })
export const tfOf = (s: State) => (transforms(s)[s.tf] ? s.tf : "value")
export const outUnit = (s: State): Unit => { const tf = tfOf(s); return tf === "value" ? METRICS[s.metric].unit : tf === "index" ? "index" : "pct" }
export const selection = (s: State) => parseSel(s.cos, (t) => coBy.has(t))

export function base(t: string, m: string, p: string | undefined): Cell | null {
  if (!p) return null
  const M = METRICS[m]
  if (M.num) {
    const a = fidx.get(key(t, M.num, p)), b = fidx.get(key(t, M.den!, p))
    return a && b && b.value ? { v: a.value / b.value, facts: [a, b] } : null
  }
  const f = fidx.get(key(t, m, p))
  return f ? { v: f.value, facts: [f] } : null
}
export function cell(s: State, t: string, p: string): Cell | null {
  const m = s.metric, b = base(t, m, p)
  if (!b) return null
  const all = allPeriods(s), i = all.indexOf(p), tf = tfOf(s)
  if (tf === "value") return b
  if (tf === "index") {
    const first = periods(s).map((x) => base(t, m, x)).find((x) => x && x.v)
    return first && first.v > 0 ? { v: (b.v / first.v) * 100, facts: [...b.facts, ...first.facts], ref: first } : null
  }
  const prev = base(t, m, all[i - (tf === "yoy" ? 4 : 1)])
  return prev && prev.v > 0 ? { v: b.v / prev.v - 1, facts: [...b.facts, ...prev.facts], ref: prev } : null
}
