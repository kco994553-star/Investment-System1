"""Build a production-shaped Web fixture for state presentation (freshness, withheld metadata).

Validation only. Every section value is a literal TEST VECTOR, never real investment data and never
a grant. No engine, provider, calibration or Holdout is called. The bundle is produced by the real
producer path (contract.make_snapshot / not_available -> assembler.assemble_bundle with an explicit
evaluation clock), so freshness and reason codes are the values the assembler persists. It is then
passed to the existing, unchanged web_mvp.build (which runs the existing schema-1 validator).

Served bundle (data.json), assembled at NOW:
  universe       FROZEN_SNAPSHOT (Track A, existing FrozenUniverseProducer)
  macro          LIVE, persisted freshness FRESH (expires far in the future)
  technical      LIVE, persisted freshness STALE (expired before NOW, no usable_until)
  changes        LIVE, persisted freshness FRESH at NOW, but expires_at is before the browser clock:
                 the existing view-time rule shows STALE
  leaderboard    LIVE past usable_until -> the assembler publishes NOT_AVAILABLE + EXPIRED_NOT_USABLE
  qgv            NOT_AVAILABLE with persisted producer metadata (reason_code, as_of, methodology, counts)
  portfolio, news, relationships   NOT_AVAILABLE from the existing default registry

Variants (written to the evidence folder, never served directly; the browser test substitutes them):
  variant-not-usable.json      a section that still carries values although its persisted freshness is
                               NOT_USABLE (news via producer.freshness, changes via producer_manifest)
  variant-sparse-metadata.json producer metadata removed, except one reason_code (nothing is fabricated)
  variant-render-error.json    schema-1-valid bundle whose news payload is an object, not a list; the
                               news route throws while rendering
  variant-expiry-{basic-format,week-date,comma-fraction}.json
                               assembled like the served bundle, except that changes.expires_at is the same
                               instant in an ISO form Python's fromisoformat accepts and JS Date.parse rejects;
                               the assembler persists FRESH, the Web must never show FRESH for it
  variant-free-text-metadata.json  assembled like the served bundle, with contract-valid but not code/token
                               shaped reason_code and methodology id/version values the Web must not display
  variant-expiry-*-separator*.json  assembled like the served bundle, except that changes.expires_at uses a '(' or
                               U+0000 date/time separator: contract.parse_ts accepts it, Date.parse reads a later
                               instant; the assembler persists FRESH, the Web must never show FRESH for it
  variant-expiry-strict-*.json changes.expires_at at the same instant as the served bundle in the strict forms
                               producers persist (isoformat(), with/without fractional seconds, Z or +-hh:mm):
                               FRESH before expiry, STALE after it
  variant-free-text-count-keys.json  assembled like the served bundle, with count keys (validation.coverage_counts
                               and validation.*_count) outside the code/token key shape the Web must not display

Usage:
  python tools/build_web_state_presentation_fixture.py --out /tmp/web-state --evidence /tmp/web-state-evidence
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.product.web_mvp import build, validate_bundle  # noqa: E402
from investment_system.producers.assembler import assemble_bundle  # noqa: E402
from investment_system.producers.contract import make_snapshot, not_available, parse_ts, validate_snapshot  # noqa: E402
from investment_system.producers.registry import (  # noqa: E402
    DEFAULT_REASON, FrozenUniverseProducer, ProduceRequest, default_registry,
)

NOW = datetime(2026, 1, 2, tzinfo=timezone.utc)  # explicit assembly clock
# The browser test pins its clock here, so the view-time STALE of `changes` does not depend on the CI date.
BROWSER_CLOCK = "2026-10-03T12:00:00Z"
AS_OF = "2026-01-01T20:00:00+00:00"
COMPANY = "nvda"
METHOD = {"id": "TEST_VECTOR", "version": "TEST_VECTOR_V1", "status": "VALIDATED"}
INPUTS = [{"artifact_id": "test:web-state-presentation", "sha256": "0" * 64}]
# Present only in withheld inputs; must never reach the DOM.
WITHHELD_PROBES = ("4321.98765", "NOT_USABLE_PROBE_NEWS", "NOT_USABLE_PROBE_CHANGES")
# changes.expires_at (2026-01-03T00:00:00+00:00) in ISO forms that contract.parse_ts accepts and JS Date.parse rejects.
UNPARSABLE_EXPIRY = {"variant-expiry-basic-format.json": "20260103T000000Z",
                     "variant-expiry-week-date.json": "2026-W01-6T00:00:00+00:00",
                     "variant-expiry-comma-fraction.json": "2026-01-03T00:00:00,5+00:00"}
# Contract-valid persisted identifiers outside the displayed shapes (reason_code ^[A-Z][A-Z0-9_]{0,63}$,
# methodology id/version <= 64 characters without whitespace): never displayed. EDGE_* are inside them: displayed.
FREE_TEXT = {"qgv.reason_code": "See memo FREE_TEXT_PROBE_REASON: withheld pending owner review\nsecond line",
             "qgv.methodology.id": "FREE TEXT PROBE METHOD",
             "qgv.methodology.version": "LONG_PROBE_VERSION_" + "9" * 46,
             "portfolio.reason_code": "LONG_PROBE_CODE_" + "X" * 49,
             "relationships.reason_code": "lower_probe_code"}
# changes.expires_at in forms contract.parse_ts accepts and Date.parse reads as a LATER instant (V8 treats '(' as
# the start of a comment and stops at U+0000, leaving the date part as midnight): never FRESH after the Python-parsed
# expiry, in any browser time zone. AFTER_EXPIRY are browser clocks after that expiry, inside the window in which
# Date.parse alone would still read the form as not yet expired.
MISPARSED_EXPIRY = {"variant-expiry-paren-separator.json": "2026-01-03(00:00+23:59",
                    "variant-expiry-nul-separator.json": "2026-01-03\u000000:00+23:59",
                    "variant-expiry-paren-separator-utc.json": "2026-01-03(00:00:00+00:00"}
AFTER_EXPIRY = (timedelta(minutes=1), timedelta(hours=6), timedelta(hours=12))
TIMEZONES = ("UTC", "Etc/GMT+12", "Pacific/Kiritimati", "Asia/Seoul")
# changes.expires_at at the served instant (2026-01-03T00:00:00Z, plus a fraction) in the strict forms producers
# persist: datetime.isoformat() of an aware datetime (copied verbatim by the assembler) and the Z spelling.
STRICT_EXPIRY = {"variant-expiry-strict-z.json": "2026-01-03T00:00:00Z",
                 "variant-expiry-strict-minutes-z.json": "2026-01-03T00:00Z",
                 "variant-expiry-strict-fraction-z.json": "2026-01-03T00:00:00.5Z",
                 "variant-expiry-strict-microseconds.json":
                     datetime(2026, 1, 3, 0, 0, 0, 123456, tzinfo=timezone.utc).isoformat(),
                 "variant-expiry-strict-plus-0900.json":
                     datetime(2026, 1, 3, tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9))).isoformat(),
                 "variant-expiry-strict-minus-1200-fraction.json":
                     datetime(2026, 1, 3, 0, 0, 0, 250000, tzinfo=timezone.utc).astimezone(
                         timezone(timedelta(hours=-12))).isoformat()}
# Persisted count keys outside the displayed key shape ^[A-Za-z][A-Za-z0-9_]{0,63}$ (free text, multi-line,
# 65 characters, leading underscore, dash, markup): the entry is never displayed. Every one contains
# COUNT_KEY_PROBE. COUNT_KEY_EDGE keys are inside the shape (64 characters, lower case): displayed.
COUNT_KEY_PROBE = "COUNT_KEY_PROBE"
FREE_TEXT_COUNT_KEYS = {
    "qgv.validation.coverage_counts": {"See memo COUNT_KEY_PROBE_SPACE": 7, "COUNT_KEY_PROBE_NEWLINE\nsecond line": 1,
                                       "COUNT_KEY_PROBE_LONG_" + "9" * 44: 2, "_COUNT_KEY_PROBE_UNDERSCORE": 3,
                                       "COUNT_KEY_PROBE-DASH": 4, "<b>COUNT_KEY_PROBE_HTML</b>": 5},
    "qgv.validation": {"free text COUNT_KEY_PROBE_VALIDATION_count": 9, "COUNT_KEY_PROBE_VLONG_" + "9" * 37 + "_count": 11},
    "leaderboard.validation": {"Ranked rows (see memo) COUNT_KEY_PROBE_LB_count": 1}}
COUNT_KEY_EDGE = {"qgv.validation.coverage_counts": {"EDGE_COUNT_KEY_" + "9" * 49: 6, "lower_case_key": 8},
                  "qgv.validation": {"edge_" + "9" * 53 + "_count": 10}}
FREE_TEXT_PROBES = ("FREE_TEXT_PROBE_REASON", "FREE TEXT PROBE METHOD", "LONG_PROBE_VERSION_", "LONG_PROBE_CODE_",
                    "lower_probe_code")
EDGE = {"news.reason_code": "EDGE_CODE_" + "9" * 54, "relationships.methodology.version": "EDGE_TOKEN_" + "9" * 53}


def _live(section, data, scope_kind, as_of, expires_at, usable_until=None, validation=None):
    return validate_snapshot(make_snapshot(
        producer_id=f"test.web_state.{section}", producer_version="TEST_VECTOR_V1", section=section,
        data_state="LIVE", as_of=as_of, requested_as_of=as_of, generated_at=NOW.isoformat(),
        expires_at=expires_at, usable_until=usable_until, methodology=METHOD, synthetic=False,
        provenance={"source": f"TEST VECTOR / {section}", "inputs": INPUTS},
        validation=validation or {"status": "PASS", "checks": ["TEST_VECTOR_SHAPE_ONLY"]},
        data=data, scope_kind=scope_kind))


def snapshots() -> dict:
    snaps = default_registry().run(ProduceRequest(NOW, NOW))
    snaps["macro"] = _live("macro", {"state": "NORMAL", "regime": "TEST_REGIME_FRESH", "indicators": {"CPIAUCSL": 33.33},
                                     "exposures": {COMPANY: "TEST_EXPOSURE_FRESH"}},
                           "DOCUMENT", AS_OF, "2099-01-01T00:00:00+00:00")
    snaps["technical"] = _live("technical", {COMPANY: {"regime": "TEST_REGIME_STALE", "execution_zone": "WAIT",
                                                       "invalidation": "TEST_INVALIDATION_STALE"}},
                               "ENTITY_MAP", "2026-01-01T00:00:00+00:00", "2026-01-01T12:00:00+00:00")
    snaps["changes"] = _live("changes", {"summary": "TEST_CHANGES_VIEW_STALE"}, "DOCUMENT", AS_OF,
                             "2026-01-03T00:00:00+00:00")
    snaps["leaderboard"] = _live("leaderboard", {"rows": [{"company_id": COMPANY, "ticker": "NVDA", "rank": 1,
                                                           "total_score": 4321.98765}]},
                                 "ROWS", "2025-12-30T00:00:00+00:00", "2025-12-31T00:00:00+00:00",
                                 usable_until="2026-01-01T00:00:00+00:00",
                                 validation={"status": "PASS", "checks": ["TEST_VECTOR_SHAPE_ONLY"],
                                             "expected_count": 1, "ranked_count": 1})
    qgv = not_available("qgv", "test.web_state.qgv", "TEST_VECTOR_V1", NOW.isoformat(), DEFAULT_REASON,
                        "RESEARCH_DISPLAY_GRANT_NONE", NOW.isoformat(),
                        {"id": "TEST_QGV", "version": "TEST_VECTOR_V1", "status": "PROVISIONAL_RESEARCH"})
    # Persisted producer metadata, distinct from section availability (same shape as the codex
    # withheld-contract fixture); none of it becomes section data or authority.
    qgv["as_of"] = AS_OF
    qgv["validation"] = {"status": "PASS", "checks": ["TEST_VECTOR_SHAPE_ONLY"],
                         "coverage_counts": {"COMPLETE": 3, "NONE": 1, "PARTIAL": 1}}
    snaps["qgv"] = validate_snapshot(qgv)
    return snaps


def fixture_bundle() -> dict:
    return assemble_bundle([{'company_id': COMPANY, 'ticker': 'NVDA', 'name': 'Test identity'}], snapshots(), NOW)


def _assembled(edit) -> dict:
    snaps = snapshots()
    edit(snaps)
    return assemble_bundle([{'company_id': COMPANY, 'ticker': 'NVDA', 'name': 'Test identity'}], snaps, NOW)


def _expiry(form):
    def edit(snaps):
        snaps["changes"] = _live("changes", {"summary": "TEST_CHANGES_VIEW_STALE"}, "DOCUMENT", AS_OF, form)
    return edit


def _free_text(snaps):
    for key, value in {**FREE_TEXT, **EDGE}.items():
        name, *path = key.split(".")
        target = snaps[name]
        if path[0] == "methodology":
            target["methodology"] = {**target["methodology"], path[1]: value}
        else:
            target[path[0]] = value


def _count_keys(snaps):
    for entries in (FREE_TEXT_COUNT_KEYS, COUNT_KEY_EDGE):
        for key, extra in entries.items():
            name, *path = key.split(".")
            target = snaps[name]
            for k in path[:-1]:
                target = target[k]
            target[path[-1]] = {**target[path[-1]], **extra}


def _utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def misparsed_expiry() -> dict:
    out = {}
    for name, form in MISPARSED_EXPIRY.items():
        expires = parse_ts(form, "expires_at")
        out[name] = {"form": form, "python_expires_at": _utc(expires),
                     "after_expiry_clocks": [_utc(expires + d) for d in AFTER_EXPIRY]}
    return out


def strict_expiry() -> dict:
    out = {}
    for name, form in STRICT_EXPIRY.items():
        expires = parse_ts(form, "expires_at")
        out[name] = {"form": form, "python_expires_at": _utc(expires),
                     "fresh_clock": _utc(expires - timedelta(seconds=1)), "stale_clock": _utc(expires + timedelta(seconds=1))}
    return out


def variants(bundle: dict) -> dict:
    not_usable = deepcopy(bundle)
    not_usable["news"] = {"state": "LIVE", "as_of": AS_OF, "source": "TEST VECTOR / news", "expires_at": "2099-01-01T00:00:00+00:00",
                          "data": [{"headline": "NOT_USABLE_PROBE_NEWS", "issuer_ids": [], "available_at": AS_OF,
                                    "source_language": "en"}],
                          "producer": {**deepcopy(bundle["macro"]["producer"]), "freshness": "NOT_USABLE"}}
    not_usable["changes"].pop("producer")
    not_usable["changes"]["data"] = {"summary": "NOT_USABLE_PROBE_CHANGES"}
    not_usable["producer_manifest"]["sections"]["changes"]["freshness"] = "NOT_USABLE"
    sparse = deepcopy(bundle)
    sparse.pop("producer_manifest")
    for name in ("universe", "qgv", "technical", "macro", "portfolio", "leaderboard", "news", "relationships", "changes"):
        sparse[name].pop("producer", None)
    sparse["portfolio"]["producer"] = {"reason_code": "ONLY_REASON_CODE_PERSISTED"}
    render_error = deepcopy(bundle)
    render_error["news"] = {"state": "FROZEN_SNAPSHOT", "as_of": AS_OF, "source": "TEST VECTOR / malformed news shape",
                            "data": {"unexpected": "object instead of a list"}}
    out = {"variant-not-usable.json": not_usable, "variant-sparse-metadata.json": sparse,
           "variant-render-error.json": render_error, "variant-free-text-metadata.json": _assembled(_free_text)}
    out.update({name: _assembled(_expiry(form)) for name, form in UNPARSABLE_EXPIRY.items()})
    out.update({name: _assembled(_expiry(form)) for name, form in MISPARSED_EXPIRY.items()})
    out.update({name: _assembled(_expiry(form)) for name, form in STRICT_EXPIRY.items()})
    out["variant-free-text-count-keys.json"] = _assembled(_count_keys)
    for v in out.values():
        validate_bundle(v)  # every variant is accepted by the existing, unchanged schema-1 validator
    return out


def manifest(bundle: dict) -> dict:
    sections = bundle["producer_manifest"]["sections"]
    return {"kind": "WEB_STATE_PRESENTATION_FIXTURE_V1", "scope": "TEST VECTORS ONLY; NOT_REAL_DATA; NO GRANT",
            "assembly_clock": NOW.isoformat(), "browser_clock": BROWSER_CLOCK, "company": COMPANY, "as_of": AS_OF,
            "persisted": {name: {"state": s["state"], "freshness": s["freshness"], "reason_code": s["reason_code"]}
                          for name, s in sections.items()},
            "expected_view": {"macro": "LIVE+FRESH", "technical": "LIVE+STALE", "changes": "LIVE+STALE (view-time)",
                              "leaderboard": "NOT_AVAILABLE+NOT_USABLE", "qgv": "NOT_AVAILABLE+metadata"},
            "withheld_probes": list(WITHHELD_PROBES), "variants": sorted(variants(bundle)),
            "unparsable_expiry": UNPARSABLE_EXPIRY, "free_text_probes": list(FREE_TEXT_PROBES), "edge": EDGE,
            "misparsed_expiry": misparsed_expiry(), "strict_expiry": strict_expiry(), "timezones": list(TIMEZONES),
            "count_key_probe": COUNT_KEY_PROBE, "free_text_count_keys": FREE_TEXT_COUNT_KEYS, "count_key_edge": COUNT_KEY_EDGE,
            "research_display": "NONE", "frozen_grant": "NONE", "live_grant": "NONE"}


def build_fixture(out, evidence) -> dict:
    from investment_system.public_price_boundary import block_public_route
    block_public_route()
    out, evidence = Path(out).resolve(), Path(evidence).resolve()
    if out == evidence or out in evidence.parents:
        raise ValueError("evidence must be outside the served Web folder")
    bundle = fixture_bundle()
    before = deepcopy(bundle)
    build(out, bundle)
    if json.loads((out / "data.json").read_text(encoding="utf-8")) != before:
        raise AssertionError("the Web build must not rewrite the bundle; presentation is render-time only")
    evidence.mkdir(parents=True, exist_ok=True)
    for name, v in variants(before).items():
        (evidence / name).write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
    m = manifest(before)
    (evidence / "fixture-manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return m


def main():
    from investment_system.public_price_boundary import block_public_route
    block_public_route()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    p.add_argument("--evidence", required=True)
    a = p.parse_args()
    print(json.dumps(build_fixture(a.out, a.evidence), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
