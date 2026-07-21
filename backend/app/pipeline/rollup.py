"""Build dataset-level rollups from per-verbatim records (deterministic KPIs)."""

from __future__ import annotations

from collections import Counter

from app.models import (
    ChurnRisk,
    InsightsRollup,
    MetricBlock,
    NpsClass,
    Sentiment,
    ThemeCount,
    VerbatimAnalysis,
)

COMPETITOR_THEME = "competitor_switch"


def build_rollup(dataset_id: str, records: list[VerbatimAnalysis]) -> InsightsRollup:
    analyzed = [r for r in records if not r.skipped]
    skipped = [r for r in records if r.skipped]

    sentiment = Counter(r.sentiment.value for r in analyzed if r.sentiment)
    emotion = Counter(r.emotion.value for r in analyzed if r.emotion)
    nps_class = Counter(r.nps_class.value for r in analyzed if r.nps_class)
    churn_risk = Counter(r.churn_risk.value for r in analyzed if r.churn_risk)

    theme_counter: Counter[str] = Counter()
    issue_counter: Counter[str] = Counter()
    delight_counter: Counter[str] = Counter()
    for record in analyzed:
        theme_counter.update(record.themes)
        issue_counter.update(record.issues)
        delight_counter.update(record.delights)

    high_churn = [
        r for r in analyzed if r.churn_risk in {ChurnRisk.high, ChurnRisk.medium}
    ][:5]

    mixed = [r for r in analyzed if r.sentiment == Sentiment.mixed][:5]
    competitor = [r for r in analyzed if COMPETITOR_THEME in r.themes][:5]

    return InsightsRollup(
        dataset_id=dataset_id,
        total=len(records),
        analyzed=len(analyzed),
        skipped=len(skipped),
        sentiment=dict(sentiment),
        emotion=dict(emotion),
        nps_class=dict(nps_class),
        churn_risk=dict(churn_risk),
        metrics=_build_metrics(analyzed, sentiment, nps_class, churn_risk),
        top_themes=_top(theme_counter),
        top_issues=_top(issue_counter),
        top_delights=_top(delight_counter),
        high_churn_samples=high_churn,
        mixed_sentiment_count=sum(1 for r in analyzed if r.sentiment == Sentiment.mixed),
        mixed_sentiment_samples=mixed,
        competitor_switch_count=sum(1 for r in analyzed if COMPETITOR_THEME in r.themes),
        competitor_switch_samples=competitor,
    )


def _build_metrics(
    analyzed: list[VerbatimAnalysis],
    sentiment: Counter[str],
    nps_class: Counter[str],
    churn_risk: Counter[str],
) -> MetricBlock:
    n = len(analyzed) or 1

    promoters = nps_class.get(NpsClass.promoter.value, 0)
    passives = nps_class.get(NpsClass.passive.value, 0)
    detractors = nps_class.get(NpsClass.detractor.value, 0)
    nps_n = promoters + passives + detractors

    pos = sentiment.get(Sentiment.positive.value, 0)
    neg = sentiment.get(Sentiment.negative.value, 0)
    high = churn_risk.get(ChurnRisk.high.value, 0)

    return MetricBlock(
        nps_score=((promoters - detractors) / nps_n * 100.0) if nps_n else None,
        nps_promoter_pct=(promoters / nps_n * 100.0) if nps_n else None,
        nps_passive_pct=(passives / nps_n * 100.0) if nps_n else None,
        nps_detractor_pct=(detractors / nps_n * 100.0) if nps_n else None,
        positive_pct=(pos / n * 100.0) if analyzed else None,
        negative_pct=(neg / n * 100.0) if analyzed else None,
        high_churn_pct=(high / n * 100.0) if analyzed else None,
    )


def _top(counter: Counter[str], limit: int = 8) -> list[ThemeCount]:
    return [ThemeCount(theme=k, count=v) for k, v in counter.most_common(limit)]
