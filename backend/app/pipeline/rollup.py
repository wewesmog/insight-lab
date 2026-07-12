"""Build dataset-level rollups from per-verbatim records."""

from __future__ import annotations

from collections import Counter

from app.models import ChurnRisk, InsightsRollup, Sentiment, ThemeCount, VerbatimAnalysis

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
        top_themes=_top(theme_counter),
        top_issues=_top(issue_counter),
        top_delights=_top(delight_counter),
        high_churn_samples=high_churn,
        mixed_sentiment_count=sum(1 for r in analyzed if r.sentiment == Sentiment.mixed),
        mixed_sentiment_samples=mixed,
        competitor_switch_count=sum(1 for r in analyzed if COMPETITOR_THEME in r.themes),
        competitor_switch_samples=competitor,
    )


def _top(counter: Counter[str], limit: int = 6) -> list[ThemeCount]:
    return [ThemeCount(theme=k, count=v) for k, v in counter.most_common(limit)]
