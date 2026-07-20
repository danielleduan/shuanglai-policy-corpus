#!/usr/bin/env python3
"""Extract searchable text from downloaded HTML and PDF files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import METADATA_FIELDS, sha256_bytes


def extract_html(path: Path) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    return soup.get_text("\n", strip=True)


def extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=Path("data/metadata.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/extracted"))
    args = parser.parse_args()
    with args.metadata.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        if row.get("status") != "downloaded" or not row.get("local_path"):
            continue
        source = Path(row["local_path"])
        try:
            text = extract_pdf(source) if source.suffix.lower() == ".pdf" else extract_html(source)
            output = args.output_dir / f"{row['record_id']}.txt"
            output.write_text(text, encoding="utf-8")
            row.update({"text_path": str(output), "text_sha256": sha256_bytes(text.encode("utf-8")), "status": "extracted"})
        except Exception as exc:
            row.update({"status": "extract_error", "error": str(exc)})
    with args.metadata.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METADATA_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"更新元数据：{args.metadata}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
