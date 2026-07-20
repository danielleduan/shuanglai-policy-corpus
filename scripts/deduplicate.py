#!/usr/bin/env python3
"""Mark duplicate policy records using binary and normalized-text hashes."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import METADATA_FIELDS, normalized_text_fingerprint


def mark_duplicates(rows: list[dict]) -> list[dict]:
    seen: dict[tuple[str, str], str] = {}
    for row in rows:
        keys = []
        if row.get("sha256"):
            keys.append(("binary", row["sha256"]))
        text_path = Path(row["text_path"]) if row.get("text_path") else None
        if text_path and text_path.exists():
            keys.append(("text", normalized_text_fingerprint(text_path.read_text(encoding="utf-8"))))
        duplicate = next((seen[key] for key in keys if key in seen), "")
        if duplicate:
            row["duplicate_of"] = duplicate
            row["status"] = "duplicate"
        else:
            for key in keys:
                seen[key] = row["record_id"]
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=Path("data/metadata.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/metadata_deduplicated.csv"))
    args = parser.parse_args()
    with args.metadata.open(encoding="utf-8-sig", newline="") as handle:
        rows = mark_duplicates(list(csv.DictReader(handle)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METADATA_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"去重结果：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
