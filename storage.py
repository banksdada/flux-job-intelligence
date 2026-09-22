"""
Local JSON persistence. No database, no cloud — everything lives under
config.DATA_DIR (mount this as a volume when running in a container so
scan history / bookmarks / CV survive a redeploy).
"""
import json
import threading

import config

_lock = threading.RLock()


def _read(path, default):
    with _lock:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default


def _write(path, data):
    with _lock:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(path)


# --- Jobs ---
def load_jobs() -> list:
    return _read(config.JOBS_FILE, [])


def save_jobs(jobs: list) -> None:
    _write(config.JOBS_FILE, jobs)


# --- CV ---
def load_cv():
    return _read(config.CV_FILE, None)


def save_cv(cv: dict) -> None:
    _write(config.CV_FILE, cv)


# --- Bookmarks (set of job ids) ---
def load_bookmarks() -> set:
    return set(_read(config.BOOKMARKS_FILE, []))


def save_bookmarks(bookmark_ids: set) -> None:
    _write(config.BOOKMARKS_FILE, sorted(bookmark_ids))


def toggle_bookmark(job_id: str) -> bool:
    """Returns the new bookmarked state (True=now saved)."""
    with _lock:
        ids = load_bookmarks()
        if job_id in ids:
            ids.discard(job_id)
            saved = False
        else:
            ids.add(job_id)
            saved = True
        save_bookmarks(ids)
        return saved
