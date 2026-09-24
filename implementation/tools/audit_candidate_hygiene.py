"""Offline, heuristic scope-hygiene audit for a candidate listings map.

An "investable US common-stock Top 500" ranking pool should hold one row per
company's primary common equity -- not preferred share classes (fixed-income-
like, shouldn't compete for a common-stock cap ranking) and not foreign OTC
ADR/ordinary tickers whose PRIMARY listing is a non-US exchange (WFE/Russell/
CRSP-style universes exclude these; see Conflict Register C-18/C-22 research).

This tool is PATTERN-BASED HEURISTICS ONLY. It never deletes or reclassifies
anything -- it flags tickers by suffix/shape for a human or a later,
better-sourced pass to verify against real SEC security-type data (e.g. the
'series'/'securityType' fields on a submissions/company_tickers_exchange
record). Do not treat its output as ground truth; do not silently drop
flagged tickers from a listings.json without checking. A generalizable
pattern check, not a per-company hardcode.

No network.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

# NYSE/Nasdaq preferred-share suffix convention: "-P" followed by a series
# letter (BAC-PL, ALL-PH), or a bare "-A"/"-B" style is a share class, not
# necessarily preferred -- only the "-P<letter>" shape is flagged here.
PREFERRED_RE = re.compile(r"-P[A-Z]$")
# Common OTC Pink / foreign-ADR ticker shape: exactly 5 letters ending in F
# (foreign ordinary/ADR, e.g. AEMRF) or Y (ADR, e.g. BBAAY). This is a
# widely-used but NOT universal convention -- some legitimate 5-letter
# Nasdaq tickers also end in these letters (rare). Flag, don't assume.
OTC_ADR_RE = re.compile(r"^[A-Z]{5}$")


def classify(ticker: str) -> str | None:
    t = ticker.upper()
    if PREFERRED_RE.search(t):
        return "PREFERRED_SHARE_SUFFIX"
    if len(t) == 5 and t.isalpha() and t[-1] in ("F", "Y"):
        return "FIVE_LETTER_F_OR_Y_OTC_ADR_SHAPE"
    return None


def audit_hygiene(listings: dict) -> dict:
    flagged: dict[str, list[str]] = {"PREFERRED_SHARE_SUFFIX": [], "FIVE_LETTER_F_OR_Y_OTC_ADR_SHAPE": []}
    clean = []
    for cid, m in sorted(listings.items()):
        t = str(m.get("yahoo") or "").upper()
        reason = classify(t) if t else None
        if reason:
            flagged[reason].append(cid)
        else:
            clean.append(cid)
    return {
        "kind": "CANDIDATE_HYGIENE_AUDIT_HEURISTIC",
        "n_total": len(listings),
        "n_flagged": sum(len(v) for v in flagged.values()),
        "n_clean": len(clean),
        "flagged": {k: sorted(v) for k, v in flagged.items()},
        "clean_company_ids": sorted(clean),
        "note": ("PATTERN HEURISTIC ONLY, not authoritative. Flags likely preferred-share and "
                 "foreign-OTC-ADR tickers so a network-enabled pass can prioritize fetching genuine "
                 "common-equity candidates first and verify each flagged ticker's real SEC security "
                 "type before excluding it. Never auto-applied to ranking or any gate."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--listings", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    listings = json.loads(a.listings.read_text(encoding="utf-8"))
    r = audit_hygiene(listings)
    s = json.dumps(r, indent=2)
    if a.out:
        a.out.write_text(s + "\n", encoding="utf-8")
    print(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
