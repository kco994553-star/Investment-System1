"""Source-pinned, inactive G replay evidence. No production or history writes.

Run with PYTHONDONTWRITEBYTECODE=1 and --owner-root pointing at the audit pin.
All numeric transformations below are current-source characterization only.
No method registry, requiredness, PIT policy or production alternative is created.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, fields, replace
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PIN = "4fb08a05728d83519b72a2bd995669f0cb06003a"
PREFIX = "implementation/src/investment_system/"
SOURCE_PATHS = [PREFIX + p for p in (
    "qgv/raw_map.py", "qgv/factors.py", "qgv/scoring.py", "qgv/pipeline.py",
    "qgv/analysis.py", "qgv/g_horizon.py", "qgv/quarterly_series.py",
    "qgv/book.py", "qgv/track_record.py", "contracts/raw.py", "contracts/models.py",
    "providers/sec_companyfacts.py", "providers/sec_vintage.py",
    "universe/events.py", "validation/records.py", "validation/file_store.py", "ingestion/raw_store.py", "ingestion/replay.py",
)]


def normalize(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [normalize(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    root, out = args.owner_root.resolve(), args.out_dir.resolve()
    if root == out or root in out.parents:
        raise SystemExit("Output must be outside the read-only owner tree")
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN:
        raise SystemExit("Owner HEAD differs from pin; no silent source rebase")
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(root / "implementation/src"))
    from investment_system.contracts.models import DataStamp, FactorObservation, QGVSnapshot
    from investment_system.contracts.raw import RawFundamentals
    from investment_system.qgv.raw_map import map_raw, _yoy, _growth_to_score, _clip_score
    from investment_system.qgv.factors import G_WEIGHTS
    from investment_system.qgv.scoring import score_g
    from investment_system.qgv.pipeline import AnalysisPipeline
    from investment_system.qgv.g_horizon import GHorizonConfig
    from investment_system.providers.sec_companyfacts import facts_to_raw, REVENUE_CONCEPTS
    from investment_system.providers.sec_vintage import resolve_vintages, select_across_concepts, select_previous
    from investment_system.contracts.enums import ProfileKind

    source_hashes = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in SOURCE_PATHS}
    prior_path = root / "implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/g_profile_checks.json"
    prior = json.loads(prior_path.read_text())
    for p, sha in prior["pinned_source_sha256"].items():
        assert hashlib.sha256((root / p).read_bytes()).hexdigest() == sha, (p, "changed since prior characterization")

    now = datetime(2026, 10, 5, 4, 0, tzinfo=timezone.utc)
    stamp = DataStamp("synthetic-g-lineage-v1", "synthetic", "fixture", "complete_raw_fixture", now, now, now,
                      period_start=date(2025, 1, 1), period_end=date(2025, 12, 31), synthetic=True)
    complete = RawFundamentals("SYNTHETIC-G-LINEAGE", stamp, revenue=120.0, revenue_prev=100.0,
                              eps=2.2, eps_prev=2.0, fcf=20.0, shares=10.0,
                              invested_capital=100.0, growth_durability_rubric=70.0,
                              industry_revenue_growth=0.10, source_kind="SYNTHETIC")
    fixture_defs = {
        "complete_eps_branch": complete,
        "missing_eps_fcf_fallback": replace(complete, eps=None, eps_prev=None),
        "zero_prior_eps_fcf_fallback": replace(complete, eps=2.2, eps_prev=0.0),
        "missing_eps_and_fcf": replace(complete, eps=None, eps_prev=None, fcf=None),
        "missing_industry_and_rubric": replace(complete, industry_revenue_growth=None, growth_durability_rubric=None),
        "missing_revenue_base": replace(complete, revenue_prev=None),
    }
    write(out / "G_SYNTHETIC_RAW_FIXTURES.json", {"synthetic": True, "source_head": head,
           "numeric_values_are_fixture_inputs_not_policy": True,
           "cases": {k: asdict(v) for k, v in fixture_defs.items()}})

    specs = {
        "next_3_5y_growth": ("observed:revenue-yoy-linearclip", ["revenue", "revenue_prev"],
            "_growth_to_score(_yoy(revenue, revenue_prev))", "latest/prior selected annual period; no forward or 3–5Y series input", None,
            "INTERIM_PROXY", "G 3–5Y conceptual/label intent unresolved against executed last-YoY; code explicitly calls it proxy"),
        "growth_efficiency": ("observed:revenue-yoy-capital-intensity-clip", ["revenue", "revenue_prev", "invested_capital"],
            "clip(50 + revenue_yoy / max(invested_capital / revenue, 0.05) * 20)", "revenue current/prior plus current invested capital; selected field periods not enforced", None,
            "MORE_EVIDENCE_REQUIRED", "capital intensity denominator uses balance/flow values; accounting basis and period pairing unresolved"),
        "revenue_growth": ("observed:revenue-yoy-linearclip", ["revenue", "revenue_prev"],
            "_growth_to_score(_yoy(revenue, revenue_prev))", "latest/prior selected annual periods, not necessarily adjacent annual periods", None,
            "MORE_EVIDENCE_REQUIRED", "execution is reproducible; YoY claim needs adjacent, matched period/unit evidence"),
        "eps_fcf_per_share_growth": ("observed:eps-yoy-or-cross-measure-fcf-prior-revenue-linearclip", ["eps", "eps_prev", "fcf", "revenue_prev"],
            "_growth_to_score(eps_yoy if eps_yoy is not None else _yoy(fcf, revenue_prev))", "EPS latest/prior; fallback current FCF divided by prior revenue; no prior FCF/shares", "observed:current-fcf-prior-revenue-minus-one-linearclip",
            "METHOD_MISMATCH", "EPS branch is EPS ratio-minus-one; fallback compares distinct measures and cannot establish FCF/per-share growth"),
        "growth_durability": ("observed:precomputed-growth-durability-rubric-passthrough", ["growth_durability_rubric"],
            "growth_durability_rubric directly assigned", "no method-specific period/horizon in raw container", None,
            "MORE_EVIDENCE_REQUIRED", "direct supplied rubric score; no rubric/input/time authority in this mapper"),
        "excess_growth_vs_industry": ("observed:revenue-yoy-industry-spread-linearclip", ["revenue", "revenue_prev", "industry_revenue_growth"],
            "clip(50 + (revenue_yoy - industry_revenue_growth) / 0.15 * 50)", "company current/prior; industry period/universe/unit unspecified", None,
            "MORE_EVIDENCE_REQUIRED", "company/industry comparable period and universe lineage not serialized"),
    }
    input_sources = {
        "revenue": {"producer": "sec_companyfacts.facts_to_raw select_across_concepts(REVENUE_CONCEPTS)",
            "concepts": list(REVENUE_CONCEPTS), "basis": "latest accepted annual-duration vintage; flow"},
        "revenue_prev": {"producer": "sec_companyfacts.facts_to_raw select_previous for selected revenue concept/unit",
            "concepts": "same concept/unit selected for revenue", "basis": "other fy/fp/end group; one-year adjacency not guaranteed"},
        "eps": {"producer": "sec_companyfacts.facts_to_raw pick_series",
            "concepts": [["us-gaap", "EarningsPerShareDiluted", "USD/shares"], ["us-gaap", "EarningsPerShareDiluted", "EUR/shares"],
                ["us-gaap", "EarningsPerShareDiluted", "USD-per-shares"], ["us-gaap", "EarningsPerShareBasic", "USD/shares"],
                ["us-gaap", "EarningsPerShareBasic", "EUR/shares"], ["us-gaap", "EarningsPerShareDiluted", "pure"]],
            "basis": "latest EPS series; diluted/basic and share basis may differ by selected concept"},
        "eps_prev": {"producer": "sec_companyfacts.facts_to_raw pick_series select_previous",
            "concepts": "selected EPS concept/unit", "basis": "previous distinct vintage group; corporate-action/adjacency not guaranteed"},
        "fcf": {"producer": "sec_companyfacts.facts_to_raw pick_series(FreeCashFlow), otherwise current CFO-abs(capex)",
            "concepts": [["us-gaap", "FreeCashFlow", "USD/EUR"], ["us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD/EUR"],
                ["us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment", "USD/EUR"]],
            "basis": "flow; selected fcf_prev is discarded; current raw shares not used in G fallback"},
        "invested_capital": {"producer": "sec_companyfacts.facts_to_raw equity+debt if both else equity",
            "concepts": "StockholdersEquity or StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest, LongTermDebt or LongTermDebtNoncurrent (USD/EUR)",
            "basis": "selected latest balance; equity-only branch possible; no matched fiscal date enforced"},
        "growth_durability_rubric": {"producer": "direct RawFundamentals supplied value; SEC adapter does not fill",
            "concepts": None, "basis": "rubric method/version, scorer and target period not represented"},
        "industry_revenue_growth": {"producer": "direct RawFundamentals supplied value; SEC adapter does not fill",
            "concepts": None, "basis": "industry universe, weighted measure, period, revisions and availability not represented"},
    }
    assert tuple(specs) == tuple(G_WEIGHTS)
    checks = []
    def check(name, actual, expected):
        ok = actual == expected
        checks.append({"case": name, "actual": normalize(actual), "expected": normalize(expected), "pass": ok})
        if not ok:
            raise AssertionError((name, actual, expected))

    def method_branch(fid, raw):
        if fid != "eps_fcf_per_share_growth":
            return specs[fid][0]
        return "observed:eps-yoy-linearclip" if _yoy(raw.eps, raw.eps_prev) is not None else specs[fid][4]

    def intermediate(fid, raw):
        yoy = _yoy(raw.revenue, raw.revenue_prev)
        if fid in {"next_3_5y_growth", "revenue_growth"}:
            return yoy
        if fid == "eps_fcf_per_share_growth":
            primary = _yoy(raw.eps, raw.eps_prev)
            return primary if primary is not None else _yoy(raw.fcf, raw.revenue_prev)
        if fid == "growth_efficiency":
            return None if yoy is None or not raw.invested_capital or not raw.revenue else yoy / max(raw.invested_capital / raw.revenue, 0.05)
        if fid == "excess_growth_vs_industry":
            return None if yoy is None or raw.industry_revenue_growth is None else yoy - raw.industry_revenue_growth
        return raw.growth_durability_rubric

    records = []
    for fid, (anchor, inputs, expression, period, fallback, verdict, unresolved) in specs.items():
        records.append({
            "factor_id": fid, "factor_ref": {"id": "G:" + fid, "source_version": head,
                "locator": PREFIX + "qgv/factors.py", "sha256": source_hashes[PREFIX + "qgv/factors.py"]},
            "method_id": None, "method_version": None,
            "observed_method_id": anchor,
            "observed_method_version": "audit-source-sha256:" + source_hashes[PREFIX + "qgv/raw_map.py"],
            "identity_authority": "AUDIT_ONLY_SOURCE_ANCHOR_NOT_AN_APPROVED_RUNTIME_METHOD_REGISTRY",
            "source_code_ref": {"head": head, "path": PREFIX + "qgv/raw_map.py", "sha256": source_hashes[PREFIX + "qgv/raw_map.py"]},
            "input_fields": inputs, "input_period": period,
            "input_source_map": {k: input_sources[k] for k in inputs},
            "input_contract_ref": {"path": PREFIX + "contracts/raw.py", "sha256": source_hashes[PREFIX + "contracts/raw.py"]},
            "fallback_method": fallback,
            "normalization": {"expression": expression, "authority": "EXISTING_PROVISIONAL_CURRENT_SOURCE_ONLY",
                "new_numeric_policy": None},
            "source_lineage": {"raw_container": "one shared DataStamp; raw selected per-field FactVintage rows not serialized",
                "replay_cases_ref": "G_LINEAGE_REPLAY.json", "raw_fixture_ref": "G_SYNTHETIC_RAW_FIXTURES.json"},
            "pit_fields": {"as_of": "QGVSnapshot.as_of", "available_at": "raw.stamp.available_at",
                "published_at": "raw.stamp.published_at", "period_start": "raw.stamp.period_start optional",
                "period_end": "raw.stamp.period_end optional", "per_input_vintage": "not in RawFundamentals; audit-only SEC row sidecars below",
                "direct_analyze_raw_admission": "no require_available call; stamps/finite values alone do not authenticate PIT"},
            "result_lineage": {"legacy_observation": "factor_id,raw_value,score_0_100,quality,stamp_id,notes; raw_value already normalized",
                "method_ref_in_legacy_observation": False, "factor_observations_in_snapshot": False,
                "sidecar_bind": "immutable payload hash + snapshot/result ref + method source anchor + input/source hashes",
                "historical_method_attribution": "UNRESOLVED unless exact archived source/input proof exists"},
            "verdict": verdict, "unresolved_semantics": unresolved,
            "requiredness": None, "applicability_truth": None,
            "current_runtime_applicability": "factor_applicable returns true for all G in GENERAL_CORPORATE/FINANCIAL; observed bool is not authority",
            "runtime_enabled": False,
        })

    replays = []
    for name, raw in fixture_defs.items():
        mapped = map_raw(raw)
        factor_rows = []
        for fid, spec in specs.items():
            obs = mapped[fid]
            value = intermediate(fid, raw)
            if fid in {"next_3_5y_growth", "revenue_growth", "eps_fcf_per_share_growth"}:
                expected = _growth_to_score(value)
            elif fid == "growth_efficiency":
                expected = None if value is None else _clip_score(50.0 + value * 20.0)
            elif fid == "excess_growth_vs_industry":
                expected = None if value is None else _clip_score(50.0 + value / 0.15 * 50.0)
            else:
                expected = value
            check(name + ":" + fid + ":source_replay", obs.score_0_100, expected)
            row = {"factor_id": fid, "observed_method_id": method_branch(fid, raw),
                "observed_method_version": records[list(specs).index(fid)]["observed_method_version"],
                "input_values": {k: getattr(raw, k) for k in spec[1]},
                "synthetic_input_period_basis": {k: {"source": "G_SYNTHETIC_RAW_FIXTURES.json:" + name,
                    "period_start": "2024-01-01" if k in {"revenue_prev", "eps_prev"} else (None if k in {"growth_durability_rubric", "invested_capital"} else "2025-01-01"),
                    "period_end": "2024-12-31" if k in {"revenue_prev", "eps_prev"} else "2025-12-31",
                    "unit": "USD/shares" if k in {"eps", "eps_prev"} else ("score_0_100" if k == "growth_durability_rubric" else ("ratio" if k == "industry_revenue_growth" else "USD")),
                    "authority": "synthetic declared fixture basis only; does not fill production per-field lineage"} for k in spec[1]},
                "economic_input_intermediate": value,
                "raw_value_in_legacy_observation": obs.raw_value,
                "score": obs.score_0_100, "quality": obs.quality.value, "notes": obs.notes,
                "stamp": raw.stamp.to_dict(), "as_of": now.isoformat(),
                "input_hash": digest({k: getattr(raw, k) for k in spec[1]})}
            row["audit_result_lineage_hash"] = digest(row)
            factor_rows.append(row)
        g, cov, notes = score_g(mapped, ProfileKind.GENERAL_CORPORATE)
        replays.append({"case": name, "synthetic": True, "raw_hash": digest(asdict(raw)),
                       "G_score": g, "G_coverage": cov.value, "G_notes": notes,
                       "factor_results": factor_rows})
    check("complete_six_G_fields", replays[0]["G_coverage"], "READY")
    check("missing_EPS_uses_distinct_fallback_anchor", replays[1]["factor_results"][3]["observed_method_id"], specs["eps_fcf_per_share_growth"][4])
    check("same_factor_distinct_existing_branch_lineage", replays[0]["factor_results"][3]["audit_result_lineage_hash"] != replays[1]["factor_results"][3]["audit_result_lineage_hash"], True)
    check("absent_EPS_and_FCF_is_missing", replays[3]["factor_results"][3]["quality"], "MISSING_DATA")
    check("legacy_observation_no_first_class_method_id", "method_id" in {f.name for f in fields(FactorObservation)}, False)
    check("legacy_snapshot_no_first_class_method_id", "method_id" in {f.name for f in fields(QGVSnapshot)}, False)

    # Read the existing committed synthetic SEC fixture only: no live or cached REAL-DATA claim.
    sec_path = root / "implementation/fixtures/sec_companyfacts_mini.json"
    sec_payload = json.loads(sec_path.read_text())
    sec_as_of = datetime(2025, 3, 1, tzinfo=timezone.utc)
    sec_raw = facts_to_raw("SYNTHETIC-NVDA-FIXTURE", "0001045810", sec_payload, sec_as_of, synthetic=True)
    rev = select_across_concepts(sec_payload, REVENUE_CONCEPTS, sec_as_of, "10-K")
    prev = select_previous(resolve_vintages(sec_payload, rev.taxonomy, rev.concept, rev.unit, sec_as_of, "10-K"), rev) if rev else None
    check("committed_SEC_fixture_current_revenue_binding", sec_raw.revenue, None if rev is None else rev.value)
    check("committed_SEC_fixture_prior_revenue_binding", sec_raw.revenue_prev, None if prev is None else prev.value)
    check("SEC_date_only_stamp_period_not_serialized", (sec_raw.stamp.period_start, sec_raw.stamp.period_end), (None, None))
    sec_replay = {"evidence_kind": "COMMITTED_SYNTHETIC_SEC_FIXTURE_REPLAY", "fixture_path": str(sec_path.relative_to(root)),
        "fixture_sha256": hashlib.sha256(sec_path.read_bytes()).hexdigest(), "as_of": sec_as_of,
        "raw": asdict(sec_raw), "selected_revenue_rows": {"current": asdict(rev) if rev else None, "previous": asdict(prev) if prev else None},
        "G_scores": {fid: normalize(asdict(map_raw(sec_raw)[fid])) for fid in specs},
        "precision_caveats": ["filed has date precision and is coerced to midnight UTC by legacy resolver",
            "fixture lacks form/start/fy/fp/accession; annual/adjacency/authoritative filing lineage NOT_VERIFIED",
            "shared DataStamp period start/end absent; SEC selected row precision not upgraded",
            "synthetic fixture; no real PIT/OOS eligibility established"]}

    historical_path = root / "implementation/reports/official_v11_book_snapshots.json"
    historical_bytes = historical_path.read_bytes()
    historical = json.loads(historical_bytes)
    old_snapshot = historical["snapshots"][0]
    check("persisted_sample_is_explicitly_synthetic", (historical["kind"], historical["synthetic_all"]), ("SYNTHETIC", True))
    h_sidecar = {"kind": "INACTIVE_HISTORICAL_IDENTITY_ATTACHMENT_EXAMPLE", "legacy_report_path": str(historical_path.relative_to(root)),
        "legacy_report_sha256": hashlib.sha256(historical_bytes).hexdigest(), "legacy_snapshot_id": old_snapshot["qgv_snapshot_id"],
        "legacy_snapshot_payload_hash": digest(old_snapshot), "legacy_as_of": old_snapshot["as_of"],
        "legacy_calculation_version_fields": {k: old_snapshot[k] for k in ("qgv_system_version", "qgv_standard_version", "qgv_analysis_contract", "implementation_line")},
        "historical_method_id": None, "historical_method_version": None,
        "historical_method_evidence": "NOT_AVAILABLE_IN_PAYLOAD; current source is not retroactively assigned to old result",
        "parallel_lineage_design": {"legacy_ref": old_snapshot["qgv_snapshot_id"], "factor_id": "eps_fcf_per_share_growth",
            "new_method_ref": "separate future approved reference; unresolved and not executed",
            "new_result_ref": "separate result id/hash; never update archived legacy snapshot payload",
            "revision_parent_ref": "existing optional revision_parent_id can link snapshot revisions but does not bind factor method identity"},
        "recalculation_performed": False, "archived_payload_mutated": False}
    check("historical_payload_bytes_unchanged", historical_path.read_bytes(), historical_bytes)
    # Avoid storing the bytes themselves as test output.
    checks[-1]["actual"] = checks[-1]["expected"] = hashlib.sha256(historical_bytes).hexdigest()

    manifest_path = root / "implementation/data/raw/manifests/companyfacts__0001045810.json"
    raw_manifest = json.loads(manifest_path.read_text())
    blob = root / "implementation/data/raw/blobs/companyfacts__0001045810"
    real_status = {"status": "NOT_RUN_SOURCE_BLOB_ABSENT" if not blob.exists() else "NOT_RUN_NOT_SELECTED",
        "manifest_path": str(manifest_path.relative_to(root)), "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "recorded_blob_sha256": raw_manifest["sha256"], "recorded_fetch_time": raw_manifest["fetched_at"],
        "expected_blob_path": str(blob.relative_to(root)), "blob_exists": blob.exists(),
        "constraint": "Manifest/STORE_INDEX historical disk-count claim is not proof that this checkout has bytes; no re-fetch attempted"}

    manifest = {"artifact_kind": "INACTIVE_G_SOURCE_PINNED_METHOD_REPLAY_MANIFEST", "source_owner_head": head,
        "runtime_enabled": False, "new_method_registry": False, "new_requiredness_roles": 0,
        "source_sha256": source_hashes, "reused_prior_probe": {"path": str(prior_path.relative_to(root)),
            "sha256": hashlib.sha256(prior_path.read_bytes()).hexdigest(), "rerun_prior_counterexamples": False}, "records": records}
    replay_result = {"status": "CURRENT_SOURCE_LINEAGE_REPLAY_PASS", "source_owner_head": head,
        "synthetic_cases": replays, "committed_SEC_fixture": sec_replay,
        "persisted_historical_sample": h_sidecar, "real_cached_raw_replay": real_status,
        "B1_evidence_update": {"prior_semantic_classification_preserved": True,
            "promoted_to_supported": [], "production_requiredness_assigned": 0,
            "finding": "all six observed method inputs pinned; G1/G4 mismatch, G2/G3/G5/G6 authority/period/rubric unresolved; behavior proof is not requiredness authority"},
        "production_method_migration": "NOT_STARTED", "scheduler_hops_added": 0,
        "not_run": ["real raw replay", "real PIT/OOS", "forecast comparison", "production replacement", "full regression", "Actions", "Holdout", "scheduler hops"]}
    write(out / "G_METHOD_REPLAY_MANIFEST.json", manifest)
    write(out / "G_LINEAGE_REPLAY.json", replay_result)
    verification = {"status": "SOURCE_PINNED_CURRENT_LINEAGE_VERIFIED_LOCALLY", "checks": checks,
        "count": len(checks), "passed": sum(c["pass"] for c in checks),
        "source_bytes_unchanged": all(hashlib.sha256((root / p).read_bytes()).hexdigest() == sha for p, sha in source_hashes.items()),
        "source_head": head, "production_semantics_changed": False, "scheduler_hops_added": 0,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "artifacts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.json")) if p.name != "G_LINEAGE_VERIFICATION.json"}}
    write(out / "G_LINEAGE_VERIFICATION.json", verification)
    print(json.dumps({"status": verification["status"], "checks": len(checks), "passed": verification["passed"],
        "manifest_sha256": hashlib.sha256((out / "G_METHOD_REPLAY_MANIFEST.json").read_bytes()).hexdigest(),
        "replay_sha256": hashlib.sha256((out / "G_LINEAGE_REPLAY.json").read_bytes()).hexdigest(),
        "real_raw_replay": real_status["status"], "scheduler_hops_added": 0}))


if __name__ == "__main__":
    main()
