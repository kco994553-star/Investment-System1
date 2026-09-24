"""One as_of vertical slice. NEW IMPLEMENTATION.

Universe → QGV @ as_of → rank → select → PortfolioInput → child outcome.

Selection is PROVISIONAL_RESEARCH_RULE, not Official QGV selection.
Does not fit cutoffs to realized returns. Does not retune V.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from ..contracts.portfolio_input import PortfolioInput, equal_weight_input
from ..contracts.universe import UniverseSnapshot
from ..ingestion.raw_store import RawDatasetStore
from ..ingestion.replay import build_payloads_and_bars
from ..markets.us import US_LISTINGS
from ..universe.engine import UniverseEngine
from .file_store import FileTrackRecordStore
from .historical import attach_name_outcomes, run_as_of
from .records import ScopedTrackStore

# Development canaries. 17-name regression stays separate.
CANARY_IDS = ("nvda", "msft", "amzn", "avgo", "amd", "qcom", "lrcx", "intc")

RULE_ID = "PROVISIONAL_QG_PRESENT_EQUAL_WEIGHT"
RULE_STATUS = "PROVISIONAL_RESEARCH"


def rank_cross_section(quality: dict[str, dict]) -> list[dict]:
    rows = []
    for cid, q in quality.items():
        Q, G, V = q.get("Q"), q.get("G"), q.get("V")
        eligible = Q is not None and G is not None
        if V is None:
            key = (int(eligible), Q or 0.0, G or 0.0, -1.0)
        else:
            key = (int(eligible), Q or 0.0, G or 0.0, V)
        rows.append({"company_id": cid, "eligible": eligible, "Q": Q, "G": G, "V": V, "sort": key})
    rows.sort(key=lambda r: r["sort"], reverse=True)
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
        row.pop("sort", None)
    return rows


def select_provisional(ranked: list[dict]) -> list[str]:
    """All Q-and-G-present names. No return-fitted cutoff."""
    return [r["company_id"] for r in ranked if r["eligible"]]


def to_portfolio(selected: list[str], as_of: datetime, tickers: dict[str, str] | None = None) -> PortfolioInput | None:
    if not selected:
        return None
    tickers = tickers or {}
    pairs = tuple((cid, tickers.get(cid) or US_LISTINGS.get(cid, {}).get("yahoo", cid.upper())) for cid in selected)
    return equal_weight_input(f"slice-{as_of.date().isoformat()}", pairs)


def run_vertical_slice(
    as_of: datetime,
    horizon_as_of: datetime,
    payloads: dict,
    bars: dict,
    company_ids: tuple[str, ...] = CANARY_IDS,
    store_path=None,
    universe: UniverseSnapshot | None = None,
) -> dict:
    """When ``universe`` is given, its as_of members ARE the cross-section.

    That keeps peers, ranking and selection limited to names that were members
    at as_of (no current roster applied backward).
    """
    if universe is not None:
        if universe.as_of != as_of:
            raise ValueError("universe snapshot as_of must equal slice as_of")
        company_ids = universe.ids()
    else:
        universe = UniverseEngine().research_canary(as_of)
    tickers = {m.company_id: m.ticker for m in universe.members}
    listings = dict(US_LISTINGS)
    for m in universe.members:
        if m.company_id not in listings and m.cik:
            listings[m.company_id] = {"yahoo": m.ticker, "cik": m.cik, "exchange": None}
    path = Path(store_path) if store_path else Path(NamedTemporaryFile(suffix=".json", delete=False).name)
    store = ScopedTrackStore(FileTrackRecordStore(path))
    row = run_as_of(as_of, payloads, bars, store, company_ids, listings=listings)
    quality = row.get("quality") or {}
    ranked = rank_cross_section(quality)
    selected = select_provisional(ranked)
    book = to_portfolio(selected, as_of, tickers)
    investable = [cid for cid, q in quality.items() if q.get("Q") is not None or q.get("G") is not None]
    missing = [cid for cid in company_ids if cid not in quality or (quality[cid].get("Q") is None and quality[cid].get("G") is None)]
    selected_records = {cid: rid for cid, rid in (row.get("name_records") or {}).items() if cid in selected}
    links = attach_name_outcomes(store, selected_records, as_of, horizon_as_of, bars)
    returns = [v.get("realized_return") for v in links.values() if v.get("status") == "LINKED" and v.get("realized_return") is not None]
    book_ret = None if not returns else sum(returns) / len(returns)
    uni = universe
    return {
        "kind": "VERTICAL_SLICE",
        "rule_id": RULE_ID,
        "rule_status": RULE_STATUS,
        "official_selection": False,
        "official_pass": False,
        "full_pit_pass": False,
        "real_data_verified": False,
        "calibrated": False,
        "v_refit": False,
        "as_of": as_of.isoformat(),
        "horizon_as_of": horizon_as_of.isoformat(),
        "universe": list(company_ids),
        "universe_id": uni.universe_id,
        "universe_kind": uni.universe_kind.value,
        "official_universe": uni.policy_status.value == "OFFICIAL",
        "universe_policy": uni.policy_status.value,
        "membership_basis": uni.membership_basis,
        "survivorship_risk": uni.survivorship_risk,
        "source_vintage": uni.source_vintage,
        "name_errors": row.get("name_errors") or {},
        "investable": investable,
        "missing_ok": missing,
        "ranked": ranked,
        "selected": selected,
        "n_selected": len(selected),
        "portfolio_role": None if book is None else book.role,
        "weights": None if book is None else {h.company_id: h.target_weight for h in book.holdings},
        "outcomes": links,
        "equal_weight_realized": book_ret,
        "store": str(path),
    }


def run_walk_forward(
    as_ofs: list[datetime],
    payloads: dict,
    bars: dict,
    universe_at,
    store_path=None,
) -> dict:
    """Consecutive single-as_of slices: predict at t, outcome at t+1.

    ``universe_at(as_of)`` returns the membership snapshot for that date, so
    entries/exits between dates change the cross-section. No parameter is fit
    to realized returns; the rule is fixed before any outcome is seen.
    """
    dates = sorted(as_ofs)
    if len(dates) < 2:
        raise ValueError("walk-forward needs at least two as_of dates")
    steps = []
    for t0, t1 in zip(dates, dates[1:]):
        res = run_vertical_slice(t0, t1, payloads, bars, store_path=store_path, universe=universe_at(t0))
        steps.append({
            "as_of": res["as_of"],
            "horizon_as_of": res["horizon_as_of"],
            "universe": res["universe"],
            "membership_basis": res["membership_basis"],
            "survivorship_risk": res["survivorship_risk"],
            "selected": res["selected"],
            "equal_weight_realized": res["equal_weight_realized"],
            "n_linked": sum(1 for v in res["outcomes"].values() if v.get("status") == "LINKED"),
            "name_errors": res["name_errors"],
        })
    return {
        "kind": "WALK_FORWARD_SLICES",
        "rule_id": RULE_ID,
        "rule_status": RULE_STATUS,
        "steps": steps,
        "fit_to_outcomes": False,
        "oos_claimed": False,
        "full_pit_pass": False,
        "real_data_verified": False,
        "calibrated": False,
    }


def run_vertical_slice_from_store(
    store: RawDatasetStore,
    as_of: datetime,
    horizon_as_of: datetime,
    universe: UniverseSnapshot,
    chart_range: str = "5y",
    store_path=None,
) -> dict:
    """Same engine as run_vertical_slice, fed from previously-ingested raw
    data (ingestion/replay.py) instead of caller-supplied payloads/bars.
    Absent companyfacts/price artifacts stay MISSING, same as live.
    """
    listings = {m.company_id: {"cik": m.cik, "yahoo": m.ticker} for m in universe.members}
    payloads, bars = build_payloads_and_bars(store, listings, chart_range=chart_range)
    return run_vertical_slice(as_of, horizon_as_of, payloads, bars, store_path=store_path, universe=universe)


def run_walk_forward_from_store(
    store: RawDatasetStore,
    as_ofs: list[datetime],
    universe_at,
    chart_range: str = "5y",
    store_path=None,
) -> dict:
    """run_walk_forward fed from the raw store. universe_at(as_of) still decides
    membership per date; only the fundamentals/price source changes.
    """
    dates = sorted(as_ofs)
    if len(dates) < 2:
        raise ValueError("walk-forward needs at least two as_of dates")
    all_ids = {}
    for d in dates:
        for m in universe_at(d).members:
            all_ids[m.company_id] = {"cik": m.cik, "yahoo": m.ticker}
    payloads, bars = build_payloads_and_bars(store, all_ids, chart_range=chart_range)
    return run_walk_forward(dates, payloads, bars, universe_at, store_path=store_path)
