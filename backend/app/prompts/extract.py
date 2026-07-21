"""LLM prompts for verbatim extraction (optional — requires OPENAI_API_KEY)."""

from __future__ import annotations

EXTRACT_SYSTEM = """You analyze customer verbatims for a bank or fintech product.
Return structured JSON only. Be specific: themes are snake_case ids, issues and delights are short phrases.
Sentiment can be mixed when both praise and complaints appear in one comment."""


def build_extract_user(*, text: str) -> str:
    return f"""Verbatim:
{text}

Return JSON with keys:
- sentiment: positive | negative | neutral | mixed
- emotion: frustrated | angry | delighted | anxious | neutral
- nps_class: promoter | passive | detractor
- churn_risk: low | medium | high
- themes: string[]
- issues: string[]
- delights: string[]
- summary: string
- key_quote: string"""
