"""Universe → existing QGV engine → per-company records → batch manifest.

The engine runs exactly as the Frozen Track A pipeline runs it: `run_vertical_slice_from_store` on the full
Official Universe snapshot. V uses a cross-section peer median, so a smaller universe would change the scores.
A SAMPLE batch therefore still runs the full cross-section; it only persists fewer companies, and its
manifest says SAMPLE.

Every Universe member gets exactly one record: PASS, FAIL or NOT_RUN. No member is dropped.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from ..contracts.enums import StrategyStyle
from ..contracts.strategy import builtin_profile
from ..contracts.universe import UniverseSnapshot
from ..ingestion.raw_store import RawDatasetStore
from ..ingestion.replay import load_price_bars
from ..providers.yahoo_chart import pit_bar
from ..validation.vertical_slice import RULE_ID, RULE_STATUS, run_vertical_slice_from_store
from .capture import capture_qgv_engine
from .record import (KNOWN_PIT_LIMITATIONS, RESEARCH_STATUS, STATUSES, QGVProducerError, canonical_sha256, make_record,
                     methodology_config_sha256, sha256_hex, snapshot_semantic, sub_factor_table, to_jsonable,
                     validate_semantic)

MANIFEST_KIND = "QGV_PRODUCER_BATCH_MANIFEST"
MANIFEST_VERSION = 1
CHART_RANGE = "5y"  # same as tools/official_pipeline.py (run_vertical_slice_from_store default)
# Engine quality-row keys copied verbatim (inputs the engine reports using). Peer list / monitors / technical are omitted.
QUALITY_KEYS = ("coverage", "period_quality", "V_policy", "pit_price", "hist_valuation", "peer_n", "peer_median",
                "peer_confidence", "revenue", "revenue_prev", "net_income", "equity", "cash", "ebit", "fcf", "eps")
RESEARCH_STATE = {"status": RESEARCH_STATUS, "rule_id": RULE_ID, "official_selection": False, "official_pass": False,
                  "full_pit_pass": False, "calibrated": False, "track_c_validated": False}


def _cik10(cik: str) -> str:
    return str(int(cik)).zfill(10)


def lineage_input(store: RawDatasetStore, artifact_id: str, store_index: Mapping[str, Mapping] | None) -> tuple[dict | None, list[str]]:
    """Hash the actual bytes and require agreement with the store manifest and (when given) the committed index."""
    if not store.has(artifact_id):
        return None, [f"LINEAGE_MISSING:{artifact_id}"]
    body = store.get_bytes(artifact_id)
    sha = sha256_hex(body)
    problems = []
    try:
        man = store.get_manifest(artifact_id)
    except (OSError, ValueError):
        man = {}
        problems.append(f"MANIFEST_MISSING:{artifact_id}")
    if man and man.get("sha256") != sha:
        problems.append(f"SOURCE_HASH_MISMATCH_MANIFEST:{artifact_id}")
    if store_index is not None:
        idx = store_index.get(artifact_id)
        if idx is None:
            problems.append(f"NOT_IN_STORE_INDEX:{artifact_id}")
        elif idx.get("sha256") != sha:
            problems.append(f"SOURCE_HASH_MISMATCH_INDEX:{artifact_id}")
    return {"artifact_id": "raw:" + artifact_id, "sha256": sha, "bytes": len(body),
            "source_kind": man.get("source_kind"), "source_url": man.get("source_url"),
            "fetched_at": man.get("fetched_at")}, problems


@dataclass
class BatchResult:
    as_of: str
    records: list[dict]
    manifest: dict
    engine_result: dict  # the unmodified run_vertical_slice result (kept in memory for invariance checks; not persisted)


def run_qgv_batch(store: RawDatasetStore, as_of: datetime, horizon_as_of: datetime, universe: UniverseSnapshot, *,
                  generated_at: str, code_commit: str, store_index: Mapping[str, Mapping] | None = None,
                  sample: Sequence[str] | None = None, universe_evidence: Mapping[str, Any] | None = None,
                  raw_source: Mapping[str, Any] | None = None, store_path=None, run_id: str | None = None) -> BatchResult:
    with capture_qgv_engine() as cap:
        res = run_vertical_slice_from_store(store, as_of, horizon_as_of, universe, chart_range=CHART_RANGE,
                                            store_path=store_path)
    ranked = {r["company_id"]: r for r in res["ranked"]}
    selected = set(res["selected"])
    # run_vertical_slice returns neither the QGVSnapshots nor their ids; the capture holds them, keyed by UUID.
    by_company: dict[str, list] = {}
    for call in cap.calls.values():
        by_company.setdefault(call.snapshot.company_id, []).append(call)
    prof = builtin_profile(StrategyStyle.BALANCED)  # the profile run_as_of records with; it does not enter the scores
    row_meta = {"profile_id": prof.profile_id, "parameter_set_hash": prof.parameter_set_hash()}
    wsha = methodology_config_sha256()
    if sample is not None:
        unknown = sorted(set(sample) - set(universe.ids()))
        if unknown:
            raise QGVProducerError("IDENTITY", f"sample ids not in the Universe: {unknown}")
    position = {cid: i for i, cid in enumerate(universe.ids(), start=1)}
    # Lineage for every member: V's peer median depends on the whole cross-section, even in a SAMPLE batch.
    lineage: dict[str, tuple[list, list]] = {}
    all_inputs = []
    for m in universe.members:
        inputs, reasons = [], []
        for aid in ([f"companyfacts:{_cik10(m.cik)}"] if m.cik else []) + [f"yahoo_chart:{m.ticker.upper()}:{CHART_RANGE}"]:
            inp, probs = lineage_input(store, aid, store_index)
            if inp is not None:
                inputs.append(inp)
                all_inputs.append([inp["artifact_id"], inp["sha256"]])
            for p in probs:
                # A missing price chart is the engine's canonical MISSING behaviour; a missing fundamentals source is not.
                reasons.append("PRICE_INPUT_ABSENT" if p.startswith("LINEAGE_MISSING:yahoo_chart") else p)
        if not m.cik:
            reasons.append("LINEAGE_MISSING:NO_CIK")
        lineage[m.company_id] = (sorted(inputs, key=lambda i: i["artifact_id"]), reasons)
    records = []
    keep = None if sample is None else set(sample)
    for m in universe.members:
        cid = m.company_id
        if keep is not None and cid not in keep:
            continue
        inputs, reasons = lineage[cid][0], list(lineage[cid][1])
        err = (res.get("name_errors") or {}).get(cid)
        calls = by_company.get(cid, [])
        call = calls[0] if len(calls) == 1 else None
        if len(calls) > 1:
            reasons.append("CAPTURE_MISMATCH:MULTIPLE_SNAPSHOTS")
        rrow = ranked.get(cid)
        bars = load_price_bars(store, m.ticker, CHART_RANGE)
        px = pit_bar(bars, as_of)
        old_px = pit_bar(bars, as_of - timedelta(days=365))
        snap = call.snapshot if call else None
        raw = call.raw if call else None
        if err is not None:
            status, reasons = "FAIL", [f"CALCULATION_ERROR:{err}"] + reasons
        elif len(calls) > 1:
            status = "FAIL"
        elif snap is None:
            status, reasons = "NOT_RUN", ["NO_FUNDAMENTALS_AT_AS_OF"] + reasons
        else:
            status = "PASS"
            if raw is None or call.observations is None:
                reasons.append("CAPTURE_MISMATCH:INCOMPLETE")
            if rrow is None or (rrow["Q"], rrow["G"], rrow["V"]) != (snap.Q_score, snap.G_score, snap.V_score):
                reasons.append("CAPTURE_MISMATCH:SCORES_DIFFER_FROM_ENGINE_RANKING")
            if raw is not None and px is not None and px.get("price") and raw.price != float(px["price"]):
                reasons.append("CAPTURE_MISMATCH:PIT_PRICE")
        semantic = {
            "company_id": cid, "ticker": m.ticker, "cik": m.cik, "as_of": as_of.isoformat(),
            "status": status, "status_reasons": sorted(set(reasons)),
            "universe": {"universe_id": universe.universe_id, "universe_kind": to_jsonable(universe.universe_kind),
                         "policy_status": to_jsonable(universe.policy_status), "membership_basis": universe.membership_basis,
                         "universe_available_at": to_jsonable(universe.available_at),
                         "member_position": position[cid], "evidence": dict(universe_evidence or {})},
            "methodology": {
                "qgv_system_version": snap.qgv_system_version if snap else None,
                "qgv_standard_version": snap.qgv_standard_version if snap else None,
                "qgv_analysis_contract": snap.qgv_analysis_contract if snap else None,
                "implementation_line": snap.implementation_line if snap else None,
                "weights_sha256": wsha, "profile_kind": to_jsonable(snap.profile_kind) if snap else None,
                "run_profile_id": row_meta["profile_id"], "run_parameter_set_hash": row_meta["parameter_set_hash"],
                "cross_section_rule_id": RULE_ID, "cross_section_rule_status": RULE_STATUS},
            "research_state": {**RESEARCH_STATE, "v_policy_status": to_jsonable(snap.V_policy_status) if snap else None},
            "synthetic": bool(snap.synthetic) if snap else False,
            "pit": {"rule": "fundamentals available_at <= as_of; price bars observed_at <= as_of (existing run_as_of/pit_bar)",
                    "fundamentals_available_at": to_jsonable(raw.stamp.available_at) if raw else None,
                    "fundamentals_stamp_id": raw.stamp.data_stamp_id if raw else None,
                    "fundamentals_quality_flags": list(raw.stamp.quality_flags) if raw else None,
                    "fundamentals_source_kind": raw.source_kind if raw else None,
                    "fundamentals_synthetic": bool(raw.stamp.synthetic) if raw else None,
                    "period_quality": raw.period_quality if raw else None,
                    "price_observed_at": to_jsonable(px["observed_at"]) if px and raw else None,
                    "prior_year_price_observed_at": to_jsonable(old_px["observed_at"]) if old_px and raw else None,
                    "known_limitations": list(KNOWN_PIT_LIMITATIONS)},
            "lineage": {"inputs": inputs,
                        "peer_context": "V peer_relative_value uses the cross-section P/E median of this Universe run; "
                                        "all members' inputs are hashed in the batch manifest data_lineage.inputs_sha256"},
            "qgv": snapshot_semantic(snap) if snap else None,
            "sub_factors": sub_factor_table(call.observations) if call and call.observations is not None else None,
            "cross_section": None if rrow is None else {"rank": rrow["rank"], "eligible": rrow["eligible"],
                                                        "selected_provisional": cid in selected,
                                                        "n_cross_section": len(res["ranked"])},
        }
        semantic = to_jsonable(semantic)
        if semantic["status"] == "PASS":
            blocking = [r for r in semantic["status_reasons"] if r != "PRICE_INPUT_ABSENT"]
            try:
                if blocking:
                    raise QGVProducerError(blocking[0].split(":")[0], ", ".join(blocking))
                validate_semantic(semantic)
            except QGVProducerError as e:
                semantic["status"] = "FAIL"
                semantic["status_reasons"] = sorted(set(semantic["status_reasons"]) | {str(e)})
        operational = {"generated_at": generated_at, "code_commit": code_commit, "run_id": run_id,
                       "qgv_snapshot_id": snap.qgv_snapshot_id if snap else None}
        records.append(make_record(semantic, operational))
    records.sort(key=lambda r: r["semantic"]["company_id"])
    manifest = build_manifest(records, res, universe, as_of, sample, universe_evidence, raw_source, store_index,
                              all_inputs, generated_at, code_commit, run_id, row_meta, wsha)
    return BatchResult(as_of=as_of.isoformat(), records=records, manifest=manifest, engine_result=res)


def ranked_fingerprint(ranked: list[dict]) -> str:
    """Numerical fingerprint of the engine's own ranked output (company, rank, eligible, exact Q/G/V)."""
    return canonical_sha256([{k: r[k] for k in ("company_id", "rank", "eligible", "Q", "G", "V")} for r in ranked])


def build_manifest(records, res, universe, as_of, sample, universe_evidence, raw_source, store_index, all_inputs,
                   generated_at, code_commit, run_id, row_meta, wsha) -> dict:
    counts = {s: sum(1 for r in records if r["semantic"]["status"] == s) for s in STATUSES}
    members = [{"company_id": m.company_id, "ticker": m.ticker, "cik": m.cik} for m in universe.members]
    rows = [{"company_id": r["semantic"]["company_id"], "status": r["semantic"]["status"],
             "status_reasons": r["semantic"]["status_reasons"], "semantic_sha256": r["semantic_sha256"]} for r in records]
    expected = len(members) if sample is None else len(set(sample))
    sem = {
        "as_of": as_of.isoformat(),
        "scope": "FULL_UNIVERSE" if sample is None else "SAMPLE",
        "scope_note": None if sample is None else "SAMPLE persistence of a full-Universe engine run; not a Universe validation",
        "sample_ids": None if sample is None else sorted(set(sample)),
        "universe": {"universe_id": universe.universe_id, "universe_kind": to_jsonable(universe.universe_kind),
                     "policy_status": to_jsonable(universe.policy_status), "membership_basis": universe.membership_basis,
                     "n_members": len(members), "members_sha256": canonical_sha256(members),
                     "evidence": dict(universe_evidence or {})},
        "expected_count": expected,
        "persisted_count": len(records),
        "counts": counts,
        "complete": counts["PASS"] == expected and len(records) == expected,
        "records": rows,
        "records_sha256": canonical_sha256(rows),
        "methodology": {"qgv_system_version": next((r["semantic"]["methodology"]["qgv_system_version"] for r in records
                                                     if r["semantic"]["qgv"]), None),
                        "qgv_standard_version": next((r["semantic"]["methodology"]["qgv_standard_version"] for r in records
                                                       if r["semantic"]["qgv"]), None),
                        "qgv_analysis_contract": next((r["semantic"]["methodology"]["qgv_analysis_contract"] for r in records
                                                        if r["semantic"]["qgv"]), None),
                        "implementation_line": next((r["semantic"]["methodology"]["implementation_line"] for r in records
                                                      if r["semantic"]["qgv"]), None),
                        "weights_sha256": wsha, "run_profile_id": row_meta["profile_id"],
                        "run_parameter_set_hash": row_meta["parameter_set_hash"],
                        "cross_section_rule_id": RULE_ID, "cross_section_rule_status": RULE_STATUS},
        "research_state": dict(RESEARCH_STATE),
        "engine_run": {"n_cross_section": len(res["ranked"]), "n_selected": res["n_selected"],
                       "n_investable": len(res["investable"]), "n_missing": len(res["missing_ok"]),
                       "n_name_errors": len(res.get("name_errors") or {}),
                       "ranked_sha256": ranked_fingerprint(res["ranked"]),
                       "selected_sha256": canonical_sha256(res["selected"])},
        "data_lineage": {"raw_source": dict(raw_source or {}),
                         "store_index_sha256": None if store_index is None else canonical_sha256(
                             sorted([k, v.get("sha256")] for k, v in store_index.items())),
                         "n_inputs": len(all_inputs),
                         "inputs_sha256": canonical_sha256(sorted(all_inputs))},
    }
    sem = to_jsonable(sem)
    return {"manifest_kind": MANIFEST_KIND, "manifest_version": MANIFEST_VERSION, "semantic": sem,
            "semantic_sha256": canonical_sha256(sem),
            "operational": {"generated_at": generated_at, "code_commit": code_commit, "run_id": run_id}}
