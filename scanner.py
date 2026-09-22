"""
F2: Job Scanning.

Scans all live sources in parallel, keeps only target-role / UK-or-Remote
postings, deduplicates same title+company into one entry, maintains a
7-day rolling window, re-scores everything against the stored CV, and
persists the result. Runs on its own background thread every
config.SCAN_INTERVAL_SECONDS (default 5 minutes) and never dies on a
single source's failure.
"""
from __future__ import annotations

import concurrent.futures
import threading
import time
from datetime import datetime, timedelta, timezone

import config
import scoring
import storage
from skills_data import (
    QUALIFYING_LOCATION_PATTERNS,
    classify_employment_type,
    classify_location,
    detect_roles,
)
from sources import fetch_all_callables

_scan_lock = threading.Lock()
_state = {
    "last_scan": None,
    "scanning": False,
    "sources": [],
    "error": None,
}


def _role_and_location_hits(job: dict):
    role_haystack = f"{job.get('title', '')} {job.get('description', '')}"
    role_hit = bool(detect_roles(role_haystack))
    location_haystack = f"{job.get('location', '')} {job.get('description', '')}"
    location_hit = any(p.search(location_haystack) for p in QUALIFYING_LOCATION_PATTERNS)
    return role_hit, location_hit


def _passes_role_and_location_filter(job: dict) -> bool:
    """F2: filter for target roles and UK/Remote locations only."""
    role_hit, location_hit = _role_and_location_hits(job)
    return role_hit and location_hit


def _dedupe(jobs: list) -> list:
    """Same title + company = 1 entry; keep the earliest-posted duplicate."""
    seen = {}
    for job in jobs:
        key = (job.get("title", "").strip().lower(), job.get("company", "").strip().lower())
        existing = seen.get(key)
        if existing is None or job.get("posted_at", "") < existing.get("posted_at", ""):
            seen[key] = job
    return list(seen.values())


def _within_window(job: dict) -> bool:
    try:
        posted = datetime.strptime(job["posted_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (KeyError, ValueError, TypeError):
        return True  # don't silently drop a job we can't date
    return datetime.now(timezone.utc) - posted <= timedelta(days=config.ROLLING_WINDOW_DAYS)


def run_scan_once() -> dict:
    with _scan_lock:
        _state["scanning"] = True

    fetched, per_source = [], []
    callables = fetch_all_callables()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(callables))) as pool:
        future_map = {pool.submit(fn): name for name, fn in callables}
        for future in concurrent.futures.as_completed(future_map, timeout=90):
            name = future_map[future]
            try:
                result = future.result()
                per_source.append({"name": name, "count": len(result), "ok": True})
                fetched.extend(result)
            except Exception as exc:  # a single source must never take the scan down
                per_source.append({"name": name, "count": 0, "ok": False, "error": str(exc)})

    filtered = []
    role_hit_count = 0
    location_hit_count = 0
    rejected_sample = []
    for job in fetched:
        role_hit, location_hit = _role_and_location_hits(job)
        if role_hit:
            role_hit_count += 1
        if location_hit:
            location_hit_count += 1
        if role_hit and location_hit:
            filtered.append(job)
        elif len(rejected_sample) < 15:
            rejected_sample.append({
                "source": job.get("source"),
                "title": job.get("title"),
                "location": job.get("location"),
                "role_hit": role_hit,
                "location_hit": location_hit,
            })
    debug = {
        "total_fetched": len(fetched),
        "role_hits": role_hit_count,
        "location_hits": location_hit_count,
        "both_hits": len(filtered),
        "rejected_sample": rejected_sample,
    }

    for job in filtered:
        job["roles"] = detect_roles(f"{job.get('title', '')} {job.get('description', '')}")
        job["role"] = job["roles"][0] if job["roles"] else None
        job["location_category"] = classify_location(job.get("location", ""), job.get("description", ""))
        job["employment_category"] = classify_employment_type(job.get("employment_type", ""))

    existing = storage.load_jobs()
    previous_ids = {j["id"] for j in existing}
    by_id = {j["id"]: j for j in existing}
    for job in filtered:
        by_id[job["id"]] = job  # fresh fetch replaces any stale copy of the same posting

    merged = _dedupe(list(by_id.values()))
    merged = [j for j in merged if _within_window(j)]

    cv = storage.load_cv()
    scoring.score_all(merged, cv)
    storage.save_jobs(merged)

    new_alerts = [
        job["id"] for job in merged
        if job["id"] not in previous_ids
        and job.get("match", {}).get("score", 0) >= config.NEW_MATCH_ALERT_THRESHOLD
    ]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _scan_lock:
        _state.update({
            "last_scan": now, "scanning": False, "sources": per_source, "error": None, "debug": debug,
        })

    return {"last_scan": now, "total_jobs": len(merged), "new_alerts": new_alerts, "sources": per_source}


def get_state() -> dict:
    with _scan_lock:
        return dict(_state)


def start_background_scanner() -> threading.Thread:
    def _loop():
        while True:
            try:
                run_scan_once()
            except Exception as exc:
                with _scan_lock:
                    _state["error"] = str(exc)
                    _state["scanning"] = False
            time.sleep(config.SCAN_INTERVAL_SECONDS)

    thread = threading.Thread(target=_loop, name="flux-scanner", daemon=True)
    thread.start()
    return thread
