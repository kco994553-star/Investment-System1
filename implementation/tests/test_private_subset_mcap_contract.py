"""Offline parity for the private subset ranker and the existing Python math.

All inputs are synthetic. Node output stays captured, and assertion messages
never interpolate candidate rows or source data.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from investment_system.universe.sources import mcap_top_n_snapshot


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "product" / "private_subset_core.js"
AS_OF = datetime(2026, 1, 15, 21, tzinfo=timezone.utc)
NODE = shutil.which("node")
NODE_SCRIPT = """
const fs = require('node:fs');
try {
  const core = require(process.argv[1]);
  const request = JSON.parse(fs.readFileSync(0, 'utf8'));
  const result = core.rankSupportedUsdSubset(request.candidates, request.options);
  process.stdout.write(JSON.stringify(result));
} catch (_) {
  process.exitCode = 1;
}
"""


def candidate(company_id, *, shares=8, price=2, **overrides):
    return {
        "company_id": company_id,
        "ticker": company_id.upper(),
        "listing_id": "synthetic-listing:" + company_id,
        "issuer_id": "synthetic-issuer:" + company_id,
        "shares": shares,
        "shares_available_at": AS_OF,
        "price": price,
        "price_observed_at": AS_OF,
        "synthetic": True,
        **overrides,
    }


@unittest.skipUnless(NODE, "Node is required for offline cross-language parity")
class PrivateSubsetMcapContractTests(unittest.TestCase):
    def rank(self, rows):
        request = {
            "candidates": {
                "state": "INPUT_RESEARCH",
                "selection_status": "COMPLETE",
                "configured_count": len(rows),
                "candidates": rows,
                "missing": [],
                "synthetic": True,
            },
            "options": {
                "jobId": "synthetic-parity-job",
                "manifestHash": "a" * 64,
                "asOf": AS_OF.isoformat(),
            },
        }
        try:
            process = subprocess.run(
                [NODE, "-e", NODE_SCRIPT, str(CORE)],
                input=json.dumps(
                    request,
                    default=lambda value: value.isoformat(),
                    allow_nan=False,
                ),
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired):
            self.fail("Offline Node rank execution failed")
        self.assertTrue(process.returncode == 0, "Offline Node rank execution failed")
        try:
            result = json.loads(process.stdout)
        except (TypeError, ValueError):
            self.fail("Offline Node rank response is invalid")
        self.assertTrue(isinstance(result, dict), "Offline rank response shape differs")
        return result

    def assert_parity(self, rows):
        snapshot, report = mcap_top_n_snapshot(rows, AS_OF, n=len(rows))
        result = self.rank(rows)
        actual = result.get("rows")
        self.assertTrue(isinstance(actual, list), "Ranked rows shape differs")
        by_id = {row["company_id"]: row for row in rows}
        expected = [
            (
                member.company_id,
                member.ticker,
                by_id[member.company_id]["shares"] * by_id[member.company_id]["price"],
                index,
            )
            for index, member in enumerate(snapshot.members, start=1)
        ]
        projection = [
            (row.get("company_id"), row.get("ticker"), row.get("market_cap"), row.get("rank"))
            for row in actual
        ]
        self.assertTrue(projection == expected, "Rank order, products, or positions differ")
        self.assertTrue(result.get("ranked_count") == report["n_ranked"], "Ranked count differs")
        self.assertTrue(len(actual) == report["n_selected"], "Selected count differs")
        self.assertTrue(result.get("missing_count") == len(report["excluded"]), "Missing count differs")
        missing = result.get("missing")
        self.assertTrue(isinstance(missing, list), "Missing rows shape differs")
        self.assertTrue(len(missing) == len(report["excluded"]), "Missing row count differs")
        expected_missing = {row["company_id"]: row["reason"] for row in report["excluded"]}
        actual_missing = {row.get("company_id"): row.get("reason") for row in missing}
        self.assertTrue(actual_missing == expected_missing, "Exclusion identity or reason differs")
        self.assertTrue(result.get("official") is False, "Private rank must remain nonofficial")
        self.assertTrue(result.get("candidate_pool_complete") is False, "Pool completeness must remain unproven")
        return result

    def test_products_ascii_ties_and_all_valid_rows_match_python(self):
        rows = [
            candidate("tie_a"),
            candidate("tie_Z", shares=4, price=4),
            candidate("tie_A", shares=2, price=8),
            candidate("largest", shares=11, price=7),
            candidate("fraction", shares=0.1, price=3),
            candidate("smallest", shares=0.125, price=0.25),
        ]
        self.assert_parity(rows)

    def test_input_permutation_does_not_change_ranking(self):
        rows = [candidate("tie_a"), candidate("tie_Z"), candidate("tie_A"), candidate("large", shares=64)]
        first = self.assert_parity(rows)
        second = self.assert_parity(list(reversed(rows)))
        self.assertTrue(
            [row["company_id"] for row in first["rows"]]
            == [row["company_id"] for row in second["rows"]],
            "Permutation changed rank order",
        )

    def test_cutoff_equality_offsets_and_future_inputs_match_python(self):
        same_instant = AS_OF.astimezone(timezone(timedelta(hours=9)))
        future = AS_OF + timedelta(milliseconds=1)
        self.assert_parity([
            candidate("at_cutoff"),
            candidate("offset_cutoff", shares_available_at=same_instant, price_observed_at=same_instant),
            candidate("earlier", shares_available_at=AS_OF - timedelta(days=1)),
            candidate("future_shares", shares_available_at=future),
            candidate("future_price", price_observed_at=future),
            candidate("future_before_nonpositive", shares=-1, price_observed_at=future),
        ])

    def test_each_missing_input_and_exclusion_precedence_match_python(self):
        rows = [candidate("valid")]
        for index, field in enumerate(("shares", "price", "shares_available_at", "price_observed_at")):
            row = candidate("missing_" + str(index))
            row[field] = None
            rows.append(row)
        rows.append(candidate("missing_before_future", shares=None, price_observed_at=AS_OF + timedelta(days=1)))
        rows.append(candidate("missing_before_nonpositive", shares=None, price=-1))
        self.assert_parity(rows)

    def test_nonpositive_inputs_match_python(self):
        self.assert_parity([
            candidate("valid"),
            candidate("zero_shares", shares=0),
            candidate("negative_shares", shares=-1),
            candidate("zero_price", price=0),
            candidate("negative_price", price=-1),
            candidate("both_negative", shares=-1, price=-1),
        ])

    def test_empty_pool_matches_python_without_completeness_claim(self):
        self.assert_parity([])


if __name__ == "__main__":
    unittest.main()
