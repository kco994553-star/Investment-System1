import hashlib
import json
from pathlib import Path
import subprocess
import sys

from investment_system.qgv import qgv_v2 as q
from investment_system.research import operational_coverage as c


def row(qv=70, gv=60, vv=50):
    return {"cik": "0000000001", "axes": {a: {"score": v, "reason": None if v is not None else "AXIS_NOT_PUBLISHED"} for a, v in zip("QGV", (qv, gv, vv))},
            "factors": {f: {"score": 50, "reason": None} for f in q.FACTORS},
            "type_weights": {"Q": 34, "G": 33, "V": 33}, "value_trap_gate": False,
            "total_reason": None, "total": 60, "in_cross_section": True}


def test_factor_counts_do_not_infer_from_total_and_target_is_not_denominator():
    a, b = row(), row(vv=None)
    b['factors']['v_fcf_yield'] = {'score': None, 'reason': 'FINANCIAL_PROFILE_V_NOT_DEFINED'}
    a['factors']['q_moat_proxy'] = {'score': None, 'reason': 'SEC_FACTOR_NOT_AVAILABLE'}
    b['total'] = 65
    result = c.summarize_rows({'NYSE:A': a, 'NYSE:B': b, 'TARGET:a': row()}, fallback={'Q': 34, 'G': 33, 'V': 33})
    assert result['denominator']['count'] == 2
    assert result['denominator']['published_rows'] == 3
    assert result['denominator']['unique_issuer_ciks'] == 1
    assert result['denominator']['unique_securities'] is None
    assert result['factors']['q_moat_proxy']['valid'] == 1
    assert result['factors']['v_fcf_yield']['not_applicable'] == 1
    assert result['axes']['V']['valid'] == 1
    assert result['all_axes']['valid'] == 1
    assert result['presets']['balanced']['valid'] == 2
    assert result['presets']['value']['valid'] == 1
    assert result['presets']['user-preset/defensive@0.1']['valid'] == 2


def test_missing_type_or_stopped_row_is_not_filled_by_a_preset():
    a, b = row(), row()
    a['type_weights'] = None
    b['total_reason'] = 'CALC_VERSION_MISMATCH'
    result = c.summarize_rows({'NYSE:A': a, 'NYSE:B': b}, fallback={'Q': 34, 'G': 33, 'V': 33})
    p = result['presets']['balanced']
    assert p['valid'] is None and p['known_valid'] == 0 and p['unknown'] == 1
    assert p['reasons'] == {'TYPE_WEIGHTS_NOT_LINKED': 1, 'CALC_VERSION_MISMATCH': 1}


def test_gate_and_available_weight_follow_engine_total_eligibility():
    a = row(qv=None, gv=None, vv=90)
    a['value_trap_gate'] = True
    result = c.summarize_rows({'NYSE:A': a}, fallback={'Q': 34, 'G': 33, 'V': 33})
    assert result['presets']['value']['valid'] == 0
    assert result['presets']['value']['reasons'] == {'AXIS_WEIGHT_INSUFFICIENT': 1}


def test_archive_cli_records_hash_and_preserves_missing_engine_proof(tmp_path):
    root = Path(__file__).resolve().parents[1]
    vectors = json.loads((root / 'tests/fixtures/qgv_official_vectors_v1.json').read_text())
    archive = tmp_path / 'archive.json'
    archive.write_text(vectors['base_text'])
    output = tmp_path / 'coverage.json'
    args = [sys.executable, str(root / 'tools/operational_qgv_coverage.py'), '--archive', str(archive), '--output', str(output)]
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report['source_sha256'] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert report['denominator']['count'] == 30  # fixture membership, never a fixed 504 fallback
    assert report['engine_matches'] is False
    assert report['presets']['balanced']['valid'] is None
    assert output.stat().st_mode & 0o777 == 0o600
    assert subprocess.run(args, capture_output=True).returncode != 0
