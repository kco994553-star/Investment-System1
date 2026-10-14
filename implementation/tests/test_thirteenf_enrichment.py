"""Narrow SEC disclosure proposal; invented aggregate values, never downloaded prices."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path

import pytest

from investment_system.config.manager_styles import load_manager_styles
from investment_system.product import thirteenf_quarter as q
from investment_system.product.public_engine_screens import generate_screen_bundle, require_public_screen
from investment_system.product.device_actual_catalog import public_actual_catalog
from tests.test_public_engine_screens import thirteen_f_manifest, NOW
from tests.test_sec_13f import _xml, _row


def generated(tmp_path):
    manifest = thirteen_f_manifest(tmp_path)
    manifest['thirteen_f_details'] = True
    return generate_screen_bundle(manifest=manifest, input_root=tmp_path, as_of=NOW,
                                  stale_after=timedelta(days=1))['sec-13f-changes.json']


def test_complete_snapshots_publish_unchanged_issuer_and_original_dollar_basis(tmp_path):
    payload = generated(tmp_path)
    report = payload['data']['reports'][0]
    current = report['details']['current']
    assert current['filing_date'] == '2026-08-01'
    holding, = current['reported_holdings']
    assert holding['issuer_names'] == ['Synthetic Issuer']
    assert holding['reported_value'] == 2000 and holding['reported_value_basis'] == 'USD_DOLLARS'
    assert holding['reported_quantity'] == 150
    assert all(k not in holding for k in ('price', 'unit_price', 'market_cap', 'portfolio_weight'))
    assert q.summarize_report(report, q.target_securities(public_actual_catalog()))['holdings_count'] == 1


@pytest.mark.parametrize('mutate', [
    lambda p: p['data']['reports'][0]['details']['current'].update(filing_date='2026-05-01'),
    lambda p: p['data']['reports'][0]['details'].update(scope='PRIVATE_DEVICE_HOLDINGS'),
    lambda p: p['data']['reports'][0]['details']['current']['reported_holdings'][0].update(price=3),
    lambda p: p['data']['reports'][0]['details']['current']['reported_holdings'][0].update(reported_quantity=0),
    lambda p: p['data']['reports'][0]['details']['current']['reported_holdings'][0].update(reported_value_basis='CURRENT_USD'),
    lambda p: p['data']['reports'][0]['details']['current']['reported_holdings'][0].update(issuer_names=['invalid' + '@' + 'host.test']),
])
def test_projection_rejects_unreviewed_fields_units_and_future_or_invalid_dates(tmp_path, mutate):
    payload = generated(tmp_path)
    mutate(payload)
    with pytest.raises(ValueError, match='PUBLIC_SCREEN_INVALID'):
        require_public_screen('sec-13f-changes.json', payload)


def test_partial_capture_has_no_public_snapshot(tmp_path):
    manifest = thirteen_f_manifest(tmp_path)
    manifest['thirteen_f_details'] = True
    manifest['thirteen_f'][0]['current']['metadata']['complete'] = False
    payload = generate_screen_bundle(manifest=manifest, input_root=tmp_path, as_of=NOW,
                                     stale_after=timedelta(days=1))['sec-13f-changes.json']
    report = payload['data']['reports'][0]
    assert report['state'] == 'NOT_AVAILABLE' and report['details'] is None and report['changes'] == []


def test_options_and_principal_rows_not_published_in_long_share_scope(tmp_path):
    manifest = thirteen_f_manifest(tmp_path)
    manifest['thirteen_f_details'] = True
    for side in ('previous', 'current'):
        item = manifest['thirteen_f'][0][side]
        (tmp_path / item['file']).write_bytes(_xml(_row(quantity='100', sole='100', put_call='Put')))
    payload = generate_screen_bundle(manifest=manifest, input_root=tmp_path, as_of=NOW,
                                     stale_after=timedelta(days=1))['sec-13f-changes.json']
    assert payload['data']['reports'][0]['details']['current']['reported_holdings'] == []


def evidence_payload():
    cfg = load_manager_styles()
    cik = [m['candidate_cik'] for m in cfg['managers'][:4]]
    def holding(key):
        return {'cusip': '67066G104', 'security_key': key * 64, 'reported_quantity': 10,
                'issuer_names': ['Synthetic Issuer'], 'reported_value': 100, 'reported_value_basis': 'USD_DOLLARS'}
    reports = []
    for i, manager in enumerate(cik):
        key = chr(97 + i)
        reports.append({'manager_cik': manager, 'current_quarter': '2026-06-30', 'previous_quarter': '2026-03-31',
                        'state': 'LIVE', 'changes': [{'kind': 'EXIT', 'unit': 'SH', 'security_key': key*64,
                        'cusip': '67066G104', 'reported_before': 10, 'reported_after': 0, 'reported_delta': -10}],
                        'details': {'scope': 'SEC_REPORTED_LONG_SH_NONOPTION',
                                    'previous': {'filing_date': '2026-05-01', 'reported_holdings': [holding(key)]},
                                    'current': {'filing_date': '2026-08-01', 'reported_holdings': []}}})
    reports[3]['details']['current']['reported_holdings'] = [holding('d')]
    reports[3]['changes'] = []
    return {'data': {'reports': reports, 'managers': [{'cik': c, 'state': 'VERIFIED'} for c in cik]}}, cfg


def test_three_unique_verified_complete_live_exits_same_quarter_only_informational():
    payload, cfg = evidence_payload()
    row = q.playbook_evidence(payload, public_actual_catalog(), cfg)['nvda']
    assert row == {'quarter': '2026-06-30', 'tracked_holding_count': 1, 'tracked_holding_types': ['event'],
                   'observed_managers': 4, 'tracked_managers': 10, 'full_exit_count': 3,
                   'structural_event': True, 'reason_code': 'THIRTEENF_REPORTED_FULL_EXITS_3_PLUS',
                   'informational_only': True}
    for mutate in (lambda p: p['data']['reports'][2].update(state='STALE'),
                   lambda p: p['data']['reports'][2].update(current_quarter='2026-03-31'),
                   lambda p: p['data']['managers'][2].update(state='NOT_AVAILABLE'),
                   lambda p: p['data']['reports'][2].pop('details'),
                   lambda p: p['data']['reports'][2].update(changes=[]),
                   lambda p: p['data']['reports'][2]['changes'][0].update(cusip='594918104'),
                   lambda p: (p['data']['reports'][2].update(manager_cik='0000000011'), p['data']['managers'][2].update(cik='0000000011')),
                   lambda p: p['data']['reports'][2]['details']['current'].update(reported_holdings=[deepcopy(p['data']['reports'][2]['details']['previous']['reported_holdings'][0])])):
        other = deepcopy(payload)
        mutate(other)
        assert q.playbook_evidence(other, public_actual_catalog(), cfg)['nvda']['structural_event'] is False
    other = deepcopy(payload)
    other['data']['reports'][2]['manager_cik'] = other['data']['reports'][1]['manager_cik']
    assert q.playbook_evidence(other, public_actual_catalog(), cfg)['nvda']['full_exit_count'] == 1


def test_legacy_coverage_zero_remains_na_not_zero_held():
    payload, cfg = evidence_payload()
    for r in payload['data']['reports']:
        r.pop('details')
    row = q.playbook_evidence(payload, public_actual_catalog(), cfg)['nvda']
    assert row['tracked_holding_count'] is None and row['full_exit_count'] is None
    assert row['structural_event'] is False and row['observed_managers'] == 0
    assert q.playbook_evidence(payload, public_actual_catalog(), cfg)['hanmi']['reason_code'] == 'NOT_13F_SECURITY'


def test_eaton_exact_public_identity_with_sec_source_digest():
    targets = {t['company_id']: t for t in q.target_securities(public_actual_catalog())}
    assert targets['etn']['cusip'] == 'G29183103'
    assert q.EATON_EVIDENCE['source_sha256'] == json.loads((Path(__file__).parents[1] /
        'data/raw/manifests/nport_xml__0001752724-25-034052.json').read_text())['sha256']
    catalog = public_actual_catalog()
    next(i for i in catalog['instruments'] if i['ticker'] == 'ETN')['security_reference']['value'] = 'IE0000000000'
    assert next(t for t in q.target_securities(catalog) if t['company_id'] == 'etn')['cusip'] is None
