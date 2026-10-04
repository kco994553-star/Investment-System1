"""Narrow synthetic CE4 reconciliation; no method/configuration is selected."""
import sys
sys.dont_write_bytecode = True
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import platform


def hex_values(value):
    if type(value) is float:
        return {"decimal": repr(value), "hex": value.hex()}
    if isinstance(value, (list, tuple)):
        return [hex_values(item) for item in value]
    if isinstance(value, dict):
        return {key: hex_values(item) for key, item in value.items()}
    return value


def identity(path):
    raw = path.read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--prior-replay", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repository = args.repository.resolve()
    sys.path.insert(0, str(repository / "implementation/src"))
    from investment_system.evl import superiority as preserved_v1
    from investment_system.evl.statistical_kernels import circular_block_indices
    from investment_system.evl.walkforward import digest
    report_root = repository / "implementation/reports"
    helper_path = report_root / "track_c_c8_gsup_mb_vs_kernel_counterexample_source_2026-10-03.py"
    historical_path = report_root / "track_c_c8_gsup_mb_vs_kernel_counterexample_2026-10-03.json"
    md_path = report_root / "track_c_c8_gsup_mb_vs_kernel_counterexample_2026-10-03.md"
    assert identity(helper_path)["git_blob"] == "f2b2b1e53dfb70beee74baf0b34b178e6a20e0c3"
    historical = json.loads(historical_path.read_text())["CE4_decision_flip_L_not_dividing_n"]
    x, L, B, seed = historical["data"], historical["L"], historical["B"], historical["seed"]
    assert x == [-.016, -.007, .053, .023, .005] and (L, B, seed) == (2, 19, 200)
    tree = ast.parse(helper_path.read_text())
    exact = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "mb_reference")
    namespace = {"math": math, "circular_block_indices": circular_block_indices}
    exec(compile(ast.Module(body=[exact], type_ignores=[]), str(helper_path), "exec"), namespace)
    helper_result = namespace["mb_reference"](x, L, B, seed)
    actual_v1 = preserved_v1.studentized_cbb(tuple(x), block_length=L, replicates=B, seed=seed)
    assert helper_result == historical["MB"] == {"p": .10, "r": 1, "degenerate": 1}
    assert {"p": actual_v1["p_value"], "r": actual_v1["exceedances"], "degenerate": actual_v1["degenerate_replicates"]} == historical["kernel"] == {"p": .15, "r": 2, "degenerate": 1}
    indices = circular_block_indices(n=len(x), block_length=L, replicates=B, seed=seed)
    assert digest(indices) == actual_v1["indices_hash"]
    n, full = len(x), math.ceil(len(x) / L) - 1
    m = sum(x) / n
    block_sums = [sum(x[(s + j) % n] for j in range(L)) for s in range(n)]
    se = math.sqrt(sum((v - L * m) ** 2 for v in block_sums) / (n * L) / n)
    T = m / se
    rows = []
    for row_number, ix in enumerate(indices, start=1):
        values = [x[i] for i in ix]
        ms = sum(values) / n
        blocks = [sum(values[j * L:(j + 1) * L]) for j in range(full)]
        var = sum((block - L * ms) ** 2 for block in blocks) / (full * L)
        t = None if var <= 0 else (ms - m) / math.sqrt(var / n)
        helper_exceed = False if t is None else t >= T
        v1_t = actual_v1["draws"][row_number - 1]
        v1_exceed = True if v1_t is None else v1_t >= actual_v1["statistic"]
        rows.append({"replicate_1_based": row_number, "indices": ix, "sample": values,
                     "helper_mean": ms, "helper_block_sums": blocks, "helper_variance": var,
                     "helper_statistic": t, "helper_degenerate": var <= 0,
                     "helper_exceeds": helper_exceed, "actual_v1_statistic": v1_t,
                     "actual_v1_degenerate": v1_t is None, "actual_v1_exceeds": v1_exceed})
    assert sum(row["helper_exceeds"] for row in rows) == helper_result["r"]
    assert sum(row["helper_degenerate"] for row in rows) == helper_result["degenerate"]
    assert sum(row["actual_v1_exceeds"] for row in rows) == actual_v1["exceedances"]
    changed = [row for row in rows if row["helper_exceeds"] != row["actual_v1_exceeds"]]
    assert len(changed) == 1 and changed[0]["replicate_1_based"] == 10
    assert changed[0]["indices"] == (1, 2, 1, 2, 3)
    assert changed[0]["helper_variance"] == 0 and changed[0]["actual_v1_degenerate"]
    prior = json.loads(args.prior_replay.read_text())
    prior_ce4 = next(case for case in prior["cases"] if case["fixture"]["id"] == "CE4_DEGENERACY")
    assert prior_ce4["indices"] == [list(row) for row in indices]
    references = [{"candidate": ref["candidate"], "summary": ref["summary"]} for ref in prior_ce4["references"]]
    result = {"status": "RECONCILED_NO_METHOD_SELECTION", "scope": "SYNTHETIC_SOFTWARE_VALIDATION_ONLY",
              "runtime": {"python": platform.python_version(), "full_python": sys.version, "platform": platform.platform()},
              "source_head": "675d0d298fbaab5b8473ed048a561ef84e2f3e78",
              "helper_source": identity(helper_path), "historical_json": identity(historical_path),
              "historical_markdown": identity(md_path), "preserved_v1_source": identity(Path(preserved_v1.__file__)),
              "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "prior_replay_sha256": hashlib.sha256(args.prior_replay.read_bytes()).hexdigest(),
              "input": hex_values({"data": x, "L": L, "B": B, "seed": seed}),
              "historical_helper_result": helper_result,
              "actual_preserved_v1_result": hex_values(actual_v1),
              "helper_observed": hex_values({"mean": m, "block_sums": block_sums, "se": se, "statistic": T}),
              "replicates": hex_values(rows), "single_changed_replicate": hex_values(changed[0]),
              "same_variance_block_count": {"M_B": full, "v1": n // L},
              "correct_historical_direction": "M-B=.10/r1 versus preserved v1=.15/r2; both degenerate1",
              "cause": "Replicate10 variance zero under helper and v1: approved M-B does not exceed; historical v1 counts degenerate as exceedance. No RNG/input/block-count difference.",
              "prior_diagnostic_summaries": references,
              "prior_literal_q1_check": prior_ce4["pinned_original_mb_s_plus1_check"],
              "source_classification": {"historical_counterexample": "HISTORICAL_REPRODUCED_DIRECTION_CORRECT",
                                        "current_arithmetic_package": "CURRENT_SYNTHETIC_DIAGNOSTIC_RECONFIRMED",
                                        "universal_only_two_difference_claim": "ANALYTIC_SCOPE_ONLY_NOT_UNIVERSAL_FLOATING_EQUIVALENCE"},
              "new_repository_tests": 0, "new_fixtures": 0, "reduction_selected": None,
              "CAL_VERIFY_accesses": 0, "Holdout_consumptions": 0, "numeric_configuration": "NOT_APPROVED",
              "C8_Freeze": False, "publication": False, "canonical_merge": False}
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"python": result["runtime"]["python"], "helper_p": helper_result["p"],
                      "v1_p": actual_v1["p_value"], "changed_replicate_1_based": 10, "status": result["status"]}))


if __name__ == "__main__":
    main()
