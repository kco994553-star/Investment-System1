"""Read-only Missing-Data Gate probes; no production policy or fixture updates.

Run from implementation/ with PYTHONPATH=src:. The current scoring functions
are called without patching globals. Zero-weight dicts are synthetic diagnostic
arguments to the existing private reducer, not new Q/G/V or Official defaults.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import timedelta
import hashlib
import json
import math
from pathlib import Path
import subprocess

from investment_system.contracts.enums import ProfileKind, QualityState
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.factors import (
    G_WEIGHTS, Q_WEIGHTS, V_INITIAL_PRIOR, validate_v_candidate_weights,
)
from investment_system.qgv.g_horizon import GHorizonConfig
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.qgv.scoring import _weighted
from investment_system.qgv.financial_issuer import synthetic_jpm
from tests.helpers import AS_OF, complete_obs

ROOT = Path(__file__).resolve().parents[4]
OUTPUT = Path(__file__).with_name('evidence') / 'current_behavior_probes.json'
SOURCE_PATHS = [
    'contracts/enums.py', 'contracts/models.py', 'qgv/scoring.py',
    'qgv/factors.py', 'qgv/analysis.py', 'qgv/raw_map.py', 'qgv/pipeline.py',
    'qgv/g_horizon.py', 'pit/resolver.py', 'providers/memory.py',
    'personal/weights.py', 'qgv/leaderboard.py', 'validation/historical.py',
]


def safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {'nonfinite': str(value)}
    if isinstance(value, dict):
        return {k: safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    if hasattr(value, 'value'):
        return value.value
    return value


def project(obs, profile=ProfileKind.GENERAL_CORPORATE):
    snap = AnalysisEngine().analyze('nvda', AS_OF, obs, profile_kind=profile,
                                   synthetic=False)
    return safe({
        'Q': snap.Q_score, 'G': snap.G_score, 'V_prior': snap.V_score,
        'total': snap.total_score,
        'axis_coverage': {axis: snap.factor_breakdown[f'{axis}_coverage']
                          for axis in ('q', 'g', 'v')},
        'axis_notes': {axis: snap.factor_breakdown[f'{axis}_notes']
                      for axis in ('q', 'g', 'v')},
        'snapshot_coverage': snap.coverage_state,
        'snapshot_confidence': snap.confidence,
        'snapshot_quality_states': snap.quality_states,
        'v_lifecycle': snap.V_policy_status,
        'v_candidates': [asdict(c) for c in snap.v_candidates],
        'v_sector_context_display': next(r for r in snap.factor_breakdown['v_factor_table']
                                         if r['factor_id'] == 'sector_context'),
    })


def main():
    baseline = complete_obs(70)
    rows = [{'case_id': 'all_70', 'output': project(baseline)}]
    representatives = {'Q': 'competitive_advantage', 'G': 'next_3_5y_growth',
                       'V': 'sector_context'}
    qualities = [QualityState.MISSING_DATA, QualityState.NOT_APPLICABLE,
                 QualityState.PIT_UNAVAILABLE, QualityState.BLOCKED_DEPENDENCY,
                 QualityState.VERSION_MISMATCH, QualityState.IDENTIFIER_AMBIGUOUS,
                 QualityState.CALCULATION_ERROR, QualityState.STALE_DATA,
                 QualityState.ESTIMATED_DATA, QualityState.CONFLICTING_SOURCE]
    for axis, fid in representatives.items():
        states = [('absent', None),
                  ('score_none_OK', replace(baseline[fid], score_0_100=None))]
        for quality in qualities:
            states.append((f'{quality.value}_numeric', replace(baseline[fid], quality=quality)))
            states.append((f'{quality.value}_null', replace(baseline[fid], quality=quality,
                                                          score_0_100=None)))
        for state, observation in states:
            obs = dict(baseline)
            if observation is None:
                del obs[fid]
            else:
                obs[fid] = observation
            rows.append({'case_id': f'{axis}__{state}', 'factor_id': fid,
                         'input_score': None if observation is None else observation.score_0_100,
                         'input_quality': None if observation is None else observation.quality.value,
                         'output': project(obs)})
    for state, obs in [('no_factors', {}), ('Q_all_missing', {
            fid: value for fid, value in baseline.items() if fid not in Q_WEIGHTS}),
        ('multiple_absent', {fid: value for fid, value in baseline.items()
                            if fid not in {'competitive_advantage', 'management_quality',
                                           'next_3_5y_growth', 'sector_context', 'reverse_dcf'}})]:
        rows.append({'case_id': state, 'output': project(obs)})
    for state in ['present', 'absent', 'blocked']:
        obs = dict(baseline)
        if state == 'absent':
            del obs['roic_wacc']
        elif state == 'blocked':
            obs['roic_wacc'] = replace(obs['roic_wacc'], quality=QualityState.BLOCKED_DEPENDENCY)
        rows.append({'case_id': f'financial_roic_{state}',
                     'output': project(obs, ProfileKind.FINANCIAL)})
    # Preserve numerical admission observations; encode NaN/Inf explicitly in JSON.
    for value in [-30.0, 300.0, float('nan'), float('inf')]:
        obs = dict(baseline)
        obs['sector_context'] = replace(obs['sector_context'], score_0_100=value)
        rows.append({'case_id': f'V_unvalidated_{value}', 'output': project(obs)})

    zero = []
    for axis, original, fid in [('Q', Q_WEIGHTS, 'competitive_advantage'),
                                ('G', G_WEIGHTS, 'next_3_5y_growth'),
                                ('V', V_INITIAL_PRIOR, 'sector_context')]:
        weights = dict(original)
        recipient = next(k for k in weights if k != fid)
        weights[recipient] += weights[fid]
        weights[fid] = 0.0
        for state in ['present', 'absent', 'null', 'pit', 'blocked', 'na']:
            obs = dict(baseline)
            if state == 'absent':
                del obs[fid]
            elif state == 'null':
                obs[fid] = replace(obs[fid], score_0_100=None)
            elif state in {'pit', 'blocked', 'na'}:
                quality = {'pit': QualityState.PIT_UNAVAILABLE,
                           'blocked': QualityState.BLOCKED_DEPENDENCY,
                           'na': QualityState.NOT_APPLICABLE}[state]
                obs[fid] = replace(obs[fid], quality=quality)
            score, coverage, notes = _weighted(weights, obs, ProfileKind.GENERAL_CORPORATE)
            zero.append({'axis': axis, 'state': state, 'factor_id': fid,
                         'synthetic_weights': weights, 'score': safe(score),
                         'coverage': coverage.value, 'notes': notes})
    candidate_zero = dict(V_INITIAL_PRIOR)
    candidate_zero['margin_of_safety'] += candidate_zero['sector_context']
    candidate_zero['sector_context'] = 0.0

    raw = synthetic_jpm(AS_OF)
    pipe = AnalysisPipeline()
    financial = pipe.analyze_raw(raw)
    future_available = replace(raw, stamp=replace(raw.stamp, available_at=AS_OF + timedelta(days=1)))
    future_published = replace(raw, stamp=replace(raw.stamp, published_at=AS_OF + timedelta(days=1)))
    upstream = {}
    for kind, candidate in [('future_available_at', future_available),
                             ('future_published_at', future_published)]:
        local_pipe = AnalysisPipeline()
        local_pipe.fundamentals.put(candidate)
        upstream[kind] = {
            'analyze_as_of_returns_none': local_pipe.analyze_as_of(candidate.company_id, AS_OF) is None,
            'direct_analyze_raw_returns_snapshot': local_pipe.analyze_raw(candidate, as_of=AS_OF) is not None,
        }
    low = pipe.analyze_raw(raw, available_quarters=0, g_horizon=GHorizonConfig('5Y'))
    high = pipe.analyze_raw(raw, available_quarters=20, g_horizon=GHorizonConfig('5Y'))
    upstream['history'] = {'zero_history': low.g_horizon, 'full_history': high.g_horizon,
                           'scores_identical': (low.Q_score, low.G_score, low.V_score) ==
                                               (high.Q_score, high.G_score, high.V_score)}
    upstream['financial_raw_fixture'] = {
        'Q': financial.Q_score, 'G': financial.G_score, 'V': financial.V_score,
        'axis_notes': {axis: financial.factor_breakdown[f'{axis}_notes'] for axis in ('q', 'g', 'v')},
        'axis_coverage': {axis: financial.factor_breakdown[f'{axis}_coverage'] for axis in ('q', 'g', 'v')},
        'synthetic': financial.synthetic,
    }

    by_id = {row['case_id']: row['output'] for row in rows}
    # Independent arithmetic and entry-point anchors, not a golden regeneration.
    assert by_id['all_70']['Q'] == by_id['all_70']['G'] == by_id['all_70']['V_prior'] == 70
    assert by_id['Q__absent']['Q'] == 56
    assert by_id['G__absent']['G'] == 52.5
    assert by_id['V__absent']['V_prior'] == 63
    assert by_id['V__NOT_APPLICABLE_numeric']['V_prior'] == 63
    assert all(c['v_score'] == 70 for c in by_id['V__NOT_APPLICABLE_numeric']['v_candidates'])
    assert by_id['Q__BLOCKED_DEPENDENCY_numeric']['Q'] is None
    assert by_id['Q__VERSION_MISMATCH_numeric']['Q'] == 70
    assert by_id['financial_roic_blocked']['Q'] == 56
    assert by_id['financial_roic_blocked']['axis_notes']['q'] == ['roic_wacc=NOT_APPLICABLE']
    assert all(row['score'] is None and row['coverage'] == 'BLOCKED'
               for row in zero if row['state'] == 'blocked')
    assert all(row['coverage'] == 'PARTIAL' for row in zero if row['state'] in {'absent', 'null', 'pit', 'na'})
    assert upstream['history']['scores_identical']
    assert all(value['analyze_as_of_returns_none'] and value['direct_analyze_raw_returns_snapshot']
               for key, value in upstream.items() if key.startswith('future_'))

    report = {
        'status': 'CURRENT_BEHAVIOR_CHARACTERIZATION_ONLY',
        'runtime_policy_changed': False, 'synthetic_only': True,
        'real_pit_oos_run': False, 'holdout_consumed': False,
        'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_sha256': {p: hashlib.sha256((ROOT / 'implementation/src/investment_system' / p).read_bytes()).hexdigest()
                          for p in SOURCE_PATHS},
        'golden_sha256_unchanged': hashlib.sha256((ROOT / 'implementation/docs/qgv_common_contract_vnext/golden_cases.json').read_bytes()).hexdigest(),
        'quality_enum': [q.value for q in QualityState],
        'not_quality_enum': ['INSUFFICIENT_HISTORY', 'SOURCE_UNAVAILABLE', 'INVALID'],
        'direct_snapshot_cases': rows, 'zero_weight_diagnostic_cases': zero,
        'candidate_zero_weight_validation': {'synthetic_weights': candidate_zero,
                                              'errors': validate_v_candidate_weights(candidate_zero)},
        'upstream_entrypoint_and_history': upstream,
        'direct_snapshot_case_count': len(rows), 'zero_weight_diagnostic_case_count': len(zero),
        'independent_anchors': 'PASS',
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'direct_snapshot_cases': len(rows), 'zero_weight_cases': len(zero),
                      'anchors': 'PASS', 'output': str(OUTPUT)}))


if __name__ == '__main__':
    main()
