# BHBA 2027 Tournament Operations Portal — Security Assessment

| Field | Value |
| --- | --- |
| **Document version** | 1.0 |
| **Last Updated** | 2026-09-08 |
| **Classification** | INTERNAL USE |
| **Assessment type** | Static application security review (white-box, source-code) |
| **Scope** | 12 HTML applications at repository root, `wadehowell1/bhba-2027` |
| **Commit assessed** | `f3641b3` (branch `claude/spec-kit-install-5t24en`) |
| **Method** | Automated scan (`scripts/security-scan.sh` v1.0) plus manual source review |
| **Frameworks applied** | OWASP Top 10 (2021), ISO/IEC 27001:2022 Annex A, NIST SP 800-53 Rev. 5, Jamaica Data Protection Act 2020 |
| **Overall RAG status** | **RED** |
| **Next review** | On closure of all Critical findings, or 2026-12-08, whichever is earlier |

---

## 1. Executive Summary

The portal's twelve applications carry two Critical and four High findings, giving an overall RAG status of **RED**; the portal must not process live registrant data until the Critical items close. The root cause is architectural rather than incidental — all twelve applications are client-side only, holding identity, roles and session state in browser `localStorage` with no server-side authorisation, so every credential shipped in the source is public and every role check is user-editable. A seeded administrator account (`admin@bhba.jm` / `Admin1234!`) and a shared relay API key are both readable in this public repository right now, and the relay key should be rotated today regardless of any other action taken. Detective controls have been established in this change — a root `.gitignore`, a dependency-free scanner, CI enforcement and a disclosure policy — but they detect these conditions rather than remedy them, and the remediation in section 5 remains outstanding.

---

## 2. Assessment Coverage

| Application | Lines | `innerHTML` sinks | Output encoder | Findings |
| --- | --- | --- | --- | --- |
| `bhba_auth.html` | 1,150 | 14 | Yes | F-02, F-03, F-04, F-04b |
| `bhba_officials.html` | 1,154 | 24 | No | F-04, F-05 |
| `bhba_matchform.html` | 1,022 | 25 | No | F-04, F-05 |
| `bhba_finance.html` | 762 | 15 | No | F-05 |
| `bhba_teams.html` | 806 | 15 | Yes | F-08 |
| `bhba_scoresheet.html` | 681 | 9 | No | F-05 |
| `bhba_jerseys.html` | 692 | 11 | No | F-05 |
| `bhba_comms.html` | 669 | 3 | No | F-01, F-04, F-05 |
| `bhba_portal.html` | 578 | 8 | No | F-04, F-05 |
| `bhba_sysadmin_hub.html` | 608 | 10 | Yes | F-01, F-04, F-07 |
| `bhba_fees_fines.html` | 585 | 1 | No | F-05 |
| `bhba_mvp.html` | 478 | 0 | n/a | F-06 only |

All twelve applications share finding F-06 (no Content-Security-Policy).

---

## 3. Findings Register

### F-01 — Shared relay API key hardcoded in client-side source
**Severity: CRITICAL** · CVSS v3.1 8.6 (AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:L/A:N) · RAG: **RED**

| Attribute | Detail |
| --- | --- |
| Location | `bhba_comms.html:624`; `bhba_sysadmin_hub.html:383, 415, 468` |
| Evidence | `const BHBA_API_KEY='BHBA-2027-COMMS-KEY';` |
| Related | Google Apps Script deployment URL committed at `bhba_comms.html:623` and `bhba_sysadmin_hub.html:246` |
| OWASP | A07:2021 Identification and Authentication Failures |
| ISO/IEC 27001:2022 | A.5.17 Authentication information; A.8.12 Data leakage prevention |
| NIST SP 800-53 | IA-5 Authenticator management |

A static shared key and its endpoint are both published in a public repository. Any party can call the communications relay directly — reading messages, sending communications as BHBA, and exercising the administrator `getMessages` path. The key provides no security value whatsoever once shipped to the browser; it functions only as an obscurity measure that has already failed.

**Remediation.** Rotate the key today. Move authentication into Google Apps Script *Script Properties* and authorise callers by verified user identity, not by a shared string. Where a relay must remain publicly callable, apply per-caller rate limiting and log every invocation.

---

### F-02 — Seeded administrator credentials in source
**Severity: CRITICAL** · CVSS v3.1 9.1 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N) · RAG: **RED**

| Attribute | Detail |
| --- | --- |
| Location | `bhba_auth.html:855–864` |
| Evidence | Account `admin@bhba.jm`, password `Admin1234!`, role `bhba_president`, auto-seeded on first load |
| OWASP | A07:2021 Identification and Authentication Failures |
| ISO/IEC 27001:2022 | A.5.17 Authentication information |
| NIST SP 800-53 | IA-5(1) Password-based authentication |

The highest-privilege account in the portal ships with a known password, published in a public repository. Anyone reading this repository can authenticate as BHBA President.

**Remediation.** Remove the seeded account. Provision the first administrator out-of-band and force a password change on first sign-in. If the account exists in any deployed instance, change the password immediately and review activity.

---

### F-03 — Passwords protected by a non-cryptographic 32-bit hash
**Severity: HIGH** · CVSS v3.1 7.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N) · RAG: **RED**

| Attribute | Detail |
| --- | --- |
| Location | `bhba_auth.html:868` |
| Evidence | `function simpleHash(s){let h=0;for(let i=0;i<s.length;i++){h=(h<<5)-h+s.charCodeAt(i);h\|=0;}return h.toString(36);}` |
| OWASP | A02:2021 Cryptographic Failures |
| ISO/IEC 27001:2022 | A.8.24 Use of cryptography |
| NIST SP 800-53 | IA-5(1), SC-28 Protection of information at rest |

This is a DJB-style string hash folded to 32 bits — not a password hash. It is unsalted, has no work factor, and its 2³² output space makes collisions trivial to generate: an attacker does not need the original password, only any string that collides with the stored value. Stored hashes are readable in `localStorage` by any script running on the origin, which finding F-05 makes reachable.

**Remediation.** Password verification must move server-side and use a memory-hard KDF — Argon2id (preferred), scrypt, or bcrypt at cost ≥ 12. No client-side hash is an acceptable substitute. Existing stored hashes cannot be migrated and must be invalidated with a forced password reset.

---

### F-04 — Authentication and authorisation enforced only in the browser
**Severity: HIGH** · CVSS v3.1 8.1 (AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N) · RAG: **RED**

| Attribute | Detail |
| --- | --- |
| Location | `bhba_auth.html:847–852`; consumed in `bhba_portal.html:367,371`, `bhba_matchform.html:9,269`, `bhba_comms.html:9`, `bhba_sysadmin_hub.html:9` |
| Evidence | `bhba_users`, `bhba_session`, `bhba_role_requests` read from and written to `localStorage` |
| OWASP | A01:2021 Broken Access Control |
| ISO/IEC 27001:2022 | A.5.15 Access control; A.8.3 Information access restriction |
| NIST SP 800-53 | AC-3 Access enforcement |

`localStorage` is fully user-writable. Any visitor can open developer tools and rewrite their own session object to grant themselves `bhba_president` — the role gate at `bhba_auth.html` checks `approvedRoles` read from the same store it trusts. The approval workflow (`approvedBy`, `approvedAt`) records intent but enforces nothing.

**Remediation.** Introduce a server-side trust boundary. Every privileged action must be re-authorised on the server against a session the client cannot forge. Until that exists, treat the portal as trusted-operator internal tooling, per section 5 of `SECURITY.md`.

---

### F-04b — Registration self-approves the requested role; no allowlist enforcement
**Severity: HIGH** · CVSS v3.1 8.8 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:L) · RAG: **RED**

| Attribute | Detail |
| --- | --- |
| Location | `bhba_auth.html:897–899` (`selectRole`), `962` (`doRegister` validation), `968` (role persisted) |
| Evidence | `roles:[{role:selectedRole,status:'approved',team,approvedBy:'self',...}]` |
| Design intent | `SELF_REGISTER_ROLES` (line 839) permits 5 roles; `RESTRICTED_ROLES` (line 840) reserves `bhba_president`, `bhba_vp`, `match_commissioner`, `bhba_executive`, `bhba_employee` |
| OWASP | A01:2021 Broken Access Control |
| ISO/IEC 27001:2022 | A.5.15 Access control; A.5.16 Identity management |
| NIST SP 800-53 | AC-2 Account management; AC-6 Least privilege |

Two defects compound here. First, every self-registration is written with `status:'approved'` and `approvedBy:'self'` — the approval workflow is recorded but never actually executed, so a registrant is approved at the moment of registration.

Second, the restriction to `SELF_REGISTER_ROLES` exists only in the rendering loop at line 889. `selectRole()` assigns `selectedRole` with no allowlist check, and `doRegister()` validates only that the value is non-empty (`if(!selectedRole)`, line 962). `RESTRICTED_ROLES` is declared but never enforced anywhere in the file.

**Reproduction** — no storage tampering required, two console statements:

```javascript
selectRole('bhba_president');   // not offered in the UI; accepted anyway
// complete the registration form, submit
```

The resulting account holds tier `exec_senior`, satisfying the `isExec` check at line 989 and unlocking the executive dashboard and approval queue.

**Remediation.** As an immediate client-side hardening step, validate in `doRegister()` that `SELF_REGISTER_ROLES.includes(selectedRole)`, and set `status:'pending'` with `approvedBy:null` for every self-registration so the approval queue is actually traversed. Note this narrows the attack surface but does not close the finding — a client-side check is bypassable by definition, and full closure depends on the server-side authorisation in F-04.

---

### F-05 — Stored cross-site scripting via unencoded `innerHTML`
**Severity: HIGH** · CVSS v3.1 7.3 (AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N) · RAG: **RED**

| Attribute | Detail |
| --- | --- |
| Confirmed sink | `bhba_portal.html:399` — `` innerHTML=`👤 <strong>${u.name\|\|u.email}</strong>` `` |
| Exposure | 8 of 11 applications using `innerHTML` define no output encoder: 96 sinks in total (`matchform` 25, `officials` 24, `finance` 15, `jerseys` 11, `scoresheet` 9, `portal` 8, `comms` 3, `fees_fines` 1) |
| Encoders present | `bhba_auth.html`, `bhba_sysadmin_hub.html`, `bhba_teams.html` only |
| OWASP | A03:2021 Injection |
| ISO/IEC 27001:2022 | A.8.28 Secure coding |
| NIST SP 800-53 | SI-10 Information input validation |

`u.name` is attacker-controlled — it is free text supplied at registration (`bhba_auth.html:949`), stored, then interpolated into `innerHTML` without encoding. A registrant whose name is `<img src=x onerror=...>` achieves script execution in the origin of every user who views the portal. Combined with F-03 and F-04, an injected script can read the entire `bhba_users` store, including password hashes.

**Remediation.** Prefer `textContent` for all interpolated values. Where markup is genuinely required, route every interpolation through an escaping helper — the pattern already present in `bhba_teams.html` (`esc()`) should be extracted to a shared include and applied across the remaining eight applications. F-06 provides defence in depth.

---

### F-06 — No Content-Security-Policy on any application
**Severity: MEDIUM** · CVSS v3.1 5.3 · RAG: **AMBER**

| Attribute | Detail |
| --- | --- |
| Location | All 12 HTML applications |
| OWASP | A05:2021 Security Misconfiguration |
| ISO/IEC 27001:2022 | A.8.8 Management of technical vulnerabilities |
| NIST SP 800-53 | SC-18 Mobile code |

No application declares a CSP, `X-Frame-Options`/`frame-ancestors`, or `Referrer-Policy`. For a static deployment, a CSP `<meta>` tag is the primary compensating control against F-05 and the only practical clickjacking defence.

**Remediation.** Add to each application's `<head>`, tightened per application:

```html
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self';
               script-src 'self' https://cdn.tailwindcss.com;
               style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
               font-src https://fonts.gstatic.com;
               connect-src https://script.google.com;
               img-src 'self' data:;
               frame-ancestors 'none';
               base-uri 'self';
               form-action 'self'">
<meta name="referrer" content="strict-origin-when-cross-origin">
```

Removing inline `<script>` blocks so `script-src` can drop to `'self'` alone is the target end state; that is a larger refactor and should be scheduled separately.

---

### F-07 — Third-party script loaded without Subresource Integrity
**Severity: MEDIUM** · CVSS v3.1 5.9 · RAG: **AMBER**

| Attribute | Detail |
| --- | --- |
| Location | `bhba_sysadmin_hub.html:19` — `<script src="https://cdn.tailwindcss.com">` |
| OWASP | A08:2021 Software and Data Integrity Failures |
| ISO/IEC 27001:2022 | A.8.28 Secure coding |
| NIST SP 800-53 | SI-7 Software, firmware and information integrity |

The Tailwind play CDN is unpinned and unverified: a CDN compromise executes arbitrary code inside the administration hub — the highest-privilege application in the portal. The play CDN compiles at runtime and does not support a stable SRI hash, so pinning alone is insufficient.

**Remediation.** Build Tailwind ahead of time and vendor the resulting stylesheet into the repository, removing the runtime script entirely. This also removes the `script-src` CDN exception in F-06. The play CDN is explicitly not intended for production use.

---

### F-08 — Personal data processed without a documented lawful basis or retention rule
**Severity: MEDIUM** · RAG: **AMBER**

| Attribute | Detail |
| --- | --- |
| Data collected | Registrant name, email address, telephone number, organisation, team affiliation (captured `bhba_auth.html:949–954`, persisted `965–970`); company TRN / registration number (`bhba_teams.html:355–356, 475`); team roster records |
| Storage | Unencrypted browser `localStorage`, no expiry, no erasure mechanism |
| Regulation | Jamaica Data Protection Act 2020 — Eighth Standard (security), Fifth Standard (retention), data subject access and erasure rights |
| ISO/IEC 27001:2022 | A.5.34 Privacy and protection of PII; A.8.12 Data leakage prevention |

Registrant contact details are personal data under the Act. They are held indefinitely in unencrypted client storage with no stated lawful basis, no retention period, and no mechanism to service an access or erasure request. Findings F-04 and F-05 make that store readable by an attacker.

Assessed as MEDIUM rather than HIGH on the basis that no health records or dates of birth are collected — the "Medical Levy" references in `bhba_fees_fines.html` and `bhba_finance.html` are fee line items, not health data, and no date-of-birth field exists in any application. Should the portal later collect data on players under 18, this finding escalates to HIGH and requires a Data Protection Impact Assessment before deployment.

**Remediation.** Publish a privacy notice stating lawful basis, retention period and data subject rights. Define and enforce a retention rule. Provide an erasure path. Register with the Office of the Information Commissioner if not already registered.

---

### F-09 — No repository security governance *(CLOSED in this change)*
**Severity: LOW** · RAG: **GREEN**

No `.gitignore`, no disclosure policy, no automated scanning existed prior to this change. All three are now in place — see section 4.

---

## 4. Controls Implemented in This Change

| Control | Artefact | Finding addressed | Standard |
| --- | --- | --- | --- |
| Secrets excluded from version control | `.gitignore` §1–2 | F-09, preventive for F-01 | ISO A.5.17 |
| Personal-data extracts excluded | `.gitignore` §8 | Preventive for F-08 | DPA 2020, Eighth Standard |
| Dependency-free repeatable scanner | `scripts/security-scan.sh` | Detective for F-01→F-08 | NIST RA-5 |
| CI enforcement, blocking on Critical/High | `.github/workflows/security-scan.yml` | F-09 | ISO A.8.8 |
| Full-history secret detection (Gitleaks) | Same workflow, `secret-scan` job | Detective for F-01 | ISO A.8.12 |
| Dependency review on pull requests | Same workflow, `dependency-review` job | Preventive for F-07 | ISO A.8.28 |
| Vulnerability disclosure policy | `SECURITY.md` | F-09 | ISO A.5.7 |
| Findings register with owners and dates | This document | F-09 | ISO A.5.1 |

**These are detective and preventive controls. They do not remediate F-01 through F-08.**

---

## 5. Remediation Plan

| ID | Action | Priority | Target | Gate |
| --- | --- | --- | --- | --- |
| F-01 | Rotate `BHBA-2027-COMMS-KEY`; move to Apps Script Properties | P0 | Immediate | Systems Administration |
| F-02 | Remove seeded admin account; provision out-of-band | P0 | 7 days | Systems Administration |
| F-04b | Enforce `SELF_REGISTER_ROLES` allowlist; set self-registrations to `status:'pending'` | P0 | 7 days | Development |
| F-05 | Extract `esc()` to a shared include; apply across 8 applications | P1 | 14 days | Development |
| F-06 | Add CSP and `Referrer-Policy` meta tags to all 12 applications | P1 | 14 days | Development |
| F-07 | Vendor a pre-built Tailwind stylesheet; drop the play CDN | P1 | 14 days | Development |
| F-03 | Server-side Argon2id password verification; force reset | P2 | 30 days | Architecture decision required |
| F-04 | Server-side trust boundary and authorisation | P2 | 90 days | Architecture decision required |
| F-08 | Privacy notice, retention rule, erasure path | P2 | 30 days | BHBA Executive |

F-03 and F-04 cannot be closed within the current architecture. Both require a decision on whether to retain a static client-side portal — in which case the portal must be restricted to trusted operators on a private deployment — or to introduce a backend. That decision is an executive one, not a development one, and it gates roughly half this register.

### Critical path

```
F-01 rotate key ──┐
F-02 remove seed ─┤
F-04b role gate ──┴─► portal safe for trusted-operator internal use
                        │
                        ├─► F-05 + F-06 + F-07 ──► portal hardened against XSS/CDN
                        │
                        └─► ARCHITECTURE DECISION ──► F-03 + F-04 ──► portal safe
                                                                      for public
                                                                      registration
                                                             │
                                                    F-08 ────┴──► DPA 2020 compliant
```

---

## 6. Risk Register

| Risk | Likelihood | Impact | Inherent | Mitigation | Residual |
| --- | --- | --- | --- | --- | --- |
| Relay key abused to send communications as BHBA | High | High | **RED** | F-01 rotation, rate limiting, call logging | AMBER |
| Unauthorised administrative access via seeded account | High | High | **RED** | F-02 removal, activity review | GREEN |
| Registrant self-elevates to executive role via `selectRole()` | High | High | **RED** | F-04b allowlist + pending status (partial), F-04 server-side authorisation (full) | AMBER after F-04b; RED until architecture decision |
| Stored XSS harvests the registrant store | Medium | High | **RED** | F-05 encoding, F-06 CSP | AMBER |
| Tailwind CDN compromise executes in admin hub | Low | High | AMBER | F-07 vendoring | GREEN |
| DPA 2020 enforcement following a personal-data breach | Medium | High | **RED** | F-08 notice and retention, F-04/F-05 closure | AMBER |
| Future secret committed to the repository | Medium | High | AMBER | `.gitignore`, Gitleaks in CI | GREEN |

---

## 7. Verification Method

| Check | Tool | Result |
| --- | --- | --- |
| Provider-format credentials (JWT, AWS, GCP, Stripe, GitHub, Slack, GitLab, PEM) | `security-scan.sh` SEC-01 | Pass — none found |
| Hardcoded application secrets | SEC-02 | **2 Critical** |
| Weak credential hashing | SEC-03 | **1 High** |
| Client-side authorisation state | SEC-04 | **1 High** |
| Self-approving role assignment | SEC-04b | **1 High** |
| XSS sinks and dynamic code execution | SEC-05 | **1 High**; no `eval`/`document.write` |
| Security headers | SEC-06 | 1 Medium |
| Subresource Integrity | SEC-07 | 1 Medium |
| Cleartext HTTP | SEC-08 | Pass |
| Reverse-tabnabbing | SEC-09 | Pass |
| Personal-data extracts committed | SEC-10 | Pass |
| Governance artefacts | SEC-11 | Pass after this change |

Final scanner state on commit: **2 Critical, 4 High, 2 Medium, 0 Low, 9 passed — exit code 1 (RED)**.
The scanner reports 2 Medium against the register's 3 because F-08 (personal data governance) has no
automatable signature and is a manual finding. F-09 is closed by this change.

Reproduce with `./scripts/security-scan.sh`. Manual review additionally confirmed no `eval`, `document.write`, `new Function`, cleartext transport, or reflected-parameter DOM injection — the single `URLSearchParams` use at `bhba_matchform.html:1005` assigns to `.value`, not to `innerHTML`, and is safe.

---

## 8. Revision History

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 1.0 | 2026-09-08 | Systems Administration | Initial assessment; 2 Critical, 4 High, 3 Medium, 1 Low. Detective controls implemented. |
