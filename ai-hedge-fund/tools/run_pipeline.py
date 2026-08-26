#!/usr/bin/env python3
"""Pipeline planner — prints the exact run plan for the 10 agents.

    python3 tools/run_pipeline.py                 # full plan
    python3 tools/run_pipeline.py --stage 5       # one stage
    python3 tools/run_pipeline.py --from 6        # stage 6 onward
    python3 tools/run_pipeline.py --ticker NVDA   # override for this run
    python3 tools/run_pipeline.py --status        # what fund/ already holds

This prints a plan; Claude Code executes it by invoking each subagent with the
Task tool. Nothing here places a trade, and nothing here can.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import guardrails                                    # noqa: E402
import prefs                                         # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STAGES = [
    (1,  "1-scanner",      "Market Scanner",      "fund/1-scan.md",         []),
    (2,  "2-news",         "News Analyst",        "fund/2-news.md",         [1]),
    (3,  "3-fundamentals", "Fundamental Analyst", "fund/3-fundamentals.md", [2]),
    (4,  "4-technicals",   "Technical Analyst",   "fund/4-technicals.md",   [1]),
    (5,  "5-quant",        "Quant Agent",         "fund/5-quant.md",        [3, 4]),
    (6,  "6-bull",         "Bull Analyst",        "fund/6-bull.md",         [2, 3, 4]),
    (7,  "7-bear",         "Bear Analyst",        "fund/7-bear.md",         [2, 3, 4]),
    (8,  "8-risk",         "Risk Manager",        "fund/8-risk.md",         [5]),
    (9,  "9-portfolio",    "Portfolio Manager",   "fund/9-portfolio.md",    [8]),
    (10, "10-memo",        "Fund Manager",        "fund/10-memo.md",        [6, 7, 8, 9]),
]
PARALLEL_GROUP = {2, 3, 4}          # independent research stages


def status() -> dict:
    out = {}
    for n, key, label, path, _ in STAGES:
        full = os.path.join(ROOT, path)
        if os.path.exists(full):
            st = os.stat(full)
            out[path] = {
                "stage": n, "agent": label, "exists": True,
                "bytes": st.st_size,
                "modified": dt.datetime.fromtimestamp(
                    st.st_mtime, dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            }
        else:
            out[path] = {"stage": n, "agent": label, "exists": False}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", type=int, help="run a single stage")
    ap.add_argument("--from", dest="from_stage", type=int, help="run from this stage onward")
    ap.add_argument("--ticker", help="override the ticker for this run")
    ap.add_argument("--status", action="store_true", help="show what fund/ holds")
    ap.add_argument("--json", action="store_true", help="machine-readable plan")
    a = ap.parse_args()

    guardrails.enforce()                 # refuses to proceed if weakened
    p = prefs.load()

    problems = prefs.validate(p)
    if problems:
        print("Preferences are invalid — fix them in the UI before running:")
        for x in problems:
            print("  -", x)
        return 1

    if a.status:
        print(json.dumps(status(), indent=2))
        return 0

    ticker = (a.ticker or p["research"]["primary_ticker"]).upper()
    agents_cfg = p["agents"]

    selected = [s for s in STAGES
                if (a.stage is None or s[0] == a.stage)
                and (a.from_stage is None or s[0] >= a.from_stage)]

    plan = []
    for n, key, label, out, deps in selected:
        cfg = agents_cfg.get(key, {})
        missing = [STAGES[d - 1][3] for d in deps
                   if not os.path.exists(os.path.join(ROOT, STAGES[d - 1][3]))]
        plan.append({
            "stage": n, "agent": key, "label": label, "model": cfg.get("model"),
            "enabled": cfg.get("enabled", True), "output": out,
            "depends_on": [STAGES[d - 1][3] for d in deps],
            "missing_inputs": missing,
            "parallel_with": sorted(PARALLEL_GROUP - {n}) if n in PARALLEL_GROUP else [],
            "notes": cfg.get("notes", ""),
        })

    if a.json:
        print(json.dumps({"ticker": ticker, "plan": plan}, indent=2))
        return 0

    print(f"\n  AI HEDGE FUND — run plan for {ticker}")
    print(f"  {'─' * 62}")
    print(f"  Provider: {p['data']['market_provider']} · news: {p['data']['news_provider']}"
          f" · SEC: {'on' if p['data']['sec_enabled'] else 'off'}")
    print(f"  Risk: max {p['risk']['max_position_pct']}%/position · "
          f"{p['risk']['min_cash_buffer_pct']}% cash floor · "
          f"min {p['risk']['min_risk_reward']}:1 R/R")
    print(f"  Backtest: {p['backtest']['lookback_years']}y lookback · "
          f"{p['backtest']['out_of_sample_pct']}% held out · "
          f"min {p['backtest']['min_trades']} trades\n")

    for s in plan:
        mark = "  " if s["enabled"] else "· "
        state = "" if s["enabled"] else "  (disabled)"
        par = f"  ∥ with stage {s['parallel_with']}" if s["parallel_with"] else ""
        print(f"{mark}{s['stage']:>2}. {s['label']:<20} [{s['model']}] → {s['output']}"
              f"{state}{par}")
        if s["missing_inputs"] and s["enabled"]:
            print(f"      ⚠ waiting on: {', '.join(s['missing_inputs'])}")

    disabled = [s for s in plan if not s["enabled"]]
    print(f"\n  {'─' * 62}")
    if disabled:
        print(f"  {len(disabled)} stage(s) disabled in preferences — enable them in the UI.")
    print("  Invoke each enabled stage in order with the Task tool, using the matching")
    print("  definition in .claude/agents/. Stages 2–4 may run in parallel.")
    print("  Everything downstream is SIMULATED. Read fund/10-memo.md at the end.")
    print("  Not investment advice. Human approval required before any real-money action.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
