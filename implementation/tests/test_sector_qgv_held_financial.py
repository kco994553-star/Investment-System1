"""Synthetic source facts, independently calculated expectations; no real values."""
from copy import deepcopy
import pytest
from investment_system.research.sector_qgv_held import held_observations, _components


def source():
    tax = {}
    for tag, value in [('NetIncomeLoss', 12), ('NetIncomeLossAvailableToCommonStockholdersBasic', 10),
                       ('NetCashProvidedByUsedInOperatingActivities', 15), ('Revenues', 100)]:
        tax[tag] = {'units': {'USD': [dict(val=value + year-2022, start=f'{year}-01-01',
            end=f'{year}-12-31', filed=f'{year+1}-02-01', form='10-K', accn=f'syn-{year}')
            for year in range(2022, 2026)]}}
    for tag, value, unit in [('Assets', 200, 'USD'), ('CommonStockholdersEquity', 100, 'USD'),
                              ('CommonStockSharesOutstanding', 10, 'shares')]:
        tax[tag] = {'units': {unit: [dict(val=value, end=f'{year}-12-31',
            filed=f'{year+1}-02-01', form='10-K', accn=f'syn-{year}') for year in range(2021, 2026)]}}
    record = dict(cik='0000000001', acquired_at='2026-02-02T12:00:00Z',
                  fiscal_year_end='2025-12-31', profile='FINANCIAL', sic='6021', state='LIVE')
    return {'cik': 1, 'facts': {'us-gaap': tax}}, record


def run(payload, record, template):
    return held_observations(payload, record, 'synthetic:companyfacts',
        as_of='2026-02-03T00:00:00Z', valuation_date='2026-02-02', accounting_template=template)


def test_financial_default_common_inputs_and_context():
    p,r=source();o,d=run(p,r,'BANK')
    assert o['roe_common_ttm']['value'] == pytest.approx(13/100)
    assert o['common_equity_assets']['value'] == pytest.approx(100/200)
    assert o['common_bps_cagr_3y']['value'] is None  # no class/action continuity proof
    assert 'COMMON_SHARE_BASIS_UNCONFIRMED' in d['common_bps_cagr_3y']
    fields,_=_components(p,r,'synthetic:companyfacts')
    assert fields['common_equity_end']['equity_basis']=='COMMON_EXCLUDING_PREFERRED_NCI'
    assert fields['net_income_common']['unit']=='USD'
    assert fields['common_equity_end']['period_end']=='2025-12-31'


def test_parent_equity_requires_explicit_same_filing_zero_preferred():
    p,r=source();t=p['facts']['us-gaap'];t['StockholdersEquity']=t.pop('CommonStockholdersEquity')
    assert run(p,r,'BANK')[0]['common_equity_assets']['value'] is None
    t['PreferredStockSharesOutstanding']=deepcopy(t['CommonStockSharesOutstanding'])
    for x in t['PreferredStockSharesOutstanding']['units']['shares']:x['val']=0
    assert run(p,r,'BANK')[0]['common_equity_assets']['value']==.5
    t['PreferredStockSharesOutstanding']['units']['shares'][-1]['accn']='different-filing'
    assert run(p,r,'BANK')[0]['common_equity_assets']['value'] is None


def test_common_income_does_not_alias_consolidated_income():
    p,r=source();del p['facts']['us-gaap']['NetIncomeLossAvailableToCommonStockholdersBasic']
    o,d=run(p,r,'INSURANCE')
    assert o['roe_common_ttm']['value'] is None
    assert d['net_income_common']['cause']=='VALUE_ABSENT_IN_EXAMINED_SOURCE'


def test_reit_improvement_connected_without_financial_substitution():
    p,r=source();r['profile']='GENERAL';o,_=run(p,r,'EQUITY_REIT')
    assert o['cfo_assets_improvement_3y']['value']==pytest.approx(18/200-15/200)
    assert o['roa_ttm']['status']=='NOT_APPLICABLE'


def test_unknown_accounting_is_not_general_and_does_not_erase_raw():
    p,r=source();o,d=run(p,r,None)
    assert d['accounting_template']=='UNCONFIRMED_RAW_ONLY'
    assert o['roa_ttm']['value']==pytest.approx(15/200)
    assert o['roe_common_ttm']['value']==pytest.approx(13/100)


@pytest.mark.parametrize('change',['future','unit','conflict'])
def test_invalid_common_equity_never_becomes_zero(change):
    p,r=source();t=p['facts']['us-gaap']['CommonStockholdersEquity'];x=t['units']['USD'][-1]
    if change=='future':x['filed']='2027-01-01'
    elif change=='unit':t['units']['EUR']=t['units'].pop('USD')
    else:t['units']['USD'].append(dict(x,val=101))
    o,d=run(p,r,'BROKER');assert o['common_equity_assets']['value'] is None
    assert d['common_equity_end']['cause']=='VALIDATION_FAILED'


def test_conflicting_common_equity_cannot_fall_back_to_parent():
    p,r=source();t=p['facts']['us-gaap']
    t['StockholdersEquity']=deepcopy(t['CommonStockholdersEquity'])
    t['PreferredStockSharesOutstanding']=deepcopy(t['CommonStockSharesOutstanding'])
    for x in t['PreferredStockSharesOutstanding']['units']['shares']:x['val']=0
    x=t['CommonStockholdersEquity']['units']['USD'][-1]
    t['CommonStockholdersEquity']['units']['USD'].append(dict(x,val=101))
    assert run(p,r,'BANK')[0]['common_equity_assets']['value'] is None


def test_newer_conflict_does_not_resurrect_older_common_equity():
    p,r=source();rows=p['facts']['us-gaap']['CommonStockholdersEquity']['units']['USD']
    old=deepcopy(rows[-1]);old['filed']='2026-01-30';old['accn']='older'
    rows.append(old);rows.append(dict(rows[-2],val=101))
    assert run(p,r,'BANK')[0]['common_equity_assets']['value'] is None


def test_repair_pins_source_and_preserves_non_qg_context(tmp_path):
    import json, hashlib, zipfile
    from investment_system.research.sector_qgv import digest
    from investment_system.research.sector_qgv_held_repair import repair
    p,r=source();body=json.dumps(p).encode();sha=hashlib.sha256(body).hexdigest()
    r['source_sha256']={'companyfacts':sha};ref='facts#sha256='+sha
    archive=tmp_path/'source.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('facts',body)
    s=dict(as_of='2026-02-03T00:00:00Z',valuation_date='2026-02-02',members=['CODE:A'],
        snapshot_id='synthetic',input_version='old',rows=[dict(company_id='CODE:A',issuer_id=r['cik'],
            accounting_template='BANK',sector_id='FINANCIALS',gate={'status':'UNKNOWN'},
            mapping={'unchanged':True},input_diagnostics={},observations={'retained':{'provenance':[ref]}})])
    plan={'schema_version':'sector-qgv-held-repair/1','snapshot_hash':digest(s),
        'archives':{'x':{'path':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'format':'ZIP'}},
        'rows':[{'company_id':'CODE:A','record':r,'archive_id':'x','member':'facts','sha256':sha,'reference':ref}]}
    saved=deepcopy(s);out,a=repair(s,plan)
    assert s==saved and out['members']==s['members'] and out['rows'][0]['mapping']==s['rows'][0]['mapping']
    assert out['rows'][0]['gate']==s['rows'][0]['gate']
    assert out['rows'][0]['observations']['roe_common_ttm']['value']==pytest.approx(.13)
    assert a['treatment']=='INPUT_CONNECTION_REPAIR'
    for kind in ('snapshot','member','issuer','duplicate'):
        q=deepcopy(plan)
        if kind=='snapshot':q['snapshot_hash']='0'*64
        elif kind=='member':q['rows'][0]['sha256']='0'*64
        elif kind=='issuer':q['rows'][0]['record']['cik']='wrong'
        else:q['rows']*=2
        with pytest.raises(ValueError):repair(s,q)


def test_historical_component_window_does_not_change_financial_v_age_rule():
    from datetime import date
    from investment_system.research.financial_v import _balance_observations
    p,_=source();args=(p,('CommonStockholdersEquity',),'USD',date(2026,2,2))
    usual=_balance_observations(*args)[0]
    history=_balance_observations(*args,history_days=1600)[0]
    assert all((date(2026,2,2)-k[0]).days<=550 for k in usual)
    assert set(usual)<set(history)


def test_unknown_accounting_raw_only_never_bypasses_v_scope():
    from investment_system.research.sector_qgv import calculate_factor
    p,r=source();fields,_=_components(p,r,'synthetic:source')
    ctx=dict(as_of='2026-02-03T00:00:00Z',valuation_date='2026-02-02',issuer_id=r['cik'],
        accounting_template=None,raw_only_accounting_unconfirmed=True)
    assert calculate_factor('common_bp',fields,ctx)['status']=='NOT_APPLICABLE'
