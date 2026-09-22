"""
Common helpers for job source adapters. Every adapter exposes:

    NAME: str                 human-readable source name
    STATUS: "live" | "stub"   whether fetch() does anything
    REASON: str | None        why a stub isn't implemented (shown in the UI)
    fetch() -> list[dict]     normalized job postings (never raises)

Normalized job schema (see docs/api spec):
    id, title, company, location, employment_type, posted_at (ISO8601 UTC),
    source, url, description
"""
import hashlib
import re
from datetime import datetime, timezone


def make_id(source: str, *parts: str) -> str:
    key = "|".join(p.strip().lower() for p in parts if p)
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"{source.lower()}-{digest}"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_iso8601(value) -> str:
    """Best-effort normalization of a variety of date formats to ISO 8601 UTC."""
    if value is None:
        return now_iso()
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OSError):
            return now_iso()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return now_iso()
        # Already ISO-ish
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S %z",
        ):
            try:
                dt = datetime.strptime(text, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue
        # Strip stray timezone abbreviations RSS feeds sometimes add
        cleaned = re.sub(r"\s*\([A-Z]+\)\s*$", "", text)
        if cleaned != text:
            return to_iso8601(cleaned)
    return now_iso()


def normalize(source: str, id_parts, title, company, location, employment_type,
              posted_at, url, description=""):
    return {
        "id": make_id(source, *id_parts),
        "title": (title or "Untitled role").strip(),
        "company": (company or "Unknown").strip(),
        "location": (location or "Not specified").strip(),
        "employment_type": (employment_type or "Not specified").strip(),
        "posted_at": to_iso8601(posted_at),
        "source": source,
        "url": url or "",
        "description": description or "",
    }


class StubSource:
    """A documented placeholder for a source we don't have a working
    integration for yet (paid/official API needed, or scraping would
    violate the site's Terms of Service)."""

    STATUS = "stub"

    def __init__(self, name: str, reason: str):
        self.NAME = name
        self.REASON = reason

    def fetch(self):
        return []
