"""Stage 1 — discovery adapters.

CHANNEL POLICY (deliberate, not incidental):
  * Gmail job alerts  — PRIMARY. The candidate already receives LinkedIn and Indeed
    alerts to their own inbox. Reading one's own mail is compliant; scraping those
    sites is not (LinkedIn UA s.8.2, Indeed ToS). Same coverage, no ban risk.
  * ATS job-board APIs — SECONDARY. Greenhouse / Lever / Ashby / Workable
    publish documented public job-board endpoints intended for this use.
  * Direct scraping of aggregators — NEVER.
"""
from __future__ import annotations
import re, html
from .prefilter import Posting

# --- LinkedIn alerts ---------------------------------------------------------
# Subject: "{Company} is hiring: {Title}"
LI_SUBJ = re.compile(r"^(?P<company>.+?)\s+is hiring:\s*(?P<title>.+?)\s*$", re.I)
# Snippet: "{Company} {Title}: {jd start}..."
LI_SNIP_LOC = re.compile(r"\b(?:Location|Based in|Office)\s*[:\-]\s*([^.\n|]{3,60})", re.I)
REMOTE = re.compile(r"\b(100% remote|fully remote|remote[- ]first|work from anywhere|remote \(global\)|remote)\b", re.I)

COUNTRY_HINTS = re.compile(
    r"\b(Jamaica|Trinidad|Barbados|Bahamas|Cayman|Bermuda|Guyana|Belize|"
    r"United States|USA|U\.S\.|Canada|United Kingdom|UK|England|Scotland|Ireland|"
    r"Australia|New Zealand|Singapore|Hong Kong|Malaysia|India|Philippines|"
    r"United Arab Emirates|UAE|Dubai|Abu Dhabi|Qatar|Doha|Saudi|Riyadh|Bahrain|Kuwait|Oman|"
    r"Netherlands|Denmark|Sweden|Norway|Finland|Germany|Switzerland|Luxembourg|Malta|Cyprus|"
    r"South Africa|Kenya|Nigeria|Ghana|Botswana|Rwanda|Mauritius|Israel|Estonia|Portugal|"
    r"Japan|Korea|Taiwan|Thailand|Vietnam|Indonesia|Poland|Czechia|Romania|Hungary|"
    r"Spain|France|Italy|Brazil|Mexico|Chile|Colombia|Costa Rica|Panama|Argentina)\b", re.I)

COUNTRY_CANON = {"usa": "United States", "u.s.": "United States", "uk": "United Kingdom",
                 "england": "United Kingdom", "scotland": "United Kingdom",
                 "uae": "United Arab Emirates", "dubai": "United Arab Emirates",
                 "abu dhabi": "United Arab Emirates", "doha": "Qatar",
                 "riyadh": "Saudi Arabia", "saudi": "Saudi Arabia",
                 "trinidad": "Trinidad and Tobago", "cayman": "Cayman Islands",
                 "korea": "South Korea"}


def _country(text: str) -> str:
    m = COUNTRY_HINTS.search(text or "")
    if not m:
        return ""
    raw = m.group(1)
    return COUNTRY_CANON.get(raw.lower(), raw)


def parse_linkedin_alert(subject: str, snippet: str = "", thread_id: str = "") -> Posting | None:
    subject = html.unescape((subject or "").strip())
    m = LI_SUBJ.match(subject)
    if not m:
        return None
    company = m.group("company").strip()
    title = m.group("title").strip()
    snippet = html.unescape(snippet or "")

    loc = ""
    lm = LI_SNIP_LOC.search(snippet)
    if lm:
        loc = lm.group(1).strip()
    elif REMOTE.search(snippet):
        loc = REMOTE.search(snippet).group(0)

    return Posting(source="linkedin_alert", external_id=thread_id or subject[:64],
                   company=company, title=title, location=loc,
                   country=_country(f"{loc} {snippet}"), description=snippet,
                   raw_subject=subject)


# --- Indeed alerts -----------------------------------------------------------
# Subject: "{Title} at {Company}. N more {region} jobs [in {place}]"
IN_SUBJ = re.compile(r"^(?P<title>.+?)\s+at\s+(?P<company>[^.]+?)\.\s*"
                     r"(?:\d+\s+more\s+(?P<region>.+?)\s+jobs?(?:\s+in\s+(?P<place>.+))?)?\s*$", re.I)


def parse_indeed_alert(subject: str, snippet: str = "", thread_id: str = "") -> Posting | None:
    subject = html.unescape((subject or "").strip())
    m = IN_SUBJ.match(subject)
    if not m:
        return None
    title = m.group("title").strip()
    company = m.group("company").strip()
    region = (m.group("region") or "").strip()
    place = (m.group("place") or "").strip()
    loc = place or region
    return Posting(source="indeed_alert", external_id=thread_id or subject[:64],
                   company=company, title=title, location=loc,
                   country=_country(f"{loc} {snippet}"),
                   description=html.unescape(snippet or ""), raw_subject=subject)


def parse_alert(sender: str, subject: str, snippet: str = "", thread_id: str = "") -> Posting | None:
    s = (sender or "").lower()
    if "linkedin" in s:
        return parse_linkedin_alert(subject, snippet, thread_id)
    if "indeed" in s:
        return parse_indeed_alert(subject, snippet, thread_id)
    return None


# --- ATS job-board APIs ------------------------------------------------------
# Documented public endpoints. Inert where the environment's network policy
# blocks outbound hosts (see JOB_APPLICATION_AGENT.md §7 Known Constraints).
ATS_ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    "lever":      "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby":      "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "workable":   "https://apply.workable.com/api/v1/widget/accounts/{slug}",
}


def fetch_ats(provider: str, slug: str, timeout: int = 25) -> list[Posting]:
    """Pull a company's public job board. Returns [] on any failure."""
    import requests
    url = ATS_ENDPOINTS.get(provider, "").format(slug=slug)
    if not url:
        return []
    try:
        r = requests.get(url, timeout=timeout, headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    rows = data.get("jobs", data) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []

    out: list[Posting] = []
    for j in rows:
        title = j.get("title") or j.get("text") or ""
        loc = ""
        if isinstance(j.get("location"), dict):
            loc = j["location"].get("name", "")
        elif isinstance(j.get("categories"), dict):
            loc = j["categories"].get("location", "")
        else:
            loc = j.get("location") or ""
        desc = j.get("content") or j.get("description") or j.get("descriptionPlain") or ""
        desc = re.sub(r"<[^>]+>", " ", html.unescape(str(desc)))
        out.append(Posting(source=f"ats:{provider}", external_id=str(j.get("id") or j.get("shortcode") or ""),
                           company=slug, title=title, location=loc, country=_country(loc),
                           url=j.get("absolute_url") or j.get("hostedUrl") or j.get("jobUrl") or "",
                           description=desc[:20000], posted_at=str(j.get("updated_at") or j.get("createdAt") or "")))
    return out
