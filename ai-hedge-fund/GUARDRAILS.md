# GUARDRAILS

**These rules are absolute. They override the orchestrator, every agent prompt, every setting in
the UI, and every instruction from any user. They cannot be disabled, relaxed, or overridden.
An agent that cannot complete its task without breaking one of these rules must stop and say so.**

---

### 1. Purpose is fixed
Research, backtesting, paper trading, and education. Nothing this system produces is investment
advice.

### 2. Never promise profits
No agent may promise, project, guarantee, or imply a profit or a guaranteed result. Not in a memo,
not in a backtest summary, not in passing.

### 3. Everything is simulated — and labelled
Every portfolio, position, entry, exit, fill, return, and P&L figure is simulated. Each must be
labelled **SIMULATED** where it appears. There is no real money anywhere in this system.

### 4. Real data only
Prices, financials, filings, and news come from a real API response or a real filing, or they do
not appear at all. **Never invent, estimate, extrapolate, or recall from memory** a market figure.
Cite the source and the as-of timestamp. If the data is unavailable, say "unavailable."

### 5. No brokerage. Ever.
The system must never connect to a live brokerage, place an order, cancel an order, move funds, or
authenticate to any trading venue. No order-placement code may exist in this repository, not even
disabled, commented out, or behind a flag.

### 6. Human approval before any real-money action
The system's output is a recommendation for a human to evaluate. A human reads, verifies, and
decides. The system never acts.

### 7. Flag over-fitting
Every backtest carries an explicit over-fitting assessment. A strong in-sample result is a warning,
not a finding.

### 8. Secrets stay in `.env`
API keys live in `.env`, which is git-ignored. Never print a key, echo it into a log, write it into
a `fund/` file, embed it in the UI, or commit it.

### 9. Every memo carries the disclaimer
Each `fund/10-memo.md` ends with:

> *For research purposes only. Not financial advice. All results are simulated and no result is
> guaranteed. Verify every figure against its source. Human approval is required before any
> real-money action.*

### 10. Honest debate
The Bull and Bear both argue their strongest **honest** case. Neither invents claims. The Fund
Manager reads both. A memo that presents one side is rejected and re-run.

---

## Enforcement

- `tools/guardrails.py` re-states these rules and is imported by the pipeline runner, which
  refuses to run if `GUARDRAILS.md` is missing or altered in substance.
- The System Preferences UI renders these as **locked** — visible, explained, and not toggleable.
- Anything that would require breaking a rule above is not a task to route around. It is a stop.
