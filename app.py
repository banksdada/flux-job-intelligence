"""
Flux backend — a dependency-light ThreadingHTTPServer exposing the v1
API and serving the static frontend. No framework, per the spec's
"Lightweight, parallel job fetching" architecture goal.
"""
from __future__ import annotations

import json
import mimetypes
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import config
import cv_parser
import scanner
import scoring
import storage
from multipart import MultipartError, parse_first_file
from sources import source_status

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"
    ),
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "no-referrer",
}


def _job_with_bookmark(job: dict, bookmark_ids: set) -> dict:
    out = dict(job)
    out["bookmarked"] = job["id"] in bookmark_ids
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "Flux/1.0"

    # --- low-level helpers -------------------------------------------------
    def _set_common_headers(self):
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._set_common_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, rel_path: str):
        if rel_path in ("", "/"):
            rel_path = "index.html"
        rel_path = rel_path.lstrip("/")
        target = (FRONTEND_DIR / rel_path).resolve()
        # Path-traversal guard: resolved path must stay inside FRONTEND_DIR.
        if FRONTEND_DIR not in target.parents and target != FRONTEND_DIR:
            self._send_json(403, {"error": "Forbidden"})
            return
        if not target.is_file():
            self._send_json(404, {"error": "Not found"})
            return
        content_type, _ = mimetypes.guess_type(str(target))
        data = target.read_bytes()
        self.send_response(200)
        self._set_common_headers()
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(length) if length else b""

    def _is_fetchlike(self) -> bool:
        """Lightweight CSRF guard: plain HTML forms cannot set this header,
        so a simple cross-site form POST won't pass this check."""
        return self.headers.get("X-Requested-With") == "Flux"

    # --- routing -------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/jobs":
                return self._handle_get_jobs()
            if parsed.path == "/api/sources":
                return self._send_json(200, {"sources": source_status()})
            if parsed.path == "/api/health":
                return self._send_json(200, {"ok": True})
            return self._send_static(parsed.path)
        except Exception:
            traceback.print_exc()
            self._send_json(500, {"error": "Internal server error"})

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/scan":
                return self._handle_scan()
            if parsed.path == "/api/upload-cv":
                return self._handle_upload_cv()
            if parsed.path == "/api/bookmark":
                return self._handle_bookmark()
            return self._send_json(404, {"error": "Not found"})
        except Exception:
            traceback.print_exc()
            self._send_json(500, {"error": "Internal server error"})

    # --- handlers --------------------------------------------------------
    def _handle_get_jobs(self):
        jobs = storage.load_jobs()
        bookmark_ids = storage.load_bookmarks()
        cv = storage.load_cv()
        state = scanner.get_state()
        payload = {
            "jobs": [_job_with_bookmark(j, bookmark_ids) for j in jobs],
            "last_scan": state.get("last_scan"),
            "scanning": state.get("scanning", False),
            "cv_evidence": cv["evidence"] if cv else [],
            "cv_roles": cv["roles"] if cv else [],
            "filter_role": cv.get("filter_role") if cv else None,
            "sources": state.get("sources", []),
            "debug": state.get("debug", {}),
        }
        self._send_json(200, payload)

    def _handle_scan(self):
        if not self._is_fetchlike():
            return self._send_json(403, {"error": "Forbidden"})
        # Kick off the scan in the background so the request returns instantly;
        # the frontend polls /api/jobs + last_scan to see when it's done.
        threading.Thread(target=scanner.run_scan_once, daemon=True).start()
        self._send_json(200, {"started": True})

    def _handle_upload_cv(self):
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return self._send_json(400, {"error": "Expected multipart/form-data"})

        content_length = int(self.headers.get("Content-Length", 0) or 0)
        if content_length <= 0:
            return self._send_json(400, {"error": "Empty request body"})
        if content_length > config.MAX_CV_UPLOAD_BYTES + 4096:  # small allowance for multipart overhead
            return self._send_json(413, {"error": "File too large (max 10MB)"})

        body = self._read_body()
        try:
            filename, file_bytes = parse_first_file(content_type, body, field_name="cv")
        except MultipartError as exc:
            return self._send_json(400, {"error": str(exc)})

        if len(file_bytes) > config.MAX_CV_UPLOAD_BYTES:
            return self._send_json(413, {"error": "File too large (max 10MB)"})

        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in config.ALLOWED_CV_EXTENSIONS:
            return self._send_json(400, {"error": f"Unsupported file type '{ext}'. Use .docx, .txt, or .md"})

        try:
            cv = cv_parser.parse_cv(filename, file_bytes)
        except Exception as exc:
            return self._send_json(400, {"error": f"Could not parse CV: {exc}"})

        storage.save_cv(cv)

        # Re-score every stored job immediately against the new CV.
        jobs = storage.load_jobs()
        scoring.score_all(jobs, cv)
        storage.save_jobs(jobs)

        self._send_json(200, {
            "success": True,
            "evidence_areas": len(cv["evidence"]),
            "roles": cv["roles"],
            "filter_role": cv["filter_role"],
            "job_scores": {j["id"]: j["match"] for j in jobs},
            "message": f"CV parsed: {len(cv['evidence'])} areas",
        })

    def _handle_bookmark(self):
        if not self._is_fetchlike():
            return self._send_json(403, {"error": "Forbidden"})
        try:
            payload = json.loads(self._read_body() or b"{}")
        except json.JSONDecodeError:
            return self._send_json(400, {"error": "Invalid JSON"})
        job_id = payload.get("job_id")
        if not job_id:
            return self._send_json(400, {"error": "job_id is required"})
        bookmarked = storage.toggle_bookmark(job_id)
        self._send_json(200, {"job_id": job_id, "bookmarked": bookmarked})

    # Quiet, structured access logging instead of BaseHTTPRequestHandler's default.
    def log_message(self, fmt, *args):
        print(f"[flux] {self.address_string()} - {fmt % args}")


def create_server() -> ThreadingHTTPServer:
    return ThreadingHTTPServer((config.HOST, config.PORT), Handler)


def main():
    scanner.start_background_scanner()
    httpd = create_server()
    print(f"Flux listening on http://{config.HOST}:{config.PORT}")
    print(f"Data directory: {config.DATA_DIR}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
