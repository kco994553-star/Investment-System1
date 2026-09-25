"""Integrated validation E2E. NEW IMPLEMENTATION. Not official PASS."""

from __future__ import annotations

import os

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..contracts.enums import StrategyStyle, TrackScope
from ..contracts.strategy import builtin_profile
from ..integration.engine import IntegrationEngine
from ..markets.us import US_LISTINGS
from ..providers.catalog import DEFAULT_AS_OF, iter_official_raw
from ..providers.us_sec import parse_us_company
from ..providers.yahoo_chart import fetch_chart, parse_bars, pit_bar, to_price_point
from ..contracts.portfolio_input import equal_weight_input
from ..qgv.portfolio import PortfolioEngine
from ..versions import IMPLEMENTATION_LINE, MACRO_CONFIRMED, QGV_ANALYSIS_CONTRACT, TECHNICAL_STRUCTURAL
from .adapters import MacroAdapter, QGVAdapter, TechnicalAdapter
from .file_store import FileTrackRecordStore
from .outcome import link_outcome
from .records import ScopedTrackStore


def default_store_path() -> Path:
    return Path(os.environ.get("INVESTMENT_SYSTEM_REPORTS_DIR") or Path(__file__).resolve().parents[3] / "reports") / "track_store.json"


def _record(store: ScopedTrackStore, scope: TrackScope, subject: str, as_of: datetime, refs: tuple[str, ...], profile, prediction: dict, decision: dict, module_version: str):
    return store.record(
        scope,
        subject,
        as_of,
        refs,
        {
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "parameter_set_hash": profile.parameter_set_hash(),
            "module_version": module_version,
            "system_version": IMPLEMENTATION_LINE,
            "prediction": prediction,
            "decision": decision,
            "evaluation_horizon": "1d",
        },
    )


def run_integrated_e2e(path: Path | None = None, as_of: datetime | None = None) -> dict:
    as_of = as_of or DEFAULT_AS_OF
    path = path or default_store_path()
    if path.exists():
        path.unlink()
    profile = builtin_profile(StrategyStyle.BALANCED)
    store = ScopedTrackStore(FileTrackRecordStore(path))
    qgv_ad = QGVAdapter()
    snaps = {}
    for raw in iter_official_raw(as_of):
        if raw.company_id in US_LISTINGS:
            snaps[raw.company_id] = qgv_ad.snapshot(raw, as_of)
    assert snaps
    q_before = {cid: (s.Q_score, s.G_score, s.V_score) for cid, s in snaps.items()}
    tech = {
        cid: TechnicalAdapter().snapshot(cid, as_of, [0.01, 0.0, -0.005], snap)
        for cid, snap in snaps.items()
    }
    assert {cid: (s.Q_score, s.G_score, s.V_score) for cid, s in snaps.items()} == q_before
    mac = MacroAdapter().snapshot(as_of, {"growth": 0.02, "inflation": 0.025}, next(iter(snaps.values())))
    pairs = tuple((cid, US_LISTINGS.get(cid, {}).get("yahoo", cid.upper())) for cid in snaps)
    pf = PortfolioEngine().from_input(equal_weight_input("e2e-generic", pairs), as_of, snaps)
    integ = IntegrationEngine().run(
        as_of,
        pf,
        tech,
        mac,
        profile_id=profile.profile_id,
        parameter_set_hash=profile.parameter_set_hash(),
    )
    q_rec = _record(
        store,
        TrackScope.QGV,
        "us-working",
        as_of,
        tuple(s.qgv_snapshot_id for s in snaps.values()),
        profile,
        {"Q": {cid: s.Q_score for cid, s in snaps.items()}, "V": None},
        {"kind": "snapshot_only"},
        QGV_ANALYSIS_CONTRACT,
    )
    t_rec = _record(
        store,
        TrackScope.TECHNICAL,
        "us-working",
        as_of,
        tuple(s.technical_snapshot_id for s in tech.values()),
        profile,
        {"regime": {cid: s.regime.value for cid, s in tech.items()}},
        {"kind": "snapshot_only"},
        TECHNICAL_STRUCTURAL,
    )
    m_rec = _record(
        store,
        TrackScope.MACRO,
        "market",
        as_of,
        (mac.macro_snapshot_id,),
        profile,
        {"state": mac.state.value, "regime": mac.regime},
        {"kind": "snapshot_only"},
        MACRO_CONFIRMED,
    )
    i_rec = _record(
        store,
        TrackScope.INTEGRATED,
        "us-working",
        as_of,
        (q_rec.track_record_id, t_rec.track_record_id, m_rec.track_record_id),
        profile,
        {"expected_return": 0.0, "gate": integ.gate.value},
        {"source": "integration", "target_weights": integ.target_weights, "orders_from_modules": False},
        "integration-v1.2-PROVISIONAL",
    )
    parent_payload = json.dumps(i_rec.payload, sort_keys=True)
    reloaded = FileTrackRecordStore(path)
    restored = reloaded.get(i_rec.track_record_id)
    assert restored.payload["parameter_set_hash"] == profile.parameter_set_hash()
    assert restored.payload["profile_id"] == profile.profile_id
    scoped = ScopedTrackStore(reloaded)
    child = link_outcome(scoped, i_rec.track_record_id, as_of + timedelta(days=2), {"realized_return": 0.0})
    after = FileTrackRecordStore(path).get(i_rec.track_record_id)
    assert json.dumps(after.payload, sort_keys=True) == parent_payload
    return {
        "kind": "INTEGRATED_E2E_SYNTHETIC",
        "official_pass": False,
        "real_data_verified": False,
        "as_of": as_of.isoformat(),
        "names": len(snaps),
        "gate": integ.gate.value,
        "profile_id": profile.profile_id,
        "parameter_set_hash": profile.parameter_set_hash(),
        "qgv_record": q_rec.track_record_id,
        "technical_record": t_rec.track_record_id,
        "macro_record": m_rec.track_record_id,
        "integrated_record": i_rec.track_record_id,
        "outcome_record": child.track_record_id,
        "parent_immutable": True,
        "reloaded": True,
        "v_all_none": all(s.V_score is None for s in snaps.values()),
        "decision_source": "integration",
        "store_path": str(path),
    }


def run_live_candidate(company_ids: tuple[str, ...] = ("nvda", "msft")) -> dict:
    now = datetime.now(timezone.utc)
    hist_as_of = DEFAULT_AS_OF
    prices_now = {}
    prices_pit = {}
    sec = {}
    for cid in company_ids:
        meta = US_LISTINGS[cid]
        payload = fetch_chart(meta["yahoo"], range="1mo")
        bars = parse_bars(payload) if payload else []
        if payload:
            from ..providers.yahoo_chart import parse_chart

            parsed = parse_chart(payload)
            if parsed:
                prices_now[cid] = {
                    "price": parsed["price"],
                    "evidence": "LIVE_FETCH",
                    "historical_as_of_attached": False,
                }
        bar = pit_bar(bars, hist_as_of)
        if bar:
            pt = to_price_point(cid, bar)
            prices_pit[cid] = {
                "price": pt.price,
                "observed_at": pt.stamp.observed_at.isoformat(),
                "available_at": pt.stamp.available_at.isoformat(),
                "evidence": "LIVE_FETCH",
                "pit_ok": pt.stamp.available_at <= hist_as_of,
            }
        raw = parse_us_company(cid, as_of=now)
        if raw is None:
            sec[cid] = {"ok": False, "evidence": "LIVE_UNAVAILABLE"}
        else:
            sec[cid] = {
                "ok": True,
                "evidence": "LIVE_FETCH",
                "period_quality": raw.period_quality,
                "real_data_verified": False,
                "revenue": raw.revenue,
            }
    return {
        "kind": "REAL_DATA_CANDIDATE",
        "stage2": False,
        "real_data_verified": False,
        "reason": "SEC period_quality not FORM_ALIGNED across book; Yahoo unofficial; single-day sample.",
        "as_of_session": now.isoformat(),
        "pit_as_of": hist_as_of.isoformat(),
        "live_prices": prices_now,
        "pit_prices": prices_pit,
        "sec": sec,
    }


def run_pit_price_probe(company_id: str = "nvda") -> dict:
    """PIT filter on Yahoo daily bars. LIVE_FETCH probe, not official historical PASS."""
    from ..pit.resolver import is_available

    hist_as_of = DEFAULT_AS_OF
    meta = US_LISTINGS[company_id]
    payload = fetch_chart(meta["yahoo"], range="1mo")
    bars = parse_bars(payload) if payload else []
    bar = pit_bar(bars, hist_as_of)
    leaked = [b for b in bars if b["observed_at"] > hist_as_of]
    ok = None
    if bar:
        pt = to_price_point(company_id, bar)
        ok = is_available(pt.stamp, hist_as_of)
    return {
        "kind": "PIT_PRICE_PROBE",
        "official_pass": False,
        "real_data_verified": False,
        "as_of": hist_as_of.isoformat(),
        "bars": len(bars),
        "future_bars_excluded": len(leaked),
        "pit_price": None if bar is None else bar["price"],
        "stamp_available": ok,
        "evidence": "LIVE_FETCH",
    }
