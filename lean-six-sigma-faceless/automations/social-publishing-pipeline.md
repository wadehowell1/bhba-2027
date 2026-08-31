# Social Publishing Pipeline

**Goal:** approve a week of content in one sitting; everything else runs itself.

**Route chosen:** Notion (approval) → Buffer (publishing) → TikTok + Instagram.
Assets via Canva. Weekly cadence driven by a scheduled Claude Routine.

---

## What is actually possible — read this first

Honest constraints, established by checking rather than assuming:

| Claim | Reality |
|---|---|
| Auto-post to Instagram | ✅ Possible. Instagram for Business has publish actions, and Buffer publishes to it |
| Auto-post to TikTok | ⚠️ **Only via an approved partner.** Zapier has **no** TikTok publishing action — only ads and lead-gen. TikTok's Content Posting API is restricted, so this must go through Buffer (or Later/Metricool) |
| Generate the slide images | ✅ Canva is connected and can generate and export designs |
| Weekly approval loop | ✅ A scheduled Routine can wake a session weekly |
| Fully hands-off video | ❌ Not without a rendering step. **This is why slideshows were chosen** — they close the loop with no video tooling |

**Requirements you must supply:**
- A **Buffer account** — TikTok publishing needs a paid plan
- **Business/Creator** accounts on both TikTok and Instagram
- Instagram connected to a Facebook Page (platform requirement, not ours)
- A **Notion** workspace (already connected)

---

## The loop

```
      ┌── Claude drafts next week's 5 posts ──┐
      │   (from 30-day-calendar.md)           │
      │              │                        │
      │              ▼                        │
      │      Canva generates slides           │
      │              │                        │
      │              ▼                        │
      │   Notion rows created — status DRAFT  │
      │              │                        │
      │              ▼                        │
      │   ✉️  Sunday: approval email to you   │
      └──────────────┼────────────────────────┘
                     │
              YOU review the board
        flip rows DRAFT → APPROVED  (5 min)
                     │
                     ▼
      ┌── Monday: Routine reads APPROVED rows ─┐
      │              │                         │
      │              ▼                         │
      │   Push to Buffer queue with times      │
      │              │                         │
      │              ▼                         │
      │   Mark rows SCHEDULED                  │
      │              │                         │
      │              ▼                         │
      │   Buffer publishes → TikTok + IG       │
      └────────────────────────────────────────┘
```

**Nothing publishes without an APPROVED row.** That is the safety property of the whole
design: the default state is "does not post."

---

## The Notion board

One database, `Content Calendar`.

| Property | Type | Purpose |
|---|---|---|
| Post | Title | Working title, e.g. "Day 12 — Value stream" |
| Day | Number | 1–30, maps to the calendar |
| Status | Select | `Draft` · `Approved` · `Scheduled` · `Posted` · `Skipped` |
| Pillar | Select | Callout / Translation / Fix / Number / Myth |
| Platform | Multi-select | TikTok / Instagram |
| Publish date | Date | When it should go out |
| Hook | Text | Slide 1 — the thing to check first |
| Slides | Text | All slide copy |
| Caption | Text | Final caption |
| Hashtags | Text | Per platform |
| CTA | Select | None / Soft / Link |
| Assets | Files/URL | Exported slide images |
| Notes | Text | Your edits |

### How you approve

Once a week, ~5 minutes:
1. Open the board, filter `Status = Draft`.
2. Read the **Hook** and **Caption** columns. That is 90% of the risk.
3. Edit anything you want changed — **edit in place, the pipeline reads your edits**.
4. Flip Status to `Approved`. Anything you leave as `Draft` does not post.
5. Set `Skipped` on anything you want killed permanently.

**Editing beats rejecting.** Your changes are the training signal for what the next
batch should sound like.

---

## Setup runbook

### Step 1 — Accounts *(you)*
- [ ] TikTok Business/Creator account, handle secured
- [ ] Instagram Business/Creator account, connected to a Facebook Page
- [ ] Buffer account on a plan that includes TikTok
- [ ] Both channels connected inside Buffer, and **one manual test post published from
      Buffer to each** before any automation is switched on

> Do not skip that manual test. Most failures in this pipeline are a broken
> Buffer↔platform connection, and they are far easier to diagnose without automation
> in the way.

### Step 2 — Notion *(Claude can do this)*
- [ ] Create the `Content Calendar` database
- [ ] Load the 30 posts from the calendar as rows, status `Draft`
- [ ] Set the default view to filter `Status = Draft`, sorted by Publish date

### Step 3 — Zapier *(needs your authorisation)*
- [ ] Enable the **Buffer** app
- [ ] Connect your Buffer account (OAuth — you do this, no key is ever handled here)
- [ ] Confirm the profile IDs for the TikTok and Instagram channels

### Step 4 — The Routines *(you must create these — see below)*
- [ ] Weekly Routine, Sundays — email you the week's posts for approval
- [ ] Weekly Routine, Mondays — read `Approved`, push to Buffer, mark `Scheduled`

> ⚠️ **These cannot be created from a Claude Code session.** A Routine created that
> way fires with **no connectors** — no Notion, no Gmail, no Zapier — so it can read
> nothing and send nothing. Attaching connectors explicitly is not available for this
> organisation from here. Create both from the **claude.ai Routines UI**, where
> connectors can be attached. Exact prompts and schedules, ready to paste:
> **`weekly-routine-setup.md`**.

### Step 5 — First week runs in supervised mode
- [ ] Approve as normal, then **watch the first two posts publish**
- [ ] Confirm they appear correctly on both platforms before trusting the loop

---

## Posting schedule

| Day | Time | Platform |
|---|---|---|
| Mon–Fri | 06:30 | TikTok |
| Mon–Fri | 07:00 | Instagram |

⚠️ Hypotheses, not data. Replace after 30 days with your own analytics.

---

## Failure modes and guards

| Risk | Consequence | Guard |
|---|---|---|
| Buffer↔TikTok connection silently expires | Posts vanish, nothing errors visibly | Weekly Routine checks last-published date; alerts if nothing posted in 48h |
| A post is approved with a broken asset link | Blank or failed post | Pipeline refuses to schedule a row with an empty Assets field |
| Duplicate scheduling | Same post twice | Status must be exactly `Approved` to schedule; immediately set to `Scheduled` |
| Nobody approves that week | Silence on the channels | Sunday email; if zero approvals by Tuesday, one reminder. **Then it stays quiet — no auto-approve, ever** |
| Platform rejects content | Post fails | Buffer reports failures; surface them in the Monday run |
| Hashtag or copy triggers a filter | Reduced reach | Human approval is the guard. No auto-generated hashtags |
| Rate limits | Failed API calls | Five posts/week/platform is far below any limit |

### The rule that must never be relaxed

**No auto-approval. Not after a missed week, not on a "safe" post, not ever.** The
moment content publishes without a person seeing it, this stops being a faceless brand
with a human editor and becomes an unattended bot — which is both a brand risk and a
platform-policy risk.

---

## Secrets

- All OAuth connections live in Zapier, Buffer and Notion. **No API key is stored in
  this repository, and none is handled in application code.**
- `.env` is git-ignored; `.env.example` holds placeholders only.
- Buffer and Zapier authorisation is done by you, in their UI. Claude never sees a
  credential.
- If a connection is revoked, the pipeline fails closed — it does not post.

---

## Cost

| Item | Cost | Note |
|---|---|---|
| Buffer | ~$6–15/channel/month | ⚠️ **Verify current pricing** — plans change |
| Notion | Free tier is sufficient | |
| Canva | Free tier workable; Pro helps with brand kit | |
| Zapier | Free tier may suffice at ~10 tasks/week | ⚠️ Verify against current task limits |

⚠️ **No pricing here is verified.** Check each before committing.

---

## What to do if the automation is more trouble than the content

A real possibility worth naming. Five posts a week is roughly **fifteen minutes** of
manual scheduling in Buffer's own UI.

**If the pipeline breaks twice, turn it off and schedule manually.** The calendar and
the production system are the valuable parts; the automation is a convenience. Do not
spend three hours debugging a connector to save fifteen minutes a week — that is
exactly the kind of waste this entire business is about eliminating.
