#!/usr/bin/env python3
"""Guardrail enforcement. Imported by the pipeline runner, which refuses to run
if the guardrails are missing or have been weakened.

    python3 tools/guardrails.py check
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "GUARDRAILS.md")

# Each rule must still be present in GUARDRAILS.md, identified by a phrase that
# cannot survive the rule being deleted or inverted.
REQUIRED = {
    "research_only":            r"research,?\s+backtesting,?\s+(and\s+)?paper trading",
    "never_promise_profits":    r"[Nn]ever promise profits",
    "label_simulated":          r"SIMULATED",
    "real_data_only":           r"[Rr]eal data only",
    "no_brokerage":             r"[Nn]ever connect to a live brokerage|No brokerage",
    "human_approval":           r"[Hh]uman approval",
    "flag_overfitting":         r"[Oo]ver-fitting",
    "secrets_in_env":           r"\.env",
    "memo_disclaimer":          r"[Nn]ot financial advice",
    "both_sides_debate":        r"Bull and Bear|both sides",
}

# Substrings that must never appear anywhere in the repository's own code —
# the system has no business knowing how to place an order.
FORBIDDEN_CODE = [
    "place_order", "submit_order", "create_order", "buy_market", "sell_market",
    "alpaca", "ibkr", "interactive_brokers", "tda_api", "brokerage_connect",
]


def check(verbose: bool = True) -> list[str]:
    problems: list[str] = []

    if not os.path.exists(DOC):
        return ["GUARDRAILS.md is missing. The pipeline will not run without it."]

    with open(DOC) as fh:
        text = fh.read()

    for name, pattern in REQUIRED.items():
        if not re.search(pattern, text, re.IGNORECASE):
            problems.append(f"GUARDRAILS.md no longer states rule '{name}'")

    tools_dir = os.path.join(ROOT, "tools")
    for fn in sorted(os.listdir(tools_dir)):
        if not fn.endswith(".py") or fn == "guardrails.py":
            continue
        with open(os.path.join(tools_dir, fn)) as fh:
            src = fh.read().lower()
        for bad in FORBIDDEN_CODE:
            if bad in src:
                problems.append(
                    f"tools/{fn} contains '{bad}' — this system must have no "
                    f"order-placement or brokerage code, not even disabled (GUARDRAILS.md #5)")

    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        gi = os.path.join(ROOT, ".gitignore")
        ignored = os.path.exists(gi) and ".env" in open(gi).read()
        if not ignored:
            problems.append(".env exists but is not git-ignored — secrets could be committed "
                            "(GUARDRAILS.md #8)")

    if verbose:
        if problems:
            print("GUARDRAIL CHECK FAILED")
            for p in problems:
                print("  ✗", p)
        else:
            print(f"Guardrails intact — {len(REQUIRED)} rules present, "
                  f"no brokerage code, secrets ignored.")
    return problems


def enforce() -> None:
    """Raise rather than let a pipeline run with weakened guardrails."""
    problems = check(verbose=False)
    if problems:
        raise SystemExit(
            "Refusing to run: guardrails have been weakened or removed.\n  - "
            + "\n  - ".join(problems))


if __name__ == "__main__":
    sys.exit(1 if check() else 0)
