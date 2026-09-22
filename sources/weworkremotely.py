"""
We Work Remotely — public RSS feeds, no key required.
Feed titles are formatted "Company: Job Title".
"""
import xml.etree.ElementTree as ET

import requests

from sources.base import normalize

NAME = "We Work Remotely"
STATUS = "live"
REASON = None

_FEEDS = [
    "https://weworkremotely.com/categories/remote-management-and-finance-jobs.rss",
    "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
]
_TIMEOUT = 12
_HEADERS = {"User-Agent": "Flux/1.0 (+local job intelligence dashboard)"}


def _fetch_feed(feed_url: str) -> list:
    resp = requests.get(feed_url, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    out = []
    for item in root.iter("item"):
        raw_title = (item.findtext("title") or "").strip()
        company, _, job_title = raw_title.partition(":")
        if not job_title:
            job_title, company = company, "Unknown"
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        description = (item.findtext("description") or "").strip()
        out.append(normalize(
            source=NAME,
            id_parts=(link, raw_title),
            title=job_title.strip(),
            company=company.strip(),
            location="Remote",
            employment_type="Remote",
            posted_at=pub_date,
            url=link,
            description=description,
        ))
    return out


def fetch() -> list:
    jobs, seen = [], set()
    for feed_url in _FEEDS:
        try:
            for job in _fetch_feed(feed_url):
                if job["id"] not in seen:
                    seen.add(job["id"])
                    jobs.append(job)
        except Exception:
            continue
    return jobs
