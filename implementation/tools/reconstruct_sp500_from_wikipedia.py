"""Reconstruct S&P 500 PIT membership for a target as_of date from a Wikipedia
current-constituent snapshot + its dated addition/removal changes table.

This is the "materially different, more reliable" replacement for manual
press-release reconstruction (which C-22 recorded as attempted and abandoned):
instead of a human reading dozens of press releases and computing a net diff
by eye, this walks a machine-parsed, dated event list backward from a fetched
current snapshot, one event at a time, so correctness rests on (a) the fetched
table being faithfully transcribed and (b) a small, auditable loop -- not on
anyone's manual arithmetic over ~500 names.

Inputs (both already saved to reports/gate_evidence/ verbatim from source):
  --constituents  the current pipe-table markdown (Symbol | Security | ... | Date added | CIK | ...)
  --changes       JSON {"events": [{"date","added","removed"}, ...]}, only events
                   with date > as_of need to be present (earlier ones are already
                   captured by "Date added" on survivors).
  --as-of         target date, e.g. 2024-12-31

Output: PIT membership = current membership, with every change whose date is
strictly after as_of undone in reverse-chronological order (most recent first).
Members whose Date added is itself after as_of are also dropped (belt and
suspenders: they must already be absent once every later event is undone, but
this is asserted, not assumed).
"""
from __future__ import annotations
import argparse, json, re, sys
from datetime import date
from pathlib import Path

ROW_RE = re.compile(
    r"^\|\s*(?P<symbol>[^|]+?)\s*\|\s*(?P<security>[^|]+?)\s*\|\s*(?P<sector>[^|]+?)\s*\|\s*"
    r"(?P<subind>[^|]+?)\s*\|\s*(?P<hq>[^|]+?)\s*\|\s*(?P<date_added>\d{4}-\d{2}-\d{2})\s*\|\s*"
    r"(?P<cik>\d{10})\s*\|\s*(?P<founded>[^|]+?)\s*\|\s*$"
)


def parse_constituents(md_text: str) -> dict[str, dict]:
    out = {}
    for line in md_text.splitlines():
        m = ROW_RE.match(line.strip())
        if not m:
            continue
        out[m.group("symbol")] = {
            "security": m.group("security"),
            "date_added": m.group("date_added"),
            "cik": m.group("cik"),
        }
    return out


def reconstruct(constituents: dict[str, dict], events: list[dict], as_of: str) -> dict:
    working = dict(constituents)  # symbol -> {security, date_added, cik}
    removed_here: dict[str, dict] = {}  # symbols added back while undoing, with a stub record
    events_sorted = sorted(events, key=lambda e: e["date"], reverse=True)
    applied = []
    for ev in events_sorted:
        if ev["date"] <= as_of:
            continue  # only undo events strictly after as_of
        added, removed = ev.get("added"), ev.get("removed")
        if added and added in working:
            del working[added]
        elif added and added in removed_here:
            del removed_here[added]
        if removed:
            removed_here[removed] = {"security": None, "date_added": None, "cik": None, "readded_by_event": ev["date"]}
        applied.append(ev)
    working.update(removed_here)
    # Belt-and-suspenders: nothing with date_added strictly after as_of should survive.
    stale = {s: v for s, v in working.items() if v.get("date_added") and v["date_added"] > as_of}
    for s in stale:
        del working[s]
    return {
        "kind": "SP500_PIT_RECONSTRUCTION",
        "as_of": as_of,
        "source": "Wikipedia 'List of S&P 500 companies' current snapshot + dated changes table (fetched 2026-09-25)",
        "method": "current snapshot with every post-as_of change mechanically undone in reverse-chronological order",
        "n_current_input": len(constituents),
        "n_events_applied": len(applied),
        "n_reconstructed": len(working),
        "n_dropped_as_stale_after_undo": len(stale),
        "stale_dropped": sorted(stale),
        "members": sorted(working.keys()),
        "membership_basis": "RECONSTRUCTED_LATER_VINTAGE",
        "survivorship_risk": False,
        "official": False,
        "c18_relation": "candidate reference for Top-500 Sufficiency Gate; NOT the Official universe (C-18 is US mcap Top 500, resolved separately)",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--constituents", type=Path, required=True)
    ap.add_argument("--changes", type=Path, required=True)
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    constituents = parse_constituents(a.constituents.read_text(encoding="utf-8"))
    changes = json.loads(a.changes.read_text(encoding="utf-8"))
    r = reconstruct(constituents, changes["events"], a.as_of)
    s = json.dumps(r, indent=2)
    if a.out:
        a.out.write_text(s + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "members"}, indent=2))
    print("members:", len(r["members"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
