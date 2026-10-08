"""Finite inactive G/C composition fixtures, never a runtime admission engine.

Imports the frozen C structural checker without executing its 38-case main.
The 21 G checks and all predecessor checks are consumed by exact byte hashes.
Actual G/C artifacts are attachments, not genuine raw input or PIT evidence.
Only the independently declared synthetic dependency graph below is exercised.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HEAD = "19e4e47d3f8fc02fb35d33399f7b052317896b62"
AXES = ["Q", "G", "V"]
REF_KEYS = {"id", "version", "sha256", "locator"}
METHOD_FIELDS = ("method_ref", "method_version_ref", "input_contract_ref")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def require(ok, code):
    if not ok:
        raise ScopeError(code)


class ScopeError(ValueError):
    pass


class Probe:
    def __init__(self, receipt_path, semantic_dir):
        self.receipt_path = receipt_path.resolve()
        self.receipt_bytes = self.receipt_path.read_bytes()
        self.receipt = json.loads(self.receipt_bytes)
        require(self.receipt["head"] == HEAD, "AUTHENTICATED_REVIEW_HEAD_MISMATCH")
        self.pins = copy.deepcopy(self.receipt["artifacts"])
        for remote, pin in self.pins.items():
            relative = pin["semantic_relative_path"]
            require(relative == remote.split("/lanes/semantic/", 1)[1] and ".." not in Path(relative).parts and not Path(relative).is_absolute(), "SEMANTIC_RELATIVE_PIN_PATH_DRIFT")
            pin["local_path"] = str(semantic_dir.resolve() / relative)
        require(len(self.pins) == 29 and all(p["verified"] is True for p in self.pins.values()), "FROZEN_INPUT_RECEIPT_INCOMPLETE")
        self.freeze()
        module_path = self.path("consumer/contract_acceptance_probe.py")
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("frozen_C_scope_checker", module_path)
        self.C = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.C)
        self.base = self.read("consumer/synthetic_carrier.json")
        self.registry = {(x["ref"]["id"], x["ref"]["version"]): x for x in self.read("consumer/synthetic_reference_contents.json")}
        self.matrix = self.read("g/G_CANDIDATE_MATRIX.json")
        self.requests = self.read("g/G_CANDIDATE_SOURCE_REQUESTS.json")
        self.diagnostics = self.read("g/G_CANDIDATE_DIAGNOSTICS.json")
        self.context = copy.deepcopy(self.base["context"])
        self.attachments = {
            "C_contract": self.attachment("consumer/CONTRACT.md", None, "INACTIVE_REFERENCE_CONTRACT"),
            "C_carrier": self.attachment("consumer/synthetic_carrier.json", "", "SYNTHETIC_TEMPLATE_ONLY"),
            "C_references": self.attachment("consumer/synthetic_reference_contents.json", "", "SYNTHETIC_REFERENCE_TEMPLATE_ONLY"),
            "G_matrix": self.attachment("g/G_CANDIDATE_MATRIX.json", "/candidates", "UNSELECTED_CANDIDATE_DESCRIPTORS"),
            "G_requests": self.attachment("g/G_CANDIDATE_SOURCE_REQUESTS.json", "/requests", "UNRESOLVED_DATA_AND_AUTHORITY_REQUESTS"),
            "G_diagnostics": self.attachment("g/G_CANDIDATE_DIAGNOSTICS.json", "/PIT_vintage_cases", "SYNTHETIC_DIAGNOSTICS_ONLY"),
            "G_semantics": self.attachment("root/SEMANTIC_CONTRACT.md", None, "APPROVED_MEANING_ONLY_METHODS_INACTIVE"),
        }
        self.axis_attachments = {
            "Q": [self.attachments[k] for k in ("C_contract", "C_carrier", "C_references")],
            "G": [self.attachments[k] for k in ("C_contract", "G_matrix", "G_requests", "G_diagnostics", "G_semantics")],
            "V": [self.attachments[k] for k in ("C_contract", "C_carrier", "C_references")],
        }
        # G here is a representative G2 child, not an assessment of all G.
        # All eight G1/G2 candidate descriptors remain independent attachments.
        self.factor_scopes = {"Q": ["FIXTURE_ONLY_Q_FACTOR"], "G": ["eps_fcf_per_share_growth"], "V": ["FIXTURE_ONLY_V_FACTOR"]}
        self.rows = [
            {"dependency_id": "FIXTURE_SHARED_CONTEXT", "scope_class": "SHARED", "affected_axes": AXES, "role": "Synthetic common subject/context only"},
            {"dependency_id": "FIXTURE_SHARED_QG_PIT", "scope_class": "SHARED", "affected_axes": ["Q", "G"], "role": "Declared synthetic shared fundamental-vintage obligation; no actual Q/G data equivalence claimed"},
            {"dependency_id": "FIXTURE_Q_LOCAL_INPUT", "scope_class": "LOCAL", "affected_axes": ["Q"], "role": "Synthetic Q evidence obligation only"},
            {"dependency_id": "FIXTURE_G_LOCAL_METHOD", "scope_class": "LOCAL", "affected_axes": ["G"], "role": "Local legacy G2 mismatch; candidate methods remain unselected"},
            {"dependency_id": "FIXTURE_V_LOCAL_SOURCE", "scope_class": "LOCAL", "affected_axes": ["V"], "role": "Synthetic V source obligation only; no actual V quote supplied"},
        ]
        for row in self.rows:
            row["affected_factor_ids"] = {axis: self.factor_scopes[axis] for axis in row["affected_axes"]}
        self.declaration = {
            "kind": "inactive_dependency_declaration", "context": self.context,
            "axes": AXES, "rows": self.rows, "runtime_enabled": False,
            "declaration_status": "SYNTHETIC_SCOPE_FIXTURE_ONLY",
            "authority_claim": "No production dependency inventory or cross-axis equivalence established",
            "evidence_attachments": list(self.attachments.values()),
        }
        self.declaration_ref = self.add("declaration", self.declaration)
        self.candidate_refs = []
        for i, candidate in enumerate(self.matrix["candidates"]):
            self.candidate_refs.append(self.add("candidate_" + candidate["candidate_id"], {
                "kind": "g_candidate_evidence", "candidate_id": candidate["candidate_id"],
                "factor_id": candidate["factor_id"], "method_id": candidate["method_id"],
                "method_version": candidate["method_version"], "method_equation": candidate["method_equation"],
                "outputs": candidate["outputs"], "disposition": "UNASSESSED",
                "runtime_enabled": False, "production_eligibility": candidate["production_eligibility"],
                "descriptor_attachment": self.attachment("g/G_CANDIDATE_MATRIX.json", f"/candidates/{i}", "CANDIDATE_EVIDENCE_NOT_ASSESSMENT"),
                "source_requests_attachment": self.attachments["G_requests"],
            }))
        # These original markers are supplied fixture reasons, not a PIT or
        # method-admission rubric. They reference exact existing evidence.
        self.events = {
            "LOCAL_G_METHOD_MISMATCH": {
                "kind": "inactive_rejection_reason", "event_id": "LOCAL_G_METHOD_MISMATCH",
                "dependency_id": "FIXTURE_G_LOCAL_METHOD", "assessment": "scoring_validity",
                "affected_axes": ["G"], "disposition": "REJECTED", "reason_code": "METHOD_MISMATCH",
                "original_reason": "Legacy G2 FCF / prior revenue - 1 is LEGACY / METHOD_MISMATCH; supplied local diagnostic reason, no candidate admission",
                "evidence_attachment": self.attachments["G_semantics"], "genuine_data_evaluated": False,
            },
            "SHARED_QG_PIT_REJECTION": {
                "kind": "inactive_rejection_reason", "event_id": "SHARED_QG_PIT_REJECTION",
                "dependency_id": "FIXTURE_SHARED_QG_PIT", "assessment": "pit",
                "affected_axes": ["Q", "G"], "disposition": "REJECTED", "reason_code": "SYNTHETIC_PIT_REJECTION",
                "original_reason": "Supplied synthetic shared PIT rejection: future_published marker retained; genuine archived source vintage remains unavailable",
                "evidence_attachment": self.attachment("g/G_CANDIDATE_DIAGNOSTICS.json", "/PIT_vintage_cases/2", "ORIGINAL_SYNTHETIC_FUTURE_PUBLISHED_CASE"),
                "genuine_data_evaluated": False,
            },
            "LOCAL_V_SOURCE_REJECTION": {
                "kind": "inactive_rejection_reason", "event_id": "LOCAL_V_SOURCE_REJECTION",
                "dependency_id": "FIXTURE_V_LOCAL_SOURCE", "assessment": "provenance",
                "affected_axes": ["V"], "disposition": "REJECTED", "reason_code": "SYNTHETIC_LOCAL_SOURCE_REJECTION",
                "original_reason": "Supplied synthetic V-local source rejection; no real V source or producer assessed",
                "evidence_attachment": self.attachments["C_references"], "genuine_data_evaluated": False,
            },
        }
        for event in self.events.values():
            event["affected_factor_ids"] = {axis: self.factor_scopes[axis] for axis in event["affected_axes"]}
        self.scenarios = {
            "LOCAL_G": ["LOCAL_G_METHOD_MISMATCH"],
            "SHARED_QG": ["SHARED_QG_PIT_REJECTION"],
            "COMBINED": ["LOCAL_G_METHOD_MISMATCH", "SHARED_QG_PIT_REJECTION"],
            "LOCAL_V": ["LOCAL_V_SOURCE_REJECTION"],
        }
        self.fixtures = {name: self.make_fixture(name, ids) for name, ids in self.scenarios.items()}

    def remote_path(self, suffix):
        paths = [path for path in self.pins if path.endswith("/" + suffix)]
        require(len(paths) == 1, "INPUT_PIN_SELECTION_AMBIGUOUS")
        return paths[0]

    def path(self, suffix):
        return Path(self.pins[self.remote_path(suffix)]["local_path"])

    def read(self, suffix):
        return json.loads(self.path(suffix).read_bytes())

    def freeze(self):
        require(self.receipt_path.read_bytes() == self.receipt_bytes, "INPUT_RECEIPT_DRIFT")
        for remote, pin in self.pins.items():
            require(hashlib.sha256(Path(pin["local_path"]).read_bytes()).hexdigest() == pin["sha256"], "FROZEN_INPUT_DRIFT:" + remote)

    def attachment(self, suffix, pointer, role):
        remote = self.remote_path(suffix)
        return {"artifact_ref": {"id": "REVIEW_ARTIFACT:" + remote, "version": HEAD,
                "sha256": self.pins[remote]["sha256"], "locator": "review://" + HEAD + "/" + remote},
                "json_pointer": pointer, "role": role, "genuine_raw_data_claim": False}

    def validate_attachment(self, attachment):
        require(set(attachment) == {"artifact_ref", "json_pointer", "role", "genuine_raw_data_claim"}, "EVIDENCE_ATTACHMENT_SHAPE")
        ref = attachment["artifact_ref"]
        require(isinstance(ref, dict) and set(ref) == REF_KEYS, "EVIDENCE_ATTACHMENT_REFERENCE_SHAPE")
        require(ref["id"].startswith("REVIEW_ARTIFACT:"), "EVIDENCE_ATTACHMENT_REFERENCE_MEANING")
        remote = ref["id"].removeprefix("REVIEW_ARTIFACT:")
        require(remote in self.pins, "EVIDENCE_ATTACHMENT_UNPINNED")
        expected = {"id": ref["id"], "version": HEAD, "sha256": self.pins[remote]["sha256"], "locator": "review://" + HEAD + "/" + remote}
        require(ref == expected, "EVIDENCE_ATTACHMENT_PIN_DRIFT")
        require(attachment["genuine_raw_data_claim"] is False, "ARTIFACT_ATTACHMENT_IS_NOT_RAW_INPUT")
        path = Path(self.pins[remote]["local_path"])
        require(hashlib.sha256(path.read_bytes()).hexdigest() == ref["sha256"], "EVIDENCE_ATTACHMENT_SOURCE_DRIFT")
        if attachment["json_pointer"] is not None:
            value = json.loads(path.read_bytes())
            pointer = attachment["json_pointer"]
            require(pointer == "" or pointer.startswith("/"), "EVIDENCE_ATTACHMENT_SELECTOR_INVALID")
            try:
                for token in pointer.split("/")[1:]:
                    token = token.replace("~1", "/").replace("~0", "~")
                    value = value[int(token)] if isinstance(value, list) else value[token]
            except (KeyError, IndexError, ValueError, TypeError):
                raise ScopeError("EVIDENCE_ATTACHMENT_SELECTOR_UNRESOLVED")
            return value

    def add(self, name, body):
        ref = {"id": "FIXTURE_SCOPE_" + name, "version": "inactive-fixture-v1", "sha256": digest(body), "locator": "fixture://dependency-scope/" + name}
        key = (ref["id"], ref["version"])
        require(key not in self.registry, "FIXTURE_REFERENCE_COLLISION")
        self.registry[key] = {"ref": ref, "body": copy.deepcopy(body)}
        return ref

    def resolve(self, ref, registry):
        require(isinstance(ref, dict) and set(ref) == REF_KEYS, "SCOPE_REFERENCE_SHAPE")
        entry = registry.get((ref["id"], ref["version"]))
        require(entry is not None, "SCOPE_REFERENCE_UNRESOLVED")
        require(ref == entry["ref"], "SCOPE_REFERENCE_PIN_DRIFT")
        require(digest(entry["body"]) == ref["sha256"], "REFERENCE_CONTENT_DRIFT")
        return entry["body"]

    def dependencies(self, axis):
        return [r["dependency_id"] for r in self.rows if axis in r["affected_axes"]]

    def make_fixture(self, name, event_ids):
        event_refs = [self.add(name + "_reason_" + event_id, self.events[event_id]) for event_id in event_ids]
        axis_reasons = {axis: [ref for ref, event_id in zip(event_refs, event_ids) if axis in self.events[event_id]["affected_axes"]] for axis in AXES}
        producers = {}
        for axis in AXES:
            prefix = name + "_" + axis + "_"
            factor_ids = self.factor_scopes[axis]
            bindings = []
            for factor_id in factor_ids:
                factor = self.add(prefix + factor_id, {"kind": "factor_identity", "factor_id": factor_id, "identity_claim": "Fixture reference only; no runtime factor registration"})
                method = version = inputs = None
                if axis != "G":
                    method = self.add(prefix + "method", {"kind": "method_identity", "factor_ref": factor, "source": "Synthetic frozen C-template adaptation only; no Q/V production method"})
                    version = self.add(prefix + "method_version", {"kind": "method_version", "method_ref": method})
                    inputs = self.add(prefix + "input_contract", {"kind": "input_contract", "method_ref": method, "periods": "UNASSESSED_SYNTHETIC_ONLY"})
                bindings.append({"factor_ref": factor, "method_ref": method, "method_version_ref": version, "input_contract_ref": inputs, "fallback_ref": None, "normalization_ref": None})
            scope = self.add(prefix + "scope", {
                "kind": "scope", "context": self.context, "axis": axis, "factor_ids": factor_ids,
                "input_ids": ["FIXTURE_ONLY_" + axis + "_INPUT"], "declaration_ref": self.declaration_ref,
                "dependency_ids": self.dependencies(axis),
                "shared_dependency_ids": [r["dependency_id"] for r in self.rows if r["scope_class"] == "SHARED" and axis in r["affected_axes"]],
                "local_dependency_ids": [r["dependency_id"] for r in self.rows if r["scope_class"] == "LOCAL" and axis in r["affected_axes"]],
            })
            source_body = copy.deepcopy(self.registry[(self.base["source_refs"][0]["id"], self.base["source_refs"][0]["version"])]["body"])
            source_body.update(evidence_attachments=self.axis_attachments[axis], g_candidate_evidence_refs=self.candidate_refs if axis == "G" else [], attachment_meaning="Exact artifact bytes only; not genuine raw values or genuine historical PIT proof")
            source = self.add(prefix + "source", source_body)
            result = self.add(prefix + "result", {"kind": "legacy_result", "context": self.context, "scope_ref": scope,
                "legacy_numeric": self.base["legacy_numeric"], "legacy_coverage_literal": self.base["legacy_coverage_literal"],
                "source_refs": [source], "numeric_meaning": "Frozen C synthetic literal, not an actual Q/G/V score"})
            assessments = {}
            for assessment in self.C.ASSESSMENTS:
                relevant = [self.events[e] for e in event_ids if axis in self.events[e]["affected_axes"] and self.events[e]["assessment"] == assessment]
                reason = " | ".join(e["original_reason"] for e in relevant) if relevant else "UNASSESSED synthetic fixture; actual method/admission authority unresolved"
                assessments[assessment] = self.add(prefix + assessment, {"kind": assessment, "context": self.context, "scope_ref": scope,
                    "producer_result_ref": result, "method_binding_refs": bindings, "source_refs": [source], "policy_ref": None,
                    "disposition": "REJECTED" if relevant else "UNASSESSED", "reason": reason,
                    "rejected_factor_ids": self.factor_scopes[axis] if relevant else []})
            carrier = copy.deepcopy(self.base)
            carrier.update(context=self.context, scope_ref=scope, producer_result_ref=result, method_binding_refs=bindings, source_refs=[source], assessments=assessments)
            carrier["aggregate"].update(scope_ref=scope, ordered_child_result_refs=[result], child_assessment_refs=[assessments])
            carrier["consumer"].update(id="FIXTURE_ONLY_" + axis + "_DIAGNOSTIC", scope_ref=scope, result_ref=result, producer_assessment_refs=assessments)
            if axis == "G":
                carrier["unassessed_reasons"].update({field: "G candidate methods unselected; no method/version/input contract registered" for field in METHOD_FIELDS})
            # No Python alias is relied upon for producer/aggregate/consumer equality.
            producers[axis] = json.loads(canonical(carrier))
        scope = self.add(name + "_composition_scope", {"kind": "inactive_composition_scope", "context": self.context,
            "ordered_axes": AXES, "child_scope_refs": [producers[a]["scope_ref"] for a in AXES], "declaration_ref": self.declaration_ref})
        results = [producers[a]["producer_result_ref"] for a in AXES]
        assessments = [producers[a]["assessments"] for a in AXES]
        return json.loads(canonical({
            "artifact_kind": "INACTIVE_G_C_DEPENDENCY_SCOPE_COMPOSITION", "version": "fixture-v1", "scenario": name,
            "runtime_enabled": False, "activation_requested": False, "context": self.context,
            "declaration_ref": self.declaration_ref, "scope_ref": scope, "event_refs": event_refs,
            "producers": producers, "producer_reason_refs": axis_reasons,
            "aggregate": {"scope_ref": scope, "ordered_child_result_refs": results, "child_assessment_refs": assessments,
                "child_reason_refs": axis_reasons, "reason_refs": event_refs, "withheld_child_result_refs": [], "planned_basis_ref": None, "arithmetic_ref": None},
            "consumer": {"id": "FIXTURE_ONLY_QGV_ANALYSIS", "version": "fixture-v1", "purpose": "DIAGNOSTIC", "namespace": self.context["namespace"],
                "scope_ref": scope, "result_refs": results, "producer_assessment_refs": assessments, "producer_reason_refs": axis_reasons,
                "policy_ref": None, "admission_decision_ref": None},
            "profile_overlay": {"kind": "INACTIVE_CONTRIBUTION_METADATA_ONLY", "profile_id": "FIXTURE_ONLY_BASE", "zero_contribution_axes": []},
            "publication_decision_ref": None,
        }))

    def validate(self, fixture, registry):
        require(set(fixture) == set(self.fixtures[fixture["scenario"]]), "COMPOSITION_SHAPE_NO_ELIGIBILITY_FLAG")
        require(fixture["runtime_enabled"] is False and fixture["activation_requested"] is False, "PRODUCTION_ACTIVATION_FORBIDDEN")
        require(fixture["artifact_kind"] == "INACTIVE_G_C_DEPENDENCY_SCOPE_COMPOSITION" and fixture["version"] == "fixture-v1", "INACTIVE_COMPOSITION_IDENTITY")
        require(fixture["context"] == self.context, "COMPOSITION_CONTEXT_DRIFT")
        declaration = self.resolve(fixture["declaration_ref"], registry)
        require(declaration == self.declaration, "DECLARED_DEPENDENCY_DRIFT")
        for attachment in declaration["evidence_attachments"]:
            self.validate_attachment(attachment)
        require(list(fixture["producers"]) == AXES or set(fixture["producers"]) == set(AXES), "QGV_PRODUCER_INVENTORY_DRIFT")
        events = [self.resolve(ref, registry) for ref in fixture["event_refs"]]
        require([e["event_id"] for e in events] == self.scenarios[fixture["scenario"]], "ORIGINAL_EVENT_INVENTORY_DROP_OR_EXPANSION")
        for event in events:
            row = next((r for r in self.rows if r["dependency_id"] == event["dependency_id"]), None)
            require(row is not None and event["affected_axes"] == row["affected_axes"] and event["affected_factor_ids"] == row["affected_factor_ids"], "EVENT_DEPENDENCY_RELEVANCE_DRIFT")
            require(event == self.events[event["event_id"]], "ORIGINAL_REJECTION_REASON_REWRITE")
            self.validate_attachment(event["evidence_attachment"])
        expected_reasons = {a: [ref for ref, e in zip(fixture["event_refs"], events) if a in e["affected_axes"]] for a in AXES}
        require(fixture["producer_reason_refs"] == expected_reasons, "PRODUCER_REASON_SCOPE_DRIFT")
        child_results, child_assessments = [], []
        for axis in AXES:
            carrier = fixture["producers"][axis]
            # Reuse the existing checker on each new affected composition child.
            outcome = self.C.validate(carrier, registry)
            require(outcome["semantic_validity"] == outcome["consumer_admission"] == "NOT_EVALUATED", "STRUCTURAL_ACCEPTANCE_PROMOTION")
            scope = self.resolve(carrier["scope_ref"], registry)
            require(scope["axis"] == axis and scope["declaration_ref"] == fixture["declaration_ref"], "AXIS_DECLARATION_BINDING_DRIFT")
            require(scope["dependency_ids"] == self.dependencies(axis), "DEPENDENCY_SCOPE_DROP_OR_EXPANSION")
            for scope_class, field in (("SHARED", "shared_dependency_ids"), ("LOCAL", "local_dependency_ids")):
                require(scope[field] == [r["dependency_id"] for r in self.rows if r["scope_class"] == scope_class and axis in r["affected_axes"]], "DEPENDENCY_CLASS_SCOPE_DRIFT")
            require(scope["input_ids"] == ["FIXTURE_ONLY_" + axis + "_INPUT"], "INPUT_SCOPE_DRIFT")
            source = self.resolve(carrier["source_refs"][0], registry)
            require(source["source_status"] == "SYNTHETIC_ONLY", "ARTIFACT_ATTACHMENT_IS_NOT_RAW_INPUT")
            for attachment in source["evidence_attachments"]:
                self.validate_attachment(attachment)
            require(source["evidence_attachments"] == self.axis_attachments[axis], "EVIDENCE_ATTACHMENT_SELECTOR_OR_CLOSURE_DRIFT")
            for name, ref in carrier["assessments"].items():
                body = self.resolve(ref, registry)
                relevant = [e for e in events if axis in e["affected_axes"] and e["assessment"] == name]
                expected_reason = " | ".join(e["original_reason"] for e in relevant) if relevant else "UNASSESSED synthetic fixture; actual method/admission authority unresolved"
                require(body["disposition"] == ("REJECTED" if relevant else "UNASSESSED"), "UNDECLARED_ASSESSMENT_REJECTION_OR_PROMOTION")
                require(body["reason"] == expected_reason, "ORIGINAL_ASSESSMENT_REASON_NOT_RETAINED")
                require(body["rejected_factor_ids"] == (self.factor_scopes[axis] if relevant else []), "LOCAL_FACTOR_REJECTION_SCOPE_EXPANSION")
            if axis == "G":
                require(scope["factor_ids"] == self.factor_scopes["G"], "G_FACTOR_IDENTITY_DRIFT")
                require(all(b[f] is None for b in carrier["method_binding_refs"] for f in METHOD_FIELDS), "G_METHOD_CALCULATION_NOT_AUTHORIZED")
                candidates = [self.resolve(ref, registry) for ref in source["g_candidate_evidence_refs"]]
                require([c["candidate_id"] for c in candidates] == [c["candidate_id"] for c in self.matrix["candidates"]], "G_CANDIDATE_INVENTORY_DRIFT")
                for i, candidate in enumerate(candidates):
                    require(candidate["disposition"] == "UNASSESSED", "G_CANDIDATE_EVIDENCE_PROMOTION")
                    require(candidate["method_id"] is candidate["method_version"] is None and candidate["method_equation"] == "UNKNOWN_UNSELECTED", "G_METHOD_CALCULATION_NOT_AUTHORIZED")
                    require(candidate["outputs"] == self.matrix["candidates"][i]["outputs"] and set(candidate["outputs"].values()) == {"UNCOMPUTED"}, "G_CANDIDATE_SCORE_NOT_UNCOMPUTED")
                    expected = self.registry[(self.candidate_refs[i]["id"], self.candidate_refs[i]["version"])]["body"]
                    require(candidate == expected, "G_CANDIDATE_DESCRIPTOR_BINDING_DRIFT")
                    require(self.validate_attachment(candidate["descriptor_attachment"]) == self.matrix["candidates"][i], "G_CANDIDATE_DESCRIPTOR_CONTENT_DRIFT")
                    self.validate_attachment(candidate["source_requests_attachment"])
            else:
                require(source["g_candidate_evidence_refs"] == [], "G_CANDIDATE_SCOPE_EXPANSION")
            child_results.append(carrier["producer_result_ref"])
            child_assessments.append(carrier["assessments"])
        scope = self.resolve(fixture["scope_ref"], registry)
        require(scope == {"kind": "inactive_composition_scope", "context": self.context, "ordered_axes": AXES,
            "child_scope_refs": [fixture["producers"][a]["scope_ref"] for a in AXES], "declaration_ref": fixture["declaration_ref"]}, "COMPOSITION_SCOPE_EXPANSION_OR_DROP")
        aggregate = fixture["aggregate"]
        require(set(aggregate) == set(self.fixtures[fixture["scenario"]]["aggregate"]) and aggregate["scope_ref"] == fixture["scope_ref"], "AGGREGATE_SCOPE_DRIFT")
        require(aggregate["ordered_child_result_refs"] == child_results and aggregate["child_assessment_refs"] == child_assessments, "AGGREGATE_CHILD_REFERENCE_DROP_OR_EXPANSION")
        require(aggregate["child_reason_refs"] == expected_reasons and aggregate["reason_refs"] == fixture["event_refs"], "AGGREGATE_REASON_CARRIAGE_DROP_OR_EXPANSION")
        require(aggregate["withheld_child_result_refs"] == [] and aggregate["planned_basis_ref"] is aggregate["arithmetic_ref"] is None, "UNAUTHORIZED_ARITHMETIC_OR_WITHHOLDING_POLICY")
        consumer = fixture["consumer"]
        require(set(consumer) == set(self.fixtures[fixture["scenario"]]["consumer"]), "COMPOSITION_CONSUMER_SHAPE")
        require(consumer["id"] == "FIXTURE_ONLY_QGV_ANALYSIS" and consumer["version"] == "fixture-v1" and consumer["purpose"] == "DIAGNOSTIC", "INACTIVE_COMPOSITION_CONSUMER_PROMOTION")
        require(consumer["namespace"] == self.context["namespace"] and consumer["scope_ref"] == fixture["scope_ref"], "CONSUMER_CONTEXT_OR_SCOPE_DRIFT")
        require(consumer["result_refs"] == child_results and consumer["producer_assessment_refs"] == child_assessments, "CONSUMER_CHILD_REFERENCE_DROP_OR_EXPANSION")
        require(consumer["producer_reason_refs"] == expected_reasons, "CONSUMER_REASON_CARRIAGE_DROP_OR_EXPANSION")
        require(consumer["policy_ref"] is consumer["admission_decision_ref"] is fixture["publication_decision_ref"] is None, "UNAPPROVED_CONSUMER_ACTIVATION")
        overlay = fixture["profile_overlay"]
        require(set(overlay) == {"kind", "profile_id", "zero_contribution_axes"} and overlay["kind"] == "INACTIVE_CONTRIBUTION_METADATA_ONLY" and isinstance(overlay["profile_id"], str) and bool(overlay["profile_id"].strip()) and set(overlay["zero_contribution_axes"]) <= set(AXES), "PROFILE_OVERLAY_SHAPE")
        return {"structural_acceptance": "PASS_STRUCTURAL_ONLY", "semantic_validity": "NOT_EVALUATED", "consumer_admission": "NOT_EVALUATED", "runtime_enabled": False,
            "reason_scope": {e["reason_code"]: e["affected_axes"] for e in events},
            "reason_factor_scope": {e["reason_code"]: e["affected_factor_ids"] for e in events},
            "unrelated_axes_without_rejection": [a for a in AXES if not expected_reasons[a]],
            "g_candidate_disposition": "UNASSESSED", "candidate_scores": "UNCOMPUTED"}

    def overlay_guard(self, base, overlay):
        # Imported compatibility rule; no numeric contribution is calculated.
        for axis in AXES:
            self.C.preserve_zero_profile_authority(base["producers"][axis], overlay["producers"][axis])
        for field in ("declaration_ref", "scope_ref", "event_refs", "producer_reason_refs", "aggregate", "consumer", "context"):
            require(base[field] == overlay[field], "ZERO_OR_PROFILE_DEPENDENCY_WAIVER")


def repin(fixture, registry, ref, change):
    """Coherently rehash a malformed case and every dependent reference.

    This makes relational negatives stronger than an accidental stale-hash fail.
    The independently declared relevance/attachment pins remain the expectation.
    """
    body = copy.deepcopy(registry[(ref["id"], ref["version"])]["body"])
    change(body)
    replacement = {**ref, "version": "coherent-mutation-v1", "sha256": digest(body)}
    registry[(replacement["id"], replacement["version"])] = {"ref": replacement, "body": body}
    cache = {(ref["id"], ref["version"]): replacement}

    def walk(value):
        if isinstance(value, list):
            return [walk(v) for v in value]
        if not isinstance(value, dict):
            return value
        if set(value) == REF_KEYS and (value["id"], value["version"]) in registry:
            key = (value["id"], value["version"])
            if key in cache:
                return cache[key]
            old_body = registry[key]["body"]
            new_body = walk(old_body)
            new_ref = value
            if new_body != old_body:
                new_ref = {**value, "version": "coherent-mutation-v1", "sha256": digest(new_body)}
                registry[(new_ref["id"], new_ref["version"])] = {"ref": new_ref, "body": new_body}
            cache[key] = new_ref
            return new_ref
        return {key: walk(v) for key, v in value.items()}
    updated = walk(fixture)
    fixture.clear()
    fixture.update(updated)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--semantic-dir", type=Path, required=True)
    parser.add_argument("--pin-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    attempt = len(list(args.output_dir.glob("ATTEMPT_*_RESULTS.json"))) + 1
    result = {"attempt": attempt, "review_head": HEAD, "validation_level": "STANDARD",
        "check_scope": "Targeted compatibility, negative, and affected composition fixtures only", "cases": []}
    try:
        probe = Probe(args.pin_manifest, args.semantic_dir)

        def run(name, scenario="COMBINED", mutate=None, expected="PASS_STRUCTURAL_ONLY", action=None, overlay=False):
            fixture = json.loads(canonical(probe.fixtures[scenario]))
            registry = copy.deepcopy(probe.registry)
            observations = {}
            try:
                if mutate:
                    mutate(fixture, registry)
                if overlay:
                    probe.overlay_guard(probe.fixtures[scenario], fixture)
                observations = action(fixture, registry) if action else probe.validate(fixture, registry)
                actual = "PASS_STRUCTURAL_ONLY"
            except (ScopeError, probe.C.CarrierError) as exc:
                actual = str(exc)
            passed = actual == expected
            result["cases"].append({"case": name, "expected": expected, "actual": actual, "pass": passed, "observations": observations})

        def scope_mutate(axis, change):
            return lambda f, r: repin(f, r, f["producers"][axis]["scope_ref"], change)

        def source_mutate(axis, change):
            return lambda f, r: repin(f, r, f["producers"][axis]["source_refs"][0], change)

        def candidate_mutate(change):
            def mutate(f, r):
                source = probe.resolve(f["producers"]["G"]["source_refs"][0], r)
                repin(f, r, source["g_candidate_evidence_refs"][0], change)
            return mutate

        def assessment_mutate(axis, name, change):
            return lambda f, r: repin(f, r, f["producers"][axis]["assessments"][name], change)

        run("S01_frozen_29_inputs_unchanged", action=lambda f, r: (probe.freeze() or {"pins_verified": 29, "prior_checks_rerun": 0}))
        run("S02_imported_C_frozen_template_compatibility", action=lambda f, r: probe.C.validate(probe.base, probe.registry))
        run("S03_local_G_mismatch_only_G", scenario="LOCAL_G")
        run("S04_shared_QG_PIT_excludes_V", scenario="SHARED_QG")
        run("S05_combined_G_retains_local_and_shared_reasons")
        run("S06_local_V_source_excludes_QG", scenario="LOCAL_V")
        run("S07_coherent_dependency_drop", mutate=scope_mutate("G", lambda b: b["dependency_ids"].remove("FIXTURE_SHARED_QG_PIT")), expected="DEPENDENCY_SCOPE_DROP_OR_EXPANSION")
        run("S08_coherent_dependency_expansion_to_V", mutate=scope_mutate("V", lambda b: b["dependency_ids"].append("FIXTURE_SHARED_QG_PIT")), expected="DEPENDENCY_SCOPE_DROP_OR_EXPANSION")
        run("S09_source_content_drift", mutate=lambda f, r: r[(f["producers"]["G"]["source_refs"][0]["id"], f["producers"]["G"]["source_refs"][0]["version"])]["body"].update(source_status="DRIFTED"), expected="REFERENCE_CONTENT_DRIFT")
        run("S10_coherent_artifact_hash_drift", mutate=source_mutate("G", lambda b: b["evidence_attachments"][1]["artifact_ref"].update(sha256="0" * 64)), expected="EVIDENCE_ATTACHMENT_PIN_DRIFT")
        run("S11_coherent_source_request_selector_drift", mutate=source_mutate("G", lambda b: b["evidence_attachments"][2].update(json_pointer="/requests/0")), expected="EVIDENCE_ATTACHMENT_SELECTOR_OR_CLOSURE_DRIFT")
        run("S12_aggregate_cannot_drop_local_reason", mutate=lambda f, r: f["aggregate"]["child_reason_refs"]["G"].pop(0), expected="AGGREGATE_REASON_CARRIAGE_DROP_OR_EXPANSION")
        run("S13_consumer_cannot_drop_shared_Q_reason", mutate=lambda f, r: f["consumer"]["producer_reason_refs"]["Q"].clear(), expected="CONSUMER_REASON_CARRIAGE_DROP_OR_EXPANSION")
        run("S14_local_G_reason_cannot_expand_to_Q", scenario="LOCAL_G", mutate=lambda f, r: f["producer_reason_refs"]["Q"].append(f["event_refs"][0]), expected="PRODUCER_REASON_SCOPE_DRIFT")
        run("S15_shared_QG_reason_cannot_drop_Q", scenario="SHARED_QG", mutate=lambda f, r: f["producer_reason_refs"]["Q"].clear(), expected="PRODUCER_REASON_SCOPE_DRIFT")
        run("S16_no_blanket_V_PIT_rejection", scenario="SHARED_QG", mutate=assessment_mutate("V", "pit", lambda b: b.update(disposition="REJECTED", reason="Blanket shared rejection")), expected="UNDECLARED_ASSESSMENT_REJECTION_OR_PROMOTION")
        run("S17_zero_profile_preserves_obligations", mutate=lambda f, r: f["profile_overlay"].update(profile_id="FIXTURE_ONLY_CUSTOM_ZERO", zero_contribution_axes=["G"]), overlay=True)
        run("S18_zero_profile_cannot_drop_G_PIT_ref", mutate=lambda f, r: f["producers"]["G"]["assessments"].update(pit=None), expected="ZERO_OR_PROFILE_SEMANTIC_WAIVER", overlay=True)
        run("S19_custom_profile_cannot_replace_method", mutate=lambda f, r: f["producers"]["G"]["method_binding_refs"][0].update(method_ref=f["producers"]["G"]["method_binding_refs"][0]["factor_ref"]), expected="ZERO_OR_PROFILE_SEMANTIC_WAIVER", overlay=True)
        run("S20_zero_profile_cannot_rewrite_dependency_scope", mutate=scope_mutate("G", lambda b: b["dependency_ids"].remove("FIXTURE_G_LOCAL_METHOD")), expected="ZERO_OR_PROFILE_SEMANTIC_WAIVER", overlay=True)
        run("S21_candidate_evidence_cannot_be_admitted", mutate=candidate_mutate(lambda b: b.update(disposition="ADMITTED")), expected="G_CANDIDATE_EVIDENCE_PROMOTION")
        run("S22_candidate_method_cannot_be_invented", mutate=candidate_mutate(lambda b: b.update(method_id="INVENTED_METHOD")), expected="G_METHOD_CALCULATION_NOT_AUTHORIZED")
        run("S23_candidate_score_must_remain_UNCOMPUTED", mutate=candidate_mutate(lambda b: b["outputs"].update(candidate_factor_score=70)), expected="G_CANDIDATE_SCORE_NOT_UNCOMPUTED")
        run("S24_structural_acceptance_never_promotes_ranking", mutate=lambda f, r: f["consumer"].update(purpose="RANKING"), expected="INACTIVE_COMPOSITION_CONSUMER_PROMOTION")
        run("S25_activation_forbidden", mutate=lambda f, r: f.update(runtime_enabled=True), expected="PRODUCTION_ACTIVATION_FORBIDDEN")
        run("S26_consumer_cannot_expand_result_inventory", mutate=lambda f, r: f["consumer"]["result_refs"].append(f["consumer"]["result_refs"][0]), expected="CONSUMER_CHILD_REFERENCE_DROP_OR_EXPANSION")
        run("S27_aggregate_cannot_drop_assessments", mutate=lambda f, r: f["aggregate"]["child_assessment_refs"].pop(), expected="AGGREGATE_CHILD_REFERENCE_DROP_OR_EXPANSION")
        run("S28_original_rejection_not_ordinary_unknown", mutate=assessment_mutate("G", "scoring_validity", lambda b: b.update(reason="Ordinary missing data")), expected="ORIGINAL_ASSESSMENT_REASON_NOT_RETAINED")
        run("S29_coherent_event_scope_cannot_expand", scenario="LOCAL_G", mutate=lambda f, r: repin(f, r, f["event_refs"][0], lambda b: b.update(affected_axes=AXES)), expected="EVENT_DEPENDENCY_RELEVANCE_DRIFT")

        def unresolved_data(f, r):
            request = probe.requests["requests"][0]
            require(request["request_id"] == "DATA-G-01" and request["known_available"]["blob_exists"] is False and request["known_available"]["status"] == "NOT_RUN_SOURCE_BLOB_ABSENT", "GENUINE_ARCHIVED_DATA_REQUEST_NOT_PRESERVED")
            return {"request_id": request["request_id"], "genuine_source_bytes": "ABSENT", "recorded_blob_sha256": request["known_available"]["recorded_blob_sha256"], "restoration_or_refetch_executed": False, "candidate_calculation": "UNCOMPUTED", "real_PIT_OOS": "NOT_RUN"}
        run("S30_genuine_source_request_remains_unresolved", action=unresolved_data)
        probe.freeze()
        pins = {"review_head": HEAD, "pin_manifest_sha256": hashlib.sha256(probe.receipt_bytes).hexdigest(),
            "authenticated_intake_receipt_sha256": probe.receipt["authenticated_intake_receipt_sha256"],
            "input_artifact_count": 29, "prior_checks_consumed_unchanged": {"G": 21, "C": 38},
            "artifacts": {path: {k: p[k] for k in ("semantic_relative_path", "git_blob_sha", "size", "sha256", "verified")} for path, p in probe.pins.items()},
            "external_artifact_attachment_meaning": "Authenticated file bytes only; genuine raw source data and historical PIT unproven"}
        registry = list(probe.registry.values())
        full_fixture_bundle = {"fixtures": probe.fixtures, "limits": "Finite synthetic declaration; no production dependency inventory, scoring or admission"}
        compact_spec = {
            "artifact_kind": "FINITE_INACTIVE_SCOPE_FIXTURE_SPEC", "runtime_enabled": False,
            "frozen_C_template_attachment": probe.attachments["C_carrier"],
            "frozen_C_reference_attachment": probe.attachments["C_references"],
            "declaration": probe.declaration, "axis_factor_scopes": probe.factor_scopes,
            "scenario_event_ids": probe.scenarios, "original_reason_cases": probe.events,
            "g_candidate_evidence": [probe.registry[(ref["id"], ref["version"])]["body"] for ref in probe.candidate_refs],
            "materialization": "The pinned probe deterministically regenerates the complete reference DAG and producer/aggregate/consumer carriers in memory; full repeated JSON is not published",
            "limits": "G representative child is G2 only; G1 descriptors remain UNASSESSED evidence. Q/V scopes are synthetic, not actual production factor inventories. No scoring or admission.",
        }
        digests = {"artifact_kind": "INACTIVE_GENERATED_SCOPE_FIXTURE_DIGESTS", "review_head": HEAD,
            "fixture_count": len(probe.fixtures), "fixture_canonical_sha256": {name: digest(fixture) for name, fixture in probe.fixtures.items()},
            "full_fixture_bundle_canonical_sha256": digest(full_fixture_bundle),
            "reference_contents_canonical_sha256": digest(registry), "reference_document_count": len(registry),
            "canonical_encoding": "JSON sort_keys=true, separators=(',',':'), ensure_ascii=false, allow_nan=false; UTF-8",
            "genuine_raw_inputs_materialized": False,
        }
        artifacts = {"INPUT_PINS.json": pins, "SCOPE_FIXTURE_SPEC.json": compact_spec, "SCOPE_FIXTURE_DIGESTS.json": digests}
        result.update(input_pins_verified_before_and_after=29, initial_failures_preserved=True,
            prior_59_checks_rerun=False, production_semantics_changed=False, runtime_enabled=False,
            candidate_scoring_executed=False, consumer_policy_activated=False, scheduler_hops_added=0,
            real_PIT_OOS="NOT_RUN", method_selection="NOT_APPROVED", fixture_count=4,
            g_candidates="8 exact descriptor attachments; UNASSESSED / UNCOMPUTED",
            checks_executed=len(result["cases"]), checks_passed=sum(c["pass"] for c in result["cases"]), checks_failed=sum(not c["pass"] for c in result["cases"]),
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            fixture_canonical_sha256=digest(full_fixture_bundle), reference_contents_canonical_sha256=digest(registry),
            remaining_D3=["Exact G1/G2 method/input/window/domain/normalization and selected branch", "B2/B3/B5/B6 actual criteria, consumer purpose/policy and migration/activation authority", "B1 real requirements and V1/V2 pending methodology"],
            remaining_data=[r["request_id"] for r in probe.requests["requests"]],
            limits="Only finite producer/aggregate/consumer carriage and exact declared relevance. Q/V scaffolding is synthetic. Actual artifact attachments are not genuine inputs; no general aggregate or failure evaluator, JSONSchema engine, runtime producer, WeightOverride wiring, PIT replay, admission rubric, cutoff, formula or ranking path.")
        result["status"] = "PASS_INACTIVE_BOUNDED_SCOPE_FIXTURES" if result["checks_failed"] == 0 else "FAIL_INACTIVE_BOUNDED_SCOPE_FIXTURES"
        result["artifact_sha256"] = {}
        for name, body in artifacts.items():
            raw = (json.dumps(body, indent=2, ensure_ascii=False) + "\n").encode()
            (args.output_dir / name).write_bytes(raw)
            result["artifact_sha256"][name] = hashlib.sha256(raw).hexdigest()
    except Exception as exc:
        result.update(status="FAIL_INACTIVE_BOUNDED_SCOPE_FIXTURES", setup_or_execution_error=f"{type(exc).__name__}: {exc}", checks_executed=len(result["cases"]), checks_passed=sum(c["pass"] for c in result["cases"]), checks_failed=sum(not c["pass"] for c in result["cases"]) + 1)
    result["executed_command"] = "python " + " ".join(sys.argv)
    raw = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    (args.output_dir / f"ATTEMPT_{attempt:02d}_RESULTS.json").write_text(raw)
    (args.output_dir / "SCOPE_VERIFICATION.json").write_text(raw)
    print(json.dumps({k: result.get(k) for k in ("status", "attempt", "checks_executed", "checks_passed", "checks_failed", "setup_or_execution_error")}))
    raise SystemExit(0 if result["status"] == "PASS_INACTIVE_BOUNDED_SCOPE_FIXTURES" else 1)


if __name__ == "__main__":
    main()
