"""SEC submissions index. NEW TOOLING.

Locks accession + filingDate available at as_of.
Does not parse filing XBRL. Does not replace companyfacts values.
Not Full PIT Historical.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

USER_AGENT = "InvestmentSystem1Research contact@example.invalid"
URL = "https://data.sec.gov/submissions/CIK{cik}.json"
FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F", "40-F/A"}
ANNUAL = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}


def parse_filings(payload: dict[str, Any], as_of: datetime) -> list[dict[str, Any]]:
    recent = (payload.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accns = recent.get("accessionNumber") or []
    out = []
    for form, day, accn in zip(forms, dates, accns):
        if str(form) not in FORMS:
            continue
        try:
            filed = datetime.fromisoformat(str(day) + "T00:00:00+00:00")
        except ValueError:
            continue
        if filed > as_of:
            continue
        out.append({"form": form, "filed": filed, "accn": str(accn).replace("-", ""), "filingDate": day})
    out.sort(key=lambda x: (x["filed"], x["accn"]))
    return out


def latest_indexed(payload: dict[str, Any], as_of: datetime, form: str = "10-K") -> dict[str, Any] | None:
    rows = [r for r in parse_filings(payload, as_of) if r["form"] == form or r["form"].startswith(form)]
    return rows[-1] if rows else None


def latest_annual(payload: dict[str, Any], as_of: datetime) -> dict[str, Any] | None:
    """10-K if present, else 20-F/40-F. Does not invent a 10-K for foreign issuers."""
    rows = [r for r in parse_filings(payload, as_of) if r["form"] in ANNUAL]
    tens = [r for r in rows if r["form"].startswith("10-K")]
    if tens:
        return tens[-1]
    return rows[-1] if rows else None


def fetch_submissions(cik: str, timeout: float = 12.0) -> dict[str, Any] | None:
    url = URL.format(cik=str(cik).zfill(10))
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
        return None
