#!/usr/bin/env python3
"""Offline source evidence replay; does not import or admit production code.

Use --write to record the diagnostic result, otherwise compare existing output.
Source numbers are recovered from the authored Markdown and Python literal text,
not from binary floats, rounded display values, or another projection's totals.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / ".git").exists())
PREFIX = "implementation/experiments/chart-contract-v0.1/"
SPEC = "QGV Portfolio · Specification v1.1.md"
PORTFOLIO = "implementation/src/investment_system/qgv/portfolio.py"
IDENTIFIERS = "implementation/src/investment_system/qgv/identifiers.py"
CONFLICT = "Investment-System1 · Contract Conflict Register 2026-09-23.md"
REFERENCE = PREFIX + "portfolio_reference.json"
EXPECTED = {"반도체 장비": Decimal("30"), "AI·반도체": Decimal("25"),
            "Big Tech": Decimal("20"), "기타산업": Decimal("25")}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def pin_sources(manifest: dict) -> dict[str, str]:
    result = {}
    for item in manifest["source_pins"]:
        path = item["path"]
        payload = (ROOT / path).read_bytes()
        require(digest(payload) == item["sha256"], f"source bytes changed: {path}")
        require(len(payload) == item["size_bytes"], f"source length changed: {path}")
        baseline = manifest["refs"]["pr41_baseline"]
        baseline_read = subprocess.run(["git", "show", f"{baseline}:{path}"], capture_output=True)
        require(baseline_read.returncode == 0 and baseline_read.stdout == payload,
                f"local source differs from baseline git bytes: {path}")
        blob = subprocess.check_output(["git", "rev-parse", f"{baseline}:{path}"], text=True).strip()
        require(blob == item["git_blob"], f"baseline git blob differs: {path}")
        result[path] = payload.decode("utf-8")
        for name, other in item["other_pinned_refs"].items():
            ref = manifest["refs"][name]
            read = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True)
            require((read.returncode == 0) == other["present"], f"git source presence changed: {ref}:{path}")
            if other["present"]:
                require(digest(read.stdout) == other["sha256"], f"git source bytes changed: {ref}:{path}")
    return result


def assignment(source: str, name: str) -> ast.AST:
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
    raise ValueError(f"source assignment missing: {name}")


def weight_literals(source: str, name: str) -> dict[str, tuple[Decimal, int, str]]:
    node = assignment(source, name)
    require(isinstance(node, ast.Dict), f"{name} must be literal dictionary")
    result = {}
    for key, value in zip(node.keys, node.values):
        company = ast.literal_eval(key)
        require(company not in result, f"duplicate source key: {company}")
        literal = ast.get_source_segment(source, value)
        weight = Decimal(literal)
        require(weight.is_finite() and weight >= 0, f"invalid source weight: {company}")
        result[company] = (weight, value.lineno, literal)
    return result


def identifier_literals(source: str) -> dict[str, dict]:
    node = assignment(source, "OFFICIAL_PORTFOLIO_V11")
    require(isinstance(node, ast.Tuple), "identifier registry must be literal tuple")
    out = {}
    for call in node.elts:
        require(isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "Identifier", "unexpected identifier source")
        args = [ast.literal_eval(a) for a in call.args]
        fields = dict(zip(["company_id", "legal_name", "display_name", "ticker", "exchange"], args))
        fields.update({kw.arg: ast.literal_eval(kw.value) for kw in call.keywords})
        fields["source_line"] = call.lineno
        require(fields["company_id"] not in out, "duplicate source company_id")
        out[fields["company_id"]] = fields
    return out


def spec_rows(source: str, identifiers: dict, conflict: str) -> tuple[list[dict], dict]:
    rows = []
    groups = {}
    for line_number, line in enumerate(source.splitlines(), 1):
        m = re.fullmatch(r"(.+?) (\d+(?:\.\d+)?)%: (.+?)\.\s*", line.replace("\\.", "."))
        if not m:
            continue
        theme, total_literal, constituents = m.groups()
        require(theme in EXPECTED and theme not in groups, f"unexpected/duplicate authored group: {theme}")
        groups[theme] = Decimal(total_literal)
        for constituent in constituents.split(", "):
            name, percent_literal = constituent.rsplit(" ", 1)
            matches = [cid for cid, ident in identifiers.items()
                       if name in (ident["legal_name"], ident["display_name"], ident["ticker"])]
            require(len(matches) == 1, f"ambiguous document alias: {name}")
            cid = matches[0]
            if name == "TEL":
                require(cid == "tokyo_electron" and
                        "Decision D-29: Identity = Tokyo Electron / company_id=tokyo_electron. Bare ticker TEL = AMBIGUOUS." in conflict,
                        "TEL company context is not confirmed by D-29")
            rows.append({"company_id": cid, "authored_label": name,
                         "target_weight_percent": Decimal(percent_literal), "theme": theme,
                         "source_line": line_number})
    require(groups == EXPECTED, "authored Theme totals differ from intended 30/25/20/25")
    return rows, groups


def validate_partition(rows: list[dict], expected_ids: set[str], cash_percent: Decimal) -> dict[str, Decimal]:
    ids = [row["company_id"] for row in rows]
    require(len(ids) == len(set(ids)), "duplicate constituent identity")
    require(set(ids) == expected_ids, "constituent completeness mismatch")
    require(cash_percent.is_finite() and cash_percent >= 0, "invalid cash weight")
    groups = defaultdict(Decimal)
    for row in rows:
        value = row["target_weight_percent"]
        require(value.is_finite() and value >= 0, "invalid constituent target weight")
        require(row["theme"] in EXPECTED, "unknown/absent Theme membership")
        groups[row["theme"]] += value
    require(sum(groups.values(), cash_percent) == Decimal("100"), "target plus cash is not exactly 100 percent")
    require(dict(groups) == EXPECTED, "Theme weights do not match authored partition")
    return dict(groups)


def negative_checks(rows: list[dict], expected_ids: set[str]) -> list[str]:
    from copy import deepcopy
    mutations = {}
    mutations["duplicate_identity"] = deepcopy(rows) + [deepcopy(rows[0])]
    mutations["missing_constituent"] = deepcopy(rows[:-1])
    mutations["source_weight_drift"] = deepcopy(rows)
    mutations["source_weight_drift"][0]["target_weight_percent"] += Decimal("0.001")
    mutations["nonfinite_weight"] = deepcopy(rows)
    mutations["nonfinite_weight"][0]["target_weight_percent"] = Decimal("NaN")
    mutations["unknown_membership"] = deepcopy(rows)
    mutations["unknown_membership"][0]["theme"] = None
    mutations["same_total_wrong_group"] = deepcopy(rows)
    mutations["same_total_wrong_group"][0]["theme"] = "Big Tech"
    checked = []
    for name, changed in mutations.items():
        try:
            validate_partition(changed, expected_ids, Decimal("0"))
        except ValueError:
            checked.append(name)
        else:
            raise ValueError(f"negative case unexpectedly admitted: {name}")
    return checked


def replay(manifest: dict, sources: dict[str, str]) -> dict:
    weights = weight_literals(sources[PORTFOLIO], "OFFICIAL_V11_TARGETS")
    identifiers = identifier_literals(sources[IDENTIFIERS])
    authored, group_labels = spec_rows(sources[SPEC], identifiers, sources[CONFLICT])
    ref = json.loads(sources[REFERENCE], parse_float=Decimal)
    ref_rows = {r["holding_id"].removeprefix("reference:company:"): r for r in ref["holdings"]}
    require(len(ref_rows) == len(ref["holdings"]), "reference duplicate identity")
    require(set(ref_rows) == set(weights) == set(identifiers), "reference/code/identifier constituent set disagreement")
    require(ref["weight_basis"] == "TARGET" and ref["data_kind"] == "USER_SPEC_REFERENCE", "reference changed its basis or origin")
    require(all(r["security_id"] is None and r["types"] is None for r in ref_rows.values()), "reference source status unexpectedly changed")
    require(ref["total_units"] == 10000 and ref["cash_units"] == 0, "reference total/cash units drift")
    require("현금 0%." in sources[SPEC], "cash source no longer explicitly zero")
    with localcontext() as context:
        context.prec = 50
        groups = validate_partition(authored, set(weights), Decimal("0"))
        membership = []
        for row in authored:
            cid = row["company_id"]
            value, code_line, literal = weights[cid]
            reference = ref_rows[cid]
            require(value * 100 == row["target_weight_percent"], f"document/code weight disagreement: {cid}")
            require(value * 10000 == reference["weight_units"], f"code/reference weight disagreement: {cid}")
            require(reference["industry"] == row["theme"], f"document/reference grouping disagreement: {cid}")
            membership.append({
                "company_id": cid, "authored_label": row["authored_label"],
                "reference_constituent_id": reference["holding_id"],
                "label": reference["label"],
                "target_weight_decimal_ratio": str(value),
                "target_weight_exact_fraction": str(Fraction(value)),
                "target_weight_percent": str(row["target_weight_percent"]),
                "reference_weight_units": reference["weight_units"],
                "strategy_theme_name": row["theme"],
                "classification_kind": "USER_DEFINED_STRATEGY_THEME_PORTFOLIO_BUCKET",
                "authored_membership_evidence_status": "READY_REFERENCE_ONLY",
                "production_assignment_status": "PARTIAL_NOT_ADOPTED",
                "production_security_id": None,
                "production_security_binding_status": "NOT_AVAILABLE",
                "taxonomy_version_observed_reference": ref["classification"]["version"],
                "adopted_taxonomy_version": None,
                "assignment_revision_id": None,
                "effective_from": None, "effective_to": None,
                "source_available_at": None,
                "applicable_period_status": "UNKNOWN",
                "sources": [
                    {"path": SPEC, "line": row["source_line"]},
                    {"path": PORTFOLIO, "line": code_line, "literal": literal},
                    {"path": IDENTIFIERS, "line": identifiers[cid]["source_line"]},
                    {"path": REFERENCE, "pointer": f"/holdings/{list(ref_rows).index(cid)}"},
                ],
            })
        negative = negative_checks(authored, set(weights))
        us_source = "implementation/src/investment_system/markets/us.py"
        us_slice = weight_literals(sources[us_source], "_OFFICIAL_SLICE")
        require(set(us_slice) == set(weights) - {"tokyo_electron", "hanmi"}, "US subset does not match documented exclusions")
        require(all(value == weights[cid][0] for cid, (value, _, _) in us_slice.items()), "US subset source weights drift")
        us_mass = sum((v for v, _, _ in us_slice.values()), Decimal("0"))
    return {
        "status": "SOURCE_REFERENCE_REPLAY_VERIFIED_PRODUCTION_ROOT_NOT_ADMITTED",
        "scope": "OFFLINE_DIAGNOSTIC_ONLY_NO_PRODUCTION_IMPLEMENTATION_OR_ADOPTION",
        "baseline_refs": manifest["refs"],
        "authoritative_authored_values_source": {"path": SPEC, "section": "2. Official Baseline", "version": "Portfolio v1.1", "date_label": "2026-09-14", "date_role": "DOCUMENT_BASELINE_LABEL_NOT_PROVEN_EFFECTIVE_OR_AVAILABLE_TIME"},
        "production_current_target_root_status": "NOT_AVAILABLE_NOT_ADMITTED",
        "authoritative_production_portfolio_id": None,
        "production_current_applicable_period": None,
        "actual": {"status": "NOT_AVAILABLE", "root": None, "fallback_to_target": False},
        "numeric_diagnostic_context": {"input": "Decimal from exact authored numeric tokens; Python binary floats never imported", "precision": 50, "rounding_performed": False, "policy_status": "OFFLINE_DIAGNOSTIC_NOT_ADOPTED_PRODUCTION_NUMERIC_POLICY"},
        "validation": {"constituent_count": len(membership), "holding_total_percent": str(sum(groups.values(), Decimal("0"))), "cash_percent": str(Decimal(ref["cash_units"]) / Decimal(ref["total_units"]) * 100), "total_percent": str(sum(groups.values(), Decimal(ref["cash_units"]) / Decimal(ref["total_units"]) * 100)), "total_decimal_ratio": str(sum((value for value, _, _ in weights.values()), Decimal("0"))), "total_exact_fraction": str(sum((Fraction(row["target_weight_decimal_ratio"]) for row in membership), Fraction(0))), "reference_total_units": sum(r["weight_units"] for r in ref_rows.values()), "source_weight_agreement": "19/19", "single_partition_membership": "19/19", "theme_count": len(groups), "theme_counts": {g: sum(r["strategy_theme_name"] == g for r in membership) for g in groups}, "theme_total_percent": {k: str(v) for k, v in groups.items()}, "authored_group_total_percent": {k: str(v) for k, v in group_labels.items()}, "source_pins_verified": len(manifest["source_pins"]), "negative_cases_rejected": negative, "production_L5_status": "NOT_RUN"},
        "duplicate_sources": {"official_fixture": "19 exact weights agree; REFERENCE_FIXTURE role, cannot be production root", "preserved_chart_reference": "19 weights and authored groups agree; TARGET/USER_SPEC_REFERENCE, all security IDs unresolved", "us_working_fixture": {"constituents": len(us_slice), "unrenormalized_weight_mass_decimal": str(us_mass), "scope": "PROVISIONAL_US_WORKING_SEPARATE_17_CONSTITUENT_FIXTURE_NOT_CURRENT_19_TARGET", "missing": ["tokyo_electron", "hanmi"]}, "ModelPortfolioSnapshot": "Contract only; no admitted 19-row production constructor found in inspected source refs"},
        "membership_matrix": membership,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write additive diagnostic JSON")
    args = parser.parse_args()
    manifest = json.loads((HERE / "SOURCE_PINS.json").read_text())
    result = replay(manifest, pin_sources(manifest))
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    output = HERE / "TARGET_ROOT_AND_MEMBERSHIP_EVIDENCE.json"
    if args.write:
        output.write_text(payload)
    else:
        require(output.read_text() == payload, "saved diagnostic differs from deterministic source replay")
    print(json.dumps({"status": "PASS_OFFLINE_SOURCE_REPLAY_ONLY", "source_pins": result["validation"]["source_pins_verified"], "weights_agree": "19/19", "exact_total_fraction": result["validation"]["total_exact_fraction"], "theme_counts": result["validation"]["theme_counts"], "theme_total_percent": result["validation"]["theme_total_percent"], "negative_cases_rejected": len(result["validation"]["negative_cases_rejected"]), "production_root": result["production_current_target_root_status"], "production_L5": "NOT_RUN"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
