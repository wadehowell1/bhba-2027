# Security

## Pre-launch gate

No application in this repository ships to a public URL until the launch checklist
in [`CLAUDE.md`](CLAUDE.md) passes.

```bash
python3 tools/security_gate.py
```

Exits non-zero on any blocker. A clean run means "nothing obviously broken in the
source" — never "safe to ship". The manual items it prints must be tested against a
running system with a second user's credentials.

---

## Open findings — BHBA portal

Found by the gate on 2026-11-03. **These pages are already deployed**, so these are
live exposures, not pre-launch theory.

### 1. Shared API key hardcoded in browser-served HTML — BLOCKER

`bhba_sysadmin_hub.html`, three occurrences, sent to the Google Apps Script relay.

Anyone who opens the page and views source has this key. If the relay accepts it as
authorization, any visitor can drive the SysAdmin Email Hub — including sending mail
that appears to come from the association. That is a phishing vector wearing BHBA's
return address.

It is also in git history (commit `d9891c2`), so deleting the line is not enough.

**Fix, in order:**
1. Rotate the key in Apps Script. Assume the current one is public, because it is.
2. Stop sending a shared secret from the browser. The relay should authenticate the
   *user*, not a constant every visitor can read.
3. Purge it from history with `git-filter-repo`.

Only you can do step 1 — it needs Apps Script access.

### 2. Authentication is client-side only — HIGH

Ten pages guard themselves with:

```js
var s = JSON.parse(localStorage.getItem('bhba_session') || 'null');
// ...redirect to login if absent
```

This hides the page; it does not protect the data. Anyone can open devtools, set
`bhba_session`, and walk straight in. If the Apps Script endpoints behind these pages
do not independently verify who is calling, the redirect is decoration and the data
is effectively public.

**Fix:** every endpoint verifies the session server-side and scopes the response to
that user. The client-side guard can stay as a convenience, never as the control.

### 3. No security headers — HIGH

No Content-Security-Policy, X-Frame-Options, Referrer-Policy or HSTS anywhere.

**Fix:** set them at the host. Note that these pages use inline `<script>`, so a CSP
has to allow them explicitly or the pages break. Do not paste a strict CSP in without
testing — a broken portal is its own kind of outage.

### 4. `innerHTML` assignments — HIGH, lower priority

Flagged across the portal and the hedge-fund UI. Most render values the user set
themselves, which limits the risk, but any path that renders *another* user's input
is a stored-XSS vector. Worth an audit pass; not a launch blocker on its own.

---

## Why these were not auto-fixed

Rotating the key needs Apps Script access. Moving authentication server-side is an
architectural change to a system people are using today. Dropping in a CSP would
break every inline script on these pages.

Each of those deserves a deliberate change with you in the loop, not a silent commit
to a live portal.
