# Open security findings

Produced by `python3 tools/security_gate.py` against `main` on 2026-11-19.

This is the findings register. The governance policy lives in [`SECURITY.md`](SECURITY.md)
and is not changed by this document.

**Status: BLOCKED — 3 blockers, 48 high.** These pages are already deployed, so these
are live exposures rather than pre-launch theory. The blocker below was first reported
on 2026-11-03 and is unchanged.

---

## 1. Shared API key hardcoded in browser-served HTML — BLOCKER

`bhba_sysadmin_hub.html` lines 383, 415, 468. Sent to the Google Apps Script relay.

Anyone who opens the page and views source has this key. If the relay accepts it as
authorization, any visitor can drive the SysAdmin Email Hub — including sending mail
that appears to come from the association. That is a phishing vector carrying BHBA's
return address.

It is also in git history (commit `d9891c2`), so deleting the line does not remove it.

**There is a gap worth naming:** `SECURITY.md` §1 scopes the policy to exclude "the
Google Apps Script relay deployment". This finding is the key *to* that relay, sitting
in this repository's own HTML. It falls between the two documents — in scope for the
code, out of scope for the policy. That is how it has stayed open since August.

**Fix, in order:**
1. Rotate the key in Apps Script. Assume the current one is public, because it is.
2. Stop sending a shared secret from the browser. The relay should authenticate the
   *user*, not a constant every visitor can read.
3. Purge it from history with `git-filter-repo`.

Step 1 needs Apps Script access and can only be done by the account owner.

## 2. Authentication is client-side only — HIGH (10 pages)

Every protected page guards itself with a `localStorage` read and a redirect:

```js
var s = JSON.parse(localStorage.getItem('bhba_session') || 'null');
```

This hides the page; it does not protect the data. Anyone can set that key in devtools
and walk in. If the Apps Script endpoints do not independently verify the caller, the
redirect is decoration and the data is effectively public.

**Fix:** every endpoint verifies the session server-side and scopes the response to that
user. The client-side guard can stay as a convenience, never as the control.

## 3. No security headers — HIGH

No Content-Security-Policy, X-Frame-Options, Referrer-Policy or HSTS.

**Fix:** set them at the host. These pages use inline `<script>`, so a CSP must allow
them explicitly or every page breaks. Do not paste a strict policy in untested.

## 4. `innerHTML` interpolation — HIGH (37 sites)

Values interpolated into `innerHTML` without an escaping helper. A sample was reviewed:
most carry configuration-derived values (fee labels, certificate options, filter names),
which limits the risk.

The concern is the subset rendering text a *user* typed — player names, team names,
notes, registration fields. Any one of those is a stored-XSS vector: a name entered once
renders as markup for every admin who later opens that list.

**Fix:** add one `esc()` helper and wrap every interpolation of user-entered text.

---

## Not checked here

A static scan cannot settle these. They need testing against the running system with a
second user's credentials, and the gate prints them on every run:

row-level security · record-level access · field tampering · API response shape ·
session cookie flags · password hashing · login rate limiting · bot protection ·
server-side input validation · file upload restrictions · HTTPS enforcement

---

## Why these were not auto-fixed

Rotating the key needs Apps Script access. Moving authentication server-side is an
architectural change to a system in daily use. Dropping in a CSP would break every
inline script on these pages. Each deserves a deliberate change, not a silent commit to
a live portal.
