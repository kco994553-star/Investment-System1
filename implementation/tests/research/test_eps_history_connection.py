"""Synthetic fiscal EPS and identity evidence; no provider calls or real values."""
from copy import deepcopy
import pytest
from investment_system.research import sector_qgv as kernel
from investment_system.research import sector_qgv_held as held


def fixture():
    tax = {}
    for tag, unit, values in [('EarningsPerShareDiluted', 'USD/shares', [1, 2, 4, 8]),
                              ('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', [10]*4),
                              ('NetIncomeLoss', 'USD', [10, 20, 40, 80])]:
        tax[tag] = {'units': {unit: [dict(val=v, start=f'{y}-01-01', end=f'{y}-12-31',
            filed='2026-02-01', form='10-K', accn='SYN:one-basis')
            for y, v in zip(range(2022, 2026), values)]}}
    return {'cik': 1, 'facts': {'us-gaap': tax}}, dict(cik='0000000001',
        acquired_at='2026-02-02T12:00:00Z', fiscal_year_end='2025-12-31', state='LIVE',
        sic='3571', profile='GENERAL')


def execute(p, r):
    return held.held_eps_observation(p, r, 'SYN:source', as_of='2026-02-03T00:00:00Z',
        valuation_date='2026-02-02', accounting_template='GENERAL')


def proof(fields):
    return dict(schema_version='historical-common-share-basis/1', status='VERIFIED',
        issuer_id='0000000001', class_basis='SYN:common-class-A', attribution='COMMON_DILUTED',
        adjustment_basis='SYN:FY0-restated', valid_from='2022-01-01', valid_to='2025-12-31',
        source_available_at='2026-02-01T12:00:00Z', retrieved_at='2026-02-02T12:00:00Z',
        provenance=['SYN:class-note', 'SYN:split-reconciliation'],
        normalized_components_hash=kernel.digest(fields))


def test_extract_and_request_eps_but_do_not_invent_security_or_share_class():
    p, r = fixture(); o, d, f = execute(p, r)
    assert len(f) == 4 and f['eps_diluted_fy']['value'] == 8
    assert o['raw_components_available'] and o['value'] is None
    assert o['status'] == 'HISTORICAL_SHARE_BASIS_UNCONFIRMED'
    assert o['security_id'] is None and o['price_asof'] is None
    assert d['endpoint_diagnostic']['value'] == 1
    assert d['endpoint_diagnostic']['adopted'] is False
    observations, _ = held.held_observations(p, r, 'SYN:source', as_of='2026-02-03T00:00:00Z',
        valuation_date='2026-02-02', accounting_template='GENERAL')
    assert 'eps_diluted_cagr_3y' in observations


def test_reviewed_history_can_compute_without_evaluation_security_or_price():
    p, r = fixture(); _, _, f = execute(p, r); r['historical_share_basis'] = proof(f)
    o, _, _ = execute(p, r)
    assert o['value'] == 1 and o['status'] == 'VALID'
    assert o['security_id'] is None and o['price_asof'] is None
    row = dict(issuer_id=r['cik'], security_id=None, accounting_template='GENERAL',
               observations={'eps_diluted_cagr_3y': o})
    s = dict(as_of='2026-02-03T00:00:00Z', valuation_date='2026-02-02')
    assert kernel._validated_observation(row, 'eps_diluted_cagr_3y', s)[0] == 1
    # Historical evidence is not authority to join valuation-date prices.
    ep = deepcopy(o); ep.update(variant_id='ep_ttm_diluted', formula_version=kernel.CATALOG['ep_ttm_diluted']['formula_version'],
        price_asof=s['valuation_date'], fiscal_period={'kind':'TTM', 'end':'2025-12-31'})
    row['observations']['ep_ttm_diluted'] = ep
    assert kernel._validated_observation(row, 'ep_ttm_diluted', s)[0] is None


@pytest.mark.parametrize('mutation', ['issuer', 'class', 'future', 'period', 'hash', 'unreviewed'])
def test_history_proof_rejects_wrong_scope_period_time_or_payload(mutation):
    p, r = fixture(); _, _, f = execute(p, r); b = proof(f)
    if mutation == 'issuer': b['issuer_id'] = '0000000002'
    elif mutation == 'class': b['class_basis'] = None
    elif mutation == 'future': b['source_available_at'] = '2027-01-01T00:00:00Z'
    elif mutation == 'period': b['valid_from'] = '2025-01-01'
    elif mutation == 'hash': b['normalized_components_hash'] = '0'*64
    else: b['status'] = 'UNREVIEWED'
    r['historical_share_basis'] = b
    assert execute(p, r)[0]['value'] is None


@pytest.mark.parametrize('value', [0, -1])
def test_nonpositive_endpoint_never_becomes_cagr(value):
    p, r = fixture(); p['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val'] = value
    _, _, f = execute(p, r); r['historical_share_basis'] = proof(f)
    o, d, _ = execute(p, r)
    assert o['status'] == 'DOMAIN_INVALID' and o['value'] is None
    assert d['endpoint_diagnostic']['status'] == 'NONPOSITIVE_ENDPOINT'


@pytest.mark.parametrize('mutation', ['missing_middle', 'ytd', 'wrong_unit', 'future', 'latest_conflict'])
def test_annual_history_rejects_missing_ytd_units_future_and_newest_conflict(mutation):
    p, r = fixture(); node=p['facts']['us-gaap']['EarningsPerShareDiluted']; rows=node['units']['USD/shares']
    if mutation == 'missing_middle': rows.pop(1)
    elif mutation == 'ytd': rows[1].update(start='2023-07-01', form='10-Q')
    elif mutation == 'wrong_unit': node['units']['USD'] = node['units'].pop('USD/shares')
    elif mutation == 'future': rows[1]['filed'] = '2027-02-01'
    else:
        old=dict(rows[0], filed='2025-02-01', accn='SYN:old')
        rows += [old, dict(rows[0],val=2)]
        # An alternate concept must not hide the latest primary conflict.
        p['facts']['us-gaap']['EarningsPerShareBasicAndDiluted']=deepcopy(node)
        p['facts']['us-gaap']['EarningsPerShareBasicAndDiluted']['units']['USD/shares']=[old]
    o,d,f=execute(p,r)
    assert o['value'] is None
    assert len(f)<4
    if mutation=='latest_conflict': assert d['annual']['eps_diluted_fy3']['status']=='LATEST_FILING_CONFLICT'


def test_split_normalization_reuses_existing_direction_and_no_double_adjustment():
    p,r=fixture();t=p['facts']['us-gaap']
    eps=t['EarningsPerShareDiluted']['units']['USD/shares']
    shares=t['WeightedAverageNumberOfDilutedSharesOutstanding']['units']['shares']
    # Older FY basis is two pre-split shares for each normalized EPS unit.
    eps[0].update(val=2, filed='2023-02-01', accn='SYN:old')
    shares.append(dict(shares[0],val=5,filed='2023-02-01',accn='SYN:old'))
    t['StockholdersEquityNoteStockSplitConversionRatio1']={'units':{'pure':[dict(val=2,end='2024-06-01',filed='2024-07-01')]}}
    _,_,f=execute(p,r)
    assert f['eps_diluted_fy3']['value']==1
    assert f['eps_diluted_fy3']['source_detail']['normalization_factor']==2
    r['historical_share_basis']=proof(f)
    assert execute(p,r)[0]['value']==1
    # A later event cannot change an earlier acquired history.
    t['StockholdersEquityNoteStockSplitConversionRatio1']['units']['pure'][0]['filed']='2027-07-01'
    o,d,_=execute(p,r)
    assert o['value'] is None and d['annual']['eps_diluted_fy3']['status']=='SHARE_NORMALIZATION_UNCONFIRMED'


def test_eps_only_existing_cli_preserves_other_observations_and_denominator(tmp_path):
    import json, hashlib, zipfile, runpy
    from pathlib import Path
    p,r=fixture(); body=json.dumps(p).encode(); sha=hashlib.sha256(body).hexdigest()
    r['source_sha256']={'companyfacts':sha}; ref='facts#sha256='+sha
    archive=tmp_path/'source.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('facts',body)
    s=dict(as_of='2026-02-03T00:00:00Z',valuation_date='2026-02-02',members=['SYN:A'],
        snapshot_id='synthetic',input_version='old',rows=[dict(company_id='SYN:A',issuer_id=r['cik'],
            accounting_template='GENERAL',gate={'status':'UNKNOWN'},mapping={'unchanged':True},
            observations={'retained':{'provenance':[ref],'value':123}})])
    def spec(path): return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    plan=dict(schema_version='sector-qgv-held-repair/1',projection='EPS_HISTORY_ONLY',snapshot_hash=kernel.digest(s),
        archives={'x':{**spec(archive),'format':'ZIP'}},rows=[dict(company_id='SYN:A',record=r,
        archive_id='x',member='facts',sha256=sha,reference=ref)])
    a=tmp_path/'snapshot.json';a.write_text(json.dumps(s));b=tmp_path/'plan.json';b.write_text(json.dumps(plan))
    run=runpy.run_path(str(Path(__file__).resolve().parents[2]/'tools/sector_qgv.py'))['run']
    out=tmp_path/'out';report=run(dict(mode='held-input-repair',data_kind='SYNTHETIC',transform_only=True,
        request_id='SYN:eps',snapshot=spec(a),repair_plan=spec(b)),out,synthetic=True)
    result=json.loads((out/'snapshot.json').read_text())
    assert report['scoring_executed'] is False and result['members']==s['members']
    assert result['rows'][0]['observations']['retained']==s['rows'][0]['observations']['retained']
    assert not (out/'preview.json').exists()
    assert result['rows'][0]['observations']['eps_diluted_cagr_3y']['raw_components_available']


def test_verified_historical_observation_enters_333_pool_but_v_stays_blocked():
    from investment_system.research.dual_qgv import run_board
    from investment_system.research.qgv_333 import candidate_configs
    from test_qgv_333 import snapshots
    p,r=fixture();_,_,f=execute(p,r);r['historical_share_basis']=proof(f);o,_,_=execute(p,r)
    ev,ref=snapshots()
    for snapshot in (ev,ref):
        for row in snapshot['rows']:
            row['security_id']=None
            x=deepcopy(o);x['issuer_id']=row['issuer_id'];x['historical_share_basis']['issuer_id']=row['issuer_id']
            row['observations']['eps_diluted_cagr_3y']=x
    b=run_board(candidate_configs()['U2-333'],ev,ref,request_id='SYN:history-only')
    assert b['rows'][0]['factors']['eps_diluted_cagr_3y']['score'] is not None
    assert b['rows'][0]['axes']['G'] is not None and b['rows'][0]['axes']['V'] is None
