# P04 — APPLICATION EMAIL
Version 1.0 | Runs on: AUTO_SEND and DRAFT routes
Input: JD + TailoringPlan + profile.yaml

Write the email that carries the application. It is read by a human in under
20 seconds, on a phone, alongside 200 others.

## Structure (strict)
- **Subject**: `Application — {job_title} ({job_ref}) — {candidate_name}`
- **Para 1 (1 sentence)**: the role applied for and where it was seen.
- **Para 2 (2–3 sentences)**: the single strongest evidenced match to the JD's
  central requirement. Cite one metric from the bank. One only.
- **Para 3 (1–2 sentences)**: the second strongest match, or the specific reason
  this employer rather than a generic one.
- **Para 4 (1 sentence)**: availability and a plain call to action.
- Signature block from `profile.sending.signature`.

## Rules
- 150 words maximum in the body. Recruiters do not read past that.
- Every factual claim traces to achievements.yaml. Same fabrication rules as P03.
- No "I am writing to apply", "I would be a great fit", "passionate about",
  "hit the ground running", "wear many hats", "dynamic self-starter".
- No em dashes as punctuation. No triplet padding. Plain declarative sentences.
- Never state a salary figure. If asked, use
  `profile.compensation.standard_answer_when_asked`.
- Never disclose current salary. Never name the current employer's clients.
- British spelling (the candidate is Jamaican; Commonwealth convention).
- Address a named person only if the posting names them. Otherwise
  "Dear Hiring Manager" — never invent a name.

## Output
```json
{"to": "", "subject": "", "body": "", "attachments": ["cv.pdf", "cv.docx"],
 "claims_used": ["ACH-###"]}
```
