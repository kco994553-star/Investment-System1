"""Build a production-shaped Web fixture for state presentation (freshness, withheld metadata).

Validation only. Every section value is a literal TEST VECTOR, never real investment data and never
a grant. No engine, provider, calibration or Holdout is called. The bundle is produced by the real
producer path (contract.make_snapshot / not_available -> assembler.assemble_bundle with an explicit
evaluation clock), so freshness and reason codes are the values the assembler persists. It is then
passed to the existing, unchanged web_mvp.build (which runs the existing schema-1 validator).

Served bundle (data.json), assembled at NOW:
  universe       FROZEN_SNAPSHOT (Track A, existing FrozenUniverseProducer)
  macro          LIVE, persisted freshness FRESH (expires far in the future)
  technical      LIVE, persisted freshness STALE (expired before NOW, no usable_until)
  changes        LIVE, persisted freshness FRESH at NOW, but expires_at is before the browser clock:
                 the existing view-time rule shows STALE
  leaderboard    LIVE past usable_until -> the assembler publishes NOT_AVAILABLE + EXPIRED_NOT_USABLE
  qgv            NOT_AVAILABLE with persisted producer metadata (reason_code, as_of, methodology, counts)
  portfolio, news, relationships   NOT_AVAILABLE from the existing default registry

Variants (written to the evidence folder, never served directly; the browser test substitutes them):
  variant-not-usable.json      a section that still carries values although its persisted freshness is
                               NOT_USABLE (news via producer.freshness, changes via producer_manifest)
  variant-sparse-metadata.json producer metadata removed, except one reason_code (nothing is fabricated)
  variant-render-error.json    schema-1-valid bundle whose news payload is an object, not a list; the
                               news route throws while rendering

Usage:
  python tools/build_web_state_presentation_fixture.py --out /tmp/web-state --evidence /tmp/web-state-evidence
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.product.web_mvp import build, validate_bundle  # noqa: E402
from investment_system.producers.assembler import assemble_bundle  # noqa: E402
from investment_system.producers.contract import make_snapshot, not_available, validate_snapshot  # noqa: E402
from investment_system.producers.registry import (  # noqa: E402
    DEFAULT_REASON, FrozenUniverseProducer, ProduceRequest, default_registry,
)

NOW = datetime(2026, 1, 2, tzinfo=timezone.utc)  # explicit assembly clock
# The browser test pins its clock here, so the view-time STALE of `changes` does not depend on the CI date.
BROWSER_CLOCK = "2026-10-03T12:00:00Z"
AS_OF = "2026-01-01T20:00:00+00:00"
COMPANY = "nvda"
METHOD = {"id": "TEST_VECTOR", "version": "TEST_VECTOR_V1", "status": "VALIDATED"}
INPUTS = [{"artifact_id": "test:web-state-presentation", "sha256": "0" * 64}]
# Present only in withheld inputs; must never reach the DOM.
WITHHELD_PROBES = ("4321.98765", "NOT_USABLE_PROBE_NEWS", "NOT_USABLE_PROBE_CHANGES")


def _live(section, data, scope_kind, as_of, expires_at, usable_until=None, validation=None):
    return validate_snapshot(make_snapshot(
        producer_id=f"test.web_state.{section}", producer_version="TEST_VECTOR_V1", section=section,
        data_state="LIVE", as_of=as_of, requested_as_of=as_of, generated_at=NOW.isoformat(),
        expires_at=expires_at, usable_until=usable_until, methodology=METHOD, synthetic=False,
        provenance={"source": f"TEST VECTOR / {section}", "inputs": INPUTS},
        validation=validation or {"status": "PASS", "checks": ["TEST_VECTOR_SHAPE_ONLY"]},
        data=data, scope_kind=scope_kind))


def snapshots() -> dict:
    snaps = default_registry().run(ProduceRequest(NOW, NOW))
    snaps["macro"] = _live("macro", {"state": "NORMAL", "regime": "TEST_REGIME_FRESH", "indicators": {"CPIAUCSL": 33.33},
                                     "exposures": {COMPANY: "TEST_EXPOSURE_FRESH"}},
                           "DOCUMENT", AS_OF, "2099-01-01T00:00:00+00:00")
    snaps["technical"] = _live("technical", {COMPANY: {"regime": "TEST_REGIME_STALE", "execution_zone": "WAIT",
                                                       "invalidation": "TEST_INVALIDATION_STALE"}},
                               "ENTITY_MAP", "2026-01-01T00:00:00+00:00", "2026-01-01T12:00:00+00:00")
    snaps["changes"] = _live("changes", {"summary": "TEST_CHANGES_VIEW_STALE"}, "DOCUMENT", AS_OF,
                             "2026-01-03T00:00:00+00:00")
    snaps["leaderboard"] = _live("leaderboard", {"rows": [{"company_id": COMPANY, "ticker": "NVDA", "rank": 1,
                                                           "total_score": 4321.98765}]},
                                 "ROWS", "2025-12-30T00:00:00+00:00", "2025-12-31T00:00:00+00:00",
                                 usable_until="2026-01-01T00:00:00+00:00",
                                 validation={"status": "PASS", "checks": ["TEST_VECTOR_SHAPE_ONLY"],
                                             "expected_count": 1, "ranked_count": 1})
    qgv = not_available("qgv", "test.web_state.qgv", "TEST_VECTOR_V1", NOW.isoformat(), DEFAULT_REASON,
                        "RESEARCH_DISPLAY_GRANT_NONE", NOW.isoformat(),
                        {"id": "TEST_QGV", "version": "TEST_VECTOR_V1", "status": "PROVISIONAL_RESEARCH"})
    # Persisted producer metadata, distinct from section availability (same shape as the codex
    # withheld-contract fixture); none of it becomes section data or authority.
    qgv["as_of"] = AS_OF
    qgv["validation"] = {"status": "PASS", "checks": ["TEST_VECTOR_SHAPE_ONLY"],
                         "coverage_counts": {"COMPLETE": 3, "NONE": 1, "PARTIAL": 1}}
    snaps["qgv"] = validate_snapshot(qgv)
    return snaps


def fixture_bundle() -> dict:
    return assemble_bundle(FrozenUniverseProducer().companies(), snapshots(), NOW)


def variants(bundle: dict) -> dict:
    not_usable = deepcopy(bundle)
    not_usable["news"] = {"state": "LIVE", "as_of": AS_OF, "source": "TEST VECTOR / news", "expires_at": "2099-01-01T00:00:00+00:00",
                          "data": [{"headline": "NOT_USABLE_PROBE_NEWS", "issuer_ids": [], "available_at": AS_OF,
                                    "source_language": "en"}],
                          "producer": {**deepcopy(bundle["macro"]["producer"]), "freshness": "NOT_USABLE"}}
    not_usable["changes"].pop("producer")
    not_usable["changes"]["data"] = {"summary": "NOT_USABLE_PROBE_CHANGES"}
    not_usable["producer_manifest"]["sections"]["changes"]["freshness"] = "NOT_USABLE"
    sparse = deepcopy(bundle)
    sparse.pop("producer_manifest")
    for name in ("universe", "qgv", "technical", "macro", "portfolio", "leaderboard", "news", "relationships", "changes"):
        sparse[name].pop("producer", None)
    sparse["portfolio"]["producer"] = {"reason_code": "ONLY_REASON_CODE_PERSISTED"}
    render_error = deepcopy(bundle)
    render_error["news"] = {"state": "FROZEN_SNAPSHOT", "as_of": AS_OF, "source": "TEST VECTOR / malformed news shape",
                            "data": {"unexpected": "object instead of a list"}}
    out = {"variant-not-usable.json": not_usable, "variant-sparse-metadata.json": sparse,
           "variant-render-error.json": render_error}
    for v in out.values():
        validate_bundle(v)  # every variant is accepted by the existing, unchanged schema-1 validator
    return out


def manifest(bundle: dict) -> dict:
    sections = bundle["producer_manifest"]["sections"]
    return {"kind": "WEB_STATE_PRESENTATION_FIXTURE_V1", "scope": "TEST VECTORS ONLY; NOT_REAL_DATA; NO GRANT",
            "assembly_clock": NOW.isoformat(), "browser_clock": BROWSER_CLOCK, "company": COMPANY, "as_of": AS_OF,
            "persisted": {name: {"state": s["state"], "freshness": s["freshness"], "reason_code": s["reason_code"]}
                          for name, s in sections.items()},
            "expected_view": {"macro": "LIVE+FRESH", "technical": "LIVE+STALE", "changes": "LIVE+STALE (view-time)",
                              "leaderboard": "NOT_AVAILABLE+NOT_USABLE", "qgv": "NOT_AVAILABLE+metadata"},
            "withheld_probes": list(WITHHELD_PROBES), "variants": sorted(variants(bundle)),
            "research_display": "NONE", "frozen_grant": "NONE", "live_grant": "NONE"}


def build_fixture(out, evidence) -> dict:
    out, evidence = Path(out).resolve(), Path(evidence).resolve()
    if out == evidence or out in evidence.parents:
        raise ValueError("evidence must be outside the served Web folder")
    bundle = fixture_bundle()
    before = deepcopy(bundle)
    build(out, bundle)
    if json.loads((out / "data.json").read_text(encoding="utf-8")) != before:
        raise AssertionError("the Web build must not rewrite the bundle; presentation is render-time only")
    evidence.mkdir(parents=True, exist_ok=True)
    for name, v in variants(before).items():
        (evidence / name).write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
    m = manifest(before)
    (evidence / "fixture-manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    p.add_argument("--evidence", required=True)
    a = p.parse_args()
    print(json.dumps(build_fixture(a.out, a.evidence), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
