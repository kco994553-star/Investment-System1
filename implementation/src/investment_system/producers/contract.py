"""PRODUCER_SNAPSHOT v1 — the common envelope every producer emits.

Data states are exactly the Web schema-1 states (product.web_mvp.STATES); no new state is
introduced here. STALE is a derived freshness of a LIVE snapshot (see freshness.py), not a
state. Research/provisional outputs are not publishable as LIVE or FROZEN_SNAPSHOT.
P01 is an additive publication envelope, not a new schema-1 state
(docs/producer_infrastructure/P01_APPROVAL_2026-10-02.md).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable, Mapping

from ..contracts.enums import CalibrationLifecycle
from ..product.web_mvp import SECTIONS, STATES
from .errors import (FreshnessContractError, IdentityError, MissingFieldError, ProvenanceError,
                     ResearchStatusError, SchemaVersionError, SourceHashError, SyntheticStateError,
                     TimestampError, UnsupportedStateError, ValidationStatusError)
from .serialization import canonical_sha256, sha256_hex

CONTRACT = 'PRODUCER_SNAPSHOT'
SCHEMA_VERSION = 1
SECTION_NAMES = ('universe', *SECTIONS)
SCOPE_KINDS = ('ENTITY_MAP', 'ROWS', 'DOCUMENT')
VALIDATION_STATUSES = ('PASS', 'FAIL', 'NOT_RUN')
PUBLISHED_STATES = ('LIVE', 'FROZEN_SNAPSHOT')
# Statuses that already exist in the repository and mean "not validated for publication".
RESEARCH_STATUSES = frozenset({'PROVISIONAL_RESEARCH'} | {s.value for s in (
    CalibrationLifecycle.IDEA, CalibrationLifecycle.RESEARCH, CalibrationLifecycle.PROVISIONAL,
    CalibrationLifecycle.PROVISIONAL_INITIAL_PRIOR)})
REQUIRED = ('contract', 'schema_version', 'producer_id', 'producer_version', 'section', 'data_state',
            'requested_as_of', 'as_of', 'generated_at', 'expires_at', 'methodology', 'synthetic',
            'provenance', 'validation', 'scope', 'data', 'data_sha256', 'reason')
_HEX64 = re.compile(r'^[0-9a-f]{64}$')


def parse_ts(value: Any, field: str, required: bool = True) -> datetime | None:
    """Strict tz-aware ISO-8601. Naive or unparsable timestamps fail closed."""
    if value is None:
        if required:
            raise MissingFieldError('timestamp required', field)
        return None
    if not isinstance(value, str):
        raise TimestampError('timestamp must be an ISO-8601 string', field)
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as e:
        raise TimestampError(f'unparsable timestamp {value!r}', field) from e
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise TimestampError('timestamp must be timezone-aware', field)
    return dt


def contains_synthetic_marker(v: Any) -> bool:
    """Same predicate as the Web schema-1 validator (product.web_mvp.validate_bundle)."""
    if isinstance(v, dict):
        return (v.get('synthetic') is True or v.get('synthetic_qgv') is True or v.get('kind') == 'SYNTHETIC'
                or any(contains_synthetic_marker(x) for x in v.values()))
    return isinstance(v, list) and any(contains_synthetic_marker(x) for x in v)


def _nonempty_str(s: Mapping, key: str, where: str | None = None) -> str:
    v = s.get(key)
    if not isinstance(v, str) or not v.strip():
        raise MissingFieldError('non-empty string required', f'{where}.{key}' if where else key)
    return v


def _entity_ids(scope_kind: str, data: Any) -> list[str] | None:
    if scope_kind == 'ENTITY_MAP':
        if not isinstance(data, dict):
            raise IdentityError('ENTITY_MAP data must be an object keyed by entity id', 'data')
        return sorted(data)
    if scope_kind == 'ROWS':
        rows = data.get('rows') if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise IdentityError('ROWS data must be an object with a rows list', 'data')
        ids = [r.get('company_id') if isinstance(r, dict) else None for r in rows]
        if any(not isinstance(i, str) or not i for i in ids):
            raise IdentityError('every row needs a company_id', 'data.rows')
        return sorted(set(ids))
    return None


def make_snapshot(*, producer_id: str, producer_version: str, section: str, data_state: str,
                  as_of: str | None, generated_at: str, methodology: Mapping[str, str], synthetic: bool,
                  provenance: Mapping[str, Any], validation: Mapping[str, Any], data: Any,
                  scope_kind: str = 'DOCUMENT', requested_as_of: str | None = None,
                  expires_at: str | None = None, usable_until: str | None = None,
                  reason: str | None = None, reason_code: str | None = None) -> dict:
    """Build a snapshot with computed scope/data hash. Does not validate; call validate_snapshot."""
    prov = dict(provenance)
    prov['inputs'] = sorted((dict(i) for i in prov.get('inputs', [])), key=lambda i: str(i.get('artifact_id')))
    snap = {
        'contract': CONTRACT, 'schema_version': SCHEMA_VERSION,
        'producer_id': producer_id, 'producer_version': producer_version, 'section': section,
        'data_state': data_state, 'requested_as_of': requested_as_of, 'as_of': as_of,
        'generated_at': generated_at, 'expires_at': expires_at, 'usable_until': usable_until,
        'methodology': dict(methodology), 'synthetic': synthetic, 'provenance': prov,
        'validation': dict(validation),
        'scope': {'kind': scope_kind, 'entity_ids': None if data is None else _entity_ids(scope_kind, data)},
        'data': data, 'data_sha256': None if data is None else canonical_sha256(data),
        'reason': reason, 'reason_code': reason_code,
    }
    return snap


def not_available(section: str, producer_id: str, producer_version: str, generated_at: str,
                  reason: str, reason_code: str, requested_as_of: str | None = None,
                  methodology: Mapping[str, str] | None = None) -> dict:
    """Explicit absence. Valid snapshot; never carries data."""
    return make_snapshot(producer_id=producer_id, producer_version=producer_version, section=section,
                         data_state='NOT_AVAILABLE', as_of=None, generated_at=generated_at,
                         methodology=methodology or {'id': 'NONE', 'version': 'NONE', 'status': 'NOT_AVAILABLE'},
                         synthetic=False, provenance={'source': None, 'inputs': []},
                         validation={'status': 'NOT_RUN', 'checks': []}, data=None,
                         requested_as_of=requested_as_of, reason=reason, reason_code=reason_code)


def validate_snapshot(s: Any) -> dict:
    """Fail-closed validation of one PRODUCER_SNAPSHOT v1. Returns the snapshot unchanged."""
    if not isinstance(s, dict):
        raise SchemaVersionError('snapshot must be an object')
    if s.get('contract') != CONTRACT:
        raise SchemaVersionError(f'contract must be {CONTRACT}', 'contract')
    if s.get('schema_version') != SCHEMA_VERSION:
        raise SchemaVersionError(f'unsupported schema_version {s.get("schema_version")!r}', 'schema_version')
    for k in REQUIRED:
        if k not in s:
            raise MissingFieldError('required field absent', k)
    _nonempty_str(s, 'producer_id')
    _nonempty_str(s, 'producer_version')
    if s['section'] not in SECTION_NAMES:
        raise IdentityError(f'unknown section {s["section"]!r}', 'section')
    state = s['data_state']
    if state not in STATES:
        raise UnsupportedStateError(f'{state!r} is not a Web schema-1 data state', 'data_state')
    generated = parse_ts(s['generated_at'], 'generated_at')
    requested = parse_ts(s['requested_as_of'], 'requested_as_of', required=False)
    if not isinstance(s['synthetic'], bool):
        raise MissingFieldError('boolean required', 'synthetic')
    if state == 'NOT_AVAILABLE':
        if s['data'] is not None or s['data_sha256'] is not None:
            raise UnsupportedStateError('NOT_AVAILABLE must not carry data', 'data')
        _nonempty_str(s, 'reason')
        return s
    as_of = parse_ts(s['as_of'], 'as_of')
    if as_of > generated:
        raise FreshnessContractError('as_of is later than generated_at', 'as_of')
    if requested is not None and as_of > requested:
        raise FreshnessContractError('actual data as_of is later than requested_as_of', 'as_of')
    expires = parse_ts(s['expires_at'], 'expires_at', required=(state == 'LIVE'))
    usable = parse_ts(s.get('usable_until'), 'usable_until', required=False)
    if expires is not None and expires <= as_of:
        raise FreshnessContractError('expires_at must be later than as_of', 'expires_at')
    if usable is not None and (expires is None or usable < expires):
        raise FreshnessContractError('usable_until requires expires_at and must not precede it', 'usable_until')
    m = s['methodology']
    if not isinstance(m, dict):
        raise MissingFieldError('object required', 'methodology')
    for k in ('id', 'version', 'status'):
        _nonempty_str(m, k, 'methodology')
    p = s['provenance']
    if not isinstance(p, dict):
        raise ProvenanceError('object required', 'provenance')
    if not isinstance(p.get('source'), str) or not p['source'].strip():
        raise ProvenanceError('provenance.source required', 'provenance.source')
    inputs = p.get('inputs')
    if not isinstance(inputs, list) or not inputs:
        raise ProvenanceError('at least one hashed source input required', 'provenance.inputs')
    seen = set()
    for i in inputs:
        if not isinstance(i, dict) or not isinstance(i.get('artifact_id'), str) or not i['artifact_id']:
            raise ProvenanceError('input needs artifact_id', 'provenance.inputs')
        if i['artifact_id'] in seen:
            raise ProvenanceError(f'duplicate input {i["artifact_id"]}', 'provenance.inputs')
        seen.add(i['artifact_id'])
        if not isinstance(i.get('sha256'), str) or not _HEX64.match(i['sha256']):
            raise SourceHashError(f'invalid sha256 for {i["artifact_id"]}', 'provenance.inputs')
    if s['data'] is None:
        raise MissingFieldError('data required unless NOT_AVAILABLE', 'data')
    if s['data_sha256'] != canonical_sha256(s['data']):
        raise SourceHashError('data_sha256 does not match canonical data', 'data_sha256')
    scope = s['scope']
    if not isinstance(scope, dict) or scope.get('kind') not in SCOPE_KINDS:
        raise IdentityError('scope.kind must be one of ' + ', '.join(SCOPE_KINDS), 'scope')
    if scope.get('entity_ids') != _entity_ids(scope['kind'], s['data']):
        raise IdentityError('scope.entity_ids does not match data', 'scope.entity_ids')
    marked = contains_synthetic_marker(s['data'])
    if marked and not s['synthetic']:
        raise SyntheticStateError('data carries a synthetic marker but synthetic=false', 'synthetic')
    if s['synthetic'] and state != 'DEMO':
        raise SyntheticStateError('synthetic output may only be DEMO', 'data_state')
    v = s['validation']
    if not isinstance(v, dict) or v.get('status') not in VALIDATION_STATUSES:
        raise ValidationStatusError('validation.status must be one of ' + ', '.join(VALIDATION_STATUSES), 'validation')
    if state in PUBLISHED_STATES:
        if v['status'] != 'PASS':
            raise ValidationStatusError(f'{state} requires producer validation PASS', 'validation.status')
        if m['status'] in RESEARCH_STATUSES:
            raise ResearchStatusError(f'methodology status {m["status"]} cannot be published as {state} '
                                      '(P01 keeps schema-1 unchanged; a research lifecycle is not a grant)',
                                      'methodology.status')
    return s


def verify_inputs(s: dict, resolver: Callable[[str], bytes | None]) -> list[str]:
    """Recompute every source input hash from actual bytes. Unresolvable or mismatched -> error."""
    validate_snapshot(s)
    checked = []
    for i in s['provenance']['inputs']:
        body = resolver(i['artifact_id'])
        if body is None:
            raise ProvenanceError(f'source input not resolvable: {i["artifact_id"]}', 'provenance.inputs')
        if sha256_hex(body) != i['sha256']:
            raise SourceHashError(f'source bytes do not match sha256: {i["artifact_id"]}', 'provenance.inputs')
        if 'bytes' in i and i['bytes'] != len(body):
            raise SourceHashError(f'source size mismatch: {i["artifact_id"]}', 'provenance.inputs')
        checked.append(i['artifact_id'])
    return checked


def file_resolver(root) -> Callable[[str], bytes | None]:
    """artifact_id 'file:<relative path>' resolved under root; no path escape."""
    from pathlib import Path
    base = Path(root).resolve()

    def resolve(artifact_id: str) -> bytes | None:
        if not artifact_id.startswith('file:'):
            return None
        p = (base / artifact_id[5:]).resolve()
        if base not in p.parents or not p.is_file():
            return None
        return p.read_bytes()
    return resolve


def store_resolver(store) -> Callable[[str], bytes | None]:
    """artifact_id 'raw:<RawDatasetStore id>' resolved from an existing RawDatasetStore."""
    def resolve(artifact_id: str) -> bytes | None:
        if not artifact_id.startswith('raw:'):
            return None
        aid = artifact_id[4:]
        return store.get_bytes(aid) if store.has(aid) else None
    return resolve
