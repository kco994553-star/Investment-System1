"""Deterministic freshness. No TTL is defined here: each producer declares its own expires_at
(and optionally usable_until). The evaluation clock is always passed explicitly.

FRESH          LIVE and now < expires_at
STALE          LIVE, now >= expires_at, and (no usable_until or now < usable_until).
               Existing Web contract: shown with a STALE badge, never silently current.
NOT_USABLE     LIVE and now >= producer-declared usable_until. The assembler withholds the data.
NOT_APPLICABLE FROZEN_SNAPSHOT / DEMO (point-in-time by definition) or NOT_AVAILABLE.
"""
from __future__ import annotations

from datetime import datetime

from .contract import parse_ts, validate_snapshot
from .errors import FreshnessContractError, TimestampError

FRESH, STALE, NOT_USABLE, NOT_APPLICABLE = 'FRESH', 'STALE', 'NOT_USABLE', 'NOT_APPLICABLE'


def require_aware(now: datetime) -> datetime:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise TimestampError('evaluation clock must be a timezone-aware datetime', 'now')
    return now


def classify(snapshot: dict, now: datetime) -> str:
    validate_snapshot(snapshot)
    require_aware(now)
    if snapshot['data_state'] == 'NOT_AVAILABLE':
        return NOT_APPLICABLE
    if parse_ts(snapshot['as_of'], 'as_of') > now:
        raise FreshnessContractError('as_of is in the future relative to the evaluation clock', 'as_of')
    if snapshot['data_state'] != 'LIVE':
        return NOT_APPLICABLE
    if now < parse_ts(snapshot['expires_at'], 'expires_at'):
        return FRESH
    usable = parse_ts(snapshot.get('usable_until'), 'usable_until', required=False)
    if usable is not None and now >= usable:
        return NOT_USABLE
    return STALE
