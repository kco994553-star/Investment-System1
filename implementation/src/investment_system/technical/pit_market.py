"""PIT screen for existing Yahoo chart bytes.

Reuses the repository price stamp (available_at = observed_at) from
providers.yahoo_chart.to_price_point. Does not choose a return series,
does not adjust for corporate actions, and does not fill missing bars.
Volume is retained only as an input fact. No indicator is computed here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from .codec import canonical_bytes, sha256_hex
from .errors import FutureInputError, MissingLookbackError, TechnicalProducerError

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _aware(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TechnicalProducerError(f"{label} must be a timezone-aware datetime")
    return value


@dataclass(frozen=True)
class PitBar:
    observed_at: datetime
    volume_observed_at: datetime
    available_at: datetime
    close: float | None
    adjclose: float | None
    volume: float | None
    currency: str
    symbol: str

    def complete(self) -> bool:
        return self.close is not None and self.volume is not None

    def violates(self, decision_time: datetime) -> bool:
        return (
            self.observed_at > decision_time
            or self.volume_observed_at > decision_time
            or self.available_at > decision_time
        )


@dataclass(frozen=True)
class InputProvenance:
    artifact_id: str
    sha256: str
    nbytes: int
    source_provider: str
    source_reference: str
    evidence_class: str  # LIVE_FETCH | STRUCTURAL_FIXTURE
    synthetic: bool

    def validate(self, body: bytes) -> None:
        from .errors import MissingProvenanceError, SyntheticLiveError

        if not isinstance(self.artifact_id, str) or not self.artifact_id.strip():
            raise MissingProvenanceError("artifact_id required")
        if not isinstance(self.source_provider, str) or not self.source_provider.strip():
            raise MissingProvenanceError("source_provider required")
        if not isinstance(self.source_reference, str) or not self.source_reference.strip():
            raise MissingProvenanceError("source_reference required")
        if not isinstance(self.sha256, str) or not _HEX64.match(self.sha256):
            raise MissingProvenanceError("sha256 must be 64 lowercase hex")
        if self.nbytes != len(body) or self.sha256 != sha256_hex(body):
            raise MissingProvenanceError("bytes do not match provenance")
        if self.evidence_class not in ("LIVE_FETCH", "STRUCTURAL_FIXTURE"):
            raise MissingProvenanceError("evidence_class must be LIVE_FETCH or STRUCTURAL_FIXTURE")
        if self.evidence_class == "LIVE_FETCH" and self.synthetic:
            raise SyntheticLiveError("synthetic bytes cannot be labelled LIVE_FETCH")
        if self.evidence_class == "STRUCTURAL_FIXTURE" and not self.synthetic:
            raise SyntheticLiveError("a fixture cannot be labelled non-synthetic")


def bars_from_yahoo_chart(payload: dict) -> tuple[str, str, list[PitBar]]:
    """Parse chart JSON the way the existing adapter reads a bar, plus volume.

    available_at is the bar timestamp. That is the stamp already written by
    yahoo_chart.to_price_point, not a new publication-lag rule.
    """
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        return "", "", []
    meta = result[0].get("meta") or {}
    symbol = str(meta.get("symbol") or "")
    currency = str(meta.get("currency") or "")
    timestamps = result[0].get("timestamp") or []
    quote = ((result[0].get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []
    adj = ((result[0].get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose") or []
    bars: list[PitBar] = []
    for i, raw_ts in enumerate(timestamps):
        if raw_ts is None:
            continue
        observed = datetime.fromtimestamp(int(raw_ts), tz=timezone.utc)
        close = float(closes[i]) if i < len(closes) and closes[i] is not None else None
        volume = float(volumes[i]) if i < len(volumes) and volumes[i] is not None else None
        adj_px = float(adj[i]) if i < len(adj) and adj[i] is not None else None
        bars.append(
            PitBar(
                observed_at=observed,
                volume_observed_at=observed,
                available_at=observed,
                close=close,
                adjclose=adj_px,
                volume=volume,
                currency=currency,
                symbol=symbol,
            )
        )
    return symbol, currency, bars


def _require_ordered_unique(bars: list[PitBar]) -> None:
    times = [b.observed_at for b in bars]
    if len(times) != len(set(times)) or times != sorted(times):
        raise TechnicalProducerError("price bars must be unique and chronological; refusing to reorder")


def select_window(
    bars: list[PitBar],
    decision_time: datetime,
    lookback_bars: int,
    *,
    on_future: str = "exclude",
) -> dict:
    """Last N complete bars at or before decision_time.

    on_future='exclude' drops later bars (raw chart replay).
    on_future='reject' fails if any supplied bar is after decision_time (curated input).
    Incomplete bars are omitted and counted. Nothing is filled.
    """
    decision_time = _aware(decision_time, "decision_time")
    if not isinstance(lookback_bars, int) or isinstance(lookback_bars, bool) or lookback_bars < 1:
        raise MissingLookbackError("lookback bar_count must be a positive integer supplied by the caller")
    _require_ordered_unique(bars)
    future = [b for b in bars if b.violates(decision_time)]
    if future and on_future == "reject":
        raise FutureInputError("supplied input contains a bar after decision_time")
    if on_future not in ("exclude", "reject"):
        raise TechnicalProducerError("on_future must be exclude or reject")
    eligible = [b for b in bars if not b.violates(decision_time)]
    complete = [b for b in eligible if b.complete()]
    incomplete = len(eligible) - len(complete)
    if len(complete) < lookback_bars:
        raise MissingLookbackError(
            f"need {lookback_bars} complete PIT bars, have {len(complete)} "
            f"(incomplete_eligible={incomplete}, future_excluded={len(future)})"
        )
    window = complete[-lookback_bars:]
    if any(b.violates(decision_time) for b in window):
        raise FutureInputError("window contains a future bar")
    return {
        "window": window,
        "future_excluded": len(future),
        "incomplete_eligible": incomplete,
        "available_at": max(b.available_at for b in window),
    }


def series_sha256(bars: list[PitBar]) -> str:
    payload = [
        {
            "observed_at": b.observed_at.isoformat(),
            "volume_observed_at": b.volume_observed_at.isoformat(),
            "available_at": b.available_at.isoformat(),
            "close": b.close,
            "adjclose": b.adjclose,
            "volume": b.volume,
        }
        for b in bars
    ]
    return sha256_hex(canonical_bytes(payload))
