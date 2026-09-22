"""
Unit tests for the four sources added after the v1 spec: Arbeitnow, The
Muse (both free, no key), and Jooble, Careerjet (both free, key-gated).

Each is mocked against its documented/verified response schema — see the
module docstrings in sources/*.py for where each shape came from. No live
network access required; run with:

    python -m pytest tests/test_new_sources.py -v
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import sources.arbeitnow as arbeitnow  # noqa: E402
import sources.careerjet as careerjet  # noqa: E402
import sources.jooble as jooble  # noqa: E402
import sources.themuse as themuse  # noqa: E402


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


# --- Arbeitnow -------------------------------------------------------

ARBEITNOW_PAYLOAD = {
    "data": [
        {
            "slug": "delivery-manager-acme-123",
            "company_name": "Acme Ltd",
            "title": "Delivery Manager",
            "description": "<p>Run our agile delivery team.</p>",
            "remote": True,
            "url": "https://www.arbeitnow.com/jobs/companies/acme/delivery-manager-acme-123",
            "tags": ["Agile"],
            "job_types": ["Full-time"],
            "location": "Berlin",
            "created_at": 1758000000,
        }
    ]
}


def test_arbeitnow_parses_and_marks_remote():
    with patch("sources.arbeitnow.requests.get", return_value=FakeResponse(ARBEITNOW_PAYLOAD)):
        jobs = arbeitnow.fetch()
    assert len(jobs) == 1
    job = jobs[0]
    assert job["title"] == "Delivery Manager"
    assert job["company"] == "Acme Ltd"
    assert job["location"] == "Remote"  # remote=True overrides the raw "Berlin" location
    assert job["source"] == "Arbeitnow"
    assert job["posted_at"].startswith("2025-")  # unix timestamp normalized to ISO8601


def test_arbeitnow_network_failure_returns_empty_list():
    with patch("sources.arbeitnow.requests.get", side_effect=ConnectionError("boom")):
        assert arbeitnow.fetch() == []


# --- The Muse ----------------------------------------------------------

THEMUSE_PAYLOAD = {
    "results": [
        {
            "id": 21763098,
            "name": "Senior Business Analyst",
            "contents": "<p>Own requirements gathering.</p>",
            "type": "Full Time",
            "publication_date": "2026-07-18T00:36:26Z",
            "locations": [{"name": "London, UK"}, {"name": "Remote"}],
            "categories": [{"name": "Project Management"}],
            "levels": [{"name": "Senior Level", "short_name": "senior"}],
            "company": {"id": 61, "short_name": "acme", "name": "Acme"},
            "refs": {"landing_page": "https://www.themuse.com/jobs/acme/senior-business-analyst"},
        }
    ],
    "page": 0,
    "page_count": 5,
}


def test_themuse_parses_nested_fields():
    with patch("sources.themuse.requests.get", return_value=FakeResponse(THEMUSE_PAYLOAD)):
        jobs = themuse.fetch()
    # _PAGES=2, same fixture returned both times, dedupe should collapse to 1
    assert len(jobs) == 1
    job = jobs[0]
    assert job["title"] == "Senior Business Analyst"
    assert job["company"] == "Acme"
    assert job["location"] == "London, UK, Remote"
    assert job["url"] == "https://www.themuse.com/jobs/acme/senior-business-analyst"
    assert job["source"] == "The Muse"


def test_themuse_one_bad_page_does_not_lose_the_other():
    calls = {"n": 0}

    def flaky_get(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("boom")
        return FakeResponse(THEMUSE_PAYLOAD)

    with patch("sources.themuse.requests.get", side_effect=flaky_get):
        jobs = themuse.fetch()
    assert len(jobs) == 1


# --- Jooble (key-gated) -------------------------------------------------

JOOBLE_PAYLOAD = {
    "totalCount": 1,
    "jobs": [
        {
            "id": 987,
            "title": "Scrum Master",
            "location": "Manchester, UK",
            "snippet": "Facilitate ceremonies for two squads.",
            "salary": "",
            "source": "example.com",
            "type": "Permanent",
            "link": "https://jooble.org/desc/987",
            "company": "Beta Corp",
            "updated": "2026-09-20T09:00:00.0000000",
        }
    ],
}


def test_jooble_disabled_without_key_returns_empty():
    original = config.JOOBLE_API_KEY
    config.JOOBLE_API_KEY = ""
    try:
        assert jooble._enabled() is False
        assert jooble.fetch() == []
    finally:
        config.JOOBLE_API_KEY = original


def test_jooble_parses_when_key_is_set():
    original = config.JOOBLE_API_KEY
    config.JOOBLE_API_KEY = "fake-key"
    try:
        with patch("sources.jooble.requests.post", return_value=FakeResponse(JOOBLE_PAYLOAD)):
            jobs = jooble.fetch()
        assert len(jobs) >= 1
        job = jobs[0]
        assert job["title"] == "Scrum Master"
        assert job["company"] == "Beta Corp"
        assert job["source"] == "Jooble"
    finally:
        config.JOOBLE_API_KEY = original


# --- Careerjet (key-gated) -----------------------------------------------

CAREERJET_PAYLOAD = {
    "type": "JOBS",
    "jobs": [
        {
            "title": "Programme Manager",
            "locations": "Leeds, UK",
            "company": "Gamma PLC",
            "salary": "£60,000 - £70,000",
            "date": "2026-09-19 14:30:00",
            "url": "https://www.careerjet.co.uk/jobad/12345",
            "site": "example.com",
            "description": "Lead a multi-workstream transformation programme.",
        }
    ],
    "pages": 1,
}


def test_careerjet_disabled_without_key_returns_empty():
    original = config.CAREERJET_AFFILIATE_ID
    config.CAREERJET_AFFILIATE_ID = ""
    try:
        assert careerjet._enabled() is False
        assert careerjet.fetch() == []
    finally:
        config.CAREERJET_AFFILIATE_ID = original


def test_careerjet_parses_when_key_is_set():
    original = config.CAREERJET_AFFILIATE_ID
    config.CAREERJET_AFFILIATE_ID = "fake-affid"
    try:
        with patch("sources.careerjet.requests.get", return_value=FakeResponse(CAREERJET_PAYLOAD)):
            jobs = careerjet.fetch()
        assert len(jobs) >= 1
        job = jobs[0]
        assert job["title"] == "Programme Manager"
        assert job["company"] == "Gamma PLC"
        assert job["source"] == "Careerjet"
    finally:
        config.CAREERJET_AFFILIATE_ID = original


def test_careerjet_ignores_non_jobs_response_type():
    original = config.CAREERJET_AFFILIATE_ID
    config.CAREERJET_AFFILIATE_ID = "fake-affid"
    try:
        with patch("sources.careerjet.requests.get", return_value=FakeResponse({"type": "LOCATIONS"})):
            assert careerjet.fetch() == []
    finally:
        config.CAREERJET_AFFILIATE_ID = original
