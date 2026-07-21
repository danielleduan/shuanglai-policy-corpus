"""Unified command-line interface."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .classify import classify_material, classify_topics, score_relevance
from .pipeline import coverage_report, crawl, discover, export_records, load_config
from .schema import read_csv, write_csv

DEFAULT_CONFIG = Path("config/sources.yaml")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="shuanglai", description="莱西—莱阳政策资料库统一 CLI")
    root.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    commands = root.add_subparsers(dest="command", required=True)
    d = commands.add_parser("discover"); d.add_argument("--limit", type=int); d.add_argument("--output", type=Path, default=Path("data/review/candidates.json"))
    c = commands.add_parser("crawl"); c.add_argument("--input", type=Path, default=Path("data/review/candidates.json")); c.add_argument("--limit", type=int); c.add_argument("--output", type=Path, default=Path("data/output/crawled.csv")); c.add_argument("--state", type=Path, default=Path("data/review/checkpoint.json"))
    commands.add_parser("classify").add_argument("--input", type=Path, default=Path("data/output/crawled.csv"))
    e = commands.add_parser("export"); e.add_argument("--input", type=Path, default=Path("data/output/crawled.csv")); e.add_argument("--output-dir", type=Path, default=Path("data/output"))
    a = commands.add_parser("audit"); a.add_argument("--input", type=Path, default=Path("data/output/all_records.csv")); a.add_argument("--output", type=Path, default=Path("data/output/coverage_report.md"))
    r = commands.add_parser("resume"); r.add_argument("--input", type=Path, default=Path("data/review/candidates.json")); r.add_argument("--output", type=Path, default=Path("data/output/crawled.csv")); r.add_argument("--state", type=Path, default=Path("data/review/checkpoint.json")); r.add_argument("--limit", type=int)
    commands.add_parser("run-all").add_argument("--limit", type=int, default=5)
    return root


def reclassify(records: list[dict]) -> list[dict]:
    for record in records:
        result = score_relevance(record["title"], record["full_text"])
        record.update(relevance_level=result["level"], relevance_score=str(result["score"]), relevance_reason=result["reason"], involved_regions="|".join(result["locations"]), cross_boundary_relation=result["cross_boundary"], matched_location_terms="|".join(result["locations"]), matched_relation_terms="|".join(result["relations"]), topic="|".join(classify_topics(record["full_text"])))
        category, document_type, formal = classify_material(record["title"], record["full_text"]); record.update(material_category=category, document_type=document_type, formal_policy=formal)
    return records


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    config = load_config(args.config) if args.command in ("discover", "crawl", "resume", "run-all") else {"project": {"log_level": "INFO"}}
    logging.basicConfig(level=getattr(logging, config["project"].get("log_level", "INFO")))
    if args.command == "discover":
        items = discover(args.config, args.limit); args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"); print(f"发现 {len(items)} 条候选：{args.output}")
    elif args.command in ("crawl", "resume"):
        records = crawl(args.config, args.input, args.state, args.limit); write_csv(args.output, records); print(f"抓取 {len(records)} 条：{args.output}")
    elif args.command == "classify":
        records = reclassify(read_csv(args.input)); write_csv(args.input, records); print(f"重新分类 {len(records)} 条")
    elif args.command == "export": export_records(read_csv(args.input), args.output_dir)
    elif args.command == "audit": args.output.write_text(coverage_report(read_csv(args.input)), encoding="utf-8"); print(args.output)
    else:
        candidates = Path("data/review/candidates.json"); crawled = Path("data/output/crawled.csv")
        items = discover(args.config, args.limit); candidates.parent.mkdir(parents=True, exist_ok=True); candidates.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        records = crawl(args.config, candidates, Path("data/review/checkpoint.json"), args.limit); write_csv(crawled, records); export_records(records, Path("data/output")); Path("data/output/coverage_report.md").write_text(coverage_report(records), encoding="utf-8")
    return 0


if __name__ == "__main__": raise SystemExit(main())
