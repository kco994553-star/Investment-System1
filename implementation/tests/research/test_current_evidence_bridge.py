"""Staged evidence linkage, not another financial or universe scoring engine."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from investment_system.research import current_evidence_bridge as bridge
from investment_system.research import current_expansion as pipeline
from investment_system.qgv import v2_factors


def sample():
    source=dict(source_ref='SYNTHETIC:catalog',scope='SEC_TICKER_OBSERVATIONS',complete=False,
                observed_at='2026-09-25T00:00:00Z',basis_date='2026-09-25',sha256='a'*64)
    candidates=[dict(cik_str=1,ticker='FIRST',title='Synthetic unused'),
                dict(cik_str=2,ticker='SYN',title='Synthetic issuer, title is not a security type')]
    financial=dict(cik='0000000002',state='LIVE',reason_codes=[],acquired_at='2026-09-25T01:00:00Z',
                   calc_version=v2_factors.CALC_VERSION,currency='USD',metrics={'net_margin':12.5},v_inputs_v2={})
    member='data/raw/blobs/submissions__0000000002'
    receipt=dict(sha256='b'*64,source_url='SYNTHETIC:submissions',fetched_at='2026-09-25T00:01:00Z')
    submissions={**receipt,'member':member,'exact_ticker_match':True,'observed_tickers':['SYN'],
                 'observed_exchanges':['Nasdaq'],'exchange_values':['Nasdaq'],
                 'tickers_json_pointers':['/tickers/0'],'exchange_json_pointers':['/exchanges/0']}
    row=dict(observation_id='1',ticker='SYN',cik='0000000002',catalog_observation=source,
             submissions_evidence=submissions,cover_evidence=[],archived_title_descriptions=[],
             issuer_ticker_multiplicity=1,security_id=None,evaluation_date='2026-11-02')
    held=dict(candidates=candidates,financials={'0000000002':financial},source=source)
    return held,{'schema':'synthetic-crosswalk/1','rows':[row]},[],{member:receipt},[]


def run(data=None, day='2026-11-02'):
    held,crosswalk,covers,sources,links=data or sample()
    return bridge.link_and_evaluate(held=held,crosswalk=crosswalk,cover_evidence=covers,
                                   source_evidence=sources,document_links=links,basis_date=day)


def document_link():
    return dict(kind='EXISTING_DOCUMENT_EVIDENCE_LINK',issuer_cik='0000000002',ticker_observation='SYN',
                cover_identity={'EntityCentralIndexKey':'0000000002','TradingSymbol':'SYN',
                                'Security12bTitle':'Common Stock, $0.01 par value','SecurityExchangeName':'NASDAQ'},
                existing_research_evidence={'level':'DOCUMENT_RECONSTRUCTED','from':'2026-08-05','to':'2026-10-30',
                                            'source_repo':'SYNTHETIC:private','source_commit':'c'*40,'source_evidence':'proof.json'})


def test_sparse_original_observation_id_survives_pipeline_reindexing():
    result=run();row=result['rows'][0]
    assert row['original_observation_id']=='1' and row['evaluation_observation_id']=='0'
    assert result['evaluation']['rows'][0]['ticker']=='SYN'
    assert result['evaluation']['rows'][0]['raw_metrics']=={'net_margin':12.5}
    assert row['stages']['issuer_link']['state']=='SUBMISSIONS_CORROBORATED'
    assert result['pipeline_inputs']['evidence']['0']['issuer_id']=='CIK:0000000002'
    assert result['pipeline_inputs']['evidence']['0']['security_id'] is None
    assert result['evaluation']['rows'][0]['eligibility']=='UNKNOWN'
    assert result['evaluation']['coverage']['denominator'] is None


def test_documentary_identity_is_independent_of_external_id_but_not_extended():
    data=sample();data[-1].append(document_link())
    before=run(data,'2026-10-30')['rows'][0]
    after=run(data,'2026-11-02')['rows'][0]
    assert before['stages']['same_security_at_basis']['state']=='DOCUMENTED_AT_BASIS'
    assert before['stages']['external_fixed_id']['state']=='NOT_SUPPLIED'
    assert before['engine_evidence']['security_type']=='COMMON'
    assert after['stages']['same_security_at_basis']['state']=='DOCUMENTED_OUTSIDE_BASIS'
    assert after['engine_evidence']['security_type'] is None
    assert after['engine_evidence']['valid_to']=='2026-10-30'


@pytest.mark.parametrize('title',[None,'','  '])
def test_bounded_identity_without_security_title_cannot_claim_type_evidence(title):
    data=sample();link=document_link();link['cover_identity']['Security12bTitle']=title;data[-1].append(link)
    with pytest.raises(ValueError,match='DOCUMENT_LINK_UNCONFIRMED'):run(data)


def test_missing_financial_record_is_preserved_without_invented_metrics():
    data=sample();data[0]['financials'].clear()
    result=run(data)
    assert result['counts']['candidate_rows']==1
    assert result['rows'][0]['stages']['issuer_link']['financial_available'] is False
    assert result['evaluation']['rows'][0]['raw_metrics']=={}
    assert result['financial_reuse']['financial_issuers_reused']==0


def test_archived_cover_title_is_carried_but_period_is_not_validity_or_exclusion():
    data=sample();held,x,covers,sources,_=data
    proof=dict(evidence_id=1,cik='0000000002',symbol='SYN',titles=['Exchange Traded Note'],
               source_member='cover',source_sha256='d'*64,accession='SYNTHETIC',context_id='ctx',
               context={'period_start':'2024-01-01','period_end':'2024-03-31'},
               symbol_byte_ranges=[{'start':1,'end_exclusive':3}],title_byte_ranges=[{'start':4,'end_exclusive':7}])
    covers.append(proof);sources['cover']={'sha256':'d'*64,'source_url':'SYNTHETIC:cover','fetched_at':'2026-09-25T00:00:00Z'}
    x['rows'][0]['cover_evidence']=[deepcopy(proof)]
    x['rows'][0]['archived_title_descriptions']=['EXPLICIT_ETN_DESCRIPTION']
    r=run(data)
    assert r['rows'][0]['stages']['security_type_evidence']['state']=='DOCUMENTED_ARCHIVED_TYPE'
    assert r['pipeline_inputs']['evidence']['0']['valid_from'] is None
    assert r['pipeline_inputs']['evidence']['0']['security_type'] is None
    assert r['evaluation']['counts']['excluded']==0 and r['evaluation']['counts']['unknown']==1


def test_single_ticker_does_not_imply_representative_or_reuse_financial_currency_for_price():
    r=run()['rows'][0]
    assert r['stages']['representative']['value'] is None
    assert r['stages']['valuation_inputs']['currency']['financial_currency']=='USD'
    assert r['stages']['valuation_inputs']['currency']['price_currency'] is None
    assert r['stages']['market_cap_eligibility']['value'] is None


def test_catalog_only_row_is_retained_with_uncorroborated_ticker_identity():
    data=sample();data[1]['rows'][0]['submissions_evidence'].update(exact_ticker_match=False,observed_tickers=['OTHER'])
    r=run(data)
    assert len(r['rows'])==1 and r['rows'][0]['stages']['issuer_link']['state']=='CATALOG_ONLY'
    assert r['evaluation']['counts']['financial_rows']==1


@pytest.mark.parametrize('mutate,reason',[
    (lambda d:d[1]['rows'][0].update(ticker='OTHER'),'CANDIDATE_CROSSWALK_MISMATCH'),
    (lambda d:d[1]['rows'][0]['submissions_evidence'].update(sha256='e'*64),'SOURCE_REFERENCE_MISMATCH'),
    (lambda d:d[1]['rows'].append(deepcopy(d[1]['rows'][0])),'DUPLICATE_OBSERVATION_ID'),
    (lambda d:d[0]['financials']['0000000002'].update(cik='0000000003'),'CACHED_FINANCIAL_IDENTITY_MISMATCH'),
])
def test_link_errors_fail_closed_without_alias_inference(mutate,reason):
    data=sample();mutate(data)
    with pytest.raises(ValueError,match=reason):run(data)


def test_cached_metrics_untouched_and_no_financial_normalizer_or_scorer_called(monkeypatch):
    def forbidden(*a,**kw):raise AssertionError('UNAUTHORIZED_RECALCULATION')
    monkeypatch.setattr(pipeline.sec,'build_row',forbidden)
    monkeypatch.setattr(pipeline,'_common_scores',forbidden)
    data=sample();original=deepcopy(data)
    r=run(data)
    assert data==original
    assert r['financial_reuse']['raw_metrics_equal'] is True
    assert r['financial_reuse']['financial_records_recomputed']==0


def test_cli_verifies_input_hashes_and_writes_private_outputs(tmp_path):
    held,crosswalk,covers,sources,links=sample();inputs={}
    for key,value in dict(held=held,crosswalk=crosswalk,covers=covers,sources=sources,links=links).items():
        p=tmp_path/(key+'.json');b=json.dumps(value).encode();p.write_bytes(b)
        inputs[key]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest()}
    job=tmp_path/'job.json';job.write_text(json.dumps(dict(basis_date='2026-11-02',inputs=inputs)))
    tool=Path(__file__).parents[2]/'tools/current_evidence_bridge.py';out=tmp_path/'out'
    args=[sys.executable,str(tool),'--job',str(job),'--output-dir',str(out)]
    p=subprocess.run(args,capture_output=True,text=True)
    assert p.returncode==0 and p.stdout=='CURRENT_EVIDENCE_BRIDGE_WRITTEN\n' and p.stderr==''
    assert (out/'staged-evidence.json').stat().st_mode&0o777==0o600
    assert json.loads((out/'current-expansion.json').read_text())['counts']['candidate_rows']==1
    inputs['crosswalk']['sha256']='f'*64;job.write_text(json.dumps(dict(basis_date='2026-11-02',inputs=inputs)))
    args[-1]=str(tmp_path/'bad');failed=subprocess.run(args,capture_output=True,text=True)
    assert failed.returncode==1 and failed.stderr=='CURRENT_EVIDENCE_BRIDGE_FAILED\n'
