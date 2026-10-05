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

READ_ONLY_CONNECTOR_OPERATIONS=frozenset(
    n for n,v in BrokerAdapter.__dict__.items()
    if not n.startswith("_") and callable(v)
)
FORBIDDEN_FINANCIAL_OPERATIONS=frozenset(FORBIDDEN_BROKER_METHODS)

def enforce_read_only_operation(operation):
    if operation not in READ_ONLY_CONNECTOR_OPERATIONS:
        raise ReadOnlyViolation("operation denied by read-only gate")

def _aware(name, value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")

@dataclass(frozen=True,order=True)
class SourceRecordRef:
    tenant_id:str
    connection_id:str
    source_record_id:str
    source_version:str
    payload_sha256:str

@dataclass(frozen=True)
class SourceRecord:
    tenant_id:str
    connection_id:str
    source_record_id:str
    source_version:str
    observed_at:datetime
    available_at:datetime
    ingested_at:datetime
    raw_payload_ref:str
    payload_sha256:str
    def __post_init__(self):
        vals=(self.tenant_id,self.connection_id,self.source_record_id,self.source_version,self.raw_payload_ref,self.payload_sha256)
        if any(not v for v in vals):
            raise ValueError("source identity/provenance required")
        for n in ("observed_at","available_at","ingested_at"):
            _aware(n,getattr(self,n))
        if self.observed_at>self.available_at or self.available_at>self.ingested_at:
            raise ValueError("invalid source time order")
        d=self.payload_sha256.lower()
        if len(d)!=64 or any(c not in "0123456789abcdef" for c in d):
            raise ValueError("invalid sha256")
    @property
    def ref(self):
        return SourceRecordRef(self.tenant_id,self.connection_id,self.source_record_id,self.source_version,self.payload_sha256.lower())
    @property
    def identity(self):
        return (self.tenant_id,self.connection_id,self.source_record_id,self.source_version)

class ImportStatus(str,Enum):
    INSERTED="INSERTED"
    DUPLICATE="DUPLICATE"

class ImportLedger:
    def __init__(self):
        self._seen={}
    def ingest(self,ctx,record):
        require_tenant(ctx,record.tenant_id)
        digest=record.payload_sha256.lower()
        old=self._seen.get(record.identity)
        if old is None:
            self._seen[record.identity]=digest
            return ImportStatus.INSERTED
        if old==digest:
            return ImportStatus.DUPLICATE
        raise RecordIntegrityError("same source version changed content")

@dataclass(frozen=True)
class NormalizedFinancialRecord:
    tenant_id:str
    normalized_id:str
    source_refs:tuple
    def __post_init__(self):
        if not self.tenant_id or not self.normalized_id or not self.source_refs:
            raise ValueError("normalized identity and lineage required")

def reconcile_records(ctx,sources,rows):
    sources=tuple(sources); rows=tuple(rows)
    for s in sources:
        require_tenant(ctx,s.tenant_id)
    known={s.ref for s in sources}; used=set(); missing=set(); cross=set()
    ids=[r.normalized_id for r in rows]
    dup=tuple(sorted({x for x in ids if ids.count(x)>1}))
    for row in rows:
        if row.tenant_id!=ctx.tenant_id:
            cross.add(row.normalized_id)
            continue
        for ref in row.source_refs:
            if ref.tenant_id!=ctx.tenant_id:
                cross.add(row.normalized_id)
            else:
                used.add(ref)
                if ref not in known:
                    missing.add(ref)
    orphan=known-used
    return {
        "missing":tuple(sorted(missing)),
        "orphan":tuple(sorted(orphan)),
        "duplicates":dup,
        "cross_tenant":tuple(sorted(cross)),
        "passed":not missing and not orphan and not dup and not cross,
    }
