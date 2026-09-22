"""
Himalayas — public JSON API, no key required.
API: https://himalayas.app/jobs/api
"""
import requests

from sources.base import normalize

NAME = "Himalayas"
STATUS = "live"
REASON = None

_BASE = "https://himalayas.app/jobs/api"
_TIMEOUT = 12
_HEADERS = {"User-Agent": "Flux/1.0 (+local job intelligence dashboard)"}


def fetch() -> list:
    try:
        resp = requests.get(_BASE, params={"limit": 100}, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return []

    out = []
    for job in payload.get("jobs", []):
        locations = job.get("locationRestrictions") or []
        location = ", ".join(locations) if locations else "Remote"
        out.append(normalize(
            source=NAME,
            id_parts=(str(job.get("guid", "")), job.get("title", ""), job.get("companyName", "")),
            title=job.get("title"),
            company=job.get("companyName"),
            location=location,
            employment_type=job.get("employmentType") or "Remote",
            posted_at=job.get("pubDate"),
            url=job.get("applicationLink"),
            description=job.get("description") or job.get("excerpt") or "",
        ))
    return out
