"""Compatibility check: persisted QGV exports vs Producer Infrastructure v1, using the Infrastructure's own code.

The Infrastructure is not merged into this branch, so it is read from a separate read-only checkout of
feature/producer-infrastructure-v1 at the pinned commit (--infra-src = <checkout>/implementation/src). Nothing
from that checkout is copied into this branch.

Checks (each recorded PASS/FAIL):
  1. QGV sources are byte-identical; models.py is either exact original or CDR-004's exact four-field adoption
     with the complete pre-existing AST preserved (so QGVSnapshot means the same thing);
  2. every Infrastructure name the boundary consumes exists;
  3. per as_of, the export reloads and re-validates; `adapters.qgv_section` accepts the rebuilt snapshots; every
     Web-read field is present; canonical serialization hashes agree;
  4. the research candidate (FROZEN_SNAPSHOT + PROVISIONAL_RESEARCH) is rejected with ResearchStatusError;
  5. a shape-only probe (status relabelled in memory, never written) passes validate_snapshot. That shows
     research status is the only blocker;
  6. the published NOT_AVAILABLE snapshot validates. Its reason code equals the registry's QGV code;
  7. the file inputs re-verify through `contract.file_resolver`;
  8. `assemble_bundle` with the default registry plus the published QGV snapshot passes `web_mvp.validate_bundle`.

  python tools/qgv_producer_infra_compat.py --infra-src /tmp/infra/implementation/src \
      --exports reports/qgv_producer/full --dates 2024-12-31 --report reports/qgv_producer/infra_compat.json
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from producer_source_compat import boundary_pin, compare_shared_sources, dependency_reference

ROOT = Path(__file__).resolve().parents[1]
OWN_SRC = ROOT / "src"
SHARED = ("investment_system/contracts/models.py", "investment_system/contracts/enums.py", "investment_system/versions.py",
          "investment_system/qgv/analysis.py", "investment_system/qgv/scoring.py", "investment_system/qgv/factors.py",
          "investment_system/qgv/raw_map.py", "investment_system/qgv/pipeline.py",
          "investment_system/validation/vertical_slice.py", "investment_system/validation/historical.py")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--infra-src", required=True)
    ap.add_argument("--exports", required=True, help="export dir relative to implementation/")
    ap.add_argument("--dates", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--root", default=str(ROOT), help="base for --exports and file: provenance ids (default implementation/)")
    ap.add_argument("--now", default=None, help="tz-aware evaluation clock for assembly (default: now UTC)")
    a = ap.parse_args()
    infra_src = Path(a.infra_src).resolve()
    base = Path(a.root).resolve()
    checks: dict[str, dict] = {}

    def check(name: str, ok: bool, **detail) -> None:
        checks[name] = {"status": "PASS" if ok else "FAIL", **detail}

    source = compare_shared_sources(OWN_SRC, infra_src, SHARED)
    check("shared_qgv_sources_compatible", source["status"] == "PASS", files=source["files"],
          authority="CDR-004 exact optional lineage adoption; all other shared sources byte-identical")
    if source["status"] != "PASS":
        return _write(a.report, checks, infra_src)
    # Infrastructure tree provides investment_system; this branch adds only the qgv_producer subpackage.
    sys.path.insert(0, str(infra_src))
    import investment_system  # noqa: E402
    investment_system.__path__.append(str(OWN_SRC / "investment_system"))
    from investment_system.qgv_producer import infra_boundary as ib  # noqa: E402
    from investment_system.qgv_producer.exporter import load_export  # noqa: E402
    from investment_system.qgv_producer.record import canonical_sha256 as own_canonical  # noqa: E402
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
    for d in [x.strip() for x in a.dates.split(",") if x.strip()]:
        records, manifest = load_export(base / a.exports, d)
        check(f"{d}:export_reload_valid", True, n_records=len(records), counts=manifest["semantic"]["counts"])
        out = ib.build_infra_snapshots(infra, records, manifest, root=base, out_dir=base / a.exports,
                                       generated_at=now.isoformat(), requested_as_of=now.isoformat())
        cand, pub = out["candidate"], out["published"]
        pass_ids = sorted(r["semantic"]["company_id"] for r in records if r["semantic"]["status"] == "PASS")
        check(f"{d}:qgv_section_entity_map", cand["scope"]["kind"] == "ENTITY_MAP" and cand["scope"]["entity_ids"] == pass_ids,
              n_entities=len(cand["scope"]["entity_ids"]))
        reads = infra.adapters.WEB_READS["qgv"]
        missing = sorted({f for v in cand["data"].values() for f in reads if f not in v})
        check(f"{d}:web_read_fields_present", not missing, web_reads=list(reads), missing=missing)
        check(f"{d}:canonical_serialization_agrees",
              own_canonical(cand["data"]) == infra.serialization.canonical_sha256(cand["data"]) == cand["data_sha256"])
        err = out["candidate_error"] or {}
        check(f"{d}:research_candidate_rejected", err.get("type") == "ResearchStatusError", error=err)
        probe = copy.deepcopy(cand)
        probe["methodology"]["status"] = "SHAPE_PROBE_ONLY_NOT_A_STATUS"
        try:
            infra.contract.validate_snapshot(probe)
            probe_err = None
        except ValueError as e:
            probe_err = f"{type(e).__name__}: {e}"
        check(f"{d}:shape_probe_valid_except_research_status", probe_err is None, error=probe_err,
              note="in-memory only; proves research status is the sole Infrastructure blocker")
        reg_code = infra.registry.DEFAULT_UNAVAILABLE["qgv"][0]
        check(f"{d}:published_not_available", pub["data_state"] == "NOT_AVAILABLE" and pub["data"] is None
              and pub["reason_code"] == reg_code == ib.REASON_CODE, reason_code=pub["reason_code"])
        resolve = file_resolver(base)
        ok = all(resolve(i["artifact_id"]) is not None and
                 infra.serialization.sha256_hex(resolve(i["artifact_id"])) == i["sha256"] for i in cand["provenance"]["inputs"])
        check(f"{d}:file_inputs_reverify", ok, inputs=cand["provenance"]["inputs"])
        snaps = reg.run(ProduceRequest(requested_as_of=now, now=now))
        snaps["qgv"] = pub
        companies = reg.producers["universe"].companies()
        try:
            bundle = assemble_bundle(companies, snaps, now)
            validate_bundle(bundle)
            check(f"{d}:bundle_assembles_and_web_validates", bundle["qgv"]["state"] == "NOT_AVAILABLE",
                  qgv_state=bundle["qgv"]["state"], qgv_reason_code=bundle["qgv"]["producer"].get("reason_code"))
        except Exception as e:  # noqa: BLE001 - record any failure as evidence
            check(f"{d}:bundle_assembles_and_web_validates", False, error=f"{type(e).__name__}: {e}")
        cids = {c.get("company_id") for c in companies}
        outside = sorted(set(pass_ids) - cids)
        checks[f"{d}:identity_keys_match_web_companies"] = {
            "status": "PASS" if not outside else "INFO", "n_not_in_web_companies": len(outside), "sample": outside[:10],
            "note": "informational: the Web companies list is the Frozen 2024-12-31 Universe; other dates may differ"}
    _write(a.report, checks, infra_src)


def _write(report: str, checks: dict, infra_src: Path) -> None:
    historical_pin = boundary_pin(OWN_SRC / "investment_system/qgv_producer/infra_boundary.py")
    out = {"kind": "QGV_PRODUCER_INFRA_COMPAT", "historical_infra_pin": historical_pin,
           "dependency_source": dependency_reference(infra_src, OWN_SRC, historical_pin), "infra_src": str(infra_src),
           "status": "PASS" if all(c["status"] in ("PASS", "INFO") for c in checks.values()) else "FAIL", "checks": checks}
    Path(report).parent.mkdir(parents=True, exist_ok=True)
    Path(report).write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({"status": out["status"], "checks": {k: v["status"] for k, v in checks.items()}}, indent=1))
    if out["status"] != "PASS":
        raise SystemExit("Producer Infrastructure compatibility FAIL")


if __name__ == "__main__":
    main()
