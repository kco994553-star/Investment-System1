"""C-21 runner hardening + offline gate chain. HTTP stubbed; proves wiring only, not data."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from investment_system.ingestion.raw_store import RawDatasetStore

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
AS_OF = "2024-12-31T00:00:00+00:00"


def _mod(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _R:
    def __init__(self, body, status=200):
        self.body, self.status, self.headers = body, status, {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_runner_retries_transient_429_then_succeeds(tmp_path, monkeypatch):
    mod = _mod("frd_retry", "fetch_real_data.py")
    calls, sleeps = [], []

    def fake(req, timeout=0):
        calls.append(req.full_url)
        if len(calls) < 3:
            raise mod.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
        return _R(b"{}")

    monkeypatch.setattr(mod, "urlopen", fake)
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
    rep = mod.run(Path(tmp_path), [], [], "5y", 0.0, skip_tickers=False)
    assert rep["n_ok"] == 1 and len(calls) == 3
    assert sleeps[:2] == [2.0, 4.0]  # exponential backoff


def test_runner_does_not_retry_origin_404(tmp_path, monkeypatch):
    mod = _mod("frd_404", "fetch_real_data.py")
    calls = []

    def fake(req, timeout=0):
        calls.append(1)
        raise mod.HTTPError(req.full_url, 404, "nf", {}, None)

    monkeypatch.setattr(mod, "urlopen", fake)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    rep = mod.run(Path(tmp_path), [], [], "5y", 0.0, skip_tickers=False)
    assert rep["log"][0]["status"] == "HTTP_404" and len(calls) == 1


def test_runner_egress_denial_is_not_retried_and_trips_per_host_breaker(tmp_path, monkeypatch):
    mod = _mod("frd_egress", "fetch_real_data.py")
    hosts = []

    def fake(req, timeout=0):
        hosts.append(req.host)
        raise mod.URLError(OSError("Tunnel connection failed: 403 Forbidden"))

    monkeypatch.setattr(mod, "urlopen", fake)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    rep = mod.run(Path(tmp_path), ["320193", "1045810"], ["AAPL", "NVDA"], "5y", 0.0, skip_tickers=False)
    # one request per host, then breaker: www.sec.gov, data.sec.gov, query1.finance.yahoo.com
    assert sorted(set(hosts)) == sorted(hosts) and len(hosts) == 3
    assert rep["n_ok"] == 0 and all(r["status"] == "EGRESS_BLOCKED" for r in rep["log"])
    assert set(rep["egress_blocked_hosts"]) == {"www.sec.gov", "data.sec.gov", "query1.finance.yahoo.com"}
    index = json.loads((Path(tmp_path) / "STORE_INDEX.json").read_text())
    assert index["n_artifacts"] == 0


def test_runner_plan_mode_resolves_missing_cik_from_stored_tickers_and_skips_present(tmp_path, monkeypatch):
    mod = _mod("frd_plan", "fetch_real_data.py")
    store = RawDatasetStore(tmp_path)
    tickers = {"0": {"cik_str": 16732, "ticker": "CPB", "title": "Campbell"},
               "1": {"cik_str": 1067983, "ticker": "BRK-B", "title": "Berkshire"}}
    store.put("sec_tickers", json.dumps(tickers).encode(), "u", "SEC_TICKERS", "application/json", "t", 200)
    plan = {"priority_fetch_plan": [{"ticker": "BRK.B", "cik": "0001067983"}, {"ticker": "CPB", "cik": None},
                                    {"ticker": "ANSS", "cik": None}]}
    fetched = []
    monkeypatch.setattr(mod, "urlopen", lambda req, timeout=0: (fetched.append(req.full_url), _R(b"{}"))[1])
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    rep = mod.run(Path(tmp_path), [], [], "5y", 0.0, skip_tickers=False, plan=plan)
    res = {r["ticker"]: r for r in rep["plan_resolution"]}
    assert res["CPB"]["method"] == "SEC_TICKERS_CURRENT" and res["CPB"]["cik"] == "0000016732"
    assert res["ANSS"]["method"] == "UNRESOLVED" and res["ANSS"]["cik"] is None
    ids = set(store.list_ids())
    assert {"companyfacts:0001067983", "companyfacts:0000016732", "yahoo_chart:BRK-B:5y", "yahoo_chart:ANSS:5y"} <= ids
    assert mod.SEC_TICKERS_URL not in fetched  # already in store -> resume, no re-download
    assert json.loads((Path(tmp_path) / "STORE_INDEX.json").read_text())["n_artifacts"] == len(ids)


def _put_name(store, cik, sym, shares, px):
    cf = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{"filed": "2024-11-01", "val": shares}]}}}}}
    store.put(f"companyfacts:{str(cik).zfill(10)}", json.dumps(cf).encode(), "u", "SEC", "application/json", "t", 200)
    chart = {"chart": {"result": [{"timestamp": [int(datetime(2024, 12, 1, tzinfo=UTC).timestamp())],
                                   "indicators": {"quote": [{"close": [px]}]}}], "error": None}}
    store.put(f"yahoo_chart:{sym}:5y", json.dumps(chart).encode(), "u", "YAHOO", "application/json", "t", 200)


def test_reference_coverage_matches_share_class_dot_and_dash(tmp_path):
    amc = _mod("amc_norm", "audit_mcap_store.py")
    store = RawDatasetStore(tmp_path)
    _put_name(store, 1067983, "BRK-B", 100, 10.0)
    listings = {"brk": {"cik": "0001067983", "yahoo": "BRK-B"}}
    ref = {"name": "SP", "source": "s", "source_vintage": "v", "as_of": AS_OF, "members": ["BRK.B", "ZZZ"]}
    out = amc.evaluate_reference_coverage(store, listings, set(), ref)
    assert out["missing_from_pool"] == ["ZZZ"]
    assert out["present_rankable_outside_top500"] == ["BRK.B"]
    assert amc.evaluate_reference_coverage(store, listings, {"BRK-B"}, ref)["present_rankable_outside_top500"] == []


def test_sufficiency_gate_detector_reference_alone_cannot_pass():
    amc = _mod("amc_det", "audit_mcap_store.py")
    audit = {"as_of": AS_OF, "rankable": 600, "top_cutoff_mcap_if_500_rankable": 1e9}
    clean = {"name": "SP", "source": "s", "source_vintage": "v", "as_of": AS_OF, "membership_basis": "DATED_INTERVALS",
             "members": ["A"], "missing_from_pool": [], "present_not_rankable": [], "present_rankable_outside_top500": []}
    g = amc.build_top500_sufficiency_gate(audit, [{**clean, "reference_role": "MISSING_LARGE_CAP_DETECTOR"}])
    assert g["passed"] is False and "ONLY_DETECTOR_REFERENCES_PASSED" in g["reasons"]
    assert amc.build_top500_sufficiency_gate(audit, [clean])["passed"] is True  # unchanged legacy behaviour


def test_ranked_top500_cutoff_agrees_with_audit(tmp_path):
    amc = _mod("amc_rank", "audit_mcap_store.py")
    store = RawDatasetStore(tmp_path)
    listings = {}
    for i in range(1, 506):
        _put_name(store, i, f"T{i}", i * 10, 1.0)
        listings[f"c{i}"] = {"cik": str(i).zfill(10), "yahoo": f"T{i}"}
    d = amc._dt(AS_OF)
    top = amc.ranked_top500(store, listings, d)
    audit = amc.audit(store, listings, d)
    assert len(top) == 500 and top[0]["yahoo"] == "T505" and top[-1]["rank"] == 500
    assert top[-1]["mcap"] == audit["top_cutoff_mcap_if_500_rankable"] == 60.0


def test_gate_chain_fails_closed_on_empty_store(tmp_path):
    chain = _mod("chain_empty", "run_top500_gate_chain.py")
    ref = {"name": "SP", "source": "s", "source_vintage": "v", "as_of": AS_OF, "membership_basis": "DATED_INTERVALS",
           "members": ["AAA", "BBB"]}
    rep = chain.run_chain(RawDatasetStore(tmp_path), {"a": {"cik": "1", "yahoo": "AAA"}}, "2024-12-31", [ref], [], None, None)
    assert rep["store"]["status"] == "EMPTY_NO_RAW_DATA" and rep["rankable"] == 0 and rep["cutoff_500_mcap"] is None
    assert rep["promotion_gate_v2"]["passed"] is False and rep["official_top500_declared"] is False
    assert rep["walk_forward"] == "NOT_RUN_GATE_V2_FAILED" and rep["real_data_verified"] is False
    assert rep["reference_coverage"][0]["missing_from_pool"] == ["BBB"]


def test_gate_chain_with_full_detector_coverage_still_not_official(tmp_path):
    chain = _mod("chain_full", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    listings = {}
    for i in range(1, 521):
        _put_name(store, i, f"T{i}", i * 10, 1.0)
        listings[f"c{i}"] = {"cik": str(i).zfill(10), "yahoo": f"T{i}"}
    ref = {"name": "SP", "source": "s", "source_vintage": "v", "as_of": AS_OF, "membership_basis": "DATED_INTERVALS",
           "members": [f"T{i}" for i in range(21, 521)]}
    ev = {"source": "x", "source_vintage": "v", "as_of": AS_OF, "eligibility_complete": False}
    rep = chain.run_chain(store, listings, "2024-12-31", [ref], [], None, ev)
    assert rep["rankable"] == 520 and rep["cutoff_500_mcap"] == 210.0
    assert rep["reference_coverage"][0]["n_missing_from_pool"] == 0
    assert "ONLY_DETECTOR_REFERENCES_PASSED" in rep["top500_sufficiency_gate"]["reasons"]
    assert rep["official_top500_declared"] is False


def test_company_level_ranking_one_line_per_cik(tmp_path):
    """Preferred / extra lines of one issuer must not occupy separate Top-500 slots."""
    chain = _mod("chain_dedupe", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    listings = {}
    for i in range(1, 501):
        _put_name(store, i, f"T{i}", i * 10, 1.0)
        listings[f"c{i}"] = {"cik": str(i).zfill(10), "yahoo": f"T{i}"}
    # issuer 9999: common BIG + preferred BIG-PA priced 25 on the same total shares
    _put_name(store, 9999, "BIG", 1_000_000, 100.0)
    chart = {"chart": {"result": [{"timestamp": [int(datetime(2024, 12, 1, tzinfo=UTC).timestamp())],
                                   "indicators": {"quote": [{"close": [25.0]}]}}], "error": None}}
    store.put("yahoo_chart:BIG-PA:5y", json.dumps(chart).encode(), "u", "YAHOO", "application/json", "t", 200)
    store.put("submissions:0000009999", json.dumps({"tickers": ["BIG", "BIG-PA"]}).encode(), "u", "SEC", "application/json", "t", 200)
    listings["big"] = {"cik": "0000009999", "yahoo": "BIG"}
    listings["big_pa"] = {"cik": "0000009999", "yahoo": "BIG-PA"}
    ref = {"name": "SP", "source": "s", "source_vintage": "v", "as_of": AS_OF, "membership_basis": "DATED_INTERVALS",
           "members": ["BIG", "BIG-PA"]}
    rep = chain.run_chain(store, listings, "2024-12-31", [ref], [], None, None)
    assert rep["row_level_audit"]["rankable"] == 502 and rep["rankable"] == 501
    assert rep["company_dedupe"]["methods"]["SEC_SUBMISSIONS_PRIMARY"] == 1
    assert rep["company_dedupe"]["multi_line_issuers"] == [{"cik": "0000009999", "kept": "BIG", "dropped": ["BIG-PA"]}]
    syms = [r["yahoo"] for r in rep["top500"]]
    assert "BIG" in syms and "BIG-PA" not in syms and len(syms) == 500
    assert rep["cutoff_500_mcap"] == 20.0  # T1 (10) dropped; row-level would have dropped T1 and T2
    cov = rep["reference_coverage"][0]
    assert cov["n_missing_from_pool"] == 0 and cov["n_present_rankable_outside_top500"] == 0  # BIG-PA = same ranked issuer


def test_cik_candidates_accepted_only_after_sec_name_verification(tmp_path):
    chain = _mod("chain_cand", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    store.put("submissions:0001013462", json.dumps({"name": "ANSYS INC"}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put("submissions:0000000777", json.dumps({"name": "SOMETHING ELSE", "formerNames": [{"name": "OTHER"}]}).encode(), "u", "SEC", "application/json", "t", 200)
    cands = {"candidates": [{"ticker": "ANSS", "cik": "1013462", "expect_name_tokens": ["ANSYS"]},
                            {"ticker": "BAD", "cik": "777", "expect_name_tokens": ["HOLOGIC"]},
                            {"ticker": "GONE", "cik": "888", "expect_name_tokens": ["X"]}]}
    v = chain.verify_cik_candidates(store, cands)
    assert v["ANSS"]["verified"] and v["ANSS"]["cik"] == "0001013462"
    assert v["BAD"]["status"] == "NAME_MISMATCH" and v["GONE"]["status"] == "SUBMISSIONS_NOT_IN_STORE"
    plan = {"priority_fetch_plan": [{"ticker": "ANSS", "cik": None}, {"ticker": "BAD", "cik": None}]}
    out, unresolved = chain.extend_listings(store, {}, plan, v)
    assert out["plan:anss"]["cik"] == "0001013462" and unresolved == ["BAD"]
