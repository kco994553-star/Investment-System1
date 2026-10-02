"""Dated listing evidence. Ticker is not the key and is not inferred."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from ..contracts.global_universe import ListingIdentity
from .calendar import _aware
from .errors import SessionContractError

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ListingEvidence:
    """One PIT listing interval. Not a Yahoo first-trade date."""

    listing: ListingIdentity
    available_at: datetime
    evidence_id: str
    source_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.listing, ListingIdentity):
            raise SessionContractError("listing must be a ListingIdentity")
        _aware(self.available_at, "listing.available_at")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise SessionContractError("listing evidence_id is required")
        if not isinstance(self.source_sha256, str) or not _HEX64.match(self.source_sha256):
            raise SessionContractError("listing source_sha256 must be 64 lowercase hex")
