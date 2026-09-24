"""Leaderboard consumes QGV snapshots. Does not rescore. NEW IMPLEMENTATION."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ..contracts.models import LeaderboardRow, LeaderboardSnapshot, QGVSnapshot
from ..versions import IMPLEMENTATION_KIND
from .identifiers import IdentifierRegistry


class LeaderboardEngine:
    def __init__(self, registry: IdentifierRegistry | None = None):
        self.registry = registry or IdentifierRegistry()

    def build(
        self,
        universe_id: str,
        generated_at: datetime,
        snapshots: list[QGVSnapshot],
        tickers: dict[str, str] | None = None,
    ) -> LeaderboardSnapshot:
        """``tickers`` (from the universe members) covers names outside the registry.

        The registry stays authoritative where it knows a name; an unknown name
        with no universe ticker still fails loudly rather than getting a guessed ticker.
        """
        tickers = tickers or {}
        ranked = sorted(
            snapshots,
            key=lambda s: (s.total_score is not None, s.total_score or -1, s.Q_score or -1),
            reverse=True,
        )
        rows = []
        for i, s in enumerate(ranked, start=1):
            try:
                ticker = self.registry.get(s.company_id).ticker
            except KeyError:
                if s.company_id not in tickers:
                    raise
                ticker = tickers[s.company_id]
            rows.append(
                LeaderboardRow(
                    rank=i,
                    company_id=s.company_id,
                    ticker=ticker,
                    qgv_snapshot_id=s.qgv_snapshot_id,
                    Q_score=s.Q_score,
                    G_score=s.G_score,
                    V_score=s.V_score,
                    total_score=s.total_score,
                    freshness="SYNTHETIC" if s.synthetic else s.coverage_state.value,
                )
            )
        return LeaderboardSnapshot(
            leaderboard_snapshot_id=f"lb_{uuid4().hex[:12]}",
            universe_id=universe_id,
            generated_at=generated_at,
            rows=tuple(rows),
            implementation_kind=IMPLEMENTATION_KIND,
            recomputed_qgv=False,
        )
