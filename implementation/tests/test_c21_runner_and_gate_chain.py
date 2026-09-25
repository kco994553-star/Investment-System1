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
    rep = chain.run_chain(store, {"a": {"cik": "1", "yahoo": "OKK"}, "b": {"cik": "2", "yahoo": "NOSH"},
                                  "c": {"cik": "3", "yahoo": "NOPX"}}, "2024-12-31", [], [], None, None)
    assert {k: v["reason"] for k, v in rep["unrankable_issuers"].items()} == {"NOSH": "SHARES_MISSING", "NOPX": "NO_AS_OF_PRICE"}


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
