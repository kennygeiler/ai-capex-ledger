// Small shared pieces built from shadcn/ui primitives.
import type { ReactNode } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { cn } from "@/lib/utils"

export function Seg({ value, onChange, options, className }: { value: string; onChange: (v: string) => void; options: Record<string, string>; className?: string }) {
  return (
    <ToggleGroup type="single" variant="outline" size="sm" value={value} onValueChange={(v) => v && onChange(v)} className={cn("flex-wrap", className)}>
      {Object.entries(options).map(([k, l]) => <ToggleGroupItem key={k} value={k} className="px-2.5 text-xs">{l}</ToggleGroupItem>)}
    </ToggleGroup>
  )
}

export function Pick({ value, onChange, options, label, className }: { value: string; onChange: (v: string) => void; options: [string, string][]; label?: string; className?: string }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger size="sm" aria-label={label} className={cn("w-full", className)}><SelectValue /></SelectTrigger>
      <SelectContent className="max-h-80">{options.map(([k, l]) => <SelectItem key={k} value={k}>{l}</SelectItem>)}</SelectContent>
    </Select>
  )
}

export function Field({ label, children, note }: { label: string; children: ReactNode; note?: ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <Label className="text-xs font-medium text-muted-foreground">{label}</Label>
      {children}
      {note && <p className="text-xs text-muted-foreground">{note}</p>}
    </div>
  )
}

export function Stat({ n, l, tone }: { n: ReactNode; l: string; tone?: "warn" | "err" }) {
  return (
    <Card size="sm" className="gap-1 py-3">
      <CardContent className="px-4">
        <div className={cn("text-2xl font-semibold tabular-nums tracking-tight", tone === "warn" && "text-warn", tone === "err" && "text-err")}>{n}</div>
        <div className="text-xs text-muted-foreground">{l}</div>
      </CardContent>
    </Card>
  )
}

export function Section({ title, description, children, id, actions }: { title: string; description?: ReactNode; children: ReactNode; id?: string; actions?: ReactNode }) {
  return (
    <section id={id} className="grid gap-3 scroll-mt-20">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="grid gap-1">
          <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
          {description && <div className="max-w-3xl text-sm text-muted-foreground">{description}</div>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  )
}

export const Code = ({ children }: { children: ReactNode }) => <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.8em]">{children}</code>

export function Swatch({ color }: { color: string }) {
  return <span className="inline-block size-2.5 shrink-0 rounded-[3px]" style={{ background: color }} />
}

export const SevBadge = ({ s }: { s: string }) => (
  <span className={cn("inline-flex rounded-md px-1.5 py-0.5 text-xs font-medium",
    s === "error" ? "bg-err/15 text-err" : s === "warn" ? "bg-warn/15 text-warn" : "bg-muted text-muted-foreground")}>{s}</span>
)

import { Table, TableBody, TableHead, TableHeader, TableRow } from "@/components/ui/table"
export function DataTable({ head, children, className }: { head: ReactNode[]; children: ReactNode; className?: string }) {
  return (
    <div className={cn("overflow-x-auto rounded-lg border", className)}>
      <Table className="text-xs">
        <TableHeader><TableRow className="bg-muted/50 hover:bg-muted/50">{head.map((h, i) => <TableHead key={i}>{h}</TableHead>)}</TableRow></TableHeader>
        <TableBody>{children}</TableBody>
      </Table>
    </div>
  )
}
