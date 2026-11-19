# Open security findings

Produced by `python3 tools/security_gate.py` against `main` on 2026-11-19.

This is the findings register. The governance policy lives in [`SECURITY.md`](SECURITY.md)
and is not changed by this document.

**Status: BLOCKED — 2 blockers, 48 high.** These pages are already deployed, so these
are live exposures rather than pre-launch theory. The API-key blocker below was first
reported on 2026-11-03 and is unchanged. The seeded-administrator blocker was closed on
2026-11-19 and is recorded in "Closed" at the foot of this document.

---

## 1. Shared API key hardcoded in browser-served HTML — BLOCKER

Four sites across two files, both served to the browser, sent to the Google Apps
Script relay:

| File | Lines |
|---|---|
| `bhba_sysadmin_hub.html` | 383, 415, 468 |
| `bhba_comms.html` | 624 |

An earlier version of this register listed only the three in `bhba_sysadmin_hub.html`.
The fourth was found by the repository's own `scripts/security-scan.sh`. The rotation
covers both files.

Anyone who opens the page and views source has this key. If the relay accepts it as
authorization, any visitor can drive the SysAdmin Email Hub — including sending mail
that appears to come from the association. That is a phishing vector carrying BHBA's
return address.

It is in git history from `9979662` onward, so deleting the lines does not remove it.
Note that the Gitleaks CI job passes on this: the key is neither token-shaped nor
high-entropy, so secret scanning does not catch it. A green secret scan is not evidence
this repository holds no secrets.

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

---

# Closed

## Seeded administrator credential — BLOCKER, closed 2026-11-19

`bhba_auth.html` seeded the account `admin@bhba.jm` with a weak default password held
as a literal in its own source, hashed with `simpleHash`, and the role `bhba_president`
already marked `approved` by `system`. The same credential was printed on the sign-in
screen itself, in a `.demo-hint` block, so it was shown to every visitor rather than
merely being readable in source.

The password value is deliberately not repeated here. It is recoverable from git
history before `cb14d1e` for anyone who needs it for incident response; a register that
restates it would keep republishing it, and would trip the repository's own SEC-02b
rule on this file.

**Why replacing the password would not have fixed it.** Three reasons, each sufficient:

1. The user store is `localStorage` in the visitor's own browser. There is no server. A
   new password literal would be just as public as the old one.
2. `simpleHash` is a 32-bit non-cryptographic hash (`bhba_auth.html`, SEC-03).
   Collisions are findable in seconds, so any stored hash admits passwords other than
   the intended one.
3. The credential is in git history. It is burned whatever the current source says.

**What was done instead:**

- The seeding block is removed. No account is created from source, and no password
  literal remains in the file.
- A purge block removes `admin@bhba.jm` from browsers that seeded it on an earlier
  visit, and clears that account's session if it is the one signed in. Without this the
  change would have been cosmetic: deleting the literal does not reach a browser that
  already holds the account.
- The seeded account is identified by its `approvedBy:'system'` role marker, which no
  other code path writes — registration writes `'self'`, an approval writes the
  approver's id. An `admin@bhba.jm` that the association registered itself is therefore
  left alone.
- The `.demo-hint` block and its now-unused CSS are removed.

**No lockout.** Registration self-approves any requested role including
`bhba_president` (see finding 4, SEC-04b), so an administrator account is created
through the normal Create Account flow with a password that never appears in source.
That self-approval is itself an open finding; closing it will require a real approval
path, at which point first-administrator provisioning needs deliberate design.

**What this does not fix.** The account is no longer a *published default*, which is
what made it a blocker. It is not *secure*: client-side authentication has no security
boundary, and anyone can still write their own admin record straight into
`localStorage` from the browser console. That is findings 2, 4 and SEC-03, all open.

One specific limit worth stating: the purge runs in `bhba_auth.html`, so a browser
already signed in as the seeded admin has its session cleared when it next loads the
sign-in page. The other pages read `bhba_session` directly and do not clear it, so a
stale session there survives until that visit. Fixing that properly means validating
sessions somewhere other than the browser, which is finding 2.

Verified: `scripts/security-scan.sh` SEC-02b clears, criticals 2 → 1; the purge logic
passes 11 behavioural tests covering a seeded browser, a clean browser, other users'
accounts and sessions, a self-registered `admin@bhba.jm`, repeat loads and malformed
records.
