# fund/ — shared memory

The fund's brain. One file per agent. Each agent **reads the files it needs and writes only its
own**. Files persist between runs, so the fund remembers.

| File | Written by | Stage |
|---|---|---|
| `1-scan.md` | Market Scanner | 1 |
| `2-news.md` | News Analyst | 2 |
| `3-fundamentals.md` | Fundamental Analyst | 3 |
| `4-technicals.md` | Technical Analyst | 4 |
| `5-quant.md` | Quant Agent | 5 |
| `6-bull.md` | Bull Analyst | 6 |
| `7-bear.md` | Bear Analyst | 7 |
| `8-risk.md` | Risk Manager | 8 |
| `9-portfolio.md` | Portfolio Manager | 9 |
| `10-memo.md` | Fund Manager | 10 — **read this one** |

Data flows down: Scanner → News / Fundamentals / Technicals → Quant → Bull ⟷ Bear → Risk →
Portfolio → Fund Manager.

The `*.md` outputs are git-ignored — they are run artifacts containing fetched market data, and
they are regenerated each run. `9-portfolio.md` is the exception worth backing up yourself if you
want to keep a simulated book across machines.

**Everything in these files is SIMULATED research. Not investment advice.**
