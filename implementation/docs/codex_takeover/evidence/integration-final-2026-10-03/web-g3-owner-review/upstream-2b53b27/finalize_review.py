from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent
source = Path('/workspace/web-g3-upstream-readonly')
upstream = '2b53b27fe0f570557159d02552911e9e1cc7be9c'
base = 'f8af596df4d235fee1f29bf0cb6c9a3cc0f89f36'
comparison = '675d0d298fbaab5b8473ed048a561ef84e2f3e78'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=source)
assert git('rev-parse', 'HEAD').decode().strip() == upstream
assert git('status', '--porcelain') == b''
assert subprocess.run(['git', 'diff', '--quiet', upstream, '--'], cwd=source).returncode == 0
changed = git('diff', '--name-status', base, upstream).decode().splitlines()
existing_changes = [line.split('\t')[-1] for line in changed if not line.startswith('A\t')]
assert set(existing_changes) == {
    'implementation/src/investment_system/product/web_assets/app.js',
    'implementation/src/investment_system/product/web_assets/locale.js',
}
base_files = git('ls-tree', '-r', '--name-only', base).decode().splitlines()
test_originals = [p for p in base_files if p.startswith('implementation/tests/')]
base_tree_preserved = len(base_files) - len(existing_changes)
authority_paths = [
    'implementation/docs/web_mvp/CONTRACT.md',
    'implementation/docs/web_mvp/STATUS.md',
    'implementation/docs/global_language_search/CONTRACT.md',
    'implementation/docs/global_language_search/STATUS.md',
    'implementation/docs/producer_infrastructure/P01_APPROVAL_2026-10-02.md',
]
authority = []
for path in authority_paths:
    raw = git('show', upstream + ':' + path)
    authority.append({'path': path, 'head': upstream, 'blob': git('rev-parse', upstream + ':' + path).decode().strip(),
                      'sha256': sha256(raw).hexdigest()})
pr = json.loads((root / 'pr34.json').read_text())
oracle = json.loads((root / 'adversarial-guard-oracle.json').read_text())
browser = json.loads((root / 'reproduction-browser-receipt.json').read_text())
owner_browser = json.loads((root / 'owner-browser-evidence/browser-validation-fixture.json').read_text())
x = ET.parse(root / 'owner-guard-tests.xml').getroot()
suites = [x] if x.tag == 'testsuite' else list(x)
pytest_counts = {name: sum(int(s.get(name, 0)) for s in suites) for name in ('tests', 'failures', 'errors', 'skipped')}
receipt = {
 'kind': 'READ_ONLY_G3_UPSTREAM_REVIEW_V1', 'observed_at': datetime.now(timezone.utc).isoformat(),
 'source_branch': 'integration/web/research-render-guard-v1', 'exact_head': upstream, 'base': base,
 'merge_base_with_675': git('merge-base', comparison, upstream).decode().strip(),
 'comparison_source_head': comparison, 'global_routing_head': '5fafee22ae4c1d246b6f2ef1f3d870344d7627c4',
 'PR': {'number': 34, 'url': pr['html_url'], 'head_sha': pr['head']['sha'], 'base_ref': pr['base']['ref'],
        'draft': pr['draft'], 'state': pr['state'], 'body_sha256': sha256(pr['body'].encode()).hexdigest()},
 'changed_paths': changed, 'existing_source_changes': existing_changes,
 'all_other_original_base_files_byte_preserved': base_tree_preserved,
 'original_test_files_byte_preserved': len(test_originals),
 'original_files_absent_from_branch_base_are_not_claimed_deleted': True,
 'scoped_authority_inputs': authority,
 'freeze_authority': {'classification': 'CONFLICT', 'resolution': 'PRIMARY_SCOPED_AUTHORITY_CLARIFICATION_REQUIRED',
    'web_phase_status': 'M1/M2 FROZEN, tested code f58f1f38585420811d3fad6ad0b17a9e281e3c39',
    'later_language_status': 'IMPLEMENTED; scoped product UI changes, tested code82ae07c5f0758038abda98cd8db9e0a0f2de1ee3',
    'new_scoped_approval_or_freeze_supersession_record_in_diff': False,
    'P01_protected_builder_bytes': 'UNCHANGED', 'absence_of_app_byte_pin_is_permission': False,
    'standing_parent_rule': 'Preserve original Frozen app.js/web_mvp.py/tests/manifests; do not infer editable from absence of byte pin'},
 'tests_actually_executed': {'runtime_python': platform.python_version(), 'owner_targeted_pytest': pytest_counts,
    'owner_fixture_browser': {'groups_passed': len(owner_browser['checks']), 'passed': owner_browser['passed'],
        'errors': owner_browser['errors'], 'runtime': owner_browser['runtime'], 'baseline_comparison': True},
    'independent_exact_function_oracle': {'passing': oracle['passing'], 'failing': oracle['failing'], 'failure': 'DIRECT_METHODOLOGY_G3_BYPASS'},
    'independent_actual_browser': browser,
    'producer_nonresearch_diagnostic_positive_controls': '2 ACCEPTED; existing producer predicate differs from recursive owner guard'},
 'actions_actually_dispatched_by_reviewer': 'NOT_RUN', 'full_pytest_by_reviewer': 'NOT_RUN',
 'Actions_observed_metadata': [
    {'run_id': r['id'], 'name': r['name'], 'run_head_sha': r['head_sha'], 'status': r['status'],
     'conclusion': r['conclusion'], 'actual_checkout_sha': 'NOT_INSPECTED'}
    for r in json.loads((root / 'actions-observed.json').read_text())['workflow_runs']],
 'review_acceptance': {'read_only_tasks_completed': 3, 'read_only_tasks_total': 3, 'upstream_G3': 'NOT_ACCEPTED; STILL_REPRODUCED',
                      'new_policy_selected': False, 'capability_maturity_increase_certified': False},
 'BRANCH_STATE': 'PR34 OPEN_DRAFT; exact2b read-only upstream',
 'INTEGRATION_STATE': 'NOT_INTEGRATED_BY_REVIEWER; original direct counterexample remains; scope authority conflict',
 'CANONICAL_STATE': 'NOT_MERGED',
 'USER_DECISION_REQUIRED': 'CONDITIONAL_ONLY_IF_FROZEN_SOURCE_CHANGE_OR_NEW_WITHHOLDING_POLICY_PROVES_NECESSARY; no observer decision request',
 'blockers': ['Primary Web owns active wf5 write set', 'Direct methodology counterexample remains', 'Original app Frozen preservation authority unresolved', 'Recursive diagnostic scan broader than producer predicate'],
 'next_autonomous_action': 'Primary owner consumes independent findings and supplies next exact-head handoff; reviewer remains read-only',
 'repo_source_changes_by_reviewer': 0, 'new_UI_implementation_branches_or_commits': 0,
 'upstream_resolution_or_repin': 'NOT_RUN', 'real_data_provider_calls': 0, 'CAL_VERIFY_actual_access': 'NOT_RUN',
 'Holdout_actual_access': 'NOT_RUN', 'grants_issued': 0, 'deployment': 'NOT_RUN',
 'preserved_prior_triage_receipt_sha256': sha256((root.parent / 'TRIAGE_RECEIPT.json').read_bytes()).hexdigest(),
}
out = root / 'FINAL_READ_ONLY_REVIEW_RECEIPT.json'
assert not out.exists(), 'append-only review receipt must not overwrite'
out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
manifest = {'kind': 'EXTERNAL_READ_ONLY_G3_EVIDENCE_MANIFEST_V1', 'exact_head': upstream, 'files': []}
for p in sorted(root.parent.rglob('*')):
    if p.is_file() and p.name != 'APPEND_ONLY_EVIDENCE_MANIFEST.json':
        b = p.read_bytes()
        manifest['files'].append({'path': str(p.relative_to(root.parent)), 'bytes': len(b), 'sha256': sha256(b).hexdigest()})
mf = root / 'APPEND_ONLY_EVIDENCE_MANIFEST.json'
assert not mf.exists()
mf.write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'head': upstream, 'review_tasks': '3/3 COMPLETED_WITH_FINDINGS', 'G3': 'STILL_REPRODUCED',
                  'receipt_sha256': sha256(out.read_bytes()).hexdigest(), 'manifest_sha256': sha256(mf.read_bytes()).hexdigest(),
                  'other_original_base_files_preserved': base_tree_preserved, 'original_tests_preserved': len(test_originals),
                  'manifest_files': len(manifest['files'])}))
