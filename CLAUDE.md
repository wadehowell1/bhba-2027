# Standing instructions — Wade Howell

## Security gate before any public launch (REQUIRED)

**No application I build ships to a public URL until the checklist below passes.**
This is a gate, not a suggestion. Treat "can we launch?" as "has the gate passed?"

Run the gate, report findings plainly, and state clearly if anything fails. Do not
describe something as ready to launch while an item is outstanding — name what is
outstanding instead.

### Secrets and credentials
- [ ] **Hide API keys** — no key, token or secret in client-side code, HTML, JS, or
      any file served to a browser. Server-side or environment only.
- [ ] **Purge git secrets** — scan history, not just the working tree. A key that was
      ever committed is burned: rotate it, don't just delete the line.
- [ ] **Use the public/anon DB key client-side** — never the service-role or admin key.

### Data access
- [ ] **Enable row-level security** on every table. RLS off is the default failure in
      Supabase/Firebase projects.
- [ ] **Encrypt sensitive data** at rest and in transit.
- [ ] **Lock record access** — a user can read and write only their own records.
      Verify by attempting to fetch another user's ID directly.
- [ ] **Block field tampering** — the server decides role, price, status, balance.
      Never trust a field the client can set.
- [ ] **Trim API responses** — return only the fields the screen needs. No password
      hashes, internal IDs, or adjacent users' data riding along in a payload.

### Authentication and sessions
- [ ] **Enforce server-side auth** — a client-side redirect is not authentication.
      Every protected endpoint checks the session itself.
- [ ] **Secure session cookies** — HttpOnly, Secure, SameSite.
- [ ] **Hash passwords** — bcrypt/argon2, never plaintext, never a fast hash.
- [ ] **Rate limit login** and any credential or OTP endpoint.
- [ ] **Add bot protection** on public forms and signup.

### Input and output
- [ ] **Parameterize queries** — no string-concatenated SQL, ever.
- [ ] **Validate all input** server-side, against an allowlist where possible.
- [ ] **Escape user content** on output — assume every stored string is hostile.
- [ ] **Restrict file uploads** — type, size, and extension; store outside the web
      root; never execute what was uploaded.

### Transport and supply chain
- [ ] **Add security headers** — CSP, X-Content-Type-Options, X-Frame-Options,
      Referrer-Policy, HSTS.
- [ ] **Force HTTPS** — redirect HTTP, set HSTS.
- [ ] **Scan dependencies** for known CVEs before shipping.

### How to apply it
1. Run `/security-review` on the diff, and the project's own gate script if it has one.
2. Work the list above explicitly — the skill does not cover all twenty items.
3. Report: what passed, what failed, what could not be checked and why.
4. A finding in code I did not write still gets reported.

### Reference
These map to the OWASP Top 10: A01 Broken Access Control, A02 Cryptographic Failures,
A03 Injection, A04 Insecure Design, A05 Security Misconfiguration, A06 Vulnerable
Components, A07 Identification & Authentication Failures, A08 Software & Data Integrity,
A09 Logging & Monitoring Failures, A10 SSRF.

---

## Attribution
End commit messages with:
```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J9FSbnYuvXXJfBuh8FqYzf
```
