import { Code, Section } from "@/components/bits"
import { META, METHOD, METRICS } from "@/data"

const Defs = ({ items }: { items: [string, React.ReactNode][] }) => (
  <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[14rem_1fr]">
    {items.map(([k, v]) => <div key={k} className="contents"><dt className="font-medium">{k}</dt><dd className="text-muted-foreground">{v}</dd></div>)}
  </dl>
)

export function Method() {
  const steps: [string, React.ReactNode][] = [
    ["Ingest", "Resolve tickers to CIKs, then pull companyfacts and submissions for each company (the Admin tab has every call)."],
    ["Fill gaps", "If a recent 10-Q/10-K is on EDGAR but not yet in companyfacts, parse that filing's instance XML (non-dimensional USD facts only)."],
    ["Vintages", "One period appears in many filings. Keep the latest-filed value; record the first and the count."],
    ["Discrete quarters", "Three-month facts as filed; year-to-date cash-flow lines differenced; Q4 = 10-K year minus nine months."],
    ["Cleaning", "Drop \"quarters\" that carry a full-year value (a filer error in four Oracle 10-Ks). Rebuild Q4 from restated quarters when the nine-month figure is on an older basis. Merge a predecessor CIK's history after a reorganization (ExxonMobil, 2026)."],
    ["Calendar alignment", `${META.calendar_rule} When two fiscal quarters share a calendar quarter (Costco's 12/12/12/16-week year), the later one moves to its next-best quarter if no other period claims it.`],
    ["Tag choice and metrics", "See \"How it was found & parsed\" and the definitions below."],
    ["Checks", "Signs, quarter length, jumps above 3×, quarters adding up to filed totals, restatements, tag switches, coverage with a reason for every gap."],
  ]
  return (
    <div className="grid gap-10">
      <Section title="How the data is made" description={`${META.source}, with a fallback to each filing's XBRL instance XML. One command rebuilds everything.`}>
        <ol className="grid gap-2 text-sm">
          {steps.map(([k, v], i) => (
            <li key={k} className="flex gap-3"><span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium tabular-nums">{i + 1}</span><span><span className="font-medium">{k}.</span> <span className="text-muted-foreground">{v}</span></span></li>
          ))}
        </ol>
      </Section>
      <Section title="Metrics">
        <Defs items={[...Object.entries(META.metrics as Record<string, string>).filter(([k]) => METRICS[k]).map(([k, v]) => [METRICS[k].label, v] as [string, string]),
          ["Ratios", "Capex ÷ revenue and opex ÷ revenue are computed in the explorer from same-period values."]]} />
      </Section>
      <Section title="Methods">
        <Defs items={Object.entries(META.methods as Record<string, string>).map(([k, v]) => [METHOD[k] ?? k, v])} />
      </Section>
      <Section title="Tags tried, in priority order">
        <Defs items={Object.entries(META.concept_candidates as Record<string, string[]>).map(([k, v]) => [k.replace(/_/g, " "), <span className="flex flex-wrap gap-1">{v.map((c) => <Code key={c}>{c}</Code>)}</span>])} />
      </Section>
    </div>
  )
}
