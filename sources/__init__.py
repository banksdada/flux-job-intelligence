"""
Source registry. `LIVE_MODULES` are real adapters (some gated on an
optional API key); `STUB_SOURCES` are documented placeholders. Together
they make up the 14 sources referenced in the v1 spec.
"""
from sources import adzuna, himalayas, jobicy, reed, remoteok, remotive, weworkremotely
from sources.stubs import STUB_SOURCES

LIVE_MODULES = [jobicy, himalayas, remoteok, remotive, weworkremotely, reed, adzuna]


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
