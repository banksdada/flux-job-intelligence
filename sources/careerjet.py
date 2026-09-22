"""
Careerjet — broad UK job aggregator, requires a free affiliate ID.
Register at https://www.careerjet.com/partners/api and set
CAREERJET_AFFILIATE_ID (see .env.example). Disabled automatically if unset.

Careerjet's API is per-locale (locale_code picks the regional site, e.g.
en_GB -> careerjet.co.uk) and requires user_ip/user_agent/url on every
request, since it's designed for displaying results to an actual visitor.
This is a background scan with no real visitor, so those are filled with
a fixed placeholder — Careerjet's docs don't document rejecting that, but
if your affiliate account ever reports zero results, this is the first
thing to check against their support.
"""
import requests

import config
from sources.base import normalize

NAME = "Careerjet"


def _enabled() -> bool:
    return bool(config.CAREERJET_AFFILIATE_ID)


STATUS = "live" if _enabled() else "stub"
REASON = None if _enabled() else "Requires a free CAREERJET_AFFILIATE_ID (see .env.example)"

_BASE = "http://public.api.careerjet.net/search"
_SEARCHES = ["project manager", "programme manager", "delivery manager", "scrum master", "business analyst"]
_TIMEOUT = 12
_USER_AGENT = "Flux/1.0 (+local job intelligence dashboard)"
_PLACEHOLDER_IP = "0.0.0.0"  # no real end-user for a background scan — see module docstring


def _fetch_search(term: str) -> list:
    resp = requests.get(
        _BASE,
        params={
            "keywords": term,
            "location": "UK",
            "locale_code": "en_GB",
            "affid": config.CAREERJET_AFFILIATE_ID,
            "user_ip": _PLACEHOLDER_IP,
            "user_agent": _USER_AGENT,
            "url": config.FLUX_PUBLIC_URL,
        },
        headers={"User-Agent": _USER_AGENT},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("type") != "JOBS":
        return []  # "LOCATIONS" (ambiguous location) or "ERROR"

    out = []
    for job in payload.get("jobs", []):
        out.append(normalize(
            source=NAME,
            id_parts=(str(job.get("url", "")), job.get("title", ""), job.get("company", "")),
            title=job.get("title"),
            company=job.get("company"),
            location=job.get("locations") or "Not specified",
            employment_type="Not specified",
            posted_at=job.get("date"),
            url=job.get("url"),
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
