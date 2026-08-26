#!/usr/bin/env python3
"""Real market data for the pipeline. Standard library only.

    python3 tools/market_data.py quote      --ticker AAPL
    python3 tools/market_data.py history    --ticker AAPL --years 5
    python3 tools/market_data.py technicals --ticker AAPL
    python3 tools/market_data.py financials --ticker AAPL
    python3 tools/market_data.py earnings   --ticker AAPL
    python3 tools/market_data.py scan       --universe sp500 --limit 10

Provider comes from data.market_provider in preferences (yfinance | alphavantage |
fmp | finnhub). "yfinance" uses Yahoo's public chart endpoint directly and needs no key.

If data cannot be fetched this exits non-zero with an explanation. It never
returns an estimated or remembered figure — see GUARDRAILS.md #4.
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import prefs                                          # noqa: E402
from datasource import DataUnavailable, fetch_json, load_env, qs, require_key  # noqa: E402

YAHOO = "https://query1.finance.yahoo.com"


# ── price history ──────────────────────────────────────────────────────────

def history(ticker: str, years: float, ttl: int) -> dict:
    """Daily OHLCV. Returns {'ticker','currency','as_of','bars':[{date,o,h,l,c,v}]}."""
    rng = f"{max(1, int(round(years)))}y"
    url = f"{YAHOO}/v8/finance/chart/{ticker}?{qs(range=rng, interval='1d')}"
    data = fetch_json(url, ttl_minutes=ttl)

    err = (data.get("chart") or {}).get("error")
    if err:
        raise DataUnavailable(f"{ticker}: {err.get('description') or err}")
    results = (data.get("chart") or {}).get("result") or []
    if not results:
        raise DataUnavailable(f"{ticker}: no data returned — check the symbol is valid")

    r = results[0]
    ts = r.get("timestamp") or []
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    meta = r.get("meta") or {}
    import datetime as dt

    bars = []
    for i, t in enumerate(ts):
        c = q.get("close", [None] * len(ts))[i]
        if c is None:
            continue          # holidays / halts come back as nulls; drop, never interpolate
        bars.append({
            "date": dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d"),
            "o": q.get("open",  [None] * len(ts))[i],
            "h": q.get("high",  [None] * len(ts))[i],
            "l": q.get("low",   [None] * len(ts))[i],
            "c": c,
            "v": q.get("volume", [None] * len(ts))[i] or 0,
        })
    if not bars:
        raise DataUnavailable(f"{ticker}: chart returned no usable bars")
    return {
        "ticker": ticker.upper(),
        "currency": meta.get("currency"),
        "exchange": meta.get("fullExchangeName"),
        "as_of": bars[-1]["date"],
        "source": "Yahoo Finance chart API",
        "bars": bars,
    }


def quote(ticker: str, ttl: int) -> dict:
    h = history(ticker, 1, ttl)
    bars = h["bars"]
    last, prev = bars[-1], (bars[-2] if len(bars) > 1 else bars[-1])
    chg = last["c"] - prev["c"]
    vols = [b["v"] for b in bars[-21:-1]] or [last["v"]]
    avg_vol = sum(vols) / len(vols)
    closes = [b["c"] for b in bars]
    return {
        "ticker": h["ticker"], "as_of": last["date"], "source": h["source"],
        "price": round(last["c"], 4),
        "change": round(chg, 4),
        "change_pct": round(chg / prev["c"] * 100, 2) if prev["c"] else None,
        "volume": last["v"],
        "avg_volume_20d": round(avg_vol),
        "rel_volume": round(last["v"] / avg_vol, 2) if avg_vol else None,
        "week52_high": round(max(closes), 4),
        "week52_low": round(min(closes), 4),
        "currency": h.get("currency"),
    }


# ── indicators (pure python, no numpy) ─────────────────────────────────────

def sma(vals: list[float], n: int) -> float | None:
    return sum(vals[-n:]) / n if len(vals) >= n else None


def rsi(closes: list[float], n: int = 14) -> float | None:
    if len(closes) < n + 1:
        return None
    gains = losses = 0.0
    for i in range(-n, 0):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return round(100 - 100 / (1 + rs), 2)


def atr(bars: list[dict], n: int = 14) -> float | None:
    if len(bars) < n + 1:
        return None
    trs = []
    for i in range(-n, 0):
        h, l, pc = bars[i]["h"], bars[i]["l"], bars[i - 1]["c"]
        if None in (h, l, pc):
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return round(sum(trs) / len(trs), 4) if trs else None


def technicals(ticker: str, years: float, ttl: int) -> dict:
    h = history(ticker, max(years, 2), ttl)
    bars = h["bars"]
    closes = [b["c"] for b in bars]
    last = closes[-1]
    ma50, ma200 = sma(closes, 50), sma(closes, 200)
    yr = closes[-252:] if len(closes) >= 252 else closes
    hi, lo = max(yr), min(yr)
    a = atr(bars)
    vols = [b["v"] for b in bars[-21:-1]] or [bars[-1]["v"]]
    avg_vol = sum(vols) / len(vols)

    return {
        "ticker": h["ticker"], "as_of": h["as_of"], "source": h["source"],
        "price": round(last, 4),
        "ma50": round(ma50, 4) if ma50 else None,
        "ma200": round(ma200, 4) if ma200 else None,
        "above_ma50": (last > ma50) if ma50 else None,
        "above_ma200": (last > ma200) if ma200 else None,
        "ma50_above_ma200": (ma50 > ma200) if (ma50 and ma200) else None,
        "rsi14": rsi(closes),
        "atr14": a,
        "atr_pct": round(a / last * 100, 2) if a and last else None,
        "week52_high": round(hi, 4), "week52_low": round(lo, 4),
        "pct_of_52w_range": round((last - lo) / (hi - lo) * 100, 1) if hi > lo else None,
        "rel_volume": round(bars[-1]["v"] / avg_vol, 2) if avg_vol else None,
        "bars_used": len(bars),
        "note": "Descriptive only — not a prediction. Verify against your own chart.",
    }


# ── fundamentals / earnings ────────────────────────────────────────────────

def financials(ticker: str, ttl: int, prefs_obj: dict) -> dict:
    """Financial statements. Requires a keyed provider — Yahoo's free chart
    endpoint does not serve statements."""
    env = load_env()
    provider = prefs_obj["data"]["market_provider"]

    if provider == "fmp":
        key = require_key(env, "FMP_API_KEY", "FMP")
        base = "https://financialmodelingprep.com/api/v3"
        out = {"ticker": ticker.upper(), "source": "Financial Modeling Prep"}
        for name, path in (("income", "income-statement"),
                           ("balance", "balance-sheet-statement"),
                           ("cashflow", "cash-flow-statement"),
                           ("ratios", "ratios")):
            out[name] = fetch_json(f"{base}/{path}/{ticker}?{qs(limit=8, apikey=key)}",
                                   ttl_minutes=ttl)
        return out

    if provider == "alphavantage":
        key = require_key(env, "ALPHAVANTAGE_API_KEY", "Alpha Vantage")
        base = "https://www.alphavantage.co/query"
        out = {"ticker": ticker.upper(), "source": "Alpha Vantage"}
        for name, fn in (("overview", "OVERVIEW"), ("income", "INCOME_STATEMENT"),
                         ("balance", "BALANCE_SHEET"), ("cashflow", "CASH_FLOW")):
            out[name] = fetch_json(f"{base}?{qs(function=fn, symbol=ticker, apikey=key)}",
                                   ttl_minutes=ttl)
        return out

    if provider == "finnhub":
        key = require_key(env, "FINNHUB_API_KEY", "Finnhub")
        base = "https://finnhub.io/api/v1"
        return {
            "ticker": ticker.upper(), "source": "Finnhub",
            "metrics": fetch_json(
                f"{base}/stock/metric?{qs(symbol=ticker, metric='all', token=key)}",
                ttl_minutes=ttl),
            "financials": fetch_json(
                f"{base}/stock/financials-reported?{qs(symbol=ticker, token=key)}",
                ttl_minutes=ttl),
        }

    raise DataUnavailable(
        "data.market_provider is 'yfinance', whose free chart endpoint does not serve "
        "financial statements. Either switch data.market_provider to fmp / alphavantage / "
        "finnhub in the Preferences UI and add that key to .env, or take the fundamentals "
        "from SEC filings via tools/sec_edgar.py. Nothing was estimated.")


def earnings(ticker: str, ttl: int, prefs_obj: dict) -> dict:
    env = load_env()
    provider = prefs_obj["data"]["market_provider"]
    if provider == "finnhub":
        key = require_key(env, "FINNHUB_API_KEY", "Finnhub")
        return {"ticker": ticker.upper(), "source": "Finnhub",
                "calendar": fetch_json(
                    f"https://finnhub.io/api/v1/calendar/earnings?{qs(symbol=ticker, token=key)}",
                    ttl_minutes=ttl)}
    if provider == "fmp":
        key = require_key(env, "FMP_API_KEY", "FMP")
        return {"ticker": ticker.upper(), "source": "Financial Modeling Prep",
                "calendar": fetch_json(
                    "https://financialmodelingprep.com/api/v3/historical/earning_calendar/"
                    f"{ticker}?{qs(limit=8, apikey=key)}", ttl_minutes=ttl)}
    raise DataUnavailable(
        f"earnings dates are not available from provider '{provider}'. Switch to finnhub or "
        f"fmp in the Preferences UI, or read the date from the latest 8-K via sec_edgar.py. "
        f"Nothing was estimated.")


# ── scan ───────────────────────────────────────────────────────────────────

UNIVERSES = {
    # A starter universe. Replace with your own list, or point at a keyed
    # provider's screener endpoint for full coverage.
    "sp500": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "AVGO",
              "JPM", "LLY", "V", "XOM", "UNH", "MA", "COST", "HD", "PG", "JNJ", "ABBV",
              "WMT", "NFLX", "CRM", "BAC", "AMD", "KO", "PEP", "TMO", "ADBE", "CSCO"],
    "megacap": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"],
    "watchlist": [],
}


def scan(universe: str, limit: int, ttl: int, prefs_obj: dict) -> dict:
    crit = prefs_obj["research"]["scan"]
    syms = UNIVERSES.get(universe)
    if syms is None:
        raise DataUnavailable(
            f"unknown universe '{universe}'. Known: {', '.join(UNIVERSES)}")
    if universe == "watchlist":
        syms = ([prefs_obj["research"]["primary_ticker"]]
                + list(prefs_obj["research"].get("watchlist", [])))
    if not syms:
        raise DataUnavailable(f"universe '{universe}' is empty")

    hits, failures = [], []
    for s in syms:
        try:
            q = quote(s, ttl)
        except DataUnavailable as e:
            failures.append({"ticker": s, "reason": str(e)})
            continue
        reasons = []
        if q["rel_volume"] and q["rel_volume"] >= crit["min_rel_volume"]:
            reasons.append(f"rel vol {q['rel_volume']}× 20d avg")
        if q["change_pct"] is not None and abs(q["change_pct"]) >= crit["min_pct_move"]:
            reasons.append(f"{q['change_pct']:+.1f}% on the day")
        if crit["include_52w_extremes"]:
            if q["price"] >= q["week52_high"] * 0.999:
                reasons.append("at/near 52-week high")
            elif q["price"] <= q["week52_low"] * 1.001:
                reasons.append("at/near 52-week low")
        dollar_vol = q["price"] * (q["avg_volume_20d"] or 0)
        if reasons and dollar_vol >= crit["min_avg_dollar_volume"]:
            hits.append({**q, "why": "; ".join(reasons),
                         "avg_dollar_volume": round(dollar_vol)})

    hits.sort(key=lambda h: (h["rel_volume"] or 0), reverse=True)
    return {
        "universe": universe,
        "criteria": crit,
        "scanned": len(syms),
        "matched": len(hits),
        "results": hits[:limit],
        "failures": failures,
        "note": ("An empty result set means the scan was quiet — that is a finding, "
                 "not a failure. Do not pad the shortlist."),
    }


# ── cli ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["quote", "history", "technicals",
                                        "financials", "earnings", "scan"])
    ap.add_argument("--ticker")
    ap.add_argument("--years", type=float)
    ap.add_argument("--universe")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    p = prefs.load()
    ttl = p["data"]["cache_ttl_minutes"]
    ticker = (a.ticker or p["research"]["primary_ticker"]).upper()
    years = a.years or p["data"]["price_history_years"]

    try:
        if a.command == "quote":
            out = quote(ticker, ttl)
        elif a.command == "history":
            out = history(ticker, years, ttl)
        elif a.command == "technicals":
            out = technicals(ticker, years, ttl)
        elif a.command == "financials":
            out = financials(ticker, ttl, p)
        elif a.command == "earnings":
            out = earnings(ticker, ttl, p)
        else:
            out = scan(a.universe or p["research"]["scan"]["universe"],
                       a.limit or p["research"]["scan"]["max_shortlist"], ttl, p)
    except DataUnavailable as e:
        print(json.dumps({"error": "data_unavailable", "detail": str(e),
                          "guardrail": "Real data only — nothing was estimated or invented "
                                       "to fill this gap (GUARDRAILS.md #4)."}, indent=2))
        return 1

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
