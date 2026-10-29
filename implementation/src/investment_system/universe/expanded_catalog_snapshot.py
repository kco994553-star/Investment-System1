"""Pure private dry-run receipts and deterministic catalog encoding.

This module writes nothing. It is neither a collector nor an atomic file
publisher; E1-B must supply its own authorized adapter and durable transaction.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json

from .expanded_catalog import CatalogError, clock, require, require_catalog
from .expanded_catalog_events import CatalogDiff, apply_listing_events, diff_snapshots

_SOURCE_ERRORS = frozenset(('HTTP_429', 'SOURCE_INTERRUPTED', 'SOURCE_CORRUPT'))
_CATALOG_ERRORS = frozenset((
    'SCHEMA_INVALID', 'INVALID_TIMESTAMP', 'INVALID_TIME_ORDER', 'IDENTITY_AMBIGUOUS',
    'EXCHANGE_UNSUPPORTED', 'POLICY_MISMATCH', 'DUPLICATE_EVENT', 'SNAPSHOT_PROVENANCE_MISMATCH',
    'EVENT_ID_CONFLICT', 'EVENT_ORDER_AMBIGUOUS', 'SECURITY_ID_REUSED', 'SECURITY_NOT_ACTIVE',
    'EVENT_PAYLOAD_MISMATCH', 'EVENT_NO_CHANGE', 'MERGER_TARGET_UNRESOLVED',
    'TICKER_INTERVAL_OVERLAP', 'CUTOFF_REGRESSION',
))


def _encode(value):
    if type(value) is datetime:
        return clock(value).isoformat().replace('+00:00', 'Z')
    if type(value) is dict:
        return {key: _encode(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_encode(item) for item in value]
    return value


def _bytes(value):
    return json.dumps(_encode(value), sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('utf-8')


def input_manifest_hash(snapshot):
    require_catalog(snapshot)
    return hashlib.sha256(_bytes([asdict(e) for e in snapshot.events])).hexdigest()


def snapshot_bytes(snapshot):
    """Private canonical content only; universe_version is its SHA-256.

    The hash is not embedded in its own preimage. No deserialize/public producer
    is provided; callers must keep this metadata in an authorized private path.
    """
    require_catalog(snapshot)
    value = asdict(snapshot)
    value.update(source_cutoff_at=snapshot.source_cutoff_at,
                 issuer_count=snapshot.issuer_count, security_count=snapshot.security_count,
                 included=[r.security_id for r in snapshot.included],
                 excluded_reason_counts=dict(snapshot.excluded_reason_counts),
                 input_manifest_hash=input_manifest_hash(snapshot))
    return _bytes(value)


def snapshot_hash(snapshot):
    return hashlib.sha256(snapshot_bytes(snapshot)).hexdigest()


@dataclass(frozen=True)
class RefreshReceipt:
    status: str
    attempted_at: datetime
    last_success_at: datetime | None
    source_cutoff_at: datetime | None
    source_id: str
    input_hash: str
    added: int
    ended: int
    changed: int
    unchanged: int
    ambiguous: int
    fail_count: int
    reason_codes: tuple[str, ...]
    previous_snapshot_version: str
    new_snapshot_version: str
    issuer_count: int
    security_count: int
    source_rights: str = 'UNVERIFIED'
    real_data_executed: bool = False


@dataclass(frozen=True)
class RefreshOutcome:
    snapshot: object
    receipt: RefreshReceipt


def render_private_receipt(snapshot, diff, status, *, previous, attempted_at,
                           last_success_at=None, reason_codes=()):
    """Aggregate-only diagnostics. Arbitrary messages/keys are never accepted.

    last_success_at belongs to the supplied previous dry-run receipt, not to
    effective/available/as_of. No success timestamp is fabricated from those.
    """
    require(type(status) is str and status in ('SYNTHETIC_PASS', 'FAILED'))
    require_catalog(previous)
    require_catalog(snapshot)
    attempted_at = clock(attempted_at)
    require(attempted_at >= snapshot.as_of, 'INVALID_TIME_ORDER')
    require(type(reason_codes) is tuple and all(type(c) is str and c in
            (_SOURCE_ERRORS | _CATALOG_ERRORS) for c in reason_codes))
    require((status == 'FAILED') == bool(reason_codes))
    require(type(diff) is CatalogDiff and diff == diff_snapshots(previous, snapshot))
    if status == 'FAILED':
        require(snapshot == previous)
    if last_success_at is not None:
        last_success_at = clock(last_success_at)
        require(last_success_at <= attempted_at, 'INVALID_TIME_ORDER')
    return RefreshReceipt(status, attempted_at, attempted_at if status == 'SYNTHETIC_PASS' else last_success_at,
                          snapshot.source_cutoff_at, 'SYNTHETIC_SUPPLIED', input_manifest_hash(snapshot),
                          len(diff.added), len(diff.ended), len(diff.changed), len(diff.unchanged),
                          int('IDENTITY_AMBIGUOUS' in reason_codes), int(status == 'FAILED'), reason_codes,
                          snapshot_hash(previous), snapshot_hash(snapshot),
                          snapshot.issuer_count, snapshot.security_count)


def dry_run_refresh(previous, events, cutoff, attempted_at, *, source_status='OK', last_success_at=None):
    """In-memory batch transaction. Supply source failure codes; never call I/O.

    A failed validation returns the exact previous object. Invalid controls or
    an invalid previous snapshot raise fixed errors rather than being relabelled
    as recoverable source failures. Successful validation is synthetic only.
    """
    require_catalog(previous)
    cutoff, attempted_at = clock(cutoff), clock(attempted_at)
    require(cutoff >= previous.as_of, 'CUTOFF_REGRESSION')
    require(attempted_at >= cutoff, 'INVALID_TIME_ORDER')
    require(type(source_status) is str and source_status in (_SOURCE_ERRORS | {'OK'}))
    if last_success_at is not None:
        last_success_at = clock(last_success_at)
        require(last_success_at <= attempted_at, 'INVALID_TIME_ORDER')
    reasons = ()
    result = previous
    if source_status != 'OK':
        reasons = (source_status,)
    else:
        try:
            result = apply_listing_events(previous, events, cutoff)
            require(all(e.collected_at <= attempted_at for e in result.events), 'INVALID_TIME_ORDER')
        except CatalogError as exc:
            require(str(exc) in _CATALOG_ERRORS)
            reasons = (str(exc),)
            result = previous
    diff = diff_snapshots(previous, result)
    receipt = render_private_receipt(result, diff, 'FAILED' if reasons else 'SYNTHETIC_PASS',
                                     previous=previous, attempted_at=attempted_at,
                                     last_success_at=last_success_at, reason_codes=reasons)
    return RefreshOutcome(result, receipt)
