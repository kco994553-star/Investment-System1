"""Read-only V/Q/G characterization; output is stdout JSON, never a source write.

Run with PYTHONDONTWRITEBYTECODE=1 python v_verify.py /path/to/exact/repository
and keep any redirected result outside that repository. No pytest dependency.
"""
import hashlib
import importlib
import inspect
import json
import math
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(root / "implementation/src"), str(root / "implementation")]
from investment_system.contracts.enums import CoverageState, ProfileKind, QualityState
from investment_system.contracts.models import DataStamp
from investment_system.contracts.raw import RawFundamentals
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.raw_map import map_raw, _central_value_score, _mos_score
from investment_system.qgv.scoring import score_v_prior, score_v_candidates
from tests.helpers import AS_OF, complete_obs

files = [p for p in subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0") if p]
def digest():
    h = hashlib.sha256()
    for p in files:
        h.update(p.encode() + b"\0" + hashlib.sha256((root / p).read_bytes()).digest())
    return h.hexdigest()
before = digest()
checks = []
def record(name, condition, observed):
    if not condition:
        raise AssertionError((name, observed))
    checks.append({"id": name, "pass": True, "observed": observed})
base = complete_obs()
p, c, _ = score_v_prior(base, ProfileKind.GENERAL_CORPORATE)
record("C01", p == 70 and c == CoverageState.READY, [p, c.value])
cs = score_v_candidates(base)
record("C02", all(x.v_score == 70 for x in cs), {x.candidate_id: x.v_score for x in cs})
missing = dict(base); del missing["fundamental_value"]
p, c, _ = score_v_prior(missing, ProfileKind.GENERAL_CORPORATE)
record("C03", p == 52.5 and c == CoverageState.PARTIAL, [p, c.value])
record("C04", all(x.v_score is None for x in score_v_candidates(missing)), "all candidate scores null")
s = AnalysisEngine().analyze("nvda", AS_OF, missing)
record("C05", s.coverage_state == CoverageState.READY and s.factor_breakdown["v_coverage"] == "PARTIAL", [s.coverage_state.value, s.factor_breakdown["v_coverage"], s.V_score])
na = dict(base); na["fundamental_value"] = replace(na["fundamental_value"], quality=QualityState.NOT_APPLICABLE)
p, c, _ = score_v_prior(na, ProfileKind.GENERAL_CORPORATE)
record("C06", p == 52.5 and c == CoverageState.PARTIAL, [p, c.value])
record("C07", all(x.v_score == 70 for x in score_v_candidates(na)), "all candidate scores 70")
pit = dict(base); pit["fundamental_value"] = replace(pit["fundamental_value"], quality=QualityState.PIT_UNAVAILABLE)
s = AnalysisEngine().analyze("nvda", AS_OF, pit)
t = next(x for x in s.factor_breakdown["v_factor_table"] if x["factor_id"] == "fundamental_value")
record("C08", s.V_score == 52.5 and t["effective_weight"] == .25, t)
record("C09", t["confidence"] == t["coverage"] == "PIT_UNAVAILABLE", [t["confidence"], t["coverage"]])
changed = dict(base); changed["fundamental_value"] = replace(changed["fundamental_value"], score_0_100=100)
a = AnalysisEngine().analyze("nvda", AS_OF, base); b = AnalysisEngine().analyze("nvda", AS_OF, changed)
record("C10", a.total_score == b.total_score == 70 and a.V_score != b.V_score, [a.V_score, b.V_score, a.total_score, b.total_score])
stamp = DataStamp("v-review-synthetic", "synthetic", "fundamentals", "synthetic-only", AS_OF, AS_OF, AS_OF, synthetic=True)
r = RawFundamentals("nvda", stamp, dcf_value=120, price=100, eps=5, revenue=120, revenue_prev=100, own_multiple=20, peer_median_multiple=20, hist_valuation_percentile=60, sector_context_score=70, theme_premium_score=70, reverse_dcf_implied_growth=.1)
o = map_raw(r)
record("C11", o["fundamental_value"].raw_value == o["fundamental_value"].score_0_100 == 75, [o["fundamental_value"].raw_value, o["fundamental_value"].score_0_100])
record("C12", _central_value_score(r) != _mos_score(r), [_central_value_score(r), _mos_score(r)])
lo = map_raw(replace(r, hist_valuation_percentile=10))["historical_valuation"].score_0_100
hi = map_raw(replace(r, hist_valuation_percentile=90))["historical_valuation"].score_0_100
record("C13", lo == 10 and hi == 90, [lo, hi])
outlier = map_raw(replace(r, theme_premium_score=1000))["theme_premium_discount"].score_0_100
record("C14", outlier == 1000, outlier)
negative = map_raw(replace(r, peer_median_multiple=-20, own_multiple=10))["peer_relative_value"].score_0_100
record("C15", negative == 100, negative)
z = map_raw(replace(r, own_multiple=0))["peer_relative_value"]
record("C16", z.score_0_100 is None and z.quality == QualityState.MISSING_DATA, z.quality.value)
a = map_raw(replace(r, reverse_dcf_implied_growth=.1)); b = map_raw(replace(r, reverse_dcf_implied_growth=.3))
record("C17", all(a[f] == b[f] for f in ("next_3_5y_growth", "revenue_growth", "eps_fcf_per_share_growth")), [a["reverse_dcf"].score_0_100, b["reverse_dcf"].score_0_100])
o = map_raw(replace(r, dcf_value=None, reverse_dcf_implied_growth=None))
record("C19", o["fundamental_value"].score_0_100 == 50 and o["margin_of_safety"].score_0_100 == 0 and math.isclose(o["reverse_dcf"].score_0_100, 100), {f: o[f].score_0_100 for f in ("fundamental_value", "margin_of_safety", "reverse_dcf")})
fs = ("fundamental_value", "peer_relative_value", "historical_valuation", "sector_context", "theme_premium_discount", "reverse_dcf", "margin_of_safety")
record("C20", len({o[f].stamp_id for f in fs}) == 1, {f: o[f].stamp_id for f in fs})
record("C21", o["peer_relative_value"].score_0_100 == 50, 50)
text = (root / "implementation/src/investment_system/validation/historical.py").read_text()
line = "peer_med = sorted(peer_pes)[len(peer_pes) // 2] if peer_pes else None"
record("C22", line in text and sorted([10, 30])[2 // 2] == 30, "source-extracted upper middle 30; not full run_as_of execution")
reg = []
for name in ("tests.test_analysis_scoring", "tests.test_v_prior_and_c15", "tests.test_peer_derived_v", "tests.test_hist_peer_ablation_pit", "tests.test_v_coverage_matrix"):
    mod = importlib.import_module(name)
    for fname, fn in inspect.getmembers(mod, inspect.isfunction):
        if not fname.startswith("test_"):
            continue
        if "tmp_path" in inspect.signature(fn).parameters:
            with tempfile.TemporaryDirectory(prefix="v-audit-regression-") as temp:
                fn(tmp_path=Path(temp))
        else:
            fn()
        reg.append(name + "." + fname)
after = digest()
record("C18", before == after, {"tracked_files": len(files), "before": before, "after": after})
print(json.dumps({"input_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip(), "characterization_count": len(checks), "checks": checks, "existing_regression_count": len(reg), "existing_regressions_direct_execution": reg, "tracked_bytes_preserved": before == after, "production_policy_changed": False, "pytest_suite": "NOT_RUN", "scope": "LOCAL_SNAPSHOT_ONLY"}, indent=2))
