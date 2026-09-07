#!/usr/bin/env python3
"""
Self-test for the AI Asset & Usage Dashboard pipeline.

Proves the parts that would otherwise be asserted rather than demonstrated:

  1. classify_tool() maps real Claude tool names onto inventoried assets.
  2. ingest_telemetry() reads a real-shaped transcript and produces usage rows.
  3. The lifecycle diff reports NEW / EXISTING / RETIRED correctly against a
     prior snapshot.
  4. The rendered dashboard contains a parseable payload and stays within the
     115 KB standalone-artifact budget.

Run:  python3 selftest.py
Exit: 0 = all pass, 1 = one or more failures.

The fixture transcript lives in tests/fixtures/ which is deliberately OUTSIDE
the telemetry glob, so running this never contaminates the real ledger.
"""

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import generate  # noqa: E402

FIXTURE_DIR = os.path.join(HERE, "tests", "fixtures")
FIXTURE = os.path.join(FIXTURE_DIR, "sample_session.jsonl")

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("  PASS  " if cond else "  FAIL  ") + name + ((" — " + detail) if detail else ""))
    return cond


def write_fixture():
    """A transcript in the exact shape Claude Code writes: one JSON object per
    line, assistant messages carrying tool_use content blocks."""
    os.makedirs(FIXTURE_DIR, exist_ok=True)
    rows = [
        {"type": "assistant", "uuid": "u1", "sessionId": "s1", "cwd": "/home/user/bhba-2027",
         "timestamp": "2026-07-14T09:12:00.000Z",
         "message": {"content": [{"type": "tool_use", "name": "mcp__Gmail__search_threads", "input": {}}]}},
        {"type": "assistant", "uuid": "u2", "sessionId": "s1", "cwd": "/home/user/bhba-2027",
         "timestamp": "2026-07-14T09:14:00.000Z",
         "message": {"content": [
             {"type": "tool_use", "name": "mcp__Google_Drive__search_files", "input": {}},
             {"type": "tool_use", "name": "Skill", "input": {"skill": "xlsx"}}]}},
        {"type": "assistant", "uuid": "u3", "sessionId": "s2", "cwd": "/home/user/bhba-2027",
         "timestamp": "2026-08-02T11:00:00.000Z",
         "message": {"content": [{"type": "tool_use", "name": "mcp__Notion__notion-search", "input": {}}]}},
        # Platform tooling — must NOT be counted as a user connector.
        {"type": "assistant", "uuid": "u4", "sessionId": "s2", "cwd": "/home/user/bhba-2027",
         "timestamp": "2026-08-02T11:05:00.000Z",
         "message": {"content": [{"type": "tool_use", "name": "mcp__github__list_commits", "input": {}}]}},
        {"type": "assistant", "uuid": "u5", "sessionId": "s2", "cwd": "/home/user/bhba-2027",
         "timestamp": "2026-08-02T11:06:00.000Z",
         "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}},
        {"type": "user", "uuid": "u6", "message": {"content": "plain text turn"}},
        {"type": "assistant", "uuid": "u7", "message": {"content": None}},
        "{ not valid json at all",
    ]
    with open(FIXTURE, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(r if isinstance(r, str) else json.dumps(r))
            fh.write("\n")


# ---------------------------------------------------------------------------
# 1. Tool classification
# ---------------------------------------------------------------------------
def test_classify():
    print("\n[1] Tool-name classification")
    cases = [
        ("mcp__Gmail__send_message", {}, ("Connector", "Gmail")),
        ("mcp__Google_Drive__search_files", {}, ("Connector", "Google Drive")),
        ("mcp__Google_Calendar__list_events", {}, ("Connector", "Google Calendar")),
        ("mcp__Intuit_Mailchimp__get_analytics", {}, ("Connector", "Intuit Mailchimp")),
        ("mcp__Notion__notion-search", {}, ("Connector", "Notion")),
        ("mcp__Canva__export-design", {}, ("Connector", "Canva")),
        ("mcp__Zapier__execute_zapier_read_action", {}, ("Connector", "Zapier")),
        ("Skill", {"skill": "xlsx"}, ("Skill", "xlsx")),
        ("Skill", {"skill": "build-dashboard"}, ("Skill", "build-dashboard")),
        # Platform control-plane and repo tooling are not user connectors.
        ("mcp__Claude_Code_Remote__list_repos", {}, (None, None)),
        ("mcp__github__list_commits", {}, (None, None)),
        ("Bash", {}, (None, None)),
        ("Read", {}, (None, None)),
    ]
    ok = True
    for tool, inp, expected in cases:
        got = generate.classify_tool(tool, inp)
        ok &= check(f"{tool} -> {expected}", got == expected, "" if got == expected else f"got {got}")
    return ok


# ---------------------------------------------------------------------------
# 2. Telemetry ingestion end-to-end
# ---------------------------------------------------------------------------
def test_ingest():
    print("\n[2] Telemetry ingestion against a real-shaped transcript")
    tmp = tempfile.mkdtemp(prefix="aiassets-selftest-")
    real_data, real_globs, real_events = generate.DATA, generate.TRANSCRIPT_GLOBS, generate.EVENTS_CSV
    try:
        generate.DATA = tmp
        generate.EVENTS_CSV = os.path.join(tmp, "usage_events.csv")
        generate.TRANSCRIPT_GLOBS = [os.path.join(FIXTURE_DIR, "*.jsonl")]

        # The fixture holds 4 asset-mapped tool calls across 3 assistant turns —
        # one turn carries two tool_use blocks, which must be counted separately.
        rows, new = generate.ingest_telemetry()
        ok = check("4 asset-mapped events extracted", len(rows) == 4, f"got {len(rows)}")
        ok &= check("malformed and non-tool lines skipped without error", new == 4, f"new={new}")
        ok &= check("both tool blocks in a single turn counted separately",
                    len({r["uuid"] for r in rows if r["uuid"].startswith("u2#")}) == 2)

        names = sorted(r["asset_name"] for r in rows)
        ok &= check("mapped assets correct",
                    names == ["Gmail", "Google Drive", "Notion", "xlsx"], f"got {names}")
        ok &= check("github/Bash/Claude_Code_Remote excluded",
                    not any("github" in r["asset_name"].lower() for r in rows))
        months = sorted({r["month"] for r in rows})
        ok &= check("months derived from event timestamps", months == ["2026-07", "2026-08"], f"got {months}")

        # Idempotency: a second pass must add nothing (dedup on event uuid).
        rows2, new2 = generate.ingest_telemetry()
        ok &= check("re-run is idempotent (append-only ledger deduped)",
                    new2 == 0 and len(rows2) == len(rows), f"new={new2}, total={len(rows2)}")
        return ok
    finally:
        generate.DATA, generate.TRANSCRIPT_GLOBS, generate.EVENTS_CSV = real_data, real_globs, real_events
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# 3. Lifecycle diff
# ---------------------------------------------------------------------------
def test_lifecycle():
    print("\n[3] Lifecycle diff against a prior snapshot")
    prior = {"period": "2026-08", "assets": [
        {"asset_id": "CONN-GMAIL", "asset_class": "Connector", "first_observed": "2026-08-01"},
        {"asset_id": "CONN-SLACK", "asset_class": "Connector", "first_observed": "2026-08-01"},
    ]}
    current = [
        {"asset_id": "CONN-GMAIL", "asset_class": "Connector", "asset_name": "Gmail",
         "first_observed": "", "status": "Active", "rag": "Green"},
        {"asset_id": "CONN-CANVA", "asset_class": "Connector", "asset_name": "Canva",
         "first_observed": "", "status": "Active", "rag": "Green"},
    ]
    out = generate.apply_lifecycle(current, "2026-09", prior)
    by = {a["asset_id"]: a for a in out}
    ok = check("carried-over asset marked EXISTING", by["CONN-GMAIL"]["lifecycle"] == "EXISTING")
    ok &= check("first_observed inherited from prior snapshot",
                by["CONN-GMAIL"]["first_observed"] == "2026-08-01")
    ok &= check("unseen asset marked NEW", by["CONN-CANVA"]["lifecycle"] == "NEW")
    ok &= check("absent asset marked RETIRED", by["CONN-SLACK"]["lifecycle"] == "RETIRED")

    # First run: no prior snapshot -> BASELINE, never a false "NEW".
    fresh = [{"asset_id": "CONN-X", "asset_class": "Connector", "asset_name": "X",
              "first_observed": "", "status": "", "rag": "Green"}]
    out2 = generate.apply_lifecycle(fresh, "2026-09", None)
    ok &= check("first run with no provisioning date -> BASELINE, not NEW",
                out2[0]["lifecycle"] == "BASELINE")
    return ok


# ---------------------------------------------------------------------------
# 4. Rendered artifact
# ---------------------------------------------------------------------------
def test_artifact():
    print("\n[4] Rendered dashboard")
    path = generate.OUTPUT
    if not os.path.exists(path):
        return check("dashboard exists", False, "run generate.py first")
    size = os.path.getsize(path)
    html = open(path, encoding="utf-8").read()
    ok = check(f"size within 115 KB budget ({size/1024:.1f} KB)", size <= 115 * 1024)
    ok &= check("payload placeholder was substituted", "/*__PAYLOAD__*/null" not in html)
    ok &= check("no unsubstituted template tokens",
                "__PERIOD__" not in html and "__GENERATED__" not in html
                and "__VERSION__" not in html and "__CLASSIFICATION__" not in html)
    # The SVG XML namespace is an identifier, never a network fetch, so it is
    # the one permitted "http://" string in a standalone file.
    stripped = html.replace("http://www.w3.org/2000/svg", "")
    ok &= check("no external resource references (standalone)",
                "http://" not in stripped and "https://" not in stripped)
    start = html.index("const DATA = ") + len("const DATA = ")
    end = html.index(";\n", start)
    try:
        payload = json.loads(html[start:end])
        ok &= check("embedded payload is valid JSON", True)
        ok &= check("payload carries assets and facts",
                    len(payload["assets"]) > 0 and len(payload["facts"]) > 0,
                    f"{len(payload['assets'])} assets, {len(payload['facts'])} facts")
        ok &= check("no placeholder text in payload",
                    not any(tok in json.dumps(payload) for tok in ("TODO", "INSERT ", "TBD", "Lorem")))
        bases = {f["basis"] for f in payload["facts"]}
        ok &= check("every fact is measured, none estimated", bases == {"measured"}, f"bases={bases}")
    except ValueError as exc:
        ok &= check("embedded payload is valid JSON", False, str(exc))
    return ok


def main():
    print("=" * 68)
    print("AI Asset & Usage Dashboard — pipeline self-test")
    print("=" * 68)
    write_fixture()
    test_classify()
    test_ingest()
    test_lifecycle()
    test_artifact()

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print("\n" + "=" * 68)
    print(f"{passed}/{total} checks passed")
    print("=" * 68)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
