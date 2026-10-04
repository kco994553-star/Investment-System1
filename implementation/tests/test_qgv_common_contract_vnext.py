"""Score-neutral characterization + INACTIVE documentation-contract validation.

No production vNext evaluator is constructed. OFFICIAL namespace here is an
isolated synthetic test container, never a real Official record or grant.
"""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import json

import pytest
from jsonschema import ValidationError

from tools.qgv_contract_audit import DOCS, digest, evaluate_case, validate_spec_record
from investment_system.contracts.enums import ProfileKind, QualityState
from investment_system.contracts.models import DataStamp
from investment_system.contracts.raw import RawFundamentals
from investment_system.contracts.strategy import custom_profile
from investment_system.personal.weights import (
    OfficialRegistry, NodeDefinition, NodeType, Maturity, PersonalStrategyVersion,
    WeightOverride, StrategyStatus, effective_tree, WeightTreeError,
)
from investment_system.personal.versioning import ResultNamespace
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.factors import Q_WEIGHTS, G_WEIGHTS, V_INITIAL_PRIOR
from investment_system.qgv.raw_map import map_raw
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.qgv.g_horizon import GHorizonConfig
from investment_system.qgv.leaderboard import LeaderboardEngine
from investment_system.qgv.track_record import TrackRecordStore
from tests.helpers import complete_obs, AS_OF

GOLDEN = json.loads((DOCS / "golden_cases.json").read_text())


@pytest.mark.parametrize("case", GOLDEN["cases"], ids=lambda c: c["case_id"])
def test_golden_exact_semantics(case):
    assert evaluate_case(case) == case["expected"]


def test_independent_arithmetic_anchors():
    values = {c["case_id"]: evaluate_case(c) for c in GOLDEN["cases"]}
    assert values["all_70"]["Q_score"] == 70
    assert values["q_one_absent"]["Q_score"] == 56
    assert values["financial_na"]["Q_score"] == 56
    assert values["V_only_delta"]["V_score"] == 77.5
    assert values["V_only_delta"]["total_score"] == 70
    assert values["out_of_range_legacy"]["Q_score"] == 256
    assert values["no_factors"]["total_score"] is None


def test_candidate_na_divergence_is_preserved_not_fixed():
    case = next(c for c in GOLDEN["cases"] if c["case_id"] == "sector_context__NOT_APPLICABLE__numeric")
    value = evaluate_case(case)
    assert value["V_score"] == 63
    assert all(v["v_score"] == 70 for v in value["v_candidates"])


def test_neutral_metadata_and_config_manifest_leave_scores_unchanged():
    case = GOLDEN["cases"][0]
    before = evaluate_case(case)
    sidecar = {"legacy_semantic_hash": digest(before), "config_binding": {
        "status": "INACTIVE_SPEC_ONLY", "existing_profile_ref": None,
        "registry_ref": None, "override_version_ref": None},
        "confidence": {"assessment": "UNASSESSED"}}
    assert sidecar["legacy_semantic_hash"] == digest(evaluate_case(case))
    assert before == evaluate_case(case)
    # This proves a non-mutating sidecar, not runtime config wiring.


def test_official_custom_isolation_existing_boundary():
    n = NodeDefinition
    reg = OfficialRegistry("synthetic-isolation", (
        n("root", None, "QGV", NodeType.GROUP, Maturity.VALIDATED, "test root"),
        n("a", "root", "QGV", NodeType.WEIGHT, Maturity.VALIDATED, "test a", .5),
        n("b", "root", "QGV", NodeType.WEIGHT, Maturity.VALIDATED, "test b", .5)))
    original = deepcopy(asdict(reg))
    official = PersonalStrategyVersion("o", "s", reg.registry_version, ResultNamespace.OFFICIAL,
                                       (), StrategyStatus.DRAFT, AS_OF)
    current_tree = effective_tree(reg, official)
    snapshots = [AnalysisEngine().analyze(cid, AS_OF, complete_obs(v), synthetic=True)
                 for cid, v in [("nvda", 70), ("msft", 60)]]
    board = LeaderboardEngine().build("SYNTHETIC-ISOLATION", AS_OF, snapshots)
    store = TrackRecordStore()
    rec = store.record_decision("SYNTHETIC_OFFICIAL_ISOLATION_TEST", "test", AS_OF,
                               tuple(s.qgv_snapshot_id for s in snapshots), {"board": board.to_dict()})
    before = digest({"snapshots":[s.to_dict() for s in snapshots],"board":board.to_dict(),"record":rec.to_dict()})
    custom = replace(official, strategy_version_id="custom", namespace=ResultNamespace.SANDBOX,
                     overrides=(WeightOverride("a", .25), WeightOverride("b", .75)))
    for local in [custom, replace(custom, overrides=(WeightOverride("a", .8), WeightOverride("b", .2)))]:
        assert effective_tree(reg, local) != current_tree
    after = digest({"snapshots":[s.to_dict() for s in snapshots],"board":board.to_dict(),"record":store.get(rec.track_record_id).to_dict()})
    assert before == after
    assert asdict(reg) == original
    assert effective_tree(reg, official) == current_tree
    with pytest.raises(WeightTreeError):
        effective_tree(reg, replace(official, overrides=custom.overrides))
    with pytest.raises(WeightTreeError):
        effective_tree(reg, replace(custom, base_registry_version="different"))
    assert Q_WEIGHTS["competitive_advantage"] == .2
    assert G_WEIGHTS["next_3_5y_growth"] == .25
    assert V_INITIAL_PRIOR["fundamental_value"] == .25


def raw_input():
    stamp = DataStamp("syn", "synthetic", "synthetic", "fixture", AS_OF, AS_OF, AS_OF, synthetic=True)
    return RawFundamentals("nvda", stamp, revenue=120, revenue_prev=100, fcf=20, source_kind="SYNTHETIC")


def test_g_yoy_forecast_proxy_and_fcf_fallback_characterization():
    raw = raw_input(); obs = map_raw(raw)
    assert obs["next_3_5y_growth"].score_0_100 == obs["revenue_growth"].score_0_100 == 90
    assert obs["eps_fcf_per_share_growth"].score_0_100 == 0
    assert obs["revenue_growth"].raw_value == 90  # not the original YoY 0.2
    eps = map_raw(replace(raw, eps=3, eps_prev=2))
    assert eps["eps_fcf_per_share_growth"].score_0_100 == 100


def test_horizon_metadata_does_not_recalculate_g():
    pipe=AnalysisPipeline(); raw=raw_input()
    one=pipe.analyze_raw(raw,available_quarters=4,g_horizon=GHorizonConfig("1Q"))
    five=pipe.analyze_raw(raw,available_quarters=4,g_horizon=GHorizonConfig("5Y"))
    assert one.G_score == five.G_score
    assert one.g_horizon != five.g_horizon


def test_future_raw_entrypoint_difference_not_real_pit_result():
    raw=raw_input(); raw=replace(raw,stamp=replace(raw.stamp,available_at=AS_OF+timedelta(days=1)))
    pipe=AnalysisPipeline(); pipe.fundamentals.put(raw)
    assert pipe.analyze_raw(raw,as_of=AS_OF) is not None
    assert pipe.analyze_as_of(raw.company_id,AS_OF) is None


def test_v_quality_label_origin_and_no_numeric_confidence_multiplier():
    obs=complete_obs(); old=AnalysisEngine().analyze("nvda",AS_OF,obs,synthetic=True)
    new=AnalysisEngine().analyze("nvda",AS_OF,obs,synthetic=True,confidence="LOW")
    assert (old.Q_score,old.G_score,old.V_score)==(new.Q_score,new.G_score,new.V_score)
    row=next(r for r in old.factor_breakdown['v_factor_table'] if r['factor_id']=='sector_context')
    assert row['confidence']==row['coverage']==QualityState.OK.value
    assert row['provenance']==obs['sector_context'].notes


def test_v_effective_weight_metadata_is_not_admission_weight():
    obs=complete_obs()
    obs['sector_context']=replace(obs['sector_context'],quality=QualityState.PIT_UNAVAILABLE)
    snap=AnalysisEngine().analyze('nvda',AS_OF,obs,synthetic=True)
    row=next(r for r in snap.factor_breakdown['v_factor_table'] if r['factor_id']=='sector_context')
    assert row['effective_weight']==.1
    assert snap.V_score==63


def test_existing_strategy_still_rejects_q_weights():
    with pytest.raises(ValueError,match="frozen keys"):
        custom_profile({"q_weights":{}})


def sample():
    return json.loads((DOCS/'contract_record.example.json').read_text())


def test_inactive_schema_example():
    assert validate_spec_record(sample()) == {"status":"SPEC_VALID","runtime_enabled":False}


@pytest.mark.parametrize("mutation", ['runtime','status','confidence','coverage','source_hash','nan','naive_time'])
def test_spec_rejects_false_activation_and_metadata_conflation(mutation):
    doc=sample()
    if mutation=='runtime': doc['runtime_enabled']=True
    if mutation=='status': doc['status']='ACTIVE'
    if mutation=='confidence': doc['confidence']='OK'
    if mutation=='coverage': doc['coverage']='OK'
    if mutation=='source_hash': doc['calculation_ref']['sha256']='unknown'
    if mutation=='nan': doc['legacy_score']=float('nan')
    if mutation=='naive_time': doc['decision_time']='2026-09-14T00:00:00'
    with pytest.raises((ValueError,ValidationError)):
        validate_spec_record(doc)


def eligible_sample():
    doc=sample(); ref=doc['calculation_ref']
    doc['pit']={'status':'ELIGIBLE','policy_ref':ref,'reason_codes':[]}
    doc['inputs']=[{'metric_id':'SYNTHETIC_PIT_ONLY','raw_value':1,'unit':'fixture',
        'period_start':None,'period_end':None,'available_at':doc['decision_time'],
        'source_ref':ref,'vintage_ref':ref,'value_state':'PRESENT',
        'applicability':'UNASSESSED','legacy_quality':'SYNTHETIC','reason_codes':[],
        'normalized_value':None,'normalization_ref':None}]
    return doc


def test_pit_equality_boundary_and_missing_provenance_spec_only():
    doc=eligible_sample()
    assert validate_spec_record(doc)['runtime_enabled'] is False
    for key in ['source_ref','vintage_ref','available_at']:
        bad=deepcopy(doc);bad['inputs'][0][key]=None
        with pytest.raises(ValueError):validate_spec_record(bad)
    bad=deepcopy(doc);bad['inputs'][0]['available_at']='2026-09-15T00:00:00Z'
    with pytest.raises(ValueError,match='future'):validate_spec_record(bad)


def test_missing_never_becomes_zero_in_spec():
    doc=eligible_sample();doc['inputs'][0]['value_state']='ABSENT'
    with pytest.raises(ValueError):validate_spec_record(doc)
    doc['pit']['status']='UNASSESSED';doc['inputs'][0]['raw_value']=None
    assert validate_spec_record(doc)['status']=='SPEC_VALID'


def test_period_date_precision_preserved_without_midnight_inference():
    doc=eligible_sample()
    doc['inputs'][0]['period_start']='2025-01-01'
    doc['inputs'][0]['period_end']='2025-12-31'
    before=deepcopy(doc)
    validate_spec_record(doc)
    assert doc==before
    doc['inputs'][0]['available_at']='2026-09-14'
    with pytest.raises(ValueError):validate_spec_record(doc)
