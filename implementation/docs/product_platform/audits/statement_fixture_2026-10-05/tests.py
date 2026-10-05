"""Deterministic acceptance examples; no owner/full-regression replay."""
from dataclasses import replace
from datetime import datetime, timedelta
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

import oracle as o


class StatementFixtureTests(unittest.TestCase):
    def setUp(self):
        self.meta, self.records, self.raw = o.fixture()
        self.ctx = o.c.TenantContext("t1", "u1")
        self.decision = datetime.fromisoformat(self.meta["decision_time"])

    def check(self, records=None, raw=None):
        return o.statement(self.ctx, self.records if records is None else records,
                           self.raw if raw is None else raw, self.decision)

    def changed(self, record_id, **values):
        records, raw = list(self.records), dict(self.raw)
        for i, record in enumerate(records):
            if record.source_record_id == record_id:
                data = json.loads(raw[record.raw_payload_ref])
                data.update(values)
                body = (json.dumps(data, sort_keys=True) + "\n").encode()
                raw[record.raw_payload_ref] = body
                records[i] = replace(record, payload_sha256=hashlib.sha256(body).hexdigest())
        return tuple(records), raw

    def test_complete_statement_matches_independent_expected_values(self):
        result = self.check()
        self.assertEqual({k: Fraction(v) for k, v in result["computed"].items()},
                         {k: Fraction(v) for k, v in self.meta["expected"].items()})
        self.assertTrue(result["passed"])
        self.assertTrue(result["lineage_passed"])
        self.assertEqual(result["admitted_unique"], 4)

    def test_deterministic_identical_replay_does_not_double_count_cash(self):
        result = self.check(self.records + (self.records[1], self.records[2]))
        self.assertEqual({k: Fraction(v) for k, v in result["computed"].items()},
                         {k: Fraction(v) for k, v in self.meta["expected"].items()})
        self.assertEqual(result["admitted_unique"], 4)

    def test_missing_transaction_rejected_before_financial_pass(self):
        with self.assertRaises(o.FixtureRejected):
            self.check(tuple(r for r in self.records if r.source_record_id != "dividend"))

    def test_empty_input_rejected(self):
        with self.assertRaises(o.FixtureRejected):
            self.check(())

    def test_missing_raw_bytes_rejected(self):
        raw = dict(self.raw)
        del raw[self.records[1].raw_payload_ref]
        with self.assertRaises(o.FixtureRejected):
            self.check(raw=raw)

    def test_changed_raw_bytes_without_hash_change_rejected(self):
        raw = dict(self.raw)
        raw[self.records[1].raw_payload_ref] += b" "
        with self.assertRaises(o.FixtureRejected):
            self.check(raw=raw)

    def test_same_source_version_conflicting_content_rejected(self):
        record = self.records[1]
        body = self.raw[record.raw_payload_ref] + b" "
        duplicate = replace(record, raw_payload_ref="fixture://conflict", payload_sha256=hashlib.sha256(body).hexdigest())
        raw = {**self.raw, duplicate.raw_payload_ref: body}
        with self.assertRaises(o.c.RecordIntegrityError):
            self.check(self.records + (duplicate,), raw)

    def test_original_and_correction_versions_can_be_retained_without_rewrite(self):
        record = self.records[1]
        data = json.loads(self.raw[record.raw_payload_ref])
        data.update(source_version="v2", cash_delta="-124.00")
        body = json.dumps(data).encode()
        correction = replace(record, source_version="v2", raw_payload_ref="fixture://buy/v2", payload_sha256=hashlib.sha256(body).hexdigest())
        raw = {**self.raw, correction.raw_payload_ref: body}
        original = dict(self.raw)
        admitted = o.admit(self.ctx, self.records + (correction,), raw, self.decision)
        self.assertEqual(len(admitted), 5)
        self.assertEqual({k: raw[k] for k in original}, original)
        # This test does not choose which correction version an account view uses.

    def test_foreign_tenant_context_rejected(self):
        with self.assertRaises(o.c.TenantIsolationError):
            o.statement(o.c.TenantContext("t2", "u1"), self.records, self.raw, self.decision)

    def test_foreign_tenant_source_rejected(self):
        with self.assertRaises(o.c.TenantIsolationError):
            self.check((replace(self.records[0], tenant_id="t2"), *self.records[1:]))

    def test_declared_account_must_match_original_payload(self):
        with self.assertRaises(o.FixtureRejected):
            self.check((replace(self.records[0], account_id="other"), *self.records[1:]))

    def test_payload_currency_mismatch_rejected(self):
        records, raw = self.changed("buy", currency="KRW")
        with self.assertRaises(o.FixtureRejected):
            self.check(records, raw)

    def test_cash_mismatch_has_no_tolerance(self):
        records, raw = self.changed("closing", cash="885.0000000000000000000000000001")
        result = self.check(records, raw)
        self.assertFalse(result["passed"])
        self.assertIn("cash", result["mismatches"])

    def test_quantity_mismatch_remains_visible(self):
        records, raw = self.changed("closing", quantity="15.001")
        result = self.check(records, raw)
        self.assertFalse(result["passed"])
        self.assertIn("quantity", result["mismatches"])

    def test_statement_market_value_and_total_mismatch_remain_visible(self):
        records, raw = self.changed("closing", market_value="375.01", total="1260.01")
        result = self.check(records, raw)
        self.assertFalse(result["passed"])
        self.assertEqual(set(result["mismatches"]), {"market_value", "total"})

    def test_unknown_target_field_cannot_supply_actual_value(self):
        records, raw = self.changed("closing", target_cash="885.00")
        with self.assertRaises(o.FixtureRejected):
            self.check(records, raw)

    def test_secret_like_extra_field_rejected_without_storage(self):
        records, raw = self.changed("buy", access_token="SYNTHETIC-NOT-A-CREDENTIAL")
        with self.assertRaises(o.FixtureRejected):
            self.check(records, raw)

    def test_duplicate_json_key_rejected_even_with_matching_hash(self):
        record = self.records[0]
        body = self.raw[record.raw_payload_ref].replace(b'"cash": "1000.00"', b'"cash": "1000.00", "cash": "0.00"')
        self.assertNotEqual(body, self.raw[record.raw_payload_ref])
        raw = {**self.raw, record.raw_payload_ref: body}
        records = (replace(record, payload_sha256=hashlib.sha256(body).hexdigest()), *self.records[1:])
        with self.assertRaises(o.FixtureRejected):
            self.check(records, raw)

    def test_future_availability_cannot_enter_decision_view(self):
        future = self.decision + timedelta(seconds=1)
        with self.assertRaises(o.FixtureRejected):
            self.check((replace(self.records[0], available_at=future, ingested_at=future), *self.records[1:]))

    def test_statement_manifest_cannot_omit_input(self):
        records, raw = self.changed("closing", included_record_ids=["opening", "buy"])
        with self.assertRaises(o.FixtureRejected):
            self.check(records, raw)

    def test_nonfinite_value_never_becomes_a_financial_pass(self):
        records, raw = self.changed("closing", price="NaN")
        with self.assertRaises(o.FixtureRejected):
            self.check(records, raw)

    def test_binary_float_amount_is_not_silently_admitted(self):
        records, raw = self.changed("buy", cash_delta=-125.0)
        with self.assertRaises(o.FixtureRejected):
            self.check(records, raw)

    def test_input_order_does_not_change_exact_result(self):
        self.assertEqual(self.check(tuple(reversed(self.records))), self.check())


if __name__ == "__main__":
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(StatementFixtureTests))
    print(stream.getvalue(), end="")
    print(json.dumps({"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "passed": result.testsRun - len(result.failures) - len(result.errors), "scope": "synthetic fixture oracle only; no owner/runtime/production claim"}, sort_keys=True))
    sys.exit(0 if result.wasSuccessful() else 1)
