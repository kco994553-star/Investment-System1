from copy import deepcopy
import pytest
from investment_system.research.qgv_555_owner_inputs import (temporary_official_inputs,
    apply_reviewed_share_metrics, apply_reviewed_roa_fallback, apply_two_stage_share_review)
from investment_system.research.qgv_555 import catalog
from investment_system.research.sector_qgv import digest


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


def roa_fixture():
    s,share=share_fixture();record=share['source_contexts']['synthetic/source~1']['source_record']
    obs=dict(variant_id='roa_improvement_3y',formula_version='1',status='VALID',value=.05,
        unit='decimal',fiscal_period=dict(kind='FY_3Y',end='2025-12-31'),issuer_id='SYN:ISSUER',
        currency='USD',source_available_at=record['acquired_at'],retrieved_at=record['acquired_at'],
        provenance=['synthetic-companyfacts'],validation_basis='VERIFIED_COMPONENTS')
    r=dict(cache={digest(record):dict(record=record,source_sha256='c'*64,observation=obs)})
    return s,r


def apply_roa(s,r):
    return apply_reviewed_roa_fallback(s,r,review_sha256='e'*64,
        reviewed_at='2026-11-14T13:00:00Z',input_cutoff='2026-11-14T13:00:00Z')


def test_missing_roa_fallback_connects_existing_kernel_observation_and_period():
    s,r=roa_fixture();out,audit=apply_roa(s,r);metric='sector::roa_improvement_3y'
    assert out['rows'][0]['metrics'][metric]==.05 and audit[0]['adopted']
    proof=out['rows'][0]['metric_evidence'][metric]
    assert proof['period']['kind']=='FY_3Y' and proof['retrieved_at']=='2026-11-04T20:00:00Z'
    assert metric not in s['rows'][0]['metrics']


@pytest.mark.parametrize('case',['valid_primary','existing_roa','financial','invalid_observation'])
def test_roa_review_does_not_replace_primary_existing_value_or_financial_recipe(case):
    s,r=roa_fixture();row=s['rows'][0];metric='sector::roa_improvement_3y'
    if case=='valid_primary':
        row['metrics']['incremental_roic_3y']=.1
        row['metric_evidence']['incremental_roic_3y']=dict(status='VERIFIED',
            variant=catalog()['incremental_roic_3y']['variant'],source_refs=['synthetic'],
            available_at='2026-11-04T20:00:00Z')
    elif case=='existing_roa':row['metrics'][metric]=.15
    elif case=='financial':row['calculation_accounting_template']=None
    else:next(iter(r['cache'].values()))['observation']['status']='MISSING_INPUT'
    out,audit=apply_roa(s,r)
    assert not any(x['adopted'] for x in audit)
    assert out['rows'][0]['metrics'].get(metric)==(.15 if case=='existing_roa' else None)


def test_roa_review_rejects_wrong_source_context():
    s,r=roa_fixture();next(iter(r['cache'].values()))['source_sha256']='f'*64
    with pytest.raises(ValueError,match='SOURCE_CONTEXT'):apply_roa(s,r)


def two_stage_fixture():
    s,old_review=share_fixture()
    s,_=apply(s,old_review)
    review=deepcopy(old_review)
    x=review['source_contexts']['synthetic/source~1']
    x['adapter_version']='held-555-share-eligibility/2'
    x['source_input_cutoff']=x['source_record']['acquired_at']
    x['review_input_cutoff']='2026-11-14T13:00:00Z'
    formulas=dict(eps_cagr_3y='REPORTED_DILUTED_EPS_CAGR_3Y',
        fcf_per_share_cagr_3y='FCF_OVER_WEIGHTED_DILUTED_SHARES_CAGR_3Y',
        dilution_3y='WEIGHTED_DILUTED_SHARES_CAGR_3Y')
    x['metrics']={m:dict(raw_value=v,value=v,basis_status='VERIFIED',
        denominator_definition='WEIGHTED_AVERAGE_DILUTED_SHARES',
        formula_variant=formulas[m],
        stage1=dict(status='CONSISTENT'),
        stage2=dict(status='FINAL_ELIGIBLE',all_used_years_linked=True,
                    documented_common_basis=True,evidence_refs=['SYNTHETIC_EXPLICIT_COMMON_BASIS']),
        corporate_action=dict(status='UNKNOWN',adjustment_applied=False))
        for m,v in [('eps_cagr_3y',.12),('fcf_per_share_cagr_3y',.15),('dilution_3y',0)]}
    return s,review


def apply_two(s,r):
    return apply_two_stage_share_review(s,r,review_sha256='f'*64,
        reviewed_at='2026-11-14T14:00:00Z',input_cutoff='2026-11-14T14:00:00Z')


def test_two_stage_quarantines_every_old_proof_even_without_new_review():
    s,r=two_stage_fixture();prior=deepcopy(s)
    out,a=apply_two(s,dict(source_contexts={}))
    row=out['rows'][0]
    assert row['metrics']['eps_cagr_3y']==.12 and row['metrics']['dilution_3y']==0
    assert all(row['metric_evidence'][m]['status']=='QUARANTINED'
               for m in ('eps_cagr_3y','fcf_per_share_cagr_3y','dilution_3y'))
    assert all(row['metric_evidence'][m]['historical_share_basis']=='UNKNOWN'
               for m in ('eps_cagr_3y','fcf_per_share_cagr_3y','dilution_3y'))
    assert len(a)==3 and not any(x['adopted'] for x in a)
    assert s==prior and out['members']==s['members']


def test_two_stage_uses_individual_final_stage_and_preserves_zero_as_value():
    s,r=two_stage_fixture();claims=r['source_contexts']['synthetic/source~1']['metrics']
    claims['fcf_per_share_cagr_3y']['stage2']['status']='UNCONFIRMED_PERIOD_BASIS'
    out,a=apply_two(s,r);row=out['rows'][0]
    assert row['metric_evidence']['eps_cagr_3y']['share_eligibility_stage']=='FINAL_ELIGIBLE'
    assert row['metric_evidence']['dilution_3y']['historical_share_basis']=='VERIFIED'
    assert row['metrics']['dilution_3y']==0
    assert row['metric_evidence']['fcf_per_share_cagr_3y']['status']=='QUARANTINED'
    assert sum(x['adopted'] for x in a)==2
    p=row['metric_evidence']['eps_cagr_3y']
    assert p['available_at']=='2026-11-14T14:00:00Z'
    assert p['retrieved_at']=='2026-11-04T20:00:00Z'
    assert p['validation_stages']['final_eligibility']=='FINAL_ELIGIBLE'
    assert p['denominator_definition']=='WEIGHTED_AVERAGE_DILUTED_SHARES'
    assert 'evidence_refs' not in p['validation_stages']
    assert '/source_contexts/synthetic~1source~01/' in p['source_refs'][0]


@pytest.mark.parametrize('status',['CONSISTENT','SPLIT_CANDIDATE'])
def test_cross_filing_consistency_or_ratio_candidate_alone_is_not_final(status):
    s,r=two_stage_fixture()
    for c in r['source_contexts']['synthetic/source~1']['metrics'].values():
        c['stage1']['status']=status
        c['stage2']=dict(status='UNCONFIRMED_PERIOD_BASIS')
        c['corporate_action']=dict(status='CANDIDATE',adjustment_applied=False)
    out,a=apply_two(s,r)
    assert not any(x['adopted'] for x in a)
    assert all(p['status']=='QUARANTINED' for p in out['rows'][0]['metric_evidence'].values()
               if p.get('two_stage_review_version'))


@pytest.mark.parametrize('field',['all_used_years_linked','documented_common_basis','evidence_refs'])
def test_final_label_without_complete_period_evidence_is_rejected(field):
    s,r=two_stage_fixture();c=r['source_contexts']['synthetic/source~1']['metrics']['eps_cagr_3y']
    c['stage2'].pop(field)
    with pytest.raises(ValueError,match='FINAL_EVIDENCE'):apply_two(s,r)


@pytest.mark.parametrize('case',['basic','actual','wrong_formula','unverified'])
def test_two_stage_metric_requires_its_exact_existing_denominator_and_formula(case):
    s,r=two_stage_fixture();c=r['source_contexts']['synthetic/source~1']['metrics']['eps_cagr_3y']
    if case=='basic':c['denominator_definition']='WEIGHTED_AVERAGE_BASIC_SHARES'
    elif case=='actual':c['denominator_definition']='END_OF_PERIOD_ACTUAL_SHARES'
    elif case=='wrong_formula':c['formula_variant']='FCF_OVER_WEIGHTED_DILUTED_SHARES_CAGR_3Y'
    else:c['basis_status']='UNKNOWN'
    with pytest.raises(ValueError,match='METRIC_DEFINITION|FINAL_EVIDENCE'):apply_two(s,r)


def test_confirmed_adjustment_is_not_reapplied_to_an_already_adjusted_value():
    s,r=two_stage_fixture();c=r['source_contexts']['synthetic/source~1']['metrics']['eps_cagr_3y']
    c.update(value=.25,corporate_action=dict(status='CONFIRMED',adjustment_applied=True,
                                           evidence_refs=['SYNTHETIC_RETROSPECTIVE_ADJUSTMENT']))
    out,a=apply_two(s,r)
    assert out['rows'][0]['metrics']['eps_cagr_3y']==.25
    assert next(x for x in a if x['metric']=='eps_cagr_3y')['corporate_action']['adjustment_applied']
    c['corporate_action']['status']='CANDIDATE'
    with pytest.raises(ValueError,match='UNCONFIRMED_ADJUSTMENT'):apply_two(s,r)


def test_two_stage_proof_stays_reference_only_for_financial_and_domain_none():
    s,r=two_stage_fixture();s['rows'][0]['calculation_accounting_template']=None
    out,a=apply_two(s,r)
    assert not any(x['adopted'] for x in a)
    assert {x['reason'] for x in a}=={'FINANCIAL_REFERENCE_ONLY'}
    s['rows'][0]['calculation_accounting_template']='GENERAL'
    r['source_contexts']['synthetic/source~1']['metrics']['eps_cagr_3y']['value']=None
    out,a=apply_two(s,r)
    assert not next(x for x in a if x['metric']=='eps_cagr_3y')['adopted']


@pytest.mark.parametrize('case',['version','hash','row_source','acquired','duplicate'])
def test_two_stage_source_context_mismatch_never_adopts(case):
    s,r=two_stage_fixture();c=r['source_contexts']['synthetic/source~1']
    if case=='version':c['adapter_version']='held-555-cross-filing-share-review/1'
    elif case=='hash':c['source_sha256']='e'*64
    elif case=='row_source':s['rows'][0]['owner_source_context']['companyfacts_sha256']='e'*64
    elif case=='acquired':s['rows'][0]['owner_source_context']['acquired_at']='2026-11-04T21:00:00Z'
    else:r['source_contexts']['duplicate']=deepcopy(c)
    with pytest.raises(ValueError):apply_two(s,r)


@pytest.mark.parametrize('case',['future','future_offset','source_mismatch','missing_source','missing_review'])
def test_source_review_clock_cannot_be_relabelled_as_an_earlier_review(case):
    s,r=two_stage_fixture();c=r['source_contexts']['synthetic/source~1']
    if case=='future':c['review_input_cutoff']='2026-11-14T14:00:00.000001Z'
    elif case=='future_offset':c['review_input_cutoff']='2026-11-14T15:00:01+01:00'
    elif case=='source_mismatch':c['source_input_cutoff']='2026-11-04T20:00:01Z'
    elif case=='missing_source':c.pop('source_input_cutoff')
    else:c.pop('review_input_cutoff')
    with pytest.raises(ValueError,match='REVIEW_CLOCK'):apply_two(s,r)


def test_review_clock_utc_equivalent_instant_is_preserved_without_retiming_source():
    s,r=two_stage_fixture();c=r['source_contexts']['synthetic/source~1']
    c['source_input_cutoff']='2026-11-04T21:00:00+01:00'
    c['review_input_cutoff']='2026-11-14T15:00:00+01:00'
    out,a=apply_two(s,r)
    assert sum(x['adopted'] for x in a)==3
    assert out['rows'][0]['metric_evidence']['eps_cagr_3y']['retrieved_at']=='2026-11-04T20:00:00Z'
