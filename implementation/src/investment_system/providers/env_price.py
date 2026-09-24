"""Env-gated live price adapter. NEW TOOLING.

Enabled only when INVESTMENT_SYSTEM_PRICE_FEED=1.
URL template from INVESTMENT_SYSTEM_PRICE_URL, must contain {symbol}.
No secrets are read or stored. Disabled by default.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..contracts.models import DataStamp
from ..contracts.raw import PricePoint
from .base import MarketDataProvider


class EnvPriceProvider(MarketDataProvider):
    name = "env-price"

    def enabled(self) -> bool:
        return os.environ.get("INVESTMENT_SYSTEM_PRICE_FEED", "") == "1"

    def url_template(self) -> str | None:
        return os.environ.get("INVESTMENT_SYSTEM_PRICE_URL") or None

    def fetch_symbol(self, symbol: str, timeout: float = 6.0) -> dict | None:
        if not self.enabled():
            return None
        tmpl = self.url_template()
        if not tmpl or "{symbol}" not in tmpl:
            return None
        url = tmpl.format(symbol=symbol)
        req = Request(url, headers={"User-Agent": "InvestmentSystem1Research", "Accept": "application/json,text/plain"})
        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
        except (URLError, TimeoutError, OSError):
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw_text": raw}

    def price_stamp(self, company_id: str, as_of: datetime) -> DataStamp | None:
        return None

    def get(self, company_id: str, symbol: str, as_of: datetime) -> PricePoint | None:
        payload = self.fetch_symbol(symbol)
        if not payload:
            return None
        price = payload.get("price") or payload.get("close")
        if price is None:
            return None
        now = datetime.now(timezone.utc)
        if now > as_of:
            # Do not leak a newer live print into a historical as_of.
            return None
        stamp = DataStamp(
            data_stamp_id=f"envpx_{company_id}",
            source_provider=self.name,
            source_type="price",
            source_reference=symbol,
            published_at=now,
            available_at=now,
            observed_at=now,
            synthetic=False,
        )
        return PricePoint(company_id=company_id, stamp=stamp, price=float(price))
