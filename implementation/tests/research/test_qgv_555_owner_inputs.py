from copy import deepcopy
import pytest
from investment_system.research.qgv_555_owner_inputs import temporary_official_inputs, apply_reviewed_share_metrics


def fixture(template=None, profile='GENERAL'):
    row = dict(company_id='SYN:ROW', issuer_id='SYN:ISSUER', security_id=None,
        accounting_template=template, sector_id='FINANCIALS' if template == 'EQUITY_REIT' else None,
        classification_status='UNKNOWN' if template is None else 'VERIFIED',
        metrics={}, metric_evidence={}, industry_group='synthetic-industry')
    snapshot = dict(rows=[row], members=['SYN:ROW'], input_cutoff='2026-11-04T22:00:00Z',
        evaluation_day='2026-11-04', source_anchors=[])
    original = dict(valuation_date='2026-11-04', rows=[dict(company_id='SYN:ROW',
        issuer_id='SYN:ISSUER', sector_id=None, component_mappings={})])
    record = dict(cik='SYN:ISSUER', acquired_at='2026-11-04T20:00:00Z', state='LIVE',
        calc_version='qgv2-calc/2026-10-23.1', profile=profile, sic='9999',
        industry_group='synthetic-industry', fiscal_year_end='2025-12-31', currency='USD',
        metrics={'roic': .2, 'eps_cagr_3y': .3}, axes={'Q': {'score': 80}, 'G': {'score': 70}},
        factors={'synthetic-official-factor': {'score': 50}})
    record['source_sha256']={'companyfacts':'c'*64}
    sources = [dict(sha256='a'*64, records_key='financials', records={'issuer~/1': record})]
    return snapshot, original, sources


def run(s,o,src):
    return temporary_official_inputs(s,src,original_snapshot=o,original_snapshot_sha256='b'*64,
        reviewed_at='2026-11-14T12:00:00Z',input_cutoff='2026-11-14T12:00:00Z')


def test_unknown_official_general_restores_raw_without_inventing_common_sector():
    s,o,src=fixture();before=deepcopy(s);out,a=run(s,o,src);r=out['rows'][0]
    assert r['accounting_template'] is None and r['calculation_accounting_template']=='GENERAL'
    assert r['sector_id'] is None and r['calculation_sector_id'] is None
    assert r['temporary_classification']['status']=='TEMPORARY_OFFICIAL_PROFILE'
    assert r['metrics']['roic']==.2
    assert r['metric_evidence']['eps_cagr_3y']['historical_share_basis']=='UNKNOWN'
    assert '/financials/issuer~0~11/metrics/roic' in r['metric_evidence']['roic']['source_refs'][0]
    assert s==before and out['members']==s['members']


def test_reit_uses_general_calculation_but_keeps_original_template_and_label():
    s,o,src=fixture('EQUITY_REIT');out,a=run(s,o,src);r=out['rows'][0]
    assert r['accounting_template']=='EQUITY_REIT' and r['calculation_accounting_template']=='GENERAL'
    assert r['temporary_classification']['label']=='REIT 임시(일반기업 식)'
    assert r['calculation_sector_id']=='FINANCIALS' and r['metrics']['roic']==.2


def test_financial_is_reference_only_not_a_555_general_recipe():
    s,o,src=fixture('BANK','FINANCIAL');out,a=run(s,o,src);r=out['rows'][0]
    assert r['calculation_accounting_template'] is None and not r['metrics']
    assert r['accounting_template']=='BANK'
    assert r['financial_reference']['profile']=='FINANCIAL'
    assert r['financial_reference']['axes']['Q']['score']==80
    assert not r['financial_reference']['counts_as_555']


def test_confirmed_sector_component_restored_independently_of_accounting():
    s,o,src=fixture();old=o['rows'][0];old['sector_id']='INDUSTRIALS'
    old['component_mappings']={'sector': {'rule_id':'synthetic-rule','evidence_refs':['synthetic-source']}}
    out,a=run(s,o,src);r=out['rows'][0]
    assert r['sector_id'] is None and r['calculation_sector_id']=='INDUSTRIALS'
    assert a[0]['restored_sector'] and r['calculation_sector_evidence']['status']=='CONFIRMED_COMPONENT_REUSED'
    old['component_mappings']['sector']['evidence_refs']=[]
    assert run(s,o,src)[0]['rows'][0]['calculation_sector_id'] is None


def test_existing_general_repair_not_overwritten_and_future_source_not_used():
    s,o,src=fixture('GENERAL');s['rows'][0]['metrics']['roic']=.25
    out,a=run(s,o,src)
    assert out['rows'][0]['metrics']['roic']==.25
    src[0]['records']['issuer~/1']['acquired_at']='2026-11-05T00:00:00Z'
    out,a=run(s,o,src)
    assert out['rows'][0]['temporary_classification']['status']=='UNCONFIRMED'
    assert out['rows'][0]['metrics']['roic']==.25


@pytest.mark.parametrize('case',['members','issuer','date','review'])
def test_original_population_identity_and_context_must_match(case):
    s,o,src=fixture()
    if case=='members':o['rows']=[]
    elif case=='issuer':o['rows'][0]['issuer_id']='OTHER'
    elif case=='date':o['valuation_date']='2026-11-03'
    else:s['input_cutoff']='2027-01-01T00:00:00Z'
    with pytest.raises(ValueError):run(s,o,src)


def share_fixture():
    s,o,src=fixture();s,_=run(s,o,src);record=deepcopy(src[0]['records']['issuer~/1'])
    review=dict(source_sha256='c'*64,source_record=record,metrics={
        'eps_cagr_3y':dict(value=.12,basis_status='VERIFIED'),
        'fcf_per_share_cagr_3y':dict(value=.15,basis_status='UNKNOWN',reason='UNLINKED_BASIS'),
        'dilution_3y':dict(value=0,basis_status='ADJUSTED')})
    return s,dict(source_contexts={'synthetic/source~1':review})


def apply(s,r):
    return apply_reviewed_share_metrics(s,r,review_sha256='d'*64,
        reviewed_at='2026-11-14T13:00:00Z',input_cutoff='2026-11-14T13:00:00Z')


def test_share_adoption_is_per_metric_and_preserves_review_and_acquisition_times():
    s,r=share_fixture();prior=deepcopy(s);out,audit=apply(s,r);row=out['rows'][0]
    assert row['metrics']['eps_cagr_3y']==.12 and row['metrics']['dilution_3y']==0
    assert row['metric_evidence']['eps_cagr_3y']['historical_share_basis']=='VERIFIED'
    assert row['metric_evidence']['dilution_3y']['historical_share_review_status']=='ADJUSTED'
    assert 'fcf_per_share_cagr_3y' not in row['metrics']
    assert sum(x['adopted'] for x in audit)==2 and s==prior
    proof=row['metric_evidence']['eps_cagr_3y']
    assert '/source_contexts/synthetic~1source~01/' in proof['source_refs'][0]
    assert proof['available_at']=='2026-11-14T13:00:00Z'
    assert proof['retrieved_at']=='2026-11-04T20:00:00Z'


def test_share_proof_does_not_activate_financial_recipe_or_invalid_numeric():
    s,r=share_fixture();s['rows'][0]['calculation_accounting_template']=None
    out,audit=apply(s,r)
    assert not audit and out['rows'][0]['metric_evidence']['eps_cagr_3y']['historical_share_basis']=='UNKNOWN'
    s['rows'][0]['calculation_accounting_template']='GENERAL'
    r['source_contexts']['synthetic/source~1']['metrics']['eps_cagr_3y']['value']=None
    out,audit=apply(s,r)
    assert not next(x for x in audit if x['metric']=='eps_cagr_3y')['adopted']


def test_unlinked_share_review_remains_three_explicit_unknowns():
    s,r=share_fixture();r['source_contexts']={}
    out,audit=apply(s,r)
    assert len(audit)==3 and not any(x['adopted'] for x in audit)
    assert {x['reason'] for x in audit}=={'REVIEW_SOURCE_CONTEXT_NOT_LINKED'}
    assert out['rows'][0]['metric_evidence']['eps_cagr_3y']['historical_share_basis']=='UNKNOWN'


@pytest.mark.parametrize('case',['source_hash','row_hash','acquired','duplicate'])
def test_share_context_mismatch_is_not_accepted(case):
    s,r=share_fixture();review=r['source_contexts']['synthetic/source~1']
    if case=='source_hash':review['source_sha256']='e'*64
    elif case=='row_hash':s['rows'][0]['owner_source_context']['companyfacts_sha256']='e'*64
    elif case=='acquired':s['rows'][0]['owner_source_context']['acquired_at']='2026-11-04T21:00:00Z'
    else:r['source_contexts']['duplicate']=deepcopy(review)
    with pytest.raises(ValueError):apply(s,r)
