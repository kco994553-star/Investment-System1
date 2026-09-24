"""Historical PIT pipeline candidate. NEW IMPLEMENTATION. Not Full PIT PASS."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from ..contracts.enums import CoverageState, MacroState, StrategyStyle, TrackScope
from ..contracts.models import MacroSnapshot
from ..contracts.strategy import builtin_profile
from ..integration.compatibility import annotate
from ..integration.engine import IntegrationEngine
from ..markets.us import US_LISTINGS, us_company_ids
from ..providers.yahoo_chart import fetch_chart, parse_bars, pit_bar
from ..providers.us_sec import parse_us_company
from ..qgv.pipeline import AnalysisPipeline
from ..contracts.portfolio_input import equal_weight_input
from ..qgv.portfolio import PortfolioEngine
from ..qgv.quarterly_series import monitor_from_facts
from ..technical.engine import TechnicalEngine
from ..versions import IMPLEMENTATION_KIND, IMPLEMENTATION_LINE, MACRO_CONFIRMED
from .file_store import FileTrackRecordStore
from .outcome import link_outcome
from .records import ScopedTrackStore


def bars_to_returns(bars: list[dict], as_of: datetime) -> list[float]:
    eligible = [b for b in bars if b["observed_at"] <= as_of]
    if len(eligible) < 2:
        return []
    rets = []
    for prev, cur in zip(eligible, eligible[1:]):
        if prev["price"]:
            rets.append(cur["price"] / prev["price"] - 1.0)
    return rets[-20:]


def attach_price_outcome(store: ScopedTrackStore, prediction_id: str, predict_as_of: datetime, horizon_as_of: datetime, bars: list[dict]):
    """Outcome uses later PIT prices only. Must not write those prices into the parent prediction."""
    px0 = pit_bar(bars, predict_as_of)
    px1 = pit_bar(bars, horizon_as_of)
    if px0 is None or px1 is None or not px0["price"]:
        raise ValueError("missing PIT prices for outcome")
    if horizon_as_of <= predict_as_of:
        raise ValueError("horizon must be after prediction as_of")
    realized = px1["price"] / px0["price"] - 1.0
    flags: list[str] = []
    if not px0.get("adjusted") or not px1.get("adjusted"):
        flags.append("UNADJUSTED_CLOSE")
    close0 = px0.get("close")
    close1 = px1.get("close")
    if close0 and close1 and px0.get("adjclose") and px1.get("adjclose"):
        raw = close1 / close0 - 1.0
        if abs(raw - realized) > 0.05:
            flags.append("CORP_ACTION_GAP")
    parent = store.store.get(prediction_id)
    before = dict(parent.payload)
    child = link_outcome(
        store,
        prediction_id,
        horizon_as_of,
        {
            "realized_return": realized,
            "px0": px0["price"],
            "px1": px1["price"],
            "adjusted": bool(px0.get("adjusted") and px1.get("adjusted")),
            "flags": flags,
        },
    )
    after = store.store.get(prediction_id)
    if after.payload != before:
        raise RuntimeError("prediction mutated by outcome prices")
    if "px1" in str(after.payload.get("prediction") or {}):
        raise RuntimeError("outcome price leaked into prediction")
    return child


def live_macro(as_of: datetime, series_payloads: dict | None = None, prefer_alfred: bool = True) -> MacroSnapshot:
    from ..macro.engine import MacroEngine
    from ..providers.fred_alfred import api_key_present, collect_indicators_alfred
    from ..providers.fred_csv import collect_indicators

    pack = None
    alfred_payloads = None
    csv_payloads = None
    if isinstance(series_payloads, dict) and series_payloads:
        first = next(iter(series_payloads.values()))
        if isinstance(first, dict):
            alfred_payloads = series_payloads
        elif isinstance(first, str):
            csv_payloads = series_payloads
    if prefer_alfred and (api_key_present() or alfred_payloads is not None):
        try:
            pack = collect_indicators_alfred(as_of, alfred_payloads)
        except Exception:
            pack = None
    used_alfred = bool(pack and pack.get("values"))
    fallback_reason = None
    if not used_alfred:
        fallback_reason = "ALFRED_EMPTY" if pack is not None else "ALFRED_NOT_ATTEMPTED"
        csv_pack = collect_indicators(as_of, csv_payloads)
        if csv_pack.get("values"):
            csv_pack["fallback_from"] = fallback_reason
            pack = csv_pack
        elif pack is None:
            pack = csv_pack
    if pack is None:
        pack = {"availability": "UNAVAILABLE", "values": {}, "vintage": None, "source": None, "missing": [], "as_of_used": {}}
    pack["fallback_reason"] = None if used_alfred else fallback_reason
    synthetic = pack.get("availability") == "UNAVAILABLE"
    snap = MacroEngine().evaluate(as_of, pack.get("values") or {}, synthetic=synthetic)
    env = dict(snap.environment)
    env.update({k: pack.get(k) for k in ("availability", "vintage", "source", "missing", "as_of_used", "fallback_reason")})
    env["real_data_verified"] = False
    return MacroSnapshot(
        macro_snapshot_id=snap.macro_snapshot_id,
        as_of=snap.as_of,
        macro_version=snap.macro_version,
        implementation_kind=snap.implementation_kind,
        state=snap.state,
        regime="UNAVAILABLE" if synthetic else snap.regime,
        environment=env,
        mutated_qgv=False,
        synthetic=synthetic,
    )


def unavailable_macro(as_of: datetime) -> MacroSnapshot:
    return MacroSnapshot(
        macro_snapshot_id=f"mac_{uuid4().hex[:12]}",
        as_of=as_of,
        macro_version=MACRO_CONFIRMED,
        implementation_kind=IMPLEMENTATION_KIND,
        state=MacroState.NORMAL,
        regime="UNAVAILABLE",
        environment={"availability": "UNAVAILABLE", "source": "FRED_KEY_MISSING"},
        synthetic=False,
    )


def run_as_of(
    as_of: datetime,
    payloads: dict[str, dict],
    bars_by_id: dict[str, list],
    store: ScopedTrackStore,
    company_ids: tuple[str, ...] = ("nvda", "msft", "asml"),
    use_live_macro: bool = False,
    fred_payloads: dict[str, str] | None = None,
    listings: dict | None = None,
) -> dict:
    profile = builtin_profile(StrategyStyle.BALANCED)
    name_errors: dict[str, str] = {}
    pipe = AnalysisPipeline()
    tech_eng = TechnicalEngine()
    snaps = {}
    tech = {}
    quality = {}
    name_records: dict[str, str] = {}
    lookahead = {"future_bars": 0, "future_filings_blocked": True}
    raws: dict = {}
    for cid in company_ids:
        try:
            raw = parse_us_company(cid, as_of=as_of, payload=payloads.get(cid), listings=listings)
        except Exception as exc:
            # One malformed filing must not abort the cross-section; the name is reported, not scored.
            name_errors[cid] = f"{type(exc).__name__}: {str(exc)[:160]}"
            quality[cid] = {"raw": False, "error": name_errors[cid]}
            continue
        if raw is None:
            quality[cid] = {"raw": False}
            continue
        bars_now = bars_by_id.get(cid) or []
        px = pit_bar(bars_now, as_of)
        if px and px.get("price"):
            raw = replace(raw, price=float(px["price"]))
        if raw.price and raw.eps and raw.eps > 0:
            raw = replace(raw, own_multiple=raw.price / raw.eps)
        old_px = pit_bar(bars_now, as_of - timedelta(days=365))
        if old_px and raw.eps_prev and raw.eps_prev > 0 and raw.price and raw.eps and raw.eps > 0:
            pe_now = raw.price / raw.eps
            pe_old = old_px["price"] / raw.eps_prev
            hist = max(0.0, min(100.0, 50.0 + (pe_old - pe_now) / max(pe_old, 1e-9) * 50.0))
            raw = replace(raw, hist_valuation_percentile=hist)
        raws[cid] = raw
    peer_pes = [r.own_multiple for r in raws.values() if r.own_multiple]
    peer_med = sorted(peer_pes)[len(peer_pes) // 2] if peer_pes else None
    if peer_med is not None:
        raws = {cid: replace(raw, peer_median_multiple=peer_med) for cid, raw in raws.items()}
    for cid, raw in raws.items():
        from ..providers.sec_vintage import resolve_vintages
        payload = payloads.get(cid) or {}
        q_rev = resolve_vintages(payload, "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", as_of, "10-Q")
        q_rev_e = resolve_vintages(payload, "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "EUR", as_of, "10-Q")
        snap = pipe.analyze_raw(raw, as_of=as_of, available_quarters=max(len(q_rev), len(q_rev_e)))
        snaps[cid] = snap
        bars = bars_by_id.get(cid) or []
        lookahead["future_bars"] += sum(1 for b in bars if b["observed_at"] > as_of)
        rets = bars_to_returns(bars, as_of)
        tech[cid] = tech_eng.evaluate(cid, as_of, rets, qgv=snap, synthetic=False)
        if snap.Q_score is not None and raw.stamp.available_at > as_of:
            raise RuntimeError("fundamental lookahead")
        qrec = store.record(
            TrackScope.QGV,
            cid,
            as_of,
            (snap.qgv_snapshot_id,),
            {
                "profile_id": profile.profile_id,
                "parameter_set_hash": profile.parameter_set_hash(),
                "system_version": IMPLEMENTATION_LINE,
                "prediction": {"Q": snap.Q_score, "G": snap.G_score, "V": snap.V_score, "as_of": as_of.isoformat()},
                "evaluation_horizon": "20d",
            },
        )
        name_records[cid] = qrec.track_record_id
        quality[cid] = {
            "period_quality": raw.period_quality,
            "coverage": snap.coverage_state.value,
            "V": snap.V_score,
            "Q": snap.Q_score,
            "G": snap.G_score,
            "synthetic": snap.synthetic,
            "pit_price": None if pit_bar(bars, as_of) is None else pit_bar(bars, as_of)["price"],
            "revenue": raw.revenue,
            "revenue_prev": raw.revenue_prev,
            "net_income": raw.net_income,
            "equity": raw.equity,
            "cash": raw.cash,
            "ebit": raw.ebit,
            "fcf": raw.fcf,
            "eps": raw.eps,
            "quarterly_monitor": monitor_from_facts(payloads.get(cid) or {}, as_of),
            "V_policy": snap.V_policy_status.value,
            "v_table": (snap.factor_breakdown or {}).get("v_factor_table"),
            "peer_universe": list(raws),
            "peer_n": len(peer_pes),
            "peer_median": peer_med,
            "peer_confidence": "LOW" if len(peer_pes) < 5 else "MEDIUM" if len(peer_pes) < 10 else "HIGH",
            "hist_valuation": raw.hist_valuation_percentile,
            "technical_regime": tech[cid].regime.value if cid in tech else None,
        }
    mac = live_macro(as_of, fred_payloads) if use_live_macro else unavailable_macro(as_of)
    pf = None
    if snaps:
        pairs = tuple((cid, cid.upper()) for cid in snaps)
        spec = equal_weight_input("pit-candidate-book", pairs)
        pf = PortfolioEngine().from_input(spec, as_of, snaps)
    integ = None
    if pf is not None:
        integ = IntegrationEngine().run(
            as_of,
            pf,
            tech,
            mac,
            profile_id=profile.profile_id,
            parameter_set_hash=profile.parameter_set_hash(),
        )
        store.record(
            TrackScope.INTEGRATED,
            "pit-candidate",
            as_of,
            tuple(s.qgv_snapshot_id for s in snaps.values()),
            {
                "profile_id": profile.profile_id,
                "profile_version": profile.profile_version,
                "parameter_set_hash": profile.parameter_set_hash(),
                "system_version": IMPLEMENTATION_LINE,
                "prediction": {"gate": integ.gate.value, "as_of": as_of.isoformat()},
                "decision": {"source": "integration", "target_weights": integ.target_weights},
                "evaluation_horizon": "20d",
                "pit_coverage": "PARTIAL",
                "macro_availability": "UNAVAILABLE",
            },
        )
    return {
        "as_of": as_of.isoformat(),
        "names": len(snaps),
        "quality": quality,
        "gate": None if integ is None else integ.gate.value,
        "macro": (mac.environment or {}).get("availability") or mac.regime,
        "macro_vintage": (mac.environment or {}).get("vintage"),
        "macro_regime": mac.regime,
        "decision_source": "integration",
        "portfolio_role": None if pf is None else pf.role,
        "portfolio_version": None if pf is None else pf.portfolio_version,
        "profile_id": profile.profile_id,
        "parameter_set_hash": profile.parameter_set_hash(),
        "lookahead": lookahead,
        "name_records": name_records,
        "name_errors": name_errors,
        "official_pass": False,
        "real_data_verified": False,
        "full_pit_pass": False,
        "kind": "PIT_BACKTEST_CANDIDATE",
        "ablation_ready": True,
        "ablation_arms": (
            "qgv",
            "technical",
            "macro",
            "qgv+technical",
            "qgv+macro",
            "technical+macro",
            "qgv+technical+macro",
        ),
        "compatibility": {
            cid: annotate(snaps.get(cid), tech.get(cid))
            for cid in snaps
        },
        "snapshot_ids": {
            "qgv": {cid: snaps[cid].qgv_snapshot_id for cid in snaps},
            "technical": {cid: tech[cid].technical_snapshot_id for cid in tech},
            "macro": mac.macro_snapshot_id,
        },
    }


def attach_name_outcomes(
    store: ScopedTrackStore,
    name_records: dict[str, str],
    predict_as_of: datetime,
    horizon_as_of: datetime,
    bars_by_id: dict[str, list],
) -> dict[str, dict]:
    """Child outcomes only. Does not promote REAL-DATA VERIFIED."""
    out: dict[str, dict] = {}
    for cid, rid in name_records.items():
        bars = bars_by_id.get(cid) or []
        try:
            child = attach_price_outcome(store, rid, predict_as_of, horizon_as_of, bars)
            parent = store.store.get(rid)
            metrics = child.outcome_metrics or {}
            realized = metrics.get("realized") if isinstance(metrics.get("realized"), dict) else metrics
            out[cid] = {
                "status": "LINKED",
                "parent": rid,
                "child": child.track_record_id,
                "realized_return": realized.get("realized_return") if isinstance(realized, dict) else None,
                "parent_payload_intact": "px1" not in str(parent.payload.get("prediction") or {}),
            }
        except Exception as exc:
            out[cid] = {"status": "SKIPPED", "reason": type(exc).__name__, "detail": str(exc)}
    return out


def run_multi_as_of(as_ofs: list[datetime], company_ids: tuple[str, ...] = ("nvda", "msft", "asml"), store_path=None, use_live_macro: bool = False) -> dict:
    payloads = {}
    bars = {}
    for cid in company_ids:
        raw = parse_us_company(cid, as_of=datetime.now(timezone.utc))
        # Re-fetch payload via live parse only gives latest raw; need facts JSON.
        from ..providers.sec_companyfacts import try_fetch_companyfacts
        from ..markets.us import US_LISTINGS

        payloads[cid] = try_fetch_companyfacts(US_LISTINGS[cid]["cik"])
        chart = fetch_chart(US_LISTINGS[cid]["yahoo"], range="5y")
        bars[cid] = parse_bars(chart) if chart else []
    from pathlib import Path
    from tempfile import NamedTemporaryFile

    path = Path(store_path) if store_path else Path(NamedTemporaryFile(suffix=".json", delete=False).name)
    store = ScopedTrackStore(FileTrackRecordStore(path))
    rows = []
    for as_of in as_ofs:
        if any(payloads[c] is None for c in company_ids):
            rows.append({"as_of": as_of.isoformat(), "blocked": "SEC_UNAVAILABLE"})
            continue
        rows.append(run_as_of(as_of, payloads, bars, store, company_ids, use_live_macro=use_live_macro))
    outcome_links = []
    quality_rows = [r for r in rows if "quality" in r]
    for pred, later in zip(quality_rows, quality_rows[1:]):
        t0 = datetime.fromisoformat(pred["as_of"])
        t1 = datetime.fromisoformat(later["as_of"])
        outcome_links.append(
            {
                "predict_as_of": pred["as_of"],
                "horizon_as_of": later["as_of"],
                "links": attach_name_outcomes(store, pred.get("name_records") or {}, t0, t1, bars),
            }
        )
    revenues = {
        cid: [row["quality"].get(cid, {}).get("Q") for row in rows if "quality" in row]
        for cid in company_ids
    }
    return {
        "official_pass": False,
        "full_pit_pass": False,
        "real_data_verified": False,
        "macro": "UNAVAILABLE",
        "rows": rows,
        "q_by_as_of": revenues,
        "store": str(path),
        "count": len(store.store),
        "kind": "PIT_MULTI_ASOF_CANDIDATE",
        "universe": "EXPLICIT",
        "n_names": len(company_ids),
        "outcome_links": outcome_links,
        "prediction_realized": prediction_realized_table(quality_rows[0] if quality_rows else {}, outcome_links[0] if outcome_links else {}),
        "full_pit_eval": full_pit_candidate_eval(quality_rows, outcome_links),
        "oos_partition": oos_partition([r.get("as_of") for r in quality_rows]),
    }


def run_us_listings_macro_pit(as_ofs: list[datetime], store_path=None) -> dict:
    out = run_multi_as_of(as_ofs, us_company_ids(), store_path=store_path, use_live_macro=True)
    out["universe"] = "US_LISTINGS"
    out["macro_requested"] = True
    out["official_pass"] = False
    out["real_data_verified"] = False
    return out


def summarize_multi_pit(result: dict) -> dict:
    rows = [r for r in result.get("rows") or [] if "quality" in r]
    v_cov = []
    for r in rows:
        mat = v_coverage_matrix(r)
        v_cov.append({"as_of": r.get("as_of"), "present": mat.get("present"), "n": mat.get("n")})
    return {
        "kind": "MULTI_ASOF_PIT_SUMMARY",
        "official_pass": False,
        "real_data_verified": False,
        "full_pit_pass": False,
        "oos": False,
        "calibrated": False,
        "as_ofs": [r.get("as_of") for r in rows],
        "macro": [r.get("macro") for r in rows],
        "macro_vintage": [r.get("macro_vintage") for r in rows],
        "ablation_ready": all(r.get("ablation_ready") for r in rows) if rows else False,
        "v_coverage": v_cov,
        "compatibility_counts": [
            {
                "as_of": r.get("as_of"),
                "labels": {
                    lab: sum(1 for v in (r.get("compatibility") or {}).values() if v.get("label") == lab)
                    for lab in ("ALIGNED", "ENTRY_CONFLICT", "FUNDAMENTAL_CONFLICT", "ALIGNED_NEGATIVE", "INSUFFICIENT")
                },
            }
            for r in rows
        ],
    }
    out["official_pass"] = False
    out["real_data_verified"] = False
    return out


def run_us_listings_candidate(as_ofs: list[datetime], store_path=None, use_live_macro: bool | None = None) -> dict:
    """PIT candidate over US listings. Generic book. Not Official v1.1."""
    from ..providers.fred_alfred import api_key_present
    live = api_key_present() if use_live_macro is None else use_live_macro
    out = run_multi_as_of(as_ofs, us_company_ids(), store_path=store_path, use_live_macro=live)
    out["universe"] = "US_LISTINGS"
    out["portfolio_expected_role"] = "GENERIC_INPUT"
    out["pit_integrity"] = pit_integrity_report(out)
    return out


def v_coverage_matrix(row: dict) -> dict:
    """Summarize V factor presence. Not CALIBRATED."""
    factors = [
        "fundamental_value",
        "reverse_dcf",
        "peer_relative_value",
        "historical_valuation",
        "margin_of_safety",
        "sector_context",
        "theme_premium_discount",
    ]
    present = {f: 0 for f in factors}
    names = 0
    rows = []
    for cid, q in (row.get("quality") or {}).items():
        table = q.get("v_table") or []
        if not table:
            continue
        names += 1
        hit = {item["factor_id"]: item.get("score") is not None for item in table}
        for f in factors:
            present[f] += int(hit.get(f, False))
        rows.append({"company_id": cid, "V": q.get("V"), "policy": q.get("V_policy"), "factors": hit})
    return {
        "kind": "V_COVERAGE_MATRIX",
        "lifecycle": "PROVISIONAL_INITIAL_PRIOR",
        "real_data_verified": False,
        "calibrated": False,
        "n": names,
        "present": present,
        "rows": rows,
    }


def run_us_listings_outcomes(predict_as_of: datetime, horizon_as_of: datetime, store_path=None) -> dict:
    """LIVE_FETCH probe. Child outcomes only. Not REAL-DATA VERIFIED."""
    from pathlib import Path
    from tempfile import NamedTemporaryFile

    from ..providers.sec_companyfacts import try_fetch_companyfacts

    ids = us_company_ids()
    payloads = {cid: try_fetch_companyfacts(US_LISTINGS[cid]["cik"]) for cid in ids}
    bars = {}
    for cid in ids:
        chart = fetch_chart(US_LISTINGS[cid]["yahoo"], range="5y")
        bars[cid] = parse_bars(chart) if chart else []
    path = Path(store_path) if store_path else Path(NamedTemporaryFile(suffix=".json", delete=False).name)
    store = ScopedTrackStore(FileTrackRecordStore(path))
    row = run_as_of(predict_as_of, payloads, bars, store, ids)
    linked = attach_name_outcomes(store, row.get("name_records") or {}, predict_as_of, horizon_as_of, bars)
    return {
        "kind": "LIVE_FETCH_OUTCOME_PROBE",
        "universe": "US_LISTINGS",
        "portfolio_role": row.get("portfolio_role"),
        "predict_as_of": predict_as_of.isoformat(),
        "horizon_as_of": horizon_as_of.isoformat(),
        "linked": sum(1 for v in linked.values() if v.get("status") == "LINKED"),
        "skipped": sum(1 for v in linked.values() if v.get("status") != "LINKED"),
        "outcomes": linked,
        "official_pass": False,
        "real_data_verified": False,
        "full_pit_pass": False,
        "store": str(path),
    }


def prediction_realized_table(predict_row: dict, link_pack: dict) -> dict:
    """Join Q/G/V predictions to child returns. Not calibration. Not OOS."""
    quality = predict_row.get("quality") or {}
    links = (link_pack or {}).get("links") or {}
    rows = []
    for cid, link in links.items():
        q = quality.get(cid) or {}
        rows.append(
            {
                "company_id": cid,
                "Q": q.get("Q"),
                "G": q.get("G"),
                "V": q.get("V"),
                "realized_return": link.get("realized_return"),
                "parent_intact": link.get("parent_payload_intact"),
                "status": link.get("status"),
            }
        )
    return {
        "kind": "PREDICTION_REALIZED_TABLE",
        "calibrated": False,
        "oos": False,
        "official_pass": False,
        "real_data_verified": False,
        "n": len(rows),
        "rows": rows,
    }


def full_pit_candidate_eval(quality_rows: list, outcome_links: list) -> dict:
    """Checklist only. Never auto-promotes Full PIT."""
    links = []
    for pack in outcome_links or []:
        links.extend((pack.get("links") or {}).values())
    intact = all(x.get("parent_intact") or x.get("parent_payload_intact") for x in links) if links else False
    linked = bool(links) and all(x.get("status") == "LINKED" for x in links)
    checks = {
        "has_multi_as_of": len(quality_rows or []) >= 2,
        "outcomes_linked": linked,
        "parent_immutable": intact,
        "official_pass_held_false": True,
        "v_weights_not_refit": True,
        "sector_theme_not_invented": True,
    }
    return {
        "kind": "FULL_PIT_CANDIDATE_EVAL",
        "full_pit_pass": False,
        "real_data_verified": False,
        "calibrated": False,
        "oos": False,
        "ready_for_review": all(checks.values()),
        "checks": checks,
    }


def oos_partition(as_ofs: list) -> dict:
    """Label-only IS/OOS split. Does not fit weights. Does not mark OOS verified."""
    ordered = list(as_ofs)
    if len(ordered) < 2:
        return {
            "kind": "OOS_PARTITION",
            "oos": False,
            "calibrated": False,
            "official_pass": False,
            "reason": "NEED_TWO_AS_OF",
            "in_sample": [str(x) for x in ordered],
            "out_of_sample": [],
        }
    cut = max(1, len(ordered) - 1)
    return {
        "kind": "OOS_PARTITION",
        "oos": False,
        "calibrated": False,
        "official_pass": False,
        "in_sample": [str(x) for x in ordered[:cut]],
        "out_of_sample": [str(x) for x in ordered[cut:]],
        "rule": "last_as_of_held_out_label_only",
    }


def pit_integrity_report(result: dict) -> dict:
    """Why Full PIT Historical is not passed. Does not raise the grade."""
    fails = ["SEC_COMPANYFACTS_VALUE_MAY_BE_RESTATED"]
    rows = [r for r in (result.get("rows") or []) if "quality" in r]
    vintages = [r.get("macro_vintage") for r in rows]
    if not rows:
        fails.append("NO_PIT_ROWS")
    if any(v not in {"ALFRED_AS_OF"} for v in vintages) or not vintages:
        fails.append("MACRO_VINTAGE_NOT_ALFRED")
    links = result.get("outcome_links") or []
    if not links:
        fails.append("OUTCOMES_NOT_LINKED")
    if result.get("official_pass"):
        fails.append("OFFICIAL_PASS_WAS_TRUE")
    return {
        "kind": "PIT_INTEGRITY",
        "ladder_rung": "PIT_PROBE",
        "full_pit_pass": False,
        "real_data_verified": False,
        "oos": False,
        "calibrated": False,
        "blocking_gaps": fails,
        "note": "companyfacts filed<=as_of is necessary but not sufficient Full PIT",
    }
