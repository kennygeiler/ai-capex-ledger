import { Code, DataTable, Field, Pick, Section, Seg, SevBadge, Stat } from "@/components/bits"
import { TableCell, TableRow } from "@/components/ui/table"
import { COS, inUni, ISSUES, META, UNIS, WINDOW, YEARS } from "@/data"
import { qLabel } from "@/lib/format"
import type { SetState, State } from "@/state"

const Cov = ({ n, of }: { n: number; of: number }) => (
  <span className="inline-flex rounded-md px-1.5 py-0.5 font-mono tabular-nums"
    style={{ background: `color-mix(in oklab, var(--warn) ${n >= of ? 0 : 20 + (of - n) * (60 / of)}%, transparent)` }}>{n}/{of}</span>
)

export function Quality({ s, set }: { s: State; set: SetState }) {
  const Q = META.quality, list0 = COS.filter((c) => inUni(c, s.uni)), tset = new Set(list0.map((c) => c.ticker))
  const checks = [...new Set(ISSUES.map((i) => i.check))].sort()
  const list = ISSUES.filter((i) => tset.has(i.ticker) && (s.sev === "all" || i.severity === s.sev) && (s.chk === "all" || i.check === s.chk) && (s.tk === "all" || i.ticker === s.tk))
  const full = (m: string) => list0.filter((c) => c.coverage[m] === 8).length
  return (
    <div className="grid gap-10">
      <Section title="Data quality" description={<>Every check the pipeline ran, and every gap with its reason. Quarters {qLabel(WINDOW[0])} to {qLabel(WINDOW.at(-1))}; fiscal years {YEARS[0]} to {YEARS.at(-1)}.</>}
        actions={<Seg value={s.uni} onChange={(v) => set({ uni: v })} options={UNIS} />}>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-7">
          <Stat n={list0.length} l="companies" />
          <Stat n={full("revenue")} l="revenue, all 8 quarters" />
          <Stat n={full("capex")} l="capex, all 8 quarters" />
          <Stat n={full("opex")} l="opex, all 8 quarters" />
          <Stat n={`${Q.tiling_checks - Q.tiling_failures}/${Q.tiling_checks}`} l="quarter sets add up to filed totals" />
          <Stat n={Q.errors} l="errors" tone={Q.errors ? "err" : undefined} />
          <Stat n={Q.warnings} l="warnings" tone={Q.warnings ? "warn" : undefined} />
        </div>
      </Section>
      <Section title="Coverage" description="Quarters of 8, then fiscal years of 5.">
        <DataTable head={["Company", "Sector", "Revenue", "Capex", "Opex", "Revenue tag", "Capex tag", "FY ends"]}>
          {list0.map((c) => (
            <TableRow key={c.ticker}>
              <TableCell><span className="font-mono font-medium">{c.ticker}</span> <span className="text-muted-foreground">{c.name}</span></TableCell>
              <TableCell className="text-muted-foreground">{c.sector}</TableCell>
              {["revenue", "capex", "opex"].map((m) => <TableCell key={m}><span className="flex gap-1"><Cov n={c.coverage[m]} of={8} /><Cov n={c.coverage_annual[m]} of={5} /></span></TableCell>)}
              <TableCell><Code>{c.concepts.revenue[0] ?? "–"}</Code></TableCell>
              <TableCell><Code>{c.concepts.capex[0] ?? "–"}</Code></TableCell>
              <TableCell>{c.fiscal_year_end ? `${c.fiscal_year_end.slice(0, 2)}/${c.fiscal_year_end.slice(2)}` : "–"}</TableCell>
            </TableRow>
          ))}
        </DataTable>
      </Section>
      <Section title={`Issues (${list.length})`}>
        <div className="grid gap-3 sm:grid-cols-3 sm:max-w-2xl">
          <Field label="Severity"><Pick label="Severity" value={s.sev} onChange={(v) => set({ sev: v })} options={[["all", "All severities"], ["error", "error"], ["warn", "warn"], ["info", "info"]]} /></Field>
          <Field label="Check"><Pick label="Check" value={s.chk} onChange={(v) => set({ chk: v })} options={[["all", "All checks"], ...checks.map((c) => [c, c] as [string, string])]} /></Field>
          <Field label="Company"><Pick label="Company" value={s.tk} onChange={(v) => set({ tk: v })} options={[["all", "All companies"], ...list0.map((c) => [c.ticker, c.ticker] as [string, string])]} /></Field>
        </div>
        <DataTable head={["Severity", "Check", "Company", "Metric", "Quarter", "Detail"]}>
          {list.slice(0, 400).map((i, n) => (
            <TableRow key={n}>
              <TableCell><SevBadge s={i.severity} /></TableCell><TableCell>{i.check}</TableCell><TableCell className="font-mono">{i.ticker}</TableCell>
              <TableCell>{i.metric}</TableCell><TableCell>{i.cal_q ? qLabel(i.cal_q) : "–"}</TableCell><TableCell className="whitespace-normal">{i.message}</TableCell>
            </TableRow>
          ))}
          {!list.length && <TableRow><TableCell colSpan={6} className="text-muted-foreground">Nothing matches.</TableCell></TableRow>}
        </DataTable>
      </Section>
      <Section title="Left out">
        <ul className="grid gap-1 pl-5 text-sm [&>li]:list-disc">
          {META.excluded.map((e: Record<string, string>) => <li key={e.ticker}><span className="font-medium">{e.ticker}</span> ({e.name}): {e.reason}</li>)}
        </ul>
      </Section>
    </div>
  )
}
