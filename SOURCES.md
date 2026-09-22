# Job source status

The v1 spec names 14 sources; four more (Arbeitnow, The Muse, Jooble,
Careerjet) were added afterward for broader coverage. Here's exactly what
each one does in this build.

| Source | Status | Notes |
|---|---|---|
| Jobicy | ✅ Live | Public JSON API, no key. Queried by role tag. |
| Himalayas | ✅ Live | Public JSON API, no key. |
| RemoteOK | ✅ Live | Public JSON API, no key. First array element is a legal notice, not a job — handled. |
| Remotive | ✅ Live | Public JSON API, no key. Queried per role search term. |
| We Work Remotely | ✅ Live | Public RSS feeds, no key. Titles arrive as "Company: Job Title" — split and normalized. |
| Arbeitnow | ✅ Live | Public JSON API, no key. European (incl. UK) roles from various ATS platforms; explicit `remote` flag per posting. |
| The Muse | ✅ Live | Public JSON API, no key. Queried against its "Project Management" category — a direct match for Flux's target roles. |
| Reed | 🔑 Live once configured | Official UK job board API. Free key at https://www.reed.co.uk/developers/jobseeker — set `REED_API_KEY`. Disabled (returns no jobs, shows as a stub in `/api/sources`) until set. |
| Adzuna | 🔑 Live once configured | Aggregates many UK boards. Free credentials at https://developer.adzuna.com/ — set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`. Disabled until set. |
| Jooble | 🔑 Live once configured | Broad UK job aggregator. Free key at https://jooble.org/api/about — set `JOOBLE_API_KEY`. Disabled until set. |
| Careerjet | 🔑 Live once configured | Broad UK job aggregator. Free affiliate ID at https://www.careerjet.com/partners/api — set `CAREERJET_AFFILIATE_ID`. Disabled until set. Field names for its response are taken from Careerjet's official client library docs rather than a live call (its API needs a registered affiliate ID to query at all) — if you register and see zero results once it shows "live", that's the first place to check. |
| LinkedIn | 🚫 Stub | No public jobs API. Scraping it violates LinkedIn's Terms of Service, so this isn't implemented. |
| Indeed | 🚫 Stub | Indeed's publisher API was retired; current job-feed access is partner-only and requires a commercial agreement with Indeed. |
| Guardian Jobs | 🚫 Stub | The standalone Guardian Jobs board has been discontinued. |
| cwjobs | 🚫 Stub | Part of the StepStone/Totaljobs Group network; no public API. |
| Totaljobs | 🚫 Stub | Same network as cwjobs; no public API. |
| ContractorUK | 🚫 Stub | No public API. |
| efinancialcareers | 🚫 Stub | No public API. |

## Adding a real integration for a stubbed source

Each live adapter (`sources/jobicy.py`, `sources/reed.py`, etc.)
implements the same tiny contract:

```python
NAME = "Source Name"
STATUS = "live"          # or "stub"
REASON = None             # or a string explaining why it's a stub

def fetch() -> list[dict]:
    ...  # return a list of jobs via sources.base.normalize(...)
```

`sources/base.py`'s `normalize()` builds the standard job schema (id,
title, company, location, employment_type, posted_at as ISO 8601 UTC,
source, url, description) and handles id generation and date parsing
for you. Once a module implements `fetch()`, register it in
`sources/__init__.py`'s `LIVE_MODULES` list and it's picked up by the
scanner automatically — no other code changes needed.

If you have a licensed data feed or a partner API agreement with one
of the stubbed sources (Indeed's Publisher Program, for example),
that's the natural place to plug it in.
