"""Regression / compatibility interface for a future original freeze suite.

Does not claim original suites are present.
NEW TOOLING.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecordedSuite:
    name: str
    module: str
    recorded_pass: str
    present_in_hub: bool
    note: str


RECORDED_SUITES = (
    RecordedSuite("qgv-analysis-python", "QGV Analysis", "299", False, "original freeze suite Missing"),
    RecordedSuite("qgv-analysis-js", "QGV Analysis", "27", False, "original freeze suite Missing"),
    RecordedSuite("qgv-analysis-browser-e2e", "QGV Analysis", "NOT RUN", False, "never recorded as run"),
    RecordedSuite("qgv-sim-v0.6.8", "QGV Simulation", "103/103", False, "local package Missing"),
    RecordedSuite("qgv-portfolio-rc26", "QGV Portfolio", "366/366", False, "RC26 package Missing"),
    RecordedSuite("leaderboard-python", "Leaderboard", "313+8", False, "package Missing"),
    RecordedSuite("technical-159", "Technical", "159/159", False, "v0.6 package Missing"),
    RecordedSuite("macro-v0.1.1", "Macro", "28/28", False, "confirmed package Missing"),
)


class CompatibilityHarness:
    def inventory(self) -> list[dict]:
        return [
            {
                "name": s.name,
                "module": s.module,
                "recorded_pass": s.recorded_pass,
                "present_in_hub": s.present_in_hub,
                "comparable": False,
                "note": s.note,
            }
            for s in RECORDED_SUITES
        ]

    def compare_if_present(self, suite_name: str, new_results: dict) -> dict:
        suite = next((s for s in RECORDED_SUITES if s.name == suite_name), None)
        if suite is None:
            return {"status": "UNKNOWN_SUITE", "suite": suite_name}
        if not suite.present_in_hub:
            return {
                "status": "ORIGINAL_MISSING",
                "suite": suite_name,
                "recorded_pass": suite.recorded_pass,
                "new_impl_results": new_results,
                "verdict": "cannot compare; original artifact Missing",
            }
        return {"status": "COMPARABLE", "suite": suite_name}
