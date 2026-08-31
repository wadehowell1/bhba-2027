# Lean Six Sigma Faceless

A complete business build-out for **lean coaching and digital products for small
businesses**, run as a faceless brand.

Built by working the "How to use Claude Code to build a business from scratch"
framework (idea → research → offer → product → website → marketing → automations →
launch) against one idea, under that framework's honesty rules:

> Do not fabricate market data. Do not invent customers, testimonials or revenue.
> Clearly label assumptions. Keep secrets in environment variables.

Working brand name: **The Lean Desk**. ⚠️ Not checked for domain or trademark
availability.

---

## The short version

**Positioning:** *Lean, translated for small business.*

The obvious market — Lean Six Sigma certification — is crowded and commoditised, with
Green Belt training already selling from roughly $300 to $2,500. Competing there means
fighting accreditation bodies and universities on price.

The opening is somewhere else, and it is documented rather than assumed: the academic
literature on lean in SMEs finds that **most published lean roadmaps were built for
large manufacturers**, and small firms cannot run them with the time, budget and
expertise they have. The method is proven. The packaging for small business is missing.

So the product is not the method. **The product is the translation** — scope shrunk to
one process, the owner's language on the outside, and every template already filled in
with an example from a business with eleven people rather than eleven hundred.

**The ladder:** free Waste Walk → $49 Kit → $349 Fix One Process → $2,400 / 90-day
coaching. *All prices are assumptions.*

**The verdict from research was TEST MORE, not GO** — and the project is sequenced
accordingly: the cheap things are built, the expensive things are gated behind
validation.

---

## Where things are

```
lean-six-sigma-faceless/
├── README.md                       ← you are here
├── business-plan.md                Phase 1 — the concept, sharpened
├── research/
│   ├── market-research.md          Phase 2 — evidence, assumptions, open questions, sources
│   ├── ideal-customer-profile.md   Two profiles: the Operator (buys) and the Practitioner (reach)
│   └── validation-plan.md          6 tests, pre-committed thresholds, stop conditions
├── offer/
│   ├── offer.md                    Phase 3 — the four rungs, objections answered honestly
│   ├── pricing-worksheet.md        Phase 4 — prices, margins (flattering and honest), illustrative mix
│   └── positioning.md              Naming, voice, the say-nothing-we-can't-show rule
├── product/
│   └── build-specification.md      Digital product + service specs, gated build order
├── website/
│   ├── index.html                  Phase 5 — the site (static, responsive, verified)
│   ├── copy.md                     Copy as a separate pass
│   ├── README.md                   Why static, launch TODOs, testing notes
│   └── .env.example                Placeholders only — never commit real keys
├── marketing/
│   ├── lead-magnet/waste-walk.md   The free tier, written out in full and usable
│   ├── content/content-system.md   Channels, 30 ideas, hooks, posts, case-study structures
│   ├── email/sequence.md           6-email sequence
│   └── outreach/sequence.md        4-message outreach, with compliance warnings
├── automations/workflows.md        Phase 7 — 16 trigger→action workflows, minimum stack
├── analytics/kpi-dashboard.md      Phase 8 — the few metrics worth tracking
└── launch/
    ├── launch-checklist.md         What blocks launch, and the launch sequence
    └── human-review.md             Every decision waiting on a person
```

---

## Read it in this order

1. `business-plan.md` — what the business is, and the one assumption it rests on
2. `research/market-research.md` — the evidence, and the **TEST MORE** verdict
3. `research/validation-plan.md` — **the most useful file here.** The cheapest order in
   which to find out whether the plan is wrong
4. `offer/offer.md` — what is actually being sold
5. `launch/human-review.md` — what needs you before anything goes public

---

## What is real, and what is not

**Grounded in cited public sources:** certification price bands, the documented SME
lean barriers (training gaps, no slack, cost-cutting misperception, frameworks built
for large manufacturers), the existence of a cheap and partly free template market,
and the viability of faceless formats for B2B education. Sources are listed in
`research/market-research.md`.

**Assumptions, labelled as such throughout:** every price, every conversion rate, every
cost-to-deliver, all build-time estimates, coaching capacity, and most of the customer
profile's behavioural detail.

**Not done, and not fudged:**
- No customer has been spoken to
- No competitor retainer pricing could be observed — none of them publish it
- No keyword volumes gathered
- No vertical chosen
- No testimonials, no case studies, no results — the site says so plainly, on purpose

Where a number could not be found, this project says so instead of estimating one that
sounds right. That is the difference between a plan you can act on and a plan that
merely reads well.

---

## Immediate next actions

1. Resolve the 🔴 blocking items in `launch/human-review.md` — especially the faceless
   scope decision, since it determines whether the coaching tier exists at all
2. Run Test 1 (keyword research) — cheapest test, and it forks the content strategy
3. Run Test 2 (competitor price discovery) — the $2,400 figure is currently unanchored
   and should not be published before this
4. Build the nine Kit files — needed regardless of what the tests say
5. **Do not build the course yet.** 80–120 hours, gated behind four validation gates

---

## A note on the website

`website/index.html` is a complete static page — no build step, open it in a browser.
It was verified during the build at 320px, 390px and 768px (no horizontal overflow),
in light and dark themes, with working client-side form validation.

It ships **deliberately unwired**: no analytics script, no live form endpoint, no
checkout links. Those need the privacy policy, the ESP account and the legal review
first. The `TODO(launch)` markers in the source list every one.
