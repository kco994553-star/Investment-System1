"""Frozen, dated security groups; high measurement = D10, regardless of desirability."""
from decimal import Decimal, localcontext
import hashlib
import json

from . import selection
from .technical_measures import METRIC_IDS, SETTINGS, SETTINGS_BYTES, number

CONDITIONS = ('gt_zero', 'ge_median', 'gt_median', 'top_decile', 'bottom_decile', 'exclude_D10')


def _conditions(value, median=None, decile=None):
    return dict(gt_zero=None if value is None else value > 0,
                ge_median=None if value is None or median is None else value >= median,
                gt_median=None if value is None or median is None else value > median,
                top_decile=None if decile is None else decile == 10,
                bottom_decile=None if decile is None else decile == 1,
                exclude_D10=None if decile is None else decile != 10)


def build_board(measurements, *, group):
    """Compare only supplied fixed security IDs at one S; unknown membership is null.

    `member_security_ids` is the original complete group, not a post-filter list.
    Numeric strings preserve precision; bools, floats and nonfinite values are ineligible.
    N<10 suppresses deciles only, retaining ordinal ranks and the group's median.
    """
    measurements = list(measurements)
    signal = group['signal_day']
    if any(m['signal_day'] != signal for m in measurements):
        raise ValueError('SIGNAL_DAY_MISMATCH')
    settings_hash = hashlib.sha256(SETTINGS_BYTES).hexdigest()
    if any(m.get('settings_version', SETTINGS['settings_version']) != SETTINGS['settings_version']
           or m.get('settings_sha256', settings_hash) != settings_hash for m in measurements):
        raise ValueError('SETTINGS_MISMATCH')
    by_id = {}
    for m in measurements:
        sid = m.get('security_id')
        if sid is not None:
            if not isinstance(sid, str) or not sid.strip():
                raise ValueError('PERMANENT_SECURITY_ID_REQUIRED')
            if sid in by_id:
                raise ValueError('DUPLICATE_SECURITY_ID')
            by_id[sid] = m
    confirmed = group.get('membership_status') == 'CONFIRMED'
    members = group.get('member_security_ids')
    if confirmed:
        if not isinstance(members, list) or not group.get('membership_source'):
            raise ValueError('GROUP_MEMBERSHIP_EVIDENCE_REQUIRED')
        if any(not isinstance(sid, str) or not sid.strip() for sid in members):
            raise ValueError('PERMANENT_SECURITY_ID_REQUIRED')
        if len(set(members)) != len(members):
            raise ValueError('DUPLICATE_GROUP_MEMBER')
        candidates = [by_id.get(sid, dict(security_id=sid, series_id=None, metrics={})) for sid in sorted(members)]
        payload = dict(group_id=group['group_id'], signal_day=signal, members=sorted(members))
        population_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    else:
        if members is not None:
            raise ValueError('UNKNOWN_MEMBERSHIP_MUST_BE_NULL')
        candidates, population_hash = measurements, None
    out = dict(schema='technical-leaderboard/1', settings_version=SETTINGS['settings_version'],
               settings_sha256=settings_hash, signal_day=signal,
               group_id=group['group_id'], membership_status=group.get('membership_status'),
               membership_source=group.get('membership_source'), population_hash=population_hash, metrics={})
    for metric in METRIC_IDS:
        items, values = [], {}
        for m in candidates:
            source = m['metrics'].get(metric, {})
            value = number(source.get('value'))
            reasons = list(source.get('null_reasons') or [])
            if value is None and not reasons:
                reasons.append('METRIC_NOT_AVAILABLE')
            if not confirmed:
                reasons.append('GROUP_MEMBERSHIP_UNCONFIRMED')
            item = dict(source)
            item.update(dict(security_id=m.get('security_id'), series_id=m.get('series_id'),
                              value=None if value is None else str(value), rank=None, decile=None,
                              conditions=_conditions(value), null_reasons=reasons))
            items.append(item)
            if confirmed and value is not None:
                values[m['security_id']] = value
        n, median, k = (len(values) if confirmed else None), None, None
        if confirmed and values:
            with localcontext() as ctx:
                # Never round an input before ordering; allow long supplied decimal strings.
                ctx.prec = max(50, max(len(v.as_tuple().digits) for v in values.values()) + 2)
                ordered = sorted(values, key=lambda sid: (values[sid].copy_negate(), sid))
                nums = [values[sid] for sid in ordered]
                median = nums[n//2] if n % 2 else (nums[n//2-1] + nums[n//2]) / 2
                deciles = {}
                if n >= SETTINGS['minimum_decile_n']:
                    tails = selection.select(values, list(values))
                    assert tuple(ordered) == tails['order']
                    k = tails['k']
                    q, r = divmod(n - 2*k, 8)
                    sizes = [k] + [q + (i < r) for i in range(8)] + [k]
                    index = 0
                    for d, size in zip(range(10, 0, -1), sizes):
                        for sid in ordered[index:index+size]:
                            deciles[sid] = d
                        index += size
                ranks = {sid: i for i, sid in enumerate(ordered, 1)}
                for item in items:
                    sid = item['security_id']
                    if sid in values:
                        item.update(rank=ranks[sid], decile=deciles.get(sid),
                                    conditions=_conditions(values[sid], median, deciles.get(sid)))
                        if n < SETTINGS['minimum_decile_n']:
                            item['null_reasons'].append('N_BELOW_10')
                items.sort(key=lambda x: (x['rank'] is None, x['rank'] or 0, x['security_id']))
        out['metrics'][metric] = dict(n_valid=n, n_members=len(members) if confirmed else None,
            median=None if median is None else str(median), k=k, rows=items,
            null_reason='GROUP_MEMBERSHIP_UNCONFIRMED' if not confirmed else 'NO_VALID_VALUES' if n == 0 else None)
    return out


def filter_board(board, conditions):
    """Only select from precomputed predicates. No mutation, regrouping or reranking.

    A missing condition (including volatility decile) never passes. The result is an
    ID selection, not a new board; callers keep the original metadata and rows.
    """
    if board['membership_status'] != 'CONFIRMED':
        return []
    keep = None
    for query in conditions:
        metric, condition = query['metric'], query['condition']
        if metric not in METRIC_IDS or condition not in CONDITIONS:
            raise ValueError('FILTER_INVALID')
        selected = {r['security_id'] for r in board['metrics'][metric]['rows']
                    if r['security_id'] and r['conditions'][condition] is True}
        keep = selected if keep is None else keep & selected
    if keep is None:
        keep = {r['security_id'] for r in board['metrics'][METRIC_IDS[0]]['rows'] if r['security_id']}
    return sorted(keep)
