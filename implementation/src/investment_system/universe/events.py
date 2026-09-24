"""Event → dirty set → incremental snapshot refresh. NEW IMPLEMENTATION.

FUNDAMENTAL dirties that company QGV only.
PRICE dirties Technical only (QGV untouched).
MACRO dirties Macro snapshot only.
NEWS is evidence only — does not dirty QGV scores.
Events with available_at > as_of are deferred (PIT gate), not applied.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable
from uuid import uuid4

from ..contracts.universe import DataEvent, EventKind, UniverseSnapshot
from ..qgv.leaderboard import LeaderboardEngine
from ..contracts.models import QGVSnapshot


def dirty_from_events(events: list[DataEvent]) -> dict[str, set[str]]:
    qgv: set[str] = set()
    technical: set[str] = set()
    macro = False
    evidence: set[str] = set()
    membership = False
    for ev in events:
        if ev.kind == EventKind.FUNDAMENTAL and ev.company_id:
            qgv.add(ev.company_id)
        elif ev.kind == EventKind.PRICE and ev.company_id:
            technical.add(ev.company_id)
        elif ev.kind == EventKind.MACRO:
            macro = True
        elif ev.kind == EventKind.NEWS and ev.company_id:
            evidence.add(ev.company_id)
        elif ev.kind == EventKind.MEMBERSHIP:
            membership = True
    return {
        "qgv": qgv,
        "technical": technical,
        "macro": macro,
        "evidence": evidence,
        "membership": membership,
    }


def _run_each(ids, fn, as_of, sink: dict) -> tuple[list[str], list[str], list[dict]]:
    """One bad name must not abort the batch; its old snapshot is kept."""
    done, missing, errors = [], [], []
    for cid in sorted(ids):
        try:
            out = fn(cid, as_of)
        except Exception as exc:  # isolated and reported, never swallowed silently
            errors.append({"company_id": cid, "error": type(exc).__name__, "detail": str(exc)[:200]})
            continue
        if out is None:
            missing.append(cid)
            continue
        sink[cid] = out
        done.append(cid)
    return done, missing, errors


class IncrementalEngine:
    """Same calculation objects as PIT replay. Stores snapshots by company_id."""

    def __init__(self):
        self.qgv: dict[str, QGVSnapshot] = {}
        self.technical: dict[str, Any] = {}
        self.macro: Any = None
        self.evidence: dict[str, list[str]] = {}
        self.leaderboard = LeaderboardEngine()

    def replace_snapshots(self, snaps: list[QGVSnapshot]) -> None:
        for s in snaps:
            self.qgv[s.company_id] = s

    def apply_fundamental(self, snap: QGVSnapshot) -> QGVSnapshot:
        self.qgv[snap.company_id] = snap
        return snap

    def refresh_leaderboard(self, universe: UniverseSnapshot, generated_at: datetime):
        members = set(universe.ids())
        # Only current members are ranked; stale non-members stay stored but unranked.
        return self.leaderboard.build(
            universe.universe_id,
            generated_at,
            [s for c, s in self.qgv.items() if c in members],
            tickers={m.company_id: m.ticker for m in universe.members},
        )

    def full_batch(
        self,
        universe: UniverseSnapshot,
        as_of: datetime,
        recompute_qgv: Callable[[str, datetime], QGVSnapshot | None],
    ) -> dict:
        """Cold start / explicit rebuild. Not the live default."""
        done, missing, errors = _run_each(universe.ids(), recompute_qgv, as_of, self.qgv)
        return {
            "kind": "FULL_BATCH",
            "as_of": as_of.isoformat(),
            "n_members": len(universe.ids()),
            "qgv_recomputed": len(done),
            "missing": missing,
            "errors": errors,
        }

    def process(
        self,
        events: list[DataEvent],
        as_of: datetime,
        universe: UniverseSnapshot,
        recompute_qgv: Callable[[str, datetime], QGVSnapshot | None],
        recompute_technical: Callable[[str, datetime], Any] | None = None,
        refresh_macro: Callable[[datetime], Any] | None = None,
    ) -> dict:
        """Live default: recompute only what the ready events dirty."""
        ready = [e for e in events if e.available_at <= as_of]
        deferred = [e.event_id for e in events if e.available_at > as_of]
        dirty = dirty_from_events(ready)
        members = set(universe.ids())
        qgv_targets = dirty["qgv"] & members
        tech_targets = dirty["technical"] & members
        q_done, q_missing, q_err = _run_each(qgv_targets, recompute_qgv, as_of, self.qgv)
        t_done, t_missing, t_err = ([], [], [])
        if recompute_technical is not None:
            t_done, t_missing, t_err = _run_each(tech_targets, recompute_technical, as_of, self.technical)
        macro_refreshed = False
        if dirty["macro"] and refresh_macro is not None:
            self.macro = refresh_macro(as_of)
            macro_refreshed = True
        for ev in ready:
            if ev.kind == EventKind.NEWS and ev.company_id:
                self.evidence.setdefault(ev.company_id, []).append(ev.event_id)
        return {
            "kind": "INCREMENTAL",
            "as_of": as_of.isoformat(),
            "n_events": len(events),
            "deferred_not_available": deferred,
            "qgv_recomputed": q_done,
            "qgv_missing": q_missing,
            "technical_recomputed": t_done,
            "technical_missing": t_missing,
            "macro_refreshed": macro_refreshed,
            "evidence_only": sorted(dirty["evidence"]),
            "ignored_not_member": sorted((dirty["qgv"] | dirty["technical"]) - members),
            "membership_changed": dirty["membership"],
            "errors": q_err + t_err,
            "untouched_qgv": len(members) - len(q_done),
        }

    def batch_capacity(self, n: int) -> dict:
        return {
            "kind": "BATCH_CAPABLE",
            "requested_n": n,
            "mode": "DIRTY_SET_PREFERRED",
            "full_batch_supported": True,
            "live_default": "incremental",
        }


def make_event(
    kind: EventKind,
    as_of: datetime,
    company_id: str | None = None,
    source: str = "TEST",
    available_at: datetime | None = None,
) -> DataEvent:
    return DataEvent(
        event_id=f"ev_{uuid4().hex[:10]}",
        kind=kind,
        as_of=as_of,
        available_at=available_at or as_of,
        company_id=company_id,
        source=source,
    )
