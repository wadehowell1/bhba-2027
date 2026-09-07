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

### Selection rules
1. **Relevance ordering.** Within each role, order achievement_ids so the
   JD's top-stated priority appears first.
2. **Budget.** 5–6 bullets for the two most recent roles, 2–3 for mid-career,
   1 for early career. A senior CV runs 2 pages; do not exceed ~25 bullets.
3. **Every role appears.** Employment gaps read as red flags. Never drop a role
   from the spine to save space — reduce its bullet count instead.
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
