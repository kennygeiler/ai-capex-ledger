import { Fragment, useRef } from "react"
// Lineage drawer (shadcn Sheet): where a number came from, down to the filing and the XBRL concept.
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { coBy, coverageIdx, issueIdx, key, META, METHOD, METRICS, pk, TRACES, type Fact } from "@/data"
import { edgarUrl, fmt, qLabel, usd } from "@/lib/format"
import { base, cell, tfOf, transforms } from "@/model"
import type { SetState, State } from "@/state"
import { Code, SevBadge } from "./bits"

const A = ({ href, children }: { href: string; children: React.ReactNode }) =>
  <a href={href} target="_blank" rel="noopener" className="underline decoration-muted-foreground/40 underline-offset-2 hover:decoration-foreground">{children}</a>

function FactBlock({ f, onTrace }: { f: Fact; onTrace: (f: Fact) => void }) {
  const c = coBy.get(f.ticker)!
  const iss = f.cal_q ? issueIdx.get(key(f.ticker, f.metric, f.cal_q)) ?? [] : []
  const rows: [string, React.ReactNode][] = [
    ["Method", <>{METHOD[f.method] ?? f.method}. <span className="text-muted-foreground">{META.methods[f.method] ?? ""}</span></>],
    ["XBRL concept", <Code>{f.concept}</Code>],
    ["Read from", f.source_api === "xbrl_instance" ? "The filing's XBRL instance XML (companyfacts API had not caught up)" : f.source_api === "derived" ? "Computed from the facts below" : "SEC companyfacts API"],
    ["Period", `${f.period_start} to ${f.period_end} (${f.days} days${f.days_outside_cal_q ? `, ${f.days_outside_cal_q} outside ${qLabel(f.cal_q)}` : ""})`],
    ["Fiscal", `FY${f.fiscal_year}${f.fiscal_quarter ? ` Q${f.fiscal_quarter}` : ""}`],
    ["Filing", <>{f.form}, filed {f.filed}, <A href={edgarUrl(c.cik, f.accession)}><Code>{f.accession}</Code></A></>],
    ["Exact value", `$${Number(f.value).toLocaleString("en-US")}`],
  ]
  if (f.vintages) rows.push(["Vintages", `Carried in ${f.vintages} filing${f.vintages > 1 ? "s" : ""}${f.restated && f.original_value != null ? `; restated from $${Number(f.original_value).toLocaleString("en-US")}` : f.restated ? "; a source was restated" : ""}`])
  if (f.basis_conflict) rows.push(["Basis", "Full year minus nine months mixed two bases; used full year minus the three restated quarters."])
  return (
    <div className="grid gap-3 rounded-lg border p-3">
      <div className="text-sm font-medium">{METRICS[f.metric]?.label ?? f.metric}, {qLabel(pk(f))}: {usd(f.value, 2)}</div>
      <dl className="grid grid-cols-[7rem_1fr] gap-x-3 gap-y-1.5 text-xs">
        {rows.map(([k, v]) => <Fragment key={k}><dt className="text-muted-foreground">{k}</dt><dd className="min-w-0 break-words">{v}</dd></Fragment>)}
      </dl>
      {f.sources?.length > 0 && (
        <div className="grid gap-1 text-xs">
          <div className="text-muted-foreground">Built from</div>
          <ul className="grid gap-1 pl-4 [&>li]:list-disc">
            {f.sources.map((x: Record<string, any>, i: number) => x.metric
              ? <li key={i}>{String(x.metric).replace(/_/g, " ")}: <Code>{x.concept}</Code> {usd(x.val)} <span className="text-muted-foreground">({x.accn})</span></li>
              : <li key={i}>{x.start} to {x.end}: {usd(x.val)} <span className="text-muted-foreground">{x.form} filed {x.filed}{x.src === "xbrl_instance" ? ", parsed from instance XML" : ""},</span> <A href={edgarUrl(c.cik, x.accn)}><Code>{x.accn}</Code></A></li>)}
          </ul>
        </div>
      )}
      {iss.length > 0 && (
        <div className="grid gap-1 text-xs">
          <div className="text-muted-foreground">Checks</div>
          {iss.map((i, n) => <div key={n} className="flex items-start gap-2"><SevBadge s={i.severity} /><span><span className="font-medium">{i.check}</span>: {i.message}</span></div>)}
        </div>
      )}
      {f.cal_q && TRACES[key(f.ticker, f.metric, f.cal_q)] && (
        <Button variant="outline" size="sm" className="w-fit" onClick={() => onTrace(f)}>See the raw facts and parsing steps</Button>
      )}
    </div>
  )
}

export function Lineage({ s, set, target: open, onClose }: { s: State; set: SetState; target: { t: string; p: string } | null; onClose: () => void }) {
  // Keep showing the last cell while the sheet animates closed.
  const last = useRef(open)
  if (open) last.current = open
  const target = last.current
  const t = target?.t ?? "", p = target?.p ?? ""
  const c = target ? cell(s, t, p) : null, co = coBy.get(t), M = METRICS[s.metric], tf = tfOf(s)
  const formula = !c ? "" : tf === "value" && M.num ? `${M.label}: ${usd(c.facts[0].value)} ÷ ${usd(c.facts[1].value)}`
    : tf === "value" ? "" : `${fmt(base(t, s.metric, p)!.v, M.unit)} against ${fmt(c.ref!.v, M.unit)} (${transforms(s)[tf].toLowerCase()})`
  const uniq = c ? [...new Map(c.facts.map((f) => [f.id, f])).values()] : []
  const onTrace = (f: Fact) => {
    onClose()
    set({ tab: "found", fco: f.ticker, fm: f.metric, fq: f.cal_q! })
    setTimeout(() => document.getElementById("parse")?.scrollIntoView({ behavior: "smooth" }), 80)
  }
  return (
    <Sheet open={!!open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-xl">
        {target && co && (
          <>
            <SheetHeader>
              <SheetTitle>{co.name} ({t}), {qLabel(p)}</SheetTitle>
              <SheetDescription>{M.label}, {transforms(s)[tf].toLowerCase()}</SheetDescription>
              <div className="pt-2 text-3xl font-semibold tabular-nums tracking-tight">{c ? fmt(c.v, tf === "value" ? M.unit : tf === "index" ? "index" : "pct") : "No value"}</div>
              {formula && <div className="text-xs text-muted-foreground">{formula}</div>}
            </SheetHeader>
            <Separator />
            <div className="grid gap-3 p-4">
              {!c && <p className="text-sm">{coverageIdx.get(key(t, M.num ?? s.metric, p)) ?? "No fact for this period."}</p>}
              {uniq.map((f) => <FactBlock key={f.id} f={f} onTrace={onTrace} />)}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
