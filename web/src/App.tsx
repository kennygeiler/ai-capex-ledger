import { useState } from "react"
import { Lineage } from "@/components/lineage"
import { Toaster } from "@/components/ui/sonner"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TooltipProvider } from "@/components/ui/tooltip"
import { COS, PULL } from "@/data"
import { Admin } from "@/pages/admin"
import { Explore } from "@/pages/explore"
import { Found } from "@/pages/found"
import { Method } from "@/pages/method"
import { Quality } from "@/pages/quality"
import { useUrlState } from "@/state"

const TABS = { explore: "Explore", quality: "Data quality", found: "How it was found & parsed", admin: "Admin", sources: "Method" }

export default function App() {
  const [s, set] = useUrlState()
  const [target, setTarget] = useState<{ t: string; p: string } | null>(null)
  const tab = s.tab in TABS ? s.tab : "explore"
  return (
    <TooltipProvider>
      <Tabs value={tab} onValueChange={(v) => { set({ tab: v }); scrollTo(0, 0) }} className="min-h-svh gap-0">
        <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
          <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5 sm:px-6">
            <div className="flex items-center gap-2 font-semibold tracking-tight">
              <span className="flex size-6 items-center justify-center rounded-md bg-primary text-[11px] font-bold text-primary-foreground">CL</span>
              Capex Ledger
            </div>
            <div className="max-w-full overflow-x-auto">
              <TabsList>{Object.entries(TABS).map(([k, v]) => <TabsTrigger key={k} value={k}>{v}</TabsTrigger>)}</TabsList>
            </div>
            <span className="ml-auto text-xs text-muted-foreground">SEC EDGAR, pulled {PULL.finished_at.slice(0, 16).replace("T", " ")} UTC · {COS.length} companies</span>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1500px] px-4 py-6 sm:px-6">
          <TabsContent value="explore"><Explore s={s} set={set} open={(t, p) => setTarget({ t, p })} /></TabsContent>
          <TabsContent value="quality"><Quality s={s} set={set} /></TabsContent>
          <TabsContent value="found"><Found s={s} set={set} /></TabsContent>
          <TabsContent value="admin"><Admin s={s} set={set} /></TabsContent>
          <TabsContent value="sources"><Method /></TabsContent>
        </main>
      </Tabs>
      <Lineage s={s} set={set} target={target} onClose={() => setTarget(null)} />
      <Toaster position="bottom-center" />
    </TooltipProvider>
  )
}
