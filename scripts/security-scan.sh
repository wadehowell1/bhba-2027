#!/usr/bin/env bash
# ==============================================================================
# BHBA 2027 — Repository Security Scanner
# Version: 1.0 | Last Updated: 2026-09-08 | Classification: INTERNAL USE
#
# Dependency-free (bash + grep + find) static security scan for the BHBA 2027
# Tournament Operations Portal. Runs identically on a developer workstation and
# in GitHub Actions.
#
# Usage:
#   ./scripts/security-scan.sh              # scan, human-readable output
#   ./scripts/security-scan.sh --quiet      # findings only, no PASS lines
#   ./scripts/security-scan.sh --strict     # exit 1 on MEDIUM as well as HIGH
#
# Exit codes:
#   0  no blocking findings
#   1  at least one CRITICAL/HIGH finding (or MEDIUM under --strict)
#   2  invalid invocation
#
# Control mapping:
#   OWASP Top 10 2021           A01, A02, A03, A05, A07, A08
#   ISO/IEC 27001:2022          A.5.17, A.8.8, A.8.12, A.8.24, A.8.28
#   NIST SP 800-53 Rev. 5       IA-5, SI-10, SC-28, RA-5
#   Jamaica Data Protection Act 2020 — Eighth Standard (security of personal data)
# ==============================================================================

set -uo pipefail

QUIET=0
STRICT=0
for arg in "$@"; do
  case "$arg" in
    --quiet)  QUIET=1 ;;
    --strict) STRICT=1 ;;
    --help|-h)
      sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *)
      printf 'Unknown option: %s (try --help)\n' "$arg" >&2
      exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 2

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_RED=$'\033[31m'; C_YEL=$'\033[33m'; C_GRN=$'\033[32m'
  C_BLU=$'\033[34m'; C_BLD=$'\033[1m'; C_OFF=$'\033[0m'
else
  C_RED=''; C_YEL=''; C_GRN=''; C_BLU=''; C_BLD=''; C_OFF=''
fi

CRITICAL=0; HIGH=0; MEDIUM=0; LOW=0; PASSED=0

# Files under version control that we scan. Excludes tooling directories so
# Spec Kit's own templates do not generate false positives.
scan_targets() {
  find . \
    -path ./.git -prune -o \
    -path ./.specify -prune -o \
    -path ./.claude -prune -o \
    -path ./node_modules -prune -o \
    -path ./scripts -prune -o \
    -path ./docs -prune -o \
    -type f \( -name '*.html' -o -name '*.htm' -o -name '*.js' -o -name '*.json' -o -name '*.md' \) \
    -print
}

hdr() { printf '\n%s%s%s\n' "$C_BLD$C_BLU" "$1" "$C_OFF"; }

finding() {
  # finding <SEVERITY> <CHECK-ID> <TITLE> <DETAIL>
  local sev="$1" id="$2" title="$3" detail="$4" colour
  case "$sev" in
    CRITICAL) colour="$C_RED"; CRITICAL=$((CRITICAL+1)) ;;
    HIGH)     colour="$C_RED"; HIGH=$((HIGH+1)) ;;
    MEDIUM)   colour="$C_YEL"; MEDIUM=$((MEDIUM+1)) ;;
    LOW)      colour="$C_YEL"; LOW=$((LOW+1)) ;;
  esac
  printf '%s[%s]%s %s — %s\n' "$colour" "$sev" "$C_OFF" "$id" "$title"
  printf '%s\n' "$detail" | sed 's/^/         /'
}

pass() {
  PASSED=$((PASSED+1))
  [ "$QUIET" -eq 1 ] && return 0
  printf '%s[PASS]%s %s — %s\n' "$C_GRN" "$C_OFF" "$1" "$2"
}

printf '%s\n' "=============================================================="
printf '%s\n' " BHBA 2027 Repository Security Scan"
printf '%s\n' " Scanner v1.0  |  $(date -u '+%Y-%m-%d %H:%M UTC')"
printf '%s\n' "=============================================================="

# ------------------------------------------------------------------------------
hdr "SEC-01  Committed secrets (high-entropy / provider key formats)"
# OWASP A07 | ISO A.5.17 | NIST IA-5
# ------------------------------------------------------------------------------
KEY_RE='(eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})|(AKIA[0-9A-Z]{16})|(AIza[0-9A-Za-z_-]{35})|(sk_(live|test)_[0-9a-zA-Z]{16,})|(gh[pousr]_[A-Za-z0-9]{30,})|(xox[baprs]-[0-9A-Za-z-]{10,})|(-----BEGIN [A-Z ]*PRIVATE KEY-----)|(glpat-[0-9A-Za-z_-]{20,})'
KEY_HITS="$(scan_targets | xargs -r grep -nEo "$KEY_RE" 2>/dev/null)"
if [ -n "$KEY_HITS" ]; then
  finding CRITICAL "SEC-01" "Provider credential committed to the repository" \
    "$(printf '%s' "$KEY_HITS" | cut -c1-120)
Rotate the credential at its provider before removing it from git history."
else
  pass "SEC-01" "No provider-format credentials found in tracked files"
fi

# ------------------------------------------------------------------------------
hdr "SEC-02  Hardcoded application secrets and default credentials"
# OWASP A07 | ISO A.5.17 | NIST IA-5
# ------------------------------------------------------------------------------
SECRET_RE="(const|let|var)[[:space:]]+[A-Za-z_]*(API_?KEY|APIKEY|SECRET|PASSCODE|PASSWORD|TOKEN)[A-Za-z_]*[[:space:]]*=[[:space:]]*['\"][^'\"]{4,}['\"]|(apiKey|api_key|passcode|password|secret|token)[[:space:]]*:[[:space:]]*['\"][^'\"]{4,}['\"]"
SECRET_HITS="$(scan_targets | xargs -r grep -nEo "$SECRET_RE" 2>/dev/null | grep -viE "['\"](\\\$\{|undefined|null|''|\"\"|placeholder|example|xxx+|\.\.\.)" )"
if [ -n "$SECRET_HITS" ]; then
  finding CRITICAL "SEC-02" "Hardcoded secret literal in client-side source" \
    "$(printf '%s' "$SECRET_HITS" | cut -c1-140)
Any value shipped in client-side HTML/JS is public. Move server-side."
else
  pass "SEC-02" "No hardcoded secret literals detected"
fi

DEFAULT_CRED_RE="simpleHash\('[^']+'\)|passHash[[:space:]]*:[[:space:]]*['\"][^'\"]+['\"]|password[[:space:]]*[:=][[:space:]]*['\"](admin|Admin|password|Password|changeme|letmein)[^'\"]*['\"]"
DEFAULT_HITS="$(scan_targets | xargs -r grep -nEo "$DEFAULT_CRED_RE" 2>/dev/null)"
if [ -n "$DEFAULT_HITS" ]; then
  finding CRITICAL "SEC-02b" "Default or seeded account credential in source" \
    "$(printf '%s' "$DEFAULT_HITS" | cut -c1-140)
Seeded administrator credentials in a public repository grant anyone admin access."
else
  pass "SEC-02b" "No seeded/default account credentials detected"
fi

# ------------------------------------------------------------------------------
hdr "SEC-03  Weak or non-cryptographic password handling"
# OWASP A02 | ISO A.8.24 | NIST SC-28
# ------------------------------------------------------------------------------
WEAK_HASH_HITS="$(scan_targets | xargs -r grep -nE 'function[[:space:]]+simpleHash|\bmd5\(|\bsha1\(|btoa\([^)]*pass' 2>/dev/null | cut -c1-140)"
if [ -n "$WEAK_HASH_HITS" ]; then
  finding HIGH "SEC-03" "Non-cryptographic or obsolete hash used for credentials" \
    "$WEAK_HASH_HITS
Passwords require a memory-hard KDF (bcrypt, scrypt, Argon2id) applied server-side."
else
  pass "SEC-03" "No weak credential hashing primitives detected"
fi

# ------------------------------------------------------------------------------
hdr "SEC-04  Client-side trust boundary (authn/authz in browser storage)"
# OWASP A01 | ISO A.5.15 | NIST AC-3
# ------------------------------------------------------------------------------
CLIENT_AUTH_HITS="$(scan_targets | xargs -r grep -nEo "(localStorage|sessionStorage)\.(get|set)Item\(['\"][^'\"]*(user|session|role|auth|admin|perm)[^'\"]*['\"]" 2>/dev/null | cut -c1-140)"
if [ -n "$CLIENT_AUTH_HITS" ]; then
  finding HIGH "SEC-04" "Identity, role or session state held in browser storage" \
    "$(printf '%s' "$CLIENT_AUTH_HITS" | head -12)
Browser storage is user-writable. Any visitor can self-elevate via developer tools.
Authorisation decisions must be re-validated server-side."
else
  pass "SEC-04" "No authorisation state found in client-side storage"
fi

SELF_APPROVE="$(scan_targets | xargs -r grep -nEo "status[[:space:]]*:[[:space:]]*['\"]approved['\"][^}]*approvedBy[[:space:]]*:[[:space:]]*['\"]self['\"]|approvedBy[[:space:]]*:[[:space:]]*['\"]self['\"]" 2>/dev/null | cut -c1-140)"
if [ -n "$SELF_APPROVE" ]; then
  finding HIGH "SEC-04b" "Self-granted role recorded as already approved" \
    "$SELF_APPROVE
Registration writes an approved role without traversing the approval workflow.
Set self-registrations to a pending status and enforce the permitted-role
allowlist at submission, not only in the rendering loop."
else
  pass "SEC-04b" "No self-approving role assignment detected"
fi

# ------------------------------------------------------------------------------
hdr "SEC-05  Cross-site scripting sinks without output encoding"
# OWASP A03 | ISO A.8.28 | NIST SI-10
# ------------------------------------------------------------------------------
XSS_FILES=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if grep -q 'innerHTML' "$f" 2>/dev/null && ! grep -qEi 'function[[:space:]]+(esc|escapeHtml|escHtml|sanitize)' "$f" 2>/dev/null; then
    n="$(grep -c 'innerHTML' "$f" 2>/dev/null)"
    XSS_FILES="${XSS_FILES}${f} (${n} sinks, no output encoder defined)
"
  fi
done <<< "$(scan_targets)"
if [ -n "$XSS_FILES" ]; then
  finding HIGH "SEC-05" "innerHTML assignment without a defined output encoder" \
    "$(printf '%s' "$XSS_FILES")
Interpolating stored or user-supplied values into innerHTML permits stored XSS.
Use textContent, or route every interpolation through an HTML-escaping helper."
else
  pass "SEC-05" "All files using innerHTML define an output encoder"
fi

DANGEROUS="$(scan_targets | xargs -r grep -nE '\beval\(|document\.write\(|new Function\(|dangerouslySetInnerHTML' 2>/dev/null | cut -c1-140)"
if [ -n "$DANGEROUS" ]; then
  finding HIGH "SEC-05b" "Dynamic code execution sink present" "$DANGEROUS"
else
  pass "SEC-05b" "No eval/document.write/new Function sinks"
fi

# ------------------------------------------------------------------------------
hdr "SEC-06  Browser security headers / hardening meta tags"
# OWASP A05 | ISO A.8.8 | NIST SC-18
# ------------------------------------------------------------------------------
MISSING_CSP=""
while IFS= read -r f; do
  case "$f" in *.html|*.htm) ;; *) continue ;; esac
  grep -qi 'Content-Security-Policy' "$f" 2>/dev/null || MISSING_CSP="${MISSING_CSP}${f}
"
done <<< "$(scan_targets)"
if [ -n "$MISSING_CSP" ]; then
  finding MEDIUM "SEC-06" "No Content-Security-Policy meta tag" \
    "$(printf '%s' "$MISSING_CSP")
A CSP is the primary compensating control against XSS in a static deployment."
else
  pass "SEC-06" "Every HTML document declares a Content-Security-Policy"
fi

# ------------------------------------------------------------------------------
hdr "SEC-07  Third-party script integrity"
# OWASP A08 | ISO A.8.28 | NIST SI-7
# ------------------------------------------------------------------------------
NO_SRI="$(scan_targets | xargs -r grep -noE '<script[^>]+src="https?://[^"]+"[^>]*>' 2>/dev/null | grep -v 'integrity=' | cut -c1-160)"
if [ -n "$NO_SRI" ]; then
  finding MEDIUM "SEC-07" "Remote script loaded without Subresource Integrity" \
    "$NO_SRI
A compromised CDN executes arbitrary code in the portal's origin. Pin a version
and add integrity + crossorigin, or vendor the asset into the repository."
else
  pass "SEC-07" "All remote scripts carry Subresource Integrity hashes"
fi

# ------------------------------------------------------------------------------
hdr "SEC-08  Insecure transport"
# OWASP A02 | ISO A.8.24 | NIST SC-8
# ------------------------------------------------------------------------------
HTTP_HITS="$(scan_targets | xargs -r grep -noE 'src="http://[^"]+"|href="http://[^"]+"|url\("?http://[^")]+' 2>/dev/null | grep -v 'www.w3.org' | cut -c1-140)"
if [ -n "$HTTP_HITS" ]; then
  finding MEDIUM "SEC-08" "Resource loaded over cleartext HTTP" "$HTTP_HITS"
else
  pass "SEC-08" "No cleartext HTTP resource references (XML namespaces excluded)"
fi

# ------------------------------------------------------------------------------
hdr "SEC-09  Reverse-tabnabbing"
# OWASP A05 | ISO A.8.28
# ------------------------------------------------------------------------------
TABNAB="$(scan_targets | xargs -r grep -noE '<a [^>]*target="_blank"[^>]*>' 2>/dev/null | grep -v 'noopener' | cut -c1-140)"
if [ -n "$TABNAB" ]; then
  finding LOW "SEC-09" "target=\"_blank\" without rel=\"noopener noreferrer\"" "$TABNAB"
else
  pass "SEC-09" "All new-tab links carry rel=noopener"
fi

# ------------------------------------------------------------------------------
hdr "SEC-10  Personal data exposure (Jamaica DPA 2020)"
# DPA 2020 Eighth Standard | ISO A.8.12 | NIST SC-28
# ------------------------------------------------------------------------------
PII_FILES="$(find . -path ./.git -prune -o -type f \( -name '*.csv' -o -name '*.xlsx' -o -name '*.db' -o -name '*.sqlite*' \) -print 2>/dev/null)"
if [ -n "$PII_FILES" ]; then
  finding HIGH "SEC-10" "Data file present in repository — verify it holds no personal data" \
    "$PII_FILES
Jamaica Data Protection Act 2020 prohibits unsecured processing of personal data."
else
  pass "SEC-10" "No spreadsheet or database extracts committed"
fi

if [ -f .gitignore ] && grep -q 'Jamaica Data Protection Act' .gitignore 2>/dev/null; then
  pass "SEC-10b" "Root .gitignore excludes personal-data extracts"
else
  finding MEDIUM "SEC-10b" "Root .gitignore missing personal-data exclusions" \
    "Add exclusions for *.csv extracts, *.db and exports/ directories."
fi

# ------------------------------------------------------------------------------
hdr "SEC-11  Repository security governance"
# ISO A.5.1, A.5.7 | NIST RA-5
# ------------------------------------------------------------------------------
[ -f SECURITY.md ] \
  && pass "SEC-11" "SECURITY.md vulnerability disclosure policy present" \
  || finding LOW "SEC-11" "No SECURITY.md" "Publish a vulnerability disclosure route."
[ -f .gitignore ] \
  && pass "SEC-11b" "Root .gitignore present" \
  || finding HIGH "SEC-11b" "No root .gitignore" "Credentials may be committed accidentally."
[ -f .github/workflows/security-scan.yml ] \
  && pass "SEC-11c" "Automated security scanning configured in CI" \
  || finding MEDIUM "SEC-11c" "No CI security scan" "Scanning is manual and therefore skippable."

# ------------------------------------------------------------------------------
printf '\n%s\n' "=============================================================="
printf '%s\n' " RESULTS"
printf '%s\n' "=============================================================="
printf ' %sCRITICAL%s : %d\n' "$C_RED" "$C_OFF" "$CRITICAL"
printf ' %sHIGH%s     : %d\n' "$C_RED" "$C_OFF" "$HIGH"
printf ' %sMEDIUM%s   : %d\n' "$C_YEL" "$C_OFF" "$MEDIUM"
printf ' %sLOW%s      : %d\n' "$C_YEL" "$C_OFF" "$LOW"
printf ' %sPASSED%s   : %d\n' "$C_GRN" "$C_OFF" "$PASSED"

BLOCKING=$((CRITICAL + HIGH))
[ "$STRICT" -eq 1 ] && BLOCKING=$((BLOCKING + MEDIUM))

if [ "$BLOCKING" -gt 0 ]; then
  printf '\n%sRAG STATUS: RED%s — %d blocking finding(s). See docs/security/ for the remediation plan.\n' \
    "$C_RED$C_BLD" "$C_OFF" "$BLOCKING"
  exit 1
fi
if [ "$((MEDIUM + LOW))" -gt 0 ]; then
  printf '\n%sRAG STATUS: AMBER%s — no blocking findings; %d advisory item(s) open.\n' \
    "$C_YEL$C_BLD" "$C_OFF" "$((MEDIUM + LOW))"
  exit 0
fi
printf '\n%sRAG STATUS: GREEN%s — all checks passed.\n' "$C_GRN$C_BLD" "$C_OFF"
exit 0
