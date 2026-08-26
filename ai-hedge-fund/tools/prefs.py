#!/usr/bin/env python3
"""Preferences — the single source of truth for the AI Hedge Fund.

Loads config/preferences.json (falling back to preferences.default.json), validates it,
and regenerates the human-readable risk-rules.md and ticker.md so the markdown the agents
read never drifts from the JSON the UI writes.

    python3 tools/prefs.py show
    python3 tools/prefs.py get risk.max_position_pct
    python3 tools/prefs.py set risk.max_position_pct 15
    python3 tools/prefs.py sync          # regenerate risk-rules.md + ticker.md
    python3 tools/prefs.py validate
    python3 tools/prefs.py reset
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULTS = os.path.join(ROOT, "config", "preferences.default.json")
ACTIVE = os.path.join(ROOT, "config", "preferences.json")

# Guardrails are not user preferences. Any attempt to write these is dropped.
LOCKED_SECTION = "guardrails"


# ── load / save ────────────────────────────────────────────────────────────

def _deep_merge(base: dict, over: dict) -> dict:
    """Overlay `over` onto `base`, recursing into dicts. Unknown keys are kept."""
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_defaults() -> dict:
    with open(DEFAULTS) as fh:
        return json.load(fh)


def load() -> dict:
    """Active preferences, with defaults filled in for anything missing."""
    base = load_defaults()
    if not os.path.exists(ACTIVE):
        return base
    try:
        with open(ACTIVE) as fh:
            user = json.load(fh)
    except json.JSONDecodeError as e:
        raise SystemExit(f"config/preferences.json is not valid JSON: {e}")
    merged = _deep_merge(base, user)
    # Guardrails always come from defaults. They are not user-settable.
    merged[LOCKED_SECTION] = base[LOCKED_SECTION]
    return merged


def save(prefs: dict, updated_by: str = "cli") -> dict:
    """Validate, stamp, write, and re-sync the markdown mirrors."""
    prefs = copy.deepcopy(prefs)
    prefs[LOCKED_SECTION] = load_defaults()[LOCKED_SECTION]
    problems = validate(prefs)
    if problems:
        raise ValueError("Invalid preferences:\n  - " + "\n  - ".join(problems))
    prefs.setdefault("meta", {})
    prefs["meta"]["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    prefs["meta"]["updated_by"] = updated_by
    os.makedirs(os.path.dirname(ACTIVE), exist_ok=True)
    tmp = ACTIVE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(prefs, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, ACTIVE)          # atomic: never leave a half-written config
    sync_markdown(prefs)
    return prefs


# ── validation ─────────────────────────────────────────────────────────────

def validate(p: dict) -> list[str]:
    """Return a list of problems. Empty list means valid."""
    errs: list[str] = []

    def num(path, lo=None, hi=None):
        node, *rest = path.split(".")
        cur = p.get(node, {})
        for r in rest[:-1]:
            cur = cur.get(r, {}) if isinstance(cur, dict) else {}
        v = cur.get(rest[-1]) if rest else cur
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            errs.append(f"{path} must be a number (got {v!r})")
            return None
        if lo is not None and v < lo:
            errs.append(f"{path} must be >= {lo} (got {v})")
        if hi is not None and v > hi:
            errs.append(f"{path} must be <= {hi} (got {v})")
        return v

    r = p.get("risk", {})
    max_pos = num("risk.max_position_pct", 0, 100)
    entry = num("risk.max_entry_position_pct", 0, 100)
    min_pos = num("risk.min_position_pct", 0, 100)
    cash = num("risk.min_cash_buffer_pct", 0, 100)
    num("risk.max_sector_pct", 0, 100)
    num("risk.max_correlated_cluster_pct", 0, 100)
    num("risk.correlation_threshold", -1, 1)
    num("risk.max_positions", 1, 500)
    num("risk.min_risk_reward", 0)
    num("risk.max_portfolio_drawdown_pct", 0, 100)
    num("risk.max_strategy_drawdown_pct", 0, 100)
    num("risk.default_stop_pct", 0, 100)

    if None not in (max_pos, entry) and entry > max_pos:
        errs.append(
            f"risk.max_entry_position_pct ({entry}) cannot exceed "
            f"risk.max_position_pct ({max_pos})")
    if None not in (min_pos, max_pos) and min_pos > max_pos:
        errs.append(
            f"risk.min_position_pct ({min_pos}) cannot exceed "
            f"risk.max_position_pct ({max_pos})")
    if None not in (max_pos, cash):
        # A single max-size position must still leave the cash buffer intact.
        if max_pos + cash > 100:
            errs.append(
                f"risk.max_position_pct ({max_pos}) + risk.min_cash_buffer_pct ({cash}) "
                f"exceeds 100% — a max-size position could not leave the buffer intact")
    mp, cnt = r.get("max_position_pct"), r.get("max_positions")
    if isinstance(mp, (int, float)) and isinstance(cnt, int) and mp * cnt < 100 - (cash or 0):
        pass  # under-allocation is allowed; only over-allocation is an error

    b = p.get("backtest", {})
    num("backtest.lookback_years", 1, 50)
    num("backtest.min_trades", 1)
    num("backtest.min_sample_years", 0)
    num("backtest.overfit_sharpe_threshold", 0)
    num("backtest.out_of_sample_pct", 0, 90)
    num("backtest.initial_capital", 1)
    num("backtest.commission_bps", 0, 1000)
    num("backtest.slippage_bps", 0, 1000)
    if isinstance(b.get("lookback_years"), (int, float)) and \
       isinstance(b.get("min_sample_years"), (int, float)) and \
       b["min_sample_years"] > b["lookback_years"]:
        errs.append(
            f"backtest.min_sample_years ({b['min_sample_years']}) exceeds "
            f"backtest.lookback_years ({b['lookback_years']}) — no backtest could ever pass")

    res = p.get("research", {})
    tick = res.get("primary_ticker")
    if not isinstance(tick, str) or not tick.strip():
        errs.append("research.primary_ticker must be a non-empty ticker symbol")
    elif not tick.replace(".", "").replace("-", "").isalnum():
        errs.append(f"research.primary_ticker {tick!r} is not a plausible symbol")
    if not isinstance(res.get("watchlist", []), list):
        errs.append("research.watchlist must be a list")

    valid_market = {"yfinance", "alphavantage", "fmp", "finnhub"}
    if p.get("data", {}).get("market_provider") not in valid_market:
        errs.append(f"data.market_provider must be one of {sorted(valid_market)}")
    valid_news = {"newsapi", "finnhub", "none"}
    if p.get("data", {}).get("news_provider") not in valid_news:
        errs.append(f"data.news_provider must be one of {sorted(valid_news)}")

    agents = p.get("agents", {})
    if not isinstance(agents, dict) or not agents:
        errs.append("agents must be a non-empty object")
    else:
        for key, a in agents.items():
            if a.get("model") not in {"opus", "sonnet", "haiku"}:
                errs.append(f"agents.{key}.model must be opus, sonnet, or haiku")
        # The debate is symmetric by design; one side alone produces a biased memo.
        bull = agents.get("6-bull", {}).get("enabled")
        bear = agents.get("7-bear", {}).get("enabled")
        if bull != bear:
            errs.append(
                "agents 6-bull and 7-bear must be enabled or disabled together — "
                "a one-sided debate produces a biased memo (GUARDRAILS.md #10)")
        if agents.get("8-risk", {}).get("enabled") is False and \
           agents.get("9-portfolio", {}).get("enabled") is True:
            errs.append(
                "agents.9-portfolio requires agents.8-risk — the Portfolio Manager may only "
                "allocate risk-approved ideas")

    g = p.get("guardrails", {})
    for k, v in g.items():
        if k.startswith("_"):
            continue
        if v is not True:
            errs.append(f"guardrails.{k} cannot be disabled (GUARDRAILS.md)")

    return errs


# ── markdown mirrors ───────────────────────────────────────────────────────

def sync_markdown(p: dict) -> None:
    """Regenerate risk-rules.md and ticker.md from the JSON."""
    r, b, res = p["risk"], p["backtest"], p["research"]
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    risk_md = f"""# Risk Rules

The Risk Manager enforces these. It **rejects** any idea that breaks one and says which.

> Generated from `config/preferences.json` at {stamp}. Edit through the System Preferences UI
> (`python3 tools/serve_ui.py`) — hand edits here are overwritten on the next sync.
> All positions and limits are **SIMULATED**.

---

## Position sizing

| Rule | Limit |
|---|---|
| Max single position | **{r['max_position_pct']}%** of simulated portfolio |
| Max new position at entry | **{r['max_entry_position_pct']}%** |
| Minimum position (avoid dust) | **{r['min_position_pct']}%** |

## Portfolio exposure

| Rule | Limit |
|---|---|
| Minimum cash buffer | **{r['min_cash_buffer_pct']}%** |
| Max single-sector exposure | **{r['max_sector_pct']}%** |
| Max correlated cluster (ρ > {r['correlation_threshold']}) | **{r['max_correlated_cluster_pct']}%** |
| Max simultaneous positions | **{r['max_positions']}** |

## Per-idea requirements

Every idea must have **all** of these or it is rejected:

- A written **entry** rule
- {'A written **exit** rule (target)' if r['require_exit_rule'] else '_(exit rule not required — not recommended)_'}
- {'A **stop** level' if r['require_stop'] else '_(stop not required — not recommended)_'}
- A risk/reward ratio of at least **{r['min_risk_reward']}:1**
- A stated holding-period assumption

## Drawdown

| Rule | Limit |
|---|---|
| Max simulated portfolio drawdown | **{r['max_portfolio_drawdown_pct']}%** — breach halts new positions |
| Max acceptable backtest max-DD for a strategy | **{r['max_strategy_drawdown_pct']}%** |
| Per-position stop distance | **{r['default_stop_pct']}%** default |

## Backtest quality gates

An idea backed by a backtest that fails these is flagged, not accepted at face value:

- Minimum **{b['min_trades']} trades** in the sample — fewer is an anecdote
- Minimum sample period **{b['min_sample_years']} years**
- Sharpe above **{b['overfit_sharpe_threshold']}** is treated as an over-fitting red flag, not a strength
- Must be checked on a held-back **{b['out_of_sample_pct']}%** out-of-sample slice

---

## How the Risk Manager reports

```
✅ PASS   — 12% position, 2.4:1 R/R, stop at $x, sector tech 28% (under {r['max_sector_pct']}% cap).
❌ REJECT — 25% position breaks the {r['max_position_pct']}% single-position cap. Resize to ≤{r['max_position_pct']}%.
⚠  FLAG   — Passes limits, but Sharpe 3.4 on 18 trades: likely over-fit. Verify out-of-sample.
```

*Simulated portfolio only. Not investment advice. Human approval required before any real-money action.*
"""

    scan = res["scan"]
    watch = "\n".join(res.get("watchlist", [])) or "_(empty)_"
    ticker_md = f"""# Ticker Under Research

> Generated from `config/preferences.json` at {stamp}. Edit through the System Preferences UI —
> hand edits here are overwritten on the next sync.
> One primary ticker moves through stages 2–10 at a time.

## Primary

```
TICKER: {res['primary_ticker']}
```

## Watchlist

Tickers the Scanner should also consider. The pipeline researches them one at a time.

```
{watch}
```

## Scan criteria

What the Market Scanner looks for:

- Relative volume above **{scan['min_rel_volume']}×** the 20-day average
- Price move of **±{scan['min_pct_move']}%** or more on the day
- {'New 52-week high or low' if scan['include_52w_extremes'] else '52-week extremes not required'}
- Universe: **{scan['universe']}**
- Minimum average daily dollar volume: **${scan['min_avg_dollar_volume']:,}**
- Exclude: tickers with earnings inside **{scan['exclude_earnings_within_days']}** days (event risk, not signal)
- Shortlist capped at **{scan['max_shortlist']}**

---
*Research only. All downstream positions are simulated.*
"""

    with open(os.path.join(ROOT, "risk-rules.md"), "w") as fh:
        fh.write(risk_md)
    with open(os.path.join(ROOT, "ticker.md"), "w") as fh:
        fh.write(ticker_md)


# ── dotted-path access ─────────────────────────────────────────────────────

def get_path(p: dict, path: str):
    cur = p
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(path)
        cur = cur[part]
    return cur


def set_path(p: dict, path: str, value) -> dict:
    parts = path.split(".")
    if parts[0] == LOCKED_SECTION:
        raise ValueError(f"{path} is a guardrail and cannot be changed (GUARDRAILS.md)")
    cur = p
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value
    return p


def _coerce(raw: str):
    low = raw.strip().lower()
    if low in {"true", "false"}:
        return low == "true"
    if low == "null":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


# ── cli ────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]

    if cmd == "show":
        print(json.dumps(load(), indent=2))
    elif cmd == "get":
        if not args:
            print("usage: prefs.py get <dotted.path>", file=sys.stderr)
            return 2
        try:
            print(json.dumps(get_path(load(), args[0]), indent=2))
        except KeyError:
            print(f"no such preference: {args[0]}", file=sys.stderr)
            return 1
    elif cmd == "set":
        if len(args) < 2:
            print("usage: prefs.py set <dotted.path> <value>", file=sys.stderr)
            return 2
        try:
            save(set_path(load(), args[0], _coerce(args[1])))
        except (ValueError, KeyError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"{args[0]} = {_coerce(args[1])!r}  → config/preferences.json (markdown re-synced)")
    elif cmd == "sync":
        sync_markdown(load())
        print("risk-rules.md and ticker.md regenerated from preferences")
    elif cmd == "validate":
        problems = validate(load())
        if problems:
            print("INVALID:")
            for x in problems:
                print("  -", x)
            return 1
        print("preferences valid")
    elif cmd == "reset":
        d = load_defaults()
        save(d, updated_by="reset")
        print("preferences reset to defaults")
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
