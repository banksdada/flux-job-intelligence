"""
Adzuna — aggregates many UK job boards, requires free API credentials.
Register at https://developer.adzuna.com/ and set ADZUNA_APP_ID /
ADZUNA_APP_KEY (see .env.example). Disabled automatically if unset.
"""
import requests

import config
from sources.base import normalize

NAME = "Adzuna"


def _enabled() -> bool:
    return bool(config.ADZUNA_APP_ID and config.ADZUNA_APP_KEY)


STATUS = "live" if _enabled() else "stub"
REASON = None if _enabled() else "Requires free ADZUNA_APP_ID/ADZUNA_APP_KEY (see .env.example)"

_BASE = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
_SEARCHES = ["project manager", "programme manager", "delivery manager", "scrum master", "business analyst"]
_TIMEOUT = 12


def _fetch_search(term: str) -> list:
    resp = requests.get(
        _BASE,
        params={
            "app_id": config.ADZUNA_APP_ID,
            "app_key": config.ADZUNA_APP_KEY,
            "what": term,
            "results_per_page": 50,
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    payload = resp.json()
    out = []
    for job in payload.get("results", []):
        company = (job.get("company") or {}).get("display_name")
        location = (job.get("location") or {}).get("display_name")
        out.append(normalize(
            source=NAME,
            id_parts=(str(job.get("id", "")),),
            title=job.get("title"),
            company=company,
            location=location,
            employment_type=job.get("contract_time") or job.get("contract_type") or "Not specified",
            posted_at=job.get("created"),
            url=job.get("redirect_url"),
            description=job.get("description") or "",
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
