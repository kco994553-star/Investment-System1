"""Raw → map → analyze pipeline. NEW IMPLEMENTATION."""

from __future__ import annotations

from datetime import datetime

from ..contracts.enums import ProfileKind
from ..contracts.models import QGVSnapshot
from ..contracts.raw import RawFundamentals
from ..providers.memory import MemoryFundamentalsProvider
from .analysis import AnalysisEngine
from .g_horizon import GHorizonConfig, assess_horizon
from .raw_map import map_raw


class AnalysisPipeline:
    def __init__(self, engine: AnalysisEngine | None = None, fundamentals: MemoryFundamentalsProvider | None = None):
        self.engine = engine or AnalysisEngine()
        self.fundamentals = fundamentals or MemoryFundamentalsProvider()

    def analyze_raw(self, raw: RawFundamentals, *, as_of: datetime | None = None, profile_kind: ProfileKind | None = None, available_quarters: int = 0, g_horizon: GHorizonConfig | None = None) -> QGVSnapshot:
        as_of = as_of or raw.stamp.available_at
        if profile_kind is None:
            profile_kind = ProfileKind.FINANCIAL if raw.profile_kind == "FINANCIAL" else ProfileKind.GENERAL_CORPORATE
        obs = map_raw(raw)
        synthetic = raw.source_kind == "SYNTHETIC" or raw.stamp.synthetic
        cov = assess_horizon(g_horizon or GHorizonConfig(), available_quarters)
        return self.engine.analyze(
            raw.company_id,
            as_of,
            obs,
            profile_kind=profile_kind,
            data_stamp_refs=(raw.stamp.data_stamp_id,),
            synthetic=synthetic,
            key_drivers=("raw_map", raw.source_kind, f"g_horizon={cov.requested_horizon}"),
            g_horizon={
                "requested": cov.requested_horizon,
                "available_quarters": cov.available_quarters,
                "effective_quarters": cov.effective_quarters,
                "coverage_state": cov.coverage_state,
                "fallback_used": cov.fallback_used,
                "mutates_g_score": False,
            },
        )

    def analyze_as_of(self, company_id: str, as_of: datetime, profile_kind: ProfileKind = ProfileKind.GENERAL_CORPORATE) -> QGVSnapshot | None:
        raw = self.fundamentals.get(company_id, as_of)
        if raw is None:
            return None
        return self.analyze_raw(raw, as_of=as_of, profile_kind=profile_kind)
