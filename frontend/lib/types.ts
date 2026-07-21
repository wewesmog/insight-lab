export type Engine = string

export type Sentiment = "positive" | "negative" | "neutral" | "mixed"
export type Emotion = "frustrated" | "angry" | "delighted" | "anxious" | "neutral"
export type NpsClass = "promoter" | "passive" | "detractor"
export type ChurnRisk = "low" | "medium" | "high"
export type AnalysisStatus = "queued" | "running" | "ready" | "failed"

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
  occurred_at?: string | null
  extras?: Record<string, string>
}

export interface VerbatimAnalysis {
  verbatim_id: string
  text: string
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

export interface MetricBlock {
  nps_score?: number | null
  nps_promoter_pct?: number | null
  nps_passive_pct?: number | null
  nps_detractor_pct?: number | null
  positive_pct?: number | null
  negative_pct?: number | null
  high_churn_pct?: number | null
}

export interface ExecutiveSummary {
  title: string
  executive_overview: string
  key_findings: string[]
  priority_issues: string[]
  strengths_to_protect: string[]
  recommended_actions: string[]
  risk_commentary: string
  closing_note: string
}

export interface ColumnProfile {
  name: string
  kind: "categorical" | "numeric" | "datetime" | "text" | "sparse"
  non_null: number
  unique_count: number
  top_values: ThemeCount[]
  interpretation?: string | null
}

export interface SegmentStat {
  column: string
  value: string
  count: number
  negative_pct?: number | null
  high_churn_pct?: number | null
  promoter_pct?: number | null
}

export interface SuggestedAnalysis {
  title: string
  rationale: string
  method: string
  priority: "high" | "medium" | "low"
  requires_columns: string[]
}

export interface DeepDiveInsight {
  headline: string
  detail: string
  evidence?: string | null
  severity: "info" | "watch" | "urgent"
}

export interface DeepDiveReport {
  available_columns: string[]
  column_profiles: ColumnProfile[]
  segment_stats: SegmentStat[]
  insights: DeepDiveInsight[]
  suggested_analyses: SuggestedAnalysis[]
  narrative: string
  analyses_run: string[]
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
  metrics: MetricBlock
  top_themes: ThemeCount[]
  top_issues: ThemeCount[]
  top_delights: ThemeCount[]
  high_churn_samples: VerbatimAnalysis[]
  mixed_sentiment_count: number
  mixed_sentiment_samples: VerbatimAnalysis[]
  competitor_switch_count: number
  competitor_switch_samples: VerbatimAnalysis[]
  executive_summary?: ExecutiveSummary | null
  deep_dive?: DeepDiveReport | null
}

export interface AnalysisSummary {
  id: string
  dataset_id: string
  name: string
  status: AnalysisStatus
  total_rows: number
  processed_rows: number
  analyzed_count: number
  skipped_count: number
  error?: string | null
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  progress_pct: number
}

export interface AnalysisListPage {
  items: AnalysisSummary[]
  total: number
  page: number
  page_size: number
}

export interface AnalysisReport {
  analysis: AnalysisSummary
  dataset: DatasetSummary
  rollup?: InsightsRollup | null
  records: VerbatimAnalysis[]
}

export interface UploadResponse {
  dataset: DatasetSummary
  preview: VerbatimRow[]
  analysis?: AnalysisSummary | null
}

export interface HealthResponse {
  status: string
  database: string
  llm_enabled: boolean
  llm_model?: string
}
