"""Immutable-append audit ledger. Every decision the agent makes is recorded."""
from __future__ import annotations
import csv, json, hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "applications.csv"
SEEN = ROOT / "data" / "seen.json"

FIELDS = ["run_id", "decided_at", "job_key", "source", "company", "job_title",
          "country", "url", "apply_email", "score_total", "score_breakdown",
          "route", "route_reasons", "questions_raised", "cv_path", "pdf_path",
          "ats_result", "fabrication_flags", "low_confidence_claims",
          "sent_at", "gmail_message_id",
          "outcome", "outcome_at", "notes"]


def job_key(company: str, title: str, external_id: str = "") -> str:
    raw = f"{company.strip().lower()}|{title.strip().lower()}|{external_id.strip()}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _ensure() -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    if not LEDGER.exists():
        with LEDGER.open("w", newline="") as f:
            csv.DictWriter(f, FIELDS).writeheader()


def append(row: dict) -> None:
    _ensure()
    row.setdefault("decided_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with LEDGER.open("a", newline="") as f:
        csv.DictWriter(f, FIELDS, extrasaction="ignore").writerow(row)


def read_all() -> list[dict]:
    _ensure()
    with LEDGER.open() as f:
        return list(csv.DictReader(f))


def applied_companies(within_days: int) -> dict[str, str]:
    """company(lower) -> most recent decided_at, for cool-off enforcement."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)
    out: dict[str, str] = {}
    for r in read_all():
        if r.get("route") not in ("AUTO_SEND", "DRAFT"):
            continue
        try:
            when = datetime.fromisoformat(r["decided_at"])
        except (ValueError, KeyError):
            continue
        if when >= cutoff:
            c = r["company"].strip().lower()
            if c not in out or r["decided_at"] > out[c]:
                out[c] = r["decided_at"]
    return out


def seen_keys() -> set[str]:
    if SEEN.exists():
        return set(json.loads(SEEN.read_text()))
    return set()


def mark_seen(keys: set[str]) -> None:
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(sorted(seen_keys() | keys), indent=0))
