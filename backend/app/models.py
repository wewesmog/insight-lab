from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Sentiment(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"
    mixed = "mixed"


class Emotion(str, Enum):
    frustrated = "frustrated"
    angry = "angry"
    delighted = "delighted"
    anxious = "anxious"
    neutral = "neutral"


class NpsClass(str, Enum):
    promoter = "promoter"
    passive = "passive"
    detractor = "detractor"


class ChurnRisk(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class SkipReason(str, Enum):
    empty = "empty"
    too_short = "too_short"
    low_signal = "low_signal"
    not_feedback = "not_feedback"
    one_word = "one_word"


class AnalysisStatus(str, Enum):
    queued = "queued"
    running = "running"
    ready = "ready"
    failed = "failed"


class RunStats(BaseModel):
    llm_calls: int = 0
    skipped: int = 0


class VerbatimRow(BaseModel):
    id: str
    external_id: str | None = None
    text: str
    occurred_at: str | None = None
    extras: dict[str, str] = Field(default_factory=dict)


class VerbatimAnalysis(BaseModel):
    verbatim_id: str
    text: str
    skipped: bool = False
    skip_reason: SkipReason | None = None
    sentiment: Sentiment | None = None
    emotion: Emotion | None = None
    nps_class: NpsClass | None = None
    churn_risk: ChurnRisk | None = None
    themes: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    delights: list[str] = Field(default_factory=list)
    summary: str | None = None
    key_quote: str | None = None
    engine: str = "llm"


class DatasetSummary(BaseModel):
    id: str
    name: str
    filename: str
    row_count: int
    analyzed_count: int
    skipped_count: int
    analyzed_at: str | None = None
    created_at: str


class ThemeCount(BaseModel):
    theme: str
    count: int


class MetricBlock(BaseModel):
    """Deterministic / countable KPIs — computed in code, not by the LLM."""

    nps_score: float | None = None
    nps_promoter_pct: float | None = None
    nps_passive_pct: float | None = None
    nps_detractor_pct: float | None = None
    positive_pct: float | None = None
    negative_pct: float | None = None
    high_churn_pct: float | None = None


class ExecutiveSummary(BaseModel):
    """LLM management commentary — narrative only; numbers come from MetricBlock."""

    title: str = Field(..., description="Short board-ready report title")
    executive_overview: str = Field(
        ...,
        description="2–4 paragraph executive overview for management",
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="5–8 crisp findings with business implication",
    )
    priority_issues: list[str] = Field(
        default_factory=list,
        description="Top issues to escalate, each with brief commentary",
    )
    strengths_to_protect: list[str] = Field(
        default_factory=list,
        description="What customers praise and why it matters",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Concrete next actions for product/ops/support",
    )
    risk_commentary: str = Field(
        ...,
        description="Commentary on churn, detractors, and competitive risk",
    )
    closing_note: str = Field(
        ...,
        description="One short closing paragraph for leadership",
    )


class ColumnProfile(BaseModel):
    name: str
    kind: Literal["categorical", "numeric", "datetime", "text", "sparse"] = "categorical"
    non_null: int = 0
    unique_count: int = 0
    top_values: list[ThemeCount] = Field(default_factory=list)
    interpretation: str | None = None


class SegmentStat(BaseModel):
    column: str
    value: str
    count: int
    negative_pct: float | None = None
    high_churn_pct: float | None = None
    promoter_pct: float | None = None


class SuggestedAnalysis(BaseModel):
    title: str
    rationale: str
    method: str
    priority: Literal["high", "medium", "low"] = "medium"
    requires_columns: list[str] = Field(default_factory=list)


class DeepDiveInsight(BaseModel):
    headline: str
    detail: str
    evidence: str | None = None
    severity: Literal["info", "watch", "urgent"] = "info"


class DeepDiveReport(BaseModel):
    """Opportunistic enrichment from extra CSV columns + AI interpretation."""

    available_columns: list[str] = Field(default_factory=list)
    column_profiles: list[ColumnProfile] = Field(default_factory=list)
    segment_stats: list[SegmentStat] = Field(default_factory=list)
    insights: list[DeepDiveInsight] = Field(default_factory=list)
    suggested_analyses: list[SuggestedAnalysis] = Field(default_factory=list)
    narrative: str = ""
    analyses_run: list[str] = Field(default_factory=list)


class InsightsRollup(BaseModel):
    dataset_id: str
    total: int
    analyzed: int
    skipped: int
    sentiment: dict[str, int]
    emotion: dict[str, int]
    nps_class: dict[str, int]
    churn_risk: dict[str, int]
    metrics: MetricBlock = Field(default_factory=MetricBlock)
    top_themes: list[ThemeCount]
    top_issues: list[ThemeCount]
    top_delights: list[ThemeCount]
    high_churn_samples: list[VerbatimAnalysis]
    mixed_sentiment_count: int = 0
    mixed_sentiment_samples: list[VerbatimAnalysis] = Field(default_factory=list)
    competitor_switch_count: int = 0
    competitor_switch_samples: list[VerbatimAnalysis] = Field(default_factory=list)
    executive_summary: ExecutiveSummary | None = None
    deep_dive: DeepDiveReport | None = None


class AnalysisSummary(BaseModel):
    id: str
    dataset_id: str
    name: str
    status: AnalysisStatus
    total_rows: int
    processed_rows: int
    analyzed_count: int
    skipped_count: int
    error: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    progress_pct: float = 0.0


class AnalysisListPage(BaseModel):
    items: list[AnalysisSummary]
    total: int
    page: int
    page_size: int


class AnalysisReport(BaseModel):
    analysis: AnalysisSummary
    dataset: DatasetSummary
    rollup: InsightsRollup | None = None
    records: list[VerbatimAnalysis] = Field(default_factory=list)


class AnalysisRunRequest(BaseModel):
    dataset_id: str
    verbatims: list[VerbatimRow]
    analysis_id: str | None = None


class AnalysisRunResponse(BaseModel):
    run_id: str
    dataset_id: str
    status: Literal["completed", "failed"] = "completed"
    engine: str
    records: list[VerbatimAnalysis]
    skipped_count: int
    analyzed_count: int
    stats: RunStats
    rollup: InsightsRollup | None = None


class UploadResponse(BaseModel):
    dataset: DatasetSummary
    preview: list[VerbatimRow]
    analysis: AnalysisSummary | None = None
