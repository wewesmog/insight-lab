"use client"

import { useParams } from "next/navigation"
import { useCallback, useEffect, useState } from "react"

import { AnalysisWorkspace } from "@/components/analysis-workspace"
import { getAnalysisReport } from "@/lib/api"
import type { AnalysisReport } from "@/lib/types"

export default function AnalysisPage() {
  const params = useParams<{ id: string }>()
  const analysisId = params.id
  const [report, setReport] = useState<AnalysisReport | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await getAnalysisReport(analysisId)
      setReport(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analysis")
    }
  }, [analysisId])

  useEffect(() => {
    setReport(null)
    setError(null)
    void refresh()
  }, [refresh])

  useEffect(() => {
    const status = report?.analysis.status
    if (status !== "queued" && status !== "running") return
    const id = window.setInterval(() => void refresh(), 2000)
    return () => window.clearInterval(id)
  }, [report?.analysis.status, refresh])

  return (
    <main className="flex h-full min-h-0 flex-col overflow-hidden">
      <AnalysisWorkspace report={report} error={error} />
    </main>
  )
}
