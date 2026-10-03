"""Independent synthetic M-B arithmetic diagnostics; no active method is selected.

This module imports no investment_system implementation. It reproduces the
approved index convention independently and compares three reduction transports.
All dimensions and seeds are explicit synthetic evidence, never research defaults.
The CLI reads no data/provider and emits only the fixed synthetic cases below.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import random


SCOPE = "SYNTHETIC_SOFTWARE_VALIDATION_ONLY"
NUMPY_EVIDENCE_VERSION = "2.3.5"
REDUCTIONS = ("MATH_FSUM", "PYTHON_311_LEFT_SUM", "NUMPY_CUMULATIVE_2_3_5")
SOURCE_BINDINGS = {
    "implementation/reports/track_c_c8_a6_method_decision_package_2026-10-02.md": "54872fdf13a66d848772bb62dfdb2f7138170fb6",
    "implementation/reports/track_c_c8_a6_method_simulation_source_2026-10-02.py": "e112f41f34d4ead287699657750875770b4c4705",
    "implementation/reports/track_c_c8_gsup_mb_vs_kernel_counterexample_2026-10-03.md": "62d8cd4c451325051a07b003a801d8454bff3b21",
    "implementation/reports/track_c_c8_gsup_mb_vs_kernel_counterexample_source_2026-10-03.py": "f2b2b1e53dfb70beee74baf0b34b178e6a20e0c3",
    "implementation/src/investment_system/evl/superiority.py": "8a1254d7b77514f6015dfff4af0e4a53f57f22af",
    "implementation/src/investment_system/evl/statistical_kernels.py": "28e1c1842625bacabc6ffc9c9b172261e7d6585a",
    "implementation/reports/track_c_c8_gsup_v2_source_identity_approval_2026-10-03.json": "a5279d516c028f0a8cb9166ee2d54366da00877b",
}


def bound_source_provenance(repository=None):
    """Only read pinned approval/source text; no outcome source is read."""
    root = Path(repository) if repository is not None else Path(__file__).resolve().parents[2]
    out = {}
    for path, expected_blob in SOURCE_BINDINGS.items():
        raw = (root / path).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if blob != expected_blob:
            raise ValueError("changed diagnostic authority/history source: " + path)
        out[path] = {"git_blob": blob, "sha256": hashlib.sha256(raw).hexdigest()}
    return out


def independent_indices(n, block_length, replicates, seed):
    """Own RNG/index stream implementing the approved frozen C6 convention."""
    for name, value in (("n", n), ("block_length", block_length), ("replicates", replicates)):
        if type(value) is not int or value <= 0:
            raise ValueError(name + " must be a positive integer")
    if type(seed) is not int or block_length > n:
        raise ValueError("explicit integer seed and block_length <= n required")
    generator = random.Random(seed)
    streams = []
    for _ in range(replicates):
        sample = []
        while len(sample) < n:
            first = generator.randrange(n)
            sample += [(first + offset) % n for offset in range(block_length)]
        streams.append(tuple(sample[:n]))
    return tuple(streams)


def left_sum(values):
    """Explicit Python 3.11 float sum transport, stable across Python minors."""
    total = 0
    for value in values:
        total += value
    return total


def _values(delta):
    values = tuple(delta)
    if len(values) < 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError("finite, non-boolean synthetic observations required")
    return tuple(float(v) for v in values)


def _result(indices, reduction, variance_blocks, observed, draws):
    exceedances = sum(row["exceeds"] for row in draws)
    return {"scope": SCOPE, "reduction": reduction, "status": "COMPUTED_DIAGNOSTIC_ONLY",
            "selected_authoritative_reduction": False, "official": False,
            "indices": indices, "variance_blocks": variance_blocks, "observed": observed,
            "replicates": draws, "exceedances": exceedances,
            "degenerate_replicates": sum(row["degenerate"] for row in draws),
            "ties": sum(row["tie"] for row in draws),
            "p_value": (exceedances + 1) / (len(draws) + 1)}


def _not_run(reduction, reason, variance_blocks):
    return {"scope": SCOPE, "reduction": reduction, "status": "NOT_RUN",
            "reason": reason, "variance_blocks": variance_blocks,
            "selected_authoritative_reduction": False, "official": False}


def scalar_reference(delta, *, block_length, replicates, seed, reduction):
    """M-B formula using an explicitly identified scalar arithmetic transport."""
    if reduction not in REDUCTIONS[:2]:
        raise ValueError("explicit diagnostic scalar reduction required")
    values = _values(delta)
    n, length = len(values), block_length
    indices = independent_indices(n, length, replicates, seed)
    full = (n + length - 1) // length - 1
    if full < 2:
        return _not_run(reduction, "FEWER_THAN_TWO_VARIANCE_BLOCKS", full)
    add = math.fsum if reduction == "MATH_FSUM" else left_sum
    mean = add(values) / n
    circular_sums = [add(values[(start + offset) % n] for offset in range(length))
                     for start in range(n)]
    lrv = add((block - length * mean) ** 2 for block in circular_sums) / (n * length)
    if not math.isfinite(lrv):
        raise ValueError("nonfinite diagnostic variance")
    if lrv <= 0:
        return _not_run(reduction, "UNDEFINED_ORIGINAL_STATISTIC", full)
    statistic = mean / math.sqrt(lrv / n)
    draws = []
    for sample in indices:
        sampled_values = [values[index] for index in sample]
        sample_mean = add(sampled_values) / n
        block_sums = [add(sampled_values[block * length:(block + 1) * length])
                      for block in range(full)]
        variance = add((block - length * sample_mean) ** 2 for block in block_sums) / (full * length)
        degenerate = variance <= 0
        t_star = None if degenerate else (sample_mean - mean) / math.sqrt(variance / n)
        draws.append({"mean": sample_mean, "block_sums": block_sums, "variance": variance,
                      "statistic": t_star, "degenerate": degenerate,
                      "tie": not degenerate and t_star == statistic,
                      "exceeds": not degenerate and t_star >= statistic})
    return _result(indices, reduction, full, {"mean": mean, "circular_block_sums": circular_sums,
                                             "long_run_variance": lrv, "statistic": statistic}, draws)


def numpy_reference(delta, *, block_length, replicates, seed):
    """Literal pinned simulation reduction algebra, with normative frozen indices.

    numpy rng.integers is deliberately replaced by the independently reproduced
    frozen C6 index stream required by the approved package. No production module
    is imported, and no numerical tolerances or rounding are applied.
    """
    import numpy as np
    if np.__version__ != NUMPY_EVIDENCE_VERSION:
        raise ValueError("diagnostic requires exact NumPy " + NUMPY_EVIDENCE_VERSION)
    values = _values(delta)
    n, length = len(values), block_length
    indices = independent_indices(n, length, replicates, seed)
    k = (n + length - 1) // length
    full, rem = k - 1, n - (k - 1) * length
    if full < 2:
        return _not_run(REDUCTIONS[2], "FEWER_THAN_TWO_VARIANCE_BLOCKS", full)
    x = np.array((values,), dtype=np.float64)
    xx = np.concatenate([x, x[:, :length]], 1)
    cumulative = np.concatenate([np.zeros((1, 1)), np.cumsum(xx, 1)], 1)
    positions = np.arange(n)
    full_sums = cumulative[:, positions + length] - cumulative[:, positions]
    partial_sums = cumulative[:, positions + rem] - cumulative[:, positions]
    mean = x.mean(1)
    lrv = ((full_sums - length * mean[:, None]) ** 2).sum(1) / (n * length)
    if not np.isfinite(lrv).all():
        raise ValueError("nonfinite diagnostic variance")
    if lrv[0] <= 0:
        return _not_run(REDUCTIONS[2], "UNDEFINED_ORIGINAL_STATISTIC", full)
    statistic = mean / np.sqrt(lrv / n)
    draws = []
    for sample in indices:
        starts = np.array((sample[::length],), dtype=int)
        sums = np.take_along_axis(full_sums, starts[:, :full], 1)
        last = np.take_along_axis(partial_sums, starts[:, full:], 1)[:, 0]
        sample_mean = (sums.sum(1) + last) / n
        variance = ((sums - length * sample_mean[:, None]) ** 2).sum(1) / (full * length)
        degenerate = bool(variance[0] <= 0)
        t_star = None if degenerate else float(((sample_mean - mean) / np.sqrt(variance / n))[0])
        draws.append({"mean": float(sample_mean[0]), "block_sums": sums[0].tolist(),
                      "variance": float(variance[0]), "statistic": t_star,
                      "degenerate": degenerate, "tie": not degenerate and bool(t_star == statistic[0]),
                      "exceeds": not degenerate and bool(t_star >= statistic[0])})
    return _result(indices, REDUCTIONS[2], full,
                   {"mean": float(mean[0]), "circular_block_sums": full_sums[0].tolist(),
                    "long_run_variance": float(lrv[0]), "statistic": float(statistic[0])}, draws)


def historical_v1_reference(delta, *, block_length, replicates, seed):
    """Independent reconstruction of unchanged v1, for historical comparison only."""
    values = _values(delta)
    n, length = len(values), block_length
    indices = independent_indices(n, length, replicates, seed)
    full = n // length
    if full < 2:
        return _not_run("HISTORICAL_V1_MATH_FSUM", "FEWER_THAN_TWO_VARIANCE_BLOCKS", full)
    mean = math.fsum(values) / n
    block_sums = [math.fsum(values[(start + offset) % n] for offset in range(length))
                  for start in range(n)]
    lrv = math.fsum((block - length * mean) ** 2 for block in block_sums) / (n * length)
    if lrv <= 0:
        return _not_run("HISTORICAL_V1_MATH_FSUM", "UNDEFINED_ORIGINAL_STATISTIC", full)
    statistic = mean / math.sqrt(lrv / n)
    draws = []
    for sample in indices:
        sampled_values = [values[index] for index in sample]
        sample_mean = math.fsum(sampled_values) / n
        sums = [math.fsum(sampled_values[block * length:(block + 1) * length])
                for block in range(full)]
        variance = math.fsum((block - length * sample_mean) ** 2 for block in sums) / (full * length)
        degenerate = variance <= 0
        t_star = None if degenerate else (sample_mean - mean) / math.sqrt(variance / n)
        draws.append({"mean": sample_mean, "block_sums": sums, "variance": variance,
                      "statistic": t_star, "degenerate": degenerate,
                      "tie": not degenerate and t_star == statistic,
                      "exceeds": degenerate or t_star >= statistic})
    return _result(indices, "HISTORICAL_V1_MATH_FSUM", full,
                   {"mean": mean, "circular_block_sums": block_sums,
                    "long_run_variance": lrv, "statistic": statistic}, draws)


CASES = (
    {"id": "CE1_RUNNABILITY", "delta": [.03, -.01, .02, .01], "block_length": 2, "replicates": 19, "seed": 1},
    {"id": "CE2_BLOCKS_AND_DEGENERACY", "delta": [.03, -.01, .02, .01, 0., .02], "block_length": 2, "replicates": 19, "seed": 1},
    {"id": "CE3_CONTROL", "delta": [.03, -.01, .02, .01, 0.], "block_length": 2, "replicates": 19, "seed": 1},
    {"id": "CE4_DEGENERACY", "delta": [-.016, -.007, .053, .023, .005], "block_length": 2, "replicates": 19, "seed": 200},
    {"id": "CE5_BLOCK_COUNT", "delta": [.008, .003, -.02, .019, .012, -.01, .019, .002], "block_length": 2, "replicates": 19, "seed": 18},
    {"id": "ARITHMETIC_NUMPY_FLIP", "delta": [.01, .01, -.01, -.02, .02, .01, .01, .01], "block_length": 3, "replicates": 19, "seed": 46},
    {"id": "ARITHMETIC_LEFT_SUM", "delta": [-.02, .01, .02, 0., .01, .01, .01, -.01, .01], "block_length": 4, "replicates": 19, "seed": 34},
    {"id": "ARITHMETIC_TIE", "delta": [.02, 0., -.02, -.01, .01, 0.], "block_length": 2, "replicates": 19, "seed": 72},
    {"id": "UNDEFINED_ORIGINAL", "delta": [0.] * 6, "block_length": 2, "replicates": 19, "seed": 1},
)


def make_evidence():
    import numpy as np
    cases = []
    for case in CASES:
        arguments = {key: value for key, value in case.items() if key != "id"}
        references = [scalar_reference(**arguments, reduction=reduction) for reduction in REDUCTIONS[:2]]
        references.append(numpy_reference(**arguments))
        cases.append({"fixture": case, "references": references,
                      "preserved_v1_reconstruction": historical_v1_reference(**arguments)})
    return {"scope": SCOPE, "status": "EVIDENCE_ONLY_NO_REDUCTION_SELECTED",
            "runtime": {"python": platform.python_version(), "numpy": np.__version__},
            "real_data_access": "NOT_RUN", "holdout_access": "NOT_RUN", "official": False,
            "pinned_sources": bound_source_provenance(),
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(make_evidence(), indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
