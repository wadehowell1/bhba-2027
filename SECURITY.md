# Security Policy — BHBA 2027 Tournament Operations Portal

**Version:** 1.0
**Last Updated:** 2026-09-08
**Classification:** PUBLIC
**Owner:** BHBA Systems Administration
**Review cadence:** Quarterly, and within 5 working days of any reported incident

---

## 1. Scope

This policy covers the source code in this repository: the twelve standalone
HTML applications that make up the BHBA 2027 Tournament Operations Portal
(authentication, portal, teams, officials, match forms, scoresheet, jerseys,
finance, fees and fines, communications, MVP tracking, and the system
administration hub), together with the Spec Kit tooling and CI configuration.

It does not cover the Google Apps Script relay deployment, Google Workspace
account security, or any hosting platform configuration. Those are governed
separately by BHBA Systems Administration.

---

## 2. Reporting a Vulnerability

Report suspected vulnerabilities privately. Do **not** open a public GitHub
issue, and do not disclose details publicly until a fix has shipped.

| Route | Detail |
| --- | --- |
| Preferred | GitHub private vulnerability reporting — repository **Security** tab → **Report a vulnerability** |
| Alternate | Direct message to the repository owner (`wadehowell1`) |

Please include: affected file and line, reproduction steps, observed versus
expected behaviour, and your assessment of impact. If you have a suggested
patch, say so — do not attach exploit code for a live system.

### Response commitments

| Stage | Target |
| --- | --- |
| Acknowledgement of report | 3 working days |
| Initial triage and severity assignment | 10 working days |
| Fix or documented mitigation — Critical | 14 calendar days |
| Fix or documented mitigation — High | 30 calendar days |
| Fix or documented mitigation — Medium / Low | Next scheduled release |
| Reporter notified of resolution | Within 5 working days of the fix merging |

Good-faith research is welcome. Do not access, modify or exfiltrate data
belonging to other people, do not degrade service availability, and do not run
automated scanning against production without written permission.

---

## 3. Severity Model

Severity is assigned using CVSS v3.1 base score, adjusted for the portal's
actual deployment context (static client-side applications with no server-side
trust boundary).

| Rating | CVSS v3.1 | Meaning in this portal |
| --- | --- | --- |
| Critical | 9.0 – 10.0 | Credential exposure, or unauthenticated administrative access |
| High | 7.0 – 8.9 | Privilege escalation, stored XSS, broken authentication |
| Medium | 4.0 – 6.9 | Missing hardening control, integrity gap in a dependency |
| Low | 0.1 – 3.9 | Defence-in-depth gap with no direct exploit path |

---

## 4. Controls In Force

| # | Control | Implementation | Standard |
| --- | --- | --- | --- |
| C1 | Secrets excluded from version control | Root `.gitignore`, section 1 | ISO/IEC 27001:2022 A.5.17 |
| C2 | Automated secret and vulnerability scanning | `.github/workflows/security-scan.yml` — every push, every pull request, weekly | ISO/IEC 27001:2022 A.8.8; NIST SP 800-53 RA-5 |
| C3 | Repeatable local scan before commit | `scripts/security-scan.sh` | NIST SP 800-53 RA-5 |
| C4 | Independent secret detection | Gitleaks, full history scan in CI | ISO/IEC 27001:2022 A.8.12 |
| C5 | Personal data excluded from the repository | Root `.gitignore`, section 8 | Jamaica DPA 2020, Eighth Standard |
| C6 | Documented disclosure route | This policy | ISO/IEC 27001:2022 A.5.7 |
| C7 | Security findings register with remediation owners | `docs/security/` | ISO/IEC 27001:2022 A.5.1 |

CI failure on a Critical or High finding is blocking. Merging past a blocking
finding requires a documented, time-bound risk acceptance recorded in
`docs/security/`.

---

## 5. Known Limitations — Read Before Deploying

The portal applications are **client-side only**. They hold identity, role and
session state in browser `localStorage` and perform no server-side
authorisation. In this architecture:

- Any user can alter their own roles and session using browser developer tools.
- No value shipped in the HTML or JavaScript is secret, including API keys.
- Client-side input validation is a usability feature, not a security control.

Until a server-side trust boundary exists, these applications must be treated
as **internal tooling for trusted operators**, not as a public registration
system handling personal data at scale. The open findings and remediation plan
are recorded in `docs/security/BHBA-2027-Security-Assessment-v1.0.md`.

---

## 6. Credential Rotation Procedure

If a credential is found in this repository or its history:

1. **Rotate first.** Revoke and reissue the credential at its provider before
   touching git. Removing a commit does not un-disclose a secret — assume any
   value that reached a public repository is compromised.
2. Redeploy the affected Google Apps Script with the new value, using a script
   property rather than a literal in source.
3. Purge the value from history (`git filter-repo`, or GitHub Support for a
   fork-heavy repository) and force-push with team coordination.
4. Review Apps Script execution logs for unauthorised calls during the exposure
   window.
5. Record the incident, exposure window and actions taken in `docs/security/`.
6. If personal data was accessible during the exposure window, assess
   notification obligations under the Jamaica Data Protection Act 2020 and
   notify the Office of the Information Commissioner where the thresholds in
   the Act are met.

---

## 7. Regulatory Context

Processing of personal data through this portal is subject to the **Jamaica
Data Protection Act 2020**. The Eighth Data Protection Standard requires
appropriate technical and organisational measures against unauthorised or
unlawful processing, accidental loss, destruction or damage. Registrant names,
email addresses, telephone numbers, organisational affiliations and team roster
data all constitute personal data under the Act.

Controls in this repository are additionally mapped to ISO/IEC 27001:2022
Annex A, the OWASP Top 10 (2021), and NIST SP 800-53 Rev. 5.
