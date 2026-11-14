"""Synthetic official-raw reuse never means copying official scores or strict proof."""
from copy import deepcopy
import hashlib
import pytest
from investment_system.research.qgv_555 import configuration, fixture, run, replay, validate_configuration, SHARE_METRICS
from investment_system.research.qgv_555_additional import attach
from investment_system.research.qgv_555_official_share import FORMULAS
from investment_system.research.qgv_555_delivery import artifacts,validate
from investment_system.research.dual_qgv import json_bytes


def inputs():
    e,r=fixture(10)
    for s in (e,r):
        for row in s['rows']:
            for m in SHARE_METRICS:
                row['metric_evidence'][m].update(status='RESEARCH_USABLE',
                    historical_share_basis='OFFICIAL_PATH_REUSED',
                    official_share_reuse_version='held-555-official-share-reuse/1',
                    adoption_basis='EVIDENCE_LINKED',requires_assumption=False,
                    evidence_only_eligible=True,allowed_assumptions=[],strict_verified=False,
                    formula_variant=FORMULAS[m])
    return e,r


def test_separate_version_and_coverage_scope_preserve_older_policies():
    c=configuration('U1-555',version='0.4.0')
    assert c['model_id']=='unified-555/0.4.0'
    assert c['historical_share_policy']=='official-kernel-share-reuse/1'
    assert c['share_evidence_scope']=='ALL_OFFICIAL_REUSE'
    c['share_evidence_scope']='EVIDENCE_ONLY';validate_configuration(c)
    c['share_evidence_scope']='UNKNOWN'
    with pytest.raises(ValueError,match='SHARE_EVIDENCE_SCOPE'):validate_configuration(c)
    for v in ('0.1.0','0.2.0','0.3.0'):
        prior=configuration('U1-555',version=v)
        assert 'share_evidence_scope' not in prior
        prior['share_evidence_scope']='ALL_OFFICIAL_REUSE'
        with pytest.raises(ValueError,match='SHARE_EVIDENCE_SCOPE'):validate_configuration(prior)


def test_official_assumptions_are_usable_only_in_explicit_research_scope():
    e,r=inputs();c=configuration('U1-555',version='0.4.0')
    for s in (e,r):
        for row in s['rows']:
            for m in SHARE_METRICS:
                row['metric_evidence'][m].update(adoption_basis='OFFICIAL_ASSUMPTION_INHERITED',
                    requires_assumption=True,evidence_only_eligible=False,
                    allowed_assumptions=['NO_OVERLAP_NO_SPLIT_FACT_FACTOR_ONE'])
    a=run(c,e,r)
    assert a['rows'][0]['roles']['g_per_share_growth']['score'] is not None
    m=a['rows'][0]['roles']['g_per_share_growth']['metrics'][0]
    assert m['share_validation']['strict_verified'] is False
    assert m['share_validation']['requires_assumption'] is True
    c['share_evidence_scope']='EVIDENCE_ONLY';b=run(c,e,r)
    assert b['rows'][0]['roles']['g_per_share_growth']['score'] is None
    assert {m['reason'] for m in b['rows'][0]['roles']['g_per_share_growth']['metrics']}=={'OFFICIAL_ASSUMPTION_NOT_IN_EVIDENCE_ONLY'}
    assert a['configuration']!=b['configuration'] and a['result_hash']!=b['result_hash']


@pytest.mark.parametrize('basis',['ADDITIONAL_VERIFICATION_REQUIRED','EXPLICIT_CONFLICT_EXCLUDED'])
def test_rejected_claim_cannot_be_reused_even_with_an_old_finite_value(basis):
    e,r=inputs();c=configuration('U1-555',version='0.4.0')
    for m in SHARE_METRICS:e['rows'][0]['metric_evidence'][m]['adoption_basis']=basis
    out=run(c,e,r);role=out['rows'][0]['roles']['g_per_share_growth']
    assert role['score'] is None
    assert {m['reason'] for m in role['metrics']}=={basis}
    extra=attach(out,e,r)
    assert extra['rows'][0]['factors']['eps_cagr_3y']['score'] is None


def test_reference_filter_is_applied_before_new_555_scoring():
    e,r=inputs();c=configuration('U1-555',version='0.4.0')
    for m in SHARE_METRICS:r['rows'][-1]['metric_evidence'][m].update(
        adoption_basis='OFFICIAL_ASSUMPTION_INHERITED',requires_assumption=True,
        evidence_only_eligible=False,allowed_assumptions=['NO_OVERLAP_NO_SPLIT_FACT_FACTOR_ONE'])
    a=run(c,e,r);c['share_evidence_scope']='EVIDENCE_ONLY';b=run(c,e,r)
    ma=a['rows'][4]['roles']['g_per_share_growth']['metrics'][0]
    mb=b['rows'][4]['roles']['g_per_share_growth']['metrics'][0]
    assert ma['reference_n']==10 and mb['reference_n']==9
    assert ma['score']!=mb['score']
    assert b['rows'][0]['roles']['g_per_share_growth']['score'] is not None


def test_prior_strict_claim_is_not_implicitly_official_reuse_and_price_gate_remains():
    e,r=fixture(10);c=configuration('U1-555',version='0.4.0')
    assert run(c,e,r)['rows'][0]['roles']['g_per_share_growth']['score'] is None
    e,r=inputs()
    for m in ('central::ebit_yield','central::fcf_yield','central::own_history','central::gap'):
        e['rows'][0]['metric_evidence'][m]['security_and_actions']='UNKNOWN'
    out=run(c,e,r)
    assert out['rows'][0]['axes']['V']['score'] is None
    assert out['rows'][0]['roles']['g_per_share_growth']['score'] is not None


@pytest.mark.parametrize('contradiction',['assumed_as_evidence','assumptions_without_flag'])
def test_direct_cli_cannot_relabel_assumptions_as_confirmed_evidence(contradiction):
    e,r=inputs();c=configuration('U1-555',version='0.4.0');c['share_evidence_scope']='EVIDENCE_ONLY'
    for m in SHARE_METRICS:
        p=e['rows'][0]['metric_evidence'][m]
        if contradiction=='assumed_as_evidence':p['adoption_basis']='OFFICIAL_ASSUMPTION_INHERITED'
        else:p['allowed_assumptions']=['NO_OVERLAP_FACTOR_ONE']
    role=run(c,e,r)['rows'][0]['roles']['g_per_share_growth']
    assert role['score'] is None
    assert {m['reason'] for m in role['metrics']}=={'OFFICIAL_SHARE_REUSE_EVIDENCE_MISSING'}


@pytest.mark.parametrize('scope',['ALL_OFFICIAL_REUSE','EVIDENCE_ONLY'])
def test_saved_scope_replays_and_delivery_keeps_model_and_both_anchors(scope):
    e,r=inputs();c=configuration('U1-555',version='0.4.0');c['share_evidence_scope']=scope
    out=run(c,e,r);assert replay(out,e,r)==out
    files=artifacts({'U1-555':out},data_kind='SYNTHETIC')
    pin=hashlib.sha256(json_bytes(files['manifest.json'])).hexdigest()
    assert validate(files,manifest_sha256=pin,expected_evaluation=out['evaluation'],expected_references={'U1-555':out['reference']})
    config=files['index.json']['models']['U1-555']['configuration']
    assert config['share_evidence_scope']==scope and config['model_id']=='unified-555/0.4.0'
