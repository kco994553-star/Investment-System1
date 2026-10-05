"""Derive an inactive finite dependency matrix from existing immutable G evidence.

No source-tree read, source replay, formula, threshold or runtime policy adoption.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
INPUTS = {
    "G_METHOD_REPLAY_MANIFEST.json": "139757a9b5cfca3317aa009bb94e92f8af72034838ea0a88711d0b1fe505216f",
    "G_LINEAGE_REPLAY.json": "77f8300c2ebf594e640582dc213d8af1b012f7c11bf825a2c2b5f536fd2595d3",
}
data = {}
for name, sha in INPUTS.items():
    body = (ROOT / name).read_bytes()
    if hashlib.sha256(body).hexdigest() != sha:
        raise SystemExit("Immutable evidence hash mismatch: " + name)
    data[name] = json.loads(body)

manifest = data["G_METHOD_REPLAY_MANIFEST.json"]
replay = data["G_LINEAGE_REPLAY.json"]
g1 = next(r for r in manifest["records"] if r["factor_id"] == "next_3_5y_growth")
g2 = next(r for r in manifest["records"] if r["factor_id"] == "eps_fcf_per_share_growth")


def row(key, clause, subject, status, available, absent, refs, owner, artifacts, acceptance, method="UNKNOWN"):
    return {"dependency_id": key, "decision_clause": clause, "subject": subject,
        "evidence_status": status, "available_evidence": available,
        "unresolved_or_absent": absent,
        "evidence_refs": [{"artifact": name, "sha256": INPUTS[name], "json_pointer": pointer} for name, pointer in refs],
        "authoritative_owner_assignment": None, "requested_authority_role": owner,
        "required_source_artifacts": artifacts,
        "acceptance_evidence_needed_for_future_decision": acceptance,
        "conditional_alternative_method": method,
        "method_formula_selected": None, "numeric_policy_selected": None,
        "production_requiredness": None, "production_enabled": False,
        "boundary": "Evidence readiness only; acceptance description is not production admission or D3 approval"}

M = "G_METHOD_REPLAY_MANIFEST.json"
R = "G_LINEAGE_REPLAY.json"
rows = [
    row("G1-01", "G1", "Economic target and horizon intent", "UNKNOWN_METHOD_AUTHORITY",
        ["Preserved factor ID and current explicit last-YoY proxy", "Requested 3Y/5Y metadata is separate from score computation"],
        ["No approved choice of forward forecast versus historical structural growth in consumed evidence"],
        [(M, "/records/0"), (R, "/synthetic_cases/0/factor_results/0")],
        "QGV semantic authority/user D3; source-producing owner documents scope",
        ["Versioned economic target/horizon declaration", "Specific decision/approval evidence"],
        ["Chosen target, direction, horizon and scope explicitly documented", "Existing archived proxy lineage retained separately"]),
    row("G1-02", "G1", "Historical revenue source availability", "PARTIAL_SYNTHETIC_ONLY",
        ["Committed SEC mini fixture has selected current/prior revenue rows", "Producer source supports dated FactVintage fields"],
        ["Cached real companyfacts bytes absent despite provenance manifest", "Mini fixture lacks complete form/start/fy/fp/accession"],
        [(R, "/committed_SEC_fixture/selected_revenue_rows"), (R, "/real_cached_raw_replay")],
        "SEC ingestion/data-provenance owner; assignment unresolved",
        ["Exact archived raw blob matching recorded SHA256", "Source manifest and issuer/concept/unit/period/accession rows"],
        ["Hash matches archived manifest", "Period/source fields retained without upgrading absent filing precision"],
        "EXISTING_SOURCE_VINTAGE_SELECTION_AVAILABLE; historical multi-year growth formula UNKNOWN"),
    row("G1-03", "G1", "Historical 3–5Y calculation readiness", "UNKNOWN_REPLACEMENT_METHOD",
        ["Quarterly-history monitor and GHorizon are source-pinned metadata/evidence structures", "Current scored method consumes only a current/prior pair"],
        ["No consumed repository calculation demonstrates a scored structural 3–5Y alternative", "Method-specific observation window and gaps authority unresolved"],
        [(M, "/records/0/input_period"), (M, "/source_sha256")],
        "QGV G-method owner under separate D3 semantic selection",
        ["Inactive intended-method/input-contract declaration", "Exact historical period/vintage series if a historical family is chosen"],
        ["Historical family justified separately from forecast family", "Any actual equation/defaults await explicit method authority"],
        "UNKNOWN; no new multi-year formula generated"),
    row("G1-04", "G1", "Forecast source/vintage readiness", "ABSENT_IN_CONSUMED_REPLAY",
        ["Current G1 raw inputs are revenue and revenue_prev only"],
        ["No forecast raw field/source snapshot/published vintage consumed", "Forecast origin, target period, revision chain and ex-ante availability missing"],
        [(M, "/records/0/input_fields"), (M, "/records/0/pit_fields")],
        "Forecast/consensus data owner plus QGV target-method authority; assignment unresolved",
        ["Archived forecast vintage with source/provider/reference/hash", "Target period/horizon, publication and availability evidence", "Revision history/issuer scope"],
        ["Forecast known at decision time evidenced rather than inferred from today's forecast", "No fetched_at substitution for past availability"],
        "UNKNOWN; no repository-grounded forecast scoring formula in consumed artifacts"),
    row("G1-05", "G1", "Period adjacency and comparability", "UNRESOLVED_PAIR_AUTHORITY",
        ["Producer selects prior distinct fy/fp/end group", "Synthetic complete case declares annual current/prior periods"],
        ["Distinct vintage group does not prove distinct end or adjacent one-year comparator", "Missing starts/forms prevent certifying annual duration"],
        [(M, "/records/0/input_source_map/revenue_prev"), (R, "/committed_SEC_fixture/precision_caveats")],
        "Fundamental-period data owner plus G economic-method authority",
        ["Exact paired period start/end/fiscal labels/unit/concept lineage", "Method-specific gap/period interpretation declaration"],
        ["Actual periods and units available for comparison", "No interval tolerance/cutoff invented by this readiness matrix"]),
    row("G2-01", "G2", "Existing EPS primary branch", "AVAILABLE_SOURCE_CHARACTERIZATION",
        ["Source replay binds EPS/current-prior branch and input values", "Separate audit-only branch anchor exists"],
        ["No authoritative production method ID/version", "Real input lineage still absent"],
        [(M, "/records/3"), (R, "/synthetic_cases/0/factor_results/3")],
        "QGV method identity owner plus EPS data owner",
        ["Versioned EPS input-contract/source binding", "Exact method authority if selected for future production"],
        ["Factor identity separated from method/version", "No current-source identity retroactively assigned to historical snapshots"],
        "OBSERVED_EPS_RATIO_MINUS_ONE_BRANCH_ONLY; new method policy UNKNOWN"),
    row("G2-02", "G2", "EPS period/share-basis comparability", "UNRESOLVED_REAL_PAIR_EVIDENCE",
        ["Adapter can select diluted/basic EPS concepts and previous selected vintage", "Synthetic replay declares EPS units and periods"],
        ["Paired diluted/basic, fiscal-duration and share-restatement basis unverified", "Financial/reporting context authority unresolved"],
        [(M, "/records/3/input_source_map/eps"), (M, "/records/3/input_source_map/eps_prev"), (R, "/synthetic_cases/0/factor_results/3/synthetic_input_period_basis")],
        "EPS/corporate-action data owner plus method authority",
        ["Paired EPS period/concept/share basis and source revisions", "Corporate-action/restatement lineage"],
        ["Paired measures share comparable documented basis", "Numeric synthetic pairing not promoted to real evidence"]),
    row("G2-03", "G2", "Current FCF numerator source", "AVAILABLE_SOURCE_SHAPE_ONLY",
        ["Direct FreeCashFlow or CFO-abs(CAPEX) source branches described", "Current FCF fallback input is reproducibly source-characterized"],
        ["Actual producer branch and matched real source rows not in legacy RawFundamentals", "Mini SEC fixture has no real paired FCF evidence"],
        [(M, "/records/3/input_source_map/fcf"), (R, "/synthetic_cases/1/factor_results/3"), (R, "/committed_SEC_fixture/raw")],
        "Cash-flow/SEC data owner; method authority separate",
        ["Exact FCF production branch and component concept/unit/period/vintage", "Archived source hashes"],
        ["Numerator lineage explicit", "CFO and CAPEX period/currency matching evidenced without invented conversion"]),
    row("G2-04", "G2", "Previous FCF dependency", "ABSENT_FROM_RUNTIME_INPUT_CONTRACT",
        ["Source adapter can select fcf_prev but drops it", "Current branch consumes revenue_prev instead"],
        ["No prior FCF field in scored raw contract or replay input closure", "Actual intended FCF growth equation/branch not approved"],
        [(M, "/records/3/input_period"), (M, "/records/3/input_source_map/fcf"), (M, "/records/3/input_fields")],
        "Cash-flow data owner and QGV G2 method owner",
        ["Paired current/prior FCF source periods and vintages if chosen", "Separate inactive alternative method contract"],
        ["Prior FCF not substituted with prior revenue", "Actual new formula/branch selection remains D3"],
        "UNKNOWN; no FCF-growth alternative formula created"),
    row("G2-05", "G2", "Per-share cash-flow dependency", "ABSENT_FROM_FALLBACK_METHOD",
        ["Manifest states fallback consumes no paired FCF/share contract"],
        ["No prior shares or paired weighted/diluted share basis in consumed fallback", "Current raw shares alone cannot prove per-share comparability"],
        [(M, "/records/3/input_period"), (M, "/records/3/result_lineage"), (R, "/committed_SEC_fixture/raw")],
        "Share/corporate-action data owner plus economic-method authority",
        ["Current/prior share basis tied to cash-flow periods", "Split/dilution/security/issuer lineage if per-share family chosen"],
        ["Per-share quantities derive from matching approved basis", "No current-share shortcut or guessed historical shares"],
        "UNKNOWN; per-share alternative not present in consumed scored method"),
    row("G2-06", "G2", "Fallback economic meaning and branch selection", "METHOD_MISMATCH_CONFIRMED",
        ["Current fallback is FCF/current divided by prior revenue minus one", "Zero prior EPS and absent EPS both select existing cross-measure branch"],
        ["No authority makes it accepted FCF growth/per-share growth/EPS substitute", "Alternative branch semantics UNKNOWN"],
        [(M, "/records/3/normalization"), (R, "/synthetic_cases/1/factor_results/3"), (R, "/synthetic_cases/2/factor_results/3")],
        "User D3/QGV G2 semantic authority",
        ["Explicit accepted fallback economic purpose and branch conditions", "Distinct factor/method/version/input contract refs"],
        ["Different measure requires separate explicit meaning", "Historical legacy branch/result remains unchanged"],
        "EXISTING_CROSS_MEASURE_BRANCH_RECORDED; replacement UNKNOWN"),
    row("G2-07", "G2", "Currency, duration and numerator/denominator alignment", "UNRESOLVED_PRODUCTION_ALIGNMENT",
        ["Synthetic input units/periods declared", "SEC source concept/unit candidates pinned"],
        ["Legacy exported stamp omits per-field concept/period/accession", "Current/prior currencies/periods not independently validated by scalar calculation"],
        [(M, "/records/3/input_source_map"), (M, "/records/3/pit_fields"), (R, "/synthetic_cases/1/factor_results/3/synthetic_input_period_basis")],
        "Financial-period/currency data owner plus G2 input-contract owner",
        ["Per-field source concept/unit/currency/start/end/vintage", "Method-approved comparator accounting basis"],
        ["Compatible units and intended period pairing evidenced", "No numeric conversion/gap policy selected here"]),
    row("G2-08", "G2", "Zero/negative denominator semantics", "ZERO_BRANCH_RECORDED_NEGATIVE_POLICY_UNKNOWN",
        ["Zero prior EPS routes to fallback in current replay", "Existing formula/normalization source anchor preserved"],
        ["No new negative-base interpretation/transform selected", "No alternative zero-base treatment authority in consumed artifacts"],
        [(M, "/records/3/normalization"), (R, "/synthetic_cases/2/factor_results/3")],
        "User D3/QGV method-domain authority",
        ["Explicit domain/zero/negative-base economic interpretation and evidence", "Method-version binding for any replacement"],
        ["No epsilon, tolerance or automatic N/A invented", "Branch source and admission result remain separate"]),
    row("G2-09", "G2", "Financial-sector applicability", "UNKNOWN_ECONOMIC_APPLICABILITY",
        ["Current factor_applicable is true for all G under both profiles"],
        ["Boolean execution not evidence that generic corporate FCF/share method applies to financial issuers", "No method-specific financial predicate authority"],
        [(M, "/records/3/current_runtime_applicability"), (M, "/records/3/applicability_truth")],
        "QGV sector-method/applicability authority under B2; assignment unresolved",
        ["Sector/issuer evidence tied to exact proposed method", "Applicability authority and evidence contract"],
        ["Missing evidence not converted to N/A", "No denominator exclusion or predicate activation before D3"]),
    row("SHARED-01", "G1+G2", "Publication/vintage/PIT precision", "PARTIAL_DATE_ONLY_SYNTHETIC_EVIDENCE",
        ["Raw shared stamp has available_at/published_at", "Mini fixture selected rows and precision caveats retained"],
        ["Per-field vintage/availability closure absent", "Date-only or missing filing identity not exact intraday proof", "Real source bytes absent"],
        [(M, "/records/0/pit_fields"), (M, "/records/3/pit_fields"), (R, "/committed_SEC_fixture/precision_caveats"), (R, "/real_cached_raw_replay")],
        "Source provenance/PIT owner plus B3 admission authority",
        ["Exact source revisions/file hashes and publication/availability precision", "Per-input source-to-result closure"],
        ["PIT uncertainty preserved rather than upgraded", "available_at and published_at traced independently of weight"]),
    row("SHARED-02", "G1+G2", "Historical parallel result/method protection", "INACTIVE_BINDING_AVAILABLE_RUNTIME_UNKNOWN",
        ["Legacy synthetic payload hash and snapshot ID preserved", "Existing factor identity separate from audit-only observed branches"],
        ["Archived method/input identity not present in historical payload", "Runtime version dispatcher/complete G result lineage absent"],
        [(R, "/persisted_historical_sample"), (M, "/records/0/result_lineage"), (M, "/records/3/result_lineage")],
        "QGV calculation/history owner under separate migration approval",
        ["Separate approved method/version/input refs and new result ID/hash", "Archived legacy payload hash and source proof"],
        ["No historical inference from current source", "No legacy snapshot rewrite or canonical migration"]),
]

matrix = {"artifact_kind": "INACTIVE_G_SOURCE_READINESS_DEPENDENCY_MATRIX",
    "task_complete": True, "source_head": manifest["source_owner_head"],
    "parent_fresh_global_ref": "6d029732e6bee02038a25685badb937b2666d04e",
    "global_context": "Parent-confirmed coordinator transfer/CDR018 only; not G semantic adoption; no Global write",
    "input_hashes": INPUTS, "derived_from": "Existing G manifest/replay only; no new source audit or replay",
    "task_scope": "Finite evidence dependency enumeration for G1/G2; all cells have evidence or unresolved authority/source request",
    "rows": rows, "row_count": len(rows),
    "production_requiredness_assigned": 0, "supported_promotions": 0,
    "new_numeric_policy": None, "new_valuation_or_growth_formula": None,
    "production_enabled": False, "scheduler_hops_added": 0,
    "B1_status": "MORE_EVIDENCE_REQUIRED",
    "B2_B3_B5_B6": "Consumer/evidence/applicability/admission policies still unapproved; this matrix does not activate them",
    "conditional_tasks": [
        {"task": "Restore exact cached SEC input bytes through authorized data owner and verify manifest/hash", "authority": "D1/D2 exact restoration/evidence only", "state": "WAITING_DATA_OWNER_SOURCE_BYTES", "next_step_after_source": "Source row lineage only; no replacement methods or scores"},
        {"task": "Populate inactive forecast/paired FCF-share input contract if exact source artifacts become available", "authority": "D1/D2 evidence only", "state": "WAITING_G1_G2_SOURCE_ARTIFACTS", "numeric_calculation": "UNKNOWN_UNTIL_SEPARATE_D3_METHOD_DECLARATION"},
    ]}
assert len({r["dependency_id"] for r in rows}) == len(rows)
assert all(r["evidence_refs"] and r["acceptance_evidence_needed_for_future_decision"] and r["required_source_artifacts"] for r in rows)
assert all(r["production_requiredness"] is None and r["method_formula_selected"] is None and not r["production_enabled"] for r in rows)
body = json.dumps(matrix, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
(ROOT / "G_SOURCE_READINESS_MATRIX.json").write_text(body)
assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha for name, sha in INPUTS.items())
print(json.dumps({"rows": len(rows), "matrix_sha256": hashlib.sha256(body.encode()).hexdigest(),
    "frozen_inputs_unchanged": True, "new_source_probes": 0, "scheduler_hops_added": 0}))
