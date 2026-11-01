"""calc 23.1 scoring of the U-A population at S for the four fixed presets ('default' = balanced, computed once).

Ported from research/qgv_backtest @ 56a0e8ce (#417/#430) and changed for EXP-STOCK-INDICATOR-DECILES-v1:
scoring_adapter.prepare_companies (L43) and the score_universe calls of scoring_adapter.score_variants (L87). Changed:

- no W0-W3 / D0-D2 weight variants: one score_universe call per fixed preset (qgv_v2.PRESETS: balanced, quality, growth,
  value) with the official inner weights, type weights ON and the value-trap gate ON (engine defaults); 'default' is
  qgv_v2.DEFAULT_PRESET == 'balanced', so its result is the balanced result object itself, never a fifth call;
- the scoring population is given explicitly (settings.SCORING_POPULATION = U-A members at S); rows outside it are not
  scored and never enter a percentile pool; U-B selects from these same scores (selection.py);
- engine companies follow qgv2_inputs.engine_companies field by field (one cross-section point per CIK among LIVE/STALE
  rows, profile/factors/qg_axes/v_inputs from qgv2_inputs.normalize, pricefree_memberships, cyclical_basis from
  playbook.classify_types_v0); as in #430 the sector subgroup comes from the as-filed SIC only (no ticker: today's fixed
  ticker-to-sector table is not applied to history);
- #430's VERIFIED basis_alignment receipt check on quotes is not ported. Quotes are taken as already basis-checked by the
  price part, which withholds a quote with an UPPER_SNAKE reason (as the operating path withholds SPLIT_AFTER_SHARE_COUNT
  or ADR_RATIO_UNCONFIRMED). A withheld or missing quote leaves V to the engine's own NA rule (NO_DEVICE_PRICE). An ADR
  quote is per ADS; runner.scoring_quotes turns it into a price per ordinary share with the record's adr_ratio before it
  reaches this module, or withholds it with ADR_RATIO_UNCONFIRMED.

Missing-data rules, type weights and the gate are the engine's, unchanged; no 15-factor completeness rule is added.
Scores are returned unrounded as the engine gives them (floats). Engine quotes are {price, currency, month_closes}: the
engine's V arithmetic is float, so Decimal prices are converted with float() at this boundary only.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import math
import re

from ...qgv import playbook, qgv2_inputs, qgv_v2, v2_factors, v2_scoring
from ...qgv.dcf_parameters import load_default_dcf_parameters
from ...qgv.type_config import load_official_type_config
from . import settings

SCHEMA = 'exp-deciles-scores/1'
_REASON = re.compile(r'[A-Z][A-Z0-9_]{0,63}')
_MONTH = re.compile(r'\d{4}-\d{2}')

# reason codes
SCORING_ROW_MISSING = 'SCORING_ROW_MISSING'
QUOTE_SUPPLIED = 'SUPPLIED'
QUOTE_NOT_SUPPLIED = 'NOT_SUPPLIED'
QUOTE_PRICE_INVALID = 'QUOTE_PRICE_INVALID'
QUOTE_CURRENCY_MISSING = 'QUOTE_CURRENCY_MISSING'


def _number(value):
    """int / float / Decimal (not bool) -> float when finite, else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return None
    out = float(value)
    return out if math.isfinite(out) else None


def _cik(value):
    if not isinstance(value, str) or not value.isdigit() or len(value) != 10 or int(value) == 0:
        raise ValueError('PERMANENT_ISSUER_ID_REQUIRED')
    return value


def population_rows(rows, population):
    """({security_id: row} for the population, [security_ids without a row]). Duplicate issuers are refused."""
    selected, missing, ciks = {}, [], set()
    for sid in sorted(set(population)):
        row = rows.get(sid)
        if row is None:
            missing.append(sid)
            continue
        cik = _cik(row.get('cik'))
        if cik in ciks:
            raise ValueError('DUPLICATE_ISSUER_IN_SCORING_POPULATION')
        ciks.add(cik)
        if row.get('calc_version') != v2_factors.CALC_VERSION:
            raise ValueError('CALC_VERSION_MISMATCH')
        selected[sid] = row
    return selected, missing


def prepare_companies(rows, *, type_config, playbook_config):
    """Q/G percentiles over exactly these rows (v2_scoring.score_rows), then engine companies.

    Returns (companies, summary, qg) where qg[key] is the score_rows output (factors, axes with reason codes)."""
    rows = deepcopy(rows)
    if not rows:
        return {}, {'cross_section_size': 0, 'cross_section_by_profile': {'GENERAL': 0, 'FINANCIAL': 0}}, {}
    scores, summary = v2_scoring.score_rows(rows, calc_version=v2_factors.CALC_VERSION)
    ranks = v2_scoring.volatility_rank_rows(rows, calc_version=v2_factors.CALC_VERSION)
    companies, qg, seen = {}, {}, set()
    for key in sorted(rows):
        row = rows[key]
        scored = scores[('universe', key)]
        row['factors'], row['axes'] = scored['factors'], scored['axes']
        metrics = dict(row.get('metrics') or {})
        rank = ranks[('universe', key)]
        if rank is None:
            metrics.pop('revenue_volatility_5y_rank_pct', None)
        else:
            metrics['revenue_volatility_5y_rank_pct'] = rank
        row['metrics'] = metrics
        pooled = row.get('state') in v2_scoring.SCORED_STATES and row['cik'] not in seen
        if pooled:
            seen.add(row['cik'])
        rec = qgv2_inputs.normalize(row, pooled)
        group = playbook.sector_for(playbook_config, None, None, rec['sic'])
        vol = rec['metrics'].get('revenue_volatility_5y_rank_pct')
        info = {'sic': rec['sic'], 'sector_subgroup': (group or {}).get('sector'),
                'revenue_volatility_5y_rank_pct': vol / 100 if qgv_v2.finite(vol) else None}
        cyclical = (playbook.classify_types_v0(playbook_config, info).get('cyclical') or {}).get('member') is True
        companies[key] = {'cyclical_basis': cyclical, 'cik': rec['cik'], 'security_id': key,
                          'industry_group': rec['industry_group'], 'profile': rec['profile'], 'factors': rec['factors'],
                          'v_inputs': rec['v_inputs'], 'qg_axes': rec['qg_axes'],
                          'in_cross_section': rec['in_cross_section'] is not False,
                          'memberships': qgv_v2.pricefree_memberships(rec['metrics'], type_config)}
        qg[key] = scored
    return companies, summary, qg


def engine_quotes(quotes, keys):
    """({key: {price, currency, month_closes}} for the engine, {key: quote status}) for the population keys only.

    Input quote: {'price': Decimal | int | float, 'currency': 'USD', 'month_closes': {'YYYY-MM': number},
    'withheld_reason': None | UPPER_SNAKE, 'price_label': optional}."""
    quotes = quotes or {}
    out, status = {}, {}
    for key in sorted(keys):
        quote = quotes.get(key)
        if quote is None:
            status[key] = QUOTE_NOT_SUPPLIED
            continue
        if not isinstance(quote, dict):
            raise TypeError('QUOTE_MUST_BE_DICT')
        withheld = quote.get('withheld_reason')
        if withheld is not None:
            if not isinstance(withheld, str) or not _REASON.fullmatch(withheld):
                raise ValueError('WITHHELD_REASON_INVALID')
            status[key] = withheld
            continue
        price = _number(quote.get('price'))
        if price is None or price <= 0:
            status[key] = QUOTE_PRICE_INVALID
            continue
        if not isinstance(quote.get('currency'), str) or not quote['currency']:
            status[key] = QUOTE_CURRENCY_MISSING
            continue
        closes = {}
        for month, value in (quote.get('month_closes') or {}).items():
            number = _number(value)
            if isinstance(month, str) and _MONTH.fullmatch(month) and number is not None and number > 0:
                closes[month] = number
        out[key] = {'price': price, 'currency': quote['currency'], 'month_closes': closes}
        status[key] = QUOTE_SUPPLIED
    return out, status


def _axis_reasons(result, axis, qg_axis):
    """Unique UPPER_SNAKE reasons for a missing axis score (empty when the score exists)."""
    engine_axis = result['axes'][axis]
    if engine_axis.get('score') is not None:
        return []
    reasons = []
    if axis in ('Q', 'G'):
        reasons.extend((qg_axis or {}).get('reason_codes') or [])
    if engine_axis.get('reason'):
        reasons.append(engine_axis['reason'])
    if axis == 'V':
        reasons.extend(sorted({f['reason'] for k, f in result['factors'].items()
                               if k in qgv_v2.WEIGHTS['V'] and f['score'] is None and f.get('reason')}))
    return list(dict.fromkeys(reasons))


def _empty_security(sid, row, reason):
    none = dict.fromkeys(settings.PRESET_IDS)
    totals = dict(none)
    totals[settings.DEFAULT_PRESET_ALIAS] = None
    return {'security_id': sid, 'cik': (row or {}).get('cik'), 'row_state': None, 'row_reasons': [reason],
            'quote_status': QUOTE_NOT_SUPPLIED, 'axes': dict.fromkeys(settings.AXES),
            'axis_reasons': {a: [reason] for a in settings.AXES}, 'totals': totals,
            'total_reasons': {p: reason for p in totals}, 'weights': dict(none), 'value_trap_gate': None,
            'flags': [], 'q_industry_percentile': None, 'factors': dict.fromkeys(qgv_v2.FACTORS),
            'factor_reasons': dict.fromkeys(qgv_v2.FACTORS, reason)}


def score_population(rows, quotes, *, population, type_config=None, parameters=None, playbook_config=None,
                     include_engine=False):
    """Score the population (U-A representative security IDs at S) with the four presets.

    rows: {security_id: pit.compute_row(...) row}; quotes: {security_id: quote} (engine_quotes doc).
    Returns {'schema', 'scoring_population', 'calc_version', 'securities': {sid: {security_id, cik, row_state,
    row_reasons, quote_status, axes {Q,G,V}, axis_reasons, totals {balanced, quality, growth, value, default},
    total_reasons, weights {preset: {Q,G,V}}, value_trap_gate, flags, q_industry_percentile, factors, factor_reasons}},
    'summary', 'engine' (only with include_engine: {preset: score_universe result, 'default': the balanced object})}."""
    type_config = load_official_type_config().to_dict() if type_config is None else type_config
    parameters = load_default_dcf_parameters() if parameters is None else parameters
    playbook_config = playbook.load_config() if playbook_config is None else playbook_config
    selected, missing = population_rows(rows, population)
    companies, summary, qg = prepare_companies(selected, type_config=type_config, playbook_config=playbook_config)
    priced, quote_status = engine_quotes(quotes, companies)
    runs = {}
    for preset in settings.PRESET_IDS:
        runs[preset] = qgv_v2.score_universe(deepcopy(companies), priced, type_config=type_config,
                                             parameters=parameters, preset=preset, gate=settings.GATE,
                                             type_weights=settings.TYPE_WEIGHTS)
    runs[settings.DEFAULT_PRESET_ALIAS] = runs[settings.PRESET_ALIASES[settings.DEFAULT_PRESET_ALIAS]]
    securities = {}
    base = settings.PRESET_ALIASES[settings.DEFAULT_PRESET_ALIAS]
    for key in sorted(companies):
        first = runs[base][key]
        for preset in settings.PRESET_IDS:
            other = runs[preset][key]
            if (any(other['axes'][a]['score'] != first['axes'][a]['score'] for a in settings.AXES)
                    or other['value_trap_gate'] != first['value_trap_gate']
                    or other['q_industry_percentile'] != first['q_industry_percentile']):
                raise ValueError('AXIS_SCORE_DEPENDS_ON_PRESET')
        row = selected[key]
        totals = {p: runs[p][key]['total'] for p in settings.PRESET_IDS}
        totals[settings.DEFAULT_PRESET_ALIAS] = totals[base]
        total_reasons = {p: runs[p][key]['total_reason'] for p in settings.PRESET_IDS}
        total_reasons[settings.DEFAULT_PRESET_ALIAS] = total_reasons[base]
        securities[key] = {
            'security_id': key, 'cik': row['cik'], 'row_state': row.get('state'),
            'row_reasons': list(row.get('reason_codes') or []), 'quote_status': quote_status[key],
            'axes': {a: first['axes'][a]['score'] for a in settings.AXES},
            'axis_reasons': {a: _axis_reasons(first, a, qg[key]['axes'].get(a)) for a in settings.AXES},
            'totals': totals, 'total_reasons': total_reasons,
            'weights': {p: dict(runs[p][key]['weights']) for p in settings.PRESET_IDS},
            'value_trap_gate': first['value_trap_gate'], 'flags': list(first['flags']),
            'q_industry_percentile': first['q_industry_percentile'],
            'factors': {f: first['factors'][f]['score'] for f in qgv_v2.FACTORS},
            'factor_reasons': {f: first['factors'][f]['reason'] for f in qgv_v2.FACTORS},
        }
    for sid in missing:
        securities[sid] = _empty_security(sid, None, SCORING_ROW_MISSING)
    out = {'schema': SCHEMA, 'scoring_population': settings.SCORING_POPULATION,
           'calc_version': v2_factors.CALC_VERSION, 'securities': dict(sorted(securities.items())),
           'summary': {'population_size': len(set(population)), 'rows_scored': len(companies),
                       'rows_missing': len(missing),
                       'percentile_population_size': summary['cross_section_size'],
                       'cross_section_by_profile': summary['cross_section_by_profile'],
                       'presets_computed': settings.PRESET_IDS, 'preset_aliases': dict(settings.PRESET_ALIASES),
                       'quotes_supplied': sum(1 for s in quote_status.values() if s == QUOTE_SUPPLIED),
                       'axes_available': {a: sum(1 for s in securities.values() if s['axes'][a] is not None)
                                          for a in settings.AXES},
                       'totals_available': {p: sum(1 for s in securities.values() if s['totals'][p] is not None)
                                            for p in settings.PRESET_IDS}}}
    if include_engine:
        out['engine'] = runs
    return out
