from copy import deepcopy
import pytest
from investment_system.research.qgv_555 import fixture,SHARE_METRICS
from investment_system.research.qgv_555_official_inputs import apply_official_share_reuse
from investment_system.research.qgv_555_official_share import FORMULAS
from investment_system.research.sector_qgv import digest


def source():
    s,_=fixture(1);s['input_cutoff']='2026-11-14T00:00:00Z'
    row=s['rows'][0];row['calculation_accounting_template']='GENERAL'
    rec=dict(cik=row['issuer_id'],acquired_at='2026-11-03T12:00:00Z',currency='USD',
        fiscal_year_end='2025-12-31',calc_version='qgv2-calc/2026-10-23.1',
        source_sha256=dict(companyfacts='a'*64))
    row['owner_source_context']=dict(record_hash=digest(rec),companyfacts_sha256='a'*64,
        acquired_at=rec['acquired_at'],fiscal_year_end=rec['fiscal_year_end'])
    review=dict(adapter_version='held-555-official-share-reuse/1',issuer_id=rec['cik'],
        source_record=rec,source_sha256='a'*64,source_input_cutoff=rec['acquired_at'],
        review_input_cutoff='2026-11-14T01:00:00Z',metrics={m:dict(value=0.,
            adoption_basis='EVIDENCE_LINKED',strict_verified=False,requires_assumption=False,
            evidence_only_eligible=True,allowed_assumptions=[],formula_source='EXISTING_OFFICIAL_KERNEL',
            denominator_definition='WEIGHTED_AVERAGE_DILUTED_SHARES',formula_variant=FORMULAS[m]) for m in SHARE_METRICS})
    file=dict(adapter_version=review['adapter_version'],reviewed_at='2026-11-14T01:00:00Z',source_contexts={'synthetic/source~1':review})
    return s,file


def apply(s,file):return apply_official_share_reuse(s,file,review_sha256='b'*64,
    reviewed_at='2026-11-14T02:00:00Z',input_cutoff='2026-11-14T02:00:00Z')


def test_zero_adopted_with_explicit_research_label_and_original_preserved():
    s,file=source();prior=deepcopy(s);out,audit=apply(s,file)
    assert s==prior and out['rows'][0]['metrics']['eps_cagr_3y']==0
    assert all(a['adopted'] and a['evidence_only_adoptable'] for a in audit)
    p=out['rows'][0]['metric_evidence']['eps_cagr_3y']
    assert p['status']=='RESEARCH_USABLE' and p['strict_verified'] is False
    assert 'synthetic~1source~01' in p['source_refs'][0]
    for key in ('gate','security_id','accounting_template','industry_group'):
        assert out['rows'][0][key]==s['rows'][0][key]
    assert out['members']==s['members'] and out['evaluation_day']==s['evaluation_day']


@pytest.mark.parametrize('basis',['ADDITIONAL_VERIFICATION_REQUIRED','EXPLICIT_CONFLICT_EXCLUDED'])
def test_rejected_source_cannot_reactivate_finite_legacy_value(basis):
    s,file=source()
    for m in SHARE_METRICS:file['source_contexts']['synthetic/source~1']['metrics'][m].update(
        adoption_basis=basis,evidence_only_eligible=False)
    out,audit=apply(s,file)
    assert not any(a['adopted'] for a in audit)
    assert out['rows'][0]['metrics']==s['rows'][0]['metrics']
    assert out['rows'][0]['metric_evidence']['eps_cagr_3y']['status']=='QUARANTINED'


def test_assumption_scope_is_separate_and_does_not_claim_strict_or_price_verification():
    s,file=source()
    for m in SHARE_METRICS:file['source_contexts']['synthetic/source~1']['metrics'][m].update(
        adoption_basis='OFFICIAL_ASSUMPTION_INHERITED',requires_assumption=True,
        evidence_only_eligible=False,allowed_assumptions=['NO_OVERLAP_FACTOR_ONE'])
    out,audit=apply(s,file)
    assert all(a['adopted'] and not a['evidence_only_adoptable'] for a in audit)
    assert not out['rows'][0]['metric_evidence']['eps_cagr_3y']['verifies_valuation_security']
    assert out['rows'][0]['security_id']==s['rows'][0]['security_id']


@pytest.mark.parametrize('change,reason',[
    ('future','SOURCE_CLOCK'),('wrong_acquired','SOURCE_CLOCK'),('wrong_body','SOURCE_IDENTITY'),
    ('wrong_record_issuer','ROW_IDENTITY'),('strict_true','METRIC_DEFINITION'),
    ('false_evidence','ASSUMPTION_IDENTITY'),('actual_shares','METRIC_DEFINITION')])
def test_source_scope_clocks_and_denominator_cannot_be_relabelled(change,reason):
    s,file=source();r=file['source_contexts']['synthetic/source~1']
    if change=='future':r['review_input_cutoff']='2026-11-14T02:00:00.000001Z'
    elif change=='wrong_acquired':r['source_input_cutoff']='2026-11-03T12:00:01Z'
    elif change=='wrong_body':r['source_sha256']='c'*64
    elif change=='wrong_record_issuer':s['rows'][0]['issuer_id']='different-issuer'
    elif change=='strict_true':r['metrics']['eps_cagr_3y']['strict_verified']=True
    elif change=='false_evidence':r['metrics']['eps_cagr_3y'].update(requires_assumption=True,
        allowed_assumptions=['NO_OVERLAP_FACTOR_ONE'])
    else:r['metrics']['eps_cagr_3y']['denominator_definition']='ACTUAL_OUTSTANDING'
    with pytest.raises(ValueError,match=reason):apply(s,file)


def test_financial_stays_reference_only_and_missing_claims_remain_unknown():
    s,file=source();s['rows'][0]['calculation_accounting_template']=None
    out,audit=apply(s,file)
    assert not any(a['adopted'] for a in audit)
    assert {a['reason'] for a in audit}=={'FINANCIAL_REFERENCE_ONLY'}
    s,file=source();file['source_contexts']={}
    out,audit=apply(s,file)
    assert not any(a['adopted'] for a in audit)
    assert {a['reason'] for a in audit}=={'REVIEW_SOURCE_CONTEXT_NOT_LINKED'}


def test_additional_verification_flag_and_specific_reasons_survive_bridge():
    s,file=source()
    for m in SHARE_METRICS:file['source_contexts']['synthetic/source~1']['metrics'][m].update(
        additional_verification_required=True,
        additional_verification=['SHARE_CLASS_CONTEXT_NOT_RETAINED','SOURCE_PRECISION_NOT_RETAINED'])
    out,_=apply(s,file);p=out['rows'][0]['metric_evidence']['eps_cagr_3y']
    assert p['additional_verification_required'] is True
    assert p['additional_verification']==['SHARE_CLASS_CONTEXT_NOT_RETAINED','SOURCE_PRECISION_NOT_RETAINED']


def test_different_formula_cannot_be_relabelled_as_eps():
    s,file=source()
    file['source_contexts']['synthetic/source~1']['metrics']['eps_cagr_3y']['formula_variant']=FORMULAS['fcf_per_share_cagr_3y']
    with pytest.raises(ValueError,match='METRIC_DEFINITION'):apply(s,file)
