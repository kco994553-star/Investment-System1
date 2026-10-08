"""Finite inactive reference-carrier tests; no QGV scoring or runtime admission.

This validates trusted fixture byte bindings, declared scopes and reference
relationships only. It never evaluates a valuation/growth formula, decides
requiredness or grants real scoring, ranking or publication authority.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

ASSESSMENTS = ("method_identity", "applicability", "evidence_admission", "provenance", "pit", "coverage", "confidence", "completeness", "scoring_validity")
NAMESPACES = {"OFFICIAL", "CUSTOM_ACTIVE", "SANDBOX", "PREVIEW", "BACKTEST", "FORWARD"}
TOP_KEYS = {"artifact_kind", "version", "runtime_enabled", "activation_requested", "authority_record_ref", "context", "scope_ref", "producer_result_ref", "legacy_numeric", "legacy_coverage_literal", "method_binding_refs", "source_refs", "assessments", "aggregate", "consumer", "publication_decision_ref", "unassessed_reasons"}
SEMANTIC_BINDINGS = ("factor_ref", "method_ref", "method_version_ref", "input_contract_ref", "fallback_ref", "normalization_ref")


class CarrierError(ValueError):
    pass


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def fixture_registry() -> tuple[dict, dict]:
    """Independent expected fixture content, never a real authority registry."""
    registry: dict[tuple[str, str], dict] = {}

    def add(name: str, body: dict) -> dict:
        ref = {"id": "SYNTHETIC_" + name, "version": "fixture-v1", "sha256": digest(body), "locator": "fixture://" + name}
        registry[(ref["id"], ref["version"])] = {"ref": ref, "body": body}
        return ref

    context = {"subject_id": "SYNTHETIC_COMPANY", "as_of": "2024-12-31T00:00:00+00:00", "decision_time": "2024-12-31T00:00:00+00:00", "namespace": "SANDBOX", "configuration_ref": None}
    factor = add("factor", {"kind": "factor_identity", "factor_id": "revenue_growth"})
    method = add("method", {"kind": "method_identity", "factor_ref": factor, "source": "synthetic characterization only"})
    version = add("method_version", {"kind": "method_version", "method_ref": method})
    inputs = add("input_contract", {"kind": "input_contract", "periods": "unassessed", "method_ref": method})
    scope = add("scope", {"kind": "scope", "context": context, "axis": "G", "factor_ids": ["revenue_growth"], "input_ids": ["SYNTHETIC_RAW"], "shared_dependency_ids": []})
    source = add("source", {"kind": "source", "source_status": "SYNTHETIC_ONLY", "available_at": context["as_of"], "published_at": context["as_of"]})
    result = add("legacy_result", {"kind": "legacy_result", "context": context, "scope_ref": scope, "legacy_numeric": 70.0, "legacy_coverage_literal": "READY", "source_refs": [source]})
    binding = {"factor_ref": factor, "method_ref": method, "method_version_ref": version, "input_contract_ref": inputs, "fallback_ref": None, "normalization_ref": None}
    assessments = {}
    for name in ASSESSMENTS:
        assessments[name] = add(name, {"kind": name, "context": context, "scope_ref": scope, "producer_result_ref": result, "method_binding_refs": [binding], "source_refs": [source], "policy_ref": None, "disposition": "UNASSESSED", "reason": "SYNTHETIC carrier; actual domain authority is not assigned"})
    fixture = {
        "artifact_kind": "INACTIVE_RESULT_ADMISSION_REF_CARRIER", "version": "0.1", "runtime_enabled": False,
        "activation_requested": False, "authority_record_ref": None, "context": context,
        "scope_ref": scope, "producer_result_ref": result, "legacy_numeric": 70.0, "legacy_coverage_literal": "READY",
        "method_binding_refs": [binding], "source_refs": [source], "assessments": assessments,
        "aggregate": {"scope_ref": scope, "ordered_child_result_refs": [result], "child_assessment_refs": [assessments], "withheld_child_result_refs": [], "planned_basis_ref": None, "arithmetic_ref": None},
        "consumer": {"id": "SYNTHETIC_ANALYSIS", "version": "fixture-v1", "purpose": "DIAGNOSTIC", "namespace": "SANDBOX", "result_ref": result, "scope_ref": scope, "producer_assessment_refs": assessments, "policy_ref": None, "admission_decision_ref": None},
        "publication_decision_ref": None,
        "unassessed_reasons": {"authority_record_ref": "Fixture authority only", "configuration_ref": "No runtime evaluator/configuration", "fallback_ref": "No new fallback selected", "normalization_ref": "No new normalizer selected", "planned_basis_ref": "No arithmetic/basis policy adopted", "arithmetic_ref": "Existing result only", "consumer_policy_ref": "B2/B3/B5/B6 not approved", "admission_decision_ref": "No actual consumer admission", "publication_decision_ref": "No grant or P01 change"},
    }
    return registry, fixture


def validate(carrier: dict, registry: dict) -> dict:
    """INACTIVE structural fixture checker, never production admission."""
    def require(ok: bool, code: str) -> None:
        if not ok:
            raise CarrierError(code)

    def reason_present(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def resolve(ref: dict | None, required: bool = True) -> dict | None:
        if ref is None:
            require(not required, "MISSING_REFERENCE")
            return None
        require(isinstance(ref, dict) and set(ref) == {"id", "version", "sha256", "locator"}, "REFERENCE_SHAPE")
        trusted = registry.get((ref["id"], ref["version"]))
        require(trusted is not None, "UNRESOLVED_REFERENCE")
        require(ref == trusted["ref"], "CONFLICTING_OR_STALE_REFERENCE")
        require(digest(trusted["body"]) == ref["sha256"], "REFERENCE_CONTENT_DRIFT")
        return trusted["body"]

    require(isinstance(carrier, dict) and set(carrier) == TOP_KEYS, "CARRIER_SHAPE_NO_ELIGIBILITY_FLAG")
    require(carrier["artifact_kind"] == "INACTIVE_RESULT_ADMISSION_REF_CARRIER" and carrier["version"] == "0.1", "INACTIVE_CARRIER_IDENTITY")
    require(carrier["runtime_enabled"] is False and carrier["activation_requested"] is False, "PRODUCTION_ACTIVATION_FORBIDDEN")
    context = carrier["context"]
    require(set(context) == {"subject_id", "as_of", "decision_time", "namespace", "configuration_ref"} and context["namespace"] in NAMESPACES, "CONTEXT_SHAPE")
    reasons = carrier["unassessed_reasons"]
    require(isinstance(reasons, dict), "UNASSESSED_REASONS_REQUIRED")
    resolve(carrier["authority_record_ref"], required=False)
    if carrier["authority_record_ref"] is None:
        require(reason_present(reasons.get("authority_record_ref")), "UNASSESSED_AUTHORITY_REASON")
    resolve(context["configuration_ref"], required=False)
    if context["configuration_ref"] is None:
        require(reason_present(reasons.get("configuration_ref")), "UNASSESSED_CONFIGURATION_REASON")
    scope = resolve(carrier["scope_ref"])
    require(scope["kind"] == "scope" and scope["context"] == context, "SCOPE_CONTEXT_MISMATCH")
    require(isinstance(scope["factor_ids"], list) and len(scope["factor_ids"]) == len(set(scope["factor_ids"])), "SCOPE_FACTOR_INVENTORY")
    result = resolve(carrier["producer_result_ref"])
    require(result["kind"] == "legacy_result", "RESULT_REFERENCE_MEANING_SUBSTITUTION")
    require(result["context"] == context and result["scope_ref"] == carrier["scope_ref"], "STALE_RESULT_BINDING")
    value = carrier["legacy_numeric"]
    require(value is None or (not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)), "NONFINITE_OR_INVALID_LITERAL")
    require(value == result["legacy_numeric"] and carrier["legacy_coverage_literal"] == result["legacy_coverage_literal"], "LEGACY_LITERAL_MUTATION")
    require(carrier["source_refs"] == result["source_refs"], "SOURCE_CLOSURE_MISMATCH")
    for ref in carrier["source_refs"]:
        require(resolve(ref)["kind"] == "source", "SOURCE_REFERENCE_MEANING_SUBSTITUTION")
    require(isinstance(carrier["method_binding_refs"], list) and bool(carrier["method_binding_refs"]), "METHOD_BINDING_INVENTORY")
    factor_ids = []
    for binding in carrier["method_binding_refs"]:
        require(set(binding) == set(SEMANTIC_BINDINGS), "METHOD_BINDING_SHAPE")
        factor = resolve(binding["factor_ref"])
        require(factor["kind"] == "factor_identity", "FACTOR_METHOD_IDENTITY_MIX")
        factor_ids.append(factor["factor_id"])
        for field, kind in (("method_ref", "method_identity"), ("method_version_ref", "method_version"), ("input_contract_ref", "input_contract")):
            doc = resolve(binding[field], required=False)
            if doc is None:
                require(reason_present(reasons.get(field)), "UNASSESSED_METHOD_REASON")
            else:
                require(doc["kind"] == kind, "FACTOR_METHOD_IDENTITY_MIX")
        method = resolve(binding["method_ref"], required=False)
        if method:
            require(method["factor_ref"] == binding["factor_ref"], "METHOD_FACTOR_CROSS_BINDING")
        input_contract = resolve(binding["input_contract_ref"], required=False)
        if input_contract:
            require(input_contract["method_ref"] == binding["method_ref"], "INPUT_CONTRACT_METHOD_CROSS_BINDING")
        version = resolve(binding["method_version_ref"], required=False)
        if version:
            require(version["method_ref"] == binding["method_ref"], "METHOD_VERSION_CROSS_BINDING")
        for field in ("fallback_ref", "normalization_ref"):
            if binding[field] is None:
                require(reason_present(reasons.get(field)), "UNASSESSED_METHOD_REASON")
            else:
                doc = resolve(binding[field])
                expected_kind = "fallback_method" if field == "fallback_ref" else "normalization"
                require(doc["kind"] == expected_kind, "FALLBACK_REFERENCE_TYPE" if field == "fallback_ref" else "NORMALIZATION_REFERENCE_TYPE")
                require(doc["method_ref"] == binding["method_ref"], "FALLBACK_NORMALIZATION_METHOD_CROSS_BINDING")
    require(set(factor_ids) == set(scope["factor_ids"]) and len(factor_ids) == len(scope["factor_ids"]), "SCOPE_EXPANSION_OR_FACTOR_DROP")
    assessments = carrier["assessments"]
    require(set(assessments) == set(ASSESSMENTS), "INDEPENDENT_ASSESSMENTS_REQUIRED")
    for name, ref in assessments.items():
        assessment = resolve(ref, required=False)
        if assessment is None:
            require(reason_present(reasons.get(name)), "UNASSESSED_ASSESSMENT_REASON")
            continue
        require(assessment["kind"] == name, "ASSESSMENT_MEANING_SUBSTITUTION")
        require(assessment["context"] == context and assessment["scope_ref"] == carrier["scope_ref"] and assessment["producer_result_ref"] == carrier["producer_result_ref"], "STALE_OR_EXPANDED_ASSESSMENT")
        require(assessment["source_refs"] == carrier["source_refs"] and assessment["method_binding_refs"] == carrier["method_binding_refs"], "ASSESSMENT_DEPENDENCY_SCOPE_DRIFT")
        # This finite phase lacks real B2/B3/B5/B6 predicates/criteria. Neither
        # fixture refs nor approved G meaning may assert operational admission.
        require(assessment["disposition"] in {"UNASSESSED", "REJECTED"} and reason_present(assessment.get("reason")), "UNAUTHORIZED_AFFIRMATIVE_ASSESSMENT")
        require(assessment["policy_ref"] is None, "UNAPPROVED_POLICY_BINDING")
    aggregate = carrier["aggregate"]
    require(set(aggregate) == {"scope_ref", "ordered_child_result_refs", "child_assessment_refs", "withheld_child_result_refs", "planned_basis_ref", "arithmetic_ref"}, "AGGREGATE_SHAPE")
    require(aggregate["scope_ref"] == carrier["scope_ref"], "AGGREGATE_SCOPE_EXPANSION")
    require(aggregate["ordered_child_result_refs"] == [carrier["producer_result_ref"]] and aggregate["child_assessment_refs"] == [assessments], "AGGREGATE_CHILD_ASSESSMENT_DROP")
    require(aggregate["withheld_child_result_refs"] == [], "UNBOUND_WITHHELD_INVENTORY")
    for field in ("planned_basis_ref", "arithmetic_ref"):
        if aggregate[field] is None:
            require(reason_present(reasons.get(field)), "UNASSESSED_BASIS_REASON")
        else:
            resolve(aggregate[field])
    consumer = carrier["consumer"]
    require(set(consumer) == {"id", "version", "purpose", "namespace", "result_ref", "scope_ref", "producer_assessment_refs", "policy_ref", "admission_decision_ref"}, "CONSUMER_SHAPE")
    require(reason_present(consumer["id"]) and reason_present(consumer["version"]), "CONSUMER_IDENTITY_REQUIRED")
    require(consumer["namespace"] == context["namespace"] and consumer["scope_ref"] == carrier["scope_ref"] and consumer["result_ref"] == carrier["producer_result_ref"], "CONSUMER_CONTEXT_OR_SCOPE_MISMATCH")
    require(consumer["producer_assessment_refs"] == assessments, "CONSUMER_ASSESSMENT_REFERENCE_MISMATCH")
    require(consumer["purpose"] == "DIAGNOSTIC", "UNASSESSED_CONSUMER_PURPOSE_PROMOTION")
    require(consumer["policy_ref"] is None and consumer["admission_decision_ref"] is None, "UNAPPROVED_CONSUMER_ACTIVATION")
    require(reason_present(reasons.get("consumer_policy_ref")) and reason_present(reasons.get("admission_decision_ref")), "UNASSESSED_CONSUMER_REASON")
    require(carrier["publication_decision_ref"] is None and reason_present(reasons.get("publication_decision_ref")), "PUBLICATION_AUTHORITY_NOT_GRANTED")
    return {"structural_acceptance": "PASS", "semantic_validity": "NOT_EVALUATED", "consumer_admission": "NOT_EVALUATED", "runtime_enabled": False, "limitation": "Fixture scope only; no production authority or new admission criteria"}


def preserve_zero_profile_authority(base: dict, overlay: dict) -> None:
    """Compare fixture immutable obligations, no weight/tree computation."""
    for field in ("scope_ref", "method_binding_refs", "source_refs", "assessments", "authority_record_ref"):
        if base[field] != overlay[field]:
            raise CarrierError("ZERO_OR_PROFILE_SEMANTIC_WAIVER")
    if base["context"] != overlay["context"]:
        raise CarrierError("OFFICIAL_CUSTOM_CONTEXT_COLLAPSE")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    registry, base = fixture_registry()
    cases = []

    def rebind_assessment(carrier: dict, name: str, ref: dict | None) -> None:
        carrier["assessments"][name] = copy.deepcopy(ref)
        carrier["aggregate"]["child_assessment_refs"][0][name] = copy.deepcopy(ref)
        carrier["consumer"]["producer_assessment_refs"][name] = copy.deepcopy(ref)

    def replace_assessment_body(trusted: dict, carrier: dict, name: str, change: dict) -> None:
        old = carrier["assessments"][name]
        body = copy.deepcopy(trusted[(old["id"], old["version"])]["body"])
        body.update(change)
        ref = {**old, "version": "fixture-v2", "sha256": digest(body)}
        trusted[(ref["id"], ref["version"])] = {"ref": ref, "body": body}
        rebind_assessment(carrier, name, ref)

    def bad_input_link(trusted: dict, carrier: dict) -> None:
        old = carrier["method_binding_refs"][0]["input_contract_ref"]
        body = copy.deepcopy(trusted[(old["id"], old["version"])]["body"])
        body["method_ref"] = carrier["method_binding_refs"][0]["factor_ref"]
        ref = {**old, "version": "fixture-v2", "sha256": digest(body)}
        trusted[(ref["id"], ref["version"])] = {"ref": ref, "body": body}
        carrier["method_binding_refs"][0]["input_contract_ref"] = ref

    def bad_method_factor_link(trusted: dict, carrier: dict) -> None:
        old = carrier["method_binding_refs"][0]["method_ref"]
        body = copy.deepcopy(trusted[(old["id"], old["version"])]["body"])
        body["factor_ref"] = carrier["scope_ref"]
        ref = {**old, "version": "fixture-v2", "sha256": digest(body)}
        trusted[(ref["id"], ref["version"])] = {"ref": ref, "body": body}
        carrier["method_binding_refs"][0]["method_ref"] = ref

    def bad_source_kind(trusted: dict, carrier: dict) -> None:
        old = carrier["source_refs"][0]
        entry = trusted[(old["id"], old["version"])]
        entry["body"]["kind"] = "method_identity"
        ref = {**old, "sha256": digest(entry["body"])}
        entry["ref"] = ref
        carrier["source_refs"] = [ref]
        # Coherently re-pin result too; rejection must be relational/type-based,
        # not merely failure to match an old byte hash.
        old_result = carrier["producer_result_ref"]
        result_entry = trusted[(old_result["id"], old_result["version"])]
        result_entry["body"]["source_refs"] = [ref]
        result_ref = {**old_result, "sha256": digest(result_entry["body"])}
        result_entry["ref"] = result_ref
        carrier["producer_result_ref"] = result_ref

    def bad_result_kind(trusted: dict, carrier: dict) -> None:
        old = carrier["producer_result_ref"]
        entry = trusted[(old["id"], old["version"])]
        entry["body"]["kind"] = "scope"
        ref = {**old, "sha256": digest(entry["body"])}
        entry["ref"] = ref
        carrier["producer_result_ref"] = ref

    def bad_normalization_link(trusted: dict, carrier: dict) -> None:
        body = {"kind": "normalization", "method_ref": carrier["method_binding_refs"][0]["factor_ref"]}
        ref = {"id": "SYNTHETIC_normalization", "version": "fixture-v1", "sha256": digest(body), "locator": "fixture://normalization"}
        trusted[(ref["id"],ref["version"])] = {"ref": ref, "body": body}
        carrier["method_binding_refs"][0]["normalization_ref"] = ref

    def run(name: str, mutate=None, expected: str | None = None, registry_mutate=None, overlay=False) -> None:
        # Serialize/deserialize to avoid Python object-alias mutations making
        # independent producer/aggregate/consumer refs agree accidentally.
        carrier, trusted = json.loads(canonical_bytes(base)), copy.deepcopy(registry)
        if mutate:
            mutate(carrier)
        if registry_mutate:
            registry_mutate(trusted, carrier)
        try:
            if overlay:
                preserve_zero_profile_authority(base, carrier)
            else:
                result = validate(carrier, trusted)
            actual = "PASS_STRUCTURAL_ONLY"
        except CarrierError as exc:
            actual = str(exc)
        assert actual == (expected or "PASS_STRUCTURAL_ONLY"), (name, actual, expected)
        observations = {}
        if name.startswith(("C26_", "C27_")):
            validity = trusted[(carrier["assessments"]["scoring_validity"]["id"],carrier["assessments"]["scoring_validity"]["version"])]["body"]
            assert carrier["legacy_numeric"] == base["legacy_numeric"] == 70.0
            assert validity["disposition"] == "REJECTED"
            marker = "VERSION_MISMATCH" if name.startswith("C26_") else "CALCULATION_ERROR"
            assert marker in validity["reason"]
            assert result["semantic_validity"] == result["consumer_admission"] == "NOT_EVALUATED"
            observations = {"retained_legacy_numeric": carrier["legacy_numeric"], "retained_disposition": validity["disposition"], "retained_reason": validity["reason"], "semantic_validity": result["semantic_validity"], "consumer_admission": result["consumer_admission"]}
        cases.append({"case": name, "expected": expected or "PASS_STRUCTURAL_ONLY", "actual": actual, "pass": True, "observations": observations})

    run("C01_linked_UNASSESSED_diagnostic_carrier")
    run("C02_missing_exact_source_ref", lambda c: c["source_refs"].clear(), "SOURCE_CLOSURE_MISMATCH")
    run("C03_unresolved_reference", lambda c: c["scope_ref"].update(id="NOT_REGISTERED"), "UNRESOLVED_REFERENCE")
    run("C04_conflicting_id_version_content", lambda c: c["scope_ref"].update(sha256="0" * 64), "CONFLICTING_OR_STALE_REFERENCE")
    run("C05_trusted_content_drift", registry_mutate=lambda r,c: r[(c["scope_ref"]["id"],c["scope_ref"]["version"])]["body"].update(axis="Q"), expected="REFERENCE_CONTENT_DRIFT")
    run("C06_stale_subject_context", lambda c: c["context"].update(subject_id="OTHER_COMPANY"), "SCOPE_CONTEXT_MISMATCH")
    run("C07_scope_expanded_to_other_axis", lambda c: c["aggregate"].update(scope_ref=c["source_refs"][0]), "AGGREGATE_SCOPE_EXPANSION")
    run("C08_independent_confidence_replaced_by_coverage", lambda c: c["assessments"].update(confidence=c["assessments"]["coverage"]), "ASSESSMENT_MEANING_SUBSTITUTION")
    run("C09_consumer_namespace_mismatch", lambda c: c["consumer"].update(namespace="OFFICIAL"), "CONSUMER_CONTEXT_OR_SCOPE_MISMATCH")
    run("C10_consumer_method_validity_ref_substitution", lambda c: c["consumer"]["producer_assessment_refs"].update(scoring_validity=c["assessments"]["coverage"]), "CONSUMER_ASSESSMENT_REFERENCE_MISMATCH")
    run("C11_missing_validity_ref_with_reason_diagnostic", lambda c: (rebind_assessment(c,"scoring_validity",None), c["unassessed_reasons"].update(scoring_validity="B5 unapproved; legacy unassessed")))
    run("C12_missing_validity_ref_without_reason", lambda c: rebind_assessment(c,"scoring_validity",None), "UNASSESSED_ASSESSMENT_REASON")
    run("C13_nonfinite_numeric_NaN", lambda c: c.update(legacy_numeric=float("nan")), "NONFINITE_OR_INVALID_LITERAL")
    run("C14_nonfinite_numeric_Infinity", lambda c: c.update(legacy_numeric=float("inf")), "NONFINITE_OR_INVALID_LITERAL")
    run("C15_numeric_bool_not_score", lambda c: c.update(legacy_numeric=True), "NONFINITE_OR_INVALID_LITERAL")
    run("C16_literal_score_mutation", lambda c: c.update(legacy_numeric=71), "LEGACY_LITERAL_MUTATION")
    run("C17_READY_numeric_promoted_via_rank_flag", lambda c: c.update(ranking_eligible=True), "CARRIER_SHAPE_NO_ELIGIBILITY_FLAG")
    run("C18_unassessed_DIAGNOSTIC_promoted_ranking_purpose", lambda c: c["consumer"].update(purpose="RANKING"), "UNASSESSED_CONSUMER_PURPOSE_PROMOTION")
    run("C19_missing_child_assessment_inventory", lambda c: c["aggregate"].update(child_assessment_refs=[]), "AGGREGATE_CHILD_ASSESSMENT_DROP")
    run("C20_zero_weight_keeps_all_obligations", overlay=True)
    run("C21_zero_weight_cannot_drop_PIT_ref", lambda c: c["assessments"].update(pit=None), "ZERO_OR_PROFILE_SEMANTIC_WAIVER", overlay=True)
    run("C22_custom_cannot_replace_method", lambda c: c["method_binding_refs"][0].update(method_ref=c["method_binding_refs"][0]["factor_ref"]), "ZERO_OR_PROFILE_SEMANTIC_WAIVER", overlay=True)
    run("C23_equal_numeric_Official_Custom_isolation", lambda c: c["context"].update(namespace="OFFICIAL"), "OFFICIAL_CUSTOM_CONTEXT_COLLAPSE", overlay=True)
    run("C24_activation_request_rejected", lambda c: c.update(activation_requested=True), "PRODUCTION_ACTIVATION_FORBIDDEN")
    run("C25_missing_publication_is_not_grant", lambda c: c.update(publication_decision_ref=c["producer_result_ref"]), "PUBLICATION_AUTHORITY_NOT_GRANTED")
    run("C26_REJECTED_VERSION_MISMATCH_retains_numeric_diagnostic", registry_mutate=lambda r,c: replace_assessment_body(r,c,"scoring_validity",{"disposition":"REJECTED","reason":"Original VERSION_MISMATCH marker retained; no consumer admission"}))
    run("C27_REJECTED_CALCULATION_ERROR_retains_numeric_diagnostic", registry_mutate=lambda r,c: replace_assessment_body(r,c,"scoring_validity",{"disposition":"REJECTED","reason":"Original CALCULATION_ERROR marker retained; no consumer admission"}))
    run("C28_REJECTED_VERSION_MISMATCH_cannot_be_promoted_rankable", lambda c:c["consumer"].update(purpose="RANKING"), "UNASSESSED_CONSUMER_PURPOSE_PROMOTION", registry_mutate=lambda r,c: replace_assessment_body(r,c,"scoring_validity",{"disposition":"REJECTED","reason":"VERSION_MISMATCH"}))
    run("C29_authenticated_input_contract_cross_method_link", expected="INPUT_CONTRACT_METHOD_CROSS_BINDING", registry_mutate=bad_input_link)
    run("C30_authenticated_method_cross_factor_link", expected="METHOD_FACTOR_CROSS_BINDING", registry_mutate=bad_method_factor_link)
    run("C31_authenticated_source_type_substitution", expected="SOURCE_REFERENCE_MEANING_SUBSTITUTION", registry_mutate=bad_source_kind)
    run("C32_whitespace_is_not_unassessed_reason", lambda c:(rebind_assessment(c,"scoring_validity",None),c["unassessed_reasons"].update(scoring_validity="   ")), "UNASSESSED_ASSESSMENT_REASON")
    run("C33_authenticated_result_type_substitution", expected="RESULT_REFERENCE_MEANING_SUBSTITUTION", registry_mutate=bad_result_kind)
    run("C34_normalization_factor_identity_substitution", lambda c:c["method_binding_refs"][0].update(normalization_ref=c["method_binding_refs"][0]["factor_ref"]), "NORMALIZATION_REFERENCE_TYPE")
    run("C35_fallback_identity_type_substitution", lambda c:c["method_binding_refs"][0].update(fallback_ref=c["method_binding_refs"][0]["method_ref"]), "FALLBACK_REFERENCE_TYPE")
    run("C36_authenticated_normalization_cross_method_link", expected="FALLBACK_NORMALIZATION_METHOD_CROSS_BINDING", registry_mutate=bad_normalization_link)
    run("C37_missing_consumer_identity", lambda c:c["consumer"].update(id=""), "CONSUMER_IDENTITY_REQUIRED")
    run("C38_missing_consumer_version", lambda c:c["consumer"].update(version=None), "CONSUMER_IDENTITY_REQUIRED")
    result = {"status": "INACTIVE_FIXTURE_CARRIER_ACCEPTANCE_PASS", "checks_passed": len(cases), "checks_failed": 0, "cases": cases, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "fixture_carrier_sha256": digest(base), "production_semantics_changed": False, "scoring_executed": False, "consumer_policy_activated": False, "scheduler_hops_counted": 0, "b1_roles_assigned": 0, "limits": "SYNTHETIC reference/content/scope relationships only. Not a JSONSchema engine, trusted remote artifact resolver, QGV evaluator, production predicate, completeness/coverage/confidence/ranking method, P01 authorizer or real PIT validation. Preserving refs under zero/profile is a fixture comparison, not WeightOverride wiring. Assertions are new contract tests, not rerun runtime characterization."}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "synthetic_carrier.json").write_text(json.dumps(base, indent=2) + "\n")
    serialized_registry = [{"ref": entry["ref"], "body": entry["body"]} for entry in registry.values()]
    (args.output_dir / "synthetic_reference_contents.json").write_text(json.dumps(serialized_registry, indent=2) + "\n")
    (args.output_dir / "CONTRACT_ACCEPTANCE_RESULTS.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "checks_passed": len(cases), "checks_failed": 0}))


if __name__ == "__main__":
    main()
