#!/usr/bin/env python3
"""Serve the System Preferences UI and read/write config/preferences.json.

    python3 tools/serve_ui.py            # http://127.0.0.1:8787
    python3 tools/serve_ui.py --port 9000

Binds to loopback only. Never exposes API key values — the key endpoint reports
presence as a boolean and nothing more (GUARDRAILS.md #8). Guardrail settings are
served read-only and any attempt to write them is rejected.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import guardrails                                    # noqa: E402
import prefs                                         # noqa: E402
import run_pipeline                                  # noqa: E402
from datasource import load_env                      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(ROOT, "ui", "index.html")

# Which .env names each provider needs. Values are never read into a response.
KEY_MAP = {
    "alphavantage": "ALPHAVANTAGE_API_KEY",
    "fmp": "FMP_API_KEY",
    "finnhub": "FINNHUB_API_KEY",
    "newsapi": "NEWSAPI_API_KEY",
    "yfinance": None,
    "none": None,
    "sec": "SEC_USER_AGENT",
}


def key_status() -> dict:
    """Presence only. Never the value."""
    env = load_env()
    out = {}
    for provider, name in KEY_MAP.items():
        if name is None:
            out[provider] = {"required": False, "present": True, "env_var": None}
        else:
            val = env.get(name, "").strip()
            present = bool(val)
            if name == "SEC_USER_AGENT":
                present = present and "@" in val      # EDGAR needs a contact email
            out[provider] = {"required": True, "present": present, "env_var": name}
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "aihf-prefs"

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    # ── helpers ──
    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj, indent=2).encode(), "application/json")

    # ── routes ──
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            if not os.path.exists(UI):
                return self._send(404, b"ui/index.html not found", "text/plain")
            with open(UI, "rb") as fh:
                return self._send(200, fh.read(), "text/html; charset=utf-8")
        if path == "/api/preferences":
            return self._json(200, {
                "preferences": prefs.load(),
                "defaults": prefs.load_defaults(),
                "keys": key_status(),
                "guardrails_intact": not guardrails.check(verbose=False),
                "connected": True,
                "config_path": "config/preferences.json",
            })
        if path == "/api/plan":
            p = prefs.load()
            plan = []
            for n, key, label, out, deps in run_pipeline.STAGES:
                cfg = p["agents"].get(key, {})
                plan.append({"stage": n, "key": key, "label": label,
                             "model": cfg.get("model"), "enabled": cfg.get("enabled", True),
                             "output": out,
                             "depends_on": [run_pipeline.STAGES[d - 1][3] for d in deps]})
            return self._json(200, {"ticker": p["research"]["primary_ticker"], "plan": plan})
        if path == "/api/status":
            return self._json(200, run_pipeline.status())
        return self._send(404, b"not found", "text/plain")

    def do_PUT(self):
        if self.path.split("?")[0] != "/api/preferences":
            return self._send(404, b"not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 1_000_000:
                return self._json(413, {"error": "payload too large"})
            incoming = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError) as e:
            return self._json(400, {"error": f"invalid JSON: {e}"})

        if not isinstance(incoming, dict):
            return self._json(400, {"error": "expected a JSON object"})

        # Guardrails are not settable. Drop the section rather than trusting it.
        incoming.pop("guardrails", None)

        merged = prefs._deep_merge(prefs.load(), incoming)
        problems = prefs.validate(merged)
        if problems:
            return self._json(422, {"error": "validation failed", "problems": problems})

        try:
            saved = prefs.save(merged, updated_by="ui")
        except ValueError as e:
            return self._json(422, {"error": str(e)})

        return self._json(200, {
            "ok": True, "preferences": saved,
            "synced": ["risk-rules.md", "ticker.md"],
        })


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    problems = guardrails.check(verbose=False)
    if problems:
        print("WARNING — guardrails need attention:")
        for p in problems:
            print("  ✗", p)
        print()

    url = f"http://127.0.0.1:{a.port}/"
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)   # loopback only
    print(f"\n  AI Hedge Fund — System Preferences")
    print(f"  {url}")
    print(f"  editing {os.path.join('config', 'preferences.json')}")
    print(f"  API keys are never read into the UI — only whether they are set.")
    print(f"  Ctrl-C to stop\n")
    if not a.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
