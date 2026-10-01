"""Read-only tap on the existing QGV engine calls.

`run_as_of` keeps each `QGVSnapshot` and its inputs in local variables and returns only Q/G/V and the
snapshot id. This context manager wraps `AnalysisPipeline.analyze_raw` and `AnalysisEngine.analyze` for the
duration of one run and records the arguments and return value of each call. The wrapped methods are
called with the same arguments and their return value is passed through unchanged, so no score can differ.
Records are joined back to the run by `qgv_snapshot_id`.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from ..qgv.analysis import AnalysisEngine
from ..qgv.pipeline import AnalysisPipeline


@dataclass
class CapturedCall:
    snapshot: Any
    raw: Any = None
    observations: dict | None = None


@dataclass
class Capture:
    calls: dict[str, CapturedCall] = field(default_factory=dict)

    def get(self, qgv_snapshot_id: str) -> CapturedCall | None:
        return self.calls.get(qgv_snapshot_id)


@contextmanager
def capture_qgv_engine() -> Iterator[Capture]:
    cap = Capture()
    orig_raw = AnalysisPipeline.analyze_raw
    orig_analyze = AnalysisEngine.analyze
    if getattr(orig_raw, "_qgv_producer_tap", False) or getattr(orig_analyze, "_qgv_producer_tap", False):
        raise RuntimeError("nested QGV engine capture is not supported")

    def analyze(self, company_id, as_of, observations, **kwargs):
        snap = orig_analyze(self, company_id, as_of, observations, **kwargs)
        cap.calls.setdefault(snap.qgv_snapshot_id, CapturedCall(snap)).observations = dict(observations)
        return snap

    def analyze_raw(self, raw, **kwargs):
        snap = orig_raw(self, raw, **kwargs)
        cap.calls.setdefault(snap.qgv_snapshot_id, CapturedCall(snap)).raw = raw
        return snap

    analyze._qgv_producer_tap = True
    analyze_raw._qgv_producer_tap = True
    AnalysisEngine.analyze = analyze
    AnalysisPipeline.analyze_raw = analyze_raw
    try:
        yield cap
    finally:
        AnalysisEngine.analyze = orig_analyze
        AnalysisPipeline.analyze_raw = orig_raw
