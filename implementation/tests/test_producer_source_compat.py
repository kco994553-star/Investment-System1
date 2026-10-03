"""Approved CDR-004 source acceptance rejects unrelated or partial contract mutation."""
import importlib.util
import importlib
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_compat_test", ROOT / "tools/producer_source_compat.py")
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)


def _legacy_models():
    return subprocess.check_output(["git", "show", "b8e39a2196a6d7794a04a0cd5393c68329e126ca:implementation/src/investment_system/contracts/models.py"], cwd=ROOT)


def test_exact_adopted_schema_preserves_original_contract_and_qgv_ast():
    legacy = compat.models_state(_legacy_models())
    adopted = compat.models_state((ROOT / "src" / compat.MODELS).read_bytes())
    assert legacy["status"] == adopted["status"] == "PASS"
    assert legacy["state"] == "PRE_ADOPTION" and adopted["state"] == "C28_ADOPTED"
    assert legacy["pre_existing_AST_preserved"] and adopted["pre_existing_AST_preserved"]
    assert adopted["lineage_fields"] == {name: list(compat.LINEAGE_DECLARATIONS)
                                          for name in ("TechnicalSnapshot", "MacroSnapshot")}


def test_partial_unapproved_and_changed_existing_contract_is_rejected():
    original = (ROOT / "src" / compat.MODELS).read_bytes()
    for before, after in [
        (b"available_at: Optional[datetime] = None", b"available_at: Optional[datetime] = datetime.now()"),
        (b"    input_hash: Optional[str] = None\n", b""),
        (b"class QGVSnapshot:", b"class QGVSnapshot:\n    unapproved: bool = True"),
        (b"class MacroSnapshot:", b"class MacroSnapshot:\n    unapproved: bool = True"),
        (b"# None/empty on legacy unqualified outputs; never inferred from as_of.", b"# unapproved byte mutation"),
    ]:
        assert before in original
        tampered = original.replace(before, after, 1)
        assert compat.models_state(tampered)["status"] == "FAIL"


def test_shared_comparison_rejects_tampered_qgv_and_missing_file(tmp_path):
    own, dep = tmp_path / "own", tmp_path / "infra"
    rel = "investment_system/qgv/scoring.py"
    for root in (own, dep):
        (root / rel).parent.mkdir(parents=True)
        (root / rel).write_bytes(b"exact-source")
    assert compat.compare_shared_sources(own, dep, (rel,))["status"] == "PASS"
    (dep / rel).write_bytes(b"changed-source")
    assert compat.compare_shared_sources(own, dep, (rel,))["status"] == "FAIL"
    (dep / rel).unlink()
    assert compat.compare_shared_sources(own, dep, (rel,))["status"] == "FAIL"


def test_identical_unapproved_models_do_not_bypass_pair_acceptance(tmp_path):
    own, dep = tmp_path / "own", tmp_path / "infra"
    for root in (own, dep):
        path = root / compat.MODELS
        path.parent.mkdir(parents=True)
        path.write_bytes((ROOT / "src" / compat.MODELS).read_bytes() + b"\n# identical but unapproved\n")
    assert compat.compare_shared_sources(own, dep, (compat.MODELS,))["status"] == "FAIL"


def test_dependency_report_labels_actual_integrated_reference_without_relabeling_pin():
    historical = compat.boundary_pin(ROOT / "src/investment_system/qgv_producer/infra_boundary.py")
    report = compat.dependency_reference(ROOT / "src", ROOT / "src", historical)
    assert report["mode"] == "INTEGRATED_SAME_TREE"
    assert report["commit"] == subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert report["historical_pin_is_actual"] is False
    assert historical["commit"] == "5fa7ce0647b6af91d767c54ecaaa3e31d1ab63e4"
    assert compat.MODELS in report["source_manifest"]


def test_default_integrated_context_rejects_incomplete_infrastructure_api(tmp_path, monkeypatch):
    for producer, variable, fn in [
        ("qgv", "QGV_PRODUCER_INFRA_SRC", "test_qgv_export_is_compatible_with_pinned_producer_infrastructure"),
        ("leaderboard", "LEADERBOARD_PRODUCER_INFRA_SRC", "test_leaderboard_export_is_compatible_with_pinned_producer_infrastructure"),
    ]:
        module = importlib.import_module(f"tests.test_{producer}_producer_infra_compat")
        boundary = module.infra_boundary
        incomplete = SimpleNamespace(**{name.rsplit(".", 1)[1]: SimpleNamespace()
                                        for name in boundary.EXPECTED_INFRA_API})
        monkeypatch.delenv(variable, raising=False)
        monkeypatch.setattr(boundary, "load_infra", lambda: incomplete)
        with pytest.raises(AssertionError, match="integrated dependency API is incomplete"):
            getattr(module, fn)(tmp_path)


def test_partially_present_dependency_cannot_be_treated_as_isolated_absence(tmp_path, monkeypatch):
    for producer, variable, fn in [
        ("qgv", "QGV_PRODUCER_INFRA_SRC", "test_qgv_export_is_compatible_with_pinned_producer_infrastructure"),
        ("leaderboard", "LEADERBOARD_PRODUCER_INFRA_SRC", "test_leaderboard_export_is_compatible_with_pinned_producer_infrastructure"),
    ]:
        module = importlib.import_module(f"tests.test_{producer}_producer_infra_compat")
        monkeypatch.delenv(variable, raising=False)
        monkeypatch.setattr(module.infra_boundary, "load_infra", lambda: None)
        with pytest.raises(AssertionError, match="integrated dependency could not be loaded"):
            getattr(module, fn)(tmp_path)
