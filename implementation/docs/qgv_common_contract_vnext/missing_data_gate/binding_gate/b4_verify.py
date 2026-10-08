"""Reproduce B4's six bounded characterization cases without production changes.

This verifier reads b4_cases.json and checks original source/golden hashes. It
does not record/overwrite any evidence, choose a method or admit a runtime score.
Use PYTHONPATH=implementation/src:implementation/tools:<existing-jsonschema-dir>.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import fields, replace
from datetime import datetime, timezone
from pathlib import Path

from investment_system.contracts.models import DataStamp, FactorObservation
from investment_system.contracts.raw import RawFundamentals
from investment_system.contracts.strategy import custom_profile
from investment_system.personal.versioning import content_hash
from investment_system.personal.weights import WeightOverride
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.g_horizon import GHorizonConfig
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.qgv.raw_map import map_raw
from investment_system.qgv.track_record import TrackRecordStore
from qgv_contract_audit import validate_spec_record


HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in HERE.parents if (parent / "implementation/src").is_dir())
DOCS = ROOT / "implementation/docs/qgv_common_contract_vnext"


def verify() -> dict:
    expected = json.loads((HERE / "b4_cases.json").read_text())
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
              for path in expected["source_and_golden_sha256"]}
    if hashes != expected["source_and_golden_sha256"]:
        raise AssertionError("Protected source/golden drift; fresh audit required")
    cases = {case["case_id"]: case for case in expected["cases"]}
    checks = []

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        checks.append({"assertion": label, "result": "PASS"})

    as_of = datetime(2026, 9, 14, tzinfo=timezone.utc)
    stamp = DataStamp("B4-SYNTHETIC", "synthetic", "synthetic", "B4 fixture",
                      as_of, as_of, as_of, synthetic=True)
    raw = RawFundamentals("B4-SYNTHETIC", stamp, revenue=120, revenue_prev=100,
                          fcf=20, source_kind="SYNTHETIC")

    def versions(snapshot):
        return {key: getattr(snapshot, key) for key in
                ("qgv_system_version", "qgv_standard_version",
                 "qgv_analysis_contract", "implementation_line")}

    base = map_raw(raw)
    engine = AnalysisEngine()
    old = engine.analyze(raw.company_id, as_of, base, synthetic=True)
    changed = dict(base)
    changed["next_3_5y_growth"] = replace(base["next_3_5y_growth"],
                                         raw_value=60.0, score_0_100=60.0)
    new = engine.analyze(raw.company_id, as_of, changed, synthetic=True)
    check("case1 accepts alternate synthetic factor output without method metadata",
          old.G_score != new.G_score and
          old.G_score == cases["B4-01"]["observed"]["G_before"] and
          new.G_score == cases["B4-01"]["observed"]["G_after"])
    check("case1 coarse snapshot versions remain equal", versions(old) == versions(new))

    one = AnalysisPipeline().analyze_raw(raw, available_quarters=4,
                                        g_horizon=GHorizonConfig("1Q"))
    five = AnalysisPipeline().analyze_raw(raw, available_quarters=4,
                                         g_horizon=GHorizonConfig("5Y"))
    check("case2 requested horizon changes metadata",
          one.g_horizon != five.g_horizon and
          one.g_horizon == cases["B4-02"]["observed"]["horizon_1Q"] and
          five.g_horizon == cases["B4-02"]["observed"]["horizon_5Y"])
    check("case2 requested horizon does not select a different G method",
          one.G_score == five.G_score == cases["B4-02"]["observed"]["G_score"])

    eps = map_raw(replace(raw, eps=3, eps_prev=2))
    fcf = base["eps_fcf_per_share_growth"]
    epsobs = eps["eps_fcf_per_share_growth"]
    check("case3 EPS and FCF branches share factor ID and explanatory label",
          fcf.factor_id == epsobs.factor_id and fcf.notes == epsobs.notes)
    check("case3 current FCF branch differs from EPS branch",
          fcf.score_0_100 == cases["B4-03"]["observed"]["fcf_fallback_score"] == 0.0 and
          epsobs.score_0_100 == cases["B4-03"]["observed"]["eps_score"] == 100.0)

    pe = map_raw(replace(raw, price=20, eps=1))["fundamental_value"]
    dcf = map_raw(replace(raw, price=20, eps=1, dcf_value=20))["fundamental_value"]
    check("case4 DCF and PE branches can emit indistinguishable observations",
          pe == dcf and pe.score_0_100 == cases["B4-04"]["observed"]["score"])
    sample = json.loads((DOCS / "contract_record.example.json").read_text())
    changed_hash = deepcopy(sample)
    changed_hash["calculation_ref"]["sha256"] = "a" * 64
    check("case4 same-version changed well-shaped hash remains SPEC_VALID",
          validate_spec_record(sample)["status"] == "SPEC_VALID" and
          validate_spec_record(changed_hash)["status"] == "SPEC_VALID" and
          sample["calculation_ref"]["version"] == changed_hash["calculation_ref"]["version"])

    store = TrackRecordStore()
    rec = store.record_decision("B4-SYNTHETIC", "B4-SYNTHETIC", as_of,
                                (old.qgv_snapshot_id,), {"snapshot": old.to_dict()})
    before = content_hash(rec.to_dict())
    saved = deepcopy(rec.to_dict())
    changed_again = engine.analyze(raw.company_id, as_of, changed, synthetic=True)
    check("case5 immutable track record preserves historical payload",
          content_hash(store.get(rec.track_record_id).to_dict()) == before and
          saved["payload"]["snapshot"]["G_score"] == cases["B4-05"]["observed"]["old_G"] and
          changed_again.G_score == cases["B4-05"]["observed"]["new_synthetic_G"])
    check("case5 FactorObservation contains no method/version dispatch key",
          not any(field.name in {"method_id", "method_version", "calculation_ref"}
                  for field in fields(FactorObservation)))

    rejections = []
    for mutation in ({"method_identity": "attempt"}, {"method_version": "attempt"},
                     {"normalization_ref": "attempt"}):
        try:
            custom_profile(mutation)
        except ValueError as exc:
            rejections.append(str(exc))
    override_error = None
    try:
        WeightOverride("factor", 0.5, method_identity="attempt")
    except TypeError as exc:
        override_error = type(exc).__name__
    check("case6 supported custom_profile API rejects three method/normalization keys",
          rejections == cases["B4-06"]["observed"]["custom_profile_rejections"] and
          len(rejections) == 3)
    check("case6 WeightOverride is numeric weight only",
          override_error == "TypeError" and
          [field.name for field in fields(WeightOverride)] == ["node_id", "local_weight"])

    manifest = {
        "factor_ref": {"id": "G:next_3_5y_growth", "version": "SYNTHETIC_FACTOR_DEF"},
        "method_ref": {"id": "SYNTHETIC_CURRENT_PROXY", "version": "SYNTHETIC_V1"},
        "input_contract_ref": {"horizon": "SYNTHETIC_YOY"},
        "fallback_ref": {"ordered": ["SYNTHETIC_EPS", "SYNTHETIC_FCF_PRIOR_REVENUE"]},
        "normalization_ref": {"id": "SYNTHETIC_LEGACY_CLIP", "version": "SYNTHETIC_V1"},
        "namespace": "SANDBOX", "runtime_enabled": False,
    }
    for mutation in expected["method_manifest_hash_demonstration"]:
        key, value = mutation["changed_ref"], mutation["replacement"]
        alternative = deepcopy(manifest)
        alternative[key] = value
        check("synthetic binding fingerprint changes " + key + " " +
              json.dumps(value, sort_keys=True),
              content_hash(alternative) != content_hash(manifest))

    if checks != expected["checks"] or len(cases) != 6 or len(checks) != 17:
        raise AssertionError("B4 recorded characterization matrix changed")
    after = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in hashes}
    if after != hashes:
        raise AssertionError("Verifier changed protected bytes")
    return {"status": "PASS", "case_count": len(cases), "assertion_count": len(checks),
            "protected_hash_count": len(hashes), "source_golden_unchanged": True,
            "scope": "BOUNDED_LEGACY_CHARACTERIZATION_AND_INACTIVE_REFERENCE_FEASIBILITY",
            "runtime_enabled": False, "real_PIT_OOS": "NOT_RUN",
            "archived_executable_replay": "NOT_RUN",
            "recommendation_is_approval": False}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
