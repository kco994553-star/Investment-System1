"""stage_private_industry_macro: pinned, context-checked byte copy (Codex #525 synthetic output)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import stage_private_industry_macro as tool  # noqa: E402

OUT = json.loads((ROOT / 'tests' / 'fixtures' / 'industry_macro_main' / 'outputs.json').read_text())['cases'][0]['output']


def _setup(tmp_path, view_extra=None):
    q = tmp_path / 'query.json'
    q.write_bytes(json.dumps(OUT, ensure_ascii=False).encode())
    data = tmp_path / 'data'
    (data / 'classification').mkdir(parents=True)
    view = dict(OUT['classification_context'], **(view_extra or {}))
    (data / 'classification' / 'view.json').write_text(json.dumps(view))
    return q, hashlib.sha256(q.read_bytes()).hexdigest(), data


def test_copies_byte_for_byte(tmp_path):
    q, pin, data = _setup(tmp_path)
    assert tool.stage(q, pin, data)['company_rows'] == 2
    assert (data / 'classification' / 'industry_macro.json').read_bytes() == q.read_bytes()


@pytest.mark.parametrize('extra, pin_ok, code', [({}, False, 'PIN_MISMATCH'), ({'classification_hash': 'f' * 64}, True, 'CLASSIFICATION_CONTEXT_MISMATCH:classification_hash'),
                                                 ({'valuation_date': '2026-11-05'}, True, 'CLASSIFICATION_CONTEXT_MISMATCH:valuation_date')])
def test_refuses_and_writes_nothing(tmp_path, extra, pin_ok, code):
    q, pin, data = _setup(tmp_path, extra)
    with pytest.raises(tool.StageError, match=code):
        tool.stage(q, pin if pin_ok else 'a' * 64, data)
    assert not (data / 'classification' / 'industry_macro.json').exists()


def test_public_data_dir_refused(tmp_path):
    q, pin, _ = _setup(tmp_path)
    with pytest.raises(tool.StageError, match='DATA_DIR_INSIDE_PUBLIC_REPOSITORY'):
        tool.stage(q, pin, ROOT / 'tests')
