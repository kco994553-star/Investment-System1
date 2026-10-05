"""Pinned owner contract audit and undeployed repair-candidate fixtures.

Run from the repository: python implementation/docs/product_platform/audits/
storage_auth_2026-10-05/owner_probes.py

This executes only seven reviewed source/test/shim files from the exact Git pin.
Package initializers are bypassed. No provider, credential, HTTP or DB is used.
Candidate fixtures are audit-only: neither deployed nor adopted by the owner.
"""
from __future__ import annotations

import argparse
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import types


PIN = "78a51462f89eac8e34647cddc4e53ed97e831178"
EARLIER = "c9e1adb5fbd9a1b8e005c4f4cea7eec30ccc84d9"
REPAIR = "603d1c64b005e07dedebcf9ea733e4ed00b504d0"
ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
T = datetime(2026, 10, 5, 3, 0, tzinfo=timezone.utc)
H = "a" * 64
SOURCE_MODULES = (
    ("investment_system.personal.versioning", "implementation/src/investment_system/personal/versioning.py"),
    ("investment_system.personal.quality", "implementation/src/investment_system/personal/quality.py"),
    ("investment_system.personal.weights", "implementation/src/investment_system/personal/weights.py"),
    ("investment_system.personal.ports", "implementation/src/investment_system/personal/ports.py"),
    ("investment_system.platform.contracts", "implementation/src/investment_system/platform/contracts.py"),
)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def load(name, path, manifest):
    blob = git("show", f"{PIN}:{path}")
    module = types.ModuleType(name)
    module.__file__ = f"git:{PIN}:{path}"
    module.__package__ = name.rpartition(".")[0]
    sys.modules[name] = module
    exec(compile(blob, module.__file__, "exec"), module.__dict__)
    manifest.append({"path": path, "git_blob": git("rev-parse", f"{PIN}:{path}").decode().strip(),
                     "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)})
    return module


def load_owner():
    for package in ("investment_system", "investment_system.personal", "investment_system.platform", "tests"):
        module = types.ModuleType(package)
        module.__path__ = []
        sys.modules[package] = module
    manifest = []
    for name, path in SOURCE_MODULES:
        module = load(name, path, manifest)
        parent, _, attr = name.rpartition(".")
        setattr(sys.modules[parent], attr, module)
    shim = load("owner_mini_pytest", "implementation/tools/mini_pytest.py", manifest)
    shim._install_shim()
    tests = load("tests.test_product_platform_contracts", "implementation/tests/test_product_platform_contracts.py", manifest)
    return sys.modules["investment_system.platform.contracts"], tests, manifest


def source(c, **changes):
    values = dict(tenant_id="t1", connection_id="conn", account_id="acct", source_record_id="r1",
                  source_version="v1", record_type="POSITION", observed_at=T - timedelta(minutes=2),
                  available_at=T - timedelta(minutes=1), ingested_at=T, source="FIXTURE_PROVIDER",
                  raw_payload_ref="fixture://t1/r1/v1", payload_sha256=H)
    values.update(changes)
    return c.SourceRecord(**values)


def normalized(c, refs=None, **changes):
    values = dict(tenant_id="t1", normalized_id="n1", record_type="POSITION",
                  source_refs=(source(c).ref,) if refs is None else refs)
    values.update(changes)
    return c.NormalizedFinancialRecord(**values)


def rejects(exception, operation):
    try:
        operation()
    except exception as error:
        return type(error).__name__
    raise AssertionError(f"expected {exception.__name__}; input accepted")


def equal(actual, expected):
    assert actual == expected, (actual, expected)
    return actual


def record_check(results, name, operation):
    try:
        observation = operation()
        results.append({"name": name, "result": "PASS", "observation": observation})
    except Exception as error:
        results.append({"name": name, "result": "FAIL", "exception": type(error).__name__, "observation": str(error)})


def original_interface_validator(c, interface):
    original = c.BrokerAdapter
    c.BrokerAdapter = interface
    try:
        return c.validate_broker_contract()
    finally:
        c.BrokerAdapter = original


def inherited_write_interface(c):
    class WriteBase:
        def trade(self):
            pass
    methods = {name: lambda self: None for name in c.READ_ONLY_CONNECTOR_OPERATIONS}
    return type("InheritedBrokerDrift", (WriteBase,), methods)


# Tests precede the candidate implementations. Missing normalization must cause
# false missing/orphan lineage; missing MRO inspection must admit inherited trade.
def test_direct_digest_case_equivalence(c, canonicalize):
    original = source(c)
    direct_upper = c.SourceRecordRef("t1", "conn", "r1", "v1", "A" * 64)
    direct_lower = c.SourceRecordRef("t1", "conn", "r1", "v1", "a" * 64)
    assert canonicalize(direct_upper) == canonicalize(direct_lower), "same SHA-256 in different case must identify the same source ref"
    report = c.reconcile_records(c.TenantContext("t1", "u1"), (original,),
                                 (normalized(c, (canonicalize(direct_upper),)),))
    assert report["passed"] is True, "digest casing must not manufacture missing/orphan source refs"
    assert report["missing"] == () and report["orphan"] == ()
    return {"passed": report["passed"], "missing": report["missing"], "orphan": report["orphan"]}


def test_inherited_callable_trade_denied(c, validate):
    validate(c.BrokerAdapter)
    interface = inherited_write_interface(c)
    denial = rejects(c.ReadOnlyViolation, lambda: validate(interface))
    class DisabledRead(c.BrokerAdapter):
        get_positions = None
    disabled_denial = rejects(c.ReadOnlyViolation, lambda: validate(DisabledRead))
    # Candidate admission cannot loosen the existing operation dispatch gate.
    rejects(c.ReadOnlyViolation, lambda: c.enforce_read_only_operation("trade"))
    c.enforce_read_only_operation("get_positions")
    assert c.validate_broker_contract() is True
    return {"inherited_trade_denial": denial, "disabled_read_denial": disabled_denial, "original_direct_gate": "PASS"}


def fixture_canonicalize_ref(ref):
    """Audit-only candidate; normalize a validated ref without owner mutation."""
    return replace(ref, payload_sha256=ref.payload_sha256.lower())


def fixture_validate_interface(c, interface):
    """Audit-only candidate; inspect public callable members across the MRO."""
    effective = {}
    for base in reversed(interface.__mro__):
        effective.update(base.__dict__)
    public = {name for name, value in effective.items()
              if not name.startswith("_") and callable(value)}
    if public != c.READ_ONLY_CONNECTOR_OPERATIONS:
        raise c.ReadOnlyViolation("audit-only fixture: public interface differs from exact read-only allowlist")
    return True


def candidate_checks(c, fixture):
    results = []
    canonicalize = fixture_canonicalize_ref if fixture else lambda ref: ref
    validate = (lambda interface: fixture_validate_interface(c, interface)) if fixture else (lambda interface: original_interface_validator(c, interface))
    record_check(results, "direct_SourceRecordRef_digest_case_equivalence", lambda: test_direct_digest_case_equivalence(c, canonicalize))
    record_check(results, "inherited_callable_trade_drift_denied", lambda: test_inherited_callable_trade_denied(c, validate))
    return results


def controls(c):
    results = []
    ctx = c.TenantContext("t1", "u1")
    check = lambda name, operation: record_check(results, name, operation)
    check("foreign_tenant_read_denied", lambda: rejects(c.TenantIsolationError, lambda: c.require_tenant(ctx, "t2")))
    check("foreign_tenant_import_denied", lambda: rejects(c.TenantIsolationError, lambda: c.ImportLedger().ingest(ctx, source(c, tenant_id="t2"))))
    check("foreign_tenant_source_reconciliation_denied", lambda: rejects(c.TenantIsolationError, lambda: c.reconcile_records(ctx, (source(c, tenant_id="t2"),), ())))
    for field in ("tenant_id", "principal_id"):
        for value in ("", " ", "\t", None, 42):
            check(f"context_rejects_{field}_{value!r}", lambda field=field, value=value: rejects(ValueError, lambda: c.TenantContext(value if field == "tenant_id" else "t1", value if field == "principal_id" else "u1")))
    for field in ("tenant_id", "connection_id", "source_record_id", "source_version"):
        check("reference_rejects_blank_" + field, lambda field=field: rejects(ValueError, lambda: replace(source(c).ref, **{field: " "})))
    for digest in ("bad", "g" * 64, "a" * 63, "a" * 65, None, 42):
        check(f"reference_rejects_digest_{digest!r}", lambda digest=digest: rejects(ValueError, lambda: replace(source(c).ref, payload_sha256=digest)))
    for refs in ((), (42,), [source(c).ref], (source(c).ref, 42)):
        check(f"normalized_rejects_refs_{refs!r}", lambda refs=refs: rejects(ValueError, lambda: normalized(c, refs)))
    for field in ("tenant_id", "connection_id", "account_id", "source_record_id", "source_version", "record_type", "source", "raw_payload_ref", "payload_sha256"):
        check("source_rejects_blank_" + field, lambda field=field: rejects(ValueError, lambda: source(c, **{field: " "})))

    def ledger_control():
        ledger = c.ImportLedger()
        original = source(c)
        assert ledger.ingest(ctx, original) == c.ImportStatus.INSERTED
        assert ledger.ingest(ctx, original) == c.ImportStatus.DUPLICATE
        assert ledger.ingest(ctx, source(c, payload_sha256=H.upper())) == c.ImportStatus.DUPLICATE
        rejects(c.RecordIntegrityError, lambda: ledger.ingest(ctx, source(c, payload_sha256="b" * 64)))
        assert ledger.ingest(ctx, original) == c.ImportStatus.DUPLICATE
        assert ledger.ingest(ctx, source(c, source_version="v2", payload_sha256="b" * 64)) == c.ImportStatus.INSERTED
        return "INSERTED; identical/uppercase replay DUPLICATE; collision denied; original preserved; v2 INSERTED"

    check("import_duplicate_collision_preserves_prior_digest", ledger_control)
    check("source_frozen_assignment_denied", lambda: rejects(FrozenInstanceError, lambda: setattr(source(c), "account_id", "other")))
    check("normalized_frozen_assignment_denied", lambda: rejects(FrozenInstanceError, lambda: setattr(normalized(c), "source_refs", ())))
    a, b = source(c), source(c, source_record_id="b")
    check("complete_lineage_passes", lambda: equal(c.reconcile_records(ctx, (a, b), (normalized(c, (a.ref,), normalized_id="a"), normalized(c, (b.ref,), normalized_id="b")))["passed"], True))
    check("missing_lineage_fails", lambda: equal(c.reconcile_records(ctx, (a,), (normalized(c, (b.ref,)),))["missing"], (b.ref,)))
    check("orphan_lineage_fails", lambda: equal(c.reconcile_records(ctx, (a, b), (normalized(c, (a.ref,)),))["orphan"], (b.ref,)))
    check("duplicate_normalized_identity_fails", lambda: equal(c.reconcile_records(ctx, (a,), (normalized(c), normalized(c)))["duplicates"], ("n1",)))
    check("cross_tenant_normalized_row_fails", lambda: equal(c.reconcile_records(ctx, (a,), (normalized(c, tenant_id="t2"),))["cross_tenant"], ("n1",)))
    check("cross_tenant_ref_fails", lambda: equal(c.reconcile_records(ctx, (a,), (normalized(c, (source(c, tenant_id="t2").ref,)),))["cross_tenant"], ("n1",)))
    aliases = ("trade", "buy", "sell", "execute_trade", "create_order", "place_order", "submit_order", "cancel_order", "modify_order", "transfer", "withdraw", "deposit", "wire_transfer", "delete_account", " get_positions", "GET_POSITIONS", "get_positions ", "get_positions\x00", "")
    for operation in aliases:
        check(f"read_only_denies_{operation!r}", lambda operation=operation: rejects(c.ReadOnlyViolation, lambda: c.enforce_read_only_operation(operation)))
    for operation in sorted(c.READ_ONLY_CONNECTOR_OPERATIONS):
        check("read_only_allows_" + operation, lambda operation=operation: equal(c.enforce_read_only_operation(operation), None))
    check("broker_contract_exact_interface_passes", lambda: equal(c.validate_broker_contract(), True))

    def drift_add():
        setattr(c.BrokerAdapter, "trade", lambda self: None)
        try:
            return rejects(c.ReadOnlyViolation, c.validate_broker_contract)
        finally:
            delattr(c.BrokerAdapter, "trade")

    def drift_remove():
        original = c.BrokerAdapter.__dict__["get_positions"]
        delattr(c.BrokerAdapter, "get_positions")
        try:
            return rejects(c.ReadOnlyViolation, c.validate_broker_contract)
        finally:
            setattr(c.BrokerAdapter, "get_positions", original)

    check("broker_contract_public_write_alias_drift_denied", drift_add)
    check("broker_contract_missing_allowed_method_drift_denied", drift_remove)
    assert len(results) == 78
    return results


def observations(c):
    ctx, a = c.TenantContext("t1", "u1"), source(c)
    ledger = c.ImportLedger()
    ledger.ingest(ctx, a)
    conflicting = source(c, payload_sha256="b" * 64)
    interface = inherited_write_interface(c)
    return [
        {"name": "same_tenant_different_principal_replay", "value": ledger.ingest(c.TenantContext("t1", "u2"), a).value,
         "classification": "runtime user ownership boundary absent; no service exploit established"},
        {"name": "empty_lineage", "value": c.reconcile_records(ctx, (), ()),
         "classification": "set coverage only; cannot establish financial completeness"},
        {"name": "same_identity_same_digest_different_account_provenance", "value": ledger.ingest(ctx, replace(a, account_id="different-account", raw_payload_ref="fixture://changed-raw", source="DIFFERENT_PROVIDER", ingested_at=T + timedelta(days=1))).value,
         "classification": "declared-hash helper does not authenticate or retain raw/provenance metadata"},
        {"name": "uppercase_direct_ref", "value": c.reconcile_records(ctx, (a,), (normalized(c, (replace(a.ref, payload_sha256=H.upper()),)),)),
         "classification": "case-equivalent SHA-256 causes false missing/orphan; audit-only candidate below"},
        {"name": "duplicate_source_entries_same_ref", "value": c.reconcile_records(ctx, (a, a), (normalized(c),)),
         "classification": "set coverage ignores source multiplicity; contract decision required"},
        {"name": "source_ref_reuse_distinct_normalized_ids", "value": c.reconcile_records(ctx, (a,), (normalized(c, normalized_id="n1"), normalized(c, normalized_id="n2"))),
         "classification": "set coverage does not establish one-to-one financial normalization"},
        {"name": "same_identity_conflicting_hashes_reconciled", "value": c.reconcile_records(ctx, (a, conflicting), (normalized(c, (a.ref,), normalized_id="a"), normalized(c, (conflicting.ref,), normalized_id="b"))),
         "classification": "ledger separately rejects conflict; pre-admission requirement or lineage conflict reporting needed"},
        {"name": "inherited_public_write_alias_interface_probe", "value": {"trade_inherited": callable(getattr(interface, "trade")), "validation_passed": original_interface_validator(c, interface)},
         "classification": "synthetic interface drift gap; actual operation gate still denies trade"},
    ]


def counts(results):
    return {"passed": sum(result["result"] == "PASS" for result in results), "failed": sum(result["result"] == "FAIL" for result in results)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("red", "full"), default="full")
    args = parser.parse_args()
    c, tests, manifest = load_owner()
    if args.phase == "red":
        results = candidate_checks(c, fixture=False)
        report = {"phase": "original_owner_RED_reproduction", "owner_pin": PIN,
                  "candidate_counts": counts(results), "candidate_results": results,
                  "scope": "audit-only fixture; no owner/harness modification"}
        print(json.dumps(report, indent=2, default=str, sort_keys=True))
        return 1 if report["candidate_counts"]["failed"] else 0

    focused = []
    for name, test in inspect.getmembers(tests, inspect.isfunction):
        if name.startswith("test_") and test.__module__ == tests.__name__:
            record_check(focused, name, test)
    additional = controls(c)
    limits = observations(c)
    baseline = candidate_checks(c, fixture=False)
    candidate = candidate_checks(c, fixture=True)
    assert len(focused) == 9 and len(limits) == 8
    expected_red = all(result["result"] == "FAIL" and result["exception"] == "AssertionError" for result in baseline)
    prior_receipt = json.loads((ROOT / "implementation/docs/product_platform/evidence/validation.json").read_text())
    mismatches = []
    for item in prior_receipt["source_manifest"]:
        blob = (ROOT / item["path"]).read_bytes()
        if hashlib.sha256(blob).hexdigest() != item["sha256"] or len(blob) != item["bytes"]:
            mismatches.append(item["path"])
    report = {
        "schema": "independent-owner-probes-v1", "owner_pin": PIN,
        "runner": "source-pinned in-memory loader using owner mini_pytest shim, not pytest",
        "command": "python implementation/docs/product_platform/audits/storage_auth_2026-10-05/owner_probes.py",
        "scope": "audit-only; fixtures not deployed or owner-adopted; no production capability promotion",
        "owner_focused": {"counts": counts(focused), "results": focused},
        "additional_controls": {"counts": counts(additional), "results": additional},
        "separate_boundary_observations": limits,
        "repair_candidates": {"original_owner_expected_RED": {"counts": counts(baseline), "expected_assertion_failures_confirmed": expected_red, "results": baseline},
                              "audit_only_fixture_GREEN": {"counts": counts(candidate), "results": candidate},
                              "root_causes": ["SourceRecord.ref lowercases SHA-256; directly constructed SourceRecordRef retains original case", "validate_broker_contract inspects direct __dict__ and omits inherited public callable members"],
                              "owner_adoption": "NOT_REQUESTED / NOT_DEPLOYED"},
        "pinned_source_manifest": manifest,
        "source_identity_history": [{"revision": revision,
                                      "contracts_git_blob": git("rev-parse", f"{revision}:implementation/src/investment_system/platform/contracts.py").decode().strip(),
                                      "tests_git_blob": git("rev-parse", f"{revision}:implementation/tests/test_product_platform_contracts.py").decode().strip()}
                                     for revision in (EARLIER, REPAIR, PIN)],
        "runner_manifest": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "bytes": len(Path(__file__).read_bytes())},
        "previous_harness_source_preservation": {"manifest_entries_checked": len(prior_receipt["source_manifest"]), "mismatches": mismatches,
                                                 "existing_84_and_396_test_suites_rerun": False},
        "safety": {"package_initializers_executed": False,
                   "real_provider_modules_loaded": any(".providers" in name for name in sys.modules),
                   "credentials_read": False, "network_providers_invoked": False,
                   "owner_source_modified": False, "previous_19_harness_manifest_files_modified": bool(mismatches)},
    }
    failures = counts(focused)["failed"] + counts(additional)["failed"] + counts(candidate)["failed"]
    report["summary"] = {"owner_tests_passed": counts(focused)["passed"], "additional_controls_passed": counts(additional)["passed"],
                         "boundary_observations": len(limits), "baseline_expected_RED": counts(baseline)["failed"],
                         "audit_only_candidates_GREEN": counts(candidate)["passed"], "unexpected_failures": failures + (not expected_red) + bool(mismatches)}
    text = json.dumps(report, indent=2, default=str, sort_keys=True) + "\n"
    (HERE / "owner_probes.json").write_text(text)
    print(text, end="")
    return 1 if report["summary"]["unexpected_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
