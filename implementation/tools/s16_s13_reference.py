#!/usr/bin/env python3
"""Synthetic Python reference vectors for the S16 13F quarter view and the S13 custom type PREVIEW (JS parity).

Writes tests/fixtures/s16_s13_reference_v1.json. Reported 13F quantities, metrics and factor scores are invented
test data; the catalog rows are the already-public TARGET identity fields (ticker, label, ISIN or exchange code).
No prices, values, holdings or personal data. Usage: python tools/s16_s13_reference.py [--check]
"""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.product import thirteenf_quarter as q  # noqa: E402
from investment_system.product.device_actual_catalog import public_actual_catalog  # noqa: E402
from investment_system.qgv import type_preview as tp  # noqa: E402

OUT = ROOT / 'tests/fixtures/s16_s13_reference_v1.json'
FACTORS = ('competitive_advantage', 'eps_fcf_per_share_growth', 'excess_growth_vs_industry', 'fcf_quality', 'financial_health',
           'growth_durability', 'growth_efficiency', 'management_quality', 'margin_quality', 'market_position',
           'next_3_5y_growth', 'revenue_growth', 'roic_wacc')


def catalog():
    return {'instruments': [{'ticker': i['ticker'], 'label': i['label'], 'security_reference': i['security_reference']}
                            for i in public_actual_catalog()['instruments']]}


def change(cusip, before, after, key='c'):
    kind = 'NEW' if before == 0 else 'EXIT' if after == 0 else 'ADD' if after > before else 'REDUCE'
    return {'cusip': cusip, 'security_key': key * 64, 'unit': 'SH', 'kind': kind,
            'reported_before': before, 'reported_after': after, 'reported_delta': after - before}


def report(cik, changes, state='LIVE', previous='2026-03-31', current='2026-06-30'):
    return {'manager_cik': cik, 'previous_quarter': previous, 'current_quarter': current, 'state': state,
            'changes': changes, 'source_hashes': {'previous': 'a' * 64, 'current': 'b' * 64}}


def types_payload(companies):
    return {'data': {'companies': companies}}


def qg_payload(companies):
    return {'data': {'companies': {cid: {'factors': {f: {'score': scores.get(f, 50.0), 'state': state} for f in FACTORS}}
                                   for cid, (scores, state) in companies.items()}}}


def s16_cases():
    cat = catalog()
    out = [('isin_to_cusip', 'cusip_from_isin', {'isins': ['US67066G1040', 'USN070592100', 'US02079K3059', 'IE00B8KQN827',
            'US67066G1041', 'us67066g1040', 'CA0679011084', 'US0000000000', 'XS1234567890', None, 'US67066G104']})]
    nvda, msft, googl = 'US67066G1040'[2:11], 'US5949181045'[2:11], 'US02079K3059'[2:11]
    reports = [
        report('0000000001', [change('Z99999995', 7, 0), change(nvda, 100, 250), change('A00000009', 0, 3), change(msft, 40, 10)]),
        report('0000000002', [change(nvda, 0, 5000), change(nvda, 20, 0, 'd'), change(googl, 9, 0), change('B12345671', 1, 2)]),
        report('0000000003', [], state='NOT_AVAILABLE'),
        report('0000000004', [change('C00000000', 4, 8)], state='STALE'),
    ]
    out.append(('pipeline_target_and_other', 's16_pipeline', {'catalog': cat, 'reports': reports}))
    out.append(('pipeline_catalog_missing', 's16_pipeline', {'catalog': None, 'reports': reports[:2]}))
    dup = copy.deepcopy(cat)
    dup['instruments'].append(copy.deepcopy(dup['instruments'][5]))
    dup['instruments'] = [i for i in dup['instruments'] if i['ticker'] != 'ROK']
    out.append(('pipeline_duplicate_and_missing_ticker', 's16_pipeline', {'catalog': dup, 'reports': reports[:1]}))
    out.append(('pipeline_no_reports', 's16_pipeline', {'catalog': cat, 'reports': []}))
    return out


def custom(mutate):
    config = tp.official_copy()
    mutate(config)
    return config


def s13_cases():
    def growth_weights(c):
        c['types'][0]['weights'] = {'Q': 20, 'G': 60, 'V': 20}

    def growth_ramp(c):
        c['types'][0]['rule']['lower'] = 0.25
        c['types'][0]['rule']['upper'] = 0.35

    def mixing(c):
        c['mixing']['pillar_max'] = 45
        c['fallback']['weights'] = {'Q': 40, 'G': 30, 'V': 30}

    types = types_payload({
        'nvda': {'metrics': {'revenue_cagr_3y': 0.31, 'roic': 0.42}},
        'amd': {'metrics': {'revenue_cagr_3y': 0.12, 'roic': None}},
        'msft': {'metrics': {'revenue_cagr_3y': 0.04, 'roic': 0.3}},
        'asml': {'metrics': {'revenue_cagr_3y': None, 'roic': None}},
        'intc': {'metrics': {'revenue_cagr_3y': True, 'roic': None}},
        'zz_not_target': {'metrics': {'revenue_cagr_3y': 0.5, 'roic': 0.1}},
    })
    qg = qg_payload({'nvda': ({'competitive_advantage': 90.0, 'roic_wacc': 30.0}, 'LIVE'), 'amd': ({}, 'STALE'),
                     'msft': ({'market_position': 77.5}, 'LIVE')})
    return [
        ('official_copy_unchanged', 'type_target_preview', {'types': types, 'qg': qg, 'custom': tp.official_copy()}),
        ('growth_weights_changed', 'type_target_preview', {'types': types, 'qg': qg, 'custom': custom(growth_weights)}),
        ('growth_ramp_changes_types', 'type_target_preview', {'types': types, 'qg': None, 'custom': custom(growth_ramp)}),
        ('mixing_and_fallback', 'type_target_preview', {'types': types, 'qg': qg, 'custom': custom(mixing)}),
        ('no_public_types', 'type_target_preview', {'types': None, 'qg': qg, 'custom': custom(growth_weights)}),
        ('invalid_custom', 'type_target_preview', {'types': types, 'qg': qg,
                                                   'custom': custom(lambda c: c['types'][0]['weights'].update(Q=99))}),
        ('diff_structure', 'config_diff', {'official': tp.official_copy(), 'custom': custom(
            lambda c: (c['types'].pop(1), c['mixing']['exclusive_pairs'].append(['growth', 'value']), c.update(extra_flag=True)))}),
    ]


def replay(case):
    if case.get('synthetic') is not True:
        raise ValueError('SYNTHETIC_ONLY')
    op, data = case['operation'], case['input']
    if op == 'cusip_from_isin':
        return [q.cusip_from_isin(x) for x in data['isins']]
    if op == 's16_pipeline':
        targets = q.target_securities(data['catalog'])
        summaries = [q.summarize_report(r, targets) for r in data['reports']]
        return {'targets': targets, 'summaries': summaries, 'overlap': q.target_overlap(summaries, targets)}
    if op == 'type_target_preview':
        return tp.target_type_preview(data['types'], data['qg'], data['custom'])
    if op == 'config_diff':
        return tp.config_diff(data['official'], data['custom'])
    raise ValueError('UNKNOWN_OPERATION')


def build():
    result = []
    for cid, op, data in s16_cases() + s13_cases():
        case = {'id': cid, 'synthetic': True, 'operation': op, 'input': data}
        case['expected'] = replay(case)
        result.append(case)
    return {'synthetic': True, 'role': 'REFERENCE_TEST_ONLY', 'cases': result}


def text():
    return json.dumps(build(), sort_keys=True, ensure_ascii=True, allow_nan=False, indent=1) + '\n'


def main(argv):
    if '--check' in argv:
        ok = OUT.exists() and OUT.read_text() == text()
        print('S16_S13_REFERENCE_OK' if ok else 'S16_S13_REFERENCE_STALE')
        return 0 if ok else 1
    OUT.write_text(text())
    print('wrote', OUT.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
