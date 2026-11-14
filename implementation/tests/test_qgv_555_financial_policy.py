from copy import deepcopy
import hashlib
import pytest
from investment_system.research.qgv_555 import configuration,fixture,run,validate_configuration
from investment_system.research.qgv_555_financial_temporary import financial_catalog
from investment_system.research.qgv_555_additional import attach
from investment_system.research.qgv_555_delivery import artifacts,validate
from investment_system.research.dual_qgv import json_bytes


def inputs(template='BANK',sector='FINANCIALS'):
    e,r=fixture(10)
    for s in (e,r):
        for i,row in enumerate(s['rows']):
            row.update(accounting_template=template,sector_id=sector,
                calculation_accounting_template=None,calculation_sector_id=sector,
                calculation_industry_group='bank',financial_calculation_profile='FINANCIAL',
                financial_peer_template=template,
                financial_temporary_policy='official-financial-role-bridge/1',
                financial_temporary_source_refs=['SYNTHETIC_FINANCIAL_SOURCE'],
                owner_source_context=dict(profile='FINANCIAL',record_hash='a'*64,companyfacts_sha256='b'*64,
                    acquired_at='2026-11-03T12:00:00Z'),
                classification_status='VERIFIED',classification_record_id='synthetic-peer',
                classification_mapping=dict(common_record_id='synthetic-peer',evidence_refs=['SYNTHETIC_CLASS'],
                    common_dictionary_version='common-industry-dictionary/2',common_mapping_version='common-classification-map/2',
                    common_classification_hash='a'*64,valid_from='2026-11-04',valid_to='2026-11-05',knowledge_as_of='2026-11-04T20:00:00Z'),
                financial_reference=dict(axes=dict(Q=99,G=99),counts_as_555=False))
            for key,spec in financial_catalog().items():
                row['metrics'][key]=(i+1)/10
                proof=dict(status='TEMPORARY_OFFICIAL_FINANCIAL_RAW',variant=spec['variant'],
                    financial_temporary_policy='official-financial-role-bridge/1',
                    source_record_hash='a'*64,source_body_sha256='b'*64,
                    source_formula_version='qgv2-calc/2026-10-23.1',source_metric=spec['source_metric'],
                    raw_reusable=True,source_refs=['SYNTHETIC_FINANCIAL_SOURCE'],available_at=s['input_cutoff'],
                    reviewed_at=s['input_cutoff'],source_available_at='2026-11-03T12:00:00Z',retrieved_at='2026-11-03T12:00:00Z')
                if spec['historical_share_evidence_required']:
                    proof.update(official_share_reuse_version='held-555-official-share-reuse/1',
                        historical_share_basis='OFFICIAL_PATH_REUSED',adoption_basis='EVIDENCE_LINKED',
                        requires_assumption=False,allowed_assumptions=[],evidence_only_eligible=True,
                        strict_verified=False,denominator_definition='WEIGHTED_AVERAGE_DILUTED_SHARES',
                        formula_variant={'eps_cagr_3y':'REPORTED_DILUTED_EPS_CAGR_3Y',
                         'dilution_3y':'WEIGHTED_DILUTED_SHARES_CAGR_3Y',
                         'book_value_per_share_cagr_3y':'OFFICIAL_EQUITY_OVER_WEIGHTED_DILUTED_SHARES_CAGR_3Y'}[spec['source_metric']])
                row['metric_evidence'][key]=proof
    return e,r


def test_temporary_financial_is_new_version_and_unsupported_roles_stay_null():
    c=configuration('U1-555',version='0.5.0');e,r=inputs();out=run(c,e,r);row=out['rows'][4]
    assert c['model_id']=='unified-555-financial-temporary/0.5.0'
    assert row['axes']['Q']['score'] is not None and row['axes']['G']['score'] is not None
    assert row['axes']['Q']['score']!=99
    assert row['roles']['q_earnings_quality']['score'] is None
    assert row['roles']['q_earnings_quality']['metrics']==[]
    assert all(row['roles'][k]['score'] is None for k in row['roles'] if k.startswith('v_'))
    assert row['axes']['Q']['weight_available']==.8
    assert row['financial_calculation_profile']=='FINANCIAL' and row['peer_accounting_template']=='BANK'
    assert 'TEMPORARY_OFFICIAL_FINANCIAL' in row['display_flags']
    rc=row['financial_temporary_contributions']['role_contributions']
    assert rc['q_profitability']['within_axis_nominal']==.25
    assert rc['q_profitability']['within_axis_effective']==.3125
    assert rc['q_earnings_quality']['within_axis_nominal']==.2
    assert rc['q_earnings_quality']['effective']==0
    assert not row['fifteen_roles_complete'] and out['coverage']['eligible_total']==0
    assert out['coverage']['role_stages']['q_earnings_quality']['raw_all']==0
    assert out['coverage']['role_stages']['v_earnings_yield']['raw_all']==0
    assert run(configuration('U1-555',version='0.4.0'),e,r)['coverage']['axes']['Q']==0


def test_s1_requires_confirmed_peer_model_and_preserves_general_configuration():
    e,r=inputs(template=None);u=run(configuration('U1-555',version='0.5.0'),e,r)
    s=run(configuration('S1-555',version='0.5.0'),e,r)
    assert u['coverage']['axes']['Q']==10 and s['coverage']['axes']['Q']==0
    assert s['rows'][0]['status']=='FINANCIAL_PEER_MODEL_UNCONFIRMED'
    e,r=fixture(10);c=configuration('U1-555',version='0.5.0');out=run(c,e,r)
    assert out['rows'][0]['roles']['q_earnings_quality']['metrics']
    assert out['rows'][0].get('financial_temporary_contributions') is None


def test_financial_peer_groups_are_not_merged_to_reach_minimum():
    e,r=inputs()
    for s in (e,r):
        for row in s['rows'][5:]:row.update(accounting_template='INSURANCE',financial_peer_template='INSURANCE')
    out=run(configuration('S1-555',version='0.5.0'),e,r)
    assert out['coverage']['axes']['Q']==0
    assert out['rows'][0]['roles']['q_profitability']['metrics'][0]['reference_n']==5


def test_evidence_only_applies_to_financial_eps_bvps_and_dilution_separately():
    e,r=inputs();c=configuration('U1-555',version='0.5.0');c['share_evidence_scope']='EVIDENCE_ONLY'
    for s in (e,r):
        for row in s['rows']:
            p=row['metric_evidence']['financial::book_value_per_share_cagr_3y']
            p.update(adoption_basis='OFFICIAL_ASSUMPTION_INHERITED',requires_assumption=True,
                allowed_assumptions=['NO_OVERLAP_FACTOR_ONE'],evidence_only_eligible=False)
    role=run(c,e,r)['rows'][0]['roles']['g_per_share_growth']
    assert role['score'] is not None
    nodes={m['metric']:m for m in role['metrics']}
    assert nodes['financial::eps_cagr_3y']['score'] is not None
    assert nodes['financial::book_value_per_share_cagr_3y']['score'] is None


def test_duplicate_mapping_or_policy_downgrade_is_rejected():
    c=configuration('U1-555',version='0.5.0')
    bad=deepcopy(c);bad['financial_roles']['g_growth_efficiency']['metrics']={'financial::roe':1}
    with pytest.raises(ValueError):validate_configuration(bad)
    old=configuration('U1-555',version='0.4.0');old['financial_temporary_policy']=c['financial_temporary_policy']
    with pytest.raises(ValueError):validate_configuration(old)


@pytest.mark.parametrize('field',['source_record_hash','source_body_sha256'])
def test_different_record_or_body_cannot_supply_financial_raw(field):
    e,r=inputs();c=configuration('U1-555',version='0.5.0')
    for key in financial_catalog():e['rows'][0]['metric_evidence'][key][field]='c'*64
    row=run(c,e,r)['rows'][0]
    assert row['axes']['Q']['score'] is None and row['axes']['G']['score'] is None
    assert row['roles']['q_profitability']['metrics'][0]['reason']=='FINANCIAL_RAW_SOURCE_UNVERIFIED'


def test_temporary_financial_projects_full_delivery_and_general_scores_are_unchanged():
    e,r=inputs();c=configuration('U1-555',version='0.5.0');core=run(c,e,r);out=attach(core,e,r)
    files=artifacts({'U1-555':out},data_kind='SYNTHETIC')
    pin=hashlib.sha256(json_bytes(files['manifest.json'])).hexdigest()
    assert validate(files,manifest_sha256=pin,expected_evaluation=out['evaluation'],expected_references={'U1-555':out['reference']})
    assert out['rows'][0]['factors']['financial::roe']['extra_score_contribution']==0
    assert out['rows'][0]['factors']['financial::roe']['reference_n']==10
    e,r=fixture(10)
    before=run(configuration('U1-555',version='0.4.0'),e,r)
    after=run(c,e,r)
    for a,b in zip(before['rows'],after['rows']):
        assert a['axes']==b['axes'] and a['roles']==b['roles'] and a['total']==b['total']


@pytest.mark.parametrize('change',['missing_hashes','future_source_clock'])
def test_direct_financial_inputs_need_real_pins_and_separate_bounded_clocks(change):
    e,r=inputs()
    for row in e['rows']:
        if change=='missing_hashes':
            row['owner_source_context'].pop('record_hash');row['owner_source_context'].pop('companyfacts_sha256')
            for key in financial_catalog():
                row['metric_evidence'][key].pop('source_record_hash');row['metric_evidence'][key].pop('source_body_sha256')
        else:
            row['owner_source_context']['acquired_at']='2030-01-01T00:00:00Z'
            for key in financial_catalog():
                row['metric_evidence'][key].update(source_available_at='2030-01-01T00:00:00Z',
                    retrieved_at='2030-01-01T00:00:00Z',reviewed_at='2030-01-01T00:00:00Z')
    out=run(configuration('U1-555',version='0.5.0'),e,r)
    assert out['coverage']['axes']==dict(Q=0,G=0,V=0)


@pytest.mark.parametrize('change',['unverified','future_mapping','wrong_hash'])
def test_s1_peer_label_needs_verified_current_mapping(change):
    e,r=inputs()
    for s in (e,r):
        for row in s['rows']:
            if change=='unverified':row['classification_status']='UNKNOWN'
            elif change=='future_mapping':row['classification_mapping']['valid_from']='2027-01-01'
            else:row['classification_mapping']['common_classification_hash']='c'*64
    out=run(configuration('S1-555',version='0.5.0'),e,r)
    assert out['coverage']['axes']['Q']==0
    assert out['rows'][0]['status']=='FINANCIAL_PEER_MODEL_UNCONFIRMED'


def test_financial_code_rows_and_unique_issuers_remain_separate():
    e,r=inputs()
    for s in (e,r):
        alt=deepcopy(s['rows'][0]);alt['company_id']='SYN:SECOND-CLASS';alt['security_id']='synthetic-second-class'
        s['rows'].append(alt);s['members'].append(alt['company_id'])
    out=run(configuration('U1-555',version='0.5.0'),e,r)
    assert len(out['rows'])==11 and out['coverage']['denominator']==10
    assert out['coverage']['financial_temporary_issuers']==10
    assert out['coverage']['financial_temporary_code_rows']==11
