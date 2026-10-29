"""Immutable, atomic listing-event replay. No connection to official universes."""
from dataclasses import dataclass, fields, replace
import re

from .expanded_catalog import (CatalogError, CatalogSnapshot, ListingEvent, clock,
                               identifier, require, require_catalog, require_record)

_CHANGES = {'TICKER_CHANGED': 'ticker', 'EXCHANGE_CHANGED': 'exchange',
            'CLASS_CHANGED': 'security_type', 'NAME_CHANGED': 'display_name'}
_KINDS = frozenset(('LISTED', 'DELISTED', 'MERGED', *_CHANGES))


def _validated_event(event, policy):
    require(type(event) is ListingEvent)
    require(all(identifier(getattr(event, key)) for key in
                ('event_id', 'issuer_id', 'security_id', 'source_ref')))
    require(type(event.event_type) is str and event.event_type in _KINDS)
    require(type(event.raw_hash) is str and re.fullmatch(r'[0-9a-f]{64}', event.raw_hash) is not None)
    event = replace(event, effective_at=clock(event.effective_at),
                    available_at=clock(event.available_at), collected_at=clock(event.collected_at))
    # Advance announcements and delayed publication are both valid. Only
    # publication AFTER our acquisition is a causal inversion.
    require(event.available_at <= event.collected_at, 'INVALID_TIME_ORDER')
    if event.event_type in ('LISTED', *_CHANGES):
        r = require_record(event.record, policy)
        require((r.issuer_id, r.security_id) == (event.issuer_id, event.security_id), 'IDENTITY_AMBIGUOUS')
        require(r.valid_from == event.effective_at and r.valid_to is None and r.status == 'ACTIVE', 'INVALID_TIME_ORDER')
    else:
        require(event.record is None)
    if event.event_type == 'MERGED':
        require(identifier(event.successor_security_id) and event.successor_security_id != event.security_id)
    else:
        require(event.successor_security_id is None)
    return event


def _materialize(events, cutoff, policy):
    """Rebuild effective-time intervals from already-public events only.

    Replaying the immutable ledger makes late deliveries order independent and
    avoids trusting a half-applied batch. Same-time operations on one security
    require source sequencing not present in v1 and therefore fail closed.
    """
    ready = sorted((e for e in events if e.available_at <= cutoff and e.effective_at <= cutoff),
                   key=lambda e: (e.effective_at, e.security_id, e.event_id))
    points = set()
    for e in ready:
        point = e.security_id, e.effective_at
        require(point not in points, 'EVENT_ORDER_AMBIGUOUS')
        points.add(point)
    active, history, used_ids = {}, [], set()
    for e in ready:
        old = active.get(e.security_id)
        if e.event_type == 'LISTED':
            require(e.security_id not in used_ids, 'SECURITY_ID_REUSED')
            used_ids.add(e.security_id)
            active[e.security_id] = e.record
        else:
            require(old is not None, 'SECURITY_NOT_ACTIVE')
            require(old.issuer_id == e.issuer_id, 'IDENTITY_AMBIGUOUS')
            require(e.effective_at > old.valid_from, 'INVALID_TIME_ORDER')
            history.append(replace(old, valid_to=e.effective_at, status='ENDED'))
            del active[e.security_id]
            if e.event_type in _CHANGES:
                allowed = {_CHANGES[e.event_type], 'valid_from', 'source_ref', 'eligibility', 'reason_codes'}
                require(all(getattr(old, f.name) == getattr(e.record, f.name)
                            for f in fields(old) if f.name not in allowed), 'EVENT_PAYLOAD_MISMATCH')
                require(getattr(old, _CHANGES[e.event_type]) != getattr(e.record, _CHANGES[e.event_type]),
                        'EVENT_NO_CHANGE')
                active[e.security_id] = e.record
            elif e.event_type == 'MERGED':
                require(e.successor_security_id in active, 'MERGER_TARGET_UNRESOLVED')
    records = tuple(sorted((*history, *active.values()), key=lambda r: (r.security_id, r.valid_from)))
    # Venue+ticker intervals must never overlap, even if both ended before cutoff.
    by_symbol = {}
    for r in records:
        by_symbol.setdefault((r.exchange, r.ticker), []).append(r)
    for intervals in by_symbol.values():
        intervals.sort(key=lambda r: r.valid_from)
        for a, b in zip(intervals, intervals[1:]):
            require(a.valid_to is not None and a.valid_to <= b.valid_from, 'TICKER_INTERVAL_OVERLAP')
    return records


def apply_listing_events(previous_snapshot, events, cutoff):
    """All-or-nothing pure update; caller retains previous object on failure."""
    previous = require_catalog(previous_snapshot)
    cutoff = clock(cutoff)
    require(cutoff >= previous.as_of, 'CUTOFF_REGRESSION')
    require(type(events) in (tuple, list))
    ledger = {e.event_id: e for e in previous.events}
    for event in events:
        event = _validated_event(event, previous.policy)
        if event.event_id in ledger:
            require(ledger[event.event_id] == event, 'EVENT_ID_CONFLICT')
        ledger[event.event_id] = event
    canonical = tuple(ledger[key] for key in sorted(ledger))
    records = _materialize(canonical, cutoff, previous.policy)
    result = replace(previous, as_of=cutoff, events=canonical, records=records)
    require_catalog(result)
    return previous if result == previous else result


@dataclass(frozen=True, repr=False)
class CatalogDiff:
    added: tuple[str, ...]
    ended: tuple[str, ...]
    changed: tuple[str, ...]
    unchanged: tuple[str, ...]

    def __repr__(self):
        return 'CatalogDiff(<private>)'


def diff_snapshots(previous, current):
    """Compare active securities by permanent ID; every ID has one category.

    Historical churn entirely between cutoffs stays in the ledger/intervals;
    these counts describe the two current views, not event throughput.
    """
    require_catalog(previous)
    require_catalog(current)
    require(previous.policy == current.policy, 'POLICY_MISMATCH')
    require(current.as_of >= previous.as_of, 'CUTOFF_REGRESSION')
    old, new = ({r.security_id: r for r in s.current} for s in (previous, current))
    shared = old.keys() & new.keys()
    changed = {key for key in shared if old[key] != new[key]}
    return CatalogDiff(tuple(sorted(new.keys() - old.keys())), tuple(sorted(old.keys() - new.keys())),
                       tuple(sorted(changed)), tuple(sorted(shared - changed)))
