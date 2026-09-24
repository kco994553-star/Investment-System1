"""US CIK SEC parse helper. NEW TOOLING. Fail-closed. Not Stage 2."""

from __future__ import annotations

from datetime import datetime, timezone

from ..markets.us import US_LISTINGS
from .sec_companyfacts import facts_to_raw, try_fetch_companyfacts


def parse_us_company(company_id: str, as_of: datetime | None = None, payload: dict | None = None, listings: dict | None = None):
    # listings lets a generic universe (any CIK-bearing member) use the same parse path.
    listings = US_LISTINGS if listings is None else listings
    if company_id not in listings:
        raise KeyError(f"{company_id} is not on the US track")
    as_of = as_of or datetime.now(timezone.utc)
    meta = listings[company_id]
    data = payload if payload is not None else try_fetch_companyfacts(meta["cik"])
    if data is None:
        return None
    raw = facts_to_raw(company_id, meta["cik"], data, as_of, synthetic=False)
    return raw
