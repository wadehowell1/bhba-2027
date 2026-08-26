#!/usr/bin/env python3
"""Shared HTTP + cache plumbing for the data tools. Standard library only.

Every fetch goes through here so that caching, the .env loader, and the
"never fabricate on failure" contract are implemented once.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(ROOT, ".cache")


class DataUnavailable(Exception):
    """A fetch failed. Callers must surface this, never substitute a guess.

    GUARDRAILS.md #4: real data only. An unavailable figure is reported as
    unavailable — it is never estimated, extrapolated, or recalled.
    """


def load_env() -> dict:
    """Read .env into a dict. Never logs or returns values to stdout."""
    env = dict(os.environ)
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def require_key(env: dict, name: str, provider: str) -> str:
    val = env.get(name, "").strip()
    if not val:
        raise DataUnavailable(
            f"{provider} needs {name}, which is not set. Add it to .env "
            f"(see .env.example). No data returned — nothing was estimated.")
    return val


def _cache_path(url: str) -> str:
    return os.path.join(CACHE_DIR, hashlib.sha256(url.encode()).hexdigest()[:32] + ".json")


def fetch_json(url: str, headers: dict | None = None, ttl_minutes: int = 60,
               timeout: int = 20) -> dict:
    """GET JSON with an on-disk cache. Raises DataUnavailable on any failure.

    Free market-data APIs are aggressively rate-limited; caching is what makes a
    multi-agent pipeline viable against them.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    cp = _cache_path(url)
    if ttl_minutes > 0 and os.path.exists(cp):
        age_min = (time.time() - os.path.getmtime(cp)) / 60
        if age_min < ttl_minutes:
            try:
                with open(cp) as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, OSError):
                pass  # bad cache entry: fall through and refetch

    req = urllib.request.Request(url, headers=headers or {"User-Agent": "ai-hedge-fund/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        hint = ""
        if e.code == 403:
            hint = (" — a 403 from SEC EDGAR means SEC_USER_AGENT is missing or lacks a real "
                    "contact email; from a data vendor it usually means a bad or absent API key")
        elif e.code == 429:
            hint = " — rate limited; raise data.cache_ttl_minutes or wait"
        raise DataUnavailable(f"HTTP {e.code} from {_host(url)}{hint}") from e
    except urllib.error.URLError as e:
        raise DataUnavailable(f"cannot reach {_host(url)}: {e.reason}") from e
    except TimeoutError as e:
        raise DataUnavailable(f"timed out after {timeout}s reaching {_host(url)}") from e

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise DataUnavailable(f"{_host(url)} returned non-JSON: {body[:120]!r}") from e

    try:
        with open(cp, "w") as fh:
            json.dump(data, fh)
    except OSError:
        pass  # cache write failure must never fail the fetch
    return data


def _host(url: str) -> str:
    return urllib.parse.urlparse(url).netloc or url


def qs(**params) -> str:
    return urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
