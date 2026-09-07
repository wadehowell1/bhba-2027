"""Stage 1b — weighted, evidence-cited scoring.

Two components:
  * DETERMINISTIC (this module): hard-requirement gate + keyword coverage
    computed against achievements.yaml. Reproducible, no tokens, auditable.
  * JUDGEMENT (prompts/02_score.md): domain fit, seniority fit, evidence
    strength. Supplied by the model, but it must cite achievement IDs.

Total = 100. Thresholds live in profile.yaml.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from .bank import load_bank, load_profile, tag_phrases, tokens

WEIGHTS = {
    "hard_requirements": 30,
    "skills_overlap": 25,
    "domain_fit": 15,
    "seniority_fit": 15,
    "evidence_strength": 10,
    "logistics": 5,
}

# Hard requirements the agent can test deterministically from the JD text.
HARD_REQ_PATTERNS = {
    "bachelors":  (r"bachelor'?s?\b|\bbsc\b|\bba\b degree|undergraduate degree", True),
    "masters":    (r"master'?s?\b|\bmba\b|\bmsc\b|postgraduate degree", True),
    "lean_six_sigma": (r"six sigma|black belt|green belt|\blean\b certif", True),
    "pmp":        (r"\bpmp\b|prince2|\bpgmp\b|\bmsp\b certif", False),
    "cissp":      (r"\bcissp\b|\bcism\b|\bcisa\b|\bcrisc\b", False),
    "iso27001_cert": (r"iso ?27001 (lead )?(auditor|implementer) certif", False),
    "master_black_belt": (r"master black belt|\bmbb\b", False),
    "cpa":        (r"\bcpa\b|\bacca\b|\bcfa\b|chartered accountant", False),
}

YEARS = re.compile(r"(\d{1,2})\+?\s*(?:-\s*\d{1,2}\s*)?year[s]?(?:\'|’)?\s+(?:of\s+)?(?:relevant\s+|progressive\s+|proven\s+)?experience", re.I)
CANDIDATE_YEARS = 20  # 1996 → 2026, stated on CV as "20+ years"


@dataclass
class HardReqResult:
    met: list[str] = field(default_factory=list)
    unmet: list[str] = field(default_factory=list)
    disqualified: bool = False
    score: float = 0.0


def hard_requirements(jd: str) -> HardReqResult:
    r = HardReqResult()
    jd_l = jd.lower()

    for name, (pattern, candidate_has) in HARD_REQ_PATTERNS.items():
        if re.search(pattern, jd_l):
            (r.met if candidate_has else r.unmet).append(name)

    m = YEARS.search(jd)
    if m:
        required = int(m.group(1))
        if required <= CANDIDATE_YEARS:
            r.met.append(f"years_experience:{required}")
        else:
            r.unmet.append(f"years_experience:{required}>{CANDIDATE_YEARS}")

    # Certification gaps are disqualifying only when the JD marks them mandatory.
    # Matched in BOTH word orders: "PMP is required" and "required: PMP".
    CERTS = r"pmp|prince2|cissp|cism|cisa|crisc|master black belt|\bmbb\b|cpa|acca|cfa"
    MUST = r"required|must have|must hold|mandatory|essential|non-negotiable"
    for pat, grp in ((rf"({MUST})[^.\n]{{0,120}}?({CERTS})", 2),
                     (rf"({CERTS})[^.\n]{{0,60}}?({MUST})", 1)):
        m = re.search(pat, jd_l)
        if m:
            r.disqualified = True
            r.unmet.append(f"mandatory_cert_missing:{m.group(grp)}")
            break

    total = len(r.met) + len(r.unmet)
    r.score = WEIGHTS["hard_requirements"] * (len(r.met) / total if total else 0.7)
    if r.disqualified:
        r.score = 0.0
    return r


@dataclass
class CoverageResult:
    matched: dict[str, list[str]] = field(default_factory=dict)  # jd phrase -> achievement ids
    gaps: list[str] = field(default_factory=list)
    score: float = 0.0
    ratio: float = 0.0


def skills_coverage(jd: str) -> CoverageResult:
    """Which JD-relevant capability phrases are evidenced in the bank."""
    r = CoverageResult()
    jd_l = jd.lower()
    phrases = tag_phrases()

    # Which of the candidate's evidenced capabilities does the JD actually ask for?
    for phrase, ids in phrases.items():
        if len(phrase) < 3:
            continue
        if re.search(rf"\b{re.escape(phrase)}\b", jd_l):
            r.matched[phrase] = sorted(set(ids))

    # JD capability phrases with no evidence behind them → declared gaps
    for phrase in _jd_capability_phrases(jd_l):
        if phrase not in r.matched:
            r.gaps.append(phrase)

    demanded = len(r.matched) + len(r.gaps)
    r.ratio = len(r.matched) / demanded if demanded else 0.0
    r.score = WEIGHTS["skills_overlap"] * r.ratio
    return r


CAPABILITY_LEXICON = [
    "stakeholder management", "change management", "project management",
    "programme management", "program management", "process improvement",
    "continuous improvement", "operational excellence", "lean six sigma",
    "data analytics", "power bi", "automation", "rpa", "governance",
    "budget management", "people leadership", "coaching", "training",
    "shared services", "global business services", "transformation",
    "risk management", "regulatory compliance", "vendor management",
    "financial services", "kpi", "reporting", "strategy", "digital transformation",
    "root cause analysis", "dmaic", "agile", "scrum", "sql", "python",
    "salesforce", "sap", "oracle", "workday", "tableau", "erp", "supply chain",
    "procurement", "machine learning", "artificial intelligence", "cloud",
    "azure", "aws", "cybersecurity", "iso 27001", "audit", "p&l",
]


def _jd_capability_phrases(jd_l: str) -> list[str]:
    return [p for p in CAPABILITY_LEXICON if re.search(rf"\b{re.escape(p)}\b", jd_l)]


def deterministic_score(jd: str) -> dict:
    hr = hard_requirements(jd)
    cov = skills_coverage(jd)
    return {
        "hard_requirements": {
            "score": round(hr.score, 1), "max": WEIGHTS["hard_requirements"],
            "met": hr.met, "unmet": hr.unmet, "disqualified": hr.disqualified,
        },
        "skills_overlap": {
            "score": round(cov.score, 1), "max": WEIGHTS["skills_overlap"],
            "coverage_ratio": round(cov.ratio, 2),
            "matched": cov.matched, "gaps": cov.gaps,
        },
        "deterministic_subtotal": round(hr.score + cov.score, 1),
        "judgement_dimensions_remaining": {
            k: WEIGHTS[k] for k in ("domain_fit", "seniority_fit", "evidence_strength", "logistics")
        },
        "disqualified": hr.disqualified,
    }
