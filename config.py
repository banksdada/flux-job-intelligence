"""
Flux configuration.

Reads settings from real OS environment variables first (this is how
Coolify / Docker inject config), and falls back to a local .env file
for convenience when running outside a container. No secrets are
hardcoded anywhere in this codebase.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Real environment variables always win over .env values.
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")

# --- Server ---
PORT = int(os.environ.get("PORT", "8765"))
HOST = os.environ.get("HOST", "0.0.0.0")

# --- Storage ---
DATA_DIR = Path(os.environ.get("FLUX_DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
JOBS_FILE = DATA_DIR / "jobs.json"
CV_FILE = DATA_DIR / "cv.json"
BOOKMARKS_FILE = DATA_DIR / "bookmarks.json"

# --- Optional source credentials (leave blank to disable that source) ---
REED_API_KEY = os.environ.get("REED_API_KEY", "").strip()
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "").strip()
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "").strip()
JOOBLE_API_KEY = os.environ.get("JOOBLE_API_KEY", "").strip()
CAREERJET_AFFILIATE_ID = os.environ.get("CAREERJET_AFFILIATE_ID", "").strip()

# Careerjet requires a "url of the page that will display results" on every
# request — there's no real visitor page for a background scan, so this is
# just where Flux itself is reachable.
FLUX_PUBLIC_URL = os.environ.get("FLUX_PUBLIC_URL", "https://fluxjobs.baseuse.xyz")

# --- Scanning ---
SCAN_INTERVAL_SECONDS = int(os.environ.get("FLUX_SCAN_INTERVAL", str(5 * 60)))
ROLLING_WINDOW_DAYS = 7
MAX_PARALLEL_SOURCES = 14

# --- Upload limits ---
MAX_CV_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_CV_EXTENSIONS = {".docx", ".txt", ".md"}

# --- Notification threshold ---
NEW_MATCH_ALERT_THRESHOLD = 65
