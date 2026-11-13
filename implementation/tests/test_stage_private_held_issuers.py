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


# The input connection repair comparison (Codex #527): pinned, its schema and treatment, and it names this delivery's result.
REPAIR = json.loads((ROOT / 'tests' / 'fixtures' / 'input_repair_comparison' / 'outputs.json').read_text())


def _repair(tmp_path, delivery, *, match=True, treatment='INPUT_CONNECTION_REPAIR'):
    x = next(c['output'] for c in REPAIR['cases'] if c['id'] == 'peer_minimum')
    x = dict(x, treatment=treatment)
    if match:
        cov = json.loads((delivery / 'coverage.json').read_bytes())['scopes']['operating']['context']
        x = dict(x, after_input_hash=cov['result_identity']['input_hash'], denominator=cov['population']['denominator'], valuation_date=cov['valuation_date'])
    path = tmp_path / 'repair.json'
    path.write_bytes(json.dumps(x).encode())
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_input_repair_comparison_is_staged_beside_the_delivery_byte_for_byte(tmp_path, capsys):
    delivery, data = _setup(tmp_path)
    path, pin = _repair(tmp_path, delivery)
    assert tool.main(['--delivery', str(delivery), '--manifest-sha256', PIN, '--data-dir', str(data), '--input-repair', str(path), '--input-repair-sha256', pin]) == 0
    assert 'input_repair sha256=' + pin in capsys.readouterr().out
    assert (data / 'classification' / 'expanded' / 'input-repair-comparison.json').read_bytes() == path.read_bytes()


@pytest.mark.parametrize('kind, code', [('other_result', 'REPAIR_RESULT_MISMATCH'), ('treatment', 'REPAIR_SCHEMA'), ('pin', 'REPAIR_PIN_MISMATCH'), ('no_pin', 'REPAIR_PIN_REQUIRED')])
def test_input_repair_comparison_refusals_keep_the_existing_copy(tmp_path, kind, code):
    delivery, data = _setup(tmp_path)
    assert tool.main(['--delivery', str(delivery), '--manifest-sha256', PIN, '--data-dir', str(data)]) == 0
    before = sorted(p.relative_to(data).as_posix() for p in (data / 'classification' / 'expanded').rglob('*') if p.is_file())
    path, pin = _repair(tmp_path, delivery, match=kind != 'other_result', treatment='FACTOR_WEIGHT_CHANGE' if kind == 'treatment' else 'INPUT_CONNECTION_REPAIR')
    if kind == 'treatment':
        pin = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(tool.StageError, match=code):
        tool.stage(delivery, PIN, data, path, None if kind == 'no_pin' else ('c' * 64 if kind == 'pin' else pin))
    assert sorted(p.relative_to(data).as_posix() for p in (data / 'classification' / 'expanded').rglob('*') if p.is_file()) == before


# The reference population research view (Codex #528): pinned, its schema, and its evaluation population is this delivery's result.
RVIEW = json.loads((ROOT / 'docs' / 'research' / 'sector_qgv' / 'reference-synthetic' / 'view.json').read_text())


def _reference(tmp_path, delivery, *, match=True, adoption='NOT_ADOPTED'):
    x = json.loads(json.dumps(RVIEW))
    x['operating_adoption'] = adoption
    if match:
        ctx = json.loads((delivery / 'coverage.json').read_bytes())['scopes']['operating']['context']
        e = x['evaluation_population']
        e.update(id=ctx['population']['id'], version=ctx['population']['version'], members_hash=ctx['population']['members_hash'],
                 code_rows=ctx['population']['denominator'], valuation_date=ctx['valuation_date'], input_hash=ctx['result_identity']['input_hash'])
        x['bindings']['config_hash'] = ctx['result_identity']['config_hash']
    path = tmp_path / 'reference-view.json'
    path.write_bytes(json.dumps(x).encode())
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_reference_view_is_staged_beside_the_delivery_byte_for_byte(tmp_path, capsys):
    delivery, data = _setup(tmp_path)
    path, pin = _reference(tmp_path, delivery)
    assert tool.main(['--delivery', str(delivery), '--manifest-sha256', PIN, '--data-dir', str(data), '--reference-view', str(path), '--reference-view-sha256', pin]) == 0
    assert 'reference_view sha256=' + pin in capsys.readouterr().out
    assert (data / 'classification' / 'expanded' / 'reference-view.json').read_bytes() == path.read_bytes()


@pytest.mark.parametrize('kind, code', [('other_result', 'REFERENCE_RESULT_MISMATCH'), ('adopted', 'REFERENCE_SCHEMA'), ('pin', 'REFERENCE_PIN_MISMATCH'), ('no_pin', 'REFERENCE_PIN_REQUIRED')])
def test_reference_view_refusals_keep_the_existing_copy(tmp_path, kind, code):
    delivery, data = _setup(tmp_path)
    assert tool.main(['--delivery', str(delivery), '--manifest-sha256', PIN, '--data-dir', str(data)]) == 0
    before = sorted(p.relative_to(data).as_posix() for p in (data / 'classification' / 'expanded').rglob('*') if p.is_file())
    path, pin = _reference(tmp_path, delivery, match=kind != 'other_result', adoption='ADOPTED' if kind == 'adopted' else 'NOT_ADOPTED')
    with pytest.raises(tool.StageError, match=code):
        tool.stage(delivery, PIN, data, reference=path, reference_pin=None if kind == 'no_pin' else ('c' * 64 if kind == 'pin' else pin))
    assert sorted(p.relative_to(data).as_posix() for p in (data / 'classification' / 'expanded').rglob('*') if p.is_file()) == before
