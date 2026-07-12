from __future__ import annotations

from pathlib import Path

SAMPLE_ROOT = Path(__file__).resolve().parents[3] / "sample-data"

SAMPLE_DATASETS: dict[str, tuple[str, str]] = {
    "bank": (
        "Kora Bank — digital banking verbatims",
        "kora_bank_verbatims.csv",
    ),
    "competitor": (
        "Competitor switch & comparison signals",
        "competitor_switch_verbatims.csv",
    ),
}

DEFAULT_SAMPLE = "bank"
