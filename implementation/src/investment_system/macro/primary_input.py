"""Observed-capture cutoff and evidence grid; no MacroEngine evaluation."""
from datetime import datetime
from decimal import Decimal

from .primary_contract import (
    AXES, DIMENSIONS, SOURCE_IDS, LEVEL_SOURCES, MacroObservation, ParseResult,
    MacroCell, MacroEvidenceGrid, aware, observation_id,
)


def select_observed_vintages(observations: tuple[MacroObservation, ...], as_of: datetime, *, strict_historical: bool = False) -> ParseResult:
    def fail(reason):
        return ParseResult("NOT_AVAILABLE", (), (reason,), (), True)
    if strict_historical:
        return fail("HISTORICAL_VINTAGE_NOT_PROVEN")
    if not aware(as_of):
        return fail("INVALID_TIMESTAMP")
    if not isinstance(observations,tuple) or any(not isinstance(o,MacroObservation) for o in observations):
        return fail("INVALID_RECEIPT")
    if len({o.synthetic for o in observations}) > 1:
        return fail("MIXED_SYNTHETIC_INPUT")
    ids, captures, selected, reasons, conflicts = {}, {}, {}, [], set()
    for o in observations:
        if not all(aware(t) for t in (o.available_at,o.vintage_at,o.ingested_at)):
            return fail("INVALID_TIMESTAMP")
        if o.available_at != o.vintage_at or o.available_at != o.ingested_at:
            return fail("INVALID_TIME_ORDER")
        if o.source_id not in SOURCE_IDS or not isinstance(o.value,Decimal) or not o.value.is_finite() or type(o.synthetic) is not bool or o.availability_basis != "OBSERVED_CAPTURE_UPPER_BOUND" or o.vintage_kind != "OBSERVED_CAPTURE":
            return fail("INVALID_RECEIPT")
        if o.observation_id in ids and ids[o.observation_id] != o:
            return fail("OBSERVATION_ID_COLLISION")
        if o.observation_id != observation_id(o.source_id,o.observation_period,o.value,o.unit,o.seasonal_adjustment,o.source_response_sha256,o.available_at):
            return fail("INVALID_RECEIPT")
        ids[o.observation_id] = o
        if o.available_at > as_of:
            reasons.append("AVAILABLE_AFTER_AS_OF"); continue
        key = (o.source_id,o.observation_period)
        capture_key = key+(o.available_at,)
        if capture_key in captures and captures[capture_key] != o:
            conflicts.add(o.source_id); reasons.append("CONFLICTING_VINTAGE")
        captures[capture_key] = o
        if key not in selected or selected[key].available_at < o.available_at:
            selected[key] = o
    good = tuple(o for _,o in sorted(selected.items()) if o.source_id not in conflicts)
    sources = sorted({o.source_id for o in observations})
    missing = tuple(s for s in sources if s not in {o.source_id for o in good})
    return ParseResult("INPUT_RESEARCH" if good else "NOT_AVAILABLE",good,tuple(dict.fromkeys(reasons)),missing,
                       observations[0].synthetic if observations else True)


def build_evidence_grid(results: tuple[ParseResult, ...], as_of: datetime) -> MacroEvidenceGrid:
    reasons = []
    observations = ()
    if not isinstance(results,tuple) or any(not isinstance(r,ParseResult) for r in results):
        reasons.append("INVALID_RECEIPT")
    elif len({r.synthetic for r in results} | {o.synthetic for r in results for o in r.observations}) > 1:
        reasons.append("MIXED_SYNTHETIC_INPUT")
    else:
        selection = select_observed_vintages(tuple(o for r in results for o in r.observations),as_of)
        observations = selection.observations
        reasons.extend(selection.reason_codes)
        reasons.extend(code for r in results for code in r.reason_codes)
    present = {o.source_id for o in observations}
    missing = tuple(s for s in SOURCE_IDS if s not in present)
    cells = []
    for axis in AXES:
        for dimension in DIMENSIONS:
            evidence, reason = (), ()
            if axis not in LEVEL_SOURCES:
                reason = ("DEFERRED_GSQ011",)
            elif dimension == "Level":
                if all(s in present for s in LEVEL_SOURCES[axis]):
                    evidence = tuple(o.observation_id for o in observations if o.source_id in LEVEL_SOURCES[axis])
                else:
                    reason = tuple(dict.fromkeys(["MISSING_SOURCE"]+reasons))
            elif dimension == "Surprise":
                reason = ("EXPECTATIONS_NOT_CONFIGURED",)
            elif dimension == "Confidence":
                reason = ("NO_APPROVED_CONFIDENCE_RULE",)
            else:
                reason = ("NO_APPROVED_STATE_RULE",)
            cells.append(MacroCell(axis,dimension,"RAW_EVIDENCE" if evidence else "NOT_AVAILABLE",evidence,reason))
    return MacroEvidenceGrid("MACRO_PRIMARY_INPUT/1",as_of,"INPUT_RESEARCH" if observations else "NOT_AVAILABLE",tuple(cells),observations,
                             "OBSERVED_BOUND_ONLY" if observations else "NOT_VERIFIED","NOT_APPLIED",missing,tuple(dict.fromkeys(reasons)))
