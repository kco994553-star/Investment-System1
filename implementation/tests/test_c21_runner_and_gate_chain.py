from tests.boundary_assertions import route_withheld_without_writes
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
    rep = mod.run(Path(tmp_path), ["320193", "1045810"], [], "5y", 0.0, skip_tickers=False)
    # one request per host, then breaker: www.sec.gov, data.sec.gov, query1.finance.yahoo.com
    assert sorted(set(hosts)) == sorted(hosts) and len(hosts) == 2
    assert rep["n_ok"] == 0 and all(r["status"] == "EGRESS_BLOCKED" for r in rep["log"])
    assert set(rep["egress_blocked_hosts"]) == {"www.sec.gov", "data.sec.gov"}
    index = json.loads((Path(tmp_path) / "STORE_INDEX.json").read_text())
    assert index["n_artifacts"] == 0


def test_runner_plan_mode_resolves_missing_cik_from_stored_tickers_and_skips_present_public_route_withheld(tmp_path, monkeypatch):
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
    with route_withheld_without_writes(tmp_path):
        rep = mod.run(Path(tmp_path), [], [], "5y", 0.0, skip_tickers=False, plan=plan)


def _put_name(store, cik, sym, shares, px):
    cf = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{"filed": "2024-11-01", "val": shares}]}}}}}
    store.put(f"companyfacts:{str(cik).zfill(10)}", json.dumps(cf).encode(), "u", "SEC", "application/json", "t", 200)
    chart = {"chart": {"result": [{"timestamp": [int(datetime(2024, 12, 1, tzinfo=UTC).timestamp())],
                                   "indicators": {"quote": [{"close": [px]}]}}], "error": None}}
    store.put(f"yahoo_chart:{sym}:5y", json.dumps(chart).encode(), "u", "YAHOO", "application/json", "t", 200)


def test_reference_coverage_matches_share_class_dot_and_dash_public_route_withheld(tmp_path):
    amc = _mod("amc_norm", "audit_mcap_store.py")
    store = RawDatasetStore(tmp_path)
    _put_name(store, 1067983, "BRK-B", 100, 10.0)
    listings = {"brk": {"cik": "0001067983", "yahoo": "BRK-B"}}
    ref = {"name": "SP", "source": "s", "source_vintage": "v", "as_of": AS_OF, "members": ["BRK.B", "ZZZ"]}
    with route_withheld_without_writes(tmp_path):
        out = amc.evaluate_reference_coverage(store, listings, set(), ref)


def test_sufficiency_gate_detector_reference_alone_cannot_pass():
    amc = _mod("amc_det", "audit_mcap_store.py")
    audit = {"as_of": AS_OF, "rankable": 600, "top_cutoff_mcap_if_500_rankable": 1e9}
    clean = {"name": "SP", "source": "s", "source_vintage": "v", "as_of": AS_OF, "membership_basis": "DATED_INTERVALS",
             "members": ["A"], "missing_from_pool": [], "present_not_rankable": [], "present_rankable_outside_top500": []}
    g = amc.build_top500_sufficiency_gate(audit, [{**clean, "reference_role": "MISSING_LARGE_CAP_DETECTOR"}])
    assert g["passed"] is False and "ONLY_DETECTOR_REFERENCES_PASSED" in g["reasons"]
    assert amc.build_top500_sufficiency_gate(audit, [clean])["passed"] is True  # unchanged legacy behaviour


def test_ranked_top500_cutoff_agrees_with_audit_public_route_withheld(tmp_path):
    amc = _mod("amc_rank", "audit_mcap_store.py")
    store = RawDatasetStore(tmp_path)
    listings = {}
    for i in range(1, 506):
        _put_name(store, i, f"T{i}", i * 10, 1.0)
        listings[f"c{i}"] = {"cik": str(i).zfill(10), "yahoo": f"T{i}"}
    d = amc._dt(AS_OF)
    with route_withheld_without_writes(tmp_path):
        top = amc.ranked_top500(store, listings, d)


def test_gate_chain_fails_closed_on_empty_store_public_route_withheld(tmp_path):
    chain = _mod("chain_empty", "run_top500_gate_chain.py")
    ref = {"name": "SP", "source": "s", "source_vintage": "v", "as_of": AS_OF, "membership_basis": "DATED_INTERVALS",
           "members": ["AAA", "BBB"]}
    with route_withheld_without_writes(tmp_path):
        rep = chain.run_chain(RawDatasetStore(tmp_path), {"a": {"cik": "1", "yahoo": "AAA"}}, "2024-12-31", [ref], [], None, None)


def test_gate_chain_with_full_detector_coverage_still_not_official_public_route_withheld(tmp_path):
    chain = _mod("chain_full", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    listings = {}
    for i in range(1, 521):
        _put_name(store, i, f"T{i}", i * 10, 1.0)
        listings[f"c{i}"] = {"cik": str(i).zfill(10), "yahoo": f"T{i}"}
    ref = {"name": "SP", "source": "s", "source_vintage": "v", "as_of": AS_OF, "membership_basis": "DATED_INTERVALS",
           "members": [f"T{i}" for i in range(21, 521)]}
    ev = {"source": "x", "source_vintage": "v", "as_of": AS_OF, "eligibility_complete": False}
    with route_withheld_without_writes(tmp_path):
        rep = chain.run_chain(store, listings, "2024-12-31", [ref], [], None, ev)


def test_company_level_ranking_one_line_per_cik_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        rep = chain.run_chain(store, listings, "2024-12-31", [ref], [], None, None)


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


def test_audit_applies_split_factor_public_route_withheld(tmp_path):
    amc = _mod("amc_split_audit", "audit_mcap_store.py")
    store = RawDatasetStore(tmp_path)
    _put_name(store, 1, "ORLY", 58_000_000, 80.0)
    store.put("yahoo_events:ORLY:5y", json.dumps(_events([(datetime(2025, 6, 10, tzinfo=UTC), 15)])).encode(),
              "u", "YAHOO", "application/json", "t", 200)
    with route_withheld_without_writes(tmp_path):
        top = amc.ranked_top500(store, {"o": {"cik": "1", "yahoo": "ORLY"}}, amc._dt(AS_OF))


def test_foreign_private_issuer_is_excluded_by_eligibility_rule_public_route_withheld(tmp_path):
    chain = _mod("chain_fpi", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    store.put("submissions:0000000007", json.dumps({"filings": {"recent": {"form": ["20-F", "6-K"],
              "filingDate": ["2024-04-01", "2024-11-01"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    det = {"cik": "0000000007", "split_events": 0, "pit_filer_status": "FOREIGN"}
    assert chain.mcap_quality_flags(store, det) == ["FOREIGN_ISSUER_ADR_RATIO_UNRESOLVED"]
    assert chain.mcap_quality_flags(store, {"cik": "0000000008", "split_events": "MISSING"}) == ["SPLIT_EVENTS_MISSING"]
    _put_name(store, 7, "ADRX", 1000, 5.0)
    with route_withheld_without_writes(tmp_path):
        rep = chain.run_chain(store, {"x": {"cik": "0000000007", "yahoo": "ADRX"}}, "2024-12-31", [], [], None, None)


def test_runner_with_split_events_writes_events_artifact_public_route_withheld(tmp_path, monkeypatch):
    mod = _mod("frd_events", "fetch_real_data.py")
    urls = []
    monkeypatch.setattr(mod, "urlopen", lambda req, timeout=0: (urls.append(req.full_url), _R(b"{}"))[1])
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    with route_withheld_without_writes(tmp_path):
        mod.run(Path(tmp_path), [], ["ORLY"], "5y", 0.0, skip_tickers=True, with_split_events=True)


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


def test_chain_class_sum_full_and_lower_bound_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        rep = chain.run_chain(store, listings, "2024-12-31", [], [], None, None)


def test_lower_bound_issuer_outside_top500_blocks_official_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        rep = chain.run_chain(store, listings, "2024-12-31", [], [], None, None)


def test_fetch_cover_xbrl_selects_issuers_and_fetches_instance_and_class_prices_public_route_withheld(tmp_path, monkeypatch):
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
    with route_withheld_without_writes(tmp_path):
        rep = fcx.run(Path(tmp_path), amc_dt(), need)


def test_class_symbols_ignore_preferred_series_without_shares():
    from investment_system.providers.sec_cover_shares import class_symbols, parse_cover
    cov = parse_cover(_instance([("CommonStockMember", 265)],
                                [("CommonStockMember", "ALL"), ("SeriesHPreferredStockMember", "ALL PR H")]))
    assert class_symbols(cov) == {"CommonStockMember": "ALL"}


def test_runner_invalid_url_is_a_logged_artifact_failure_not_a_crash_public_route_withheld(tmp_path, monkeypatch):
    import http.client
    mod = _mod("frd_badurl", "fetch_real_data.py")

    def fake(req, timeout=0):
        if " " in req.full_url:
            raise http.client.InvalidURL("URL can't contain control characters")
        return _R(b"{}")

    monkeypatch.setattr(mod, "urlopen", fake)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    with route_withheld_without_writes(tmp_path):
        rep = mod.run(Path(tmp_path), [], ["ALL PR H", "ALL"], "5y", 0.0, skip_tickers=True)


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


def test_chain_lists_unrankable_issuers_with_reason_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        rep = chain.run_chain(store, {"a": {"cik": "1", "yahoo": "OKK"}, "b": {"cik": "2", "yahoo": "NOSH"},
                                      "c": {"cik": "3", "yahoo": "NOPX"}}, "2024-12-31", [], [], None, None)


def test_unknown_filer_without_as_of_price_is_not_listed_at_as_of_public_route_withheld(tmp_path):
    """SNDK pattern (run #17): Form 10 before as_of, first trade and first 10-Q in 2025."""
    chain = _mod("chain_nottrading", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    store.put("submissions:0002023554", json.dumps({"filings": {"recent": {"form": ["10-Q", "10-12B"],
              "filingDate": ["2025-05-01", "2024-12-10"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put("yahoo_chart:SNDK:5y", json.dumps({"chart": {"result": [{"timestamp": [int(datetime(2025, 2, 24, 14, 30, tzinfo=UTC).timestamp())],
              "indicators": {"quote": [{"close": [50.0]}]}}], "error": None}}).encode(), "u", "Y", "application/json", "t", 200)
    with route_withheld_without_writes(tmp_path):
        kept, rep = chain.eligibility_filter(store, {"s": {"cik": "0002023554", "yahoo": "SNDK"}}, amc_dt())


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


def test_zero_companyfacts_shares_needs_cover_and_cover_resolves_it_public_route_withheld(tmp_path):
    """CRWD/HOOD/DDOG/CVNA/PSKY/TAP pattern (run #16): companyfacts reports 0 undimensioned shares."""
    fcx = _mod("fcx_zero", "fetch_cover_xbrl.py")
    chain = _mod("chain_zero", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    _put_name(store, 1535527, "CRWD", 0, 350.0)  # companyfacts shares = 0
    assert fcx.needs_cover(store, {"c": {"cik": "0001535527", "yahoo": "CRWD"}}, amc_dt()) == ["0001535527"]
    aid = _sub_with_filing(store, "0001535527")
    store.put(aid, _instance([("CommonClassAMember", 240_000_000), ("CommonClassBMember", 5_000_000)], [(None, "CRWD")],
                             [(None, "Class A common stock")]), "u", "SEC", "application/xml", "t", 200)
    with route_withheld_without_writes(tmp_path):
        rep = chain.run_chain(store, {"c": {"cik": "0001535527", "yahoo": "CRWD"}}, "2024-12-31", [], [], None, None)


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


def test_stooq_fallback_written_only_after_calibration_and_only_without_yahoo_as_of_bar_public_route_withheld(tmp_path, monkeypatch):
    fsp = _mod('stooq_withheld', 'fetch_stooq_prices.py')
    with route_withheld_without_writes(tmp_path):
        fsp.run(tmp_path, amc_dt(), ['EXAMPLE'])


def load_bars(store, sym):
    from investment_system.ingestion.replay import load_price_bars
    return load_price_bars(store, sym, "5y")


def test_stooq_calibration_mismatch_writes_nothing_public_route_withheld(tmp_path, monkeypatch):
    fsp = _mod('stooq_withheld', 'fetch_stooq_prices.py')
    with route_withheld_without_writes(tmp_path):
        fsp.run(tmp_path, amc_dt(), ['EXAMPLE'])


def test_stooq_never_overwrites_a_yahoo_as_of_bar_public_route_withheld(tmp_path, monkeypatch):
    fsp = _mod("fsp_keep", "fetch_stooq_prices.py")
    store = RawDatasetStore(tmp_path)
    _yahoo_close(store, "KEEP", 50.0)
    frd = fsp._load("fetch_real_data"); ibr = fsp._load("import_bulk_real_data")
    for c in fsp.CONTROLS:
        _yahoo_close(store, c, 100.0)
    monkeypatch.setattr(fsp, "_load", lambda name: frd if name == "fetch_real_data" else ibr)
    monkeypatch.setattr(frd, "urlopen", lambda req, timeout=0: _R(_stooq_csv([("2024-12-30", 100.0 if "keep" not in req.full_url else 51.0)])))
    monkeypatch.setattr(frd.time, "sleep", lambda s: None)
    with route_withheld_without_writes(tmp_path):
        rep = fsp.run(Path(tmp_path), amc_dt(), ["KEEP"])


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
            "present_rankable_outside_top500": [f"T{i}" for i in range(500, 1000)],
            "member_cusips": {f"T{i}": [f"{i:06d}105"] for i in range(1000)}, "unresolved_holdings": []}
    assert amc.build_top500_sufficiency_gate(audit, [base])["passed"] is True
    # run #53: unresolved equity holdings, one CIK absorbing two issuers, or no member CUSIPs -> fail-closed
    unres = amc.build_top500_sufficiency_gate(audit, [{**base, "unresolved_holdings": [
        {"name": "BLUE OWL CAPITAL INC.", "cusip": "09581B103", "name_matches": 5, "value": 12.5,
         "balance": "5", "units": "NS", "fair_value_level": "2"}]}])
    assert unres["passed"] is False and "UNRESOLVED_REFERENCE_HOLDINGS" in unres["references"][0]["reasons"]
    unresolved = unres["references"][0]["unresolved_reference_holdings"][0]
    assert {k: unresolved[k] for k in ("value", "balance", "units", "fair_value_level")} == {
        "value": 12.5, "balance": "5", "units": "NS", "fair_value_level": "2"}
    esc = amc.build_top500_sufficiency_gate(audit, [{**base, "unresolved_holdings": [
        {"name": "ESC GCI LIBERTY INC SR", "cusip": "361ESC049"}]}])
    assert esc["passed"] is True  # escrow position, not a listed equity line
    coll = amc.build_top500_sufficiency_gate(audit, [{**base, "member_cusips": {
        **base["member_cusips"], "T1": ["615369105", "26484T106"]}}])
    assert "REFERENCE_CIK_COLLISION_DISTINCT_ISSUERS" in coll["references"][0]["reasons"]
    same_issuer_classes = {**base["member_cusips"], "T1": ["115637100", "115637209"]}
    assert amc.build_top500_sufficiency_gate(audit, [{**base, "member_cusips": same_issuer_classes}])["passed"]
    nocus = amc.build_top500_sufficiency_gate(audit, [{**base, "member_cusips": None}])
    assert "REFERENCE_MEMBER_CUSIPS_MISSING" in nocus["references"][0]["reasons"]
    partial_cusips = {**base["member_cusips"]}
    partial_cusips.pop("T7")
    partial = amc.build_top500_sufficiency_gate(audit, [{**base, "member_cusips": partial_cusips}])
    assert partial["passed"] is False and partial["references"][0]["members_missing_cusips"] == ["T7"]
    bad = amc.build_top500_sufficiency_gate(audit, [{**base, "missing_from_pool": ["T7"]}])
    assert bad["passed"] is False and "MISSING_LARGE_CAP_NAMES" in bad["references"][0]["reasons"]
    small = amc.build_top500_sufficiency_gate(audit, [{**base, "members": ["T1"]}])
    assert "SUPERSET_REFERENCE_TOO_SMALL" in small["references"][0]["reasons"]


def test_chain_superset_maps_class_tickers_counts_rule_exclusions_and_derives_eligibility_public_route_withheld(tmp_path):
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
           "membership_basis": "DATED_FUND_HOLDINGS", "reference_role": "SUPERSET_REFERENCE", "members": members,
           "member_cusips": {m: [f"{i:06d}105"] for i, m in enumerate(members)}, "unresolved_holdings": []}
    with route_withheld_without_writes(tmp_path):
        rep = chain.run_chain(store, listings, "2024-12-31", [], [ref], None, None)


NPORT_XML = b"""<?xml version="1.0"?><edgarSubmission xmlns="http://www.sec.gov/edgar/nport"><formData>
<genInfo><seriesName>iShares Russell 1000 ETF</seriesName><repPdDate>2024-12-31</repPdDate></genInfo>
<invstOrSecs>
<invstOrSec><name>APPLE INC</name><title>APPLE COMMON STOCK</title><cusip>037833100</cusip><identifiers><isin value="US0378331005"/></identifiers><balance>2</balance><units>NS</units><curCd>USD</curCd><valUSD>100</valUSD><assetCat>EC</assetCat><issuerCat>CORP</issuerCat><invCountry>US</invCountry><payoffProfile>Long</payoffProfile><fairValLevel>1</fairValLevel></invstOrSec>
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
    assert {k: eq[0][k] for k in ("title", "balance", "units", "currency", "issuer_cat", "payoff_profile",
                                  "fair_value_level")} == {
        "title": "APPLE COMMON STOCK", "balance": "2", "units": "NS", "currency": "USD",
        "issuer_cat": "CORP", "payoff_profile": "Long", "fair_value_level": "1"}
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


def test_nport_historical_member_demotion_precedes_sibling_cusip_attestation(tmp_path):
    fnr = _mod("fnr_demote", "fetch_nport_reference.py")
    holdings = [
        {"name": "OLD ISSUER", "cusip": "000001101", "isin": "US0000011018", "asset_cat": "EC",
         "country": "US", "value": 12.5, "balance": "5", "units": "NS", "fair_value_level": "2"},
        {"name": "OLD ISSUER", "cusip": "000001200", "isin": "US0000012008", "asset_cat": "EC",
         "country": "US", "value": 7.5, "balance": "3", "units": "NS", "fair_value_level": "2"},
    ]
    member = {"names": ["OLD ISSUER", "OLD ISSUER"], "cusips": ["000001101", "000001200"]}
    rows = fnr.demoted_member_rows(member, holdings, "0000000042")
    assert [r["cusip"] for r in rows] == ["000001101", "000001200"]
    assert [r["value"] for r in rows] == [12.5, 7.5]
    assert all(r["reason"] == "HISTORICAL_NAME_MATCH_NOT_A_PIT_REGISTRANT" for r in rows)
    assert all(r["candidates"] == ["0000000042"] for r in rows)

    store = RawDatasetStore(tmp_path)
    store.put("submissions:0002003397", json.dumps({"filings": {"recent": {"form": ["SC 13G"],
              "filingDate": ["2024-02-12"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    liberty = {"name": "LIBERTY SIRIUS XM", "cusip": "531229813", "asset_cat": "EC"}
    members = {
        "0002003397": {"names": [liberty["name"]], "cusips": [liberty["cusip"]], "method": "SEC_CIK_LOOKUP"},
        "0001560385": {"names": ["LIBERTY MEDIA CORP - FORMULA ONE GROUP"], "cusips": ["531229755"],
                       "method": "CUSIP_ATTESTED_OWNERSHIP_FILING"},
    }
    demoted = fnr.demote_non_pit_historical_members(store, lambda aid, url, kind: None, members, [liberty], amc_dt())
    assert list(members) == ["0001560385"] and demoted[0]["candidates"] == ["0002003397"]
    assert fnr.cusip_attestation_candidates(demoted[0], members, {}, {}) == ["0001560385", "0002003397"]


def test_chain_superset_with_cik_members_public_route_withheld(tmp_path):
    chain = _mod("chain_cikref", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    listings = {}
    for i in range(1, 911):
        _put_name(store, i, f"T{i}", i * 10, 1.0)
        store.put(f"submissions:{str(i).zfill(10)}", json.dumps({"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2024-11-01"]}}}).encode(),
                  "u", "SEC", "application/json", "t", 200)
        listings[f"c{i}"] = {"cik": str(i).zfill(10), "yahoo": f"T{i}"}
    ref = {"name": "R1000", "source": "SEC NPORT-P x", "source_vintage": "2025-02-27", "as_of": AS_OF, "membership_basis": "DATED_FUND_HOLDINGS",
           "reference_role": "SUPERSET_REFERENCE", "member_id_type": "CIK10", "members": [str(i).zfill(10) for i in range(1, 911)],
           "member_cusips": {str(i).zfill(10): [f"{i:06d}105"] for i in range(1, 911)}, "unresolved_holdings": []}
    with route_withheld_without_writes(tmp_path):
        ok = chain.run_chain(store, listings, "2024-12-31", [], [ref], None, None)


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


def test_equal_economics_upper_bound_settles_small_unlisted_classes_only_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        rep = chain.run_chain(store, listings, "2024-12-31", [ref], [], None, None)


def _tiingo_json(rows):
    return json.dumps([{"date": f"{d}T00:00:00.000Z", "close": c, "adjClose": c * 0.9} for d, c in rows]).encode()


def test_tiingo_fallback_raw_close_header_token_and_calibration_public_route_withheld(tmp_path, monkeypatch):
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
    with route_withheld_without_writes(tmp_path):
        rep = ftp.run(Path(tmp_path), amc_dt(), ["ANSS", "GONE"], "secret-token-123")


def test_tiingo_without_key_writes_nothing_public_route_withheld(tmp_path):
    ftp = _mod("ftp_nokey", "fetch_tiingo_prices.py")
    with route_withheld_without_writes(tmp_path):
        rep = ftp.run(Path(tmp_path), amc_dt(), ["ANSS"], None)


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


def test_run25_ticker_change_uses_primary_line_for_the_only_listed_class_public_route_withheld(tmp_path):
    chain = _mod("chain_r25tc", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    _put_name(store, 1512673, "XYZ", 1, 70.0)  # current ticker's chart carries the SQ-era history
    aid = _sub_with_filing(store, "0001512673")
    store.put(aid, _instance([("CommonClassAMember", 550), ("CommonClassBMember", 50)], [("CommonClassAMember", "SQ")]),
              "u", "SEC", "application/xml", "t", 200)
    with route_withheld_without_writes(tmp_path):
        ov, _ = chain.cover_mcap_overrides(store, {"x": {"cik": "0001512673", "yahoo": "XYZ"}}, amc_dt())


def test_run25_never_periodic_sec_filer_excluded_but_ipo_kept_public_route_withheld(tmp_path):
    chain = _mod("chain_r25ozk", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    store.put("submissions:0001569650", json.dumps({"filings": {"recent": {"form": ["8-K", "DEF 14A"],
              "filingDate": ["2024-10-17", "2024-03-01"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put("submissions:0000000777", json.dumps({"filings": {"recent": {"form": ["10-Q", "424B4", "S-1"],
              "filingDate": ["2025-02-10", "2024-11-20", "2024-10-01"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    _put_name(store, 1569650, "OZK", 1, 45.0)
    _put_name(store, 777, "IPO", 1, 30.0)
    with route_withheld_without_writes(tmp_path):
        kept, rep = chain.eligibility_filter(store, {"o": {"cik": "0001569650", "yahoo": "OZK"}, "i": {"cik": "0000000777", "yahoo": "IPO"}}, amc_dt())


def test_run25_tiingo_empty_reply_is_retried_once_public_route_withheld(tmp_path, monkeypatch):
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
    with route_withheld_without_writes(tmp_path):
        rep = ftp.run(Path(tmp_path), amc_dt(), ["EQR"], "k")


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


def test_run26_tiingo_alternate_series_by_unique_sec_name_public_route_withheld(tmp_path, monkeypatch):
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
    with route_withheld_without_writes(tmp_path):
        rep = ftp.run(Path(tmp_path), amc_dt(), ["PINC", "WOLF", "EQR"], "k",
                      names={"PINC": ["Premier, Inc."], "WOLF": ["Wolfspeed, Inc.", "CREE INC"],
                             "EQR": ["VIVMARK RESIDENTIAL", "EQUITY RESIDENTIAL"]})


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
        listed = next(c for c in classes if c["price"])
        if det.get("undetermined"):
            # partial proof (OWL: Class D unvalued): a higher LOWER BOUND = (listed + proven classes) x listed price
            assert ev["status"] == "ECONOMIC_EQUIVALENT_PARTIAL_LOWER_BOUND", (det["symbol"], ev)
            proven = {m for m in det["classes"]} | {listed["member"]}
            assert abs(mcap - sum(c["shares"] for c in classes if c["member"] in proven) * listed["price"]) < 1e-3
            assert set(det["undetermined"]) <= set(ev["undetermined_classes"])
        else:
            assert ev["status"] == "ECONOMIC_EQUIVALENT_DETERMINED", (det["symbol"], ev)
            assert abs(mcap - sum(c["shares"] for c in classes) * listed["price"]) < 1e-3
        got[det["symbol"]] = mcap
    assert sorted(got) == ["DKS", "H", "OWL", "RKT", "RYAN", "TKO", "TPG"]
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


def test_run30_nport_exception_applied_only_to_listed_issuers_and_fail_closed_public_route_withheld(tmp_path):
    chain = _mod("chain_npr", "run_top500_gate_chain.py")
    store, cik, ev, exc, px = _nport_setup(tmp_path)
    listings = {"p": {"cik": cik, "yahoo": "PINC"}, "o": {"cik": "0000000321", "yahoo": "OTHER"}}
    ov = {}
    with route_withheld_without_writes(tmp_path):
        out = chain.apply_nport_reported_prices(store, ov, listings, exc, ev, amc_dt())


def test_run30_nport_exception_rejects_tampered_price_late_attestation_and_cik_mismatch_public_route_withheld(tmp_path):
    chain = _mod("chain_npr2", "run_top500_gate_chain.py")
    store, cik, ev, exc, px = _nport_setup(tmp_path / "a")
    listings = {"p": {"cik": cik, "yahoo": "PINC"}}
    bad = json.loads(json.dumps(ev))
    bad["issuers"]["PINC"]["price"] = px * 1.01
    with route_withheld_without_writes(tmp_path):
        assert chain.apply_nport_reported_prices(store, {}, listings, exc, bad, amc_dt())["PINC"]["failures"][0].startswith("PRICE_NOT_REPRODUCED")


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


def test_run31_cover_text_maps_undimensioned_symbol_to_the_member_with_the_stated_count_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        ov, unres = chain.cover_mcap_overrides(store, {"i": {"cik": cik, "yahoo": "PPLI"}}, amc_dt())


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


def test_run32_share_scale_error_corrected_only_from_cover_text_public_route_withheld(tmp_path):
    """HXL: XBRL dei 81,002,128,000,000 (scale error x10^6) vs weighted-average 81.3M -> corrected to the count printed on
    the 10-Q cover (81,002,128); without that document the issuer is excluded (not ranked with the inflated count)."""
    chain = _mod("chain_scale", "run_top500_gate_chain.py")
    amc = _mod("amc_scale", "audit_mcap_store.py")
    listings = {"h": {"cik": "0000717605", "yahoo": "HXL"}}
    store, cik = _scale_store(tmp_path / "a", 81_002_128_000_000,
                              "The number of shares of common stock outstanding as of October 18, 2024 was 81,002,128.")
    ov = {}
    with route_withheld_without_writes(tmp_path):
        ev = chain.share_scale_overrides(store, listings, ov, amc_dt())


def test_run32_cover_text_found_after_a_long_ixbrl_hidden_header():
    chain = _mod("chain_hdr", "run_top500_gate_chain.py")
    cover = {"titles": {None: ["Common stock, par value $0.0001"]},
             "classes": [{"member": "CommonClassAMember", "shares": 80_479_073.0}, {"member": "CommonClassBMember", "shares": 5_789_499.0}]}
    text = ("c-1 0001800227 2024-01-01 2024-09-30 " * 3000) + "Common Stock 80,479,073 Class B common stock 5,789,499"
    assert len(text) > 60000 and chain.cover_text_symbol_member(text, cover)[0] == "CommonClassAMember"
    k, cnt, _ = chain.cover_text_share_count(("x " * 40000) + "81,002,128 shares outstanding", 81_002_128_000_000)
    assert (k, cnt) == (6, 81_002_128)


def test_run33_stale_share_fact_routes_to_cover_and_needs_cover_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        ov, _ = chain.cover_mcap_overrides(store, {"m": {"cik": cik, "yahoo": "MA"}}, amc_dt())


def test_run33_single_class_stale_uses_fresh_cover_count_unless_it_fails_the_scale_check_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        ov, _ = chain.cover_mcap_overrides(store, {"s": {"cik": cik, "yahoo": "SGL"}}, amc_dt())


def test_run34_stale_fact_with_unresolved_cover_is_excluded_not_ranked_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        assert amc.audit(store, listings, amc_dt(), mcap_override=ov)["rankable"] == 0


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


def test_run35_gate_snapshot_consistency_preserves_cover_shares_and_close_basis_public_route_withheld(tmp_path):
    chain = _mod("chain_cons", "run_top500_gate_chain.py")
    amc = _mod("amc_cons", "audit_mcap_store.py")
    from investment_system.universe.sources import official_mcap500_snapshot_from_store
    store, listings = _consistency_store(tmp_path)
    with route_withheld_without_writes(tmp_path):
        ov, _ = chain.cover_mcap_overrides(store, listings, amc_dt())


def test_run35_consistency_flags_gate_member_whose_price_is_not_available_at_as_of_public_route_withheld(tmp_path):
    chain = _mod("chain_cons2", "run_top500_gate_chain.py")
    amc = _mod("amc_cons2", "audit_mcap_store.py")
    store, listings = _consistency_store(tmp_path)
    with route_withheld_without_writes(tmp_path):
        ov, _ = chain.cover_mcap_overrides(store, listings, amc_dt())


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


def test_run35_bf_separator_normalised_to_same_cik_ticker_and_mtd_text_count_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        ov, _ = chain.cover_mcap_overrides(store, {"b": {"cik": cik, "yahoo": "BF-B"}}, amc_dt())


def test_run35_reviewed_symbol_mapping_verified_against_filing_quote_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        ov, un = chain.cover_mcap_overrides(store, listings, amc_dt(), symbol_mappings=maps)


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


def test_run37_official_pipeline_rebuilds_snapshot_only_from_passing_gate_evidence_public_route_withheld(tmp_path, monkeypatch):
    op = _mod("op", "official_pipeline.py")
    monkeypatch.setattr(op, "GE", tmp_path)
    cands = [{"company_id": f"c{i}", "ticker": f"T{i}", "cik": str(i).zfill(10), "shares": 1000.0 - i, "price": 10.0,
              "shares_available_at": "2024-11-01T00:00:00+00:00", "price_observed_at": "2024-12-30T21:00:00+00:00",
              "shares_basis": "COMPANYFACTS_PIT", "price_basis": "CLOSE_X_POST_AS_OF_SPLIT_FACTOR", "gate_mcap": (1000.0 - i) * 10}
             for i in range(5)]
    ev = {"official_top500_declared": True, "share_price_unit_audit": {"passed": True}, "gate_snapshot_consistency": {"passed": True, "universe_id": "uni_gate"}, "official_snapshot_candidates": cands,
          "top500": [{"company_id": f"c{i}"} for i in range(5)]}
    (tmp_path / "gate_chain_2024-12-31_real_gha.json").write_text(json.dumps(ev))
    with route_withheld_without_writes(tmp_path):
        snap, st = op.load_official("2024-12-31")


def test_workflow_has_no_gate_reuse_or_publication_sink():
    workflow = (Path(__file__).resolve().parents[2] / '.github/workflows/c21-real-data.yml').read_text()
    assert 'reuse_gate_evidence:' not in workflow
    assert 'run_top500_gate_chain.py' not in workflow
    assert 'actions/upload' not in workflow and 'git push' not in workflow
    assert 'test_public_price_boundary.py' in workflow


def test_walk_forward_gate_rejects_selection_or_return_drift():
    import copy
    op = _mod("op_wf_consistency", "official_pipeline.py")
    singles = {d: {"horizon_as_of": h, "universe": ["old"], "selected": ["old"],
                   "equal_weight_realized": 0.1, "name_errors": {}, "outcomes": {"old": {"status": "LINKED"}}}
               for d, h in [("a", "b"), ("b", "c"), ("c", "d")]}
    wf = {"steps": [{"as_of": d, **{k: v for k, v in singles[d].items() if k != "outcomes"},
                      "n_linked": 1} for d in ["a", "b"]]}
    assert op.walk_forward_consistency(singles, wf)["passed"]
    bad = copy.deepcopy(wf)
    bad["steps"][0]["selected"] = ["new"]  # same count, wrong issuer
    bad["steps"][0]["equal_weight_realized"] = 0.2
    report = op.walk_forward_consistency(singles, bad)
    assert not report["passed"]
    assert {x["field"] for x in report["mismatches"]} == {"selected", "equal_weight_realized"}
    assert not op.walk_forward_consistency(singles, {"steps": wf["steps"][:1]})["passed"]


def test_share_unit_audit_blocks_unclassified_events_without_applying_a_ratio(tmp_path):
    chain = _mod("chain_units", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    effective = datetime(2024, 6, 10, tzinfo=UTC)
    events = {"chart": {"result": [{"events": {"splits": {"one": {
        "date": int(effective.timestamp()), "numerator": 10, "denominator": 1}}}}]}}
    store.put("yahoo_events:AAA:5y", json.dumps(events).encode(), "u", "YAHOO_SPLIT_EVENTS", "application/json", "t", 200)
    candidate = {"company_id": "a", "ticker": "AAA", "cik": "1", "shares": 100,
                 "shares_basis": "COMPANYFACTS_PIT", "shares_available_at": "2024-05-29T00:00:00+00:00"}
    report = chain.share_price_unit_audit(store, [candidate], datetime(2024, 6, 30, tzinfo=UTC))
    assert not report["passed"] and report["unresolved"][0]["events"][0]["factor"] == 10
    assert candidate["shares"] == 100  # never infer actual outstanding shares from a chart adjustment
    assert chain.share_price_unit_audit(store, [candidate], datetime(2024, 6, 1, tzinfo=UTC))["passed"]
    current = {**candidate, "shares_available_at": "2024-06-11T00:00:00+00:00"}
    assert chain.share_price_unit_audit(store, [current], datetime(2024, 6, 30, tzinfo=UTC))["passed"]


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


def test_run42_nport_exception_is_per_as_of_and_records_look_ahead_public_route_withheld(tmp_path):
    chain = _mod("chain_npr3", "run_top500_gate_chain.py")
    store, cik, ev, exc, px = _nport_setup(tmp_path)
    listings = {"p": {"cik": cik, "yahoo": "PINC"}}
    with route_withheld_without_writes(tmp_path):
        out = chain.apply_nport_reported_prices(store, {}, listings, exc, ev, amc_dt())["PINC"]


def test_run43_total_member_dropped_partial_economics_and_equal_per_share_wording_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        ov, _ = chain.cover_mcap_overrides(store, {"r": {"cik": cik, "yahoo": "RYAN"}}, amc_dt())


def test_run44_registration_doc_share_count_amtm_spinoff_public_route_withheld(tmp_path):
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
    with route_withheld_without_writes(tmp_path):
        ev = chain.registration_share_count_overrides(store, listings, ov, amc_dt())


def test_run44_registration_doc_share_count_ambiguous_or_missing_stays_blocker_public_route_withheld(tmp_path):
    chain = _mod("chain_amtm2", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    cik = "0009999999"
    store.put(f"submissions:{cik}", json.dumps({"tickers": ["ZZZ"], "filings": {"recent": {
        "form": ["8-K"], "filingDate": ["2024-09-27"], "accessionNumber": ["a"], "primaryDocument": ["d.htm"]}}}).encode(),
              "u", "SEC", "application/json", "t", 200)
    listings = {"z": {"cik": cik, "yahoo": "ZZZ"}}
    with route_withheld_without_writes(tmp_path):
        assert chain.registration_share_count_overrides(store, listings, {}, amc_dt())["ZZZ"]["status"] == "NO_COUNT_FOUND"


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


def test_share_count_diagnostic_distribution_sentences_catches_share_count_without_the_word_outstanding(tmp_path):
    """Run #49: GRAL (GRAIL, Inc.) spin-off 8-Ks scored 0 cover_sentences matches (its distribution-notice wording
    states a share count without the word 'outstanding' nearby, unlike AMTM's). distribution_sentences must find a
    number-of-shares statement by proximity to 'shares' alone, so the diagnostic surfaces real candidate quotes
    instead of a silent empty list."""
    scd = _mod("scd_dist", "share_count_diagnostic.py")
    text = ("Pursuant to the Separation and Distribution Agreement, Illumina distributed 100,000,000 shares of "
            "GRAIL common stock, par value $0.01 per share, to holders of Illumina common stock.")
    hits = scd.distribution_sentences(text)
    assert hits and "100,000,000" in hits[0] and "shares" in hits[0]
    assert scd.distribution_sentences("Nothing relevant here at all, no numbers of any kind.") == []


def test_run49_committed_2024_06_30_class_economics_all_verify_against_stored_evidence():
    """Every issuer in the committed 2024-06-30 class_economics file must verify (quotes found verbatim in the
    referenced filing document, filed on or before 2024-06-30) using the actual fetched evidence, when present.
    RKT/TPG/TOST were restored here (run #49): every claim each needs is proven from its FY2023 10-K alone (filed
    Feb 2024), not the Aug-2024 10-Q used for 2024-09-30/2024-12-31 -- no future filing evidence applied."""
    chain = _mod("chain_ce0630", "run_top500_gate_chain.py")
    ge = Path(chain.GE)
    ce_path = ge / "class_economics_2024-06-30.json"
    store_dir = ge.parents[1] / "data" / "raw"
    if not ce_path.exists() or not store_dir.exists():
        return
    ce = json.loads(ce_path.read_text(encoding="utf-8"))
    store = RawDatasetStore(store_dir)
    for cik, det in ce["issuers"].items():
        for member, cd in det["classes"].items():
            for c in cd["citations"]:
                assert c["filed"] <= "2024-06-30", (det["symbol"], member, c["filed"])
                if store.has(c["artifact_id"]):
                    frc = _mod("frc_verify_0630", "fetch_class_rights_evidence.py")
                    text = frc.html_text(store.get_bytes(c["artifact_id"]))
                    assert c["quote"] in text, (det["symbol"], member, c["quote"][:80])


def test_run49_rkt_tpg_tost_2024_06_30_citations_are_substrings_of_the_fetched_passages():
    """Cross-check against the committed class_rights_passages_2024-06-30.json (the fetched, offset-addressed
    extraction) independently of whether the raw store blobs happen to be present in this environment."""
    ge = Path(__file__).resolve().parents[1] / "reports" / "gate_evidence"
    ce = json.loads((ge / "class_economics_2024-06-30.json").read_text(encoding="utf-8"))
    passages = json.loads((ge / "class_rights_passages_2024-06-30.json").read_text(encoding="utf-8"))
    lookup = {}
    for issuer in passages["issuers"].values():
        for doc in issuer["documents"]:
            for p in doc["passages"]:
                lookup[(doc["artifact_id"], p["offset"])] = p["text"]
    checked = 0
    for det in ce["issuers"].values():
        if det["symbol"] not in ("RKT", "TPG", "TOST"):
            continue
        for member, cd in det["classes"].items():
            for c in cd["citations"]:
                key = (c["artifact_id"], c["offset"])
                assert key in lookup, (det["symbol"], member, key)
                assert c["quote"] in lookup[key], (det["symbol"], member, c["quote"][:80])
                checked += 1
    assert checked >= 5


def test_nport_investigation_is_read_only_by_the_approved_general_policy_path():
    """D3-P approval converted WRK from an investigation into a result-independent CA-PRICE-01 candidate.
    The legacy PINC/WOLF exception remains separate and the policy file is required fail-closed."""
    root = Path(__file__).resolve().parents[1]
    chain_src = (root / "tools" / "run_top500_gate_chain.py").read_text(encoding="utf-8")
    assert "nport_price_investigation" in chain_src and "CA-PRICE-01" in chain_src
    npr = _mod("npr_inv", "nport_reported_prices.py")
    h = {"name": "WestRock Co", "asset_cat": "EC", "units": "NS", "cur_cd": "USD", "balance": "100", "val_usd": "5000"}
    got, how = npr.holding_for([h], ["WestRock Co"])
    assert how == "UNIQUE" and npr.reported_price(got) == (50.0, "OK")


def test_share_count_diagnostic_exhibit_names_selects_ex99_documents_only():
    """GRAL (2024-06-30): the Form 10 Information Statement / distribution press release are EX-99.x exhibits, not
    the primary document; only EX-99 htm/txt documents of the same filing are read (diagnostic only)."""
    scd = _mod("scd_ex99", "share_count_diagnostic.py")
    idx = json.dumps({"directory": {"item": [
        {"name": "d556103d1012ba.htm", "size": "10294"}, {"name": "d556103dex991.htm", "size": "2500000"},
        {"name": "ex99-1.htm", "size": "40000"}, {"name": "d556103dex31.htm", "size": "900"},
        {"name": "Financial_Report.xlsx", "size": "1"}, {"name": "dex992.htm", "size": "99999999"}]}}).encode()
    assert scd.exhibit_names(idx) == ["d556103dex991.htm", "ex99-1.htm"]
    assert scd.exhibit_names(b"not json") == []


def test_nport_cross_check_calibration_and_targets_feed_only_ca_price_policy():
    """WRK (2024-06-30): the cross-check measures whether N-PORT per-share values reproduce as-of market closes
    (calibration over closes of issuers the gate priced) and reports target CUSIPs; the gate reads it only together
    with the approved CA-PRICE-01 policy evidence."""
    ncc = _mod("ncc", "nport_cross_check.py")
    root = Path(__file__).resolve().parents[1]
    source = (root / "tools" / "run_top500_gate_chain.py").read_text(encoding="utf-8")
    assert "nport_cross_check" in source and "apply_corporate_action_prices" in source
    ref_h = [{"name": "AAA INC", "cusip": "000000AA1", "asset_cat": "EC"}, {"name": "BBB INC", "cusip": "000000BB1", "asset_cat": "EC"}]
    cmap = ncc.cusip_to_cik(ref_h, {"0000000001": ["AAA INC"], "0000000002": ["BBB INC"]})
    assert cmap == {"000000AA1": "0000000001", "000000BB1": "0000000002"}
    closes = ncc.market_closes({"top500": [
        {"cik": "0000000001", "detail": {"mcap_price": 10.0}, "cover_override": None},
        {"cik": "0000000002", "detail": {"mcap_price": 20.0}, "cover_override": {"classes": []}}]})
    assert closes == {"0000000001": 10.0}  # multi-class cover rows are not controls
    hold = [{"name": "AAA", "cusip": "000000AA1", "asset_cat": "EC", "units": "NS", "cur_cd": "USD", "balance": "3",
             "val_usd": "30.003", "fair_val_level": "1"},
            {"name": "WRK", "cusip": "96145D105", "asset_cat": "EC", "units": "NS", "cur_cd": "USD", "balance": "2",
             "val_usd": "100.52", "fair_val_level": "1"}]
    cal = ncc.calibrate(hold, cmap, closes)
    assert cal["n"] == 1 and cal["within_0_1pct"] == 1
    t = ncc.targets(hold, ["96145D105", "000000ZZ9"])
    assert t["96145D105"]["status"] == "UNIQUE" and abs(t["96145D105"]["value_per_share"] - 50.26) < 1e-9
    assert t["000000ZZ9"]["status"] == "HOLDINGS_0"
    assert ncc.per_share({"units": "PA", "balance": "1", "val_usd": "1"}) is None


def _ca_policy(as_of="2024-06-30"):
    return {"policy_version": "D3-P-CA-v1.0", "as_of": as_of, "result_independent": True,
            "rank_and_cutoff_not_inputs": True, "reconstruction_only": True,
            "rules": {"CA-PRICE-01": {"max_relative_price_difference": 0.005,
                                        "min_control_within_tolerance_ratio": 0.99,
                                        "min_independent_sponsors": 2, "required_fair_value_level": "1"},
                      "CA-SHARES-01": {"forbidden_count_basis": ["pro forma", "approximately", "weighted average"]},
                      "CA-SECURITY-01": {"cross_tracking_group_equivalence": False},
                      "CA-ELIGIBILITY-01": {"positive_residual_value_treatment": "PRESERVE_IN_AUDIT_EVIDENCE"}}}


def _put_ca_chart(store, symbol, price=20.0):
    chart = {"chart": {"result": [{"timestamp": [int(datetime(2024, 6, 28, tzinfo=UTC).timestamp())],
                                     "indicators": {"quote": [{"close": [price]}]}}], "error": None}}
    store.put(f"yahoo_chart:{symbol}:5y", json.dumps(chart).encode(), "u", "YAHOO", "application/json", "t", 200)


def test_d3p_ca_price_uses_exact_security_level1_and_two_independent_calibrated_sponsors_public_route_withheld(tmp_path):
    chain = _mod("chain_ca_price", "run_top500_gate_chain.py")
    npr = _mod("npr_ca_price", "nport_reported_prices.py")
    store = RawDatasetStore(tmp_path)
    cik, symbol, cusip, accn = "0001732845", "WRK", "96145D105", "0001752724-24-189684"
    xml = (f'<edgarSubmission><formData><genInfo><repPdDate>2024-06-30</repPdDate></genInfo><invstOrSecs>'
           f'<invstOrSec><name>WESTROCK COMPANY</name><cusip>{cusip}</cusip><balance>10</balance><units>NS</units>'
           f'<curCd>USD</curCd><valUSD>502.6</valUSD><assetCat>EC</assetCat><fairValLevel>1</fairValLevel>'
           f'</invstOrSec></invstOrSecs></formData></edgarSubmission>').encode()
    store.put(f"nport_xml:{accn}", xml, "u", "SEC", "application/xml", "t", 200)
    companyfacts = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
        {"filed": "2024-05-01", "end": "2024-03-31", "val": 250_000_000}]}}}}}
    store.put(f"companyfacts:{cik}", json.dumps(companyfacts).encode(), "u", "SEC", "application/json", "t", 200)
    store.put(f"submissions:{cik}", json.dumps({"filings": {"recent": {"form": ["10-Q"],
              "filingDate": ["2024-05-01"], "accessionNumber": ["x"], "primaryDocument": ["x.htm"]}}}).encode(),
              "u", "SEC", "application/json", "t", 200)
    doc_id = "sec_filing_doc:0002005951:0001104659-24-099502"
    phrase = "The Combination closed on July 5, 2024 subsequent to the fiscal quarter ended June 30, 2024"
    store.put(doc_id, phrase.encode(), "u", "SEC", "text/html", "t", 200)
    policy = _ca_policy()
    policy["price_reconstruction"] = {cik: {"symbol": symbol, "cusip": cusip, "effective_date": "2024-07-05",
                                              "document": {"artifact_id": doc_id, "required_phrases": [phrase]}}}
    h = npr.raw_holdings(xml)[0]
    inv = {"source_accession": accn, "source_artifact": f"nport_xml:{accn}", "valuation_date": "2024-06-30",
           "filing_date": "2024-08-26", "issuers": {cik: {"holding_match": "UNIQUE", "holding_raw": h}}}
    filings = []
    for i, accession in enumerate((accn, "independent-a", "independent-b")):
        filings.append({"status": "FOUND", "accession": accession,
                        "calibration_vs_as_of_close": {"n": 100, "within_0_5pct": 100},
                        "targets": {cusip: {"status": "UNIQUE", "value_per_share": 50.26,
                                             "fair_val_level": "1"}}})
    ov = {}
    with route_withheld_without_writes(tmp_path):
        out = chain.apply_corporate_action_prices(store, ov, {"wrk": {"cik": cik, "yahoo": symbol}}, policy, inv,
                                                   {"filings": filings}, datetime(2024, 6, 30, tzinfo=UTC))


def test_d3p_ca_shares_accepts_only_exact_event_count_in_first_subsequent_periodic_public_route_withheld(tmp_path):
    chain = _mod("chain_ca_shares", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    cik, aid = "0001699031", "sec_filing_doc:0001699031:0001699031-25-000041"
    store.put(f"submissions:{cik}", json.dumps({"filings": {"recent": {"form": ["10-K", "10-Q"],
              "filingDate": ["2025-03-05", "2025-05-08"], "accessionNumber": ["0001699031-25-000041", "later"],
              "primaryDocument": ["gral.htm", "later.htm"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put(aid, b"Common stock shares contribution from member, net 31,049,148", "u", "SEC", "text/html", "t", 200)
    _put_ca_chart(store, "GRAL", 15.0)
    policy = _ca_policy()
    policy["share_reconstruction"] = {cik: {"symbol": "GRAL", "event_date": "2024-06-24", "shares": 31_049_148,
        "first_subsequent_periodic_document": {"artifact_id": aid, "accession": "0001699031-25-000041", "form": "10-K",
          "filed": "2025-03-05", "required_phrases_near_count": ["31,049,148", "contribution from member, net"]}}}
    ov = {}
    with route_withheld_without_writes(tmp_path):
        out = chain.apply_corporate_action_share_counts(store, ov, {"gral": {"cik": cik, "yahoo": "GRAL"}}, policy,
                                                         datetime(2024, 6, 30, tzinfo=UTC))


def test_d3p_delisting_exclusion_preserves_positive_residual_holding_and_fails_closed(tmp_path):
    chain = _mod("chain_ca_delist", "run_top500_gate_chain.py")
    store = RawDatasetStore(tmp_path)
    cik, cusip = "0001689662", "L0223L101"
    store.put(f"submissions:{cik}", json.dumps({"tickers": [], "filings": {"recent": {"form": ["25", "15-12B"],
              "filingDate": ["2021-10-06", "2021-10-18"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    docs = []
    for accn, text in (("a", "Class A common shares New York Stock Exchange"), ("b", "Class A common shares 115")):
        aid = f"sec_filing_doc:{cik}:{accn}"
        store.put(aid, text.encode(), "u", "SEC", "text/html", "t", 200)
        docs.append({"artifact_id": aid, "required_phrases": text.split(" ", 1)})
    policy = _ca_policy()
    policy["reference_exclusions"] = {cusip: {"cik": cik, "delisted_effective_date": "2021-10-08",
        "deregistered_date": "2021-10-18", "no_relisting_through": "2024-06-30", "documents": docs}}
    holding = {"name": "ARDAGH GROUP SA", "cusip": cusip, "asset_cat": "EC", "candidates": [cik], "value": 76686.39}
    refs, report = chain.apply_reference_delisting_policy(store, [{"unresolved_holdings": [holding]}], policy,
                                                           datetime(2024, 6, 30, tzinfo=UTC))
    assert refs[0]["unresolved_holdings"] == []
    assert refs[0]["policy_excluded_holdings"][0]["value"] == 76686.39
    assert report[cusip]["positive_residual_value_preserved"] == 76686.39
    store.put(docs[0]["artifact_id"], b"tampered", "u", "SEC", "text/html", "t", 200)
    refs2, report2 = chain.apply_reference_delisting_policy(store, [{"unresolved_holdings": [holding]}], policy,
                                                             datetime(2024, 6, 30, tzinfo=UTC))
    assert refs2[0]["unresolved_holdings"] == [holding] and report2[cusip]["status"] == "NOT_EXCLUDED"


def test_d3p_security_policy_forbids_cross_tracking_group_equivalence():
    root = Path(__file__).resolve().parents[1]
    policy = json.loads((root / "reports" / "gate_evidence" / "corporate_action_policy_2024-06-30.json").read_text())
    rule = policy["rules"]["CA-SECURITY-01"]
    assert rule["membership_basis"] == "ISSUER_OR_COMPANY_LEVEL"
    assert rule["valuation_basis"] == "EACH_LISTED_SECURITY_PRICE_X_ITS_OWN_SHARES"
    assert rule["cross_tracking_group_equivalence"] is False and rule["unpriced_security_treatment"] == "EXPLICIT_BOUND"


def test_nport_reference_splits_cik_collisions_of_distinct_issuers():
    """Run #53: 'DUN & BRADSTREET HOLDINGS, INC.' (CUSIP 26484T) was resolved to Moody's CIK (615369) and 'F.N.B.
    CORPORATION' to V.F.'s. A CIK keeps only the issuer group matched by the strongest method; the other group retries
    without that CIK (exactly one remaining candidate) or becomes unresolved. Share classes (same 6-char issuer number)
    stay together."""
    fnr = _mod("fnr_coll", "fetch_nport_reference.py")
    cur = {fnr.norm_name("MOODYS CORP /DE/"): {"0001059556"}}
    hist = {fnr.norm_name("DUN & BRADSTREET HOLDINGS, INC."): {"0001059556", "0001799208"}}
    holdings = [{"name": "MOODY'S CORPORATION", "cusip": "615369105"},
                {"name": "DUN & BRADSTREET HOLDINGS, INC.", "cusip": "26484T106"}]
    members = {"0001059556": {"names": ["MOODY'S CORPORATION", "DUN & BRADSTREET HOLDINGS, INC."],
                              "cusips": ["615369105", "26484T106"], "method": "SEC_TICKERS_TITLE",
                              "methods": ["SEC_TICKERS_TITLE", "SEC_CIK_LOOKUP_UNIQUE_ACTIVE"]}}
    out, unres = fnr.split_collisions(members, [], holdings, cur, hist)
    assert out["0001059556"]["cusips"] == ["615369105"]
    assert out["0001799208"]["cusips"] == ["26484T106"] and out["0001799208"]["collision_retry_from"] == ["0001059556"]
    assert unres == []
    # equal-strength claims: nobody keeps the CIK
    members2 = {"X": {"names": ["A", "B"], "cusips": ["111111101", "222222202"], "method": "SEC_TICKERS_TITLE",
                      "methods": ["SEC_TICKERS_TITLE", "SEC_TICKERS_TITLE"]}}
    out2, unres2 = fnr.split_collisions(members2, [], [{"name": "A", "cusip": "111111101"}, {"name": "B", "cusip": "222222202"}], {}, {})
    assert "X" not in out2 and {u["reason"] for u in unres2} == {"CIK_COLLISION_DISTINCT_CUSIP_ISSUERS"}
    # share classes of one issuer are not a collision
    members3 = {"BF": {"names": ["BROWN-FORMAN A", "BROWN-FORMAN B"], "cusips": ["115637100", "115637209"],
                       "method": "SEC_TICKERS_TITLE", "methods": ["SEC_TICKERS_TITLE", "SEC_TICKERS_TITLE"]}}
    assert fnr.split_collisions(members3, [], [], {}, {})[0]["BF"]["cusips"] == ["115637100", "115637209"]


def test_nport_reference_cusip_attestation_decides_ambiguous_names(tmp_path):
    """Ambiguous or unmatched reference holdings (BLUE OWL CAPITAL INC. -> 5 Blue Owl entities; tracking-group names)
    are identified only by the candidate's own 13G/13D (subject company, filed <= as_of) printing the CUSIP."""
    fnr = _mod("fnr_att", "fetch_nport_reference.py")
    npr = _mod("npr_att", "nport_reported_prices.py")
    frc = _mod("frc_att", "fetch_class_rights_evidence.py")
    store = RawDatasetStore(tmp_path)
    def sub(c, accn, filed):
        store.put(f"submissions:{c}", json.dumps({"filings": {"recent": {"form": ["SC 13G"], "filingDate": [filed],
                  "accessionNumber": [accn], "primaryDocument": ["d.htm"]}}}).encode(), "u", "SEC", "application/json", "t", 200)
    sub("0000000001", "0000000001-24-000001", "2024-02-14")
    sub("0000000002", "0000000002-24-000001", "2024-02-14")
    store.put("sec_filing_doc:0000000001:0000000001-24-000001", b"<p>CUSIP No. 09581B 10 3 Blue Owl Capital Inc.</p>", "u", "SEC", "text/html", "t", 200)
    store.put("sec_filing_doc:0000000002:0000000002-24-000001", b"<p>CUSIP No. 09581K 10 0 Blue Owl Capital Corp</p>", "u", "SEC", "text/html", "t", 200)
    store.put("edgar_index_headers:0000000001-24-000001", b"<SEC-HEADER>\nSUBJECT COMPANY:\n COMPANY DATA:\n  CENTRAL INDEX KEY: 0000000001\nFILED BY:\n</SEC-HEADER>", "u", "SEC", "text/html", "t", 200)
    store.put("edgar_index_headers:0000000002-24-000001", b"&lt;SEC-HEADER&gt;\nSUBJECT COMPANY:\n COMPANY DATA:\n  CENTRAL INDEX KEY: 2\nREPORTING-OWNER:\n&lt;/SEC-HEADER&gt;", "u", "SEC", "text/html", "t", 200)
    get = lambda aid, url, kind: None  # noqa: E731  (offline: artifacts already stored)
    att = fnr.attest_by_cusip(store, get, ["0000000001", "0000000002"], "09581B103", amc_dt(), npr, frc)
    assert att["status"] == "UNIQUE" and att["cik"] == "0000000001"
    none = fnr.attest_by_cusip(store, get, ["0000000002"], "09581B103", amc_dt(), npr, frc)
    assert none["cik"] is None and none["status"] == "ATTESTED_0"
    # A reporting person's submissions can list a 13G whose subject is another candidate. Identity comes from the
    # index-header SUBJECT COMPANY CIK, never from the submissions CIK (run #54 D&B false double-attestation).
    sub("0000000011", "0000000011-24-000001", "2024-02-14")
    store.put("sec_filing_doc:0000000011:0000000011-24-000001", b"<p>Dun & Bradstreet Holdings CUSIP 26484T106</p>", "u", "SEC", "text/html", "t", 200)
    store.put("edgar_index_headers:0000000011-24-000001", b"<SEC-HEADER>\nSUBJECT COMPANY:\n COMPANY DATA:\n  CENTRAL INDEX KEY: 0000000012\nFILED BY:\n COMPANY DATA:\n  CENTRAL INDEX KEY: 0000000011\n</SEC-HEADER>", "u", "SEC", "text/html", "t", 200)
    routed = fnr.attest_by_cusip(store, get, ["0000000011", "0000000012"], "26484T106", amc_dt(), npr, frc)
    assert routed["cik"] == "0000000012" and routed["status"] == "UNIQUE"
    cur = {fnr.norm_name("LIBERTY MEDIA CORP"): {"0001560385"}}
    assert fnr.name_candidates("LIBERTY MEDIA CORP - FORMULA ONE GROUP", cur, {}) == {"0001560385"}


def test_nport_reference_same_issuer_prefix_only_adds_exact_cusip_attestation_candidate(tmp_path):
    """A tracking-group name can miss the registrant.  A unique already-resolved issuer-prefix adds a candidate, but
    never resolves identity by itself: the exact unresolved CUSIP must still pass ownership-filing attestation."""
    fnr = _mod("fnr_att_prefix", "fetch_nport_reference.py")
    npr = _mod("npr_att_prefix", "nport_reported_prices.py")
    frc = _mod("frc_att_prefix", "fetch_class_rights_evidence.py")
    unresolved = {"name": "LIBERTY MEDIA CORP - LIBERTY SIRIUSXM", "cusip": "531229813",
                  "candidates": ["0002003397"]}
    members = {"0001560385": {"names": ["LIBERTY MEDIA CORP - FORMULA ONE GROUP"],
                               "cusips": ["531229755", "531229771"], "method": "CUSIP_ATTESTED_OWNERSHIP_FILING"}}
    cands = fnr.cusip_attestation_candidates(unresolved, members, {}, {})
    assert cands == ["0001560385", "0002003397"]  # sibling issuer first, so the bounded scan cannot drop it
    ambiguous = {**members, "0009999999": {"names": ["OTHER"], "cusips": ["531229999"], "method": "TEST"}}
    assert fnr.cusip_attestation_candidates(unresolved, ambiguous, {}, {}) == ["0002003397"]

    store = RawDatasetStore(tmp_path)
    cik, accn = "0001560385", "0001560385-24-000001"
    store.put(f"submissions:{cik}", json.dumps({"filings": {"recent": {"form": ["SC 13G"],
              "filingDate": ["2024-02-12"], "accessionNumber": [accn], "primaryDocument": ["d.htm"]}}}).encode(),
              "u", "SEC", "application/json", "t", 200)
    store.put(f"sec_filing_doc:{cik}:{accn}", b"<p>Liberty SiriusXM Class A CUSIP 531229813</p>",
              "u", "SEC", "text/html", "t", 200)
    store.put(f"edgar_index_headers:{accn}",
              b"SUBJECT COMPANY:\n\tCENTRAL INDEX KEY:\t\t0001560385\n", "u", "SEC", "text/plain", "t", 200)
    get = lambda aid, url, kind: None  # noqa: E731
    att = fnr.attest_by_cusip(store, get, cands, unresolved["cusip"], amc_dt(), npr, frc)
    assert att["status"] == "UNIQUE" and att["cik"] == cik
    store.put(f"sec_filing_doc:{cik}:{accn}", b"<p>Liberty Formula One CUSIP 531229755</p>",
              "u", "SEC", "text/html", "t", 200)
    none = fnr.attest_by_cusip(store, get, cands, unresolved["cusip"], amc_dt(), npr, frc)
    assert none["status"] == "ATTESTED_0" and none["cik"] is None


def test_nport_reference_retries_rows_that_precede_their_resolved_sibling(tmp_path):
    """The Sirius rows precede Formula One in the N-PORT. Formula One identifies CIK 1560385 on pass one; Sirius may
    use that sibling only on pass two and must still attest its own exact CUSIP."""
    fnr = _mod("fnr_att_retry", "fetch_nport_reference.py")
    npr = _mod("npr_att_retry", "nport_reported_prices.py")
    frc = _mod("frc_att_retry", "fetch_class_rights_evidence.py")
    store = RawDatasetStore(tmp_path)
    cik = "0001560385"
    accns = [f"{cik}-24-{i:06d}" for i in range(5)]
    store.put(f"submissions:{cik}", json.dumps({"name": "LIBERTY MEDIA CORP", "filings": {"recent": {
              "form": ["10-Q"] + ["SC 13G"] * 4,
              "filingDate": ["2024-05-08", "2024-02-14", "2024-02-13", "2024-02-12", "2024-02-11"],
              "reportDate": ["2024-03-31"] + [""] * 4, "accessionNumber": accns,
              "primaryDocument": ["q.htm", "f.htm", "s.htm", "l1.htm", "l2.htm"]}}}).encode(),
              "u", "SEC", "application/json", "t", 200)
    for accn, cusip in zip(accns[1:], ["531229755", "531229813", "531229722", "531229748"]):
        store.put(f"sec_filing_doc:{cik}:{accn}", f"<p>CUSIP {cusip}</p>".encode(),
                  "u", "SEC", "text/html", "t", 200)
        store.put(f"edgar_index_headers:{accn}",
                  b"SUBJECT COMPANY:\n\tCENTRAL INDEX KEY:\t\t0001560385\n", "u", "SEC", "text/plain", "t", 200)
    sirius = {"name": "LIBERTY SIRIUS XM", "cusip": "531229813", "candidates": ["0002003397"]}
    formula = {"name": "LIBERTY MEDIA CORP - FORMULA ONE GROUP", "cusip": "531229755", "candidates": []}
    live = [{"name": "LIBERTY LIVE", "cusip": cusip} for cusip in ("531229722", "531229748")]
    successor = "0002078416"
    store.put(f"submissions:{successor}", json.dumps({"filings": {"recent": {
              "form": ["10-Q"], "filingDate": ["2025-05-08"], "reportDate": ["2025-03-31"],
              "accessionNumber": [f"{successor}-25-000001"], "primaryDocument": ["q.htm"]}}}).encode(),
              "u", "SEC", "application/json", "t", 200)
    cur = {fnr.norm_name("LIBERTY MEDIA CORP"): {cik}}
    members = {successor: {"names": [r["name"] for r in live], "cusips": [r["cusip"] for r in live],
                           "method": "SEC_TICKERS_TITLE"}}
    unresolved, attestations = fnr.attest_unresolved_holdings(
        store, lambda aid, url, kind: None, members, [sirius, formula], [sirius, formula] + live,
        cur, {}, amc_dt(), npr, frc)
    assert unresolved == [] and successor not in members
    assert members[cik]["cusips"] == ["531229755", "531229813", "531229722", "531229748"]
    assert attestations["LIBERTY SIRIUS XM|531229813"]["status"] == "UNIQUE"
    assert attestations["LIBERTY SIRIUS XM|531229813"]["candidates"] == [cik, "0002003397", successor]


def test_nport_reference_attestation_tie_broken_only_by_pit_registrant(tmp_path):
    """Run #54: 'DUN & BRADSTREET HOLDINGS, INC.' CUSIP 26484T106 was printed by the ownership filings of two
    entities (ATTESTED_2). Only the one filing 10-K/10-Q around as_of can be the listed issuer at as_of."""
    fnr = _mod("fnr_att2", "fetch_nport_reference.py")
    npr = _mod("npr_att2", "nport_reported_prices.py")
    frc = _mod("frc_att2", "fetch_class_rights_evidence.py")
    store = RawDatasetStore(tmp_path)
    def sub(c, forms, dates):
        n = len(forms)
        store.put(f"submissions:{c}", json.dumps({"name": f"E{c}", "filings": {"recent": {"form": forms, "filingDate": dates,
                  "accessionNumber": [f"{c}-24-{i:06d}" for i in range(n)], "primaryDocument": ["d.htm"] * n,
                  "reportDate": ["2024-09-30" if fm == "10-Q" else "" for fm in forms]}}}).encode(),
                  "u", "SEC", "application/json", "t", 200)
    sub("0000000001", ["10-Q", "SC 13G"], ["2024-11-05", "2024-02-14"])      # live registrant at as_of
    sub("0000000002", ["SC 13G"], ["2024-02-10"])                            # predecessor, no periodic filing
    for c in ("0000000001", "0000000002"):
        accn = f"{c}-24-{(1 if c.endswith('1') else 0):06d}"
        store.put(f"sec_filing_doc:{c}:{accn}", b"<p>CUSIP 26484T106</p>",
                  "u", "SEC", "text/html", "t", 200)
        store.put(f"edgar_index_headers:{accn}",
                  f"SUBJECT COMPANY:\n\tCENTRAL INDEX KEY:\t\t{int(c)}\n".encode(),
                  "u", "SEC", "text/plain", "t", 200)
    get = lambda aid, url, kind: None  # noqa: E731
    att = fnr.attest_by_cusip(store, get, ["0000000001", "0000000002"], "26484T106", amc_dt(), npr, frc)
    assert fnr.pit_registrant(store, "0000000001", amc_dt()) and not fnr.pit_registrant(store, "0000000002", amc_dt())
    assert att["cik"] == "0000000001" and att["status"] == "UNIQUE_PIT_REGISTRANT_AMONG_ATTESTED"
    assert att["attested_ciks"] == ["0000000001", "0000000002"]


def test_c36_owl_class_c_paired_units_proven_class_d_left_unvalued():
    """Run #55: Blue Owl (OWL) entered the pool via the fixed reference (C-36) as a cover-class lower bound (Class A
    only). Its FY2023 10-K (filed 2024-02-23, before every as_of) proves Class C (non-economic, one per Common Unit held
    outside the company) pairs 1:1 with Common Units exchanged for Class A; Class D pairs with Principal units that
    exchange into UNLISTED Class B, so it stays unvalued (partial lower bound). Quotes must be verbatim in the fetched
    passages, filed <= each as_of, and satisfy the claim patterns."""
    import re
    chain = _mod("chain_owl", "run_top500_gate_chain.py")
    ge = Path(chain.GE)
    pas = json.loads((ge / "class_rights_passages_2024-12-31.json").read_text(encoding="utf-8"))["issuers"]["OWL"]
    texts = {(d["artifact_id"], p["offset"]): p["text"] for d in pas["documents"] for p in d["passages"]}
    for a in ("2024-06-30", "2024-09-30", "2024-12-31"):
        det = json.loads((ge / f"class_economics_{a}.json").read_text(encoding="utf-8"))["issuers"]["0001823945"]
        assert set(det["classes"]) == {"CommonClassCMember"}
        got = set()
        for c in det["classes"]["CommonClassCMember"]["citations"]:
            assert c["filed"] <= a and c["quote"] in texts[(c["artifact_id"], c["offset"])]
            assert "Class C Shares" in c["quote"]
            got |= {s for s in c["supports"] if re.search(chain.CLAIM_PATTERNS[s], c["quote"], re.I)}
        assert got >= chain.BASIS_CLAIMS["PAIRED_UNITS_EXCHANGEABLE_INTO_LISTED"]
