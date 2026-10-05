"""Fail-closed Product Platform contracts. Non-production."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..personal.ports import BrokerAdapter, FORBIDDEN_BROKER_METHODS


class TenantIsolationError(PermissionError):
    pass


class ReadOnlyViolation(PermissionError):
    pass


class RecordIntegrityError(ValueError):
    pass


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    principal_id: str

    def __post_init__(self):
        if not self.tenant_id or not self.principal_id:
            raise ValueError("tenant_id and principal_id required")


def require_tenant(ctx, tenant_id):
    if not tenant_id or ctx.tenant_id != tenant_id:
        raise TenantIsolationError("cross-tenant access denied")


READ_ONLY_CONNECTOR_OPERATIONS = frozenset({
    "connect",
    "refresh_auth",
    "disconnect",
    "get_capabilities",
    "get_accounts",
    "get_balances",
    "get_positions",
    "get_transactions",
    "get_orders",
    "get_sync_status",
    "sync",
})
FORBIDDEN_FINANCIAL_OPERATIONS = frozenset(FORBIDDEN_BROKER_METHODS)


def enforce_read_only_operation(operation):
    if operation not in READ_ONLY_CONNECTOR_OPERATIONS:
        raise ReadOnlyViolation("operation denied by read-only gate")


def validate_broker_contract():
    public = frozenset(
        name for name, value in BrokerAdapter.__dict__.items()
        if not name.startswith("_") and callable(value)
    )
    missing = READ_ONLY_CONNECTOR_OPERATIONS - public
    forbidden_exposed = public & FORBIDDEN_FINANCIAL_OPERATIONS
    unexpected = public - READ_ONLY_CONNECTOR_OPERATIONS
    if missing or forbidden_exposed or unexpected:
        raise ReadOnlyViolation(
            f"BrokerAdapter drift: missing={sorted(missing)}, "
            f"forbidden={sorted(forbidden_exposed)}, unexpected={sorted(unexpected)}"
        )
    return True


def _aware(name, value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True, order=True)
class SourceRecordRef:
    tenant_id: str
    connection_id: str
    source_record_id: str
    source_version: str
    payload_sha256: str


@dataclass(frozen=True)
class SourceRecord:
    tenant_id: str
    connection_id: str
    account_id: str
    source_record_id: str
    source_version: str
    record_type: str
    observed_at: datetime
    available_at: datetime
    ingested_at: datetime
    source: str
    raw_payload_ref: str
    payload_sha256: str

    def __post_init__(self):
        vals = (
            self.tenant_id,
            self.connection_id,
            self.account_id,
            self.source_record_id,
            self.source_version,
            self.record_type,
            self.source,
            self.raw_payload_ref,
            self.payload_sha256,
        )
        if any(not value for value in vals):
            raise ValueError("source identity/provenance required")
        for name in ("observed_at", "available_at", "ingested_at"):
            _aware(name, getattr(self, name))
        if self.observed_at > self.available_at or self.available_at > self.ingested_at:
            raise ValueError("invalid source time order")
        digest = self.payload_sha256.lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid sha256")

    @property
    def ref(self):
        return SourceRecordRef(
            self.tenant_id,
            self.connection_id,
            self.source_record_id,
            self.source_version,
            self.payload_sha256.lower(),
        )

    @property
    def identity(self):
        return (
            self.tenant_id,
            self.connection_id,
            self.source_record_id,
            self.source_version,
        )


class ImportStatus(str, Enum):
    INSERTED = "INSERTED"
    DUPLICATE = "DUPLICATE"


class ImportLedger:
    def __init__(self):
        self._seen = {}

    def ingest(self, ctx, record):
        require_tenant(ctx, record.tenant_id)
        digest = record.payload_sha256.lower()
        old = self._seen.get(record.identity)
        if old is None:
            self._seen[record.identity] = digest
            return ImportStatus.INSERTED
        if old == digest:
            return ImportStatus.DUPLICATE
        raise RecordIntegrityError("same source version changed content")


@dataclass(frozen=True)
class NormalizedFinancialRecord:
    tenant_id: str
    normalized_id: str
    record_type: str
    source_refs: tuple

    def __post_init__(self):
        if not self.tenant_id or not self.normalized_id or not self.record_type or not self.source_refs:
            raise ValueError("normalized identity and lineage required")


def reconcile_records(ctx, sources, rows):
    sources = tuple(sources)
    rows = tuple(rows)
    for source in sources:
        require_tenant(ctx, source.tenant_id)
    known = {source.ref for source in sources}
    used = set()
    missing = set()
    cross = set()
    ids = [row.normalized_id for row in rows]
    duplicates = tuple(sorted({value for value in ids if ids.count(value) > 1}))
    for row in rows:
        if row.tenant_id != ctx.tenant_id:
            cross.add(row.normalized_id)
            continue
        for ref in row.source_refs:
            if ref.tenant_id != ctx.tenant_id:
                cross.add(row.normalized_id)
            else:
                used.add(ref)
                if ref not in known:
                    missing.add(ref)
    orphan = known - used
    return {
        "missing": tuple(sorted(missing)),
        "orphan": tuple(sorted(orphan)),
        "duplicates": duplicates,
        "cross_tenant": tuple(sorted(cross)),
        "passed": not missing and not orphan and not duplicates and not cross,
    }
