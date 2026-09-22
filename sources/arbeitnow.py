"""
Arbeitnow — public JSON API, no key required. Covers European (including
UK) roles pulled from various ATS platforms (Greenhouse, Team Tailor,
Recruitee, etc.), with an explicit `remote` flag per posting.
API: https://www.arbeitnow.com/api/job-board-api
"""
import requests

from sources.base import normalize

NAME = "Arbeitnow"
STATUS = "live"
REASON = None

_BASE = "https://www.arbeitnow.com/api/job-board-api"
_TIMEOUT = 12
_HEADERS = {"User-Agent": "Flux/1.0 (+local job intelligence dashboard)"}


def fetch() -> list:
    try:
        resp = requests.get(_BASE, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return []

    out = []
    for job in payload.get("data", []):
        out.append(normalize(
            source=NAME,
            id_parts=(str(job.get("slug", "")), job.get("title", ""), job.get("company_name", "")),
            title=job.get("title"),
            company=job.get("company_name"),
            location="Remote" if job.get("remote") else (job.get("location") or "Not specified"),
            employment_type=", ".join(job.get("job_types", []) or []) or "Not specified",
            posted_at=job.get("created_at"),  # unix timestamp — to_iso8601 handles int/float
            url=job.get("url"),
            description=job.get("description") or "",
        ))
    return out
