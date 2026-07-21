"""Skip low-signal verbatims before calling the LLM."""

from __future__ import annotations

import re

from app.models import SkipReason


def should_skip(text: str) -> SkipReason | None:
    stripped = text.strip()
    if not stripped:
        return SkipReason.empty
    if len(stripped) < 8:
        return SkipReason.too_short
    if " " not in stripped:
        # One token only (no spaces) — usually not useful feedback.
        return SkipReason.one_word
    if re.fullmatch(r"[\W\d_]+", stripped, flags=re.UNICODE):
        return SkipReason.low_signal
    if stripped.lower() in {"ok", "good", "bad", "nice", "thanks", "thank you"}:
        return SkipReason.not_feedback
    return None
