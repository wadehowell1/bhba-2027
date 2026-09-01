# Automations

> ⚠️ **The framework's warning, restated because it matters:** Claude Code can only
> reach tools you have actually connected and authorized. Nothing in this file is
> live. It is a design for workflows a human must set up, connect and test.

## Design principle: automate the delivery, not the relationship

The whole business rests on trust, and the coaching tier is sold by conversation. So
the rule is: **automate anything that is the same every time, and never automate
anything that pretends to be personal.** An auto-reply written as though a human typed
it is a small lie, and this audience is unusually good at spotting them.

Specifically: delivery, receipts, reminders and internal alerts get automated.
Discovery replies, coaching check-ins and anything answering a real question do not.

---

## Trigger → Action map

| # | Trigger | Action | Tool | Priority |
|---|---|---|---|---|
| 1 | Waste Walk form submitted | Add to list (unconfirmed) → double opt-in email | ESP | **P1 — launch blocker** |
| 2 | Opt-in confirmed | Deliver worksheet → start 6-email sequence | ESP | **P1** |
| 3 | Reply to any sequence email | Flag to inbox as **research** + pause the sequence | ESP + inbox rule | **P1** |
| 4 | Kit purchased | Deliver files → receipt → tag `customer` → exit sales sequence, enter onboarding | Checkout + ESP | **P1 (before selling)** |
| 5 | Kit purchased | Remove from Kit promotion in all future sends | ESP | **P1** |
| 6 | Refund requested | Notify human, revoke nothing automatically | Checkout | P1 |
| 7 | Course purchased | Grant access → onboarding sequence → day-7 "did you pick a process?" nudge | Course platform | P2 |
| 8 | Course, no activity in 7 days | One nudge. **One.** | Course platform | P2 |
| 9 | Discovery call booked | Confirmation + prep questions + calendar hold | Cal.com | P2 |
| 10 | Call completed | Manual follow-up task created | Task tool | P2 — **not** an auto-email |
| 11 | Coaching client signed | Onboarding pack, session scheduling, diagnostic request | Manual + template | P2 |
| 12 | Fortnightly during engagement | Reminder to write the one-page report | Calendar | P3 |
| 13 | Engagement day 75 | Internal task: prepare handover + renewal conversation | Task tool | P3 |
| 14 | New content published | Cross-post + queue shorts | Buffer/Make | P3 |
| 15 | Weekly Monday | KPI snapshot email to self | Sheets + script | P3 |
| 16 | Outreach: no reply in 4 days | Internal reminder for the next message | CRM/Sheet | P3 — **draft prompt, not auto-send** |

**Note on #16.** Outreach follow-ups are *reminded*, never auto-sent. Each message
should be looked at before it goes, because half the value of outreach is noticing
something specific about the recipient — which is exactly what automation removes.

---

## The minimum viable stack

Everything below can be replaced. Start with the smallest set that works.

| Need | Suggested | Notes |
|---|---|---|
| Email | ConvertKit / MailerLite | Both do double opt-in, tagging and sequences on a free-to-cheap tier |
| Checkout + delivery | Gumroad or Podia | Handles VAT/sales tax on digital goods in some regions — ⚠️ **verify for your jurisdiction; this is a real liability** |
| Payments (coaching) | Stripe invoice | Hosted; never handle card data |
| Booking | Cal.com | — |
| Analytics | Plausible / Fathom | Cookieless; simpler privacy position |
| Glue | Make or Zapier | Only where native integrations do not exist |
| CRM | A spreadsheet | Until ~50 contacts. A real CRM before then is procrastination |

> **Do not buy a stack before Gate 3.** The full set above costs real money monthly.
> Until something has sold, a form, a spreadsheet and an email account are enough.

---

## What deliberately stays manual

| Stays manual | Why |
|---|---|
| Replies to Waste Walk responses | These *are* the customer research. Reading them is the job |
| Anything after a discovery call | A templated post-call email reads as exactly what it is |
| Coaching session prep and reports | Non-repeatable by nature |
| Refund conversations | A refund handled well is sometimes a future customer |
| Choosing which content to make | The replies tell you. Automating this loses the signal |

---

## Failure modes to design against

| Risk | Guard |
|---|---|
| Sequence keeps sending after someone replies | Workflow #3 pauses on reply. **Test this before launch** — it is the most common and most embarrassing failure |
| Buyer keeps getting sold what they bought | Workflow #5. Test with a real purchase |
| Double opt-in never confirmed → list looks broken | Monitor confirmation rate; check spam placement |
| Delivery email lands in spam | Authenticate the domain (SPF, DKIM, DMARC) **before** the first send |
| Automation fires on a test purchase | Use the provider's test mode; verify tags after |

---

## Setup order

1. Domain + email authentication (SPF/DKIM/DMARC) — **before anything sends**
2. ESP account, double opt-in form, workflows #1–#3
3. Privacy policy live — ⚠️ **before a single email address is collected**
4. Test the whole opt-in path with a real address
5. Checkout + workflows #4–#6 — only when the Kit is ready to sell
6. Everything else, later, and only when the volume justifies it
