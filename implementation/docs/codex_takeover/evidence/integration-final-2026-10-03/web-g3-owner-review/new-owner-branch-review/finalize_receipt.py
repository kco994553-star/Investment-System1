from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
source = Path('/workspace/web-g3-state-upstream-readonly')
head = 'e91dc773af600ff66d31575ce3774490a0b0be8c'
parent = '2b53b27fe0f570557159d02552911e9e1cc7be9c'
global_ref = '5fafee22ae4c1d246b6f2ef1f3d870344d7627c4'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=source)
assert git('rev-parse', 'HEAD').decode().strip() == head
assert git('status', '--porcelain') == b''
assert git('show', '-s', '--format=%P', head).decode().strip() == parent
assert git('rev-parse', 'origin/integration/global-handoff-v1').decode().strip() == global_ref
prior_paths = {'original_triage': root.parent / 'TRIAGE_RECEIPT.json',
               'prior_guard_review': root.parent / 'upstream-2b53b27/FINAL_READ_ONLY_REVIEW_RECEIPT.json',
               'prior_guard_manifest': root.parent / 'upstream-2b53b27/APPEND_ONLY_EVIDENCE_MANIFEST.json'}
expected = {'original_triage': '130fd8a72bfe240234aeba6616b8912b747bebc140311b591f08dc910ba1957c',
            'prior_guard_review': '931777986a7a0ac64a3f11c9de3806424a7a479ffbf7b0625218cb460e674b6c',
            'prior_guard_manifest': 'f2e18e9f6b326f393bee574794bde38e125b86c82eea10e3433cb610b9e75751'}
for k,p in prior_paths.items():
    assert sha256(p.read_bytes()).hexdigest() == expected[k]
preserved_paths = [
    'implementation/src/investment_system/product/web_mvp.py',
    'implementation/src/investment_system/producers/contract.py',
    'implementation/tests/test_web_mvp.py',
    'implementation/tests/test_global_language_search.py',
    'implementation/tests/test_web_research_guard.py',
]
preserved = []
for path in preserved_paths:
    raw = git('show', head + ':' + path)
    assert raw == git('show', parent + ':' + path)
    preserved.append({'path': path, 'sha256': sha256(raw).hexdigest(), 'byte_identical_to_parent': True})
browser = json.loads((root / 'reproduction-browser-receipt.json').read_text())
preparation = json.loads((root / 'probe-preparation-receipt.json').read_text())
assert browser['source_head'] == head
assert browser['external_page_requests'] == 0 and browser['page_errors'] == []
receipt = {
 'kind': 'READ_ONLY_NEW_OWNER_PRESENTATION_BRANCH_CHECK_V1', 'observed_at': datetime.now(timezone.utc).isoformat(),
 'owner_branch': 'integration/web/production-state-presentation-v1', 'fresh_fetched_head': head,
 'parent': parent, 'merge_base_with_PR34': git('merge-base', parent, head).decode().strip(),
 'origin_global_routing_ref_as_observed': global_ref, 'routing_marker': 'GSI-007; wf5 Web batch running',
 'relation_to_PR34': 'STACKED_INDEPENDENT_PRESENTATION_WORK; NO_EVIDENCED_SUPERSESSION',
 'commit_subject': git('show', '-s', '--format=%s', head).decode().strip(),
 'changed_paths_vs_parent': git('diff', '--name-status', parent, head).decode().splitlines(),
 'new_scoped_approval_docs_or_freeze_supersession': git('diff', '--name-only', parent, head, '--', 'implementation/docs').decode().splitlines(),
 'scope_authority': 'Prior original-Web Frozen source preservation CONFLICT remains unresolved; current commit supplies no new scoped authority record',
 'researchMarker': {'byte_identical_to_PR34': preparation['researchMarker_byte_identical_to_parent'],
                     'sha256': preparation['researchMarker_sha256'], 'direct_methodology_status_supported': False},
 'source_hashes': {'new_app_sha256': preparation['new_app_sha256'], 'parent_app_sha256': preparation['parent_app_sha256']},
 'preserved_builder_policy_tests': preserved,
 'actual_existing_probe': {'builder_admission': preparation['bundle_builder_admission'], 'browser': browser,
                          'source_runtime': 'exact upstream e91dc773; Chromium /usr/bin/chromium; viewport390x844; all page requests intercepted from local test assets'},
 'G3_status': 'NOT_RESOLVED; DIRECT_METHODOLOGY_RESEARCH_STILL_RENDERS_LIVE_11.11',
 'read_only_acceptance_tasks_completed': 3, 'read_only_acceptance_tasks_total': 3,
 'production_presentation_acceptance_or_maturity': 'NOT_CERTIFIED',
 'owner_presentation_full_pytest': 'NOT_RUN', 'owner_presentation_E2E': 'NOT_RUN', 'Actions': 'NOT_RUN',
 'BRANCH_STATE': 'ACTIVE_READ_ONLY_UPSTREAM_EXACT_e91dc773',
 'INTEGRATION_STATE': 'NOT_INTEGRATED_BY_OBSERVER; PR34_direct_methodology_finding_persists',
 'CANONICAL_STATE': 'NOT_MERGED',
 'USER_DECISION_REQUIRED': 'NO_NEW_DECISION_SELECTED_BY_OBSERVER; scope conflict remains for Primary authority review',
 'source_edits': 0, 'new_UI_branch': False, 'external_messages': 'NOT_SENT', 'upstream_repin_or_resolution': 'NOT_RUN',
 'real_data_provider_calls': 0, 'CAL_VERIFY_actual_access': 'NOT_RUN', 'Holdout_actual_access': 'NOT_RUN',
 'grants_issued': 0, 'deployment': 'NOT_RUN', 'previous_receipts_sha256_preserved': expected,
 'next_step': 'Primary owner consumes exact-head findings; no duplicate implementation or owner changes',
}
out = root / 'READ_ONLY_REVIEW_RECEIPT.json'
assert not out.exists()
out.write_text(json.dumps(receipt, indent=2) + '\n')
manifest = {'kind': 'NEW_OWNER_BRANCH_REVIEW_ARTIFACT_MANIFEST_V1', 'head': head, 'files': []}
for p in sorted(root.rglob('*')):
    if p.is_file() and p.name != 'ARTIFACT_MANIFEST.json':
        raw = p.read_bytes()
        manifest['files'].append({'path': str(p.relative_to(root)), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()})
mf = root / 'ARTIFACT_MANIFEST.json'
assert not mf.exists()
mf.write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'head': head, 'G3': receipt['G3_status'], 'review_tasks': '3/3 COMPLETED_WITH_FINDINGS',
                  'receipt_sha256': sha256(out.read_bytes()).hexdigest(), 'manifest_sha256': sha256(mf.read_bytes()).hexdigest(),
                  'previous_receipts_byte_preserved': True, 'files': len(manifest['files'])}))
