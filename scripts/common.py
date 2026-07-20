"""Shared helpers for the policy crawler."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse


METADATA_FIELDS = [
    "record_id", "source_id", "title", "url", "document_url",
    "published_date", "retrieved_at", "media_type", "local_path",
    "sha256", "text_path", "text_sha256", "status", "duplicate_of", "error",
]


def canonicalize_url(url: str, base_url: str | None = None) -> str:
    absolute = urljoin(base_url or "", url.strip())
    absolute, _ = urldefrag(absolute)
    parsed = urlparse(absolute)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def is_allowed_url(url: str, allowed_domains: list[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == domain.lower() or host.endswith("." + domain.lower()) for domain in allowed_domains)


def matches_keywords(text: str, keywords: list[str]) -> list[str]:
    compact = re.sub(r"\s+", "", text).lower()
    return [keyword for keyword in keywords if re.sub(r"\s+", "", keyword).lower() in compact]


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def safe_filename(url: str, suffix: str) -> str:
    parsed = urlparse(url)
    stem = Path(parsed.path).stem or "index"
    stem = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "-", stem).strip("-._") or "document"
    return f"{stem[:60]}-{sha256_bytes(url.encode('utf-8'))[:12]}{suffix}"


def normalized_text_fingerprint(text: str) -> str:
    normalized = re.sub(r"\W+", "", text, flags=re.UNICODE).lower()
    return sha256_bytes(normalized.encode("utf-8"))
