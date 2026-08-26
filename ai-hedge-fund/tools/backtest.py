#!/usr/bin/env python3
"""Backtest engine — SIMULATED results only. Standard library, no numpy.

    python3 tools/backtest.py --ticker AAPL --rules rules.json
    python3 tools/backtest.py --ticker AAPL --rules rules.json --years 5
    python3 tools/backtest.py --selftest          # run on synthetic series

rules.json shape:

    {
      "entry":  {"above_ma": 200, "min_rel_volume": 2.0, "rsi_below": 70},
      "exit":   {"target_pct": 15, "max_hold_days": 40, "below_ma": 50},
      "stop":   {"pct": 8},
      "size_pct": 12
    }

Every figure this produces is SIMULATED. It excludes real fill quality, borrow cost,
gaps through stops, and liquidity. Real execution is worse than this model.
Commission and slippage from preferences are applied to both sides of every trade.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import prefs                                              # noqa: E402
import market_data as md                                  # noqa: E402
from datasource import DataUnavailable                    # noqa: E402

TRADING_DAYS = 252


# ── indicator series ───────────────────────────────────────────────────────

def sma_series(closes: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if n <= 0 or len(closes) < n:
        return out
    run = sum(closes[:n])
    out[n - 1] = run / n
    for i in range(n, len(closes)):
        run += closes[i] - closes[i - n]
        out[i] = run / n
    return out


def rsi_series(closes: list[float], n: int = 14) -> list[float | None]:
    """Wilder's RSI."""
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= n:
        return out
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0.0); losses += max(-d, 0.0)
    ag, al = gains / n, losses / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (n - 1) + max(d, 0.0)) / n
        al = (al * (n - 1) + max(-d, 0.0)) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def relvol_series(vols: list[float], n: int = 20) -> list[float | None]:
    out: list[float | None] = [None] * len(vols)
    for i in range(n, len(vols)):
        window = vols[i - n:i]
        avg = sum(window) / n
        out[i] = (vols[i] / avg) if avg else None
    return out


# ── the simulation ─────────────────────────────────────────────────────────

def run(bars: list[dict], rules: dict, cfg: dict) -> dict:
    """Long-only, one position at a time, next-open execution.

    Signals are evaluated on bar i's close and executed at bar i+1's open. This
    avoids the single most common backtest error — filling at a price that could
    not have been known when the signal fired.
    """
    closes = [b["c"] for b in bars]
    vols = [float(b["v"] or 0) for b in bars]
    entry, exit_r, stop = rules.get("entry", {}), rules.get("exit", {}), rules.get("stop", {})

    ma_entry = sma_series(closes, int(entry["above_ma"])) if entry.get("above_ma") else None
    ma_exit = sma_series(closes, int(exit_r["below_ma"])) if exit_r.get("below_ma") else None
    rsis = rsi_series(closes) if ("rsi_below" in entry or "rsi_above" in entry) else None
    rvs = relvol_series(vols) if entry.get("min_rel_volume") else None

    cost_bps = (cfg["commission_bps"] + cfg["slippage_bps"]) / 10_000.0

    def entry_ok(i: int) -> bool:
        if ma_entry is not None:
            if ma_entry[i] is None or closes[i] <= ma_entry[i]:
                return False
        if entry.get("below_ma"):
            m = sma_series(closes, int(entry["below_ma"]))[i]
            if m is None or closes[i] >= m:
                return False
        if rvs is not None:
            if rvs[i] is None or rvs[i] < entry["min_rel_volume"]:
                return False
        if rsis is not None:
            r = rsis[i]
            if r is None:
                return False
            if "rsi_below" in entry and r >= entry["rsi_below"]:
                return False
            if "rsi_above" in entry and r <= entry["rsi_above"]:
                return False
        if entry.get("min_pct_move") is not None and i > 0:
            chg = (closes[i] - closes[i - 1]) / closes[i - 1] * 100
            if chg < entry["min_pct_move"]:
                return False
        return True

    trades = []
    pos = None
    for i in range(len(bars) - 1):
        nxt = bars[i + 1]
        if pos is None:
            if entry_ok(i):
                fill = nxt["o"] or nxt["c"]
                pos = {"entry_date": nxt["date"], "entry": fill, "entry_idx": i + 1,
                       "stop": fill * (1 - stop["pct"] / 100) if stop.get("pct") else None,
                       "target": fill * (1 + exit_r["target_pct"] / 100)
                                 if exit_r.get("target_pct") else None}
            continue

        # Position open: check intrabar stop/target on THIS bar, else exit rules at next open.
        b = bars[i]
        held = i - pos["entry_idx"]
        reason = px = None

        if pos["stop"] is not None and b["l"] is not None and b["l"] <= pos["stop"]:
            # Conservative: assume the stop fills at the stop, or worse if the bar
            # gapped below it. Gaps are where backtests flatter reality most.
            px = min(pos["stop"], b["o"] if b["o"] is not None else pos["stop"])
            reason = "stop"
        elif pos["target"] is not None and b["h"] is not None and b["h"] >= pos["target"]:
            px = max(pos["target"], b["o"] if b["o"] is not None else pos["target"])
            reason = "target"
        elif exit_r.get("max_hold_days") and held >= exit_r["max_hold_days"]:
            px = nxt["o"] or nxt["c"]; reason = "time"
        elif ma_exit is not None and ma_exit[i] is not None and closes[i] < ma_exit[i]:
            px = nxt["o"] or nxt["c"]; reason = "ma_exit"

        if reason:
            gross = (px - pos["entry"]) / pos["entry"]
            net = gross - 2 * cost_bps          # both sides
            trades.append({
                "entry_date": pos["entry_date"], "exit_date": b["date"] if reason in
                ("stop", "target") else nxt["date"],
                "entry": round(pos["entry"], 4), "exit": round(px, 4),
                "return_pct": round(net * 100, 3), "gross_pct": round(gross * 100, 3),
                "days_held": held, "reason": reason,
            })
            pos = None

    if pos is not None:
        last = bars[-1]
        gross = (last["c"] - pos["entry"]) / pos["entry"]
        trades.append({
            "entry_date": pos["entry_date"], "exit_date": last["date"],
            "entry": round(pos["entry"], 4), "exit": round(last["c"], 4),
            "return_pct": round((gross - 2 * cost_bps) * 100, 3),
            "gross_pct": round(gross * 100, 3),
            "days_held": len(bars) - 1 - pos["entry_idx"], "reason": "open_at_end",
        })

    return {"trades": trades, "bars": len(bars),
            "period": {"from": bars[0]["date"], "to": bars[-1]["date"]}}


# ── statistics ─────────────────────────────────────────────────────────────

def stats(trades: list[dict], cfg: dict, size_pct: float, period: dict) -> dict:
    if not trades:
        return {"trades": 0, "note": "No trades triggered. The rules never fired over this "
                                     "sample — that is a result, not an error."}
    rets = [t["return_pct"] / 100 for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]

    # Equity curve at the configured position size; the rest of the book sits in cash.
    frac = size_pct / 100.0
    equity, peak, max_dd = 1.0, 1.0, 0.0
    curve = [1.0]
    for r in rets:
        equity *= (1 + r * frac)
        curve.append(equity)
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)

    avg = sum(rets) / len(rets)
    var = sum((r - avg) ** 2 for r in rets) / (len(rets) - 1) if len(rets) > 1 else 0.0
    sd = math.sqrt(var)

    # Annualize per-trade Sharpe by trade frequency. Stated as an approximation,
    # because it is one: it assumes trades are independent and identically sized.
    days = sum(t["days_held"] for t in trades) or 1
    avg_hold = days / len(trades)
    trades_per_year = TRADING_DAYS / max(avg_hold, 1)
    sharpe = (avg / sd * math.sqrt(trades_per_year)) if sd > 0 else None

    gross_win = sum(wins) or 0.0
    gross_loss = abs(sum(losses)) or 0.0

    by_year: dict[str, list[float]] = {}
    for t in trades:
        by_year.setdefault(t["exit_date"][:4], []).append(t["return_pct"])

    return {
        "trades": len(trades),
        "win_rate_pct": round(len(wins) / len(rets) * 100, 1),
        "avg_win_pct": round(sum(wins) / len(wins) * 100, 2) if wins else 0.0,
        "avg_loss_pct": round(sum(losses) / len(losses) * 100, 2) if losses else 0.0,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else None,
        "total_return_pct": round((equity - 1) * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe": round(sharpe, 2) if sharpe is not None else None,
        "avg_hold_days": round(avg_hold, 1),
        "exit_reasons": {r: sum(1 for t in trades if t["reason"] == r)
                         for r in {t["reason"] for t in trades}},
        "by_year": {y: {"trades": len(v), "total_pct": round(sum(v), 2)}
                    for y, v in sorted(by_year.items())},
        "position_size_pct": size_pct,
        "period": period,
        "costs_applied": f"{cfg['commission_bps']}bps commission + "
                         f"{cfg['slippage_bps']}bps slippage, both sides",
        "sharpe_note": "Annualized from per-trade returns by trade frequency; an approximation "
                       "that assumes independent, equally sized trades.",
    }


def overfit_assessment(s: dict, oos: dict | None, cfg: dict) -> dict:
    """The mandatory over-fitting section. A strong result is a warning."""
    flags = []
    if s.get("trades", 0) < cfg["min_trades"]:
        flags.append(f"only {s.get('trades', 0)} trades vs a {cfg['min_trades']} minimum — "
                     f"too few to distinguish skill from luck")
    sh = s.get("sharpe")
    if sh is not None and sh > cfg["overfit_sharpe_threshold"]:
        flags.append(f"Sharpe {sh} exceeds the {cfg['overfit_sharpe_threshold']} red-flag "
                     f"threshold — treat as a warning, not a strength")
    if s.get("win_rate_pct", 0) > 75:
        flags.append(f"win rate {s['win_rate_pct']}% is implausibly high for a simple rule set")

    years = 0.0
    p = s.get("period") or {}
    if p.get("from") and p.get("to"):
        try:
            years = (dt.date.fromisoformat(p["to"]) - dt.date.fromisoformat(p["from"])).days / 365.25
        except ValueError:
            years = 0.0
    if years and years < cfg["min_sample_years"]:
        flags.append(f"sample is {years:.1f}y vs a {cfg['min_sample_years']}y minimum")

    if oos and oos.get("trades"):
        gap = (s.get("total_return_pct", 0) or 0) - (oos.get("total_return_pct", 0) or 0)
        if oos["trades"] < 5:
            flags.append(f"out-of-sample slice has only {oos['trades']} trades — "
                         f"too few to validate anything")
        elif gap > 20:
            flags.append(f"in-sample return exceeds out-of-sample by {gap:.1f}pp — "
                         f"the classic over-fit signature")
    else:
        flags.append("no usable out-of-sample result — the strategy is unvalidated")

    by_year = s.get("by_year") or {}
    if len(by_year) > 1:
        tot = sum(v["total_pct"] for v in by_year.values())
        best = max(by_year.values(), key=lambda v: v["total_pct"])["total_pct"]
        if tot > 0 and best / tot > 0.7:
            flags.append("over 70% of the total return comes from a single year — "
                         "that is one lucky year, not a strategy")

    verdict = ("LIKELY OVER-FIT" if len(flags) >= 3
               else "POSSIBLY OVER-FIT" if flags else "REASONABLE")
    return {
        "verdict": verdict,
        "flags": flags or ["No structural over-fit signal in these checks."],
        "caveat": ("These checks cannot see how many rule variants were tried before this one. "
                   "That number is the single biggest over-fitting risk and only the analyst "
                   "knows it — state it explicitly in fund/5-quant.md."),
    }


def selftest() -> int:
    """Run the engine against synthetic series with known properties."""
    import random
    random.seed(7)
    ok = True

    def synth(n, drift, vol, start=100.0):
        bars, px = [], start
        d = dt.date(2018, 1, 1)
        for _ in range(n):
            px *= math.exp(random.gauss(drift, vol))
            hi, lo = px * (1 + abs(random.gauss(0, vol))), px * (1 - abs(random.gauss(0, vol)))
            bars.append({"date": d.isoformat(), "o": px * (1 + random.gauss(0, vol / 3)),
                         "h": max(hi, px), "l": min(lo, px), "c": px,
                         "v": random.randint(1_000_000, 5_000_000)})
            d += dt.timedelta(days=1)
        return bars

    cfg = {"commission_bps": 5, "slippage_bps": 5, "min_trades": 30,
           "min_sample_years": 3, "overfit_sharpe_threshold": 3.0}

    # 1. Indicator correctness against hand-computed values
    assert sma_series([1, 2, 3, 4, 5], 3)[-1] == 4.0, "SMA wrong"
    assert sma_series([1, 2], 3)[-1] is None, "SMA should be None before warmup"
    r = rsi_series([float(i) for i in range(1, 40)])   # strictly rising → RSI 100
    assert r[-1] == 100.0, f"RSI on a monotonic rise should be 100, got {r[-1]}"
    print("  ✓ indicators (SMA warmup, monotonic RSI)")

    # 2. A rule that can never fire produces zero trades, not an error
    bars = synth(600, 0.0003, 0.012)
    res = run(bars, {"entry": {"rsi_above": 99.9}, "exit": {"max_hold_days": 5}}, cfg)
    assert res["trades"] == [], "impossible entry rule should produce no trades"
    print("  ✓ impossible rule → 0 trades, no crash")

    # 3. Stop is always respected: no trade may lose much more than the stop
    res = run(bars, {"entry": {"above_ma": 20}, "exit": {"max_hold_days": 30},
                     "stop": {"pct": 8}}, cfg)
    worst = min((t["gross_pct"] for t in res["trades"]), default=0)
    assert worst >= -25, f"stop breached implausibly: worst gross {worst}%"
    print(f"  ✓ stop respected ({len(res['trades'])} trades, worst gross {worst:.1f}%)")

    # 4. Costs reduce returns
    free = run(bars, {"entry": {"above_ma": 20}, "exit": {"max_hold_days": 30}},
               {"commission_bps": 0, "slippage_bps": 0})
    paid = run(bars, {"entry": {"above_ma": 20}, "exit": {"max_hold_days": 30}},
               {"commission_bps": 50, "slippage_bps": 50})
    if free["trades"] and paid["trades"]:
        assert paid["trades"][0]["return_pct"] < free["trades"][0]["return_pct"], \
            "costs must reduce net return"
        print("  ✓ commission + slippage reduce net return")

    # 5. Stats sanity + drawdown is non-negative and bounded
    s = stats(res["trades"], cfg, 12, res["period"])
    assert 0 <= s["max_drawdown_pct"] <= 100, s["max_drawdown_pct"]
    assert 0 <= s["win_rate_pct"] <= 100
    print(f"  ✓ stats bounded (win {s['win_rate_pct']}%, maxDD {s['max_drawdown_pct']}%, "
          f"Sharpe {s['sharpe']})")

    # 6. Over-fit detector fires on a tiny, unvalidated sample
    tiny = stats(res["trades"][:4], cfg, 12, res["period"])
    oa = overfit_assessment(tiny, None, cfg)
    assert oa["verdict"] in ("LIKELY OVER-FIT", "POSSIBLY OVER-FIT"), oa
    assert any("trades" in f for f in oa["flags"])
    print(f"  ✓ over-fit detector on 4 trades → {oa['verdict']}")

    # 7. Empty-trade path returns a clean result
    e = stats([], cfg, 12, {"from": "2020-01-01", "to": "2024-01-01"})
    assert e["trades"] == 0 and "note" in e
    print("  ✓ zero-trade stats handled cleanly")

    print("\nAll self-tests passed." if ok else "FAILURES")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticker")
    ap.add_argument("--rules", help="path to rules.json")
    ap.add_argument("--years", type=float)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.rules:
        print("--rules is required (or use --selftest). See the docstring for the shape.",
              file=sys.stderr)
        return 2

    p = prefs.load()
    cfg = p["backtest"]
    ticker = (a.ticker or p["research"]["primary_ticker"]).upper()
    years = a.years or cfg["lookback_years"]

    with open(a.rules) as fh:
        rules = json.load(fh)

    try:
        hist = md.history(ticker, years, p["data"]["cache_ttl_minutes"])
    except DataUnavailable as e:
        print(json.dumps({"error": "data_unavailable", "detail": str(e),
                          "guardrail": "No backtest was run and no result was invented "
                                       "(GUARDRAILS.md #4)."}, indent=2))
        return 1

    bars = hist["bars"]
    size = rules.get("size_pct", 10)

    split = int(len(bars) * (1 - cfg["out_of_sample_pct"] / 100.0))
    in_bars, oos_bars = bars[:split], bars[split:]

    full = run(bars, rules, cfg)
    full_stats = stats(full["trades"], cfg, size, full["period"])
    ins = run(in_bars, rules, cfg) if len(in_bars) > 250 else {"trades": [], "period": full["period"]}
    ins_stats = stats(ins["trades"], cfg, size, ins.get("period", full["period"]))
    oos = run(oos_bars, rules, cfg) if len(oos_bars) > 60 else {"trades": [], "period": full["period"]}
    oos_stats = stats(oos["trades"], cfg, size, oos.get("period", full["period"]))

    print(json.dumps({
        "SIMULATED": True,
        "ticker": ticker,
        "source": hist["source"],
        "as_of": hist["as_of"],
        "rules": rules,
        "full_sample": full_stats,
        "in_sample": ins_stats,
        "out_of_sample": oos_stats,
        "overfitting": overfit_assessment(full_stats, oos_stats, cfg),
        "trades": full["trades"],
        "disclaimer": ("SIMULATED results. Excludes real fill quality, borrow cost, gaps "
                       "through stops, liquidity limits, and taxes. Real execution is worse. "
                       "Not investment advice; no result is guaranteed."),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
