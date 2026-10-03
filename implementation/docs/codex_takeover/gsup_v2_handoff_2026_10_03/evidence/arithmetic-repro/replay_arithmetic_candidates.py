"""Evidence-only fresh-process replay; never selects an authoritative G-SUP method.

Input is the nine already-published synthetic diagnostic fixtures. There are no
providers, outcome files, defaults, tolerance rules, registration mutations, or
production statistical-kernel imports. The pinned original S_plus1 statements
and Frozen C6 index function are extracted read-only for comparison.
"""
import argparse
import ast
import builtins
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import random
import sys

SCOPE = "SYNTHETIC_SOFTWARE_VALIDATION_ONLY"
SELECTED = False


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def with_hex(value):
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("nonfinite result is not an executable decision")
        return {"decimal": repr(value), "hex": value.hex()}
    if isinstance(value, dict):
        return {key: with_hex(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [with_hex(item) for item in value]
    return value


def scalar_candidate(D, arguments, reducer, label):
    values = tuple(float(item) for item in arguments["delta"])
    n, length = len(values), arguments["block_length"]
    indices = D.independent_indices(n, length, arguments["replicates"], arguments["seed"])
    blocks = (n + length - 1) // length - 1
    common = {"scope": SCOPE, "reduction": label, "selected_authoritative_reduction": False,
              "official": False, "variance_blocks": blocks}
    if blocks < 2:
        return {**common, "status": "NOT_RUN", "reason": "FEWER_THAN_TWO_VARIANCE_BLOCKS"}
    mean = reducer(values) / n
    circular = [reducer(values[(start + offset) % n] for offset in range(length))
                for start in range(n)]
    lrv = reducer((value - length * mean) ** 2 for value in circular) / (n * length)
    if not math.isfinite(lrv):
        raise ValueError("nonfinite variance")
    if lrv <= 0:
        return {**common, "status": "NOT_RUN", "reason": "UNDEFINED_ORIGINAL_STATISTIC"}
    observed = mean / math.sqrt(lrv / n)
    draws = []
    for indices_row in indices:
        sample = [values[index] for index in indices_row]
        sample_mean = reducer(sample) / n
        sums = [reducer(sample[block * length:(block + 1) * length]) for block in range(blocks)]
        variance = reducer((value - length * sample_mean) ** 2 for value in sums) / (blocks * length)
        degenerate = variance <= 0
        statistic = None if degenerate else (sample_mean - mean) / math.sqrt(variance / n)
        draws.append({"mean": sample_mean, "block_sums": sums, "variance": variance,
                      "statistic": statistic, "degenerate": degenerate,
                      "tie": not degenerate and statistic == observed,
                      "exceeds": not degenerate and statistic >= observed})
    r = builtins.sum(row["exceeds"] for row in draws)
    return {**common, "status": "COMPUTED_DIAGNOSTIC_ONLY", "indices": indices,
            "observed": {"mean": mean, "circular_block_sums": circular,
                         "long_run_variance": lrv, "statistic": observed},
            "replicates": draws, "exceedances": r,
            "degenerate_replicates": builtins.sum(row["degenerate"] for row in draws),
            "ties": builtins.sum(row["tie"] for row in draws),
            "p_value": (r + 1) / (len(draws) + 1)}


def original_functions(repository, np):
    frozen_path = repository / "implementation/src/investment_system/evl/statistical_kernels.py"
    frozen = ast.parse(frozen_path.read_text())
    needed = {"MissingStatisticalEvidence", "_positive_integer", "circular_block_indices"}
    chosen = [item for item in frozen.body if isinstance(item, (ast.FunctionDef, ast.ClassDef))
              and item.name in needed]
    if len(chosen) != 3:
        raise AssertionError("pinned frozen index function changed")
    index_namespace = {"random": random}
    exec(compile(ast.Module(body=chosen, type_ignores=[]), str(frozen_path), "exec"), index_namespace)
    if np is None:
        return index_namespace["circular_block_indices"], None
    simulation_path = repository / "implementation/reports/track_c_c8_a6_method_simulation_source_2026-10-02.py"
    source = ast.parse(simulation_path.read_text())
    run = next(item for item in source.body if isinstance(item, ast.FunctionDef) and item.name == "run")
    # Preserve every original statement through creation of out (including U).
    # Remove only the subsequent alternative M-C/BM_t section and return out.
    # No S_plus1 expression, scalar, comparison or reduction is rewritten.
    out_position = next(index for index, item in enumerate(run.body) if isinstance(item, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == "out" for target in item.targets))
    run.body = run.body[:out_position + 1] + [ast.Return(value=ast.Name(id="out", ctx=ast.Load()))]
    module = ast.fix_missing_locations(ast.Module(body=[run], type_ignores=[]))
    namespace = {"np": np, "math": math}
    exec(compile(module, str(simulation_path), "exec"), namespace)
    return index_namespace["circular_block_indices"], namespace["run"]


class FrozenStarts:
    def __init__(self, np, indices, length):
        self.np, self.indices, self.length, self.position = np, indices, length, 0

    def integers(self, low, high, shape):
        row = self.indices[self.position]
        self.position += 1
        starts = row[::self.length]
        assert low == 0 and high == len(row) and shape == (1, len(starts))
        return self.np.array((starts,), dtype=int)


def outcome_summary(result):
    if result["status"] == "NOT_RUN":
        return {"status": "NOT_RUN", "reason": result["reason"]}
    return {"status": result["status"], "r": result["exceedances"], "tie": result["ties"],
            "degenerate": result["degenerate_replicates"],
            "p": result["p_value"], "p_hex": result["p_value"].hex()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repository = args.repository.resolve()
    diagnostic_path = repository / "implementation/tools/gsup_mb_reduction_diagnostic.py"
    specification = importlib.util.spec_from_file_location("pinned_diagnostic", diagnostic_path)
    D = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(D)
    provenance = D.bound_source_provenance(repository)
    diagnostic_raw = diagnostic_path.read_bytes()
    provenance[str(diagnostic_path.relative_to(repository))] = {
        "sha256": sha256(diagnostic_raw),
        "git_blob": hashlib.sha1(b"blob " + str(len(diagnostic_raw)).encode() + b"\0" + diagnostic_raw).hexdigest()}
    import numpy as np
    pinned_numpy_available = np.__version__ == D.NUMPY_EVIDENCE_VERSION
    frozen_indices, original_mb = original_functions(repository, np if pinned_numpy_available else None)
    grid_checks = 0
    index_rows = []
    for n in (1, 2, 3, 4, 5, 8, 9, 12):
        for length in range(1, n + 1):
            for seed in (-2, 0, 1, 46):
                expected = frozen_indices(n=n, block_length=length, replicates=19, seed=seed)
                actual = D.independent_indices(n, length, 19, seed)
                assert expected == actual
                index_rows.append({"n": n, "L": length, "B": 19, "seed": seed, "indices": actual})
                grid_checks += 1
    cases = []
    for fixture in D.CASES:
        arguments = {key: value for key, value in fixture.items() if key != "id"}
        outputs = []
        for label, reducer, old_name in (("MATH_FSUM", math.fsum, "MATH_FSUM"),
                                        ("ACTUAL_PYTHON_BUILTIN_SUM", builtins.sum, None),
                                        ("PYTHON_311_LEFT_SUM_RECONSTRUCTION", D.left_sum, "PYTHON_311_LEFT_SUM")):
            result = scalar_candidate(D, arguments, reducer, label)
            if old_name:
                prior = D.scalar_reference(**arguments, reduction=old_name)
                assert {key: value for key, value in result.items() if key != "reduction"} == {
                    key: value for key, value in prior.items() if key != "reduction"}
            outputs.append(result)
        indices = D.independent_indices(len(fixture["delta"]), fixture["block_length"], fixture["replicates"], fixture["seed"])
        assert indices == frozen_indices(n=len(fixture["delta"]), block_length=fixture["block_length"],
                                         replicates=fixture["replicates"], seed=fixture["seed"])
        literal_match = {"status": "NOT_RUN", "reason": "NUMPY_2_3_5_NOT_INSTALLED_FOR_THIS_RUNTIME"}
        if pinned_numpy_available:
            numpy_result = D.numpy_reference(**arguments)
            outputs.append(numpy_result)
            starts = FrozenStarts(np, indices, fixture["block_length"])
            with np.errstate(divide="ignore", invalid="ignore"):
                original = original_mb(np.array((fixture["delta"],), dtype=np.float64), fixture["block_length"], fixture["replicates"], starts)
            assert starts.position == fixture["replicates"]
            raw_p = float(original["S_plus1"][0])
            if numpy_result["status"] != "NOT_RUN":
                assert raw_p == numpy_result["p_value"]
                literal_match = {"status": "EXACT_P_HEX_MATCH", "p": raw_p, "p_hex": raw_p.hex(),
                                 "r_recovered": int(round(raw_p * (fixture["replicates"] + 1) - 1))}
            else:
                literal_match = {"status": "DIAGNOSTIC_FAIL_CLOSED_BOUNDARY", "reason": numpy_result["reason"],
                                 "simulation_raw_p": "NaN" if math.isnan(raw_p) else raw_p,
                                 "simulation_raw_p_hex": None if math.isnan(raw_p) else raw_p.hex()}
        else:
            outputs.append({"scope": SCOPE, "reduction": "NUMPY_CUMULATIVE_2_3_5", "status": "NOT_RUN",
                            "reason": "NUMPY_2_3_5_NOT_INSTALLED_FOR_THIS_RUNTIME",
                            "selected_authoritative_reduction": False, "official": False})
        references = []
        for result in outputs:
            numeric = {key: value for key, value in result.items() if key != "reduction"}
            encoded = with_hex(result)
            references.append({"candidate": result["reduction"], "summary": outcome_summary(result),
                               "numeric_payload_sha256": sha256(canonical(with_hex(numeric))), "trace": encoded})
        cases.append({"fixture": with_hex(fixture), "indices": indices,
                      "indices_sha256": sha256(canonical(indices)), "references": references,
                      "pinned_original_mb_s_plus1_check": literal_match,
                      "historical_v1_readonly_comparison": with_hex(D.historical_v1_reference(**arguments))})
    core = {"scope": SCOPE, "status": "EVIDENCE_ONLY_NO_REDUCTION_SELECTED", "cases": cases,
            "frozen_index_grid_checks": grid_checks, "frozen_index_grid_sha256": sha256(canonical(index_rows))}
    multiarray = importlib.import_module("numpy._core._multiarray_umath")
    runtime = {"implementation": platform.python_implementation(), "python_version": platform.python_version(),
               "python_full_version": sys.version, "compiler": platform.python_compiler(),
               "executable": sys.executable, "executable_sha256": sha256(Path(sys.executable).read_bytes()),
               "platform": platform.platform(), "machine": platform.machine(), "system": platform.system(),
               "libc": platform.libc_ver(), "byteorder": sys.byteorder, "numpy": np.__version__,
               "numpy_module": np.__file__, "numpy_multiarray_module": multiarray.__file__,
               "numpy_multiarray_sha256": sha256(Path(multiarray.__file__).read_bytes()),
               "numpy_config": np.show_config(mode="dicts"),
               "float_info": {name: getattr(sys.float_info, name) for name in
                              ("max", "max_exp", "max_10_exp", "min", "min_exp", "min_10_exp",
                               "dig", "mant_dig", "epsilon", "radix", "rounds")},
               "actual_builtin_sum": {"module": builtins.sum.__module__, "name": builtins.sum.__name__,
                                      "probe_floats": with_hex((-2e16, 1.0, 2e16)),
                                      "probe_sum": with_hex(builtins.sum((-2e16, 1.0, 2e16))),
                                      "probe_fsum": with_hex(math.fsum((-2e16, 1.0, 2e16))),
                                      "probe_311_left": with_hex(D.left_sum((-2e16, 1.0, 2e16)))}}
    result = {**core, "runtime": runtime, "pinned_sources": provenance,
              "driver_sha256": sha256(Path(__file__).read_bytes()),
              "canonical_numeric_output_sha256": sha256(canonical(with_hex(core))),
              "safety": {"real_data_access": "NOT_RUN", "CAL_VERIFY_accesses": 0, "Holdout_consumptions": 0,
                         "numeric_configuration_selected": False, "C8_Freeze": False,
                         "publication": False, "canonical_merge": False},
              "original_mb_extraction": "Unchanged original run() statements through out assignment; unrelated BM_t alternative removed. Only rng.integers is supplied Frozen C6 starts. Undefined-original diagnostics fail closed instead of transporting simulation NaN."}
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"python": runtime["python_version"], "numpy": runtime["numpy"],
                      "fixtures": len(cases), "grid_checks": grid_checks,
                      "canonical_numeric_output_sha256": result["canonical_numeric_output_sha256"],
                      "status": result["status"]}))


if __name__ == "__main__":
    main()
