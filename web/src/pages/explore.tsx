import { Download, Link2 } from "lucide-react"
import { toast } from "sonner"
import { Legend, BarsChart, LinesChart, Multiples } from "@/components/charts"
import { Field, Pick, Seg, Swatch } from "@/components/bits"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { COS, coBy, coverageIdx, FACTS, groupOf, inUni, issueIdx, key, METRICS, UNIS, WINDOW } from "@/data"
import { colorVar, fmt, qLabel } from "@/lib/format"
import { cn } from "@/lib/utils"
import { allPeriods, annual, cell, outUnit, periods, selection, transforms } from "@/model"
import { addCos, withCos, type SetState, type State } from "@/state"

const CHARTS = { line: "Lines", bars: "Bars", multiples: "Small multiples", heat: "Heat table" }
type Open = (t: string, p: string) => void

function download(name: string, text: string) {
  const a = document.createElement("a")
  a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" })); a.download = name; a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}
const csvRow = (xs: unknown[]) => xs.map((x) => (x == null ? "" : /[",\n]/.test(String(x)) ? `"${String(x).replace(/"/g, '""')}"` : x)).join(",")
function viewCsv(s: State) {
  const rows: unknown[][] = [["ticker", "name", "period", "metric", "transform", "value", "methods", "accessions"]]
  for (const x of selection(s)) for (const p of periods(s)) {
    const c = cell(s, x.t, p)
    rows.push([x.t, coBy.get(x.t)!.name, p, s.metric, s.tf, c?.v ?? "", c ? [...new Set(c.facts.map((f) => f.method))].join("|") : "", c ? [...new Set(c.facts.map((f) => f.accession))].join("|") : ""])
  }
  return rows.map(csvRow).join("\n")
}
function factsCsv() {
  const cols = ["ticker", "period_type", "metric", "cal_q", "fy_key", "value", "method", "source_api", "concept", "period_start", "period_end", "fiscal_year", "fiscal_quarter", "form", "filed", "accession", "restated", "in_window"]
  return [cols, ...FACTS.map((f) => cols.map((c) => f[c]))].map(csvRow).join("\n")
}

function Controls({ s, set }: { s: State; set: SetState }) {
  const S = selection(s), selected = new Set(S.map((x) => x.t)), TF = transforms(s)
  const pool = COS.filter((c) => inUni(c, s.uni)).filter((c) => !s.q || `${c.ticker} ${c.name} ${c.legal_name}`.toLowerCase().includes(s.q.toLowerCase()))
  const groups = [...new Set(pool.map((c) => groupOf(c, s.uni)))]
  const all = allPeriods(s), [fk, tk] = annual(s) ? (["yf", "yt"] as const) : (["qf", "qt"] as const)
  const setGroup = (g: string, on: boolean) => {
    const members = COS.filter((c) => inUni(c, s.uni) && groupOf(c, s.uni) === g).map((c) => c.ticker)
    const cur = S.filter((x) => !members.includes(x.t))
    set({ cos: withCos(on ? addCos(cur, members) : cur) })
  }
  return (
    <Card size="sm" className="lg:sticky lg:top-16">
      <CardContent className="grid gap-4">
        <Field label="Periods"><Seg value={s.per} onChange={(v) => set({ per: v })} options={{ q: "Quarterly (10-Q)", y: "Annual (10-K)" }} /></Field>
        <Field label="Metric"><Pick label="Metric" value={s.metric} onChange={(v) => set({ metric: v })} options={Object.entries(METRICS).map(([k, m]) => [k, m.label])} /></Field>
        <Field label="Show as"><Pick label="Show as" value={TF[s.tf] ? s.tf : "value"} onChange={(v) => set({ tf: v })} options={Object.entries(TF)} /></Field>
        <Field label="Chart"><Seg value={s.chart} onChange={(v) => set({ chart: v })} options={CHARTS} /></Field>
        {s.chart === "line" && <Field label="Y axis"><Seg value={s.scale} onChange={(v) => set({ scale: v })} options={{ linear: "Linear", log: "Log" }} /></Field>}
        {s.chart === "multiples" && <Field label="Scale"><Seg value={s.mscale} onChange={(v) => set({ mscale: v })} options={{ shared: "Shared", own: "Own per company" }} /></Field>}
        <Field label={annual(s) ? "Fiscal years" : "Quarters"} note={annual(s) ? "Fiscal years as each company defines them (Nvidia's ends in January, Microsoft's in June)." : "Calendar quarters; fiscal quarters are mapped by most days."}>
          <div className="grid grid-cols-2 gap-2">
            <Pick label="From" value={s[fk]} onChange={(v) => set({ [fk]: v })} options={all.filter((p) => p <= s[tk]).map((p) => [p, qLabel(p)])} />
            <Pick label="To" value={s[tk]} onChange={(v) => set({ [tk]: v })} options={all.filter((p) => p >= s[fk]).map((p) => [p, `${qLabel(p)}${!annual(s) && p > WINDOW.at(-1)! ? " (partial)" : ""}`])} />
          </div>
        </Field>
        <Field label={`Companies (${S.length} selected)`}>
          <Seg value={s.uni} onChange={(v) => set({ uni: v })} options={UNIS} />
          <Input type="search" placeholder="Search ticker or name" value={s.q} onChange={(e) => set({ q: e.target.value })} className="h-8" aria-label="Search companies" />
          <ScrollArea className="h-80 rounded-md border">
            <div className="grid gap-0.5 p-2">
              {groups.map((g) => (
                <div key={g} className="grid gap-0.5">
                  <div className="flex items-center justify-between pt-2 pb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground first:pt-0">
                    <span className="truncate">{g}</span>
                    <span className="flex shrink-0 gap-1 normal-case">
                      <Button variant="ghost" size="xs" className="h-5 px-1.5" onClick={() => setGroup(g, true)}>all</Button>
                      <Button variant="ghost" size="xs" className="h-5 px-1.5" onClick={() => setGroup(g, false)}>none</Button>
                    </span>
                  </div>
                  {pool.filter((c) => groupOf(c, s.uni) === g).map((c) => {
                    const on = selected.has(c.ticker), slot = S.find((x) => x.t === c.ticker)?.slot ?? -1
                    return (
                      <label key={c.ticker} className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-sm hover:bg-muted">
                        <Checkbox checked={on} onCheckedChange={(v) => { const cur = S.filter((x) => x.t !== c.ticker); set({ cos: withCos(v ? addCos(cur, [c.ticker]) : cur) }) }} />
                        <Swatch color={on ? colorVar(slot) : "transparent"} />
                        <span className="w-12 shrink-0 font-mono text-xs font-medium">{c.ticker}</span>
                        <span className="truncate text-muted-foreground" title={c.legal_name ?? c.name}>{c.name}</span>
                      </label>
                    )
                  })}
                </div>
              ))}
              {!groups.length && <p className="p-2 text-xs text-muted-foreground">No match.</p>}
            </div>
          </ScrollArea>
          <Button variant="link" size="xs" className="h-auto w-fit p-0 text-muted-foreground" onClick={() => set({ cos: "" })}>Clear selection</Button>
          {S.length > 8 && (s.chart === "line" || s.chart === "bars") && <p className="text-xs text-warn">Over 8 companies: extra series turn grey. Small multiples or the heat table read better.</p>}
        </Field>
      </CardContent>
    </Card>
  )
}

// Returns the fill and whether it is strong enough to need light text (light mode; dark mode text is already light).
function heat(v: number, lo: number, hi: number, pct: boolean) {
  if (pct) { const k = Math.min(1, Math.abs(v) / 0.5) * 85; return { bg: `color-mix(in oklab, var(${v >= 0 ? "--div-pos" : "--div-neg"}) ${k.toFixed(0)}%, var(--div-neutral))`, strong: k > 50 } }
  const k = hi > lo ? ((v - lo) / (hi - lo)) * 100 : 50
  return { bg: `color-mix(in oklab, var(--seq-hi) ${k.toFixed(0)}%, var(--seq-lo))`, strong: k > 50 }
}

function Pivot({ s, open }: { s: State; open: Open }) {
  const ps = periods(s), S = selection(s), isHeat = s.chart === "heat", unit = outUnit(s)
  const vals = S.flatMap((x) => ps.map((p) => cell(s, x.t, p)?.v)).filter((v): v is number => v != null)
  const lo = Math.min(...vals), hi = Math.max(...vals)
  const heatOf = (v: number) => heat(v, lo, hi, unit === "pct")
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table className="text-xs">
        <TableHeader>
          <TableRow className="bg-muted/50 hover:bg-muted/50">
            <TableHead className="sticky left-0 z-10 bg-muted">Company</TableHead>
            {ps.map((p) => <TableHead key={p} className="text-right tabular-nums">{qLabel(p)}</TableHead>)}
            <TableHead className="text-right">Coverage</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {S.map((x) => {
            let n = 0
            return (
              <TableRow key={x.t}>
                <TableCell className="sticky left-0 z-10 bg-background">
                  <span className="flex items-center gap-2"><Swatch color={colorVar(x.slot)} /><span className="font-mono font-medium">{x.t}</span><span className="max-w-40 truncate text-muted-foreground">{coBy.get(x.t)?.name}</span></span>
                </TableCell>
                {ps.map((p) => {
                  const c = cell(s, x.t, p)
                  if (!c) {
                    const reason = coverageIdx.get(key(x.t, METRICS[s.metric].num ?? s.metric, p)) ?? (annual(s) ? "No 10-K full-year value for this fiscal year." : "No value for this quarter.")
                    return <TableCell key={p} className="text-right text-muted-foreground" title={reason}>–</TableCell>
                  }
                  n++
                  const derived = c.facts.some((f) => f.method !== "reported")
                  const iss = c.facts.flatMap((f) => issueIdx.get(key(f.ticker, f.metric, f.cal_q ?? "")) ?? [])
                  const flag = iss.some((i) => i.severity === "error") ? "err" : iss.some((i) => i.severity === "warn") ? "warn" : ""
                  const xml = c.facts.some((f) => f.source_api === "xbrl_instance")
                  const h = isHeat ? heatOf(c.v) : null
                  return (
                    <TableCell key={p} className="p-0 text-right">
                      <button onClick={() => open(x.t, p)} title={xml ? "Parsed from the filing's XBRL instance XML" : "Show filing lineage"}
                        className={cn("w-full px-2 py-2 text-right font-mono tabular-nums transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring", h && "hover:brightness-110", h?.strong && "text-white")}
                        style={h ? { background: h.bg } : undefined}>
                        <span className={cn(derived && "underline decoration-dotted underline-offset-[3px]")}>{fmt(c.v, unit)}</span>
                        {xml && <sup className="ml-0.5 text-muted-foreground">x</sup>}
                        {flag && <span className={cn("ml-0.5 font-sans font-bold", flag === "err" ? "text-err" : "text-warn")}>!</span>}
                      </button>
                    </TableCell>
                  )
                })}
                <TableCell className="text-right text-muted-foreground tabular-nums">{n}/{ps.length}</TableCell>
              </TableRow>
            )
          })}
        </TableBody>
        {s.tf === "value" && METRICS[s.metric].unit === "usd" && S.length > 1 && (
          <TableFooter>
            <TableRow>
              <TableCell className="sticky left-0 z-10 bg-muted font-medium">Selected total</TableCell>
              {ps.map((p) => {
                const xs = S.map((x) => cell(s, x.t, p)?.v), sum = xs.reduce<number>((a, b) => a + (b ?? 0), 0), gap = xs.some((v) => v == null)
                return <TableCell key={p} className="text-right font-mono tabular-nums" title={gap ? "Some companies have no value for this period" : undefined}>{fmt(sum, "usd")}{gap ? "*" : ""}</TableCell>
              })}
              <TableCell />
            </TableRow>
          </TableFooter>
        )}
      </Table>
    </div>
  )
}

export function Explore({ s, set, open }: { s: State; set: SetState; open: Open }) {
  const S = selection(s), ps = periods(s), TF = transforms(s)
  const title = `${METRICS[s.metric].label}${s.tf !== "value" && TF[s.tf] ? `, ${TF[s.tf].toLowerCase()}` : ""}`
  const sub = `${S.length} companies, ${qLabel(ps[0])} to ${qLabel(ps.at(-1))}, ${annual(s) ? "fiscal years from 10-K filings" : "calendar quarters from 10-Q and 10-K filings"}.`
  return (
    <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
      <aside><Controls s={s} set={set} /></aside>
      <div className="grid min-w-0 content-start gap-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="grid gap-1">
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            <p className="text-sm text-muted-foreground">{sub} Click any point, bar or cell for its filings.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => navigator.clipboard?.writeText(location.href).then(() => toast.success("Link copied"), () => toast.error("Copy failed"))}><Link2 />Copy link</Button>
            <Button variant="outline" size="sm" onClick={() => download(`capex-ledger_${s.metric}_${annual(s) ? "annual" : "quarterly"}.csv`, viewCsv(s))}><Download />This view</Button>
            <Button variant="outline" size="sm" onClick={() => download("capex-ledger_facts.csv", factsCsv())}><Download />All facts</Button>
          </div>
        </div>
        {S.length === 0 ? <p className="text-sm text-muted-foreground">Pick at least one company on the left.</p> : (
          <>
            {s.chart === "line" || s.chart === "bars" ? (
              <Card>
                <CardHeader>
                  <CardTitle>{title}</CardTitle>
                  <CardDescription>{annual(s) ? "Fiscal years" : "Calendar quarters"}, {qLabel(ps[0])} to {qLabel(ps.at(-1))}</CardDescription>
                  <CardAction><Legend S={S} /></CardAction>
                </CardHeader>
                <CardContent>{s.chart === "line" ? <LinesChart s={s} S={S} open={open} /> : <BarsChart s={s} S={S} open={open} />}</CardContent>
              </Card>
            ) : s.chart === "multiples" ? <Multiples s={s} S={S} open={open} /> : null}
            <div className="grid gap-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-lg font-semibold tracking-tight">{s.chart === "heat" ? "Heat table" : "Values"}</h2>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span><span className="underline decoration-dotted underline-offset-[3px]">1.2</span> derived</span>
                  <span><sup>x</sup> parsed from instance XML</span>
                  <span><strong className="text-warn">!</strong> check flagged</span>
                  <span>– no value (hover for why)</span>
                </div>
              </div>
              <Pivot s={s} open={open} />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
