# Production System

How a line of copy becomes a published slideshow, without anyone appearing on camera
and without it eating a weekend.

---

## The design system

Consistency is the whole game for a faceless account. There is no face to recognize,
so **the look has to do the recognizing.** Someone should identify a Lean Desk post
from the thumbnail, at speed, without reading the handle.

### Canvas

| Platform | Size | Notes |
|---|---|---|
| TikTok photo mode | 1080 × 1920 | Keep all text inside the middle 1080 × 1420 — UI covers top and bottom |
| Instagram carousel | 1080 × 1350 | 4:5 takes more vertical space in feed than square |

Design once at 1080 × 1920, then crop to 1350 for Instagram. Do not design twice.

### Palette

Same tokens as the website, so social and site look like one business:

| Role | Hex | Use |
|---|---|---|
| Paper | `#FAF8F4` | Background on most slides |
| Ink | `#1A1A17` | Body text |
| Accent | `#B4451F` | The one word that matters, and hook slides |
| Accent soft | `#F6E6DE` | Hook slide background |
| Rule | `#DDD6C8` | Dividers |

**Rule: one accent element per slide.** If everything is highlighted, nothing is.

### Type

- One typeface, heavy weight, tight tracking. Inter, Söhne, or any grotesque you have.
- **Hook slide:** 90–110pt. Big enough to read at thumbnail size.
- **Body slides:** 60–72pt. If your copy needs smaller than 54pt, the copy is too long
  — cut it, do not shrink it.
- Left-aligned. Centered text at this size reads as a motivational quote.

### Slide anatomy

```
┌─────────────────────────┐
│                         │
│  [tiny brand mark]      │   ← same corner, every slide
│                         │
│                         │
│   THE HEADLINE          │   ← left, large, one idea
│   GOES HERE             │
│                         │
│                         │
│                         │
│              [3/7]      │   ← slide counter, bottom right
└─────────────────────────┘
```

**The slide counter matters more than it looks.** It signals length, which measurably
helps people commit to swiping.

### The rules that keep it recognizable

1. **One idea per slide.** If there is an "and", it is two slides.
2. **No stock photography.** Ever. It is the single fastest way to look like every
   other business account.
3. **No logos on every slide.** A small mark in one corner is enough.
4. **The last slide is not a hard sell.** It is the point landing. The CTA belongs in
   the caption.
5. **Never put the CTA link in an image.** Nobody can click it.

---

## Two production routes

### ✅ Built: HTML → PNG renderer

**This is done.** `tools/slide-renderer/` renders every slide from the calendar copy —
no design tool, no subscription, no manual layout.

```bash
cd tools/slide-renderer && python3 render.py
```

**Current output: 30 posts, 216 slides, 432 PNGs** (TikTok 1080×1920 and Instagram
1080×1350), in `marketing/social/slides/`. A full run takes about 2.5 minutes.

The calendar markdown is the single source of truth: edit a slide there, re-run, and
the PNG updates. There is no separate data file to drift out of sync.

**What this changes about production.** The original plan had Canva at 5–8 minutes per
post. Regenerating all thirty now costs one command, so the marginal cost of a copy
change is effectively zero — which matters because after the day-30 review the winning
pillar gets rebuilt and rerun, not hand-edited.

See `tools/slide-renderer/README.md` for the design rules it encodes and the two Chrome
rendering bugs found and fixed while building it.

### Canva, if you prefer to hand-tune

Still viable for one-off variants or if you want to art-direct a specific post. Build
one master template with Hook / Body / Emphasis / Close layouts and fill from the
calendar. Slower per post, and the output will drift from the renderer's unless you
are careful — so treat it as the exception, not the route.

## Batching

**Do not produce daily.** Two sessions a month, ten posts each.

| Step | Time | What |
|---|---|---|
| 1 | 20 min | Review the next ten in the calendar; adjust anything stale |
| 2 | **~1 min** | `python3 render.py` — regenerates every slide |
| 3 | 15 min | Captions and hashtags — already drafted, just check |
| 4 | 10 min | Confirm the Notion rows point at the right assets |
| **Total** | **~45 min** | **Ten posts = two weeks of publishing** |

Roughly **1.5 hours a month** for a five-a-week presence on two platforms, now that
rendering is a command rather than an hour in a design tool.

The batching discipline still matters — reviewing copy ten at a time keeps the voice
consistent — but the production step is no longer the expensive part.

---

## Quality gate — check before it goes in the queue

- [ ] Hook readable at thumbnail size (shrink to 15% and squint — genuinely do this)
- [ ] No text in the platform UI zones
- [ ] Slide counter correct
- [ ] One accent element per slide
- [ ] Caption has no invented statistic, testimonial or client
- [ ] Any example is labeled as an example
- [ ] Hashtags within platform norms (TikTok 3–5, IG 8–12)
- [ ] Link CTA points at the Waste Walk page, and that page is live
- [ ] Read the caption out loud — if it sounds like an advert, rewrite it

That last check catches more bad posts than the rest combined.

---

## What never gets automated

| Stays human | Why |
|---|---|
| **Approving the week** | The whole point of the system |
| **Replying to comments** | Comments are free customer research. Automating them destroys the only signal social produces |
| **Deciding what to make next** | The analytics tell you. A generator will happily produce thirty more of a losing pillar |
| **Anything responding to a real person** | An automated reply pretending to be human is a small lie, and this audience is good at spotting them |

**Comment replies are worth protecting specifically.** When someone says "this is
literally my Tuesday," that is a discovery conversation asking to happen — and Test 4
in the validation plan needs fifteen of those.
