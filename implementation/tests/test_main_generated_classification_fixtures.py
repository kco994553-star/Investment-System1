"""Main's generated copies of Codex #525 outputs stay equal to a fresh call of Codex's own code (owner 2026-11-09 queue item 5)."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def _check(tool):
    r = subprocess.run([sys.executable, str(ROOT / 'implementation' / 'tools' / tool), '--check'], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_common_taxonomy_js_is_codex_current_taxonomy():
    _check('common_taxonomy_main.py')


def test_industry_macro_main_outputs_are_codex_query_outputs():
    _check('industry_macro_main_fixture.py')


def test_input_repair_comparison_outputs_are_codex_comparison_outputs():
    _check('input_repair_comparison_fixture.py')
