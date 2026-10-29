"""Price-free discovery catalog types. No acquisition, persistence or publication.

Identifiers are supplied evidence, never inferred from a current ticker. The
existing issuer CIK convention is reused only after strict ASCII validation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re

from .resolve import company_id_for

SCHEMA_VERSION = 'expanded-catalog/1'
UNIVERSE_ID = 'U-US-DISCOVERY'
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9:._/-]{0,127}', re.ASCII)
_TICKER = re.compile(r'[A-Z0-9][A-Z0-9.\-]{0,15}', re.ASCII)
_CLOCK = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})')
_SENSITIVE = re.compile(r'(?i)bearer\s|(?:secret|token|password|api[_-]?key)\s*[:=]|ya29\.|gh[pousr]_|github_pat_|sk-[A-Za-z0-9]|docs\.google\.com/spreadsheets/|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
SECURITY_TYPES = frozenset(('COMMON', 'COMMON_CLASS', 'ADR', 'REIT', 'ETF',
                           'CLOSED_END_FUND', 'PREFERRED', 'WARRANT', 'RIGHT', 'UNIT'))


class CatalogError(ValueError):
    """Fixed diagnostics only: never attach offending input or upstream messages."""


def require(condition, code='SCHEMA_INVALID'):
    if not condition:
        raise CatalogError(code)


def clock(value):
    if type(value) is str and _CLOCK.fullmatch(value):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            raise CatalogError('INVALID_TIMESTAMP') from None
    require(type(value) is datetime and value.utcoffset() is not None, 'INVALID_TIMESTAMP')
    try:
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise CatalogError('INVALID_TIMESTAMP') from None


def identifier(value):
    return type(value) is str and _ID.fullmatch(value) is not None and not _SENSITIVE.search(value)


def safe_name(value):
    return (type(value) is str and 0 < len(value) <= 200 and value == value.strip()
            and all(c.isprintable() for c in value) and not _SENSITIVE.search(value))


@dataclass(frozen=True)
class CatalogPolicy:
    exchanges: tuple[str, ...] = ('NASDAQ', 'NYSE', 'NYSE_AMERICAN', 'BATS')
    adr_policy: str = 'PENDING'
    reit_policy: str = 'PENDING'


def require_policy(policy):
    require(type(policy) is CatalogPolicy and type(policy.exchanges) is tuple)
    require(bool(policy.exchanges) and all(identifier(x) for x in policy.exchanges))
    require(len(set(policy.exchanges)) == len(policy.exchanges))
    require(policy.adr_policy in ('INCLUDE', 'EXCLUDE', 'PENDING')
            and policy.reit_policy in ('INCLUDE', 'EXCLUDE', 'PENDING'))


@dataclass(frozen=True)
class Rejection:
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, repr=False)
class SecurityRecord:
    issuer_id: str
    cik: str
    security_id: str
    ticker: str
    exchange: str
    security_type: str
    display_name: str
    valid_from: datetime
    valid_to: datetime | None
    status: str
    source_ref: str
    eligibility: str
    reason_codes: tuple[str, ...]

    def __repr__(self):
        return 'SecurityRecord(<private>)'


RAW_KEYS = frozenset(('issuer_id', 'cik', 'security_id', 'ticker', 'exchange',
                      'security_type', 'display_name', 'valid_from', 'valid_to', 'status', 'source_ref'))


def eligibility(kind, policy):
    if kind in ('COMMON', 'COMMON_CLASS'):
        return 'INCLUDED', ()
    if kind in ('ADR', 'REIT'):
        decision = policy.adr_policy if kind == 'ADR' else policy.reit_policy
        if decision == 'INCLUDE':
            return 'INCLUDED', ()
        if decision == 'PENDING':
            return 'PENDING', ('SOURCE_POLICY_PENDING',)
    return 'EXCLUDED', ('SECURITY_TYPE_EXCLUDED',)


def normalize_security_record(raw, policy):
    """Validate one supplied listing interval, returning only fixed rejections."""
    try:
        require_policy(policy)
        require(type(raw) is dict and set(raw) == RAW_KEYS)
        cik = raw['cik']
        require(type(cik) in (str, int), 'IDENTITY_AMBIGUOUS')
        cik = str(cik)
        require(re.fullmatch(r'[0-9]{1,10}', cik) is not None and int(cik) > 0, 'IDENTITY_AMBIGUOUS')
        cik = cik.zfill(10)
        require(raw['issuer_id'] == company_id_for(cik), 'IDENTITY_AMBIGUOUS')
        require(identifier(raw['security_id']) and identifier(raw['source_ref']))
        require(type(raw['ticker']) is str and _TICKER.fullmatch(raw['ticker']) is not None)
        require(type(raw['exchange']) is str and raw['exchange'] in policy.exchanges, 'EXCHANGE_UNSUPPORTED')
        require(type(raw['security_type']) is str and raw['security_type'] in SECURITY_TYPES)
        require(safe_name(raw['display_name']))
        start = clock(raw['valid_from'])
        end = None if raw['valid_to'] is None else clock(raw['valid_to'])
        require(end is None or end > start, 'INVALID_TIME_ORDER')
        require((raw['status'] == 'ACTIVE' and end is None) or (raw['status'] == 'ENDED' and end is not None))
        included, reasons = eligibility(raw['security_type'], policy)
        return SecurityRecord(raw['issuer_id'], cik, raw['security_id'], raw['ticker'],
                              raw['exchange'], raw['security_type'], raw['display_name'],
                              start, end, raw['status'], raw['source_ref'], included, reasons)
    except CatalogError as exc:
        return Rejection((str(exc),))


def require_record(record, policy):
    require(type(record) is SecurityRecord)
    raw = {key: getattr(record, key) for key in RAW_KEYS}
    normalized = normalize_security_record(raw, policy)
    if isinstance(normalized, Rejection):
        raise CatalogError(normalized.reason_codes[0])
    require(normalized == record)
    return record


def policy_digest(policy):
    require_policy(policy)
    return hashlib.sha256(json.dumps([policy.exchanges, policy.adr_policy, policy.reit_policy],
                                     separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True, repr=False)
class Issuer:
    issuer_id: str
    cik: str
    display_name: str
    status: str
    source_ref: str

    def __repr__(self):
        return 'Issuer(<private>)'


@dataclass(frozen=True, repr=False)
class ListingEvent:
    event_id: str
    issuer_id: str
    security_id: str
    event_type: str
    effective_at: datetime
    available_at: datetime
    collected_at: datetime
    source_ref: str
    raw_hash: str
    record: SecurityRecord | None = None
    successor_security_id: str | None = None

    def __repr__(self):
        return 'ListingEvent(<private>)'


@dataclass(frozen=True, repr=False)
class CatalogSnapshot:
    as_of: datetime
    policy: CatalogPolicy = field(default_factory=CatalogPolicy)
    records: tuple[SecurityRecord, ...] = ()
    events: tuple[ListingEvent, ...] = ()
    schema_version: str = SCHEMA_VERSION
    universe_id: str = UNIVERSE_ID
    source_rights_state: str = 'UNVERIFIED'
    quality: str = 'SYNTHETIC_NOT_LIVE'
    policy_fingerprint: str = ''

    def __post_init__(self):
        if self.policy_fingerprint == '':
            object.__setattr__(self, 'policy_fingerprint', policy_digest(self.policy))

    def __repr__(self):
        return 'CatalogSnapshot(<private>)'

    @property
    def current(self):
        return tuple(r for r in self.records if r.valid_from <= self.as_of
                     and (r.valid_to is None or self.as_of < r.valid_to))

    @property
    def included(self):
        return tuple(r for r in self.current if r.eligibility == 'INCLUDED')

    @property
    def issuers(self):
        latest = {}
        for r in sorted(self.current, key=lambda r: (r.valid_from, r.security_id)):
            latest[r.issuer_id] = Issuer(r.issuer_id, r.cik, r.display_name, 'ACTIVE', r.source_ref)
        return tuple(latest[k] for k in sorted(latest))

    @property
    def issuer_count(self):
        return len(self.issuers)

    @property
    def security_count(self):
        return len(self.current)

    @property
    def excluded_reason_counts(self):
        counts = {}
        for r in self.current:
            for reason in r.reason_codes:
                counts[reason] = counts.get(reason, 0) + 1
        return tuple(sorted(counts.items()))

    @property
    def source_cutoff_at(self):
        return max((e.available_at for e in self.events if e.available_at <= self.as_of), default=None)

    @property
    def universe_version(self):
        from .expanded_catalog_snapshot import snapshot_hash
        return snapshot_hash(self)


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason_codes: tuple[str, ...] = ()


def validate_catalog(snapshot):
    """Validate schema AND replay provenance, including historical intervals."""
    try:
        require(type(snapshot) is CatalogSnapshot)
        require(snapshot.schema_version == SCHEMA_VERSION and snapshot.universe_id == UNIVERSE_ID)
        require(snapshot.source_rights_state == 'UNVERIFIED' and snapshot.quality == 'SYNTHETIC_NOT_LIVE')
        require(type(snapshot.records) is tuple and type(snapshot.events) is tuple)
        require(type(snapshot.as_of) is datetime and clock(snapshot.as_of) == snapshot.as_of)
        require(snapshot.policy_fingerprint == policy_digest(snapshot.policy), 'POLICY_MISMATCH')
        for record in snapshot.records:
            require_record(record, snapshot.policy)
        from .expanded_catalog_events import _validated_event, _materialize
        require(all(_validated_event(e, snapshot.policy) == e for e in snapshot.events))
        require(len({e.event_id for e in snapshot.events}) == len(snapshot.events), 'DUPLICATE_EVENT')
        require(snapshot.events == tuple(sorted(snapshot.events, key=lambda e: e.event_id)))
        require(_materialize(snapshot.events, snapshot.as_of, snapshot.policy) == snapshot.records,
                'SNAPSHOT_PROVENANCE_MISMATCH')
        return ValidationResult(True)
    except CatalogError as exc:
        return ValidationResult(False, (str(exc),))


def require_catalog(snapshot):
    result = validate_catalog(snapshot)
    if not result.ok:
        raise CatalogError(result.reason_codes[0])
    return snapshot
