"""Canonical record schema and serialization helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path

FIELDS = [
    "record_id", "title", "document_number", "issuing_authority",
    "joint_issuing_authorities", "publication_date", "effective_date",
    "expiry_date", "validity_status", "administrative_level", "document_type",
    "formal_policy", "material_category", "topic", "source_domain",
    "source_page_url", "attachment_url", "parent_column_url", "original_filename",
    "file_format", "full_text", "text_length", "summary", "key_measures",
    "relevant_regions", "matched_keywords", "relevance_level", "relevance_score",
    "relevance_reason", "involved_regions", "cross_boundary_relation",
    "matched_location_terms", "matched_relation_terms", "discovery_method",
    "crawl_time", "content_sha256", "parsing_status", "review_status",
    "duplicate_of", "alternate_sources", "error",
]

POLICY_TYPES = ("规划", "实施方案", "意见", "通知", "办法", "支持政策", "行动计划", "责任分工", "工作要点", "批复", "公报")
EVIDENCE_TYPES = ("工作报告", "计划报告", "建议答复", "提案答复", "工作总结", "项目进展", "新闻", "会议", "签约", "政务服务")


def empty_record(**values) -> dict:
    record = {field: "" for field in FIELDS}
    record.update(values)
    return record


def validate_record(record: dict) -> list[str]:
    return [field for field in FIELDS if field not in record]


def write_csv(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
