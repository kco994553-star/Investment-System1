"""Macro real-producer boundary. v0.1.1 engine is called, not modified.

Flow: PIT vintage records → existing ALFRED collector → existing MacroEngine
→ research MacroSnapshot → Producer Infrastructure NOT_AVAILABLE snapshot.

Does not add indicators, regime rules, weights, thresholds, exposure
coefficients, or a Web reshape. Series IDs are the existing provisional
``fred_csv.SERIES`` map. Because that map is provisional and no exposure
model is approved, the Web section is POLICY_BLOCKED rather than LIVE.
Current revised (non-ALFRED) history is never applied to a decision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Iterable, Mapping

from ..providers.fred_alfred import collect_indicators_alfred
from ..providers.fred_csv import SERIES
from ..versions import MACRO_CANDIDATE, MACRO_CONFIRMED
from .engine import MacroEngine

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ACCEPTED_VINTAGE = "ALFRED_AS_OF"
_REJECTED_REVISED = "CURRENT_REVISED_NOT_ALFRED"
_REQUIRED_PILLARS = ("growth", "inflation")
PRODUCER_ID = "macro.real.v1"
PUBLICATION = "POLICY_BLOCKED"
PUBLICATION_REASONS = (
    "SERIES_MAPPING_PROVISIONAL",
    "EXPOSURE_NOT_APPROVED",
    "WEB_INDICATORS_NOT_RESHAPED",
    "NO_APPROVED_LIVE_EXPIRY",
)


class MacroRealProducerError(ValueError):
    code = "MACRO_REAL_PRODUCER"


class MacroProvenanceError(MacroRealProducerError):
    code = "MISSING_PROVENANCE"


class FutureReleaseError(MacroRealProducerError):
    code = "FUTURE_RELEASE"


class RevisedHistoryError(MacroRealProducerError):
    code = "REVISED_HISTORY"


class SyntheticLiveError(MacroRealProducerError):
    code = "SYNTHETIC_LIVE"


class PolicyBlocked(MacroRealProducerError):
    code = "POLICY_BLOCKED"


class MacroInputError(MacroRealProducerError):
    code = "MACRO_INPUT"


def _canonical_sha256(value: Any) -> str:
    # Local import: producer infrastructure is a read-only dependency.
    from ..producers.serialization import canonical_sha256

    return canonical_sha256(value)


def _aware(value: datetime | None, field: str, *, required: bool) -> datetime | None:
    if value is None:
        if required:
            raise MacroInputError(f"{field} is required")
        return None
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise MacroInputError(f"{field} must be a timezone-aware datetime")
    return value


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


@dataclass(frozen=True)
class VintageSeries:
    """One ALFRED vintage of one existing series. Not a new indicator."""

    series_id: str
    available_at: datetime
    payload: Mapping[str, Any]
    artifact_id: str
    sha256: str
    source: str
    synthetic: bool = False
    vintage_kind: str = _ACCEPTED_VINTAGE
    vintage_at: datetime | None = None
    release_at: datetime | None = None
    ingested_at: datetime | None = None


@dataclass(frozen=True)
class MacroProducerResult:
    snapshot: Any
    producer_snapshot: dict[str, Any]
    provenance: tuple[dict[str, Any], ...]
    publication: str
    publication_reasons: tuple[str, ...]


def company_industry_exposure(*_args: Any, **_kwargs: Any) -> None:
    """Approved exposure coefficients do not exist. v0.1.4 is not promoted."""

    raise PolicyBlocked(
        "POLICY_BLOCKED: no approved company or industry exposure coefficients; "
        "v0.1.4 candidate is not promoted and no exposure model is created"
    )


def _check_vintage(vintage: VintageSeries) -> None:
    if not isinstance(vintage.series_id, str) or vintage.series_id not in set(SERIES.values()):
        raise MacroInputError(
            f"series {vintage.series_id!r} is outside the existing provisional SERIES map"
        )
    _aware(vintage.available_at, "available_at", required=True)
    for field in ("vintage_at", "release_at", "ingested_at"):
        _aware(getattr(vintage, field), field, required=False)
    if not isinstance(vintage.payload, Mapping):
        raise MacroProvenanceError("payload must be an object")
    if not isinstance(vintage.artifact_id, str) or not vintage.artifact_id.strip():
        raise MacroProvenanceError("artifact_id is required")
    if not isinstance(vintage.source, str) or not vintage.source.strip():
        raise MacroProvenanceError("source is required")
    if not isinstance(vintage.sha256, str) or not _HEX64.match(vintage.sha256):
        raise MacroProvenanceError("sha256 must be 64 lowercase hex")
    actual = _canonical_sha256(dict(vintage.payload))
    if actual != vintage.sha256:
        raise MacroProvenanceError(f"sha256 does not match canonical payload for {vintage.artifact_id}")
    if vintage.synthetic:
        raise SyntheticLiveError("synthetic macro input cannot be used as a real or LIVE producer input")
    if vintage.vintage_kind != _ACCEPTED_VINTAGE:
        raise RevisedHistoryError(
            f"{vintage.vintage_kind} cannot be applied to a decision; "
            f"{_REJECTED_REVISED} history is not a point-in-time vintage"
        )


def _select(vintages: Iterable[VintageSeries], decision_time: datetime) -> tuple[dict[str, VintageSeries], dict[str, int]]:
    seen: set[str] = set()
    eligible: dict[str, list[VintageSeries]] = {}
    future: dict[str, int] = {}
    for vintage in vintages:
        _check_vintage(vintage)
        if vintage.artifact_id in seen:
            raise MacroProvenanceError(f"duplicate artifact_id {vintage.artifact_id}")
        seen.add(vintage.artifact_id)
        if vintage.available_at > decision_time:
            future[vintage.series_id] = future.get(vintage.series_id, 0) + 1
            continue
        eligible.setdefault(vintage.series_id, []).append(vintage)
    chosen: dict[str, VintageSeries] = {}
    for series_id, group in eligible.items():
        by_time: dict[datetime, list[VintageSeries]] = {}
        for vintage in group:
            by_time.setdefault(vintage.available_at, []).append(vintage)
        latest = max(by_time)
        if len(by_time[latest]) != 1:
            raise MacroInputError(f"ambiguous vintage at {latest.isoformat()} for {series_id}")
        chosen[series_id] = by_time[latest][0]
    return chosen, future


def _provenance(chosen: Mapping[str, VintageSeries]) -> tuple[dict[str, Any], ...]:
    rows = []
    for series_id in sorted(chosen):
        vintage = chosen[series_id]
        rows.append(
            {
                "series_id": series_id,
                "artifact_id": vintage.artifact_id,
                "sha256": vintage.sha256,
                "source": vintage.source,
                "available_at": vintage.available_at.isoformat(),
                "vintage_at": _iso(vintage.vintage_at),
                "release_at": _iso(vintage.release_at),
                "ingested_at": _iso(vintage.ingested_at),
                "vintage_kind": vintage.vintage_kind,
            }
        )
    return tuple(rows)


def _producer_snapshot(snapshot_id: str, decision_time: datetime, generated_at: datetime) -> dict[str, Any]:
    from ..producers.contract import not_available, validate_snapshot

    reason = (
        f"거시 연구 Snapshot {snapshot_id}은 웹에 게시하지 않습니다. "
        "FRED 시계열 매핑은 PROVISIONAL이고, 승인된 기업/산업 exposure 계수가 없으며, "
        "environment.indicators를 Web indicators로 바꾸지 않습니다."
    )
    snap = not_available(
        "macro",
        PRODUCER_ID,
        MACRO_CONFIRMED,
        generated_at.isoformat(),
        reason,
        PUBLICATION,
        decision_time.isoformat(),
        {"id": "MACRO_CONFIRMED_ENGINE", "version": MACRO_CONFIRMED, "status": "PROVISIONAL"},
    )
    return validate_snapshot(snap)


def produce(
    decision_time: datetime,
    vintages: Iterable[VintageSeries],
    *,
    generated_at: datetime,
) -> MacroProducerResult:
    """Point-in-time research snapshot plus a fail-closed Web producer snapshot.

    Later revisions are ignored for this decision_time. The confirmed engine
    is not called when growth or inflation is missing, so its 0.0 default
    cannot turn an empty input into NEUTRAL.
    """

    decision_time = _aware(decision_time, "decision_time", required=True)
    generated_at = _aware(generated_at, "generated_at", required=True)
    assert decision_time is not None and generated_at is not None
    if decision_time > generated_at:
        raise MacroInputError("decision_time cannot be later than generated_at")
    vintages = tuple(vintages)
    if not vintages:
        raise MacroInputError("at least one vintage is required")
    chosen, future = _select(vintages, decision_time)
    payloads = {series_id: dict(vintage.payload) for series_id, vintage in chosen.items()}
    pack = collect_indicators_alfred(decision_time, payloads)
    values = dict(pack.get("values") or {})
    missing = [SERIES[pillar] for pillar in _REQUIRED_PILLARS if pillar not in values]
    if missing:
        if any(future.get(series_id) for series_id in missing):
            raise FutureReleaseError(
                "required series has no vintage with available_at <= decision_time: " + ", ".join(missing)
            )
        raise MacroInputError(
            "growth and inflation are absent after PIT filtering; engine defaults are not applied: "
            + ", ".join(missing)
        )
    engine_snapshot = MacroEngine().evaluate(decision_time, values, synthetic=False)
    provenance = _provenance(chosen)
    identity = {
        "as_of": decision_time.isoformat(),
        "indicators": values,
        "state": engine_snapshot.state.value,
        "regime": engine_snapshot.regime,
        "macro_version": engine_snapshot.macro_version,
        "artifacts": list(provenance),
    }
    snapshot_id = "mac_" + _canonical_sha256(identity)[:12]
    environment = dict(engine_snapshot.environment)
    environment.update(
        {key: pack.get(key) for key in ("availability", "vintage", "source", "missing", "as_of_used")}
    )
    environment["fallback_reason"] = None
    environment["real_data_verified"] = False
    environment["pit"] = {"decision_time": decision_time.isoformat(), "series": list(provenance)}
    if environment.get("candidate_not_applied") != MACRO_CANDIDATE:
        raise MacroRealProducerError("confirmed engine did not retain the unpromoted candidate marker")
    snapshot = replace(
        engine_snapshot,
        macro_snapshot_id=snapshot_id,
        environment=environment,
        mutated_qgv=False,
        synthetic=False,
    )
    return MacroProducerResult(
        snapshot=snapshot,
        producer_snapshot=_producer_snapshot(snapshot_id, decision_time, generated_at),
        provenance=provenance,
        publication=PUBLICATION,
        publication_reasons=PUBLICATION_REASONS,
    )
