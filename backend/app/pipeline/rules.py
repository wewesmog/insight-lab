"""Rule-based verbatim extraction — explainable, no API key required."""

from __future__ import annotations

import re

from app.models import (
    ChurnRisk,
    Emotion,
    NpsClass,
    Sentiment,
    SkipReason,
    VerbatimAnalysis,
    VerbatimRow,
)

THEME_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("login_failure", ("can't login", "cannot login", "login", "log in", "password")),
    ("payment_failure", ("payment failed", "payment", "transfer failed", "pay bills")),
    ("kyc_friction", ("kyc", "upload keeps failing", "verification", "pending")),
    ("fraud_security", ("without permission", "withdraw", "fraud", "unauthorized", "otp")),
    ("atm_branch", ("atm", "branch", "swallowed my card")),
    ("app_stability", ("crash", "crashes", "app crash", "broken")),
    ("customer_service", ("support", "customer service", "callback", "rude", "hung up")),
    ("product_delight", ("recommend", "impressed", "game changer", "great", "love")),
    ("pricing_value", ("interest rate", "savings", "budgeting")),
    ("competitor_switch", (
        "switching",
        "switched to",
        "moving to",
        "monzo",
        "equity",
        "kcb",
        "mpesa",
        "m-pesa",
        "coop bank",
        "absa",
        "stanbic",
        "ncba",
        "instead",
        "better than kora",
        "competitor",
    )),
]

NEGATIVE_WORDS = (
    "failed",
    "failing",
    "can't",
    "cannot",
    "unacceptable",
    "broken",
    "buggy",
    "rude",
    "waiting",
    "crash",
    "problem",
    "issue",
    "hate",
    "without permission",
    "unreliable",
    "painful",
)
POSITIVE_WORDS = (
    "fast",
    "clean",
    "recommend",
    "great",
    "love",
    "impressed",
    "resolved",
    "transparent",
    "game changer",
    "helped",
)
CHURN_PHRASES = ("switching", "instead", "monzo", "equity", "considering", "leave")
ANGRY_PHRASES = ("unacceptable", "without permission", "rude", "hung up", "broken")
DELIGHT_PHRASES = ("recommend", "impressed", "game changer", "resolved", "transparent")
ANXIOUS_PHRASES = ("without permission", "need help", "never arrives", "waiting")


def rule_skip(text: str) -> SkipReason | None:
    stripped = text.strip()
    if not stripped:
        return SkipReason.empty
    if len(stripped) < 8:
        return SkipReason.too_short
    if re.fullmatch(r"[\W\d_]+", stripped, flags=re.UNICODE):
        return SkipReason.low_signal
    if stripped.lower() in {"ok", "good", "bad", "nice", "thanks", "thank you"}:
        return SkipReason.not_feedback
    return None


def _match_themes(text: str) -> list[str]:
    lowered = text.lower()
    themes = [theme for theme, phrases in THEME_RULES if any(p in lowered for p in phrases)]
    return themes or ["general_feedback"]


def _sentiment_from_text(text: str, star_rating: float | None) -> Sentiment:
    lowered = text.lower()
    neg = sum(1 for word in NEGATIVE_WORDS if word in lowered)
    pos = sum(1 for word in POSITIVE_WORDS if word in lowered)
    if neg and pos:
        return Sentiment.mixed
    if neg > pos:
        return Sentiment.negative
    if pos > neg:
        return Sentiment.positive
    if star_rating is not None:
        if star_rating >= 4:
            return Sentiment.positive
        if star_rating <= 2:
            return Sentiment.negative
    return Sentiment.neutral


def _nps_class(star_rating: float | None, sentiment: Sentiment) -> NpsClass:
    if star_rating is not None:
        if star_rating >= 4.5:
            return NpsClass.promoter
        if star_rating <= 2.5:
            return NpsClass.detractor
        return NpsClass.passive
    if sentiment == Sentiment.positive:
        return NpsClass.promoter
    if sentiment == Sentiment.negative:
        return NpsClass.detractor
    return NpsClass.passive


def _emotion(text: str, sentiment: Sentiment) -> Emotion:
    lowered = text.lower()
    if any(p in lowered for p in ANGRY_PHRASES):
        return Emotion.angry
    if any(p in lowered for p in ANXIOUS_PHRASES):
        return Emotion.anxious
    if any(p in lowered for p in DELIGHT_PHRASES) or sentiment == Sentiment.positive:
        return Emotion.delighted
    if sentiment in {Sentiment.negative, Sentiment.mixed}:
        return Emotion.frustrated
    return Emotion.neutral


def _churn_risk(text: str, sentiment: Sentiment, star_rating: float | None) -> ChurnRisk:
    lowered = text.lower()
    if any(p in lowered for p in CHURN_PHRASES):
        return ChurnRisk.high
    if sentiment == Sentiment.negative and (star_rating is None or star_rating <= 2):
        return ChurnRisk.high
    if sentiment == Sentiment.mixed:
        return ChurnRisk.medium
    if sentiment == Sentiment.negative:
        return ChurnRisk.medium
    return ChurnRisk.low


def _extract_issues(text: str, themes: list[str]) -> list[str]:
    issues: list[str] = []
    lowered = text.lower()
    if "login_failure" in themes:
        issues.append("Login problems after update")
    if "payment_failure" in themes:
        issues.append("Payment or transfer failures")
    if "kyc_friction" in themes:
        issues.append("KYC upload friction")
    if "fraud_security" in themes:
        issues.append("Security or fraud concern")
    if "app_stability" in themes:
        issues.append("App crashes during key flows")
    if "customer_service" in themes and any(w in lowered for w in ("rude", "hung up", "waiting")):
        issues.append("Poor service recovery")
    return issues[:3]


def _extract_delights(text: str, themes: list[str]) -> list[str]:
    delights: list[str] = []
    lowered = text.lower()
    if "product_delight" in themes:
        delights.append("Strong product experience")
    if "pricing_value" in themes:
        delights.append("Perceived value from rates or insights")
    if "customer_service" in themes and any(w in lowered for w in ("resolved", "support")):
        delights.append("Support resolved issue quickly")
    return delights[:3]


def _summary(text: str, sentiment: Sentiment, themes: list[str]) -> str:
    theme_label = themes[0].replace("_", " ")
    return f"{sentiment.value.title()} feedback focused on {theme_label}."


def _key_quote(text: str) -> str:
    parts = re.split(r"[.!?]", text)
    parts = [part.strip() for part in parts if part.strip()]
    return parts[0] if parts else text[:120]


def analyze_with_rules(row: VerbatimRow) -> VerbatimAnalysis:
    skip = rule_skip(row.text)
    if skip is not None:
        return VerbatimAnalysis(
            verbatim_id=row.id,
            text=row.text,
            star_rating=row.star_rating,
            skipped=True,
            skip_reason=skip,
            engine="rules",
        )

    themes = _match_themes(row.text)
    sentiment = _sentiment_from_text(row.text, row.star_rating)
    emotion = _emotion(row.text, sentiment)
    nps = _nps_class(row.star_rating, sentiment)
    churn = _churn_risk(row.text, sentiment, row.star_rating)

    return VerbatimAnalysis(
        verbatim_id=row.id,
        text=row.text,
        star_rating=row.star_rating,
        sentiment=sentiment,
        emotion=emotion,
        nps_class=nps,
        churn_risk=churn,
        themes=themes,
        issues=_extract_issues(row.text, themes),
        delights=_extract_delights(row.text, themes),
        summary=_summary(row.text, sentiment, themes),
        key_quote=_key_quote(row.text),
        engine="rules",
    )
