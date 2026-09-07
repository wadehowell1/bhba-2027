# P03 — TAILORING PLAN (replaces viral Prompt 2)
Version 1.0 | Runs on: postings scoring >= draft threshold
Input: JD + achievements.yaml + P02 output

## Why this replaces "rewrite my experience to include those keywords"
That instruction tells the model to manufacture evidence for keywords the
candidate does not have. That is how invented metrics reach a signed CV. Here
you SELECT and SEQUENCE existing evidence. You may re-word. You may not
originate a number, date, employer, title, scope or outcome.
`src/render_cv.py::verify_plan()` enforces this in code and will reject your
output if you break it.

## Your task
Produce a `TailoringPlan` JSON that maximises the JD's stated priorities using
ONLY records from achievements.yaml.

### Confidence rules
Records carry a `confidence` field. `CHECK` means the master CVs disagree on the
figure; `medium` means only one CV carries it. Prefer a `high`-confidence record
whenever one supports the same JD requirement — a `CHECK` record forces the
application to DRAFT and costs the auto-send.

### Selection rules
1. **Relevance ordering.** Within each role, order achievement_ids so the
   JD's top-stated priority appears first.
2. **Budget — hard cap, enforced in code.** `src/ats_check.py` FAILS any CV
   estimated over 2 pages, and a FAIL blocks submission entirely. Each
   employment record carries a `tier`; budget by it:

   | tier | roles | bullets each | notes |
   |---|---|---|---|
   | `recent` | EMP-01, EMP-02 | 4–5 | the two roles that carry the application |
   | `mid` | EMP-03 to EMP-06 | 2–3 | pick only JD-relevant records |
   | `early` | EMP-07 to EMP-14 | 0–1 | group; most JDs need none of these |

   **Total must not exceed 22 bullets.** Early-career roles may be omitted from
   `roles` entirely when the JD does not reach back that far — with 14 roles on
   the spine, listing all of them is what pushes the CV to three pages.
3. **No unexplained gaps.** Roles may be omitted only from the contiguous
   early-career block, and only when the remaining spine still reads as
   continuous employment from the earliest role shown to the present. Never
   drop a `recent` or `mid` role, and never leave a hole in the middle.
4. **Metric density.** At least half the bullets in the top two roles must carry
   a metric drawn from the record's `metric` field.

### Rewording rules (`rephrasings`)
- Permitted: leading with the JD's own vocabulary, tightening, converting to the
  X-Y-Z shape using the record's `xyz` fields, British/US spelling alignment.
- Forbidden: any digit not already in the source `statement`; upgrading scope
  ("regional" → "global"); upgrading seniority; merging two records into one
  claim; attributing a record to a different employer.
- If a JD keyword has no supporting record, put it in `gaps`. Never write around it.

### Summary rules
3–4 sentences. The only numbers permitted are ones that appear in a bank record
(plus "20+ years"). Lead with the candidate's strongest JD-relevant proof, not
with adjectives. No "results-driven", "proven track record", "passionate".

## Output — JSON only
```json
{
  "job_title": "", "company": "", "source_job_id": "",
  "headline": "<= 90 chars, role-aligned, no puffery",
  "summary": "3-4 sentences",
  "competencies": ["8-12 items, drawn from skills inventory + JD vocabulary the bank supports"],
  "roles": [
    {"employment_id": "EMP-###",
     "achievement_ids": ["ACH-###"],
     "rephrasings": {"ACH-###": "reworded text"}}
  ],
  "gaps": ["JD requirement with no bank evidence — reported, not written around"],
  "self_check": {
    "every_bullet_has_bank_record": true,
    "no_new_numbers_introduced": true,
    "all_roles_present": true
  }
}
```
