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
