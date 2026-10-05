"""Branch spelling must not hide a Track C subject; no outside-scope PASS."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'tools/integration'


def tool():
    p = TOOLS / 'track_c_fpia_applicability.py'
    assert p.exists(), 'branch-independent applicability is not implemented'
    sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location('applicability_under_test', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


@pytest.fixture
def history(tmp_path):
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'user.email', 'fixture@example.invalid')
    git(tmp_path, 'config', 'user.name', 'fixture')
    (tmp_path / 'plain.py').write_text('x = 1\n')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'pre Track C')
    before = git(tmp_path, 'rev-parse', 'HEAD')
    p = tmp_path / 'src/protected_area/a.py'
    p.parent.mkdir(parents=True)
    p.write_text('x = 2\n')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'Track C reference')
    reference = git(tmp_path, 'rev-parse', 'HEAD')
    return tmp_path, before, reference


def assess(history, subject):
    repo, _, reference = history
    return tool().subject_decision(repo, reference, subject,
        lambda p: p.startswith('src/protected_area/'),
        {'package.protected_area'})


def test_reference_descendant_applies_regardless_of_branch_name(history):
    repo, _, reference = history
    git(repo, 'branch', '-m', 'ordinary-owner-branch')
    assert assess(history, reference)['status'] == 'APPLIES'


def test_pre_track_c_is_not_run_never_pass(history):
    result = assess(history, history[1])
    assert result['status'] == 'OUTSIDE_SCOPE_NOT_RUN'
    assert result['fpia_status'] == 'NOT_RUN'
    assert result['integration_acceptance'] == 'BLOCKED'


@pytest.mark.parametrize('source', [
    'import package.protected_area\n',
    'from package import protected_area\n',
    'from package.protected_area import a\n',
    'import importlib\nimportlib.import_module("package.protected_area.a")\n',
    'import importlib\nimportlib.import_module(module_name)\n',
    'import importlib\nf = importlib.import_module\nf(name)\n',
    '__import__(name)\n',
    'from . import protected_area\n',
    'from .protected_area import a\n',
    'getattr(__builtins__, "__" + "import__")(name)\n',
    'this is ( invalid\n',
])
def test_unmerged_import_or_ambiguous_source_fails_closed(history, source):
    repo, before, _ = history
    git(repo, 'checkout', '-q', before)
    (repo / 'foreign.py').write_text(source)
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'foreign source')
    assert assess(history, git(repo, 'rev-parse', 'HEAD'))['status'] == 'BLOCKED'


def test_squashed_namespace_content_fails_closed(history):
    repo, before, _ = history
    git(repo, 'checkout', '-q', before)
    p = repo / 'src/protected_area/new.py'
    p.parent.mkdir(parents=True)
    p.write_text('x = 3\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'non merge preserving')
    assert assess(history, git(repo, 'rev-parse', 'HEAD'))['status'] == 'BLOCKED'


def test_unknown_reference_never_outside_scope(history):
    repo, before, _ = history
    assert tool().subject_decision(repo, 'f'*40, before, lambda _: False,
                                   {'package.protected_area'})['status'] == 'UNAVAILABLE'


def test_workflow_has_no_branch_spelling_filter():
    text = (TOOLS.parents[2] / '.github/workflows/track-c-fpia.yml').read_text()
    assert 'startsWith(' not in text
    assert 'track_c_fpia_applicability.py' in text
    assert 'ref: ${{ github.workflow_sha }}' in text
    assert 'path: .fpia-verifier' in text
    assert 'python .fpia-verifier/implementation/tools/integration/track_c_fpia_applicability.py --repo .' in text
    assert 'track_c_fpia_ci_receipt.py --repo .fpia-verifier' in text
    assert "steps.applicability.outputs.applies == 'true'" in text


@pytest.mark.parametrize('filename,mode', [('launcher.pyw', '100644'), ('launcher', '100755')])
def test_unclassified_executable_blocks(history, filename, mode):
    repo, before, _ = history
    git(repo, 'checkout', '-q', before)
    p = repo / filename
    p.write_text('#!/usr/bin/python\nimport package.protected_area\n')
    if mode == '100755':
        p.chmod(0o755)
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'executable')
    assert assess(history, git(repo, 'rev-parse', 'HEAD'))['status'] == 'BLOCKED'


def test_authenticated_reference_is_derived_not_supplied(tmp_path, monkeypatch):
    from tests import integration_fpia_testkit as tk
    tool()
    import track_c_fpia as fpia
    w = tk.variant(tmp_path)
    monkeypatch.setitem(fpia.DEFAULT_OPTIONS, 'authority_remote', str(w.repo))
    result = tool().authenticated_preflight(w.repo, w.c['T0'], w.c['G0'], tk.TEST_CDR)
    assert result['authority']['status'] == 'PASS'
    assert result['reference'] == w.c['R0']
    assert result['status'] == 'APPLIES'
    assert result['integration_acceptance'] == 'BLOCKED'


def test_unauthenticated_register_cannot_skip_audit(tmp_path, monkeypatch):
    from tests import integration_fpia_testkit as tk
    tool()
    import track_c_fpia as fpia
    w = tk.variant(tmp_path)
    monkeypatch.setitem(fpia.DEFAULT_OPTIONS, 'authority_remote', str(w.repo))
    result = tool().authenticated_preflight(w.repo, w.c['T0'], w.c['R0'], tk.TEST_CDR)
    assert result['status'] == 'UNAVAILABLE'
    assert result['fpia_status'] == 'NOT_RUN'
