"""Additive M-B v2 under CDR-006/010; synthetic validation only.

No v1 globals, records, or arithmetic are replaced. CDR-010 fixes fsum,
direct block sums, block-grouped replicate means and the run() standard-error
degeneracy predicate. Numerical configuration and real data access stay closed.
"""
from copy import deepcopy
from hashlib import sha1
import json
import math
from pathlib import Path
import random

from . import superiority as legacy
from .calibration_contracts import IntegrityFailure, MissingPrerequisite, finite_number
from .statistical_kernels import MissingStatisticalEvidence, _series, _positive_integer, circular_block_indices
from .superiority_source_identity import IdentityBoundGsupRegistry
from .walkforward import digest

METHOD = "C8_GSUP_STUDENTIZED_CBB_v2"
POLICY = "TC-C8-GSUP-M-V2-CDR006-CDR010"
ARITHMETIC_CONTRACT = {
    "reducer": "MATH_FSUM", "replicate_aggregation": "BLOCK_GROUPING",
    "block_sums": "DIRECT", "degeneracy": "SQRT_V_OVER_N_GT_ZERO",
}
APPROVAL_PATH = (Path(__file__).resolve().parents[3] / "docs/codex_takeover/"
                "gsup_v2_handoff_2026_10_03/evidence/authoritative-v2/CDR010_APPROVAL.json")
APPROVAL_BLOB = "3a9eecbba5a7454c5d81ee6db209aecc4bdf113b"


def authority():
    """Pinned original M/source approval and separately recorded CDR-010."""
    legacy.authority()
    raw = APPROVAL_PATH.read_bytes()
    if sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() != APPROVAL_BLOB:
        raise IntegrityFailure("changed v2 arithmetic approval authority")
    record = json.loads(raw)
    original, expected = legacy.REPORTS / "track_c_c8_gsup_v2_source_identity_approval_2026-10-03.json", \
        "a5279d516c028f0a8cb9166ee2d54366da00877b"
    source = original.read_bytes()
    if sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest() != expected:
        raise IntegrityFailure("changed M-v2/source-identity approval")
    if record["method"] != METHOD or record["arithmetic_contract"] != ARITHMETIC_CONTRACT:
        raise IntegrityFailure("v2 approved arithmetic contract mismatch")
    return record


def studentized_cbb(delta, *, block_length, replicates, seed):
    """Normalize unsupported finite arithmetic range to NOT_RUN, without fallback."""
    authority()
    x = _series(delta)
    try:
        return _studentized_cbb(x, block_length=block_length, replicates=replicates, seed=seed)
    except (OverflowError, ZeroDivisionError) as exc:
        raise MissingStatisticalEvidence("unsupported finite arithmetic range") from exc


def _studentized_cbb(x, *, block_length, replicates, seed):
    """M-B: q=ceil(n/L)-1 variance blocks, plus a final 1..L block.

    The last block is excluded from replicate variance even when n is divisible
    by L. Degenerate replicates do not exceed; ties do. All B draws retain the
    plus-one denominator. No tolerance, rounding, fallback or numeric default.
    """
    _positive_integer(block_length, "block_length")
    _positive_integer(replicates, "replicates")
    if type(seed) is not int:
        raise ValueError("explicit integer seed required")
    n, length = len(x), block_length
    blocks = (n + length - 1) // length - 1
    if length > n or blocks < 2:
        raise MissingStatisticalEvidence("fewer than two M-B variance blocks")
    mean = math.fsum(x) / n
    sums = [math.fsum(x[(start + j) % n] for j in range(length)) for start in range(n)]
    lrv = math.fsum((b - length * mean) ** 2 for b in sums) / (n * length)
    if not math.isfinite(lrv):
        raise MissingStatisticalEvidence("nonfinite long-run variance")
    se = math.sqrt(lrv / n)
    if not se > 0:
        raise MissingStatisticalEvidence("zero standard error; statistic undefined")
    statistic = mean / se
    if not math.isfinite(statistic):
        raise MissingStatisticalEvidence("nonfinite observed statistic")
    indices = circular_block_indices(n=n, block_length=length, replicates=replicates, seed=seed)
    draws, traces, exceed, degenerate, ties = [], [], 0, 0, 0
    for ix in indices:
        values = [x[i] for i in ix]
        full_sums = [math.fsum(values[j * length:(j + 1) * length]) for j in range(blocks)]
        partial = math.fsum(values[blocks * length:])
        ms = (math.fsum(full_sums) + partial) / n
        variance = math.fsum((b - length * ms) ** 2 for b in full_sums) / (blocks * length)
        if not math.isfinite(variance):
            raise MissingStatisticalEvidence("nonfinite replicate variance")
        sv = math.sqrt(variance / n)
        is_degenerate = not sv > 0
        t = None if is_degenerate else (ms - mean) / sv
        if t is not None and not math.isfinite(t):
            raise MissingStatisticalEvidence("nonfinite replicate statistic")
        tie = not is_degenerate and t == statistic
        exceeds = not is_degenerate and t >= statistic
        degenerate += is_degenerate
        ties += tie
        exceed += exceeds
        draws.append(t)
        traces.append({"replicate_mean": ms, "variance": variance, "se": sv,
                       "block_sums": tuple(full_sums), "partial_sum": partial,
                       "statistic": t, "degenerate": is_degenerate, "tie": tie, "exceeds": exceeds})
    return {"method": METHOD, "arithmetic_contract": deepcopy(ARITHMETIC_CONTRACT),
            "n": n, "mean": mean, "long_run_variance": lrv, "statistic": statistic,
            "variance_blocks": blocks, "exceedances": exceed, "degenerate_replicates": degenerate,
            "ties": ties, "replicates": replicates, "p_value": (exceed + 1) / (replicates + 1),
            "draws": tuple(draws), "traces": tuple(traces), "indices_hash": digest(indices),
            "block_length": length, "seed": seed, "one_sided": "GREATER"}


def validate_registration(spec):
    """Reuse frozen conditional gates structurally, without relabeling v1 records."""
    authority()
    s = deepcopy(spec)
    if s.get("schema") != METHOD or s.get("policy") != POLICY:
        raise IntegrityFailure("explicit approved v2 method/policy required; no fallback")
    compatibility = {**s, "schema": legacy.METHOD, "policy": legacy.POLICY}
    legacy.validate_registration(compatibility)
    return s


def assess_feasibility(registration, estimate):
    """Development-only pre-access size check with the actual v2 procedure."""
    s = validate_registration(registration)
    legacy.validate_estimate(estimate, s)
    f, n, alpha, B = s["feasibility"], s["verify_periods"], s["alpha"], s["replicates"]
    length = legacy._block_length(s["block_rule"], n)
    reasons = []
    if 1 / (B + 1) > alpha:
        reasons.append("ALPHA_UNREACHABLE_AT_B")
    if n < s["minimum_support"]:
        reasons.append("BELOW_MINIMUM_SUPPORT")
    if length > n or (n + length - 1) // length - 1 < 2:
        reasons.append("FEWER_THAN_TWO_VARIANCE_BLOCKS")
    points = legacy.combined_envelope(s, estimate)
    sizes = []
    if not reasons:
        for point in points:
            rng = random.Random(int(digest([f["seed"], point])[:16], 16))
            rejected = undefined = 0
            for _ in range(f["replications"]):
                try:
                    p = studentized_cbb(legacy._null_series(rng, n, point["phi"]), block_length=length,
                                        replicates=B, seed=s["seed"])["p_value"]
                except MissingStatisticalEvidence:
                    undefined += 1
                    continue
                rejected += p <= alpha
            size = rejected / f["replications"]
            sizes.append({"point": point, "empirical_size": size, "undefined": undefined,
                          "within_tolerance": size <= alpha + f["size_tolerance"]})
        if any(not row["within_tolerance"] for row in sizes):
            reasons.append("EMPIRICAL_SIZE_EXCEEDS_TOLERANCE")
    record = {"method": METHOD, "arithmetic_contract": deepcopy(ARITHMETIC_CONTRACT),
              "registration_hash": digest(s), "status": "FEASIBLE" if not reasons else "NOT_RUN_INFEASIBLE",
              "reasons": reasons, "envelope": points, "sizes": sizes, "development_estimate": estimate,
              "cal_verify_read": False, "configuration_scope": legacy.FIXTURE_SCOPE}
    record["record_hash"] = digest(record)
    return record


def _evaluate(s, data):
    if (not isinstance(data, dict) or data.get("dataset_role") != "CAL_VERIFY"
            or data.get("dataset_id") != s["verify_dataset_id"] or data.get("role_id") != s["role_id"]):
        raise IntegrityFailure("provider must return the registered synthetic target only")
    if data.get("synthetic") is not True:
        raise MissingPrerequisite("real CAL_VERIFY access is not approved")
    if set(data["cohorts"]) != set(s["cohorts"]) or digest(data["cohorts"]) != s["verify_content_hash"]:
        raise IntegrityFailure("provider cohorts/content differ from preregistered commitment")
    length = legacy._block_length(s["block_rule"], s["verify_periods"])
    cells = {}
    for cohort in sorted(s["cohorts"]):
        block = data["cohorts"][cohort]
        if set(block["controls"]) != set(s["controls"]):
            raise IntegrityFailure("provider controls differ from registration")
        role = block["role"]
        for control in sorted(s["controls"]):
            other = block["controls"][control]
            if len(role) != s["verify_periods"] or len(other) != s["verify_periods"]:
                raise IntegrityFailure("observed periods differ from registered calendar")
            for value in list(role) + list(other):
                finite_number(value)
            delta = tuple(a - b for a, b in zip(role, other))
            name = f"{cohort}|{control}"
            if any(not math.isfinite(value) for value in delta):
                cells[name] = {"status": "NOT_RUN", "reason": "nonfinite derived return difference"}
                continue
            try:
                out = studentized_cbb(delta, block_length=length, replicates=s["replicates"], seed=s["seed"])
            except MissingStatisticalEvidence as exc:
                cells[name] = {"status": "NOT_RUN", "reason": str(exc)}
                continue
            cell = {k: v for k, v in out.items() if k not in {"draws", "traces"}}
            cell["draws_hash"], cell["traces_hash"] = digest(out["draws"]), digest(out["traces"])
            cell["status"] = "REJECT_H0" if out["p_value"] <= s["alpha"] else "NOT_REJECTED"
            if s["comparison_evidence"]:
                cell["comparison"] = legacy.comparison_unstudentized(
                    delta, block_length=length, replicates=s["replicates"], seed=s["seed"])
            cells[name] = cell
    return cells


class GsupV2Registry(IdentityBoundGsupRegistry):
    """Same trusted one-shot store as v1 identity wrapper; no version reset."""
    _validate_spec = staticmethod(validate_registration)
    _feasibility = staticmethod(assess_feasibility)
    _evaluate = staticmethod(_evaluate)

    @staticmethod
    def _result(spec, statistical, decision, cells, reasons):
        return {**legacy._result(spec, statistical, decision, cells, reasons),
                "method": METHOD, "arithmetic_contract": deepcopy(ARITHMETIC_CONTRACT)}

    @staticmethod
    def _attach(result, binding):
        return {**IdentityBoundGsupRegistry._attach(result, binding),
                "validation_mode": "SYNTHETIC_M_B_V2_ONLY"}
