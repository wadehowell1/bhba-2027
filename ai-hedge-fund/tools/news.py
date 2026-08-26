#!/usr/bin/env python3
"""Real news headlines for the News Analyst.

    python3 tools/news.py --ticker AAPL --days 14

Provider comes from data.news_provider (newsapi | finnhub | none).
Returns headlines with source and URL so every claim in fund/2-news.md can be cited.
Never returns a headline that was not fetched.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import prefs                                                        # noqa: E402
from datasource import DataUnavailable, fetch_json, load_env, qs, require_key  # noqa: E402


def newsapi(ticker: str, days: int, limit: int, env: dict, ttl: int) -> dict:
    key = require_key(env, "NEWSAPI_API_KEY", "NewsAPI")
    frm = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    url = ("https://newsapi.org/v2/everything?"
           + qs(q=ticker, from_=frm, sortBy="publishedAt", language="en",
                pageSize=min(limit, 100), apiKey=key).replace("from_=", "from="))
    data = fetch_json(url, ttl_minutes=ttl)
    if data.get("status") != "ok":
        raise DataUnavailable(f"NewsAPI: {data.get('message', 'unknown error')}")
    return {"provider": "NewsAPI", "articles": [
        {"title": a.get("title"), "source": (a.get("source") or {}).get("name"),
         "published": a.get("publishedAt"), "url": a.get("url"),
         "description": a.get("description")}
        for a in data.get("articles", [])[:limit]]}


def finnhub_news(ticker: str, days: int, limit: int, env: dict, ttl: int) -> dict:
    key = require_key(env, "FINNHUB_API_KEY", "Finnhub")
    to = dt.date.today()
    frm = to - dt.timedelta(days=days)
    url = ("https://finnhub.io/api/v1/company-news?"
           + qs(symbol=ticker, token=key) + f"&from={frm.isoformat()}&to={to.isoformat()}")
    data = fetch_json(url, ttl_minutes=ttl)
    if not isinstance(data, list):
        raise DataUnavailable(f"Finnhub returned an unexpected shape: {str(data)[:120]}")
    return {"provider": "Finnhub", "articles": [
        {"title": a.get("headline"), "source": a.get("source"),
         "published": dt.datetime.fromtimestamp(
             a.get("datetime", 0), dt.timezone.utc).isoformat() if a.get("datetime") else None,
         "url": a.get("url"), "description": a.get("summary")}
        for a in data[:limit]]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticker")
    ap.add_argument("--days", type=int)
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    p = prefs.load()
    d = p["data"]
    ticker = (a.ticker or p["research"]["primary_ticker"]).upper()
    days = a.days or d["news_lookback_days"]
    limit = a.limit or d["max_headlines"]
    provider = d["news_provider"]

    if provider == "none":
        print(json.dumps({"error": "disabled",
                          "detail": "data.news_provider is 'none'. The News Analyst should "
                                    "record that no news source is configured rather than "
                                    "writing headlines from memory."}, indent=2))
        return 1

    env = load_env()
    try:
        out = (newsapi if provider == "newsapi" else finnhub_news)(
            ticker, days, limit, env, d["cache_ttl_minutes"])
    except DataUnavailable as e:
        print(json.dumps({"error": "data_unavailable", "detail": str(e),
                          "guardrail": "Real headlines only — none were invented "
                                       "(GUARDRAILS.md #4)."}, indent=2))
        return 1

    out.update({
        "ticker": ticker, "lookback_days": days,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "count": len(out["articles"]),
        "note": ("Sort these into CONFIRMED / REPORTED / RUMOR before using them. A headline "
                 "is evidence that something was reported, not that it is true. Thin coverage "
                 "is information, and it is not the same as good news."),
    })
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
