"""Offline Leaderboard replay from persisted QGV exports. Does not fetch and does not rescore.

Example:
  python tools/leaderboard_producer.py \
    --qgv-exports /path/to/qgv_producer/full \
    --dates 2024-06-30,2024-09-30,2024-12-31 \
    --out reports/leaderboard_producer/full
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.leaderboard_producer.exporter import export_batch  # noqa: E402
from investment_system.leaderboard_producer.qgv_input import load_official_snapshot, load_qgv_export  # noqa: E402
from investment_system.leaderboard_producer.rank import build_leaderboard  # noqa: E402


def _code_commit(explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qgv-exports", required=True)
    ap.add_argument("--dates", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--official-dir", default=str(ROOT / "reports" / "gate_evidence"))
    ap.add_argument("--code-commit", default=None)
    ap.add_argument("--now", default=None)
    a = ap.parse_args()
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(timezone.utc).replace(microsecond=0)
    if now.tzinfo is None:
        raise SystemExit("now must be timezone-aware")
    code = _code_commit(a.code_commit)
    summary = []
    for day in [x.strip() for x in a.dates.split(",") if x.strip()]:
        records, manifest = load_qgv_export(a.qgv_exports, day)
        official, official_sha = load_official_snapshot(Path(a.official_dir) / f"official_snapshot_{day}.json")
        produced, out_manifest = build_leaderboard(
            records, manifest, official, official_sha, generated_at=now, code_commit=code, require_real=True,
        )
        written = export_batch(produced, out_manifest, a.out)
        sem = written["semantic"]
        summary.append({
            "as_of": day,
            "expected": sem["expected_count"],
            "eligible": sem["eligible_count"],
            "ranked": sem["ranked_count"],
            "not_ranked": sem["not_ranked_count"],
            "coverage": sem["coverage_counts"],
            "null_total_score_count": sem["null_total_score_count"],
            "tie_group_count": sem["tie_group_count"],
            "tied_company_count": sem["tied_company_count"],
            "within_tie_order_approval": sem["within_tie_order_approval"],
            "ranking_fingerprint": sem["ranking_fingerprint"],
            "semantic_sha256": written["semantic_sha256"],
            "publication": sem["publication"]["data_state"],
            "universe_id": sem["universe"]["universe_id"],
        })
        print(json.dumps(summary[-1], sort_keys=True))
    report = Path(a.out) / "leaderboard_producer_run.json"
    report.write_text(json.dumps({"code_commit": code, "generated_at": now.isoformat(), "dates": summary}, indent=1) + "\n")


if __name__ == "__main__":
    main()
