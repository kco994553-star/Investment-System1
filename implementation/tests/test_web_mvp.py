"""Read-only boundary and misleading-data regressions."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import pytest
from investment_system.product.web_mvp import repository_bundle, demo_bundle, validate_bundle, build, ROOT


def test_frozen_universe_exact_no_live_fabrication():
    b=repository_bundle()
    u=json.loads((ROOT/'reports/gate_evidence/official_snapshot_2024-12-31.json').read_text())
    assert b['universe']['data']==u and len(b['companies'])==500
    for name in ('qgv','technical','macro','portfolio','leaderboard','news','relationships'):
        assert b[name]['state']=='NOT_AVAILABLE' and b[name]['data'] is None


def test_demo_opt_in_values_not_rescored():
    b=demo_bundle(repository_bundle())
    src=json.loads((ROOT/'reports/official_v11_book_snapshots.json').read_text())
    assert list(b['qgv']['data'].values())==src['snapshots']
    assert b['qgv']['state']==b['portfolio']['state']=='DEMO'
    assert b['leaderboard']['data'] is None


def test_false_production_synthetic_missing_provenance_fail_closed():
    b=demo_bundle(repository_bundle())
    for state in ('LIVE','FROZEN_SNAPSHOT'):
        c=deepcopy(b);c['qgv']['state']=state
        with pytest.raises(ValueError):validate_bundle(c)
    c=deepcopy(b);c['qgv']['source']=None
    with pytest.raises(ValueError):validate_bundle(c)
    c=deepcopy(b);c['qgv']['state']='NOT_AVAILABLE'
    with pytest.raises(ValueError):validate_bundle(c)


def test_unknown_duplicate_identity_fail_closed():
    b=repository_bundle();b['companies'].append(b['companies'][0])
    with pytest.raises(ValueError):validate_bundle(b)
    b=demo_bundle(repository_bundle());b['portfolio']['data']['holdings'][0]['company_id']='not-known'
    with pytest.raises(ValueError):validate_bundle(b)


def test_no_mutation_missing_zero_distinction():
    b=demo_bundle(repository_bundle());b['qgv']['data']['nvda']['Q_score']=0
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
