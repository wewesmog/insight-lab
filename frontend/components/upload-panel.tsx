"use client"

import { FileUp, Loader2, Sparkles } from "lucide-react"
import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { loadSampleDataset, uploadDataset, analyzeDataset } from "@/lib/api"
import type { AnalyzeResponse, DatasetSummary } from "@/lib/types"

export type DatasetSource = "upload" | "sample"

interface UploadPanelProps {
  onDatasetReady: (dataset: DatasetSummary, meta: { source: DatasetSource }) => void
  onSampleAnalyzed?: (result: AnalyzeResponse) => void
  onSampleAnalyzeError?: (message: string) => void
  busy: boolean
}

export function UploadPanel({
  onDatasetReady,
  onSampleAnalyzed,
  onSampleAnalyzeError,
  busy,
}: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFile(file: File) {
    setLoading(true)
    setError(null)
    try {
      const res = await uploadDataset(file)
      onDatasetReady(res.dataset, { source: "upload" })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setLoading(false)
    }
  }

  async function handleSample(sample: "bank" | "competitor") {
    setLoading(true)
    setError(null)
    try {
      const res = await loadSampleDataset(sample)
      onDatasetReady(res.dataset, { source: "sample" })
      const analyzed = await analyzeDataset(res.dataset.id)
      onSampleAnalyzed?.(analyzed)
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not load sample"
      setError(message)
      onSampleAnalyzeError?.(message)
    } finally {
      setLoading(false)
    }
  }

  const disabled = busy || loading

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your data</CardTitle>
        <CardDescription>
          Upload your own CSV (text column: <code className="text-xs">verbatim</code>,{" "}
          <code className="text-xs">feedback</code>, etc.). Optional star rating. Then run
          analysis.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div
          className="flex min-h-36 cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-muted/30 px-4 py-8 text-center transition hover:bg-muted/50"
          onClick={() => !disabled && inputRef.current?.click()}
          onKeyDown={(e) => e.key === "Enter" && !disabled && inputRef.current?.click()}
          role="button"
          tabIndex={0}
        >
          <FileUp className="size-8 text-muted-foreground" />
          <p className="text-sm font-medium">Drop your CSV or click to browse</p>
          <p className="text-xs text-muted-foreground">
            Your file stays in the local SQLite DB — click Run analysis when ready
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            disabled={disabled}
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) void handleFile(file)
              e.target.value = ""
            }}
          />
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Demo samples (instant insights)</p>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={disabled}
              onClick={() => void handleSample("bank")}
            >
              {loading ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
              Kora Bank sample
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={disabled}
              onClick={() => void handleSample("competitor")}
            >
              {loading ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
              Competitor switch sample
            </Button>
          </div>
        </div>

        {error ? <p className="text-sm text-destructive">{error}</p> : null}
      </CardContent>
    </Card>
  )
}
