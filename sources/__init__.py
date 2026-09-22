"""
Source registry. `LIVE_MODULES` are real adapters (some gated on an
optional API key); `STUB_SOURCES` are documented placeholders. The v1
spec named 14 sources — Arbeitnow, The Muse, Jooble, and Careerjet were
added afterward as additional live sources, beyond the original spec.
"""
from sources import (
    adzuna,
    arbeitnow,
    careerjet,
    himalayas,
    jobicy,
    jooble,
    reed,
    remoteok,
    remotive,
    themuse,
    weworkremotely,
)
from sources.stubs import STUB_SOURCES

LIVE_MODULES = [
    jobicy, himalayas, remoteok, remotive, weworkremotely, arbeitnow, themuse,
    reed, adzuna, jooble, careerjet,
]


def source_status() -> list:
    """Summary of every configured source and whether it's actually fetching."""
    status = []
    for mod in LIVE_MODULES:
        status.append({
            "name": mod.NAME,
            "status": mod.STATUS,
            "reason": getattr(mod, "REASON", None),
        })
    for stub in STUB_SOURCES:
        status.append({
            "name": stub.NAME,
            "status": stub.STATUS,
            "reason": stub.REASON,
        })
    return status


def fetch_all_callables():
    """Return a list of (name, callable) pairs the scanner should run in parallel."""
    return [(mod.NAME, mod.fetch) for mod in LIVE_MODULES]
