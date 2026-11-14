from copy import deepcopy
import hashlib
import pytest
from investment_system.research.qgv_555 import run,configuration,fixture
from investment_system.research.qgv_555_delivery import artifacts,validate
from investment_system.research.dual_qgv import json_bytes


def test_complete_deciles_and_bound_files():
    e,r=fixture(23);b=run(configuration('U1-555'),e,r);f=artifacts({'U1-555':b},data_kind='SYNTHETIC')
    pin=hashlib.sha256(json_bytes(f['manifest.json'])).hexdigest()
    assert validate(f,manifest_sha256=pin,expected_evaluation=b['evaluation'],expected_references={'U1-555':b['reference']})['groups']==15
    assert all(sum(x['count'] for x in g['bins'])==23 for g in f['index.json']['groups'])
    g=f['index.json']['groups'][0];bad=deepcopy(f);del bad[g['files'][0]]
    with pytest.raises(ValueError,match='MISSING_MEMBER'):validate(bad,manifest_sha256=pin,expected_evaluation=b['evaluation'],expected_references={'U1-555':b['reference']})


def test_anchor_independent_and_partial_sample_kept():
    e,r=fixture(8);b=run(configuration('U1-555'),e,r);f=artifacts({'U1-555':b},data_kind='SYNTHETIC')
    assert all(g['evaluation_valid_n']==8 and sum(x['count'] for x in g['bins'])==0 for g in f['index.json']['groups'])
    pin=hashlib.sha256(json_bytes(f['manifest.json'])).hexdigest()
    with pytest.raises(ValueError,match='REFERENCE_ANCHOR'):
        validate(f,manifest_sha256=pin,expected_evaluation=b['evaluation'],expected_references={'U1-555':b['evaluation']})
