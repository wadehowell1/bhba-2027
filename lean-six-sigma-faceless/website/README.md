# Website — The Lean Desk

A single-page static marketing site. Open `index.html` in a browser; there is no
build step.

## Why static HTML and not a framework

The framework document recommends a modern frontend framework. This deviates
deliberately, for three reasons:

1. **It matches how this repository already deploys** — the existing pages are static
   HTML served directly. A build pipeline would be new infrastructure for one page.
2. **The site is one page with one form.** A framework would add a toolchain, a
   dependency tree and a deploy step without changing what the visitor gets.
3. **Speed is a feature here.** No hydration, no framework payload, no render-blocking
   third-party scripts. The page is a single file.

**Revisit this** if the site grows past ~5 pages, needs a blog with many posts, or
needs server-rendered dynamic content. At that point Astro or Eleventy would be the
natural step — both keep the static output.

## What's in the page

Hero · Problem · Solution · How it works · Benefits · The Kit · Pricing · Proof ·
FAQ · Signup · Footer — the structure recommended by the framework.

Implemented:

- **Responsive** — single fluid column on mobile, grids from 760px, no horizontal scroll.
- **Light and dark** — full token palette on `:root`, overridden under
  `prefers-color-scheme: dark` and `[data-theme="dark"]`. No color is defined only
  inside a media query.
- **SEO basics** — title, meta description, canonical, Open Graph, Twitter card,
  `Organization` JSON-LD.
- **Accessibility** — skip link, labeled input, `aria-invalid` on error,
  `role="status"` live region, visible focus, `prefers-reduced-motion` respected.
- **Form validation** — client-side, permissive by design (the ESP does real
  verification through double opt-in; over-strict regexes reject valid addresses).
- **Analytics placeholder** — commented out. Nothing third-party loads by default.

## Before this goes live

Everything marked `TODO(launch)` in the source, plus:

- [ ] Replace `example.com` in canonical, Open Graph and JSON-LD
- [ ] Add `og-image.png` and a favicon
- [ ] **Create `/privacy.html` before collecting a single email address**
- [ ] Create `/terms.html` and `/contact.html` (footer links are live and will 404)
- [ ] Connect the email provider (see below)
- [ ] Connect real checkout links on the Kit and course CTAs
- [ ] Enable analytics — only after the privacy policy exists
- [ ] Confirm the Rung 3 price ($2,400) against real competitor quotes — Test 2 in
      `../research/validation-plan.md`. **This number is currently unvalidated and is
      printed on the page.**

## Wiring up the form — the secrets rule

The form does not submit anywhere yet. When connecting it, there are exactly two
acceptable approaches:

1. **The ESP's own hosted form endpoint** — ConvertKit, MailerLite and Resend all
   provide a public form action that needs no secret. Simplest, and preferred.
2. **A serverless function** (Cloudflare Worker, Netlify/Vercel function) that reads
   the API key from an environment variable and forwards the request.

**Never put an API key in this file.** It is static, client-side, and public. Anything
in it is readable by every visitor, and anything pushed to git should be assumed
public permanently. Copy `.env.example` to `.env` (git-ignored) for local work.

## Testing before launch

| Check | How |
|---|---|
| Mobile layout | Device emulation at 320px, 375px, 768px |
| No horizontal scroll | `document.documentElement.scrollWidth <= document.documentElement.clientWidth` |
| Dark mode | Toggle OS theme, then force `document.documentElement.dataset.theme` both ways |
| Form validation | Empty submit, `notanemail`, `a@b.co` |
| Keyboard | Tab through: skip link → nav → CTAs → FAQ → form |
| Links | Every anchor resolves; footer links do not 404 |

### Gotcha when testing narrow widths headlessly

Headless Chrome enforces a **minimum window width of roughly 485px**, so
`--window-size=320,760 --screenshot` does *not* give you a 320px viewport. It lays the
page out at ~485px and crops the image to 320px — which looks exactly like a
horizontal-overflow bug and is not one.

To get a genuinely narrow viewport, load the page in a fixed-width iframe:

```html
<!doctype html><body style="margin:0">
<iframe src="index.html" style="width:320px;height:1500px;border:0"></iframe>
```

Media queries then evaluate against the iframe's width. Verified with this method at
320px, 390px and 768px: `scrollWidth === clientWidth`, no overflowing elements.

**One real bug was found and fixed this way:** the header CTA carried an inline
`style="padding:.55rem 1rem"`, which outranked the mobile media query and pushed the
page 5px past a 320px viewport. Keep button sizing in CSS rules — an inline style will
silently beat any breakpoint you add later.
