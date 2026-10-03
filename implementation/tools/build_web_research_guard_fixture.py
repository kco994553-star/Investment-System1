"""Build a hand-made schema-1 Web fixture for the render-time research guard (G3).

Validation only. Every section value is a literal TEST VECTOR, never real investment data,
never a grant. No engine, provider, calibration or Holdout is called. The bundle is passed
to the existing, unchanged web_mvp.build (which runs the existing schema-1 validator).

Sections:
  withheld  LIVE / FROZEN_SNAPSHOT carrying a research marker (producers/contract.py RESEARCH_STATUSES)
  rendered  valid LIVE (non-research methodology), legacy FROZEN_SNAPSHOT universe, DEMO, NOT_AVAILABLE

Usage:
  python tools/build_web_research_guard_fixture.py --out /tmp/web-guard --evidence /tmp/web-guard-evidence
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.product.web_mvp import build, repository_bundle  # noqa: E402

AS_OF = "2026-10-02T20:00:00+00:00"
# Far-future expiry keeps the valid LIVE section FRESH regardless of the test clock.
EXPIRES = "2099-01-01T00:00:00+00:00"
COMPANY = "nvda"
# Probe values: present in data.json, must never reach the DOM for withheld sections.
WITHHELD_PROBES = ("11.11", "22.22", "66.66", "77.77", "RESEARCH_PROBE_QGV", "RESEARCH_PROBE_REGIME",
                   "RESEARCH_PROBE_ZONE", "RESEARCH_PROBE_CHANGES", "RESEARCH_PROBE_NEWS")
# Values of the valid sections: must render exactly as before.
RENDERED_PROBES = {"macro": ("TEST_REGIME_VALID", "33.33"), "portfolio": ("44.44%", "TEST DEMO / NOT ACTUAL")}


def _producer(state: str, status: str) -> dict:
    """Producer metadata at the path the assembler writes (<section>.producer.methodology.status)."""
    return {"producer_id": "test.web_research_guard", "producer_version": "TEST_VECTOR_V1",
            "data_state": state, "freshness": "FRESH" if state == "LIVE" else "NOT_APPLICABLE",
            "as_of": AS_OF, "methodology": {"id": "TEST_VECTOR", "version": "TEST_VECTOR_V1", "status": status},
            "synthetic": False, "validation": {"status": "PASS", "checks": ["TEST_VECTOR_SHAPE_ONLY"]}}


def _section(state: str, data, source: str, status: str | None = None) -> dict:
    s = {"state": state, "as_of": AS_OF, "source": source, "data": data}
    if state == "LIVE":
        s["expires_at"] = EXPIRES
    if status is not None:
        s["producer"] = _producer(state, status)
    return s


def fixture_bundle() -> dict:
    b = repository_bundle()  # Track A FROZEN_SNAPSHOT universe (legacy, no producer metadata)
    # (a) LIVE + methodology.status in RESEARCH_STATUSES
    b["qgv"] = _section("LIVE", {COMPANY: {"Q_score": 11.11, "G_score": 11.11, "V_score": 11.11, "total_score": 11.11,
                                           "confidence": 11.11, "coverage_state": "RESEARCH_PROBE_QGV"}},
                        "TEST VECTOR / research qgv", "PROVISIONAL_RESEARCH")
    b["changes"] = _section("LIVE", {"summary": "RESEARCH_PROBE_CHANGES 77.77"}, "TEST VECTOR / research changes", "IDEA")
    b["news"] = _section("LIVE", [{"headline": "RESEARCH_PROBE_NEWS", "issuer_ids": [], "available_at": AS_OF,
                                   "source_language": "en"}],
                         "TEST VECTOR / research news", "PROVISIONAL_INITIAL_PRIOR")
    # (b) FROZEN_SNAPSHOT + research marker (methodology.status, and research_state.status without producer metadata)
    b["technical"] = _section("FROZEN_SNAPSHOT", {COMPANY: {"regime": "RESEARCH_PROBE_REGIME",
                                                             "execution_zone": "RESEARCH_PROBE_ZONE", "invalidation": 22.22}},
                              "TEST VECTOR / research technical", "PROVISIONAL")
    b["leaderboard"] = _section("FROZEN_SNAPSHOT", {"rows": [{"company_id": COMPANY, "ticker": "NVDA", "rank": 1,
                                                              "total_score": 66.66,
                                                              "research_state": {"status": "PROVISIONAL_RESEARCH",
                                                                                 "track_c_validated": False}}]},
                                "TEST VECTOR / research leaderboard rows")
    # (c) valid LIVE: methodology.status outside RESEARCH_STATUSES
    b["macro"] = _section("LIVE", {"state": "NORMAL", "regime": "TEST_REGIME_VALID", "indicators": {"CPIAUCSL": 33.33},
                                   "exposures": {COMPANY: "TEST_EXPOSURE_VALID"}},
                          "TEST VECTOR / valid macro", "VALIDATED")
    # (d) DEMO (legacy, no producer metadata) and NOT_AVAILABLE (relationships, from repository_bundle)
    b["portfolio"] = _section("DEMO", {"holdings": [{"company_id": COMPANY, "ticker": "NVDA", "target_weight": 0.4444}],
                                       "role": "TEST DEMO / NOT ACTUAL"}, "TEST VECTOR / demo portfolio")
    return b


def manifest() -> dict:
    return {"kind": "WEB_RESEARCH_GUARD_FIXTURE_V1", "scope": "TEST VECTORS ONLY; NOT_REAL_DATA; NO GRANT",
            "company": COMPANY,
            "withheld": {"qgv": "producer.methodology.status: PROVISIONAL_RESEARCH",
                         "changes": "producer.methodology.status: IDEA",
                         "news": "producer.methodology.status: PROVISIONAL_INITIAL_PRIOR",
                         "technical": "producer.methodology.status: PROVISIONAL",
                         "leaderboard": "research_state.status: PROVISIONAL_RESEARCH"},
            "rendered": {"universe": "FROZEN_SNAPSHOT", "macro": "LIVE", "portfolio": "DEMO",
                         "relationships": "NOT_AVAILABLE"},
            "withheld_probes": list(WITHHELD_PROBES), "rendered_probes": RENDERED_PROBES,
            "research_display": "NONE", "frozen_grant": "NONE", "live_grant": "NONE"}


def build_fixture(out, evidence) -> dict:
    out, evidence = Path(out).resolve(), Path(evidence).resolve()
    if out == evidence or out in evidence.parents:
        raise ValueError("evidence must be outside the served Web folder")
    bundle = fixture_bundle()
    before = deepcopy(bundle)
    build(out, bundle)
    if json.loads((out / "data.json").read_text(encoding="utf-8")) != before:
        raise AssertionError("the Web build must not rewrite the bundle; the guard is render-time only")
    m = manifest()
    evidence.mkdir(parents=True, exist_ok=True)
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
