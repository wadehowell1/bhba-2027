#!/usr/bin/env python3
"""Pre-launch security gate. Static checks against the launch checklist.

    python3 tools/security_gate.py            # scan the repo
    python3 tools/security_gate.py --json
    python3 tools/security_gate.py --path .   # scan elsewhere

Exits non-zero if any BLOCKER is found.

WHAT THIS IS: a static scanner that catches the mistakes that are visible in
source. It covers maybe half the checklist.

WHAT THIS IS NOT: proof the app is secure. Row-level security, server-side
authorization, record-level access and field tampering can only be verified by
testing a running system with a second user's credentials. Those are reported
as MANUAL and must be checked by hand before launch.

A clean run means "nothing obviously broken in the source", never "safe to ship".
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

# ── patterns ───────────────────────────────────────────────────────────────

SECRET_PATTERNS = [
    (r'AIza[0-9A-Za-z_\-]{35}', "Google API key"),
    (r'sk-[A-Za-z0-9]{20,}', "OpenAI-style secret key"),
    (r'sk_live_[0-9a-zA-Z]{24,}', "Stripe live secret key"),
    (r'xox[baprs]-[0-9A-Za-z\-]{10,}', "Slack token"),
    (r'ghp_[0-9A-Za-z]{36}', "GitHub personal access token"),
    (r'github_pat_[0-9A-Za-z_]{40,}', "GitHub fine-grained PAT"),
    (r'AKIA[0-9A-Z]{16}', "AWS access key ID"),
    (r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', "private key"),
    (r'eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.', "JWT (check if it is a service key)"),
    (r'service_role', "Supabase service_role key reference"),
    (r'(?i)\b(?:api[_\-]?key|secret|password|passwd|token)\s*[:=]\s*["\'][^"\'\s]{12,}["\']',
     "hardcoded credential"),
]

CLIENT_EXT = {".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
             "build", ".next", ".cache", "vendor"}
SKIP_FILES = {".env.example", "security_gate.py", "CLAUDE.md", "SECURITY.md"}

SQL_CONCAT = re.compile(
    r'(?i)(?:execute|query|cursor\.execute|db\.query|\.raw)\s*\(\s*[^)]*?'
    r'(?:["\'][^"\']*(?:SELECT|INSERT|UPDATE|DELETE)[^"\']*["\']\s*(?:\+|%|\.format\(|f["\'])'
    r'|f["\'][^"\']*(?:SELECT|INSERT|UPDATE|DELETE))')

DANGEROUS_SINKS = [
    (r'\.innerHTML\s*=(?!\s*["\'`]\s*["\'`])', "innerHTML assignment — escape or use textContent"),
    (r'document\.write\s*\(', "document.write — XSS sink"),
    (r'\beval\s*\(', "eval()"),
    (r'dangerouslySetInnerHTML', "dangerouslySetInnerHTML"),
    (r'new\s+Function\s*\(', "new Function()"),
]

CLIENT_AUTH_ONLY = [
    (r'(?i)(?:localStorage|sessionStorage)\.(?:get|set)Item\(\s*["\'][^"\']*(?:auth|token|session|user|login|role|admin)',
     "auth state in browser storage — a client-side guard is not authentication"),
    (r'(?i)window\.location(?:\.href)?\s*=\s*["\'][^"\']*login',
     "client-side redirect used as an auth guard"),
]


def walk(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES:
                continue
            yield os.path.join(dirpath, fn)


def read(path: str) -> str | None:
    try:
        if os.path.getsize(path) > 3_000_000:
            return None
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return None


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root)


# ── checks ─────────────────────────────────────────────────────────────────

def check_secrets(root: str) -> list[dict]:
    out = []
    for path in walk(root):
        txt = read(path)
        if txt is None:
            continue
        client = os.path.splitext(path)[1].lower() in CLIENT_EXT
        for pat, label in SECRET_PATTERNS:
            for m in re.finditer(pat, txt):
                line = txt[:m.start()].count("\n") + 1
                out.append({
                    "severity": "BLOCKER" if client else "HIGH",
                    "check": "Hide API keys",
                    "file": rel(root, path), "line": line,
                    "detail": f"{label} found"
                              + (" in a file served to the browser" if client else ""),
                    "fix": "Move it server-side or into an environment variable, "
                           "then ROTATE it — a committed key is burned.",
                })
    return out


def check_env_ignored(root: str) -> list[dict]:
    out = []
    gi = os.path.join(root, ".gitignore")
    ignored = ".env" in (read(gi) or "") if os.path.exists(gi) else False
    if os.path.exists(os.path.join(root, ".env")) and not ignored:
        out.append({"severity": "BLOCKER", "check": "Purge git secrets",
                    "file": ".env", "line": 0,
                    "detail": ".env exists and is not git-ignored",
                    "fix": "Add .env to .gitignore before the next commit."})
    return out


def check_git_history(root: str) -> list[dict]:
    """A secret deleted from the working tree still lives in history."""
    out = []
    if not os.path.isdir(os.path.join(root, ".git")):
        return out
    try:
        r = subprocess.run(["git", "-C", root, "log", "--all", "--name-only",
                            "--pretty=format:", "--diff-filter=A"],
                           capture_output=True, text=True, timeout=60)
        names = {n.strip() for n in r.stdout.splitlines() if n.strip()}
    except (subprocess.SubprocessError, OSError):
        return [{"severity": "MANUAL", "check": "Purge git secrets", "file": "-", "line": 0,
                 "detail": "could not read git history", "fix": "Scan history manually."}]
    risky = sorted(n for n in names
                   if re.search(r'(?:^|/)\.env(?!\.example)|\.pem$|\.p12$|\.pfx$|'
                                r'(?:^|/)(?:id_rsa|credentials|secrets?)(?:\.|$)', n))
    for n in risky:
        out.append({"severity": "BLOCKER", "check": "Purge git secrets",
                    "file": n, "line": 0,
                    "detail": "this path was committed at some point in history",
                    "fix": "Rotate anything it held, then purge with git-filter-repo. "
                           "Deleting the file now does not remove it from history."})
    return out


def check_injection(root: str) -> list[dict]:
    out = []
    for path in walk(root):
        if os.path.splitext(path)[1].lower() not in {".py", ".js", ".ts", ".php", ".rb", ".go", ".java"}:
            continue
        txt = read(path)
        if txt is None:
            continue
        for m in SQL_CONCAT.finditer(txt):
            out.append({"severity": "BLOCKER", "check": "Parameterize queries",
                        "file": rel(root, path),
                        "line": txt[:m.start()].count("\n") + 1,
                        "detail": "SQL appears to be built by string concatenation or interpolation",
                        "fix": "Use bound parameters."})
    return out


def check_xss(root: str) -> list[dict]:
    out = []
    for path in walk(root):
        if os.path.splitext(path)[1].lower() not in CLIENT_EXT:
            continue
        txt = read(path)
        if txt is None:
            continue
        for pat, label in DANGEROUS_SINKS:
            for m in re.finditer(pat, txt):
                out.append({"severity": "HIGH", "check": "Escape user content",
                            "file": rel(root, path),
                            "line": txt[:m.start()].count("\n") + 1,
                            "detail": label,
                            "fix": "Escape before insertion, or use textContent. "
                                   "Assume every stored string is hostile."})
    return out


def check_client_auth(root: str) -> list[dict]:
    out = []
    for path in walk(root):
        if os.path.splitext(path)[1].lower() not in CLIENT_EXT:
            continue
        txt = read(path)
        if txt is None:
            continue
        for pat, label in CLIENT_AUTH_ONLY:
            hits = list(re.finditer(pat, txt))
            if hits:
                out.append({"severity": "HIGH", "check": "Enforce server-side auth",
                            "file": rel(root, path),
                            "line": txt[:hits[0].start()].count("\n") + 1,
                            "detail": f"{label} ({len(hits)} occurrence(s))",
                            "fix": "Every protected endpoint must verify the session "
                                   "server-side. A redirect only hides the page."})
    return out


def check_headers(root: str) -> list[dict]:
    """Look for security headers configured anywhere in the project."""
    wanted = {
        "Content-Security-Policy": False, "X-Content-Type-Options": False,
        "X-Frame-Options": False, "Referrer-Policy": False,
        "Strict-Transport-Security": False,
    }
    for path in walk(root):
        txt = read(path)
        if txt is None:
            continue
        for h in wanted:
            if h.lower() in txt.lower():
                wanted[h] = True
    missing = [h for h, found in wanted.items() if not found]
    if missing:
        return [{"severity": "HIGH", "check": "Add security headers",
                 "file": "-", "line": 0,
                 "detail": "not configured anywhere in the project: " + ", ".join(missing),
                 "fix": "Set them at the host or in a meta tag. CSP is the one that "
                        "actually blunts XSS."}]
    return []


def check_deps(root: str) -> list[dict]:
    out = []
    has_npm = os.path.exists(os.path.join(root, "package.json"))
    has_py = any(os.path.exists(os.path.join(root, f))
                 for f in ("requirements.txt", "pyproject.toml", "Pipfile"))
    if has_npm:
        out.append({"severity": "MANUAL", "check": "Scan dependencies",
                    "file": "package.json", "line": 0,
                    "detail": "npm project — dependency CVEs not checked by this script",
                    "fix": "Run `npm audit --omit=dev` and resolve criticals."})
    if has_py:
        out.append({"severity": "MANUAL", "check": "Scan dependencies",
                    "file": "requirements.txt", "line": 0,
                    "detail": "Python project — dependency CVEs not checked by this script",
                    "fix": "Run `pip-audit`."})
    if not has_npm and not has_py:
        out.append({"severity": "PASS", "check": "Scan dependencies",
                    "file": "-", "line": 0,
                    "detail": "no third-party dependency manifest found",
                    "fix": ""})
    return out


# Items no static scan can settle. These must be tested on a running system.
MANUAL_ITEMS = [
    ("Enable row-level security",
     "Confirm RLS is ON for every table, with a policy per operation."),
    ("Lock record access",
     "Sign in as user A, request user B's record by ID directly. It must fail."),
    ("Block field tampering",
     "POST a role/price/status/balance field the UI never sends. The server must ignore it."),
    ("Use public DB key",
     "Confirm the client holds the anon/publishable key, never service-role."),
    ("Encrypt sensitive data",
     "Confirm encryption at rest for PII and TLS everywhere in transit."),
    ("Secure session cookies",
     "Inspect Set-Cookie: HttpOnly, Secure, SameSite must all be present."),
    ("Hash passwords",
     "Confirm bcrypt or argon2. Never a fast hash, never plaintext."),
    ("Rate limit login",
     "Fire 20 bad logins. Requests must start being refused."),
    ("Add bot protection",
     "Confirm a challenge on signup and other public forms."),
    ("Validate all input",
     "Confirm server-side validation exists and is not only client-side."),
    ("Restrict file uploads",
     "Confirm type/size limits, storage outside the web root, no execution."),
    ("Trim API responses",
     "Read a real payload. No hashes, internal IDs, or other users' data."),
    ("Force HTTPS",
     "Confirm HTTP redirects and HSTS is set."),
]


def run(root: str) -> dict:
    findings = []
    for fn in (check_secrets, check_env_ignored, check_git_history, check_injection,
               check_xss, check_client_auth, check_headers, check_deps):
        try:
            findings.extend(fn(root))
        except Exception as e:                                   # noqa: BLE001
            findings.append({"severity": "MANUAL", "check": fn.__name__,
                             "file": "-", "line": 0,
                             "detail": f"check failed to run: {e}",
                             "fix": "Investigate manually."})
    order = {"BLOCKER": 0, "HIGH": 1, "MANUAL": 2, "PASS": 3}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f["check"], f["file"]))
    counts = {s: sum(1 for f in findings if f["severity"] == s)
              for s in ("BLOCKER", "HIGH", "MANUAL", "PASS")}
    return {
        "root": os.path.abspath(root), "findings": findings, "counts": counts,
        "manual_checklist": [{"check": c, "how": h} for c, h in MANUAL_ITEMS],
        "verdict": "BLOCKED" if counts["BLOCKER"] else
                   "REVIEW" if counts["HIGH"] else "NO BLOCKERS FOUND",
        "caveat": ("A static scan cannot prove an application is secure. The manual "
                   "checklist must be worked against a running system before launch."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--path", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = run(a.path)

    if a.json:
        print(json.dumps(res, indent=2))
        return 1 if res["counts"]["BLOCKER"] else 0

    c = res["counts"]
    print(f"\n  PRE-LAUNCH SECURITY GATE — {res['root']}")
    print(f"  {'─' * 66}")
    print(f"  {c['BLOCKER']} blocker · {c['HIGH']} high · {c['MANUAL']} manual\n")

    cur = None
    for f in res["findings"]:
        if f["severity"] == "PASS":
            continue
        if f["severity"] != cur:
            cur = f["severity"]
            print(f"  ── {cur} {'─' * (62 - len(cur))}")
        loc = f["file"] + (f":{f['line']}" if f["line"] else "")
        print(f"  [{f['check']}] {loc}")
        print(f"      {f['detail']}")
        if f["fix"]:
            print(f"      → {f['fix']}")
        print()

    print(f"  ── MUST BE TESTED BY HAND {'─' * 41}")
    for m in res["manual_checklist"]:
        print(f"  ☐ {m['check']}")
        print(f"      {m['how']}")
    print(f"\n  {'─' * 66}")
    print(f"  VERDICT: {res['verdict']}")
    print(f"  {res['caveat']}\n")
    return 1 if c["BLOCKER"] else 0


if __name__ == "__main__":
    sys.exit(main())
