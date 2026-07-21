"""Discovery, crawl, export, checkpoint, and audit pipeline."""

from __future__ import annotations

import json
import logging
import mimetypes
import time
import urllib.robotparser
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .classify import classify_material, classify_topics, content_hash, mark_duplicates, score_relevance
from .parsing import extract_document_number, extract_file, extract_html, extract_issuing_authority, parse_chinese_date
from .schema import FIELDS, empty_record, read_csv, write_csv, write_jsonl

LOG = logging.getLogger(__name__)


def load_config(path: Path) -> dict:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_keywords(config_path: Path, config: dict) -> list[str]:
    path = config_path.parent / config["search"].get("keywords_file", "keywords.txt")
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]


def _allowed(url: str, domains: list[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host.endswith(".gov.cn") and any(host == d or host.endswith("." + d) for d in domains)


def discover(config_path: Path, limit: int | None = None) -> list[dict]:
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urldefrag, urljoin

    config, records = load_config(config_path), []
    settings = config["project"]
    session = requests.Session()
    session.headers["User-Agent"] = settings["user_agent"]
    for source in config["sources"]:
        queue, visited = deque((url, 0, "entry") for url in source["start_urls"]), set()
        maximum = limit or int(settings["max_pages_per_source"])
        robots = {}
        while queue and len(visited) < maximum:
            url, depth, method = queue.popleft()
            url = urldefrag(url)[0]
            if url in visited or not _allowed(url, source["allowed_domains"]): continue
            host = urlparse(url).netloc
            if settings.get("obey_robots_txt", True):
                rp = robots.setdefault(host, urllib.robotparser.RobotFileParser(f"{urlparse(url).scheme}://{host}/robots.txt"))
                if not getattr(rp, "_shuanglai_read", False):
                    try: rp.read()
                    except Exception: pass
                    rp._shuanglai_read = True
                if not rp.can_fetch(settings["user_agent"], url): continue
            visited.add(url)
            try:
                response = session.get(url, timeout=settings["request_timeout_seconds"])
                response.raise_for_status()
                if "html" not in response.headers.get("Content-Type", "").lower(): continue
                soup = BeautifulSoup(response.content, "lxml")
                title = (soup.find("h1") or soup.title)
                records.append({"source_id":source["id"], "source_name":source["name"], "title":title.get_text(" ", strip=True) if title else url, "url":response.url, "parent_column_url":url if depth == 0 else "", "discovery_method":method})
                if depth < int(settings["max_depth"]):
                    for anchor in soup.find_all("a", href=True):
                        link = urljoin(response.url, anchor["href"])
                        if _allowed(link, source["allowed_domains"]): queue.append((link, depth + 1, "link_tracking"))
            except Exception as exc:
                LOG.warning("discover failed %s: %s", url, exc)
            time.sleep(float(settings["request_interval_seconds"]))
    unique = {item["url"]: item for item in records}
    return list(unique.values())


def build_record(candidate: dict, html: bytes | str, crawl_time: str | None = None) -> tuple[dict, list[dict]]:
    title, text, attachments = extract_html(html, candidate["url"])
    title = title or candidate.get("title", "")
    relevance = score_relevance(title, text)
    material, document_type, formal = classify_material(title, text)
    record = empty_record(
        record_id=content_hash(candidate["url"])[:16], title=title,
        document_number=extract_document_number(text), issuing_authority=extract_issuing_authority(text, title),
        publication_date=parse_chinese_date(text), document_type=document_type, formal_policy=formal,
        material_category=material, topic="|".join(classify_topics(text)), source_domain=urlparse(candidate["url"]).hostname or "",
        source_page_url=candidate["url"], parent_column_url=candidate.get("parent_column_url", ""), file_format="html",
        full_text=text, text_length=str(len(text)), summary=text[:300], relevant_regions="|".join(relevance["locations"]),
        relevance_level=relevance["level"], relevance_score=str(relevance["score"]), relevance_reason=relevance["reason"],
        involved_regions="|".join(relevance["locations"]), cross_boundary_relation=relevance["cross_boundary"],
        matched_location_terms="|".join(relevance["locations"]), matched_relation_terms="|".join(relevance["relations"]),
        matched_keywords="|".join(relevance["locations"] + relevance["relations"]), discovery_method=candidate.get("discovery_method", "link_tracking"),
        crawl_time=crawl_time or datetime.now(timezone.utc).isoformat(), content_sha256=content_hash(text), parsing_status="parsed",
        review_status="pending" if relevance["level"] in ("B", "C") or not parse_chinese_date(text) else "auto_classified",
    )
    if attachments:
        record["attachment_url"] = "|".join(item["url"] for item in attachments)
        record["original_filename"] = "|".join(item["filename"] for item in attachments)
    return record, attachments


def crawl(config_path: Path, candidates_path: Path, state_path: Path, limit: int | None = None) -> list[dict]:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    config, candidates = load_config(config_path), json.loads(candidates_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"completed": []}
    completed, records = set(state["completed"]), []
    session = requests.Session(); session.headers["User-Agent"] = config["project"]["user_agent"]
    retry = Retry(total=int(config["project"].get("retries", 2)), backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET", "HEAD"))
    session.mount("https://", HTTPAdapter(max_retries=retry)); session.mount("http://", HTTPAdapter(max_retries=retry))
    for candidate in candidates[:limit]:
        if candidate["url"] in completed and not config["project"].get("refetch"): continue
        try:
            response = session.get(candidate["url"], timeout=config["project"]["request_timeout_seconds"]); response.raise_for_status()
            record, attachments = build_record(candidate, response.content)
            raw_html = Path("data/raw/html") / f"{record['record_id']}.html"; raw_html.parent.mkdir(parents=True, exist_ok=True); raw_html.write_bytes(response.content)
            attachment_status = []
            if config["project"].get("download_attachments", True):
                for attachment in attachments:
                    try:
                        file_response = session.get(attachment["url"], timeout=config["project"]["request_timeout_seconds"]); file_response.raise_for_status()
                        maximum = int(config["project"].get("max_response_bytes", 52_428_800))
                        if len(file_response.content) > maximum: raise ValueError(f"attachment exceeds {maximum} bytes")
                        suffix = Path(attachment["filename"]).suffix or mimetypes.guess_extension(file_response.headers.get("Content-Type", "").split(";", 1)[0]) or ".bin"
                        target = Path("data/raw/files") / f"{record['record_id']}-{len(attachment_status)+1}{suffix}"
                        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(file_response.content)
                        _, status = extract_file(target); attachment_status.append(status)
                    except Exception as attachment_error:
                        attachment_status.append(f"failed:{attachment_error}")
            if any(status == "needs_ocr" for status in attachment_status): record["parsing_status"] = "needs_ocr"
            elif any(status.startswith("failed:") or status == "unsupported_format" for status in attachment_status): record["parsing_status"] = "partial"
            records.append(record); completed.add(candidate["url"])
            state_path.parent.mkdir(parents=True, exist_ok=True); state_path.write_text(json.dumps({"completed":sorted(completed)}, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            records.append(empty_record(record_id=content_hash(candidate["url"])[:16], title=candidate.get("title", ""), source_page_url=candidate["url"], source_domain=urlparse(candidate["url"]).hostname or "", parsing_status="failed", review_status="required", error=str(exc)))
    return records


def export_records(records: list[dict], output_dir: Path) -> None:
    records = mark_duplicates(records)
    accepted = [r for r in records if r["relevance_level"] != "D" and not r.get("duplicate_of")]
    policies = [r for r in accepted if r["material_category"] == "policy"]
    evidence = [r for r in accepted if r["material_category"] == "evidence"]
    review = [r for r in records if r["review_status"] in ("pending", "required") or r["parsing_status"] not in ("parsed", "") or not r["publication_date"] or not r["issuing_authority"]]
    for name, rows in (("all_records.csv", records), ("policies.csv", policies), ("evidence.csv", evidence), ("review_queue.csv", review)):
        write_csv(output_dir / name, rows)
    write_jsonl(output_dir / "all_records.jsonl", records)


def coverage_report(records: list[dict]) -> str:
    domains = Counter(r["source_domain"] or "未知" for r in records)
    years = Counter((r["publication_date"][:4] if r["publication_date"] else "未知") for r in records)
    categories = Counter(r["material_category"] or "未分类" for r in records)
    topics = Counter(topic for r in records for topic in r["topic"].split("|") if topic)
    keywords = Counter(term for r in records for term in r["matched_keywords"].split("|") if term)
    failures = [r for r in records if r["parsing_status"] not in ("parsed", "")]
    excluded = [r for r in records if r["relevance_level"] == "D"]
    review = [r for r in records if r["review_status"] in ("pending", "required")]
    def table(counter): return "\n".join(f"- {key}: {value}" for key, value in sorted(counter.items())) or "- 无"
    return f"""# 覆盖率审计报告\n\n## 各政府网站发现数量\n{table(domains)}\n\n## 各年份数量\n{table(years)}\n\n## 正式政策与实施材料数量\n{table(categories)}\n\n## 各主题数量\n{table(topics)}\n\n## 各关键词命中数量\n{table(keywords)}\n\n## 解析失败文件\n- {len(failures)} 条\n\n## 被排除页面及理由\n- {len(excluded)} 条，详见 all_records.csv 的 relevance_reason\n\n## 尚未覆盖的栏目\n- sitemap、旧版栏目和部分站内搜索分页仍需下一轮扩展。\n\n## 需要人工核验\n- {len(review)} 条，详见 review_queue.csv。\n\n## 下一轮建议\n- 扩展政府信息公开目录与附件服务器入口；按年份分段检索；人工复核 B/C 级记录。\n"""
