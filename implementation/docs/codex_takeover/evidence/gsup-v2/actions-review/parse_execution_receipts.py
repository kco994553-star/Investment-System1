"""Parse archived read-only Actions data; never contact GitHub or dispatch jobs."""
from hashlib import sha256
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
HEAD = '675d0d298fbaab5b8473ed048a561ef84e2f3e78'
MACRO = '4a07099e36ec3cecda24b82ecedad53800f0aa81'
RUNS = {
    37106686279: 'codex-integration-readiness',
    37106686295: 'web-mvp-validation',
    37106686280: 'technical-real-producer',
    37106686281: 'technical-real-model',
    37106686274: 'us-equity-session',
    37106686285: 'sec-primary-disclosure',
    37106686269: 'p01-research-publication',
    37106686317: 'qgv-invalidation-binding',
}

def read(path):
    return json.loads(path.read_text())

def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()

def exclusive_json(path, value):
    with path.open('x') as f:
        f.write(json.dumps(value, indent=2) + '\n')

def main():
    runs = read(ROOT / 'runs-completed.json')['workflow_runs']
    run_map = {r['id']: r for r in runs}
    assert set(run_map) == set(RUNS), 'eight exact new runs required'
    merge = read(ROOT / 'pr31-merge-commit.json')
    checkout_merge = merge['sha']
    entries = []
    for rid, name in RUNS.items():
        run = run_map[rid]
        assert run['head_sha'] == HEAD and run['name'] == name
        assert run['status'] == 'completed' and run['conclusion'] == 'success'
        assert run['head_commit']['tree_id'] == merge['tree']['sha']
        base = ROOT / str(rid)
        job_data = read(base / 'jobs-completed.connector.json')['jobs']
        jobs = []
        for job in job_data:
            assert job['status'] == 'completed' and job['conclusion'] == 'success'
            log_path = base / f"job{job['id']}.connector.log"
            content = log_path.read_text(encoding='utf-8-sig')
            shas = re.findall(r'git log -1 --format=%H\n[^\n]*Z ([0-9a-f]{40})(?:\s|$)', content)
            assert len(shas) == 1, (rid, job['id'], shas)
            expected = MACRO if job['name'] == 'macro-adoption-offline' else HEAD if name == 'codex-integration-readiness' else checkout_merge
            assert shas[0] == expected
            summaries = re.findall(r'\d+ passed(?:, \d+ \w+)* in [\d.]+s', content)
            expected_tests = 11 if expected == MACRO else 1277
            assert any(re.match(f'{expected_tests} passed in ', s) for s in summaries)
            printed_json_checks = []
            for line in content.splitlines():
                payload = line.partition('Z ')[2]
                if payload.startswith('{'):
                    try:
                        obj = json.loads(payload)
                    except ValueError:
                        continue
                    if obj.get('passed') is True and isinstance(obj.get('checks'), int):
                        printed_json_checks.append(obj)
            jobs.append({
                'job_id': job['id'], 'job_name': job['name'],
                'run_head_sha': HEAD, 'actual_checkout_sha': shas[0],
                'checkout_source': 'connector job log git log -1 --format=%H',
                'checkout_tree_equals_pr_head': expected != MACRO,
                'status': job['status'], 'conclusion': job['conclusion'],
                'pytest_log_summaries': summaries, 'log_sha256': file_hash(log_path),
                'printed_json_assertion_results': printed_json_checks,
                'steps': job['steps'],
            })
        artifacts = read(base / 'artifacts-completed.connector.json')['artifacts']
        artifact_receipts = []
        for a in artifacts:
            assert a['workflow_run']['head_sha'] == HEAD
            archive = base / f"artifact{a['id']}.zip"
            local = file_hash(archive)
            assert a['digest'] == 'sha256:' + local
            expanded = base / f"artifact{a['id']}"
            xml_data = []
            for p in expanded.rglob('*.xml'):
                top = ET.parse(p).getroot()
                suites = top.findall('testsuite') if top.tag == 'testsuites' else [top]
                parsed = [{key: s.get(key) for key in ('name', 'tests', 'failures', 'errors', 'skipped', 'time')} for s in suites]
                assert all(int(x['failures']) == int(x['errors']) == int(x['skipped']) == 0 for x in parsed)
                xml_data.append({'path': str(p.relative_to(expanded)), 'suites': parsed})
            browser_data = []
            for p in expanded.rglob('*browser*.json'):
                data = read(p)
                assert data['passed'] is True and data['errors'] == []
                browser_data.append({'path': str(p.relative_to(expanded)), 'check_groups': len(data['checks']), 'data': data})
            metadata_data = []
            for p in expanded.rglob('entity_metadata_search.json'):
                data = read(p)
                assert data['pass'] is True and data['failures'] == []
                metadata_data.append({'path': str(p.relative_to(expanded)), 'data': data})
            fixture_data = []
            for p in expanded.rglob('fixture-manifest.json'):
                data = read(p)
                assert data['research_display'] == data['frozen_grant'] == data['live_grant'] == 'NONE'
                assert data['records_unchanged'] and data['schema1_sections_unchanged']
                fixture_data.append({'path': str(p.relative_to(expanded)), 'data': data})
            artifact_receipts.append({
                'artifact_id': a['id'], 'name': a['name'],
                'github_artifact_digest': a['digest'], 'local_download_sha256': local,
                'digest_verified': True, 'xml_results': xml_data, 'browser_results': browser_data,
                'entity_metadata_results': metadata_data, 'fixture_contract_results': fixture_data,
                'files_sha256': {str(p.relative_to(expanded)): file_hash(p) for p in expanded.rglob('*') if p.is_file()},
                'retrieval': 'GitHub connector archive plus authorized file_id download',
            })
        entry = {'run_id': rid, 'workflow': name, 'run_attempt': run['run_attempt'],
                 'run_head_sha': HEAD, 'status': run['status'], 'conclusion': run['conclusion'],
                 'html_url': run['html_url'], 'jobs': jobs, 'artifacts': artifact_receipts}
        exclusive_json(base / 'execution-receipt.json', entry)
        entries.append(entry)
    native = next(e for e in entries if e['workflow'] == 'codex-integration-readiness')
    original_web = next(e for e in entries if e['workflow'] == 'web-mvp-validation')
    producer_browsers = [b for a in native['artifacts'] for b in a['browser_results']]
    web_browsers = [b for a in original_web['artifacts'] for b in a['browser_results']]
    assert len(producer_browsers) == 1 and producer_browsers[0]['check_groups'] == 6
    assert sorted(b['check_groups'] for b in web_browsers) == [8, 10]
    original_node = [c for j in original_web['jobs'] for c in j['printed_json_assertion_results']]
    assert any(c['checks'] == 26 for c in original_node)
    receipt = {
        'schema': 'GSUP_SOURCE_IDENTITY_FINAL_ACTIONS_REVIEW_v1',
        'pr_number': 31, 'pr_draft': True, 'source_head': HEAD,
        'base_head': '86ad3628dd5c62c6d873e42511e577f24f4fb588',
        'synthetic_pr_merge_checkout_sha': checkout_merge,
        'source_and_merge_tree': merge['tree']['sha'],
        'different_commit_identity_preserved': True,
        'workflow_baseline_observed_at': '2026-10-03T06:48:04Z',
        'baseline_workflow_successes_not_recounted': 8,
        'new_workflow_runs': 8, 'new_workflow_successes': 8,
        'acceptance_criteria_completed': 3, 'acceptance_criteria_total': 3,
        'full_native_pytest': {'tests': 1277, 'failures': 0, 'errors': 0, 'skipped': 0},
        'macro_pytest': {'tests': 11, 'actual_checkout_sha': MACRO},
        'producer_web_browser': {'check_groups': 6, 'passed': True, 'errors': []},
        'existing_web_browser': {'check_groups': 10, 'passed': True, 'errors': []},
        'existing_language_search_browser': {'check_groups': 8, 'passed': True, 'errors': []},
        'existing_node_assertions': {'checks': 26, 'passed': True},
        'tool_manifest_actions_semantics': 'NOT_RUN means fixture/browser tools did not dispatch workflows; this receipt identifies their actual enclosing Actions execution.',
        'CAL_VERIFY_actual_access': 'NOT_RUN', 'Holdout_actual_access': 'NOT_RUN',
        'actions_dispatched_by_reviewer': 0, 'reruns_dispatched_by_reviewer': 0,
        'canonical_merge': 'NOT_RUN', 'publication_grants': 'NONE',
        'active_authoritative_M_B_v2_numeric_kernel': False,
        'separate_blocker': 'USER_DECISION_REQUIRED_ARITHMETIC_REDUCTION',
        'runs': entries,
    }
    exclusive_json(ROOT / 'FINAL_ACTIONS_REVIEW_RECEIPT.json', receipt)
    print(json.dumps({'new_successful_runs': len(entries), 'review_criteria_completed': 3,
                      'receipt_sha256': file_hash(ROOT / 'FINAL_ACTIONS_REVIEW_RECEIPT.json')}, indent=2))

if __name__ == '__main__':
    main()
