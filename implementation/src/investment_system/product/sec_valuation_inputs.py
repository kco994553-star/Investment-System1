"""Price-free FCFE-per-share and V inputs from retained SEC 10-K facts (fcfe/1).

User decision 2026-10-11 (V1_UNCALIBRATED_DEFAULT):
FCFE = operating cash flow - capital expenditure + net borrowing, on weighted
average diluted shares, same fiscal period and currency. Net borrowing is
long-term debt issuance + net short-term borrowing - long-term debt repayment.

Only exact us-gaap concepts listed in COMPONENTS are read, in fallback order.
A component that the filing does not report is NOT_AVAILABLE; it is never
replaced by zero (a reported zero is a real zero). No price, market cap, V
score or price ratio is produced here; the device computes those in RAM.
"""
from __future__ import annotations

from datetime import date
import math
import re

FILENAME = 'sec-valuation-inputs.json'
KIND = 'SEC_VALUATION_INPUTS'
FCFE_DEFINITION = 'fcfe/1'
SHARE_BASIS = 'WEIGHTED_AVERAGE_DILUTED'
STATES = ('LIVE', 'STALE', 'NOT_AVAILABLE')
ANNUAL_FORMS = ('10-K', '10-K/A')
# (component, alternatives); an alternative is usable only when every term is reported.
COMPONENTS = (
    ('operating_cash_flow', ((('NetCashProvidedByUsedInOperatingActivities', 1),),
                             (('NetCashProvidedByUsedInOperatingActivitiesContinuingOperations', 1),))),
    ('capital_expenditure', ((('PaymentsToAcquirePropertyPlantAndEquipment', 1),),
                             (('PaymentsToAcquireProductiveAssets', 1),))),
    ('long_term_debt_issuance', ((('ProceedsFromIssuanceOfLongTermDebt', 1),),
                                 (('ProceedsFromIssuanceOfSeniorLongTermDebt', 1),))),
    ('long_term_debt_repayment', ((('RepaymentsOfLongTermDebt', 1),),
                                  (('RepaymentsOfSeniorDebt', 1),))),
    ('net_short_term_borrowing', ((('ProceedsFromRepaymentsOfShortTermDebt', 1),),
                                  (('ProceedsFromRepaymentsOfCommercialPaper', 1),),
                                  (('ProceedsFromShortTermDebt', 1), ('RepaymentsOfShortTermDebt', -1)))),
    ('diluted_shares', ((('WeightedAverageNumberOfDilutedSharesOutstanding', 1),),)),
)
COMPONENT_KEYS = tuple(key for key, _ in COMPONENTS)
ALTERNATIVES = {key: tuple(tuple(c for c, _ in alt) for alt in alts) for key, alts in COMPONENTS}
SIGNS = {key: {tuple(c for c, _ in alt): tuple(s for _, s in alt) for alt in alts} for key, alts in COMPONENTS}
FCFE_REASONS = frozenset({
    'SEC_INPUT_NOT_AVAILABLE', 'US_GAAP_CASH_FLOW_NOT_REPORTED', 'PERIOD_AMBIGUOUS', 'CURRENCY_AMBIGUOUS',
    'COMPONENT_CURRENCY_MISMATCH', 'COMPONENT_AMBIGUOUS', 'MIXED_FILINGS', 'DILUTED_SHARES_NON_POSITIVE',
    'NUMERIC_INVALID', *(key.upper() + '_MISSING' for key in COMPONENT_KEYS),
})
V_INPUT_KEYS = ('eps', 'revenue', 'revenue_prev')
V_REASONS = frozenset({'SEC_INPUT_NOT_AVAILABLE', 'SEC_INPUT_AMBIGUOUS', 'EPS_MISSING', 'REVENUE_MISSING', 'REVENUE_PREV_MISSING'})
_AMBIGUOUS = {'AMBIGUOUS_FACT_VALUES', 'AMBIGUOUS_REVISION_ORDER', 'AMBIGUOUS_FILING'}


def _need(condition):
    if not condition:
        raise ValueError('PUBLIC_SCREEN_INVALID')


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _day(value):
    _need(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is not None)
    return date.fromisoformat(value)


def fcfe_total(components):
    """The adopted sum, in a fixed order shared with the JS validator."""
    c = {k: components[k]['value'] for k in COMPONENT_KEYS}
    return (c['operating_cash_flow'] - c['capital_expenditure'] + c['long_term_debt_issuance']
            + c['net_short_term_borrowing'] - c['long_term_debt_repayment'])


def empty_fcfe(reason='SEC_INPUT_NOT_AVAILABLE'):
    return {'state': 'NOT_AVAILABLE', 'reason_codes': [reason], 'fcfe_per_share': None, 'currency': None,
            'fiscal_period_start': None, 'fiscal_period_end': None, 'accn': None, 'form': None,
            'components': dict.fromkeys(COMPONENT_KEYS)}


def empty_v_inputs(reason='SEC_INPUT_NOT_AVAILABLE'):
    return {'state': 'NOT_AVAILABLE', 'reason_codes': [reason], 'eps': None, 'revenue': None, 'revenue_prev': None, 'currency': None}


def empty_row():
    return {'state': 'NOT_AVAILABLE', 'source_hashes': {}, 'fcfe': empty_fcfe(), 'v_inputs': empty_v_inputs()}


def _annual(row):
    try:
        start, end = date.fromisoformat(row['start']), date.fromisoformat(row['end'])
    except (TypeError, ValueError):
        return False
    return 300 <= (end - start).days <= 400 and row['form'] in ANNUAL_FORMS


def project_fcfe(m1, state):
    """Latest annual fiscal period of operating cash flow; every component in that exact period."""
    facts = [r for r in m1.get('selected_input_facts') or () if r.get('taxonomy') == 'us-gaap' and _annual(r) and _finite(r.get('value'))]
    by = {}
    for r in facts:
        by.setdefault((r['concept'], r['unit'], r['start'], r['end']), r)
    ocf_concepts = {c for alt in ALTERNATIVES['operating_cash_flow'] for c in alt}
    ocf = [r for r in facts if r['concept'] in ocf_concepts and re.fullmatch(r'[A-Z]{3}', r['unit'])]
    if not ocf:
        return empty_fcfe('US_GAAP_CASH_FLOW_NOT_REPORTED')
    end = max(r['end'] for r in ocf)
    latest = [r for r in ocf if r['end'] == end]
    if len({r['start'] for r in latest}) != 1:
        return empty_fcfe('PERIOD_AMBIGUOUS')
    if len({r['unit'] for r in latest}) != 1:
        return empty_fcfe('CURRENCY_AMBIGUOUS')
    start, currency = latest[0]['start'], latest[0]['unit']
    out = empty_fcfe()
    out.update(reason_codes=[], currency=currency, fiscal_period_start=start, fiscal_period_end=end)
    used, reasons = [], []
    for key, alternatives in COMPONENTS:
        unit = 'shares' if key == 'diluted_shares' else currency
        for alt in alternatives:
            hits = [by.get((concept, unit, start, end)) for concept, _ in alt]
            if all(hits):
                value = math.fsum(sign * hit['value'] for (_, sign), hit in zip(alt, hits))
                out['components'][key] = {'concepts': [c for c, _ in alt], 'value': value}
                used.extend(hits)
                break
        else:
            concepts = {c for alt in alternatives for c, _ in alt}
            if any(r['concept'] in concepts and r['start'] == start and r['end'] == end and r['unit'] != unit for r in facts):
                reasons.append('COMPONENT_CURRENCY_MISMATCH')
            elif any(c.get('taxonomy') == 'us-gaap' and c.get('concept') in concepts and c.get('end') == end
                     and set(c.get('exclusion_reasons') or ()) & _AMBIGUOUS for c in m1.get('revision_candidates') or ()):
                reasons.append('COMPONENT_AMBIGUOUS')
            else:
                reasons.append(key.upper() + '_MISSING')
    accns = {r['accn'] for r in used}
    if len(accns) == 1:
        out['accn'] = next(iter(accns))
        out['form'] = used[0]['form'] if len({r['form'] for r in used}) == 1 else None
    elif used:
        reasons.append('MIXED_FILINGS')
    shares = out['components']['diluted_shares']
    if shares is not None and shares['value'] <= 0:
        reasons.append('DILUTED_SHARES_NON_POSITIVE')
    if not reasons and out['form'] is None:
        reasons.append('MIXED_FILINGS')
    if not reasons:
        value = fcfe_total(out['components']) / shares['value']
        if not math.isfinite(value):
            reasons.append('NUMERIC_INVALID')
        else:
            out.update(state=state, fcfe_per_share=value)
    out['reason_codes'] = list(dict.fromkeys(reasons))
    return out


def project_v_inputs(m1, state, ambiguous):
    raw = m1.get('raw_fundamentals') if m1.get('status') == 'READY' else None
    if raw is None:
        return empty_v_inputs()
    if ambiguous:
        return empty_v_inputs('SEC_INPUT_AMBIGUOUS')
    out = {'state': 'NOT_AVAILABLE', 'reason_codes': [], 'currency': None}
    for key in V_INPUT_KEYS:
        value = raw.get(key)
        out[key] = float(value) if _finite(value) else None
        if out[key] is None:
            out['reason_codes'].append(key.upper() + '_MISSING')
    if any(out[k] is not None for k in V_INPUT_KEYS):
        out.update(state=state, currency=raw.get('reporting_currency') if re.fullmatch(r'[A-Z]{3}', str(raw.get('reporting_currency'))) else None)
        if out['currency'] is None:
            return empty_v_inputs('SEC_INPUT_AMBIGUOUS')
    return out


def project_row(m1, state, refs, ambiguous):
    fcfe = project_fcfe(m1, state)
    v = project_v_inputs(m1, state, ambiguous)
    states = (fcfe['state'], v['state'])
    return {'state': 'NOT_AVAILABLE' if states == ('NOT_AVAILABLE',) * 2 else state,
            'source_hashes': dict(refs), 'fcfe': fcfe, 'v_inputs': v}


def data(companies):
    return {'companies': companies, 'method_status': 'PROVISIONAL_UNCALIBRATED', 'availability_basis': 'OBSERVED_CAPTURE_ONLY',
            'fcfe_definition': FCFE_DEFINITION, 'share_basis': SHARE_BASIS}


def _keys(value, expected):
    _need(isinstance(value, dict) and set(value) == set(expected))


def _validate_fcfe(f, row_state):
    _keys(f, ('state', 'reason_codes', 'fcfe_per_share', 'currency', 'fiscal_period_start', 'fiscal_period_end', 'accn', 'form', 'components'))
    _need(f['state'] in ('NOT_AVAILABLE', row_state) and isinstance(f['reason_codes'], list) and len(set(f['reason_codes'])) == len(f['reason_codes']))
    _need(all(r in FCFE_REASONS for r in f['reason_codes']))
    _need(f['currency'] is None or isinstance(f['currency'], str) and re.fullmatch(r'[A-Z]{3}', f['currency']) is not None)
    _need((f['fiscal_period_start'] is None) == (f['fiscal_period_end'] is None))
    if f['fiscal_period_end'] is not None:
        days = (_day(f['fiscal_period_end']) - _day(f['fiscal_period_start'])).days
        _need(300 <= days <= 400)
    _need(f['accn'] is None or isinstance(f['accn'], str) and re.fullmatch(r'\d{18}', f['accn']) is not None)
    _need(f['form'] is None or f['form'] in ANNUAL_FORMS)
    _keys(f['components'], COMPONENT_KEYS)
    for key, c in f['components'].items():
        if c is None:
            continue
        _keys(c, ('concepts', 'value'))
        _need(isinstance(c['concepts'], list) and tuple(c['concepts']) in ALTERNATIVES[key] and _finite(c['value']))
    if f['state'] == 'NOT_AVAILABLE':
        _need(f['fcfe_per_share'] is None and f['reason_codes'])
        return
    _need(not f['reason_codes'] and all(f['components'][k] is not None for k in COMPONENT_KEYS))
    _need(f['currency'] is not None and f['fiscal_period_end'] is not None and f['accn'] is not None and f['form'] is not None)
    shares = f['components']['diluted_shares']['value']
    _need(shares > 0 and _finite(f['fcfe_per_share']))
    expected = fcfe_total(f['components']) / shares
    _need(math.isclose(f['fcfe_per_share'], expected, rel_tol=1e-12, abs_tol=1e-12))


def _validate_v(v, row_state):
    _keys(v, ('state', 'reason_codes', 'eps', 'revenue', 'revenue_prev', 'currency'))
    _need(v['state'] in ('NOT_AVAILABLE', row_state) and isinstance(v['reason_codes'], list) and all(r in V_REASONS for r in v['reason_codes']))
    _need(len(set(v['reason_codes'])) == len(v['reason_codes']))
    for key in V_INPUT_KEYS:
        _need(v[key] is None or _finite(v[key]))
    present = any(v[k] is not None for k in V_INPUT_KEYS)
    _need((v['state'] != 'NOT_AVAILABLE') == present)
    _need(v['currency'] is None if not present else isinstance(v['currency'], str) and re.fullmatch(r'[A-Z]{3}', v['currency']) is not None)
    if not present:
        _need(bool(v['reason_codes']))
    else:
        _need(v['reason_codes'] == [k.upper() + '_MISSING' for k in V_INPUT_KEYS if v[k] is None])


def validate_data(payload_data, companies, check_refs):
    """Strict schema; returns row states. check_refs(row, state) verifies provenance/freshness."""
    _keys(payload_data, ('companies', 'method_status', 'availability_basis', 'fcfe_definition', 'share_basis'))
    _need(payload_data['method_status'] == 'PROVISIONAL_UNCALIBRATED' and payload_data['availability_basis'] == 'OBSERVED_CAPTURE_ONLY')
    _need(payload_data['fcfe_definition'] == FCFE_DEFINITION and payload_data['share_basis'] == SHARE_BASIS)
    rows = payload_data['companies']
    _need(isinstance(rows, dict) and set(rows) == set(companies))
    states = []
    for row in rows.values():
        _keys(row, ('state', 'source_hashes', 'fcfe', 'v_inputs'))
        _need(row['state'] in STATES)
        _validate_fcfe(row['fcfe'], row['state'])
        _validate_v(row['v_inputs'], row['state'])
        inner = [row['fcfe']['state'], row['v_inputs']['state']]
        _need(row['state'] == ('NOT_AVAILABLE' if all(s == 'NOT_AVAILABLE' for s in inner) else next(s for s in inner if s != 'NOT_AVAILABLE')))
        check_refs(row, row['state'])
        states.append(row['state'])
    return states
