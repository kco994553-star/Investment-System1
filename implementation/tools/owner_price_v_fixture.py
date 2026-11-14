"""Developer-only SYNTHETIC RAM fixtures; no network, persistence or real-input mode."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import runpy

from investment_system.research.kis_price_bridge import normalize_page
from investment_system.research.qgv_555 import configuration
from investment_system.research.sector_qgv import digest


def fixture(n=23,model='U1-555'):
    source=Path(__file__).resolve().parents[1]/'tests/research/test_personal_sheet_v.py'
    req,e,r,financial,_=runpy.run_path(str(source))['fixture'](n)
    day='2026-11-13';cutoff='2026-11-14T04:02:00Z';contracts={}
    req.update(schema_version='owner-price-v-request/1',namespace='OWNER_PRIVATE_KIS_V')
    req['configuration']=configuration(model,version='0.4.0')
    req['context'].update(context_id='synthetic-owner-kis-close',evaluated_at=cutoff,input_cutoff=cutoff,
        provider='KIS',price_definition='KIS_DAILY_CLOSE',evaluation_mode='EXPLICIT_EOD_ASOF')
    for s in (e,r):
        s.update(input_cutoff=cutoff,population_version='owner-synthetic-context/1')
    for i,row in enumerate(e['rows']):
        cid=row['company_id'];b=financial[cid]['basis_evidence'];symbol='SYN'+str(i)
        b['mapping'].update(provider='KIS',exchange='NASDAQ',provider_exchange_code='NAS')
        b['corporate_actions']['basis']='NO_ACTIONS_DOCUMENTED'
        body=json.dumps(dict(rt_cd='0',output1=dict(rsym='DNAS'+symbol),
            output2=[dict(xymd='20261113',open=str(10+i),high=str(12+i),low=str(9+i),
                clos=str(10+i),tvol='100',tamt=str(1000+i*100))]),sort_keys=True).encode()
        receipt=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),fetched_at='2026-11-14T04:00:00Z',http_status=200)
        request=dict(SYMB=symbol,EXCD='NAS',MODP='0',GUBN='0',BYMD='20261113')
        evidence=dict(currency='USD',currency_reference='SYNTHETIC_USD',
            identity_status='CONFIRMED',identity_reference='SYNTHETIC_LISTING',
            identity_start='2026-09-30',identity_end=day,issuer_id=row['issuer_id'],
            security_id=row['security_id'],confirmed_ranges=[
                dict(**{'from':'2026-09-30','to':day},evidence='SYNTHETIC_ACTION_COVERAGE')],
            held_ranges=[],splits=[])
        c=normalize_page(body,receipt=receipt,request=request,evidence=evidence)
        c['fixture_kind']='SYNTHETIC_NOT_A_COMPANY'
        contracts[cid]=c
    return req,e,r,financial,contracts,{cid:digest(c) for cid,c in contracts.items()}


def prepared(case=None):
    from investment_system.research.personal_sheet_v import prepare_owner
    from investment_system.research.qgv_555 import identity
    req,e,r,f,c,pins=fixture() if case is None else case
    return prepare_owner(req,e,r,f,expected_evaluation=identity(e),expected_reference=identity(r),
        contracts=c,expected_contract_hashes=pins)


def examples():
    """Same producer, full RAM packet/result plus small display projections."""
    from investment_system.research.personal_sheet_v import owner_result,owner_page,owner_group_page
    p=prepared();result=owner_result(p)
    group=next(g for g in result['groups'] if g['kind']=='roles' and g['key']=='v_earnings_yield')
    return dict(packet=p['packet_text'],pins=dict(expected_payload_sha256=p['payload_sha256'],
        expected_evaluation=p['packet']['evaluation_original'],expected_reference=p['packet']['reference_original'],
        expected_configuration_hash=p['packet']['configuration_hash']),
        result=result,page=owner_page(result,limit=3),
        deciles=[owner_group_page(result,group['group_id'],decile=d) for d in range(1,11)])


def wire_files():
    """Return bounded synthetic UTF-8 members in RAM; no disk writer or real mode."""
    from investment_system.research.dual_qgv import json_bytes
    e=examples()
    out={'packet.json':e['packet'].encode()}
    for name in ('pins','result','page'):out[name+'.json']=json_bytes(e[name])
    out.update({'decile-'+str(d)+'.json':json_bytes(v) for d,v in enumerate(e['deciles'],1)})
    return out


def example_manifest():
    files=wire_files()
    return dict(schema_version='synthetic-owner-price-example-manifest/1',data_kind='SYNTHETIC',
        namespace='OWNER_PRIVATE_KIS_V',real_price_input_received=False,
        real_price_calculation_executed=False,files=[dict(path=name,size=len(raw),
            sha256=hashlib.sha256(raw).hexdigest()) for name,raw in sorted(files.items())])


def state_examples():
    from investment_system.research.personal_sheet_v import owner_result
    out=[]
    for name in ('NORMAL','MISSING_PRICE','MISSING_EXACT_DAY','IDENTITY_UNCONFIRMED',
                 'SPLIT_UNCONFIRMED','EV_INPUT_MISSING','GATE_UNKNOWN'):
        case=fixture(10);req,e,r,f,c,pins=case;cid=e['rows'][0]['company_id']
        if name=='MISSING_PRICE':del c[cid];del pins[cid]
        elif name=='MISSING_EXACT_DAY':
            for key in ('raw_bars','bars'):c[cid][key][0]['date']='2026-11-12'
            c[cid]['price_basis_date']='2026-11-12';pins[cid]=digest(c[cid])
        elif name=='IDENTITY_UNCONFIRMED':f[cid]['basis_evidence']['mapping']['status']='UNKNOWN'
        elif name=='SPLIT_UNCONFIRMED':
            c[cid]['splits']=[dict(date='2026-10-15',ratio='2',status='CONFIRMED',evidence='SYNTHETIC_SPLIT')]
            f[cid]['basis_evidence']['corporate_actions']['basis']='ALREADY_NORMALIZED';pins[cid]=digest(c[cid])
        elif name=='EV_INPUT_MISSING':
            record=f[cid]['record'];record['v_inputs_v2']['cash_and_equivalents']['value']=None
            for snapshot in (e,r):snapshot['rows'][0]['owner_source_context']['record_hash']=digest(record)
        elif name=='GATE_UNKNOWN':e['rows'][0]['gate']=None
        result=owner_result(prepared(case));row=result['rows'][0]
        out.append(dict(case=name,denominator=result['denominator'],counts=result['counts'],
            price_metadata=row['price_metadata'],capitalization_basis=row['capitalization_basis'],
            raw_available={key:value is not None for key,value in row['raw'].items()},
            role_available={key:value['score'] is not None for key,value in row['roles'].items()},
            V_available=row['axes']['V'] is not None,gate_status=row['gate_status'],
            total_available=row['total'] is not None))
    return dict(schema_version='synthetic-owner-price-states/1',data_kind='SYNTHETIC',states=out)
