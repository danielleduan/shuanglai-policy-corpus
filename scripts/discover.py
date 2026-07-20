#!/usr/bin/env python3
"""Discover keyword-matching public HTML pages and PDF attachments."""

from __future__ import annotations

import argparse
import csv
import time
from collections import deque
from pathlib import Path

from common import canonicalize_url, is_allowed_url, matches_keywords


FIELDS = ["source_id", "source_name", "title", "url", "document_url", "matched_keywords"]


def load_config(path: Path) -> tuple[dict, list[str]]:
    import yaml

    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    keywords_path = path.parent / config.get("keywords_file", "keywords.txt")
    keywords = [line.strip() for line in keywords_path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    return config, keywords


def discover_source(session, source: dict, keywords: list[str], timeout: float, interval: float) -> list[dict]:
    from bs4 import BeautifulSoup

    queue = deque((canonicalize_url(url), 0) for url in source["start_urls"])
    visited: set[str] = set()
    results: dict[tuple[str, str], dict] = {}
    max_depth = int(source.get("max_depth", 1))

    while queue:
        url, depth = queue.popleft()
        if url in visited or not is_allowed_url(url, source["allowed_domains"]):
            continue
        visited.add(url)
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" not in content_type:
            continue
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else url
        page_text = soup.get_text(" ", strip=True)
        page_matches = matches_keywords(f"{title} {page_text}", keywords)
        if page_matches:
            results[(url, "")] = {
                "source_id": source["id"], "source_name": source["name"], "title": title,
                "url": url, "document_url": "", "matched_keywords": "|".join(page_matches),
            }
        for anchor in soup.find_all("a", href=True):
            link = canonicalize_url(anchor["href"], url)
            label = anchor.get_text(" ", strip=True)
            link_matches = matches_keywords(f"{label} {link}", keywords)
            if link.lower().endswith(".pdf") and link_matches and is_allowed_url(link, source["allowed_domains"]):
                results[(url, link)] = {
                    "source_id": source["id"], "source_name": source["name"], "title": label or Path(link).name,
                    "url": url, "document_url": link, "matched_keywords": "|".join(link_matches),
                }
            elif depth < max_depth and is_allowed_url(link, source["allowed_domains"]):
                queue.append((link, depth + 1))
        time.sleep(max(0.0, interval))
    return list(results.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/sources.yaml"))
    parser.add_argument("--output", type=Path, default=Path("data/discovered.csv"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        raw = args.config.read_text(encoding="utf-8")
        keyword_file = "keywords.txt"
        for line in raw.splitlines():
            if line.strip().startswith("keywords_file:"):
                keyword_file = line.split(":", 1)[1].strip().strip("'\"")
                break
        keywords = [line.strip() for line in (args.config.parent / keyword_file).read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
        source_count = sum(1 for line in raw.splitlines() if line.strip().startswith("- id:"))
        if not source_count or not keywords:
            raise ValueError("配置必须至少包含一个来源和一个关键词")
        print(f"配置有效：{source_count} 个来源，{len(keywords)} 个关键词")
        return 0
    config, keywords = load_config(args.config)
    sources = [source for source in config.get("sources", []) if source.get("enabled", True)]
    import requests

    session = requests.Session()
    session.headers["User-Agent"] = config["user_agent"]
    records = []
    for source in sources:
        records.extend(discover_source(session, source, keywords, float(config.get("request_timeout_seconds", 20)), float(config.get("request_interval_seconds", 1))))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    print(f"发现 {len(records)} 条候选记录：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
