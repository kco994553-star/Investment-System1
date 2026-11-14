"""The new evidence contract cannot silently inherit a historical v1 approval."""
from copy import deepcopy
import hashlib
import pytest
from investment_system.research.qgv_555 import (
    configuration, fixture, run, replay, validate_configuration, SHARE_METRICS, catalog,
)
from investment_system.research.qgv_555_additional import attach
from investment_system.research.qgv_555_delivery import artifacts, validate
from investment_system.research.dual_qgv import json_bytes


def test_new_evidence_policy_preserves_legacy_configuration():
    old=configuration('U1-555',version='0.2.0')
    new=configuration('U1-555',version='0.3.0')
    assert old['historical_share_policy']=='cross-filing-annual-duplicates/1'
    assert new['model_id']=='unified-555/0.3.0'
    assert new['historical_share_policy']=='cross-filing-consistency-full-period/2'
    changed={k for k in old if old[k]!=new[k]}
    assert changed=={'version','model_id','historical_share_policy'}
    bad=deepcopy(new);bad['historical_share_policy']=old['historical_share_policy']
    with pytest.raises(ValueError,match='POLICY_CHANGE'):validate_configuration(bad)


@pytest.mark.parametrize('stage',['LEGACY','CROSS_FILING_CONSISTENT'])
def test_first_stage_is_not_final_adoption_and_additional_view_agrees(stage):
    e,r=fixture(8)
    for s in (e,r):
        for row in s['rows']:
            for m in SHARE_METRICS:
                p=row['metric_evidence'][m]
                p['share_eligibility_stage']=stage
    # v0.2 replay semantics remain separate from the new eligibility contract.
    prior=run(configuration('U1-555',version='0.2.0'),e,r)
    assert prior['rows'][0]['roles']['g_per_share_growth']['score'] is not None
    current=run(configuration('U1-555',version='0.3.0'),e,r)
    role=current['rows'][0]['roles']['g_per_share_growth']
    assert role['score'] is None
    assert {m['reason'] for m in role['metrics']}=={'SHARE_PERIOD_ELIGIBILITY_UNVERIFIED'}
    assert role['metrics'][0]['share_validation']['diagnostic_raw']==e['rows'][0]['metrics'][role['metrics'][0]['metric']]
    assert current['rows'][0]['roles']['q_capital_allocation']['score'] is not None
    # Additional views use the same eligibility check and contribute no new weight.
    out=attach(current,e,r)
    assert out['rows'][0]['factors']['eps_cagr_3y']['score'] is None
    assert out['rows'][0]['factors']['eps_cagr_3y']['extra_score_contribution']==0


@pytest.mark.parametrize('candidate',['U1-555','S1-555'])
def test_complete_synthetic_evidence_is_automatically_eligible_and_deliverable(candidate):
    e,r=fixture(8)
    out=run(configuration(candidate,version='0.3.0'),e,r)
    for m in out['rows'][0]['roles']['g_per_share_growth']['metrics']:
        assert m['score'] is not None
        assert m['share_validation']['final_eligibility']=='FINAL_ELIGIBLE'
        assert m['share_validation']['denominator_definition']=='WEIGHTED_AVERAGE_DILUTED_SHARES'
    files=artifacts({candidate:out},data_kind='SYNTHETIC')
    pin=hashlib.sha256(json_bytes(files['manifest.json'])).hexdigest()
    assert validate(files,manifest_sha256=pin,expected_evaluation=out['evaluation'],
        expected_references={candidate:out['reference']})
    assert files['index.json']['models'][candidate]['model_id']==out['model_id']


def test_basic_or_actual_shares_do_not_satisfy_diluted_metric_contract():
    e,r=fixture(8)
    for m in SHARE_METRICS:
        e['rows'][0]['metric_evidence'][m]['denominator_definition']='ACTUAL_ENDING_SHARES'
    out=run(configuration('U1-555',version='0.3.0'),e,r)
    role=out['rows'][0]['roles']['g_per_share_growth']
    assert role['score'] is None
    assert {m['reason'] for m in role['metrics']}=={'SHARE_DENOMINATOR_DEFINITION_MISMATCH'}
    assert catalog()['dilution_3y']['actual_issuance_interpretation'] is False
    assert 'REPORTED_DILUTED_EPS' in catalog()['eps_cagr_3y']['numerator_definition']


def test_new_version_replay_uses_both_saved_input_contexts():
    e,r=fixture(8)
    saved=run(configuration('U1-555',version='0.3.0'),e,r)
    assert replay(saved,e,r)==saved
    r['rows'][0]['metric_evidence']['eps_cagr_3y']['share_eligibility_stage']='UNCONFIRMED'
    with pytest.raises(ValueError,match='SAVED_INPUT_MISMATCH'):replay(saved,e,r)
