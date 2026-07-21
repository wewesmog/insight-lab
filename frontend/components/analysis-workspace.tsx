"use client"

import { Loader2, PanelLeftOpen } from "lucide-react"

import { AnalysisReportView } from "@/components/analysis-report"
import { useShellChrome } from "@/components/shell-chrome"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import type { AnalysisReport, AnalysisStatus } from "@/lib/types"

function statusLabel(status: AnalysisStatus) {
  if (status === "queued") return "Queued"
  if (status === "running") return "Running"
  if (status === "ready") return "Ready"
  return "Failed"
}

function displayName(name: string) {
  return name.replace(/\.csv$/i, "")
}

function progressStage(pct: number) {
  if (pct < 5) return "Queued — starting pipeline"
  if (pct < 85) return "Extracting insights per verbatim"
  if (pct < 95) return "Rolling up metrics & deep dive"
  return "Writing executive commentary"
}

export function AnalysisWorkspace({
  report,
  error,
}: {
  report: AnalysisReport | null
  error?: string | null
}) {
  const { sidebarOpen, toggleSidebar } = useShellChrome()

  if (error) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <WorkspaceHeader
          title="Unable to load"
          sidebarOpen={sidebarOpen}
          onOpenSidebar={toggleSidebar}
        />
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-8 lg:px-10">
          <Card className="mx-auto max-w-lg shadow-none">
            <CardContent className="space-y-2 py-8">
              <p className="font-semibold text-destructive">Couldn’t load this analysis</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <WorkspaceHeader
          title="Loading…"
          sidebarOpen={sidebarOpen}
          onOpenSidebar={toggleSidebar}
        />
        <div className="flex min-h-0 flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Loading analysis…
        </div>
      </div>
    )
  }

  const status = report.analysis.status
  const title = displayName(report.analysis.name)

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <WorkspaceHeader
        title={title}
        sidebarOpen={sidebarOpen}
        onOpenSidebar={toggleSidebar}
        trailing={
          <div className="flex flex-wrap items-center gap-2">
            {status === "ready" ? (
              <Badge variant="outline" className="tabular-nums">
                {report.analysis.analyzed_count || report.analysis.total_rows} verbatims
              </Badge>
            ) : null}
            <Badge
              variant={
                status === "ready" ? "success" : status === "failed" ? "destructive" : "warning"
              }
            >
              {statusLabel(status)}
            </Badge>
          </div>
        }
      />

      <div
        data-report-scroll
        className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-10 print:overflow-visible print:px-0"
      >
        {status === "queued" || status === "running" ? (
          <Card className="mx-auto max-w-xl shadow-none">
            <CardContent className="space-y-5 py-14 text-center">
              <Loader2 className="mx-auto size-9 animate-spin text-primary" />
              <div>
                <p className="font-serif text-2xl font-semibold tracking-tight">
                  {status === "queued" ? "Queued for analysis" : "Building your briefing"}
                </p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {progressStage(report.analysis.progress_pct)}. You can leave this page — progress
                  stays in the sidebar.
                </p>
              </div>
              <div className="mx-auto h-2.5 max-w-md overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${Math.max(report.analysis.progress_pct, 3)}%` }}
                />
              </div>
              <p className="text-xs tabular-nums text-muted-foreground">
                {report.analysis.processed_rows} / {report.analysis.total_rows} verbatims ·{" "}
                {report.analysis.progress_pct.toFixed(0)}%
              </p>
            </CardContent>
          </Card>
        ) : status === "failed" ? (
          <Card className="mx-auto max-w-xl shadow-none">
            <CardContent className="space-y-2 py-10">
              <p className="font-semibold text-destructive">Analysis failed</p>
              <p className="text-sm text-muted-foreground">
                {report.analysis.error || "Unknown error — try uploading again."}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="rounded-2xl border border-border/60 bg-card px-5 py-8 shadow-[0_12px_40px_-24px_rgba(40,30,20,0.35)] sm:px-8 lg:px-12 print:border-0 print:shadow-none print:px-0">
            <AnalysisReportView report={report} />
          </div>
        )}
      </div>
    </div>
  )
}

function WorkspaceHeader({
  title,
  sidebarOpen,
  onOpenSidebar,
  trailing,
}: {
  title: string
  sidebarOpen: boolean
  onOpenSidebar: () => void
  trailing?: React.ReactNode
}) {
  return (
    <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border/70 bg-[oklch(0.995_0.003_80)/0.92] px-4 py-4 backdrop-blur sm:px-6 lg:px-10 print:hidden">
      <div className="flex min-w-0 items-center gap-3">
        {!sidebarOpen ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onOpenSidebar}
            title="Show analyses sidebar"
            aria-label="Show analyses sidebar"
          >
            <PanelLeftOpen className="size-4" />
            Analyses
          </Button>
        ) : null}
        <div className="min-w-0">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Management report
          </p>
          <h2 className="truncate font-serif text-xl font-semibold tracking-tight sm:text-2xl">
            {title}
          </h2>
        </div>
      </div>
      {trailing}
    </header>
  )
}
