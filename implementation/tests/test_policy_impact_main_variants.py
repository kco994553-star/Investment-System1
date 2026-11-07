"""4.5 정책·지정학 (owner 2026-11-07): Main's screen input is Codex's engine output, nothing hand-made.

- Codex's synthetic-view.json and every expected view of synthetic-states.json are exactly
  research.policy_impact.build on synthetic-job.json / the state inputs (same companies, as_of, public build).
- tests/fixtures/policy_impact_view_main_variants.json is exactly tools/policy_impact_main_variants.py (Codex build).
- The old Main-drafted policy-impact/1 fixture (withdrawn for Codex's contract) is gone."""
import json
import subprocess
import sys
from pathlib import Path

from investment_system.research.policy_impact import build

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'docs/research/policy_impact'


def test_codex_synthetic_view_is_the_engine_output():
    j = json.loads((D / 'synthetic-job.json').read_text())
    got = build(j['bundle'], j['company_ids'], j['as_of'], public=j['public'], public_macro_ids=j['public_macro_ids'])
    assert got == json.loads((D / 'synthetic-view.json').read_text())


def test_codex_state_cases_are_the_engine_output():
    j = json.loads((D / 'synthetic-job.json').read_text())
    states = json.loads((D / 'synthetic-states.json').read_text())
    assert [s['name'] for s in states] == ['EMPTY', 'FUTURE_SOURCE', 'UNVERIFIED_SOURCE', 'MISSING_RATIO']
    for s in states:
        assert build(s['input'], j['company_ids'], j['as_of'], public=True) == s['expected'], s['name']


def test_main_variants_file_is_the_engine_output():
    r = subprocess.run([sys.executable, str(ROOT / 'tools/policy_impact_main_variants.py'), '--check'], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    v = json.loads((ROOT / 'tests/fixtures/policy_impact_view_main_variants.json').read_text())['variants']
    assert v['REVISED']['current_policy_revisions']['p0'] == '2'
    assert [h['review_status'] for h in v['REVISED']['bundle']['hypotheses'] if h['policy_id'] == 'p0'] == ['REVIEW_REQUIRED']
    assert {p['lifecycle_status'] for p in v['HISTORICAL']['bundle']['policies']} == {'UNKNOWN'}
    assert all(x['data_kind'] == 'SYNTHETIC' for x in (v[k]['bundle'] for k in v))


def test_withdrawn_main_draft_fixture_is_gone():
    assert not (ROOT / 'tests/fixtures/policy_impact_v1_synthetic.json').exists()
    assert not (ROOT / 'tools/policy_impact_synthetic_fixture.py').exists()
