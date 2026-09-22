"""
Shared vocabulary used to read evidence out of a CV and out of job
descriptions, so both sides of the match are scored against the same
dictionary. Each entry is (canonical_label, [regex patterns]).
"""
from __future__ import annotations

import re

# 65 skills/certifications/tools relevant to the v1 target roles
# (Project/Programme/Delivery Management, Scrum, Business Analysis, Agile).
SKILLS = [
    ("PRINCE2", [r"prince\s*2"]),
    ("PMP", [r"\bpmp\b"]),
    ("MSP", [r"\bmsp\b", r"managing successful programmes"]),
    ("Agile", [r"\bagile\b"]),
    ("Scrum", [r"\bscrum\b"]),
    ("SAFe", [r"\bsafe\b", r"scaled agile"]),
    ("Kanban", [r"\bkanban\b"]),
    ("Six Sigma", [r"six sigma"]),
    ("Lean", [r"\blean\b"]),
    ("JIRA", [r"\bjira\b"]),
    ("Confluence", [r"confluence"]),
    ("Trello", [r"\btrello\b"]),
    ("Asana", [r"\basana\b"]),
    ("MS Project", [r"ms project", r"microsoft project"]),
    ("Primavera", [r"primavera"]),
    ("Waterfall", [r"waterfall"]),
    ("ITIL", [r"\bitil\b"]),
    ("TOGAF", [r"\btogaf\b"]),
    ("Change Management", [r"change management"]),
    ("Stakeholder Management", [r"stakeholder management", r"stakeholder engagement"]),
    ("Risk Management", [r"risk management", r"\brisk register\b"]),
    ("Budget Management", [r"budget management", r"budget(ing)?\b"]),
    ("RAID", [r"\braid\b"]),
    ("RACI", [r"\braci\b"]),
    ("Salesforce", [r"salesforce"]),
    ("SAP", [r"\bsap\b"]),
    ("Power BI", [r"power\s*bi"]),
    ("Tableau", [r"tableau"]),
    ("Excel", [r"\bexcel\b"]),
    ("PowerPoint", [r"powerpoint"]),
    ("Visio", [r"\bvisio\b"]),
    ("SQL", [r"\bsql\b"]),
    ("Business Case", [r"business case"]),
    ("Benefits Realisation", [r"benefits realisation", r"benefits realization"]),
    ("Portfolio Management", [r"portfolio management"]),
    ("Programme Management", [r"programme management", r"program management"]),
    ("Project Management", [r"project management"]),
    ("Delivery Management", [r"delivery management"]),
    ("Scrum Master", [r"scrum master"]),
    ("Product Owner", [r"product owner"]),
    ("Business Analysis", [r"business analysis", r"business analyst"]),
    ("Requirements Gathering", [r"requirements gathering", r"requirements elicitation"]),
    ("User Stories", [r"user stor(y|ies)"]),
    ("UAT", [r"\buat\b", r"user acceptance testing"]),
    ("BPMN", [r"\bbpmn\b"]),
    ("Process Mapping", [r"process mapping"]),
    ("Gap Analysis", [r"gap analysis"]),
    ("KPI", [r"\bkpis?\b", r"key performance indicator"]),
    ("OKR", [r"\bokrs?\b", r"objectives and key results"]),
    ("Continuous Improvement", [r"continuous improvement"]),
    ("Vendor Management", [r"vendor management"]),
    ("Procurement", [r"procurement"]),
    ("Contract Management", [r"contract management"]),
    ("Agile Coaching", [r"agile coach"]),
    ("DevOps", [r"devops"]),
    ("Sprint Planning", [r"sprint planning"]),
    ("Retrospectives", [r"retrospective"]),
    ("Backlog Management", [r"backlog management", r"backlog grooming", r"backlog refinement"]),
    ("Governance", [r"\bgovernance\b"]),
    ("Compliance", [r"\bcompliance\b"]),
    ("GDPR", [r"\bgdpr\b"]),
    ("Cloud Migration", [r"cloud migration"]),
    ("ERP", [r"\berp\b"]),
    ("CRM", [r"\bcrm\b"]),
    ("Digital Transformation", [r"digital transformation"]),
    ("Data Analysis", [r"data analysis"]),
    ("Financial Management", [r"financial management"]),
    ("Resource Planning", [r"resource planning"]),
]

_COMPILED_SKILLS = [
    (label, [re.compile(p, re.IGNORECASE) for p in patterns])
    for label, patterns in SKILLS
]


def find_skills(text: str) -> set:
    """Return the set of canonical skill labels found in `text`."""
    if not text:
        return set()
    found = set()
    for label, patterns in _COMPILED_SKILLS:
        if any(p.search(text) for p in patterns):
            found.add(label)
    return found


# The 6 target roles Flux v1 filters and detects against.
ROLES = {
    "project": {
        "label": "Project Manager",
        "patterns": [r"project manager\b(?!.*programme)"],
    },
    "programme": {
        "label": "Programme Manager",
        "patterns": [r"programme manager", r"program manager"],
    },
    "delivery": {
        "label": "Delivery Manager",
        "patterns": [r"\bdelivery manager\b"],
    },
    "agile_delivery": {
        "label": "Agile Delivery Manager",
        "patterns": [r"agile delivery manager"],
    },
    "scrum_master": {
        "label": "Scrum Master",
        "patterns": [r"scrum master"],
    },
    "business_analyst": {
        "label": "Business Analyst",
        "patterns": [r"business analyst"],
    },
}

_COMPILED_ROLES = {
    key: [re.compile(p, re.IGNORECASE) for p in cfg["patterns"]]
    for key, cfg in ROLES.items()
}


def detect_roles(text: str) -> list:
    """Return role keys detected in `text`, ordered by how strongly they occur."""
    if not text:
        return []
    counts = {}
    for key, patterns in _COMPILED_ROLES.items():
        n = sum(len(p.findall(text)) for p in patterns)
        if n:
            counts[key] = n
    return [k for k, _ in sorted(counts.items(), key=lambda kv: -kv[1])]


# 9 title patterns used by the scoring engine's Title component (max 20 pts),
# checked in order, first match wins.
TITLE_PATTERNS = [
    (re.compile(r"\bdelivery manager\b", re.IGNORECASE), 20),
    (re.compile(r"\bprogramme manager\b|\bprogram manager\b", re.IGNORECASE), 19),
    (re.compile(r"\bproject manager\b", re.IGNORECASE), 18),
    (re.compile(r"\bagile delivery manager\b", re.IGNORECASE), 17),
    (re.compile(r"\bscrum master\b", re.IGNORECASE), 16),
    (re.compile(r"\bagile coach\b", re.IGNORECASE), 15),
    (re.compile(r"\bbusiness analyst\b", re.IGNORECASE), 14),
    (re.compile(r"\bchange manager\b", re.IGNORECASE), 12),
    (re.compile(r"\brelease manager\b", re.IGNORECASE), 10),
]

# Locations that score full marks under F3.
UK_LOCATION_PATTERN = re.compile(
    r"\bunited kingdom\b|\buk\b|\bengland\b|\bscotland\b|\bwales\b|\bnorthern ireland\b|\blondon\b",
    re.IGNORECASE,
)
REMOTE_LOCATION_PATTERN = re.compile(
    r"\bremote\b|\bwork from home\b|\bwfh\b|\bworldwide\b|\banywhere\b|\bglobal\b|\binternational\b|\bdistributed\b",
    re.IGNORECASE,
)
EUROPE_LOCATION_PATTERN = re.compile(r"\beurope\b|\beu\b", re.IGNORECASE)
UAE_LOCATION_PATTERN = re.compile(r"\buae\b|\bdubai\b|\babu dhabi\b", re.IGNORECASE)

QUALIFYING_LOCATION_PATTERNS = [
    UK_LOCATION_PATTERN,
    REMOTE_LOCATION_PATTERN,
    EUROPE_LOCATION_PATTERN,
    UAE_LOCATION_PATTERN,
]


def classify_location(location: str, description: str = "") -> str | None:
    """F4 Location filter bucket: 'uk', 'remote', or None (still visible under 'All')."""
    haystack_loc = location or ""
    if UK_LOCATION_PATTERN.search(haystack_loc):
        return "uk"
    haystack_all = f"{location or ''} {description or ''}"
    if (REMOTE_LOCATION_PATTERN.search(haystack_all)
            or EUROPE_LOCATION_PATTERN.search(haystack_all)
            or UAE_LOCATION_PATTERN.search(haystack_all)):
        return "remote"
    return None


_CONTRACT_PATTERN = re.compile(r"\bcontract\b", re.IGNORECASE)
_FULLTIME_PATTERN = re.compile(r"full[\s-]?time|permanent", re.IGNORECASE)
_REMOTE_TYPE_PATTERN = re.compile(r"\bremote\b", re.IGNORECASE)


def classify_employment_type(employment_type: str) -> str | None:
    """F4 Employment Type filter bucket: 'contract', 'full-time', 'remote', or None."""
    text = employment_type or ""
    if _CONTRACT_PATTERN.search(text):
        return "contract"
    if _FULLTIME_PATTERN.search(text):
        return "full-time"
    if _REMOTE_TYPE_PATTERN.search(text):
        return "remote"
    return None

SENIORITY_LEVELS = {
    "junior": 1,
    "associate": 1,
    "mid": 2,
    "intermediate": 2,
    "senior": 3,
    "lead": 4,
    "principal": 4,
    "head of": 5,
    "director": 5,
}
_SENIORITY_PATTERNS = [(re.compile(rf"\b{k}\b", re.IGNORECASE), v) for k, v in SENIORITY_LEVELS.items()]


def detect_seniority_level(text: str) -> int:
    """Best-guess seniority level (1-5) mentioned in title/description; 2 (mid) if none found."""
    if not text:
        return 2
    levels = [v for p, v in _SENIORITY_PATTERNS if p.search(text)]
    return max(levels) if levels else 2


_YEARS_PATTERN = re.compile(r"(\d{1,2})\+?\s*(?:years|yrs)", re.IGNORECASE)


def estimate_years_experience(cv_text: str) -> int:
    """Rough estimate of years of experience mentioned anywhere in the CV."""
    if not cv_text:
        return 0
    matches = [int(m.group(1)) for m in _YEARS_PATTERN.finditer(cv_text)]
    return max(matches) if matches else 0


def years_to_level(years: int) -> int:
    if years >= 12:
        return 5
    if years >= 8:
        return 4
    if years >= 5:
        return 3
    if years >= 2:
        return 2
    return 1
