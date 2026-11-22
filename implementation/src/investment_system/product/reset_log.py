"""History-reset log of a rolling public file (owner 2026-11-22, PUBLIC_FILE_INCIDENTS.md; the #613 rule for macro-evidence).

`news-signals.json` and `sec-disclosures.json` carry their previous Pages copy forward. When a run cannot carry it, the
file starts again from this run's rows, and that is never silent: the optional top-level `resets` list records it,

    resets: [{"at": <this run's as_of>, "reason": <RESET_REASONS>, "previous_as_of": <as_of of the copy not carried | null>}]

oldest first, at most MAX_RESETS entries, carried from copy to copy. The key is absent until the first reset, so a file
that never reset keeps its exact earlier shape (readers accept both shapes).

Reasons: NO_LIVE (404: no live copy), PREVIOUS_UNAVAILABLE (the live copy could not be fetched), PREVIOUS_DISCARDED (it
failed its checks), PREVIOUS_PLACEHOLDER (it was the empty build placeholder).
"""
from __future__ import annotations

import re

RESET_REASONS = ('NO_LIVE', 'PREVIOUS_UNAVAILABLE', 'PREVIOUS_DISCARDED', 'PREVIOUS_PLACEHOLDER')
MAX_RESETS = 500
ENTRY_KEYS = ('at', 'reason', 'previous_as_of')
_INSTANT = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+00:00')


def _instant(value) -> bool:
    return type(value) is str and _INSTANT.fullmatch(value) is not None


def require(value, as_of: str) -> list:
    """A present `resets` list: 1..MAX_RESETS entries, each at <= as_of, in time order. Raises ValueError otherwise."""
    if type(value) is not list or not 1 <= len(value) <= MAX_RESETS:
        raise ValueError('RESETS_INVALID')
    last = None
    for entry in value:
        if type(entry) is not dict or set(entry) != set(ENTRY_KEYS) or entry['reason'] not in RESET_REASONS:
            raise ValueError('RESETS_INVALID')
        if not _instant(entry['at']) or entry['at'] > as_of or (last is not None and entry['at'] < last):
            raise ValueError('RESETS_INVALID')
        if entry['previous_as_of'] is not None and (not _instant(entry['previous_as_of']) or entry['previous_as_of'] > entry['at']):
            raise ValueError('RESETS_INVALID')
        last = entry['at']
    return value


def salvage(raw) -> list:
    """The `resets` of a copy that was not carried (discarded or placeholder), when that list alone is still valid."""
    if type(raw) is not dict or 'resets' not in raw or not _instant(raw.get('as_of')):
        return []
    try:
        return [dict(e) for e in require(raw['resets'], raw['as_of'])]
    except ValueError:
        return []


def previous_as_of(raw):
    return raw['as_of'] if type(raw) is dict and _instant(raw.get('as_of')) else None


def next_resets(previous, *, at: str, reason: str | None, prior: list | None = None,
                not_carried_as_of: str | None = None) -> list:
    """This run's `resets`: the carried copy's list (or `prior`, salvaged from a copy not carried), plus one entry when
    this run starts again (reason given)."""
    carried = [dict(e) for e in (previous or {}).get('resets', [])] if previous is not None else [dict(e) for e in prior or []]
    if reason is None:
        return carried
    if reason not in RESET_REASONS:
        raise ValueError('RESETS_INVALID')
    if not_carried_as_of is not None and not_carried_as_of > at:
        not_carried_as_of = None
    return (carried + [{'at': at, 'reason': reason, 'previous_as_of': not_carried_as_of}])[-MAX_RESETS:]


def report(prefix: str, title: str, reason: str | None, resets: list) -> None:
    """One fixed log line and a GitHub annotation when a run started the rolling window again (never silent)."""
    if reason is None:
        return
    last = resets[-1] if resets else {}
    print('%s HISTORY_RESET reason=%s resets=%d previous_as_of=%s' % (
        prefix, reason, len(resets), last.get('previous_as_of') or '-'))
    print('::warning title=%s history reset::reason=%s, resets so far=%d' % (title, reason, len(resets)))
