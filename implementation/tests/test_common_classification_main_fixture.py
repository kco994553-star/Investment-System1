"""공통 분류 (DC-48, owner 2026-11-07): Main's screen input is Codex's own output, nothing hand-made.

tests/fixtures/common_classification_main/main_fixture.json must equal, byte for byte in the one canonical JSON form,
tools/common_classification_main_fixture.py: Codex records.resolve / technical_macro.technical_groups / macro_projection on
Codex's fixtures.json cases and the CLI's synthetic run (qgv-classification-links.json). The Codex handoff files keep the
SHA-256 Codex published (manifest.json), and each case keeps the expected outcome Codex wrote next to it."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / 'docs/research/common_classification'
FIXTURE = ROOT / 'tests/fixtures/common_classification_main/main_fixture.json'
TOOL = ROOT / 'tools/common_classification_main_fixture.py'


def load():
    return json.loads(FIXTURE.read_text())


def test_codex_handoff_files_keep_the_published_sha256():
    manifest = json.loads((HANDOFF / 'manifest.json').read_text())
    for f in manifest['files']:
        body = (HANDOFF / f['path']).read_bytes()
        assert hashlib.sha256(body).hexdigest() == f['sha256'] and len(body) == f['size'], f['path']
    assert load()['codex_handoff']['sha256'] == {f['path']: f['sha256'] for f in manifest['files']}


def test_committed_main_fixture_is_exactly_the_codex_functions_output():
    r = subprocess.run([sys.executable, str(TOOL), '--check'], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_each_case_keeps_codex_expected_outcome():
    codex = json.loads((HANDOFF / 'fixtures.json').read_text()); main = load()
    assert set(main['record_cases']) == set(codex['record_cases']) and len(codex['record_cases']) == 13
    assert set(main['technical_cases']) == set(codex['technical_cases']) and len(codex['technical_cases']) == 9
    for name, case in codex['record_cases'].items():
        want, got = case['expected'], main['record_cases'][name]
        if want.get('error'):
            assert got['error'] == want['error'] and got['view'] is None, name; continue
        rows = got['view']['rows']
        assert got['error'] is None and len(rows) == want['member_count'], name
        assert rows[0]['sector']['status'] == want['sector_status'] and rows[0]['industry']['status'] == want['industry_status'], name
        if want['reason']:
            assert want['reason'] in rows[0]['sector']['reasons'], name
        assert got['macro']['classification_hash'] == got['view']['classification_hash']
        assert [r['classification_record_id'] for r in got['macro']['rows']] == [r['record_id'] for r in rows]
        assert got['macro']['benchmark_is_common_sector'] is False and got['macro']['sector_returns'] is None
    for name, case in codex['technical_cases'].items():
        want, got = case['expected'], main['technical_cases'][name]
        if want['error']:
            assert got['error'] == want['error'] and got['technical'] is None, name; continue
        group = next(g for g in got['technical']['groups'] if g['sector_id'] == 'INFORMATION_TECHNOLOGY')
        metric = group['board']['metrics']['momentum_3m']
        assert group['membership_status'] == want['membership_status'], name
        assert metric['n_valid'] == want['n_valid'] and metric['k'] == want['k'], name
        assert got['technical']['classification_hash'] == case['view']['classification_hash']


def test_other_date_variant_and_owner_cases_point_at_real_entries():
    main = load()
    row = main['variants']['normal_other_date']['view']['rows'][0]
    assert row['sector']['status'] == 'UNKNOWN' and row['sector']['reasons'] == ['EVALUATION_ONLY_DATE_MISMATCH']
    for name, refs in main['owner_cases'].items():
        for ref in refs:
            part, key = ref.split('.')
            assert key in main[part], (name, ref)


def test_bundle_is_one_run_with_one_record_per_company():
    b = load()['bundle']
    h = b['view']['classification_hash']
    assert b['qgv_links']['classification_hash'] == h == b['technical']['classification_hash'] == b['macro']['classification_hash']
    ids = {r['company_id']: r['record_id'] for r in b['view']['rows']}
    for part in (b['qgv_links']['rows'], b['technical']['rows'], b['macro']['rows']):
        assert {r['company_id']: r['classification_record_id'] for r in part} == ids
    # Today's Codex state: no verified security id, so no confirmed technical group with members and no rank.
    assert all(r['security_ids'] == [] for r in b['technical']['rows'])
    assert b['macro']['benchmark_is_common_sector'] is False and b['macro']['probabilities'] is None


def test_universe_runs_differ_from_the_codex_runs_only_by_the_renamed_company_ids():
    main = load(); u = main['universe']; codes = u['codes']
    strip = lambda rows: [{k: r[k] for k in ('issuer_id', 'record_id', 'sector', 'industry', 'accounting')} for r in rows]
    for name, case in main['record_cases'].items():
        got = u['record_cases'][name]
        if case['error']:
            assert got['error'] == case['error']; continue
        assert sorted(strip(got['view']['rows']), key=json.dumps) == sorted(strip(case['view']['rows']), key=json.dumps), name
        assert set(got['view']['members']) <= set(codes)
    b = u['bundle']; h = b['view']['classification_hash']
    assert sorted(r['company_id'] for r in b['view']['rows']) == sorted(codes)
    assert b['qgv_links']['classification_hash'] == h == b['technical']['classification_hash'] == b['macro']['classification_hash']
    ids = {r['company_id']: r['record_id'] for r in b['view']['rows']}
    for part in (b['qgv_links']['rows'], b['technical']['rows'], b['macro']['rows']):
        assert {r['company_id']: r['classification_record_id'] for r in part} == ids
    t = u['technical_normal']['technical']; g = next(x for x in t['groups'] if x['sector_id'] == 'INFORMATION_TECHNOLOGY')
    assert g['membership_status'] == 'CONFIRMED' and g['counts']['company_members'] == 10
    assert {r['company_id'] for r in t['rows']} == set(codes[:10])
