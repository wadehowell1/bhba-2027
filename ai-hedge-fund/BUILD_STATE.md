# BUILD STATE — AI Hedge Fund Research System

> **Resume contract.** If a session ends early (token limit, timeout, crash), the next
> session reads THIS FILE FIRST and continues from the first unchecked box.
> Keep it current: tick a box in the same commit that completes the work.

**Repo:** `wadehowell1/bhba-2027` · **Branch:** `claude/system-preference-ui-tcbs5o`
**Project root:** `ai-hedge-fund/`
**Source spec:** `docs/SPEC.md` (extracted from the uploaded PDF guide — the authoritative ask)

---

## How to resume

```bash
cd ai-hedge-fund
cat BUILD_STATE.md          # ← you are here; find first unchecked box
cat docs/SPEC.md            # the full requirement
git log --oneline -10       # what already landed
```
Then continue at the first unchecked stage below. Do not redo checked stages.

---

## Stages

- [x] **S0 — Scaffold**
      Directory tree, `.gitignore` (blocks `.env`), `.env.example`, this checkpoint.
- [x] **S1 — Spec + orchestrator**
      `docs/SPEC.md`, `CLAUDE.md` orchestrator, `GUARDRAILS.md`, `risk-rules.md`, `ticker.md`.
- [x] **S2 — The 10 agents**
      `.claude/agents/*.md` — one per agent, prompts from the guide, wired to `fund/`.
- [x] **S3 — Tool layer**
      `tools/` — market data, SEC EDGAR, news, backtest engine, preference loader, pipeline runner.
- [x] **S4 — System Preferences UI**
      `ui/index.html` control panel + `tools/serve_ui.py` config server reading/writing
      `config/preferences.json`.
- [ ] **S5 — Ship**
      Artifact published, committed, pushed, draft PR open.

---

## Invariants (never violate, at any stage)

1. Research / backtesting / paper trading / education **only**. Not investment advice.
2. Never promise profits or guarantee results.
3. Everything is **SIMULATED** and must be labelled so.
4. **Real data only** — never invent prices, financials, filings, or news. Cite sources.
5. **Never** connect to a live brokerage or place a real trade. No order-placement code.
6. Human approval required before any real-money action.
7. Flag over-fitting risk on every backtest.
8. API keys live in `.env`, git-ignored, never printed or committed.
9. Every memo ends with a not-financial-advice disclaimer.

## Decisions already made (do not relitigate)

- Built under `ai-hedge-fund/` inside the existing `bhba-2027` repo (that is the attached repo).
- Agents are Claude Code **subagents** (`.claude/agents/*.md`) so the pipeline is actually runnable.
- Preferences are one JSON file, `config/preferences.json`, that both the UI and the
  Python tool layer read — single source of truth.
- Guardrail settings in the UI are **render-only and locked**; they cannot be toggled off.
- `yfinance` is the zero-key default market-data provider.
