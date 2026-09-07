"""Regression suite. Run: python3 -m tests.test_agent  (from job-agent/)

Requires the private evidence bank and profile (both gitignored) to be present.
A fresh clone must first copy the *.example.yaml templates and populate them.
"""
from __future__ import annotations
import json, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.prefilter import Posting, prefilter
from src.ingest import parse_alert
from src.score import deterministic_score
from src.render_cv import TailoringPlan, render, verify_plan, low_confidence_claims
from src.render_pdf import render_pdf
from src.ats_check import validate
from src.gate import decide, extract_apply_email, AUTO_SEND, DRAFT, REJECT
from src.bank import load_bank, open_questions, load_profile

FIXTURE = json.load(open(Path(__file__).parent / "fixture_plan.json"))
PASSED, FAILED = [], []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASSED if cond else FAILED).append(f"{name}{' — ' + detail if detail and not cond else ''}")


# --- bank -------------------------------------------------------------------
b = load_bank()
check("bank.records", len(b["achievements"]) == 40, str(len(b["achievements"])))
check("bank.employment", len(b["employment"]) == 14, str(len(b["employment"])))
check("bank.credentials", len(b["credentials"]) == 10, str(len(b["credentials"])))
check("bank.verification_notes_present", len(b.get("verification_notes", [])) == 4)
check("bank.every_achievement_has_id_and_statement",
      all(a.get("id") and a.get("statement") for a in b["achievements"]))
check("bank.employment_ids_resolve",
      all(a["employment_id"] in {e["id"] for e in b["employment"]}
          for a in b["achievements"] if a.get("employment_id")))

# --- prefilter --------------------------------------------------------------
cases = [
    ("remote head of ops", Posting("li","1","X","Head of Operations",location="100% Remote"), True),
    ("french required", Posting("li","2","X","Director of Continuous Improvement",
                                country="France", description="Fluency in French is required."), False),
    ("japan english ok", Posting("li","3","X","Senior Manager, Process Excellence", country="Japan",
                                 description="English is the working language of this office."), True),
    ("too junior", Posting("li","4","X","Process Improvement Analyst", country="Canada"), False),
    ("off target", Posting("li","5","X","Remote Part-Time Graphic Designer", country="Jamaica"), False),
    ("vp opex", Posting("li","6","X","VP Operational Excellence", country="Canada"), True),
    ("project director", Posting("li","7","X","Project Director", country="United Kingdom"), True),
    ("excluded keyword", Posting("li","8","X","Head of Operations", country="United States",
                                 description="US citizens only."), False),
]
for name, p, expect in cases:
    check(f"prefilter.{name}", prefilter(p).passed == expect)

# --- ingest -----------------------------------------------------------------
p = parse_alert("jobalerts-noreply@linkedin.com", "Maersk is hiring: Head of Operational Excellence",
                "Singapore based role", "t1")
check("ingest.linkedin", p is not None and p.company == "Maersk"
      and p.title == "Head of Operational Excellence" and p.country == "Singapore")
p2 = parse_alert("donotreply@jobalert.indeed.com",
                 "Operations Director at Acme Corp. 3 more Jamaica Caribbean jobs", "", "t2")
check("ingest.indeed", p2 is not None and p2.company == "Acme Corp" and p2.title == "Operations Director")
check("ingest.unknown_sender", parse_alert("x@y.com", "anything", "", "t3") is None)

# --- scorer -----------------------------------------------------------------
jd = ("Head of Operational Excellence. 15+ years experience, Master's degree. Lean Six Sigma "
      "Black Belt required. Continuous improvement, change management, stakeholder management, "
      "governance, KPI reporting, global business services. Power BI, automation, RPA. "
      "Financial services. People leadership and coaching. SAP and Workday advantageous.")
d = deterministic_score(jd)
check("score.subtotal_in_range", 45 <= d["deterministic_subtotal"] <= 55, str(d["deterministic_subtotal"]))
check("score.gaps_identified", set(d["skills_overlap"]["gaps"]) == {"sap", "workday"},
      str(d["skills_overlap"]["gaps"]))
check("score.not_disqualified", not d["disqualified"])
dq = deterministic_score("Director role. PMP certification is required and mandatory.")
check("score.mandatory_cert_disqualifies", dq["disqualified"])

# --- fabrication guards -----------------------------------------------------
good = TailoringPlan.from_json(FIXTURE)
check("guard.clean_plan_passes", verify_plan(good) == [])

bad_metric = TailoringPlan.from_json({**FIXTURE, "roles": [
    {"employment_id": "EMP-01", "achievement_ids": ["ACH-001"],
     "rephrasings": {"ACH-001": "Governed a USD 120M+ portfolio with 40% gains."}}]})
check("guard.invented_metric", any("invented_metric" in f for f in verify_plan(bad_metric)))

bad_id = TailoringPlan.from_json({**FIXTURE, "roles": [
    {"employment_id": "EMP-01", "achievement_ids": ["ACH-999"]}]})
check("guard.unknown_id", any("unknown_achievement" in f for f in verify_plan(bad_id)))

bad_sum = TailoringPlan.from_json({**FIXTURE, "summary": "Led 900 people to 99% satisfaction.",
                                   "roles": [{"employment_id": "EMP-01", "achievement_ids": ["ACH-001"]}]})
check("guard.unsourced_summary_number", any("unsourced_number" in f for f in verify_plan(bad_sum)))

bad_role = TailoringPlan.from_json({**FIXTURE, "summary": "Clean.", "roles": [
    {"employment_id": "EMP-03", "achievement_ids": ["ACH-001"]}]})
check("guard.wrong_role_attribution", any("wrong_role" in f for f in verify_plan(bad_role)))

# --- render + ATS -----------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    docx, flags = render(good, Path(td) / "cv.docx")
    check("render.docx_no_flags", flags == [])
    rep = validate(docx)
    check("ats.docx_passes", rep.passed, ";".join(rep.errors))
    check("ats.bullets_intact", rep.bullet_count_source == rep.bullet_count_extracted)
    check("ats.substantial", rep.extracted_chars > 4000, str(rep.extracted_chars))

    pdf, _ = render_pdf(good, Path(td) / "cv.pdf")
    from pdfminer.high_level import extract_text
    t = extract_text(str(pdf)); u = t.upper()
    check("pdf.contact_first", load_profile()["identity"]["email"] in t[:300])
    check("pdf.headings", all(h in u for h in
          ["PROFESSIONAL SUMMARY", "CORE COMPETENCIES", "PROFESSIONAL EXPERIENCE"]))
    check("pdf.reading_order", u.find("PROFESSIONAL SUMMARY") < u.find("PROFESSIONAL EXPERIENCE"))
    check("pdf.metrics_recovered", all(m in t for m in ["500K", "250+", "23 countries", "45%"]),
          "missing: " + ",".join(m for m in ["500K", "250+", "23 countries", "45%"] if m not in t))

# --- gate -------------------------------------------------------------------
g = decide(posting_text="Send CV to careers@maersk.com", company="ZZTestA", score_total=81,
           ats_passed=True, fabrication_flags=[])
check("gate.auto_send", g.route == AUTO_SEND and g.apply_email == "careers@maersk.com")

check("gate.portal_only_drafts",
      decide(posting_text="Apply only via our careers portal. hr@acme.com for queries.",
             company="ZZTestB", score_total=90, ats_passed=True, fabrication_flags=[]).route == DRAFT)
check("gate.salary_question_drafts",
      decide(posting_text="Email jobs@b.com. State your salary expectations.",
             company="ZZTestC", score_total=88, ats_passed=True, fabrication_flags=[]).route == DRAFT)
check("gate.fabrication_rejects",
      decide(posting_text="careers@y.com", company="ZZTestD", score_total=95, ats_passed=True,
             fabrication_flags=["invented_metric:ACH-001"]).route == REJECT)
check("gate.ats_fail_rejects",
      decide(posting_text="careers@y.com", company="ZZTestE", score_total=95, ats_passed=False,
             fabrication_flags=[]).route == REJECT)
check("gate.low_score_rejects",
      decide(posting_text="careers@y.com", company="ZZTestF", score_total=55, ats_passed=True,
             fabrication_flags=[]).route == REJECT)
check("gate.cover_letter_not_escalated",
      decide(posting_text="Email t@z.com with CV and cover letter.", company="ZZTestG",
             score_total=90, ats_passed=True, fabrication_flags=[]).route == AUTO_SEND)
check("gate.long_essay_escalates",
      decide(posting_text="Email t@z.com. Answer in 500 words why you want this.",
             company="ZZTestH", score_total=90, ats_passed=True, fabrication_flags=[]).route == DRAFT)

check("email.filters_noreply",
      extract_apply_email("Contact noreply@linkedin.com or hiring@realco.com") == "hiring@realco.com")
check("email.never_guesses", extract_apply_email("Join Acme Corp! Great team.") is None)
check("email.prefers_recruitment_mailbox",
      extract_apply_email("Reach john.smith@acme.com or careers@acme.com") == "careers@acme.com")

# --- memory -----------------------------------------------------------------
check("profile.open_questions_tracked", len(open_questions()) == 9, str(len(open_questions())))

# --- confidence gate --------------------------------------------------------
disputed = TailoringPlan.from_json({"job_title": "x", "company": "y", "headline": "h",
    "summary": "Clean.", "competencies": [],
    "roles": [{"employment_id": "EMP-01", "achievement_ids": ["ACH-001"]}]})
check("confidence.disputed_detected",
      any(f.endswith(":CHECK") for f in low_confidence_claims(disputed)))
check("confidence.disputed_blocks_autosend",
      decide(posting_text="Send CV to careers@t.com", company="ZZConf1", score_total=90,
             ats_passed=True, fabrication_flags=[],
             low_confidence=low_confidence_claims(disputed)).route == DRAFT)
clean = TailoringPlan.from_json({"job_title": "x", "company": "y", "headline": "h",
    "summary": "Clean.", "competencies": [],
    "roles": [{"employment_id": "EMP-01", "achievement_ids": ["ACH-002"]}]})
check("confidence.clean_allows_autosend",
      decide(posting_text="Send CV to careers@t.com", company="ZZConf2", score_total=90,
             ats_passed=True, fabrication_flags=[],
             low_confidence=low_confidence_claims(clean)).route == AUTO_SEND)

# --- report -----------------------------------------------------------------
print(f"\n{'='*62}\n  JOB APPLICATION AGENT — REGRESSION SUITE\n{'='*62}")
print(f"  PASSED: {len(PASSED)}    FAILED: {len(FAILED)}")
if FAILED:
    print("\n  FAILURES:")
    for f in FAILED:
        print("   ✗", f)
else:
    print("\n  All guards verified.")
print("="*62)
sys.exit(1 if FAILED else 0)
