import type {
  AnalysisListPage,
  AnalysisReport,
  HealthResponse,
  UploadResponse,
} from "@/lib/types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `Request failed: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export function getApiBase() {
  return API_BASE
}

export function getHealth() {
  return request<HealthResponse>("/health")
}

/** Upload CSV and start a background analysis job. */
export function uploadAndStartAnalysis(file: File, name?: string) {
  const body = new FormData()
  body.append("file", file)
  if (name) body.append("name", name)
  return request<UploadResponse>("/analyses/upload", { method: "POST", body })
}

export function listAnalyses(page = 1, pageSize = 20) {
  return request<AnalysisListPage>(`/analyses?page=${page}&page_size=${pageSize}`)
}

export function getAnalysisReport(analysisId: string) {
  return request<AnalysisReport>(`/analyses/${analysisId}`)
}

export function getAnalysisExportCsvUrl(analysisId: string) {
  return `${API_BASE}/analyses/${analysisId}/export.csv`
}

export function deleteAnalysis(analysisId: string) {
  return request<{ message: string }>(`/analyses/${analysisId}`, { method: "DELETE" })
}

/** Download records CSV with a filename based on the analysis name. */
export async function downloadAnalysisCsv(analysisId: string, analysisName: string) {
  const res = await fetch(getAnalysisExportCsvUrl(analysisId))
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `Export failed: ${res.status}`)
  }
  const blob = await res.blob()
  const stem = analysisName.includes(".")
    ? analysisName.slice(0, analysisName.lastIndexOf("."))
    : analysisName
  const safe =
    stem.replace(/[^a-zA-Z0-9-_]+/g, "_").replace(/^_+|_+$/g, "") || "analysis"
  const filename = `${safe}_records.csv`
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/** Print / Save as PDF using the analysis name as the document title (browser PDF filename). */
export function exportReportPdf(analysisName: string) {
  const previous = document.title
  const stem = analysisName.replace(/\.(csv|pdf)$/i, "").trim() || "Insight Lab Report"
  document.title = stem

  const restore = () => {
    document.title = previous
    window.removeEventListener("afterprint", restore)
  }
  window.addEventListener("afterprint", restore)
  window.setTimeout(restore, 60_000)

  // Ensure print starts from the top of the report (viewport clip otherwise truncates).
  const root = document.querySelector(".report-root")
  root?.scrollIntoView({ block: "start" })
  window.scrollTo(0, 0)

  window.print()
}
