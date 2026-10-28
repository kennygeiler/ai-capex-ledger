// Explore charts on shadcn/ui's chart wrapper (Recharts). Every point and bar opens its filing lineage.
import { useRef } from "react"
import { Bar, BarChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, type ChartConfig } from "@/components/ui/chart"
import { coBy, METRICS } from "@/data"
import { axisFmt, colorVar, fmt, qLabel, type Unit } from "@/lib/format"
import { cell, outUnit, periods, type Cell } from "@/model"
import type { Sel, State } from "@/state"
import { Swatch } from "./bits"

type Open = (t: string, p: string) => void
type Row = { p: string; label: string } & Record<string, number | string | null>

function rows(s: State, S: Sel[]): Row[] {
  return periods(s).map((p) => {
    const r: Row = { p, label: qLabel(p) }
    for (const x of S) r[x.t] = cell(s, x.t, p)?.v ?? null
    return r
  })
}
const config = (S: Sel[]): ChartConfig => Object.fromEntries(S.map((x) => [x.t, { label: x.t, color: colorVar(x.slot) }]))

function Tip({ active, payload, label, unit, hint }: { active?: boolean; payload?: { dataKey: string; value: number | null; color?: string }[]; label?: string; unit: Unit; hint: string }) {
  if (!active || !payload?.length) return null
  const items = payload.filter((x) => x.value != null).sort((a, b) => (b.value as number) - (a.value as number))
  return (
    <div className="grid min-w-36 gap-1.5 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
      <div className="font-medium">{label}</div>
      {items.map((x) => (
        <div key={x.dataKey} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-muted-foreground"><Swatch color={x.color ?? "var(--other)"} />{x.dataKey}</span>
          <span className="font-mono font-medium tabular-nums text-foreground">{fmt(x.value, unit)}</span>
        </div>
      ))}
      {!items.length && <div className="text-muted-foreground">No data</div>}
      <div className="text-muted-foreground">{hint}</div>
    </div>
  )
}

export function Legend({ S }: { S: Sel[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {S.map((x) => <span key={x.t} className="flex items-center gap-1.5"><Swatch color={colorVar(x.slot)} /><span className="font-medium text-foreground">{x.t}</span></span>)}
    </div>
  )
}

export function LinesChart({ s, S, open }: { s: State; S: Sel[]; open: Open }) {
  const data = rows(s, S), unit = outUnit(s), box = useRef<HTMLDivElement>(null)
  const log = s.scale === "log" && s.tf === "value" && data.every((r) => S.every((x) => r[x.t] == null || (r[x.t] as number) > 0))
  // Recharts' hover dot sits above the series dots, so clicks are resolved here: nearest dot in the hovered period.
  const onClick = (st: { activeIndex?: number | string | null }, e: React.MouseEvent) => {
    const i = st?.activeIndex == null ? -1 : Number(st.activeIndex)
    if (i < 0 || !box.current) return
    const dots = [...box.current.querySelectorAll<SVGCircleElement>(`circle[data-i="${i}"][data-t]`)]
    const hit = dots.map((d) => { const r = d.getBoundingClientRect(); return { t: d.dataset.t!, dist: Math.abs(r.top + r.height / 2 - e.clientY) } }).sort((a, b) => a.dist - b.dist)[0]
    if (hit) open(hit.t, data[i].p)
  }
  return (
    <div ref={box}>
      <ChartContainer config={config(S)} className="aspect-auto h-[380px] w-full cursor-pointer [&_:focus:not(:focus-visible)]:outline-none">
        <LineChart data={data} margin={{ left: 4, right: 16, top: 8, bottom: 0 }} onClick={onClick as never}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} minTickGap={16} />
          <YAxis tickLine={false} axisLine={false} width={64} tickFormatter={(v) => axisFmt(v, unit)} scale={log ? "log" : "auto"} domain={log ? ["auto", "auto"] : undefined} />
          <ChartTooltip cursor={{ strokeDasharray: "3 3" }} content={<Tip unit={unit} hint="Click a point for its filings" />} />
          {S.map((x) => {
            const c = colorVar(x.slot)
            const dot = (r: number, mark: boolean) => (p: { cx?: number; cy?: number; index?: number; value?: unknown }) =>
              p.cx == null || p.cy == null || p.value == null ? <g key={`${x.t}-${p.index}-${r}`} /> : (
                <circle key={`${x.t}-${p.index}-${r}`} cx={p.cx} cy={p.cy} r={r} fill={c} stroke="var(--background)" strokeWidth={r > 3 ? 2 : 0}
                  {...(mark ? { "data-t": x.t, "data-i": p.index } : {})} />
              )
            return <Line key={x.t} dataKey={x.t} type="linear" stroke={c} strokeWidth={2} dot={dot(2.5, true)} activeDot={dot(5, false)} isAnimationActive={false} />
          })}
        </LineChart>
      </ChartContainer>
    </div>
  )
}

export function BarsChart({ s, S, open }: { s: State; S: Sel[]; open: Open }) {
  const data = rows(s, S), unit = outUnit(s)
  return (
    <ChartContainer config={config(S)} className="aspect-auto h-[380px] w-full [&_:focus:not(:focus-visible)]:outline-none">
      <BarChart data={data} margin={{ left: 4, right: 8, top: 8, bottom: 0 }} barGap={2}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} minTickGap={16} />
        <YAxis tickLine={false} axisLine={false} width={64} tickFormatter={(v) => axisFmt(v, unit)} />
        <ChartTooltip content={<Tip unit={unit} hint="Click a bar for its filings" />} />
        {S.map((x) => (
          <Bar key={x.t} dataKey={x.t} fill={colorVar(x.slot)} radius={[4, 4, 0, 0]} maxBarSize={18} isAnimationActive={false}
            className="cursor-pointer" onClick={(d: { payload?: Row }) => d.payload && open(x.t, d.payload.p)} />
        ))}
      </BarChart>
    </ChartContainer>
  )
}

export function Multiples({ s, S, open }: { s: State; S: Sel[]; open: Open }) {
  const data = rows(s, S), unit = outUnit(s)
  const vals = data.flatMap((r) => S.map((x) => r[x.t] as number | null)).filter((v): v is number => v != null)
  const shared: [number, number] = [Math.min(0, ...vals), Math.max(0, ...vals)]
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {S.map((x) => {
        const last = [...data].reverse().map((r) => r[x.t]).find((v) => v != null) as number | undefined
        return (
          <Card key={x.t} size="sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Swatch color={colorVar(x.slot)} />{x.t}<span className="truncate font-normal text-muted-foreground">{coBy.get(x.t)?.name}</span></CardTitle>
              <CardDescription>Latest {fmt(last, unit)}</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer config={config([x])} className="aspect-auto h-[140px] w-full [&_:focus:not(:focus-visible)]:outline-none">
                <BarChart data={data} margin={{ left: 0, right: 0, top: 4, bottom: 0 }}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={40} />
                  <YAxis tickLine={false} axisLine={false} width={52} tickCount={3} tickFormatter={(v) => axisFmt(v, unit)} domain={s.mscale === "shared" ? shared : undefined} />
                  <ChartTooltip content={<Tip unit={unit} hint={`${METRICS[s.metric].label}. Click for filings`} />} />
                  <Bar dataKey={x.t} fill={colorVar(x.slot)} radius={[3, 3, 0, 0]} maxBarSize={16} isAnimationActive={false}
                    className="cursor-pointer" onClick={(d: { payload?: Row }) => d.payload && open(x.t, d.payload.p)} />
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
export type { Cell }
