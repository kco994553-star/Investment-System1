"""RawDatasetStore + offline replay + network-runner wiring. SYNTHETIC scope.

None of this fetches real data. It proves: (a) the store round-trips bytes +
manifest, (b) replay feeds run_as_of through the exact same MISSING/PIT path
as live data, (c) the network runner's artifact-id/manifest wiring is correct
when HTTP is stubbed, and (d) it fails closed (per-artifact, not a crash) when
HTTP is refused - reproducing this sandbox's real behaviour.
"""

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_system.ingestion.raw_store import RawDatasetStore
from investment_system.ingestion.replay import build_payloads_and_bars, load_companyfacts, load_price_bars
from investment_system.validation.historical import run_as_of
from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.records import ScopedTrackStore

from .synthetic_universe import bars as gen_bars, companyfacts

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def _chart_json(symbol, prices, start_ts=1_700_000_000, step=86400):
    ts = [start_ts + i * step for i in range(len(prices))]
    return {"chart": {"result": [{
        "meta": {"symbol": symbol, "currency": "USD"},
        "timestamp": ts,
        "indicators": {"quote": [{"close": prices}], "adjclose": [{"adjclose": prices}]},
    }]}}


def test_store_roundtrip_and_manifest_is_not_pit_availability(tmp_path):
    store = RawDatasetStore(tmp_path)
    body = b'{"facts": {}}'
    m = store.put("companyfacts:0001045810", body, "https://data.sec.gov/x", "SEC_COMPANYFACTS", "application/json", "test-fetcher")
    assert store.has("companyfacts:0001045810")
    assert store.get_bytes("companyfacts:0001045810") == body
    man = store.get_manifest("companyfacts:0001045810")
    assert man["sha256"] == m.sha256 and man["bytes"] == len(body)
    assert "fetched_at" in man and "source_url" in man
    assert store.list_ids() == ["companyfacts:0001045810"]
    with pytest.raises(FileNotFoundError):
        store.get_bytes("nope")


def test_replay_feeds_run_as_of_through_the_real_pit_path(tmp_path):
    store = RawDatasetStore(tmp_path / "store")
    cf = companyfacts(3, full=True)
    store.put("companyfacts:0000000003", json.dumps(cf).encode(), "https://data.sec.gov/x", "SEC_COMPANYFACTS", "application/json", "test")
    store.put("yahoo_chart:SYN3:5y", json.dumps(_chart_json("SYN3", [10.0, 11.0, 12.5])).encode(), "https://q", "YAHOO_CHART", "application/json", "test")
    listings = {"syn3": {"cik": "3", "yahoo": "SYN3"}, "syn4_missing": {"cik": "4", "yahoo": "SYN4"}}
    payloads, bars = build_payloads_and_bars(store, listings, chart_range="5y")
    assert "syn3" in payloads and "syn4_missing" not in payloads  # absent stays absent, not fabricated
    assert bars["syn3"][0]["observed_at"] < bars["syn3"][-1]["observed_at"]
    assert load_companyfacts(store, "3") == cf
    assert load_price_bars(store, "NOPE") == []

    trk = ScopedTrackStore(FileTrackRecordStore(tmp_path / "t.json"))
    row = run_as_of(datetime(2026, 1, 15, tzinfo=UTC), payloads, bars, trk, ("syn3", "syn4_missing"),
                     listings={"syn3": {"yahoo": "SYN3", "cik": "3"}, "syn4_missing": {"yahoo": "SYN4", "cik": "4"}})
    assert row["quality"]["syn3"]["Q"] is not None  # real store data scores through the unmodified engine
    assert row["quality"]["syn4_missing"] == {"raw": False}  # missing companyfacts -> MISSING, not invented
    assert row["real_data_verified"] is False  # fetching+replaying synthetic bytes is still not REAL-DATA


def _stub_urlopen(monkeypatch, mod, routes: dict[str, tuple[bytes, int]]):
    class _Resp:
        def __init__(self, body, status):
            self.body, self.status, self.headers = body, status, {"Content-Type": "application/json"}

        def read(self):
            return self.body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    import email.message
    def fake(req, timeout=0):
        url = req.full_url
        if url not in routes:
            raise mod.URLError(f"no route: {url}")
        body, status = routes[url]
        r = _Resp(body, status)
        r.headers = email.message.Message()
        r.headers["Content-Type"] = "application/json"
        return r

    monkeypatch.setattr(mod, "urlopen", fake)


def test_network_runner_writes_correct_artifact_ids_with_stubbed_http(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("fetch_real_data", ROOT / "tools" / "fetch_real_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    routes = {
        mod.SEC_TICKERS_URL: (b'{"0":{"cik_str":320193,"ticker":"AAPL","title":"Apple"}}', 200),
        mod.SEC_FACTS_URL.format(cik="0000320193"): (b'{"facts": {}}', 200),
        mod.SEC_SUBS_URL.format(cik="0000320193"): (b'{"filings": {}}', 200),
        mod.YAHOO_CHART_URL.format(symbol="AAPL", range="1y"): (json.dumps(_chart_json("AAPL", [1, 2])).encode(), 200),
    }
    _stub_urlopen(monkeypatch, mod, routes)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    rep = mod.run(Path(tmp_path), ["320193"], ["AAPL"], "1y", 0.0, skip_tickers=False)
    assert rep["n_failed"] == 0 and rep["real_data_verified"] is False
    store = RawDatasetStore(tmp_path)
    assert sorted(store.list_ids()) == sorted(["sec_tickers", "companyfacts:0000320193", "submissions:0000320193", "yahoo_chart:AAPL:1y"])
    man = store.get_manifest("companyfacts:0000320193")
    assert man["source_kind"] == "SEC_COMPANYFACTS" and man["http_status"] == 200
    # Second run must not re-fetch (idempotent / doesn't waste a request budget).
    rep2 = mod.run(Path(tmp_path), ["320193"], ["AAPL"], "1y", 0.0, skip_tickers=False)
    assert all(r["status"] == "SKIPPED_ALREADY_PRESENT" for r in rep2["log"])


def test_network_runner_fails_closed_per_artifact_not_crash(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("fetch_real_data2", ROOT / "tools" / "fetch_real_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def deny(req, timeout=0):
        raise mod.HTTPError(req.full_url, 403, "Host not in allowlist", None, None)

    monkeypatch.setattr(mod, "urlopen", deny)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    rep = mod.run(Path(tmp_path), ["320193"], ["AAPL"], "1y", 0.0, skip_tickers=False)
    assert rep["n_ok"] == 0 and rep["n_failed"] == 4
    assert all(r["status"] == "HTTP_403" for r in rep["log"])
    store = RawDatasetStore(tmp_path)
    assert store.list_ids() == []  # nothing partially written on failure


def test_store_refresh_archives_previous_raw_bytes_and_manifest(tmp_path):
    store = RawDatasetStore(tmp_path)
    store.put("sec_tickers", b"first", "https://sec/one", "SEC_TICKERS", "application/json", "test")
    first = store.get_manifest("sec_tickers")
    store.put("sec_tickers", b"second", "https://sec/two", "SEC_TICKERS", "application/json", "test")
    assert store.get_bytes("sec_tickers") == b"second"
    history = store.list_history("sec_tickers")
    assert len(history) == 1
    assert (history[0] / "blob").read_bytes() == b"first"
    archived = json.loads((history[0] / "manifest.json").read_text())
    assert archived["sha256"] == first["sha256"] and archived["source_url"] == "https://sec/one"


def test_network_runner_refresh_replaces_canonical_but_preserves_history(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("fetch_real_data_refresh", ROOT / "tools" / "fetch_real_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _stub_urlopen(monkeypatch, mod, {mod.SEC_TICKERS_URL: (b"v1", 200)})
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    mod.run(Path(tmp_path), [], [], "1y", 0.0, skip_tickers=False)
    _stub_urlopen(monkeypatch, mod, {mod.SEC_TICKERS_URL: (b"v2", 200)})
    rep = mod.run(Path(tmp_path), [], [], "1y", 0.0, skip_tickers=False, refresh=True)
    store = RawDatasetStore(tmp_path)
    assert rep["n_failed"] == 0 and store.get_bytes("sec_tickers") == b"v2"
    assert len(store.list_history("sec_tickers")) == 1
