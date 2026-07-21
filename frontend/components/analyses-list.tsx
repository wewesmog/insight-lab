"use client"

import Link from "next/link"
import { useState } from "react"
import { Loader2, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { deleteAnalysis } from "@/lib/api"
import type { AnalysisStatus, AnalysisSummary } from "@/lib/types"
import { cn } from "@/lib/utils"

function statusVariant(status: AnalysisStatus) {
  if (status === "ready") return "success" as const
  if (status === "failed") return "destructive" as const
  if (status === "running") return "warning" as const
  return "secondary" as const
}

function statusLabel(status: AnalysisStatus) {
  if (status === "queued") return "Queued"
  if (status === "running") return "Running"
  if (status === "ready") return "Ready"
  return "Failed"
}

function formatShortDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function displayName(name: string) {
  return name.replace(/\.csv$/i, "")
}

function apiErrorMessage(err: unknown): string {
  if (!(err instanceof Error)) return "Delete failed"
  try {
    const parsed = JSON.parse(err.message) as { detail?: string }
    if (typeof parsed.detail === "string") return parsed.detail
  } catch {
    /* not JSON */
  }
  return err.message || "Delete failed"
}

export function AnalysesSidebarList({
  items,
  loading,
  selectedId,
  className,
  onDeleted,
}: {
  items: AnalysisSummary[]
  loading?: boolean
  selectedId?: string | null
  className?: string
  onDeleted?: (analysisId: string) => void
}) {
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmItem, setConfirmItem] = useState<AnalysisSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleDelete(analysisId: string) {
    setError(null)
    setDeletingId(analysisId)
    try {
      await deleteAnalysis(analysisId)
      setConfirmItem(null)
      onDeleted?.(analysisId)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) {
    return (
      <div className={cn("flex items-center gap-2 px-3 py-6 text-xs text-muted-foreground", className)}>
        <Loader2 className="size-3.5 animate-spin" />
        Loading…
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <p className={cn("px-3 py-6 text-xs text-muted-foreground", className)}>
        No analyses yet. Upload a CSV to start.
      </p>
    )
  }

  const deleting = deletingId !== null

  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      {error ? (
        <p className="shrink-0 border-b border-destructive/30 bg-destructive/5 px-3 py-2 text-[10px] text-destructive">
          {error}
        </p>
      ) : null}
      <ul className="min-h-0 flex-1 divide-y divide-border/60 overflow-y-auto">
        {items.map((item) => {
          const active = item.id === selectedId
          return (
            <li key={item.id}>
              <div
                className={cn(
                  "flex border-l-2 transition",
                  active
                    ? "border-l-primary bg-muted/70"
                    : "border-l-transparent hover:bg-muted/35"
                )}
              >
                <Link href={`/analyses/${item.id}`} className="min-w-0 flex-1 px-3 py-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <p className="line-clamp-2 text-xs font-medium leading-snug">
                      {displayName(item.name)}
                    </p>
                    <Badge
                      variant={statusVariant(item.status)}
                      className="shrink-0 px-1.5 py-0 text-[10px]"
                    >
                      {statusLabel(item.status)}
                    </Badge>
                  </div>
                  <p className="mt-1 text-[10px] text-muted-foreground">
                    {formatShortDate(item.created_at)}
                    <span> · </span>
                    {item.total_rows} verbatims
                    {item.status === "running" || item.status === "queued" ? (
                      <span className="tabular-nums"> · {item.progress_pct.toFixed(0)}%</span>
                    ) : null}
                  </p>
                  {(item.status === "running" || item.status === "queued") && (
                    <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${Math.max(item.progress_pct, 4)}%` }}
                      />
                    </div>
                  )}
                  {item.status === "failed" && item.error ? (
                    <p className="mt-1 line-clamp-2 text-[10px] text-destructive">{item.error}</p>
                  ) : null}
                </Link>
                <button
                  type="button"
                  title="Delete analysis"
                  aria-label={`Delete ${displayName(item.name)}`}
                  disabled={deleting}
                  className="shrink-0 self-start px-2 py-2.5 text-muted-foreground transition hover:text-destructive disabled:opacity-50"
                  onClick={() => {
                    setError(null)
                    setConfirmItem(item)
                  }}
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            </li>
          )
        })}
      </ul>

      <Dialog
        open={confirmItem !== null}
        onOpenChange={(open) => {
          if (!open && !deleting) setConfirmItem(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete analysis</DialogTitle>
            <DialogDescription>
              {confirmItem
                ? `Delete “${displayName(confirmItem.name)}”? This cannot be undone. Consider downloading the report before deleting.`
                : "Are you sure you want to delete this analysis?"}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" disabled={deleting} />}>
              Cancel
            </DialogClose>
            <Button
              variant="destructive"
              disabled={deleting || !confirmItem}
              onClick={() => {
                if (confirmItem) void handleDelete(confirmItem.id)
              }}
            >
              {deleting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  Deleting…
                </>
              ) : (
                "Delete"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
