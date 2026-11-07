"""Research comparison only; delegates scores and selections to existing calc 23.1 paths.

No active sector weights until original book evidence and historical sector mappings are available.
This is baseline/fallback preparation, not an implemented sector-weight strategy or a performance engine.
"""
from collections import Counter
from . import scoring, selection
from ...qgv import qgv_v2


def compare_scores(a, b, *, members, sectors):
    """Separate coverage changes from rank changes on exactly the common eligible set."""
    own_a, own_b = (selection.select(s, members) for s in (a, b))
    eligible_a = set(members) - set(own_a['not_eligible'])
    eligible_b = set(members) - set(own_b['not_eligible'])
    common = sorted(eligible_a & eligible_b)
    ca, cb = (selection.select(s, common) for s in (a, b))
    def changes(x, y):
        out = {}
        for side in ('top', 'bottom'):
            if x['status'] != selection.RUN or y['status'] != selection.RUN:
                out[side] = None
                continue
            before = {r['security_id'] for r in x[side]}
            after = {r['security_id'] for r in y[side]}
            out[side] = dict(entered=sorted(after-before), exited=sorted(before-after),
                             sectors_before=dict(sorted(Counter(sectors.get(s) or 'UNKNOWN' for s in before).items())),
                             sectors_after=dict(sorted(Counter(sectors.get(s) or 'UNKNOWN' for s in after).items())))
        return out
    ranks = None if ca['status'] != selection.RUN else {
        s: dict(before=ca['ranks'][s], after=cb['ranks'][s], delta=ca['ranks'][s]-cb['ranks'][s])
        for s in common if ca['ranks'][s] != cb['ranks'][s]}
    return dict(eligible_a=len(eligible_a), eligible_b=len(eligible_b), common_eligible=len(common),
                coverage_gained=sorted(eligible_b-eligible_a), coverage_lost=sorted(eligible_a-eligible_b),
                common_rank_changes=ranks, own_population=changes(own_a, own_b), common_population=changes(ca, cb),
                reason=ca['reason'], selection_a=own_a, selection_b=own_b)


def baseline_diagnostic(rows, quotes, *, population, groups, config):
    """Run the unchanged baseline once; B/C are explicitly inactive aliases, never claimed candidate results."""
    if config.get('schema') != 'exp-sector-liquidity-config/1' or config.get('baseline') != 'balanced':
        raise ValueError('CONFIG_INVALID')
    if config.get('active_sector_candidates') != []:
        raise ValueError('SECTOR_CANDIDATE_NOT_IMPLEMENTED_OR_EVIDENCED')
    if config.get('gate') is not True or config.get('type_weights') is not True:
        raise ValueError('BASELINE_POLICY_CHANGED')
    result = scoring.score_population(rows, quotes, population=population, include_engine=True)
    if result['calc_version'] != config.get('calc_version'):
        raise ValueError('CALC_VERSION_MISMATCH')
    a = {sid: s['totals']['balanced'] for sid, s in result['securities'].items()}
    sectors = {sid: r.get('industry_group') for sid, r in rows.items()}
    comparisons = {g: compare_scores(a, a, members=members, sectors=sectors) for g, members in groups.items()}
    stages = {}
    for sid, r in result['engine']['balanced'].items():
        included = [p for p in qgv_v2.PILLARS if r['axes'][p]['score'] is not None
                    and not (p == 'V' and r['value_trap_gate'])]
        stages[sid] = qgv_v2._weight_stages(
            qgv_v2.official_weights('balanced'), True, r['weights'], r['type_reason'], r['selected_types'],
            r['axes'], r['factors'], included, r['value_trap_gate'], r['total'], r['total_reason'],
            {'Q':'PUBLISHED', 'G':'PUBLISHED', 'V':'DEVICE'})
    return dict(schema='exp-sector-comparison/1', status='BASELINE_ONLY_CANDIDATES_BLOCKED',
                baseline=result, variants={'A':'BASELINE', 'B':'BASELINE_FALLBACK_NO_EVIDENCED_CANDIDATE',
                                            'C':'BASELINE_FALLBACK_NO_EVIDENCED_CANDIDATE'},
                comparisons=comparisons, effective_weight_stages=stages,
                performance=None, performance_reason='NO_ACTIVE_SECTOR_CANDIDATES')
