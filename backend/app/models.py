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


class RunStats(BaseModel):
    llm_calls: int = 0
    rule_skips: int = 0
    rule_analyzed: int = 0


class VerbatimRow(BaseModel):
    id: str
    external_id: str | None = None
    text: str
    star_rating: float | None = None
    occurred_at: str | None = None


class VerbatimAnalysis(BaseModel):
    verbatim_id: str
    text: str
    star_rating: float | None = None
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
    engine: Literal["rules", "llm"] = "rules"


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


class InsightsRollup(BaseModel):
    dataset_id: str
    total: int
    analyzed: int
    skipped: int
    sentiment: dict[str, int]
    emotion: dict[str, int]
    nps_class: dict[str, int]
    churn_risk: dict[str, int]
    top_themes: list[ThemeCount]
    top_issues: list[ThemeCount]
    top_delights: list[ThemeCount]
    high_churn_samples: list[VerbatimAnalysis]
    mixed_sentiment_count: int = 0
    mixed_sentiment_samples: list[VerbatimAnalysis] = Field(default_factory=list)
    competitor_switch_count: int = 0
    competitor_switch_samples: list[VerbatimAnalysis] = Field(default_factory=list)


class AnalysisRunRequest(BaseModel):
    dataset_id: str
    verbatims: list[VerbatimRow]


class AnalysisRunResponse(BaseModel):
    run_id: str
    dataset_id: str
    status: Literal["completed", "failed"] = "completed"
    engine: Literal["rules", "llm"]
    records: list[VerbatimAnalysis]
    skipped_count: int
    analyzed_count: int
    stats: RunStats
    rollup: InsightsRollup | None = None


class AnalyzeResponse(BaseModel):
    dataset_id: str
    run_id: str
    status: Literal["completed"] = "completed"
    analyzed: int
    skipped: int
    engine: Literal["rules", "llm"]
    records: list[VerbatimAnalysis]
    rollup: InsightsRollup


class UploadResponse(BaseModel):
    dataset: DatasetSummary
    preview: list[VerbatimRow]
