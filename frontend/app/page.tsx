"use client"

import { Loader2, Play, Radio } from "lucide-react"
import { useCallback, useEffect, useState } from "react"

import { InsightsDashboard } from "@/components/insights-dashboard"
import { UploadPanel } from "@/components/upload-panel"
import { VerbatimTable } from "@/components/verbatim-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { analyzeDataset, getApiBase, getHealth } from "@/lib/api"
import type { AnalyzeResponse, DatasetSummary } from "@/lib/types"

export default function HomePage() {
  const [dataset, setDataset] = useState<DatasetSummary | null>(null)
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [apiOk, setApiOk] = useState<boolean | null>(null)
  const [llmEnabled, setLlmEnabled] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getHealth()
      .then((h) => {
        setApiOk(true)
        setLlmEnabled(h.llm_enabled)
      })
      .catch(() => setApiOk(false))
  }, [])

  const handleAnalyze = useCallback(async () => {
    if (!dataset) return
    setAnalyzing(true)
    setError(null)
    try {
      const res = await analyzeDataset(dataset.id)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed")
    } finally {
      setAnalyzing(false)
    }
  }, [dataset])

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-5">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-primary">CVM-AI</p>
            <h1 className="text-xl font-semibold">Insight Lab</h1>
            <p className="text-sm text-muted-foreground">
              CSV → LangGraph → themes, churn, NPS — not just positive/negative
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {apiOk === null ? (
              <Badge variant="outline">Checking API…</Badge>
            ) : apiOk ? (
              <Badge variant="success">
                <Radio className="mr-1 size-3" />
                API {getApiBase()}
              </Badge>
            ) : (
              <Badge variant="destructive">API offline — start backend on :8000</Badge>
            )}
            <Badge variant="outline">{llmEnabled ? "LLM engine" : "Rules engine"}</Badge>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-4 py-8">
        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <div className="space-y-4">
            <UploadPanel
              busy={analyzing}
              onDatasetReady={(d, meta) => {
                setDataset(d)
                setError(null)
                if (meta.source === "upload") {
                  setResult(null)
                }
              }}
              onSampleAnalyzed={(res) => {
                setResult(res)
                setError(null)
              }}
              onSampleAnalyzeError={(message) => setError(message)}
            />

            {dataset ? (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Dataset</CardTitle>
                  <CardDescription>{dataset.name}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="text-sm text-muted-foreground">
                    <p>{dataset.row_count} rows · {dataset.filename}</p>
                    {dataset.analyzed_at ? (
                      <p className="mt-1">Last analyzed {new Date(dataset.analyzed_at).toLocaleString()}</p>
                    ) : null}
                  </div>
                  <Button
                    className="w-full"
                    disabled={analyzing || apiOk === false}
                    onClick={() => void handleAnalyze()}
                  >
                    {analyzing ? (
                      <>
                        <Loader2 className="size-4 animate-spin" />
                        Running LangGraph…
                      </>
                    ) : (
                      <>
                        <Play className="size-4" />
                        Run analysis
                      </>
                    )}
                  </Button>
                  {error ? <p className="text-sm text-destructive">{error}</p> : null}
                </CardContent>
              </Card>
            ) : null}
          </div>

          <div className="space-y-6">
            {!result ? (
              <Card className="flex min-h-64 items-center justify-center">
                <CardContent className="text-center">
                  <p className="text-sm font-medium">No insights yet</p>
                  <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                    Load a demo sample for instant insights, or upload your own CSV and click Run
                    analysis. The graph extracts themes, churn risk, and issues per verbatim, then
                    rolls up KPIs in code.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <>
                <InsightsDashboard rollup={result.rollup} engine={result.engine} />
                <VerbatimTable records={result.records} />
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
