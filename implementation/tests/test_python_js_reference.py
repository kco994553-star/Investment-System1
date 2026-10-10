import importlib.util
import json
from pathlib import Path
import pytest
PATH=Path(__file__).parents[1]/'tools/python_js_reference.py'

def api():
    s=importlib.util.spec_from_file_location('js_reference',PATH);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def assert_same(actual,expected):
    if type(expected) is dict:
        assert set(actual)==set(expected)
        for k,v in expected.items():assert_same(actual[k],v)
    elif type(expected) is list:
        assert len(actual)==len(expected)
        for a,e in zip(actual,expected):assert_same(a,e)
    elif type(expected) in (int,float):
        assert type(actual) in (int,float) and actual==pytest.approx(expected,rel=1e-10,abs=1e-10)
    else:
        assert type(actual) is type(expected)
        assert actual==expected


def vectors():
    p=Path(__file__).parent/'fixtures/python_js_reference_v1.json'
    return json.loads(p.read_text())['cases'] if p.exists() else [{'id':'not-yet','operation':'missing','input':{},'expected':None}]


@pytest.mark.parametrize('case',vectors(),ids=lambda c:c['id'])
def test_synthetic_python_goldens(case):
    m=api()
    if case['operation']=='company_types' and importlib.util.find_spec('investment_system.qgv.company_types') is None:
        with pytest.raises(m.DependencyPending,match='TYPE_ENGINE_PENDING_MERGE'):m.replay(case)
    else:assert_same(m.replay(case),case['expected'])


def test_live_fixture_refused():
    with pytest.raises(ValueError,match='SYNTHETIC_ONLY'):api().replay({'synthetic':False})


@pytest.mark.parametrize('actual,expected',[(1,True),(0,False),(True,1),(False,0)])
def test_booleans_and_numbers_are_never_interchangeable(actual,expected):
    with pytest.raises(AssertionError):assert_same(actual,expected)
