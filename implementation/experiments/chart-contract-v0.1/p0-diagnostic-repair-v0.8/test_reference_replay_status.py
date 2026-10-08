"""Source prerequisite failures must not be reported as failed calculations.

All candidate owner claims are synthetic. These tests never admit an owner
receipt or change source bytes; only one in-memory Git read is fault-injected.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
PREFLIGHT = HERE.parent / "p0-receipt-preflight-v0.6"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReferenceReplayStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = load("reference_replay_tool", PREFLIGHT / "receipt_preflight.py")
        cls.fixtures = load("reference_replay_fixtures", PREFLIGHT / "test_receipt_preflight.py")
        cls.baseline = json.loads(cls.fixtures.BASELINE_PATH.read_text(encoding="utf-8"))

    def inspect(self, packet):
        before = deepcopy(packet)
        result = self.tool.inspect_packet(
            packet, self.baseline, self.fixtures.REPO, self.fixtures.DECISION_TIME
        )
        self.assertEqual(packet, before)
        self.assertEqual(result["open_count"], 6)
        self.assertEqual(result["closed_count"], 0)
        self.assertEqual(result["production_readiness"], "IMPLEMENTATION_NOT_READY")
        self.assertIsNone(result["production_payload"])
        self.assertEqual(result["actual"]["status"], "NOT_AVAILABLE")
        self.assertFalse(result["actual"]["fallback_to_target"])
        return result

    def source_failure(self, failure):
        packet = self.fixtures.fake_complete_packet(self.baseline)
        source = self.baseline["constituents"][0]["source_refs"][0]
        original_git_bytes = self.tool.git_bytes

        def read(repo, commit, path):
            if (commit, path) == (source["commit"], source["path"]):
                if failure == "missing":
                    raise subprocess.CalledProcessError(128, ["git", "show", f"{commit}:{path}"])
                return original_git_bytes(repo, commit, path) + b"\nFAULT_INJECTION_ONLY\n"
            return original_git_bytes(repo, commit, path)

        with patch.object(self.tool, "git_bytes", side_effect=read), patch.object(
            self.tool, "exact_decimal", side_effect=AssertionError("numeric replay reached")
        ) as arithmetic:
            result = self.inspect(packet)
        arithmetic.assert_not_called()
        self.assertEqual(result["source_inspection"], "INVALID")
        self.assertEqual(result["reference_replay"], "NOT_RUN_SOURCE_INVALID")
        self.assertIsNone(result["reference_diagnostic"])
        self.assertNotIn("INVALID_REFERENCE_ALLOCATION", {f["code"] for f in result["findings"]})
        return result

    def test_missing_trusted_source_skips_arithmetic_without_allocation_failure(self):
        result = self.source_failure("missing")
        self.assertIn("SOURCE_PIN_UNRESOLVED", {f["code"] for f in result["findings"]})

    def test_hash_invalid_trusted_source_skips_arithmetic_without_allocation_failure(self):
        result = self.source_failure("hash")
        self.assertIn("SOURCE_HASH_MISMATCH", {f["code"] for f in result["findings"]})

    def test_attempted_numeric_failure_and_success_have_distinct_diagnostic_status(self):
        packet = self.fixtures.fake_complete_packet(self.baseline)
        with patch.object(self.tool, "exact_decimal", side_effect=ValueError("numeric failure probe")) as arithmetic:
            failed = self.inspect(packet)
        arithmetic.assert_called_once()
        self.assertEqual(failed["source_inspection"], "INVALID")
        self.assertEqual(failed["reference_replay"], "FAILED")
        self.assertIsNone(failed["reference_diagnostic"])
        self.assertIn("INVALID_REFERENCE_ALLOCATION", {f["code"] for f in failed["findings"]})
        completed = self.inspect(packet)
        self.assertEqual(completed["source_inspection"], "INPUT_COMPLETE_UNAUTHENTICATED")
        self.assertEqual(completed["reference_replay"], "COMPLETED_DIAGNOSTIC")
        self.assertIsNotNone(completed["reference_diagnostic"])
        self.assertFalse(completed["reference_diagnostic"]["is_renderable_production_data"])


if __name__ == "__main__":
    unittest.main()
