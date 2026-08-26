# Ticker Under Research

> Generated from `config/preferences.json` at 2026-08-26 11:06 UTC. Edit through the System Preferences UI —
> hand edits here are overwritten on the next sync.
> One primary ticker moves through stages 2–10 at a time.

## Primary

```
TICKER: AAPL
```

## Watchlist

Tickers the Scanner should also consider. The pipeline researches them one at a time.

```
MSFT
NVDA
GOOGL
```

## Scan criteria

What the Market Scanner looks for:

- Relative volume above **2.0×** the 20-day average
- Price move of **±5.0%** or more on the day
- New 52-week high or low
- Universe: **sp500**
- Minimum average daily dollar volume: **$10,000,000**
- Exclude: tickers with earnings inside **2** days (event risk, not signal)
- Shortlist capped at **10**

---
*Research only. All downstream positions are simulated.*
