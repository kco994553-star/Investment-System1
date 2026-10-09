"""Independent adversarial checks of diagnostic receipt inspection.

All owner-return values here are deliberately fabricated test fixtures. They
must never establish source adoption, publication authority, or production
readiness. No original source file is changed by these tests.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / ".git").exists())
BASELINE_PATH = HERE.parent / "p0-slice-owner-closure-v0.5/lane-a/TARGET_OWNER_ADMISSION_REQUEST.json"
DECISION_TIME = datetime(2026, 10, 5, 3, 0, tzinfo=timezone.utc)
OPEN_GATES = {"A-S1", "A-S2", "A-S3", "A-G1", "A-G2", "A-G3"}


def load_inspector():
    spec = importlib.util.spec_from_file_location(
        "chart_receipt_preflight_adversarial", HERE / "receipt_preflight.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.inspect_packet


def fake_complete_packet(baseline):
    """A complete-shaped but unauthenticated fixture, never an admitted root."""
    packet = deepcopy(baseline)
    root = packet["root_owner_return"]
    for name in root:
        root[name] = "test-only:self-declared:" + name
    root.update(
        portfolio_version=baseline["observed_candidate_allocation"]["authored_version"],
        snapshot_hash="a" * 64,
        effective_from="2026-10-05T00:00:00+00:00",
        effective_to=None,
        available_at="2026-10-05T00:30:00+00:00",
    )
    themes = baseline["observed_candidate_allocation"]["strategy_theme_names"]
    for index, row in enumerate(packet["constituents"]):
        owner = row["owner_return"]
        for name in owner:
            owner[name] = f"test-only:self-declared:{index}:{name}"
        owner.update(
            security_namespace="test-only:self-declared:namespace",
            security_type="test-only:self-declared:equity",
            share_class_or_form="test-only:self-declared:share-form",
            theme_concept_id=f"test-only:self-declared:theme:{themes.index(row['observed_theme_name'])}",
            taxonomy_id="test-only:self-declared:taxonomy",
            taxonomy_version="test-only:self-declared:taxonomy-v1",
            catalog_revision_id="test-only:self-declared:catalog-revision",
            assignment_revision_id="test-only:self-declared:assignment-revision",
            effective_from="2026-10-05T00:00:00+00:00",
            effective_to=None,
            available_at="2026-10-05T00:30:00+00:00",
        )
    return packet


class ReceiptPreflightAdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inspect = staticmethod(load_inspector())
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    def report(self, packet, decision_time=DECISION_TIME):
        before = deepcopy(packet)
        result = self.inspect(packet, self.baseline, REPO, decision_time)
        self.assertEqual(packet, before, "inspection must not fill or mutate owner input")
        self.assertEqual(result["production_readiness"], "IMPLEMENTATION_NOT_READY")
        self.assertEqual(set(result["open_gate_ids"]), OPEN_GATES)
        self.assertEqual(len(result["open_gate_ids"]), 6)
        self.assertEqual(result["actual"]["status"], "NOT_AVAILABLE")
        self.assertIs(result["actual"]["fallback_to_target"], False)
        self.assertNotIn("renderable_allocation", result)
        self.assertNotIn("chart_payload", result)
        return result

    def invalid(self, packet, decision_time=DECISION_TIME):
        result = self.report(packet, decision_time)
        self.assertEqual(result["source_inspection"], "INVALID")
        self.assertTrue(result["findings"])
        return result

    def complete(self):
        return fake_complete_packet(self.baseline)

    def test_original_request_is_incomplete_and_cannot_display_reference(self):
        result = self.report(deepcopy(self.baseline))
        self.assertEqual(result["source_inspection"], "INCOMPLETE")
        self.assertTrue(result["findings"])

    def test_complete_self_declared_receipts_never_close_a_gate(self):
        result = self.report(self.complete())
        self.assertEqual(result["source_inspection"], "INPUT_COMPLETE_UNAUTHENTICATED")
        self.assertIn("OWNER_RECEIPTS_UNAUTHENTICATED", {x["code"] for x in result["findings"]})

    def test_source_observation_cannot_be_changed_even_when_totals_hold(self):
        packet = self.complete()
        # A total-preserving reassignment is still an unauthorized source change.
        packet["constituents"][0]["observed_theme_name"] = "Big Tech"
        packet["constituents"][10]["observed_theme_name"] = "반도체 장비"
        self.invalid(packet)

    def test_source_label_or_company_key_tamper_is_rejected(self):
        for key in ("authored_label", "company_id", "classification_kind"):
            with self.subTest(key=key):
                packet = self.complete()
                packet["constituents"][0][key] = "unreviewed-source-change"
                self.invalid(packet)

    def test_dropped_and_duplicated_rows_cannot_claim_completeness(self):
        dropped = self.complete()
        dropped["constituents"].pop()
        self.invalid(dropped)
        duplicated = self.complete()
        duplicated["constituents"].append(deepcopy(duplicated["constituents"][0]))
        self.invalid(duplicated)

    def test_duplicate_reference_key_is_rejected(self):
        packet = self.complete()
        packet["constituents"][1]["source_row_key"] = packet["constituents"][0]["source_row_key"]
        self.invalid(packet)

    def test_forged_exact_source_pins_are_rejected(self):
        for key, value in (
            ("sha256", "0" * 64),
            ("git_blob", "0" * 40),
            ("commit", "0" * 40),
            ("path", "implementation/src/investment_system/qgv/identifiers.py"),
        ):
            with self.subTest(pin=key):
                packet = self.complete()
                packet["constituents"][0]["source_refs"][0][key] = value
                self.invalid(packet)

    def test_provenance_line_and_pointer_cannot_be_repointed(self):
        packet = self.complete()
        packet["constituents"][0]["source_refs"][0]["line"] = 1
        self.invalid(packet)
        packet = self.complete()
        packet["constituents"][0]["source_refs"][-1]["pointer"] = "/holdings/1"
        self.invalid(packet)

    def test_nonfinite_and_binary_float_weight_inputs_are_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity", 0.09, float("nan")):
            with self.subTest(weight=repr(value)):
                packet = self.complete()
                packet["constituents"][0]["observed_target_weight"]["decimal_ratio"] = value
                self.invalid(packet)

    def test_decimal_fraction_percent_disagreement_is_rejected(self):
        for key, value in (("decimal_ratio", "0.08"), ("exact_fraction", "1/10"), ("percent", "8")):
            with self.subTest(key=key):
                packet = self.complete()
                packet["constituents"][0]["observed_target_weight"][key] = value
                self.invalid(packet)

    def test_fake_candidate_total_and_cash_cannot_override_source(self):
        for key, value in (("total_target_weight_decimal_ratio", "0.9"), ("cash_target_percent", "10")):
            with self.subTest(key=key):
                packet = self.complete()
                packet["observed_candidate_allocation"][key] = value
                self.invalid(packet)

    def test_null_and_blank_owner_fields_are_not_admissions(self):
        for value in (None, "", "   "):
            with self.subTest(value=value):
                packet = self.complete()
                packet["root_owner_return"]["source_receipt_ref"] = value
                result = self.report(packet)
                self.assertEqual(result["source_inspection"], "INCOMPLETE")
        packet = self.complete()
        packet["constituents"][18]["owner_return"]["security_id"] = None
        self.assertEqual(self.report(packet)["source_inspection"], "INCOMPLETE")

    def test_naive_decision_and_receipt_clocks_fail_closed(self):
        self.invalid(self.complete(), datetime(2026, 10, 5, 3, 0))
        for key in ("effective_from", "available_at"):
            with self.subTest(key=key):
                packet = self.complete()
                packet["root_owner_return"][key] = "2026-10-05T00:00:00"
                self.invalid(packet)

    def test_future_availability_is_rejected_for_root_and_assignment(self):
        for owner in ("root", "row"):
            with self.subTest(owner=owner):
                packet = self.complete()
                receipt = packet["root_owner_return"] if owner == "root" else packet["constituents"][0]["owner_return"]
                receipt["available_at"] = "2026-10-05T04:00:00+00:00"
                self.invalid(packet)

    def test_future_effective_and_exclusive_expired_end_are_rejected(self):
        for key, value in (
            ("effective_from", "2026-10-05T04:00:00+00:00"),
            ("effective_to", "2026-10-05T03:00:00+00:00"),
            ("effective_to", "2026-10-04T00:00:00+00:00"),
        ):
            with self.subTest(key=key, value=value):
                packet = self.complete()
                packet["root_owner_return"][key] = value
                self.invalid(packet)

    def test_duplicate_security_binding_or_admitted_row_is_rejected(self):
        for key in ("security_id", "admitted_target_row_id"):
            with self.subTest(key=key):
                packet = self.complete()
                packet["constituents"][1]["owner_return"][key] = packet["constituents"][0]["owner_return"][key]
                self.invalid(packet)

    def test_theme_concept_aliasing_and_splitting_are_rejected(self):
        packet = self.complete()
        packet["constituents"][5]["owner_return"]["theme_concept_id"] = packet["constituents"][0]["owner_return"]["theme_concept_id"]
        self.invalid(packet)
        packet = self.complete()
        packet["constituents"][1]["owner_return"]["theme_concept_id"] = "test-only:self-declared:split-same-theme"
        self.invalid(packet)

    def test_mixed_catalog_and_assignment_revisions_are_rejected(self):
        for key in ("taxonomy_id", "taxonomy_version", "catalog_revision_id", "assignment_revision_id"):
            with self.subTest(key=key):
                packet = self.complete()
                packet["constituents"][1]["owner_return"][key] = "test-only:self-declared:conflicting-revision"
                self.invalid(packet)

    def test_unknown_owner_fields_are_not_a_backdoor_schema_extension(self):
        packet = self.complete()
        packet["root_owner_return"]["source_admitted"] = True
        self.invalid(packet)
        packet = self.complete()
        packet["constituents"][0]["owner_return"]["authority"] = "APPROVED"
        self.invalid(packet)

    def test_readiness_flags_and_actual_fallback_cannot_be_spoofed(self):
        for key in ("source_admission", "activation", "grant_issued", "production_schema_adoption"):
            with self.subTest(key=key):
                packet = self.complete()
                packet[key] = True
                self.invalid(packet)
        packet = self.complete()
        packet["actual"]["fallback_to_target"] = True
        self.invalid(packet)

    def test_malformed_top_level_input_is_diagnostic_not_exception(self):
        for packet in (None, [], "APPROVED", {}, {"root_owner_return": {}}):
            with self.subTest(packet=repr(packet)):
                self.invalid(packet)


if __name__ == "__main__":
    unittest.main()
