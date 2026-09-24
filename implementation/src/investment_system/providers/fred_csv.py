"""FRED public CSV adapter. NEW TOOLING.

No API key. Uses fredgraph.csv.
This is CURRENT vintage (revised history), not ALFRED observation-time vintage.
Evidence class LIVE_FETCH. Not REAL-DATA VERIFIED. Not Full PIT.
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from io import StringIO
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
USER_AGENT = "Mozilla/5.0 InvestmentSystem1Research/0.2"

# Confirmed v0.1.1 pillars. Mapping is PROVISIONAL.
SERIES = {
    "growth": "INDPRO",
    "inflation": "CPIAUCSL",
    "rates": "DGS10",
    "liquidity": "WALCL",
    "risk": "BAMLH0A0HYM2",
}


def fetch_csv(series_id: str, timeout: float = 12.0) -> str | None:
    url = CSV_URL.format(sid=series_id)
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except (URLError, TimeoutError, ValueError, OSError):
        return None


def parse_observations(text: str, series_id: str) -> list[dict[str, Any]]:
    rows = []
    reader = csv.DictReader(StringIO(text))
    value_key = series_id if series_id in (reader.fieldnames or []) else [k for k in (reader.fieldnames or []) if k != "observation_date" and k != "DATE"][0]
    date_key = "observation_date" if "observation_date" in (reader.fieldnames or []) else "DATE"
    for row in reader:
        raw = (row.get(value_key) or "").strip()
        if raw in {"", ".", "NA"}:
            continue
        d = (row.get(date_key) or "").strip()
        try:
            dt = datetime.fromisoformat(d).replace(tzinfo=timezone.utc)
            rows.append({"date": dt, "value": float(raw), "series_id": series_id})
        except ValueError:
            continue
    return rows


def latest_on_or_before(rows: list[dict[str, Any]], as_of: datetime) -> dict[str, Any] | None:
    eligible = [r for r in rows if r["date"] <= as_of]
    return eligible[-1] if eligible else None


def yoy(rows: list[dict[str, Any]], as_of: datetime) -> float | None:
    cur = latest_on_or_before(rows, as_of)
    if cur is None:
        return None
    prior_as_of = datetime(cur["date"].year - 1, cur["date"].month, min(cur["date"].day, 28), tzinfo=timezone.utc)
    prev = latest_on_or_before(rows, prior_as_of)
    if prev is None or prev["value"] == 0:
        return None
    return cur["value"] / prev["value"] - 1.0


def collect_indicators(as_of: datetime, payloads: dict[str, str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "availability": "LIVE_FETCH",
        "vintage": "CURRENT_REVISED_NOT_ALFRED",
        "source": "fredgraph.csv",
        "real_data_verified": False,
        "values": {},
        "as_of_used": {},
        "missing": [],
    }
    for pillar, sid in SERIES.items():
        text = payloads[sid] if payloads and sid in payloads else fetch_csv(sid)
        if not text:
            out["missing"].append(sid)
            continue
        rows = parse_observations(text, sid)
        if pillar in {"growth", "inflation"}:
            val = yoy(rows, as_of)
        else:
            hit = latest_on_or_before(rows, as_of)
            val = None if hit is None else hit["value"]
            if hit:
                out["as_of_used"][pillar] = hit["date"].date().isoformat()
        if val is None:
            out["missing"].append(sid)
        else:
            out["values"][pillar] = val
            if pillar not in out["as_of_used"]:
                hit = latest_on_or_before(rows, as_of)
                if hit:
                    out["as_of_used"][pillar] = hit["date"].date().isoformat()
    if not out["values"]:
        out["availability"] = "UNAVAILABLE"
    elif out["missing"]:
        out["availability"] = "PARTIAL"
    return out
