"""Repeatable independent synthetic v2 comparison; no outcome reader or defaults."""
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from investment_system.evl import superiority as v1, superiority_v2 as v2
from tests.evl_c8_gsup_v2_oracle import OracleNotRun, oracle_studentized
from tools.gsup_mb_reduction_diagnostic import CASES

PUBLIC_KEYS = frozenset({"method", "arithmetic_contract", "n", "mean", "long_run_variance", "statistic",
                         "variance_blocks", "exceedances", "degenerate_replicates", "ties", "replicates",
                         "p_value", "draws", "traces", "indices_hash", "block_length", "seed", "one_sided"})
APPROVED_CONTRACT = {"reducer": "MATH_FSUM", "replicate_aggregation": "BLOCK_GROUPING",
                     "block_sums": "DIRECT", "degeneracy": "SQRT_V_OVER_N_GT_ZERO"}


def exact(value):
    if type(value) is float:
        return {"decimal": repr(value), "hex": value.hex()}
    if isinstance(value, dict):
        return {key: exact(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact(item) for item in value]
    return value


def commitment(value):
    return hashlib.sha256(json.dumps(exact(value), sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def verify():
    fixtures = (*CASES,
                {"id": "OPERAND_SEED275", "delta": [.01, -.03, .04, -.01, -.01],
                 "block_length": 2, "replicates": 19, "seed": 275},
                {"id": "STANDARD_ERROR_UNDERFLOW", "delta": [0., 0., 4e-162, 4e-162, 4e-162, 4e-160],
                 "block_length": 1, "replicates": 19, "seed": 0})
    cases = []
    for fixture in fixtures:
        name = fixture["id"]
        args = {key: value for key, value in fixture.items() if key != "id"}
        try:
            oracle = oracle_studentized(**args)
        except OracleNotRun:
            try:
                v2.studentized_cbb(**args)
            except v2.MissingStatisticalEvidence:
                cases.append({"id": name, "status": "MATCHED_NOT_RUN", "fixture_hash": commitment(args)})
                continue
            raise AssertionError("production returned a p-value for undefined/insufficient evidence")
        production = v2.studentized_cbb(**args)
        assert set(production) == PUBLIC_KEYS, "incomplete/unknown production result schema: " + name
        assert production["arithmetic_contract"] == APPROVED_CONTRACT, "unapproved result arithmetic contract"
        expected = {key: oracle[key] for key in PUBLIC_KEYS}
        assert exact(production) == exact(expected), name
        row = {"id": name, "status": "EXACT_DECIMAL_AND_HEX_PASS", "fixture_hash": commitment(args),
               "p_value": exact(production["p_value"]), "exceedances": production["exceedances"],
               "degenerate": production["degenerate_replicates"], "ties": production["ties"],
               "variance_blocks": production["variance_blocks"], "indices_hash": production["indices_hash"],
               "production_exact_hash": commitment(production), "oracle_exact_hash": commitment(expected),
               "replicate_trace_exact_hash": commitment(production["traces"])}
        if name == "CE4_DEGENERACY":
            old = v1.studentized_cbb(**args)
            assert production["p_value"] == .10 and old["p_value"] == .15
            row["preserved_v1_p_value"] = exact(old["p_value"])
        cases.append(row)
    paths = [Path(v2.__file__), ROOT / "tests/evl_c8_gsup_v2_oracle.py", Path(__file__),
             Path(v1.__file__), v2.APPROVAL_PATH]
    return {"scope": "SYNTHETIC_SOFTWARE_VALIDATION_ONLY", "status": "PASS",
            "runtime": {"implementation": platform.python_implementation(), "python": platform.python_version()},
            "arithmetic_contract": APPROVED_CONTRACT, "cases": cases,
            "numerical_output_sha256": commitment(cases),
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            "actual_CAL_VERIFY": 0, "Holdout": 0, "numeric_defaults": 0, "grants": 0,
            "historical_v1_rewritten": False}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True, allow_nan=False))
