# 🌊 Flux v1.0 — CV-Upload Job Intelligence Platform

A self-hosted job intelligence dashboard: upload your CV, it scans job
sources on a timer, scores every posting against your actual skills
(not keyword search), and shows you what's genuinely relevant — with a
transparent breakdown of *why*. Everything runs on infrastructure you
control; nothing is sent to a third party.

Built from `Flux v1.0 Specification` (Sept 16, 2026). See
[SOURCES.md](./SOURCES.md) for exactly which of the spec's 14 job
sources are live vs. stubbed, and why.

## Quick start (local)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional — only needed if you have Reed/Adzuna keys
python3 app.py
```

Open http://localhost:8765. Upload a CV (.docx/.txt/.md), click **Scan
now**, and jobs will start appearing as sources respond. A background
thread re-scans automatically every 5 minutes.

## Deploying on Coolify

Flux ships as a plain Dockerfile + docker-compose.yml, which Coolify
builds natively.

1. Push this project to a git repository your Coolify instance can
   reach (GitHub, GitLab, or a self-hosted Gitea).
2. In Coolify: **+ New Resource → Application → your repo**. Coolify
   will detect `docker-compose.yml` — choose the **Docker Compose**
   build pack (or point it at the `Dockerfile` directly if you'd
   rather manage the compose settings through Coolify's UI).
3. Set the exposed port to **8765** (Coolify's proxy will terminate
   TLS and map its own domain/port to it).
4. Add a **persistent volume** mounted at `/app/data` — this is where
   `jobs.json`, `cv.json`, and `bookmarks.json` live. Without it,
   every redeploy wipes your scan history, CV, and bookmarks.
5. (Optional) Add environment variables if you've registered for free
   API keys — see **Job sources** below:
   - `REED_API_KEY`
   - `ADZUNA_APP_ID` / `ADZUNA_APP_KEY`
6. Deploy. Coolify will build the image from the `Dockerfile` and
   start the container; the healthcheck hits `GET /api/health`.

The app binds `0.0.0.0:8765` by default (both are overridable via
`HOST`/`PORT` env vars), which is what Coolify's reverse proxy expects.

> This Dockerfile/compose setup was written and reviewed carefully and
> the underlying Python app was fully tested (see **What's been
> tested** below), but the actual `docker build` wasn't run in the
> sandbox this was built in (no Docker daemon available there) — do a
> `docker compose up --build` on your Coolify host as your first
> deploy check.

## Job sources

The spec names 14 sources. Real scraping of LinkedIn/Indeed/etc. either
violates their Terms of Service or requires a commercial partner
agreement, so sources split into three groups — full detail and every
adapter's status in [SOURCES.md](./SOURCES.md):

- **Live, no key needed (5):** Jobicy, Himalayas, RemoteOK, Remotive,
  We Work Remotely
- **Live, needs a free API key you register for yourself (2):** Reed,
  Adzuna — disabled until you set their env vars
- **Documented stubs (7):** LinkedIn, Indeed, Guardian Jobs, cwjobs,
  Totaljobs, ContractorUK, efinancialcareers — each has no viable free
  API; `sources/stubs.py` explains why and `sources/base.py` documents
  the `fetch()` contract a real adapter would need to implement

`GET /api/sources` reports live status for all 14 at runtime.

## What's been tested

- 16 unit tests (`python -m pytest tests/`) covering CV parsing, skill
  and role detection, the scoring engine (including the essential-
  requirement score caps), deduplication, the 7-day rolling window,
  date normalization, and multipart upload parsing — all passing.
- The live HTTP server, exercised with real requests: static file
  serving + security headers, CSV/CSRF-style guard on state-changing
  POSTs, CV upload (success + oversize + wrong-extension rejection),
  bookmark toggle persistence, and end-to-end scoring against a seeded
  CV and job set.
- The dashboard itself, driven headlessly in a real browser: rendering,
  all six filters, sorting, pagination (including >25 jobs and the
  empty state), the bookmark star, the score-breakdown expand panel,
  and a 375px-wide layout with zero horizontal scroll and no console
  errors.
- Outbound calls to the real job-board APIs could **not** be exercised
  from the sandbox this was built in (its network policy blocks those
  hosts) — each adapter is written against each API's documented
  public schema and fails safe (catches its own errors and returns an
  empty list) so one source going down, or a schema drift, never takes
  the scan down. Confirm the live sources return real postings once
  this is deployed somewhere with normal internet access.

## Project layout

```
app.py            HTTP server + API routes (stdlib ThreadingHTTPServer)
config.py         Env-driven settings, no hardcoded secrets
scanner.py        F2: parallel scan, dedupe, rolling window, background loop
scoring.py        F3: scoring engine + essential-requirement caps
cv_parser.py      F1: .docx/.txt/.md text extraction + skill/role detection
skills_data.py    Shared skill/role/location vocabulary (60+ skills, 6 roles)
storage.py        Local JSON persistence
multipart.py      Minimal multipart/form-data parser (no deprecated `cgi`)
sources/          One module per job source (see SOURCES.md)
frontend/         Vanilla HTML/CSS/JS dashboard, no build step
tests/            Unit tests (pytest)
Dockerfile, docker-compose.yml   Coolify/Docker packaging
```

## Security notes

- CSP, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection,
  HSTS, and Referrer-Policy are set on every response.
- No inline `onclick`/inline `<script>` — all JS is in `app.js` with
  `addEventListener`, satisfying the CSP `script-src 'self'` with no
  `unsafe-inline`.
- State-changing POST endpoints (`/api/scan`, `/api/bookmark`) require
  an `X-Requested-With: Flux` header, which a plain cross-site HTML
  form can't set — a lightweight CSRF guard appropriate for a
  single-user, self-hosted tool. `/api/upload-cv` is additionally
  gated on a valid `multipart/form-data` content type.
- CV uploads are capped at 10MB and restricted to `.docx`/`.txt`/`.md`
  by extension, checked both before and after reading the body.
- All data — jobs, CV text, bookmarks — stays in the JSON files under
  `FLUX_DATA_DIR`. Nothing is transmitted anywhere except the outbound
  requests each job-source adapter makes to fetch postings.
- The container runs as a non-root user.
