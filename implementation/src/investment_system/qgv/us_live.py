"""US-track live price attach. CURRENT as_of only. NEW TOOLING."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..markets.kr import KR_DEFERRED
from ..markets.us import OUT_OF_US_TRACK, US_LISTINGS, US_WORKING_TARGETS
from ..contracts.enums import StrategyStyle, TrackScope
from ..contracts.strategy import builtin_profile
from ..providers.catalog import DEFAULT_AS_OF, iter_official_raw
from ..providers.us_sec import parse_us_company
from ..providers.yahoo_chart import fetch_chart, parse_chart, to_price_point
from ..validation.adapters import MacroAdapter, TechnicalAdapter
from ..validation.file_store import FileTrackRecordStore
from ..validation.records import ScopedTrackStore
from .pipeline import AnalysisPipeline
from ..contracts.portfolio_input import equal_weight_input
from .portfolio import PortfolioEngine
from ..integration.engine import IntegrationEngine


def persist(payload: dict, name: str) -> Path:
    root = Path(__file__).resolve().parents[3] / "reports"
    root.mkdir(exist_ok=True)
    path = root / name
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def run_us_synthetic_working(as_of: datetime = DEFAULT_AS_OF) -> dict:
    pipe = AnalysisPipeline()
    snaps = {}
    for raw in iter_official_raw(as_of):
        if raw.company_id in US_LISTINGS:
            snaps[raw.company_id] = pipe.analyze_raw(raw, as_of=as_of)
    pf = PortfolioEngine().us_working(as_of, snaps)
    return {
        "kind": "SYNTHETIC_FIXTURE",
        "role": pf.role,
        "track": "US",
        "portfolio_version": pf.portfolio_version,
        "names": len(pf.holdings),
        "weight_sum": pf.weight_sum,
        "excluded": dict(OUT_OF_US_TRACK),
        "kr_deferred": list(KR_DEFERRED),
        "v_null": all(s.V_score is None for s in snaps.values()),
        "company_ids": [h.company_id for h in pf.holdings],
    }


def run_us_live_prices(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    prices = {}
    failures = {}
    for cid, meta in US_LISTINGS.items():
        payload = fetch_chart(meta["yahoo"])
        parsed = parse_chart(payload) if payload else None
        if not parsed:
            failures[cid] = "LIVE_UNAVAILABLE"
            continue
        pt = to_price_point(cid, parsed)
        # Live print is current-session only. Do not stamp onto DEFAULT_AS_OF.
        prices[cid] = {
            "price": pt.price,
            "currency": pt.currency,
            "yahoo": meta["yahoo"],
            "cik": meta["cik"],
            "exchange": meta["exchange"],
            "observed_at": pt.stamp.observed_at.isoformat(),
            "evidence": "LIVE_FETCH",
            "historical_as_of_attached": False,
        }
    return {
        "kind": "LIVE_ATTEMPT",
        "track": "US",
        "as_of": now.isoformat(),
        "stage2": False,
        "real_data_verified": False,
        "ok": len(prices),
        "failed": failures,
        "excluded": dict(OUT_OF_US_TRACK),
        "working_weight_sum": sum(US_WORKING_TARGETS.values()),
        "prices": prices,
    }


def evaluate_current_session(live_prices: dict | None = None) -> dict:
    """Synthetic Q/G snapshots + current-session live prices. Not official history."""
    now = datetime.now(timezone.utc)
    syn = run_us_synthetic_working()
    live = live_prices or run_us_live_prices(now)
    pipe = AnalysisPipeline()
    snaps = {}
    rows = []
    for raw in iter_official_raw():
        if raw.company_id not in US_LISTINGS:
            continue
        snap = pipe.analyze_raw(raw)
        snaps[raw.company_id] = snap
        px = (live.get("prices") or {}).get(raw.company_id, {})
        rows.append(
            {
                "company_id": raw.company_id,
                "yahoo": US_LISTINGS[raw.company_id]["yahoo"],
                "exchange": US_LISTINGS[raw.company_id]["exchange"],
                "cik": US_LISTINGS[raw.company_id]["cik"],
                "target_weight": US_WORKING_TARGETS[raw.company_id],
                "Q": snap.Q_score,
                "G": snap.G_score,
                "V": snap.V_score,
                "price": px.get("price"),
                "price_evidence": px.get("evidence"),
                "synthetic_qgv": snap.synthetic,
            }
        )
    pairs = tuple((cid, US_LISTINGS[cid]["yahoo"]) for cid in snaps)
    pf = PortfolioEngine().from_input(equal_weight_input("session-generic", pairs), now, snaps)
    px_map = {cid: rec["price"] for cid, rec in (live.get("prices") or {}).items() if rec.get("price") is not None}
    ev = PortfolioEngine().evaluate(pf, px_map)
    priced = sum(1 for h in ev.holdings if h.price is not None)
    profile = builtin_profile(StrategyStyle.BALANCED)
    tech = {
        cid: TechnicalAdapter().snapshot(cid, now, [0.01, 0.0, -0.01], snap)
        for cid, snap in snaps.items()
    }
    mac = MacroAdapter().snapshot(now, {"growth": 0.02, "inflation": 0.025})
    integ = IntegrationEngine().run(
        now,
        ev,
        tech,
        mac,
        profile_id=profile.profile_id,
        parameter_set_hash=profile.parameter_set_hash(),
    )
    store_path = Path(__file__).resolve().parents[3] / "reports" / "track_store.json"
    store = ScopedTrackStore(FileTrackRecordStore(store_path))
    rec = store.record(
        TrackScope.INTEGRATED,
        "us-working",
        now,
        tuple(s.qgv_snapshot_id for s in snaps.values()),
        {
            "profile_id": profile.profile_id,
            "parameter_set_hash": profile.parameter_set_hash(),
            "prediction": {"Q_by_id": {cid: s.Q_score for cid, s in snaps.items()}},
            "decision": {
                "gate": integ.gate.value,
                "target_weights": integ.target_weights,
                "source": "integration",
            },
            "evaluation_horizon": "20d",
        },
    )
    persist({"envelope": rec.payload, "historical_as_of_attached": False}, "us_session_track_record.json")
    return {
        "kind": "SESSION_MIXED",
        "track": "US",
        "qgv_kind": "SYNTHETIC",
        "price_kind": "LIVE_FETCH",
        "stage2": False,
        "real_data_verified": False,
        "as_of_session": now.isoformat(),
        "historical_as_of_attached": False,
        "names": len(rows),
        "priced": priced,
        "portfolio_version": ev.portfolio_version,
        "profile_id": integ.profile_id,
        "parameter_set_hash": integ.parameter_set_hash,
        "gate": integ.gate.value,
        "track_record_id": rec.track_record_id,
        "excluded": dict(OUT_OF_US_TRACK),
        "rows": rows,
        "holdings": [
            {
                "company_id": h.company_id,
                "ticker": h.ticker,
                "target_weight": h.target_weight,
                "price": h.price,
            }
            for h in ev.holdings
        ],
    }


def try_us_sec_sample(company_ids: tuple[str, ...] = ("nvda", "msft")) -> dict:
    now = datetime.now(timezone.utc)
    out = {}
    for cid in company_ids:
        raw = parse_us_company(cid, as_of=now)
        if raw is None:
            out[cid] = {"ok": False, "evidence": "LIVE_UNAVAILABLE"}
            continue
        out[cid] = {
            "ok": True,
            "evidence": "LIVE_FETCH",
            "revenue": raw.revenue,
            "revenue_prev": raw.revenue_prev,
            "source_kind": raw.source_kind,
            "synthetic": raw.stamp.synthetic,
        }
    return {"kind": "LIVE_ATTEMPT", "track": "US", "stage2": False, "parses": out}
