"""
RemoteOK — public JSON API, no key required.
API: https://remoteok.com/api  (first array element is a legal-notice
object, not a job — must be skipped).
"""
import requests

from sources.base import normalize

NAME = "RemoteOK"
STATUS = "live"
REASON = None

_BASE = "https://remoteok.com/api"
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
    for job in payload:
        if not isinstance(job, dict) or "position" not in job:
            continue  # skip the legal-notice entry
        out.append(normalize(
            source=NAME,
            id_parts=(str(job.get("id", "")), job.get("position", ""), job.get("company", "")),
            title=job.get("position"),
            company=job.get("company"),
            location=job.get("location") or "Remote",
            employment_type="Remote",
            posted_at=job.get("date"),
            url=job.get("url"),
            description=job.get("description") or "",
        ))
    return out
