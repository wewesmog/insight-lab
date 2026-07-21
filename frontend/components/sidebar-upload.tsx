"use client"

import { FileUp, Loader2, X } from "lucide-react"
import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { uploadAndStartAnalysis } from "@/lib/api"
import type { AnalysisSummary } from "@/lib/types"

interface SidebarUploadProps {
  onAnalysisStarted: (analysis: AnalysisSummary) => void
  busy?: boolean
}

function defaultReportName(filename: string) {
  return filename.replace(/\.csv$/i, "").trim() || filename
}

export function SidebarUpload({ onAnalysisStarted, busy }: SidebarUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)

  function clearSelection() {
    setFile(null)
    setName("")
    setError(null)
    if (inputRef.current) inputRef.current.value = ""
  }

  function takeFile(next: File | undefined) {
    if (!next) return
    if (!next.name.toLowerCase().endsWith(".csv")) {
      setError("Please upload a .csv file")
      return
    }
    setFile(next)
    setName(defaultReportName(next.name))
    setError(null)
  }

  async function startAnalysis() {
    if (!file) return
    const reportName = name.trim() || defaultReportName(file.name)
    setLoading(true)
    setError(null)
    try {
      const res = await uploadAndStartAnalysis(file, reportName)
      if (!res.analysis) throw new Error("Upload did not create an analysis")
      clearSelection()
      onAnalysisStarted(res.analysis)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setLoading(false)
    }
  }

  const disabled = busy || loading

  return (
    <div className="space-y-2">
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        disabled={disabled}
        onChange={(e) => {
          takeFile(e.target.files?.[0])
        }}
      />

      {!file ? (
        <button
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          onDragEnter={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragOver(false)
            takeFile(e.dataTransfer.files?.[0])
          }}
          className={[
            "flex w-full flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed px-3 py-4 text-center transition bg-orange-500",
            dragOver
              ? "border-primary bg-primary/5"
              : "border-border/80 bg-muted/15 hover:border-foreground/30 hover:bg-orange-700",
            disabled ? "pointer-events-none opacity-50" : "",
          ].join(" ")}
        >
          <FileUp className="size-4 text-white" />
          <span className="text-xs font-medium text-white">Drop CSV or browse</span>
        </button>
      ) : (
        <div className="space-y-2 rounded-lg border border-border/70 bg-muted/20 p-2">
          <div className="flex items-start justify-between gap-1">
            <p className="truncate text-[11px] text-muted-foreground" title={file.name}>
              {file.name}
            </p>
            <button
              type="button"
              className="shrink-0 rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
              disabled={loading}
              onClick={clearSelection}
              aria-label="Clear file"
            >
              <X className="size-3.5" />
            </button>
          </div>
          <label className="block space-y-1">
            <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              Report name
            </span>
            <input
              type="text"
              value={name}
              disabled={disabled}
              autoFocus
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void startAnalysis()
                if (e.key === "Escape") clearSelection()
              }}
              className="h-8 w-full rounded-md border border-border bg-card px-2 text-xs outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-50"
              placeholder={defaultReportName(file.name)}
            />
          </label>
          <Button
            type="button"
            className="w-full"
            size="sm"
            disabled={disabled || !name.trim()}
            onClick={() => void startAnalysis()}
          >
            {loading ? <Loader2 className="size-4 animate-spin" /> : null}
            {loading ? "Starting…" : "Start analysis"}
          </Button>
        </div>
      )}

      <p className="text-[10px] leading-relaxed text-muted-foreground">
        Must have a <span className="text-orange-500 font-bold">verbatim</span> column with the review text.
        Extra fields (channel, product, region…) feed the deep dive. <br />
        <br />
        <span className="text-orange-500 font-bold">Important:</span>  Dont inlude Personal Identifiable Information (PII) in the review text. 
        You can delete the report after analysis is complete and all your data will be deleted from our servers.
      </p>
      {busy && !loading ? (
        <p className="text-[11px] text-warning">API or LLM not ready — check the badges above.</p>
      ) : null}
      {error ? <p className="text-[11px] text-destructive line-clamp-4">{error}</p> : null}
    </div>
  )
}
