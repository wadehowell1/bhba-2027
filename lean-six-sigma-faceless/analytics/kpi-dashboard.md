# Analytics & KPIs

## What to track, and what to ignore

The failure mode for a business at this stage is tracking twelve numbers that all move
for reasons you cannot explain. Track few things, and know what each one would make
you *do* differently.

| Metric | Why it earns its place | What a bad number means |
|---|---|---|
| **Waste Walk opt-ins** | The only leading indicator that exists early | Traffic or offer is wrong |
| **Landing → opt-in %** | Isolates the page from the traffic | Below 15% → the page, not the audience |
| **Replies to emails** | The single best early signal, and the source of Test 4 data | Nobody replying = audience is passive or wrong |
| **Kit sales** | First real evidence anyone will pay | Validates or kills Gate 3 |
| **List → Kit conversion %** | Comparable over time as the list grows | Below 1% → wrong audience or weak page |
| **Discovery calls booked** | The only route to coaching revenue | — |
| **Coaching engagements** | Revenue | — |
| **Unsubscribe rate** | Honesty check on send frequency and relevance | Spiking after a specific email → that email is wrong |

**Deliberately not tracked early:** follower counts, impressions, video views in
isolation, "engagement rate." None of them change a decision at this stage.

---

## Weekly KPI snapshot

Fill this in every Monday. Ten minutes. The comparison column matters more than the
absolute number.

| Metric | This week | Last week | Goal | Notes |
|---|---|---|---|---|
| Site visitors | — | — | — | |
| Landing page views | — | — | — | |
| Waste Walk opt-ins | — | — | — | |
| Opt-in conversion % | — | — | ≥25% | Gate 1 threshold |
| Email replies | — | — | — | *Read them. That is the point* |
| Kit sales | — | — | — | |
| List → Kit % | — | — | ≥2% | Gate 3 threshold |
| Discovery calls booked | — | — | — | |
| Coaching engagements (live) | — | — | ≤6 | Capacity ceiling, not a target |
| Unsubscribes | — | — | — | |
| Content published | — | — | 1 long + 3 short | |

> The two goal figures are the **pre-committed decision thresholds** from the
> validation plan — chosen in advance as decision rules, not predictions and not
> benchmarks measured from this niche.

---

## Funnel view

```
Content  ──►  Landing page  ──►  Opt-in  ──►  Email sequence  ──►  Kit  ──►  Course
                                    │                                 │
                                    └──────►  Reply / conversation ────┴──►  Coaching
```

Measure the **drop-off between each pair**, not just the ends. A funnel that converts
badly overall usually has one bad joint, and the average hides it.

---

## Tracking setup

- **Privacy-friendly analytics** (Plausible or Fathom) — cookieless, which keeps the
  privacy position simple and avoids a consent banner in most cases.
  ⚠️ **Confirm your own obligations; this is not legal advice.**
- **Custom events:** opt-in submitted, Kit CTA clicked, course CTA clicked, coaching
  CTA clicked, FAQ opened. The three CTA clicks tell you what people want before
  anything is buyable — the site already emits these to the console as placeholders.
- **No third-party script loads until the privacy policy exists.** The site ships with
  analytics commented out for exactly this reason.
- **Never** put personal data (email addresses) into analytics event properties.

## Review rhythm

- **Weekly:** the table above. Ten minutes.
- **Monthly:** which content produced opt-ins? Where did the funnel leak? Update the
  assumption log below.
- **At each gate:** compare against the pre-committed threshold and **write down the
  decision you made and why** — including when you decided to proceed despite missing a
  threshold. That record is what stops you rewriting history later.

## Assumption log

| Date | Assumption tested | Result | Decision |
|---|---|---|---|
| — | — | — | — |

> Start filling this on day one. It is the difference between a business that learns
> and one that just accumulates activity.
