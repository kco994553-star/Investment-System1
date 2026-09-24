"""Module adapters. Snapshots only. Must not mutate QGV raw scores."""

from __future__ import annotations

from datetime import datetime

from ..contracts.models import QGVSnapshot
from ..macro.engine import MacroEngine
from ..qgv.pipeline import AnalysisPipeline
from ..technical.engine import TechnicalEngine


class QGVAdapter:
    def __init__(self, pipeline: AnalysisPipeline | None = None) -> None:
        self.pipeline = pipeline or AnalysisPipeline()

    def snapshot(self, raw, as_of: datetime | None = None) -> QGVSnapshot:
        return self.pipeline.analyze_raw(raw, as_of=as_of)


class TechnicalAdapter:
    def __init__(self, engine: TechnicalEngine | None = None) -> None:
        self.engine = engine or TechnicalEngine()

    def snapshot(self, company_id: str, as_of: datetime, returns: list[float], qgv: QGVSnapshot | None = None):
        before = None if qgv is None else (qgv.Q_score, qgv.G_score, qgv.V_score)
        snap = self.engine.evaluate(company_id, as_of, returns, qgv=qgv)
        if qgv is not None and (qgv.Q_score, qgv.G_score, qgv.V_score) != before:
            raise RuntimeError("Technical adapter mutated QGV")
        return snap


class MacroAdapter:
    def __init__(self, engine: MacroEngine | None = None) -> None:
        self.engine = engine or MacroEngine()

    def snapshot(self, as_of: datetime, indicators: dict[str, float] | None = None, qgv: QGVSnapshot | None = None):
        before = None if qgv is None else (qgv.Q_score, qgv.G_score, qgv.V_score)
        snap = self.engine.evaluate(as_of, indicators)
        if qgv is not None and (qgv.Q_score, qgv.G_score, qgv.V_score) != before:
            raise RuntimeError("Macro adapter mutated QGV")
        return snap
