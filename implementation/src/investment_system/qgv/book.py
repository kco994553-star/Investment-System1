"""Official v1.1 book runner over synthetic catalog. NEW IMPLEMENTATION."""

from __future__ import annotations

import os

import json
from datetime import datetime
from pathlib import Path

from ..contracts.models import IntegrationResult, LeaderboardSnapshot, PortfolioSnapshot, QGVSnapshot
from ..integration.engine import IntegrationEngine
from ..macro.engine import MacroEngine
from ..providers.catalog import DEFAULT_AS_OF, iter_official_prices, iter_official_raw
from ..providers.memory import MemoryPriceProvider
from ..technical.engine import TechnicalEngine
from .leaderboard import LeaderboardEngine
from .pipeline import AnalysisPipeline
from .portfolio import OFFICIAL_V11_TARGETS, PortfolioEngine


def persist_book(payload: dict, path: Path | None = None) -> Path:
    root = Path(os.environ.get("INVESTMENT_SYSTEM_REPORTS_DIR") or Path(__file__).resolve().parents[3] / "reports")
    root.mkdir(exist_ok=True)
    path = path or root / "official_v11_book_snapshots.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def run_official_book(as_of: datetime = DEFAULT_AS_OF, persist: bool = False) -> dict:
    pipe = AnalysisPipeline()
    snaps: dict[str, QGVSnapshot] = {}
    for raw in iter_official_raw(as_of):
        snaps[raw.company_id] = pipe.analyze_raw(raw, as_of=as_of)
    missing = [cid for cid in OFFICIAL_V11_TARGETS if cid not in snaps]
    pf: PortfolioSnapshot = PortfolioEngine().official_v11(as_of, snaps)
    prices = MemoryPriceProvider()
    for px in iter_official_prices(as_of):
        prices.put(px)
    price_map = {cid: prices.get(cid, as_of).price for cid in snaps if prices.get(cid, as_of)}
    pf_eval = PortfolioEngine().evaluate(pf, price_map)
    lb: LeaderboardSnapshot = LeaderboardEngine().build("official-v1.1-synthetic", as_of, list(snaps.values()))
    tech = {cid: TechnicalEngine().evaluate(cid, as_of, [0.01, 0.0, -0.01], qgv=snap) for cid, snap in snaps.items()}
    mac = MacroEngine().evaluate(as_of, {"growth": 0.02, "inflation": 0.025})
    integ: IntegrationResult = IntegrationEngine().run(as_of, pf_eval, tech, mac)
    result = {
        "as_of": as_of.isoformat(),
        "kind": "SYNTHETIC",
        "names": len(snaps),
        "missing_official": missing,
        "portfolio_weight_sum": pf.weight_sum,
        "leaderboard_id": lb.leaderboard_snapshot_id,
        "recomputed_qgv": lb.recomputed_qgv,
        "gate": integ.gate.value,
        "policy_status": integ.policy_status,
        "v_production_all_none": all(s.V_score is None for s in snaps.values()),
        "synthetic_all": all(s.synthetic for s in snaps.values()),
        "snapshots": [s.to_dict() for s in snaps.values()],
        "leaderboard": lb.to_dict(),
        "integration": integ.to_dict(),
    }
    if persist:
        result["persisted_path"] = str(persist_book(result))
    return result
