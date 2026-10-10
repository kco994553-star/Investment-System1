"""Observed-capture selection and an unscored 8-axis evidence grid."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re

from .primary_contract import (
    AXES, DIMENSIONS, LEVEL_REQUIRED, REASON_CODES, SOURCE_IDS, SOURCE_REGISTRY,
    MacroCell, MacroEvidenceGrid, MacroObservation, ParseResult, aware, make_result,
    nonempty, observation_id, ordered_reasons, release_error, valid_hash,
)


def _period_valid(period: object, frequency: str) -> bool:
    if type(period) is not str:
        return False
    try:
        if frequency == "M" and re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", period):
            date.fromisoformat(period + "-01")
            return True
        if frequency == "Q" and re.fullmatch(r"[0-9]{4}Q[1-4]", period):
            return int(period[:4]) > 0
        if frequency == "D" and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", period):
            date.fromisoformat(period)
            return True
    except ValueError:
        pass
    return False


def _observation_error(obs: object) -> str | None:
    if not isinstance(obs, MacroObservation):
        return "INVALID_RECEIPT"
    if (type(obs.source_id) is not str or obs.source_id not in SOURCE_REGISTRY
            or not valid_hash(obs.observation_id) or not valid_hash(obs.source_response_sha256)
            or type(obs.synthetic) is not bool):
        return "INVALID_RECEIPT"
    if not all(aware(t) for t in (obs.available_at, obs.vintage_at, obs.ingested_at)):
        return "INVALID_TIMESTAMP"
    if not obs.available_at == obs.vintage_at == obs.ingested_at:
        return "INVALID_TIME_ORDER"
    definition = SOURCE_REGISTRY[obs.source_id]
    if (obs.axis != definition.axis or obs.frequency != definition.frequency
            or obs.seasonal_adjustment != definition.seasonal_adjustment
            or not _period_valid(obs.observation_period, definition.frequency)
            or not nonempty(obs.unit) or (definition.unit is not None and obs.unit != definition.unit)
            or obs.availability_basis != "OBSERVED_CAPTURE_UPPER_BOUND" or obs.vintage_kind != "OBSERVED_CAPTURE"
            or type(obs.source_notes) is not tuple or any(type(n) is not str for n in obs.source_notes)
            or type(obs.quality_flags) is not tuple or not obs.quality_flags
            or any(not nonempty(n) for n in obs.quality_flags)):
        return "SCHEMA_MISMATCH"
    if definition.provider == "BEA":
        if type(obs.unit_multiplier) is not int or not nonempty(obs.metric_name) or not nonempty(obs.source_series_code):
            return "SCHEMA_MISMATCH"
    elif obs.unit_multiplier is not None or obs.metric_name is not None or obs.source_series_code is not None:
        return "SCHEMA_MISMATCH"
    if type(obs.value) is not Decimal or not obs.value.is_finite():
        return "INVALID_VALUE"
    error = release_error(obs.release, obs.ingested_at)
    if error:
        return error
    if obs.observation_id != observation_id(obs.source_id, obs.observation_period, obs.value, obs.unit,
                                           obs.seasonal_adjustment, obs.source_response_sha256, obs.ingested_at):
        return "INVALID_RECEIPT"
    return None


def _collision(observations) -> bool:
    seen = {}
    for obs in observations:
        if not isinstance(obs, MacroObservation) or not valid_hash(obs.observation_id):
            continue
        previous = seen.get(obs.observation_id)
        if previous is not None:
            try:
                if previous != obs:
                    return True
            except (InvalidOperation, TypeError, ValueError):
                # Malformed objects must not escape validation through dataclass
                # equality (e.g. a signaling NaN). They cannot share a usable ID.
                return True
        seen[obs.observation_id] = obs
    return False


def _capture_content(obs: MacroObservation):
    # Different response wrappers/hashes can contain the same capture value.
    return (obs.value, obs.unit, obs.unit_multiplier, obs.metric_name, obs.source_series_code,
            obs.seasonal_adjustment, obs.source_notes, obs.release, obs.quality_flags)


def select_observed_vintages(observations: tuple[MacroObservation, ...], as_of: datetime,
                             *, strict_historical: bool = False) -> ParseResult:
    if not aware(as_of):
        return make_result(reasons=("INVALID_TIMESTAMP",))
    if type(strict_historical) is not bool or type(observations) is not tuple:
        return make_result(reasons=("INVALID_REQUEST",))
    expected = tuple(s for s in SOURCE_IDS if any(isinstance(o, MacroObservation) and o.source_id == s for o in observations))
    if strict_historical:
        return make_result(reasons=("HISTORICAL_VINTAGE_NOT_PROVEN",), expected=expected)
    if _collision(observations):
        return make_result(reasons=("OBSERVATION_ID_COLLISION",), expected=expected)
    flags = {o.synthetic for o in observations if isinstance(o, MacroObservation) and type(o.synthetic) is bool}
    if len(flags) > 1:
        return make_result(reasons=("MIXED_SYNTHETIC_INPUT",), expected=expected)
    synthetic = next(iter(flags)) if flags else True
    blocked, reasons, valid = set(), [], []
    for obs in observations:
        error = _observation_error(obs)
        if error:
            reasons.append(error)
            if not isinstance(obs, MacroObservation) or type(obs.source_id) is not str or obs.source_id not in SOURCE_REGISTRY:
                return make_result(reasons=(error,), expected=expected, synthetic=synthetic)
            blocked.add(obs.source_id)
        else:
            valid.append(obs)
    # Validate same-capture conflicts before choosing a latest capture. A later
    # observation cannot hide an ambiguous earlier capture of the same source.
    captures = {}
    for obs in valid:
        key = (obs.source_id, obs.observation_period, obs.available_at)
        previous = captures.get(key)
        if previous is not None and _capture_content(previous) != _capture_content(obs):
            blocked.add(obs.source_id)
            reasons.append("CONFLICTING_VINTAGE")
        elif previous is None or obs.observation_id < previous.observation_id:
            captures[key] = obs
    selected = {}
    for obs in captures.values():
        if obs.source_id in blocked:
            continue
        if obs.available_at > as_of:
            reasons.append("AVAILABLE_AFTER_AS_OF")
            continue
        key = (obs.source_id, obs.observation_period)
        if key not in selected or obs.available_at > selected[key].available_at:
            selected[key] = obs
    output = tuple(sorted(selected.values(), key=lambda o: (SOURCE_IDS.index(o.source_id), o.observation_period)))
    return make_result(output, reasons, expected, synthetic=synthetic)


def _result_valid(result: object) -> bool:
    return (isinstance(result, ParseResult) and type(result.state) is str and result.state in ("INPUT_RESEARCH", "NOT_AVAILABLE")
            and type(result.observations) is tuple and type(result.synthetic) is bool
            and type(result.reason_codes) is tuple and all(type(r) is str and r in REASON_CODES for r in result.reason_codes)
            and type(result.missing_source_ids) is tuple
            and all(type(s) is str and s in SOURCE_REGISTRY for s in result.missing_source_ids)
            and len(set(result.missing_source_ids)) == len(result.missing_source_ids)
            and not any(isinstance(o, MacroObservation) and type(o.source_id) is str
                        and o.source_id in result.missing_source_ids for o in result.observations)
            and (result.state == "INPUT_RESEARCH") == bool(result.observations))


def _grid(observations, as_of, reasons, source_reasons) -> MacroEvidenceGrid:
    present = {o.source_id for o in observations}
    missing = tuple(s for s in SOURCE_IDS if s not in present)
    cells = []
    for axis in AXES:
        for dim in DIMENSIONS:
            state, evidence = "NOT_AVAILABLE", ()
            if axis not in LEVEL_REQUIRED:
                cell_reasons = ("DEFERRED_GSQ011",)
            elif dim == "Level":
                required = LEVEL_REQUIRED[axis]
                absent = tuple(s for s in required if s not in present)
                if not absent:
                    state = "RAW_EVIDENCE"
                    evidence = tuple(o.observation_id for o in observations if o.source_id in required)
                    cell_reasons = ()
                else:
                    cell_reasons = ordered_reasons(("MISSING_SOURCE",) + tuple(
                        reason for source in absent for reason in source_reasons.get(source, ())))
            elif dim == "Surprise":
                cell_reasons = ("EXPECTATIONS_NOT_CONFIGURED",)
            elif dim == "Confidence":
                cell_reasons = ("NO_APPROVED_CONFIDENCE_RULE",)
            else:
                cell_reasons = ("NO_APPROVED_STATE_RULE",)
            cells.append(MacroCell(axis, dim, state, evidence, cell_reasons))
    return MacroEvidenceGrid("MACRO_PRIMARY_INPUT/1", as_of, "INPUT_RESEARCH" if observations else "NOT_AVAILABLE",
                             tuple(cells), tuple(observations), "OBSERVED_BOUND_ONLY" if observations else "NOT_VERIFIED",
                             "NOT_APPLIED", missing, ordered_reasons(tuple(reasons) + (("MISSING_SOURCE",) if missing else ())))


def build_evidence_grid(results: tuple[ParseResult, ...], as_of: datetime) -> MacroEvidenceGrid:
    def failure(reason):
        return _grid((), as_of, (reason,), {s: (reason,) for s in SOURCE_IDS})

    if not aware(as_of):
        return failure("INVALID_TIMESTAMP")
    if type(results) is not tuple or any(not _result_valid(r) for r in results):
        return failure("INVALID_RECEIPT")
    if len({r.synthetic for r in results}) > 1:
        return failure("MIXED_SYNTHETIC_INPUT")
    observations = tuple(o for result in results for o in result.observations)
    if _collision(observations):
        return failure("OBSERVATION_ID_COLLISION")
    for result in results:
        if any(isinstance(o, MacroObservation) and type(o.synthetic) is bool and o.synthetic != result.synthetic for o in result.observations):
            return failure("MIXED_SYNTHETIC_INPUT")
    selected = select_observed_vintages(observations, as_of)
    if any(r in selected.reason_codes for r in ("OBSERVATION_ID_COLLISION", "MIXED_SYNTHETIC_INPUT")):
        return failure(selected.reason_codes[0])
    reasons, source_reasons = list(selected.reason_codes), {}
    for result in results:
        reasons.extend(result.reason_codes)
        for source in result.missing_source_ids:
            source_reasons.setdefault(source, []).extend(result.reason_codes)
    for source in selected.missing_source_ids:
        source_reasons.setdefault(source, []).extend(selected.reason_codes)
    return _grid(selected.observations, as_of, reasons, source_reasons)
