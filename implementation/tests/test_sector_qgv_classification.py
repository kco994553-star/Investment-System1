import copy
import hashlib
import json
import pytest
from investment_system.research.sector_qgv_classification import classify, link_classification, official_q_gate

ASOF='2026-11-04T02:29:35.166580Z'


def evidence(sic='7372',desc='SERVICES-PREPACKAGED SOFTWARE',cik='0000000001'):
    return {'issuer_id':cik,'sic':sic,'sic_description':desc,'source_sha256':'a'*64,
            'archive_sha256':'b'*64,'member':'synthetic/0000000001/submissions.json',
            'acquired_at':'2026-11-03T00:00:00Z','source_url':'https://example.invalid/submissions',
            'source_kind':'SEC_SUBMISSIONS','fiscal_year_end':'1231'}


def test_research_mapping_preserves_official_classification_and_point_scope():
    e=evidence();r=classify(e,as_of=ASOF,expected_issuer='0000000001',expected_sic='7372',source_profile='GENERAL')
    assert r['sector_id']=='INFORMATION_TECHNOLOGY' and r['accounting_template']=='GENERAL'
    assert r['official_classification']['system']=='SEC_SIC'
    assert r['official_classification']['code']=='7372'
    assert r['mapping']['kind']=='RESEARCH_CORRESPONDENCE'
    assert r['mapping']['valid_from']=='2026-11-04' and r['mapping']['valid_to']=='2026-11-05'
    assert r['mapping']['effective_date_basis']=='SINGLE_EVALUATION_APPLICATION_NOT_SOURCE_CHANGE_DATE'


@pytest.mark.parametrize('sic,reason',[('6798','REIT_ACCOUNTING_AND_BOOK_SECTOR_UNRESOLVED'),
 ('6282','FEE_BUSINESS_NOT_ESTABLISHED'),('4833','BOOK_TELECOM_MEDIA_BOUNDARY_UNRESOLVED'),
 ('7389','SIC_BUSINESS_MIX_UNRESOLVED')])
def test_ambiguous_sic_is_not_promoted(sic,reason):
    r=classify(evidence(sic),as_of=ASOF,expected_issuer='0000000001',expected_sic=sic,source_profile='GENERAL')
    assert r['mapping'] is None and reason in r['reasons']


def test_future_conflict_and_missing_source_fail_closed():
    e=evidence();e['acquired_at']='2026-11-05T00:00:00Z'
    assert classify(e,as_of=ASOF,expected_issuer='0000000001',expected_sic='7372',source_profile='GENERAL')['reasons']==['SOURCE_NOT_AVAILABLE_AT_EVALUATION']
    e=evidence(cik='0000000002')
    assert 'ISSUER_MISMATCH' in classify(e,as_of=ASOF,expected_issuer='0000000001',expected_sic='7372',source_profile='GENERAL')['reasons']
    e=evidence();e['source_sha256']=None
    assert classify(e,as_of=ASOF,expected_issuer='0000000001',expected_sic='7372',source_profile='GENERAL')['mapping'] is None


def test_banks_insurers_and_software_do_not_share_peers():
    for sic,template in [('6021','BANK'),('6331','INSURANCE'),('6211','BROKER')]:
        r=classify(evidence(sic),as_of=ASOF,expected_issuer='0000000001',expected_sic=sic,source_profile='FINANCIAL')
        assert r['sector_id']=='FINANCIALS' and r['accounting_template']==template
    r=classify(evidence('6021'),as_of=ASOF,expected_issuer='0000000001',expected_sic='6021',source_profile='GENERAL')
    assert 'ACCOUNTING_PROFILE_CONFLICT' in r['reasons']


def test_link_preserves_raw_observations_and_unmapped_members():
    obs={'roa_ttm':{'value':.05,'status':'VALID'}}
    before={'as_of':ASOF,'valuation_date':'2026-11-04','snapshot_id':'before','input_version':'before/1',
            'members':['A','B'],'rows':[{'company_id':'A','issuer_id':'0000000001','source_sic':'7372','source_profile':'GENERAL','observations':obs},
                                     {'company_id':'B','issuer_id':'0000000002','source_sic':'6798','source_profile':'GENERAL','observations':{}}]}
    old=copy.deepcopy(before)
    after,audit=link_classification(before,{'A':evidence(),'B':evidence('6798',cik='0000000002')})
    assert before==old and after['members']==before['members']
    assert after['rows'][0]['observations']==obs
    assert after['rows'][1]['mapping'] is None and audit['mapped']==1 and audit['unresolved']==1
    assert audit['raw_observations_recomputed']==0


def test_gate_uses_existing_official_q_and_preserves_its_policy():
    # The wrapper consumes the existing official-engine context, not sector Q.
    companies={str(i):{'qg_axes':{'Q':{'score':i*5}},'industry_group':'old-industry',
                      'cik':str(i),'in_cross_section':True,'factors':{}} for i in range(20)}
    gates=official_q_gate(companies,as_of=ASOF,source_sha256='a'*64,calc_version='qgv2-calc/2026-10-23.1')
    assert gates['0']['q_industry_percentile']==0
    assert gates['19']['q_industry_percentile']==100
    assert gates['0']['as_of']=='2026-11-04' and gates['0']['derivation']=='OFFICIAL_Q_ONLY_REPLAY'
    assert gates['0']['peer_count']==20
    with pytest.raises(ValueError,match='VERSION'):
        official_q_gate(companies,as_of=ASOF,source_sha256='a'*64,calc_version='other')


def test_classification_unlocks_partial_qg_without_price_or_gate_substitution():
    from pathlib import Path
    from investment_system.research.sector_qgv import default_config, preview_qgv
    s=json.loads((Path(__file__).parents[1]/'docs/research/sector_qgv/synthetic-input.json').read_text());ev={}
    for row in s['rows']:
        row.update(sector_id=None,accounting_template=None,mapping=None,source_sic='7372',source_profile='GENERAL',gate=None)
        ev[row['company_id']]=evidence(cik=row['issuer_id'])
        ev[row['company_id']]['acquired_at']='2026-11-01T00:00:00Z'
        row['observations']={v:o for v,o in row['observations'].items() if v in ('operating_margin_ttm','accruals_assets_ttm','debt_assets','revenue_cagr_3y','roa_improvement_3y')}
    linked,audit=link_classification(s,ev)
    p=preview_qgv(default_config(),linked,'partial')
    assert audit['mapped']==20 and audit['raw_observations_recomputed']==0
    assert {a:x['valid'] for a,x in p['coverage']['axes'].items()}=={'Q':20,'G':20,'V':0}
    assert p['coverage']['total']['valid']==0
    assert all(r['gate_status']=='UNKNOWN' and r['total'] is None for r in p['result_rows'])
    linked['rows'].pop();linked['members'].pop()
    p=preview_qgv(default_config(),linked,'small')
    assert p['coverage']['axes']['Q']['valid']==0
    assert p['coverage']['factors']['operating_margin_ttm']['score_failures']=={'PEER_SAMPLE_SMALL':19}


def test_gate_evaluation_must_match_not_november_two_price_date():
    s={'as_of':ASOF,'valuation_date':'2026-11-04','snapshot_id':'old','members':['A'],
       'rows':[{'company_id':'A','issuer_id':'0000000001','source_sic':'7372','source_profile':'GENERAL','observations':{}}]}
    with pytest.raises(ValueError,match='GATE_SNAPSHOT_MISMATCH'):
        link_classification(s,{'A':evidence()},gates={'A':{'as_of':'2026-11-02','source_as_of':ASOF}})


def test_identical_source_uses_earliest_verified_observation_not_archive_order(tmp_path):
    import io
    import tarfile
    from investment_system.research.sector_qgv_classification import load_held_classification
    body=json.dumps({'cik':1,'sic':'7372','sicDescription':'PREPACKAGED SOFTWARE','fiscalYearEnd':'1231'}).encode()
    sha=hashlib.sha256(body).hexdigest();specs=[]
    for release,when in [('later','2026-11-05T00:00:00Z'),('earlier','2026-11-03T00:00:00Z')]:
        manifest={'companies':[{'cik':'0000000001','acquired_at':when,'sha256':{'submissions.json':sha}}]}
        path=tmp_path/(release+'.tar.gz')
        with tarfile.open(path,'w:gz') as archive:
            for member,b in [(release+'/manifest.json',json.dumps(manifest).encode()),(release+'/0000000001/submissions.json',body)]:
                info=tarfile.TarInfo(member);info.size=len(b);archive.addfile(info,io.BytesIO(b))
        specs.append({'path':str(path),'release':release,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    sec={'records':{'A':{'cik':'0000000001','source_sha256':{'submissions':sha}}}}
    a=load_held_classification(sec,specs);b=load_held_classification(sec,list(reversed(specs)))
    assert a==b and a['A']['acquired_at']=='2026-11-03T00:00:00Z'
    assert classify(a['A'],as_of=ASOF,expected_issuer='0000000001',expected_sic='7372',source_profile='GENERAL')['mapping'] is not None


def test_gate_replay_clock_is_not_a_new_input_or_cache_identity():
    companies={str(i):{'qg_axes':{'Q':{'score':i*5}},'industry_group':'old-industry','cik':str(i)} for i in range(20)}
    first=official_q_gate(companies,as_of=ASOF,source_sha256='a'*64,calc_version='qgv2-calc/2026-10-23.1')
    second=official_q_gate(companies,as_of=ASOF,source_sha256='a'*64,calc_version='qgv2-calc/2026-10-23.1')
    assert first==second
    assert all('computed_at' not in r for r in first.values())


def test_addendum_connects_exact_activity_without_touching_previous_inputs():
    from investment_system.research.sector_qgv_classification import extend_held_classification
    s={'as_of':ASOF,'valuation_date':'2026-11-04','snapshot_id':'old','members':['A','B','C'],
       'rows':[{'company_id':'A','issuer_id':'0000000001','source_sic':'2070','source_profile':'GENERAL',
                'reasons':['EXACT_SIC_CORRESPONDENCE_NOT_REVIEWED'],'mapping':None,'observations':{'kept':1},'gate':{'kept':2}},
               {'company_id':'B','mapping':{'original':True},'observations':{},'gate':None},
               {'company_id':'C','source_sic':'6798','mapping':None,'reasons':['REIT_ACCOUNTING_AND_BOOK_SECTOR_UNRESOLVED']}]}
    original=copy.deepcopy(s)
    linked,audit=extend_held_classification(s,{'A':evidence('2070','Fats & Oils')})
    assert s==original and audit['newly_mapped']==1
    assert linked['rows'][0]['sector_id']=='CONSUMER_STAPLES'
    assert linked['rows'][0]['observations']=={'kept':1} and linked['rows'][0]['gate']=={'kept':2}
    assert linked['rows'][1:]==s['rows'][1:] and linked['members']==s['members']
    assert classify(evidence('2070','Fats & Oils'),as_of=ASOF,expected_issuer='0000000001',expected_sic='2070',source_profile='GENERAL')['mapping'] is None
    for e in [evidence('2070','Wrong activity'),dict(evidence('2070','Fats & Oils'),acquired_at='2026-11-05T00:00:00Z')]:
        assert extend_held_classification(s,{'A':e})[1]['newly_mapped']==0
