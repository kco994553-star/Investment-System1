"""Point-in-time test helpers shared by pattern tests (§13.2). Mirror: tools/pattern_pit_helpers.js.

`run(raw_bars)` is any function that turns a list of raw daily bars into a list of transitions carrying
`known_at`. The helpers only compare results; they never read prices from anywhere but their arguments.
"""
from __future__ import annotations

import json


def _key(items):
    return json.dumps(items, sort_keys=True, separators=(',', ':'))


def prefix_violations(run, raw_bars, cut_of, start=1):
    """Prefix invariance: run(bars[:t]) == [x in run(bars) if known_at <= cut_of(bars[:t])] for every t."""
    full = run(raw_bars)
    bad = []
    for t in range(start, len(raw_bars) + 1):
        cut = cut_of(raw_bars[:t])
        expected = [x for x in full if cut is not None and x['known_at'] <= cut]
        if _key(run(raw_bars[:t])) != _key(expected):
            bad.append(t)
    return bad


def future_mutation_violations(run, raw_bars, t, mutate, cut_of):
    """Future mutation: changing bars after index t (exclusive prefix length t) never changes known_at <= cut."""
    cut = cut_of(raw_bars[:t])
    before = [x for x in run(raw_bars) if cut is not None and x['known_at'] <= cut]
    changed = list(raw_bars[:t]) + [mutate(i, dict(b)) for i, b in enumerate(raw_bars[t:], start=t)]
    after = [x for x in run(changed) if cut is not None and x['known_at'] <= cut]
    return [] if _key(before) == _key(after) else [t]


def pivot_lag_violations(transitions, k):
    """Time lower bound: every pivot transition is known at least k bars after its anchor."""
    return [x['object_id'] for x in transitions if x.get('object_kind') == 'PIVOT' and x['known_index'] - x['anchor_index'] < k]
