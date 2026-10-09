"""Read-only owner-interface diagnostic. No production Chart implementation.

Runs existing P01/QGV-binding cases and a few existing-function compatibility
calls against the pinned PR42 tree. Refuses any Track C (evl) module import.
Neither hypothetical fixture events nor grants are persisted/activated.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.abc
import importlib.util
import inspect
import io
import json
import sys
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


OWNER_HEAD = "523e702a806a718d163cfbf62aa3fc29d8c3ef3c"
OWNER_WORKTREE = Path("/workspace/scratch/e21499bd6a66/fpia-readonly-work")
OUT = Path(__file__).resolve().parent
PIN_PATHS = (
    "src/investment_system/producers/serialization.py",
    "src/investment_system/producers/contract.py",
    "src/investment_system/producers/assembler.py",
    "src/investment_system/publication/authorization.py",
    "src/investment_system/publication/envelope.py",
    "src/investment_system/publication/extractors.py",
    "src/investment_system/publication/facts.py",
    "src/investment_system/publication/predicate.py",
    "src/investment_system/publication/invalidation.py",
    "src/investment_system/publication/qgv_binding.py",
    "src/investment_system/product/web_mvp.py",
    "src/investment_system/product/web_assets/app.js",
    "tools/export_web_bundle.py",
    "tools/mini_pytest.py",
    "tests/test_p01_research_publication.py",
    "tests/test_qgv_invalidation_binding.py",
    "docs/research_publication/CONTRACT.md",
    "docs/producer_infrastructure/P01_APPROVAL_2026-10-02.md",
)


class RefuseTrackC(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "investment_system.evl" or fullname.startswith("investment_system.evl."):
            raise ImportError("Track C imports are outside this read-only diagnostic")
        return None


def captured_call(label, fn):
    try:
        result = fn()
        return {"label": label, "returned": result}
    except Exception as exc:
        return {"label": label, "exception_type": type(exc).__name__, "message": str(exc)}


def main():
    import subprocess
    found = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=OWNER_WORKTREE, text=True).strip()
    if found != OWNER_HEAD:
        raise RuntimeError("owner worktree no longer has the pinned exact head")
    implementation = OWNER_WORKTREE / "implementation"
    pins = []
    for path in PIN_PATHS:
        raw = (implementation / path).read_bytes()
        from_git = subprocess.check_output(["git", "show", f"{OWNER_HEAD}:implementation/{path}"], cwd=OWNER_WORKTREE)
        if raw != from_git:
            raise RuntimeError(f"working bytes differ from pinned Git object: {path}")
        pins.append({"path": "implementation/" + path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    sys.dont_write_bytecode = True
    sys.meta_path.insert(0, RefuseTrackC())
    sys.path.insert(0, str(implementation / "src"))

    from investment_system.producers.serialization import canonical_bytes, canonical_sha256
    from investment_system.publication.authorization import ACTIVE_AUTHORIZATIONS, summarize_grants
    from investment_system.publication.extractors import extract
    from investment_system.publication.invalidation import CONTRACT, resolve_target
    from investment_system.publication.qgv_binding import provenance_from_persisted

    tagged = {"numeric_kind": "lexical_decimal", "unit": "percent", "value": "5.50", "label": "반도체 장비"}
    reordered = {key: tagged[key] for key in reversed(tuple(tagged))}
    encoded = canonical_bytes(tagged)
    chart_shape = {"capability": "Target Strategy Theme Allocation", "basis": "TARGET", "immutable_payload_sha256": canonical_sha256(tagged)}
    now = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    event = {
        "contract": CONTRACT,
        "schema_version": 1,
        "target_sha256": "ab" * 32,
        "state": "CLEAR",
        "reason_code": "EXPLICIT_CLEAR",
        "effective_at": "2026-10-06T00:00:00+00:00",
        "available_at": "2026-10-04T00:00:00+00:00",
        "supersedes": None,
        "authority_ref": "diagnostic-only:not-an-authenticated-approval",
    }
    probes = [
        {"label": "tagged-string canonical serialization", "canonical_utf8": encoded.decode(), "sha256": hashlib.sha256(encoded).hexdigest(), "key_order_invariant": encoded == canonical_bytes(reordered), "trailing_zero_preserved": json.loads(encoded)["value"] == "5.50"},
        captured_call("native Decimal unsupported", lambda: canonical_bytes({"value": Decimal("5.50")})),
        captured_call("Chart shape unregistered", lambda: extract(chart_shape)),
        captured_call("QGV binding refuses Chart shape", lambda: provenance_from_persisted(chart_shape, {})),
        {"label": "current active grant set", "authorization_count": len(ACTIVE_AUTHORIZATIONS), "summary": summarize_grants()},
        {"label": "generic resolver with available future-effective fixture", "decision_time": now.isoformat(), "event_effective_at": event["effective_at"], "event_available_at": event["available_at"], "resolution": resolve_target((event,), event["target_sha256"], now), "interpretation": "mechanical available_at visibility is not a TARGET applicability or authority-authentication check; fixture is never admitted"},
    ]

    node_ids = [
        "test_schema1_states_and_active_grants_stay_closed",
        "test_producer_pass_is_not_a_grant_and_modes_match_without_a_name",
        "test_explicit_research_grant_stays_out_of_schema1_and_blocked_bytes_stay_hidden",
        "test_one_grant_does_not_satisfy_another_and_promotion_is_refused",
        "test_component_label_and_forged_track_c_are_not_authority",
        "test_authorization_record_is_explicit_and_closed",
        "test_extractors_copy_hashes_and_drop_scores",
        "test_same_fact_axes_decide_the_same_way",
        "test_production_envelope_keeps_sections_and_does_not_activate_display",
        "test_research_lifecycle_is_still_rejected_as_live",
        "test_publication_package_does_not_import_engines_or_name_them_in_the_predicate",
    ]
    runner_path = implementation / "tools/mini_pytest.py"
    spec = importlib.util.spec_from_file_location("owner_existing_mini_pytest", runner_path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner._install_shim()
    cases, failed = [], []
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        for filename, selected in (("test_p01_research_publication.py", node_ids), ("test_qgv_invalidation_binding.py", None)):
            spec = importlib.util.spec_from_file_location("owner_existing_" + filename[:-3], implementation / "tests" / filename)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            existing = {name: fn for name, fn in inspect.getmembers(module, inspect.isfunction) if name.startswith("test_") and fn.__module__ == spec.name}
            for name in selected or sorted(existing):
                if inspect.signature(existing[name]).parameters:
                    raise RuntimeError("bounded selection unexpectedly requires fixture injection")
                ident = filename + "::" + name
                try:
                    existing[name]()
                    cases.append({"node_id": ident, "status": "PASS"})
                except Exception:
                    failed.append({"node_id": ident, "status": "FAIL", "traceback": traceback.format_exc()})
        exit_code = 1 if failed else 0
        print(f"{len(cases)} passed, {len(failed)} failed (existing mini_pytest raises shim; not pytest)")
    loaded_track_c = sorted(key for key in sys.modules if key == "investment_system.evl" or key.startswith("investment_system.evl."))
    receipt = {
        "status": "DIAGNOSTIC_ONLY_EXISTING_OWNER_FUNCTIONS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_head": OWNER_HEAD,
        "owner_worktree": str(OWNER_WORKTREE),
        "source_pins": pins,
        "compatibility_probes": probes,
        "existing_owner_cases": {"runner": "selected unchanged owner functions using existing mini_pytest raises shim; not pytest", "pytest_available": False, "initial_pytest_attempt": "ModuleNotFoundError: No module named 'pytest'; no owner cases ran on that attempt", "exit_code": int(exit_code), "p01_selected_node_ids": node_ids, "qgv_binding_file": "implementation/tests/test_qgv_invalidation_binding.py", "passed_cases": cases, "failed_cases": failed, "stdout": stream.getvalue()},
        "track_c_import_guard": "ACTIVE",
        "loaded_track_c_modules": loaded_track_c,
        "production_chart_tests": "NOT_RUN",
        "merge_result_fpia": "NOT_RUN",
        "authorization_written_or_activated": False,
        "source_modified": False,
    }
    (OUT / "EXISTING_AUTHORITY_INTERFACE_DIAGNOSTIC_v0.5.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_head": OWNER_HEAD, "source_pin_count": len(pins), "diagnostic_exit_code": int(exit_code), "loaded_track_c_modules": loaded_track_c, "case_summary": stream.getvalue().strip().splitlines()[-1]}, ensure_ascii=False))
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
