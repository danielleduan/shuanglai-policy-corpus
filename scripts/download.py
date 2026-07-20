#!/usr/bin/env python3
"""Download discovered public HTML pages and PDF attachments."""

from __future__ import annotations

import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

from common import METADATA_FIELDS, safe_filename, sha256_bytes


def download(session, url: str, destination: Path, timeout: float, max_bytes: int) -> tuple[str, str]:
    with session.get(url, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0]
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > max_bytes:
                raise ValueError(f"response exceeds {max_bytes} bytes")
            chunks.append(chunk)
    content = b"".join(chunks)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return content_type, sha256_bytes(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/discovered.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("data/metadata.csv"))
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--max-bytes", type=int, default=52_428_800)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print(f"输入：{args.input}；元数据：{args.metadata}")
        return 0
    import requests

    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        candidates = list(csv.DictReader(handle))
    session = requests.Session()
    session.headers["User-Agent"] = "ShuanglaiPolicyCorpus/0.1"
    rows = []
    for index, item in enumerate(candidates, 1):
        target_url = item.get("document_url") or item["url"]
        is_pdf = target_url.lower().endswith(".pdf")
        suffix, folder = (".pdf", Path("data/raw/pdf")) if is_pdf else (".html", Path("data/raw/html"))
        path = folder / safe_filename(target_url, suffix)
        row = {field: "" for field in METADATA_FIELDS}
        row.update({"record_id": f"{item['source_id']}-{index:05d}", "source_id": item["source_id"], "title": item["title"], "url": item["url"], "document_url": item.get("document_url", ""), "retrieved_at": datetime.now(timezone.utc).isoformat()})
        try:
            media_type, digest = download(session, target_url, path, args.timeout, args.max_bytes)
            row.update({"media_type": media_type, "local_path": str(path), "sha256": digest, "status": "downloaded"})
        except Exception as exc:  # preserve per-record failures in the audit log
            row.update({"status": "error", "error": str(exc)})
        rows.append(row)
        time.sleep(max(0.0, args.interval))
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    with args.metadata.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METADATA_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"处理 {len(rows)} 条记录：{args.metadata}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
