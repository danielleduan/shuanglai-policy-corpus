#!/usr/bin/env python3
"""Download complete originals for the verified policy URL set.

Uses the Python standard library for HTTP so it can run before optional crawler
dependencies are installed. HTML extraction also has a standard-library fallback.
PDF files are always saved; install pypdf to extract their text.
"""

from __future__ import annotations

import json
import argparse
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shuanglai_corpus.pipeline import build_record
from shuanglai_corpus.parsing import extract_file
from shuanglai_corpus.schema import empty_record, write_csv, write_jsonl

USER_AGENT = "ShuanglaiPolicyCorpus/0.2 (+https://github.com/danielleduan/shuanglai-policy-corpus)"


def fetch(url: str, retries: int = 2, timeout: int = 30, maximum: int = 52_428_800) -> tuple[bytes, str, str]:
    last_error = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content = response.read(maximum + 1)
                if len(content) > maximum:
                    raise ValueError(f"response exceeds {maximum} bytes")
                return content, response.headers.get_content_type(), response.geturl()
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(str(last_error))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "tests/fixtures/trial_pages.json")
    parser.add_argument("--interval", type=float, default=1.5)
    args = parser.parse_args(argv)
    pages = json.loads(args.input.read_text(encoding="utf-8"))
    raw_html, raw_files, text_dir = ROOT / "data/raw/html", ROOT / "data/raw/files", ROOT / "data/text"
    for directory in (raw_html, raw_files, text_dir):
        directory.mkdir(parents=True, exist_ok=True)
    records = []
    for index, page in enumerate(pages, 1):
        url = page["url"]
        print(f"[{index}/{len(pages)}] {url}")
        try:
            content, media_type, final_url = fetch(url)
            is_pdf = media_type == "application/pdf" or urlparse(final_url).path.lower().endswith(".pdf")
            suffix = ".pdf" if is_pdf else ".html"
            target_dir = raw_files if is_pdf else raw_html
            target = target_dir / f"verified-{index:02d}{suffix}"
            target.write_bytes(content)
            if is_pdf:
                try:
                    text, status = extract_file(target)
                except ImportError:
                    text, status = "", "saved_needs_pypdf"
                record = empty_record(
                    record_id=f"verified-{index:02d}", title=page.get("title", target.name),
                    source_domain=urlparse(final_url).hostname or "", source_page_url=final_url,
                    attachment_url=final_url, parent_column_url=page.get("parent_column_url", ""),
                    original_filename=Path(urlparse(final_url).path).name, file_format="pdf",
                    local_raw_path=str(target.relative_to(ROOT)), full_text=text, text_length=str(len(text)),
                    discovery_method=page.get("discovery_method", "verified_target"),
                    crawl_time=datetime.now(timezone.utc).isoformat(), parsing_status=status,
                    review_status="required" if status != "parsed" else "pending",
                )
            else:
                candidate = dict(page, url=final_url)
                record, _ = build_record(candidate, content)
                record["local_raw_path"] = str(target.relative_to(ROOT))
                text_path = text_dir / f"{record['record_id']}.txt"
                text_path.write_text(record["full_text"], encoding="utf-8")
                record["text_path"] = str(text_path.relative_to(ROOT))
            records.append(record)
        except Exception as exc:
            records.append(empty_record(
                record_id=f"verified-{index:02d}", title=page.get("title", ""),
                source_domain=urlparse(url).hostname or "", source_page_url=url,
                parent_column_url=page.get("parent_column_url", ""),
                discovery_method=page.get("discovery_method", "verified_target"),
                crawl_time=datetime.now(timezone.utc).isoformat(), parsing_status="failed",
                review_status="required", error=str(exc),
            ))
        time.sleep(max(0.0, args.interval))
    output = ROOT / "data/output"
    write_csv(output / "verified_originals.csv", records)
    write_jsonl(output / "verified_originals.jsonl", records)
    succeeded = sum(record["parsing_status"] != "failed" for record in records)
    print(f"完成：{succeeded}/{len(records)}；结果：data/output/verified_originals.csv")
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
