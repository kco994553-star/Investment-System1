import copy
import json
from pathlib import Path
import pytest
from investment_system.research.sector_qgv import digest
from investment_system.research.sector_qgv_v import VERSION,resume,readiness,component


def fixture():
    s=json.loads((Path(__file__).parents[1]/'docs/research/sector_qgv/synthetic-input.json').read_text())
    rows=[];records={}
    for i,r in enumerate(s['rows']):
        record={'currency':'USD','acquired_at':s['as_of'],'cik':r['issuer_id']}
        end=r['observations']['operating_margin_ttm']['fiscal_period']['end']
        from datetime import date,timedelta
        start=str(date.fromisoformat(end)-timedelta(days=364))
        def part(field,value,kind,unit='USD'):
            x=component(record,field,value,kind,s['valuation_date'] if kind=='PRICE' else end,'synthetic:source',start=start if kind=='TTM' else None,unit=unit)
            x.update(security_id=r['security_id'],share_basis='COMMON:1',corporate_action_basis='NO_CHANGE_VERIFIED');return x
        fields={'eps_ttm_diluted':part('eps_ttm_diluted',i+1,'TTM','USD/share'),'cfo':part('cfo',100+i,'TTM'),'revenue':part('revenue',1000+i,'TTM')}
        rows.append({k:r[k] for k in ('company_id','issuer_id','security_id','sector_id','accounting_template')}|{'selected_variants':['ep_ttm_diluted','cfo_mcap','sales_ev'],'inputs':fields,'diagnostics':{}})
        price=part('price',10,'PRICE','USD/share');mcap=part('issuer_mcap',1000,'PRICE');ev=part('enterprise_value',1200,'PRICE')
        for x,d in [(mcap,'ALL_CORRESPONDING_COMMON_CLASSES'),(ev,'EQUITY_DEBT_PREFERRED_NCI_LESS_CASH')]:x.update(definition_id=d,capital_scope_evidence=['synthetic:capital'])
        records[r['company_id']]={'basis':{'issuer_id':r['issuer_id'],'security_id':r['security_id'],'valid_from':'2000-01-01','valid_to':'2100-01-01','evidence_refs':['synthetic:basis']},
          'inputs':{'price':price,'issuer_mcap':mcap,'enterprise_value':ev},'capital_evidence':{'all_common_classes_confirmed':True,'classes':[{'security_id':r['security_id'],'actual_shares':100,'unit':'shares','date':s['valuation_date'],'evidence_refs':['synthetic:shares'],'corporate_action_basis':'NO_CHANGE_VERIFIED'}],
          'components':{k:{'value':v,'currency':'USD','period_end':end,'evidence_refs':['synthetic:'+k]} for k,v in {'debt':300,'cash':100,'preferred':0,'nci':0}.items()}}}
        r['observations']={k:v for k,v in r['observations'].items() if not k in ['ep_ttm_diluted','cfo_mcap','sales_ev']}
    for record in records.values():
        b=record['basis'];b.update(available_at=s['as_of'],retrieved_at=s['as_of'])
        cap=record['capital_evidence'];c=cap['classes'][0];c.update(available_at=s['as_of'],retrieved_at=s['as_of'],share_basis='COMMON:1')
        c['quote']={'security_id':c['security_id'],'date':s['valuation_date'],'value':10,'currency':'USD','unit':'USD/share','share_basis':'COMMON:1','corporate_action_basis':'NO_CHANGE_VERIFIED','evidence_refs':['synthetic:quote'],'available_at':s['as_of'],'retrieved_at':s['as_of']}
        for v in cap['components'].values():v.update(available_at=s['as_of'],retrieved_at=s['as_of'])
    pack={'schema_version':VERSION,'valuation_date':s['valuation_date'],'as_of':s['as_of'],'snapshot':s,'rows':rows,'data_kind':'SYNTHETIC'}
    market={'schema_version':'sector-qgv-v-market-input/1','data_kind':'SYNTHETIC','valuation_date':s['valuation_date'],'as_of':s['as_of'],'resume_hash':digest(pack),'records':records}
    return pack,market


def test_same_kernel_price_to_ratio_factor_v_and_total():
    pack,market=fixture();old=copy.deepcopy(pack);s,p=resume(pack,market,'synthetic')
    assert pack==old
    assert p['coverage']['axes']['V']['valid']==20 and p['coverage']['total']['valid']==20
    assert s['rows'][0]['observations']['ep_ttm_diluted']['value']==.1
    assert s['rows'][0]['observations']['cfo_mcap']['value']==.1
    assert s['rows'][0]['observations']['sales_ev']['value']==pytest.approx(1000/1200)
    assert all(r['observations']['roa_improvement_3y']==old['snapshot']['rows'][i]['observations']['roa_improvement_3y'] for i,r in enumerate(s['rows']))


@pytest.mark.parametrize('mutation,reason',[
 ('date','CONTEXT'),('shares','SHARES'),('nci','EV_COMPONENT'),('financial','REPLACE_FINANCIAL'),('identity','IDENTITY')])
def test_resume_rejects_wrong_date_missing_zero_evidence_and_basis(mutation,reason):
    p,m=fixture();first=next(iter(m['records'].values()))
    if mutation=='date':m['valuation_date']='2026-11-02' if p['valuation_date']!='2026-11-02' else '2026-11-04'
    elif mutation=='shares':first['capital_evidence']['classes'][0]['actual_shares']=None
    elif mutation=='nci':first['capital_evidence']['components'].pop('nci')
    elif mutation=='financial':first['inputs']['cfo']=p['rows'][0]['inputs']['cfo']
    elif mutation=='identity':first['basis']['security_id']=None
    with pytest.raises(ValueError,match=reason):resume(p,m,'invalid')


def test_missing_eps_and_small_peer_are_not_zero_or_price_success():
    p,m=fixture();p['rows'][0]['inputs'].pop('eps_ttm_diluted');m['resume_hash']=digest(p)
    s,view=resume(p,m,'missing')
    assert s['rows'][0]['observations']['ep_ttm_diluted']['value'] is None
    assert view['coverage']['axes']['V']['valid']==0
    assert view['result_rows'][1]['factors']['ep_ttm_diluted']['score_status']=='PEER_SAMPLE_SMALL'
    assert readiness(p)['counts']['numerator_ready']==59


def test_late_source_rejected_not_retimed():
    p,m=fixture();first=next(iter(m['records'].values()));first['inputs']['price']['retrieved_at']='2099-01-01T00:00:00Z'
    s,_=resume(p,m,'late');assert s['rows'][0]['observations']['ep_ttm_diluted']['status']=='NOT_YET_AVAILABLE'


def test_future_capital_and_inconsistent_amounts_are_rejected():
    for mutation,reason in [('future','FUTURE'),('class','TARGET_CLASS'),('quote','QUOTE_BASIS'),('amount','RECONCILIATION')]:
        p,m=fixture();r=next(iter(m['records'].values()))
        if mutation=='future':r['capital_evidence']['components']['nci']['available_at']='2099-01-01T00:00:00Z'
        if mutation=='class':r['capital_evidence']['classes'][0]['security_id']='UNRELATED'
        if mutation=='quote':r['capital_evidence']['classes'][0]['quote']['currency']='EUR'
        if mutation=='amount':r['inputs']['enterprise_value']['value']=999
        with pytest.raises(ValueError,match=reason):resume(p,m,'invalid')


def test_existing_cli_writes_v_preview_and_manifest_without_qg_reconstruction(tmp_path):
    import hashlib,importlib.util
    p,m=fixture()
    def write(name,data):
        path=tmp_path/name;path.write_text(json.dumps(data));return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    job={'mode':'v-resume','data_kind':'SYNTHETIC','request_id':'synthetic-v-cli','v_pack':write('pack.json',p),'market_inputs':write('market.json',m)}
    sp=importlib.util.spec_from_file_location('v_cli',Path(__file__).parents[1]/'tools/sector_qgv.py');cli=importlib.util.module_from_spec(sp);sp.loader.exec_module(cli)
    summary=cli.run(job,tmp_path/'run',True)
    assert summary['axes']['V']['valid']==20 and summary['total']['valid']==20
    assert (tmp_path/'run/manifest.json').exists()


def test_later_calculation_clock_preserves_financial_snapshot_and_rejects_earlier_clock():
    p,m=fixture();original=p['as_of'];m['as_of']='2026-11-08T00:00:00Z'
    s,_=resume(p,m,'later');assert s['source_financial_as_of']==original and s['as_of']==m['as_of']
    m['as_of']='2000-01-01T00:00:00Z'
    with pytest.raises(ValueError,match='CONTEXT'):resume(p,m,'earlier')


def test_offset_capital_evidence_uses_utc_valuation_date():
    p,m=fixture();m['as_of']='2026-11-08T00:00:00Z'
    next(iter(m['records'].values()))['basis']['available_at']=p['valuation_date']+'T20:00:00-08:00'
    with pytest.raises(ValueError,match='FUTURE'):resume(p,m,'offset')


def test_cli_cannot_label_private_market_as_synthetic(tmp_path):
    import hashlib,importlib.util
    p,m=fixture();m['data_kind']='PRIVATE'
    def put(name,data):
        path=tmp_path/name;path.write_text(json.dumps(data));return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    job={'mode':'v-resume','data_kind':'SYNTHETIC','request_id':'kind','v_pack':put('p.json',p),'market_inputs':put('m.json',m)}
    sp=importlib.util.spec_from_file_location('v_cli_kind',Path(__file__).parents[1]/'tools/sector_qgv.py');cli=importlib.util.module_from_spec(sp);sp.loader.exec_module(cli)
    with pytest.raises(ValueError,match='DATA_KIND'):cli.run(job,tmp_path/'out',True)


def test_sec_preparation_cannot_be_published_as_a_synthetic_job(tmp_path):
    import importlib.util
    sp=importlib.util.spec_from_file_location('v_prepare_kind',Path(__file__).parents[1]/'tools/sector_qgv.py');cli=importlib.util.module_from_spec(sp);sp.loader.exec_module(cli)
    with pytest.raises(ValueError,match='PREPARATION_PRIVATE'):
        cli.run({'mode':'v-prepare','data_kind':'SYNTHETIC'},tmp_path/'out',True)
