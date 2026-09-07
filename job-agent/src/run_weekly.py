"""Weekly orchestrator — two stages, explicit hand-off points.

    STAGE 1  discover -> dedupe -> prefilter -> triage-ready
    STAGE 2  score -> tailor -> render -> ATS validate -> gate -> route

Claude supplies the reasoning at two hand-offs (triage/score, tailoring plan);
everything else is deterministic here so it is reproducible and auditable.

Usage
  python3 -m src.run_weekly stage1 --inbox out/inbox.json
  python3 -m src.run_weekly stage2 --scored out/scored.json
  python3 -m src.run_weekly report
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

from .prefilter import Posting, prefilter, to_dict
from .ingest import parse_alert
from .score import deterministic_score
from .render_cv import TailoringPlan, render, FabricationError
from .render_pdf import render_pdf
from .ats_check import validate
from .gate import decide, AUTO_SEND, DRAFT, REJECT
from .ledger import append, job_key, seen_keys, mark_seen, read_all
from .bank import open_questions

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M")


# ---------------------------------------------------------------- STAGE 1 ---
def stage1(inbox_path: Path) -> dict:
    """Input: [{sender, subject, snippet, thread_id}] harvested from Gmail.
    Output: postings worth spending reasoning tokens on."""
    raw = json.loads(inbox_path.read_text())
    rid = run_id()
    parsed, dropped, dupes = [], [], 0
    known = seen_keys()
    new_keys: set[str] = set()

    for item in raw:
        p = parse_alert(item.get("sender", ""), item.get("subject", ""),
                        item.get("snippet", ""), item.get("thread_id", ""))
        if p is None:
            dropped.append({"subject": item.get("subject", "")[:90], "reason": "unparseable_alert"})
            continue
        k = job_key(p.company, p.title, p.external_id)
        if k in known or k in new_keys:
            dupes += 1
            continue
        new_keys.add(k)
        r = prefilter(p)
        rec = to_dict(p, r)
        rec["job_key"] = k
        (parsed if r.passed else dropped).append(rec)

    mark_seen(new_keys)
    result = {
        "run_id": rid, "ingested": len(raw), "duplicates": dupes,
        "prefilter_passed": len(parsed), "prefilter_dropped": len(dropped),
        "token_reduction": f"{100 * (1 - len(parsed) / max(len(raw), 1)):.0f}%",
        "candidates": parsed,
        "drop_reasons": _tally(dropped),
    }
    path = OUT / "logs" / f"stage1_{rid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    result["_path"] = str(path)
    return result


def _tally(dropped: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in dropped:
        for r in str(d.get("prefilter_reasons", d.get("reason", ""))).split(";"):
            if r and not r.startswith("themes:"):
                counts[r] = counts.get(r, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


# ---------------------------------------------------------------- STAGE 2 ---
def stage2(scored_path: Path) -> dict:
    """Input: [{posting:{...}, score_total, score_breakdown, plan:{...}}]
    Renders, validates, gates and writes the ledger."""
    items = json.loads(scored_path.read_text())
    rid = run_id()
    decisions = []

    for it in items:
        post = it["posting"]
        company, title = post["company"], post["title"]
        key = post.get("job_key") or job_key(company, title, post.get("external_id", ""))
        jd = post.get("description", "")

        cv_path = pdf_path = ""
        flags: list[str] = []
        ats_ok = False
        ats_detail = "not_run"

        try:
            plan = TailoringPlan.from_json(it["plan"])
            safe = _slug(f"{company}_{title}")
            d, fl = render(plan, OUT / "cv" / f"{rid}_{safe}.docx")
            cv_path, flags = str(d), fl
            p, _ = render_pdf(plan, OUT / "cv" / f"{rid}_{safe}.pdf")
            pdf_path = str(p)
            rep = validate(d)
            ats_ok = rep.passed
            ats_detail = "PASS" if rep.passed else "FAIL:" + ";".join(rep.errors)
        except FabricationError as e:
            flags = str(e).split("; ")
            ats_detail = "not_run_fabrication_blocked"
        except (KeyError, ValueError) as e:
            flags = [f"plan_error:{type(e).__name__}:{e}"]
            ats_detail = "not_run_plan_error"

        g = decide(posting_text=jd, company=company,
                   score_total=float(it.get("score_total", 0)),
                   ats_passed=ats_ok, fabrication_flags=flags,
                   apply_email=post.get("apply_email"))

        row = {
            "run_id": rid, "job_key": key, "source": post.get("source", ""),
            "company": company, "job_title": title, "country": post.get("country", ""),
            "url": post.get("url", ""), "apply_email": g.apply_email or "",
            "score_total": it.get("score_total", 0),
            "score_breakdown": json.dumps(it.get("score_breakdown", {}))[:900],
            "route": g.route, "route_reasons": ";".join(g.reasons),
            "questions_raised": " | ".join(g.questions),
            "cv_path": cv_path, "pdf_path": pdf_path,
            "ats_result": ats_detail[:300], "fabrication_flags": ";".join(flags),
            "sent_at": "", "gmail_message_id": "", "outcome": "pending",
            "outcome_at": "", "notes": "",
        }
        append(row)
        decisions.append(row)

    summary = {
        "run_id": rid, "processed": len(decisions),
        "auto_send": [d for d in decisions if d["route"] == AUTO_SEND],
        "draft": [d for d in decisions if d["route"] == DRAFT],
        "rejected": [d for d in decisions if d["route"] == REJECT],
        "open_profile_questions": open_questions(),
    }
    summary["auto_send_ratio"] = (
        f"{100 * len(summary['auto_send']) / max(len(summary['auto_send']) + len(summary['draft']), 1):.0f}%")
    path = OUT / "logs" / f"stage2_{rid}.json"
    path.write_text(json.dumps(summary, indent=2))
    summary["_path"] = str(path)
    return summary


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s)[:70].strip("_")


# ----------------------------------------------------------------- REPORT ---
def report() -> dict:
    rows = read_all()
    by_route: dict[str, int] = {}
    by_outcome: dict[str, int] = {}
    for r in rows:
        by_route[r["route"]] = by_route.get(r["route"], 0) + 1
        by_outcome[r.get("outcome", "")] = by_outcome.get(r.get("outcome", ""), 0) + 1
    sent = [r for r in rows if r["route"] == AUTO_SEND]
    replies = [r for r in rows if r.get("outcome") in ("reply", "interview", "offer")]
    return {
        "total_decisions": len(rows), "by_route": by_route, "by_outcome": by_outcome,
        "response_rate": f"{100 * len(replies) / max(len(sent), 1):.1f}%",
        "open_profile_questions": open_questions(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(prog="run_weekly")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("stage1"); s1.add_argument("--inbox", required=True)
    s2 = sub.add_parser("stage2"); s2.add_argument("--scored", required=True)
    sub.add_parser("report")
    a = ap.parse_args()

    if a.cmd == "stage1":
        out = stage1(Path(a.inbox))
        print(json.dumps({k: v for k, v in out.items() if k != "candidates"}, indent=2))
    elif a.cmd == "stage2":
        out = stage2(Path(a.scored))
        print(json.dumps({k: (len(v) if isinstance(v, list) else v)
                          for k, v in out.items()}, indent=2))
    else:
        print(json.dumps(report(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
