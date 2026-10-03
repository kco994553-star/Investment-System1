"""C8 G-SUP: designated role vs control one-sided superiority (A6 S1-S8, method Q1-Q6).

Versioned studentized circular-block bootstrap-t with a pre-access size-feasibility
gate and one-shot CAL_VERIFY protocol. No numeric research default exists here:
every alpha/B/L/seed/tolerance/envelope/support value must be preregistered, and
only SYNTHETIC_SOFTWARE_VALIDATION_ONLY values are accepted until a separate
numeric approval. There is no real CAL_VERIFY or Holdout reader.
"""
from copy import deepcopy
from hashlib import sha1
import json
import math
import os
from pathlib import Path
import random

from .calibration_contracts import IntegrityFailure, MissingPrerequisite, identity, instant, finite_number
from .ledger import canonical_json
from .selection_contracts import PROFILES
from .statistical_kernels import (MissingStatisticalEvidence, _series, _positive_integer,
                                  circular_block_indices, family_reality_check)
from .walkforward import digest

METHOD = "C8_GSUP_STUDENTIZED_CBB_v1"
POLICY = "TC-C8-A6-METHOD-Q1-Q6-2026-10-02"
REPORTS = Path(__file__).resolve().parents[3] / "reports"
APPROVALS = {
    "A6_PARTIAL": (REPORTS / "track_c_c8_a6_partial_approval_2026-10-02.json",
                   "4f897ec79f341653d8a69aecdfe7aa7eb33b6566"),
    "A6_METHOD": (REPORTS / "track_c_c8_a6_method_approval_2026-10-02.json",
                  "a6f994144ac8e7073c74fdd16983c92eac54eb5f"),
}
SCOPE = "SYNTHETIC_SOFTWARE_VALIDATION"
FIXTURE_SCOPE = "SYNTHETIC_SOFTWARE_VALIDATION_ONLY"
SUPPORTED_CONTROLS = ("EQUAL_SIMPLE", "MARKET_CAP")
UNSUPPORTED_CONTROLS = {"RANDOM_RANKING": "UNSUPPORTED_SINGLE_DRAW",
                        "RANDOMIZED_WEIGHTS": "UNSUPPORTED_SINGLE_DRAW"}
REQUIRED_COHORTS = tuple(f"{m}-{v}" for m in ("ROLLING", "EXPANDING")
                         for v in ("PRIMARY", "REBALANCE_GAP_STRESS"))
NOT_SUPERIORITY_EVIDENCE = ("PSR", "DSR", "PBO", "FAMILY_REALITY_CHECK", "ABSOLUTE_POSITIVE_RETURN",
                            "POSITIVE_SHARPE", "C6_DIAGNOSTIC_PASS")
COMPARISON_ONLY = "C8_GSUP_U_v1"            # existing C6 unstudentized kernel, never a hard decision
INACTIVE = {COMPARISON_ONLY: "COMPARISON_EVIDENCE_ONLY",
            "C8_GSUP_BATCH_MEANS_T_v1": "INACTIVE_NO_FALLBACK"}
ROLES = ("CHAMPION", "CHALLENGER")
EVIDENCE_KIND = "CONTROL_RELATIVE_PERIOD_NET_RETURN_DIFFERENCE"
ESTIMATORS = ("AR1_LAG1_AUTOCORRELATION_v1",)
EFFECT_FLOOR = {"convention": "DEFERRED_A6_S7", "value": None}


class UnsupportedControl(MissingPrerequisite):
    """Control exists in C6 but cannot support a G-SUP hard decision."""


def authority():
    """Both A6 approval records, pinned by Git blob identity."""
    out = {}
    for name, (path, blob) in APPROVALS.items():
        raw = path.read_bytes()
        if sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() != blob:
            raise IntegrityFailure("changed/missing A6 approval authority: " + name)
        out[name] = json.loads(raw)
    if out["A6_METHOD"]["Q"]["Q1"]["approved_method"] != METHOD:
        raise IntegrityFailure("approved G-SUP method mismatch")
    if out["A6_PARTIAL"]["supported_controls"] != list(SUPPORTED_CONTROLS):
        raise IntegrityFailure("approved control set mismatch")
    return out


def reject_superiority_substitute(kind):
    """S1: these existing outputs never establish control-relative superiority."""
    if kind in NOT_SUPERIORITY_EVIDENCE:
        raise IntegrityFailure(kind + " is not control-relative superiority evidence")
    if kind != EVIDENCE_KIND:
        raise IntegrityFailure("unregistered superiority evidence kind")
    return kind


def studentized_cbb(delta, *, block_length, replicates, seed):
    """One-sided studentized circular-block bootstrap-t for H0: E[delta] <= 0.

    T = mean/se, se^2 = overlapping circular block long-run variance / n.
    T*_b = (mean*_b - mean)/se*_b, se*_b from the replicate's full-block sums.
    Indices come from the frozen C6 `circular_block_indices` convention.
    A degenerate replicate (zero variance) counts as an exceedance (conservative).
    p = (r+1)/(B+1) with r = #{T*_b >= T}.
    """
    x = _series(delta)
    _positive_integer(block_length, "block_length")
    _positive_integer(replicates, "replicates")
    n, L = len(x), block_length
    full = n // L
    if L > n or full < 2:
        raise MissingStatisticalEvidence("fewer than two full replicate blocks")
    m = math.fsum(x) / n
    sums = [math.fsum(x[(s + j) % n] for j in range(L)) for s in range(n)]
    lrv = math.fsum((s - L * m) ** 2 for s in sums) / (n * L)
    if not lrv > 0:
        raise MissingStatisticalEvidence("zero long-run variance; statistic undefined")
    statistic = m / math.sqrt(lrv / n)
    indices = circular_block_indices(n=n, block_length=L, replicates=replicates, seed=seed)
    draws, exceed, degenerate = [], 0, 0
    for ix in indices:
        values = [x[i] for i in ix]
        ms = math.fsum(values) / n
        blocks = [math.fsum(values[j * L:(j + 1) * L]) for j in range(full)]
        v = math.fsum((b - L * ms) ** 2 for b in blocks) / (full * L)
        if not v > 0:
            degenerate += 1
            exceed += 1
            draws.append(None)
            continue
        t = (ms - m) / math.sqrt(v / n)
        draws.append(t)
        exceed += t >= statistic
    return {"method": METHOD, "n": n, "mean": m, "long_run_variance": lrv, "statistic": statistic,
            "exceedances": exceed, "degenerate_replicates": degenerate, "replicates": replicates,
            "p_value": (exceed + 1) / (replicates + 1), "draws": tuple(draws),
            "indices_hash": digest(indices), "block_length": L, "seed": seed, "one_sided": "GREATER"}


def comparison_unstudentized(delta, *, block_length, replicates, seed):
    """Q1-A preserved as comparison evidence only: frozen C6 singleton Reality Check kernel."""
    x = _series(delta)
    rc = family_reality_check(("ROLE",), {"ROLE": x}, (0.,) * len(x),
                              block_length=block_length, replicates=replicates, seed=seed)
    r = sum(d >= rc["observed_max_mean_statistic"] for d in rc["centered_bootstrap_statistics"])
    return {"method": COMPARISON_ONLY, "role": "COMPARISON_EVIDENCE_ONLY_NOT_DECISION",
            "kernel_tail_fraction": rc["tail_fraction"], "p_value_plus_one": (r + 1) / (replicates + 1),
            "indices_hash": rc["indices_hash"]}


def _block_length(rule, n):
    if not isinstance(rule, dict) or "kind" not in rule:
        raise MissingPrerequisite("preregistered block convention required")
    if rule["kind"] == "FIXED":
        if set(rule) != {"kind", "block_length"}:
            raise IntegrityFailure("fixed block convention fields")
        _positive_integer(rule["block_length"], "block_length")
        return rule["block_length"]
    if rule["kind"] == "DETERMINISTIC_RULE":
        raise MissingPrerequisite("no deterministic block rule is approved yet")
    raise IntegrityFailure("data-driven or unknown block selection is forbidden")


def _numeric(spec, field):
    value = spec.get(field)
    if value is None:
        raise MissingPrerequisite("numeric configuration not approved: " + field)
    return value


def validate_registration(spec):
    """Every Q1-Q6 convention fixed before any CAL_VERIFY access. No default is filled."""
    s = deepcopy(spec)
    fields = {"schema", "policy", "scope", "configuration_scope", "temporal_origin", "registered_at",
              "campaign_id", "profile", "role", "role_id", "role_designation_ref", "verify_dataset_id",
              "verify_content_hash", "development_dataset_id", "verify_periods", "controls", "cohorts", "evidence_kind", "comparison_evidence", "alpha",
              "replicates", "block_rule", "seed", "minimum_support", "feasibility", "effect_floor"}
    if set(s) != fields:
        raise IntegrityFailure("missing/unknown G-SUP registration fields")
    if s["schema"] != METHOD:
        if s["schema"] in INACTIVE:
            raise IntegrityFailure(s["schema"] + " is " + INACTIVE[s["schema"]] + "; no fallback")
        raise IntegrityFailure("unapproved G-SUP method")
    authority()
    if s["policy"] != POLICY:
        raise IntegrityFailure("policy mismatch")
    if s["scope"] != SCOPE or s["configuration_scope"] != FIXTURE_SCOPE or s["temporal_origin"] != "SIMULATED":
        raise MissingPrerequisite("real numeric configuration / CAL_VERIFY access not approved")
    instant(s["registered_at"])
    for f in ("campaign_id", "role_id", "verify_dataset_id", "role_designation_ref",
              "verify_content_hash", "development_dataset_id"):
        identity(s[f])
    if s["development_dataset_id"] == s["verify_dataset_id"]:
        raise IntegrityFailure("Development dependence evidence cannot be the CAL_VERIFY target")
    if s["profile"] not in PROFILES or s["role"] not in ROLES:
        raise IntegrityFailure("unknown profile/role")
    if s["role_designation_ref"] != "SYNTHETIC_FIXTURE_ROLE":
        raise MissingPrerequisite("A10 role designation is not approved")
    reject_superiority_substitute(s["evidence_kind"])
    controls = s["controls"]
    for c in controls:
        if c in UNSUPPORTED_CONTROLS:
            raise UnsupportedControl(c + ": " + UNSUPPORTED_CONTROLS[c])
    if sorted(controls) != sorted(SUPPORTED_CONTROLS) or len(set(controls)) != len(controls):
        raise IntegrityFailure("conjunction requires exactly every approved control")
    if sorted(s["cohorts"]) != sorted(REQUIRED_COHORTS) or len(set(s["cohorts"])) != len(s["cohorts"]):
        raise MissingPrerequisite("conjunction requires every required cohort")
    if s["comparison_evidence"] not in ([], [COMPARISON_ONLY]):
        raise IntegrityFailure("only the unstudentized kernel may be retained as comparison evidence")
    if s["effect_floor"] != EFFECT_FLOOR:
        raise IntegrityFailure("effect floor is deferred (A6-S7); no value and no zero default")
    _positive_integer(s["verify_periods"], "verify_periods")
    alpha = finite_number(_numeric(s, "alpha"))
    if not 0 < alpha < 1:
        raise IntegrityFailure("alpha must lie in (0, 1)")
    _positive_integer(_numeric(s, "replicates"), "replicates")
    _block_length(_numeric(s, "block_rule"), s["verify_periods"])
    if type(_numeric(s, "seed")) is not int:
        raise IntegrityFailure("explicit integer seed")
    _positive_integer(_numeric(s, "minimum_support"), "minimum_support")
    f = _numeric(s, "feasibility")
    if set(f) != {"size_tolerance", "conservative_envelope", "margin", "dependence_estimator",
                  "replications", "seed"}:
        raise IntegrityFailure("feasibility fields")
    for key in ("size_tolerance", "conservative_envelope", "margin", "replications", "seed"):
        _numeric(f, key)
    if f["dependence_estimator"] not in ESTIMATORS:
        raise IntegrityFailure("unregistered dependence estimator")
    if finite_number(f["size_tolerance"]) < 0 or finite_number(f["margin"]) < 0:
        raise IntegrityFailure("tolerance/margin must be nonnegative")
    _positive_integer(f["replications"], "feasibility replications")
    if type(f["seed"]) is not int:
        raise IntegrityFailure("explicit integer feasibility seed")
    if not f["conservative_envelope"]:
        raise MissingPrerequisite("conservative dependence envelope required")
    for point in f["conservative_envelope"]:
        _envelope_point(point)
    return s


def _envelope_point(point):
    if set(point) != {"kind", "phi"} or point["kind"] != "AR1_GAUSSIAN":
        raise IntegrityFailure("envelope point must be an explicit AR1_GAUSSIAN process")
    if not 0 <= finite_number(point["phi"]) < 1:
        raise IntegrityFailure("stationary AR1 coefficient required")
    return point


def development_dependence_estimate(series, *, dataset_role, dataset_id, estimator):
    """Q3 Development-only estimate; CAL_VERIFY/Holdout inputs are refused."""
    if dataset_role != "DEVELOPMENT":
        raise IntegrityFailure("dependence is estimated from Development evidence only")
    if estimator not in ESTIMATORS:
        raise IntegrityFailure("unregistered dependence estimator")
    x = _series(series, minimum=3)
    m = math.fsum(x) / len(x)
    denominator = math.fsum((v - m) ** 2 for v in x)
    if not denominator > 0:
        raise MissingStatisticalEvidence("zero Development variance")
    phi = math.fsum((x[t] - m) * (x[t - 1] - m) for t in range(1, len(x))) / denominator
    estimate = {"estimator": estimator, "dataset_role": "DEVELOPMENT", "dataset_id": identity(dataset_id),
                "n": len(x), "phi": phi, "series_hash": digest(x)}
    estimate["estimate_hash"] = digest(estimate)
    return estimate


def validate_estimate(estimate, registration):
    """Q3: only an intact Development-only estimate bound to the registration is usable."""
    if not isinstance(estimate, dict) or set(estimate) != {"estimator", "dataset_role", "dataset_id", "n",
                                                           "phi", "series_hash", "estimate_hash"}:
        raise IntegrityFailure("dependence estimate fields")
    if estimate["dataset_role"] != "DEVELOPMENT":
        raise IntegrityFailure("dependence is estimated from Development evidence only")
    if estimate["estimator"] != registration["feasibility"]["dependence_estimator"]:
        raise IntegrityFailure("estimate does not use the registered estimator")
    if (estimate["dataset_id"] != registration["development_dataset_id"]
            or estimate["dataset_id"] == registration["verify_dataset_id"]):
        raise IntegrityFailure("estimate is not bound to the registered Development dataset")
    if type(estimate["n"]) is not int or estimate["n"] < 3:
        raise IntegrityFailure("estimate support")
    if not -1 < finite_number(estimate["phi"]) < 1:
        raise IntegrityFailure("lag-1 autocorrelation outside (-1, 1)")
    identity(estimate["series_hash"])
    if digest({k: v for k, v in estimate.items() if k != "estimate_hash"}) != estimate["estimate_hash"]:
        raise IntegrityFailure("dependence estimate tampered")
    return estimate


def combined_envelope(registration, estimate):
    """Stricter of the Development estimate (+margin) and the conservative envelope: all must pass."""
    f = registration["feasibility"]
    validate_estimate(estimate, registration)
    phi = min(max(estimate["phi"], 0.) + f["margin"], 0.99)
    points = [dict(p) for p in f["conservative_envelope"]] + [{"kind": "AR1_GAUSSIAN", "phi": phi}]
    unique = {canonical_json(p): p for p in points}
    return [unique[k] for k in sorted(unique)]


def _null_series(rng, n, phi):
    burn, x, out = 50, 0., []
    scale = math.sqrt(1 - phi * phi)
    for t in range(n + burn):
        x = phi * x + rng.gauss(0., 1.)
        if t >= burn:
            out.append(x * scale)
    return out


def assess_feasibility(registration, estimate):
    """Q2/Q4/Q6: synthetic boundary-null size check under the exact registered procedure.

    Never reads CAL_VERIFY outcomes; uses only registered n (calendar), L, B, seed, alpha.
    """
    s = validate_registration(registration)
    validate_estimate(estimate, s)
    f, n, alpha, B = s["feasibility"], s["verify_periods"], s["alpha"], s["replicates"]
    L = _block_length(s["block_rule"], n)
    reasons = []
    if 1 / (B + 1) > alpha:
        reasons.append("ALPHA_UNREACHABLE_AT_B")
    if n < s["minimum_support"]:
        reasons.append("BELOW_MINIMUM_SUPPORT")
    if L > n or n // L < 2:
        reasons.append("FEWER_THAN_TWO_FULL_BLOCKS")
    points = combined_envelope(s, estimate)
    sizes = []
    if not reasons:
        for point in points:
            rng = random.Random(int(digest([f["seed"], point])[:16], 16))
            rejected = undefined = 0
            for _ in range(f["replications"]):
                try:
                    p = studentized_cbb(_null_series(rng, n, point["phi"]), block_length=L,
                                        replicates=B, seed=s["seed"])["p_value"]
                except MissingStatisticalEvidence:
                    undefined += 1
                    continue
                rejected += p <= alpha
            size = rejected / f["replications"]
            sizes.append({"point": point, "empirical_size": size, "undefined": undefined,
                          "within_tolerance": size <= alpha + f["size_tolerance"]})
        if any(not x["within_tolerance"] for x in sizes):
            reasons.append("EMPIRICAL_SIZE_EXCEEDS_TOLERANCE")
    record = {"method": METHOD, "registration_hash": digest(s), "status":
              "FEASIBLE" if not reasons else "NOT_RUN_INFEASIBLE", "reasons": reasons,
              "envelope": points, "sizes": sizes, "development_estimate": estimate,
              "cal_verify_read": False, "configuration_scope": FIXTURE_SCOPE}
    record["record_hash"] = digest(record)
    return record


class GsupRegistry:
    """Exclusive durable slots. Per-campaign registration under `root`; the one-shot
    CAL_VERIFY access intent, feasibility verdict and result live in the explicit
    shared `access_registry`, keyed by the preregistered CAL_VERIFY content commitment
    and profile/role only, so campaign, role_id, dataset label or registry root
    changes cannot reopen, retest or substitute (Q4/A6-S4)."""

    def __init__(self, root, access_registry):
        self.root = Path(root)
        self.shared = Path(access_registry)
        for d in (self.root, self.shared):
            d.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def target_key(spec):
        return digest({k: spec[k] for k in ("campaign_id", "profile", "role", "role_id", "verify_dataset_id")})

    @staticmethod
    def access_key(spec):
        return digest({k: spec[k] for k in ("verify_content_hash", "profile", "role")})

    @staticmethod
    def _create(directory, kind, key, payload):
        path = directory / f"{kind}-{key}.json"
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
        except FileExistsError:
            raise IntegrityFailure(kind + " already recorded for this target; no re-registration/retry")
        with os.fdopen(fd, "w") as handle:
            handle.write(canonical_json(payload) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return payload

    @staticmethod
    def _load(directory, kind, key):
        path = directory / f"{kind}-{key}.json"
        if not path.exists():
            return None
        raw = path.read_text()
        if not raw.endswith("\n"):
            raise IntegrityFailure("incomplete " + kind + " record")
        return json.loads(raw)

    def _spent(self, akey):
        return any(self._load(self.shared, kind, akey) is not None
                   for kind in ("feasibility", "access", "result"))

    def register(self, spec):
        s = validate_registration(spec)
        if self._spent(self.access_key(s)):
            raise IntegrityFailure("CAL_VERIFY target already assessed/verdicted; no retest under a new registration")
        key = self.target_key(s)
        self._create(self.root, "registration", key, {"registration": s, "registration_hash": digest(s),
                                                      "access_key": self.access_key(s)})
        return key

    def _registration(self, key):
        stored = self._load(self.root, "registration", key)
        if stored is None:
            raise MissingPrerequisite("registration required")
        s = validate_registration(stored["registration"])
        if digest(s) != stored["registration_hash"] or stored["access_key"] != self.access_key(s):
            raise IntegrityFailure("registration changed after preregistration")
        return s

    def record_feasibility(self, key, development_series, *, dataset_role, dataset_id):
        """Q2/Q3: the estimate is computed here from Development evidence; no external estimate."""
        s = self._registration(key)
        akey = self.access_key(s)
        if self._load(self.shared, "access", akey) is not None or self._load(self.shared, "result", akey) is not None:
            raise IntegrityFailure("feasibility after CAL_VERIFY access intent")
        estimate = development_dependence_estimate(development_series, dataset_role=dataset_role,
                                                   dataset_id=dataset_id,
                                                   estimator=s["feasibility"]["dependence_estimator"])
        record = assess_feasibility(s, estimate)
        record["registration_target"] = key
        record["record_hash"] = digest({k: v for k, v in record.items() if k != "record_hash"})
        return self._create(self.shared, "feasibility", akey, record)

    def assess(self, key, provider, *, accessed_at):
        s = self._registration(key)
        akey = self.access_key(s)
        feasibility = self._load(self.shared, "feasibility", akey)
        if feasibility is None:
            raise MissingPrerequisite("pre-access feasibility required")
        body = {k: v for k, v in feasibility.items() if k != "record_hash"}
        if digest(body) != feasibility["record_hash"] or feasibility["registration_hash"] != digest(s) \
                or feasibility["registration_target"] != key:
            raise IntegrityFailure("feasibility record tampered or bound to another registration")
        if instant(accessed_at) <= instant(s["registered_at"]):
            raise IntegrityFailure("CAL_VERIFY access must follow preregistration")
        if self._load(self.shared, "result", akey) is not None or self._load(self.shared, "access", akey) is not None:
            raise IntegrityFailure("CAL_VERIFY is one-shot; no retry for this target")
        if feasibility["status"] != "FEASIBLE":
            return self._create(self.shared, "result", akey, _result(s, "NOT_RUN_INFEASIBLE", "NOT_RUN_INFEASIBLE",
                                                                     {}, feasibility["reasons"]))
        self._create(self.shared, "access", akey, {"registration_hash": digest(s), "accessed_at": accessed_at,
                                                   "cal_verify_target": s["verify_dataset_id"],
                                                   "verify_content_hash": s["verify_content_hash"]})
        try:
            data = provider(s["verify_dataset_id"])
            cells = _evaluate(s, data)
        except BaseException as exc:
            self._create(self.shared, "result", akey, _result(s, "NOT_RUN", "CRASH_NO_RETRY", {},
                                                              [type(exc).__name__]))
            raise
        statuses = [c["status"] for c in cells.values()]
        if any(x == "NOT_RUN" for x in statuses):
            stat = "NOT_RUN"
        elif all(x == "REJECT_H0" for x in statuses):
            stat = "STAT_PASS"
        else:
            stat = "STAT_FAIL"
        return self._create(self.shared, "result", akey, _result(s, stat, "NOT_RUN_EFFECT_FLOOR_DEFERRED", cells, []))


def _evaluate(s, data):
    if (not isinstance(data, dict) or data.get("dataset_role") != "CAL_VERIFY"
            or data.get("dataset_id") != s["verify_dataset_id"] or data.get("role_id") != s["role_id"]):
        raise IntegrityFailure("provider must return the registered CAL_VERIFY target only")
    if data.get("synthetic") is not True:
        raise MissingPrerequisite("real CAL_VERIFY access is not approved")
    if set(data["cohorts"]) != set(s["cohorts"]):
        raise IntegrityFailure("provider cohorts differ from registration")
    if digest(data["cohorts"]) != s["verify_content_hash"]:
        raise IntegrityFailure("CAL_VERIFY content differs from the preregistered commitment")
    L = _block_length(s["block_rule"], s["verify_periods"])
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
            for v in list(role) + list(other):
                finite_number(v)
            delta = tuple(a - b for a, b in zip(role, other))
            name = f"{cohort}|{control}"
            try:
                out = studentized_cbb(delta, block_length=L, replicates=s["replicates"], seed=s["seed"])
            except MissingStatisticalEvidence as exc:
                cells[name] = {"status": "NOT_RUN", "reason": str(exc)}
                continue
            cell = {k: v for k, v in out.items() if k != "draws"}
            cell["draws_hash"] = digest([d for d in out["draws"]])
            cell["status"] = "REJECT_H0" if out["p_value"] <= s["alpha"] else "NOT_REJECTED"
            if s["comparison_evidence"]:
                cell["comparison"] = comparison_unstudentized(delta, block_length=L,
                                                             replicates=s["replicates"], seed=s["seed"])
            cells[name] = cell
    return cells


def _result(s, statistical, decision, cells, reasons):
    return {"method": METHOD, "registration_hash": digest(s), "statistical_status": statistical,
            "decision": decision, "claim": "ALL_APPROVED_CONTROLS_ALL_REQUIRED_COHORTS",
            "cells": cells, "reasons": reasons, "effect_floor": EFFECT_FLOOR,
            "unsupported_controls": UNSUPPORTED_CONTROLS, "scope": SCOPE,
            "official": False, "promotion_authority": None, "real_holdout_eligible": False}
