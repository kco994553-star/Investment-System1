"""Independent malformed-input regression checks; synthetic claims only.

These checks exercise the Chart diagnostic preflight. They do not authenticate
owner evidence, adopt a production schema, or close any readiness gate.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IndependentMalformedInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = load("independent_edge_tool", HERE / "receipt_preflight.py")
        cls.fixtures = load("independent_edge_fixtures", HERE / "test_receipt_preflight.py")
        cls.baseline = json.loads(cls.fixtures.BASELINE_PATH.read_text(encoding="utf-8"))

    def complete(self):
        return self.fixtures.fake_complete_packet(self.baseline)

    def inspect(self, packet):
        before = deepcopy(packet)
        result = self.tool.inspect_packet(
            packet, self.baseline, self.fixtures.REPO, self.fixtures.DECISION_TIME
        )
        self.assertEqual(packet, before)
        self.assertEqual(result["open_count"], 6)
        self.assertEqual(result["closed_count"], 0)
        self.assertEqual(result["production_readiness"], "IMPLEMENTATION_NOT_READY")
        return result

    def test_unhashable_observed_theme_is_invalid_without_exception(self):
        for value in ([], {}, ["Big Tech"]):
            with self.subTest(value=value):
                packet = self.complete()
                packet["constituents"][0]["observed_theme_name"] = value
                result = self.inspect(packet)
                self.assertEqual(result["source_inspection"], "INVALID")
                self.assertIsNone(result["reference_diagnostic"])

    def test_malformed_source_row_key_does_not_throw(self):
        for value in ([], {}, None, True, 9):
            with self.subTest(value=value):
                packet = self.complete()
                packet["constituents"][0]["source_row_key"] = value
                self.assertEqual(self.inspect(packet)["source_inspection"], "INVALID")

    def test_explicit_open_end_only_accepts_null_not_falsey_substitutes(self):
        for value in (False, 0, "", [], {}):
            for subject in ("root", "row"):
                with self.subTest(value=value, subject=subject):
                    packet = self.complete()
                    owner = packet["root_owner_return"] if subject == "root" else packet["constituents"][0]["owner_return"]
                    owner["effective_to"] = value
                    self.assertEqual(self.inspect(packet)["source_inspection"], "INVALID")

    def test_unhashable_owner_claims_do_not_throw_or_admit(self):
        for name in ("security_id", "theme_concept_id", "taxonomy_id", "assignment_revision_id"):
            for value in ([], {}):
                with self.subTest(name=name, value=value):
                    packet = self.complete()
                    packet["constituents"][0]["owner_return"][name] = value
                    self.assertEqual(self.inspect(packet)["source_inspection"], "INVALID")

    def test_nested_weight_shape_failures_are_diagnostic(self):
        for value in (None, [], "0.09", 0.09):
            with self.subTest(value=value):
                packet = self.complete()
                packet["constituents"][0]["observed_target_weight"] = value
                self.assertEqual(self.inspect(packet)["source_inspection"], "INVALID")

    def test_cli_json_rejects_duplicate_and_nonfinite_literals(self):
        for raw in ('{"same":1,"same":2}', '{"x":{"same":1,"same":2}}', '{"x":NaN}', '{"x":Infinity}'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    self.tool.strict_json(raw)

    def test_owner_clock_object_types_do_not_throw(self):
        for name in ("effective_from", "effective_to", "available_at"):
            for value in ([], {}, True, 7):
                with self.subTest(name=name, value=value):
                    packet = self.complete()
                    packet["root_owner_return"][name] = value
                    self.assertEqual(self.inspect(packet)["source_inspection"], "INVALID")

    def test_immutable_weight_mismatch_never_reaches_decimal_replay(self):
        packet = self.complete()
        packet["constituents"][0]["observed_target_weight"]["decimal_ratio"] = "1e999999999"
        # Do not allocate this deliberately dangerous value. Immutable-source
        # rejection must happen before any Decimal/Fraction calculation.
        with patch.object(self.tool, "exact_decimal", side_effect=AssertionError("numeric replay reached")) as numeric:
            result = self.inspect(packet)
        numeric.assert_not_called()
        self.assertEqual(result["source_inspection"], "INVALID")
        self.assertEqual(result["open_count"], 6)
        self.assertEqual(result["closed_count"], 0)
        self.assertIsNone(result["reference_diagnostic"])
        self.assertIn("IMMUTABLE_ROW_CHANGED", {f["code"] for f in result["findings"]})


if __name__ == "__main__":
    unittest.main()
