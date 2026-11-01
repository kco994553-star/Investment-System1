"""Additive, versioned research registration and cost-independent selection.

The original thirty-strategy validator is intentionally not changed. Forty
decile portfolios and sixty *comparison cohorts* are different counts: a
factor cohort generates a factor plan and its own matched QGV plan.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

GROUPS = ('U-BOOK200', 'U-SPX-HIST')
ACTIVE_FACTORS = ('F03', 'F07', 'F06', 'F04', 'F10', 'F14')
LOW_FACTORS = frozenset(('F02', 'F03', 'F05', 'F06', 'F07'))
SPEC_ID = 'qgv-reuse/2026-10-27.1'


def default_extension():
    return dict(spec_id=SPEC_ID, base_spec_id='qgv-backtest-standard/2026-10-26.5',
                groups=list(GROUPS), active_factors=list(ACTIVE_FACTORS), minimum_eligible=100,
                primary_panel='PANEL_FULL_QGV', primary_cost_bps=10,
                book200=dict(reference_year=2009, floor_usd=200000000, upper_usd=None,
                             include_adr=True, include_reit=True),
                priority_order=['P0', 'P1', 'P2', 'P3'],
                source_prs=dict(engine=417, expansion=418),
                inference=dict(comparisons=20, block_months=12, resamples=10000,
                               seed=20261026, minimum_full_months=60))


def validate_extension(spec):
    from .annual import ANNUAL_SPEC_ID,annual_extension
    expected = annual_extension() if spec.get('spec_id')==ANNUAL_SPEC_ID else default_extension()
    if spec.get('active_factors') != expected['active_factors']:
        raise ValueError('ACTIVE_FACTOR_SET_CHANGED')
    for key in expected:
        if spec.get(key) != expected[key]:
            raise ValueError('EXTENSION_CONTRACT_CHANGED')


def registered_cells(spec):
    validate_extension(spec)
    cells = []
    for group, short in zip(GROUPS, ('ALL', 'SPX')):
        for mode, suffix in (('QUARTERLY', 'Q'), ('ANNUAL_FEBRUARY', 'Y')):
            primary_mode=spec.get('primary_rebalance','QUARTERLY')
            primary=mode==primary_mode
            for decile in range(1, 11):
                cells.append(dict(id=f'DEC-{short}-W0-{suffix}-D{decile}', kind='QGV_DECILE',
                    group=group, variant='W0', rebalance=mode, decile=decile,
                    phase='P1' if primary else 'P3', status='NOT_RUN',
                    analysis_role='PRIMARY_ANNUAL_RESELECTION' if primary_mode=='ANNUAL_FEBRUARY' and primary else
                                  'PRIMARY_QUARTERLY_LEGACY' if primary else 'CADENCE_SENSITIVITY',
                    book_exactness='BOOK_EXACT_UNCONFIRMED'))
            for factor in (f'F{i:02}' for i in range(1, 16)):
                cells.append(dict(id=f'FAC-{short}-{factor}-{suffix}', kind='FACTOR_PAIR',
                    group=group, variant='W0', rebalance=mode, factor_id=factor,
                    phase='P2' if primary and factor in ACTIVE_FACTORS else 'P3', status='NOT_RUN',
                    analysis_role='PRIMARY_ANNUAL_RESELECTION' if primary_mode=='ANNUAL_FEBRUARY' and primary else
                                  'PRIMARY_QUARTERLY_LEGACY' if primary else 'CADENCE_SENSITIVITY',
                    book_exactness='BOOK_EXACT_UNCONFIRMED'))
    return cells


def selected_cells(spec, stage, experiment_ids=None):
    cells = registered_cells(spec)
    if experiment_ids is not None:
        if spec.get('primary_rebalance')=='ANNUAL_FEBRUARY':
            from .annual import fixed_annual_registry
            cells+=fixed_annual_registry()
        ids = set(experiment_ids)
        if not ids or ids - {c['id'] for c in cells}:
            raise ValueError('UNKNOWN_EXPERIMENT')
        cells = [c for c in cells if c['id'] in ids]
    else:
        cells = [c for c in cells if c['phase'] in ('P1', 'P2')]
    costs = (0, 10, 20, 25, 30) if stage == 'sensitivity' else (10,)
    return [dict(cell,panel=panel,cost_bps=cost) for cell in cells for cost in costs
            for panel in (('COMMON','PRACTICAL') if cell['kind']=='FIXED_N' else (spec['primary_panel'],))]


@dataclass(frozen=True)
class SelectionPlan:
    group: str
    signal_day: str
    selector: str
    panel: str
    selected: tuple
    slots: int
    eligible_count: int
    boundary_tie: bool
    excluded_count: int


def finite(value):
    return type(value) in (int, float) and isfinite(value)


def _candidates(identities, scores, panel, eligible_ids=None):
    if panel not in ('PANEL_FULL_QGV', 'PANEL_OPERATIONAL_ELIGIBLE'):
        raise ValueError('UNKNOWN_PANEL')
    allowed = set(identities) if eligible_ids is None else set(eligible_ids)
    candidates, seen = [], set()
    # Dedup before observing score order; the universe adapter normally already
    # chooses the representative by historical liquidity, never by QGV score.
    ordered = sorted(identities, key=lambda sid: (str(identities[sid]['cik']).zfill(10), identities[sid]['security_id']))
    for key in ordered:
        identity, score = identities[key], scores.get(key, {})
        issuer = identity.get('issuer_id') or str(identity['cik']).zfill(10)
        if issuer in seen:
            continue
        seen.add(issuer)
        if key not in allowed or not finite(score.get('total')):
            continue
        if panel == 'PANEL_FULL_QGV' and not all(finite(score.get('axes', {}).get(a, {}).get('score')) for a in ('Q','G','V')):
            continue
        cik = str(identity['cik'])
        if not cik.isdigit() or len(cik) > 10 or int(cik) == 0:
            raise ValueError('PERMANENT_ISSUER_ID_REQUIRED')
        candidates.append(dict(key=key, security_id=identity['security_id'], cik=cik.zfill(10),
                               issuer_id=issuer, total=score['total']))
    return candidates


def _plan(identities, candidates, group, signal_day, decile, panel, selector, metric, low=False):
    if group not in GROUPS or type(decile) is not int or not 1 <= decile <= 10:
        raise ValueError('INVALID_SELECTION_CONTRACT')
    n = len(candidates)
    if n < 100:
        raise ValueError('NO_DECILE_COVERAGE')
    ordered = sorted(candidates, key=lambda r: (metric[r['key']] if low else -metric[r['key']], r['cik'], r['security_id']))
    selected = tuple(dict(row, rank=i+1) for i,row in enumerate(ordered) if 1 + 10*i//n == decile)
    chosen = {r['key'] for r in selected}
    tie = any(metric[a['key']] == metric[b['key']] and ((a['key'] in chosen) != (b['key'] in chosen))
              for a,b in zip(ordered, ordered[1:]))
    return SelectionPlan(group, str(signal_day), selector, panel, selected, len(selected), n, tie, len(identities)-n)


def selection_plan(identities, scores, *, group, signal_day, decile=1, panel='PANEL_FULL_QGV', eligible_ids=None):
    candidates = _candidates(identities, scores, panel, eligible_ids)
    return _plan(identities, candidates, group, signal_day, decile, panel, 'QGV_DECILE',
                 {r['key']: r['total'] for r in candidates})


def matched_plans(identities, scores, factor_values, *, factor_id, group, signal_day, panel='PANEL_FULL_QGV'):
    if factor_id not in ACTIVE_FACTORS:
        raise ValueError('BLOCKED_ON_FORMULA')
    valid = {sid for sid,value in factor_values.items() if finite(value)
             and (factor_id not in ('F03','F06','F07') or value > 0)}
    candidates = _candidates(identities, scores, panel, valid)
    factor = _plan(identities, candidates, group, signal_day, 1, panel, factor_id, factor_values, factor_id in LOW_FACTORS)
    qgv = _plan(identities, candidates, group, signal_day, 1, panel, f'MATCHED_QGV_{factor_id}',
                {r['key']: r['total'] for r in candidates})
    return factor, qgv
