"""Provider abstraction. NEW TOOLING. No API secrets stored."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..contracts.models import DataStamp


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def price_stamp(self, company_id: str, as_of: datetime) -> DataStamp | None:
        raise NotImplementedError


class NullProvider(MarketDataProvider):
    name = "null"

    def price_stamp(self, company_id: str, as_of: datetime) -> DataStamp | None:
        return None
