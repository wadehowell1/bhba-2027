# Risk Rules

The Risk Manager enforces these. It **rejects** any idea that breaks one and says which.

> Generated from `config/preferences.json` at 2026-08-26 11:06 UTC. Edit through the System Preferences UI
> (`python3 tools/serve_ui.py`) — hand edits here are overwritten on the next sync.
> All positions and limits are **SIMULATED**.

---

## Position sizing

| Rule | Limit |
|---|---|
| Max single position | **20%** of simulated portfolio |
| Max new position at entry | **15%** |
| Minimum position (avoid dust) | **2%** |

## Portfolio exposure

| Rule | Limit |
|---|---|
| Minimum cash buffer | **10%** |
| Max single-sector exposure | **35%** |
| Max correlated cluster (ρ > 0.7) | **40%** |
| Max simultaneous positions | **12** |

## Per-idea requirements

Every idea must have **all** of these or it is rejected:

- A written **entry** rule
- A written **exit** rule (target)
- A **stop** level
- A risk/reward ratio of at least **2.0:1**
- A stated holding-period assumption

## Drawdown

| Rule | Limit |
|---|---|
| Max simulated portfolio drawdown | **20%** — breach halts new positions |
| Max acceptable backtest max-DD for a strategy | **25%** |
| Per-position stop distance | **8%** default |

## Backtest quality gates

An idea backed by a backtest that fails these is flagged, not accepted at face value:

- Minimum **30 trades** in the sample — fewer is an anecdote
- Minimum sample period **3 years**
- Sharpe above **3.0** is treated as an over-fitting red flag, not a strength
- Must be checked on a held-back **30%** out-of-sample slice

---

## How the Risk Manager reports

```
✅ PASS   — 12% position, 2.4:1 R/R, stop at $x, sector tech 28% (under 35% cap).
❌ REJECT — 25% position breaks the 20% single-position cap. Resize to ≤20%.
⚠  FLAG   — Passes limits, but Sharpe 3.4 on 18 trades: likely over-fit. Verify out-of-sample.
```

*Simulated portfolio only. Not investment advice. Human approval required before any real-money action.*
