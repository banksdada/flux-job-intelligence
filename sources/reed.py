"""
Reed — official UK job board API, requires a free API key.
Register at https://www.reed.co.uk/developers/jobseeker and set
REED_API_KEY (see .env.example). Disabled automatically if unset.
"""
import requests

import config
from sources.base import normalize

NAME = "Reed"


def _enabled() -> bool:
    return bool(config.REED_API_KEY)


STATUS = "live" if _enabled() else "stub"
REASON = None if _enabled() else "Requires a free REED_API_KEY (see .env.example)"

_BASE = "https://www.reed.co.uk/api/1.0/search"
_SEARCHES = ["project manager", "programme manager", "delivery manager", "scrum master", "business analyst"]
_TIMEOUT = 12


def _fetch_search(term: str) -> list:
    resp = requests.get(
        _BASE,
        params={"keywords": term, "resultsToTake": 50},
        auth=(config.REED_API_KEY, ""),
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    payload = resp.json()
    out = []
    for job in payload.get("results", []):
        employment_type = "Full-time" if job.get("fullTime") else "Part-time"
        if job.get("contractType"):
            employment_type = job["contractType"]
        out.append(normalize(
            source=NAME,
            id_parts=(str(job.get("jobId", "")),),
            title=job.get("jobTitle"),
            company=job.get("employerName"),
            location=job.get("locationName"),
            employment_type=employment_type,
            posted_at=job.get("date"),
            url=job.get("jobUrl"),
            description=job.get("jobDescription") or "",
        ))
    return out


def fetch() -> list:
    if not _enabled():
        return []
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
