"""Independent CDR-010 M-B arithmetic oracle; synthetic software validation only.

Derived from ``run()`` in the original A6 simulation (2026-10-02): k =
ceil(n/L), q = k-1 variance blocks, and a final block of n-q*L observations.
The final block has length L when n is divisible by L; it is still excluded
from replicate variance. CDR-010 selects fsum/direct sums/block grouping and
the original sqrt(v/n)>0 predicate. Frozen C6 supplies the RNG *convention*,
reproduced here with our own Random instance, never an implementation import.

Authority: e30241f49e31f4ac5ab0d4f322ecddc78a044d75, coordination register
CDR-010/011. No production or diagnostic arithmetic is imported. All numeric
dimensions and seeds are mandatory arguments; this is not a data reader.
"""

import hashlib
import json
import math
import random


METHOD = "C8_GSUP_STUDENTIZED_CBB_v2"
ARITHMETIC_CONTRACT = {
    "reducer": "MATH_FSUM",
    "replicate_aggregation": "BLOCK_GROUPING",
    "block_sums": "DIRECT",
    "degeneracy": "SQRT_V_OVER_N_GT_ZERO",
}


class OracleNotRun(ValueError):
    """Insufficient evidence or undefined observed statistic; never a p-value."""


def oracle_indices(n, block_length, replicates, seed):
    """Independent Frozen C6 circular-block stream, including the last start."""
    for name, value in (("n", n), ("block_length", block_length),
                        ("replicates", replicates)):
        if type(value) is not int or value <= 0:
            raise ValueError(name + " must be a positive integer")
    if type(seed) is not int:
        raise ValueError("seed must be an explicit integer")
    if block_length > n:
        raise OracleNotRun("block length exceeds aligned history")
    rng = random.Random(seed)
    samples = []
    for _ in range(replicates):
        indices = []
        while len(indices) < n:
            start = rng.randrange(n)
            for offset in range(block_length):
                indices.append((start + offset) % n)
        samples.append(tuple(indices[:n]))
    return tuple(samples)


def _finite(value):
    if not math.isfinite(value):
        raise ValueError("nonfinite oracle arithmetic")
    return value


def oracle_studentized(delta, block_length, replicates, seed):
    """Return v1-shaped results plus the approved v2 contract and full traces.

    Extra ``indices``/``circular_block_sums``/``se`` fields expose independently
    derived intermediate evidence. No rounding, epsilon, or rational transport
    is used to decide degeneracy, equality, or exceedance.
    """
    values = tuple(delta)
    if len(values) < 2:
        raise OracleNotRun("insufficient observations")
    if any(type(value) not in (int, float) or not math.isfinite(value)
           for value in values):
        raise ValueError("finite non-boolean observations required")
    n, length = len(values), block_length
    indices = oracle_indices(n, length, replicates, seed)
    # Integer ceil avoids a separate floating-point dimension calculation.
    q = (n + length - 1) // length - 1
    if q < 2:
        raise OracleNotRun("fewer than two variance blocks")

    mean = _finite(math.fsum(values) / n)
    circular_sums = []
    for start in range(n):
        circular_sums.append(_finite(math.fsum(
            values[(start + offset) % n] for offset in range(length))))
    lrv = _finite(math.fsum((total - length * mean) ** 2
                          for total in circular_sums) / (n * length))
    observed_se = math.sqrt(lrv / n)
    if not observed_se > 0:
        raise OracleNotRun("undefined original statistic")
    statistic = _finite(mean / observed_se)

    traces = []
    for sample in indices:
        # Directly sum each sampled block, not cumulative-sum differences or
        # the flattened n observations. The final block is a separate operand.
        blocks = []
        for block in range(q):
            blocks.append(_finite(math.fsum(
                values[sample[position]]
                for position in range(block * length, (block + 1) * length))))
        partial = _finite(math.fsum(values[sample[position]]
                                  for position in range(q * length, n)))
        replicate_mean = _finite((math.fsum(blocks) + partial) / n)
        variance = _finite(math.fsum((total - length * replicate_mean) ** 2
                                   for total in blocks) / (q * length))
        se = math.sqrt(variance / n)
        degenerate = not se > 0
        t_star = None if degenerate else _finite((replicate_mean - mean) / se)
        traces.append({
            "replicate_mean": replicate_mean, "variance": variance, "se": se,
            "block_sums": tuple(blocks), "partial_sum": partial,
            "statistic": t_star, "degenerate": degenerate,
            "tie": not degenerate and t_star == statistic,
            "exceeds": not degenerate and t_star >= statistic,
        })

    exceedances = sum(row["exceeds"] for row in traces)
    # Reproduce the v1 JSON wire hash using stdlib, not its digest helper.
    encoded_indices = json.dumps(indices, sort_keys=True, separators=(",", ":"),
                                 allow_nan=False).encode()
    return {
        "method": METHOD, "n": n, "mean": mean, "long_run_variance": lrv,
        "statistic": statistic, "exceedances": exceedances,
        "degenerate_replicates": sum(row["degenerate"] for row in traces),
        "replicates": replicates, "p_value": (exceedances + 1) / (replicates + 1),
        "draws": tuple(row["statistic"] for row in traces),
        "indices_hash": hashlib.sha256(encoded_indices).hexdigest(),
        "block_length": length, "seed": seed, "one_sided": "GREATER",
        "variance_blocks": q, "ties": sum(row["tie"] for row in traces),
        "arithmetic_contract": dict(ARITHMETIC_CONTRACT), "traces": tuple(traces),
        "indices": indices, "circular_block_sums": tuple(circular_sums),
        "se": observed_se,
    }
