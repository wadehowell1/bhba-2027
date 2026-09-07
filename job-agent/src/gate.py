"""Stage 2 routing gate — decides AUTO_SEND, DRAFT or REJECT.

Design intent: the target is ~90% auto-submitted. That ratio is achieved by making
the *profile* answer as many questions as possible up front, NOT by loosening
the safety conditions. Every condition below is a genuine blocker: failing one
means the agent would otherwise be guessing on the candidate's behalf.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from .bank import load_profile, open_questions
from .ledger import applied_companies

AUTO_SEND, DRAFT, REJECT = "AUTO_SEND", "DRAFT", "REJECT"

# Addresses that are never a real application inbox
BLOCKED_EMAIL_DOMAINS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com",
    "monster.com", "example.com", "sentry.io", "wixpress.com",
}
BLOCKED_LOCALPARTS = {"noreply", "no-reply", "donotreply", "do-not-reply",
                      "postmaster", "mailer-daemon", "unsubscribe", "privacy",
                      "support", "webmaster", "abuse", "security"}

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")

# Signals that the posting demands something the profile cannot answer
NEEDS_SALARY = re.compile(r"salary (expectation|requirement)|expected (salary|compensation)|"
                          r"desired (salary|compensation)|current salary", re.I)
NEEDS_NOTICE = re.compile(r"notice period|when (can|could) you start|availability to start|"
                          r"earliest start", re.I)
NEEDS_TRAVEL = re.compile(r"willing(ness)? to travel|travel requirement|%\s*travel", re.I)
# A standard cover letter is NOT an escalation — the agent writes it from the
# evidence bank and the fabrication guard validates it. Only genuinely bespoke
# long-form work is escalated, per profile.per_role_always_ask.
NEEDS_ESSAY = re.compile(r"\b(2[5-9]\d|[3-9]\d{2}|\d{4})\s*(?:-|to)?\s*\d*\s*words?\b|"
                         r"answer the following question|written (exercise|submission)|"
                         r"essay|respond to the following prompt", re.I)
NEEDS_ASSESSMENT = re.compile(r"assessment|psychometric|coding (test|challenge)|"
                              r"timed (test|exercise)|video interview|hirevue|"
                              r"case study submission", re.I)
PORTAL_ONLY = re.compile(r"apply (only )?(via|through|on) (our|the) (website|portal|careers)|"
                         r"applications? (are )?only accepted (via|through)|"
                         r"no email applications", re.I)

FIELD_TRIGGERS = [
    (NEEDS_SALARY,  ["compensation.expected_base_min", "compensation.expected_base_target"]),
    (NEEDS_NOTICE,  ["compensation.notice_period", "compensation.earliest_start_date"]),
    (NEEDS_TRAVEL,  ["standing_answers.willing_to_travel"]),
]


@dataclass
class GateDecision:
    route: str
    reasons: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    apply_email: str | None = None


def extract_apply_email(posting_text: str, company: str = "") -> str | None:
    """Return an application address ONLY if the employer published one.

    Never guesses, never pattern-builds (first.last@company.com), never uses a
    third-party or scraped address. This is a deliverability decision and a
    lawful-basis decision under DPA 2020 / GDPR Art.6(1)(b).
    """
    best: str | None = None
    for m in EMAIL_RE.finditer(posting_text or ""):
        addr = m.group(0).lower().strip(".")
        local, _, domain = addr.partition("@")
        if domain in BLOCKED_EMAIL_DOMAINS or any(domain.endswith("." + d) for d in BLOCKED_EMAIL_DOMAINS):
            continue
        if local in BLOCKED_LOCALPARTS or any(local.startswith(b) for b in BLOCKED_LOCALPARTS):
            continue
        # Prefer a recruitment-shaped mailbox, else the first credible address.
        if re.match(r"(careers?|jobs?|recruit|hiring|hr|talent|apply|applications?|cv|resume)", local):
            return addr
        best = best or addr
    return best


def decide(*, posting_text: str, company: str, score_total: float,
           ats_passed: bool, fabrication_flags: list[str],
           apply_email: str | None = None,
           low_confidence: list[str] | None = None) -> GateDecision:
    prof = load_profile()
    pol = prof["submission_policy"]
    d = GateDecision(route=DRAFT)

    # --- Absolute blockers -------------------------------------------------
    if fabrication_flags:
        d.route = REJECT
        d.reasons.append("fabrication_flags:" + ";".join(fabrication_flags))
        return d
    if not ats_passed:
        d.route = REJECT
        d.reasons.append("ats_validation_failed")
        return d
    if score_total < pol["draft_score_threshold"]:
        d.route = REJECT
        d.reasons.append(f"score_below_draft_threshold:{score_total}")
        return d

    # --- Cool-off ----------------------------------------------------------
    recent = applied_companies(pol["cooloff_days"])
    if company.strip().lower() in recent:
        d.route = REJECT
        d.reasons.append(f"cooloff_active_since:{recent[company.strip().lower()]}")
        return d

    # --- Unanswered profile fields this posting actually needs -------------
    unanswered = set(open_questions())
    for pattern, fields in FIELD_TRIGGERS:
        if pattern.search(posting_text):
            for f in fields:
                if f in unanswered:
                    d.questions.append(f"Posting requires an answer for `{f}`")

    # --- Unconfirmed claims ------------------------------------------------
    # A disputed figure (CHECK) blocks auto-send outright. A single-sourced one
    # (medium) is surfaced but does not block, since it is still on a master CV.
    for item in (low_confidence or []):
        if item.endswith(":CHECK"):
            d.questions.append(
                f"CV uses {item.split(':')[0]}, whose figure differs between your master CVs "
                f"— confirm before this is sent")

    # --- Per-role escalations ---------------------------------------------
    if NEEDS_ESSAY.search(posting_text):
        d.questions.append("Posting requires a bespoke long-form written response")
    if NEEDS_ASSESSMENT.search(posting_text):
        d.questions.append("Posting includes an assessment, test or video interview step")

    # --- Channel -----------------------------------------------------------
    d.apply_email = apply_email or extract_apply_email(posting_text, company)
    if PORTAL_ONLY.search(posting_text):
        d.reasons.append("portal_only_declared")
        d.apply_email = None
    if not d.apply_email:
        d.reasons.append("no_published_application_email")

    # --- Route -------------------------------------------------------------
    if (d.apply_email and not d.questions
            and score_total >= pol["auto_send_score_threshold"]):
        d.route = AUTO_SEND
        d.reasons.append(f"auto_send_score:{score_total}")
    else:
        d.route = DRAFT
        if score_total < pol["auto_send_score_threshold"]:
            d.reasons.append(f"score_below_auto_threshold:{score_total}")
        if d.questions:
            d.reasons.append(f"open_questions:{len(d.questions)}")
    return d
