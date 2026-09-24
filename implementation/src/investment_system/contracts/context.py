"""Shared Security Context across QGV and Technical workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class SecurityContext:
    company_id: str
    ticker: str
    exchange: Optional[str]
    as_of: datetime
    market_track: str = "US"

    def query(self) -> str:
        return f"company_id={self.company_id}&ticker={self.ticker}&as_of={self.as_of.date().isoformat()}"
