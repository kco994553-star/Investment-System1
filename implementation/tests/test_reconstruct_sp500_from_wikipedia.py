"""Mechanical PIT reconstruction from a Wikipedia-shaped snapshot + changes list.
Small synthetic fixtures here (not the real 503-row file) so this is fast and
self-contained; the real run is evidence in reports/gate_evidence/, not a test."""
import importlib.util
from pathlib import Path

def load_tool():
    p = Path(__file__).parents[1] / 'tools' / 'reconstruct_sp500_from_wikipedia.py'
    s = importlib.util.spec_from_file_location('reconstruct_sp500', p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

MD = """| Symbol | Security | GICS Sector | GICS Sub-Industry | Headquarters Location | Date added | CIK | Founded |
|---|---|---|---|---|---|---|---|
| AAA | Alpha Co | Tech | Software | X | 1990-01-01 | 0000000001 | 1980 |
| CCC | Charlie Co | Tech | Software | X | 2025-06-01 | 0000000003 | 2000 |
| DDD | Delta Co | Tech | Software | X | 2010-01-01 | 0000000004 | 1995 |
"""


def test_parse_constituents_extracts_symbol_date_cik():
    m = load_tool()
    rows = m.parse_constituents(MD)
    assert rows["AAA"] == {"security": "Alpha Co", "date_added": "1990-01-01", "cik": "0000000001"}
    assert len(rows) == 3


def test_swap_add_and_remove_events_reversed_correctly():
    m = load_tool()
    rows = m.parse_constituents(MD)
    # CCC added 2025-06-01 replacing BBB. As of 2024-12-31, CCC shouldn't be a
    # member yet and BBB should still be one.
    events = [{"date": "2025-06-01", "added": "CCC", "removed": "BBB"}]
    r = m.reconstruct(rows, events, "2024-12-31")
    assert "CCC" not in r["members"]
    assert "BBB" in r["members"]
    assert "AAA" in r["members"] and "DDD" in r["members"]
    assert r["n_events_applied"] == 1


def test_events_on_or_before_as_of_are_not_reversed():
    m = load_tool()
    rows = m.parse_constituents(MD)
    # An event at exactly as_of (not strictly after it) must NOT be undone.
    # If it were wrongly undone, AAA would be removed here.
    events = [{"date": "2024-12-31", "added": "AAA", "removed": None}]
    r = m.reconstruct(rows, events, "2024-12-31")
    assert r["n_events_applied"] == 0
    assert "AAA" in r["members"]


def test_add_only_and_remove_only_events():
    m = load_tool()
    rows = m.parse_constituents(MD)
    events = [
        {"date": "2026-01-01", "added": "EEE", "removed": None},   # standalone add -> undo removes EEE
        {"date": "2026-02-01", "added": None, "removed": "FFF"},   # standalone remove -> undo adds FFF back
    ]
    r = m.reconstruct(rows, events, "2024-12-31")
    assert "EEE" not in r["members"]
    assert "FFF" in r["members"]


def test_double_touch_ticker_resolved_by_reverse_chronological_order():
    """A ticker added then later removed within the reversal window (like SOLS in
    the real S&P 500 data) must end up NOT present in the reconstruction -- it
    never existed as a member as of the target as_of."""
    m = load_tool()
    rows = m.parse_constituents(MD)
    events = [
        {"date": "2025-12-01", "added": "ZZZ", "removed": None},   # ZZZ added (most recent)
        {"date": "2025-06-01", "added": "ZZZ", "removed": "AAA"},  # then ZZZ itself had replaced AAA earlier
    ]
    r = m.reconstruct(rows, events, "2024-12-31")
    assert "ZZZ" not in r["members"]
    assert "AAA" in r["members"]  # AAA was still present; was only replaced later


def test_stale_date_added_is_dropped_as_belt_and_suspenders():
    m = load_tool()
    clean_md = """| Symbol | Security | GICS Sector | GICS Sub-Industry | Headquarters Location | Date added | CIK | Founded |
|---|---|---|---|---|---|---|---|
| AAA | Alpha Co | Tech | Software | X | 1990-01-01 | 0000000001 | 1980 |
| GGG | Gamma Co | Tech | Software | X | 2025-03-01 | 0000000007 | 2001 |
"""
    rows = m.parse_constituents(clean_md)
    r = m.reconstruct(rows, [], "2024-12-31")  # no events reference GGG at all
    assert "GGG" not in r["members"]
    assert r["n_dropped_as_stale_after_undo"] == 1
    assert r["stale_dropped"] == ["GGG"]


def test_cli_end_to_end(tmp_path):
    m = load_tool()
    md_path = tmp_path / "c.md"
    md_path.write_text(MD, encoding="utf-8")
    import json
    ev_path = tmp_path / "e.json"
    ev_path.write_text(json.dumps({"events": [{"date": "2025-06-01", "added": "CCC", "removed": "BBB"}]}), encoding="utf-8")
    out = tmp_path / "out.json"
    import sys
    old = sys.argv
    try:
        sys.argv = ["reconstruct_sp500_from_wikipedia.py", "--constituents", str(md_path),
                    "--changes", str(ev_path), "--as-of", "2024-12-31", "--out", str(out)]
        m.main()
    finally:
        sys.argv = old
    r = json.loads(out.read_text(encoding="utf-8"))
    assert "BBB" in r["members"] and "CCC" not in r["members"]
    assert r["official"] is False and r["survivorship_risk"] is False
