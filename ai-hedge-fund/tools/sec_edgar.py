#!/usr/bin/env python3
"""SEC EDGAR filings — free, no API key, but a real User-Agent is mandatory.

    python3 tools/sec_edgar.py --ticker AAPL --forms 10-K,10-Q,8-K
    python3 tools/sec_edgar.py --ticker AAPL --facts          # XBRL company facts

EDGAR requires a descriptive User-Agent containing a contact email, or it returns
403. Set SEC_USER_AGENT in .env, e.g.  SEC_USER_AGENT=Jane Doe jane@example.com

Fair-access policy: keep requests under ~10/second. The cache in datasource.py
does most of that work for you.
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import prefs                                                        # noqa: E402
from datasource import DataUnavailable, fetch_json, load_env, qs    # noqa: E402

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{doc}"


def _headers(env: dict) -> dict:
    ua = env.get("SEC_USER_AGENT", "").strip()
    if not ua or "@" not in ua:
        raise DataUnavailable(
            "SEC EDGAR requires SEC_USER_AGENT in .env containing a real contact email, "
            "e.g. 'Jane Doe jane@example.com'. Without it EDGAR returns 403. "
            "No filings fetched — nothing was estimated.")
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov"}


def resolve_cik(ticker: str, env: dict, ttl: int) -> str:
    """Ticker → zero-padded 10-digit CIK."""
    h = dict(_headers(env)); h["Host"] = "www.sec.gov"
    data = fetch_json(TICKERS_URL, headers=h, ttl_minutes=max(ttl, 1440))
    want = ticker.upper()
    for row in data.values():
        if str(row.get("ticker", "")).upper() == want:
            return str(row["cik_str"]).zfill(10)
    raise DataUnavailable(
        f"{ticker} not found in the SEC ticker index. Non-US listings and some ADRs "
        f"are not in EDGAR. Nothing was estimated.")


def recent_filings(ticker: str, forms: list[str], limit: int, env: dict, ttl: int) -> dict:
    cik = resolve_cik(ticker, env, ttl)
    data = fetch_json(SUBMISSIONS.format(cik=cik), headers=_headers(env), ttl_minutes=ttl)
    recent = (data.get("filings") or {}).get("recent") or {}
    cols = ("form", "filingDate", "reportDate", "accessionNumber",
            "primaryDocument", "primaryDocDescription")
    rows = list(zip(*[recent.get(c, []) for c in cols]))

    wanted = {f.strip().upper() for f in forms}
    out = []
    for form, filed, report, acc, doc, desc in rows:
        if wanted and form.upper() not in wanted:
            continue
        out.append({
            "form": form, "filed": filed, "period": report,
            "accession": acc, "description": desc,
            "url": ARCHIVE.format(cik_int=int(cik), acc_nodash=acc.replace("-", ""), doc=doc),
        })
        if len(out) >= limit:
            break

    return {
        "ticker": ticker.upper(), "cik": cik,
        "company": data.get("name"),
        "sic": data.get("sicDescription"),
        "fiscal_year_end": data.get("fiscalYearEnd"),
        "source": "SEC EDGAR",
        "filings": out,
        "note": ("Read Item 1A Risk Factors in the latest 10-K. Quote the company's own "
                 "wording; cite the filing URL and date for every figure taken from it."),
    }


def company_facts(ticker: str, env: dict, ttl: int) -> dict:
    """XBRL company facts — the structured financials behind the filings."""
    cik = resolve_cik(ticker, env, ttl)
    data = fetch_json(FACTS.format(cik=cik), headers=_headers(env), ttl_minutes=ttl)
    us = (data.get("facts") or {}).get("us-gaap") or {}

    def series(tag: str, unit: str = "USD", n: int = 8):
        node = us.get(tag)
        if not node:
            return None
        vals = (node.get("units") or {}).get(unit) or []
        annual = [v for v in vals if v.get("form") in ("10-K", "10-Q") and v.get("fy")]
        annual.sort(key=lambda v: (v.get("end") or ""), reverse=True)
        return [{"end": v.get("end"), "form": v.get("form"), "fy": v.get("fy"),
                 "fp": v.get("fp"), "val": v.get("val")} for v in annual[:n]]

    return {
        "ticker": ticker.upper(), "cik": cik,
        "company": data.get("entityName"),
        "source": "SEC EDGAR XBRL company facts",
        "revenue": series("RevenueFromContractWithCustomerExcludingAssessedTax")
                   or series("Revenues"),
        "net_income": series("NetIncomeLoss"),
        "operating_income": series("OperatingIncomeLoss"),
        "assets": series("Assets"),
        "liabilities": series("Liabilities"),
        "long_term_debt": series("LongTermDebtNoncurrent"),
        "cash": series("CashAndCashEquivalentsAtCarryingValue"),
        "operating_cash_flow": series("NetCashProvidedByUsedInOperatingActivities"),
        "capex": series("PaymentsToAcquirePropertyPlantAndEquipment"),
        "shares_diluted": series("WeightedAverageNumberOfDilutedSharesOutstanding", "shares"),
        "note": ("These are as-reported GAAP figures straight from XBRL. Where the company "
                 "reports adjusted numbers too, say which you are using and why."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticker")
    ap.add_argument("--forms", default="10-K,10-Q,8-K")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--facts", action="store_true", help="XBRL company facts instead of filings")
    a = ap.parse_args()

    p = prefs.load()
    if not p["data"].get("sec_enabled", True):
        print(json.dumps({"error": "disabled",
                          "detail": "data.sec_enabled is false in preferences."}, indent=2))
        return 1

    env = load_env()
    ticker = (a.ticker or p["research"]["primary_ticker"]).upper()
    ttl = p["data"]["cache_ttl_minutes"]
    try:
        out = (company_facts(ticker, env, ttl) if a.facts
               else recent_filings(ticker, a.forms.split(","), a.limit, env, ttl))
    except DataUnavailable as e:
        print(json.dumps({"error": "data_unavailable", "detail": str(e),
                          "guardrail": "Real filings only — nothing was estimated "
                                       "(GUARDRAILS.md #4)."}, indent=2))
        return 1
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
