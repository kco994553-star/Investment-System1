"""Execution source is distinct from audit subject; observations never authorize."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

TOOL = Path(__file__).resolve().parents[1] / 'tools/integration/track_c_fpia_ci_receipt.py'


def module():
    assert TOOL.is_file(), 'CI execution-source receipt not implemented'
    spec = importlib.util.spec_from_file_location('ci_receipt_test', TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


@pytest.fixture
def source(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    git(repo, 'init', '-q')
    git(repo, 'config', 'user.name', 'Synthetic fixture')
    git(repo, 'config', 'user.email', 'fixture@example.invalid')
    wf = repo / '.github/workflows/track-c-fpia.yml'
    wf.parent.mkdir(parents=True)
    wf.write_text('name: original\n')
    tool = repo / 'implementation/tools/integration/track_c_fpia_child.py'
    tool.parent.mkdir(parents=True)
    tool.write_text('# immutable launcher fixture\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'workflow source')
    workflow_sha = git(repo, 'rev-parse', 'HEAD')
    wf.write_text('name: subject differs\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'subject')
    context = {'repository': 'example/repo', 'workflow_sha': workflow_sha,
               'workflow_ref': 'example/repo/.github/workflows/track-c-fpia.yml@refs/heads/workflow-source',
               'event_sha': workflow_sha, 'subject_sha': git(repo, 'rev-parse', 'HEAD'),
               'run_id': '23', 'run_attempt': '2', 'job_key': 'fpia', 'event_name': 'pull_request'}
    return repo, context, tool


def test_workflow_source_never_falls_back_to_subject(source):
    repo, c, _ = source
    r = module().collect_receipt(c, repo, "implementation/tools/integration")
    assert r['status'] == 'OBSERVED_BYTE_MATCH'
    assert r['workflow']['source_commit'] == c['workflow_sha'] != c['subject_sha']
    assert r['workflow']['blob'] == git(repo, 'rev-parse', c['workflow_sha'] + ':.github/workflows/track-c-fpia.yml')
    assert r['checkout']['head'] == c['subject_sha']
    assert r['authentication'] == 'NOT_VERIFIED'
    assert r['integration_acceptance'] == 'BLOCKED'
    assert r['execution']['numeric_job_id'] == 'UNAVAILABLE'
    assert r['execution']['run_attempt'] == 2


@pytest.mark.parametrize('field,value', [
    ('workflow_sha', ''), ('workflow_sha', 'f' * 40),
    ('workflow_sha', '--help'), ('subject_sha', '0' * 40),
    ('repository', 'other/repo'), ('run_id', 'true'), ('run_attempt', '0'),
    ('workflow_ref', 'example/repo/.github/workflows/../secrets.yml@refs/heads/main'),
])
def test_missing_substituted_or_malformed_runtime_source_is_unavailable(source, field, value):
    repo, c, _ = source
    c[field] = value
    r = module().collect_receipt(c, repo, "implementation/tools/integration")
    assert r['status'] == 'UNAVAILABLE'
    assert r['errors']
    assert r['authentication'] == 'NOT_VERIFIED'
    assert r['integration_acceptance'] == 'BLOCKED'


def test_dirty_launcher_is_not_identical_to_checkout(source):
    repo, c, tool = source
    tool.write_text('# substituted\n')
    r = module().collect_receipt(c, repo, "implementation/tools/integration")
    assert r['status'] == 'UNAVAILABLE'
    assert any('working bytes' in x for x in r['errors'])


def test_untracked_executable_file_is_not_hidden_by_tracked_manifest(source):
    repo, c, tool = source
    (tool.parent / 'untracked.py').write_text('raise RuntimeError("not executed")\n')
    assert module().collect_receipt(c, repo, "implementation/tools/integration")['status'] == 'UNAVAILABLE'


def test_symlink_is_not_accepted_as_regular_verifier_source(source):
    repo, c, tool = source
    original = tool.read_text()
    tool.unlink()
    target = repo / 'external.py'
    target.write_text(original)
    tool.symlink_to(target)
    assert module().collect_receipt(c, repo, "implementation/tools/integration")['status'] == 'UNAVAILABLE'


def test_checkout_of_a_different_subject_is_unavailable(source):
    repo, c, _ = source
    c['subject_sha'] = c['workflow_sha']
    assert module().collect_receipt(c, repo, "implementation/tools/integration")['status'] == 'UNAVAILABLE'


@pytest.mark.parametrize('path', ['/tmp', '../outside', '.', ''])
def test_invalid_verifier_directory_is_unavailable(source, path):
    repo, c, _ = source
    assert module().collect_receipt(c, repo, path)['status'] == 'UNAVAILABLE'


def test_cli_does_not_capture_unrelated_environment_or_write_repository(source):
    import os
    repo, c, _ = source
    env = dict(os.environ, UNRELATED_SECRET='must-not-appear')
    env.update({'FPIA_' + k.upper(): v for k, v in c.items()})
    before = git(repo, 'status', '--porcelain')
    run = subprocess.run([sys.executable, str(TOOL), '--repo', str(repo), '--verifier-path', 'implementation/tools/integration'], env=env,
                         capture_output=True, text=True)
    assert run.returncode == 0
    assert json.loads(run.stdout)['status'] == 'OBSERVED_BYTE_MATCH'
    assert 'must-not-appear' not in run.stdout + run.stderr
    assert git(repo, 'status', '--porcelain') == before


def test_workflow_emits_runtime_context_and_does_not_rewrite_audit_exit():
    wf = (TOOL.parents[3] / '.github/workflows/track-c-fpia.yml').read_text()
    assert 'FPIA_WORKFLOW_SHA: ${{ github.workflow_sha }}' in wf
    assert 'FPIA_WORKFLOW_REF: ${{ github.workflow_ref }}' in wf
    assert 'FPIA_SUBJECT_SHA: ${{ inputs.tree || github.event.pull_request.head.sha || github.sha }}' in wf
    assert 'fpia-ci-receipt.json' in wf
    assert 'exit $rc' in wf
