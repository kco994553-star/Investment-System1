"""Daily reconciliation. Checks stamps / missing / membership. NEW IMPLEMENTATION."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..contracts.models import DataStamp, QGVSnapshot
from ..contracts.universe import UniverseSnapshot


def daily_reconciliation(
    as_of: datetime,
    universe: UniverseSnapshot,
    snapshots: dict[str, QGVSnapshot],
    latest_stamp: Callable[[str, datetime], DataStamp | None] | None = None,
) -> dict:
    """Find what must be recomputed. Never proposes clean names.

    stale_data: a newer fundamental stamp is available at as_of that the stored
    snapshot was not built from (a missed event). Needs ``latest_stamp``.
    """
    members = set(universe.ids())
    have = set(snapshots)
    missing = sorted(members - have)
    extra = sorted(have - members)
    stale = []
    stale_data = []
    for cid in sorted(members & have):
        snap = snapshots[cid]
        if snap.as_of > as_of:
            stale.append({"company_id": cid, "reason": "SNAPSHOT_AS_OF_AFTER_UNIVERSE"})
            continue
        if latest_stamp is not None:
            st = latest_stamp(cid, as_of)
            if st is not None and st.available_at <= as_of and st.data_stamp_id not in snap.data_stamp_refs:
                stale_data.append(cid)
    recompute = sorted(set(missing) | set(stale_data) | {s["company_id"] for s in stale})
    return {
        "kind": "DAILY_RECON",
        "as_of": as_of.isoformat(),
        "universe_id": universe.universe_id,
        "n_members": len(members),
        "n_snapshots": len(have),
        "missing_updates": missing,
        "extra_not_in_universe": extra,
        "stale_or_lookahead": stale,
        "stale_data": stale_data,
        "stamp_check": latest_stamp is not None,
        "recompute_set": recompute,
        "clean_skipped": len(members) - len(recompute),
        "recompute_unchanged": False,
        "full_pit_pass": False,
        "official_pass": False,
    }
