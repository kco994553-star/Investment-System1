"""Reuse operational factor percentiles, memberships and QGV for W0--W3.

`score_variants` accepts historical metric rows produced by build_pit_rows. A
second explicit shape, engine-company rows containing `factors` and `v_inputs`,
supports synthetic operational parity tests; it does not establish PIT validity.
COMMON is a selection mask applied after all four full-population calls. Gate
and cyclical normalization remain enabled for every variant. D0/D2, when asked
for, are fixed 34/33/33 with type weights off and official/equal inner weights.
"""
from __future__ import annotations

from copy import deepcopy
import math

from ...qgv import playbook, qgv2_inputs, qgv_v2, v2_factors, v2_scoring
from ...qgv.dcf_parameters import load_default_dcf_parameters
from ...qgv.type_config import load_official_type_config
from .pit_adapter import _accession, _basis_alignment
from .calendar_adapter import aware, day
from datetime import datetime, time, timezone

VARIANTS = ('W0', 'W1', 'W2', 'W3')


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def variant_options(variant):
    """A fresh weight tree; W0 retains the exact operational default path."""
    if variant not in VARIANTS + ('D0', 'D2'):
        raise ValueError('VARIANT_INVALID')
    if variant == 'W0':
        return {'preset': 'balanced', 'gate': True, 'weights': None, 'type_weights': True}
    tree = qgv_v2.official_weights('balanced')
    if variant in ('W1', 'W3'):
        tree['axis'] = dict.fromkeys(qgv_v2.PILLARS, 1)
    if variant in ('W2', 'W3', 'D2'):
        tree['inner'] = {axis: dict.fromkeys(qgv_v2.WEIGHTS[axis], 20) for axis in qgv_v2.PILLARS}
    return {'preset': 'balanced', 'gate': True, 'weights': tree, 'type_weights': variant == 'W2'}


def prepare_companies(rows, *, type_config=None):
    """Compute Q/G and volatility percentiles on the full PIT universe once."""
    type_config = load_official_type_config().to_dict() if type_config is None else type_config
    rows = deepcopy(rows)
    if not rows:
        return {}, {'cross_section_size': 0}
    metric_mode = ['metrics' in r for r in rows.values()]
    if not any(metric_mode):
        if not all('factors' in r for r in rows.values()):
            raise ValueError('PIT_METRICS_OR_SYNTHETIC_COMPANIES_REQUIRED')
        return rows, {'cross_section_size': len({r.get('cik', key) for key, r in rows.items()
                                                if r.get('in_cross_section', True) is not False})}
    if not all(metric_mode):
        raise ValueError('MIXED_SCORING_INPUT_SHAPES')
    for row in rows.values():
        if row.get('calc_version') != v2_factors.CALC_VERSION:
            raise ValueError('CALC_VERSION_MISMATCH')
        if not isinstance(row.get('cik'), str) or not row['cik'].isdigit() or int(row['cik']) == 0:
            raise ValueError('PERMANENT_ISSUER_ID_REQUIRED')
    scores, summary = v2_scoring.score_rows(rows, calc_version=v2_factors.CALC_VERSION)
    ranks = v2_scoring.volatility_rank_rows(rows, calc_version=v2_factors.CALC_VERSION)
    playbook_config = playbook.load_config()
    companies = {}
    for key, row in sorted(rows.items()):
        row.update(scores[('universe', key)])
        row['metrics']['revenue_volatility_5y_rank_pct'] = ranks[('universe', key)]
        normalized = qgv2_inputs.normalize(row, True)
        # Do not apply today's fixed TARGET ticker-to-sector assignments to history.
        group = playbook.sector_for(playbook_config, None, None, row.get('sic'))
        rank = ranks[('universe', key)]
        classification = playbook.classify_types_v0(playbook_config, {
            'sic': row.get('sic'), 'sector_subgroup': group.get('sector'),
            'revenue_volatility_5y_rank_pct': None if rank is None else rank / 100})
        companies[key] = {
            'cik': row['cik'], 'security_id': row.get('security_id', key),
            'profile': row.get('profile'), 'industry_group': row.get('industry_group'),
            'factors': normalized['factors'], 'qg_axes': normalized['qg_axes'],
            'v_inputs': normalized['v_inputs'], 'in_cross_section': True,
            'memberships': qgv_v2.pricefree_memberships(row['metrics'], type_config),
            'cyclical_basis': (classification.get('cyclical') or {}).get('member') is True,
        }
    return companies, summary


def score_variants(rows, quotes, *, type_config=None, parameters=None, include_diagnostics=False):
    type_config = load_official_type_config().to_dict() if type_config is None else type_config
    parameters = load_default_dcf_parameters() if parameters is None else parameters
    companies, population = prepare_companies(rows, type_config=type_config)
    if rows and all('metrics' in row for row in rows.values()):
        # A source attestation must identify this exact share fact, not merely
        # state that both prices and shares are "raw". This also rejects split
        # adjusted histories accidentally paired with historical raw shares.
        aligned = {}
        for key, quote in (quotes or {}).items():
            row = rows.get(key)
            if row is None:
                continue
            provenance = row.get('provenance') or {}
            shares = (row.get('v_inputs_v2') or {}).get('diluted_shares') or {}
            shares_basis = provenance.get('shares_basis') or {}
            receipt = quote.get('basis_alignment') or {}
            try:
                signal_day = day(provenance.get('signal_day'))
                decision_at = (aware(provenance['decision_at']) if provenance.get('decision_at') else
                               datetime.combine(signal_day, time.max, timezone.utc))
                valid = _basis_alignment({'basis_alignment': receipt}, signal_day, signal_day, decision_at)
            except (TypeError, ValueError):
                valid = None
            if (valid and receipt.get('shares_period_end') == shares.get('period_end')
                    and shares_basis.get('period_end') == shares.get('period_end')
                    and _accession(shares_basis.get('accn'))
                    and _accession(receipt.get('shares_filing_accn')) == _accession(shares_basis['accn'])):
                aligned[key] = quote
        quotes = aligned
    variants = VARIANTS + (('D0', 'D2') if include_diagnostics else ())
    scores = {variant: qgv_v2.score_universe(companies, quotes, type_config=type_config,
                                            parameters=parameters, **variant_options(variant))
              for variant in variants}
    common_ids = tuple(key for key in sorted(companies) if all(
        _finite(scores[v][key]['axes'][axis]['score']) for v in VARIANTS for axis in qgv_v2.PILLARS))
    common_set = set(common_ids)
    practical = {v: tuple(key for key in sorted(companies) if _finite(scores[v][key]['total'])) for v in variants}
    common = {v: tuple(key for key in practical[v] if key in common_set) for v in variants}
    return {'scores': scores, 'common_ids': common_ids, 'panels': {'COMMON': common, 'PRACTICAL': practical},
            'summary': {'percentile_population_size': population['cross_section_size'],
                        'input_rows': len(companies), 'common_size': len(common_ids),
                        'practical_sizes': {v: len(practical[v]) for v in variants},
                        'panel_exclusions': {v: len(companies) - len(common[v]) for v in variants},
                        'gate_changes_vs_w0': {v: sum(scores[v][key]['value_trap_gate'] !=
                                                     scores['W0'][key]['value_trap_gate'] for key in companies)
                                               for v in variants}, 'population': population}}


def select_top(scores, identities, n, eligible_ids=None):
    """Total descending, numeric CIK ascending, permanent security ID ascending."""
    if type(n) is not int or n <= 0:
        raise ValueError('PORTFOLIO_SIZE_INVALID')
    eligible = set(scores) if eligible_ids is None else set(eligible_ids)
    candidates = []
    for key, result in scores.items():
        if key not in eligible or not _finite(result.get('total')):
            continue
        identity = identities[key]
        cik, sid = identity.get('cik'), identity.get('security_id', key)
        if not isinstance(cik, str) or not cik.isdigit() or len(cik) > 10 or int(cik) == 0:
            raise ValueError('PERMANENT_ISSUER_ID_REQUIRED')
        if not isinstance(sid, str) or not sid.strip():
            raise ValueError('PERMANENT_SECURITY_ID_REQUIRED')
        candidates.append((result['total'], cik.zfill(10), sid, key))
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    selected, seen = [], set()
    for total, cik, sid, key in candidates:
        if cik in seen:
            continue
        seen.add(cik)
        selected.append({'security_id': sid, 'cik': cik, 'total': total, 'rank': len(selected) + 1, 'key': key})
        if len(selected) == n:
            break
    return tuple(selected)
