# AI Hedge Fund — multi-agent research system

Ten specialized agents pass one stock idea down a research pipeline and finish with a
fund-manager memo for **you** to read and verify.

```
SCAN → RESEARCH → ANALYZE → DEBATE → BACKTEST → RISK → ALLOCATE → REVIEW
```

> **Research, backtesting, paper trading, and education only.** This is not investment advice.
> It does not promise profits. Every portfolio, trade, and result is **simulated**. The system
> never places real trades and never connects to a live brokerage. Human approval is required
> before any real-money action. Investing carries real risk of loss — verify everything and
> consult a licensed professional.

Built from the guide *Build Your Own AI Hedge Fund With Claude Code* (@seb.ai). The full
requirement, including the original Master Build Prompt, is in [`docs/SPEC.md`](docs/SPEC.md).

---

## Quick start

```bash
cd ai-hedge-fund

# 1. Credentials (optional to start — Yahoo prices need no key)
cp .env.example .env && $EDITOR .env

# 2. Set your preferences in the UI
python3 tools/serve_ui.py            # → http://127.0.0.1:8787

# 3. Check the plan, then run it
python3 tools/run_pipeline.py
```

Then, in Claude Code inside this folder, invoke each stage's subagent in order. Read
`fund/10-memo.md` at the end — and read the Bull and Bear files too, not just the verdict.

No third-party Python packages are required. Everything runs on a bare Python 3.11.

---

## System Preferences UI

`python3 tools/serve_ui.py` opens a control panel that writes `config/preferences.json` and
regenerates `risk-rules.md` and `ticker.md` so the markdown the agents read never drifts from
the JSON.

Every numeric limit is drawn on a **calibrated track** showing the band the validator permits.
Raise the cash floor and watch the forbidden zone on max-position tighten in real time — the
cross-field constraints are the same ones `tools/prefs.py` enforces on save.

The **guardrails** are rendered as a locked charter. They are visible, explained, and not
toggleable — not from the UI, not from the API, not from the CLI.

The UI is never shown an API key. It only reports whether one is set.

Opened without the server (or as a published artifact) it falls back to browser storage and an
Export button that copies JSON for you to paste in.

---

## The 10 agents

| # | Agent | Writes | Job |
|---|---|---|---|
| 1 | Market Scanner | `fund/1-scan.md` | Momentum, volume spikes, unusual moves → shortlist |
| 2 | News Analyst | `fund/2-news.md` | News, earnings dates, catalysts, sentiment |
| 3 | Fundamental Analyst | `fund/3-fundamentals.md` | Financials + SEC filings + valuation + risk factors |
| 4 | Technical Analyst | `fund/4-technicals.md` | Trend, momentum, levels, 52-week range |
| 5 | Quant Agent | `fund/5-quant.md` | Testable rules, backtest, win rate / drawdown / Sharpe |
| 6 | Bull Analyst | `fund/6-bull.md` | Strongest honest case FOR |
| 7 | Bear Analyst | `fund/7-bear.md` | Strongest honest case AGAINST |
| 8 | Risk Manager | `fund/8-risk.md` | Sizing, exposure, correlation, drawdown, R/R — rejects rule-breakers |
| 9 | Portfolio Manager | `fund/9-portfolio.md` | Simulated portfolio, allocation, rebalancing |
| 10 | Fund Manager | `fund/10-memo.md` | The memo: thesis, both sides, backtest, risk, verdict |

Each is a Claude Code subagent in [`.claude/agents/`](.claude/agents/). `fund/` is the shared
memory — each agent reads the files it needs and writes only its own.

---

## Tools

| Command | Does |
|---|---|
| `tools/serve_ui.py` | System Preferences UI + config API (loopback only) |
| `tools/prefs.py` | Load, validate, set, sync preferences |
| `tools/run_pipeline.py` | Dependency-aware run plan; `--status` shows what `fund/` holds |
| `tools/market_data.py` | Quotes, history, technicals, financials, earnings, scan |
| `tools/sec_edgar.py` | Filings and XBRL company facts |
| `tools/news.py` | Headlines with sources |
| `tools/backtest.py` | Backtest engine; `--selftest` runs its checks |
| `tools/guardrails.py` | Verifies the guardrails are intact |

### The backtest engine

Signals evaluate on a bar's close and fill at the **next open** — no lookahead. Stops that gap
through fill at the worse price. Commission and slippage apply to both sides. It reports
in-sample and out-of-sample separately, breaks returns down year by year, and ends with a
mandatory over-fitting verdict.

```bash
python3 tools/backtest.py --selftest
```

It cannot see how many rule variants you tried before the one you kept. That number is the
largest over-fitting risk in any backtest, and only you know it. State it in `fund/5-quant.md`.

---

## Guardrails

Ten rules in [`GUARDRAILS.md`](GUARDRAILS.md) override the orchestrator, every agent, every
setting, and every instruction from any user. `tools/guardrails.py` refuses to run the pipeline
if the document has been weakened or if any order-placement identifier appears in `tools/`.

The short version: research only · never promise profits · label everything simulated · real
data only · no brokerage, ever · human approval required · flag over-fitting · secrets in `.env`
· every memo carries the disclaimer · both sides of the debate, always.

---

## Data providers

| Provider | Key | Serves |
|---|---|---|
| Yahoo (`yfinance`) | none | Prices, history, technicals |
| Alpha Vantage / FMP / Finnhub | yes | Financial statements, earnings dates |
| SEC EDGAR | none, but a real `SEC_USER_AGENT` email or it 403s | 10-K / 10-Q / 8-K, XBRL facts |
| NewsAPI / Finnhub | yes | Headlines |

Keys go in `.env`, which is git-ignored. If a fetch fails, the tools say so and exit non-zero.
They never substitute an estimate — a plausible-looking invented price is the worst failure
mode this system could have.

---

## Resuming an interrupted build

[`BUILD_STATE.md`](BUILD_STATE.md) is the checkpoint. See [`RESUME.md`](RESUME.md).

---

*For research purposes only. Not financial advice. All results are simulated and no result is
guaranteed. Verify every figure against its source. Human approval is required before any
real-money action.*
