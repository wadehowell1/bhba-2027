# Slide Renderer

Turns the slide copy in `marketing/social/30-day-calendar.md` into finished PNGs for
TikTok photo mode and Instagram carousels. No design tool, no subscription, no manual
layout step.

```bash
cd tools/slide-renderer
python3 render.py                    # all 30 posts, both platforms
python3 render.py --days 1 2 3       # specific days
python3 render.py --platform ig      # tiktok | ig | both
```

Output lands in `marketing/social/slides/day-NN/{tiktok,ig}/NN.png`, plus a
`manifest.json` listing every file.

**Current output: 30 posts, 216 slides, 432 PNGs, ~16 MB.**

## Requirements

- Python 3 with Pillow (`pip install pillow`)
- Chromium or Chrome — the script looks in `CHROME_CANDIDATES`, which already includes
  the Playwright Chromium preinstalled in this environment
- The Inter fonts in `fonts/` (bundled, SIL Open Font License — see
  `fonts/LICENSE-Inter.txt`)

## How it works

1. **Parses the calendar.** The markdown file is the single source of truth. Slide copy
   is read from the numbered table rows under each `## Day N — Title` heading, so
   editing a slide means editing the calendar, never a separate data file that can
   drift out of sync.
2. **Builds one HTML page per post** with the slides stacked vertically, styled with
   the same tokens as the website so social and site read as one brand.
3. **Screenshots the whole strip in one headless Chrome pass**, then splits it with
   Pillow. One browser launch per post rather than one per slide — the full run is
   about 2.5 minutes instead of roughly 15.

## Design rules encoded here

**Emphasis.** `**double asterisks**` in the calendar resolve to the accent color, but
only where the accent still means something:

| Case | Result |
|---|---|
| Hook slide (slide 1) | Emphasis stripped, text stays ink. The accent-soft background already carries the signal, and accent-on-accent-soft is low contrast |
| Body slide fully wrapped in `**` | Whole line takes the accent — it is the payoff slide |
| Body slide partially wrapped | Only that fragment takes the accent |

Without this rule nearly every slide came out fully accented and the color stopped
distinguishing anything, breaking "one accent element per slide."

The result is a deliberate rhythm across a post: pale accent-soft hook in ink → ink
body slides on paper → an accent payoff slide.

**Auto-fit.** Copy that overflows its box is shrunk in 2px steps down to a 26px floor.
It never grows — the sizes in `PLATFORMS` are intended maximums, so a slide that fits
looks identical to every other slide that fits. If a slide shrinks noticeably, the
copy is too long; cut it in the calendar rather than letting the type get small.

**Safe zones.** TikTok gets a 200px right gutter for the action rail and a 400px bottom
margin for the caption overlay. Instagram needs far less, so it uses tighter padding.
This is why the two platforms are separate renders rather than one image cropped.

## Two bugs found while building this, both fixed

**1. Chrome does not paint the last ~100px of an exactly-sized headless window.** With
`--window-size=1080,{n*1350}` the strip came out the right pixel dimensions, so the
size assertion passed, but the bottom band was never painted — which silently dropped
the slide counter from the **final slide of every post**. Every other slide was fine,
which is what made it easy to miss.

Fixed by rendering with `BOTTOM_SLACK = 200` extra pixels and cropping tiles from the
top. Do not remove that slack.

**2. Headless Chrome has a minimum window width of roughly 485px.** Relevant when
testing narrow layouts, not for these renders. Documented in `website/README.md`.

## Verification

After a full run, every file was checked programmatically for correct dimensions, a
present slide counter, and non-blank body text — 432/432 passed. Worth re-running that
check after changing the template:

```python
# see the QA snippet in the project history, or simply spot-check:
python3 -c "from PIL import Image; im=Image.open('../../marketing/social/slides/day-01/tiktok/07.png'); print(im.size)"
```

## Changing the look

Everything visual lives in two places at the top of `render.py`:

- `TOKENS` — colors, matched to the website palette
- `PLATFORMS` — canvas size, padding (safe zones), and hook/body type sizes

Change those and re-run. Do not hand-edit the PNGs; they are build output and get
overwritten.
