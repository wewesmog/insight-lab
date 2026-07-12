export type Engine = "rules" | "llm"

export type Sentiment = "positive" | "negative" | "neutral" | "mixed"
export type Emotion = "frustrated" | "angry" | "delighted" | "anxious" | "neutral"
export type NpsClass = "promoter" | "passive" | "detractor"
export type ChurnRisk = "low" | "medium" | "high"

export interface DatasetSummary {
  id: string
  name: string
  filename: string
  row_count: number
  analyzed_count: number
  skipped_count: number
  analyzed_at: string | null
  created_at: string
}

export interface VerbatimRow {
  id: string
  external_id?: string | null
  text: string
  star_rating?: number | null
  occurred_at?: string | null
}

export interface VerbatimAnalysis {
  verbatim_id: string
  text: string
  star_rating?: number | null
  skipped: boolean
  skip_reason?: string | null
  sentiment?: Sentiment | null
  emotion?: Emotion | null
  nps_class?: NpsClass | null
  churn_risk?: ChurnRisk | null
  themes: string[]
  issues: string[]
  delights: string[]
  summary?: string | null
  key_quote?: string | null
  engine: Engine
}

export interface ThemeCount {
  theme: string
  count: number
}

export interface InsightsRollup {
  dataset_id: string
  total: number
  analyzed: number
  skipped: number
  sentiment: Record<string, number>
  emotion: Record<string, number>
  nps_class: Record<string, number>
  churn_risk: Record<string, number>
  top_themes: ThemeCount[]
  top_issues: ThemeCount[]
  top_delights: ThemeCount[]
  high_churn_samples: VerbatimAnalysis[]
  mixed_sentiment_count: number
  mixed_sentiment_samples: VerbatimAnalysis[]
  competitor_switch_count: number
  competitor_switch_samples: VerbatimAnalysis[]
}

export interface UploadResponse {
  dataset: DatasetSummary
  preview: VerbatimRow[]
}

export interface AnalyzeResponse {
  dataset_id: string
  run_id: string
  status: "completed"
  analyzed: number
  skipped: number
  engine: Engine
  records: VerbatimAnalysis[]
  rollup: InsightsRollup
}

export interface HealthResponse {
  status: string
  database: string
  llm_enabled: boolean
}
