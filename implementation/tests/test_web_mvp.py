"""Read-only boundary and misleading-data regressions."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import pytest
from tests.web_contract_fixture import synthetic_bundle
from investment_system.product.web_mvp import repository_bundle, demo_bundle, validate_bundle, build, ROOT


def test_default_universe_is_withheld_without_live_fabrication():
    b = repository_bundle()
    assert b['universe']['state'] == 'NOT_AVAILABLE'
    assert b['universe']['data'] is None and b['companies'] == []
    for name in ('qgv','technical','macro','portfolio','leaderboard','news','relationships'):
        assert b[name]['state'] == 'NOT_AVAILABLE' and b[name]['data'] is None


def test_mixed_demo_is_not_a_public_export(tmp_path):
    with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
        demo_bundle(repository_bundle())
    with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
        build(tmp_path / 'demo', demo=True)
    assert not (tmp_path / 'demo').exists()


def test_false_production_synthetic_missing_provenance_fail_closed():
    b=synthetic_bundle()
    for state in ('LIVE','FROZEN_SNAPSHOT'):
        c=deepcopy(b);c['qgv']['state']=state
        with pytest.raises(ValueError):validate_bundle(c)
    c=deepcopy(b);c['qgv']['source']=None
    with pytest.raises(ValueError):validate_bundle(c)
    c=deepcopy(b);c['qgv']['state']='NOT_AVAILABLE'
    with pytest.raises(ValueError):validate_bundle(c)


def test_unknown_duplicate_identity_fail_closed():
    b=synthetic_bundle();b['companies'].append(b['companies'][0])
    with pytest.raises(ValueError):validate_bundle(b)
    b=synthetic_bundle();b['portfolio']['data']['holdings'][0]['company_id']='not-known'
    with pytest.raises(ValueError):validate_bundle(b)


def test_no_mutation_missing_zero_distinction():
    b=synthetic_bundle();b['qgv']['data']['nvda']['Q_score']=0
    before=deepcopy(b);v=validate_bundle(b)
    assert b==before and v==before and v is not b
    assert v['qgv']['data']['nvda']['Q_score']==0
    assert v['qgv']['data']['nvda']['V_score'] is None


def test_live_requires_expiry_and_offset():
    b=repository_bundle();b['macro']={'state':'LIVE','as_of':'2026-09-28T09:00:00+09:00','source':'producer:test','data':{'state':'NORMAL'}}
    with pytest.raises((ValueError,KeyError)):validate_bundle(b)
    b['macro']['expires_at']='2026-09-28T15:00:00'
    with pytest.raises(ValueError):validate_bundle(b)
    b['macro']['expires_at']+='+09:00'
    assert validate_bundle(b)['macro']['data']=={'state':'NORMAL'}


def test_build_reuses_canonical_prompt_payload():
    from investment_system.prompt_library.catalog import load_catalog
    from investment_system.prompt_library.ui import render_html
    cat=load_catalog()
    with tempfile.TemporaryDirectory() as d:
        build(d)
        research=(Path(d)/'research.html').read_text()
        assert cat.sha256 in research
        assert render_html().split('<script type="application/json" id="plv1-data">')[1].split('</script>')[0] in research
        assert not (Path(d)/'network.html').exists()


def test_no_scoring_track_owner_imports():
    import ast
    p=ROOT/'src/investment_system/product/web_mvp.py'
    imports=[n.module or '' for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,ast.ImportFrom)]
    assert not any(x.startswith(('qgv','technical','macro','universe','personal','validation')) for x in imports)
