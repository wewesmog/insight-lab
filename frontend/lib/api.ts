import type {
  AnalyzeResponse,
  DatasetSummary,
  HealthResponse,
  InsightsRollup,
  UploadResponse,
  VerbatimAnalysis,
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

export function listDatasets() {
  return request<DatasetSummary[]>("/datasets")
}

export function loadSampleDataset(sample: "bank" | "competitor" = "bank") {
  return request<UploadResponse>(`/datasets/sample?sample=${sample}`, { method: "POST" })
}

export function uploadDataset(file: File, name?: string) {
  const body = new FormData()
  body.append("file", file)
  if (name) body.append("name", name)
  return request<UploadResponse>("/datasets/upload", { method: "POST", body })
}

export function analyzeDataset(datasetId: string) {
  return request<AnalyzeResponse>(`/datasets/${datasetId}/analyze`, {
    method: "POST",
  })
}

export function getInsights(datasetId: string) {
  return request<InsightsRollup>(`/datasets/${datasetId}/insights`)
}

export function getRecords(datasetId: string) {
  return request<VerbatimAnalysis[]>(`/datasets/${datasetId}/records`)
}
