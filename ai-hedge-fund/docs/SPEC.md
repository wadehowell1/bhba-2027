# SPEC — AI Hedge Fund Multi-Agent Research System

Source: *"Build Your Own AI Hedge Fund With Claude Code"* (uploaded PDF, built by @seb.ai).
This file is the authoritative requirement. Extracted verbatim in substance from the guide,
including the **Master Build Prompt** on its final content page.

---

## ⚠ Read this first

> This is for research, backtesting, paper trading, and education only. It does **NOT** promise
> profits and is **NOT** investment advice. Every portfolio, trade, and result is simulated.
> The system never places real trades and never connects to a live brokerage. It only produces
> research for you to review — human approval is required before any real-money action.
> Investing carries real risk of loss; verify everything and consult a licensed professional.

---

## The workflow

```
SCAN → RESEARCH → ANALYZE → DEBATE → BACKTEST → RISK → ALLOCATE → REVIEW
```

Ten specialized agents pass one stock idea down a research pipeline — scanning, digging into
fundamentals + news + charts, arguing both sides, backtesting, risk-checking, simulating a
portfolio, and finishing with a fund-manager memo. All simulated, all for your judgment.

## Recommended tools & data

- Claude Code + a terminal — runs the fund
- Market-data API — prices + financials (yfinance free; or Alpha Vantage / FMP / Finnhub)
- SEC EDGAR — free filings (10-K / 10-Q / 8-K)
- News API — headlines + catalysts

Keys go in `.env`. Use **ONLY real data** — agents must never invent prices, filings, or news.

## Project structure

```
ai-hedge-fund/
├── CLAUDE.md        ← orchestrator + rules
├── .env             ← API keys (never commit)
├── risk-rules.md    ← your risk limits
├── ticker.md        ← the stock under research
└── fund/            ← shared memory (one file per agent)
    ├── 1-scan.md         ├── 2-news.md      ├── 3-fundamentals.md
    ├── 4-technicals.md   ├── 5-quant.md     ├── 6-bull.md
    ├── 7-bear.md         ├── 8-risk.md      ├── 9-portfolio.md
    └── 10-memo.md
```

## Shared memory & communication

The `fund/` folder is the shared brain. Each agent reads the files it needs and writes its own.
Data flows down the pipeline — Scanner → News/Fundamentals/Technicals → Quant → Bull/Bear debate
→ Risk → Portfolio → Fund Manager, who reads everything. Files persist, so the fund "remembers."

---

## The 10 agents

### 1. Market Scanner
- **Does:** scans stocks/sectors for momentum, volume, unusual moves → a shortlist
- **Tools:** market-data API · **Gets:** your criteria · **Passes:** shortlist → everyone
- **Prompt:** "Market Scanner. Using real market data, scan for stocks showing momentum, volume
  spikes, or unusual moves. Build a shortlist with ticker, price, and why it's interesting.
  Real data only — never invent tickers or numbers. Output to `fund/1-scan.md`."
- *Example:* "NVDA — vol 2x avg, +6% breakout. ABC — new 52wk high."

### 2. News Analyst
- **Does:** tracks breaking news, earnings, macro, catalysts, sentiment
- **Tools:** news API · **Gets:** shortlist · **Passes:** catalysts → Fundamental, Bull, Bear
- **Prompt:** "News Analyst. For the ticker, gather recent news, earnings dates, macro events, and
  catalysts, and gauge sentiment. Separate confirmed facts from rumor; cite sources; never invent
  headlines. Output to `fund/2-news.md`."
- *Example:* "Earnings in 2 wks (catalyst). Positive product news [source]. Sentiment: bullish."

### 3. Fundamental Analyst
- **Does:** revenue, earnings, margins, cash flow, debt, SEC filings, valuation
- **Tools:** market-data API + SEC EDGAR · **Gets:** ticker + news
- **Passes:** financial health → Quant, Bull, Bear, Fund Mgr
- **Prompt:** "Fundamental Analyst. Using real financials + SEC filings (10-K/10-Q/8-K), review
  revenue, earnings, margins, cash flow, debt, and valuation (P/E, P/S, EV/EBITDA). Summarize the
  risk factors from the filing. Real data only; cite sources. Output to `fund/3-fundamentals.md`."
- *Example:* "Rev +12%, margins improving, low debt. P/E x vs peers y. 10-K flags customer concentration."

### 4. Technical Analyst
- **Does:** trend, momentum, volume, support/resistance, market structure
- **Tools:** market-data API · **Gets:** ticker · **Passes:** technical read → Quant, Bull, Bear
- **Prompt:** "Technical Analyst. Using real price/volume data, describe trend (vs 50/200-day MAs),
  momentum, key support/resistance, and 52-week range. Factual context, not prediction.
  Output to `fund/4-technicals.md`."
- *Example:* "Above 200-day MA (uptrend). Support ~$x, resistance ~$y. Momentum strong."

### 5. Quant Agent
- **Does:** turns the idea into rules, backtests, measures win rate, drawdown, Sharpe
- **Tools:** market-data API + Python · **Gets:** fundamentals + technicals
- **Passes:** backtest stats → Risk, Fund Mgr
- **Prompt:** "Quant Agent. Turn the trade idea into clear, testable rules (entry/exit). Backtest on
  real historical data and report win rate, max drawdown, Sharpe ratio, and consistency. Label
  results as SIMULATED and note over-fitting risk. Output to `fund/5-quant.md`."
- *Example (sim):* "Rule: buy on breakout. Backtest: 54% win, -12% max DD, Sharpe 1.1. Simulated — verify."

### 6. Bull Analyst
- **Does:** strongest case FOR, catalysts, upside, challenges the bear
- **Tools:** reads research · **Gets:** fundamentals/news/technicals · **Passes:** bull case → Fund Mgr
- **Prompt:** "Bull Analyst. Build the strongest honest case FOR this investment: catalysts, upside
  drivers, and why the bear case might be wrong. Base it on the real research — no hype or made-up
  claims. Output to `fund/6-bull.md`."
- *Example:* "Upside: new product + margin expansion. Undervalued vs peers. Catalyst: earnings beat likely."

### 7. Bear Analyst
- **Does:** weaknesses, downside risks, challenges the bull, reasons it fails
- **Tools:** reads research · **Gets:** same research · **Passes:** bear case → Fund Mgr
- **Prompt:** "Bear Analyst. Build the strongest honest case AGAINST: weaknesses, downside risks,
  red flags, and why the bull thesis could fail. Base it on real research. Output to `fund/7-bear.md`."
- *Example:* "Risks: valuation stretched, competition rising, debt maturities. Bull assumes flawless execution."

### 8. Risk Manager
- **Does:** position sizing, exposure, correlation, drawdown limits, R/R — rejects rule-breakers
- **Tools:** `risk-rules.md` · **Gets:** quant + portfolio · **Passes:** approve/reject → Portfolio, Fund Mgr
- **Prompt:** "Risk Manager. Using `risk-rules.md`, check position size, portfolio exposure,
  correlation, drawdown limits, and risk/reward for this idea. REJECT anything that breaks the rules
  and say why. This is for a simulated portfolio. Output to `fund/8-risk.md`."
- *Example:* "❌ Rejected — 25% position breaks 20% cap. ✅ At 15% + 2:1 R/R it passes."

### 9. Portfolio Manager
- **Does:** combines approved ideas into a simulated portfolio; tracks allocation, diversification,
  exposure, rebalancing
- **Tools:** files · **Gets:** risk-approved ideas · **Passes:** portfolio → Fund Mgr
- **Prompt:** "Portfolio Manager. Combine risk-approved ideas into a SIMULATED portfolio. Track each
  position's allocation %, overall diversification, sector exposure, and suggest rebalancing.
  Label everything as simulated. Output to `fund/9-portfolio.md`."
- *Example (sim):* "Position 12% · tech exposure 40% (watch) · cash 20% · rebalance suggested."

### 10. Fund Manager
- **Does:** reviews all research, weighs bull vs bear, backtests + risk → final memo;
  approve / reject / watchlist (for research)
- **Tools:** reads all files · **Gets:** everything · **Passes:** the memo → YOU
- **Prompt:** "Fund Manager. Read all `fund/` files. Weigh bull vs bear, review the backtest + risk
  check, and write a final investment research memo: Thesis, Bull points, Bear points, Backtest,
  Risk, and a verdict — Approve / Reject / Watchlist — FOR RESEARCH PURPOSES ONLY. End with a
  'not financial advice, human approval required before any real action' disclaimer.
  Output to `fund/10-memo.md`."
- *Example:* "Verdict: Watchlist (research). Strong bull case but valuation risk — revisit after earnings."

---

## Example (one stock)

Scanner flags XYZ (volume spike) → News: earnings soon → Fundamentals: growing, fair value →
Technicals: uptrend → Quant: backtest 54% win / Sharpe 1.1 (sim) → Bull: margin expansion;
Bear: valuation risk → Risk: OK at 15% size → Portfolio: adds to sim book at 12% →
Fund Manager: Watchlist (research). All simulated; you decide.

## Backtesting & paper portfolio

**Backtesting:** the Quant agent tests rules on real historical data and reports win rate,
drawdown, and Sharpe — always labeled simulated, always flagging over-fitting.
**Paper portfolio:** the Portfolio Manager keeps a simulated book in `fund/9-portfolio.md` —
fake money, real prices, no brokerage connection, ever.

## Risk rules (edit in `risk-rules.md`)

- Max ~20% in any one position
- Keep a cash buffer
- Every idea needs an exit + stop
- Watch sector concentration + correlation
- Minimum risk/reward (e.g. 2:1)
- Max simulated drawdown limit

## Human approval rules

- The system only produces research + simulations
- It never places real trades or connects to a live brokerage
- You approve before ANY real-money action
- Verify every number against the source before relying on it

## Setup checklist

- Install Claude Code + make the folder
- Add data/news API keys to `.env` + SEC email
- Set your limits in `risk-rules.md`
- Put a ticker in `ticker.md`
- Run Scan → … → Fund Manager memo
- Read the memo + both sides of the debate
- Verify the numbers yourself · keep it 100% paper

## Troubleshooting

- **No data?** Check the ticker + that your API covers it.
- **SEC blocked?** EDGAR needs a User-Agent with your email.
- **Backtest looks amazing?** Suspect over-fitting — test on unseen data.
- **Memo one-sided?** Re-run Bull AND Bear before the Fund Manager.
- **Rate-limited?** Free APIs cap requests — cache results to the `fund/` files.

---

## 🎛 MASTER BUILD PROMPT (the authoritative ask)

> "Build me a 10-agent AI hedge fund RESEARCH system. Create a CLAUDE.md orchestrator, a .env for my
> market-data + news API keys and SEC email, a risk-rules.md, a ticker.md, and a fund/ folder as
> shared memory (one output file per agent, 1-scan … 10-memo).
>
> The agents run: (1) Market Scanner → (2) News Analyst, (3) Fundamental Analyst, (4) Technical
> Analyst → (5) Quant (rules + backtest: win rate, drawdown, Sharpe) → (6) Bull + (7) Bear debate →
> (8) Risk Manager (checks sizing/exposure/correlation/drawdown/RR, rejects rule-breakers) →
> (9) Portfolio Manager (simulated portfolio) → (10) Fund Manager (final memo: thesis, bull, bear,
> backtest, risk, verdict Approve/Reject/Watchlist for research). Each reads the fund/ files it
> needs and writes its own.
>
> **ABSOLUTE RULES:** This is for research, backtesting, paper trading, and education — NOT
> investment advice, and it must NEVER promise profits or guarantee results. Everything is
> SIMULATED; label it so. Use ONLY real data from the APIs/filings — never invent prices,
> financials, filings, or news; cite sources. NEVER connect to a live brokerage or place real
> trades. Human approval is required before any real-money action. Flag over-fitting in backtests.
> Keep API keys in .env, out of git. End the memo with a not-financial-advice disclaimer.
>
> Set up each agent with its prompt from my guide, then ask me for my API keys + a ticker and show
> me how to run the full pipeline."

---

## Additional requirements from the user (beyond the PDF)

- **A System Preferences UI** — an interface to easily manipulate the system's preferences
  (ticker/watchlist, risk limits, agent enablement + model per agent, data providers, pipeline
  settings), with strong design/UX.
- **Resume-on-limit** — the build must checkpoint itself so it can start or resume if a session
  runs out of tokens or hits a limit. See `BUILD_STATE.md`.
