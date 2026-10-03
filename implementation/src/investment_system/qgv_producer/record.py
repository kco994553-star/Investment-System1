"""QGV_COMPANY_RESULT v1: one company's existing QGV engine output, persisted with PIT and lineage.

This is not a new score model. `semantic.qgv` is the engine's own `QGVSnapshot`, serialized verbatim
except for `qgv_snapshot_id`. That id is a fresh UUID per run, so it is kept under `operational`.
The record only adds what the snapshot does not carry:
- the Q/G/V sub-factor observations the engine actually scored;
- PIT timestamps and the raw-artifact lineage (sha256);
- the cross-section rank the engine produced;
- the research state.

Determinism: `semantic_sha256` is the sha256 of the canonical JSON of `semantic`. The same code, data,
methodology, as_of and Universe give the same hash. `operational` (generated_at, snapshot UUID, code
commit, run id) is excluded.

Validation fails closed (`QGVProducerError`). A record can be PASS only with real (non-synthetic)
inputs, PIT timestamps no later than as_of, hashed lineage, and a research state that is not promoted.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
from datetime import date, datetime
from enum import Enum
from typing import Any, Iterable, Mapping

from ..contracts.enums import CalibrationLifecycle, CoverageState, ProfileKind, QualityState
from ..contracts.models import QGVSnapshot, VCandidate
from ..qgv.factors import G_WEIGHTS, Q_WEIGHTS, V_CANDIDATES, V_INITIAL_PRIOR

RECORD_KIND = "QGV_COMPANY_RESULT"
RECORD_VERSION = 1
STATUSES = ("PASS", "FAIL", "NOT_RUN")  # same vocabulary as Track A gates and Producer Infrastructure validation
RESEARCH_STATUS = "PROVISIONAL_RESEARCH"  # validation.vertical_slice.RULE_STATUS, copied verbatim
PROMOTED_VALUES = frozenset({"OFFICIAL", "VALIDATED", "PROMOTED", "LIVE_OFFICIAL", "LIVE", "STANDARD", "CALIBRATED",
                             "VALIDATION_SELECTED", "OOS_TESTED", "PIT_TESTED"})
# Post-as_of evaluation data must never enter a PIT snapshot.
OUTCOME_KEYS = frozenset({"realized_return", "px1", "horizon_as_of", "outcomes", "outcome_metrics",
                          "equal_weight_realized", "realized"})
KNOWN_PIT_LIMITATIONS = (
    # validation.historical.pit_integrity_report: filed<=as_of is necessary but not sufficient Full PIT.
    "SEC_COMPANYFACTS_VALUE_MAY_BE_RESTATED",
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class QGVProducerError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


# ---------------------------------------------------------------- canonical JSON (same settings as Producer Infra v1)
def to_jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return to_jsonable(value.value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise QGVProducerError("SERIALIZATION", "naive datetime")
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        out = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise QGVProducerError("SERIALIZATION", f"non-string key {k!r}")
            out[k] = to_jsonable(v)
        return out
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise QGVProducerError("SERIALIZATION", "NaN/Infinity is not valid JSON")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise QGVProducerError("SERIALIZATION", f"unsupported type {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(to_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_hex(canonical_bytes(value))


def parse_ts(value: Any, where: str) -> datetime:
    if not isinstance(value, str):
        raise QGVProducerError("PIT_EVIDENCE_MISSING", f"{where} must be an ISO timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise QGVProducerError("PIT_EVIDENCE_MISSING", f"{where} unparsable: {value!r}") from e
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise QGVProducerError("PIT_EVIDENCE_MISSING", f"{where} must be timezone-aware")
    return dt


# ---------------------------------------------------------------- methodology identity
def methodology_config() -> dict:
    """The frozen weights the engine scores with (qgv/factors.py), read, not copied into a new standard."""
    return {
        "Q_WEIGHTS": dict(Q_WEIGHTS),
        "G_WEIGHTS": dict(G_WEIGHTS),
        "V_INITIAL_PRIOR": dict(V_INITIAL_PRIOR),
        "V_CANDIDATES": {k: {"weights": dict(v["weights"]), "lifecycle": v["lifecycle"]} for k, v in V_CANDIDATES.items()},
    }


def methodology_config_sha256() -> str:
    return canonical_sha256(methodology_config())


def snapshot_semantic(snapshot: QGVSnapshot) -> dict:
    d = to_jsonable(snapshot)
    d.pop("qgv_snapshot_id")
    return d


def sub_factor_table(observations: Mapping[str, Any]) -> dict:
    return {fid: {"raw_value": o.raw_value, "score_0_100": o.score_0_100, "quality": to_jsonable(o.quality),
                  "stamp_id": o.stamp_id, "notes": o.notes}
            for fid, o in sorted(observations.items())}


# ---------------------------------------------------------------- validation
def _walk_keys(v: Any) -> Iterable[str]:
    if isinstance(v, dict):
        for k, x in v.items():
            yield k
            yield from _walk_keys(x)
    elif isinstance(v, list):
        for x in v:
            yield from _walk_keys(x)


def check_research_state(rs: Any) -> None:
    if not isinstance(rs, dict):
        raise QGVProducerError("RESEARCH_STATE", "research_state required")
    if rs.get("status") != RESEARCH_STATUS:
        raise QGVProducerError("PROMOTION_FORBIDDEN", f"research_state.status must stay {RESEARCH_STATUS}, got {rs.get('status')!r}")
    if str(rs.get("v_policy_status")) in PROMOTED_VALUES:
        raise QGVProducerError("PROMOTION_FORBIDDEN", f"V policy {rs.get('v_policy_status')!r} is not promotable here")
    for k in ("official_selection", "official_pass", "full_pit_pass", "calibrated", "track_c_validated"):
        if rs.get(k) is not False:
            raise QGVProducerError("PROMOTION_FORBIDDEN", f"research_state.{k} must be false")


def validate_semantic(sem: Mapping, *, require_real: bool = True) -> None:
    """Fail-closed checks for one record's semantic content. PASS requirements apply when status == PASS."""
    if not isinstance(sem, Mapping):
        raise QGVProducerError("SCHEMA", "semantic must be an object")
    for k in ("company_id", "ticker", "as_of", "status", "status_reasons", "universe", "methodology", "research_state",
              "synthetic", "pit", "lineage", "qgv", "sub_factors", "cross_section"):
        if k not in sem:
            raise QGVProducerError("SCHEMA", f"semantic.{k} absent")
    cid = sem["company_id"]
    if not isinstance(cid, str) or not cid:
        raise QGVProducerError("IDENTITY", "company_id required")
    if sem["status"] not in STATUSES:
        raise QGVProducerError("SCHEMA", f"status {sem['status']!r} not in {STATUSES}")
    as_of = parse_ts(sem["as_of"], "as_of")
    check_research_state(sem["research_state"])
    leaked = OUTCOME_KEYS.intersection(_walk_keys(dict(sem)))
    if leaked:
        raise QGVProducerError("OUTCOME_LEAK", f"post-as_of keys present: {sorted(leaked)}")
    if not isinstance(sem["synthetic"], bool):
        raise QGVProducerError("SYNTHETIC_STATE", "synthetic must be boolean")
    if sem["status"] != "PASS":
        if not sem["status_reasons"]:
            raise QGVProducerError("SCHEMA", f"{sem['status']} requires status_reasons")
        return
    q = sem["qgv"]
    if not isinstance(q, dict):
        raise QGVProducerError("SCHEMA", "PASS requires the engine QGVSnapshot")
    if q.get("company_id") != cid:
        raise QGVProducerError("IDENTITY", f"snapshot company_id {q.get('company_id')!r} != {cid!r}")
    if parse_ts(q.get("as_of"), "qgv.as_of") != as_of:
        raise QGVProducerError("IDENTITY", "snapshot as_of differs from record as_of")
    for k in ("Q_score", "G_score", "V_score", "total_score", "coverage_state", "qgv_analysis_contract"):
        if k not in q:
            raise QGVProducerError("SCHEMA", f"qgv.{k} absent")
    m = sem["methodology"]
    for k in ("qgv_system_version", "qgv_standard_version", "qgv_analysis_contract", "implementation_line"):
        if m.get(k) != q.get(k):
            raise QGVProducerError("METHODOLOGY", f"methodology.{k} {m.get(k)!r} != snapshot {q.get(k)!r}")
    if not isinstance(m.get("weights_sha256"), str) or not _HEX64.match(m["weights_sha256"]):
        raise QGVProducerError("METHODOLOGY", "weights_sha256 required")
    if not isinstance(sem["sub_factors"], dict) or not sem["sub_factors"]:
        raise QGVProducerError("SCHEMA", "PASS requires sub-factor observations")
    # synthetic / real consistency
    marked = (q.get("synthetic") is True or q.get("coverage_state") == CoverageState.SYNTHETIC.value
              or QualityState.SYNTHETIC.value in (q.get("quality_states") or [])
              or any(v.get("quality") == QualityState.SYNTHETIC.value for v in sem["sub_factors"].values())
              or sem["pit"].get("fundamentals_synthetic") is True
              or any(str(i.get("source_kind", "")).upper().startswith("SYNTHETIC") for i in (sem["lineage"].get("inputs") or [])))
    if marked != sem["synthetic"]:
        raise QGVProducerError("SYNTHETIC_STATE", f"synthetic={sem['synthetic']} but inputs/snapshot say synthetic={marked}")
    if require_real and sem["synthetic"]:
        raise QGVProducerError("SYNTHETIC_STATE", "the real producer does not export synthetic results")
    # PIT
    p = sem["pit"]
    avail = parse_ts(p.get("fundamentals_available_at"), "pit.fundamentals_available_at")
    if avail > as_of:
        raise QGVProducerError("PIT_VIOLATION", f"fundamentals available_at {avail.isoformat()} > as_of {as_of.isoformat()}")
    for k in ("price_observed_at", "prior_year_price_observed_at"):
        if p.get(k) is not None and parse_ts(p[k], f"pit.{k}") > as_of:
            raise QGVProducerError("PIT_VIOLATION", f"{k} {p[k]} > as_of {as_of.isoformat()}")
    # provenance
    inputs = sem["lineage"].get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise QGVProducerError("MISSING_PROVENANCE", "no hashed raw input")
    seen = set()
    for i in inputs:
        aid = i.get("artifact_id") if isinstance(i, dict) else None
        if not isinstance(aid, str) or not aid.startswith("raw:"):
            raise QGVProducerError("MISSING_PROVENANCE", f"input artifact_id {aid!r} is not a raw store id")
        if aid in seen:
            raise QGVProducerError("MISSING_PROVENANCE", f"duplicate input {aid}")
        seen.add(aid)
        if not isinstance(i.get("sha256"), str) or not _HEX64.match(i["sha256"]):
            raise QGVProducerError("SOURCE_HASH", f"invalid sha256 for {aid}")
    if not any(a.startswith("raw:companyfacts:") for a in seen):
        raise QGVProducerError("MISSING_PROVENANCE", "fundamentals source (companyfacts) not in lineage")


def make_record(semantic: dict, operational: dict) -> dict:
    sem = to_jsonable(semantic)
    return {"record_kind": RECORD_KIND, "record_version": RECORD_VERSION, "semantic": sem,
            "semantic_sha256": canonical_sha256(sem), "operational": to_jsonable(operational)}


def validate_record(rec: Any, *, require_real: bool = True) -> dict:
    if not isinstance(rec, dict) or rec.get("record_kind") != RECORD_KIND:
        raise QGVProducerError("SCHEMA", f"record_kind must be {RECORD_KIND}")
    if rec.get("record_version") != RECORD_VERSION:
        raise QGVProducerError("SCHEMA", f"unsupported record_version {rec.get('record_version')!r}")
    if rec.get("semantic_sha256") != canonical_sha256(rec.get("semantic")):
        raise QGVProducerError("SEMANTIC_HASH", "semantic_sha256 does not match semantic content")
    validate_semantic(rec["semantic"], require_real=require_real)
    op = rec.get("operational")
    if not isinstance(op, dict):
        raise QGVProducerError("SCHEMA", "operational required")
    if rec["semantic"]["qgv"] is not None and not op.get("qgv_snapshot_id"):
        raise QGVProducerError("IDENTITY", "operational.qgv_snapshot_id required when a snapshot is persisted")
    return rec


# ---------------------------------------------------------------- reconstruction (verbatim, no rescoring)
def qgv_snapshot_from_record(rec: Mapping) -> QGVSnapshot:
    """Rebuild the engine's QGVSnapshot exactly; to_jsonable(result) equals the persisted snapshot."""
    q = dict(rec["semantic"]["qgv"])
    q["qgv_snapshot_id"] = rec["operational"]["qgv_snapshot_id"]
    q["analyzed_at"] = datetime.fromisoformat(q["analyzed_at"])
    q["as_of"] = datetime.fromisoformat(q["as_of"])
    q["profile_kind"] = ProfileKind(q["profile_kind"])
    q["V_policy_status"] = CalibrationLifecycle(q["V_policy_status"])
    q["coverage_state"] = CoverageState(q["coverage_state"])
    q["quality_states"] = tuple(QualityState(x) for x in q["quality_states"])
    q["key_drivers"] = tuple(q["key_drivers"])
    q["data_stamp_refs"] = tuple(q["data_stamp_refs"])
    q["v_candidates"] = tuple(VCandidate(candidate_id=v["candidate_id"], lifecycle=CalibrationLifecycle(v["lifecycle"]),
                                         weights=dict(v["weights"]), v_score=v["v_score"], blocked_reason=v["blocked_reason"])
                              for v in q["v_candidates"])
    fields = {f.name for f in dataclasses.fields(QGVSnapshot)}
    if set(q) != fields:
        raise QGVProducerError("SCHEMA", f"snapshot fields differ from QGVSnapshot: {sorted(set(q) ^ fields)}")
    snap = QGVSnapshot(**q)
    if snapshot_semantic(snap) != rec["semantic"]["qgv"]:
        raise QGVProducerError("SCHEMA", "reconstructed snapshot is not byte-identical to the persisted one")
    return snap
