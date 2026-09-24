"""In-memory PIT providers. NEW IMPLEMENTATION."""

from __future__ import annotations

from datetime import datetime

from ..contracts.raw import PricePoint, ProviderRecord, RawFundamentals
from ..contracts.models import DataStamp
from ..pit.resolver import select_latest
from .base import MarketDataProvider


class MemoryStore:
    def __init__(self) -> None:
        self._rows: dict[str, list[ProviderRecord]] = {}

    def add(self, key: str, record: ProviderRecord) -> None:
        self._rows.setdefault(key, []).append(record)

    def resolve(self, key: str, as_of: datetime) -> ProviderRecord | None:
        rows = self._rows.get(key, [])
        stamps = [r.stamp for r in rows]
        latest = select_latest(stamps, as_of)
        if latest is None:
            return None
        for r in rows:
            if r.stamp.data_stamp_id == latest.data_stamp_id:
                return r
        return None


class MemoryFundamentalsProvider:
    name = "memory-fundamentals"

    def __init__(self, store: MemoryStore | None = None):
        self.store = store or MemoryStore()

    def put(self, raw: RawFundamentals) -> None:
        self.store.add(
            raw.company_id,
            ProviderRecord(available_at=raw.stamp.available_at, payload=raw, stamp=raw.stamp),
        )

    def get(self, company_id: str, as_of: datetime) -> RawFundamentals | None:
        rec = self.store.resolve(company_id, as_of)
        return rec.payload if rec else None


class MemoryPriceProvider(MarketDataProvider):
    name = "memory-price"

    def __init__(self, store: MemoryStore | None = None):
        self.store = store or MemoryStore()

    def put(self, point: PricePoint) -> None:
        self.store.add(
            point.company_id,
            ProviderRecord(available_at=point.stamp.available_at, payload=point, stamp=point.stamp),
        )

    def get(self, company_id: str, as_of: datetime) -> PricePoint | None:
        rec = self.store.resolve(company_id, as_of)
        return rec.payload if rec else None

    def price_stamp(self, company_id: str, as_of: datetime) -> DataStamp | None:
        rec = self.store.resolve(company_id, as_of)
        return rec.stamp if rec else None
