"""
F3: Intelligent Scoring.

Score = Requirements (60) + Title (20) + Seniority (10) + Location (10)
Essential requirements: missing 1 caps the total at 72, missing 2+ caps it at 60.
Bands: Strong (80+), Good (65-79), Stretch (50-64), Weak (<50).
"""
from __future__ import annotations

import re

from skills_data import (
    QUALIFYING_LOCATION_PATTERNS,
    TITLE_PATTERNS,
    detect_seniority_level,
    find_skills,
    years_to_level,
)

_DESIRABLE_MARKERS = re.compile(
    r"(desirable|nice[\s-]?to[\s-]?have|preferred(?! candidate)|bonus points?|would be an advantage)",
    re.IGNORECASE,
)


def _split_essential_desirable(description: str):
    if not description:
        return "", ""
    match = _DESIRABLE_MARKERS.search(description)
    if not match:
        return description, ""
    return description[: match.start()], description[match.start():]


def _band(total: int) -> str:
    if total >= 80:
        return "Strong"
    if total >= 65:
        return "Good"
    if total >= 50:
        return "Stretch"
    return "Weak"


def _title_score(title: str) -> int:
    for pattern, points in TITLE_PATTERNS:
        if pattern.search(title or ""):
            return points
    # Loose fallback: any generic PM/BA/Scrum wording still earns a little credit.
    if re.search(r"manager|analyst|scrum|coach|coordinator|lead", title or "", re.IGNORECASE):
        return 5
    return 0


def _location_score(location: str, description: str) -> int:
    haystack = f"{location or ''} {description or ''}"
    return 10 if any(p.search(haystack) for p in QUALIFYING_LOCATION_PATTERNS) else 0


def _seniority_score(job_title: str, description: str, cv_years: int) -> int:
    job_level = detect_seniority_level(f"{job_title or ''} {description or ''}")
    cv_level = years_to_level(cv_years) if cv_years else 2  # assume mid-level if unknown
    if cv_level >= job_level:
        return 10
    if cv_level == job_level - 1:
        return 5
    return 0


def score_job(job: dict, cv_evidence: set, cv_years: int) -> dict:
    description = job.get("description", "")
    essential_text, desirable_text = _split_essential_desirable(description)

    essential_skills = find_skills(essential_text)
    desirable_skills = find_skills(desirable_text) - essential_skills
    all_job_skills = essential_skills | desirable_skills

    if essential_skills:
        matched = essential_skills & cv_evidence
        missing = essential_skills - cv_evidence
        requirements_ratio = len(matched) / len(essential_skills)
    elif all_job_skills:
        matched = all_job_skills & cv_evidence
        missing = set()  # nothing explicitly "essential" was identified
        requirements_ratio = len(matched) / len(all_job_skills)
    else:
        matched, missing, requirements_ratio = set(), set(), 0.5  # no signal either way

    requirements_score = round(requirements_ratio * 60)
    title_score = _title_score(job.get("title", ""))
    seniority_score = _seniority_score(job.get("title", ""), description, cv_years)
    location_score = _location_score(job.get("location", ""), description)

    raw_total = requirements_score + title_score + seniority_score + location_score

    missing_count = len(missing)
    if missing_count == 1:
        cap = 72
    elif missing_count >= 2:
        cap = 60
    else:
        cap = 100
    total = min(raw_total, cap)

    gaps = [{"label": label} for label in sorted(missing)]

    return {
        "score": total,
        "band": _band(total),
        "gaps": gaps,
        "breakdown": {
            "requirements": requirements_score,
            "title": title_score,
            "seniority": seniority_score,
            "location": location_score,
        },
    }


def score_all(jobs: list, cv: dict | None) -> list:
    cv_evidence = set(cv["evidence"]) if cv else set()
    cv_years = cv.get("years_experience", 0) if cv else 0
    for job in jobs:
        job["match"] = score_job(job, cv_evidence, cv_years)
    return jobs
