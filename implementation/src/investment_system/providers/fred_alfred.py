"""ALFRED vintage adapter. NEW TOOLING.

Reads FRED_API_KEY from the process environment only.
Never log or persist the key.
Vintage = observations as published at realtime_end=as_of.
LIVE_FETCH / ALFRED_VINTAGE. Not REAL-DATA VERIFIED. Not Full System PIT.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .fred_csv import SERIES, yoy

API = "https://api.stlouisfed.org/fred/series/observations"
USER_AGENT = "Mozilla/5.0 InvestmentSystem1Research/0.2"
_CACHE: dict[tuple[str, str], dict[str, Any] | None] = {}


_RUNTIME_KEY_FILE = "/tmp/is1_fred_key"


def _key() -> str | None:
    key = os.environ.get("FRED_API_KEY", "").strip()
    if len(key) >= 16:
        return key
    try:
        raw = open(_RUNTIME_KEY_FILE, encoding="utf-8").read().strip()
    except OSError:
        raw = ""
    return raw if len(raw) >= 16 else None


def api_key_present() -> bool:
    return _key() is not None


def fetch_vintage(series_id: str, as_of: datetime, timeout: float = 12.0) -> dict[str, Any] | None:
    key = _key()
    if not key:
        return None
    day = as_of.date().isoformat()
    start = (as_of - timedelta(days=800)).date().isoformat()
    qs = urlencode(
        {
            "series_id": series_id,
            "api_key": key,
            "file_type": "json",
            "realtime_start": day,
            "realtime_end": day,
            "observation_start": start,
            "observation_end": day,
        }
    )
    cache_key = (series_id, day)
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    req = Request(f"{API}?{qs}", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    payload = None
    try:
        with urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            if "observations" not in payload:
                payload = None
    except (URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
        payload = None
    _CACHE[cache_key] = payload
    return payload


def parse_observations(payload: dict[str, Any], series_id: str) -> list[dict[str, Any]]:
    rows = []
    for item in payload.get("observations") or []:
        raw = (item.get("value") or "").strip()
        if raw in {"", ".", "NA"}:
            continue
        d = (item.get("date") or "").strip()
        try:
            dt = datetime.fromisoformat(d).replace(tzinfo=timezone.utc)
            rt = item.get("realtime_end") or item.get("realtime_start") or d
            available_at = datetime.fromisoformat(str(rt)[:10]).replace(tzinfo=timezone.utc)
            rows.append({"date": dt, "available_at": available_at, "value": float(raw), "series_id": series_id})
        except ValueError:
            continue
    return rows


def collect_indicators_alfred(as_of: datetime, payloads: dict[str, dict] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "availability": "UNAVAILABLE",
        "vintage": "ALFRED_AS_OF",
        "source": "fred/series/observations realtime_end=as_of",
        "real_data_verified": False,
        "values": {},
        "as_of_used": {},
        "missing": [],
        "key_present": api_key_present(),
    }
    if payloads is None and not api_key_present():
        out["missing"] = list(SERIES.values())
        return out
    from .fred_csv import latest_on_or_before

    for pillar, sid in SERIES.items():
        payload = payloads.get(sid) if payloads else fetch_vintage(sid, as_of)
        if not payload:
            out["missing"].append(sid)
            continue
        rows = [r for r in parse_observations(payload, sid) if r["date"] <= as_of and r.get("available_at", r["date"]) <= as_of]
        if pillar in {"growth", "inflation"}:
            val = yoy(rows, as_of)
        else:
            hit = latest_on_or_before(rows, as_of)
            val = None if hit is None else hit["value"]
        hit = latest_on_or_before(rows, as_of)
        if hit:
            out["as_of_used"][pillar] = hit["date"].date().isoformat()
        if val is None:
            out["missing"].append(sid)
        else:
            out["values"][pillar] = val
    if out["values"] and not out["missing"]:
        out["availability"] = "ALFRED_VINTAGE"
    elif out["values"]:
        out["availability"] = "PARTIAL"
    return out
