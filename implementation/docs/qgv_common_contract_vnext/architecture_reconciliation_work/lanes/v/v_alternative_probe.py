"""Inactive source-pinned V impact continuation; never writes into the repository.

All numeric transforms/reducers are imported from the pinned legacy snapshot.
Supplied numbers are synthetic inputs, not recommended thresholds or formulas.
Run: PYTHONDONTWRITEBYTECODE=1 python v_alternative_probe.py REPO OUTPUT_DIR
"""
from __future__ import annotations

import copy
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
if OUT == ROOT or ROOT in OUT.parents:
    raise SystemExit("Output must be outside the source snapshot")
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "implementation/src"))
from investment_system.contracts.enums import ProfileKind, QualityState
from investment_system.contracts.models import DataStamp, FactorObservation
from investment_system.contracts.raw import RawFundamentals
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.factors import V_FACTORS, V_INITIAL_PRIOR, V_CANDIDATES
from investment_system.qgv.raw_map import map_raw
from investment_system.qgv.scoring import score_v_prior, score_v_candidates
from investment_system.qgv.leaderboard import LeaderboardEngine
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.validation.historical import run_as_of
from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.records import ScopedTrackStore

ASOF = datetime(2026, 9, 14, tzinfo=timezone.utc)
SOURCE_HEAD = "4fb08a05728d83519b72a2bd995669f0cb06003a"
SOURCE_PATHS = [
    "implementation/src/investment_system/qgv/raw_map.py",
    "implementation/src/investment_system/qgv/factors.py",
    "implementation/src/investment_system/qgv/scoring.py",
    "implementation/src/investment_system/qgv/analysis.py",
    "implementation/src/investment_system/qgv/pipeline.py",
    "implementation/src/investment_system/qgv/leaderboard.py",
    "implementation/src/investment_system/contracts/raw.py",
    "implementation/src/investment_system/contracts/models.py",
    "implementation/src/investment_system/contracts/enums.py",
    "implementation/src/investment_system/validation/historical.py",
    "implementation/src/investment_system/providers/sec_companyfacts.py",
    "implementation/src/investment_system/providers/sec_vintage.py",
    "implementation/src/investment_system/providers/us_sec.py",
    "implementation/src/investment_system/providers/yahoo_chart.py",
    "implementation/docs/qgv_common_contract_vnext/golden_cases.json",
    "implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/V_DESCRIPTOR_MANIFEST.json",
    "implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/v_review.md",
    "implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/v_evidence.json",
]
def sha(data):
    return hashlib.sha256(data).hexdigest()
def pins():
    return {p: sha((ROOT / p).read_bytes()) for p in SOURCE_PATHS}
def protected_digest():
    paths = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"]).decode().split("\0")
    h = hashlib.sha256()
    n = 0
    for p in sorted(x for x in paths if x):
        h.update(p.encode() + b"\0" + sha((ROOT / p).read_bytes()).encode() + b"\n")
        n += 1
    return {"tracked_files": n, "aggregate_sha256": h.hexdigest()}
BEFORE_PINS, BEFORE_PROTECTED = pins(), protected_digest()
stamp = DataStamp("v-alt-synthetic", "SYNTHETIC", "FIXTURE", "INACTIVE-V-IMPACT", ASOF, ASOF, ASOF, synthetic=True)
BASE = RawFundamentals(
    "nvda", stamp, revenue=120, revenue_prev=100, ebit=24, fcf=18,
    net_income=20, invested_capital=100, cash=30, total_debt=10, eps=5, eps_prev=4,
    industry_revenue_growth=.10, market_share=.20, peer_median_market_share=.15,
    wacc=.10, competitive_advantage_rubric=70, management_quality_rubric=70,
    growth_durability_rubric=70, dcf_value=120, price=100, peer_median_multiple=20,
    own_multiple=20, hist_valuation_percentile=70, sector_context_score=60,
    theme_premium_score=40, reverse_dcf_implied_growth=.08,
)
results, checks = {}, []
def check(cid, passed, observed):
    checks.append({"id": cid, "pass": bool(passed), "observed": observed})
    if not passed:
        raise AssertionError(f"{cid}: {observed}")
def summarize(obs, profile=ProfileKind.GENERAL_CORPORATE):
    prior, cov, notes = score_v_prior(obs, profile)
    snap = AnalysisEngine().analyze("nvda", ASOF, obs, profile_kind=profile, synthetic=True)
    numeric = [f for f in V_FACTORS if obs.get(f) is not None and obs[f].score_0_100 is not None]
    excluded = {QualityState.MISSING_DATA, QualityState.BLOCKED_DEPENDENCY, QualityState.PIT_UNAVAILABLE, QualityState.NOT_APPLICABLE}
    admitted = [f for f in numeric if obs[f].quality not in excluded]
    return {
        "factor_scores": {f: None if obs.get(f) is None else obs[f].score_0_100 for f in V_FACTORS},
        "legacy_raw_value": {f: None if obs.get(f) is None else obs[f].raw_value for f in V_FACTORS},
        "quality": {f: None if obs.get(f) is None else obs[f].quality.value for f in V_FACTORS},
        "V_prior": prior, "V_prior_coverage": cov.value, "V_prior_notes": notes,
        "research_candidate_scores": {c.candidate_id: c.v_score for c in score_v_candidates(obs)},
        "numeric_presence_count": len(numeric), "legacy_prior_numeric_admitted_count": len(admitted),
        "legacy_prior_weighted_presence": sum(V_INITIAL_PRIOR[f] for f in admitted),
        "method_validity": None, "semantic_completeness": None, "input_coverage": None,
        "confidence_assessment": None, "ranking_eligibility": None, "publication_eligibility": None,
        "snapshot_default_confidence_literal": snap.confidence,
        "v_table_confidence_literals": {x["factor_id"]: x["confidence"] for x in snap.factor_breakdown["v_factor_table"]},
        "snapshot_coverage_literal": snap.coverage_state.value,
        "Q": snap.Q_score, "G": snap.G_score, "legacy_composite": snap.total_score,
    }
raw_cases = {
    "supplied_dcf_and_implied_growth": BASE,
    "existing_pe_fallback_family": replace(BASE, dcf_value=None, reverse_dcf_implied_growth=None),
    "same_dcf_reverse_pe_proxy": replace(BASE, reverse_dcf_implied_growth=None),
    "same_dcf_supplied_implied_025": replace(BASE, reverse_dcf_implied_growth=.25),
    "no_eps_no_dcf": replace(BASE, dcf_value=None, eps=None, reverse_dcf_implied_growth=None),
    "missing_sector_context": replace(BASE, sector_context_score=None),
    "historical_supplied_20": replace(BASE, hist_valuation_percentile=20),
    "historical_supplied_80": replace(BASE, hist_valuation_percentile=80),
    "financial_same_valuation_inputs": replace(BASE, profile_kind="FINANCIAL"),
}
for name, raw in raw_cases.items():
    profile = ProfileKind.FINANCIAL if raw.profile_kind == "FINANCIAL" else ProfileKind.GENERAL_CORPORATE
    results[name] = {"inputs": {f: getattr(raw, f) for f in ["dcf_value", "price", "eps", "revenue", "revenue_prev", "own_multiple", "peer_median_multiple", "hist_valuation_percentile", "sector_context_score", "theme_premium_score", "reverse_dcf_implied_growth"]}, **summarize(map_raw(raw), profile)}
dcf, pe = results["supplied_dcf_and_implied_growth"], results["existing_pe_fallback_family"]
check("V01_source_branch_impacts", dcf["factor_scores"]["fundamental_value"] > pe["factor_scores"]["fundamental_value"] and dcf["factor_scores"]["margin_of_safety"] > pe["factor_scores"]["margin_of_safety"] and dcf["V_prior"] != pe["V_prior"], {"dcf": dcf["factor_scores"], "pe": pe["factor_scores"]})
check("V02_v_inputs_do_not_change_composite", dcf["legacy_composite"] == pe["legacy_composite"], {"dcf_total": dcf["legacy_composite"], "pe_total": pe["legacy_composite"]})
check("V03_reverse_branch_impact", results["same_dcf_reverse_pe_proxy"]["factor_scores"]["reverse_dcf"] != results["same_dcf_supplied_implied_025"]["factor_scores"]["reverse_dcf"], {k: results[k]["factor_scores"]["reverse_dcf"] for k in ["same_dcf_reverse_pe_proxy", "same_dcf_supplied_implied_025"]})
check("V04_missing_compares_reducers", results["missing_sector_context"]["numeric_presence_count"] == 6 and all(v is None for v in results["missing_sector_context"]["research_candidate_scores"].values()), results["missing_sector_context"])
check("V05_same_numbers_financial_profile", results["financial_same_valuation_inputs"]["factor_scores"] == dcf["factor_scores"], "Financial context currently does not change V methods/applicability")
check("V06_history_direction_unresolved", results["historical_supplied_20"]["factor_scores"]["historical_valuation"] == 20 and results["historical_supplied_80"]["factor_scores"]["historical_valuation"] == 80, "Supplied historical field is direct monotonic score input; no percentile polarity inferred")

# These outputs copy existing golden topology, without rewriting the golden or
# introducing a new valuation function. Nonuniform values are synthetic stimuli.
golden = json.loads((ROOT / SOURCE_PATHS[14]).read_text())
gcase = next(c for c in golden["cases"] if c["case_id"] == "all_70")
gobs = {r["factor_id"]: FactorObservation(r["factor_id"], r["raw_value"], r["score_0_100"], QualityState(r["quality"]), r["stamp_id"], r["notes"]) for r in gcase["observations"]}
vectors = {
    "company_A_valuation_growth_strength": {"fundamental_value": 100, "peer_relative_value": 70, "historical_valuation": 70, "sector_context": 50, "theme_premium_discount": 50, "reverse_dcf": 100, "margin_of_safety": 0},
    "company_B_safety_strength": {"fundamental_value": 50, "peer_relative_value": 70, "historical_valuation": 70, "sector_context": 50, "theme_premium_discount": 50, "reverse_dcf": 50, "margin_of_safety": 100},
}
for name, values in vectors.items():
    obs = dict(gobs)
    obs.update({f: replace(gobs[f], raw_value=v, score_0_100=v) for f, v in values.items()})
    results[name] = summarize(obs)
results["candidate_orderings"] = {cid: sorted(vectors, key=lambda n: results[n]["research_candidate_scores"][cid], reverse=True) for cid in V_CANDIDATES}
results["candidate_score_groups"] = {cid: [{"score": score, "companies_tied_at_exact_score": [n for n in vectors if results[n]["research_candidate_scores"][cid] == score]} for score in sorted({results[n]["research_candidate_scores"][cid] for n in vectors}, reverse=True)] for cid in V_CANDIDATES}
results["candidate_ordering_scope"] = "Hypothetical V-only diagnostic comparison; not current Leaderboard ranking (which sorts unchanged Q/G composite). Exact-score tie groups preserved; no new tolerance or tie-break policy."
check("V07_existing_weights_reorder_companies", results["candidate_orderings"]["initial_prior"] != results["candidate_orderings"]["mos_tilt_research"], results["candidate_orderings"])
for quality in [QualityState.NOT_APPLICABLE, QualityState.VERSION_MISMATCH, QualityState.CALCULATION_ERROR]:
    obs = dict(gobs)
    obs["fundamental_value"] = replace(gobs["fundamental_value"], quality=quality)
    results[f"numeric_{quality.value}"] = summarize(obs)
check("V08_na_admission_asymmetry_in_impact", results["numeric_NOT_APPLICABLE"]["legacy_prior_numeric_admitted_count"] == 6 and results["numeric_NOT_APPLICABLE"]["research_candidate_scores"]["initial_prior"] == 70, results["numeric_NOT_APPLICABLE"])
check("V09_version_mismatch_still_numeric", results["numeric_VERSION_MISMATCH"]["V_prior"] == 70 and results["numeric_VERSION_MISMATCH"]["research_candidate_scores"]["initial_prior"] == 70, results["numeric_VERSION_MISMATCH"])
check("V10_calculation_error_still_numeric", results["numeric_CALCULATION_ERROR"]["V_prior"] == 70 and results["numeric_CALCULATION_ERROR"]["research_candidate_scores"]["initial_prior"] == 70, results["numeric_CALCULATION_ERROR"])

# Real legacy historical provider path on synthetic filings and prices only.
def payload():
    rows = lambda vals, unit: {"units": {unit: [{"start": f"{yr}-01-01", "end": f"{yr}-12-31", "val": val, "filed": f"{yr+1}-02-01", "form": "10-K", "fy": yr, "fp": "FY", "accn": f"synthetic-{yr}"} for yr, val in vals]}}
    return {"facts": {"us-gaap": {"RevenueFromContractWithCustomerExcludingAssessedTax": rows([(2023, 80), (2024, 100), (2025, 120)], "USD"), "EarningsPerShareDiluted": rows([(2024, 1), (2025, 2)], "USD/shares")}}}
def historical_case(cid, prices, old_price=True, future_inputs=False, sector_labels=None):
    ids = tuple(prices)
    data = {c: payload() for c in ids}
    bars = {c: ([{"price": p, "observed_at": ASOF - timedelta(days=500), "adjusted": True}] if old_price else []) + [{"price": p, "observed_at": ASOF - timedelta(days=1), "adjusted": True}] for c, p in prices.items()}
    if future_inputs:
        for c in ids:
            bars[c].append({"price": 10000, "observed_at": ASOF + timedelta(days=1), "adjusted": True})
            data[c]["facts"]["us-gaap"]["EarningsPerShareDiluted"]["units"]["USD/shares"].append({"start": "2026-01-01", "end": "2026-12-31", "val": 1000, "filed": "2027-02-01", "form": "10-K", "fy": 2026, "fp": "FY", "accn": "future-synthetic"})
    listings = {c: {"cik": "0000000001", "ticker": c.upper(), "yahoo": c.upper(), "sector": (sector_labels or {}).get(c, "UNASSESSED")} for c in ids}
    store = ScopedTrackStore(FileTrackRecordStore(OUT / f"{cid}_synthetic_store.json"))
    row = run_as_of(ASOF, data, bars, store, ids, listings=listings)
    return {"fixture_sector_labels": {c: listings[c]["sector"] for c in ids}, "official_pass": row["official_pass"], "full_pit_pass": row["full_pit_pass"], "names": row["names"], "rows": {c: {k: q.get(k) for k in ["V", "coverage", "V_policy", "pit_price", "eps", "peer_universe", "peer_n", "peer_median", "peer_confidence", "hist_valuation"]} | {"factor_scores": {i["factor_id"]: i["score"] for i in q.get("v_table") or []}} for c, q in row["quality"].items()}}
results["book_two_peers"] = historical_case("book_two", {"nvda": 20, "msft": 60}, sector_labels={"nvda": "SEMICONDUCTORS", "msft": "SOFTWARE"})
results["book_three_peers"] = historical_case("book_three", {"nvda": 20, "msft": 60, "asml": 20}, sector_labels={"nvda": "SEMICONDUCTORS", "msft": "SOFTWARE", "asml": "SEMICONDUCTORS"})
results["book_sector_labels_swapped"] = historical_case("book_labels", {"nvda": 20, "msft": 60}, sector_labels={"nvda": "SOFTWARE", "msft": "SEMICONDUCTORS"})
results["book_future_inputs"] = historical_case("book_future", {"nvda": 20, "msft": 60}, future_inputs=True)
results["book_sparse_history"] = historical_case("book_sparse", {"nvda": 20, "msft": 60}, old_price=False)
a, b = results["book_two_peers"]["rows"], results["book_three_peers"]["rows"]
check("V11_actual_book_membership_impact", a["nvda"]["peer_median"] == 30 and b["nvda"]["peer_median"] == 10 and a["nvda"]["factor_scores"]["peer_relative_value"] != b["nvda"]["factor_scores"]["peer_relative_value"], {"two": a, "three": b})
check("V12_sector_labels_not_semantic_peers", all(a[c]["factor_scores"] == results["book_sector_labels_swapped"]["rows"][c]["factor_scores"] for c in a), "Legacy comparator is book membership, not sector-peer construction; bias direction unquantified")
check("V13_future_prices_and_filings_excluded", all(a[c]["factor_scores"] == results["book_future_inputs"]["rows"][c]["factor_scores"] for c in a), {"present": a, "future_input": results["book_future_inputs"]["rows"]})
check("V14_sparse_history_admits_partial", all(results["book_sparse_history"]["rows"][c]["hist_valuation"] is None and results["book_sparse_history"]["rows"][c]["V"] is not None and results["book_sparse_history"]["rows"][c]["V"] != a[c]["V"] for c in a), {"full": a, "sparse": results["book_sparse_history"]["rows"]})
check("V15_historical_method_label_gap", all(a[c]["hist_valuation"] == 75 for c in a), "Actual 1-prior-price/1-prior-EPS two-point method returns 75; not a historical percentile distribution")

# A method-invalid G/V producer can reach consumer ranking because only numeric
# snapshot total is sorted. This is an observed gap, never authorized admission.
invalid_obs = dict(gobs)
invalid_obs["revenue_growth"] = replace(gobs["revenue_growth"], quality=QualityState.VERSION_MISMATCH)
invalid_obs["fundamental_value"] = replace(gobs["fundamental_value"], quality=QualityState.VERSION_MISMATCH)
invalid_snap = AnalysisEngine().analyze("nvda", ASOF, invalid_obs, synthetic=True)
board = LeaderboardEngine().build("inactive-v-admission-probe", ASOF, [invalid_snap])
results["consumer_invalid_method_numeric"] = {"G_quality": "VERSION_MISMATCH", "V_quality": "VERSION_MISMATCH", "snapshot_total": invalid_snap.total_score, "snapshot_method_binding": None, "board_rank": board.rows[0].rank, "board_total": board.rows[0].total_score, "recomputed": board.recomputed_qgv}
check("V16_incomplete_method_validity_reaches_rank", board.rows[0].rank == 1 and board.rows[0].total_score == 70 and not board.recomputed_qgv, results["consumer_invalid_method_numeric"])
future = replace(BASE, stamp=replace(stamp, published_at=ASOF + timedelta(days=1), available_at=ASOF + timedelta(days=1)))
future_snap = AnalysisPipeline().analyze_raw(future, as_of=ASOF)
results["direct_raw_future_stamp_boundary"] = {"as_of": ASOF.isoformat(), "available_at": future.stamp.available_at.isoformat(), "V": future_snap.V_score, "total": future_snap.total_score, "coverage_literal": future_snap.coverage_state.value, "interpretation": "Direct analyze_raw does not independently enforce future availability; historical resolver/provider filtering does not protect every entry point."}
check("V17_direct_future_raw_still_numeric", future_snap.V_score is not None, results["direct_raw_future_stamp_boundary"])
descriptor = json.loads((ROOT / SOURCE_PATHS[15]).read_text())
check("V18_existing_descriptors_not_runtime_bindings", len(descriptor["records"]) == 7 and all(r["method_ref"] is None and r["method_version_ref"] is None for r in descriptor["records"]), "Seven characterized method source anchors are not registered production identities/versions")
check("V19_metadata_unassessed_preserved", all(results[n]["confidence_assessment"] is None and results[n]["method_validity"] is None for n in raw_cases), "Unknowns preserved; MEDIUM/SYNTHETIC literals do not become method confidence/validity evidence")
check("V20_factor_identity_prior_preserved", set(V_FACTORS) == set(V_INITIAL_PRIOR) and set(V_CANDIDATES) == {"initial_prior", "equal_research", "mos_tilt_research"}, {"factors": V_FACTORS, "candidate_ids": list(V_CANDIDATES), "PeerDerivedV_weights": "NOT_FOUND_IN_PINNED_CODE; test name refers to book comparator"})
AFTER_PINS, AFTER_PROTECTED = pins(), protected_digest()
check("V21_source_bytes_unchanged", BEFORE_PINS == AFTER_PINS and BEFORE_PROTECTED == AFTER_PROTECTED, AFTER_PROTECTED)
bundle = {"status": "D1_D2_INACTIVE_ALTERNATIVE_IMPACT_COMPLETE", "source_head": SOURCE_HEAD, "prior_reconciliation_artifacts": "remote df5c70447dfa83805395b7cbbcacbc2024e77f3d; same local bytes as source pins", "scope": "NEW SYNTHETIC V ALTERNATIVE COMPARISONS; not rerun of prior22 characterization or13 regressions", "scheduler_hops_counted": 0, "production_semantics_changed": False, "new_numeric_formula_or_default": None, "new_requiredness_roles": 0, "golden_changed": False, "original_sources_changed": False, "source_pins_sha256": BEFORE_PINS, "existing_candidate_weights": {cid: {"weights": spec["weights"], "lifecycle": spec["lifecycle"].value} for cid, spec in V_CANDIDATES.items()}, "results": results, "checks": checks, "checks_pass": sum(c["pass"] for c in checks), "checks_total": len(checks), "protected_files_before": BEFORE_PROTECTED, "protected_files_after": AFTER_PROTECTED}
(OUT / "V_ALTERNATIVE_RESULTS.json").write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
print(json.dumps({"checks_pass": bundle["checks_pass"], "checks_total": bundle["checks_total"], "results_file": str(OUT / "V_ALTERNATIVE_RESULTS.json"), "sha256": sha((OUT / "V_ALTERNATIVE_RESULTS.json").read_bytes()), "source_preserved": BEFORE_PINS == AFTER_PINS}, indent=2))
