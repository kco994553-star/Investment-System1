"""Independent CDR-012 M-B oracle, derived from the original simulation formula.

SYNTHETIC_SOFTWARE_VALIDATION_ONLY. No production, historical oracle or
diagnostic arithmetic import. Inputs/dimensions/seeds are explicit, not defaults.
CDR-010 keeps fsum, direct blocks, grouped mean and sqrt(v/n)>0 degeneracy.
CDR-012 fixes residual squaring to multiplication and refuses an entirely
degenerate bootstrap. Authority: 1620f7118dbe91283cde1cc1431cdea236ab0829,
COORDINATION_DECISION_REGISTER CDR-012. Historical pow evidence is untouched.
"""

import hashlib
import json
import math
import random


METHOD = "C8_GSUP_STUDENTIZED_CBB_v2"
ARITHMETIC_CONTRACT = {
    "reducer": "MATH_FSUM", "replicate_aggregation": "BLOCK_GROUPING",
    "block_sums": "DIRECT", "degeneracy": "SQRT_V_OVER_N_GT_ZERO",
    "squaring": "MULTIPLICATION", "all_degenerate": "NOT_RUN",
}


class OracleNotRun(ValueError):
    """No inferential result; optional intermediate evidence never has a p-value."""

    def __init__(self, reason, evidence=None):
        super().__init__(reason)
        self.evidence = evidence


def oracle_indices(n, block_length, replicates, seed):
    """Own Random instance implementing the original frozen C6 index convention."""
    for name, value in (("n", n), ("block_length", block_length), ("replicates", replicates)):
        if type(value) is not int or value <= 0:
            raise ValueError(name + " must be a positive integer")
    if type(seed) is not int:
        raise ValueError("explicit integer seed required")
    if block_length > n:
        raise OracleNotRun("block length exceeds history")
    generator = random.Random(seed)
    draws = []
    for _ in range(replicates):
        positions = []
        while len(positions) < n:
            first = generator.randrange(n)
            for offset in range(block_length):
                positions.append((first + offset) % n)
        draws.append(tuple(positions[:n]))
    return tuple(draws)


def _finite(value):
    if not math.isfinite(value):
        raise OracleNotRun("nonfinite arithmetic")
    return value


def _mean_square_residual(blocks, target, denominator):
    """Rounded multiplication of each residual, then the approved fsum reducer."""
    squared = []
    for total in blocks:
        residual = total - target
        squared.append(residual * residual)
    return _finite(math.fsum(squared) / denominator)


def oracle_studentized(delta, block_length, replicates, seed):
    """Independent M-B result and all intermediate traces; no epsilon or rounding.

    k=ceil(n/L), q=k-1 variance blocks; the last block has n-qL observations
    (1..L), contributes to the mean, and is excluded from replicate variance.
    The observed variance uses all n overlapping circular blocks. A bootstrap
    with no positive replicate SE raises OracleNotRun before any p-value exists.
    """
    x = tuple(delta)
    if len(x) < 2:
        raise OracleNotRun("insufficient observations")
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in x):
        raise ValueError("finite non-boolean observations required")
    try:
        return _derive(x, block_length, replicates, seed)
    except (OverflowError, ZeroDivisionError) as exc:
        raise OracleNotRun("unsupported finite arithmetic range") from exc


def _derive(x, length, count, seed):
    n = len(x)
    indices = oracle_indices(n, length, count, seed)
    q = (n + length - 1) // length - 1
    if q < 2:
        raise OracleNotRun("fewer than two variance blocks")
    mean = _finite(math.fsum(x) / n)
    circular = tuple(_finite(math.fsum(x[(start + j) % n] for j in range(length)))
                     for start in range(n))
    lrv = _mean_square_residual(circular, length * mean, n * length)
    observed_se = math.sqrt(lrv / n)
    if not observed_se > 0:
        raise OracleNotRun("undefined original statistic")
    statistic = _finite(mean / observed_se)

    traces = []
    for sample in indices:
        full = tuple(_finite(math.fsum(x[sample[i]] for i in range(j * length, (j + 1) * length)))
                     for j in range(q))
        partial = _finite(math.fsum(x[sample[i]] for i in range(q * length, n)))
        ms = _finite((math.fsum(full) + partial) / n)
        variance = _mean_square_residual(full, length * ms, q * length)
        se = math.sqrt(variance / n)
        degenerate = not se > 0
        t = None if degenerate else _finite((ms - mean) / se)
        traces.append({"replicate_mean": ms, "variance": variance, "se": se,
                       "block_sums": full, "partial_sum": partial, "statistic": t,
                       "degenerate": degenerate, "tie": not degenerate and t == statistic,
                       "exceeds": not degenerate and t >= statistic})

    degenerate_count = sum(row["degenerate"] for row in traces)
    encoded = json.dumps(indices, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    result = {
        "method": METHOD, "n": n, "mean": mean, "long_run_variance": lrv,
        "statistic": statistic, "variance_blocks": q,
        "exceedances": sum(row["exceeds"] for row in traces),
        "degenerate_replicates": degenerate_count, "ties": sum(row["tie"] for row in traces),
        "replicates": count, "draws": tuple(row["statistic"] for row in traces),
        "traces": tuple(traces), "indices_hash": hashlib.sha256(encoded).hexdigest(),
        "block_length": length, "seed": seed, "one_sided": "GREATER",
        "arithmetic_contract": dict(ARITHMETIC_CONTRACT), "indices": indices,
        "circular_block_sums": circular, "se": observed_se,
    }
    if degenerate_count == count:
        raise OracleNotRun("all bootstrap replicates degenerate", result)
    result["p_value"] = (result["exceedances"] + 1) / (count + 1)
    return result
