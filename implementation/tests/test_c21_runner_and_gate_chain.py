"""C-21 runner hardening + offline gate chain. HTTP stubbed; proves wiring only, not data."""
import importlib.util
import json
import sys
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
    assert rep["walk_forward"] == "NOT_RUN_OFFICIAL_BLOCKED" and rep["real_data_verified"] is False
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
    store.put("submissions:0000009999", json.dumps({"tickers": ["BIG", "BIG-PA"], "filings": {"recent": {
        "form": ["10-Q"], "filingDate": ["2024-11-01"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
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


def test_runner_does_not_throttle_skipped_artifacts(tmp_path, monkeypatch):
    mod = _mod("frd_throttle", "fetch_real_data.py")
    store = RawDatasetStore(tmp_path)
    store.put("sec_tickers", b"{}", "u", "SEC_TICKERS", "application/json", "t", 200)
    store.put("companyfacts:0000000001", b"{}", "u", "SEC", "application/json", "t", 200)
    sleeps = []
    monkeypatch.setattr(mod, "urlopen", lambda req, timeout=0: _R(b"{}"))
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
    mod.run(Path(tmp_path), ["1"], [], "5y", 0.15, skip_tickers=False)
    assert sleeps == [0.15]  # only submissions:0000000001 was actually requested


def _events(splits):
    return {"chart": {"result": [{"events": {"splits": {str(int(d.timestamp())): {"date": int(d.timestamp()), "numerator": n, "denominator": 1}
                                                        for d, n in splits}}}], "error": None}}


def test_mcap_price_uses_close_not_adjclose_and_undoes_later_splits(tmp_path):
    amc = _mod("amc_split", "audit_mcap_store.py")
    store = RawDatasetStore(tmp_path)
    d = amc._dt(AS_OF)
    bar = {"price": 76.0, "close": 80.0, "adjclose": 76.0}
    assert amc.mcap_price(bar, None, d) == 80.0  # dividend-adjusted adjclose is not a traded price
    store.put("yahoo_events:ORLY:5y", json.dumps(_events([(datetime(2025, 6, 10, tzinfo=UTC), 15),
                                                          (datetime(2020, 1, 2, tzinfo=UTC), 2)])).encode(),
              "u", "YAHOO", "application/json", "t", 200)
    splits = amc.load_splits(store, "ORLY")
    assert amc.split_factor_after(splits, d) == 15.0  # only the post-as_of split
    assert amc.mcap_price(bar, splits, d) == 1200.0
    assert amc.load_splits(store, "NONE") is None


def test_audit_applies_split_factor(tmp_path):
    amc = _mod("amc_split_audit", "audit_mcap_store.py")
    store = RawDatasetStore(tmp_path)
    _put_name(store, 1, "ORLY", 58_000_000, 80.0)
    store.put("yahoo_events:ORLY:5y", json.dumps(_events([(datetime(2025, 6, 10, tzinfo=UTC), 15)])).encode(),
              "u", "YAHOO", "application/json", "t", 200)
    top = amc.ranked_top500(store, {"o": {"cik": "1", "yahoo": "ORLY"}}, amc._dt(AS_OF))
    assert top[0]["mcap"] == 58_000_000 * 80.0 * 15


def test_foreign_private_issuer_is_excluded_by_eligibility_rule(tmp_path):
    chain = _mod("chain_fpi", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    store.put("submissions:0000000007", json.dumps({"filings": {"recent": {"form": ["20-F", "6-K"],
              "filingDate": ["2024-04-01", "2024-11-01"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    det = {"cik": "0000000007", "split_events": 0, "pit_filer_status": "FOREIGN"}
    assert chain.mcap_quality_flags(store, det) == ["FOREIGN_ISSUER_ADR_RATIO_UNRESOLVED"]
    assert chain.mcap_quality_flags(store, {"cik": "0000000008", "split_events": "MISSING"}) == ["SPLIT_EVENTS_MISSING"]
    _put_name(store, 7, "ADRX", 1000, 5.0)
    rep = chain.run_chain(store, {"x": {"cik": "0000000007", "yahoo": "ADRX"}}, "2024-12-31", [], [], None, None)
    # user decision 2026-09-25: foreign private issuers (20-F/40-F, no 10-K/10-Q) are not in the US Top 500
    assert rep["eligibility"]["excluded_foreign_private_issuers"] == ["ADRX"] and rep["top500"] == []
    assert rep["official_top500_declared"] is False


def test_runner_with_split_events_writes_events_artifact(tmp_path, monkeypatch):
    mod = _mod("frd_events", "fetch_real_data.py")
    urls = []
    monkeypatch.setattr(mod, "urlopen", lambda req, timeout=0: (urls.append(req.full_url), _R(b"{}"))[1])
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    mod.run(Path(tmp_path), [], ["ORLY"], "5y", 0.0, skip_tickers=True, with_split_events=True)
    assert set(RawDatasetStore(tmp_path).list_ids()) == {"yahoo_chart:ORLY:5y", "yahoo_events:ORLY:5y"}
    assert any("events=split" in u for u in urls)


def _instance(classes, symbols, titles=()):
    """classes: [(member|None, shares)], symbols: [(member|None, sym)], titles: [(member|None, text)]."""
    ctx, facts, i = [], [], 0
    def c(member, instant):
        nonlocal i
        i += 1
        seg = (f'<xbrli:segment><xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">us-gaap:{member}'
               f'</xbrldi:explicitMember></xbrli:segment>') if member else ""
        per = f"<xbrli:instant>{instant}</xbrli:instant>" if instant else "<xbrli:startDate>2024-07-01</xbrli:startDate><xbrli:endDate>2024-09-30</xbrli:endDate>"
        ctx.append(f'<xbrli:context id="c{i}"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier>{seg}</xbrli:entity><xbrli:period>{per}</xbrli:period></xbrli:context>')
        return f"c{i}"
    for m, sh in classes:
        facts.append(f'<dei:EntityCommonStockSharesOutstanding contextRef="{c(m, "2024-10-25")}" unitRef="shares">{sh}</dei:EntityCommonStockSharesOutstanding>')
    for m, sym in symbols:
        facts.append(f'<dei:TradingSymbol contextRef="{c(m, None)}">{sym}</dei:TradingSymbol>')
    for m, t in titles:
        facts.append(f'<dei:Security12bTitle contextRef="{c(m, None)}">{t}</dei:Security12bTitle>')
    return ('<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
            'xmlns:dei="http://xbrl.sec.gov/dei/2024" xmlns:us-gaap="http://fasb.org/us-gaap/2024">'
            + "".join(ctx) + "".join(facts) + "</xbrli:xbrl>").encode()


def test_cover_parser_maps_classes_to_symbols():
    from investment_system.providers.sec_cover_shares import class_symbols, parse_cover
    brk = parse_cover(_instance([("CommonClassAMember", 591), ("CommonClassBMember", 1_300_000)],
                                [("CommonClassAMember", "BRK.A"), ("CommonClassBMember", "BRK.B")]))
    assert class_symbols(brk) == {"CommonClassAMember": "BRK.A", "CommonClassBMember": "BRK.B"}
    meta = parse_cover(_instance([("CommonClassAMember", 2_180), ("CommonClassBMember", 344)], [(None, "META")],
                                 [(None, "Class A Common Stock, $0.000006 par value")]))
    assert class_symbols(meta) == {"CommonClassAMember": "META"}  # class B unlisted -> unmapped
    amb = parse_cover(_instance([("CommonClassAMember", 1), ("CommonClassBMember", 2)], [(None, "X")], [(None, "Common Stock")]))
    assert class_symbols(amb) == {}  # no evidence which class trades -> fail-closed
    single = parse_cover(_instance([(None, 4_300)], [(None, "XOM")]))
    assert single["classes"][0]["shares"] == 4_300 and class_symbols(single) == {None: "XOM"}


def test_select_filing_latest_periodic_on_or_before_as_of():
    from investment_system.providers.sec_cover_shares import instance_name, select_filing
    sub = {"filings": {"recent": {"form": ["8-K", "10-Q", "10-Q", "10-K"], "filingDate": ["2024-12-20", "2024-10-30", "2025-04-30", "2024-02-01"],
                                  "accessionNumber": ["a", "b", "c", "d"], "primaryDocument": ["x.htm", "q3.htm", "q1.htm", "k.htm"]}}}
    f = select_filing(sub, amc_dt())
    assert f["accn"] == "b" and instance_name(f["primary_document"]) == "q3_htm.xml"


def amc_dt():
    return datetime(2024, 12, 31, tzinfo=UTC)


def _sub_with_filing(store, cik10, accn="0000000000-24-000001"):
    store.put(f"submissions:{cik10}", json.dumps({"tickers": [], "filings": {"recent": {"form": ["10-Q"], "filingDate": ["2024-10-30"],
              "accessionNumber": [accn], "primaryDocument": ["q.htm"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    return f"xbrl_instance:{cik10}:{accn}"


def test_chain_class_sum_full_and_lower_bound(tmp_path):
    chain = _mod("chain_cover", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    # BRK-like: both classes listed -> exact sum
    _put_name(store, 1067983, "BRK-B", 1, 450.0)
    _put_name(store, 1067984, "BRK-A", 1, 680_000.0)  # chart for BRK-A (companyfacts id unused)
    aid = _sub_with_filing(store, "0001067983")
    store.put(aid, _instance([("CommonClassAMember", 600), ("CommonClassBMember", 1_300_000)],
                             [("CommonClassAMember", "BRK.A"), ("CommonClassBMember", "BRK.B")]), "u", "SEC", "application/xml", "t", 200)
    # META-like: class B unlisted -> lower bound
    _put_name(store, 1326801, "META", 1, 585.0)
    aid2 = _sub_with_filing(store, "0001326801")
    store.put(aid2, _instance([("CommonClassAMember", 2_180), ("CommonClassBMember", 344)], [(None, "META")],
                              [(None, "Class A Common Stock")]), "u", "SEC", "application/xml", "t", 200)
    listings = {"brk": {"cik": "0001067983", "yahoo": "BRK-B"}, "meta": {"cik": "0001326801", "yahoo": "META"}}
    rep = chain.run_chain(store, listings, "2024-12-31", [], [], None, None)
    ov = rep["cover_overrides"]
    assert ov["BRK-B"]["status"] == "COVER_CLASS_SUM" and ov["BRK-B"]["mcap"] == 600 * 680_000.0 + 1_300_000 * 450.0
    assert ov["META"]["status"] == "COVER_CLASS_SUM_LOWER_BOUND" and ov["META"]["mcap"] == 2_180 * 585.0
    row = next(r for r in rep["top500"] if r["yahoo"] == "META")
    assert row["notes"] == ["RANK_IS_LOWER_BOUND"] and rep["lower_bound_issuers_outside_top500"] == []


def test_lower_bound_issuer_outside_top500_blocks_official(tmp_path):
    chain = _mod("chain_lb", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    listings = {}
    for i in range(1, 501):
        _put_name(store, i, f"T{i}", 1000, 10.0 + i)
        listings[f"c{i}"] = {"cik": str(i).zfill(10), "yahoo": f"T{i}"}
    _put_name(store, 777777, "LOWB", 1, 1.0)
    aid = _sub_with_filing(store, "0000777777")
    store.put(aid, _instance([("CommonClassAMember", 5), ("CommonClassBMember", 10**9)], [(None, "LOWB")], [(None, "Class A Common Stock")]),
              "u", "SEC", "application/xml", "t", 200)
    listings["lowb"] = {"cik": "0000777777", "yahoo": "LOWB"}
    rep = chain.run_chain(store, listings, "2024-12-31", [], [], None, None)
    assert rep["lower_bound_issuers_outside_top500"] == ["LOWB"]
    assert "LOWER_BOUND_ISSUERS_OUTSIDE_TOP500" in rep["official_blockers"]


def test_fetch_cover_xbrl_selects_issuers_and_fetches_instance_and_class_prices(tmp_path, monkeypatch):
    fcx = _mod("fcx", "fetch_cover_xbrl.py")
    store = RawDatasetStore(tmp_path)
    store.put("companyfacts:0001067983", b'{"facts": {}}', "u", "SEC", "application/json", "t", 200)  # shares missing
    _sub_with_filing(store, "0001067983", "0000950170-24-000001")
    _put_name(store, 5, "SOLO", 10, 1.0)  # single line, shares OK -> not needed
    rows = {"a": {"cik": "0001067983", "yahoo": "BRK-B"}, "s": {"cik": "5", "yahoo": "SOLO"}}
    need = fcx.needs_cover(store, rows, amc_dt())
    assert need == ["0001067983"]
    inst = _instance([("CommonClassAMember", 600), ("CommonClassBMember", 1_300_000)],
                     [("CommonClassAMember", "BRK.A"), ("CommonClassBMember", "BRK.B")])
    urls = []

    def fake(req, timeout=0):
        urls.append(req.full_url)
        return _R(inst if req.full_url.endswith("_htm.xml") else b"{}")

    frd = fcx._load("fetch_real_data")
    monkeypatch.setattr(fcx, "_load", lambda name: frd)
    monkeypatch.setattr(frd, "urlopen", fake)
    monkeypatch.setattr(frd.time, "sleep", lambda s: None)
    rep = fcx.run(Path(tmp_path), amc_dt(), need)
    assert "https://www.sec.gov/Archives/edgar/data/1067983/000095017024000001/q_htm.xml" in urls
    ids = set(store.list_ids())
    assert "xbrl_instance:0001067983:0000950170-24-000001" in ids
    assert {"yahoo_chart:BRK-A:5y", "yahoo_chart:BRK-B:5y", "yahoo_events:BRK-A:5y"} <= ids
    assert rep["n_class_symbols"] == 2 and rep["n_failed"] == 0


def test_class_symbols_ignore_preferred_series_without_shares():
    from investment_system.providers.sec_cover_shares import class_symbols, parse_cover
    cov = parse_cover(_instance([("CommonStockMember", 265)],
                                [("CommonStockMember", "ALL"), ("SeriesHPreferredStockMember", "ALL PR H")]))
    assert class_symbols(cov) == {"CommonStockMember": "ALL"}


def test_runner_invalid_url_is_a_logged_artifact_failure_not_a_crash(tmp_path, monkeypatch):
    import http.client
    mod = _mod("frd_badurl", "fetch_real_data.py")

    def fake(req, timeout=0):
        if " " in req.full_url:
            raise http.client.InvalidURL("URL can't contain control characters")
        return _R(b"{}")

    monkeypatch.setattr(mod, "urlopen", fake)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    rep = mod.run(Path(tmp_path), [], ["ALL PR H", "ALL"], "5y", 0.0, skip_tickers=True)
    st = {r["artifact_id"]: r["status"] for r in rep["log"]}
    assert st["yahoo_chart:ALL PR H:5y"] == "ERROR_InvalidURL" and st["yahoo_chart:ALL:5y"] == "OK"


def test_class_symbols_single_dimensioned_class_and_plain_common_stock():
    from investment_system.providers.sec_cover_shares import class_symbols, parse_cover
    hrl = parse_cover(_instance([("CommonStockMember", 548_000_000)], [(None, "HRL")]))
    assert class_symbols(hrl) == {"CommonStockMember": "HRL"}
    ford = parse_cover(_instance([("CommonStockMember", 3_900_000_000), ("CommonClassBMember", 70_000_000)], [(None, "F")],
                                 [(None, "Common Stock, par value $.01 per share")]))
    assert class_symbols(ford) == {"CommonStockMember": "F"}  # Class B unlisted -> lower bound later


def test_foreign_flag_matches_eligibility_rule_for_domestic_filers_with_20f_history(tmp_path):
    chain = _mod("chain_fflag", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    # CRH/ENB/NXPI pattern: 20-F history, 10-K by as_of -> domestic at as_of, no foreign flag
    store.put("submissions:0000000009", json.dumps({"filings": {"recent": {"form": ["10-K", "20-F"],
              "filingDate": ["2024-02-28", "2023-03-01"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    assert chain._filer_status(store, "0000000009", amc_dt()) == "DOMESTIC"
    assert chain.mcap_quality_flags(store, {"cik": "0000000009", "split_events": 0, "pit_filer_status": "DOMESTIC"}) == []


def test_pit_filer_status_uses_filings_on_or_before_as_of_not_todays_forms():
    from investment_system.providers.sec_cover_shares import pit_filer_status
    d = amc_dt()
    rec = lambda forms, dates: {"filings": {"recent": {"form": forms, "filingDate": dates}}}  # noqa: E731
    # BAM pattern: 40-F filer at as_of, became a 10-K filer in 2025 -> FOREIGN at 2024-12-31
    assert pit_filer_status(rec(["10-K", "10-Q", "40-F"], ["2026-02-20", "2025-05-01", "2024-03-15"]), d) == "FOREIGN"
    # SNDK/HONA pattern: first filing after as_of -> not a registrant at as_of
    assert pit_filer_status(rec(["10-K", "10-12B"], ["2025-08-01", "2025-02-01"]), d) == "NOT_REGISTERED_AT_AS_OF"
    # large bank pattern: recent starts after as_of and older pages are not in the store -> UNKNOWN (never guessed)
    assert pit_filer_status(rec(["424B2"], ["2025-06-01"]), d, pages_complete=False) == "UNKNOWN"
    # IPO with only a registration statement by as_of -> UNKNOWN
    assert pit_filer_status(rec(["S-1", "424B4"], ["2024-10-01", "2024-11-20"]), d) == "UNKNOWN"


def test_merged_submissions_pages_resolve_filings_before_as_of(tmp_path):
    from investment_system.ingestion.replay import load_submissions_merged
    from investment_system.providers.sec_cover_shares import pages_needed, pit_filer_status, select_filing
    store = RawDatasetStore(tmp_path)
    sub = {"filings": {"recent": {"form": ["424B2"], "filingDate": ["2025-06-01"], "accessionNumber": ["x"], "primaryDocument": ["p.htm"]},
                       "files": [{"name": "CIK0000019617-submissions-001.json", "filingFrom": "2023-01-01", "filingTo": "2025-05-31"}]}}
    store.put("submissions:0000019617", json.dumps(sub).encode(), "u", "SEC", "application/json", "t", 200)
    assert pages_needed(sub, amc_dt()) == ["CIK0000019617-submissions-001.json"]
    merged, complete = load_submissions_merged(store, "19617")
    assert complete is False and pit_filer_status(merged, amc_dt(), complete) == "UNKNOWN"
    page = {"form": ["10-Q", "424B2"], "filingDate": ["2024-11-04", "2024-12-20"], "accessionNumber": ["a", "b"], "primaryDocument": ["q.htm", "s.htm"]}
    store.put("submissions_page:CIK0000019617-submissions-001.json", json.dumps(page).encode(), "u", "SEC", "application/json", "t", 200)
    merged, complete = load_submissions_merged(store, "19617")
    assert complete and pit_filer_status(merged, amc_dt(), complete) == "DOMESTIC"
    assert select_filing(merged, amc_dt())["accn"] == "a"


def test_pit_cik_replacement_only_after_verification(tmp_path):
    chain = _mod("chain_pitcik", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    store.put("submissions:0000034088", json.dumps({"name": "EXXON MOBIL CORP"}).encode(), "u", "SEC", "application/json", "t", 200)
    cands = {"candidates": [{"ticker": "XOM", "cik": "0000034088", "expect_name_tokens": ["EXXON MOBIL"], "replaces_current_cik": True},
                            {"ticker": "PSKY", "cik": "0000813828", "expect_name_tokens": ["PARAMOUNT GLOBAL"], "replaces_current_cik": True}]}
    v = chain.verify_cik_candidates(store, cands)
    rows, _ = chain.extend_listings(store, {"xom": {"yahoo": "XOM", "cik": "0002115436"}, "psky": {"yahoo": "PSKY", "cik": "0002041610"}}, None, v)
    assert rows["xom"]["cik"] == "0000034088" and rows["xom"]["cik_replaced_from"] == "0002115436"
    assert rows["psky"]["cik"] == "0002041610"  # candidate not verified (no submissions in store) -> unchanged


def test_pit_cik_replacement_also_applies_to_plan_added_names(tmp_path):
    chain = _mod("chain_pitplan", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    store.put("submissions:0000813828", json.dumps({"name": "Paramount Global"}).encode(), "u", "SEC", "application/json", "t", 200)
    v = chain.verify_cik_candidates(store, {"candidates": [{"ticker": "PSKY", "cik": "0000813828",
                                                            "expect_name_tokens": ["PARAMOUNT GLOBAL"], "replaces_current_cik": True}]})
    rows, unresolved = chain.extend_listings(store, {}, {"priority_fetch_plan": [{"ticker": "PSKY", "cik": "0002041610"}]}, v)
    assert rows["plan:psky"]["cik"] == "0000813828" and unresolved == []


def test_chain_lists_unrankable_issuers_with_reason(tmp_path):
    chain = _mod("chain_unrank", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    _put_name(store, 1, "OKK", 10, 5.0)
    store.put("companyfacts:0000000002", b'{"facts": {}}', "u", "SEC", "application/json", "t", 200)  # no shares
    _put_name(store, 3, "NOPX", 10, 5.0)
    store.put("yahoo_chart:NOPX:5y", json.dumps({"chart": {"result": [{"timestamp": [int(datetime(2025, 3, 1, tzinfo=UTC).timestamp())],
              "indicators": {"quote": [{"close": [5.0]}]}}], "error": None}}).encode(), "u", "Y", "application/json", "t", 200)
    for c in ("0000000001", "0000000002", "0000000003"):  # domestic 10-Q filers at as_of
        store.put(f"submissions:{c}", json.dumps({"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2024-11-01"]}}}).encode(),
                  "u", "SEC", "application/json", "t", 200)
    rep = chain.run_chain(store, {"a": {"cik": "1", "yahoo": "OKK"}, "b": {"cik": "2", "yahoo": "NOSH"},
                                  "c": {"cik": "3", "yahoo": "NOPX"}}, "2024-12-31", [], [], None, None)
    assert {k: v["reason"] for k, v in rep["unrankable_issuers"].items()} == {"NOSH": "SHARES_MISSING", "NOPX": "NO_AS_OF_PRICE"}


def test_unknown_filer_without_as_of_price_is_not_listed_at_as_of(tmp_path):
    """SNDK pattern (run #17): Form 10 before as_of, first trade and first 10-Q in 2025."""
    chain = _mod("chain_nottrading", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    store.put("submissions:0002023554", json.dumps({"filings": {"recent": {"form": ["10-Q", "10-12B"],
              "filingDate": ["2025-05-01", "2024-12-10"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put("yahoo_chart:SNDK:5y", json.dumps({"chart": {"result": [{"timestamp": [int(datetime(2025, 2, 24, 14, 30, tzinfo=UTC).timestamp())],
              "indicators": {"quote": [{"close": [50.0]}]}}], "error": None}}).encode(), "u", "Y", "application/json", "t", 200)
    kept, rep = chain.eligibility_filter(store, {"s": {"cik": "0002023554", "yahoo": "SNDK"}}, amc_dt())
    assert kept == {} and rep["excluded_not_trading_at_as_of"] == ["SNDK"]


def test_fetch_submission_pages_requests_only_needed_pages(tmp_path, monkeypatch):
    fcx = _mod("fcx_pages", "fetch_cover_xbrl.py")
    store = RawDatasetStore(tmp_path)
    store.put("submissions:0000019617", json.dumps({"filings": {"recent": {"form": ["424B2"], "filingDate": ["2025-06-01"]},
              "files": [{"name": "CIK0000019617-submissions-001.json", "filingFrom": "2023-01-01"},
                        {"name": "CIK0000019617-submissions-002.json", "filingFrom": "2026-01-01"}]}}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put("submissions:0000000005", json.dumps({"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2024-11-01"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    urls = []
    frd = fcx._load("fetch_real_data")
    monkeypatch.setattr(fcx, "_load", lambda name: frd)
    monkeypatch.setattr(frd, "urlopen", lambda req, timeout=0: (urls.append(req.full_url), _R(b"{}"))[1])
    monkeypatch.setattr(frd.time, "sleep", lambda s: None)
    n = fcx.fetch_submission_pages(store, ["0000019617", "0000000005"], amc_dt(), [])
    assert n == 1 and urls == ["https://data.sec.gov/submissions/CIK0000019617-submissions-001.json"]
    assert store.has("submissions_page:CIK0000019617-submissions-001.json")


def test_pages_needed_when_recent_has_only_prospectuses_before_as_of_and_only_window_pages(tmp_path):
    """STT/DB pattern (run #16): 'recent' reaches back before as_of but only with 424B2/FWP filings."""
    from investment_system.ingestion.replay import load_submissions_merged
    from investment_system.providers.sec_cover_shares import pages_needed, pit_filer_status
    store = RawDatasetStore(tmp_path)
    sub = {"filings": {"recent": {"form": ["424B2", "FWP"], "filingDate": ["2025-01-10", "2024-12-15"]},
                       "files": [{"name": "CIK0000093751-submissions-001.json", "filingFrom": "2024-06-01", "filingTo": "2024-12-14"},
                                 {"name": "CIK0000093751-submissions-002.json", "filingFrom": "2019-01-01", "filingTo": "2022-12-31"}]}}
    assert pages_needed(sub, amc_dt()) == ["CIK0000093751-submissions-001.json"]  # 2019-22 page is outside the window
    store.put("submissions:0000093751", json.dumps(sub).encode(), "u", "SEC", "application/json", "t", 200)
    store.put("submissions_page:CIK0000093751-submissions-001.json", json.dumps({"form": ["10-Q"], "filingDate": ["2024-11-01"]}).encode(),
              "u", "SEC", "application/json", "t", 200)
    merged, complete = load_submissions_merged(store, "93751", amc_dt())
    assert complete is True  # the out-of-window page is not required
    assert pit_filer_status(merged, amc_dt(), complete) == "DOMESTIC"
    assert pages_needed({"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2024-11-01"]}}}, amc_dt()) == []


def test_zero_companyfacts_shares_needs_cover_and_cover_resolves_it(tmp_path):
    """CRWD/HOOD/DDOG/CVNA/PSKY/TAP pattern (run #16): companyfacts reports 0 undimensioned shares."""
    fcx = _mod("fcx_zero", "fetch_cover_xbrl.py")
    chain = _mod("chain_zero", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    _put_name(store, 1535527, "CRWD", 0, 350.0)  # companyfacts shares = 0
    assert fcx.needs_cover(store, {"c": {"cik": "0001535527", "yahoo": "CRWD"}}, amc_dt()) == ["0001535527"]
    aid = _sub_with_filing(store, "0001535527")
    store.put(aid, _instance([("CommonClassAMember", 240_000_000), ("CommonClassBMember", 5_000_000)], [(None, "CRWD")],
                             [(None, "Class A common stock")]), "u", "SEC", "application/xml", "t", 200)
    rep = chain.run_chain(store, {"c": {"cik": "0001535527", "yahoo": "CRWD"}}, "2024-12-31", [], [], None, None)
    o = rep["cover_overrides"]["CRWD"]
    assert o["status"] == "COVER_CLASS_SUM_LOWER_BOUND" and o["mcap"] == 240_000_000 * 350.0
    assert "CRWD" not in rep["unrankable_issuers"]


def test_reference_normalisation_uses_only_values_stated_in_the_file():
    chain = _mod("chain_norm", "run_top500_gate_chain.py")
    r = chain.normalize_reference({"kind": "SP500_PIT_RECONSTRUCTION", "as_of": "2024-12-31",
                                   "source": "Wikipedia list + dated changes table (fetched 2026-09-25)", "members": ["A"]})
    assert r["as_of"] == AS_OF and r["source_vintage"] == "2026-09-25" and r["name"] == "SP500_PIT_RECONSTRUCTION"
    assert chain.normalize_reference({"as_of": AS_OF, "source": "no date here"})["source_vintage"] is None


def _stooq_csv(rows):
    return ("Date,Open,High,Low,Close,Volume\n" + "".join(f"{d},1,1,1,{c},100\n" for d, c in rows)).encode()


def test_stooq_bars_are_stamped_after_the_close_no_lookahead():
    ibr = _mod("ibr_ts", "import_bulk_real_data.py")
    chart = json.loads(ibr._stooq_to_chart(_stooq_csv([("2024-12-30", 10.0), ("2024-12-31", 11.0)]), "X"))
    ts = chart["chart"]["result"][0]["timestamp"]
    assert datetime.fromtimestamp(ts[1], tz=UTC) == datetime(2024, 12, 31, 21, 0, tzinfo=UTC)
    fsp = _mod("fsp_ts", "fetch_stooq_prices.py")
    assert fsp.csv_close_on_or_before(_stooq_csv([("2024-12-30", 10.0), ("2024-12-31", 11.0)]), amc_dt()) == ("2024-12-30", 10.0)


def _yahoo_close(store, sym, close, day=30):
    chart = {"chart": {"result": [{"timestamp": [int(datetime(2024, 12, day, 14, 30, tzinfo=UTC).timestamp())],
                                   "indicators": {"quote": [{"close": [close]}]}}], "error": None}}
    store.put(f"yahoo_chart:{sym}:5y", json.dumps(chart).encode(), "u", "YAHOO_CHART", "application/json", "t", 200)


def _stooq_run(tmp_path, monkeypatch, control_close, targets, stooq_bodies):
    fsp = _mod("fsp_run_" + str(abs(hash((control_close, tuple(targets))))), "fetch_stooq_prices.py")
    store = RawDatasetStore(tmp_path)
    for c in fsp.CONTROLS:
        _yahoo_close(store, c, 100.0)
    frd = fsp._load("fetch_real_data")
    ibr = fsp._load("import_bulk_real_data")
    monkeypatch.setattr(fsp, "_load", lambda name: frd if name == "fetch_real_data" else ibr)

    def fake(req, timeout=0):
        sym = req.full_url.split("s=")[1].split(".us")[0].upper()
        if sym in stooq_bodies:
            return _R(stooq_bodies[sym])
        return _R(_stooq_csv([("2024-12-30", control_close)]))

    monkeypatch.setattr(frd, "urlopen", fake)
    monkeypatch.setattr(frd.time, "sleep", lambda s: None)
    return fsp, store, fsp.run(Path(tmp_path), amc_dt(), targets)


def test_stooq_fallback_written_only_after_calibration_and_only_without_yahoo_as_of_bar(tmp_path, monkeypatch):
    bodies = {"ANSS": _stooq_csv([("2024-12-30", 337.0), ("2025-07-10", 360.0)]), "AVB": _stooq_csv([("2024-12-30", 220.0)]),
              "NEWCO": _stooq_csv([("2025-03-01", 9.0)]), "JUNK": b"<html>captcha</html>"}
    fsp, store, rep = _stooq_run(tmp_path, monkeypatch, 100.2, ["ANSS", "AVB", "NEWCO", "JUNK"], bodies)
    assert rep["calibrated"] is True
    assert rep["results"]["ANSS"] == "WRITTEN_STOOQ_FALLBACK" and rep["results"]["AVB"] == "WRITTEN_STOOQ_FALLBACK"
    assert rep["results"]["NEWCO"] == "NO_STOOQ_BAR_ON_OR_BEFORE_AS_OF" and rep["results"]["JUNK"] == "NO_STOOQ_DATA"
    m = store.get_manifest("yahoo_chart:ANSS:5y")
    assert m["source_kind"] == "STOOQ_DAILY" and "stooq.com" in m["source_url"]
    assert [b["close"] for b in load_bars(store, "ANSS") if b["observed_at"] <= amc_dt()] == [337.0]


def load_bars(store, sym):
    from investment_system.ingestion.replay import load_price_bars
    return load_price_bars(store, sym, "5y")


def test_stooq_calibration_mismatch_writes_nothing(tmp_path, monkeypatch):
    bodies = {"ANSS": _stooq_csv([("2024-12-30", 337.0)])}
    fsp, store, rep = _stooq_run(tmp_path, monkeypatch, 97.0, ["ANSS"], bodies)  # 3 % off -> dividend-adjusted-like
    assert rep["calibrated"] is False and rep["results"]["ANSS"] == "NOT_WRITTEN_CALIBRATION_FAILED"
    assert not store.has("yahoo_chart:ANSS:5y") and store.has("stooq_csv:ANSS")


def test_stooq_never_overwrites_a_yahoo_as_of_bar(tmp_path, monkeypatch):
    fsp = _mod("fsp_keep", "fetch_stooq_prices.py")
    store = RawDatasetStore(tmp_path)
    _yahoo_close(store, "KEEP", 50.0)
    frd = fsp._load("fetch_real_data"); ibr = fsp._load("import_bulk_real_data")
    for c in fsp.CONTROLS:
        _yahoo_close(store, c, 100.0)
    monkeypatch.setattr(fsp, "_load", lambda name: frd if name == "fetch_real_data" else ibr)
    monkeypatch.setattr(frd, "urlopen", lambda req, timeout=0: _R(_stooq_csv([("2024-12-30", 100.0 if "keep" not in req.full_url else 51.0)])))
    monkeypatch.setattr(frd.time, "sleep", lambda s: None)
    rep = fsp.run(Path(tmp_path), amc_dt(), ["KEEP"])
    assert rep["results"]["KEEP"] == "YAHOO_AS_OF_BAR_PRESENT" and store.get_manifest("yahoo_chart:KEEP:5y")["source_kind"] == "YAHOO_CHART"


IWB_SAMPLE = ('iShares Russell 1000 ETF\nFund Holdings as of,"Dec 31, 2024"\nInception Date,"May 15, 2000"\n'
              'Shares Outstanding,"1,000"\n \nTicker,Name,Sector,Asset Class,Market Value,Weight (%),Notional Value,Quantity,Price,'
              'Location,Exchange,Currency,FX Rate,Market Currency,Accrual Date\n'
              '"AAPL","APPLE INC","Information Technology","Equity","1","6.5","1","1","250","United States","NASDAQ","USD","1","USD","-"\n'
              '"BRKB","BERKSHIRE HATHAWAY INC CLASS B","Financials","Equity","1","1.6","1","1","453","United States","New York Stock Exchange Inc.","USD","1","USD","-"\n'
              '"ANSS","ANSYS INC","Information Technology","Equity","1","0.1","1","1","337","United States","NASDAQ","USD","1","USD","-"\n'
              '"ZZZ","AMBIGUOUS CORP","Industrials","Equity","1","0.1","1","1","10","United States","NYSE","USD","1","USD","-"\n'
              '"USD","USD CASH","Cash and/or Derivatives","Cash","1","0.1","1","1","1","United States","-","USD","1","USD","-"\n').encode()


def test_ishares_holdings_parse_and_member_resolution(tmp_path):
    fir = _mod("fir", "fetch_ishares_reference.py")
    as_of, rows = fir.parse_holdings(IWB_SAMPLE)
    assert as_of == "2024-12-31" and [r["ticker"] for r in rows] == ["AAPL", "BRKB", "ANSS", "ZZZ"]  # cash row dropped
    store = RawDatasetStore(tmp_path)
    store.put("sec_tickers", json.dumps({"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple"}}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put("sec_cik_lookup", b"ANSYS INC:0001013462:\nAMBIGUOUS CORP:0000000011:\nAMBIGUOUS CORPORATION:0000000012:\n", "u", "SEC", "text/plain", "t", 200)
    ref, extra, res = fir.build(store, "2024-12-31", rows, {"BRK-B"}, "2026-09-25")
    assert res["IN_POOL"] == 1 and res["SEC_TICKERS_CURRENT"] == 1 and res["SEC_CIK_LOOKUP_UNIQUE_NAME"] == 1
    assert extra["r1000:anss"]["cik"] == "0001013462" and extra["r1000:aapl"]["cik"] == "0000320193"
    assert [u["ticker"] for u in res["UNRESOLVED"]] == ["ZZZ"]  # two CIKs for the same normalised name -> not guessed
    assert ref["reference_role"] == "SUPERSET_REFERENCE" and ref["as_of"] == AS_OF and ref["source_vintage"] == "2026-09-25"


def test_superset_reference_allows_ranks_below_500_but_not_missing_or_unrankable():
    amc = _mod("amc_superset", "audit_mcap_store.py")
    audit = {"as_of": AS_OF, "rankable": 600, "top_cutoff_mcap_if_500_rankable": 1e9}
    base = {"name": "R1000", "source": "iShares IWB", "source_vintage": "2026-09-25", "as_of": AS_OF,
            "membership_basis": "DATED_FUND_HOLDINGS", "reference_role": "SUPERSET_REFERENCE",
            "members": [f"T{i}" for i in range(1000)], "missing_from_pool": [], "present_not_rankable": [],
            "present_rankable_outside_top500": [f"T{i}" for i in range(500, 1000)]}
    assert amc.build_top500_sufficiency_gate(audit, [base])["passed"] is True
    bad = amc.build_top500_sufficiency_gate(audit, [{**base, "missing_from_pool": ["T7"]}])
    assert bad["passed"] is False and "MISSING_LARGE_CAP_NAMES" in bad["references"][0]["reasons"]
    small = amc.build_top500_sufficiency_gate(audit, [{**base, "members": ["T1"]}])
    assert "SUPERSET_REFERENCE_TOO_SMALL" in small["references"][0]["reasons"]


def test_chain_superset_maps_class_tickers_counts_rule_exclusions_and_derives_eligibility(tmp_path):
    chain = _mod("chain_superset", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    listings = {}
    for i in range(1, 511):
        _put_name(store, i, f"T{i}", i * 10, 1.0)
        store.put(f"submissions:{str(i).zfill(10)}", json.dumps({"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2024-11-01"]}}}).encode(),
                  "u", "SEC", "application/json", "t", 200)
        listings[f"c{i}"] = {"cik": str(i).zfill(10), "yahoo": f"T{i}"}
    listings["c3"]["yahoo"] = "T3-B"  # pool uses a class separator
    _put_name(store, 3, "T3-B", 30, 1.0)
    store.put("submissions:0000000999", json.dumps({"filings": {"recent": {"form": ["20-F"], "filingDate": ["2024-04-01"]}}}).encode(),
              "u", "SEC", "application/json", "t", 200)
    _put_name(store, 999, "FPI", 10**9, 1.0)
    listings["fpi"] = {"cik": "0000000999", "yahoo": "FPI"}
    members = ["T3B" if i == 3 else f"T{i}" for i in range(1, 511)] + ["FPI"] + [f"T{i}" for i in range(4, 400)]
    ref = {"name": "R1000", "source": "iShares IWB", "source_vintage": "2026-09-25", "as_of": AS_OF,
           "membership_basis": "DATED_FUND_HOLDINGS", "reference_role": "SUPERSET_REFERENCE", "members": members}
    rep = chain.run_chain(store, listings, "2024-12-31", [], [ref], None, None)
    r = rep["top500_sufficiency_gate"]["references"][0]
    assert r["missing_from_pool"] == [] and r["present_not_rankable"] == [] and r["excluded_by_eligibility_rule"] == ["FPI"]
    assert r["passed"] is True and rep["top500_sufficiency_gate"]["passed"] is True
    ev = rep["eligibility_evidence_derived_from_superset"]
    assert ev["eligibility_complete"] is True and ev["basis"] == "SUPERSET_REFERENCE_FULLY_COVERED"
    assert rep["promotion_gate_v2"]["passed"] is True  # synthetic: every eligible issuer rankable
    missing = chain.run_chain(store, listings, "2024-12-31", [], [{**ref, "members": members + ["NOTINPOOL"]}], None, None)
    assert missing["top500_sufficiency_gate"]["passed"] is False and missing["eligibility_evidence_derived_from_superset"] is None
    assert missing["promotion_gate_v2"]["passed"] is False and missing["official_top500_declared"] is False


NPORT_XML = b"""<?xml version="1.0"?><edgarSubmission xmlns="http://www.sec.gov/edgar/nport"><formData>
<genInfo><seriesName>iShares Russell 1000 ETF</seriesName><repPdDate>2024-12-31</repPdDate></genInfo>
<invstOrSecs>
<invstOrSec><name>APPLE INC</name><cusip>037833100</cusip><identifiers><isin value="US0378331005"/></identifiers><valUSD>100</valUSD><assetCat>EC</assetCat><invCountry>US</invCountry></invstOrSec>
<invstOrSec><name>ALPHABET INC</name><cusip>02079K305</cusip><valUSD>50</valUSD><assetCat>EC</assetCat><invCountry>US</invCountry></invstOrSec>
<invstOrSec><name>ALPHABET INC</name><cusip>02079K107</cusip><valUSD>45</valUSD><assetCat>EC</assetCat><invCountry>US</invCountry></invstOrSec>
<invstOrSec><name>ANSYS INC</name><cusip>03662Q105</cusip><valUSD>5</valUSD><assetCat>EC</assetCat><invCountry>US</invCountry></invstOrSec>
<invstOrSec><name>TWIN NAME CORP</name><cusip>000000001</cusip><valUSD>1</valUSD><assetCat>EC</assetCat><invCountry>US</invCountry></invstOrSec>
<invstOrSec><name>BLACKROCK CASH FUND</name><cusip>000000002</cusip><valUSD>1</valUSD><assetCat>STIV</assetCat><invCountry>US</invCountry></invstOrSec>
</invstOrSecs></formData></edgarSubmission>"""


def test_nport_parse_series_filings_and_name_resolution(tmp_path):
    fnr = _mod("fnr", "fetch_nport_reference.py")
    doc = fnr.parse_nport(NPORT_XML)
    assert doc["report_date"] == "2024-12-31" and doc["series_name"] == "iShares Russell 1000 ETF"
    eq = [h for h in doc["holdings"] if h["asset_cat"] == "EC"]
    assert len(eq) == 5 and eq[0]["isin"] == "US0378331005"
    hdr = b"<html><pre>&lt;SERIES-NAME&gt;iShares Russell 1000 ETF\n&lt;SERIES-NAME&gt;iShares Russell 1000 Growth ETF\n</pre></html>"
    assert fnr.series_names(hdr) == ["iShares Russell 1000 ETF", "iShares Russell 1000 Growth ETF"]
    sub = {"filings": {"recent": {"form": ["NPORT-P", "NPORT-P", "497K"], "reportDate": ["2024-12-31", "2024-11-30", ""],
                                  "filingDate": ["2025-02-27", "2025-01-28", "2025-01-01"], "accessionNumber": ["a", "b", "c"],
                                  "primaryDocument": ["primary_doc.xml", "primary_doc.xml", "x.htm"]}}}
    assert [f["accn"] for f in fnr.nport_filings_for(sub, "2024-12-31")] == ["a"]
    store = RawDatasetStore(tmp_path)
    store.put("sec_tickers", json.dumps({"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
                                         "1": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."}}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put("sec_cik_lookup", b"ANSYS INC:0001013462:\nTWIN NAME CORP:0000000011:\nTWIN NAME CORPORATION:0000000012:\n", "u", "SEC", "text/plain", "t", 200)
    cur, hist, tick = fnr.name_index(store)
    members, unresolved = fnr.resolve(eq, cur, hist)
    assert set(members) == {"0000320193", "0001652044", "0001013462"}  # two Alphabet classes -> one issuer
    assert members["0001652044"]["cusips"] == ["02079K305", "02079K107"] and members["0001013462"]["method"] == "SEC_CIK_LOOKUP"
    assert [u["name"] for u in unresolved] == ["TWIN NAME CORP"] and tick["0000320193"] == "AAPL"


def test_chain_superset_with_cik_members(tmp_path):
    chain = _mod("chain_cikref", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    listings = {}
    for i in range(1, 911):
        _put_name(store, i, f"T{i}", i * 10, 1.0)
        store.put(f"submissions:{str(i).zfill(10)}", json.dumps({"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2024-11-01"]}}}).encode(),
                  "u", "SEC", "application/json", "t", 200)
        listings[f"c{i}"] = {"cik": str(i).zfill(10), "yahoo": f"T{i}"}
    ref = {"name": "R1000", "source": "SEC NPORT-P x", "source_vintage": "2025-02-27", "as_of": AS_OF, "membership_basis": "DATED_FUND_HOLDINGS",
           "reference_role": "SUPERSET_REFERENCE", "member_id_type": "CIK10", "members": [str(i).zfill(10) for i in range(1, 911)]}
    ok = chain.run_chain(store, listings, "2024-12-31", [], [ref], None, None)
    assert ok["top500_sufficiency_gate"]["passed"] is True
    bad = chain.run_chain(store, listings, "2024-12-31", [], [{**ref, "members": ref["members"] + ["0009999999"]}], None, None)
    assert bad["top500_sufficiency_gate"]["references"][0]["missing_from_pool"] == ["CIK0009999999"]


def test_nport_raw_xml_path_strips_xsl_rendering_directory():
    """Run #21: the submissions primaryDocument 'xslFormNPORT-P_X01/primary_doc.xml' is an XSL-rendered HTML page."""
    fnr = _mod("fnr_xsl", "fetch_nport_reference.py")
    assert fnr.raw_xml_doc("xslFormNPORT-P_X01/primary_doc.xml") == "primary_doc.xml"
    assert fnr.raw_xml_doc("primary_doc.xml") == "primary_doc.xml"


def test_nport_name_normalisation_cases_from_run_22():
    fnr = _mod("fnr_norm", "fetch_nport_reference.py")
    n = fnr.norm_name
    assert n("AMERICAN TOWER CORPORATION") == n("AMERICAN TOWER CORP /MA/")
    assert n("W. R. BERKLEY CORPORATION") == n("BERKLEY W R CORP")
    assert n("LOWE'S COMPANIES, INC.") == n("LOWES COMPANIES INC")
    assert n("MEDTRONIC PUBLIC LIMITED COMPANY") == n("Medtronic plc")
    assert n("Schlumberger N.V.") == n("SCHLUMBERGER LIMITED/NV")
    assert n("APPLE INC") != n("APPLIED MATERIALS INC")


def test_nport_historical_name_collision_resolved_only_by_a_unique_active_cik():
    fnr = _mod("fnr_active", "fetch_nport_reference.py")
    k = fnr.norm_name("DUN & BRADSTREET HOLDINGS, INC.")
    cur = {fnr.norm_name("Something Else Inc"): {"0000000001"}, "X": {"0001799208"}}
    hist = {k: {"0000030312", "0001115222", "0001799208"}}
    members, unresolved = fnr.resolve([{"name": "DUN & BRADSTREET HOLDINGS, INC.", "cusip": "x"}], cur, hist)
    assert list(members) == ["0001799208"] and members["0001799208"]["method"] == "SEC_CIK_LOOKUP_UNIQUE_ACTIVE"
    members, unresolved = fnr.resolve([{"name": "DUN & BRADSTREET HOLDINGS, INC.", "cusip": "x"}], {}, hist)
    assert members == {} and unresolved[0]["name_matches"] == 3  # no active registrant to disambiguate -> not guessed


def test_nport_name_normalisation_cases_from_run_23():
    fnr = _mod("fnr_norm23", "fetch_nport_reference.py")
    n = fnr.norm_name
    assert n("VERISIGN, INC.") == n("VERISIGN INC/CA") and n("CORNING INCORPORATED") == n("CORNING INC /NY")
    assert n("SKECHERS U.S.A., INC.", True) == n("SKECHERS USA INC", True)
    assert n("W. R. BERKLEY CORPORATION") == n("BERKLEY W R CORP")  # default key still keeps single initials
    members, unresolved = fnr.resolve([{"name": "TARGET CORPORATION", "cusip": "x"}],
                                      {n("TARGET CORP"): {"0000027419", "0000999999"}}, {}, pool_ciks={"0000027419"})
    assert list(members) == ["0000027419"] and members["0000027419"]["method"] == "SEC_TICKERS_TITLE_UNIQUE_IN_POOL"


def test_equal_economics_upper_bound_settles_small_unlisted_classes_only(tmp_path):
    """Rule (b), user decision 2026-09-25 (NYT-like settled outside; RKT-like stays undetermined)."""
    chain = _mod("chain_ub", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    listings = {}
    for i in range(1, 501):
        _put_name(store, i, f"T{i}", 1000, 100.0 + i)  # cutoff = 1000 * 101 = 101,000
        store.put(f"submissions:{str(i).zfill(10)}", json.dumps({"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2024-11-01"]}}}).encode(),
                  "u", "SEC", "application/json", "t", 200)
        listings[f"c{i}"] = {"cik": str(i).zfill(10), "yahoo": f"T{i}"}
    for cik, sym, a_sh, b_sh in (("0000700001", "NYTX", 500, 10), ("0000700002", "RKTX", 100, 5000)):
        _put_name(store, int(cik), sym, 1, 20.0)
        aid = _sub_with_filing(store, cik)
        store.put(aid, _instance([("CommonClassAMember", a_sh), ("CommonClassBMember", b_sh)], [(None, sym)], [(None, "Class A Common Stock")]),
                  "u", "SEC", "application/xml", "t", 200)
        listings[sym.lower()] = {"cik": cik, "yahoo": sym}
    ref = {"name": "SP", "source": "s", "source_vintage": "v", "as_of": AS_OF, "membership_basis": "DATED_INTERVALS",
           "members": ["NYTX", "RKTX"]}
    rep = chain.run_chain(store, listings, "2024-12-31", [ref], [], None, None)
    assert rep["cutoff_500_mcap"] == 101_000.0
    assert rep["lower_bound_settled_outside_by_upper_bound"] == {"NYTX": {"lower_bound": 10_000.0, "upper_bound": 10_200.0}}
    assert rep["lower_bound_issuers_outside_top500"] == ["RKTX"]  # UB 102,000 >= cutoff -> undetermined
    cov = rep["reference_coverage"][0]
    r = rep["top500_sufficiency_gate"]["references"][0]
    assert "NYTX" in r["present_rankable_outside_top500"] and r["present_not_rankable"] == ["RKTX"]


def _tiingo_json(rows):
    return json.dumps([{"date": f"{d}T00:00:00.000Z", "close": c, "adjClose": c * 0.9} for d, c in rows]).encode()


def test_tiingo_fallback_raw_close_header_token_and_calibration(tmp_path, monkeypatch):
    ftp = _mod("ftp", "fetch_tiingo_prices.py")
    store = RawDatasetStore(tmp_path)
    for c in ftp.CONTROLS:
        _yahoo_close(store, c, 100.0)
    store.put("yahoo_events:ANSS:5y", json.dumps(_events([(datetime(2025, 3, 1, tzinfo=UTC), 2)])).encode(), "u", "Y", "application/json", "t", 200)
    frd = ftp._load("fetch_real_data")
    monkeypatch.setattr(ftp, "_load", lambda name: frd)
    seen = []

    def fake(req, timeout=0):
        seen.append((req.full_url, req.get_header("Authorization")))
        if "/anss/" in req.full_url:
            return _R(_tiingo_json([("2024-12-30", 337.5), ("2025-07-10", 360.0)]))
        if "/gone/" in req.full_url:
            return _R(b'{"detail": "Error: Ticker GONE not found"}')
        return _R(_tiingo_json([("2024-12-30", 100.1)]))

    monkeypatch.setattr(frd, "urlopen", fake)
    monkeypatch.setattr(frd.time, "sleep", lambda s: None)
    rep = ftp.run(Path(tmp_path), amc_dt(), ["ANSS", "GONE"], "secret-token-123")
    assert rep["calibrated"] is True and rep["results"] == {"ANSS": "WRITTEN_TIINGO_FALLBACK", "GONE": "NO_TIINGO_DATA"}
    assert all("secret-token-123" not in u and a == "Token secret-token-123" for u, a in seen)
    raw_run = json.dumps(rep) + "".join(json.dumps(store.get_manifest(i)) for i in store.list_ids())
    assert "secret-token-123" not in raw_run  # never in reports or manifests
    amc = _mod("amc_tiingo", "audit_mcap_store.py")
    bars = [b for b in load_bars(store, "ANSS") if b["observed_at"] <= amc_dt()]
    assert bars[-1]["close"] == 337.5 and amc.load_splits(store, "ANSS") == []  # raw close: no split undo
    assert amc.mcap_price(bars[-1], amc.load_splits(store, "ANSS"), amc_dt()) == 337.5


def test_tiingo_without_key_writes_nothing(tmp_path):
    ftp = _mod("ftp_nokey", "fetch_tiingo_prices.py")
    rep = ftp.run(Path(tmp_path), amc_dt(), ["ANSS"], None)
    assert rep["status"] == "NO_TIINGO_API_KEY" and rep["written"] == []


def test_nport_pit_registrant_tie_break_and_as_of_symbol(tmp_path):
    fnr = _mod("fnr_pit", "fetch_nport_reference.py")
    store = RawDatasetStore(tmp_path)
    # old dormant entity with the same name vs the registrant filing 10-Qs at as_of (NORDSTROM-like)
    store.put("submissions:0000000070", json.dumps({"filings": {"recent": {"form": ["10-K"], "filingDate": ["1998-03-01"],
              "accessionNumber": ["o"], "primaryDocument": ["o.htm"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    aid = _sub_with_filing(store, "0000072333")
    assert fnr.pit_registrant(store, "0000072333", amc_dt()) is True
    assert fnr.pit_registrant(store, "0000000070", amc_dt()) is False
    store.put(aid, _instance([(None, 165_000_000)], [(None, "JWN")]), "u", "SEC", "application/xml", "t", 200)
    assert fnr.as_of_symbol(store, "0000072333", amc_dt()) == "JWN"
    assert fnr.as_of_symbol(store, "0000000070", amc_dt()) is None


def test_run25_fixes_backslash_tags_and_per_series_common_symbol():
    fnr = _mod("fnr_r25", "fetch_nport_reference.py")
    assert fnr.norm_name("U.S. BANCORP", True) == fnr.norm_name("US BANCORP \\DE\\", True)
    from investment_system.providers.sec_cover_shares import class_symbols, parse_cover
    snv = parse_cover(_instance([(None, 141_000_000)], [("CommonStockMember", "SNV"), ("SeriesDPreferredStockMember", "SNV-PD"),
                                                         ("SeriesEPreferredStockMember", "SNV-PE")]))
    assert class_symbols(snv) == {None: "SNV"}
    amb = parse_cover(_instance([(None, 10)], [("CommonClassAMember", "X"), ("CommonClassBMember", "Y")]))
    assert class_symbols(amb) == {}  # two common-looking members -> not guessed


def test_run25_ticker_change_uses_primary_line_for_the_only_listed_class(tmp_path):
    chain = _mod("chain_r25tc", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    _put_name(store, 1512673, "XYZ", 1, 70.0)  # current ticker's chart carries the SQ-era history
    aid = _sub_with_filing(store, "0001512673")
    store.put(aid, _instance([("CommonClassAMember", 550), ("CommonClassBMember", 50)], [("CommonClassAMember", "SQ")]),
              "u", "SEC", "application/xml", "t", 200)
    ov, _ = chain.cover_mcap_overrides(store, {"x": {"cik": "0001512673", "yahoo": "XYZ"}}, amc_dt())
    a = ov["x"]["classes"][0]
    assert a["price"] == 70.0 and a["price_basis"] == "PRIMARY_LINE_SAME_CIK_TICKER_CHANGE"
    assert ov["x"]["status"] == "COVER_CLASS_SUM_LOWER_BOUND" and ov["x"]["mcap"] == 550 * 70.0


def test_run25_never_periodic_sec_filer_excluded_but_ipo_kept(tmp_path):
    chain = _mod("chain_r25ozk", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    store.put("submissions:0001569650", json.dumps({"filings": {"recent": {"form": ["8-K", "DEF 14A"],
              "filingDate": ["2024-10-17", "2024-03-01"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put("submissions:0000000777", json.dumps({"filings": {"recent": {"form": ["10-Q", "424B4", "S-1"],
              "filingDate": ["2025-02-10", "2024-11-20", "2024-10-01"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    _put_name(store, 1569650, "OZK", 1, 45.0)
    _put_name(store, 777, "IPO", 1, 30.0)
    kept, rep = chain.eligibility_filter(store, {"o": {"cik": "0001569650", "yahoo": "OZK"}, "i": {"cik": "0000000777", "yahoo": "IPO"}}, amc_dt())
    assert rep["excluded_no_sec_periodic_reports"] == ["OZK"] and list(kept) == ["i"]


def test_run25_tiingo_empty_reply_is_retried_once(tmp_path, monkeypatch):
    ftp = _mod("ftp_retry", "fetch_tiingo_prices.py")
    store = RawDatasetStore(tmp_path)
    for c in ftp.CONTROLS:
        _yahoo_close(store, c, 100.0)
    frd = ftp._load("fetch_real_data")
    monkeypatch.setattr(ftp, "_load", lambda name: frd)
    calls = {"eqr": 0}

    def fake(req, timeout=0):
        if "/eqr/" in req.full_url:
            calls["eqr"] += 1
            return _R(b"[]" if calls["eqr"] == 1 else _tiingo_json([("2024-12-30", 72.0)]))
        return _R(_tiingo_json([("2024-12-30", 100.0)]))

    monkeypatch.setattr(frd, "urlopen", fake)
    monkeypatch.setattr(frd.time, "sleep", lambda s: None)
    rep = ftp.run(Path(tmp_path), amc_dt(), ["EQR"], "k")
    assert calls["eqr"] == 2 and rep["results"]["EQR"] == "WRITTEN_TIINGO_FALLBACK"
    rep2 = ftp.run(Path(tmp_path), amc_dt(), ["EQR"], "k")
    assert calls["eqr"] == 2  # present and non-empty now -> no further request


def _with_axis(xml: bytes, axis: str, member: str) -> bytes:
    """Put every duration (symbol/title) context on one non-class axis."""
    seg = (f'<xbrli:segment><xbrldi:explicitMember dimension="dei:{axis}">dei:{member}</xbrldi:explicitMember></xbrli:segment>')
    return xml.replace(b'</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:startDate>',
                       f'</xbrli:identifier>{seg}</xbrli:entity><xbrli:period><xbrli:startDate>'.encode())


def test_run26_symbol_tagged_per_exchange_is_the_undimensioned_security():
    from investment_system.providers.sec_cover_shares import class_symbols, parse_cover
    x = _with_axis(_instance([(None, 225_000_000)], [(None, "X"), (None, "X")], [(None, "Common Stock")]),
                   "EntityListingsExchangeAxis", "NYSEMember")
    assert class_symbols(parse_cover(x)) == {None: "X"}  # US Steel: X on NYSE and Chicago SE
    other = _with_axis(_instance([(None, 225_000_000)], [(None, "SUB")]), "LegalEntityAxis", "SubsidiaryMember")
    assert class_symbols(parse_cover(other)) == {}  # a subsidiary's security is still not the issuer's class


def test_run26_tiingo_alternate_series_by_unique_sec_name(tmp_path, monkeypatch):
    ftp = _mod("ftp_alt", "fetch_tiingo_prices.py")
    store = RawDatasetStore(tmp_path)
    for c in ftp.CONTROLS:
        _yahoo_close(store, c, 100.0)
    frd = ftp._load("fetch_real_data")
    monkeypatch.setattr(ftp, "_load", lambda name: frd)
    seen = []

    def fake(req, timeout=0):
        u = req.full_url
        seen.append(u)
        if "/utilities/search" in u:
            assert "%2C" not in u and "INC" not in u  # plain normalised words only
        if "/utilities/search" in u and "query=VIVMARK" in u:
            return _R(b"[]")  # renamed after as_of: current name not in Tiingo yet
        if "/utilities/search" in u and "query=EQUITY%20RESIDENTIAL" in u:
            return _R(json.dumps([{"name": "Equity Residential", "ticker": "EQR", "permaTicker": "US000000000555", "assetType": "Stock"}]).encode())
        if "/daily/us000000000555/" in u:
            return _R(_tiingo_json([("2024-12-30", 71.9)]))
        if "/daily/eqr/" in u:
            return _R(b"[]")
        if "/utilities/search" in u and "query=PREMIER" in u:
            return _R(json.dumps([{"name": "Premier Inc", "ticker": "PINC", "permaTicker": "US000000000123", "assetType": "Stock"},
                                  {"name": "Premier Financial Corp", "ticker": "PFC", "permaTicker": "US000000000999", "assetType": "Stock"}]).encode())
        if "/utilities/search" in u and "query=WOLFSPEED" in u:  # two same-name series both trading at as_of -> ambiguous
            return _R(json.dumps([{"name": "Wolfspeed Inc", "ticker": "WOLF", "permaTicker": "US1", "assetType": "Stock"},
                                  {"name": "Wolfspeed Inc", "ticker": "WOLF-OLD", "permaTicker": "US2", "assetType": "Stock"}]).encode())
        if "/daily/us000000000123/" in u:
            return _R(_tiingo_json([("2024-12-30", 25.1)]))
        if "/daily/pfc/" in u or "/daily/us000000000999/" in u:
            raise AssertionError("non-matching name must not be fetched")
        if "/daily/pinc/" in u or "/daily/wolf/" in u:
            return _R(_tiingo_json([("2025-10-01", 30.0)]))  # reused ticker: history starts after as_of
        if "/daily/us1/" in u or "/daily/wolf-old/" in u:
            return _R(_tiingo_json([("2024-12-30", 6.6)]))
        if "/daily/us2/" in u:
            return _R(_tiingo_json([("2024-12-30", 7.0)]))
        return _R(_tiingo_json([("2024-12-30", 100.0)]))

    monkeypatch.setattr(frd, "urlopen", fake)
    monkeypatch.setattr(frd.time, "sleep", lambda s: None)
    rep = ftp.run(Path(tmp_path), amc_dt(), ["PINC", "WOLF", "EQR"], "k",
                  names={"PINC": ["Premier, Inc."], "WOLF": ["Wolfspeed, Inc.", "CREE INC"],
                         "EQR": ["VIVMARK RESIDENTIAL", "EQUITY RESIDENTIAL"]})
    assert rep["results"]["EQR"] == "WRITTEN_TIINGO_FALLBACK" and len(rep["alternates"]["EQR"]["search_ids"]) == 2
    assert rep["results"]["PINC"] == "WRITTEN_TIINGO_FALLBACK" and rep["alternates"]["PINC"]["status"] == "UNIQUE"
    assert rep["results"]["WOLF"] == "NO_TIINGO_BAR_ON_OR_BEFORE_AS_OF" and rep["alternates"]["WOLF"]["status"] == "AMBIGUOUS"
    bars = [b for b in load_bars(store, "PINC") if b["observed_at"] <= amc_dt()]
    assert bars[-1]["close"] == 25.1 and "us000000000123" in store.get_manifest("yahoo_chart:PINC:5y")["notes"]
    assert not store.has("yahoo_chart:WOLF:5y")
    assert ftp.norm_name("Premier, Inc.") == ftp.norm_name("PREMIER INC") == ftp.norm_name("Premier Inc - Class A")
    assert ftp.norm_name("Class Acceptance Corp") == "CLASS ACCEPTANCE"  # only a class DESIGNATION is dropped
    assert rep["alternates"]["PINC"]["hits"][0]["name"] == "Premier Inc" and ftp.norm_name("Equity Residential") == "EQUITY RESIDENTIAL"


def _class_econ_store(tmp_path, filed="2024-10-31"):
    store = RawDatasetStore(tmp_path)
    cik = "0001234567"
    store.put(f"submissions:{cik}", json.dumps({"name": "UPC CORP", "filings": {"recent": {
        "form": ["10-Q"], "filingDate": [filed], "accessionNumber": ["0001234567-24-000009"], "primaryDocument": ["q3.htm"]}}}).encode(),
        "u", "SEC", "application/json", "t", 200)
    doc = ("<html><body><p>Each share of Class&nbsp;B common stock is paired with one OpCo Unit. Holders may exchange "
           "OpCo Units, together with an equal number of shares of Class B common stock, for shares of Class A common stock "
           "on a one-for-one basis.</p><p>Shares of Class B common stock have no economic rights.</p></body></html>")
    store.put(f"sec_filing_doc:{cik}:0001234567-24-000009", doc.encode(), "u", "SEC", "text/html", "t", 200)
    ov = {"mcap": 100 * 10.0, "status": "COVER_CLASS_SUM_LOWER_BOUND", "source": "x",
          "classes": [{"member": "CommonClassAMember", "shares": 100, "price": 10.0, "symbol": "UPC"},
                      {"member": "CommonClassBMember", "shares": 300, "price": None, "symbol": None}]}
    quote = ("Holders may exchange OpCo Units, together with an equal number of shares of Class B common stock, "
             "for shares of Class A common stock on a one-for-one basis.")
    det = {"listed_member": "CommonClassAMember", "double_count_check": "Class A count excludes units held by the issuer",
           "classes": {"CommonClassBMember": {"basis": "PAIRED_UNITS_EXCHANGEABLE_INTO_LISTED", "ratio": 1, "citations": [
               {"artifact_id": f"sec_filing_doc:{cik}:0001234567-24-000009", "quote": quote, "supports": ["pairing", "exchange_ratio"]}]}}}
    return store, cik, ov, det


def test_run28_class_economics_verified_quote_gives_economic_equivalent_mcap(tmp_path):
    chain = _mod("chain_ce_ok", "run_top500_gate_chain.py")
    store, cik, ov, det = _class_econ_store(tmp_path)
    mcap, ev = chain.verify_class_economics(store, cik, ov, det, amc_dt())
    assert mcap == (100 + 300) * 10.0 and ev["status"] == "ECONOMIC_EQUIVALENT_DETERMINED"
    assert ev["formula"] == "(CommonClassAMember 100 x 1 + CommonClassBMember 300 x 1) x 10.0"
    assert ev["citations"][0]["filed"] == "2024-10-31"
    overrides = {"u": dict(ov)}
    chain.apply_class_economics(store, overrides, {"u": {"cik": cik, "yahoo": "UPC"}}, {"issuers": {cik: det}}, amc_dt())
    assert overrides["u"]["status"] == "COVER_ECONOMIC_EQUIVALENT" and overrides["u"]["lower_bound"] == 1000.0


def test_run28_class_economics_fail_closed(tmp_path):
    chain = _mod("chain_ce_fail", "run_top500_gate_chain.py")
    store, cik, ov, det = _class_econ_store(tmp_path)
    bad = json.loads(json.dumps(det))
    bad["classes"]["CommonClassBMember"]["citations"][0]["quote"] = "Holders may exchange Class B common stock for cash at a ratio set by the board of directors."
    assert chain.verify_class_economics(store, cik, ov, bad, amc_dt())[0] is None  # quote not in the filing
    only_pair = json.loads(json.dumps(det))
    only_pair["classes"]["CommonClassBMember"]["citations"][0]["supports"] = ["pairing"]
    mcap, ev = chain.verify_class_economics(store, cik, ov, only_pair, amc_dt())
    assert mcap is None and ev["failures"] == ["CLAIMS_UNPROVEN:CommonClassBMember:exchange_ratio"]
    ratio2 = json.loads(json.dumps(det))
    ratio2["classes"]["CommonClassBMember"]["ratio"] = 2
    assert chain.verify_class_economics(store, cik, ov, ratio2, amc_dt())[0] is None  # no guessed ratios
    assert chain.verify_class_economics(store, "0009999999", ov, det, amc_dt())[0] is None  # other CIK's filing
    late_store, _, _, _ = _class_econ_store(tmp_path / "late", filed="2025-02-20")
    mcap, ev = chain.verify_class_economics(late_store, cik, ov, det, amc_dt())
    assert mcap is None and ev["failures"][0].startswith("CITATION_NOT_FILED_ON_OR_BEFORE_AS_OF")
    missing = json.loads(json.dumps(det))
    missing["classes"] = {}
    assert chain.verify_class_economics(store, cik, ov, missing, amc_dt())[1]["failures"] == ["NO_DETERMINATION:CommonClassBMember"]


def test_run28_class_rights_passages_and_latest_forms():
    frc = _mod("frc", "fetch_class_rights_evidence.py")
    text = frc.html_text(b"<p>Each share of Class&nbsp;B common stock is convertible at any time into one share of Class A common stock.</p>"
                         b"<p>The weather in Chicago was pleasant and Class B common stock was mentioned without rights words here</p>")
    ps = frc.passages(text, frc.class_phrases("CommonClassBMember"))
    assert [p["text"] for p in ps] == ["Each share of Class B common stock is convertible at any time into one share of Class A common stock."]
    sub = {"filings": {"recent": {"form": ["10-Q", "10-K", "10-Q", "10-K"], "filingDate": ["2025-02-01", "2024-02-20", "2024-11-01", "2023-02-20"],
                                  "accessionNumber": ["a", "b", "c", "d"], "primaryDocument": ["a.htm", "b.htm", "c.htm", "d.htm"]}}}
    assert [f["accn"] for f in frc.latest_forms(sub, amc_dt())] == ["b", "c"]
    assert "Nonvoting Class A" in frc.class_phrases("NonvotingCommonStockMember")


def test_run29_reviewed_class_economics_file_verifies_against_its_cited_filings(tmp_path):
    """The committed determinations (H, RKT, TKO, TPG) pass the chain's verifier when the cited filings contain the
    quotes; the resulting market caps equal (listed + ratio x unlisted shares) x listed price."""
    chain = _mod("chain_ce_real", "run_top500_gate_chain.py")
    ge = Path(chain.GE)
    dets = json.loads((ge / "class_economics_2024-12-31.json").read_text(encoding="utf-8"))
    passages = json.loads((ge / "class_rights_passages_2024-12-31.json").read_text(encoding="utf-8"))["issuers"]
    store = RawDatasetStore(tmp_path)
    got = {}
    for cik, det in dets["issuers"].items():
        p = passages[det["symbol"]]
        docs = {}
        for cd in det["classes"].values():
            for q in cd["citations"]:
                docs.setdefault(q["artifact_id"], (q["accession"], q["filed"], []))[2].append(q["quote"])
        rec = {"form": [], "filingDate": [], "accessionNumber": [], "primaryDocument": []}
        for aid, (accn, filed, quotes) in docs.items():
            store.put(aid, ("<html><p>" + "</p><p>".join(quotes) + "</p></html>").encode(), "u", "SEC", "text/html", "t", 200)
            for k, v in (("form", "10-Q"), ("filingDate", filed), ("accessionNumber", accn), ("primaryDocument", "d.htm")):
                rec[k].append(v)
        store.put(f"submissions:{cik}", json.dumps({"filings": {"recent": rec}}).encode(), "u", "SEC", "application/json", "t", 200)
        classes = [{**c, "price": c.get("price") or None} for c in p["classes"]]
        ov = {"mcap": sum(c["shares"] * c["price"] for c in classes if c["price"]), "status": "COVER_CLASS_SUM_LOWER_BOUND", "classes": classes}
        mcap, ev = chain.verify_class_economics(store, cik, ov, det, amc_dt())
        assert ev["status"] == "ECONOMIC_EQUIVALENT_DETERMINED", (det["symbol"], ev)
        listed = next(c for c in classes if c["price"])
        assert abs(mcap - sum(c["shares"] for c in classes) * listed["price"]) < 1e-3
        got[det["symbol"]] = mcap
    assert sorted(got) == ["DKS", "H", "RKT", "RYAN", "TKO", "TPG"]
    assert all(min(c["filed"] for cd in d["classes"].values() for c in cd["citations"]) <= "2024-12-31" for d in dets["issuers"].values())


def test_run29_identical_rights_basis_and_context_citations_do_not_prove_ratios(tmp_path):
    chain = _mod("chain_ce_ctx", "run_top500_gate_chain.py")
    store, cik, ov, det = _class_econ_store(tmp_path)
    ctx_only = json.loads(json.dumps(det))
    ctx_only["classes"]["CommonClassBMember"]["citations"] = [{
        "artifact_id": f"sec_filing_doc:{cik}:0001234567-24-000009",
        "quote": "Each share of Class B common stock is paired with one OpCo Unit.", "supports": ["voting_only_context"]}]
    mcap, ev = chain.verify_class_economics(store, cik, ov, ctx_only, amc_dt())
    assert mcap is None and "CLAIMS_UNPROVEN" in ev["failures"][0]
    import re
    assert re.search(chain.CLAIM_PATTERNS["identical_rights"], "have the same rights and privileges as, rank equally and share ratably with")
    assert re.search(chain.RATIO_ONE, "were converted on a share-for-share basis into shares of Class A common stock")


def _nport_xml(holdings, report_date="2024-12-31"):
    rows = "".join(
        f"<invstOrSec><name>{n}</name><lei>L</lei><title>{n} COMMON</title><cusip>{c}</cusip>"
        f"<identifiers><isin value=\"US{c}0\"/></identifiers><balance>{b}</balance><units>{u}</units><curCd>USD</curCd>"
        f"<valUSD>{v}</valUSD><assetCat>EC</assetCat><invCountry>US</invCountry></invstOrSec>"
        for n, c, b, u, v in holdings)
    return (f'<edgarSubmission xmlns="http://www.sec.gov/edgar/nport"><formData><genInfo><repPdDate>{report_date}</repPdDate>'
            f"</genInfo><invstOrSecs>{rows}</invstOrSecs></formData></edgarSubmission>").encode()


def _nport_setup(tmp_path, g_filed="2024-11-08"):
    store = RawDatasetStore(tmp_path)
    accn = "0001752724-25-034052"
    store.put(f"nport_xml:{accn}", _nport_xml([("PREMIER INC-CLASS A", "74051N102", "402151", "NS", "8525601.2"),
                                               ("OTHER CORP", "000000000", "10", "NS", "100")]),
              "u", "SEC", "application/xml", "t", 200)
    cik = "0001577916"
    cf = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{"filed": "2024-11-01", "val": 96108595}]}}}}}
    store.put(f"companyfacts:{cik}", json.dumps(cf).encode(), "u", "SEC", "application/json", "t", 200)
    store.put(f"submissions:{cik}", json.dumps({"filings": {"recent": {"form": ["SC 13G/A"], "filingDate": [g_filed],
              "accessionNumber": ["0000102909-24-000111"], "primaryDocument": ["g.txt"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put(f"sec_filing_doc:{cik}:0000102909-24-000111", b"SCHEDULE 13G Premier, Inc. (Name of Issuer) Class A Common Stock "
              b"(Title of Class of Securities) 74051N 10 2 (CUSIP Number)", "u", "SEC", "text/plain", "t", 200)
    npr = _mod("npr_t", "nport_reported_prices.py")
    h = next(x for x in npr.raw_holdings(store.get_bytes(f"nport_xml:{accn}")) if x["cusip"] == "74051N102")
    px, _ = npr.reported_price(h)
    ev = {"as_of": "2024-12-31", "source_artifact": f"nport_xml:{accn}", "valuation_date": "2024-12-31", "filing_date": "2025-02-24",
          "issuers": {"PINC": {
        "status": "IDENTITY_AND_PRICE_VERIFIED", "holding_raw": h, "price": px,
        "cusip_attestation": [{"artifact_id": f"sec_filing_doc:{cik}:0000102909-24-000111", "form": "SC 13G/A", "filed": g_filed}]}}}
    exc = {"as_of": "2024-12-31", "issuers": {"PINC": cik, "WOLF": "0000895419"}}
    return store, cik, ev, exc, px


def test_run30_nport_reported_value_raw_fields_price_and_cusip():
    npr = _mod("npr_u", "nport_reported_prices.py")
    h = npr.raw_holdings(_nport_xml([("PREMIER INC-CLASS A", "74051N102", "402151", "NS", "8525601.2")]))[0]
    assert (h["balance"], h["units"], h["cur_cd"], h["val_usd"], h["isin"]) == ("402151", "NS", "USD", "8525601.2", "US74051N1020")
    px, why = npr.reported_price(h)
    assert why == "OK" and px == 8525601.2 / 402151
    assert npr.reported_price({**h, "units": "PA"})[0] is None  # principal amount is not a per-share value
    assert npr.cusip_attested("... 74051N 10 2 (CUSIP Number)", "74051N102")
    assert npr.cusip_attested("... 74051N 10 3 (CUSIP Number)", "74051N102") is None
    assert npr.holding_for([h, dict(h)], ["PREMIER INC-CLASS A"])[1] == "EC_HOLDINGS_FOR_CIK_2"  # ambiguous -> fail


def test_run30_nport_exception_applied_only_to_listed_issuers_and_fail_closed(tmp_path):
    chain = _mod("chain_npr", "run_top500_gate_chain.py")
    store, cik, ev, exc, px = _nport_setup(tmp_path)
    listings = {"p": {"cik": cik, "yahoo": "PINC"}, "o": {"cik": "0000000321", "yahoo": "OTHER"}}
    ov = {}
    out = chain.apply_nport_reported_prices(store, ov, listings, exc, ev, amc_dt())
    assert out["PINC"]["status"] == "APPLIED" and ov["p"]["status"] == "NPORT_REPORTED_VALUE"
    assert abs(ov["p"]["mcap"] - 96108595 * px) < 1e-3 and ov["p"]["valuation_date"] == "2024-12-31"
    assert "OTHER" not in out and "o" not in ov  # never extended beyond the exception list
    # a real close on/before as_of always wins
    _put_name(store, 1577916, "PINC", 96108595, 21.0)
    ov2 = {}
    assert chain.apply_nport_reported_prices(store, ov2, listings, exc, ev, amc_dt())["PINC"]["failures"] == ["MARKET_CLOSE_AVAILABLE"]
    assert ov2 == {}


def test_run30_nport_exception_rejects_tampered_price_late_attestation_and_cik_mismatch(tmp_path):
    chain = _mod("chain_npr2", "run_top500_gate_chain.py")
    store, cik, ev, exc, px = _nport_setup(tmp_path / "a")
    listings = {"p": {"cik": cik, "yahoo": "PINC"}}
    bad = json.loads(json.dumps(ev))
    bad["issuers"]["PINC"]["price"] = px * 1.01
    assert chain.apply_nport_reported_prices(store, {}, listings, exc, bad, amc_dt())["PINC"]["failures"][0].startswith("PRICE_NOT_REPRODUCED")
    assert chain.apply_nport_reported_prices(store, {}, listings, {"as_of": "2024-12-31", "issuers": {"PINC": "0000000001"}}, ev, amc_dt())["PINC"]["failures"] == ["CIK_MISMATCH"]
    late, cik2, ev2, exc2, _ = _nport_setup(tmp_path / "b", g_filed="2025-02-10")
    assert chain.apply_nport_reported_prices(late, {}, listings, exc2, ev2, amc_dt())["PINC"]["failures"] == ["CUSIP_NOT_ATTESTED"]


def test_run30_share_count_diagnostic_separates_post_as_of_filings():
    scd = _mod("scd", "share_count_diagnostic.py")
    cf = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
        {"val": 0, "end": "2024-10-31", "filed": "2024-11-12", "form": "10-Q"},
        {"val": 5_000_000, "end": "2024-12-31", "filed": "2025-03-01", "form": "10-K"}]}}}}}
    rows = scd.companyfacts_shares(cf, amc_dt())
    assert [r["val"] for r in rows["filed_on_or_before_as_of"]] == [0]
    assert [r["val"] for r in rows["POST_AS_OF_FILINGS_ABOUT_PERIODS_ENDING_ON_OR_BEFORE_AS_OF"]] == [5_000_000]
    facts = scd.cover_facts(_instance([(None, 0)], [(None, "PPLI")]))
    assert {f["concept"] for f in facts} == {"EntityCommonStockSharesOutstanding", "TradingSymbol"}
    assert next(f for f in facts if f["concept"] == "EntityCommonStockSharesOutstanding")["unit"] == "shares"


def test_run31_cover_text_maps_undimensioned_symbol_to_the_member_with_the_stated_count(tmp_path):
    """IAC (CIK 1800227, now PPLI): XBRL tags 'IAC' undimensioned, title 'Common stock, par value $0.0001', members Class A/B.
    The same 10-Q's cover text 'Common Stock 80,479,073 Class B common stock 5,789,499' identifies the listed member."""
    chain = _mod("chain_iac", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    cik = "0001800227"
    aid = _sub_with_filing(store, cik, accn="0001800227-24-000046")
    store.put(aid, _instance([("CommonClassAMember", 80_479_073), ("CommonClassBMember", 5_789_499)], [(None, "IAC")],
                             [(None, "Common stock, par value $0.0001")]), "u", "SEC", "application/xml", "t", 200)
    cover = chain.parse_cover(store.get_bytes(aid))
    text = ("As of November 8, 2024, the following shares of the registrant's common stock were outstanding: "
            "Common Stock 80,479,073 Class B common stock 5,789,499 TABLE OF CONTENTS")
    assert chain.cover_text_symbol_member(text, cover)[0] == "CommonClassAMember"
    assert chain.cover_text_symbol_member("Common Stock 1,000 Class B common stock 5,789,499", cover) == (None, None)
    # without the stored filing text nothing is mapped (fail-closed)
    ov, unres = chain.cover_mcap_overrides(store, {"i": {"cik": cik, "yahoo": "PPLI"}}, amc_dt())
    assert unres == {"i": "NO_PRICED_CLASS"}
    store.put(f"sec_filing_doc:{cik}:0001800227-24-000046", f"<html><p>{text}</p></html>".encode(), "u", "SEC", "text/html", "t", 200)
    cf = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{"filed": "2020-06-03", "val": 0}]}}}}}
    store.put(f"companyfacts:{cik}", json.dumps(cf).encode(), "u", "SEC", "application/json", "t", 200)
    chart = {"chart": {"result": [{"timestamp": [int(datetime(2024, 12, 30, 21, tzinfo=UTC).timestamp()) - 86400 * 2],
                                   "indicators": {"quote": [{"close": [43.0]}]}}], "error": None}}
    store.put("yahoo_chart:PPLI:5y", json.dumps(chart).encode(), "u", "YAHOO", "application/json", "t", 200)
    ov, unres = chain.cover_mcap_overrides(store, {"i": {"cik": cik, "yahoo": "PPLI"}}, amc_dt())
    o = ov["i"]
    assert o["status"] == "COVER_CLASS_SUM_LOWER_BOUND" and o["mcap"] == 80_479_073 * 43.0  # Class B unpriced: lower bound
    a = next(c for c in o["classes"] if c["member"] == "CommonClassAMember")
    assert a["symbol"] == "IAC" and a["price_basis"] == "PRIMARY_LINE_SAME_CIK_TICKER_CHANGE"
    assert a["symbol_basis"]["basis"] == "COVER_TEXT_TITLE_COUNT_MATCH" and "80,479,073" in a["symbol_basis"]["quote"]
    assert chain.equal_economics_upper_bound(o) == (80_479_073 + 5_789_499) * 43.0
    # a reused old ticker whose close disagrees with the same-CIK primary line is not used
    chart2 = {"chart": {"result": [{"timestamp": chart["chart"]["result"][0]["timestamp"], "indicators": {"quote": [{"close": [9.0]}]}}], "error": None}}
    store.put("yahoo_chart:IAC:5y", json.dumps(chart2).encode(), "u", "YAHOO", "application/json", "t", 200)
    ov2, unres2 = chain.cover_mcap_overrides(store, {"i": {"cik": cik, "yahoo": "PPLI"}}, amc_dt())
    assert unres2 == {"i": "NO_PRICED_CLASS"}


def _scale_store(tmp_path, dei_val, doc_text=None):
    store = RawDatasetStore(tmp_path)
    cik = "0000717605"
    cf = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
              {"filed": "2024-10-21", "end": "2024-10-18", "val": dei_val}]}}},
          "us-gaap": {"WeightedAverageNumberOfSharesOutstandingBasic": {"units": {"shares": [
              {"filed": "2024-10-21", "end": "2024-09-29", "val": 81_300_000, "accn": "0000717605-24-000060"}]}}}}}
    store.put(f"companyfacts:{cik}", json.dumps(cf).encode(), "u", "SEC", "application/json", "t", 200)
    _sub_with_filing(store, cik, accn="0000717605-24-000060")
    chart = {"chart": {"result": [{"timestamp": [int(datetime(2024, 12, 27, 21, tzinfo=UTC).timestamp())],
                                   "indicators": {"quote": [{"close": [62.59]}]}}], "error": None}}
    store.put("yahoo_chart:HXL:5y", json.dumps(chart).encode(), "u", "YAHOO", "application/json", "t", 200)
    if doc_text:
        store.put(f"sec_filing_doc:{cik}:0000717605-24-000060", f"<html><p>{doc_text}</p></html>".encode(), "u", "SEC", "text/html", "t", 200)
    return store, cik


def test_run32_share_scale_error_corrected_only_from_cover_text(tmp_path):
    """HXL: XBRL dei 81,002,128,000,000 (scale error x10^6) vs weighted-average 81.3M -> corrected to the count printed on
    the 10-Q cover (81,002,128); without that document the issuer is excluded (not ranked with the inflated count)."""
    chain = _mod("chain_scale", "run_top500_gate_chain.py")
    amc = _mod("amc_scale", "audit_mcap_store.py")
    listings = {"h": {"cik": "0000717605", "yahoo": "HXL"}}
    store, cik = _scale_store(tmp_path / "a", 81_002_128_000_000,
                              "The number of shares of common stock outstanding as of October 18, 2024 was 81,002,128.")
    ov = {}
    ev = chain.share_scale_overrides(store, listings, ov, amc_dt())
    assert ev["HXL"]["status"] == "SHARE_SCALE_CORRECTED_FROM_COVER_TEXT" and ev["HXL"]["scale_power"] == 6
    assert ov["h"]["mcap"] == 81_002_128 * 62.59
    no_doc, _ = _scale_store(tmp_path / "b", 81_002_128_000_000)
    ov2 = {}
    assert chain.share_scale_overrides(no_doc, listings, ov2, amc_dt())["HXL"]["status"] == "SHARE_SCALE_UNVERIFIED"
    assert amc.audit(no_doc, listings, amc_dt(), mcap_override=ov2)["rankable"] == 0
    assert amc.ranked_top500(no_doc, listings, amc_dt(), mcap_override=ov2) == []
    ok, _ = _scale_store(tmp_path / "c", 81_002_128)  # consistent -> untouched
    assert chain.share_scale_overrides(ok, listings, {}, amc_dt()) == {}
    # ambiguous: text prints both readings -> not corrected
    amb, _ = _scale_store(tmp_path / "d", 81_002_128_000_000,
                          "81,002,128 shares outstanding; authorized 81,002,128,000 shares outstanding")
    assert chain.share_scale_overrides(amb, listings, {}, amc_dt())["HXL"]["status"] == "SHARE_SCALE_UNVERIFIED"


def test_run32_cover_text_found_after_a_long_ixbrl_hidden_header():
    chain = _mod("chain_hdr", "run_top500_gate_chain.py")
    cover = {"titles": {None: ["Common stock, par value $0.0001"]},
             "classes": [{"member": "CommonClassAMember", "shares": 80_479_073.0}, {"member": "CommonClassBMember", "shares": 5_789_499.0}]}
    text = ("c-1 0001800227 2024-01-01 2024-09-30 " * 3000) + "Common Stock 80,479,073 Class B common stock 5,789,499"
    assert len(text) > 60000 and chain.cover_text_symbol_member(text, cover)[0] == "CommonClassAMember"
    k, cnt, _ = chain.cover_text_share_count(("x " * 40000) + "81,002,128 shares outstanding", 81_002_128_000_000)
    assert (k, cnt) == (6, 81_002_128)


def test_run33_stale_share_fact_routes_to_cover_and_needs_cover(tmp_path):
    """MA-like: companyfacts' only undimensioned dei count was filed years before the latest 10-Q (the 10-Q tagged per
    class, dimensions dropped) -> stale -> cover instance fetched and used; a current single-class fact is not stale."""
    chain = _mod("chain_stale", "run_top500_gate_chain.py")
    fcx = _mod("fcx_stale", "fetch_cover_xbrl.py")
    store = RawDatasetStore(tmp_path)
    cik = "0001141391"
    cf = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{"filed": "2012-02-16", "val": 122_530_193}]}}}}}
    store.put(f"companyfacts:{cik}", json.dumps(cf).encode(), "u", "SEC", "application/json", "t", 200)
    aid = _sub_with_filing(store, cik)
    sh = chain.pit_shares(cf, amc_dt())
    assert chain.share_fact_stale(store, cik, sh, amc_dt()) is True
    assert fcx.needs_cover(store, {"m": {"cik": cik, "yahoo": "MA"}}, amc_dt()) == [cik]
    store.put(aid, _instance([("CommonClassAMember", 917_000_000), ("CommonClassBMember", 7_000_000)],
                             [("CommonClassAMember", "MA")]), "u", "SEC", "application/xml", "t", 200)
    chart = {"chart": {"result": [{"timestamp": [int(datetime(2024, 12, 27, 21, tzinfo=UTC).timestamp())],
                                   "indicators": {"quote": [{"close": [526.0]}]}}], "error": None}}
    store.put("yahoo_chart:MA:5y", json.dumps(chart).encode(), "u", "YAHOO", "application/json", "t", 200)
    ov, _ = chain.cover_mcap_overrides(store, {"m": {"cik": cik, "yahoo": "MA"}}, amc_dt())
    assert ov["m"]["status"] == "COVER_CLASS_SUM_LOWER_BOUND" and ov["m"]["mcap"] == 917_000_000 * 526.0
    fresh = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{"filed": "2024-10-30", "val": 5}]}}}}}
    assert chain.share_fact_stale(store, cik, chain.pit_shares(fresh, amc_dt()), amc_dt()) is False


def test_run33_single_class_stale_uses_fresh_cover_count_unless_it_fails_the_scale_check(tmp_path):
    chain = _mod("chain_stale1", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    cik = "0000000555"
    cf = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{"filed": "2020-06-03", "val": 0}]}}},
          "us-gaap": {"WeightedAverageNumberOfSharesOutstandingBasic": {"units": {"shares": [
              {"filed": "2024-10-30", "end": "2024-09-30", "val": 100_000_000}]}}}}}
    store.put(f"companyfacts:{cik}", json.dumps(cf).encode(), "u", "SEC", "application/json", "t", 200)
    aid = _sub_with_filing(store, cik)
    chart = {"chart": {"result": [{"timestamp": [int(datetime(2024, 12, 27, 21, tzinfo=UTC).timestamp())],
                                   "indicators": {"quote": [{"close": [10.0]}]}}], "error": None}}
    store.put("yahoo_chart:SGL:5y", json.dumps(chart).encode(), "u", "YAHOO", "application/json", "t", 200)
    store.put(aid, _instance([(None, 101_000_000)], [(None, "SGL")]), "u", "SEC", "application/xml", "t", 200)
    ov, _ = chain.cover_mcap_overrides(store, {"s": {"cik": cik, "yahoo": "SGL"}}, amc_dt())
    assert ov["s"]["status"] == "COVER_SINGLE_CLASS" and ov["s"]["mcap"] == 101_000_000 * 10.0
    store.put(aid, _instance([(None, 101_000_000_000_000)], [(None, "SGL")]), "u", "SEC", "application/xml", "t", 200)
    ov2, un2 = chain.cover_mcap_overrides(store, {"s": {"cik": cik, "yahoo": "SGL"}}, amc_dt())
    assert ov2 == {} and un2 == {"s": "COVER_SHARES_FAIL_SCALE_CHECK"}


def test_run34_stale_fact_with_unresolved_cover_is_excluded_not_ranked(tmp_path):
    chain = _mod("chain_stalex", "run_top500_gate_chain.py")
    amc = _mod("amc_stalex", "audit_mcap_store.py")
    store = RawDatasetStore(tmp_path)
    cik = "0001156375"
    _put_name(store, 1156375, "CME", 66_643_583, 230.0)  # companyfacts fact filed 2024-11-01 ...
    store.put(f"submissions:{cik}", json.dumps({"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2024-11-08"],
              "accessionNumber": ["0001156375-24-000200"], "primaryDocument": ["q.htm"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    listings = {"c": {"cik": cik, "yahoo": "CME"}}
    ov = {}
    ex = chain.exclude_stale_unresolved(store, listings, ov, amc_dt())  # ... but the latest 10-Q was filed 2024-11-08
    assert ex["CME"]["status"] == "STALE_SHARE_FACT_UNRESOLVED" and ov["c"]["exclude"] is True
    assert amc.audit(store, listings, amc_dt(), mcap_override=ov)["rankable"] == 0
    fresh = RawDatasetStore(tmp_path / "f")
    _put_name(fresh, 1156375, "CME", 360_000_000, 230.0)
    fresh.put(f"submissions:{cik}", json.dumps({"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2024-11-01"],
              "accessionNumber": ["a"], "primaryDocument": ["q.htm"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    assert chain.exclude_stale_unresolved(fresh, listings, {}, amc_dt()) == {}


def _consistency_store(tmp_path):
    store = RawDatasetStore(tmp_path)
    t = int(datetime(2024, 12, 27, 21, tzinfo=UTC).timestamp())
    def chart(sym, close, adj):
        store.put(f"yahoo_chart:{sym}:5y", json.dumps({"chart": {"result": [{"timestamp": [t], "indicators": {
            "quote": [{"close": [close]}], "adjclose": [{"adjclose": [adj]}]}}], "error": None}}).encode(), "u", "Y", "application/json", "t", 200)
    for cik, sym, sh, close, adj in (("0000000101", "AAA", 1000, 50.0, 48.0), ("0000000102", "BBB", 900, 40.0, 39.0)):
        store.put(f"companyfacts:{cik}", json.dumps({"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
            {"filed": "2024-11-01", "val": sh}]}}}}}).encode(), "u", "SEC", "application/json", "t", 200)
        store.put(f"submissions:{cik}", json.dumps({"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2024-11-01"],
                  "accessionNumber": [f"{cik}-24-1"], "primaryDocument": ["q.htm"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
        chart(sym, close, adj)
    # BRK-like two listed classes -> cover class sum (not reproducible from companyfacts)
    cik = "0001067983"
    aid = _sub_with_filing(store, cik)
    store.put(aid, _instance([("CommonClassAMember", 10), ("CommonClassBMember", 2000)], [("CommonClassAMember", "BRK.A"), ("CommonClassBMember", "BRK.B")]),
              "u", "SEC", "application/xml", "t", 200)
    chart("BRK-A", 700.0, 700.0)
    chart("BRK-B", 0.5, 0.5)
    listings = {"a": {"cik": "0000000101", "yahoo": "AAA"}, "b": {"cik": "0000000102", "yahoo": "BBB"}, "k": {"cik": cik, "yahoo": "BRK-B"}}
    return store, listings


def test_run35_gate_snapshot_consistency_preserves_cover_shares_and_close_basis(tmp_path):
    chain = _mod("chain_cons", "run_top500_gate_chain.py")
    amc = _mod("amc_cons", "audit_mcap_store.py")
    from investment_system.universe.sources import official_mcap500_snapshot_from_store
    store, listings = _consistency_store(tmp_path)
    ov, _ = chain.cover_mcap_overrides(store, listings, amc_dt())
    assert ov["k"]["status"] == "COVER_CLASS_SUM" and ov["k"]["mcap"] == 10 * 700.0 + 2000 * 0.5
    top = amc.ranked_top500(store, listings, amc_dt(), mcap_override=ov)
    cands = chain.gate_audited_candidates(store, listings, ov, amc_dt())
    rep = chain.gate_snapshot_consistency(store, listings, top, cands, amc_dt())
    assert rep["passed"] and rep["n_snapshot"] == 3 and rep["shares_basis_counts"]["COVER_CLASS_SUM"] == 1
    k = next(c for c in cands if c["company_id"] == "k")
    assert abs(k["shares"] * k["price"] - 8000.0) < 1e-9 and k["price_basis"] == "CLOSE_X_POST_AS_OF_SPLIT_FACTOR"
    # the unchanged default path (companyfacts shares x adjclose) does not reproduce the gate: evidence for C-32
    snap_default, _ = official_mcap500_snapshot_from_store(store, {c: listings[c] for c in ("a", "b")}, amc_dt())
    snap_gate, _ = official_mcap500_snapshot_from_store(store, listings, amc_dt(), gate_candidates=cands)
    assert list(snap_gate.ids()) == [r["company_id"] for r in top]
    assert "k" not in snap_default.ids()  # cover-page class sum lost on the default path


def test_run35_consistency_flags_gate_member_whose_price_is_not_available_at_as_of(tmp_path):
    chain = _mod("chain_cons2", "run_top500_gate_chain.py")
    amc = _mod("amc_cons2", "audit_mcap_store.py")
    store, listings = _consistency_store(tmp_path)
    ov, _ = chain.cover_mcap_overrides(store, listings, amc_dt())
    ov["b"] = {"mcap": 900 * 21.2, "status": "NPORT_REPORTED_VALUE", "valuation_date": "2024-12-31", "classes": [],
               "nport_reported_value": {"price": 21.2}}
    top = amc.ranked_top500(store, listings, amc_dt(), mcap_override=ov)
    cands = chain.gate_audited_candidates(store, listings, ov, amc_dt())
    rep = chain.gate_snapshot_consistency(store, listings, top, cands, amc_dt())
    assert rep["passed"] is False and rep["only_in_gate"] == ["b"]
    assert rep["gate_members_excluded_by_snapshot"] == [{"company_id": "b", "price_basis": "NPORT_REPORTED_VALUE"}]


def test_run35_cover_parser_dedupes_and_new_symbol_rules():
    from investment_system.providers.sec_cover_shares import class_symbols, parse_cover
    # CME: every share fact duplicated; title 'Class A Common Stock'
    cme = _instance([("CommonClassAMember", 360_359_063), ("CommonClassAMember", 360_359_063), ("ClassBCommonStockClassB1Member", 625),
                     ("ClassBCommonStockClassB1Member", 625)], [(None, "CME")], [(None, "Class A Common Stock")])
    cov = parse_cover(cme)
    assert len(cov["classes"]) == 2 and class_symbols(cov) == {"CommonClassAMember": "CME"}
    # AOS / COKE / TRIP / AA: plain-common member names
    for plain, other in (("CommonStockClassUndefinedMember", "CommonClassAMember"), ("CommonClassUndefinedMember", "CommonClassBMember"),
                         ("CommonStockUnclassifiedMember", "CommonClassBMember"),
                         ("CommonStockParValueZeroPointZeroOnePerShareMember", "SeriesAConvertiblePreferredStockMember")):
        c = parse_cover(_instance([(plain, 100), (other, 10)], [(None, "SYM")], [(None, "Common Stock, par value $1.00")]))
        assert class_symbols(c) == {plain: "SYM"}, plain
    # ARES: symbol on a differently named member of the same class letter; preferred ignored
    ares = parse_cover(_instance([("CommonClassAMember", 198), ("CommonClassCMember", 111), ("NonvotingCommonStockMember", 3)],
                                 [("ClassACommonStockParValue0.01PerShareMember", "ARES"),
                                  ("A6.75SeriesBMandatoryConvertiblePreferredStockParValue0.01PerShareMember", "ARES.PRB")]))
    assert class_symbols(ares) == {"CommonClassAMember": "ARES"}
    # DKS / IBKR: 'Common Stock' with Class A + Class B members -> still unmapped (needs reviewed evidence)
    dks = parse_cover(_instance([("CommonClassAMember", 57), ("CommonClassBMember", 23)], [(None, "DKS")], [(None, "Common Stock, $0.01 par value")]))
    assert class_symbols(dks) == {}


def test_run35_bf_separator_normalised_to_same_cik_ticker_and_mtd_text_count(tmp_path):
    chain = _mod("chain_bf", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    cik = "0000014693"
    aid = _sub_with_filing(store, cik)
    sub = json.loads(store.get_bytes(f"submissions:{cik}"))
    sub["tickers"] = ["BF-B", "BF-A"]
    store.put(f"submissions:{cik}", json.dumps(sub).encode(), "u", "SEC", "application/json", "t", 200)
    store.put(aid, _instance([("CommonClassAMember", 169_123_305), ("NonvotingCommonStockMember", 303_537_999)],
                             [("CommonClassAMember", "BFA"), ("NonvotingCommonStockMember", "BFB")]), "u", "SEC", "application/xml", "t", 200)
    t = int(datetime(2024, 12, 27, 21, tzinfo=UTC).timestamp())
    for sym, px in (("BF-A", 38.0), ("BF-B", 37.9)):
        store.put(f"yahoo_chart:{sym}:5y", json.dumps({"chart": {"result": [{"timestamp": [t], "indicators": {"quote": [{"close": [px]}]}}],
                  "error": None}}).encode(), "u", "Y", "application/json", "t", 200)
    ov, _ = chain.cover_mcap_overrides(store, {"b": {"cik": cik, "yahoo": "BF-B"}}, amc_dt())
    assert ov["b"]["status"] == "COVER_CLASS_SUM" and ov["b"]["mcap"] == 169_123_305 * 38.0 + 303_537_999 * 37.9
    assert {c["price_symbol"] for c in ov["b"]["classes"]} == {"BF-A", "BF-B"}
    assert chain.same_cik_ticker(store, cik, "BFC") is None
    assert chain.cover_text_single_count("The Registrant had 21,102,668 shares of Common Stock outstanding at September 30, 2024 ... "
                                         "outstanding 21,102,668 shares and 21,526,172 shares") == 21_102_668
    assert chain.cover_text_single_count("10,000 shares of common stock outstanding; 12,000 shares of common stock outstanding") is None


def test_run35_reviewed_symbol_mapping_verified_against_filing_quote(tmp_path):
    chain = _mod("chain_dks", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    cik = "0001089063"
    store.put(f"submissions:{cik}", json.dumps({"filings": {"recent": {"form": ["10-Q", "10-K"], "filingDate": ["2024-11-27", "2024-03-28"],
              "accessionNumber": ["0001089063-24-000121", "0001089063-24-000037"], "primaryDocument": ["q.htm", "k.htm"]}}}).encode(),
              "u", "SEC", "application/json", "t", 200)
    store.put(f"xbrl_instance:{cik}:0001089063-24-000121", _instance([("CommonClassAMember", 57_903_976), ("CommonClassBMember", 23_570_633)],
              [(None, "DKS")], [(None, "Common Stock, $0.01 par value")]), "u", "SEC", "application/xml", "t", 200)
    store.put(f"sec_filing_doc:{cik}:0001089063-24-000037", b"<p>We also have shares of Class B common stock outstanding, which are not "
              b"listed or traded on any stock exchange or other market.</p>", "u", "SEC", "text/html", "t", 200)
    t = int(datetime(2024, 12, 27, 21, tzinfo=UTC).timestamp())
    store.put("yahoo_chart:DKS:5y", json.dumps({"chart": {"result": [{"timestamp": [t], "indicators": {"quote": [{"close": [230.0]}]}}],
              "error": None}}).encode(), "u", "Y", "application/json", "t", 200)
    maps = json.loads((Path(chain.GE) / "symbol_mappings_2024-12-31.json").read_text(encoding="utf-8"))
    listings = {"d": {"cik": cik, "yahoo": "DKS"}}
    ov, un = chain.cover_mcap_overrides(store, listings, amc_dt(), symbol_mappings=maps)
    assert ov["d"]["status"] == "COVER_CLASS_SUM_LOWER_BOUND" and ov["d"]["mcap"] == 57_903_976 * 230.0
    assert chain.equal_economics_upper_bound(ov["d"]) == (57_903_976 + 23_570_633) * 230.0
    assert chain.cover_mcap_overrides(store, listings, amc_dt())[1] == {"d": "NO_PRICED_CLASS"}  # without review: fail-closed
    bad = json.loads(json.dumps(maps))
    bad["issuers"][cik]["citations"][0]["quote"] = "We also have shares of Class B common stock outstanding, which trade on the NYSE."
    assert chain.cover_mcap_overrides(store, listings, amc_dt(), symbol_mappings=bad)[1] == {"d": "NO_PRICED_CLASS"}


def test_run35_unit_only_ratio_quote_needs_a_pairing_quote_naming_unit_and_class(tmp_path):
    chain = _mod("chain_ryan", "run_top500_gate_chain.py")
    store, cik, ov, det = _class_econ_store(tmp_path)
    doc = ("<p>Each LLC Unitholder, other than the Company, has an equivalent number of shares of our Class B common stock "
           "which are entitled to 10 votes per share for each LLC Common Unit held. LLC Common Units may be exchanged for "
           "shares of Class A common stock on a one-for-one basis at the election of the holder.</p>")
    store.put(f"sec_filing_doc:{cik}:0001234567-24-000009", doc.encode(), "u", "SEC", "text/html", "t", 200)
    aid = f"sec_filing_doc:{cik}:0001234567-24-000009"
    pair = "Each LLC Unitholder, other than the Company, has an equivalent number of shares of our Class B common stock which are entitled to 10 votes per share for each LLC Common Unit held."
    ratio = "LLC Common Units may be exchanged for shares of Class A common stock on a one-for-one basis at the election of the holder."
    d = {"listed_member": "CommonClassAMember", "classes": {"CommonClassBMember": {
        "basis": "PAIRED_UNITS_EXCHANGEABLE_INTO_LISTED", "ratio": 1, "paired_instrument": "LLC Common Unit",
        "citations": [{"artifact_id": aid, "quote": pair, "supports": ["pairing"]},
                      {"artifact_id": aid, "quote": ratio, "supports": ["exchange_ratio"]}]}}}
    mcap, ev = chain.verify_class_economics(store, cik, ov, d, amc_dt())
    assert mcap == 400 * 10.0 and ev["status"] == "ECONOMIC_EQUIVALENT_DETERMINED"
    no_inst = json.loads(json.dumps(d))
    del no_inst["classes"]["CommonClassBMember"]["paired_instrument"]
    assert chain.verify_class_economics(store, cik, ov, no_inst, amc_dt())[0] is None  # unit-only quote needs the declared instrument
    other = json.loads(json.dumps(d))
    other["classes"]["CommonClassBMember"]["paired_instrument"] = "OpCo Unit"
    assert chain.verify_class_economics(store, cik, ov, other, amc_dt())[0] is None


def test_run37_official_pipeline_rebuilds_snapshot_only_from_passing_gate_evidence(tmp_path, monkeypatch):
    op = _mod("op", "official_pipeline.py")
    monkeypatch.setattr(op, "GE", tmp_path)
    cands = [{"company_id": f"c{i}", "ticker": f"T{i}", "cik": str(i).zfill(10), "shares": 1000.0 - i, "price": 10.0,
              "shares_available_at": "2024-11-01T00:00:00+00:00", "price_observed_at": "2024-12-30T21:00:00+00:00",
              "shares_basis": "COMPANYFACTS_PIT", "price_basis": "CLOSE_X_POST_AS_OF_SPLIT_FACTOR", "gate_mcap": (1000.0 - i) * 10}
             for i in range(5)]
    ev = {"official_top500_declared": True, "gate_snapshot_consistency": {"passed": True}, "official_snapshot_candidates": cands,
          "top500": [{"company_id": f"c{i}"} for i in range(5)]}
    (tmp_path / "gate_chain_2024-12-31_real_gha.json").write_text(json.dumps(ev))
    snap, st = op.load_official("2024-12-31")
    assert st["status"] == "OFFICIAL" and list(snap.ids()) == [f"c{i}" for i in range(5)] and snap.policy_status.value == "OFFICIAL"
    bad = {**ev, "official_top500_declared": False, "official_blockers": ["PROMOTION_GATE_V2_FAILED"]}
    (tmp_path / "gate_chain_2024-09-30_real_gha.json").write_text(json.dumps(bad))
    assert op.load_official("2024-09-30")[1]["status"] == "NOT_OFFICIAL"
    swapped = {**ev, "top500": [{"company_id": f"c{i}"} for i in (1, 0, 2, 3, 4)]}
    (tmp_path / "gate_chain_2024-06-30_real_gha.json").write_text(json.dumps(swapped))
    assert op.load_official("2024-06-30")[1]["status"] == "REBUILT_SNAPSHOT_DIFFERS_FROM_GATE"
    assert op.load_official("2024-03-31")[1]["status"] == "NO_GATE_EVIDENCE"
    monkeypatch.setattr(sys, "argv", ["x", "--store", str(tmp_path), "--dates", "2024-06-30,2024-09-30", "--final-horizon", "2025-03-31"])
    op.main()
    out = json.loads((tmp_path / "official_pipeline_2024-06-30_2024-09-30.json").read_text())
    assert out["walk_forward_status"] == "BLOCKED_FEWER_THAN_3_DATES" and out["status"] == "BLOCKED_NO_OFFICIAL_DATE"


def test_run40_dated_evidence_keeps_only_citations_filed_on_or_before_the_target_date():
    dde = _mod("dde", "derive_dated_evidence.py")
    ce = {"as_of": "2024-12-31", "issuers": {
        "1": {"symbol": "OLD", "classes": {"CommonClassBMember": {"basis": "CONVERTIBLE_INTO_LISTED", "citations": [
            {"filed": "2024-02-23", "supports": ["conversion_ratio"], "quote": "q1"},
            {"filed": "2024-10-31", "supports": ["equal_dividend_context"], "quote": "q2"}]}}},
        "2": {"symbol": "NEW", "classes": {"CommonClassDMember": {"basis": "PAIRED_UNITS_EXCHANGEABLE_INTO_LISTED", "citations": [
            {"filed": "2024-02-27", "supports": ["exchange_ratio"], "quote": "q3"},
            {"filed": "2024-11-12", "supports": ["pairing"], "quote": "q4"}]}}}}}
    doc, dropped = dde.derive_class_economics(ce, "2024-09-30")
    assert list(doc["issuers"]) == ["1"] and [c["filed"] for c in doc["issuers"]["1"]["classes"]["CommonClassBMember"]["citations"]] == ["2024-02-23"]
    assert "NEW" in dropped and doc["derived_from"] == "2024-12-31" and doc["as_of"] == "2024-09-30"
    sm = {"as_of": "2024-12-31", "issuers": {"9": {"symbol": "LATE", "citations": [{"filed": "2024-11-01", "quote": "x"}]}}}
    doc2, dropped2 = dde.derive_symbol_mappings(sm, "2024-09-30")
    assert doc2["issuers"] == {} and dropped2 == {"LATE": "NO_CITATION_FILED_ON_OR_BEFORE_AS_OF"}
    # the committed 2024-09-30 files contain no citation filed after 2024-09-30
    ge = Path(dde.GE)
    for name in ("class_economics_2024-09-30.json", "symbol_mappings_2024-09-30.json"):
        d = json.loads((ge / name).read_text(encoding="utf-8"))
        cites = [c for v in d["issuers"].values() for cd in (v.get("classes") or {"_": v}).values() for c in cd.get("citations") or []]
        assert cites and all(c["filed"] <= "2024-09-30" for c in cites), name


def test_run42_nport_exception_is_per_as_of_and_records_look_ahead(tmp_path):
    chain = _mod("chain_npr3", "run_top500_gate_chain.py")
    store, cik, ev, exc, px = _nport_setup(tmp_path)
    listings = {"p": {"cik": cik, "yahoo": "PINC"}}
    out = chain.apply_nport_reported_prices(store, {}, listings, exc, ev, amc_dt())["PINC"]
    assert out["status"] == "APPLIED" and out["valuation_date"] == "2024-12-31" and out["filing_date"] == "2025-02-24"
    assert out["available_at"] == "2025-02-24" and out["look_ahead"] is True and out["price_type"] == "NPORT_REPORTED_VALUE"
    other = {**ev, "as_of": "2024-09-30"}  # another date's evidence (or value) is never reused
    assert "EVIDENCE_OR_EXCEPTION_FOR_ANOTHER_AS_OF" in chain.apply_nport_reported_prices(store, {}, listings, exc, other, amc_dt())["PINC"]["failures"]
    other_exc = {**exc, "as_of": "2024-09-30"}
    assert "EVIDENCE_OR_EXCEPTION_FOR_ANOTHER_AS_OF" in chain.apply_nport_reported_prices(store, {}, listings, other_exc, ev, amc_dt())["PINC"]["failures"]


def test_run43_total_member_dropped_partial_economics_and_equal_per_share_wording(tmp_path):
    chain = _mod("chain_r43", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    cik = "0001849253"
    aid = _sub_with_filing(store, cik)
    # RYAN Q2-2024 cover: a CommonStockMember TOTAL equal to Class A + Class B
    store.put(aid, _instance([("CommonStockMember", 261_448_198), ("CommonClassAMember", 120_351_717), ("CommonClassBMember", 141_096_481)],
                             [("CommonClassAMember", "RYAN")]), "u", "SEC", "application/xml", "t", 200)
    t = int(datetime(2024, 9, 27, 21, tzinfo=UTC).timestamp())
    store.put("yahoo_chart:RYAN:5y", json.dumps({"chart": {"result": [{"timestamp": [t], "indicators": {"quote": [{"close": [66.0]}]}}],
              "error": None}}).encode(), "u", "Y", "application/json", "t", 200)
    ov, _ = chain.cover_mcap_overrides(store, {"r": {"cik": cik, "yahoo": "RYAN"}}, amc_dt())
    o = ov["r"]
    assert o["total_member_dropped"]["member"] == "CommonStockMember" and {c["member"] for c in o["classes"]} == {"CommonClassAMember", "CommonClassBMember"}
    assert o["mcap"] == 120_351_717 * 66.0 and chain.equal_economics_upper_bound(o) == 261_448_198 * 66.0  # counted once
    # partial: one unlisted class proven, another not -> higher LOWER BOUND, never exact
    s2, cik2, ov2, det2 = _class_econ_store(tmp_path / "p")
    ov2 = {**ov2, "classes": ov2["classes"] + [{"member": "CommonClassCMember", "shares": 50, "price": None, "symbol": None}]}
    mcap, ev = chain.verify_class_economics(s2, cik2, ov2, det2, amc_dt())
    assert ev["status"] == "ECONOMIC_EQUIVALENT_PARTIAL_LOWER_BOUND" and ev["undetermined_classes"] == ["CommonClassCMember"]
    overrides = {"u": dict(ov2)}
    chain.apply_class_economics(s2, overrides, {"u": {"cik": cik2, "yahoo": "UPC"}}, {"issuers": {cik2: det2}}, amc_dt())
    u = overrides["u"]
    assert u["status"] == "COVER_CLASS_SUM_LOWER_BOUND" and u["mcap"] == (100 + 300) * 10.0
    assert chain.equal_economics_upper_bound(u) == (100 + 300 + 50) * 10.0  # proven class not double counted in the bound
    import re
    assert re.search(chain.CLAIM_PATTERNS["identical_rights"], "Class A common stock and Class B common stock share proportionately, "
                     "on a per share basis, in our net income (losses) and participate equally in the dividends")
    frc = _mod("frc_ord", "fetch_class_rights_evidence.py")
    assert "Class B ordinary shares" in frc.class_phrases("CommonClassBMember")


def test_run44_registration_doc_share_count_amtm_spinoff(tmp_path):
    """AMTM (Amentum) spun off from Jacobs 2024-09-27, no 10-K/10-Q by 2024-09-30: the 8-K filed on the spin date
    ('resulting in 153,280,369 issued and outstanding shares of SpinCo Common Stock') is the only PIT-safe source."""
    chain = _mod("chain_amtm", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    cik = "0002011286"
    store.put(f"submissions:{cik}", json.dumps({"tickers": ["AMTM"], "filings": {"recent": {
        "form": ["8-K", "10-12B/A"], "filingDate": ["2024-09-27", "2024-09-13"],
        "accessionNumber": ["0001193125-24-227910", "0001193125-24-218486"],
        "primaryDocument": ["form8k.htm", "form10.htm"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put(f"sec_filing_doc:{cik}:0001193125-24-227910",
              b"<p>The Split Amendment increased the number of authorized shares of SpinCo Common Stock to "
              b"1,000,000,000, and effected a stock split of the outstanding shares of SpinCo Common Stock, resulting "
              b"in 153,280,369 issued and outstanding shares of SpinCo Common Stock</p>", "u", "SEC", "text/html", "t", 200)
    t = int(datetime(2024, 9, 27, 13, 30, tzinfo=UTC).timestamp())
    store.put("yahoo_chart:AMTM:5y", json.dumps({"chart": {"result": [{"timestamp": [t],
              "indicators": {"quote": [{"close": [21.5]}]}}], "error": None}}).encode(), "u", "Y", "application/json", "t", 200)
    listings = {"a": {"cik": cik, "yahoo": "AMTM"}}
    ov = {}
    ev = chain.registration_share_count_overrides(store, listings, ov, amc_dt())
    assert ev["AMTM"]["status"] == "APPLIED" and ev["AMTM"]["shares"] == 153_280_369
    assert ov["a"]["status"] == "REGISTRATION_DOC_SHARE_COUNT" and ov["a"]["mcap"] == 153_280_369 * 21.5
    # a later periodic filing's count must NOT be used even if present in the store under a later date
    late_cf = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
        {"filed": "2025-01-15", "val": 999_999_999}]}}}}}
    store.put(f"companyfacts:{cik}", json.dumps(late_cf).encode(), "u", "SEC", "application/json", "t", 200)
    ov2 = {}
    ev2 = chain.registration_share_count_overrides(store, listings, ov2, amc_dt())
    assert ev2["AMTM"]["shares"] == 153_280_369  # unaffected by the post-as_of companyfacts fact


def test_run44_registration_doc_share_count_ambiguous_or_missing_stays_blocker(tmp_path):
    chain = _mod("chain_amtm2", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    cik = "0009999999"
    store.put(f"submissions:{cik}", json.dumps({"tickers": ["ZZZ"], "filings": {"recent": {
        "form": ["8-K"], "filingDate": ["2024-09-27"], "accessionNumber": ["a"], "primaryDocument": ["d.htm"]}}}).encode(),
              "u", "SEC", "application/json", "t", 200)
    listings = {"z": {"cik": cik, "yahoo": "ZZZ"}}
    assert chain.registration_share_count_overrides(store, listings, {}, amc_dt())["ZZZ"]["status"] == "NO_COUNT_FOUND"
    # a single document stating two different counts near the pattern is ambiguous at the per-document level
    # (never guessed which one is right) -> no candidate at all from that document
    store.put(f"sec_filing_doc:{cik}:a", b"<p>100,000,000 issued and outstanding shares of Common Stock. Separately, "
              b"200,000,000 issued and outstanding shares of Common Stock were also reported.</p>",
              "u", "SEC", "text/html", "t", 200)
    assert chain.registration_share_count_overrides(store, listings, {}, amc_dt())["ZZZ"]["status"] == "NO_COUNT_FOUND"
    # two separate documents each stating their OWN unique count, but disagreeing with each other -> AMBIGUOUS_COUNTS
    store.put(f"submissions:{cik}", json.dumps({"tickers": ["ZZZ"], "filings": {"recent": {
        "form": ["8-K", "10-12B/A"], "filingDate": ["2024-09-27", "2024-09-13"],
        "accessionNumber": ["a", "b"], "primaryDocument": ["d.htm", "e.htm"]}}}).encode(),
              "u", "SEC", "application/json", "t", 200)
    store.put(f"sec_filing_doc:{cik}:a", b"<p>100,000,000 issued and outstanding shares of Common Stock.</p>",
              "u", "SEC", "text/html", "t", 200)
    store.put(f"sec_filing_doc:{cik}:b", b"<p>250,000,000 issued and outstanding shares of Common Stock.</p>",
              "u", "SEC", "text/html", "t", 200)
    assert chain.registration_share_count_overrides(store, listings, {}, amc_dt())["ZZZ"]["status"] == "AMBIGUOUS_COUNTS"


def test_run44_registration_doc_evidence_exists_in_committed_2024_09_30_run(tmp_path):
    """Regression against the real fetched evidence: AMTM's 8-K text does state the unique count."""
    import sys as _sys
    chain = _mod("chain_amtm3", "run_top500_gate_chain.py")
    ge = Path(chain.GE)
    diag_path = ge / "share_count_diagnostic_0002011286_2024-09-30.json"
    if not diag_path.exists():
        return  # evidence not yet fetched in this environment
    diag = json.loads(diag_path.read_text(encoding="utf-8"))
    frc = _mod("frc_amtm", "fetch_class_rights_evidence.py")
    found = None
    for d in diag["documents"]:
        if d["form"] == "8-K" and d["filed"] == "2024-09-27":
            found = d
    assert found is not None


def test_run44_rprx_paired_units_together_with_the_related_wording(tmp_path):
    """RPRX (Royalty Pharma plc): 'Class B ordinary shares, together with the related RP Holdings Class B Interests,
    are exchangeable into Class A ordinary shares on a one-for-one basis' -- a pairing phrasing distinct from
    'an equal number of shares of Class X' (RKT/TPG/TKO wording)."""
    chain = _mod("chain_rprx", "run_top500_gate_chain.py")
    import re
    quote = ("Our outstanding Class B ordinary shares are, however, considered potentially dilutive shares of Class A "
             "ordinary shares because Class B ordinary shares, together with the related RP Holdings Class B Interests, "
             "are exchangeable into Class A ordinary shares on a one-for-one basis.")
    assert re.search(chain.CLAIM_PATTERNS["pairing"], quote, re.I)
    assert re.search(chain.CLAIM_PATTERNS["exchange_ratio"], quote, re.I)
    store, cik, ov, det = _class_econ_store(tmp_path)
    d2 = json.loads(json.dumps(det))
    d2["classes"]["CommonClassBMember"]["citations"] = [{
        "artifact_id": f"sec_filing_doc:{cik}:0001234567-24-000009", "quote": quote, "supports": ["pairing", "exchange_ratio"]}]
    d2["classes"]["CommonClassBMember"]["paired_instrument"] = "RP Holdings Class B Interest"
    store.put(f"sec_filing_doc:{cik}:0001234567-24-000009", ("<p>" + quote + "</p>").encode(), "u", "SEC", "text/html", "t", 200)
    mcap, ev = chain.verify_class_economics(store, cik, ov, d2, amc_dt())
    assert ev["status"] == "ECONOMIC_EQUIVALENT_DETERMINED" and mcap == 400 * 10.0


def test_run45_rprx_one_for_one_with_extraction_space_proves_exchange_ratio(tmp_path):
    """Run #45: the stored RPRX 10-K text reads 'one -for-one' (an inline tag split the word). The ratio claim must
    still be proven from that verbatim quote; unrelated wording still does not prove a ratio."""
    chain = _mod("chain_rprx45", "run_top500_gate_chain.py")
    import re
    quote = ("Our outstanding Class B ordinary shares are, however, considered potentially dilutive shares of Class A "
             "ordinary shares because Class B ordinary shares, together with the related RP Holdings Class B Interests, "
             "are exchangeable into Class A ordinary shares on a one -for-one basis.")
    assert re.search(chain.CLAIM_PATTERNS["exchange_ratio"], quote, re.I)
    assert re.search(chain.CLAIM_PATTERNS["pairing"], quote, re.I)
    assert not re.search(chain.CLAIM_PATTERNS["exchange_ratio"], "exchangeable into Class A ordinary shares at a ratio "
                         "determined by the board", re.I)
    assert not re.search(chain.CLAIM_PATTERNS["exchange_ratio"], "one for two basis", re.I)
    store, cik, ov, det = _class_econ_store(tmp_path)
    d2 = json.loads(json.dumps(det))
    d2["classes"]["CommonClassBMember"]["citations"] = [{
        "artifact_id": f"sec_filing_doc:{cik}:0001234567-24-000009", "quote": quote, "supports": ["pairing", "exchange_ratio"]}]
    d2["classes"]["CommonClassBMember"]["paired_instrument"] = "RP Holdings Class B Interest"
    store.put(f"sec_filing_doc:{cik}:0001234567-24-000009", ("<p>" + quote + "</p>").encode(), "u", "SEC", "text/html", "t", 200)
    mcap, ev = chain.verify_class_economics(store, cik, ov, d2, amc_dt())
    assert ev["status"] == "ECONOMIC_EQUIVALENT_DETERMINED" and mcap == 400 * 10.0


def test_run44_committed_2024_09_30_class_economics_all_verify_against_stored_evidence():
    """Every issuer in the committed 2024-09-30 class_economics file must verify (quotes found verbatim in the
    referenced filing document, filed on or before 2024-09-30) using the actual fetched evidence, when present."""
    chain = _mod("chain_ce0930", "run_top500_gate_chain.py")
    ge = Path(chain.GE)
    ce_path = ge / "class_economics_2024-09-30.json"
    store_dir = ge.parents[1] / "data" / "raw"
    if not ce_path.exists() or not store_dir.exists():
        return
    ce = json.loads(ce_path.read_text(encoding="utf-8"))
    store = RawDatasetStore(store_dir)
    for cik, det in ce["issuers"].items():
        for member, cd in det["classes"].items():
            for c in cd["citations"]:
                assert c["filed"] <= "2024-09-30", (det["symbol"], member, c["filed"])
                if store.has(c["artifact_id"]):
                    frc = _mod("frc_verify", "fetch_class_rights_evidence.py")
                    text = frc.html_text(store.get_bytes(c["artifact_id"]))
                    assert c["quote"] in text, (det["symbol"], member, c["quote"][:80])


def test_fetch_stooq_prices_resolves_dated_cik_candidates_file(tmp_path):
    """fetch_stooq_prices.py's --cik-candidates default (run #48, 2024-06-30: WRK NO_AS_OF_PRICE after Yahoo+Tiingo)
    must use the per-as_of delisted_cik_candidates file when it exists, same rule as fetch_tiingo_prices.py (a PIT
    CIK correction such as BLK's 2024-10-01 reorganisation is per as_of, never the 2024-12-31 file by default)."""
    fsp = _mod("fsp_resolve", "fetch_stooq_prices.py")
    ge = tmp_path / "gate_evidence"
    ge.mkdir()
    (ge / "delisted_cik_candidates_2024-12-31.json").write_text("{}", encoding="utf-8")
    assert fsp.resolve_cik_candidates(ge, "2024-06-30").name == "delisted_cik_candidates_2024-12-31.json"
    (ge / "delisted_cik_candidates_2024-06-30.json").write_text("{}", encoding="utf-8")
    assert fsp.resolve_cik_candidates(ge, "2024-06-30").name == "delisted_cik_candidates_2024-06-30.json"


def test_fetch_stooq_prices_written_only_after_calibration_and_only_if_yahoo_still_missing(tmp_path):
    """Regression: a Stooq close is written to the yahoo_chart replay id only when (a) the control-symbol
    calibration passes and (b) the target symbol still has no Yahoo bar on/before as_of; a symbol whose Yahoo bar
    already exists must never be overwritten by a Stooq fallback."""
    fsp = _mod("fsp_write_rule", "fetch_stooq_prices.py")
    import inspect
    src = inspect.getsource(fsp.run)
    assert "YAHOO_AS_OF_BAR_PRESENT" in src and "NOT_WRITTEN_CALIBRATION_FAILED" in src
