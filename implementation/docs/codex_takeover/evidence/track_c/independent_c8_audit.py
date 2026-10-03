"""Read-only synthetic audit of exact Track C tip; no real data service is used."""
from copy import deepcopy
import json
import math
from pathlib import Path
import random
import sys
import tempfile

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/track-c-audit")
sys.path.insert(0, str(REPO / "implementation/src"))
from investment_system.evl import superiority as G
from investment_system.evl.calibration_contracts import IntegrityFailure
from investment_system.evl.walkforward import digest


def indices(n, L, B, seed):
    """Own index stream; no import of the frozen index kernel."""
    rng = random.Random(seed)
    for _ in range(B):
        ix = []
        while len(ix) < n:
            start = rng.randrange(n)
            ix.extend((start + j) % n for j in range(L))
        yield ix[:n]


def oracle(x, L, B, seed, mb=False):
    n = len(x)
    full = math.ceil(n / L) - 1 if mb else n // L
    if full < 2:
        return {"status": "NOT_RUN", "full_blocks": full}
    mean = math.fsum(x) / n
    lrv = math.fsum((math.fsum(x[(s + j) % n] for j in range(L)) - L * mean) ** 2
                    for s in range(n)) / (n * L)
    if not lrv > 0:
        return {"status": "NOT_RUN", "full_blocks": full}
    T = mean / math.sqrt(lrv / n)
    r = deg = 0
    for ix in indices(n, L, B, seed):
        v = [x[i] for i in ix]
        ms = math.fsum(v) / n
        var = math.fsum((math.fsum(v[j * L:(j + 1) * L]) - L * ms) ** 2
                        for j in range(full)) / (full * L)
        if var <= 0:
            deg += 1
            r += not mb
        else:
            r += (ms - mean) / math.sqrt(var / n) >= T
    return {"status": "RUN", "full_blocks": full, "exceedances": r,
            "degenerate": deg, "p": (r + 1) / (B + 1)}


CASES = [
    ("CE1", [0.03, -0.01, 0.02, 0.01], 2, 19, 1),
    ("CE2", [0.03, -0.01, 0.02, 0.01, 0., 0.02], 2, 19, 1),
    ("CE3", [0.03, -0.01, 0.02, 0.01, 0.], 2, 19, 1),
    ("CE4", [-0.016, -0.007, 0.053, 0.023, 0.005], 2, 19, 200),
    ("CE5", [0.008, 0.003, -0.02, 0.019, 0.012, -0.01, 0.019, 0.002], 2, 19, 18),
]
out = {"scope": "SYNTHETIC_ONLY_NO_REAL_CAL_VERIFY_OR_HOLDOUT_ACCESS", "cases": {}}
for name, x, L, B, seed in CASES:
    k = G.studentized_cbb(tuple(x), block_length=L, replicates=B, seed=seed)
    ref = oracle(x, L, B, seed)
    assert k["p_value"] == ref["p"] and k["exceedances"] == ref["exceedances"]
    out["cases"][name] = {"x": x, "L": L, "B": B, "seed": seed,
                           "MB_reference": oracle(x, L, B, seed, mb=True), "kernel_oracle": ref,
                           "kernel_p": k["p_value"]}
assert out["cases"]["CE4"]["MB_reference"]["p"] == .10
assert out["cases"]["CE4"]["kernel_p"] == .15

randomized = random.Random(934)
oracle_matches = agreement = agreement_eligible = 0
for case in range(300):
    n = randomized.choice([13, 17, 25, 31])
    L = randomized.choice([2, 3, 4, 5])
    x = [randomized.gauss(0.2, 1.0) for _ in range(n)]
    k = G.studentized_cbb(x, block_length=L, replicates=49, seed=case)
    ref = oracle(x, L, 49, case)
    assert ref["p"] == k["p_value"]
    oracle_matches += 1
    mb = oracle(x, L, 49, case, mb=True)
    if n % L and ref["degenerate"] == 0 and mb.get("degenerate") == 0:
        agreement_eligible += 1
        agreement += ref["p"] == mb["p"]
assert agreement == agreement_eligible
out["randomized"] = {"kernel_oracle_matches": oracle_matches,
                     "MB_kernel_agree_when_difference_inactive": agreement,
                     "eligible": agreement_eligible}

dev = tuple(math.sin(j) + .2 * math.cos(3 * j) for j in range(30))


def provider(floats=True):
    cast = float if floats else int
    def supply(dataset_id):
        return {"dataset_role": "CAL_VERIFY", "dataset_id": dataset_id, "role_id": "candidate-1",
                "synthetic": True, "cohorts": {
                    c: {"role": [cast(j + 2) for j in range(8)],
                        "controls": {k: [cast(0) for _ in range(8)] for k in G.SUPPORTED_CONTROLS}}
                    for c in G.REQUIRED_COHORTS}}
    return supply


def spec(p):
    return {"schema": G.METHOD, "policy": G.POLICY, "scope": G.SCOPE,
            "configuration_scope": G.FIXTURE_SCOPE, "temporal_origin": "SIMULATED",
            "registered_at": "2030-01-01T00:00:00+00:00", "campaign_id": "audit-campaign-1",
            "profile": "Balanced", "role": "CHAMPION", "role_id": "candidate-1",
            "role_designation_ref": "SYNTHETIC_FIXTURE_ROLE", "verify_dataset_id": "audit-verify-1",
            "verify_content_hash": digest(p("audit-verify-1")["cohorts"]),
            "development_dataset_id": "audit-dev", "development_content_hash": digest(dev),
            "development_lineage_ref": G.DEVELOPMENT_FIXTURE_LINEAGE, "verify_periods": 8,
            "controls": list(G.SUPPORTED_CONTROLS), "cohorts": list(G.REQUIRED_COHORTS),
            "evidence_kind": G.EVIDENCE_KIND, "comparison_evidence": [], "alpha": .1,
            "replicates": 19, "block_rule": {"kind": "FIXED", "block_length": 2},
            "seed": 7, "minimum_support": 2,
            "feasibility": {"size_tolerance": 1., "conservative_envelope": [{"kind": "AR1_GAUSSIAN", "phi": 0.}],
                            "margin": 0., "dependence_estimator": G.ESTIMATORS[0], "replications": 5, "seed": 11},
            "effect_floor": dict(G.EFFECT_FLOOR)}


def feasibility(reg, key, series=dev):
    return reg.record_feasibility(key, series, dataset_role="DEVELOPMENT", dataset_id="audit-dev")


p = provider()
s = spec(p)
with tempfile.TemporaryDirectory(prefix="c8-independent-audit-") as tmp:
    root = Path(tmp)
    reg = G.GsupRegistry(root / "campaign-1", root / "shared")
    key = reg.register(s)
    try:
        feasibility(reg, key, tuple(range(30)))
        raise AssertionError("uncommitted Development content was accepted")
    except IntegrityFailure as e:
        out["uncommitted_development"] = {"blocked": True, "reason": str(e)}
    feasibility(reg, key)
    first = reg.assess(key, p, accessed_at="2030-02-01T00:00:00+00:00")
    new_campaign = deepcopy(s)
    new_campaign["campaign_id"] = "audit-campaign-2"
    reg2 = G.GsupRegistry(root / "campaign-2", root / "shared")
    try:
        reg2.register(new_campaign)
        raise AssertionError("simple campaign change bypassed one-shot")
    except IntegrityFailure as e:
        out["simple_campaign_retest"] = {"blocked": True, "reason": str(e)}

    integer_p = provider(floats=False)
    integer_s = spec(integer_p)
    integer_s["campaign_id"] = "audit-campaign-3"
    assert integer_s["verify_content_hash"] != s["verify_content_hash"]
    # Same numerical observations; only their JSON int/float representation differs.
    assert integer_p("audit-verify-1")["cohorts"] == p("audit-verify-1")["cohorts"]
    reg3 = G.GsupRegistry(root / "campaign-3", root / "shared")
    second_key = reg3.register(integer_s)
    feasibility(reg3, second_key)
    second = reg3.assess(second_key, integer_p, accessed_at="2030-02-02T00:00:00+00:00")
    assert first["cells"] == second["cells"]
    out["numeric_reencoding_retest"] = {
        "accepted": True, "same_numerical_observations": True, "same_cells": True,
        "first_content_hash": s["verify_content_hash"], "second_content_hash": integer_s["verify_content_hash"],
        "first_access_key": reg.access_key(s), "second_access_key": reg3.access_key(integer_s),
        "first_statistical_status": first["statistical_status"], "second_statistical_status": second["statistical_status"],
        "decision": first["decision"], "official": first["official"],
    }

# The registered envelope margin exceeds stationarity but is silently capped at 0.99.
margin_s = deepcopy(s)
margin_s["feasibility"]["margin"] = 2.
estimate = G.development_dependence_estimate(dev, dataset_role="DEVELOPMENT", dataset_id="audit-dev",
                                           estimator=G.ESTIMATORS[0])
envelope = G.combined_envelope(G.validate_registration(margin_s), estimate)
out["unapproved_envelope_cap"] = {"registered_margin": 2., "estimate_phi": estimate["phi"],
                                   "points": envelope, "contains_hardcoded_point_099":
                                   any(point["phi"] == .99 for point in envelope)}
print(json.dumps(out, indent=2, sort_keys=True))
