from copy import deepcopy
from investment_system.research.qgv_555 import configuration,run,fixture
from investment_system.research.qgv_555_additional import attach
from investment_system.research.qgv_555_delivery import artifacts


def test_additional_full_deciles_do_not_change_any_core_result():
    e,ref=fixture(23);b=run(configuration('U1-555'),e,ref);old=deepcopy(b)
    out=attach(b,e,ref)
    assert b==old and not out['core_scores_recomputed']
    for before,after in zip(b['rows'],out['rows']):
        assert all(before[k]==after[k] for k in before)
        assert after['factors']['sector::roa_ttm']['extra_score_contribution']==0
    f=artifacts({'U1-555':out},data_kind='SYNTHETIC');g=next(x for x in f['index.json']['groups'] if x['role']=='sector::roa_ttm')
    assert g['evaluation_valid_n']==23 and sum(x['count'] for x in g['bins'])==23


def test_group_index_is_bounded_without_dropping_groups():
    import hashlib
    from investment_system.research.qgv_555_delivery import read_groups,validate
    from investment_system.research.dual_qgv import json_bytes
    e,ref=fixture(12);b=attach(run(configuration('U1-555'),e,ref),e,ref)
    f=artifacts({'U1-555':b},data_kind='SYNTHETIC',max_bytes=100000)
    assert f['index.json']['groups_layout']=='SHARDED'
    assert len(read_groups(f))==f['index.json']['groups_count']
    assert max(len(json_bytes(v)) for v in f.values())<=100000
    pin=hashlib.sha256(json_bytes(f['manifest.json'])).hexdigest()
    validate(f,manifest_sha256=pin,expected_evaluation=b['evaluation'],expected_references={'U1-555':b['reference']})
