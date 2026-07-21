"use client"

import { FileSpreadsheet, PanelLeftOpen, Sparkles } from "lucide-react"

import { useShellChrome } from "@/components/shell-chrome"
import { Button } from "@/components/ui/button"

export default function HomePage() {
  const { sidebarOpen, toggleSidebar } = useShellChrome()

  return (
    <main className="flex h-full flex-col overflow-hidden">
      <header className="flex shrink-0 items-center gap-3 border-b border-border/70 bg-[oklch(0.995_0.003_80)/0.92] px-4 py-4 sm:px-6 lg:px-10 print:hidden">
        {!sidebarOpen ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={toggleSidebar}
            aria-label="Show analyses sidebar"
          >
            <PanelLeftOpen className="size-4" />
            Analyses
          </Button>
        ) : null}
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Insight Lab
          </p>
          <h2 className="font-serif text-xl font-semibold tracking-tight">Workspace</h2>
        </div>
      </header>

      <div className="flex flex-1 items-center justify-center px-6 py-10">
        <div className="w-full max-w-lg space-y-8 text-center">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Your analyses
            </p>
            <h2 className="mt-2 font-serif text-3xl font-semibold tracking-tight">
              Select an analysis
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Upload a CSV in the sidebar to start a briefing, or open an existing job to watch
              progress or read the report.
            </p>
          </div>

          <div className="grid gap-3 text-left sm:grid-cols-2">
            <div className="rounded-xl border border-border/70 bg-card/80 px-4 py-3">
              <FileSpreadsheet className="size-4 text-primary" />
              <p className="mt-2 text-sm font-medium">CSV in</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Needs a <code className="text-[10px]">verbatim</code> column. Extra fields power
                the deep dive.
              </p>
            </div>
            <div className="rounded-xl border border-border/70 bg-card/80 px-4 py-3">
              <Sparkles className="size-4 text-primary" />
              <p className="mt-2 text-sm font-medium">Briefing out</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Management commentary, scorecards, themes — export PDF or CSV when ready.
              </p>
            </div>
          </div>

          {!sidebarOpen ? (
            <Button type="button" onClick={toggleSidebar}>
              <PanelLeftOpen className="size-4" />
              Open sidebar to upload
            </Button>
          ) : null}
        </div>
      </div>
    </main>
  )
}
