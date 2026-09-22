"""
The Muse — public JSON API, no key required (unauthenticated requests are
capped at 500/hour, plenty for a 5-minute scan interval). Its "Project
Management" category is a direct match for Flux's target roles.
API: https://www.themuse.com/api/public/jobs
"""
import requests

from sources.base import normalize

NAME = "The Muse"
STATUS = "live"
REASON = None

_BASE = "https://www.themuse.com/api/public/jobs"
_CATEGORY = "Project Management"
_PAGES = 2  # ~20 results/page — two pages is enough for a 5-minute poll
_TIMEOUT = 12
_HEADERS = {"User-Agent": "Flux/1.0 (+local job intelligence dashboard)"}


def _fetch_page(page: int) -> list:
    resp = requests.get(
        _BASE,
        params={"category": _CATEGORY, "page": page},
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    payload = resp.json()
    out = []
    for job in payload.get("results", []):
        locations = job.get("locations") or []
        location = ", ".join(loc.get("name", "") for loc in locations if loc.get("name")) or "Not specified"
        company = (job.get("company") or {}).get("name")
        out.append(normalize(
            source=NAME,
            id_parts=(str(job.get("id", "")), job.get("name", ""), company or ""),
            title=job.get("name"),
            company=company,
            location=location,
            employment_type=job.get("type") or "Not specified",
            posted_at=job.get("publication_date"),
            url=(job.get("refs") or {}).get("landing_page"),
            description=job.get("contents") or "",
        ))
    return out


def fetch() -> list:
    jobs, seen = [], set()
    for page in range(_PAGES):
        try:
            for job in _fetch_page(page):
                if job["id"] not in seen:
                    seen.add(job["id"])
                    jobs.append(job)
        except Exception:
            continue
    return jobs
