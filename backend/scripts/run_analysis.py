"""CLI entry: run the LangGraph on the bundled sample CSV."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parents[1]
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv

load_dotenv(_backend_root / ".env")

from app.pipeline.run import run_dataset_analysis
from app.shared_services.db import init_db
from app import store


def main() -> None:
    init_db()
    sample_path = _backend_root.parent / "sample-data" / "kora_bank_verbatims.csv"
    rows = store.parse_csv(sample_path.read_bytes(), sample_path.name)
    dataset = store.create_dataset("CLI sample run", sample_path.name, rows)

    print(f"Dataset: {dataset.id} ({dataset.row_count} rows)")
    print("Running LangGraph pipeline...\n")

    result = run_dataset_analysis(dataset.id, rows)
    store.save_analyses(dataset.id, result.records, result.engine)

    print(f"Run {result.run_id} | engine={result.engine}")
    print(f"Analyzed: {result.analyzed_count} | Skipped: {result.skipped_count}")
    print(f"Stats: {result.stats.model_dump()}\n")

    for record in result.records:
        label = "SKIP" if record.skipped else "OK"
        print(f"[{label}] {record.external_id if hasattr(record, 'external_id') else record.verbatim_id}")
        print(json.dumps(record.model_dump(), indent=2, default=str))
        print()

    if result.rollup:
        print("=== Rollup ===")
        print(json.dumps(result.rollup.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    main()
