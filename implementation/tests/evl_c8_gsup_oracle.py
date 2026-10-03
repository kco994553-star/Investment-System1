"""Independent G-SUP oracle: written from the A6 method package text, not from the kernel.

No import from investment_system; plain loops and its own circular-block index stream.
SYNTHETIC_SOFTWARE_VALIDATION_ONLY.
"""
import math
import random


def oracle_indices(n, block_length, replicates, seed):
    rng = random.Random(seed)
    out = []
    for _ in range(replicates):
        idx = []
        while len(idx) < n:
            start = rng.randrange(n)
            for j in range(block_length):
                idx.append((start + j) % n)
        out.append(idx[:n])
    return out


def oracle_studentized(delta, block_length, replicates, seed):
    n, L = len(delta), block_length
    mean = sum(delta) / n
    total = 0.0
    for s in range(n):
        block = 0.0
        for j in range(L):
            block += delta[(s + j) % n]
        total += (block - L * mean) ** 2
    se = math.sqrt(total / (n * L) / n)
    statistic = mean / se
    full = n // L
    r = 0
    for idx in oracle_indices(n, L, replicates, seed):
        values = [delta[i] for i in idx]
        m_star = sum(values) / n
        v = 0.0
        for j in range(full):
            v += (sum(values[j * L:(j + 1) * L]) - L * m_star) ** 2
        v /= full * L
        if v <= 0:
            r += 1
            continue
        if (m_star - mean) / math.sqrt(v / n) >= statistic:
            r += 1
    return {"statistic": statistic, "exceedances": r, "p_value": (r + 1) / (replicates + 1)}


def oracle_unstudentized(delta, block_length, replicates, seed):
    n = len(delta)
    mean = sum(delta) / n
    observed = math.sqrt(n) * mean
    r = sum(math.sqrt(n) * (sum(delta[i] for i in idx) / n - mean) >= observed
            for idx in oracle_indices(n, block_length, replicates, seed))
    return {"exceedances": r, "p_value": (r + 1) / (replicates + 1)}


def synthetic_delta(seed, n, mu, phi=0.0):
    rng = random.Random(seed)
    x, out = 0.0, []
    for _ in range(n + 30):
        x = phi * x + rng.gauss(0, 1)
        out.append(x)
    return tuple(mu + v * math.sqrt(1 - phi * phi) for v in out[30:])
