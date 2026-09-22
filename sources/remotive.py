"""
Remotive — public JSON API, no key required.
API: https://remotive.com/api/remote-jobs
"""
import requests

from sources.base import normalize

NAME = "Remotive"
STATUS = "live"
REASON = None

_BASE = "https://remotive.com/api/remote-jobs"
_SEARCHES = ["project manager", "programme manager", "delivery manager", "scrum master", "business analyst"]
_TIMEOUT = 12
_HEADERS = {"User-Agent": "Flux/1.0 (+local job intelligence dashboard)"}


def _fetch_search(term: str) -> list:
    resp = requests.get(_BASE, params={"search": term, "limit": 30}, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    out = []
    for job in payload.get("jobs", []):
        out.append(normalize(
            source=NAME,
            id_parts=(str(job.get("id", "")), job.get("title", ""), job.get("company_name", "")),
            title=job.get("title"),
            company=job.get("company_name"),
            location=job.get("candidate_required_location") or "Remote",
            employment_type=job.get("job_type") or "Not specified",
            posted_at=job.get("publication_date"),
            url=job.get("url"),
            description=job.get("description") or "",
        ))
    return out


def fetch() -> list:
    jobs, seen = [], set()
    for term in _SEARCHES:
        try:
            for job in _fetch_search(term):
                if job["id"] not in seen:
                    seen.add(job["id"])
                    jobs.append(job)
        except Exception:
            continue
    return jobs
