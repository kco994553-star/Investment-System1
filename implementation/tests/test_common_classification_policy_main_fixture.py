"""공통 분류 /2 경계 정책판 (owner 2026-11-08): Main's /2 screen input is Codex's own output on Codex's own six cases.

tests/fixtures/common_classification_main/policy_v2_fixture.json must equal, byte for byte, the output of
tools/common_classification_policy_main_fixture.py (Codex extend_held_classification → from_sector_snapshot /2 → resolve →
macro_projection on tests/fixtures/common_classification/boundary-policy-v2.json, Codex #520 41f2a25b)."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/common_classification_main/policy_v2_fixture.json'
CASES = ROOT / 'tests/fixtures/common_classification/boundary-policy-v2.json'
TOOL = ROOT / 'tools/common_classification_policy_main_fixture.py'


def test_committed_policy_fixture_is_exactly_the_codex_functions_output():
    r = subprocess.run([sys.executable, str(TOOL), '--check'], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_six_codex_cases_keep_codex_expected_components_and_the_policy():
    main = json.loads(FIXTURE.read_text()); codex = json.loads(CASES.read_text())
    assert main['codex_cases_sha256'] == hashlib.sha256(CASES.read_bytes()).hexdigest()
    assert [c['case_id'] for c in codex['cases']] == [c['case_id'] for c in main['cases']] and len(main['cases']) == 6
    for case, got in zip(codex['cases'], main['cases']):
        assert got['expected'] == case['expected']
        view = got['view']
        assert (view['dictionary_version'], view['mapping_version']) == ('common-industry-dictionary/2', 'common-classification-map/2')
        assert view['boundary_policy']['version'] == main['dictionary']['policy']['version']
        row = view['rows'][0]
        assert row['sector']['id'] == case['expected']['sector_id'], case['case_id']
        assert row['accounting']['id'] == case['expected']['accounting_template'], case['case_id']
        assert got['macro']['classification_hash'] == view['classification_hash']
    assert main['dictionary']['policy']['book_direct_claim'] is False
    assert main['dictionary']['policy']['automatic_company_assignment'] is False
