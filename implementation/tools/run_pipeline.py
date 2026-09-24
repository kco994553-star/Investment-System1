#!/usr/bin/env python3
"""NEW TOOLING: run synthetic pipeline and write reports. Not real-data validation."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.integration.engine import IntegrationEngine
from investment_system.macro.engine import MacroEngine
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.compatibility import CompatibilityHarness
from investment_system.qgv.leaderboard import LeaderboardEngine
from investment_system.qgv.portfolio import PortfolioEngine
from investment_system.qgv.track_record import TrackRecordStore
from investment_system.technical.engine import TechnicalEngine
from investment_system.versions import IMPLEMENTATION_KIND, IMPLEMENTATION_LINE
from investment_system.contracts.enums import QualityState
from investment_system.contracts.models import FactorObservation
from investment_system.qgv.factors import G_WEIGHTS, Q_WEIGHTS, V_FACTORS


def synth_obs(score: float) -> dict:
    out = {}
    for fid in list(Q_WEIGHTS) + list(G_WEIGHTS) + list(V_FACTORS):
        out[fid] = FactorObservation(fid, score, score, QualityState.OK, "syn", "SYNTHETIC")
    return out


def main() -> int:
    as_of = datetime(2026, 9, 14, tzinfo=timezone.utc)
    analysis = AnalysisEngine()
    companies = {"nvda": 82.0, "msft": 75.0, "asml": 71.0}
    snaps = [
        analysis.analyze(cid, as_of, synth_obs(score), synthetic=True, key_drivers=("synthetic_fixture",))
        for cid, score in companies.items()
    ]
    lb = LeaderboardEngine().build("synthetic-demo", as_of, snaps)
    qgv_map = {s.company_id: s for s in snaps}
    pf = PortfolioEngine().official_v11(as_of, qgv_map)
    tech = {
        s.company_id: TechnicalEngine().evaluate(s.company_id, as_of, [0.01, 0.00, 0.02], qgv=s)
        for s in snaps
    }
    mac = MacroEngine().evaluate(as_of, {"growth": 0.02, "inflation": 0.025})
    integ = IntegrationEngine().run(as_of, pf, tech, mac)
    store = TrackRecordStore()
    rec = store.record_decision(
        "INTEGRATION",
        "official-v1.1",
        as_of,
        tuple(integ.qgv_refs),
        {"gate": integ.gate.value, "policy": integ.policy_status},
    )
    report = {
        "kind": IMPLEMENTATION_KIND,
        "implementation_line": IMPLEMENTATION_LINE,
        "evidence_class": "SYNTHETIC VERIFIED",
        "as_of": as_of.isoformat(),
        "qgv_snapshots": [s.to_dict() for s in snaps],
        "leaderboard": lb.to_dict(),
        "portfolio_weight_sum": pf.weight_sum,
        "macro_version": mac.macro_version,
        "integration": integ.to_dict(),
        "track_record_id": rec.track_record_id,
        "compatibility": CompatibilityHarness().inventory(),
    }
    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "synthetic_pipeline_2026-09-23.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
