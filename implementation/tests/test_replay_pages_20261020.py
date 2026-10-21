"""The one-off replay may copy fixed collected JSON, never old code or a new observation."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.error
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/replay_pages_20261020.py'
NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
DATA_FILES = (
    'actual-catalog.json', 'company-classification.json', 'company-logos.json',
    'company-names-ko.json', 'company-types-pricefree.json', 'dart-disclosures.json',
    'dart-financials.json', 'data.json', 'entities.json', 'forward-validation-ledger.json',
    'macro-evidence.json', 'macro-screen.json', 'news-signals.json', 'sec-13f-changes.json',
    'sec-disclosures.json', 'sec-filing-windows.json', 'sec-m2-candidates.json',
    'sec-public-inputs.json', 'sec-qg-factors.json', 'sec-qgv2.json', 'sec-universe-qg.json',
    'sec-universe-shares.json', 'sec-valuation-inputs.json', 'universe-codes.json',
    'universe-domains.json',
)


def test_cli_missing_source_fails_without_exposing_paths_or_provider_text(tmp_path):
    out = tmp_path / 'fresh'
    out.mkdir()
    sentinel = out / 'app.js'
    sentinel.write_bytes(b'fresh code')
    result = subprocess.run([
        sys.executable, str(TOOL), '--archive', str(tmp_path / 'private-source-canary'),
        '--run-metadata', str(tmp_path / 'run.json'), '--artifact-metadata', str(tmp_path / 'artifact.json'),
        '--out', str(out),
    ], capture_output=True, text=True)
    assert result.returncode == 1
    assert result.stdout.startswith('REPLAY_20261020_FAILED reason=')
    assert 'private-source-canary' not in result.stdout + result.stderr
    assert result.stderr == ''
    assert sentinel.read_bytes() == b'fresh code'


@pytest.fixture
def replay():
    spec = importlib.util.spec_from_file_location('replay_pages_20261020', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metadata():
    linked = {'id': 39522288311, 'head_sha': '8c671ae4859bc509be228ec59b4d923f1bb2af43',
              'head_branch': 'claude/investment-system-top500-validation-alrugm'}
    run = {**linked, 'event': 'schedule', 'status': 'completed', 'conclusion': 'failure',
           'path': '.github/workflows/sec-daily-public-inputs.yml',
           'repository': {'full_name': 'kco994553-star/Investment-System1'},
           'head_repository': {'full_name': 'kco994553-star/Investment-System1'}}
    artifact = {'id': 12311543375, 'name': 'github-pages', 'size_in_bytes': 1862217,
                'digest': 'sha256:16a0af04725323edc624bc0ce503ab3700224c38d7df55cd604a9e42b22d0826',
                'expired': False, 'expires_at': '2026-10-22T00:50:43Z', 'workflow_run': linked}
    return run, artifact


def archive_bytes(files=None, extras=()):
    if files is None:
        files = {name: ('{ "synthetic": ' + json.dumps(name) + ', "observed": "2026-10-20" }\n').encode()
                 for name in DATA_FILES}
    contents = io.BytesIO()
    with tarfile.open(fileobj=contents, mode='w', format=tarfile.USTAR_FORMAT) as handle:
        entries = [('./' + name, body) for name, body in files.items()]
        entries += [('./app.js', b'old source code'), ('./manifest.json', b'{"old":true}')]
        entries += list(extras)
        for name, body in entries:
            if isinstance(name, tarfile.TarInfo):
                handle.addfile(name, io.BytesIO(body) if body else None)
            else:
                info = tarfile.TarInfo(name)
                info.size = len(body)
                handle.addfile(info, io.BytesIO(body))
    return contents.getvalue(), files


def setup_replay(tmp_path, replay, monkeypatch, body=None):
    baseline, files = archive_bytes()
    body = baseline if body is None else body
    # Only synthetic tests replace the pins. The CLI has no pin override.
    monkeypatch.setattr(replay, 'TAR_SHA256', hashlib.sha256(body).hexdigest())
    monkeypatch.setattr(replay, 'LEDGER_SHA256', hashlib.sha256(files['forward-validation-ledger.json']).hexdigest())
    archive = tmp_path / 'source.tar'
    archive.write_bytes(body)
    run, artifact = metadata()
    run_path, artifact_path = tmp_path / 'run.json', tmp_path / 'artifact.json'
    run_path.write_text(json.dumps(run))
    artifact_path.write_text(json.dumps(artifact))
    out = tmp_path / 'fresh'
    out.mkdir()
    (out / 'app.js').write_bytes(b'corrected canonical code')
    (out / 'manifest.json').write_bytes(b'{"fresh":true}')
    for name in DATA_FILES:
        (out / name).write_bytes(b'{"placeholder":true}')
    args = (archive, run_path, artifact_path, out)
    return args, files


def snapshot(out):
    return {p.name: p.read_bytes() for p in out.iterdir() if p.is_file() and not p.is_symlink()}


def test_restore_preserves_all_25_bytes_and_fresh_code_without_rewriting_observations(tmp_path, replay, monkeypatch):
    args, files = setup_replay(tmp_path, replay, monkeypatch)
    assert set(replay.DATA_FILES) == set(DATA_FILES)
    replay.restore(*args, now=NOW)
    out = args[-1]
    assert {name: (out / name).read_bytes() for name in DATA_FILES} == files
    assert (out / 'app.js').read_bytes() == b'corrected canonical code'
    assert (out / 'manifest.json').read_bytes() == b'{"fresh":true}'
    assert len(list(out.iterdir())) == 27


@pytest.mark.parametrize('which,path,value', [
    ('run', ('id',), 1), ('run', ('head_sha',), '0' * 40),
    ('run', ('head_branch',), 'other-branch'), ('run', ('event',), 'pull_request'),
    ('run', ('status',), 'in_progress'), ('run', ('conclusion',), 'success'),
    ('run', ('path',), '.github/workflows/cockpit-pages.yml'),
    ('run', ('repository', 'full_name'), 'other/repo'),
    ('run', ('head_repository', 'full_name'), 'other/repo'),
    ('artifact', ('id',), 1), ('artifact', ('name',), 'other-artifact'),
    ('artifact', ('size_in_bytes',), 10), ('artifact', ('digest',), 'sha256:' + '0' * 64),
    ('artifact', ('expired',), True), ('artifact', ('expired',), 'false'),
    ('artifact', ('expires_at',), '2026-10-21T11:00:00Z'),
    ('artifact', ('expires_at',), '2026-10-22T00:50:43'),
    ('artifact', ('workflow_run', 'id'), 1),
    ('artifact', ('workflow_run', 'head_sha'), '0' * 40),
    ('artifact', ('workflow_run', 'head_branch'), 'other-branch'),
])
def test_source_metadata_mismatch_blocks_all_writes(tmp_path, replay, monkeypatch, which, path, value):
    args, _ = setup_replay(tmp_path, replay, monkeypatch)
    file = args[1 if which == 'run' else 2]
    data = json.loads(file.read_text())
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    file.write_text(json.dumps(data))
    before = snapshot(args[-1])
    with pytest.raises(replay.ReplayError):
        replay.restore(*args, now=NOW)
    assert snapshot(args[-1]) == before


def test_digest_mismatch_and_expiration_boundary_fail_closed(tmp_path, replay, monkeypatch):
    args, _ = setup_replay(tmp_path, replay, monkeypatch)
    before = snapshot(args[-1])
    args[0].write_bytes(args[0].read_bytes() + b'tampered')
    with pytest.raises(replay.ReplayError, match='TAR_DIGEST_MISMATCH'):
        replay.restore(*args, now=NOW)
    assert snapshot(args[-1]) == before
    run, artifact = metadata()
    with pytest.raises(replay.ReplayError, match='SOURCE_EXPIRED'):
        replay.verify_source(run, artifact, now=datetime(2026, 10, 22, 0, 50, 43, tzinfo=timezone.utc))


@pytest.mark.parametrize('kind', ['traversal', 'absolute', 'nested', 'backslash', 'duplicate',
                                  'symlink', 'hardlink', 'fifo', 'device', 'directory', 'oversized'])
def test_adversarial_tar_members_never_touch_output_or_escape(tmp_path, replay, monkeypatch, kind):
    names = {'traversal': '../escape.json', 'absolute': str(tmp_path / 'escape.json'),
             'nested': 'subdir/data.json', 'backslash': '..\\escape.json', 'duplicate': 'data.json'}
    info = tarfile.TarInfo(names.get(kind, 'escape.json'))
    types = {'symlink': tarfile.SYMTYPE, 'hardlink': tarfile.LNKTYPE, 'fifo': tarfile.FIFOTYPE,
             'device': tarfile.CHRTYPE, 'directory': tarfile.DIRTYPE}
    info.type = types.get(kind, tarfile.REGTYPE)
    info.linkname = '../escape.json' if kind in ('symlink', 'hardlink') else ''
    body = b'{}' if info.isreg() else b''
    info.size = len(body)
    payload, _ = archive_bytes(extras=[(info, body)])
    args, _ = setup_replay(tmp_path, replay, monkeypatch, payload)
    if kind == 'oversized':
        monkeypatch.setattr(replay, 'MAX_FILE_BYTES', 1)
    before = snapshot(args[-1])
    with pytest.raises(replay.ReplayError):
        replay.restore(*args, now=NOW)
    assert snapshot(args[-1]) == before
    assert not (tmp_path / 'escape.json').exists()


@pytest.mark.parametrize('kind', ['missing', 'extra-json', 'invalid-json', 'duplicate-key', 'nonfinite', 'ledger-change'])
def test_data_validation_finishes_before_any_destination_write(tmp_path, replay, monkeypatch, kind):
    _, files = archive_bytes()
    files = deepcopy(files)
    if kind == 'missing':
        del files['macro-evidence.json']
    elif kind == 'extra-json':
        files['unexpected.json'] = b'{}'
    elif kind == 'invalid-json':
        files['macro-evidence.json'] = b'{'
    elif kind == 'duplicate-key':
        files['macro-evidence.json'] = b'{"x":1,"x":2}'
    elif kind == 'nonfinite':
        files['macro-evidence.json'] = b'{"x":NaN}'
    else:
        files['forward-validation-ledger.json'] = b'{"rewritten":true}'
    payload, _ = archive_bytes(files)
    args, _ = setup_replay(tmp_path, replay, monkeypatch, payload)
    before = snapshot(args[-1])
    with pytest.raises(replay.ReplayError):
        replay.restore(*args, now=NOW)
    assert snapshot(args[-1]) == before


@pytest.mark.parametrize('kind', ['zip', 'truncated', 'archive-symlink', 'output-symlink', 'destination-symlink',
                                  'destination-directory', 'metadata-duplicate-key'])
def test_unsafe_containers_and_filesystem_targets_fail_closed(tmp_path, replay, monkeypatch, kind):
    args, _ = setup_replay(tmp_path, replay, monkeypatch)
    archive, run_path, artifact_path, out = args
    sentinel = tmp_path / 'untouched'
    sentinel.write_bytes(b'private canary never overwritten')
    if kind == 'zip':
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zipped:
            zipped.writestr('../escape', b'bad')
            zipped.writestr('artifact.tar', archive.read_bytes())
        archive.write_bytes(buffer.getvalue())
        monkeypatch.setattr(replay, 'TAR_SHA256', hashlib.sha256(buffer.getvalue()).hexdigest())
    elif kind == 'truncated':
        archive.write_bytes(archive.read_bytes()[:600])
        monkeypatch.setattr(replay, 'TAR_SHA256', hashlib.sha256(archive.read_bytes()).hexdigest())
    elif kind == 'archive-symlink':
        archive.unlink()
        archive.symlink_to(sentinel)
    elif kind == 'output-symlink':
        alias = tmp_path / 'alias'
        alias.symlink_to(out, target_is_directory=True)
        args = (archive, run_path, artifact_path, alias)
    elif kind == 'metadata-duplicate-key':
        run_path.write_text('{"id":1,"id":39522288311}')
    else:
        destination = out / 'macro-evidence.json'
        destination.unlink()
        if kind == 'destination-symlink':
            destination.symlink_to(sentinel)
        else:
            destination.mkdir()
    before = snapshot(out)
    with pytest.raises(replay.ReplayError):
        replay.restore(*args, now=NOW)
    assert snapshot(out) == before
    assert sentinel.read_bytes() == b'private canary never overwritten'
    assert not (tmp_path / 'escape').exists()


class LiveResponse:
    def __init__(self, url, body, status=200, redirect=False):
        self.url, self.body, self.status = url, body, status
        self.redirect = redirect

    def geturl(self):
        return 'https://untrusted.example/' if self.redirect else self.url

    def read(self, n):
        return self.body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture
def deploy_check(tmp_path, replay, monkeypatch):
    baseline = {name: json.dumps({'baseline': name}).encode() for name in DATA_FILES}
    source = {name: json.dumps({'collected': name}).encode() for name in DATA_FILES}
    pins = {name: (hashlib.sha256(baseline[name]).hexdigest(), hashlib.sha256(source[name]).hexdigest())
            for name in DATA_FILES}
    monkeypatch.setattr(replay, 'DATA_HASHES', pins)
    out = tmp_path / 'candidate'
    out.mkdir()
    for name, body in source.items():
        (out / name).write_bytes(body)
    return out, baseline, source


@pytest.mark.parametrize('state', ['baseline', 'source', 'mixed'])
def test_deploy_checks_all_25_live_files_without_changing_candidate(deploy_check, replay, state):
    out, baseline, source = deploy_check
    live = baseline if state == 'baseline' else source if state == 'source' else {
        name: (source if i % 2 else baseline)[name] for i, name in enumerate(DATA_FILES)}
    requests = []
    before = snapshot(out)

    def fetch(request, *, timeout):
        requests.append(request)
        assert request.full_url.startswith('https://kco994553-star.github.io/Investment-System1/')
        assert '?replay-check=' in request.full_url
        assert request.get_header('Cache-control') == 'no-cache, no-store'
        assert request.get_header('Accept-encoding') == 'identity'
        assert timeout == 20
        name = request.full_url.split('/')[-1].split('?')[0]
        return LiveResponse(request.full_url, live[name])

    replay.check_deploy(out, open_response=fetch)
    assert len(requests) == 25
    assert {r.full_url.split('/')[-1].split('?')[0] for r in requests} == set(DATA_FILES)
    assert snapshot(out) == before


@pytest.mark.parametrize('name', DATA_FILES)
@pytest.mark.parametrize('side', ['candidate', 'live'])
def test_changed_data_in_any_of_the_25_files_stops_deploy(deploy_check, replay, name, side):
    out, baseline, source = deploy_check
    changed = b'{"newer_or_changed":true}'
    calls = []
    if side == 'candidate':
        (out / name).write_bytes(changed)
    else:
        baseline[name] = changed
    before = snapshot(out)

    def fetch(request, **_):
        calls.append(request)
        key = request.full_url.split('/')[-1].split('?')[0]
        return LiveResponse(request.full_url, baseline[key])

    with pytest.raises(replay.ReplayError, match='CANDIDATE_DATA_MISMATCH' if side == 'candidate' else 'LIVE_DATA_UNEXPECTED'):
        replay.check_deploy(out, open_response=fetch)
    if side == 'candidate':
        assert calls == []
    assert snapshot(out) == before


@pytest.mark.parametrize('kind', ['404', '500', '304', 'network', 'redirect', 'oversized', 'empty', 'invalid-json'])
def test_live_read_uncertainty_fails_closed_without_mutation(deploy_check, replay, kind):
    out, baseline, source = deploy_check
    before = snapshot(out)

    def fetch(request, **_):
        if kind in ('404', '500'):
            raise urllib.error.HTTPError(request.full_url, int(kind), 'private canary', None, None)
        if kind == 'network':
            raise urllib.error.URLError('private canary')
        body = b'x' * (replay.MAX_FILE_BYTES + 1) if kind == 'oversized' else b'' if kind == 'empty' else b'{' if kind == 'invalid-json' else baseline[DATA_FILES[0]]
        return LiveResponse(request.full_url, body, status=304 if kind == '304' else 200, redirect=kind == 'redirect')

    with pytest.raises(replay.ReplayError) as error:
        replay.check_deploy(out, open_response=fetch)
    assert 'private canary' not in str(error.value)
    assert snapshot(out) == before


@pytest.mark.parametrize('kind', ['missing', 'symlink', 'directory'])
def test_missing_or_unsafe_candidate_ledger_stops_before_network(deploy_check, replay, kind):
    out, baseline, source = deploy_check
    ledger = out / 'forward-validation-ledger.json'
    ledger.unlink()
    if kind == 'symlink':
        ledger.symlink_to(out / DATA_FILES[0])
    elif kind == 'directory':
        ledger.mkdir()
    with pytest.raises(replay.ReplayError):
        replay.check_deploy(out, open_response=lambda *_args, **_kwargs: pytest.fail('candidate rejected before network'))


def test_data_pins_cover_exactly_25_files_and_known_ledger(replay):
    assert set(replay.DATA_HASHES) == set(DATA_FILES)
    assert replay.DATA_HASHES['forward-validation-ledger.json'][1] == replay.LEDGER_SHA256
    for pair in replay.DATA_HASHES.values():
        assert len(pair) == 2
        assert all(len(value) == 64 and set(value) <= set('0123456789abcdef') for value in pair)


def test_deploy_check_cli_has_no_source_override_or_secret_output(tmp_path, replay, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(replay, 'check_deploy', lambda out: calls.append(out))
    assert replay.main(['--check-deploy', '--out', str(tmp_path)]) == 0
    assert calls == [tmp_path]
    assert 'DEPLOY_CHECKED files=25' in capsys.readouterr().out
    def fail(_out):
        raise OSError('private canary')
    monkeypatch.setattr(replay, 'check_deploy', fail)
    assert replay.main(['--check-deploy', '--out', str(tmp_path)]) == 1
    assert capsys.readouterr().out == 'REPLAY_20261020_FAILED reason=UNEXPECTED_ERROR\n'
    with pytest.raises(SystemExit) as error:
        replay.main(['--check-deploy', '--out', str(tmp_path), '--archive', 'private canary'])
    assert error.value.code == 2
    assert capsys.readouterr().err == 'REPLAY_20261020_FAILED reason=ARGUMENTS_INVALID\n'


def test_workflow_replay_is_opt_in_read_only_and_keeps_the_existing_deploy_gate():
    workflow = (ROOT.parent / '.github/workflows/cockpit-pages.yml').read_text()
    source_job = workflow.split('\n  replay_source:\n', 1)[1].split('\n  build:\n', 1)[0]
    build, deploy = workflow.split('\n  build:\n', 1)[1].split('\n  deploy:\n', 1)
    input_block = workflow.split('      replay_20261020:\n', 1)[1].split('\npermissions:', 1)[0]
    assert '        type: boolean' in input_block.splitlines() and '        default: false' in input_block.splitlines()
    # No Actions permission or credential is exposed to PR build scripts/dependencies.
    assert '\npermissions:\n  contents: read\njobs:\n' in workflow
    assert '    permissions:\n      actions: read\n' in source_job
    assert workflow.count('actions: read') == 1 and 'write' not in source_job
    assert 'permissions:' not in build and 'github.token' not in build and 'GH_TOKEN' not in build
    assert "if: github.event_name == 'workflow_dispatch' && inputs.replay_20261020 && github.ref_name == 'claude/investment-system-top500-validation-alrugm'" in source_job
    assert 'actions/checkout@' not in source_job and 'pip install' not in source_job and 'npm install' not in source_job
    assert '    needs: replay_source\n' in build
    assert "if: ${{ !cancelled() && (needs.replay_source.result == 'success' || (needs.replay_source.result == 'skipped' && !inputs.replay_20261020)) }}" in build
    steps = build.split('\n      - ')[1:]
    preserve = next(step for step in steps if step.startswith('name: Preserve previously published'))
    assert "if: github.event_name == 'workflow_dispatch' && !inputs.replay_20261020" in preserve
    selected = [step for step in steps if "if: github.event_name == 'workflow_dispatch' && inputs.replay_20261020" in step]
    assert len(selected) == 2
    handoff, restore = selected
    source, download, upload = source_job.split('\n      - ')[1:]
    assert 'gh api --method GET repos/kco994553-star/Investment-System1/actions/runs/39522288311' in source
    assert 'gh api --method GET repos/kco994553-star/Investment-System1/actions/artifacts/12311543375' in source
    assert '--jq' in source and 'head_repository: {full_name: .head_repository.full_name}' in source
    assert "artifact-ids: '12311543375'" in download and "run-id: '39522288311'" in download
    assert 'github-token: ${{ github.token }}' in download
    # With artifact-ids (rather than name), v4 otherwise adds a github-pages subdirectory.
    assert 'merge-multiple: true' in download
    assert 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02' in upload
    assert 'name: replay-20261020-source-${{ github.run_attempt }}' in upload
    assert 'artifact_id: ${{ steps.handoff.outputs.artifact-id }}' in source_job
    assert 'artifact-ids: ${{ needs.replay_source.outputs.artifact_id }}' in handoff
    assert 'merge-multiple: true' in handoff
    assert 'retention-days: 1' in upload and 'if-no-files-found: error' in upload
    assert 'github-token:' not in handoff and 'run-id:' not in handoff
    assert restore.index('replay_pages_20261020.py') < restore.index('pages_artifact_guard.py')
    replay_steps = source_job + ''.join(selected)
    assert '--live' not in replay_steps and 'forward_validation_ledger.py' not in replay_steps
    assert build.index('replay_pages_20261020.py') < build.index('ci_browser_tests.txt') < build.index('actions/upload-pages-artifact@')
    assert '    needs: build\n' in deploy
    assert '    concurrency:\n      group: checked-cockpit-pages\n      cancel-in-progress: false\n' in deploy
    assert '    permissions:\n      contents: read\n      pages: write\n      id-token: write\n' in deploy
    assert deploy.index('pages_freshness_guard.py') < deploy.index('--check-deploy') < deploy.index('actions/deploy-pages@')
    final_check = deploy.split('\n      - ')[-2]
    assert 'if: inputs.replay_20261020' in final_check
    assert 'replay_pages_20261020.py --check-deploy --out "$RUNNER_TEMP/deploy-check"' in final_check
