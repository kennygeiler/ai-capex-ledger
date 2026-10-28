// All view state lives in the URL query string, so any view can be shared as a link.
import { useCallback, useSyncExternalStore } from "react"
import { WINDOW, YEARS } from "./data"

export const DEFAULT = {
  tab: "explore", per: "q", uni: "ai", q: "", cos: "MSFT.0,GOOGL.1,AMZN.2,META.3,ORCL.4,CRWV.5", metric: "capex", tf: "value", chart: "line",
  qf: WINDOW[0], qt: WINDOW.at(-1)!, yf: YEARS[0], yt: YEARS.at(-1)!, scale: "linear", mscale: "shared",
  sev: "warn", chk: "all", tk: "all", fco: "MSFT", fm: "capex", fq: "", dco: "VZ", net: "network",
}
export type State = typeof DEFAULT
export type SetState = (patch: Partial<State>) => void

function read(): State {
  const s = { ...DEFAULT }
  for (const [k, v] of new URLSearchParams(location.search)) if (k in DEFAULT) (s as Record<string, string>)[k] = v
  return s
}
let snapshot = read()
const subs = new Set<() => void>()
function write(patch: Partial<State>) {
  snapshot = { ...snapshot, ...patch }
  const url = new URL(location.href)
  for (const k of Object.keys(DEFAULT) as (keyof State)[]) snapshot[k] === DEFAULT[k] ? url.searchParams.delete(k) : url.searchParams.set(k, snapshot[k])
  history.replaceState(null, "", url)
  subs.forEach((f) => f())
}
export function useUrlState(): [State, SetState] {
  const s = useSyncExternalStore((f) => (subs.add(f), () => subs.delete(f)), () => snapshot)
  return [s, useCallback((p: Partial<State>) => write(p), [])]
}

export type Sel = { t: string; slot: number }
export const parseSel = (cos: string, valid: (t: string) => boolean): Sel[] =>
  cos ? cos.split(",").filter(Boolean).map((x) => { const [t, n] = x.split("."); return { t, slot: +n } }).filter((x) => valid(x.t)) : []
export const withCos = (list: Sel[]) => list.map((x) => `${x.t}.${x.slot}`).join(",")
export function addCos(cur: Sel[], ts: string[]) {
  const out = [...cur]
  for (const t of ts) {
    if (out.some((x) => x.t === t)) continue
    const used = new Set(out.map((x) => x.slot))
    out.push({ t, slot: [0, 1, 2, 3, 4, 5, 6, 7].find((n) => !used.has(n)) ?? 9 })
  }
  return out
}
