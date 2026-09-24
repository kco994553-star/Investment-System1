#!/usr/bin/env python3
"""Opportunistic free-source smoke. LIVE_FETCH only. Not Stage 2."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.providers.yahoo_chart import fetch_chart, parse_chart, to_price_point
from investment_system.qgv.financial_issuer import analyze_synthetic_jpm, try_sec_jpm


def main() -> int:
    now = datetime.now(timezone.utc)
    report = {
        "kind": "LIVE_ATTEMPT",
        "as_of": now.isoformat(),
        "stage2": False,
        "real_data_verified": False,
        "yahoo": {},
        "jpm_synthetic": None,
        "jpm_sec": None,
    }
    for cid, symbol in (("nvda", "NVDA"), ("jpm", "JPM"), ("msft", "MSFT")):
        payload = fetch_chart(symbol)
        parsed = parse_chart(payload) if payload else None
        if parsed:
            pt = to_price_point(cid, parsed)
            report["yahoo"][cid] = {
                "ok": True,
                "price": pt.price,
                "currency": pt.currency,
                "source": "yahoo-chart",
                "evidence": "LIVE_FETCH",
            }
        else:
            report["yahoo"][cid] = {"ok": False, "evidence": "LIVE_UNAVAILABLE"}
    snap = analyze_synthetic_jpm()
    report["jpm_synthetic"] = {
        "profile": snap.profile_kind.value,
        "Q": snap.Q_score,
        "V": snap.V_score,
        "synthetic": snap.synthetic,
    }
    live = try_sec_jpm(now)
    if live is None:
        report["jpm_sec"] = {"ok": False, "evidence": "LIVE_UNAVAILABLE"}
    else:
        report["jpm_sec"] = {
            "ok": True,
            "evidence": "LIVE_FETCH",
            "Q": live.Q_score,
            "V": live.V_score,
            "source_kind": live.implementation_kind,
            "synthetic": live.synthetic,
        }
    out = ROOT / "reports" / "live_smoke_2026-09-23.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(out)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
