from datetime import datetime,timedelta,timezone
import importlib
import json
from pathlib import Path
import sys
import pytest

NOW=datetime(2026,10,10,tzinfo=timezone.utc)
TOOLS=Path(__file__).parents[1]/'tools'
sys.path.insert(0,str(TOOLS))

def api():return importlib.import_module('investment_system.product.public_engine_screens')
def manifest():return {'schema_version':1,'sec':[],'macro':[],'thirteen_f':[]}
def build(tmp_path,m=None):return api().generate_screen_bundle(manifest=m or manifest(),input_root=tmp_path,as_of=NOW,stale_after=timedelta(days=2))

def sec(tmp_path,synthetic=False,acquired='2026-10-10T00:00:00Z'):
    cik='0001045810';rows=[];forms=[]
    for year,value in zip(range(2022,2026),(100,115,132.25,152.0875)):
        accn=f'{cik}-{year+1-2000:02d}-000001';filed=f'{year+1}-02-01'
        rows.append({'start':f'{year}-01-01','end':f'{year}-12-31','val':value,'accn':accn,'form':'10-K','filed':filed,'fp':'FY','fy':year})
        forms.append((accn,filed,f'{year}-12-31'))
    facts={'cik':1045810,'facts':{'us-gaap':{'Revenues':{'units':{'USD':rows}},'StockPrice':{'units':{'USD':[{'val':99999}]}}}},'private_value':'TEST_ONLY_CANARY'}
    subs={'cik':1045810,'filings':{'recent':{'form':['10-K']*4,'accessionNumber':[r[0] for r in forms],'filingDate':[r[1] for r in forms],'reportDate':[r[2] for r in forms],'acceptanceDateTime':[r[1]+'T12:00:00Z' for r in forms]}}}
    (tmp_path/'facts.json').write_text(json.dumps(facts));(tmp_path/'submissions.json').write_text(json.dumps(subs))
    m=manifest();m['sec']=[{'company_id':'nvda','companyfacts':'facts.json','submissions':'submissions.json','acquired_at':acquired,'synthetic':synthetic}];return m


def test_empty_input_produces_five_versioned_unavailable_files(tmp_path):
    outputs=build(tmp_path)
    assert len(outputs)==5
    for name,payload in outputs.items():
        assert payload['schema_version']==1 and payload['state']=='NOT_AVAILABLE' and payload['as_of']==NOW.isoformat()
        assert payload['sources']==[]
        api().require_public_screen(name,payload)


def test_sec_reuses_qg_mapper_without_price_and_estimate_is_not_confirmed(tmp_path):
    outputs=build(tmp_path,sec(tmp_path))
    q=outputs['sec-qg-factors.json'];row=q['data']['companies']['nvda']
    assert row['factors']['revenue_growth']['score'] is not None
    assert q['state']=='LIVE' and row['state']=='LIVE'
    windows=outputs['sec-filing-windows.json']['data']['companies']['nvda']
    assert windows['confirmed_earnings_date'] is None and windows['role']=='ESTIMATED_PATTERN_NOT_CONFIRMED'
    text=json.dumps(outputs)
    def numeric_values(value):
        if isinstance(value,dict):
            for child in value.values():yield from numeric_values(child)
        elif isinstance(value,list):
            for child in value:yield from numeric_values(child)
        elif type(value) in (int,float):yield value
    # A legitimate 0.499999... ramp contains the digit substring; reject the
    # actual price sentinel value, not unrelated floating-point spellings.
    assert 99999 not in set(numeric_values(outputs))
    assert 'TEST_ONLY_CANARY' not in text and 'StockPrice' not in text
    assert len(q['sources'])==2


def test_stale_is_acquisition_ttl_not_filing_age_and_missing_remains_null(tmp_path):
    out=build(tmp_path,sec(tmp_path,acquired='2026-10-01T00:00:00Z'))
    assert out['sec-qg-factors.json']['state']=='STALE'
    assert out['sec-qg-factors.json']['data']['companies']['nvda']['factors']['management_quality']['score'] is None


def test_synthetic_and_future_sources_are_not_published_live(tmp_path):
    out=build(tmp_path,sec(tmp_path,synthetic=True))
    assert out['sec-qg-factors.json']['state']=='NOT_AVAILABLE'
    assert all(f['score'] is None for f in out['sec-qg-factors.json']['data']['companies']['nvda']['factors'].values())
    out=build(tmp_path,sec(tmp_path,acquired='2026-10-11T00:00:00Z'))
    assert out['sec-qg-factors.json']['state']=='NOT_AVAILABLE'


def test_type_engine_pending_and_pricefree_schema_never_emits_other_types(tmp_path):
    out=build(tmp_path,sec(tmp_path))['company-types-pricefree.json']
    assert set(out['data']['companies']['nvda']['memberships'])=={'growth','quality','cyclical','defensive'}
    assert out['data']['companies']['nvda']['memberships']['quality'] is None

@pytest.mark.parametrize('mutate',[
    lambda p:p.update(price=1), lambda p:p['sources'].append({'agency':'SEC','url':'private'}),
    lambda p:p['data']['companies']['nvda']['factors'].update(V={'score':80,'state':'LIVE'}),
    lambda p:p['data']['companies']['nvda']['factors']['revenue_growth'].update(score=float('nan')),
    lambda p:p.update(reason_codes=['private arbitrary message']),
])
def test_public_schema_rejects_price_unknown_fields_and_unbounded_text(tmp_path,mutate):
    payload=build(tmp_path,sec(tmp_path))['sec-qg-factors.json'];mutate(payload)
    with pytest.raises(ValueError,match='PUBLIC_SCREEN_INVALID'):api().require_public_screen('sec-qg-factors.json',payload)


def test_cli_preserves_existing_assets_and_passes_pages_artifact_guard(tmp_path,capsys):
    from build_pages_cockpit import build_public_cockpit as build_site
    from pages_artifact_guard import scan_artifact
    mod=importlib.import_module('public_engine_screens')
    site=tmp_path/'site';build_site(site)
    source=tmp_path/'manifest.json';source.write_text(json.dumps(manifest()))
    assert mod.main(['--manifest',str(source),'--output-dir',str(site),'--as-of',NOW.isoformat(),'--stale-after-hours','48'])==0
    assert scan_artifact(site)['pages_artifact_guard']=='PASS'
    assert 'PUBLIC_SCREENS_OK files=5' in capsys.readouterr().out


def test_manifest_path_escape_and_duplicate_company_fail_without_source_values(tmp_path):
    m=sec(tmp_path);m['sec'][0]['companyfacts']='../private.json'
    with pytest.raises(ValueError,match='PUBLIC_SCREENS_INPUT_INVALID'):build(tmp_path,m)
    m=sec(tmp_path);m['sec'].append(dict(m['sec'][0]))
    with pytest.raises(ValueError,match='PUBLIC_SCREENS_INPUT_INVALID'):build(tmp_path,m)

@pytest.mark.parametrize('mutate',[
    lambda p:p.update(state='STALE'),
    lambda p:p['sources'].clear(),
    lambda p:p['sources'][0].update(agency='BLS'),
    lambda p:p['data']['companies']['nvda'].update(state='NOT_AVAILABLE'),
])
def test_guard_rejects_status_and_provenance_contradictions(tmp_path,mutate):
    payload=build(tmp_path,sec(tmp_path))['sec-qg-factors.json'];mutate(payload)
    with pytest.raises(ValueError,match='PUBLIC_SCREEN_INVALID'):api().require_public_screen('sec-qg-factors.json',payload)


def macro_manifest(tmp_path):
    from tests.test_macro_primary_input import bls_payload,bea_payload,treasury_body,BLS_IDS
    m=manifest()
    for provider,body,extra in [('BLS',json.dumps(bls_payload()).encode(),{'series_ids':list(BLS_IDS)}),('BEA',json.dumps(bea_payload()).encode(),{'table':'T10106'}),('TREASURY',treasury_body(),{})]:
        name=provider+'.input';(tmp_path/name).write_bytes(body)
        m['macro'].append({'provider':provider,'file':name,'acquired_at':NOW.isoformat(),'synthetic':False,**extra})
    return m


def test_macro_nonempty_raw_levels_only_no_regime_or_private_request(tmp_path):
    out=build(tmp_path,macro_manifest(tmp_path))['macro-screen.json']
    assert out['state']=='LIVE' and len(out['data']['observations'])==6
    assert sum(c['state']=='RAW_EVIDENCE' for c in out['data']['cells'])==4
    assert all(c['dimension']=='Level' for c in out['data']['cells'] if c['state']=='RAW_EVIDENCE')
    assert out['data']['regime'] is None and out['data']['pit_status']=='OBSERVED_BOUND_ONLY'
    assert 'SYNTHETIC_PRIVATE_SENTINEL' not in json.dumps(out)


def thirteen_f_manifest(tmp_path):
    from tests.test_sec_13f import _xml,_row,_metadata
    from dataclasses import fields
    from datetime import date
    m=manifest();pair={'synthetic':False}
    for key,qty,quarter,accn,day in [('previous',100,date(2026,3,31),'0000000123-26-000002',date(2026,5,1)),('current',150,date(2026,6,30),'0000000123-26-000001',date(2026,8,1))]:
        name=key+'.xml';(tmp_path/name).write_bytes(_xml(_row(quantity=str(qty),sole=str(qty))))
        obj=_metadata(quarter_end=quarter,accession=accn,filing_date=day,acquired_at=NOW);md={f.name:getattr(obj,f.name) for f in fields(obj)}
        md['cover_binding_evidence']=dict(md['cover_binding_evidence']) if 'cover_binding_evidence' in md else None
        md={k:v for k,v in md.items() if k!='cover_binding_evidence' or v is not None}
        for k,v in tuple(md.items()):
            if isinstance(v,tuple):md[k]=list(v)
            elif hasattr(v,'items'):md[k]=dict(v)
        for k in ('quarter_end','filing_date','acquired_at'):md[k]=md[k].isoformat()
        pair[key]={'file':name,'metadata':md}
    m['thirteen_f']=[pair];return m


def test_13f_projects_public_reported_quantity_not_dollar_value_or_trades(tmp_path):
    out=build(tmp_path,thirteen_f_manifest(tmp_path))['sec-13f-changes.json']
    report=out['data']['reports'][0];assert report['state']=='LIVE'
    change=report['changes'][0]
    assert (change['kind'],change['reported_before'],change['reported_after'],change['reported_delta'])==('ADD',100,150,50)
    assert 'value' not in json.dumps(out) and '2000' not in json.dumps(out)
    change['kind']='REDUCE'
    with pytest.raises(ValueError,match='PUBLIC_SCREEN_INVALID'):api().require_public_screen('sec-13f-changes.json',out)


def test_new_sidecars_checked_in_plain_pages_tar_and_price_injection_blocked(tmp_path):
    from build_pages_cockpit import build_public_cockpit as build_site
    from pages_artifact_guard import scan_artifact,validate_pages_tar
    import tarfile
    site=tmp_path/'site';build_site(site)
    for name,payload in build(tmp_path).items():(site/name).write_text(json.dumps(payload))
    archive=tmp_path/'artifact.tar'
    with tarfile.open(archive,'w',format=tarfile.GNU_FORMAT) as tar:
        import io
        for p in site.iterdir():
            body=p.read_bytes();info=tarfile.TarInfo('./'+p.name);info.size=len(body);info.mode=0o644
            tar.addfile(info,io.BytesIO(body))
    assert validate_pages_tar(archive)['pages_artifact_guard']=='PASS'
    payload=json.loads((site/'sec-qg-factors.json').read_text());payload['data']['price']=123
    (site/'sec-qg-factors.json').write_text(json.dumps(payload))
    assert scan_artifact(site)['pages_artifact_guard']=='FAIL'


def remaining_manifest(tmp_path,provider='FED_H41',unit=None):
    from tests.test_macro_remaining import binding,fed_body,mts_payload,api as remaining_api,MTS_URL,FED_URL
    from dataclasses import fields
    obj=binding(remaining_api(),provider)
    values={f.name:getattr(obj,f.name) for f in fields(obj)}
    if unit is not None:values['unit']=unit
    if values['unit_multiplier'] is not None:values['unit_multiplier']=str(values['unit_multiplier'])
    body=json.dumps(mts_payload(rows=[{'line_code':'SYNTHETIC_TOTAL','reporting_period':'2026-09','record_date':'2026-10-01','amount':'12.50'}])).encode() if provider=='TREASURY_MTS' else fed_body(period='2026-10-09')
    (tmp_path/'remaining.input').write_bytes(body)
    m=manifest();m['macro']=[{'provider':provider,'file':'remaining.input','binding':values,'source_url':MTS_URL if provider=='TREASURY_MTS' else FED_URL,'acquired_at':NOW.isoformat(),'synthetic':False}]
    return m


def test_remaining_source_scale_and_binding_identity_are_preserved_without_private_text(tmp_path):
    out=build(tmp_path,remaining_manifest(tmp_path))['macro-screen.json']
    obs=out['data']['observations'][0]
    assert obs['unit_scale']=={'kind':'MULTIPLIER','value':'1000000'} and obs['value']=='12.50'
    assert len(obs['binding_sha256'])==64 and obs['source_id']=='FED_H41_SUPPLIED_BINDING'
    text=json.dumps(out)
    assert 'SYNTHETIC_EXPLICIT_BASIS' not in text and 'SYNTHETIC_SERIES' not in text and 'http' not in text


def test_manifest_private_unit_is_not_a_public_string(tmp_path):
    out=build(tmp_path,remaining_manifest(tmp_path,provider='TREASURY_MTS',unit='TEST_ONLY_PRIVATE_CANARY'))['macro-screen.json']
    assert out['state']=='NOT_AVAILABLE' and not out['data']['observations']
    assert 'TEST_ONLY_PRIVATE_CANARY' not in json.dumps(out)


@pytest.mark.parametrize('change',[
    lambda p:p['data']['observations'][0].update(source_response_sha256='0'*64),
    lambda p:p['data']['observations'][0].update(available_at='2026-10-01T00:00:00Z'),
    lambda p:p['data']['cells'][1].update(state='RAW_EVIDENCE'),
    lambda p:p['data']['observations'][0].update(observation_period='2026-99'),
])
def test_macro_guard_rejects_unbound_or_incoherent_raw_evidence(tmp_path,change):
    out=build(tmp_path,macro_manifest(tmp_path))['macro-screen.json'];change(out)
    with pytest.raises(ValueError,match='PUBLIC_SCREEN_INVALID'):api().require_public_screen('macro-screen.json',out)


def test_two_bindings_on_same_response_keep_their_own_binding_hash(tmp_path):
    m=remaining_manifest(tmp_path,provider='TREASURY_MTS')
    body=json.loads((tmp_path/'remaining.input').read_text());body['data'].append(dict(body['data'][0],line_code='SYNTHETIC_OTHER',amount='99.0'))
    (tmp_path/'remaining.input').write_text(json.dumps(body))
    import copy
    second=copy.deepcopy(m['macro'][0]);second['binding']['field_filters']=[['line_code','SYNTHETIC_OTHER']];m['macro'].append(second)
    observations=build(tmp_path,m)['macro-screen.json']['data']['observations']
    assert len(observations)==2 and len({o['binding_sha256'] for o in observations})==2
    assert {o['value'] for o in observations}=={'12.50','99.0'}


def test_official_bea_chained_dollar_unit_spelling_is_public(tmp_path):
    m=macro_manifest(tmp_path);body=json.loads((tmp_path/'BEA.input').read_text())
    body['BEAAPI']['Results']['Data'][0]['CL_UNIT']='Billions of Chained (2017) Dollars'
    (tmp_path/'BEA.input').write_text(json.dumps(body))
    out=build(tmp_path,m)['macro-screen.json']
    assert next(o for o in out['data']['observations'] if o['provider']=='BEA')['unit']=='Billions of Chained (2017) Dollars'
    assert next(c for c in out['data']['cells'] if c['axis']=='Growth' and c['dimension']=='Level')['state']=='RAW_EVIDENCE'


def test_merged_type_engine_uses_three_year_revenue_ramp_without_price(tmp_path):
    if importlib.util.find_spec('investment_system.qgv.company_types') is None:
        pytest.skip('type engine awaiting PR135 approval')
    out=build(tmp_path,sec(tmp_path))['company-types-pricefree.json']
    row=out['data']['companies']['nvda']
    assert row['memberships']['growth']==pytest.approx(.5)
    assert row['config_version']=='type_config/1' and row['state']=='LIVE'


def test_pricefree_type_metrics_are_published_beside_memberships_and_legacy_rows_still_validate(tmp_path):
    out=build(tmp_path,sec(tmp_path))['company-types-pricefree.json']
    row=out['data']['companies']['nvda']
    assert set(row['metrics'])=={'revenue_cagr_3y','roic'}
    assert row['metrics']['revenue_cagr_3y']==pytest.approx(.15)
    assert out['data']['companies']['asml']['metrics']=={'revenue_cagr_3y':None,'roic':None}
    assert 'price' not in json.dumps(out)
    legacy=json.loads(json.dumps(out))
    for r in legacy['data']['companies'].values():r.pop('metrics')
    api().require_public_screen('company-types-pricefree.json',legacy)
    for bad in (float('nan'),1e9,'0.1'):
        broken=json.loads(json.dumps(out));broken['data']['companies']['nvda']['metrics']['roic']=bad
        with pytest.raises(ValueError):api().require_public_screen('company-types-pricefree.json',broken)
