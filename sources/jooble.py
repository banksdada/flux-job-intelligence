"""
Jooble — broad UK job aggregator, requires a free API key.
Register at https://jooble.org/api/about and set JOOBLE_API_KEY (see
.env.example). Disabled automatically if unset.

Unlike the other search-gated sources, Jooble's API takes the key in the
URL path (not a query param/header) and is a POST, not a GET — see
https://jooble.org/api/{key} in their REST docs.
"""
import requests

import config
from sources.base import normalize

NAME = "Jooble"


def _enabled() -> bool:
    return bool(config.JOOBLE_API_KEY)


STATUS = "live" if _enabled() else "stub"
REASON = None if _enabled() else "Requires a free JOOBLE_API_KEY (see .env.example)"

_SEARCHES = ["project manager", "programme manager", "delivery manager", "scrum master", "business analyst"]
_TIMEOUT = 12


def _fetch_search(term: str) -> list:
    resp = requests.post(
        f"https://jooble.org/api/{config.JOOBLE_API_KEY}",
        json={"keywords": term, "location": "United Kingdom"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    payload = resp.json()
    out = []
    for job in payload.get("jobs", []):
        out.append(normalize(
            source=NAME,
            id_parts=(str(job.get("id", "")), job.get("title", ""), job.get("company", "")),
            title=job.get("title"),
            company=job.get("company"),
            location=job.get("location"),
            employment_type=job.get("type") or "Not specified",
            posted_at=job.get("updated"),
            url=job.get("link"),
            description=job.get("snippet") or "",
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
