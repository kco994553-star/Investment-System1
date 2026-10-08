"""INACTIVE research comparison; never imported by the production evaluator.

Read existing weights and golden observations without changing them. REQUIRED /
OPTIONAL assignments below are toy fixtures, not a proposed factor registry.
No calibrated defaults, coverage cutoffs, confidence formulas or production
admission rules are introduced. The output is a policy decision illustration.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
REPO = HERE.parents[3]
POLICIES = ("A_STRICT_COMPLETE", "B_AVAILABLE_ESTIMATE", "C_FIXED_PARTIAL", "D_REQUIREDNESS_HYBRID")
ORDINARY_MISSING = {"ABSENT", "SCORE_NONE", "MISSING_DATA", "INSUFFICIENT_HISTORY", "SOURCE_UNAVAILABLE"}
CONSUMED_FAILURES = {"PIT_UNAVAILABLE", "INVALID", "VERSION_MISMATCH", "IDENTIFIER_AMBIGUOUS", "CALCULATION_ERROR", "BLOCKED_DEPENDENCY"}


def fraction(value):
    return Fraction(str(value))


def number(value):
    return None if value is None else float(value)


def hashes(paths):
    return {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def load_inputs():
    factor_map = json.loads((DOCS / "current_factor_map.json").read_text())
    golden = json.loads((DOCS / "golden_cases.json").read_text())
    baseline = json.loads((DOCS / "evidence/baseline.json").read_text())
    paths = [DOCS / "golden_cases.json", DOCS / "current_factor_map.json"]
    paths.extend(REPO / name for name in baseline["source_sha256"])
    return factor_map, golden, baseline, paths


def make_case(axis, name, factor_map, golden_case):
    observations = {row["factor_id"]: row for row in golden_case["observations"]}
    nodes = [row for row in factor_map["nodes"] if row["axis"] == axis]
    rows = []
    for index, node in enumerate(nodes):
        fid = node["factor_id"]
        observation = observations.get(fid)
        score = observation["score_0_100"] if observation else None
        quality = observation["quality"] if observation else "ABSENT"
        state = "PRESENT" if quality == "OK" and score is not None else quality
        if state == "OK":
            state = "SCORE_NONE"
        na = golden_case["profile_kind"] == "FINANCIAL" and fid == "roic_wacc"
        rows.append({
            "factor_id": fid, "weight": node["current_local_weight"],
            "score": score, "state": state,
            "applicable": not na,
            "applicability_basis": "existing FINANCIAL_NOT_APPLICABLE: roic_wacc" if na else "illustrative resolved applicable",
            "requiredness": "REQUIRED" if index == 0 else "OPTIONAL",
            "consumed": not na,
        })
    return {
        "case_id": f"{axis}/{name}", "axis": axis, "rows": rows,
        "source_golden_case": golden_case["case_id"],
        "source_confidence": golden_case["confidence"],
        "current_expected_score_read_only": golden_case["expected"][f"{axis}_score"],
        "current_expected_matches_this_input": True,
        "requiredness_assignment": "SIMULATION_ONLY: first existing factor required, others optional; NOT an Official registry decision",
        "weight_assignment": "existing current_factor_map values, unless explicitly zeroed for a toy Custom fixture",
    }


def mutate_case(base, name, indexes=(), state=None, **changes):
    case = copy.deepcopy(base)
    case["case_id"] = f"{case['axis']}/{name}"
    case["current_expected_matches_this_input"] = False
    for index in indexes:
        if state is not None:
            case["rows"][index]["state"] = state
            case["rows"][index]["score"] = None
        case["rows"][index].update(changes)
    return case


def make_cases(factor_map, golden):
    originals = {row["case_id"]: row for row in golden["cases"]}
    cases = []
    for axis in "QGV":
        base = make_case(axis, "all_present", factor_map, originals["all_70"])
        count = len(base["rows"])
        cases.append(base)
        cases.append(mutate_case(base, "optional_missing", (1,), "MISSING_DATA"))
        cases.append(mutate_case(base, "required_missing", (0,), "MISSING_DATA"))
        cases.append(mutate_case(base, "factor_absent", (1,), "ABSENT"))
        cases.append(mutate_case(base, "score_none", (1,), "SCORE_NONE"))
        cases.append(mutate_case(base, "source_unavailable", (1,), "SOURCE_UNAVAILABLE"))
        cases.append(mutate_case(base, "young_company_history", (1,), "INSUFFICIENT_HISTORY"))
        cases.append(mutate_case(base, "proven_na", (1,), "NOT_APPLICABLE", applicable=False, consumed=False, applicability_basis="HYPOTHETICAL validated N/A evidence; no registry adoption"))
        cases.append(mutate_case(base, "unverified_na_claim", (1,), "NOT_APPLICABLE", applicable="UNKNOWN", applicability_basis="No applicability evidence; status label alone is insufficient"))
        cases.append(mutate_case(base, "na_with_consumed_contamination", (1,), "INVALID", applicable=False, consumed=True, applicability_basis="N/A cannot erase contamination already consumed by applicability/global identity"))
        cases.append(mutate_case(base, "pit_unavailable", (1,), "PIT_UNAVAILABLE"))
        cases.append(mutate_case(base, "invalid_consumed", (1,), "INVALID"))
        numeric_invalid = mutate_case(base, "numeric_integrity_failure", (1,), "VERSION_MISMATCH", score=70)
        cases.append(numeric_invalid)
        cases.append(mutate_case(base, "blocked_dependency", (1,), "BLOCKED_DEPENDENCY"))
        cases.append(mutate_case(base, "version_mismatch", (1,), "VERSION_MISMATCH"))
        cases.append(mutate_case(base, "identifier_ambiguous", (1,), "IDENTIFIER_AMBIGUOUS"))
        resolved_change = mutate_case(base, "identifier_changed_resolved_mapping", (1,), lineage_state="IDENTIFIER_CHANGED", lineage_resolution="HYPOTHETICAL_RESOLVED_DATED_MAPPING")
        cases.append(resolved_change)
        unresolved_change = mutate_case(base, "identifier_changed_unresolved_mapping", (1,), "IDENTIFIER_AMBIGUOUS", lineage_state="IDENTIFIER_CHANGED", lineage_resolution="UNRESOLVED")
        cases.append(unresolved_change)
        cases.append(mutate_case(base, "calculation_error", (1,), "CALCULATION_ERROR"))
        cases.append(mutate_case(base, "zero_weight_present", (1,), weight=0))
        cases.append(mutate_case(base, "zero_weight_required_missing", (0,), "MISSING_DATA", weight=0))
        cases.append(mutate_case(base, "zero_weight_required_pit", (0,), "PIT_UNAVAILABLE", weight=0))
        cases.append(mutate_case(base, "zero_weight_optional_missing", (1,), "MISSING_DATA", weight=0, consumed=False, request_scope="PREDECLARED_OPTIONAL_UNREQUESTED; not used by identity/applicability/global admission"))
        cases.append(mutate_case(base, "zero_weight_optional_consumed_pit", (1,), "PIT_UNAVAILABLE", weight=0, consumed=True))
        cases.append(mutate_case(base, "several_optional_missing", (1, 2), "MISSING_DATA"))
        cases.append(mutate_case(base, "all_missing", range(count), "MISSING_DATA"))
        cases.append(mutate_case(base, "all_na", range(count), "NOT_APPLICABLE", applicable=False, consumed=False))
        cases.append(mutate_case(base, "all_zero_weight", range(count), weight=0))
        cases.append(mutate_case(base, "unknown_applicability", (1,), applicable="UNKNOWN"))
        for time_field in ("available_at", "published_at"):
            global_failure = mutate_case(base, f"provider_{time_field}_after_decision")
            global_failure["global_admission_failure"] = f"{time_field} > decision_time"
            cases.append(global_failure)
        heterogeneous = make_case(axis, "heterogeneous_present", factor_map, originals["heterogeneous_fractional"])
        cases.append(heterogeneous)
        lowest = min(range(count), key=lambda index: heterogeneous["rows"][index]["score"])
        removed = mutate_case(heterogeneous, "hide_lowest_score", (lowest,), "MISSING_DATA")
        removed["counterfactual_basis"] = f"selectively hide {heterogeneous['rows'][lowest]['factor_id']} score {heterogeneous['rows'][lowest]['score']}; same registered weight and meaning"
        cases.append(removed)
    for original in ("financial_na", "financial_na_even_if_bad_roic"):
        cases.append(make_case("Q", original, factor_map, originals[original]))
    financial = next(c for c in cases if c["case_id"] == "Q/financial_na")
    cases.append(mutate_case(financial, "financial_optional_missing", (2,), "MISSING_DATA"))
    return cases


def evaluate(case, policy):
    rows = case["rows"]
    unknown = [r["factor_id"] for r in rows if r["applicable"] not in (True, False)]
    applicable = [r for r in rows if r["applicable"] is True]
    consumed_bad = [r["factor_id"] for r in rows if r["consumed"] and r["state"] in CONSUMED_FAILURES]
    valid = [r for r in applicable if r["state"] == "PRESENT" and r["score"] is not None]
    missing = [r for r in applicable if r not in valid]
    active_scoring = [r for r in applicable if r["weight"] > 0]
    active_scoring_missing = [r for r in missing if r["weight"] > 0]
    required = [r for r in applicable if r["requiredness"] == "REQUIRED"]
    required_missing = [r["factor_id"] for r in required if r not in valid]
    applicable_weight = sum((fraction(r["weight"]) for r in applicable), Fraction())
    available_weight = sum((fraction(r["weight"]) for r in valid), Fraction())
    numerator = sum((fraction(r["weight"]) * fraction(r["score"]) for r in valid), Fraction())
    denominator = available_weight if policy == "B_AVAILABLE_ESTIMATE" else applicable_weight
    output = {
        "policy": policy,
        "eligibility": {
            "global_admission_failure": case.get("global_admission_failure"),
            "unknown_applicability": unknown,
            "consumed_integrity_failures": consumed_bad,
            "required_missing": required_missing,
            "missing_reasons": {r["factor_id"]: r["state"] for r in missing},
            "active_scoring_missing": [r["factor_id"] for r in active_scoring_missing],
            "evidence_inventory_missing": [r["factor_id"] for r in missing],
            "excluded_proven_na": [r["factor_id"] for r in rows if r["applicable"] is False],
        },
        "arithmetic_diagnostic": {
            "numerator": number(numerator), "denominator": None if unknown else number(denominator),
            "applicable_weight": None if unknown else number(applicable_weight),
            "available_weight": number(available_weight),
            "candidate_quotient": None if unknown or not denominator else number(numerator / denominator),
        },
        "coverage": {
            "weight_fraction": None if unknown or not applicable_weight else number(available_weight / applicable_weight),
            "count_fraction": None if unknown or not applicable else len(valid) / len(applicable),
            "active_scoring_count_fraction": None if unknown or not active_scoring else (len(active_scoring) - len(active_scoring_missing)) / len(active_scoring),
            "available_count": len(valid), "applicable_count": len(applicable),
            "required_present_count": len(required) - len(required_missing), "required_count": len(required),
            "zero_weight_rows_remain_in_evidence_count": True,
            "complete_construct_basis": "method-required evidence plus positive-weight applicable active scoring; inventory count is separate",
            "basis": "existing profile-weight evidence coverage plus separate applicable factor count; no cutoff",
        },
        "confidence": {"formula": "NOT_DEFINED", "input_metadata": case["source_confidence"], "independent_of_coverage": True},
        "score": None, "score_kind": None, "final_status": None,
        "complete_rank_eligible_under_this_candidate": False,
        "ranking_scope": "ILLUSTRATIVE future completeness gate; no Official Leaderboard admission approved",
    }
    # The safety boundary precedes weights and applies to evidence actually
    # consumed by this calculation / applicability decision, including weight=0.
    if case.get("global_admission_failure"):
        output["final_status"] = "BLOCKED_GLOBAL_SOURCE_ADMISSION"
    elif consumed_bad:
        output["final_status"] = "BLOCKED_CONSUMED_PIT_OR_INTEGRITY"
    elif unknown:
        output["final_status"] = "BLOCKED_UNRESOLVED_APPLICABILITY"
    elif not applicable_weight:
        output["final_status"] = "BLOCKED_NO_POSITIVE_APPLICABLE_WEIGHT"
    elif not available_weight:
        output["final_status"] = "BLOCKED_NO_SCORING_EVIDENCE"
    elif policy == "A_STRICT_COMPLETE" and missing:
        output["final_status"] = "BLOCKED_INCOMPLETE"
    elif policy == "D_REQUIREDNESS_HYBRID" and required_missing:
        output["final_status"] = "BLOCKED_REQUIRED_EVIDENCE"
    else:
        output["score"] = number(numerator / denominator)
        # Method-required evidence stays compulsory at zero weight. Optional
        # predeclared unrequested zero-weight inventory does not make an otherwise
        # complete construct partial. It remains visible in inventory coverage.
        # B/C may emit a diagnostic without required evidence, but cannot certify
        # completeness under the shared proposed M4 completeness context.
        construct_incomplete = bool(active_scoring_missing or required_missing)
        if construct_incomplete:
            output["score_kind"] = "PARTIAL_ESTIMATE" if policy == "B_AVAILABLE_ESTIMATE" else "PARTIAL_CONTRIBUTION"
            output["final_status"] = output["score_kind"] + "_DIAGNOSTIC_ONLY"
        else:
            output["score_kind"] = "COMPLETE_APPLICABLE_SCORE"
            output["final_status"] = "COMPLETE_IN_THIS_SYNTHETIC_COMPARISON"
            output["complete_rank_eligible_under_this_candidate"] = True
    return output


def unsafe_counterexamples(cases):
    """Illustrate a forbidden bypass; these outputs are not viable policies."""
    outputs = []
    for axis in "QGV":
        case = next(c for c in cases if c["case_id"] == f"{axis}/zero_weight_required_pit")
        active_valid = [r for r in case["rows"] if r["weight"] > 0 and r["state"] == "PRESENT"]
        numerator = sum((fraction(r["weight"]) * fraction(r["score"]) for r in active_valid), Fraction())
        denominator = sum((fraction(r["weight"]) for r in active_valid), Fraction())
        outputs.append({
            "case_id": case["case_id"],
            "unsafe_filter": "remove zero weights first; treat consumed PIT failure as ordinary missing; renormalize remaining evidence",
            "unsafe_score": number(numerator / denominator),
            "guarded_score": None,
            "guarded_status": evaluate(case, "D_REQUIREDNESS_HYBRID")["final_status"],
            "status": "REJECTED_COUNTEREXAMPLE_NOT_POLICY",
        })
    return outputs


def denominator_sensitivity(cases):
    """Keep the N/A denominator decision explicit rather than burying it."""
    rows = []
    for case_id in ("Q/financial_na", "Q/financial_optional_missing"):
        case = next(c for c in cases if c["case_id"] == case_id)
        total = sum((fraction(r["weight"]) for r in case["rows"]), Fraction())
        applicable = sum((fraction(r["weight"]) for r in case["rows"] if r["applicable"] is True), Fraction())
        present = [r for r in case["rows"] if r["applicable"] is True and r["state"] == "PRESENT"]
        available = sum((fraction(r["weight"]) for r in present), Fraction())
        numerator = sum((fraction(r["weight"]) * fraction(r["score"]) for r in present), Fraction())
        rows.append({
            "case_id": case_id, "numerator": number(numerator),
            "keep_entire_registered_denominator": {"denominator": number(total), "quotient": number(numerator / total)},
            "exclude_proven_na_keep_ordinary_missing": {"denominator": number(applicable), "quotient": number(numerator / applicable)},
            "available_only": {"denominator": number(available), "quotient": number(numerator / available)},
            "status": "PROPOSED_ALTERNATIVE_ARITHMETIC_NOT_PRODUCTION_POLICY",
        })
    return rows


def handchecks(cases, outputs):
    indexed = {c["case_id"]: c for c in cases}
    get = lambda case, policy: outputs[case][policy]
    checks = []
    def check(name, passed):
        if not passed:
            raise AssertionError(name)
        checks.append({"check": name, "result": "PASS"})
    for axis in "QGV":
        for policy in POLICIES:
            check(f"{axis}/{policy}: complete uniform evidence is 70", get(f"{axis}/all_present", policy)["score"] == 70)
            for case_name in ("pit_unavailable", "invalid_consumed", "blocked_dependency", "version_mismatch", "identifier_ambiguous", "identifier_changed_unresolved_mapping", "calculation_error", "zero_weight_required_pit", "zero_weight_optional_consumed_pit", "na_with_consumed_contamination", "numeric_integrity_failure", "provider_available_at_after_decision", "provider_published_at_after_decision"):
                result = get(f"{axis}/{case_name}", policy)
                check(f"{axis}/{policy}/{case_name}: failure cannot produce or rank a score", result["score"] is None and not result["complete_rank_eligible_under_this_candidate"])
            for case_name in ("all_zero_weight", "all_na", "all_missing", "unknown_applicability", "unverified_na_claim"):
                check(f"{axis}/{policy}/{case_name}: undefined denominator/evidence cannot score", get(f"{axis}/{case_name}", policy)["score"] is None)
            check(f"{axis}/{policy}: dated resolved identifier change alone is not a blanket integrity failure", get(f"{axis}/identifier_changed_resolved_mapping", policy)["score"] == 70)
        first_weight = fraction(indexed[f"{axis}/all_present"]["rows"][0]["weight"])
        second_weight = fraction(indexed[f"{axis}/all_present"]["rows"][1]["weight"])
        fixed = get(f"{axis}/optional_missing", "D_REQUIREDNESS_HYBRID")
        check(f"{axis}: fixed partial equals 70 times retained registered weight", fixed["score"] == number(70 * (1 - second_weight)))
        check(f"{axis}: optional missing carries count coverage and cannot rank", fixed["coverage"]["count_fraction"] < 1 and not fixed["complete_rank_eligible_under_this_candidate"])
        check(f"{axis}: zero weight does not remove requiredness", get(f"{axis}/zero_weight_required_missing", "D_REQUIREDNESS_HYBRID")["score"] is None)
        zero_optional = get(f"{axis}/zero_weight_optional_missing", "D_REQUIREDNESS_HYBRID")
        check(f"{axis}: predeclared unrequested optional-zero inventory missing leaves required/active construct complete", zero_optional["score"] == 70 and zero_optional["complete_rank_eligible_under_this_candidate"] and zero_optional["coverage"]["count_fraction"] < 1 and zero_optional["coverage"]["active_scoring_count_fraction"] == 1)
        for policy in ("B_AVAILABLE_ESTIMATE", "C_FIXED_PARTIAL"):
            check(f"{axis}/{policy}: numeric diagnostic at zero weight cannot certify absent method-required evidence", not get(f"{axis}/zero_weight_required_missing", policy)["complete_rank_eligible_under_this_candidate"])
        check(f"{axis}: available estimate cannot inflate uniform score above 70", get(f"{axis}/optional_missing", "B_AVAILABLE_ESTIMATE")["score"] == 70)
        before = get(f"{axis}/heterogeneous_present", "B_AVAILABLE_ESTIMATE")["score"]
        after = get(f"{axis}/hide_lowest_score", "B_AVAILABLE_ESTIMATE")["score"]
        check(f"{axis}: selective low-score removal inflates renormalized estimate", after > before)
        fixed_before = get(f"{axis}/heterogeneous_present", "C_FIXED_PARTIAL")["score"]
        fixed_after = get(f"{axis}/hide_lowest_score", "C_FIXED_PARTIAL")["score"]
        check(f"{axis}: removal cannot improve fixed contribution with nonnegative scores", fixed_after <= fixed_before)
    check("financial golden current score remains independently stored as 56", indexed["Q/financial_na"]["current_expected_score_read_only"] == 56)
    check("financial applicability proposal: 56 numerator / 0.8 denominator = 70", get("Q/financial_na", "D_REQUIREDNESS_HYBRID")["score"] == 70)
    check("financial unused ROIC failure is not consumed and does not bypass any consumed evidence guard", get("Q/financial_na_even_if_bad_roic", "D_REQUIREDNESS_HYBRID")["score"] == 70)
    return checks


def run(output_path):
    factor_map, golden, baseline, paths = load_inputs()
    before = hashes(paths)
    cases = make_cases(factor_map, golden)
    outputs = {case["case_id"]: {policy: evaluate(case, policy) for policy in POLICIES} for case in cases}
    checks = handchecks(cases, outputs)
    after = hashes(paths)
    if before != after:
        raise AssertionError("Read-only source/golden inputs changed during simulation")
    source_match = {name: before[name] == expected for name, expected in baseline["source_sha256"].items()}
    if not all(source_match.values()):
        raise AssertionError("Source bytes differ from the original inactive-contract baseline; impact review required")
    if before[str((DOCS / "golden_cases.json").relative_to(REPO))] != baseline["golden_fixture_sha256"]:
        raise AssertionError("Original golden fixture identity changed")
    result = {
        "status": "PROPOSED_INACTIVE_SYNTHETIC_ONLY_NOT_APPROVED",
        "production_imports": False, "production_execution": False,
        "production_changed": False, "pit_oos": "NOT_RUN", "holdout": "UNCONSUMED",
        "source_commit_of_current_factor_map": factor_map["source_commit"],
        "role_assignment": "SIMULATION_ONLY; no factor requiredness/applicability registry has been approved",
        "confidence_formula": "NONE", "coverage_threshold": "NONE",
        "configuration_validation_scope": "Toy zero-weight vectors are denominator/requiredness sensitivity inputs; sibling weights are not redistributed and sum can be below 1. They are NOT validated Personal WeightOverride requests. Production must validate pinned configuration before aggregation; no runtime isolation/config acceptance is proven here.",
        "policy_definitions": {
            "A_STRICT_COMPLETE": "Strong fail-closed illustration: all applicable evidence complete, including toy optional factors. Stricter than merely required-factor blocking. Denominator = all applicable configured weights.",
            "B_AVAILABLE_ESTIMATE": "Available-weight renormalization; ordinary missing may include required factors. Incomplete output is an estimate, excluded from complete-ranking illustration. Shared consumed PIT/integrity guard.",
            "C_FIXED_PARTIAL": "All applicable weights remain in denominator for ordinary missing. Incomplete contribution is diagnostic only. No required-factor gate beyond no evidence. Shared consumed PIT/integrity guard.",
            "D_REQUIREDNESS_HYBRID": "Required missing blocks regardless of weight; positive-weight optional ordinary missing yields fixed-applicable-denominator contribution diagnostic only; proven N/A removed. Predeclared unrequested optional-zero inventory does not impair required/active construct completeness. Shared consumed PIT/integrity and unresolved-applicability guards.",
        },
        "separate_open_choice": "Permit optional partial diagnostic (D) versus withhold optional-incomplete score (A). These policy alternatives are not approved.",
        "cases": cases, "results": outputs,
        "unsafe_counterexamples": unsafe_counterexamples(cases),
        "denominator_sensitivity": denominator_sensitivity(cases),
        "verification": {
            "source_hashes_before": before, "source_hashes_after": after,
            "all_inputs_unchanged": before == after,
            "baseline_source_hash_matches": source_match,
            "golden_sha256": baseline["golden_fixture_sha256"],
            "handcalculated_and_safety_checks": checks,
            "checks_passed": len(checks), "case_count": len(cases), "policy_result_count": len(cases) * len(POLICIES),
        },
    }
    output_path.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "simulation_results.json")
    args = parser.parse_args()
    result = run(args.output)
    verification = result["verification"]
    print(json.dumps({"status": result["status"], "cases": verification["case_count"], "policy_results": verification["policy_result_count"], "checks_passed": verification["checks_passed"], "read_only_sources": verification["all_inputs_unchanged"], "golden_sha256": verification["golden_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
