"""NewsEvent/EconomicEvent -> DataEvent(kind=NEWS) boundary. NEW IMPLEMENTATION.

The existing incremental engine treats NEWS as evidence only (it does not dirty QGV
scores). This adapter only builds such a DataEvent; it does not change DataEvent or
the engine. ``company_id`` is the pipeline's id and must be supplied by the upstream
identity owner: RIG does not equate ``issuer_id`` with ``company_id``.
"""

from __future__ import annotations

from ..contracts.universe import DataEvent, EventKind
from .model import EconomicEvent, NewsEvent, RealWorldEvent, _require_text


def to_data_event(event: RealWorldEvent, company_id: str) -> DataEvent:
    if not isinstance(event, (NewsEvent, EconomicEvent)):
        raise TypeError("event must be a NewsEvent or EconomicEvent")
    _require_text("company_id", company_id)
    return DataEvent(
        event_id=f"rig:{event.event_id}",
        kind=EventKind.NEWS,
        as_of=event.available_at,
        available_at=event.available_at,
        company_id=company_id,
        source=f"RIG:{type(event).__name__}",
    )
