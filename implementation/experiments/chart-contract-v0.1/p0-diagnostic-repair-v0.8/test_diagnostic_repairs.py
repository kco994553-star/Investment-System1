"""Negative CLI regression for malformed owner-return diagnostics only.

The nested JSON is a deliberately invalid owner packet, never production data.
This test selects no parser depth limit or owner-admission policy.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in HERE.parents if (parent / ".git").exists())
TOOL = HERE.parent / "p0-receipt-preflight-v0.6" / "receipt_preflight.py"
GATES = {"A-S1", "A-S2", "A-S3", "A-G1", "A-G2", "A-G3"}


class MalformedJsonCliTests(unittest.TestCase):
    def test_nested_packet_parser_failure_emits_structured_invalid_diagnostic(self):
        malformed_packet = '{"root_owner_return":' + "[" * 10_000 + "0" + "]" * 10_000 + "}"
        with tempfile.TemporaryDirectory(prefix="chart-malformed-cli-") as folder:
            packet_path = Path(folder) / "packet.json"
            output_path = Path(folder) / "diagnostic.json"
            packet_path.write_text(malformed_packet, encoding="utf-8")
            run = subprocess.run(
                [sys.executable, "-B", str(TOOL), "--repo", str(REPO),
                 "--packet", str(packet_path), "--decision-time", "2026-10-05T04:30:00+00:00",
                 "--output", str(output_path)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertNotIn("Traceback", run.stderr)
            report = json.loads(run.stdout)
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), report)
            self.assertEqual(report["source_inspection"], "INVALID")
            self.assertEqual(report["production_readiness"], "IMPLEMENTATION_NOT_READY")
            self.assertEqual(set(report["open_gate_ids"]), GATES)
            self.assertEqual(report["open_count"], 6)
            self.assertEqual(report["closed_count"], 0)
            self.assertIsNone(report["production_payload"])
            self.assertIsNone(report["reference_diagnostic"])
            self.assertEqual(report["actual"]["status"], "NOT_AVAILABLE")
            self.assertFalse(report["actual"]["fallback_to_target"])
            self.assertIn("PACKET_READ_FAILED", {finding["code"] for finding in report["findings"]})
            self.assertEqual(packet_path.read_text(encoding="utf-8"), malformed_packet)


if __name__ == "__main__":
    unittest.main()
