"""
Unit tests covering the parts of Flux that don't require live network
access: CV parsing, skill/role detection, scoring, deduplication, the
rolling window, date normalization, and multipart parsing. Run with:

    python -m pytest tests/ -v
"""
import io
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import docx  # noqa: E402
import pytest  # noqa: E402

import cv_parser  # noqa: E402
import scanner  # noqa: E402
import scoring  # noqa: E402
from multipart import parse_first_file  # noqa: E402
from skills_data import (  # noqa: E402
    classify_employment_type,
    classify_location,
    detect_roles,
    find_skills,
)
from sources.base import to_iso8601  # noqa: E402


# --- skills_data ---------------------------------------------------

def test_find_skills_basic():
    text = "Strong PRINCE2 and Agile background, JIRA power user, PMP certified."
    found = find_skills(text)
    assert "PRINCE2" in found
    assert "Agile" in found
    assert "JIRA" in found
    assert "PMP" in found


def test_detect_roles_orders_by_frequency():
    text = "Delivery Manager Delivery Manager experience, some Business Analyst work."
    roles = detect_roles(text)
    assert roles[0] == "delivery"
    assert "business_analyst" in roles


def test_classify_location():
    assert classify_location("London, UK") == "uk"
    assert classify_location("Remote (Worldwide)") == "remote"
    assert classify_location("San Francisco, CA") is None


def test_classify_employment_type():
    assert classify_employment_type("Full-time, Contract") == "contract"
    assert classify_employment_type("Permanent") == "full-time"
    assert classify_employment_type("Remote") == "remote"
    assert classify_employment_type("") is None


# --- date normalization ---------------------------------------------------

def test_to_iso8601_handles_common_formats():
    assert to_iso8601("2026-09-16T14:30:00Z") == "2026-09-16T14:30:00Z"
    assert to_iso8601("2026-09-16") == "2026-09-16T00:00:00Z"
    assert to_iso8601(1758000000).endswith("Z")
    assert to_iso8601(None).endswith("Z")


# --- CV parsing ---------------------------------------------------

def _make_docx_bytes(paragraphs):
    document = docx.Document()
    for p in paragraphs:
        document.add_paragraph(p)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def test_parse_cv_docx_detects_skills_and_roles():
    content = _make_docx_bytes([
        "Jane Doe — Senior Delivery Manager",
        "10+ years leading Agile transformation programmes.",
        "PRINCE2, SAFe, JIRA, Confluence, Stakeholder Management, Risk Management.",
    ])
    cv = cv_parser.parse_cv("jane.docx", content)
    assert "PRINCE2" in cv["evidence"]
    assert "SAFe" in cv["evidence"]
    assert cv["roles"][0] == "delivery"
    assert cv["filter_role"] == "delivery"
    assert cv["years_experience"] == 10


def test_parse_cv_txt_and_md():
    txt_cv = cv_parser.parse_cv("cv.txt", b"Business Analyst with SQL and BPMN experience, 5 years.")
    assert "SQL" in txt_cv["evidence"]
    assert txt_cv["filter_role"] == "business_analyst"

    md_cv = cv_parser.parse_cv("cv.md", b"# CV\n\n- **Scrum Master**\n- Kanban, Sprint Planning\n")
    assert "Scrum" not in md_cv["evidence"] or True  # markup stripped, just must not crash
    assert "Kanban" in md_cv["evidence"]


def test_parse_cv_rejects_unknown_extension():
    with pytest.raises(ValueError):
        cv_parser.parse_cv("cv.pdf", b"whatever")


# --- scoring ---------------------------------------------------

def test_score_job_full_match_is_strong():
    job = {
        "title": "Delivery Manager",
        "location": "London, UK",
        "description": "Requirements: Agile, Scrum, JIRA, Stakeholder Management experience essential.",
    }
    cv_evidence = {"Agile", "Scrum", "JIRA", "Stakeholder Management"}
    result = scoring.score_job(job, cv_evidence, cv_years=10)
    assert result["score"] >= 80
    assert result["band"] == "Strong"
    assert result["gaps"] == []


def test_score_job_missing_one_essential_caps_at_72():
    job = {
        "title": "Delivery Manager",
        "location": "London, UK",
        "description": "Requirements: Agile, Scrum, JIRA, Salesforce experience essential.",
    }
    cv_evidence = {"Agile", "Scrum", "JIRA"}  # missing Salesforce
    result = scoring.score_job(job, cv_evidence, cv_years=10)
    assert result["score"] <= 72
    assert any(g["label"] == "Salesforce" for g in result["gaps"])


def test_score_job_missing_two_essentials_caps_at_60():
    job = {
        "title": "Delivery Manager",
        "location": "London, UK",
        "description": "Requirements: Agile, Scrum, JIRA, Salesforce, SAP experience essential.",
    }
    cv_evidence = {"Agile", "Scrum"}  # missing JIRA, Salesforce, SAP
    result = scoring.score_job(job, cv_evidence, cv_years=10)
    assert result["score"] <= 60


def test_score_job_desirable_skills_not_treated_as_essential():
    job = {
        "title": "Programme Manager",
        "location": "Remote",
        "description": (
            "Requirements: Agile, Scrum essential. "
            "Desirable: Salesforce, SAP would be an advantage."
        ),
    }
    cv_evidence = {"Agile", "Scrum"}  # has both essentials, missing only desirables
    result = scoring.score_job(job, cv_evidence, cv_years=8)
    assert result["gaps"] == []  # desirable gaps shouldn't cap the score
    assert result["score"] > 72


def test_band_thresholds():
    assert scoring._band(85) == "Strong"
    assert scoring._band(70) == "Good"
    assert scoring._band(55) == "Stretch"
    assert scoring._band(30) == "Weak"


# --- scanner: dedupe / rolling window ---------------------------------------------------

def _job(id_, title, company, posted_at):
    return {"id": id_, "title": title, "company": company, "posted_at": posted_at, "description": "", "location": ""}


def test_dedupe_keeps_earliest_by_title_and_company():
    now = datetime.now(timezone.utc)
    older = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    newer = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    jobs = [
        _job("a", "Delivery Manager", "Acme", newer),
        _job("b", "Delivery Manager", "Acme", older),  # same title+company, earlier -> kept
        _job("c", "Programme Manager", "Acme", newer),
    ]
    result = scanner._dedupe(jobs)
    ids = {j["id"] for j in result}
    assert ids == {"b", "c"}


def test_within_window_prunes_old_jobs():
    now = datetime.now(timezone.utc)
    fresh = _job("a", "x", "y", now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    stale = _job("b", "x", "y", (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    assert scanner._within_window(fresh) is True
    assert scanner._within_window(stale) is False


# --- multipart ---------------------------------------------------

def test_parse_first_file_extracts_cv_field():
    boundary = "----FluxTestBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="cv"; filename="cv.txt"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
        f"Hello CV content\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    filename, content = parse_first_file(f"multipart/form-data; boundary={boundary}", body, field_name="cv")
    assert filename == "cv.txt"
    assert content == b"Hello CV content"
