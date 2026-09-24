"""G time-horizon policy and quarterly monitor.

NEW IMPLEMENTATION / PROVISIONAL policy layer.
This module does not change the Frozen G factor names or weights.
Default G analysis horizon is 3Y by current project decision; horizon performance
must still be validated by PIT/OOS/Calibration before promotion to a Frozen standard.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

DEFAULT_G_HORIZON = "3Y"
G_HORIZON_MEANINGS = {
    "1Q": ("Latest Quarter", "최근 분기의 성장 변화와 급변 신호"),
    "2Q": ("Short-term Trend", "최근 두 분기 변화의 연속성"),
    "4Q": ("Current Growth Cycle", "최근 4개 분기의 현재 성장 사이클; 계절성 완화"),
    "2Y": ("Short-Medium Growth", "최근 성장 변화가 단발성이 아닌지 확인"),
    "3Y": ("Structural Growth", "중기 구조적 성장; 기본 G 분석기간"),
    "5Y": ("Long-term Durability", "장기 성장 지속성과 복리 성장 특성"),
    "CUSTOM": ("Custom Horizon", "사용자가 지정한 연구·분석 기간"),
}


@dataclass(frozen=True)
class GHorizonConfig:
    requested_horizon: str = DEFAULT_G_HORIZON
    custom_quarters: int | None = None

    def __post_init__(self) -> None:
        h = self.requested_horizon.upper()
        if h not in G_HORIZON_MEANINGS:
            raise ValueError(f"unsupported G horizon: {self.requested_horizon}")
        if h == "CUSTOM" and (self.custom_quarters is None or self.custom_quarters < 1):
            raise ValueError("CUSTOM horizon requires custom_quarters >= 1")
        if h != "CUSTOM" and self.custom_quarters is not None:
            raise ValueError("custom_quarters is only valid with CUSTOM horizon")
        object.__setattr__(self, "requested_horizon", h)

    @property
    def requested_quarters(self) -> int:
        return {"1Q": 1, "2Q": 2, "4Q": 4, "2Y": 8, "3Y": 12, "5Y": 20}.get(
            self.requested_horizon, self.custom_quarters or 0
        )

    @property
    def meaning(self) -> dict[str, str]:
        en, ko = G_HORIZON_MEANINGS[self.requested_horizon]
        return {"label_en": en, "meaning_ko": ko}


@dataclass(frozen=True)
class QuarterlyFundamentalPoint:
    period_end: date
    revenue: float | None = None
    eps: float | None = None
    fcf_per_share: float | None = None


@dataclass(frozen=True)
class GHorizonCoverage:
    requested_horizon: str
    requested_quarters: int
    available_quarters: int
    effective_quarters: int
    coverage_ratio: float
    coverage_state: str
    horizon_meaning: dict[str, str]
    fallback_used: bool
    fallback_reason: str | None


def assess_horizon(config: GHorizonConfig, available_quarters: int) -> GHorizonCoverage:
    req = config.requested_quarters
    avail = max(0, available_quarters)
    eff = min(req, avail)
    ratio = 0.0 if req == 0 else min(1.0, avail / req)
    state = "READY" if ratio >= 1.0 else ("PARTIAL" if avail > 0 else "MISSING")
    return GHorizonCoverage(
        requested_horizon=config.requested_horizon,
        requested_quarters=req,
        available_quarters=avail,
        effective_quarters=eff,
        coverage_ratio=round(ratio, 4),
        coverage_state=state,
        horizon_meaning=config.meaning,
        fallback_used=state != "READY",
        fallback_reason=None if state == "READY" else "INSUFFICIENT_QUARTERLY_HISTORY",
    )


def _growth(cur: float | None, prev: float | None) -> float | None:
    if cur is None or prev is None or prev == 0:
        return None
    return cur / prev - 1.0


def quarterly_monitor(points: Iterable[QuarterlyFundamentalPoint]) -> dict:
    """Return raw quarterly evidence only; it does not alter the Frozen G score.

    Points are sorted by period_end. YoY requires five observations including the
    latest; QoQ requires two. Acceleration compares the latest two available YoY
    growth rates and therefore needs six quarterly observations.
    """
    rows = sorted(points, key=lambda p: p.period_end)
    if not rows:
        return {"status": "MISSING", "quarter_count": 0}
    latest = rows[-1]

    def metric(name: str) -> dict:
        vals = [getattr(p, name) for p in rows]
        qoq = _growth(vals[-1], vals[-2]) if len(vals) >= 2 else None
        yoy = _growth(vals[-1], vals[-5]) if len(vals) >= 5 else None
        prev_yoy = _growth(vals[-2], vals[-6]) if len(vals) >= 6 else None
        accel = None if yoy is None or prev_yoy is None else yoy - prev_yoy
        return {"qoq": qoq, "yoy": yoy, "yoy_acceleration": accel}

    return {
        "status": "READY",
        "latest_period_end": latest.period_end.isoformat(),
        "quarter_count": len(rows),
        "revenue": metric("revenue"),
        "eps": metric("eps"),
        "fcf_per_share": metric("fcf_per_share"),
        "note": "RAW_EVIDENCE_ONLY; does not mutate Frozen G score",
    }
