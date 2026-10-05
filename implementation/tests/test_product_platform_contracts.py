"""Product Platform contract tests."""
from datetime import datetime, timedelta, timezone

import pytest

from investment_system.personal import ports as personal_ports
from investment_system.platform.contracts import (
    ImportLedger,
    ImportStatus,
    NormalizedFinancialRecord,
    ReadOnlyViolation,
    RecordIntegrityError,
    SourceRecord,
    TenantContext,
    TenantIsolationError,
    enforce_read_only_operation,
    reconcile_records,
    require_tenant,
    validate_broker_contract,
)

UTC = timezone.utc
T0 = datetime(2026, 10, 5, 3, 0, tzinfo=UTC)
H = "a" * 64


def row(tenant="t1", rid="r1", version="v1", digest=H):
    return SourceRecord(
        tenant,
        "conn",
        "acct",
        rid,
        version,
        "POSITION",
        T0 - timedelta(minutes=2),
        T0 - timedelta(minutes=1),
        T0,
        "FIXTURE_PROVIDER",
        f"fixture://{tenant}/{rid}/{version}",
        digest,
    )


def test_read_only_gate_is_exact_and_detects_broker_contract_drift():
    methods = {
        n for n, v in personal_ports.BrokerAdapter.__dict__.items()
        if not n.startswith("_") and callable(v)
    }
    assert "get_positions" in methods and "sync" in methods
    assert not methods & set(personal_ports.FORBIDDEN_BROKER_METHODS)
    assert validate_broker_contract() is True
    enforce_read_only_operation("get_positions")
    enforce_read_only_operation("sync")
    for op in (*personal_ports.FORBIDDEN_BROKER_METHODS, "delete_account", "trade"):
        with pytest.raises(ReadOnlyViolation):
            enforce_read_only_operation(op)


def test_tenant_scope_is_fail_closed():
    ctx = TenantContext("t1", "u1")
    require_tenant(ctx, "t1")
    with pytest.raises(TenantIsolationError):
        require_tenant(ctx, "t2")
    with pytest.raises(TenantIsolationError):
        require_tenant(ctx, "")


def test_source_record_requires_provenance_time_and_hash():
    assert row().ref.payload_sha256 == H
    with pytest.raises(ValueError):
        SourceRecord(
            "t1", "c", "a", "r", "v1", "POSITION",
            T0.replace(tzinfo=None), T0, T0, "src", "ref", H,
        )
    with pytest.raises(ValueError):
        SourceRecord(
            "t1", "c", "a", "r", "v1", "POSITION",
            T0, T0 - timedelta(minutes=1), T0, "src", "ref", H,
        )


def test_import_is_idempotent_and_same_version_content_change_fails():
    ctx = TenantContext("t1", "u1")
    ledger = ImportLedger()
    first = row()
    assert ledger.ingest(ctx, first) == ImportStatus.INSERTED
    assert ledger.ingest(ctx, first) == ImportStatus.DUPLICATE
    with pytest.raises(RecordIntegrityError):
        ledger.ingest(ctx, row(digest="b" * 64))
    assert ledger.ingest(ctx, row(version="v2", digest="b" * 64)) == ImportStatus.INSERTED


def test_import_rejects_cross_tenant():
    with pytest.raises(TenantIsolationError):
        ImportLedger().ingest(TenantContext("t1", "u1"), row(tenant="t2"))


def test_reconciliation_lineage_and_full_coverage():
    ctx = TenantContext("t1", "u1")
    a, b = row(rid="a"), row(rid="b")
    rows = (
        NormalizedFinancialRecord("t1", "na", "POSITION", (a.ref,)),
        NormalizedFinancialRecord("t1", "nb", "POSITION", (b.ref,)),
    )
    assert reconcile_records(ctx, (a, b), rows)["passed"]
    orphan = reconcile_records(ctx, (a, b), rows[:1])
    assert not orphan["passed"] and orphan["orphan"] == (b.ref,)
    missing = row(rid="c").ref
    report = reconcile_records(
        ctx,
        (a,),
        (NormalizedFinancialRecord("t1", "n", "POSITION", (missing,)),),
    )
    assert not report["passed"] and report["missing"] == (missing,)


def test_reconciliation_rejects_duplicate_and_cross_tenant_outputs():
    ctx = TenantContext("t1", "u1")
    a = row(rid="a")
    duplicate = (
        NormalizedFinancialRecord("t1", "same", "POSITION", (a.ref,)),
        NormalizedFinancialRecord("t1", "same", "POSITION", (a.ref,)),
    )
    assert reconcile_records(ctx, (a,), duplicate)["duplicates"] == ("same",)
    cross = reconcile_records(
        ctx,
        (a,),
        (NormalizedFinancialRecord("t2", "other", "POSITION", (a.ref,)),),
    )
    assert cross["cross_tenant"] == ("other",) and not cross["passed"]
