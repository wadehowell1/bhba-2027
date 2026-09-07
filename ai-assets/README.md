# AI Asset & Usage Register — Operating Procedure

| | |
|---|---|
| **Document** | AI Asset & Usage Register — Operating Procedure |
| **Version** | 1.0.0 |
| **Classification** | INTERNAL USE |
| **Owner** | Wade Howell |
| **Effective** | 2026-09-07 |
| **Review cycle** | Monthly, with the register run. Out-of-cycle on connector addition or after any security incident. |
| **Control mapping** | ISO/IEC 27001:2022 A.5.9, A.5.19, A.5.23, A.8.9, A.8.16, A.8.28, A.8.31 · NIST SP 800-53 Rev.5 CM-8 · NIST CSF 2.0 ID.AM-02 · Jamaica Data Protection Act 2020, First Schedule Standards 7 and 8 |

---

## 1. Executive summary

This register enumerates every AI asset in the estate — MCP connectors, Claude skills, plugins and code repositories — classifies each as new or existing against the prior month, and reports the usage that can actually be measured. It regenerates monthly without manual input. The September 2026 baseline covers **64 assets**: 14 connectors, 45 skills, 5 repositories, 0 plugins. Invocation telemetry for connectors and skills is not yet accumulating, because no usage-analytics API exists for them; the mechanism that will accumulate it is built, tested and running, and is described in §6.

---

## 2. What the run produces

| Output | Purpose |
|---|---|
| `ai_assets_dashboard.html` | Standalone dashboard. No build step, no CDN, no external fetches. Opens from disk in any browser; ~86 KB. |
| `data/asset_register.csv` | One row per asset with lifecycle, RAG status, risk tier, data exposure and control reference. |
| `data/usage_monthly.csv` | Tidy long format — one row per month/asset/metric. Loads into Power BI or Excel without reshaping. |
| `data/usage_events.csv` | Append-only telemetry ledger, deduplicated on event UUID. Grows month over month. |
| `data/snapshots/<YYYY-MM>.json` | Immutable monthly snapshot. The audit trail, and the basis of next month's diff. |

---

## 3. SIPOC

| Suppliers | Inputs | Process | Outputs | Customers |
|---|---|---|---|---|
| claude.ai connector registry | `sources/connectors.json` | 1. Capture sources | Asset register (CSV) | Asset owner (Wade Howell) |
| Claude synced skills service | `sources/skills_manifest.json` | 2. Assemble inventory | Monthly usage facts (CSV) | Security / audit reviewer |
| GitHub REST API + local clones | `sources/repo_commits.json`, `sources/repositories.json` | 3. Diff against prior snapshot | Telemetry ledger (CSV) | Anyone assessing DPA 2020 exposure |
| Claude session transcripts | `~/.claude/projects/**/*.jsonl` | 4. Ingest telemetry | Immutable snapshot (JSON) | Board / management reporting |
| | | 5. Render dashboard | Dashboard (HTML) | |
| | | 6. Self-test, then commit | | |

**Entry criteria** — all four source captures present and parseable.
**Exit criteria** — `selftest.py` returns 0, and the snapshot for the period is written.
**Escalation** — a failed self-test blocks the commit. Nothing is published from a run that did not verify.

---

## 4. Running it

```bash
python3 ai-assets/refresh_sources.py                 # refresh what a job can refresh
python3 ai-assets/generate.py --period 2026-09       # build register, dataset, dashboard
python3 ai-assets/selftest.py                        # 33 checks; must pass before publishing
```

`generate.py` defaults to the current UTC month. `--no-telemetry` skips transcript ingestion.

---

## 5. Monthly regeneration — two mechanisms, deliberately

Neither mechanism alone can refresh everything, so both run.

| | GitHub Actions | Claude Routine |
|---|---|---|
| **Schedule** | 1st of month, 06:12 UTC (01:12 Jamaica) | 1st of month, 06:40 UTC (01:40 Jamaica) |
| **Defined in** | `.github/workflows/ai-assets-monthly.yml` | claude.ai Routines |
| **Refreshes** | Repository history, telemetry ledger, all derived outputs | Connector registry, skills manifest, repository list — then re-runs the full pipeline |
| **Cannot refresh** | Connector and skill inventory (needs a Claude session) | — |
| **Failure mode** | Self-test failure blocks the commit | Reports and leaves the last good register in place |

Jamaica is UTC−5 year round and observes no daylight saving, so these slots do not drift seasonally. Minutes are deliberately off the hour: every scheduled job on the platform that asks for "06:00" fires at once.

The Actions run refreshes private repositories only if the optional `AI_ASSETS_TOKEN` secret is set — a fine-grained PAT with read-only Contents access. Without it, those repositories keep their last capture and the dashboard's freshness panel says so.

---

## 6. Measurement and control plan

| Metric | Source | Basis | Status |
|---|---|---|---|
| Repository commits per month | Git history, all refs | Measured | Green — complete for 3 of 5 repositories |
| Skill provisioning per month | `updatedAt` in the skills manifest | Measured | Green — all 45 skills dated |
| Connector / skill invocations | Session transcripts, tool-use events | Measured | Red — mechanism live, no events yet |
| Asset lifecycle (new / existing / retired) | Snapshot diff | Measured | Baseline established; a real diff from October |

**Why invocation counts read zero.** claude.ai exposes no usage-analytics API. The only measurable record of connector and skill use is the local session transcript, which logs every tool call with a timestamp. `generate.py` parses those transcripts, maps `mcp__<Server>__*` calls to connectors and `Skill` calls to skills, and appends them to a UUID-deduplicated ledger. Platform tooling (GitHub, the Claude Code control plane) is excluded so it cannot inflate connector figures.

The ledger reads zero because the container this baseline was produced in was created fresh and holds one session, in which no connector or skill was invoked. Run the pipeline on the machine where day-to-day Claude work happens and it will pick up that history. The parser is proven against a fixture in `selftest.py` §2 rather than assumed to work.

**Treat a zero in this report as unmeasured, not unused.** The dashboard states this on the Governance tab and flags affected classes Red on the instrumentation panel.

---

## 7. Risk register

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | Stale inventory is read as current | Medium | High | Every source is aged; captures over 45 days old are flagged Stale on the dashboard and named in the limitations panel | Asset owner |
| R2 | Telemetry never accumulates because the pipeline runs somewhere without transcripts | High | Medium | Ledger is append-only and committed, so history survives ephemeral containers; §6 states the requirement plainly | Asset owner |
| R3 | Tier 1 connector authorised without review | Medium | High | Register flags all Tier 1 assets; monthly diff surfaces additions as NEW | Asset owner |
| R4 | A public repository receives sensitive content | Low | High | `wadehowell1/bhba-2027` is public and flagged Tier 1 with an explicit exposure note | Asset owner |
| R5 | Scheduled job silently stops | Medium | Medium | Two independent mechanisms; a missing monthly snapshot file is the detection signal | Asset owner |
| R6 | Register drifts from reality between runs | Medium | Low | Out-of-cycle review is triggered by connector addition or security incident, not only by the calendar | Asset owner |

---

## 8. Known limitations

1. **No invocation telemetry for connectors and skills yet** — §6.
2. **Connector install dates are not exposed.** The registry returns no provisioning timestamp, so connectors are seeded BASELINE on the first run rather than falsely reported as new. Their NEW/RETIRED status becomes a measured diff from the second run.
3. **`wadehowell1/job-agent` is inventory-only.** Attaching it to the session was denied by policy, so its commit history could not be retrieved. It is recorded with that reason attached, not omitted and not estimated.
4. **`wadehowell1/BHBA2027` is empty.** GitHub returns 409 for it — zero commits, flagged Red.
5. **Risk tiers are a considered judgement, not a vendor assertion.** They are set in `CONNECTOR_RISK` in `generate.py` and should be reviewed if a connector's scope changes.

---

## 9. Verification

`selftest.py` runs 33 checks across four groups: tool-name classification, end-to-end telemetry ingestion against a fixture transcript, the lifecycle diff, and the rendered artifact. The artifact checks assert the size budget, that no template token survives substitution, that no external resource is referenced, that the embedded payload parses, and that **every fact carries basis `measured`** — a run containing an estimated figure fails.

The dashboard was verified in Chromium: no console errors, no horizontal overflow at 345 / 485 / 753 / 1009 px across all four tabs, and both themes rendered.

---

## 10. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-09-07 | Wade Howell | Initial baseline. Inventory established across connectors, skills and repositories; telemetry ledger opened; monthly regeneration scheduled via GitHub Actions and a Claude Routine. |
