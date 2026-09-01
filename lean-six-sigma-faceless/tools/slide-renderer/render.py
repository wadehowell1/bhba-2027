#!/usr/bin/env python3
"""
Slide renderer for The Lean Desk.

Reads the slide copy straight out of `marketing/social/30-day-calendar.md` — that file
stays the single source of truth — and renders finished PNGs for TikTok photo mode
(1080x1920) and Instagram carousel (1080x1350).

Method: build one HTML page per post with the slides stacked vertically, screenshot the
whole strip in a single headless Chrome pass, then split the strip with PIL. One browser
launch per post rather than one per slide.

Usage:
    python3 render.py                 # render everything
    python3 render.py --days 1 2 3    # render specific days
    python3 render.py --platform ig   # tiktok | ig | both (default both)
"""

import argparse, html, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
CALENDAR = PROJECT / "marketing" / "social" / "30-day-calendar.md"
OUT = PROJECT / "marketing" / "social" / "slides"
FONTS = ROOT / "fonts"

CHROME_CANDIDATES = [
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/usr/bin/chromium", "/usr/bin/google-chrome", "/usr/bin/chromium-browser",
]

# Design tokens — kept in step with the website palette so social and site read as one brand.
TOKENS = {
    "paper": "#FAF8F4", "ink": "#1A1A17", "ink3": "#6F6A60",
    "accent": "#B4451F", "accent_soft": "#F6E6DE", "rule": "#DDD6C8",
}

# Chrome does not paint the last ~100px of an exactly-sized headless window, so every
# strip is rendered with this much extra height and the tiles cropped from the top.
BOTTOM_SLACK = 200

PLATFORMS = {
    # pad = (top, right, bottom, left). TikTok needs a wide right gutter for its action
    # rail and a deep bottom margin for the caption overlay; Instagram needs far less.
    "tiktok": dict(w=1080, h=1920, pad=(250, 200, 400, 88), hook_size=104, body_size=70),
    "ig":     dict(w=1080, h=1350, pad=(150, 96, 190, 88),  hook_size=96,  body_size=64),
}


def find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    found = shutil.which("chromium") or shutil.which("google-chrome")
    if found:
        return found
    sys.exit("No Chrome/Chromium binary found. Set one in CHROME_CANDIDATES.")


def parse_calendar(path: Path):
    """Pull every '## Day N — Title' section and its numbered slide table rows."""
    text = path.read_text(encoding="utf-8")
    posts = []
    # Day headings, excluding the summary table at the top of the file.
    sections = re.split(r"^## Day (\d+) — (.+)$", text, flags=re.M)
    # sections = [preamble, num, title, body, num, title, body, ...]
    for i in range(1, len(sections), 3):
        day = int(sections[i])
        title = sections[i + 1].strip()
        body = sections[i + 2]
        pillar = None
        m = re.search(r"\*\*Pillar:\*\*\s*(\w+)", body)
        if m:
            pillar = m.group(1)
        # Slide rows look like: | 3 | Some copy |
        slides = []
        for row in re.finditer(r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*$", body, flags=re.M):
            slides.append((int(row.group(1)), row.group(2).strip()))
        if not slides:
            continue
        slides.sort(key=lambda s: s[0])
        posts.append(dict(day=day, title=title, pillar=pillar,
                          slides=[s[1] for s in slides]))
    posts.sort(key=lambda p: p["day"])
    return posts


def to_html(raw: str, hook: bool = False) -> str:
    """Escape, then resolve **emphasis** into the accent color.

    Emphasis only earns the accent when it distinguishes part of a slide from the rest:

    - Hook slide: the accent-soft background already carries the signal, so emphasis is
      stripped and the text stays ink. Accent on accent-soft is both low contrast and
      redundant.
    - Body slide wrapped entirely in ** : the whole line is the payoff, so the whole
      line takes the accent against the paper ground.
    - Body slide with partial ** : only that fragment takes the accent.

    Without this every slide came out fully accented and the color stopped meaning
    anything, breaking the "one accent element per slide" rule in production-system.md.
    """
    stripped = raw.strip()
    fully_marked = (stripped.startswith("**") and stripped.endswith("**")
                    and stripped.count("**") == 2)
    if fully_marked:
        inner = html.escape(stripped[2:-2])
        return inner if hook else f'<span class="em">{inner}</span>'
    esc = html.escape(stripped)
    return re.sub(r"\*\*(.+?)\*\*", r'<span class="em">\1</span>', esc)


def build_page(post, spec) -> str:
    w, h = spec["w"], spec["h"]
    pt, pr, pb, pl = spec["pad"]
    n = len(post["slides"])
    slides_html = []
    for idx, raw in enumerate(post["slides"], start=1):
        hook = idx == 1
        cls = "slide hook" if hook else "slide"
        size = spec["hook_size"] if hook else spec["body_size"]
        slides_html.append(f"""
  <section class="{cls}" style="--fs:{size}px">
    <div class="mark">
      <svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="2" y="4"    width="20" height="3" rx="1" fill="{TOKENS['ink']}"/>
        <rect x="2" y="10.5" width="13" height="3" rx="1" fill="{TOKENS['accent']}"/>
        <rect x="2" y="17"   width="8"  height="3" rx="1" fill="{TOKENS['ink']}" opacity=".45"/>
      </svg>
      <span>THE LEAN DESK</span>
    </div>
    <div class="body"><p>{to_html(raw, hook)}</p></div>
    <div class="counter">{idx}/{n}</div>
  </section>""")

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@font-face {{ font-family:'ID'; src:url('{(FONTS/'InterDisplay-Bold.ttf').as_uri()}'); font-weight:700; }}
@font-face {{ font-family:'ID'; src:url('{(FONTS/'InterDisplay-SemiBold.ttf').as_uri()}'); font-weight:600; }}
@font-face {{ font-family:'IM'; src:url('{(FONTS/'Inter-Medium.ttf').as_uri()}'); font-weight:500; }}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{TOKENS['paper']}}}
.slide{{
  width:{w}px; height:{h}px; position:relative; overflow:hidden;
  background:{TOKENS['paper']}; padding:{pt}px {pr}px {pb}px {pl}px;
  display:flex; flex-direction:column; justify-content:center;
}}
.slide.hook{{ background:{TOKENS['accent_soft']}; }}
.mark{{
  position:absolute; top:{max(70, pt-140)}px; left:{pl}px;
  display:flex; align-items:center; gap:12px;
  font-family:'IM',sans-serif; font-size:19px; font-weight:500;
  letter-spacing:.16em; color:{TOKENS['ink3']};
}}
.body{{ display:flex; align-items:center; }}
.body p{{
  font-family:'ID',sans-serif; font-weight:700;
  font-size:var(--fs); line-height:1.13; letter-spacing:-.028em;
  color:{TOKENS['ink']}; text-wrap:balance;
}}
.slide:not(.hook) .body p{{ font-weight:600; letter-spacing:-.022em; }}
.em{{ color:{TOKENS['accent']}; }}
.counter{{
  position:absolute; right:{pr}px; bottom:{max(60, pb-150)}px;
  font-family:'IM',sans-serif; font-size:22px; font-weight:500;
  letter-spacing:.06em; color:{TOKENS['ink3']};
}}
</style></head><body>
{''.join(slides_html)}
<script>
// Shrink any slide whose copy overflows its content box. Never grow — the sizes above
// are the intended maximums, and a slide that fits should look identical across posts.
for (const s of document.querySelectorAll('.slide')) {{
  const p = s.querySelector('.body p');
  const box = s.clientHeight - {pt} - {pb};
  let fs = parseFloat(getComputedStyle(p).fontSize);
  let guard = 0;
  while (p.scrollHeight > box && fs > 26 && guard++ < 200) {{
    fs -= 2; p.style.fontSize = fs + 'px';
  }}
}}
document.title = 'ready';
</script></body></html>"""


def render_post(chrome, post, platform, spec, outdir):
    from PIL import Image
    w, h, n = spec["w"], spec["h"], len(post["slides"])
    page = build_page(post, spec)
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "page.html"
        src.write_text(page, encoding="utf-8")
        strip = Path(td) / "strip.png"
        # Render the strip TALLER than the slides need. Chrome leaves roughly the last
        # 100px of an exactly-sized window unpainted, which silently dropped the slide
        # counter from the final slide of every post. The slack absorbs that dead band;
        # tiles are still cropped from the top, so slide geometry is unaffected.
        cmd = [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
               "--force-device-scale-factor=1", "--allow-file-access-from-files",
               f"--window-size={w},{h*n + BOTTOM_SLACK}", "--virtual-time-budget=8000",
               f"--screenshot={strip}", src.as_uri()]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if not strip.exists():
            raise RuntimeError(f"Chrome produced no screenshot for day {post['day']}\n{r.stderr[-600:]}")
        img = Image.open(strip)
        if img.size[0] != w or img.size[1] < h * n:
            raise RuntimeError(
                f"Day {post['day']} {platform}: strip is {img.size}, need at least {(w, h*n)}. "
                "Chrome likely clamped the window height — render fewer slides per strip.")
        outdir.mkdir(parents=True, exist_ok=True)
        written = []
        for i in range(n):
            tile = img.crop((0, i * h, w, (i + 1) * h))
            fp = outdir / f"{i+1:02d}.png"
            tile.save(fp, optimize=True)
            written.append(fp)
        return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", nargs="*", type=int, help="day numbers; default all")
    ap.add_argument("--platform", choices=["tiktok", "ig", "both"], default="both")
    args = ap.parse_args()

    chrome = find_chrome()
    posts = parse_calendar(CALENDAR)
    if args.days:
        posts = [p for p in posts if p["day"] in args.days]
    plats = ["tiktok", "ig"] if args.platform == "both" else [args.platform]

    total = 0
    manifest = []
    for post in posts:
        entry = dict(day=post["day"], title=post["title"], pillar=post["pillar"],
                     slides=len(post["slides"]), files={})
        for plat in plats:
            outdir = OUT / f"day-{post['day']:02d}" / plat
            files = render_post(chrome, post, plat, PLATFORMS[plat], outdir)
            total += len(files)
            entry["files"][plat] = [str(f.relative_to(PROJECT)) for f in files]
        manifest.append(entry)
        print(f"  day {post['day']:2d}  {len(post['slides'])} slides  {post['title'][:44]}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{len(posts)} posts, {total} PNGs -> {OUT.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
