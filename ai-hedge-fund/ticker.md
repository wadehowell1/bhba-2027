# Ticker Under Research

> Set through the System Preferences UI, or edit the block below.
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
- Price move of **±5%** or more on the day
- New 52-week high or low
- Universe: **S&P 500**
- Minimum average daily dollar volume: **$10M**
- Exclude: tickers with earnings inside **2** days (event risk, not signal)

---
*Research only. All downstream positions are simulated.*
