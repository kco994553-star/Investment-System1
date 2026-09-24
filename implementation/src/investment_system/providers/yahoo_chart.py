"""Yahoo Finance chart adapter. NEW TOOLING. No API key.

Unofficial public JSON. Not an exchange official feed.
Evidence class LIVE_FETCH. Not Stage 2 PASS. Not REAL-DATA VERIFIED for fundamentals.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..contracts.models import DataStamp
from ..contracts.raw import PricePoint

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={range}"
USER_AGENT = "Mozilla/5.0 InvestmentSystem1Research/0.2"


def parse_chart(payload: dict[str, Any]) -> dict[str, Any] | None:
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        return None
    meta = result[0].get("meta") or {}
    price = meta.get("regularMarketPrice")
    currency = meta.get("currency") or "USD"
    symbol = meta.get("symbol")
    ts = meta.get("regularMarketTime")
    if price is None:
        quotes = ((result[0].get("indicators") or {}).get("quote") or [{}])[0]
        closes = [c for c in (quotes.get("close") or []) if c is not None]
        if not closes:
            return None
        price = closes[-1]
    observed = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else datetime.now(timezone.utc)
    return {"symbol": symbol, "price": float(price), "currency": currency, "observed_at": observed}


def parse_bars(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        return []
    ts = result[0].get("timestamp") or []
    quotes = ((result[0].get("indicators") or {}).get("quote") or [{}])[0]
    closes = quotes.get("close") or []
    adj = ((result[0].get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose") or []
    currency = (result[0].get("meta") or {}).get("currency") or "USD"
    symbol = (result[0].get("meta") or {}).get("symbol")
    bars = []
    for i, t in enumerate(ts):
        if t is None or i >= len(closes) or closes[i] is None:
            continue
        adj_px = float(adj[i]) if i < len(adj) and adj[i] is not None else None
        close_px = float(closes[i])
        bars.append(
            {
                "symbol": symbol,
                "price": adj_px if adj_px is not None else close_px,
                "close": close_px,
                "adjclose": adj_px,
                "adjusted": adj_px is not None,
                "currency": currency,
                "observed_at": datetime.fromtimestamp(int(t), tz=timezone.utc),
            }
        )
    return bars


def pit_bar(bars: list[dict[str, Any]], as_of: datetime) -> dict[str, Any] | None:
    eligible = [b for b in bars if b["observed_at"] <= as_of]
    return eligible[-1] if eligible else None


def fetch_chart(symbol: str, timeout: float = 8.0, range: str = "5d") -> dict[str, Any] | None:
    url = YAHOO_CHART.format(symbol=symbol, range=range)
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, TimeoutError, ValueError, OSError):
        return None


def to_price_point(company_id: str, parsed: dict[str, Any]) -> PricePoint:
    observed = parsed["observed_at"]
    stamp = DataStamp(
        data_stamp_id=f"yahoo_{company_id}_{observed.date().isoformat()}",
        source_provider="yahoo-chart",
        source_type="price",
        source_reference=parsed.get("symbol") or company_id,
        published_at=observed,
        available_at=observed,
        observed_at=observed,
        synthetic=False,
    )
    return PricePoint(company_id=company_id, stamp=stamp, price=parsed["price"], currency=parsed.get("currency", "USD"))
