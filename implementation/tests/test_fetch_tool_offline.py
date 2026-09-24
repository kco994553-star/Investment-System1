"""tools/fetch_sp500_intervals.py logic with HTTP stubbed. Proves wiring only, not data."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class _Resp:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_fetch_tool_end_to_end_with_stubbed_http(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("fetch_tool", ROOT / "tools" / "fetch_sp500_intervals.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    csv = b"ticker,start_date,end_date\nAAA,2000-01-03,\nOLD,2005-01-03,2015-06-30\n"
    tick = json.dumps({"0": {"cik_str": 1, "ticker": "AAA", "title": "a"}, "1": {"cik_str": 2, "ticker": "OLD", "title": "o"}}).encode()

    def fake_urlopen(req, timeout=0):
        url = req.full_url
        return _Resp(csv if url == mod.URL else tick)

    monkeypatch.setattr(mod, "urlopen", fake_urlopen)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    monkeypatch.setattr(mod, "fetch_submissions", lambda cik: {"filings": {"recent": {"form": ["10-K"], "filingDate": ["2010-02-01"], "accessionNumber": ["x"]}}})
    rep = mod.main(Path(tmp_path), verify_closed=True)
    assert rep["n_rows"] == 2 and rep["resolve_methods"]["CURRENT_OPEN"] == 1
    assert rep["resolve_methods"]["VERIFIED_FILINGS"] == 1
    assert rep["member_count_probes"]["2008-09-15"] == 2
    assert rep["member_count_probes"]["2020-03-31"] == 1
    assert rep["real_data_verified"] is False
    rep2 = mod.main(Path(tmp_path), verify_closed=False)
    assert rep2["resolve_methods"]["UNRESOLVED"] == 1
