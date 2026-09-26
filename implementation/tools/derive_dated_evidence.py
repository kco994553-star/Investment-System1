"""Carry reviewed filing evidence to another as_of WITHOUT future information.

From the reviewed symbol_mappings_<from>.json / class_economics_<from>.json, write <to>-dated files that keep only
citations whose filing date is on or before <to>. A symbol mapping is kept only if a citation remains; a class
determination only if every claim its basis requires is still supported by a remaining citation. Nothing is added or
re-worded: the gate chain re-verifies each quote verbatim in the stored filing (same CIK, filed <= as_of) and uses the
share counts of the <to> cover filing. Issuers that drop out stay blockers for <to> until reviewed from <= <to> filings.

Usage: python tools/derive_dated_evidence.py --from 2024-12-31 --to 2024-09-30
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GE = ROOT / "reports" / "gate_evidence"
BASIS_CLAIMS = {"CONVERTIBLE_INTO_LISTED": {"conversion_ratio"},
                "PAIRED_UNITS_EXCHANGEABLE_INTO_LISTED": {"pairing", "exchange_ratio"},
                "ECONOMICALLY_IDENTICAL_TO_LISTED": {"identical_rights"}}


def keep_citations(cites: list[dict], to: str) -> list[dict]:
    return [c for c in cites or [] if str(c.get("filed") or "9999") <= to]


def derive_symbol_mappings(src: dict, to: str) -> tuple[dict, dict]:
    kept, dropped = {}, {}
    for cik, m in (src.get("issuers") or {}).items():
        cites = keep_citations(m.get("citations"), to)
        if cites:
            kept[cik] = {**m, "citations": cites}
        else:
            dropped[m.get("symbol") or cik] = "NO_CITATION_FILED_ON_OR_BEFORE_AS_OF"
    return {**src, "as_of": to, "issuers": kept, "derived_from": src.get("as_of"), "dropped": dropped}, dropped


def derive_class_economics(src: dict, to: str) -> tuple[dict, dict]:
    kept, dropped = {}, {}
    for cik, det in (src.get("issuers") or {}).items():
        classes, ok = {}, True
        for member, cd in (det.get("classes") or {}).items():
            cites = keep_citations(cd.get("citations"), to)
            need = BASIS_CLAIMS.get(cd.get("basis"), {"UNKNOWN"})
            have = {s for c in cites for s in c.get("supports") or []}
            if not need <= have:
                ok = False
                dropped[det.get("symbol") or cik] = f"{member}: claims {sorted(need - have)} have no citation filed on or before {to}"
                break
            # only citations supporting a required claim or context of this class remain
            classes[member] = {**cd, "citations": cites}
        if ok:
            kept[cik] = {**det, "classes": classes}
    return {**src, "as_of": to, "issuers": kept, "derived_from": src.get("as_of"), "dropped": dropped}, dropped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--to", dest="dst", required=True)
    a = ap.parse_args()
    if a.dst >= a.src:
        raise SystemExit("evidence is only carried to an EARLIER as_of (citations are filtered by filing date)")
    out = {}
    for name, fn in (("symbol_mappings", derive_symbol_mappings), ("class_economics", derive_class_economics)):
        p = GE / f"{name}_{a.src}.json"
        if not p.exists():
            continue
        doc, dropped = fn(json.loads(p.read_text(encoding="utf-8")), a.dst)
        (GE / f"{name}_{a.dst}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        out[name] = {"kept": sorted(v.get("symbol") for v in doc["issuers"].values()), "dropped": dropped}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
