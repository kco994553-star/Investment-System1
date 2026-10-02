"""Compatibility of a Leaderboard export with Producer Infrastructure v1 (read-only checkout).

Nothing from that checkout is copied into this branch.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWN_SRC = ROOT / "src"
SHARED = (
    "investment_system/contracts/models.py",
    "investment_system/qgv/leaderboard.py",
    "investment_system/qgv/scoring.py",
    "investment_system/qgv/factors.py",
    "investment_system/qgv/analysis.py",
)


def _sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--infra-src", required=True)
    ap.add_argument("--exports", required=True)
    ap.add_argument("--dates", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--now", default=None)
    a = ap.parse_args()
    infra_src = Path(a.infra_src).resolve()
    base = Path(a.root).resolve()
    checks: dict[str, dict] = {}

    def check(name: str, ok: bool, **detail) -> None:
        checks[name] = {"status": "PASS" if ok else "FAIL", **detail}

    diffs = {f: {"infra": _sha(infra_src / f), "own": _sha(OWN_SRC / f)} for f in SHARED}
    check("shared_leaderboard_sources_identical", all(d["infra"] == d["own"] and d["own"] for d in diffs.values()), files=diffs)
    sys.path.insert(0, str(infra_src))
    import investment_system  # noqa: E402
    investment_system.__path__.append(str(OWN_SRC / "investment_system"))
    from investment_system.leaderboard_producer import infra_boundary as ib  # noqa: E402
    from investment_system.leaderboard_producer.exporter import load_export  # noqa: E402
    from investment_system.leaderboard_producer.canonical import canonical_sha256 as own_canonical  # noqa: E402
    from investment_system.qgv.leaderboard import LeaderboardEngine  # noqa: E402

    infra = ib.load_infra()
    check("infra_importable", infra is not None, infra_src=str(infra_src))
    if infra is None:
        return _write(a.report, checks, infra_src)
    check("infra_api_complete", not ib.missing_api(infra), missing=ib.missing_api(infra))
    from investment_system.producers.assembler import assemble_bundle  # noqa: E402
    from investment_system.producers.contract import file_resolver  # noqa: E402
    from investment_system.producers.registry import ProduceRequest, default_registry  # noqa: E402
    from investment_system.product.web_mvp import validate_bundle  # noqa: E402

    now = datetime.fromisoformat(a.now) if a.now else datetime.now(timezone.utc).replace(microsecond=0)
    reg = default_registry()
    original_build = LeaderboardEngine.build

    def _boom(*_a, **_k):
        raise AssertionError("exporter/infra path recalculated ranking")

    LeaderboardEngine.build = _boom  # type: ignore[method-assign]
    try:
        for d in [x.strip() for x in a.dates.split(",") if x.strip()]:
            records, manifest = load_export(base / a.exports, d)
            check(f"{d}:export_reload_valid", True, n_records=len(records), ranked=manifest["semantic"]["ranked_count"])
            out = ib.build_infra_snapshots(
                infra, records, manifest, root=base, out_dir=base / a.exports,
                generated_at=now.isoformat(), requested_as_of=now.isoformat(),
            )
            cand, pub = out["candidate"], out["published"]
            ranked_ids = sorted(
                r["semantic"]["company_id"] for r in records if r["semantic"]["eligibility"]["state"] == "RANKED"
            )
            check(
                f"{d}:leaderboard_section_rows",
                cand["scope"]["kind"] == "ROWS" and cand["scope"]["entity_ids"] == ranked_ids and cand["synthetic"] is False,
                n=len(cand["scope"]["entity_ids"]),
            )
            reads = infra.adapters.WEB_READS["leaderboard"]
            row0 = (cand["data"].get("rows") or [{}])[0]
            present = [f.split(".")[-1] for f in reads if f.split(".")[-1] in row0 or f.endswith("rank") and "rank" in row0]
            # Web reads rank/company_id/ticker/total_score from the engine row. The other four stay absent.
            have = {k for k in ("rank", "company_id", "ticker", "total_score") if k in row0}
            absent = {k for k in ("market_cap_rank", "daily_move", "consensus", "scenario", "reevaluation_trigger") if k not in row0}
            check(
                f"{d}:web_fields_match_partial_contract",
                have == {"rank", "company_id", "ticker", "total_score"} and len(absent) == 5,
                present_on_engine_row=sorted(have),
                absent_on_engine_row=sorted(absent),
                adapter_missing=list(infra.adapters.SECTION_COMPATIBILITY["leaderboard"]["missing_web_fields"]),
                web_reads=list(reads),
            )
            check(
                f"{d}:canonical_serialization_agrees",
                own_canonical(cand["data"]) == infra.serialization.canonical_sha256(cand["data"]) == cand["data_sha256"],
            )
            err = out["candidate_error"] or {}
            check(f"{d}:research_candidate_rejected", err.get("type") == "ResearchStatusError", error=err)
            probe = copy.deepcopy(cand)
            probe["methodology"]["status"] = "SHAPE_PROBE_ONLY_NOT_A_STATUS"
            try:
                infra.contract.validate_snapshot(probe)
                probe_err = None
            except ValueError as e:
                probe_err = f"{type(e).__name__}: {e}"
            check(f"{d}:shape_probe_valid_except_research_status", probe_err is None, error=probe_err)
            check(
                f"{d}:published_not_available",
                pub["data_state"] == "NOT_AVAILABLE" and pub["data"] is None and pub["reason_code"] == ib.REASON_CODE,
                reason_code=pub["reason_code"],
                registry_placeholder=infra.registry.DEFAULT_UNAVAILABLE["leaderboard"][0],
            )
            resolve = file_resolver(base)
            ok = all(
                resolve(i["artifact_id"]) is not None
                and infra.serialization.sha256_hex(resolve(i["artifact_id"])) == i["sha256"]
                for i in cand["provenance"]["inputs"]
            )
            check(f"{d}:file_inputs_reverify", ok)
            snaps = reg.run(ProduceRequest(requested_as_of=now, now=now))
            snaps["leaderboard"] = pub
            try:
                bundle = assemble_bundle(reg.producers["universe"].companies(), snaps, now)
                validate_bundle(bundle)
                check(
                    f"{d}:bundle_assembles_and_web_validates",
                    bundle["leaderboard"]["state"] == "NOT_AVAILABLE",
                    leaderboard_state=bundle["leaderboard"]["state"],
                    reason_code=bundle["leaderboard"]["producer"].get("reason_code"),
                )
            except Exception as e:  # noqa: BLE001
                check(f"{d}:bundle_assembles_and_web_validates", False, error=f"{type(e).__name__}: {e}")
            check(f"{d}:engine_not_called", out["engine_called"] is False and LeaderboardEngine.build is _boom)
    finally:
        LeaderboardEngine.build = original_build  # type: ignore[method-assign]
    _write(a.report, checks, infra_src)


def _write(report: str, checks: dict, infra_src: Path) -> None:
    from investment_system.leaderboard_producer.infra_boundary import INFRA_PIN
    out = {
        "kind": "LEADERBOARD_PRODUCER_INFRA_COMPAT",
        "infra_pin": INFRA_PIN,
        "infra_src": str(infra_src),
        "status": "PASS" if checks and all(c["status"] == "PASS" for c in checks.values()) else "FAIL",
        "checks": checks,
    }
    Path(report).parent.mkdir(parents=True, exist_ok=True)
    Path(report).write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({"status": out["status"], "checks": {k: v["status"] for k, v in checks.items()}}, indent=1))
    if out["status"] != "PASS":
        raise SystemExit("Producer Infrastructure compatibility FAIL")


if __name__ == "__main__":
    main()
