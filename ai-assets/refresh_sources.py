#!/usr/bin/env python3
"""
Refresh the source captures that a scheduled job is able to refresh.

Classification : INTERNAL USE
Version        : 1.0.0

Scope, stated plainly so a stale register is never mistaken for a current one:

  REFRESHED HERE
    sources/repo_commits.json   commit history for every repository in the
                                register that this job can reach.

  NOT REFRESHED HERE
    sources/connectors.json     the claude.ai connector registry is readable
    sources/skills_manifest.json  only from a Claude session, so both are
    sources/repositories.json   refreshed by the companion monthly Routine.

Anything not refreshed keeps its previous ``captured_at``. generate.py ages
every source and flags any capture older than 45 days as Stale on the
dashboard's provenance panel, so carry-forward data is always visible as such.

Reachability, in order of preference per repository:
  1. A local git clone (authoritative, includes every ref, no API limits).
  2. The GitHub REST API using AI_ASSETS_TOKEN or GITHUB_TOKEN.
  3. Neither - the previous capture is kept and the repository is reported.

Stdlib only. Exits 0 even when some repositories could not be refreshed: a
partial refresh with an honest freshness flag beats a failed pipeline.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(HERE, "sources")
REPO_ROOT = os.path.dirname(HERE)

API = "https://api.github.com"
TOKEN = os.environ.get("AI_ASSETS_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
TIMEOUT = 30


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(name):
    with open(os.path.join(SOURCES, name), encoding="utf-8") as fh:
        return json.load(fh)


def save(name, data):
    with open(os.path.join(SOURCES, name), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Source 1: a local clone
# ---------------------------------------------------------------------------


def local_commit_dates(path):
    """Every commit date across all refs, normalised to UTC. None if not a repo."""
    try:
        out = subprocess.run(
            ["git", "-C", path, "log", "--all", "--pretty=%aI"],
            capture_output=True, text=True, timeout=TIMEOUT, check=True,
        ).stdout.split()
    except (subprocess.SubprocessError, OSError):
        return None
    dates = []
    for raw in out:
        try:
            dates.append(
                dt.datetime.fromisoformat(raw)
                .astimezone(dt.timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ")
            )
        except ValueError:
            continue
    return sorted(dates) if dates else None


# ---------------------------------------------------------------------------
# Source 2: the GitHub REST API
# ---------------------------------------------------------------------------


def api_commit_dates(full_name):
    """Default-branch commit dates, paged. None if unreachable or unauthorised."""
    if not TOKEN:
        return None
    dates, page = [], 1
    while page <= 10:  # 1,000 commits is far beyond anything in this register
        req = urllib.request.Request(
            f"{API}/repos/{full_name}/commits?per_page=100&page={page}",
            headers={
                "Authorization": "Bearer " + TOKEN,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ai-asset-register/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                batch = json.load(resp)
        except urllib.error.HTTPError as exc:
            # 409 is GitHub's "repository is empty" - a real, reportable answer.
            if exc.code == 409:
                return []
            return None
        except (urllib.error.URLError, ValueError, OSError):
            return None
        if not batch:
            break
        for c in batch:
            d = (c.get("commit", {}).get("author") or {}).get("date")
            if d:
                dates.append(d)
        if len(batch) < 100:
            break
        page += 1
    return sorted(dates)


# ---------------------------------------------------------------------------


def main():
    repos = load("repositories.json")
    commits = load("repo_commits.json")
    dates_map = commits.get("commit_dates", {})

    refreshed, kept = [], []

    for entry in repos["repositories"]:
        full_name = entry["full_name"]
        short = full_name.split("/")[-1]

        # 1. local clone - this repository itself, or a sibling checkout
        found = None
        for candidate in (REPO_ROOT, os.path.join(os.path.dirname(REPO_ROOT), short)):
            if os.path.isdir(os.path.join(candidate, ".git")):
                remote = subprocess.run(
                    ["git", "-C", candidate, "remote", "get-url", "origin"],
                    capture_output=True, text=True,
                ).stdout.strip().lower()
                if short.lower() in remote:
                    found = local_commit_dates(candidate)
                    if found is not None:
                        dates_map[full_name] = found
                        entry["commit_history"] = "complete"
                        refreshed.append(f"{full_name} <- local clone ({len(found)} commits)")
                        break
        if found is not None:
            continue

        # 2. REST API
        api = api_commit_dates(full_name)
        if api is not None:
            dates_map[full_name] = api
            entry["commit_history"] = "complete" if api else "empty"
            refreshed.append(f"{full_name} <- REST API ({len(api)} commits)")
            continue

        # 3. unreachable - keep the previous capture, and say so
        kept.append(full_name)

    commits["commit_dates"] = dates_map
    commits["captured_at"] = utcnow()
    commits["refreshed"] = refreshed
    commits["not_refreshed"] = kept
    save("repo_commits.json", commits)

    if refreshed:
        repos["captured_at"] = utcnow()
        save("repositories.json", repos)

    print("Refreshed:")
    for line in refreshed or ["  (none)"]:
        print("  " + line)
    if kept:
        print("Kept at previous capture (unreachable this run):")
        for name in kept:
            print("  " + name)
        print("\nSet the AI_ASSETS_TOKEN secret to a fine-grained PAT with read-only")
        print("Contents access to refresh private repositories from a scheduled job.")
    print("\nNot refreshable by a scheduled job (needs a Claude session):")
    print("  sources/connectors.json, sources/skills_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
