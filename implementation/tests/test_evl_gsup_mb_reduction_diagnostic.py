"""Independent diagnostic regressions; no active G-SUP reduction is selected."""
import ast
import json
import math
from pathlib import Path
import subprocess

import pytest

from tools import gsup_mb_reduction_diagnostic as D


def fixture(case_id):
    case = next(case for case in D.CASES if case["id"] == case_id)
    return {key: value for key, value in case.items() if key != "id"}


def test_oracle_has_no_production_import():
    tree = ast.parse(Path(D.__file__).read_text())
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
    assert not any("investment_system" in name for name in modules)


def test_changed_historical_authority_is_refused(tmp_path):
    repository = Path(D.__file__).resolve().parents[2]
    for source in D.SOURCE_BINDINGS:
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((repository / source).read_bytes())
    assert set(D.bound_source_provenance(tmp_path)) == set(D.SOURCE_BINDINGS)
    authority = next(iter(D.SOURCE_BINDINGS))
    with (tmp_path / authority).open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="changed diagnostic authority"):
        D.bound_source_provenance(tmp_path)


def test_independent_index_stream_matches_frozen_convention_grid():
    from investment_system.evl.statistical_kernels import circular_block_indices
    for n in (1, 2, 3, 4, 5, 8, 9, 12):
        for length in range(1, n + 1):
            for seed in (-2, 0, 1, 46):
                assert D.independent_indices(n, length, 19, seed) == circular_block_indices(
                    n=n, block_length=length, replicates=19, seed=seed)


@pytest.mark.parametrize("case_id,expected_mb,expected_v1", [
    ("CE1_RUNNABILITY", None, .30), ("CE2_BLOCKS_AND_DEGENERACY", .05, .10),
    ("CE3_CONTROL", .05, .05), ("CE4_DEGENERACY", .10, .15), ("CE5_BLOCK_COUNT", .30, .25)])
def test_fixed_historical_method_counterexamples(case_id, expected_mb, expected_v1):
    arguments = fixture(case_id)
    mb = D.scalar_reference(**arguments, reduction="MATH_FSUM")
    historical = D.historical_v1_reference(**arguments)
    if expected_mb is None:
        assert mb["status"] == "NOT_RUN"
        assert mb["reason"] == "FEWER_THAN_TWO_VARIANCE_BLOCKS"
    else:
        assert mb["p_value"] == expected_mb
        assert len(mb["replicates"]) == arguments["replicates"]
    assert historical["p_value"] == expected_v1


def test_fixed_numpy_arithmetic_exceedance_and_degeneracy_counterexample():
    arguments = fixture("ARITHMETIC_NUMPY_FLIP")
    fsum = D.scalar_reference(**arguments, reduction="MATH_FSUM")
    numpy = D.numpy_reference(**arguments)
    assert fsum["indices"] == numpy["indices"]
    assert (fsum["exceedances"], fsum["degenerate_replicates"], fsum["p_value"]) == (1, 2, .10)
    assert (numpy["exceedances"], numpy["degenerate_replicates"], numpy["p_value"]) == (3, 0, .20)
    changed = [(a, b) for a, b in zip(fsum["replicates"], numpy["replicates"])
               if a["degenerate"] != b["degenerate"]]
    assert len(changed) == 2
    assert all(a["variance"] == 0 and b["variance"] > 0 for a, b in changed)


def test_fixed_left_sum_arithmetic_counterexample_and_explicit_reduction():
    arguments = fixture("ARITHMETIC_LEFT_SUM")
    fsum = D.scalar_reference(**arguments, reduction="MATH_FSUM")
    left = D.scalar_reference(**arguments, reduction="PYTHON_311_LEFT_SUM")
    assert fsum["indices"] == left["indices"]
    assert (fsum["exceedances"], fsum["degenerate_replicates"], fsum["p_value"]) == (6, 1, .35)
    assert (left["exceedances"], left["degenerate_replicates"], left["p_value"]) == (7, 0, .40)
    values = (-2e16, 1.0, 2e16)
    assert D.left_sum(values) == 0
    assert math.fsum(values) == 1
    with pytest.raises(ValueError, match="explicit"):
        D.scalar_reference(**arguments, reduction="AUTO")


def test_ties_remain_greater_or_equal_and_degenerate_replicates_never_exceed():
    output = D.scalar_reference(**fixture("ARITHMETIC_TIE"), reduction="MATH_FSUM")
    assert output["observed"]["statistic"] == 0
    assert output["ties"] > 0
    assert output["degenerate_replicates"] == 2
    assert all(row["exceeds"] for row in output["replicates"] if row["tie"])
    assert all(not row["exceeds"] for row in output["replicates"] if row["degenerate"])
    assert output["p_value"] == .45


def test_undefined_original_statistic_fails_closed_across_reductions():
    args = fixture("UNDEFINED_ORIGINAL")
    outputs = [D.scalar_reference(**args, reduction=name) for name in D.REDUCTIONS[:2]]
    outputs.append(D.numpy_reference(**args))
    assert all(out["status"] == "NOT_RUN" for out in outputs)
    assert all(out["reason"] == "UNDEFINED_ORIGINAL_STATISTIC" for out in outputs)
    assert all("p_value" not in out for out in outputs)


@pytest.mark.parametrize("field,value", [("delta", [0., float("nan"), .01]),
                                        ("delta", [0., float("inf"), .01]),
                                        ("delta", [True, 0., .01]),
                                        ("block_length", True), ("replicates", 0),
                                        ("seed", True), ("block_length", 99)])
def test_nonfinite_or_implicit_dimensions_refused(field, value):
    arguments = fixture("CE3_CONTROL")
    arguments[field] = value
    with pytest.raises(ValueError):
        D.scalar_reference(**arguments, reduction="MATH_FSUM")
    with pytest.raises(ValueError):
        D.numpy_reference(**arguments)


def test_trace_determinism_in_fresh_processes_and_no_selected_method(tmp_path):
    outputs = [tmp_path / (str(index) + ".json") for index in range(2)]
    import sys
    for output in outputs:
        subprocess.run([sys.executable, D.__file__, "--out", str(output)], check=True)
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    evidence = json.loads(outputs[0].read_text())
    assert evidence["runtime"]["numpy"] == "2.3.5"
    assert evidence["scope"] == "SYNTHETIC_SOFTWARE_VALIDATION_ONLY"
    assert evidence["status"] == "EVIDENCE_ONLY_NO_REDUCTION_SELECTED"
    assert evidence["real_data_access"] == evidence["holdout_access"] == "NOT_RUN"
    assert not evidence["official"]
    for case in evidence["cases"]:
        for output in case["references"]:
            assert not output["selected_authoritative_reduction"]
            assert not output["official"]
