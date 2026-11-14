"""Stage QGV 555 saved delivery (owner 2026-11-14 「#537 최신 미리보기·Top500 표시 계약 인수」 §3, §6).

On Codex's own synthetic delivery (tests/fixtures/qgv555, produced by qgv_555_delivery.artifacts on qgv_555.fixture()) laid out like
the private handoff: the pinned manifest, members byte for byte, independent anchors computed from the input files the job pins,
Codex validate(), and the whole-or-nothing swap that keeps the previous good copy on any failure."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import stage_private_qgv555 as stage  # noqa: E402
import qgv555_private_fixture as fixture  # noqa: E402
from investment_system.research import qgv_555  # noqa: E402

FIX = ROOT / 'tests' / 'fixtures' / 'qgv555'
PRODUCER = 'a' * 40
HANDOFF = 'b' * 8 + ':handoffs/synthetic'
HM = 'c' * 64


def sha(b):
    return hashlib.sha256(b).hexdigest()


def layout(tmp: Path) -> tuple[Path, str]:
    """The private handoff's shape around Codex's synthetic delivery (tools/qgv555_private_fixture.py)."""
    return fixture.layout(tmp)


def run(root, ms, data):
    files, receipt = stage.check(root, 'operating504', ms, producer_sha=PRODUCER, handoff=HANDOFF, handoff_manifest_sha256=HM)
    return stage.stage(data, 'operating504', files, receipt), receipt


@pytest.fixture()
def env(tmp_path):
    if not (FIX / 'manifest.json').exists():
        pytest.skip('Codex synthetic delivery not present')
    root, ms = layout(tmp_path)
    return root, ms, tmp_path / 'data'


def test_stages_byte_for_byte_with_independent_anchors(env):
    root, ms, data = env
    final, receipt = run(root, ms, data)
    manifest = json.loads((root / 'r2-operating504' / 'manifest.json').read_bytes())
    for f in manifest['files']:
        assert sha((final / f['path']).read_bytes()) == f['sha256']
    assert (final / 'manifest.json').read_bytes() == (root / 'r2-operating504' / 'manifest.json').read_bytes()
    e, ref = qgv_555.fixture()
    assert receipt['expected_evaluation'] == qgv_555.identity(e)
    assert receipt['expected_references'] == {'U1-555': qgv_555.identity(ref), 'S1-555': qgv_555.identity(ref)}
    assert receipt['stored_result_only'] is True and receipt['schema_version'] == 'qgv-555-stage/1'
    assert json.loads((final / 'stage.json').read_text()) == receipt
    assert sorted(p.name for p in final.iterdir()) == sorted([f['path'] for f in manifest['files']] + ['manifest.json', 'stage.json'])


@pytest.mark.parametrize('defect', ['manifest_pin', 'member_byte', 'evaluation_input', 'reference_input', 'evaluation_anchor', 'model_id'])
def test_refusal_keeps_the_previous_good_copy(env, defect):
    root, ms, data = env
    final, _ = run(root, ms, data)
    before = {p.name: p.read_bytes() for p in final.iterdir()}
    src, inputs = root / 'r2-operating504', root / 'inputs-v3'
    if defect == 'manifest_pin':
        ms = 'd' * 64
    elif defect == 'member_byte':
        p = next(src.glob('distribution-*.json'))
        p.write_bytes(p.read_bytes().replace(b'"rows"', b'"rowz"', 1))
    elif defect == 'evaluation_input':
        (inputs / 'operating.json').write_bytes(b'{}')
    elif defect == 'reference_input':
        (inputs / 'operating_reference.json').write_bytes(b'{}')
    elif defect in ('evaluation_anchor', 'model_id'):
        # A job naming other (self-consistent) inputs: the delivery's anchors no longer match → Codex validate refuses.
        e, ref = qgv_555.fixture(n=22)
        job = json.loads((inputs / 'operating504-job.json').read_text())
        target = 'operating.json' if defect == 'evaluation_anchor' else 'operating_reference.json'
        b = json.dumps(e if defect == 'evaluation_anchor' else ref).encode()
        (inputs / target).write_bytes(b)
        job['evaluation' if defect == 'evaluation_anchor' else 'reference'].update(sha256=sha(b), size=len(b))
        (inputs / 'operating504-job.json').write_text(json.dumps(job))
    with pytest.raises(stage.Refused):
        run(root, ms, data)
    assert {p.name: p.read_bytes() for p in final.iterdir()} == before


def test_failed_swap_restores_the_previous_copy(env, monkeypatch):
    root, ms, data = env
    final, _ = run(root, ms, data)
    before = {p.name: p.read_bytes() for p in final.iterdir()}
    files, receipt = stage.check(root, 'operating504', ms, producer_sha=PRODUCER, handoff=HANDOFF, handoff_manifest_sha256=HM)
    real = stage.os.replace
    calls = []

    def flaky(a, b):
        calls.append((a, b))
        if len(calls) == 2:
            raise OSError('swap failed')
        return real(a, b)
    monkeypatch.setattr(stage.os, 'replace', flaky)
    with pytest.raises(OSError):
        stage.stage(data, 'operating504', files, {**receipt, 'files': -1})
    monkeypatch.setattr(stage.os, 'replace', real)
    assert {p.name: p.read_bytes() for p in final.iterdir()} == before
    assert not list((data / 'classification' / 'q555').glob('.*'))


def test_data_dir_inside_the_public_repo_is_refused(env):
    root, ms, _ = env
    with pytest.raises(stage.Refused):
        run(root, ms, ROOT / 'tmp-q555-should-not-exist')


def test_scope_directory_layouts(env):
    """r2 holds r2-<scope>/, the FY debt delivery (raw c0a8bf51) <scope>/; either alone is read, both at once is refused."""
    root, ms, data = env
    (root / 'r2-operating504').rename(root / 'operating504')
    final, receipt = run(root, ms, data)
    assert receipt['manifest_sha256'] == ms and (final / 'index.json').exists()
    shutil.copytree(root / 'operating504', root / 'r2-operating504')
    with pytest.raises(stage.Refused, match='SCOPE_DIRECTORY'):
        run(root, ms, data)
