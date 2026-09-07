"""Evidence bank loader + keyword index. Source of truth for all CV content."""
from __future__ import annotations
import re, yaml
from pathlib import Path
from functools import lru_cache

ROOT = Path(__file__).resolve().parent.parent
BANK_PATH = ROOT / "data" / "achievements.yaml"
PROFILE_PATH = ROOT / "config" / "profile.yaml"

_TOKEN = re.compile(r"[a-z0-9&+#.]+")


def tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


@lru_cache(maxsize=1)
def load_bank() -> dict:
    return yaml.safe_load(BANK_PATH.read_text())


@lru_cache(maxsize=1)
def load_profile() -> dict:
    return yaml.safe_load(PROFILE_PATH.read_text())


@lru_cache(maxsize=1)
def employment_index() -> dict[str, dict]:
    return {e["id"]: e for e in load_bank()["employment"]}


@lru_cache(maxsize=1)
def achievement_index() -> dict[str, dict]:
    return {a["id"]: a for a in load_bank()["achievements"]}


@lru_cache(maxsize=1)
def bank_vocabulary() -> set[str]:
    """Every phrase the candidate can legitimately claim, as tokens."""
    b = load_bank()
    vocab: set[str] = set()
    for a in b["achievements"]:
        for t in a.get("tags", []):
            vocab |= tokens(t)
        vocab |= tokens(a["statement"])
    for c in b["credentials"]:
        vocab |= tokens(c["name"])
        for t in c.get("tags", []):
            vocab |= tokens(t)
    for group in b["skills"].values():
        for s in group:
            vocab |= tokens(s)
    return vocab


def tag_phrases() -> dict[str, list[str]]:
    """Map each multiword tag phrase -> achievement ids that carry it."""
    out: dict[str, list[str]] = {}
    for a in load_bank()["achievements"]:
        for t in a.get("tags", []):
            out.setdefault(t.lower(), []).append(a["id"])
    for c in load_bank()["credentials"]:
        for t in c.get("tags", []):
            out.setdefault(t.lower(), []).append(c["id"])
    return out


def open_questions() -> list[str]:
    """Dotted paths in profile.yaml still set to ASK."""
    def walk(o, p=""):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from walk(v, f"{p}.{k}" if p else k)
        elif o == "ASK":
            yield p
    return list(walk(load_profile()))
