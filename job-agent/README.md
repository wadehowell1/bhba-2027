# Job Application Agent

Weekly agent that discovers roles the configured candidate qualifies for, scores them against
a reproducible rubric, generates a CV tailored from a verified evidence bank,
validates it through real text extractors, and submits by email or drafts for review.

The full operating specification, compliance position and maintenance log are kept
outside this repository (see `private/`), because they describe an individual's
live job search. This README covers the system itself.

## Install
```bash
pip3 install -r requirements.txt
```

## Run
```bash
cd job-agent
python3 -m src.run_weekly stage1 --inbox out/inbox.json   # discover + qualify
python3 -m src.run_weekly stage2 --scored out/scored.json # tailor + gate
python3 -m src.run_weekly report                          # pipeline stats
python3 -m tests.test_agent                               # 43 regression checks
```

Stages 1 and 2 are separated by two reasoning hand-offs (triage/scoring and the
tailoring plan) that Claude performs using `prompts/`. Everything else is
deterministic Python so it is reproducible and auditable.

## Layout
| Path | Purpose |
|---|---|
| `data/achievements.yaml` | Verified evidence bank — **the source of truth for every CV claim** |
| `config/profile.yaml` | Persistent agent memory: identity, authorisation, geography, standing answers |
| `prompts/` | P01 triage · P02 scoring · P03 tailoring · P04 application email |
| `src/prefilter.py` | Deterministic filter — cuts ~85% of intake at zero token cost |
| `src/score.py` | 55 of the 100 rubric points, computed in code |
| `src/render_cv.py` | ATS-safe `.docx` + the fabrication guards |
| `src/render_pdf.py` | `.pdf` from the same plan, no system dependencies |
| `src/ats_check.py` | Round-trip parse validation (not an LLM roleplay) |
| `src/gate.py` | AUTO_SEND / DRAFT / REJECT routing |
| `src/ledger.py` | Append-only audit trail |

## Non-negotiables
- No CV claim exists that is not in `achievements.yaml`. Four guards enforce it.
- No scraping of LinkedIn, Indeed or Glassdoor. Discovery reads the candidate's own inbox.
- No guessed email addresses. Only what the employer published in the posting.
- No attestation answered that the candidate has not answered themselves.
