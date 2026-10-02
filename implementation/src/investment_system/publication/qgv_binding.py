"""QGV company composite subject. RESEARCH_SUBJECT_BINDING_V1.

Copies persisted QGV fields and binds one invalidation event.
Does not recompute Q, G, V, rank, a peer median, or a cross-section.
Does not issue a research-display, Frozen, or Live grant.
"""

from __future__ import annotations

import re
from datetime import datetime

from ..producers.serialization import canonical_sha256
from .invalidation import event_id, resolve_target, validate_event

BINDING_CONTRACT = "RESEARCH_SUBJECT_BINDING_V1"
BINDING_SCHEMA = 1
PRODUCER_ID = "qgv.real_research_producer"
RECORD_KIND = "QGV_COMPANY_RESULT"
MANIFEST_KIND = "QGV_PRODUCER_BATCH_MANIFEST"
COMPONENT_FIELDS = (
    "persisted_output_sha256",
    "inputs_sha256",
    "members_sha256",
    "weights_sha256",
)
PROVENANCE_KEYS = (
    "producer_id",
    "qgv_system_version",
    "qgv_standard_version",
    "qgv_analysis_contract",
    "implementation_line",
    "weights_sha256",
    "code_commit",
    "as_of",
    "company_id",
    "persisted_output_sha256",
    "universe_id",
    "members_sha256",
    "inputs_sha256",
    "cross_section_rule_id",
    "cross_section_rule_status",
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_METHODOLOGY = (
    "qgv_system_version",
    "qgv_standard_version",
    "qgv_analysis_contract",
    "implementation_line",
    "weights_sha256",
    "cross_section_rule_id",
    "cross_section_rule_status",
)


class BindingContractError(ValueError):
    code = "BINDING_CONTRACT"

    def __init__(self, message: str):
        super().__init__(f"{self.code}: {message}")


def provenance_from_persisted(company: dict, manifest: dict) -> dict:
    """Copy the approved constituents. Operational noise is not copied."""
    _require_documents(company, manifest)
    semantic = _mapping(company.get("semantic"), "company semantic")
    manifest_semantic = _mapping(manifest.get("semantic"), "manifest semantic")
    if canonical_sha256(semantic) != company.get("semantic_sha256"):
        raise BindingContractError("company semantic_sha256 does not match persisted semantic bytes")
    if canonical_sha256(manifest_semantic) != manifest.get("semantic_sha256"):
        raise BindingContractError("manifest semantic_sha256 does not match persisted semantic bytes")
    methodology = _mapping(manifest_semantic.get("methodology"), "manifest methodology")
    company_methodology = _mapping(semantic.get("methodology"), "company methodology")
    for key in _METHODOLOGY:
        if key not in methodology or company_methodology.get(key) != methodology.get(key):
            raise BindingContractError(f"company methodology {key} does not match the manifest")
    universe = _mapping(manifest_semantic.get("universe"), "manifest universe")
    company_universe = _mapping(semantic.get("universe"), "company universe")
    if semantic.get("as_of") != manifest_semantic.get("as_of"):
        raise BindingContractError("company as_of does not match the manifest")
    if company_universe.get("universe_id") != universe.get("universe_id"):
        raise BindingContractError("company universe_id does not match the manifest")
    company_id = semantic.get("company_id")
    output = company.get("semantic_sha256")
    records = manifest_semantic.get("records")
    if not isinstance(records, list):
        raise BindingContractError("manifest records are missing")
    rows = [row for row in records if isinstance(row, dict) and row.get("company_id") == company_id]
    if len(rows) != 1 or rows[0].get("semantic_sha256") != output:
        raise BindingContractError("manifest records do not name this company output exactly once")
    lineage = _mapping(manifest_semantic.get("data_lineage"), "data lineage")
    provenance = {
        "producer_id": PRODUCER_ID,
        "qgv_system_version": methodology["qgv_system_version"],
        "qgv_standard_version": methodology["qgv_standard_version"],
        "qgv_analysis_contract": methodology["qgv_analysis_contract"],
        "implementation_line": methodology["implementation_line"],
        "weights_sha256": methodology["weights_sha256"],
        "code_commit": manifest["operational"]["code_commit"],
        "as_of": semantic["as_of"],
        "company_id": company_id,
        "persisted_output_sha256": output,
        "universe_id": universe["universe_id"],
        "members_sha256": universe["members_sha256"],
        "inputs_sha256": lineage["inputs_sha256"],
        "cross_section_rule_id": methodology["cross_section_rule_id"],
        "cross_section_rule_status": methodology["cross_section_rule_status"],
    }
    _validate_provenance(provenance)
    return provenance


def provenance_sha256(provenance: dict) -> str:
    _validate_provenance(provenance)
    return canonical_sha256(provenance)


def build_binding(company: dict, manifest: dict, event: dict) -> dict:
    """Bind one explicit event. Does not choose a chain head and does not grant."""
    provenance = provenance_from_persisted(company, manifest)
    body = validate_event(event)
    target = provenance_sha256(provenance)
    if body["target_sha256"] != target:
        raise BindingContractError("event target is not this provenance hash")
    binding = {
        "contract": BINDING_CONTRACT,
        "schema_version": BINDING_SCHEMA,
        **provenance,
        "invalidation_event_id": event_id(body),
        "invalidation_state": body["state"],
    }
    return {
        "provenance": provenance,
        "provenance_sha256": target,
        "binding": binding,
        "subject_sha256": canonical_sha256(binding),
        "event_id": event_id(body),
        "publication": "NOT_AVAILABLE",
        "research_display_grant": "NONE",
        "frozen_grant": "NONE",
        "live_grant": "NONE",
    }


def resolve_binding(binding: dict, events: tuple | list, decision_time: datetime) -> dict:
    """Currency of one composite. A component without an event does not block and is not CLEAR."""
    body = _validate_binding(binding)
    provenance = {key: body[key] for key in PROVENANCE_KEYS}
    target = provenance_sha256(provenance)
    bound_id = body["invalidation_event_id"]
    matched = [event_id(validate_event(item)) for item in events].count(bound_id)
    if matched != 1:
        raise BindingContractError("binding event is not in the log exactly once")
    stored = next(item for item in events if event_id(validate_event(item)) == bound_id)
    stored_body = validate_event(stored)
    if stored_body["target_sha256"] != target or stored_body["state"] != body["invalidation_state"]:
        raise BindingContractError("binding event does not match the provenance target or stored state")
    provenance_resolution = resolve_target(events, target, decision_time)
    veto = []
    for field in COMPONENT_FIELDS:
        component = resolve_target(events, body[field], decision_time)
        if component["resolution"] == "UNSTATED":
            continue
        if component["resolution"] != "CLEAR":
            veto.append({"field": field, "target_sha256": body[field], "resolution": component["resolution"]})
    current = (
        provenance_resolution["resolution"] == "CLEAR"
        and provenance_resolution["event_id"] == bound_id
        and body["invalidation_state"] == "CLEAR"
        and not veto
    )
    return {
        "provenance_resolution": provenance_resolution["resolution"],
        "provenance_event_id": provenance_resolution["event_id"],
        "defect": provenance_resolution["defect"],
        "component_veto": tuple(veto),
        "current_valid": current,
        "not_bindable": not current,
        "publication": "NOT_AVAILABLE",
        "research_display_grant": "NONE",
        "frozen_grant": "NONE",
        "live_grant": "NONE",
    }


def _require_documents(company: dict, manifest: dict) -> None:
    if not isinstance(company, dict) or company.get("record_kind") != RECORD_KIND or company.get("record_version") != 1:
        raise BindingContractError("company record is not QGV_COMPANY_RESULT v1")
    if not isinstance(manifest, dict) or manifest.get("manifest_kind") != MANIFEST_KIND or manifest.get("manifest_version") != 1:
        raise BindingContractError("manifest is not QGV_PRODUCER_BATCH_MANIFEST v1")
    stated = manifest.get("producer_id", PRODUCER_ID)
    if stated != PRODUCER_ID:
        raise BindingContractError("producer_id is not the persisted QGV research producer id")
    for label, value in (("company semantic", company.get("semantic")), ("manifest semantic", manifest.get("semantic"))):
        if not isinstance(value, dict):
            raise BindingContractError(f"{label} is missing")
    if not isinstance(manifest.get("operational"), dict) or not isinstance(manifest["operational"].get("code_commit"), str):
        raise BindingContractError("operational.code_commit is missing")
    if manifest["operational"]["code_commit"].strip() == "":
        raise BindingContractError("code_commit is empty")


def _mapping(value: object, where: str) -> dict:
    if not isinstance(value, dict):
        raise BindingContractError(f"{where} is missing")
    return value


def _validate_provenance(provenance: dict) -> None:
    if set(provenance) != set(PROVENANCE_KEYS):
        raise BindingContractError("provenance keys are not the approved set")
    if provenance["producer_id"] != PRODUCER_ID:
        raise BindingContractError("producer_id is not the persisted QGV research producer id")
    for key in ("code_commit", "as_of", "company_id", "qgv_system_version", "qgv_standard_version",
                "qgv_analysis_contract", "implementation_line", "universe_id",
                "cross_section_rule_id", "cross_section_rule_status"):
        if not isinstance(provenance[key], str) or provenance[key] == "":
            raise BindingContractError(f"{key} is required")
    for key in ("weights_sha256", "persisted_output_sha256", "members_sha256", "inputs_sha256"):
        if not isinstance(provenance[key], str) or not _HEX64.match(provenance[key]):
            raise BindingContractError(f"{key} must be 64 lowercase hex")


def _validate_binding(binding: dict) -> dict:
    if not isinstance(binding, dict):
        raise BindingContractError("binding must be an object")
    expected = set(PROVENANCE_KEYS) | {"contract", "schema_version", "invalidation_event_id", "invalidation_state"}
    if set(binding) != expected:
        raise BindingContractError("binding keys are not the approved set")
    if binding.get("contract") != BINDING_CONTRACT or binding.get("schema_version") != BINDING_SCHEMA:
        raise BindingContractError("binding contract is not RESEARCH_SUBJECT_BINDING_V1")
    provenance = {key: binding[key] for key in PROVENANCE_KEYS}
    _validate_provenance(provenance)
    if not isinstance(binding.get("invalidation_event_id"), str) or not _HEX64.match(binding["invalidation_event_id"]):
        raise BindingContractError("invalidation_event_id must be 64 lowercase hex")
    if binding.get("invalidation_state") not in ("CLEAR", "SUSPENDED", "INVALIDATED"):
        raise BindingContractError("invalidation_state is not an admitted stored state")
    return binding
