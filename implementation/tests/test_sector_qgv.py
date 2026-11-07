import copy
import math
import pytest
from investment_system.research.sector_qgv import (
    default_config, preset, validate_config, effective_weights, calculate_factor,
    preview_qgv, save_user_config, list_factors, config_hash, comparison_configs,
)
from investment_system.research.sector_qgv_registry import CATALOG, SECTORS


def context():
    return {'as_of':'2026-11-02T23:59:59Z','valuation_date':'2026-11-02',
            'accounting_template':'GENERAL','issuer_id':'issuer-1','security_id':'security-1'}


def component(value, *, period='TTM', unit='USD/share', end='2026-09-30', **kw):
    return dict(value=value, period_kind=period, period_end=end, unit=unit, currency='USD',
                period_start='2025-10-01' if period=='TTM' else None,
                issuer_id='issuer-1', security_id='security-1', share_basis='ordinary-adjusted',
                corporate_action_basis='split-through-2026-11-02', scope='CONSOLIDATED',
                available_at='2026-10-25T12:00:00Z', retrieved_at='2026-10-26T12:00:00Z',
                provenance=['synthetic:fixture'], **kw)


def prices(eps=5, price=100):
    return {'eps_ttm_diluted':component(eps),
            'price':component(price,period='PRICE',end='2026-11-02')}


def snapshot(n=20):
    ctx=context(); rows=[]
    for i in range(n):
        obs={}
        for v in CATALOG:
            obs[v]={'value':float(i+1),'status':'VALID','variant_id':v,'formula_version':'1',
                    'unit':CATALOG[v]['unit'],'fiscal_period':{'kind':CATALOG[v]['period'],'end':'2026-09-30'},
                    'price_asof':'2026-11-02' if CATALOG[v]['axis']=='V' else None,
                    'issuer_id':f'issuer-{i}','security_id':f'security-{i}',
                    'source_available_at':'2026-10-25T12:00:00Z','retrieved_at':'2026-10-26T12:00:00Z',
                    'currency':'USD','scope':'CONSOLIDATED','corporate_action_basis':'verified-fixture',
                    'provenance':['synthetic:fixture'],'validation_basis':'VERIFIED_DEFINITION',
                    'raw_components_available':True}
        obs['ebitda_ev']['value']=float(n-i)
        obs['cfo_mcap']['value']=float((i*7)%n+1)
        rows.append({'company_id':f'company-{i:03}','issuer_id':f'issuer-{i}',
                     'security_id':f'security-{i}','sector_id':'INFORMATION_TECHNOLOGY',
                     'accounting_template':'GENERAL','mapping':{'version':'book-sector-map/1',
                     'valid_from':'2026-01-01','valid_to':None,'evidence_refs':['synthetic:map']},
                     'observations':obs,'gate':{'q_industry_percentile':50,
                     'calc_version':'qgv2-calc/2026-10-23.1','as_of':'2026-11-02',
                     'provenance':['synthetic:official-gate']}})
    return dict(schema_version='sector-qgv-input/1',snapshot_id='synthetic-snapshot/1',
                universe_id='synthetic-20',universe_version='1',mapping_version='book-sector-map/1',
                input_version='synthetic-input/1',as_of=ctx['as_of'],valuation_date=ctx['valuation_date'],
                members=[r['company_id'] for r in rows],rows=rows)


def test_exact_defaults_and_hierarchy():
    c=default_config();validate_config(c)
    assert preset(c,'INFORMATION_TECHNOLOGY','GENERAL')['axis_weights']=={'Q':3000,'G':2500,'V':4500}
    p=preset(c,'FINANCIALS','BANK');w=effective_weights(p)
    assert w['roa_ttm']==pytest.approx(.4*.7*.5)
    assert w['roe_common_ttm']==pytest.approx(.4*.7*.5)
    assert w['common_equity_assets']==pytest.approx(.4*.3)
    for s in SECTORS:
        assert sum(effective_weights(preset(c,s,'GENERAL')).values())==pytest.approx(1)


@pytest.mark.parametrize('eps,expected,status',[(5,.05,'VALID'),(-5,-.05,'VALID_NEGATIVE'),(0,0,'VALID_ZERO')])
def test_eps_ratio_and_display(eps,expected,status):
    r=calculate_factor('ep_ttm_diluted',prices(eps),context())
    assert r['value']==expected and r['status']==status
    assert r['display_multiple']==(20 if eps==5 else None)


def test_peg_and_variant_separation():
    p=prices();p['eps_growth_3y']=component(.10,period='FY_3Y',unit='decimal')
    assert calculate_factor('peg_historical',p,context())['value']==2
    p['eps_growth_3y']['value']=0
    assert calculate_factor('peg_historical',p,context())['status']=='DOMAIN_INVALID'
    assert CATALOG['ep_ttm_diluted']['overlap_group'] != CATALOG['net_income_mcap']['overlap_group']
    assert CATALOG['ep_ttm_diluted']['overlap_group'] != CATALOG['ep_fy_diluted']['overlap_group']
    assert calculate_factor('ep_ttm_diluted',{'price':prices()['price']},context())['status']=='MISSING_INPUT'


def test_split_adr_period_and_pit():
    a=prices();b=prices(2.5,50)
    assert calculate_factor('ep_ttm_diluted',a,context())['value']==calculate_factor('ep_ttm_diluted',b,context())['value']
    a['price']['share_basis']='ADR-2:1'
    assert calculate_factor('ep_ttm_diluted',a,context())['status']=='SCOPE_MISMATCH'
    a=prices();a['eps_ttm_diluted']['period_kind']='FY'
    assert calculate_factor('ep_ttm_diluted',a,context())['status']=='PERIOD_MISMATCH'
    a=prices();a['eps_ttm_diluted']['available_at']='2026-11-03T00:00:00Z'
    assert calculate_factor('ep_ttm_diluted',a,context())['status']=='NOT_YET_AVAILABLE'


def test_minimum_sample_and_missing_are_separate():
    out=preview_qgv(default_config(),snapshot(19),'r1')
    assert out['coverage']['total']['valid']==0
    assert out['result_rows'][0]['factors']['ep_ttm_diluted']['score_status']=='PEER_SAMPLE_SMALL'
    s=snapshot();s['rows'][0]['observations'].pop('ep_ttm_diluted')
    out=preview_qgv(default_config(),s,'r2')
    assert out['result_rows'][0]['factors']['ep_ttm_diluted']['raw_status']=='MISSING_INPUT'
    assert out['result_rows'][1]['factors']['ep_ttm_diluted']['score_status']=='PEER_SAMPLE_SMALL'


def test_selection_gate_and_strict_missing():
    c=default_config();s=snapshot();s['rows'][0]['gate']=None
    p=copy.deepcopy(preset(c,'INFORMATION_TECHNOLOGY','GENERAL'))
    p['axis_weights']={'Q':0,'G':5000,'V':5000}
    c['scoped_overrides']={'INFORMATION_TECHNOLOGY|GENERAL':p}
    out=preview_qgv(c,s,'r');r=out['result_rows'][0]
    assert r['pre_gate_total'] is not None
    assert r['total'] is None and r['gate_status']=='UNKNOWN' and r['rank'] is None
    s['rows'][0]['gate']={'q_industry_percentile':20,'as_of':'2026-11-02',
                         'calc_version':'qgv2-calc/2026-10-23.1','provenance':['synthetic']}
    r=preview_qgv(c,s,'r')['result_rows'][0]
    assert r['gate_status']=='VALUE_EXCLUDED' and r['post_gate_axis_weights']=={'Q':0.0,'G':1.0,'V':0.0}
    s['rows'][0]['observations'].pop('ep_ttm_diluted')
    assert preview_qgv(c,s,'r')['result_rows'][0]['total'] is None


def test_config_duplicate_alias_scope_and_invalid_weight():
    c=default_config();p=copy.deepcopy(preset(c,'FINANCIALS','BANK'))
    p['axes']['V']['earnings']['factors']={'ep_ttm_diluted':5000,'PER_TTM_DILUTED':5000}
    c['scoped_overrides']={'FINANCIALS|BANK':p}
    with pytest.raises(ValueError,match='DUPLICATE'):validate_config(c)
    p=copy.deepcopy(preset(default_config(),'FINANCIALS','BANK'));p['axis_weights']={'Q':5000,'G':0,'V':5000}
    c['scoped_overrides']={'FINANCIALS|BANK':p};validate_config(c)
    assert preset(c,'FINANCIALS','INSURANCE')['axis_weights']=={'Q':4000,'G':1500,'V':4500}
    p['axis_weights']['G']=math.nan
    with pytest.raises(ValueError):validate_config(c)


def test_determinism_lynch_versions_saved_preview():
    c=default_config();s=snapshot();a=preview_qgv(c,s,'r')
    t=copy.deepcopy(s);t['rows'].reverse()
    for r in t['rows']:r['lynch_tags']=['turnaround']
    b=preview_qgv(c,t,'r')
    assert a==b
    assert a['coverage']['total']=={'valid':20,'denominator':20}
    saved=save_user_config(c,a,request_id='r',expected_preview_id=a['preview_id'])
    assert saved['canonical_config_hash']==a['config_hash']
    with pytest.raises(ValueError):save_user_config(c,a,request_id='new',expected_preview_id=a['preview_id'])
    c['display_preferences']={'sort':'name'}
    assert config_hash(c)==a['config_hash']
    t['universe_version']='2'
    assert preview_qgv(c,t,'r')['preview_id']!=a['preview_id']


def test_whole_original_population_and_no_issuer_auto_merge():
    s=snapshot();s['members'].append('unavailable-company')
    out=preview_qgv(default_config(),s,'r')
    assert out['coverage']['total']['denominator']==21
    assert out['result_rows'][-1]['status']=='MAPPING_UNRESOLVED'
    s['rows'][1]['issuer_id']=s['rows'][0]['issuer_id']
    # A source must resolve the issuer's scoring representative; never double count issuer peers.
    out=preview_qgv(default_config(),s,'r')
    assert out['coverage']['total']['valid']==0


def test_comparisons_preregistered_and_catalog():
    assert len(comparison_configs())==3
    cat=list_factors(default_config(),'INFORMATION_TECHNOLOGY','GENERAL')
    assert any(f['variant_id']=='ep_ttm_diluted' and f['is_default'] for f in cat)
    assert all(f['validation_state']=='initial' for f in cat)


def test_all_design_ids_registered_and_no_fake_operating_aliases():
    ids={v['factor_id'] for v in CATALOG.values()}
    assert {f'Q{i:02}' for i in range(1,15)} <= ids
    assert {f'G{i:02}' for i in range(1,15)} <= ids
    assert {f'V{i:02}' for i in range(1,16)} <= ids
    assert CATALOG['roa_improvement_3y']['formula']=='difference'
    assert CATALOG['gross_profit_assets_ttm']['formula']=='ratio_average'
    assert CATALOG['roic_explicit']['calculator_status']=='PENDING_DEFINITION'
    for sector in SECTORS:
        for template in ('GENERAL','BANK','INSURANCE','BROKER','MORTGAGE_REIT','ASSET_MANAGER','EQUITY_REIT'):
            p=preset(default_config(),sector,template)
            assert sum(effective_weights(p).values())==pytest.approx(1)


def test_effective_role_budget_and_hand_total():
    from investment_system.research.sector_qgv import aggregate
    p=preset(default_config(),'INFORMATION_TECHNOLOGY','GENERAL')
    p['axis_weights']={'Q':3000,'G':2000,'V':5000}
    p['axes']['Q']['profitability']['factors']={'roa_ttm':5000,'operating_margin_ttm':5000}
    w=effective_weights(p)
    assert w['roa_ttm']+w['operating_margin_ttm']==pytest.approx(.12)
    scores={v:{'score':{'Q':80,'G':60,'V':40}[CATALOG[v]['axis']]} for v in w}
    r=aggregate(p,scores,None,'2026-11-02')
    assert r['pre_gate_total']==56 and r['total'] is None


def test_joint_coverage_not_single_factor_coverage():
    s=snapshot(100)
    for i in range(10):s['rows'][i]['observations'].pop('revenue_cagr_3y')
    for i in range(10,20):s['rows'][i]['observations'].pop('ep_ttm_diluted')
    r=preview_qgv(default_config(),s,'joint')
    assert r['coverage']['factors']['revenue_cagr_3y']['score_valid']==90
    assert r['coverage']['factors']['ep_ttm_diluted']['score_valid']==90
    assert r['coverage']['total']=={'valid':80,'denominator':100}


def test_ttm_start_zero_dividend_ev_and_growth_history():
    p=prices();p['eps_ttm_diluted'].pop('period_start')
    assert calculate_factor('ep_ttm_diluted',p,context())['status']=='PERIOD_MISMATCH'
    p=prices();p['common_dps_ttm']=p.pop('eps_ttm_diluted');p['common_dps_ttm']['value']=0
    assert calculate_factor('dividend_yield_ttm',p,context())['status']=='VALID_ZERO'
    del p['common_dps_ttm']
    assert calculate_factor('dividend_yield_ttm',p,context())['status']=='MISSING_INPUT'
    p={'revenue':component(100,unit='USD'),
       'enterprise_value':component(0,period='PRICE',unit='USD',end='2026-11-02',capital_scope_evidence=['synthetic:all-classes'],definition_id='EQUITY_DEBT_PREFERRED_NCI_LESS_CASH')}
    assert calculate_factor('sales_ev',p,context())['status']=='DOMAIN_INVALID'
    p={}
    for k,v in enumerate([133.1,121,110,100]):
        p['revenue_fy'+(str(k) if k else '')]=component(v,period='FY' if k==0 else f'FY_MINUS_{k}',unit='USD',end=f'{2025-k}-12-31')
    assert calculate_factor('revenue_cagr_3y',p,context())['value']==pytest.approx(.1)
    del p['revenue_fy1']
    assert calculate_factor('revenue_cagr_3y',p,context())['status']=='MISSING_INPUT'


def test_input_versions_status_and_duplicates():
    s=snapshot();s['rows'][0]['observations']['ep_ttm_diluted']['formula_version']='other'
    out=preview_qgv(default_config(),s,'r')
    assert out['result_rows'][0]['factors']['ep_ttm_diluted']['raw_status']=='OBSERVATION_VERSION_MISMATCH'
    s=snapshot();s['rows'][0]['observations']['ep_ttm_diluted']['status']='STALE'
    assert preview_qgv(default_config(),s,'r')['result_rows'][0]['total'] is None
    s=snapshot();s['rows'][0]['observations']['ep_ttm_diluted']['value']=float('nan')
    with pytest.raises(ValueError):preview_qgv(default_config(),s,'r')
    s=snapshot();s['rows'].append(s['rows'][0])
    with pytest.raises(ValueError,match='DUPLICATE'):preview_qgv(default_config(),s,'r')


def test_cli_hashes_and_saved_config(tmp_path):
    import importlib.util,json,hashlib
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('sector_cli',Path(__file__).resolve().parents[1]/'tools/sector_qgv.py')
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    src=tmp_path/'input.json';src.write_text(json.dumps(snapshot()))
    job={'data_kind':'SYNTHETIC','snapshot':{'path':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()},
         'request_id':'cli','comparisons':True}
    summary=cli.run(job,tmp_path/'out',True)
    assert summary['total']['valid']==20
    saved=json.loads((tmp_path/'out/saved-config.json').read_text())
    preview=json.loads((tmp_path/'out/preview.json').read_text())
    assert saved['canonical_config_hash']==preview['config_hash']
    assert len(json.loads((tmp_path/'out/comparisons.json').read_text()))==3
    with pytest.raises(ValueError,match='OUTPUT_ALREADY_EXISTS'):cli.run(job,tmp_path/'out',True)
    job['snapshot']['sha256']='0'*64
    with pytest.raises(ValueError,match='HASH'):cli.run(job,tmp_path/'new',True)


def test_inputs_acquired_but_invalid_not_lost_from_coverage():
    p=prices();p['price']['currency']='EUR';p['price']['unit']='EUR/share'
    o=calculate_factor('ep_ttm_diluted',p,context())
    assert o['status']=='CURRENCY_MISMATCH' and o['raw_components_available'] is True
    p=prices();p['eps_ttm_diluted']['available_at']='bad'
    assert calculate_factor('ep_ttm_diluted',p,context())['status']=='INPUT_INVALID'


def test_held_adapter_reuses_common_facts_without_eps_arithmetic():
    from investment_system.research.sector_qgv_held import _components
    facts={}
    for tag,mult in [('Revenues',100),('NetIncomeLoss',5),('NetCashProvidedByUsedInOperatingActivities',7),('OperatingIncomeLoss',8)]:
        facts[tag]={'units':{'USD':[{'val':mult*(year-2020),'start':f'{year}-01-01','end':f'{year}-12-31',
                                   'filed':f'{year+1}-02-15','form':'10-K','accn':f'{year}-fixture'} for year in range(2021,2026)]}}
    facts['Assets']={'units':{'USD':[{'val':1000,'end':f'{year}-12-31','filed':f'{year+1}-02-15','form':'10-K','accn':f'{year}-fixture'} for year in range(2020,2026)]}}
    record={'acquired_at':'2026-02-16T12:00:00Z','fiscal_year_end':'2025-12-31','sic':'3571','profile':'GENERAL','cik':'issuer-1'}
    fields,reasons=_components({'facts':{'us-gaap':facts}},record,'synthetic:source')
    assert 'eps_ttm_diluted' not in fields
    assert 'VERIFIED_TTM' in reasons['eps_ttm_diluted']
    ctx=context();ctx['as_of']='2026-02-17T00:00:00Z';ctx['valuation_date']='2026-02-16'
    assert calculate_factor('roa_improvement_3y',fields,ctx)['value']==pytest.approx(.025-.010)
    assert calculate_factor('revenue_cagr_3y',fields,ctx)['value']==pytest.approx((500/200)**(1/3)-1)
    # Later reported period cannot quietly fall back to the annual observation.
    facts['Revenues']['units']['USD'].append({'val':300,'start':'2026-01-01','end':'2026-06-30',
        'filed':'2026-08-01','form':'10-Q','accn':'2026-q'})
    record['acquired_at']='2026-08-02T12:00:00Z'
    fields,reasons=_components({'facts':{'us-gaap':facts}},record,'synthetic:source')
    assert 'revenue' not in fields and reasons['revenue']=='LATEST_TTM_INCOMPLETE_NO_ANNUAL_FALLBACK'


def test_future_valuation_and_post_valuation_forecast_rejected():
    s=snapshot();s['as_of']='2026-10-30T23:59:59Z'
    with pytest.raises(ValueError,match='VALUATION_AFTER_AS_OF'):preview_qgv(default_config(),s,'future')
    c=default_config();p=preset(c,'INFORMATION_TECHNOLOGY','GENERAL')
    p['axes']['V']['earnings']['factors']={'ep_fy1':10000};c['scoped_overrides']={'INFORMATION_TECHNOLOGY|GENERAL':p}
    s=snapshot();s['as_of']='2026-11-06T12:00:00Z'
    for row in s['rows']:
        row['observations']['ep_fy1']['source_available_at']='2026-11-05T12:00:00Z'
        row['observations']['ep_fy1']['retrieved_at']='2026-11-05T12:00:00Z'
    out=preview_qgv(c,s,'late-consensus')
    assert out['coverage']['total']['valid']==0
    assert out['result_rows'][0]['factors']['ep_fy1']['raw_status']=='NOT_YET_AVAILABLE'


def test_composite_yield_requires_same_security_basis_and_date():
    values={'dividend_yield':component(.02,unit='decimal',evaluation_date='2026-11-02'),
            'net_share_reduction':component(.03,unit='decimal',period='ONE_YEAR',evaluation_date='2026-11-02')}
    assert calculate_factor('shareholder_yield',values,context())['value']==.05
    values['dividend_yield']['security_id']='other-security'
    assert calculate_factor('shareholder_yield',values,context())['status']=='SCOPE_MISMATCH'
    values['dividend_yield']['security_id']='security-1'
    values['net_share_reduction']['corporate_action_basis']='different-basis'
    assert calculate_factor('shareholder_yield',values,context())['status']=='SCOPE_MISMATCH'
    values['net_share_reduction']['corporate_action_basis']='split-through-2026-11-02'
    values['net_share_reduction']['evaluation_date']='2026-11-01'
    assert calculate_factor('shareholder_yield',values,context())['status']=='PERIOD_MISMATCH'


def test_held_source_stale_and_cross_issuer_not_overwritten(tmp_path):
    import io,json,tarfile,hashlib
    from investment_system.research.sector_qgv_held import _components,build_held_snapshot
    facts={'facts':{'us-gaap':{tag:{'units':{'USD':[{'val':value,'start':'2025-01-01','end':'2025-12-31','filed':'2026-02-15','form':'10-K','accn':'fixture'}]}} for tag,value in [('Revenues',100),('OperatingIncomeLoss',10)]}},'cik':2}
    record={'acquired_at':'2026-02-16T12:00:00Z','fiscal_year_end':'2025-12-31','sic':'3571','profile':'GENERAL','cik':'0000000001','state':'STALE','reason_codes':['STALE_INPUT']}
    fields,_=_components(facts,record,'synthetic:source')
    ctx=context();ctx['issuer_id']='0000000001'
    assert calculate_factor('operating_margin_ttm',fields,ctx)['status']=='STALE'
    body=json.dumps(facts).encode();h=hashlib.sha256(body).hexdigest();tag='synthetic-release'
    manifest={'companies':[{'cik':'0000000002','sha256':{'companyfacts.json':h}}]}
    path=tmp_path/'source.tar.gz'
    with tarfile.open(path,'w:gz') as archive:
        for name,content in [(tag+'/manifest.json',json.dumps(manifest).encode()),(tag+'/0000000002/companyfacts.json',body)]:
            entry=tarfile.TarInfo(name);entry.size=len(content);archive.addfile(entry,io.BytesIO(content))
    record['source_sha256']={'companyfacts':h};record['calc_version']='qgv2-calc/2026-10-23.1'
    sec={'as_of':'2026-11-02T12:00:00Z','registry_sha256':'synthetic','records':{'SYNTHETIC:A':record},'calc_version':'qgv2-calc/2026-10-23.1'}
    with pytest.raises(ValueError,match='RECORD_ISSUER_MISMATCH'):
        build_held_snapshot(sec,[{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'release':tag}],snapshot_hash='synthetic')
    record.update(cik='0000000002',state='NOT_AVAILABLE',calc_version=None)
    held,audit=build_held_snapshot(sec,[{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'release':tag}],snapshot_hash='synthetic')
    assert held['rows'][0]['observations']=={}
    assert held['rows'][0]['input_diagnostics']['source']=='SOURCE_NOT_AVAILABLE'
    assert audit['source_hash_connected']==1


def test_preregistered_changes_produce_separate_effects_and_public_private_equal():
    from investment_system.research.sector_qgv import compare_previews
    s=snapshot();c=default_config();before=preview_qgv(c,s,'base')
    for cid,changed in comparison_configs().items():
        after=preview_qgv(changed,s,cid)
        assert any(r['delta']!=0 for r in compare_previews(before,after,cid)['rows'])
    c['owner_scope']='PRIVATE';private=preview_qgv(c,s,'same')
    c['owner_scope']='PUBLIC';public=preview_qgv(c,s,'same')
    assert public['result_rows']==private['result_rows']
    assert public['coverage']==private['coverage']


def test_ties_and_zero_role_do_not_change_active_budget():
    s=snapshot()
    for row in s['rows']:
        for obs in row['observations'].values():obs['value']=1
    out=preview_qgv(default_config(),s,'ties')
    assert all(r['total']==50 for r in out['result_rows'])
    assert [r['rank'] for r in out['result_rows']]==list(range(1,21))
    c=default_config();p=preset(c,'INFORMATION_TECHNOLOGY','GENERAL')
    p['axes']['Q']['profitability']['weight']=0
    p['axes']['Q']['accounting_quality']['weight']=5000
    p['axes']['Q']['financial_capacity']['weight']=5000
    c['scoped_overrides']={'INFORMATION_TECHNOLOGY|GENERAL':p}
    for row in s['rows']:row['observations'].pop('operating_margin_ttm')
    out=preview_qgv(c,s,'zero-role')
    assert out['coverage']['total']['valid']==20
    assert out['coverage']['factors']['operating_margin_ttm']['selected_coverage']['denominator']==0


def test_public_fixture_is_the_current_contract():
    import json,hashlib
    from pathlib import Path
    p=Path(__file__).resolve().parents[1]/'docs/research/sector_qgv'
    data=json.loads((p/'synthetic-input.json').read_text())
    expected=json.loads((p/'synthetic-preview.json').read_text())
    assert preview_qgv(default_config(),data,'synthetic-normal')==expected
    assert hashlib.sha256((p/'synthetic-input.json').read_bytes()).hexdigest()==json.loads((p/'synthetic-job.json').read_text())['snapshot']['sha256']
    assert all('synthetic' in ref for row in data['rows'] for obs in row['observations'].values() for ref in obs['provenance'])
