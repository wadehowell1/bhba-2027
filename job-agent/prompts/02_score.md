# P02 — WEIGHTED MATCH SCORE (replaces viral Prompt 1)
Version 1.0 | Runs on: postings that returned ADVANCE from P01
Input: full JD + `deterministic_score()` output + achievements.yaml

## Why this replaces "give me a match score out of 100"
An unrubriced score is an anchor, not a measurement — models cluster at 70–85
regardless of fit, so the number cannot gate a decision. Here, 55 of the 100
points are computed in code (`src/score.py`) and are reproducible. You supply
only the 45 points that require judgement, and every point must cite evidence.

## Your task
`hard_requirements` (30) and `skills_overlap` (25) are ALREADY SCORED and given
to you. Do not recompute or override them. Score only:

| Dimension | Max | Basis |
|---|---|---|
| domain_fit | 15 | Sector and regulatory-environment adjacency to the candidate's actual history |
| seniority_fit | 15 | Team size, budget, reporting line and scope vs. the candidate's evidenced scope |
| evidence_strength | 10 | For the specific capabilities THIS JD demands, how much of the candidate's supporting evidence carries a verified metric |
| logistics | 5 | Location/authorisation/working-language practicality |

### Calibration — apply these anchors literally

**domain_fit**
- 15 = Same sector and same regulatory posture (e.g. GBS centre inside a bank)
- 11 = Adjacent regulated sector (insurance, fintech, professional services)
- 7  = Unregulated commercial sector, transferable process work
- 3  = Sector the candidate has never worked in and the JD treats as essential
- 0  = Sector requires licensure the candidate lacks

**seniority_fit**
- 15 = Scope matches evidenced scope within ±25% (team, budget, geography)
- 11 = One band adjacent, clearly reachable
- 7  = Two bands adjacent, or scope stated vaguely
- 3  = Materially below evidenced scope (would read as a step down)
- 0  = Outside the Senior Manager–VP band

**evidence_strength**
- 10 = Every JD-critical capability maps to a `verified: true` record WITH a metric
- 7  = Most map to verified records; some carry no metric
- 4  = Capabilities are evidenced only as unmetriced statements
- 0  = The JD's central capability has no supporting record at all

**logistics**
- 5 = Remote, or a Tier 1 English-native country
- 3 = Tier 2 country where English is the business language
- 1 = Tier 3 country with English confirmed in the posting
- 0 = Any working-language or work-authorisation blocker

## Output — JSON only
```json
{
  "job_key": "<from ledger>",
  "domain_fit":       {"score": 0, "evidence": ["ACH-###"], "jd_line": "<quoted>"},
  "seniority_fit":    {"score": 0, "evidence": ["ACH-###"], "jd_line": "<quoted>"},
  "evidence_strength":{"score": 0, "evidence": ["ACH-###"], "jd_line": "<quoted>"},
  "logistics":        {"score": 0, "evidence": [], "jd_line": "<quoted>"},
  "judgement_subtotal": 0,
  "total": 0,
  "top_gaps": ["<JD requirement with no bank evidence>"],
  "red_flags": ["<what a recruiter spots against THIS candidate in 10 seconds>"],
  "recommendation": "AUTO|DRAFT|SKIP"
}
```

## Hard rules
- A dimension with an empty `evidence` array scores **0**. No citation, no points.
- `jd_line` must be a verbatim quote from the posting. If you cannot quote it,
  the requirement is not in the posting and must not be scored.
- `total` = deterministic_subtotal + judgement_subtotal. Show your arithmetic.
- `top_gaps` is the second deliverable of this agent. Be specific and honest —
  it drives the quarterly capability plan, not just this application.
