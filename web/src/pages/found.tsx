import { Code, DataTable, Field, Pick, Section } from "@/components/bits"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TableCell, TableRow } from "@/components/ui/table"
import { COS, coBy, FACTS, key, META, METHOD, TRACES, WINDOW } from "@/data"
import { dollars, edgarUrl, qLabel } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { SetState, State } from "@/state"

const A = ({ href, children }: { href: string; children: React.ReactNode }) =>
  <a href={href} target="_blank" rel="noopener" className="underline decoration-muted-foreground/40 underline-offset-2 hover:decoration-foreground">{children}</a>

function Usage({ rows, first }: { rows: [string, string[]][]; first: string }) {
  return (
    <DataTable head={[first, "Companies", "Which"]}>
      {rows.map(([t, list]) => (
        <TableRow key={t}><TableCell className="align-top">{t.startsWith("<") ? t : <Code>{t}</Code>}</TableCell><TableCell className="align-top tabular-nums">{list.length}</TableCell>
          <TableCell className="whitespace-normal font-mono text-muted-foreground">{list.join(", ")}</TableCell></TableRow>
      ))}
    </DataTable>
  )
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <Card size="sm">
      <CardHeader><CardTitle className="flex items-center gap-2"><Badge variant="secondary" className="tabular-nums">Step {n}</Badge>{title}</CardTitle></CardHeader>
      <CardContent className="grid gap-3 text-sm">{children}</CardContent>
    </Card>
  )
}

export function Found({ s, set }: { s: State; set: SetState }) {
  // A. Which tag each company uses, across the whole set.
  const usage = (m: string) => {
    const by: Record<string, string[]> = {}
    for (const c of COS) (by[c.concepts[m][0] ?? "(none found)"] ??= []).push(c.ticker)
    return Object.entries(by).sort((a, b) => b[1].length - a[1].length)
  }
  const opexBy: Record<string, string[]> = {}
  for (const f of FACTS) if (f.metric === "opex" && f.period_type === "quarter" && f.cal_q === WINDOW.at(-1)) (opexBy[f.method] ??= []).push(f.ticker)
  const noOpex = COS.filter((c) => !c.coverage.opex).map((c) => c.ticker)

  // B. One company's discovery scan.
  const dc = coBy.get(s.dco) ?? COS[0]
  const fams: Record<string, string> = { revenue: "Revenue", capex: "Capex", cost_of_revenue: "Cost of revenue", operating: "Operating costs and income" }
  const usedFor: Record<string, string[]> = { revenue: dc.concepts.revenue, capex: dc.concepts.capex, cost_of_revenue: dc.concepts.cost_of_revenue,
    operating: [...dc.concepts.operating_income, ...dc.concepts.costs_and_expenses, ...dc.concepts.opex_reported, ...(dc.concepts.sga ?? []), ...(dc.concepts.noninterest_expense ?? [])] }
  const fills = (dc.gap_fills ?? []).filter((g: Record<string, unknown>) => g.status)

  // C. Parse trace for one number.
  const traceCos = [...new Set(Object.keys(TRACES).map((k) => k.split("|")[0]))]
  const tco = traceCos.includes(s.fco) ? s.fco : traceCos[0]
  const tms = ["revenue", "capex", "cost_of_revenue", "operating_income"].filter((m) => Object.keys(TRACES).some((k) => k.startsWith(`${tco}|${m}|`)))
  const tm = tms.includes(s.fm) ? s.fm : tms[0]
  const tqs = WINDOW.filter((q) => TRACES[key(tco, tm, q)])
  const tq = tqs.includes(s.fq) ? s.fq : [...tqs].reverse().find((q) => TRACES[key(tco, tm, q)].method !== "reported") ?? tqs.at(-1)!
  const tr = TRACES[key(tco, tm, tq)]
  const row = FACTS.find((f) => f.ticker === tco && f.metric === tm && f.cal_q === tq)
  const co = coBy.get(tco)!
  type St = { value: number; start: string; end: string; vintages: Record<string, any>[] }
  const steps: St[] = tr?.steps ?? []
  const arith = !tr ? null : steps.length === 2
    ? <>{dollars(steps[0].value)} <span className="text-muted-foreground">({steps[0].start} to {steps[0].end})</span> − {dollars(steps[1].value)} <span className="text-muted-foreground">({steps[1].start} to {steps[1].end})</span> = <strong>{dollars(steps[0].value - steps[1].value)}</strong></>
    : steps.length > 2
      ? <>{dollars(steps[0].value)} <span className="text-muted-foreground">(full year)</span> − {steps.slice(1).map((x) => dollars(x.value)).join(" − ")} = <strong>{dollars(steps[0].value - steps.slice(1).reduce((a, x) => a + x.value, 0))}</strong></>
      : <>Taken as filed: <strong>{dollars(steps[0].value)}</strong></>

  return (
    <div className="grid gap-12">
      <Section title="How each company's label was found" description="Companies tag the same line item with different XBRL concepts, and change tags over time. The pipeline doesn't guess. For every company it:">
        <ol className="grid gap-2 text-sm">
          {[<>Scans the company's full list of us-gaap concepts against search patterns for each line item (<Code>{META.discovery_patterns.revenue}</Code> for revenue, and similar).</>,
            "For every match, builds discrete quarters and counts how many the concept covers in the last three years.",
            "Ranks the candidate tags by that recent coverage (then by a fixed priority), and takes each quarter from the best-ranked tag that has it. Matches outside the candidate list are shown, so a missed tag is visible."]
            .map((x, i) => <li key={i} className="flex gap-3"><span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium">{i + 1}</span><span className="text-muted-foreground">{x}</span></li>)}
        </ol>
        <div className="grid gap-6 xl:grid-cols-2">
          <div className="grid content-start gap-2"><h3 className="text-sm font-medium">Revenue: which tag each company uses</h3><Usage first="Tag (XBRL concept)" rows={usage("revenue")} /></div>
          <div className="grid content-start gap-2"><h3 className="text-sm font-medium">Capex: which tag each company uses</h3><Usage first="Tag (XBRL concept)" rows={usage("capex")} /></div>
        </div>
        <div className="grid gap-2">
          <h3 className="text-sm font-medium">Opex: which route each company needs ({qLabel(WINDOW.at(-1))})</h3>
          <DataTable head={["Route", "Companies", "Which"]}>
            {Object.entries(opexBy).sort((a, b) => b[1].length - a[1].length).map(([m, l]) => (
              <TableRow key={m}><TableCell className="align-top whitespace-normal"><div className="font-medium">{METHOD[m] ?? m}</div><div className="text-muted-foreground">{META.methods[m] ?? ""}</div></TableCell>
                <TableCell className="align-top tabular-nums">{l.length}</TableCell><TableCell className="whitespace-normal font-mono text-muted-foreground">{l.join(", ")}</TableCell></TableRow>
            ))}
            {noOpex.length > 0 && <TableRow><TableCell>No route has data</TableCell><TableCell>{noOpex.length}</TableCell><TableCell className="whitespace-normal font-mono text-muted-foreground">{noOpex.join(", ")}</TableCell></TableRow>}
          </DataTable>
        </div>
      </Section>

      <Section title="The scan for one company" description={`${dc.n_concepts} us-gaap concepts in ${dc.legal_name ?? dc.name}'s filings.`}
        actions={<div className="w-72"><Pick label="Company" value={dc.ticker} onChange={(v) => set({ dco: v })} options={COS.map((c) => [c.ticker, `${c.ticker} ${c.name}`])} /></div>}>
        {Object.entries(fams).map(([fam, label]) => {
          const hits: Record<string, any>[] = dc.discovery?.[fam] ?? []
          return (
            <div key={fam} className="grid gap-2">
              <h3 className="text-sm font-medium">{label}</h3>
              {hits.length ? (
                <DataTable head={["Concept found", "Taxonomy label", "Quarters, last 3 yrs", "Quarters, all", "Latest period", "Status"]}>
                  {hits.map((h) => {
                    const rank = usedFor[fam].indexOf(h.concept)
                    const used = rank === 0 && h.quarters_recent
                    return (
                      <TableRow key={h.concept} className={cn(used && "bg-muted/40")}>
                        <TableCell><Code>{h.concept}</Code></TableCell><TableCell className="max-w-72 whitespace-normal">{h.label}</TableCell>
                        <TableCell className="tabular-nums">{h.quarters_recent}</TableCell><TableCell className="tabular-nums">{h.quarters_all}</TableCell><TableCell>{h.last_period_end ?? "–"}</TableCell>
                        <TableCell>{used ? <Badge>Used (ranked first)</Badge> : rank > 0 ? <Badge variant="secondary">Candidate, rank {rank + 1}</Badge> : h.candidate ? <Badge variant="outline">Candidate, no data</Badge> : <span className="text-muted-foreground">Found by scan, not a candidate</span>}</TableCell>
                      </TableRow>
                    )
                  })}
                </DataTable>
              ) : <p className="text-sm text-muted-foreground">No us-gaap concept matched. If the company reports this line, it uses its own extension tag, which the companyfacts API leaves out.</p>}
            </div>
          )
        })}
        {fills.length > 0 && (
          <div className="grid gap-2">
            <h3 className="text-sm font-medium">Filings parsed from instance XML</h3>
            <DataTable head={["Form", "Period", "Filed", "Facts read", "File"]}>
              {fills.map((g: Record<string, any>, i: number) => (
                <TableRow key={i}><TableCell>{g.form ?? ""}</TableCell><TableCell>{g.period ?? ""}</TableCell><TableCell>{g.filed ?? ""}</TableCell>
                  <TableCell>{g.facts ?? ""} facts, {g.concepts ?? ""} concepts</TableCell><TableCell>{g.url ? <A href={g.url}>{g.url.split("/").pop()}</A> : g.status}</TableCell></TableRow>
              ))}
            </DataTable>
          </div>
        )}
      </Section>

      <Section id="parse" title="How one number was parsed" description={<>Pick a number. Each step uses the facts exactly as the API returned them. Traces are kept for the AI set; the full set's raw files are in <Code>data/raw/</Code>.</>}>
        <div className="grid gap-3 sm:grid-cols-3 sm:max-w-3xl">
          <Field label="Company"><Pick label="Company" value={tco} onChange={(v) => set({ fco: v })} options={traceCos.map((t) => [t, `${t} ${coBy.get(t)?.name}`])} /></Field>
          <Field label="Line item"><Pick label="Line item" value={tm} onChange={(v) => set({ fm: v })} options={tms.map((m) => [m, m.replace(/_/g, " ")])} /></Field>
          <Field label="Quarter"><Pick label="Quarter" value={tq} onChange={(v) => set({ fq: v })} options={tqs.map((q) => [q, `${qLabel(q)} (${METHOD[TRACES[key(tco, tm, q)].method]})`])} /></Field>
        </div>
        {!tr ? <p className="text-sm text-muted-foreground">No trace for this selection.</p> : (
          <div className="grid gap-4">
            <p className="text-sm text-muted-foreground">Concept <Code>{tr.concept}</Code>, taxonomy label "{tr.label}". {tr.description}</p>
            <Step n={1} title={`Raw facts returned for this concept and period${steps.length > 1 ? "s" : ""}`}>
              <p className="text-muted-foreground">Each row is one filing that reported the period. Comparatives in later filings repeat it, and restatements change it. The latest filing is used.</p>
              {steps.map((x, i) => (
                <div key={i} className="grid gap-1.5">
                  <div className="text-xs text-muted-foreground">{x.start} to {x.end}</div>
                  <DataTable head={["Value", "Form", "Filing's FY / period", "Filed", "Accession", "Frame", ""]}>
                    {x.vintages.map((v, j) => (
                      <TableRow key={j} className={cn(v.chosen && "bg-muted/40 font-medium")}>
                        <TableCell className="font-mono tabular-nums">{dollars(v.val)}</TableCell><TableCell>{v.form}</TableCell><TableCell>{v.fy ?? ""} {v.fp ?? ""}</TableCell><TableCell>{v.filed}</TableCell>
                        <TableCell><A href={edgarUrl(co.cik, v.accn)}><Code>{v.accn}</Code></A></TableCell><TableCell>{v.frame ?? ""}</TableCell><TableCell>{v.chosen && <Badge>used</Badge>}</TableCell>
                      </TableRow>
                    ))}
                  </DataTable>
                </div>
              ))}
            </Step>
            <Step n={2} title={`Arithmetic (${METHOD[tr.method] ?? tr.method})`}>
              <p className="font-mono text-[13px] leading-relaxed">{arith}</p>
              <p className="text-muted-foreground">{META.methods[tr.method] ?? ""}</p>
            </Step>
            {row && (
              <>
                <Step n={3} title="Calendar placement">
                  <p>Fiscal period {row.period_start} to {row.period_end} ({row.days} days) is FY{row.fiscal_year} Q{row.fiscal_quarter} for {co.name} (fiscal year ends {co.fiscal_year_end?.slice(0, 2)}/{co.fiscal_year_end?.slice(2)}). {row.days_outside_cal_q ? `${row.days - row.days_outside_cal_q} of its days fall in ${qLabel(row.cal_q)}, so it is placed there.` : `It matches ${qLabel(row.cal_q)} exactly.`}</p>
                </Step>
                <Step n={4} title="Clean row">
                  <pre className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs">{JSON.stringify({ ticker: row.ticker, metric: row.metric, cal_q: row.cal_q, value: row.value, method: row.method, concept: row.concept, period: `${row.period_start}..${row.period_end}`, fiscal: `FY${row.fiscal_year} Q${row.fiscal_quarter}`, form: row.form, accession: row.accession, filed: row.filed, vintages: row.vintages, restated: row.restated }, null, 2)}</pre>
                </Step>
              </>
            )}
          </div>
        )}
      </Section>
    </div>
  )
}
