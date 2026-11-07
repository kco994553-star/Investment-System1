"""Top / bottom decile selection: k = floor(N x 0.10) from one total order, N < 10 not run.

Ported from research/qgv_backtest @ 56a0e8ce (#417/#430) and changed for EXP-STOCK-INDICATOR-DECILES-v1:
scoring_adapter.select_top (L136: total descending, then CIK, then security ID, one name per CIK, first n). Changed: the
tie-break is the fixed security ID only (owner rule; one representative per issuer is already guaranteed by universe.py);
any strategy score (axis Q, G, V or a preset total) can be ordered; eligible = group members with a finite score;
N < settings.MIN_N -> NOT_RUN; k = floor(N x settings.DECILE); top = the first k and bottom = the last k of the same
order (2k <= N, so they never overlap). Not the forward-validation v3 rules (no ceil(n/10), no n >= 100, no D01-D10).

Direction: higher is better for every strategy score. Q/G sub-metric percentiles negate lower-is-better metrics
(v2_scoring.SUBMETRICS directions); V factors are mid-rank percentiles of yields (higher yield = cheaper) and of -gap for
the expectation check (qgv_v2.score_universe); axes and totals are weighted means of those 0..100 values. So the order is
score descending, then security_id ascending. Scores are used unrounded.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR
import math

from . import settings

RUN, NOT_RUN = 'RUN', 'NOT_RUN'
# reason codes
ELIGIBLE_BELOW_MIN_N = 'ELIGIBLE_BELOW_MIN_N'
NOT_IN_SCORING_POPULATION = 'NOT_IN_SCORING_POPULATION'
NO_SCORE = 'NO_SCORE'
SCORE_NOT_FINITE = 'SCORE_NOT_FINITE'


def decile_k(n, decile=settings.DECILE):
    """floor(n x decile) in exact Decimal arithmetic."""
    if type(n) is not int or n < 0:
        raise ValueError('ELIGIBLE_COUNT_INVALID')
    return int((Decimal(n) * Decimal(decile)).to_integral_value(rounding=ROUND_FLOOR))


def _finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return False
    return value.is_finite() if isinstance(value, Decimal) else math.isfinite(value)


def select(scores, members, *, na_reasons=None, decile=settings.DECILE, min_n=settings.MIN_N):
    """One strategy in one group.

    scores: {security_id: score | None} (the scoring population); members: the group's security IDs.
    Returns {'status' RUN | NOT_RUN, 'reason', 'members', 'N', 'k', 'order' (security IDs, best first), 'ranks'
    {sid: 1..N}, 'top' / 'bottom' (({'security_id', 'rank', 'score'}, ...) in order), 'not_eligible' {sid: reason}}.
    NOT_RUN returns no order, ranks, top or bottom."""
    members = list(members)
    if len(set(members)) != len(members):
        raise ValueError('DUPLICATE_GROUP_MEMBER')
    for sid in members:
        if not isinstance(sid, str) or not sid.strip():
            raise ValueError('PERMANENT_SECURITY_ID_REQUIRED')
    na_reasons = na_reasons or {}
    eligible, not_eligible = [], {}
    for sid in sorted(members):
        if sid not in scores:
            not_eligible[sid] = NOT_IN_SCORING_POPULATION
        elif scores[sid] is None:
            not_eligible[sid] = na_reasons.get(sid) or NO_SCORE
        elif not _finite(scores[sid]):
            not_eligible[sid] = SCORE_NOT_FINITE
        else:
            eligible.append((scores[sid], sid))
    n = len(eligible)
    out = {'status': NOT_RUN, 'reason': None, 'members': len(members), 'N': n, 'k': None, 'order': (), 'ranks': {},
           'top': (), 'bottom': (), 'not_eligible': not_eligible}
    if n < min_n:
        out['reason'] = ELIGIBLE_BELOW_MIN_N
        return out
    k = decile_k(n, decile)
    order = sorted(eligible, key=lambda item: (-item[0], item[1]))
    ranked = tuple({'security_id': sid, 'rank': i, 'score': score} for i, (score, sid) in enumerate(order, 1))
    out.update(status=RUN, k=k, order=tuple(r['security_id'] for r in ranked),
               ranks={r['security_id']: r['rank'] for r in ranked}, top=ranked[:k], bottom=ranked[n - k:])
    return out


def strategy_scores(score_result, strategy):
    """({security_id: score | None}, {security_id: first NA reason}) of one strategy from scoring.score_population."""
    strategy = settings.resolve_strategy(strategy)
    spec = settings.STRATEGIES[strategy]
    scores, reasons = {}, {}
    for sid, sec in score_result['securities'].items():
        if spec['kind'] == 'AXIS':
            scores[sid] = sec['axes'][spec['axis']]
            first = (sec['axis_reasons'][spec['axis']] or [None])[0]
        else:
            preset = settings.resolve_preset(spec['preset'])
            scores[sid] = sec['totals'][preset]
            first = sec['total_reasons'][preset]
        if scores[sid] is None and first:
            reasons[sid] = first
    return scores, reasons


def select_all(score_result, groups, *, strategies=settings.STRATEGY_IDS):
    """{strategy: {group: select(...)}} for every strategy and group, plus each alias pointing at the same object.

    groups: {'U_A': U-A member security IDs, 'U_B': U-B member security IDs} (universe.build_universes
    [group]['member_securities']). Both groups select from the one U-A scoring result."""
    unknown = set(groups) - set(settings.GROUPS)
    if unknown:
        raise ValueError('GROUP_INVALID')
    out = {}
    for strategy in strategies:
        strategy = settings.resolve_strategy(strategy)
        scores, reasons = strategy_scores(score_result, strategy)
        out[strategy] = {group: select(scores, groups[group], na_reasons=reasons) for group in settings.GROUPS
                         if group in groups}
    for alias, target in settings.STRATEGY_ALIASES.items():
        if target in out:
            out[alias] = out[target]
    return out
