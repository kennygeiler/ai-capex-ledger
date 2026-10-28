import { Code, DataTable, Section, Seg, Stat } from "@/components/bits"
import { TableCell, TableRow } from "@/components/ui/table"
import { COS, cikBy, FACTS, META, PULL } from "@/data"
import { bytes, qLabel } from "@/lib/format"
import type { SetState, State } from "@/state"

const A = ({ href, children }: { href: string; children: React.ReactNode }) =>
  <a href={href} target="_blank" rel="noopener" className="underline decoration-muted-foreground/40 underline-offset-2 hover:decoration-foreground">{children}</a>

const ENDPOINTS = [
  ["https://www.sec.gov/files/company_tickers.json", "Ticker → CIK lookup for every SEC registrant. Resolves the 113 tickers at run time."],
  ["https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json", "Every XBRL fact a company has filed, by concept, with period, value, form, accession and filing date. The main source."],
  ["https://data.sec.gov/submissions/CIK##########.json", "Filing history: forms, filing dates, report periods, fiscal year end, SIC code, exchanges."],
  ["https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json → *_htm.xml", "Fallback: a filing's own XBRL instance XML, parsed when companyfacts hasn't caught up with a new 10-Q/10-K."],
]

export function Admin({ s, set }: { s: State; set: SetState }) {
  const P = PULL, logs = (P.log as Record<string, any>[]).filter((x) => s.net === "all" || x.source === s.net)
  const tickerOf = (url: string) => { const m = url.match(/CIK0*(\d+)|\/data\/(\d+)\//); return m ? cikBy.get(m[1] ?? m[2]) ?? "" : url.includes("company_tickers") ? "*" : "" }
  const lastQ = new Map<string, string>()
  for (const f of FACTS) if (f.metric === "revenue" && f.period_type === "quarter" && (lastQ.get(f.ticker) ?? "") < f.cal_q!) lastQ.set(f.ticker, f.cal_q!)
  return (
    <div className="grid gap-10">
      <Section title="Last data pull" description={<>Rate limit: {P.rate_limit} (SEC allows 10). User-Agent: {P.user_agent}. Raw responses are kept unchanged in <Code>data/raw/</Code> with their SHA-256, so any number can be re-derived offline.</>}>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-7">
          <Stat n={P.finished_at.slice(0, 16).replace("T", " ")} l="finished (UTC)" />
          <Stat n={`${P.seconds}s`} l="run time" />
          <Stat n={P.network_requests} l="network requests" />
          <Stat n={P.cache_reads} l="cache reads (under 24h old)" />
          <Stat n={bytes(P.bytes_downloaded)} l="downloaded this run" />
          <Stat n={P.http_errors} l="HTTP errors" tone={P.http_errors ? "err" : undefined} />
          <Stat n={P.failures.length} l="companies failed" tone={P.failures.length ? "err" : undefined} />
        </div>
        <pre className="overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs">{`python3 -m pipeline.run             # refresh anything older than 24h
python3 -m pipeline.run --refresh   # re-download everything
cd web && pnpm build                # rebuild explorer/standalone.html`}</pre>
        {P.failures.length > 0 && <ul className="text-sm">{P.failures.map((f: Record<string, string>) => <li key={f.ticker}>{f.ticker} ({f.stage}): {f.error}</li>)}</ul>}
      </Section>
      <Section title="API connections">
        <DataTable head={["Endpoint", "What it gives"]}>
          {ENDPOINTS.map(([u, d]) => <TableRow key={u}><TableCell><Code>{u}</Code></TableCell><TableCell className="whitespace-normal">{d}</TableCell></TableRow>)}
        </DataTable>
      </Section>
      <Section title="Company freshness">
        <DataTable head={["Company", "CIK", "Latest 10-Q / 10-K", "Period", "Filed", "Latest quarter in data", "Read from", "Raw file fetched"]}>
          {COS.map((c) => {
            const f = c.recent_filings[0] ?? {}, raw = META.raw_files.find((r: Record<string, string>) => r.ticker === c.ticker && r.kind === "companyfacts")
            const xml = (c.gap_fills ?? []).filter((g: Record<string, string>) => g.status === "parsed").length
            return (
              <TableRow key={c.ticker}>
                <TableCell><span className="font-mono font-medium">{c.ticker}</span> <span className="text-muted-foreground">{c.name}</span></TableCell>
                <TableCell className="tabular-nums">{c.cik}</TableCell><TableCell>{f.form ?? "–"}</TableCell><TableCell>{f.period ?? "–"}</TableCell><TableCell>{f.filed ?? "–"}</TableCell>
                <TableCell>{lastQ.get(c.ticker) ? qLabel(lastQ.get(c.ticker)) : "–"}</TableCell><TableCell>{xml ? `companyfacts + ${xml} instance XML` : "companyfacts"}</TableCell>
                <TableCell className="text-muted-foreground">{raw ? raw.fetched_at.slice(0, 16).replace("T", " ") : "–"}</TableCell>
              </TableRow>
            )
          })}
        </DataTable>
      </Section>
      <Section title={`Request log (${logs.length})`} actions={<Seg value={s.net} onChange={(v) => set({ net: v })} options={{ network: "Network only", cache: "Cache reads", all: "All" }} />}>
        <DataTable head={["Time (UTC)", "Source", "Status", "ms", "Size", "Company", "URL"]}>
          {logs.map((x, i) => (
            <TableRow key={i}>
              <TableCell className="text-muted-foreground tabular-nums">{x.at.slice(11, 19)}</TableCell><TableCell>{x.source}{x.attempt > 1 ? ` (try ${x.attempt})` : ""}</TableCell>
              <TableCell className={x.error ? "text-err" : ""}>{x.status ?? "–"}{x.error ? ` ${x.error}` : ""}</TableCell><TableCell className="tabular-nums">{x.ms}</TableCell>
              <TableCell className="tabular-nums">{bytes(x.bytes)}</TableCell><TableCell className="font-mono">{tickerOf(x.url)}</TableCell><TableCell><Code>{x.url.replace("https://", "")}</Code></TableCell>
            </TableRow>
          ))}
          {!logs.length && <TableRow><TableCell colSpan={7} className="text-muted-foreground">Nothing in this view. The last run read everything from cache; switch to "All".</TableCell></TableRow>}
        </DataTable>
      </Section>
      <Section title="Raw files">
        <DataTable head={["Company", "File", "Fetched", "Size", "SHA-256"]}>
          {META.raw_files.map((r: Record<string, any>, i: number) => (
            <TableRow key={i}><TableCell className="font-mono">{r.ticker}</TableCell><TableCell><A href={r.url}>{r.kind}</A></TableCell><TableCell className="text-muted-foreground">{r.fetched_at}</TableCell>
              <TableCell className="tabular-nums">{bytes(r.bytes)}</TableCell><TableCell><Code>{r.sha256.slice(0, 16)}…</Code></TableCell></TableRow>
          ))}
        </DataTable>
      </Section>
    </div>
  )
}
