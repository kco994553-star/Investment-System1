"""File-backed synthetic catalog for Official Portfolio v1.1. NEW TOOLING."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..contracts.models import DataStamp
from ..contracts.raw import PricePoint, RawFundamentals
from ..qgv.portfolio import OFFICIAL_V11_TARGETS

DEFAULT_AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)


def catalog_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "fixtures"


def load_json(name: str) -> dict:
    path = catalog_dir() / name
    return json.loads(path.read_text(encoding="utf-8"))


def _stamp(company_id: str, kind: str, as_of: datetime) -> DataStamp:
    return DataStamp(
        data_stamp_id=f"fix_{kind}_{company_id}",
        source_provider="fixture-catalog",
        source_type=kind,
        source_reference=f"v1.1/{company_id}",
        published_at=as_of,
        available_at=as_of,
        observed_at=as_of,
        synthetic=True,
    )


def iter_official_raw(as_of: datetime = DEFAULT_AS_OF) -> list[RawFundamentals]:
    payload = load_json("official_v11_synthetic_book.json")
    out = []
    for cid, row in payload["companies"].items():
        if cid not in OFFICIAL_V11_TARGETS:
            continue
        fields = {k: v for k, v in row.items() if k not in {"ticker", "note"}}
        out.append(
            RawFundamentals(
                company_id=cid,
                stamp=_stamp(cid, "fundamentals", as_of),
                source_kind="SYNTHETIC",
                **fields,
            )
        )
    return out


def iter_official_prices(as_of: datetime = DEFAULT_AS_OF) -> list[PricePoint]:
    payload = load_json("official_v11_synthetic_prices.json")
    out = []
    for cid, row in payload["prices"].items():
        out.append(PricePoint(company_id=cid, stamp=_stamp(cid, "price", as_of), price=float(row["price"]), currency=row.get("currency", "USD")))
    return out
