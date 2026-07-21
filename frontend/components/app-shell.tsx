"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useCallback, useEffect, useMemo, useState } from "react"
import {
  ChevronLeft,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
  Radio,
} from "lucide-react"

import { AnalysesSidebarList } from "@/components/analyses-list"
import { ShellChromeProvider } from "@/components/shell-chrome"
import { SidebarUpload } from "@/components/sidebar-upload"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { getApiBase, getHealth, listAnalyses } from "@/lib/api"
import type { AnalysisSummary } from "@/lib/types"
import { cn } from "@/lib/utils"

const PAGE_SIZE = 15
const SIDEBAR_KEY = "insight-lab-sidebar-open"

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const selectedId = useMemo(() => {
    const match = pathname.match(/^\/analyses\/([^/]+)/)
    return match?.[1] ?? null
  }, [pathname])

  const [items, setItems] = useState<AnalysisSummary[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [apiOk, setApiOk] = useState<boolean | null>(null)
  const [llmEnabled, setLlmEnabled] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(SIDEBAR_KEY)
      if (raw === "0") setSidebarOpen(false)
    } catch {
      /* ignore */
    }
  }, [])

  function toggleSidebar() {
    setSidebarOpen((prev) => {
      const next = !prev
      try {
        window.localStorage.setItem(SIDEBAR_KEY, next ? "1" : "0")
      } catch {
        /* ignore */
      }
      return next
    })
  }

  const refresh = useCallback(async (nextPage: number) => {
    try {
      const data = await listAnalyses(nextPage, PAGE_SIZE)
      setItems(data.items)
      setTotal(data.total)
      setPage(data.page)
    } catch {
      /* ignore while API offline */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    getHealth()
      .then((h) => {
        setApiOk(true)
        setLlmEnabled(h.llm_enabled)
      })
      .catch(() => setApiOk(false))
  }, [])

  useEffect(() => {
    void refresh(page)
  }, [page, refresh])

  useEffect(() => {
    const hasActive = items.some((i) => i.status === "queued" || i.status === "running")
    if (!hasActive) return
    const id = window.setInterval(() => void refresh(page), 2500)
    return () => window.clearInterval(id)
  }, [items, page, refresh])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <ShellChromeProvider value={{ sidebarOpen, toggleSidebar }}>
      <div className="flex h-dvh overflow-hidden bg-[oklch(0.97_0.006_75)]">
        <aside
          className={cn(
            "flex h-full shrink-0 flex-col overflow-hidden border-r border-border/70 bg-[oklch(0.995_0.004_80)] transition-[width] duration-200 ease-out print:hidden",
            sidebarOpen ? "w-72" : "w-0 border-r-0"
          )}
        >
          <div
            className={cn(
              "flex h-full w-72 flex-col overflow-hidden",
              !sidebarOpen && "pointer-events-none opacity-0"
            )}
          >
            <div className="shrink-0 border-b border-border/70 px-4 py-4">
              <div className="flex items-start justify-between gap-2">
                <Link href="/" className="block min-w-0">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    CVM-AI
                  </p>
                  <h1 className="font-serif text-lg font-semibold tracking-tight">Insight Lab</h1>
                </Link>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="shrink-0"
                  onClick={toggleSidebar}
                  title="Hide sidebar"
                  aria-label="Hide sidebar"
                >
                  <PanelLeftClose className="size-4" />
                </Button>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {apiOk === null ? (
                  <Badge variant="outline">API…</Badge>
                ) : apiOk ? (
                  <Badge variant="success">
                    <Radio className="mr-1 size-3" />
                    Online
                  </Badge>
                ) : (
                  <Badge variant="destructive">Offline</Badge>
                )}
                <Badge variant={llmEnabled ? "success" : "destructive"}>
                  {llmEnabled ? "LLM" : "No key"}
                </Badge>
              </div>
              <p className="mt-2 truncate text-[10px] text-muted-foreground" title={getApiBase()}>
                {getApiBase()}
              </p>
            </div>

            <div className="shrink-0 border-b border-border/70 px-3 py-3">
              <SidebarUpload
                busy={!llmEnabled || apiOk === false}
                onAnalysisStarted={(analysis) => {
                  setPage(1)
                  setItems((prev) =>
                    [analysis, ...prev.filter((p) => p.id !== analysis.id)].slice(0, PAGE_SIZE)
                  )
                  setTotal((t) => t + 1)
                  router.push(`/analyses/${analysis.id}`)
                  void refresh(1)
                }}
              />
            </div>

            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <div className="flex shrink-0 items-center justify-between px-3 py-2">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  Analyses
                </p>
                <span className="text-[11px] tabular-nums text-muted-foreground">{total}</span>
              </div>
              <AnalysesSidebarList
                items={items}
                loading={loading}
                selectedId={selectedId}
                className="min-h-0 flex-1 overflow-hidden"
                onDeleted={(analysisId) => {
                  setItems((prev) => prev.filter((item) => item.id !== analysisId))
                  setTotal((t) => Math.max(0, t - 1))
                  if (selectedId === analysisId) {
                    router.push("/")
                  }
                  void refresh(page)
                }}
              />
              {totalPages > 1 ? (
                <div className="flex shrink-0 items-center justify-between gap-2 border-t border-border/70 px-2 py-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    <ChevronLeft className="size-4" />
                  </Button>
                  <span className="text-[11px] tabular-nums text-muted-foreground">
                    {page} / {totalPages}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  >
                    <ChevronRight className="size-4" />
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
        </aside>

        <div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {children}
        </div>
      </div>
    </ShellChromeProvider>
  )
}
