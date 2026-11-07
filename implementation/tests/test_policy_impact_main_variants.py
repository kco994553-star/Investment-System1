"""4.5 정책·지정학 (owner 2026-11-07): Main's screen input is Codex's engine output, nothing hand-made.

- Codex #509 c2ae92a0: a public build is policy-impact-view/2 (watch items need an explicit ALLOWED permission);
  synthetic-public-v2.json is exactly build() on synthetic-job.json. The retained public v1 files (synthetic-view.json,
  synthetic-states.json) differ from today's build ONLY by those two documented changes (schema name, no watch items).
- navigation-synthetic-view.json is exactly Codex navigation.project on navigation-synthetic-job.json.
- tests/fixtures/policy_impact_view_main_variants.json is exactly tools/policy_impact_main_variants.py (Codex build).
- The old Main-drafted policy-impact/1 fixture (withdrawn for Codex's contract) is gone."""
import json
import subprocess
import sys
from pathlib import Path

from investment_system.research.policy_impact import build

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'docs/research/policy_impact'


def as_retained_v1(view):
    """Today's public build written the retained v1 way: only the two c2ae92a0 changes are undone."""
    return {**view, 'schema_version': 'policy-impact-view/1'}


def without_watch(view):
    v = json.loads(json.dumps(view))
    for h in v['bundle']['hypotheses']:
        h['watch_items'] = []
    return v


def test_codex_public_v2_is_the_engine_output_and_v1_differs_only_as_documented():
    j = json.loads((D / 'synthetic-job.json').read_text())
    got = build(j['bundle'], j['company_ids'], j['as_of'], public=j['public'], public_macro_ids=j['public_macro_ids'])
    assert got == json.loads((D / 'synthetic-public-v2.json').read_text())
    assert got['schema_version'] == 'policy-impact-view/2'
    assert as_retained_v1(got) == without_watch(json.loads((D / 'synthetic-view.json').read_text()))


def test_codex_state_cases_differ_from_the_engine_only_as_documented():
    j = json.loads((D / 'synthetic-job.json').read_text())
    states = json.loads((D / 'synthetic-states.json').read_text())
    assert [s['name'] for s in states] == ['EMPTY', 'FUTURE_SOURCE', 'UNVERIFIED_SOURCE', 'MISSING_RATIO']
    for s in states:
        got = build(s['input'], j['company_ids'], j['as_of'], public=True)
        assert got['schema_version'] == 'policy-impact-view/2', s['name']
        assert as_retained_v1(got) == without_watch(s['expected']), s['name']


def test_codex_navigation_view_is_the_projection_output():
    import hashlib
    from investment_system.research.policy_impact.navigation import project
    j = json.loads((D / 'navigation-synthetic-job.json').read_text())
    bodies = {}
    for spec in j['title_sources']:
        body = (D / Path(spec['path']).name).read_bytes()
        assert hashlib.sha256(body).hexdigest() == spec['sha256']
        bodies[spec['sha256']] = body
    got = project(j['view'], j['navigation'], j['as_of'], public=j['public'], title_sources=bodies)
    assert got == json.loads((D / 'navigation-synthetic-view.json').read_text())


def test_main_variants_file_is_the_engine_output():
    r = subprocess.run([sys.executable, str(ROOT / 'tools/policy_impact_main_variants.py'), '--check'], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    v = json.loads((ROOT / 'tests/fixtures/policy_impact_view_main_variants.json').read_text())['variants']
    assert v['REVISED']['current_policy_revisions']['p0'] == '2'
    assert [h['review_status'] for h in v['REVISED']['bundle']['hypotheses'] if h['policy_id'] == 'p0'] == ['REVIEW_REQUIRED']
    assert {p['lifecycle_status'] for p in v['HISTORICAL']['bundle']['policies']} == {'UNKNOWN'}
    assert all(x['data_kind'] == 'SYNTHETIC' for x in (v[k]['bundle'] for k in ('REVISED', 'HISTORICAL', 'NEWS')))
    assert [v[k]['schema_version'] for k in ('REVISED', 'HISTORICAL', 'NEWS')] == ['policy-impact-view/2', 'policy-impact-view/2', 'policy-impact-view/1']
    nav = v['NAV']['navigation']
    assert nav['data_kind'] == 'SYNTHETIC' and len(nav['titles']) == 1 and len(nav['news_links']) == 1 and nav['reasons'] == []
    from investment_system.research.policy_impact.build import digest
    assert nav['base_view_hash'] == digest(v['NAV']['view'])


def test_withdrawn_main_draft_fixture_is_gone():
    assert not (ROOT / 'tests/fixtures/policy_impact_v1_synthetic.json').exists()
    assert not (ROOT / 'tools/policy_impact_synthetic_fixture.py').exists()
