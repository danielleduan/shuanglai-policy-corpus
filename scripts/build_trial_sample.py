#!/usr/bin/env python3
"""Build deterministic small outputs from verified government-page snapshots."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shuanglai_corpus.pipeline import build_record, coverage_report, export_records


def main() -> int:
    pages = json.loads((ROOT / "tests/fixtures/trial_pages.json").read_text(encoding="utf-8"))
    records = []
    for page in pages:
        record, _ = build_record(page, page["html"], crawl_time="2026-07-21T00:00:00+08:00")
        records.append(record)
    output = ROOT / "data/output"
    export_records(records, output)
    (output / "coverage_report.md").write_text(coverage_report(records), encoding="utf-8")
    print(f"generated {len(records)} verified trial records")
    return 0


if __name__ == "__main__": raise SystemExit(main())
