"""Approved C8 entry, boundary and fixture-only threshold registration paths.

No calibration search/plateau validity computation, A6 hypothesis test, A8 hard
distinctness, A10 role selection, real provider or promotion is implemented.
"""
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import json

from .calibration_contracts import (SCOPE, FIXTURE_SCOPE, IntegrityFailure, MissingPrerequisite,
                                   validate_plan, instant, finite_number, identity, METRIC_VERSION,
                                   authority, code_hash, APPROVAL_BLOB)
from .landscape import checkpoint
from .profile_selection import resolve_selection, registration as selection_registration
from .robustness import c4_report
from .walkforward import digest


def _software_upstream_declaration(selection_ledger):
    declared = selection_registration(selection_ledger)["body"]["plan"]
    if declared["scope"] != SCOPE or declared["configuration_scope"] != FIXTURE_SCOPE:
        raise MissingPrerequisite("real upstream validation is not authorized for C8 foundation")
    return declared


def upstream_snapshot(selection_ledger, cohorts):
    _software_upstream_declaration(selection_ledger)
    files = {p.name: sha256(p.read_bytes()).hexdigest()
             for p in sorted(selection_ledger.directory.iterdir())
             if p.suffix in (".json", ".jsonl")}
    return {"c7_files": files, "c4_c5_c6": checkpoint(cohorts)}


_RESOLVED_UPSTREAM = None


def describe_upstream(selection_ledger, cohorts):
    """Actual current C4/C5/C6/C7 resolution, never a boolean authority adapter."""
    global _RESOLVED_UPSTREAM
    authority()
    registration = _software_upstream_declaration(selection_ledger)
    committed = upstream_snapshot(selection_ledger, cohorts)
    # Only fully resolved metadata is memoized, never producer PASS or flags.
    # The key includes every current input/file plus actual code and authority.
    key = digest({"snapshot": committed, "code_hash": code_hash(), "approval_blob": APPROVAL_BLOB})
    cached = _RESOLVED_UPSTREAM
    if cached is not None and cached[0] == key:
        return deepcopy(cached[1])
    report = resolve_selection(selection_ledger, cohorts)
    landscape = report["output"]["stages"][0]["output"]
    model_instances, sample_ids, windows, horizons, c6_refs = {}, set(), [], {}, {}
    for cohort, args in sorted(cohorts.items()):
        ledger, split, source, bundles, drift = args
        model_instances[cohort] = {}
        for candidate, bundle in sorted(bundles.items()):
            c4 = c4_report(bundle["c4_ledger"], bundle["c4_trial_id"])
            model_instances[cohort][candidate] = {
                "model_hash": c4["model_hash"], "predictive_threshold_hash": c4["threshold_hash"],
                "prediction_hash": c4["prediction_hash"], "parameters_hash": digest(c4["parameters"]),
                "code_hash": c4["code_hash"], "c4_trial_id": c4["trial_id"],
                "dataset_vintage": bundle["c4_ledger"].registration()["dataset_vintage"]}
            for ids in c4["partition"]["retained"].values():
                sample_ids.update(ids)
        split_body = split.payload()
        windows.extend(deepcopy(list(split_body["windows"].values())))
        horizons[cohort] = {k: split_body[k] for k in
                           ("policy_id", "max_label_horizon_microseconds", "schedule_id")}
        c6_refs[cohort] = deepcopy(landscape["cohorts"][cohort]["acceptance"])
    holdouts = {args[1].holdout_start.isoformat() for args in cohorts.values()}
    if len(holdouts) != 1:
        raise IntegrityFailure("shared frozen Holdout boundary metadata differs")
    result = {"holdout_boundary": next(iter(holdouts)),
            "snapshot_hash": digest(upstream_snapshot(selection_ledger, cohorts)),
            "c7_report_hash": digest(report),
            "family_members": sorted(landscape["roster"]),
            "representative_ties": {name: deepcopy(p["representative_tie_set"])
                                    for name, p in report["output"]["profiles"].items()},
            "cohort_metadata": deepcopy(registration["cohort_metadata"]),
            "model_instances": model_instances,
            "used_outcomes": {"sample_ids": sorted(sample_ids), "windows": windows},
            "horizon_contracts": horizons, "c6_evidence_refs": c6_refs,
            "descriptive_distinctness": deepcopy(report["output"]["distinctness"]),
            "scope": report["scope"], "configuration_scope": report["configuration_scope"]}
    if upstream_snapshot(selection_ledger, cohorts) != committed:
        raise IntegrityFailure("upstream changed during full validation; cannot cache it")
    _RESOLVED_UPSTREAM = (key, deepcopy(result))  # Atomic tuple, at most one qualified entry.
    return deepcopy(result)


def resolve_entry(ledger, selection_ledger, cohorts):
    """Current hashes, real bytes/lineage, invalidation, methodology and approval."""
    p = validate_plan(ledger.registration()["body"]["plan"])
    if not ledger.active():
        raise IntegrityFailure("C8 current invalidation")
    ledger.events()
    if digest(upstream_snapshot(selection_ledger, cohorts)) != p["upstream_snapshot_hash"]:
        raise IntegrityFailure("changed/invalidated frozen upstream checkpoint")
    current = describe_upstream(selection_ledger, cohorts)
    if current["snapshot_hash"] != p["upstream_snapshot_hash"]:
        raise IntegrityFailure("upstream changed during current evidence resolution")
    if current["scope"] != SCOPE or current["configuration_scope"] != FIXTURE_SCOPE:
        raise IntegrityFailure("mixed upstream scope cannot qualify software or real research")
    fields = ("family_members", "representative_ties", "cohort_metadata", "model_instances",
              "used_outcomes", "horizon_contracts", "holdout_boundary")
    if any(current[k] != p[k] for k in fields):
        raise IntegrityFailure("complete family/ties/models/data/horizon lineage differs")
    # C6 protocol PASS is retained evidence, never skill/validation authority.
    return p, current


def register_calibration(ledger, selection_ledger, cohorts, plan):
    p = validate_plan(plan)
    current = describe_upstream(selection_ledger, cohorts)
    if current["snapshot_hash"] != p["upstream_snapshot_hash"]:
        raise IntegrityFailure("registration must bind current upstream bytes")
    for k in ("family_members", "representative_ties", "cohort_metadata", "model_instances",
              "used_outcomes", "horizon_contracts", "holdout_boundary"):
        if current[k] != p[k]:
            raise IntegrityFailure("registration cannot substitute surviving subset or changed model")
    if current["scope"] != p["scope"]:
        raise IntegrityFailure("registered upstream scope mismatch")
    return ledger.register(p)


def _unseen_verify(ledger, plan):
    if ledger.registry.spent(plan["datasets"]["CAL_VERIFY"]):
        raise MissingPrerequisite("VERIFY boundary already accessed: no refit/tune/next-best")


def _boundary(plan, role, at):
    data = plan["datasets"][role]
    at = instant(at)
    if instant(data["available_at"]) > at:
        raise IntegrityFailure("dataset available_at exceeds boundary evaluation time")
    schedule = [instant(t) for t in plan["rebalance_schedule"]]
    verify_start = instant(plan["datasets"]["CAL_VERIFY"]["window"]["start"])
    for cohort, meta in plan["cohort_metadata"].items():
        cutoff = (schedule[schedule.index(verify_start) - 1]
                  if role == "CAL_FIT" and meta["variant"] == "REBALANCE_GAP_STRESS"
                  else verify_start if role == "CAL_FIT"
                  else instant(data["window"]["end"]))
        horizon = timedelta(microseconds=plan["horizon_contracts"][cohort]["max_label_horizon_microseconds"])
        for s in data["samples"]:
            start, end, available = map(instant, (s["decision_time"], s["label_end"], s["label_available_at"]))
            if not (instant(data["window"]["start"]) <= start < instant(data["window"]["end"])):
                raise IntegrityFailure("sample outside registered calibration role")
            if not start < end <= start + horizon or available < end:
                raise IntegrityFailure("label horizon/publication provenance invalid")
            if end >= cutoff or available >= cutoff:
                raise MissingPrerequisite("insufficient independent mature support at approved exclusion boundary")
            if available > at:
                raise IntegrityFailure("unrealized/unpublished outcome cannot be evaluated")
            if not s["observations"]:
                raise IntegrityFailure("missing feature provenance")
            for obs in s["observations"]:
                identity(obs["observation_id"])
                identity(obs["source_id"])
                identity(obs["vintage"])
                if instant(obs["available_at"]) > start:
                    raise IntegrityFailure("predictor lookahead")
    return data


def _qualified_payload(body, data, plan, current, at):
    fields = {"dataset_id", "scope", "synthetic", "temporal_origin", "tax_mode", "source_id",
              "vintage", "lineage_ids", "manifest_hash", "samples", "cohorts"}
    if set(body) != fields or digest(body) != data["content_hash"]:
        raise IntegrityFailure("target bytes/hash or payload schema changed")
    if (body["dataset_id"] != data["dataset_id"] or body["scope"] != SCOPE
            or body["synthetic"] is not True or body["temporal_origin"] != "SIMULATED"
            or body["tax_mode"] != "EXCLUDED"
            or any(body[k] != data[k] for k in ("source_id", "vintage", "lineage_ids", "manifest_hash", "samples"))):
        raise IntegrityFailure("actual input identity/lineage/scope/tax mismatch")
    if set(body["cohorts"]) != set(plan["cohort_metadata"]):
        raise MissingPrerequisite("required cohort evidence incomplete")
    for cohort, candidates in body["cohorts"].items():
        if set(candidates) != set(plan["family_members"]):
            raise IntegrityFailure("complete registered family cannot be shrunk")
        for candidate, record in candidates.items():
            if record["frozen_instance"] != current["model_instances"][cohort][candidate]:
                raise IntegrityFailure("candidate/model/predictive thresholds changed")
            if (record["metric_report"]["metric_version"] != METRIC_VERSION
                    or record["metric_report"]["tax_mode"] != "EXCLUDED"):
                raise IntegrityFailure("exact C3 metric version/Pre-Tax evidence required")
            if set(record["controls"]) != {c["control_id"] for c in plan["controls"]}:
                raise MissingPrerequisite("negative control support incomplete")
            for metrics in (record["metric_report"], *record["controls"].values()):
                if metrics["metric_version"] != record["metric_report"]["metric_version"] or metrics["tax_mode"] != "EXCLUDED":
                    raise IntegrityFailure("control methodology/tax mismatch")
                if metrics.get("official") is not False or instant(metrics["evaluation_time"]) > instant(at):
                    raise IntegrityFailure("metric source is not realized/current Pre-Tax fixture evidence")
                if len(metrics["provenance"]) != len(data["samples"]):
                    raise MissingPrerequisite("complete metric sample provenance missing")
                for stamps, sample in zip(metrics["provenance"], data["samples"]):
                    if set(stamps) != {"risk_free_stamp", "outcome_stamp", "inflation_stamp"}:
                        raise IntegrityFailure("complete C3 source stamps required")
                    for stamp in stamps.values():
                        identity(stamp["observation_id"])
                        identity(stamp["source_id"])
                        identity(stamp["vintage"])
                        if instant(stamp["available_at"]) > instant(metrics["evaluation_time"]):
                            raise IntegrityFailure("metric source publication lookahead")
                    if instant(stamps["risk_free_stamp"]["available_at"]) > instant(sample["decision_time"]):
                        raise IntegrityFailure("RF must be known at period start")
                    outcome = stamps["outcome_stamp"]
                    if (outcome["source_id"] != data["source_id"] or outcome["vintage"] != data["vintage"]
                            or instant(outcome["available_at"]) != instant(sample["label_available_at"])):
                        raise IntegrityFailure("outcome dataset lineage/publication mismatch")
    return deepcopy(body)


def read_partition(ledger, selection_ledger, cohorts, provider, *, role, attempt_id,
                   at, fit_attempt_id=None, choice_attempt_id=None):
    if role not in ("CAL_FIT", "CAL_VERIFY"):
        raise IntegrityFailure("no Holdout/Development read interface")

    def produce(pending):
        plan, current = resolve_entry(ledger, selection_ledger, cohorts)
        _unseen_verify(ledger, plan)
        if role == "CAL_VERIFY":
            fit = ledger.receipt(fit_attempt_id)
            choice = ledger.receipt(choice_attempt_id)
            if fit["operation"] != "CAL_FIT" or choice["operation"] != "THRESHOLD_CHOICE":
                raise IntegrityFailure("FIT/choice lineage missing")
            if (choice["output"]["fit_receipt_hash"] != digest(fit)
                    or choice["output"]["threshold_registration_hash"] != digest(plan["threshold_registration"])):
                raise IntegrityFailure("exact threshold choice/config must be frozen before VERIFY")
        data = _boundary(plan, role, at)
        if provider.scope != SCOPE or provider.synthetic is not True or provider.describe(role) != data:
            raise IntegrityFailure("actual provider commitment does not match declaration")
        event = ledger.mark_access(pending, role, at)
        # Durable registry intent and ledger pending/access checkpoint precede read.
        body = _qualified_payload(provider.read(role), data, plan, current, at)
        after_plan, after_current = resolve_entry(ledger, selection_ledger, cohorts)
        if after_plan != plan or after_current != current:
            raise IntegrityFailure("upstream/authority changed during target access")
        return {"role": role, "data": body, "data_hash": digest(body),
                "manifest_hash": data["manifest_hash"], "access_event_hash": event["sha256"],
                "c7_report_hash": current["c7_report_hash"], "model_instances": current["model_instances"],
                "universal": {k: "PASS" for k in
                              ("PIT", "PROVENANCE", "LINEAGE", "COMPLETE_LEDGER", "SCOPE",
                               "TAX_MODE", "INVALIDATION", "HOLDOUT_ISOLATION", "FROZEN_CANDIDATES")},
                "confirmation_decision": None, "research_state": None}
    return ledger.execute(attempt_id, role, at, produce)


def record_fixture_threshold_choice(ledger, selection_ledger, cohorts, *, fit_attempt_id,
                                    vector_id, rounded_vector, approval_event, attempt_id, at):
    """Explicit fixture registration event, not real threshold eligibility."""
    def produce(pending):
        plan, current = resolve_entry(ledger, selection_ledger, cohorts)
        _unseen_verify(ledger, plan)
        fit = ledger.receipt(fit_attempt_id)
        if fit["operation"] != "CAL_FIT":
            raise IntegrityFailure("choice must bind CAL_FIT receipt")
        registry = plan["threshold_registration"]
        if registry is None:
            raise MissingPrerequisite("no registered threshold/support configuration")
        if vector_id not in registry["vectors"]:
            raise IntegrityFailure("no implicit peak/next-best/unregistered threshold")
        support = registry["fixture_fit_support"][vector_id]
        if rounded_vector != support["rounded_vector"]:
            raise IntegrityFailure("rounding support cannot be changed post-result")
        expected_keys = {"event_id", "actor_id", "kind", "at", "registration_hash", "approval_blob"}
        if (set(approval_event) != expected_keys
                or approval_event["kind"] != "EXPLICIT_SOFTWARE_FIXTURE_CHOICE"
                or approval_event["registration_hash"] != ledger.registration()["sha256"]
                or approval_event["approval_blob"] != plan["approval_blob"]
                or instant(approval_event["at"]) != instant(at)):
            raise IntegrityFailure("explicit scoped choice approval event required")
        identity(approval_event["event_id"])
        identity(approval_event["actor_id"])
        if any(r["body"]["event"]["kind"] == "TERMINAL"
               and r["body"]["event"]["status"] == "PASS"
               and ledger.receipt(r["body"]["event"]["attempt_id"])["operation"] == "THRESHOLD_CHOICE"
               for r in ledger.events()):
            raise MissingPrerequisite("threshold choice already fixed; no replacement")
        return {"choice_kind": "FIXTURE_ONLY_REGISTRATION_RECORD",
                "vector_id": vector_id, "registered_vector": deepcopy(registry["vectors"][vector_id]),
                "rounded_vector": deepcopy(rounded_vector), "rounding_support_ref": support["support_ref"],
                "threshold_registration_hash": digest(registry), "fit_receipt_hash": digest(fit),
                "approval_event": deepcopy(approval_event), "eligibility_decision": None,
                "real_threshold_authority": None, "c7_report_hash": current["c7_report_hash"]}
    return ledger.execute(attempt_id, "THRESHOLD_CHOICE", at, produce)
