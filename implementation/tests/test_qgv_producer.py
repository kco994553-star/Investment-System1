"""QGV Real Producer v1: persistence, PIT/provenance fail-closed, determinism, exporter invariance.

The fixture store goes through the same path as the Frozen run:
RawDatasetStore → run_vertical_slice_from_store → run_as_of → AnalysisEngine.
The fixture data itself is test data, so nothing here claims a real-data result.
"""
import copy
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_system import versions
from investment_system.contracts.universe import UniverseMember
from investment_system.ingestion.raw_store import RawDatasetStore
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.factors import G_WEIGHTS, Q_WEIGHTS
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.qgv_producer import infra_boundary
from investment_system.qgv_producer.batch import ranked_fingerprint, run_qgv_batch
from investment_system.qgv_producer.capture import capture_qgv_engine
from investment_system.qgv_producer.exporter import export_batch, load_export, manifest_name, snapshots_name
from investment_system.qgv_producer.record import (QGVProducerError, canonical_sha256, make_record,
                                                   qgv_snapshot_from_record, to_jsonable, validate_record)
from investment_system.universe.engine import UniverseEngine
from investment_system.validation.vertical_slice import run_vertical_slice_from_store

UTC = timezone.utc
T0 = datetime(2025, 3, 31, tzinfo=UTC)
T1 = datetime(2025, 6, 30, tzinfo=UTC)
NAMES = {"aaa": ("AAA", "1000001", 100.0), "bbb": ("BBB", "1000002", 160.0), "ccc": ("CCC", "1000003", 90.0),
         "ddd": ("DDD", "1000004", 230.0), "eee": ("EEE", "1000005", 140.0)}


def _facts(base):
    years = (2021, 2022, 2023, 2024)
    rows = lambda f: [{"end": f"{y}-12-31", "val": f(base * (1.1 ** (y - 2021))), "filed": f"{y + 1}-02-15",
                       "form": "10-K", "fy": y, "fp": "FY", "accn": f"a{y}"} for y in years]
    return {"facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": rows(lambda v: v * 1e7)}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": rows(lambda v: v / 40)}},
        "NetIncomeLoss": {"units": {"USD": rows(lambda v: v * 1e6)}},
        "OperatingIncomeLoss": {"units": {"USD": rows(lambda v: v * 1.3e6)}},
        "StockholdersEquity": {"units": {"USD": rows(lambda v: v * 5e6)}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": rows(lambda v: v * 1.5e6)}},
        "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": rows(lambda v: v * 4e5)}},
    }}}


def _chart(sym, base):
    start = int(datetime(2023, 6, 1, tzinfo=UTC).timestamp())
    ts = [start + i * 7 * 86400 for i in range(120)]  # weekly to ~2025-09
    px = [round(base * (1 + 0.004 * i), 4) for i in range(120)]
    return {"chart": {"result": [{"meta": {"symbol": sym, "currency": "USD"}, "timestamp": ts,
                                  "indicators": {"quote": [{"close": px}], "adjclose": [{"adjclose": px}]}}]}}


def make_store(tmp_path, names=NAMES):
    store = RawDatasetStore(Path(tmp_path) / "raw")
    for cid, (sym, cik, base) in names.items():
        store.put(f"companyfacts:{cik.zfill(10)}", json.dumps(_facts(base)).encode(), "fixture", "SEC_COMPANYFACTS",
                  "application/json", "test")
        store.put(f"yahoo_chart:{sym}:5y", json.dumps(_chart(sym, base)).encode(), "fixture", "YAHOO_CHART",
                  "application/json", "test")
    index = {a: store.get_manifest(a) for a in store.list_ids()}
    return store, index


_UNIVERSES = {}


def universe(as_of, names=NAMES):
    """One snapshot per as_of. UniverseEngine mints a fresh universe_id per call; the real path pins the
    gate-evidence id (tools/official_pipeline.load_official), so a re-run sees the same Universe identity."""
    key = (as_of, tuple(names))
    if key not in _UNIVERSES:
        roster = tuple(UniverseMember(cid, sym, entered_on="2015-01-01", cik=cik) for cid, (sym, cik, _) in names.items())
        _UNIVERSES[key] = UniverseEngine().snapshot(as_of, roster=roster, source_vintage="2025-01-01")
    return _UNIVERSES[key]


def batch(store, index, as_of=T0, horizon=T1, uni=None, **kw):
    return run_qgv_batch(store, as_of, horizon, uni or universe(as_of), generated_at="2026-10-01T00:00:00+00:00",
                         code_commit="test", store_index=index, universe_evidence={"file": "fixture"}, **kw)


def rehash(rec):
    rec["semantic_sha256"] = canonical_sha256(rec["semantic"])
    return rec


def _run(tmp_path):
    store, index = make_store(tmp_path)
    return store, index, batch(store, index)


# ------------------------------------------------------------------ PASS path, identity, exact preservation
def test_engine_result_to_snapshot_pass(tmp_path):
    run = _run(tmp_path)
    _, _, b = run
    assert [r["semantic"]["status"] for r in b.records] == ["PASS"] * 5
    for r in b.records:
        validate_record(r)
        assert r["semantic"]["synthetic"] is False
        assert r["semantic"]["research_state"]["status"] == "PROVISIONAL_RESEARCH"
    assert b.manifest["semantic"]["complete"] is True and b.manifest["semantic"]["scope"] == "FULL_UNIVERSE"


def test_pit_valid_timestamps(tmp_path):
    run = _run(tmp_path)
    for r in run[2].records:
        p, as_of = r["semantic"]["pit"], datetime.fromisoformat(r["semantic"]["as_of"])
        assert datetime.fromisoformat(p["fundamentals_available_at"]) <= as_of
        assert datetime.fromisoformat(p["price_observed_at"]) <= as_of
        assert datetime.fromisoformat(p["prior_year_price_observed_at"]) <= as_of


def test_company_identity_preserved(tmp_path):
    run = _run(tmp_path)
    _, _, b = run
    for r in b.records:
        s = r["semantic"]
        sym, cik, _ = NAMES[s["company_id"]]
        assert (s["ticker"], s["cik"], s["qgv"]["company_id"]) == (sym, cik, s["company_id"])
        assert s["universe"]["universe_id"] == b.manifest["semantic"]["universe"]["universe_id"]


def test_qgv_scores_exactly_equal_plain_engine_run(tmp_path):
    store, index = make_store(tmp_path)
    plain = run_vertical_slice_from_store(store, T0, T1, universe(T0), chart_range="5y")
    b = batch(store, index)
    assert ranked_fingerprint(plain["ranked"]) == ranked_fingerprint(b.engine_result["ranked"])
    by_id = {r["company_id"]: r for r in plain["ranked"]}
    for r in b.records:
        q = r["semantic"]["qgv"]
        e = by_id[r["semantic"]["company_id"]]
        assert (q["Q_score"], q["G_score"], q["V_score"]) == (e["Q"], e["G"], e["V"])  # exact, not approx
        assert r["semantic"]["cross_section"]["rank"] == e["rank"]
    assert plain["selected"] == b.engine_result["selected"]


def test_sub_factors_are_the_ones_the_engine_scored(tmp_path):
    run = _run(tmp_path)
    for r in run[2].records:
        s = r["semantic"]
        sf, q = s["sub_factors"], s["qgv"]
        # Q/G: the engine's weighted sum over the persisted sub-factor scores (no renormalisation, freeze rule)
        for weights, key in ((Q_WEIGHTS, "Q_score"), (G_WEIGHTS, "G_score")):
            acc = sum(w * sf[f]["score_0_100"] for f, w in weights.items()
                      if f in sf and sf[f]["score_0_100"] is not None and sf[f]["quality"] not in ("BLOCKED_DEPENDENCY",))
            assert acc == pytest.approx(q[key], rel=1e-12, abs=1e-12)
        for row in q["factor_breakdown"]["v_factor_table"]:
            assert row["score"] == (sf[row["factor_id"]]["score_0_100"] if row["factor_id"] in sf else None)


def test_methodology_version_preserved(tmp_path):
    run = _run(tmp_path)
    for r in run[2].records:
        m, q = r["semantic"]["methodology"], r["semantic"]["qgv"]
        assert m["qgv_analysis_contract"] == q["qgv_analysis_contract"] == versions.QGV_ANALYSIS_CONTRACT
        assert m["qgv_standard_version"] == versions.QGV_STANDARD and m["qgv_system_version"] == versions.QGV_SYSTEM_LINE
        assert m["implementation_line"] == versions.IMPLEMENTATION_LINE
        assert m["cross_section_rule_status"] == "PROVISIONAL_RESEARCH"


def test_snapshot_reconstruction_is_verbatim(tmp_path):
    run = _run(tmp_path)
    for r in run[2].records:
        snap = qgv_snapshot_from_record(r)
        d = to_jsonable(snap)
        assert d.pop("qgv_snapshot_id") == r["operational"]["qgv_snapshot_id"]
        assert d == r["semantic"]["qgv"]


def test_capture_restores_engine_and_passes_values_through(tmp_path):
    a, p = AnalysisEngine.analyze, AnalysisPipeline.analyze_raw
    with capture_qgv_engine():
        assert AnalysisEngine.analyze is not a
        with pytest.raises(RuntimeError):
            with capture_qgv_engine():
                pass
    assert AnalysisEngine.analyze is a and AnalysisPipeline.analyze_raw is p


# ------------------------------------------------------------------ determinism
def test_same_input_same_semantic_hash(tmp_path):
    store, index = make_store(tmp_path)
    b1, b2 = batch(store, index), batch(store, index)
    assert [r["semantic_sha256"] for r in b1.records] == [r["semantic_sha256"] for r in b2.records]
    assert b1.manifest["semantic_sha256"] == b2.manifest["semantic_sha256"]
    # operational ids genuinely differ; they are outside the semantic hash
    assert {r["operational"]["qgv_snapshot_id"] for r in b1.records}.isdisjoint(
        {r["operational"]["qgv_snapshot_id"] for r in b2.records})


def test_universe_identity_is_part_of_the_semantic_hash(tmp_path):
    store, index = make_store(tmp_path)
    roster = tuple(UniverseMember(cid, sym, entered_on="2015-01-01", cik=cik) for cid, (sym, cik, _) in NAMES.items())
    other = UniverseEngine().snapshot(T0, roster=roster, source_vintage="2025-01-01")
    a, b = batch(store, index), batch(store, index, uni=other)
    assert all(x["semantic_sha256"] != y["semantic_sha256"] for x, y in zip(a.records, b.records))
    assert [x["semantic"]["qgv"] for x in a.records] == [y["semantic"]["qgv"] for y in b.records]


def test_different_as_of_distinct_snapshot(tmp_path):
    store, index = make_store(tmp_path)
    t = datetime(2025, 6, 30, tzinfo=UTC)
    b1, b2 = batch(store, index), batch(store, index, as_of=t, horizon=datetime(2025, 9, 1, tzinfo=UTC), uni=universe(t))
    h1 = {r["semantic"]["company_id"]: r["semantic_sha256"] for r in b1.records}
    h2 = {r["semantic"]["company_id"]: r["semantic_sha256"] for r in b2.records}
    assert all(h1[c] != h2[c] for c in h1)
    assert all(r["semantic"]["as_of"] == t.isoformat() for r in b2.records)
    assert b1.manifest["semantic_sha256"] != b2.manifest["semantic_sha256"]


def test_deterministic_manifest_and_export_bytes(tmp_path):
    store, index = make_store(tmp_path)
    b1, b2 = batch(store, index), batch(store, index)
    m1 = export_batch(b1.records, b1.manifest, tmp_path / "o1")
    m2 = export_batch(b2.records, b2.manifest, tmp_path / "o2")
    assert m1["semantic"] == m2["semantic"]
    strip = lambda p: [json.loads(x)["semantic"] for x in (p / snapshots_name(T0.isoformat())).read_text().splitlines()]
    assert strip(tmp_path / "o1") == strip(tmp_path / "o2")


def test_sample_scope_equals_full_run_records(tmp_path):
    store, index = make_store(tmp_path)
    full = {r["semantic"]["company_id"]: r["semantic_sha256"] for r in batch(store, index).records}
    s = batch(store, index, sample=["ccc", "aaa"])
    assert [r["semantic"]["company_id"] for r in s.records] == ["aaa", "ccc"]
    assert all(full[r["semantic"]["company_id"]] == r["semantic_sha256"] for r in s.records)
    assert s.manifest["semantic"]["scope"] == "SAMPLE" and s.manifest["semantic"]["expected_count"] == 2
    assert "not a Universe validation" in s.manifest["semantic"]["scope_note"]
    with pytest.raises(QGVProducerError):
        batch(store, index, sample=["zzz"])


# ------------------------------------------------------------------ fail-closed
def _pass_record(run):
    return copy.deepcopy(run[2].records[0])


def test_pit_violation_fails(tmp_path):
    run = _run(tmp_path)
    r = _pass_record(run)
    r["semantic"]["pit"]["fundamentals_available_at"] = "2025-04-01T00:00:00+00:00"
    with pytest.raises(QGVProducerError, match="PIT_VIOLATION"):
        validate_record(rehash(r))
    r = _pass_record(run)
    r["semantic"]["pit"]["price_observed_at"] = "2025-04-02T00:00:00+00:00"
    with pytest.raises(QGVProducerError, match="PIT_VIOLATION"):
        validate_record(rehash(r))
    r = _pass_record(run)
    r["semantic"]["pit"]["fundamentals_available_at"] = None
    with pytest.raises(QGVProducerError, match="PIT_EVIDENCE_MISSING"):
        validate_record(rehash(r))


def test_pit_violation_at_engine_input_aborts_before_persistence(tmp_path, monkeypatch):
    """A fundamentals stamp later than as_of at the engine input: run_as_of's own lookahead guard raises,
    so the producer persists nothing (fail-closed); the record-level check above is the second layer."""
    store, index = make_store(tmp_path)
    import investment_system.validation.historical as hist
    orig = hist.parse_us_company

    def late(cid, **kw):
        raw = orig(cid, **kw)
        if cid == "bbb" and raw is not None:
            raw = replace(raw, stamp=replace(raw.stamp, available_at=datetime(2025, 5, 1, tzinfo=UTC)))
        return raw
    monkeypatch.setattr(hist, "parse_us_company", late)
    out = tmp_path / "out"
    with pytest.raises(RuntimeError, match="lookahead"):
        b = batch(store, index)
        export_batch(b.records, b.manifest, out)
    assert not out.exists()


def test_missing_provenance_fails(tmp_path):
    run = _run(tmp_path)
    r = _pass_record(run)
    r["semantic"]["lineage"]["inputs"] = []
    with pytest.raises(QGVProducerError, match="MISSING_PROVENANCE"):
        validate_record(rehash(r))
    r = _pass_record(run)
    r["semantic"]["lineage"]["inputs"] = [i for i in r["semantic"]["lineage"]["inputs"] if "companyfacts" not in i["artifact_id"]]
    with pytest.raises(QGVProducerError, match="MISSING_PROVENANCE"):
        validate_record(rehash(r))
    r = _pass_record(run)
    r["semantic"]["lineage"]["inputs"][0]["sha256"] = "x" * 64
    with pytest.raises(QGVProducerError, match="SOURCE_HASH"):
        validate_record(rehash(r))


def test_synthetic_real_mismatch_fails(tmp_path):
    run = _run(tmp_path)
    r = _pass_record(run)
    r["semantic"]["qgv"]["synthetic"] = True
    with pytest.raises(QGVProducerError, match="SYNTHETIC_STATE"):
        validate_record(rehash(r))
    r = _pass_record(run)
    r["semantic"]["sub_factors"][next(iter(r["semantic"]["sub_factors"]))]["quality"] = "SYNTHETIC"
    with pytest.raises(QGVProducerError, match="SYNTHETIC_STATE"):
        validate_record(rehash(r))
    r = _pass_record(run)  # consistently synthetic: not exportable by the real producer
    r["semantic"]["synthetic"] = True
    r["semantic"]["qgv"]["synthetic"] = True
    with pytest.raises(QGVProducerError, match="real producer does not export synthetic"):
        validate_record(rehash(r))


def test_semantic_tamper_detected(tmp_path):
    run = _run(tmp_path)
    r = _pass_record(run)
    r["semantic"]["qgv"]["Q_score"] = r["semantic"]["qgv"]["Q_score"] + 1e-9
    with pytest.raises(QGVProducerError, match="SEMANTIC_HASH"):
        validate_record(r)


def test_promotion_forbidden(tmp_path):
    run = _run(tmp_path)
    for status in ("OFFICIAL", "VALIDATED", "PROMOTED", "LIVE_OFFICIAL"):
        r = _pass_record(run)
        r["semantic"]["research_state"]["status"] = status
        with pytest.raises(QGVProducerError, match="PROMOTION_FORBIDDEN"):
            validate_record(rehash(r))
    r = _pass_record(run)
    r["semantic"]["research_state"]["v_policy_status"] = "CALIBRATED"
    with pytest.raises(QGVProducerError, match="PROMOTION_FORBIDDEN"):
        validate_record(rehash(r))


def test_research_flags_cannot_flip(tmp_path):
    run = _run(tmp_path)
    r = _pass_record(run)
    r["semantic"]["research_state"]["official_selection"] = True
    with pytest.raises(QGVProducerError, match="PROMOTION_FORBIDDEN"):
        validate_record(rehash(r))


def test_outcome_data_never_in_snapshot(tmp_path):
    run = _run(tmp_path)
    r = _pass_record(run)
    r["semantic"]["cross_section"]["realized_return"] = 0.1
    with pytest.raises(QGVProducerError, match="OUTCOME_LEAK"):
        validate_record(rehash(r))
    for rec in run[2].records:
        assert "realized_return" not in json.dumps(rec)


def test_missing_company_evidence_fail_closed(tmp_path, monkeypatch):
    store, index = make_store(tmp_path)
    # (1) source bytes differ from the committed index: scored by the engine, but FAIL
    store.put("companyfacts:0001000002", json.dumps(_facts(161.0)).encode(), "fixture", "SEC_COMPANYFACTS", "application/json", "test")
    # (2) fundamentals blob absent: no live fetch may replace it
    (store.root / "blobs" / "companyfacts__0001000003").unlink()
    calls = []
    import investment_system.providers.us_sec as us_sec
    monkeypatch.setattr(us_sec, "try_fetch_companyfacts", lambda cik: calls.append(cik))
    b = batch(store, index)
    st = {r["semantic"]["company_id"]: r["semantic"] for r in b.records}
    assert st["bbb"]["status"] == "FAIL" and "SOURCE_HASH_MISMATCH_INDEX:companyfacts:0001000002" in st["bbb"]["status_reasons"]
    assert st["ccc"]["status"] == "NOT_RUN" and "LINEAGE_MISSING:companyfacts:0001000003" in st["ccc"]["status_reasons"]
    assert calls == ["1000003"]  # the engine asked; the replay returned nothing; nothing was fabricated
    m = b.manifest["semantic"]
    assert m["counts"] == {"PASS": 3, "FAIL": 1, "NOT_RUN": 1} and m["complete"] is False and m["expected_count"] == 5


# ------------------------------------------------------------------ exporter
def test_exporter_does_not_modify_scores_or_ranking(tmp_path):
    store, index = make_store(tmp_path)
    b = batch(store, index)
    before = copy.deepcopy(b.records)
    out = tmp_path / "out"
    export_batch(b.records, b.manifest, out)
    assert b.records == before
    loaded, m = load_export(out, T0.isoformat())
    assert loaded == before
    ranks = {r["company_id"]: r["rank"] for r in b.engine_result["ranked"]}
    assert {r["semantic"]["company_id"]: r["semantic"]["cross_section"]["rank"] for r in loaded} == ranks
    assert m["semantic"]["engine_run"]["ranked_sha256"] == ranked_fingerprint(b.engine_result["ranked"])


def test_partial_batch_is_reported_never_hidden(tmp_path, monkeypatch):
    store, index = make_store(tmp_path)
    (store.root / "blobs" / "companyfacts__0001000004").unlink()
    import investment_system.providers.us_sec as us_sec
    monkeypatch.setattr(us_sec, "try_fetch_companyfacts", lambda cik: None)
    b = batch(store, index)
    out = tmp_path / "out"
    m = export_batch(b.records, b.manifest, out)
    assert m["semantic"]["counts"]["NOT_RUN"] == 1 and m["semantic"]["complete"] is False
    with pytest.raises(QGVProducerError, match="MANIFEST_MISMATCH|PARTIAL_BATCH_HIDDEN"):
        export_batch([r for r in b.records if r["semantic"]["status"] == "PASS"], b.manifest, tmp_path / "o2")


def test_failed_export_keeps_previous_files(tmp_path):
    store, index = make_store(tmp_path)
    b = batch(store, index)
    out = tmp_path / "out"
    export_batch(b.records, b.manifest, out)
    snap = (out / snapshots_name(T0.isoformat())).read_bytes()
    man = (out / manifest_name(T0.isoformat())).read_bytes()
    bad = copy.deepcopy(b.records)
    bad[0]["semantic"]["qgv"]["Q_score"] = 0.0
    with pytest.raises(QGVProducerError):
        export_batch(bad, b.manifest, out)
    assert (out / snapshots_name(T0.isoformat())).read_bytes() == snap and (out / manifest_name(T0.isoformat())).read_bytes() == man
    (out / snapshots_name(T0.isoformat())).write_bytes(snap.replace(b'"PASS"', b'"FAIL"', 1))
    with pytest.raises(QGVProducerError):
        load_export(out, T0.isoformat())


# ------------------------------------------------------------------ Producer Infrastructure boundary
def test_export_decision_is_blocked_research():
    m = {"semantic": {"complete": True, "counts": {}, "research_state": {"status": "PROVISIONAL_RESEARCH"}}}
    d = infra_boundary.export_decision(m)
    assert d["data_state"] == "NOT_AVAILABLE" and d["reason_code"] == "QGV_RESEARCH_ONLY_NO_EXPORT"
    assert "TRACK_C_VALIDATION_NOT_COMPLETE" in d["blockers"] and "P01_RESEARCH_DATA_STATE_NOT_APPROVED" in d["blockers"]


def test_infra_dependency_absent_on_this_branch_is_explicit():
    # Producer Infrastructure v1 is not merged into this branch; the boundary says so instead of forking its schema.
    import importlib.util
    if importlib.util.find_spec("investment_system.producers") is None:
        assert infra_boundary.load_infra() is None
    else:  # once merged, the consumed API must be complete
        assert infra_boundary.missing_api(infra_boundary.load_infra()) == []
