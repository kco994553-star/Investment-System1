"""stage_private_held_issuers: byte-for-byte staging of the Codex #524 held issuer delivery, pinned and anchored to the staged summary.

Codex's public synthetic delivery only (tests/fixtures/held_issuer_shards)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import stage_private_held_issuers as tool  # noqa: E402

FIX = ROOT / 'tests' / 'fixtures' / 'held_issuer_shards'
PIN = hashlib.sha256((FIX / 'manifest.json').read_bytes()).hexdigest()


def _setup(tmp_path):
    delivery = tmp_path / 'delivery'
    for name in ('manifest.json', 'expanded-index.json', 'coverage.json', 'expanded-detail/55.json', 'expanded-detail/df.json'):
        (delivery / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIX / name, delivery / name)
    data = tmp_path / 'data'
    (data / 'classification').mkdir(parents=True)
    shutil.copyfile(FIX / 'source-summary.json', data / 'classification' / 'expanded_summary.json')
    return delivery, data


def test_stages_every_file_byte_for_byte(tmp_path, capsys):
    delivery, data = _setup(tmp_path)
    assert tool.main(['--delivery', str(delivery), '--manifest-sha256', PIN, '--data-dir', str(data)]) == 0
    out = capsys.readouterr().out
    assert 'issuers=2 shards=2 files=5' in out and 'kind=SYNTHETIC' in out and PIN in out
    for p in delivery.rglob('*.json'):
        rel = p.relative_to(delivery)
        assert (data / 'classification' / 'expanded' / rel).read_bytes() == p.read_bytes()


@pytest.mark.parametrize('change, code', [
    (lambda d, data: None, None),
    (lambda d, data: (d / 'expanded-detail' / 'df.json').unlink(), 'DELIVERY_REFUSED'),
    (lambda d, data: (d / 'extra.json').write_bytes(b'{}'), 'DELIVERY_REFUSED'),
    (lambda d, data: (d / 'coverage.json').write_bytes((d / 'coverage.json').read_bytes().replace(b'NOT_MEASURED', b'MEASURED')), 'DELIVERY_REFUSED'),
    (lambda d, data: (data / 'classification' / 'expanded_summary.json').write_bytes(b'{"calculation_counts":{}}'), 'SUMMARY_MISMATCH:sha256'),
    (lambda d, data: (data / 'classification' / 'expanded_summary.json').unlink(), 'SUMMARY_NOT_STAGED'),
])
def test_refuses_before_writing_and_keeps_the_existing_copy(tmp_path, change, code):
    delivery, data = _setup(tmp_path)
    assert tool.main(['--delivery', str(delivery), '--manifest-sha256', PIN, '--data-dir', str(data)]) == 0
    before = {p.relative_to(data).as_posix(): p.read_bytes() for p in (data / 'classification' / 'expanded').rglob('*') if p.is_file()}
    change(delivery, data)
    if code is None:
        return
    with pytest.raises(tool.StageError) as e:
        tool.stage(delivery, PIN, data)
    assert str(e.value).startswith(code)
    after = {p.relative_to(data).as_posix(): p.read_bytes() for p in (data / 'classification' / 'expanded').rglob('*') if p.is_file()}
    assert after == before


def test_the_pin_must_name_the_manifest(tmp_path):
    delivery, data = _setup(tmp_path)
    with pytest.raises(tool.StageError, match='MANIFEST_PIN_MISMATCH'):
        tool.stage(delivery, 'b' * 64, data)
    with pytest.raises(tool.StageError, match='PIN_INVALID'):
        tool.stage(delivery, 'B' * 64, data)
    assert not (data / 'classification' / 'expanded').exists()


def test_a_summary_with_another_held_scope_is_refused(tmp_path):
    delivery, data = _setup(tmp_path)
    summary = json.loads((FIX / 'source-summary.json').read_bytes())
    summary['calculation_counts']['scopes']['held_financial_subsample']['valuation_date'] = '2026-11-05'
    raw = json.dumps(summary).encode()
    (data / 'classification' / 'expanded_summary.json').write_bytes(raw)
    with pytest.raises(tool.StageError, match='SUMMARY_MISMATCH:sha256'):
        tool.stage(delivery, PIN, data)


def test_oversize_file_and_public_data_dir_are_refused(tmp_path):
    delivery, data = _setup(tmp_path)
    (delivery / 'expanded-detail' / 'df.json').write_bytes(b' ' * (tool.MAX_BYTES + 1))
    with pytest.raises(tool.StageError, match='FILE_TOO_LARGE'):
        tool.stage(delivery, PIN, data)
    with pytest.raises(tool.StageError, match='DATA_DIR_INSIDE_PUBLIC_REPOSITORY'):
        tool.stage(delivery, PIN, ROOT / 'tests')
