#!/usr/bin/env python3
"""
AI Asset & Usage Dashboard - generator
======================================
Classification : INTERNAL USE
Version        : 1.0.0
Owner          : Wade Howell (wade.howell1@gmail.com)
Control mapping: ISO/IEC 27001:2022 A.5.9 (Inventory of information and other
                 associated assets), A.8.16 (Monitoring activities);
                 NIST SP 800-53 Rev.5 CM-8 (System Component Inventory);
                 NIST CSF 2.0 ID.AM-02 (Software platforms inventoried).

Builds, from auditable source captures under ``sources/``:

  data/asset_register.csv    one row per AI asset, with lifecycle + RAG status
  data/usage_monthly.csv     long-format monthly usage facts (tidy, Power BI ready)
  data/usage_events.csv      durable append-only telemetry ledger (deduped by uuid)
  data/snapshots/<YYYY-MM>.json   immutable monthly snapshot (the audit trail)
  ai_assets_dashboard.html   standalone dashboard (no build step, no CDN)

Lifecycle classification is a genuine diff: the current inventory is compared
against the most recent prior snapshot. On the very first run there is no prior
snapshot, so assets are marked BASELINE rather than falsely reported as "new".

Stdlib only. Python 3.9+.

Usage:
    python3 generate.py                       # normal monthly run
    python3 generate.py --period 2026-09      # pin the reporting period
    python3 generate.py --no-telemetry        # skip transcript ingestion
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(HERE, "sources")
DATA = os.path.join(HERE, "data")
SNAPSHOTS = os.path.join(DATA, "snapshots")
TEMPLATE = os.path.join(HERE, "dashboard_template.html")
OUTPUT = os.path.join(HERE, "ai_assets_dashboard.html")

VERSION = "1.0.0"
CLASSIFICATION = "INTERNAL USE"
OWNER = "Wade Howell"

# ---------------------------------------------------------------------------
# Governance reference data
# ---------------------------------------------------------------------------

# Connectors that can reach personal data are Tier 1 under the Jamaica Data
# Protection Act 2020 (First Schedule, Standard 7 - Security; Standard 8 -
# transfer of personal data outside Jamaica, which every cloud connector here
# engages). Tier 2 handles business content without a personal-data payload.
# Tier 3 is non-sensitive / personal convenience.
CONNECTOR_RISK = {
    "Gmail": (1, "Mailbox contents, contacts, message bodies"),
    "Google Calendar": (1, "Attendee identities, meeting subjects"),
    "Google Drive": (1, "Document corpus, may contain personal data"),
    "Microsoft 365": (1, "SharePoint / OneDrive / Outlook / Teams corpus"),
    "Slack": (1, "Workspace messages and member identities"),
    "Notion": (1, "Workspace pages, may contain personal data"),
    "Intuit Mailchimp": (1, "Marketing lists - personal data by definition"),
    "Atlassian Rovo": (1, "Jira / Confluence work graph"),
    "Zapier": (1, "Credential broker with 9,000+ downstream app reach"),
    "Canva": (2, "Design assets and brand collateral"),
    "Figma": (2, "Design files and design-system context"),
    "Wix": (2, "Site content and publishing control"),
    "Booking.com": (3, "Travel search, no corporate data"),
    "Spotify": (3, "Personal media, no corporate data"),
}

CONTROL_REF = {
    "Connector": "ISO 27001 A.5.19 / A.5.23 - Supplier & cloud service security",
    "Skill": "ISO 27001 A.8.9 - Configuration management",
    "Repository": "ISO 27001 A.8.28 / A.8.31 - Secure coding; environment separation",
    "Plugin": "ISO 27001 A.8.9 - Configuration management",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def month_of(iso: str) -> str:
    return iso[:7]


def read_json(name: str):
    with open(os.path.join(SOURCES, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


def month_range(start: str, end: str):
    """Inclusive list of YYYY-MM strings."""
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    out = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


# ---------------------------------------------------------------------------
# 1. Inventory assembly
# ---------------------------------------------------------------------------


def build_inventory(period: str):
    """Return the flat asset list from the source captures."""
    assets = []

    # --- Connectors -------------------------------------------------------
    conn = read_json("connectors.json")
    for c in conn["connectors"]:
        name = c["name"]
        tier, exposure = CONNECTOR_RISK.get(name, (2, "Not classified"))
        connected = c.get("connected")
        if connected is True and c.get("enabledInChat"):
            status, rag = "Active", "Green"
        elif connected is True:
            status, rag = "Authorised, not enabled in chat", "Amber"
        else:
            status, rag = "Installed, authorisation unverified", "Amber"
        assets.append(
            {
                "asset_id": "CONN-" + re.sub(r"[^A-Za-z0-9]+", "-", name).upper().strip("-"),
                "asset_class": "Connector",
                "asset_name": name,
                "provider": "claude.ai MCP connector"
                            + ("" if not c.get("isAuthless") else " (authless)"),
                "description": c.get("description", ""),
                "status": status,
                "rag": rag,
                "risk_tier": tier,
                "data_exposure": exposure,
                "first_observed": "",       # filled by lifecycle diff
                "last_changed": "",
                "instrumentation": "Telemetry-capable (MCP tool namespace)",
                "control_ref": CONTROL_REF["Connector"],
                "source": conn["source"],
            }
        )

    # --- Skills -----------------------------------------------------------
    man = read_json("skills_manifest.json")
    for s in man.get("skills", []):
        updated = s.get("updatedAt", "")[:10]
        src = s.get("source", "unknown")
        origin = {
            "custom": "Custom / user-authored",
            "anthropic": "Anthropic first-party",
            "anthropic-example": "Anthropic example library",
        }.get(src, src)
        assets.append(
            {
                "asset_id": "SKIL-" + re.sub(r"[^A-Za-z0-9]+", "-", s["name"]).upper().strip("-"),
                "asset_class": "Skill",
                "asset_name": s["name"],
                "provider": origin,
                "description": (s.get("description") or "").split(". ")[0][:220],
                "status": "Enabled",
                "rag": "Green",
                "risk_tier": 2 if src == "custom" else 3,
                "data_exposure": "Executes in session context; inherits session tool grants",
                "first_observed": updated,
                "last_changed": updated,
                "instrumentation": "Telemetry-capable (Skill tool invocation)",
                "control_ref": CONTROL_REF["Skill"],
                "source": "Claude synced skills manifest.json",
            }
        )

    # --- Repositories -----------------------------------------------------
    repos = read_json("repositories.json")
    commits = read_json("repo_commits.json")["commit_dates"]
    for r in repos["repositories"]:
        fn = r["full_name"]
        dates = commits.get(fn)
        hist = r.get("commit_history")
        if hist == "unavailable":
            status, rag = "Inventory only - history not retrievable", "Amber"
            first = ""
        elif hist == "empty" or not dates:
            status, rag = "Empty - zero commits", "Red"
            first = ""
        else:
            status, rag = "Active", "Green"
            first = min(dates)[:10]
        assets.append(
            {
                "asset_id": "REPO-" + re.sub(r"[^A-Za-z0-9]+", "-", fn.split("/")[-1]).upper().strip("-"),
                "asset_class": "Repository",
                "asset_name": fn,
                "provider": "GitHub (" + r["visibility"] + ")",
                "description": r.get("note", ""),
                "status": status,
                "rag": rag,
                "risk_tier": 1 if r["visibility"] == "public" else 2,
                "data_exposure": (
                    "PUBLIC - anything committed is world-readable"
                    if r["visibility"] == "public"
                    else "Private repository"
                ),
                "first_observed": first,
                "last_changed": r.get("pushed_at", "")[:10],
                "instrumentation": "Instrumented (commit history)"
                if hist == "complete"
                else "Not instrumented this run",
                "control_ref": CONTROL_REF["Repository"],
                "source": repos["source"],
            }
        )

    # --- Plugins ----------------------------------------------------------
    # ListPlugins returned an empty set. Recorded explicitly: an empty class is
    # a finding, not an omission.
    return assets


# ---------------------------------------------------------------------------
# 2. Lifecycle diff against the prior snapshot
# ---------------------------------------------------------------------------


def prior_snapshot(period: str):
    files = sorted(glob.glob(os.path.join(SNAPSHOTS, "*.json")))
    files = [f for f in files if os.path.basename(f)[:7] < period]
    if not files:
        return None
    with open(files[-1], "r", encoding="utf-8") as fh:
        return json.load(fh)


def apply_lifecycle(assets, period, prior):
    """Classify each asset NEW / EXISTING / BASELINE and detect RETIRED."""
    prior_ids = {}
    if prior:
        for a in prior.get("assets", []):
            prior_ids[a["asset_id"]] = a

    for a in assets:
        pid = prior_ids.get(a["asset_id"])
        if prior is None:
            # Skills and repositories carry a real provenance date, so their
            # cohort can be dated even on the first run. Connectors do not
            # expose an install date, so they are honestly marked BASELINE.
            if a["first_observed"] and month_of(a["first_observed"]) == period:
                a["lifecycle"] = "NEW"
            elif a["first_observed"]:
                a["lifecycle"] = "EXISTING"
            else:
                a["lifecycle"] = "BASELINE"
        elif pid is None:
            a["lifecycle"] = "NEW"
            if not a["first_observed"]:
                a["first_observed"] = period + "-01"
        else:
            a["lifecycle"] = "EXISTING"
            if not a["first_observed"]:
                a["first_observed"] = pid.get("first_observed", "")

    retired = []
    current_ids = {a["asset_id"] for a in assets}
    for aid, pa in prior_ids.items():
        if aid not in current_ids:
            r = dict(pa)
            r["lifecycle"] = "RETIRED"
            r["status"] = "Removed since " + prior["period"]
            r["rag"] = "Red"
            retired.append(r)
    return assets + retired


# ---------------------------------------------------------------------------
# 3. Telemetry ingestion (real invocation counts)
# ---------------------------------------------------------------------------

TRANSCRIPT_GLOBS = [
    os.path.expanduser("~/.claude/projects/**/*.jsonl"),
    os.path.join(DATA, "telemetry", "**", "*.jsonl"),
]

EVENTS_CSV = os.path.join(DATA, "usage_events.csv")
EVENT_FIELDS = ["uuid", "timestamp", "month", "asset_class", "asset_name", "tool", "session_id", "cwd"]


def ingest_telemetry():
    """Scan Claude session transcripts for tool-use events.

    Maps each event onto an inventoried asset:
      mcp__<Server>__<tool>  -> Connector <Server>
      Skill(skill=<name>)    -> Skill <name>
      any event with a cwd   -> Repository <basename of cwd>

    The ledger is append-only and deduplicated on the transcript event uuid, so
    running this every month accumulates real history even though the execution
    container is ephemeral.
    """
    existing = {}
    if os.path.exists(EVENTS_CSV):
        with open(EVENTS_CSV, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                existing[row["uuid"]] = row

    found = 0
    for pattern in TRANSCRIPT_GLOBS:
        for path in glob.glob(pattern, recursive=True):
            try:
                fh = open(path, "r", encoding="utf-8", errors="replace")
            except OSError:
                continue
            with fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                    except ValueError:
                        continue
                    msg = d.get("message") or {}
                    content = msg.get("content")
                    if not isinstance(content, list):
                        continue
                    ts = d.get("timestamp") or ""
                    for i, block in enumerate(content):
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        tool = block.get("name") or ""
                        uid = f"{d.get('uuid','')}#{i}"
                        if not uid.strip("#") or uid in existing:
                            continue
                        cls, name = classify_tool(tool, block.get("input") or {})
                        if not cls:
                            continue
                        existing[uid] = {
                            "uuid": uid,
                            "timestamp": ts,
                            "month": month_of(ts),
                            "asset_class": cls,
                            "asset_name": name,
                            "tool": tool,
                            "session_id": d.get("sessionId", ""),
                            "cwd": d.get("cwd", ""),
                        }
                        found += 1

    os.makedirs(DATA, exist_ok=True)
    rows = sorted(existing.values(), key=lambda r: r["timestamp"])
    with open(EVENTS_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=EVENT_FIELDS)
        w.writeheader()
        w.writerows(rows)
    return rows, found


MCP_RE = re.compile(r"^mcp__([A-Za-z0-9_]+?)__")
SERVER_TO_CONNECTOR = {
    "Google_Calendar": "Google Calendar",
    "Google_Drive": "Google Drive",
    "Intuit_Mailchimp": "Intuit Mailchimp",
    "Claude_Code_Remote": None,   # platform control plane, not a user connector
    "github": None,               # platform integration, not a claude.ai connector
}


def classify_tool(tool: str, tool_input: dict):
    m = MCP_RE.match(tool)
    if m:
        server = m.group(1)
        if server in SERVER_TO_CONNECTOR:
            mapped = SERVER_TO_CONNECTOR[server]
            if mapped is None:
                return None, None
            return "Connector", mapped
        return "Connector", server.replace("_", " ")
    if tool == "Skill":
        name = (tool_input or {}).get("skill")
        if name:
            return "Skill", str(name)
    return None, None


# ---------------------------------------------------------------------------
# 4. Monthly fact table
# ---------------------------------------------------------------------------


def build_facts(assets, events, period):
    """Long-format monthly facts. One row = (month, asset, metric, value)."""
    facts = []
    commits = read_json("repo_commits.json")["commit_dates"]

    # Repository commit activity - real, measured
    for full_name, dates in commits.items():
        if not dates:
            continue
        per_month = Counter(month_of(d) for d in dates)
        for mth, n in sorted(per_month.items()):
            facts.append(
                {
                    "month": mth,
                    "asset_class": "Repository",
                    "asset_name": full_name,
                    "metric": "commits",
                    "value": n,
                    "basis": "measured",
                }
            )

    # Skill provisioning events - real, from manifest updatedAt
    for a in assets:
        if a["asset_class"] == "Skill" and a["first_observed"]:
            facts.append(
                {
                    "month": month_of(a["first_observed"]),
                    "asset_class": "Skill",
                    "asset_name": a["asset_name"],
                    "metric": "provisioned",
                    "value": 1,
                    "basis": "measured",
                }
            )

    # Observed invocations - real, from transcript telemetry
    inv = Counter((e["month"], e["asset_class"], e["asset_name"]) for e in events)
    for (mth, cls, name), n in sorted(inv.items()):
        facts.append(
            {
                "month": mth,
                "asset_class": cls,
                "asset_name": name,
                "metric": "invocations",
                "value": n,
                "basis": "measured",
            }
        )
    return facts


# ---------------------------------------------------------------------------
# 5. Emit
# ---------------------------------------------------------------------------


def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


REGISTER_FIELDS = [
    "asset_id", "asset_class", "asset_name", "provider", "lifecycle", "status",
    "rag", "risk_tier", "data_exposure", "first_observed", "last_changed",
    "instrumentation", "control_ref", "description", "source",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m"))
    ap.add_argument("--no-telemetry", action="store_true")
    args = ap.parse_args()
    period = args.period

    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    prior = prior_snapshot(period)
    assets = apply_lifecycle(build_inventory(period), period, prior)

    events, new_events = ([], 0) if args.no_telemetry else ingest_telemetry()
    facts = build_facts(assets, events, period)

    write_csv(os.path.join(DATA, "asset_register.csv"), assets, REGISTER_FIELDS)
    write_csv(
        os.path.join(DATA, "usage_monthly.csv"),
        facts,
        ["month", "asset_class", "asset_name", "metric", "value", "basis"],
    )

    snapshot = {
        "period": period,
        "generated_at": generated_at,
        "version": VERSION,
        "classification": CLASSIFICATION,
        "owner": OWNER,
        "prior_period": prior["period"] if prior else None,
        "counts": dict(Counter(a["asset_class"] for a in assets)),
        "lifecycle": dict(Counter(a["lifecycle"] for a in assets)),
        "telemetry_events_total": len(events),
        "telemetry_events_new_this_run": new_events,
        "assets": assets,
    }
    os.makedirs(SNAPSHOTS, exist_ok=True)
    with open(os.path.join(SNAPSHOTS, period + ".json"), "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=1)

    render(assets, facts, events, snapshot, period, generated_at, prior)

    print(f"period            : {period}")
    print(f"assets            : {len(assets)}  {snapshot['counts']}")
    print(f"lifecycle         : {snapshot['lifecycle']}")
    print(f"facts             : {len(facts)}")
    print(f"telemetry events  : {len(events)} ({new_events} new this run)")
    print(f"dashboard         : {OUTPUT} ({os.path.getsize(OUTPUT)/1024:.1f} KB)")


def render(assets, facts, events, snapshot, period, generated_at, prior):
    with open(TEMPLATE, "r", encoding="utf-8") as fh:
        tpl = fh.read()

    months = sorted({f["month"] for f in facts})
    if months:
        months = month_range(months[0], max(months[-1], period))
    else:
        months = [period]

    payload = {
        "meta": {
            "period": period,
            "generated_at": generated_at,
            "version": VERSION,
            "classification": CLASSIFICATION,
            "owner": OWNER,
            "prior_period": prior["period"] if prior else None,
            "months": months,
        },
        "assets": assets,
        "facts": facts,
        "instrumentation": instrumentation_summary(assets, events),
        "provenance": provenance_rows(),
    }

    out = tpl.replace("/*__PAYLOAD__*/null", json.dumps(payload, separators=(",", ":")))
    out = out.replace("__PERIOD__", html.escape(period))
    out = out.replace("__GENERATED__", html.escape(generated_at))
    out = out.replace("__VERSION__", VERSION)
    out = out.replace("__CLASSIFICATION__", CLASSIFICATION)
    with open(OUTPUT, "w", encoding="utf-8") as fh:
        fh.write(out)


def instrumentation_summary(assets, events):
    """RAG coverage: which asset classes actually have measurable usage."""
    seen = defaultdict(set)
    for e in events:
        seen[e["asset_class"]].add(e["asset_name"])

    rows = []
    by_class = defaultdict(list)
    for a in assets:
        if a["lifecycle"] != "RETIRED":
            by_class[a["asset_class"]].append(a)

    for cls, items in sorted(by_class.items()):
        total = len(items)
        if cls == "Repository":
            observed = sum(1 for a in items if a["instrumentation"].startswith("Instrumented"))
            metric = "Commit history"
        else:
            observed = len(seen.get(cls, ()))
            metric = "Session-transcript tool-use events"
        pct = round(100 * observed / total) if total else 0
        rag = "Green" if pct >= 80 else "Amber" if pct >= 30 else "Red"
        rows.append(
            {
                "asset_class": cls,
                "total": total,
                "observed": observed,
                "coverage_pct": pct,
                "rag": rag,
                "metric": metric,
            }
        )
    return rows


STALE_AFTER_DAYS = 45


def age_days(captured_at, now):
    try:
        t = dt.datetime.strptime(captured_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except (ValueError, TypeError):
        return None
    return (now - t).days


def provenance_rows():
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for fname in sorted(os.listdir(SOURCES)):
        path = os.path.join(SOURCES, fname)
        if not fname.endswith(".json"):
            continue
        try:
            d = json.load(open(path, encoding="utf-8"))
        except ValueError:
            continue
        captured = d.get("captured_at")
        if not captured and d.get("lastUpdated"):
            captured = dt.datetime.fromtimestamp(
                d["lastUpdated"] / 1000, dt.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
        age = age_days(captured, now)
        rows.append(
            {
                "file": "sources/" + fname,
                "source": d.get("source", "Claude synced skills manifest (manifest.json)"),
                "captured_at": captured or "",
                "age_days": age,
                "stale": bool(age is not None and age > STALE_AFTER_DAYS),
                "bytes": os.path.getsize(path),
            }
        )
    return rows


if __name__ == "__main__":
    sys.exit(main())
