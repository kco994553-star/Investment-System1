"""Track E — Prompt Library v1 runtime tests (E0-E8) against the Frozen PLV1_CONTENT_V1.0 catalog."""
import ast
import dataclasses
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_system.prompt_library import catalog as C
from investment_system.prompt_library.catalog import (CatalogIntegrityError, RetiredPromptError, build_catalog,
                                                      load_catalog, resolve)
from investment_system.prompt_library.fill import (NOT_PROVIDED, VariableFillError, bundle_variables, copy_text,
                                                   export, fill, preview, variable_specs)
from investment_system.prompt_library.search import SearchFilterError, facets, search
from investment_system.prompt_library.ui import DEFAULT_OUT, JS, catalog_payload, render_html
from investment_system.prompt_library.validation import validate_catalog, validate_prompt

PKG = Path(C.__file__).resolve().parent
NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
TECH_OK = {"input_mode": "SYSTEM_CONTEXT", "ticker": "AAPL", "period": "1Y", "as_of": "2024-12-31",
           "technical_input": "TechnicalSnapshot 2024-12-31 (pasted)"}


def _cat():
    return load_catalog()  # cached per content dir (deterministic); plain helper, runs under pytest and mini_pytest


# ---------- E0 Frozen catalog loader / integrity ----------

def test_frozen_files_match_pinned_hashes_and_loader_is_deterministic():
    cat = _cat()
    raw = (PKG / "content" / C.CATALOG_FILE).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == C.FROZEN_CATALOG_SHA256 == cat.sha256
    hist = (PKG / "content" / C.DECISION_HISTORY_FILE).read_text(encoding="utf-8")
    assert f"Frozen catalog SHA-256: `{C.FROZEN_CATALOG_SHA256}`" in hist  # Decision History records the same hash
    again = build_catalog(raw.decode("utf-8"), hist, C.FROZEN_CATALOG_SHA256)
    assert again.prompts == cat.prompts and again.migrations == cat.migrations and again.bundles == cat.bundles
    assert cat.content_version == "PLV1_CONTENT_V1.0" and "CONTENT FROZEN" in cat.status_line
    assert cat.freeze_time == "2026-09-27 12:36:40 KST" and cat.schema_version == "plv1.runtime.schema.v1"


def test_altered_or_missing_frozen_content_fails_closed(tmp_path):
    d = tmp_path / "content"
    shutil.copytree(PKG / "content", d)
    f = d / C.CATALOG_FILE
    f.write_text(f.read_text(encoding="utf-8").replace("Margin 개선", "Margin 향상", 1), encoding="utf-8")
    with pytest.raises(CatalogIntegrityError, match="FROZEN_CONTENT_HASH_MISMATCH"):
        load_catalog(d)
    f.unlink()
    with pytest.raises(CatalogIntegrityError, match="CATALOG_NOT_PRESENT"):
        load_catalog(d)


def test_build_rejects_structurally_broken_text():
    text = (PKG / "content" / C.CATALOG_FILE).read_text(encoding="utf-8")
    hist = (PKG / "content" / C.DECISION_HISTORY_FILE).read_text(encoding="utf-8")
    one_less = re.sub(r"\n### IDEA-005\.v1\.0.*?(?=\n### )", "", text, count=1, flags=re.S)
    with pytest.raises(CatalogIntegrityError):
        build_catalog(one_less, hist, "x")
    with pytest.raises(CatalogIntegrityError):
        build_catalog(text.replace("- status: `ACTIVE`", "- status: `DRAFT`", 1), hist, "x")


# ---------- E1 schema / identity / migration ----------

def test_70_active_identity_and_distributions():
    cat = _cat()
    ps = cat.active()
    assert len(ps) == 70 and len({p.prompt_id for p in ps}) == 70 and len({p.prompt_code for p in ps}) == 70
    assert all(p.status == "ACTIVE" and p.prompt_code == f"{p.legacy_code}.v1.0" for p in ps)
    assert all(re.fullmatch(r"plv1\.(idea|fund|tech|macro|cross)\.\d{3}", p.prompt_id) for p in ps)
    assert dict(Counter(p.domain for p in ps)) == {"DISCOVERY": 13, "FUNDAMENTAL": 21, "TECHNICAL": 14, "MACRO": 13,
                                                   "CROSS_VALIDATION": 9}
    assert dict(Counter(p.role for p in ps)) == {"BASIC": 8, "EXPAND": 34, "CHALLENGE": 10, "BLIND-SPOT": 18}
    assert dict(Counter(p.system_overlap for p in ps)) == {"LOW_TO_MEDIUM": 13, "HIGH_CONTROLLED": 57}


def test_active_ids_match_decision_history_continuity_list():
    cat = _cat()
    hist = (PKG / "content" / C.DECISION_HISTORY_FILE).read_text(encoding="utf-8")
    listed = re.findall(r"^- `(plv1\.[a-z]+\.\d{3})` → `([A-Z]+-\d{3}\.v1\.0)`$", hist, re.M)
    assert len(listed) == 70
    assert {pid: code for pid, code in listed} == {p.prompt_id: p.prompt_code for p in cat.active()}


def test_merge_and_retire_migration_preserved_and_resolvable():
    cat = _cat()
    migs = list(cat.migrations.values())
    assert Counter(m.status for m in migs) == {"MERGED_INTO": 38, "RETIRED_SYSTEM_OVERLAP": 6}
    assert len({m.target_prompt_id for m in migs if m.status == "MERGED_INTO"}) == 22
    assert len(cat.prompts) + len(cat.migrations) == 114 and not set(cat.prompts) & set(cat.migrations)
    for m in migs:
        if m.status == "MERGED_INTO":
            for ident in (m.prompt_id, m.legacy_code):
                r = resolve(cat, ident)
                assert r.via == "MERGED_INTO" and r.prompt.prompt_id == m.target_prompt_id and r.migration == m
            assert m.prompt_id in cat.prompts[m.target_prompt_id].aliases
        else:
            for ident in (m.prompt_id, m.legacy_code):
                with pytest.raises(RetiredPromptError) as e:
                    resolve(cat, ident)
                assert e.value.migration.replacement_path
    assert resolve(cat, "plv1.tech.001").via == "PROMPT_ID"
    assert resolve(cat, "TECH-001.v1.0").via == "PROMPT_CODE" and resolve(cat, "TECH-001").via == "LEGACY_CODE"
    with pytest.raises(KeyError, match="UNKNOWN_PROMPT_IDENTIFIER"):
        resolve(cat, "TECH-999")


def test_records_are_immutable():
    cat = _cat()
    p = cat.get("plv1.tech.001")
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.body = "changed"
    with pytest.raises(TypeError):
        cat.prompts["plv1.x.999"] = p


# ---------- E2 validation (content contracts) ----------

def test_every_prompt_passes_contract_checks():
    cat = _cat()
    assert validate_catalog(cat) == []
    for p in cat.active():
        assert validate_prompt(p) == [], p.prompt_code
        assert "as_of" in p.variables and "{{as_of}}" in p.body
        assert set(C.variables_in(p.body)) == set(p.variables)


def test_input_mode_contract_tech_macro_only():
    cat = _cat()
    tm = [p for p in cat.active() if p.requires_input_mode]
    assert len(tm) == 27 and {p.domain for p in tm} == {"TECHNICAL", "MACRO"}
    assert all(p.domain in ("TECHNICAL", "MACRO") for p in tm)
    p = cat.get("plv1.macro.001")
    broken = dataclasses.replace(p, body=p.body.replace("`INSUFFICIENT_DATA`로 종료해", "추정해"))
    assert any("INSUFFICIENT_DATA" in e for e in validate_prompt(broken))
    stray = dataclasses.replace(cat.get("plv1.fund.002"), variables=cat.get("plv1.fund.002").variables + ("input_mode",))
    assert any("undeclared" in e or "unused" in e or "outside TECH/MACRO" in e for e in validate_prompt(stray))


def test_validation_detects_body_variable_drift():
    cat = _cat()
    p = cat.get("plv1.idea.005")
    assert any("not declared" in e for e in validate_prompt(dataclasses.replace(p, body=p.body + "{{extra}}")))
    assert any("unused" in e for e in validate_prompt(dataclasses.replace(p, variables=p.variables + ("ghost",))))


# ---------- Starter / Bundle ----------

def test_starters_and_bundles_reference_active_ids_only():
    cat = _cat()
    assert cat.starters == ("plv1.idea.020", "plv1.fund.030", "plv1.tech.001", "plv1.macro.001", "plv1.cross.014",
                            "plv1.cross.013")
    assert len(cat.bundles) == 10 and [b.number for b in cat.bundles] == list(range(1, 11))
    for b in cat.bundles:
        assert b.prompt_ids and all(pid in cat.prompts for pid in b.prompt_ids)
    assert {f.name for f in dataclasses.fields(C.Bundle)} == {"number", "name", "prompt_ids"}  # no body copy
    assert cat.bundles[3].name == "Technical 검증"
    assert cat.bundles[3].prompt_ids == ("plv1.tech.001", "plv1.tech.007", "plv1.tech.017", "plv1.tech.022")


# ---------- E3 search / filter ----------

def test_search_filters():
    cat = _cat()
    assert len(search(cat)) == 70
    assert len(search(cat, domain="TECHNICAL")) == 14 and len(search(cat, role="BLIND-SPOT")) == 18
    assert {p.prompt_id for p in search(cat, starter=True)} == set(cat.starters)
    assert len(search(cat, starter=False)) == 64
    assert [p.prompt_id for p in search(cat, bundle=4)] == list(cat.bundles[3].prompt_ids)  # bundle order kept
    assert len(search(cat, input_mode="STANDALONE")) == 27
    assert {p.prompt_id for p in search(cat, scope="COMPANY")} == {p.prompt_id for p in cat.active() if
                                                                   {"company", "ticker", "seed_company", "seed_ticker"} & set(p.variables)}
    assert [p.prompt_code for p in search(cat, "Delta Evidence", domain="CROSS_VALIDATION")] == ["CROSS-015.v1.0"]
    assert "plv1.tech.001" in {p.prompt_id for p in search(cat, "TECH-002")}  # merged legacy code found via alias
    assert search(cat, "절대로없는검색어") == ()
    for bad in ({"domain": "FUND"}, {"role": "basic"}, {"scope": "SECTOR"}, {"input_mode": "AUTO"}, {"bundle": 99},
                {"category": "X"}):
        with pytest.raises(SearchFilterError):
            search(cat, **bad)
    f = facets(cat)
    assert sum(f["domain"].values()) == 70 and f["scope"]["COMPANY"] == len(search(cat, scope="COMPANY"))


# ---------- E4 variable fill (fail-closed, PIT) ----------

def test_fill_substitutes_every_variable_without_mutating_canonical_body():
    cat = _cat()
    p = cat.get("plv1.tech.001")
    before = p.body
    out = fill(p, TECH_OK, now=NOW)
    assert "{{" not in out and "AAPL" in out and "`2024-12-31` 시점에" in out and "`SYSTEM_CONTEXT`" in out
    assert p.body == before == cat.get("plv1.tech.001").body
    assert copy_text(p, TECH_OK, now=NOW) == out


def test_fill_fail_closed_cases():
    cat = _cat()
    p = cat.get("plv1.tech.001")
    cases = [
        ({k: v for k, v in TECH_OK.items() if k != "technical_input"}, "missing required"),
        ({**TECH_OK, "as_of": ""}, "missing required"),
        ({**TECH_OK, "as_of": "31/12/2024"}, "ISO date"),
        ({**TECH_OK, "as_of": "2024-12-31T10:00:00"}, "ISO date"),  # naive datetime is ambiguous
        ({**TECH_OK, "as_of": "2026-10-01"}, "future"),
        ({**TECH_OK, "input_mode": "AUTO"}, "input_mode"),
        ({**TECH_OK, "ticker": "{{ticker}}"}, "braces"),
        ({**TECH_OK, "tickr": "AAPL"}, "unknown variables"),
    ]
    for vals, msg in cases:
        with pytest.raises(VariableFillError, match=msg):
            fill(p, vals, now=NOW)
    assert "2024-12-31T10:00:00+09:00" in fill(p, {**TECH_OK, "as_of": "2024-12-31T10:00:00+09:00"}, now=NOW)


def test_prior_cutoff_must_precede_as_of_and_candidate_count_is_positive():
    cat = _cat()
    p = cat.get("plv1.cross.015")
    ok = {"company": "Apple", "ticker": "AAPL", "system_summary": "S", "as_of": "2024-12-31", "prior_cutoff": "2024-09-30"}
    assert "2024-09-30" in fill(p, ok, now=NOW)
    for prior in ("2024-12-31", "2025-01-15"):
        with pytest.raises(VariableFillError, match="prior_cutoff"):
            fill(p, {**ok, "prior_cutoff": prior}, now=NOW)
    d = cat.get("plv1.idea.005")
    dv = {"universe": "US large cap", "candidate_count": "10", "as_of": "2024-12-31", "existing_system_candidates": "none"}
    assert "`10`" in fill(d, dv, now=NOW)
    for n in ("0", "-3", "ten"):
        with pytest.raises(VariableFillError, match="positive integer"):
            fill(d, {**dv, "candidate_count": n}, now=NOW)


def test_only_qgv_snapshot_summary_is_optional():
    cat = _cat()
    specs = {s.name: s for p in cat.active() for s in variable_specs(p)}
    assert {n for n, s in specs.items() if not s.required} == {"qgv_snapshot_summary"}
    fund = cat.get("plv1.fund.002")
    out = fill(fund, {"company": "Apple", "ticker": "AAPL", "as_of": "2024-12-31"}, now=NOW)
    assert f"기존 QGV 요약은 `{NOT_PROVIDED}`다" in out
    assert specs["technical_input"].system_input_owner == "TECHNICAL" and specs["macro_input"].system_input_owner == "MACRO"


# ---------- E5 preview / E6 copy-export ----------

def test_preview_partial_then_ready():
    cat = _cat()
    p = cat.get("plv1.tech.001")
    pv = preview(p, {"ticker": "AAPL", "as_of": "2099-01-01"}, now=NOW)
    assert not pv.ready_to_copy and "input_mode" in pv.missing and any("future" in i for i in pv.invalid)
    assert "`AAPL`" in pv.text and "{{as_of}}" in pv.text and "{{input_mode}}" in pv.text  # invalid value not shown
    full = preview(p, TECH_OK, now=NOW)
    assert full.ready_to_copy and full.text == copy_text(p, TECH_OK, now=NOW)


def test_bundle_export_text_and_json():
    cat = _cat()
    b = cat.bundles[3]
    vals = {**TECH_OK, "news_event_evidence": "(paste events)"}
    assert [s.name for s in bundle_variables(cat, 4)] == ["input_mode", "ticker", "period", "as_of", "technical_input",
                                                          "news_event_evidence"]
    txt = export(cat, b.prompt_ids, vals, now=NOW)
    codes = [cat.prompts[pid].prompt_code for pid in b.prompt_ids]
    assert [m for m in re.findall(r"^----- \[\d/4\] (\S+) -----$", txt, re.M)] == codes and "{{" not in txt
    js = json.loads(export(cat, b.prompt_ids, vals, fmt="json", now=NOW))
    assert [x["prompt_id"] for x in js] == list(b.prompt_ids)
    assert all(x["catalog_sha256"] == C.FROZEN_CATALOG_SHA256 and x["as_of"] == "2024-12-31" for x in js)
    with pytest.raises(VariableFillError):
        export(cat, b.prompt_ids, TECH_OK, now=NOW)  # news_event_evidence missing for one member
    with pytest.raises(VariableFillError, match="unknown"):
        export(cat, b.prompt_ids, {**vals, "company": "x"}, now=NOW)


# ---------- E7 UI ----------

def test_ui_embeds_canonical_bodies_verbatim_and_committed_page_is_current():
    cat = _cat()
    payload = catalog_payload(cat)
    assert [x["prompt_id"] for x in payload["prompts"]] == list(cat.prompts)
    assert all(x["body"] == cat.prompts[x["prompt_id"]].body for x in payload["prompts"])
    page = render_html(cat)
    data = json.loads(re.search(r'<script type="application/json" id="plv1-data">(.*?)</script>', page, re.S)
                      .group(1).replace("<\\/", "</"))
    assert data == json.loads(json.dumps(payload, ensure_ascii=False))
    assert "http://" not in page and "https://" not in page  # self-contained: no external script / network
    assert DEFAULT_OUT.exists() and DEFAULT_OUT.read_text(encoding="utf-8") == page, \
        "run: python tools/prompt_library.py render-html"


def test_browser_checks_match_python_rules(tmp_path):
    cat = _cat()
    node = shutil.which("node")
    if not node:
        return  # node not installed (CI python-only): the Python rules above are the contract
    p = cat.get("plv1.cross.015")
    cases = [{"company": "A", "ticker": "T", "system_summary": "S", "as_of": "2024-12-31", "prior_cutoff": "2024-09-30"},
             {"company": "A", "ticker": "T", "system_summary": "S", "as_of": "2024-12-31", "prior_cutoff": "2024-12-31"},
             {"company": "A", "ticker": "{{x}}", "as_of": "2099-01-01"}, {"as_of": "31/12/2024", "zzz": "1"}]
    data = json.dumps(catalog_payload(cat), ensure_ascii=False)
    script = ("const document={getElementById:()=>({textContent:" + json.dumps(data) + "})};\n" + JS +
              "\nconst p=DATA.prompts.find(x=>x.prompt_id==='plv1.cross.015');\n" +
              f"console.log(JSON.stringify({json.dumps(cases)}.map(v=>plvCheck(p,v,'{NOW.isoformat()}'))));")
    f = tmp_path / "t.js"
    f.write_text(script, encoding="utf-8")
    got = json.loads(subprocess.run([node, str(f)], capture_output=True, text=True, check=True).stdout)
    for vals, js in zip(cases, got):
        pv = preview(p, vals, now=NOW)
        assert js["text"] == pv.text and js["ready"] == pv.ready_to_copy
        assert js["missing"] == list(pv.missing) and js["unknown"] == list(pv.unknown)
        assert [i.split(":")[0] for i in js["invalid"]] == [i.split(":")[0] for i in pv.invalid]


# ---------- boundaries ----------

def test_package_depends_on_nothing_outside_itself():
    """Track E never imports Track A/B/C/D code or QGV/Technical/Macro engines, and uses no network library."""
    banned_net = {"urllib", "http", "requests", "socket", "httpx", "aiohttp"}
    for f in PKG.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    assert not (node.module or "").startswith("investment_system"), (f.name, node.module)
                    assert (node.module or "").split(".")[0] not in banned_net, (f.name, node.module)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    assert not a.name.startswith("investment_system") and a.name.split(".")[0] not in banned_net
