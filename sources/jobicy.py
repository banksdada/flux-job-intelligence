"""
Jobicy — public JSON API, no key required.
API: https://jobicy.com/api/v2/remote-jobs
"""
import requests

from sources.base import normalize

NAME = "Jobicy"
STATUS = "live"
REASON = None

_BASE = "https://jobicy.com/api/v2/remote-jobs"
_TAGS = ["project-manager", "delivery-manager", "business-analyst", "scrum-master"]
_TIMEOUT = 12
_HEADERS = {"User-Agent": "Flux/1.0 (+local job intelligence dashboard)"}


def _fetch_tag(tag: str) -> list:
    resp = requests.get(_BASE, params={"count": 30, "tag": tag}, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    out = []
    for job in payload.get("jobs", []):
        out.append(normalize(
            source=NAME,
            id_parts=(str(job.get("id", "")), job.get("jobTitle", ""), job.get("companyName", "")),
            title=job.get("jobTitle"),
            company=job.get("companyName"),
            location=job.get("jobGeo") or "Remote",
            employment_type=", ".join(job.get("jobType", []) or []) or "Remote",
            posted_at=job.get("pubDate"),
            url=job.get("url"),
            description=job.get("jobDescription") or job.get("jobExcerpt") or "",
        ))
    return out


def fetch() -> list:
    jobs, seen = [], set()
    for tag in _TAGS:
        try:
            for job in _fetch_tag(tag):
                if job["id"] not in seen:
                    seen.add(job["id"])
                    jobs.append(job)
        except Exception:
            # A single bad tag/network blip shouldn't take the whole source down.
            continue
    return jobs
