"""Stage 1a — deterministic pre-filter. Zero LLM tokens spent here.

Cuts the weekly intake (~200 postings) down to the ~15% worth reasoning about.
Every rejection carries a machine-readable reason for the audit ledger.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field, asdict
from .bank import load_profile, tokens

LANG_REQ = re.compile(
    r"\b(fluen\w*|nativ\w*|proficien\w*|bilingual|command of|working knowledge|"
    r"must speak|speak(?:s|ing)?)\b[^.\n]{0,80}?\b("
    r"french|spanish|german|arabic|mandarin|cantonese|chinese|japanese|korean|"
    r"portuguese|italian|dutch|russian|polish|hebrew|hindi|urdu|turkish|thai|"
    r"vietnamese|indonesian|malay|swedish|danish|norwegian|finnish|czech|"
    r"romanian|hungarian|greek)\b", re.I)

ENGLISH_OK = re.compile(r"\benglish\b[^.\n]{0,60}\b(working language|is the|only|required|fluency)\b", re.I)

SENIORITY_RANK = {
    "officer": 1, "analyst": 1, "specialist": 2, "manager": 3,
    "senior manager": 4, "head of": 5, "principal": 5, "lead": 4,
    "associate director": 5, "director": 6, "avp": 5,
    "assistant vice president": 5, "vice president": 7, "vp": 7,
    "general manager": 6, "gm": 6, "chief of staff": 5, "senior director": 6,
    "executive director": 7, "partner": 8, "chief": 8, "c-level": 8,
}
FLOOR_RANK, CEILING_RANK = 4, 7


# Title themes — regex, not literal phrases, so "Project Director" and
# "Head of Business Process Re-engineering" both land correctly.
TITLE_THEMES = {
    "improvement":    r"continuous improvement|operational excellence|process excellence|"
                      r"business improvement|performance improvement|business process|"
                      r"\blean\b|six sigma|kaizen|process re-?engineering|quality",
    "transformation": r"transformation|change manage|transition|\bchange\b",
    "programme":      r"programme|program manage|project (director|manager|lead)|\bpmo\b|"
                      r"portfolio|delivery (lead|manager|director|head)|project delivery",
    "operations":     r"\boperations?\b|service delivery|shared services|"
                      r"global business services|\bgbs\b|business services|centre of excellence|"
                      r"center of excellence|\bcoe\b",
    "innovation":     r"innovation|digital transformation|automation|intelligent automation",
    "executive":      r"chief of staff|general manager|managing director|country manager",
    "strategy":       r"strategy|strategic (initiative|programme|program|planning)|business planning",
}


def _title_themes(title: str) -> list[str]:
    t = title.lower()
    return [name for name, pat in TITLE_THEMES.items() if re.search(pat, t)]


@dataclass
class Posting:
    source: str
    external_id: str
    company: str
    title: str
    location: str = ""
    country: str = ""
    url: str = ""
    apply_email: str | None = None
    description: str = ""
    posted_at: str = ""
    raw_subject: str = ""


@dataclass
class PrefilterResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    seniority_rank: int = 0
    geo_tier: int = 0
    themes: list[str] = field(default_factory=list)


def _seniority_rank(title: str) -> int:
    t = title.lower()
    best = 0
    for token, rank in SENIORITY_RANK.items():
        if re.search(rf"\b{re.escape(token)}\b", t):
            best = max(best, rank)
    return best


def _geo_tier(posting: Posting, prof: dict) -> int:
    g = prof["geography"]
    hay = f"{posting.country} {posting.location}".lower()
    if re.search(r"\b(remote|anywhere|worldwide|global)\b", hay):
        return 1
    for tier, key in ((1, "tier_1_english_native"),
                      (2, "tier_2_english_business_language"),
                      (3, "tier_3_conditional")):
        for c in g[key]:
            if c.lower() in hay:
                return tier
    return 0


def prefilter(posting: Posting) -> PrefilterResult:
    prof = load_profile()
    tgt = prof["targeting"]
    res = PrefilterResult(passed=True)
    title_l = posting.title.lower()
    blob = f"{posting.title}\n{posting.description}"
    blob_l = blob.lower()

    # 1. Hard title exclusions
    for bad in tgt["hard_exclusions"]["titles"]:
        if re.search(rf"\b{re.escape(bad)}\b", title_l):
            res.passed = False
            res.reasons.append(f"excluded_title:{bad}")

    # 2. Hard keyword exclusions
    for bad in tgt["hard_exclusions"]["keywords"]:
        if bad.lower() in blob_l:
            res.passed = False
            res.reasons.append(f"excluded_keyword:{bad}")

    # 3. Seniority band
    rank = _seniority_rank(posting.title)
    res.seniority_rank = rank
    if rank == 0:
        res.reasons.append("seniority_indeterminate")
    elif rank < FLOOR_RANK:
        res.passed = False
        res.reasons.append(f"below_seniority_floor:{rank}")
    elif rank > CEILING_RANK:
        res.passed = False
        res.reasons.append(f"above_seniority_ceiling:{rank}")

    # 4. Domain relevance — title must touch at least one target theme
    hits = _title_themes(posting.title)
    res.themes = hits
    if not hits:
        res.passed = False
        res.reasons.append("no_target_title_theme")
    else:
        res.reasons.append("themes:" + "+".join(hits))

    # 5. Language gate (working-language constraint)
    if LANG_REQ.search(blob) and not ENGLISH_OK.search(blob):
        res.passed = False
        res.reasons.append("non_english_language_requirement")

    # 6. Geography / English-capability tier
    tier = _geo_tier(posting, prof)
    res.geo_tier = tier
    if tier == 0 and posting.country:
        res.passed = False
        res.reasons.append("country_outside_english_tiers")
    if tier == 3 and not ENGLISH_OK.search(blob):
        res.passed = False
        res.reasons.append("tier3_country_without_english_confirmation")

    if res.passed and not res.reasons:
        res.reasons.append("clean_pass")
    return res


def to_dict(p: Posting, r: PrefilterResult) -> dict:
    d = asdict(p)
    d.update(prefilter_passed=r.passed, prefilter_reasons=";".join(r.reasons),
             seniority_rank=r.seniority_rank, geo_tier=r.geo_tier,
             themes="+".join(r.themes))
    return d
