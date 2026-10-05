"""Synthetic sync integration and ownership/provenance negative tests.

Limits below are explicit test settings, not production policy defaults.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import unittest

from investment_system.product_platform.domain import PlatformError, Principal, ReadPage, json_text
from investment_system.product_platform.fixture import synthetic_connector, synthetic_identities
from investment_system.product_platform.service import PlatformService
from investment_system.product_platform.store import ScopedStore


NOW = datetime(2026, 10, 5, 3, 48, 10, tzinfo=timezone.utc)
LATER = NOW + timedelta(hours=1)
IDENTITIES = tuple((identity,) for identity in synthetic_identities())


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.store = ScopedStore(":memory:")
        self.service = PlatformService(self.store, IDENTITIES, max_payload_bytes=100_000, max_pages=8)
        self.p = Principal("user-a", "tenant-a", "internal-session-a")
        self.other = Principal("user-b", "tenant-b", "internal-session-b")

    def tearDown(self):
        self.store.close()

    def connection(self, connector=None, principal=None):
        connector = connector or synthetic_connector(NOW)
        return connector, self.service.create_connection(principal or self.p, connector, NOW)

    def page(self, connector, resource, mutate, *, cursor=None, **page_fields):
        original = connector.pages[resource][cursor]
        body = json.loads(original.body)
        mutate(body)
        changed = replace(original, body=json_text(body).encode("utf-8"), **page_fields)
        connector.pages[resource][cursor] = changed
        return changed

    def update_record(self, connector, resource, **fields):
        return self.page(connector, resource, lambda body: body["records"][0].update(fields))

    def count(self, table):
        # Table names are test constants, never provider/user input.
        return self.store.db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]

    def assertCode(self, expected, call):
        with self.assertRaises(PlatformError) as caught:
            call()
        self.assertEqual(caught.exception.code, expected)

    def sync_ok(self, cid, now=NOW):
        run = self.service.sync(self.p, cid, now)
        self.assertEqual(run["state"], "SUCCEEDED", run)
        self.assertIsNone(run["error_code"])
        return run

    def sync_failed(self, cid, code, now=NOW):
        run = self.service.sync(self.p, cid, now)
        self.assertEqual((run["state"], run["error_code"]), ("FAILED", code), run)
        return run

    def test_happy_path_reuses_actual_portfolio_and_preserves_provenance(self):
        connector, cid = self.connection()
        run = self.sync_ok(cid, LATER)
        portfolio = self.service.portfolio(self.p, cid, LATER)
        self.assertEqual((portfolio["portfolio_kind"], portfolio["data_state"], portfolio["is_real"]), ("ACTUAL", "DEMO", False))
        self.assertTrue(portfolio["complete"])
        self.assertEqual(portfolio["as_of"], NOW.isoformat())
        self.assertEqual(portfolio["sync_completed_at"], LATER.isoformat())
        self.assertEqual(portfolio["last_sync_attempt"]["id"], run["id"])
        analytics = portfolio["analytics"]
        self.assertEqual(analytics["source"], "personal.ActualPortfolioSnapshot")
        self.assertEqual(Decimal(analytics["calculated_total"]), Decimal("1000.00"))
        self.assertEqual(analytics["calculated_weights"], {"synthetic-security-1": "0.75"})
        self.assertTrue(analytics["is_reconciled"])
        self.assertEqual(len(portfolio["receipt_ids"]), 5)
        self.assertEqual({m["resource"] for m in portfolio["resource_metadata"]}, {"accounts", "balances", "positions", "transactions", "statements"})
        for row in self.store.records(self.p, cid, "positions", LATER):
            receipt = self.store.receipt(self.p, row["receipt_id"])
            self.assertEqual(receipt["resource"], "positions")
            self.assertEqual(receipt["body"], connector.sync_positions().body)
        for engine in portfolio["engines"].values():
            self.assertEqual(engine["state"], "NOT_AVAILABLE")
        self.assertEqual(portfolio["target"]["state"], "NOT_AVAILABLE")
        export = self.service.export(self.p, cid, LATER)
        self.assertEqual(export["transactions"][0]["kind"], "BUY")
        self.assertFalse(export["is_real"])
        self.assertIn("DATA_EXPORTED", {entry["event"] for entry in export["audit"]})

    def test_replay_is_idempotent_for_raw_and_normalized_records(self):
        connector, cid = self.connection()
        self.sync_ok(cid)
        counts = self.count("receipts"), self.count("records")
        self.sync_ok(cid, LATER)
        self.assertEqual((self.count("receipts"), self.count("records")), counts)
        self.assertEqual(len(self.store.records(self.p, cid, "transactions", LATER, history=True)), 1)
        self.assertEqual(self.service.portfolio(self.p, cid, LATER)["positions"][0]["quantity"], "5.000")

    def test_correction_appends_revision_and_historical_query_uses_available_time(self):
        connector, cid = self.connection()
        self.sync_ok(cid)
        first = self.service.portfolio(self.p, cid, NOW)["snapshot_id"]
        self.update_record(connector, "positions", revision=2, market_value="700.00", available_at=LATER.isoformat(), provider_reported_at=LATER.isoformat())
        self.sync_ok(cid, LATER)
        history = self.store.records(self.p, cid, "positions", LATER, history=True)
        self.assertEqual([r["revision"] for r in history], [1, 2])
        self.assertNotEqual(history[0]["receipt_id"], history[1]["receipt_id"])
        self.assertEqual(self.store.records(self.p, cid, "positions", NOW)[0]["revision"], 1)
        self.assertEqual(self.store.records(self.p, cid, "positions", LATER)[0]["revision"], 2)
        self.assertEqual(self.service.portfolio(self.p, cid, NOW)["snapshot_id"], first)
        self.assertEqual(self.service.portfolio(self.p, cid, LATER)["positions"][0]["market_value"], "700.00")

    def test_revision_collision_retains_snapshot_and_rolls_back_other_resources(self):
        connector, cid = self.connection()
        self.sync_ok(cid)
        snapshot = self.service.portfolio(self.p, cid, NOW)["snapshot_id"]
        self.update_record(connector, "accounts", revision=2)
        self.update_record(connector, "positions", market_value="700.00")
        self.sync_failed(cid, "REVISION_COLLISION", LATER)
        self.assertEqual(self.service.portfolio(self.p, cid, LATER)["snapshot_id"], snapshot)
        self.assertEqual(len(self.store.records(self.p, cid, "accounts", LATER, history=True)), 1)
        self.assertEqual(len(self.store.records(self.p, cid, "positions", LATER, history=True)), 1)
        self.assertGreater(self.count("receipts"), 5)

    def test_revision_regression_is_rejected_after_a_correction(self):
        connector, cid = self.connection()
        self.sync_ok(cid)
        original = connector.pages["positions"][None]
        self.update_record(connector, "positions", revision=2, market_value="700.00")
        self.sync_ok(cid, LATER)
        connector.pages["positions"][None] = original
        self.sync_failed(cid, "REVISION_REGRESSION", LATER)
        self.assertEqual(self.store.records(self.p, cid, "positions", LATER)[0]["revision"], 2)

    def test_duplicate_records_on_pages_deduplicate_but_conflicting_duplicate_fails(self):
        connector, cid = self.connection()
        page = connector.pages["accounts"][None]
        connector.pages["accounts"][None] = replace(page, next_cursor="account-page-2")
        connector.pages["accounts"]["account-page-2"] = page
        self.sync_ok(cid)
        self.assertEqual(len(self.store.records(self.p, cid, "accounts", NOW)), 1)
        self.page(connector, "accounts", lambda body: body["records"][0].update(status="CLOSED"), cursor="account-page-2")
        self.sync_failed(cid, "REVISION_COLLISION", LATER)

    def test_pagination_commits_only_final_incremental_watermark_and_retry_uses_it(self):
        connector, cid = self.connection()
        page = connector.pages["transactions"][None]
        empty = json.loads(page.body)
        empty["records"] = []
        connector.pages["transactions"][None] = replace(page, next_cursor="next-1", resume_cursor="ignored-intermediate")
        connector.pages["transactions"]["next-1"] = ReadPage("transactions", json_text(empty).encode(), resume_cursor="watermark-1")
        self.sync_ok(cid)
        self.assertEqual(self.store.cursor(self.p, cid, "transactions"), "watermark-1")
        connector.pages["transactions"]["watermark-1"] = ReadPage("transactions", json_text(empty).encode(), resume_cursor="watermark-2")
        self.sync_ok(cid, LATER)
        self.assertEqual(self.store.cursor(self.p, cid, "transactions"), "watermark-2")
        self.assertEqual(len(self.store.records(self.p, cid, "transactions", LATER, history=True)), 1)

    def test_cursor_loop_failure_has_no_records_watermark_or_snapshot(self):
        connector, cid = self.connection()
        page = connector.pages["transactions"][None]
        connector.pages["transactions"][None] = replace(page, next_cursor="loop")
        connector.pages["transactions"]["loop"] = replace(page, next_cursor="loop")
        self.sync_failed(cid, "CURSOR_LOOP")
        self.assertIsNone(self.store.cursor(self.p, cid, "transactions"))
        self.assertEqual(self.count("records"), 0)
        self.assertEqual(self.service.portfolio(self.p, cid, NOW)["data_state"], "NOT_AVAILABLE")
        connector.pages["transactions"][None] = page
        self.sync_ok(cid)

    def test_incomplete_intermediate_page_never_promotes_group_to_success(self):
        connector, cid = self.connection()
        page = connector.pages["accounts"][None]
        connector.pages["accounts"][None] = replace(page, complete=False, next_cursor="complete-final")
        connector.pages["accounts"]["complete-final"] = page
        run = self.service.sync(self.p, cid, NOW)
        self.assertEqual(run["state"], "PARTIAL")
        self.assertEqual(self.count("records"), 0)
        self.assertIsNone(self.store.cursor(self.p, cid, "transactions"))
        self.assertEqual(self.service.portfolio(self.p, cid, NOW)["data_state"], "NOT_AVAILABLE")

    def test_invalid_cursor_and_explicit_page_limit_are_enforced(self):
        connector, cid = self.connection()
        page = connector.pages["accounts"][None]
        connector.pages["accounts"][None] = replace(page, next_cursor=42)
        self.sync_failed(cid, "CURSOR_REJECTED")
        self.service.max_pages = 2
        connector.pages["accounts"][None] = replace(page, next_cursor="one")
        connector.pages["accounts"]["one"] = replace(page, next_cursor="two")
        connector.pages["accounts"]["two"] = page
        self.sync_failed(cid, "PAGE_LIMIT")
        self.assertEqual(self.count("records"), 0)

    def test_partial_failure_and_permission_outage_preserve_complete_snapshot_watermark(self):
        connector, cid = self.connection()
        tx = connector.pages["transactions"][None]
        connector.pages["transactions"][None] = replace(tx, resume_cursor="retained-watermark")
        connector.pages["transactions"]["retained-watermark"] = replace(tx, resume_cursor="retained-watermark")
        self.sync_ok(cid)
        snapshot = self.service.portfolio(self.p, cid, NOW)["snapshot_id"]
        positions = connector.pages["positions"][None]
        self.update_record(connector, "positions", revision=2, market_value="700.00")
        connector.pages["positions"][None] = replace(connector.pages["positions"][None], complete=False)
        connector.pages["transactions"]["retained-watermark"] = replace(tx, resume_cursor="must-not-commit")
        partial = self.service.sync(self.p, cid, LATER)
        self.assertEqual(partial["state"], "PARTIAL")
        self.assertEqual(self.service.portfolio(self.p, cid, LATER)["snapshot_id"], snapshot)
        self.assertEqual(self.store.cursor(self.p, cid, "transactions"), "retained-watermark")
        self.assertEqual(len(self.store.records(self.p, cid, "positions", LATER, history=True)), 1)
        connector.pages["positions"][None] = positions
        for error in ("PERMISSION_DENIED", "PROVIDER_UNAVAILABLE"):
            connector.failures["positions"] = error
            self.sync_failed(cid, error, LATER)
            self.assertEqual(self.service.portfolio(self.p, cid, LATER)["snapshot_id"], snapshot)
            self.assertEqual(self.store.cursor(self.p, cid, "transactions"), "retained-watermark")
        del connector.failures["positions"]
        connector.pages["transactions"]["retained-watermark"] = replace(tx, resume_cursor="recovered")
        self.sync_ok(cid, LATER)
        self.assertEqual(self.store.cursor(self.p, cid, "transactions"), "recovered")

    def test_user_and_tenant_isolation_covers_connection_run_receipt_cursor_export_sync(self):
        connector, cid = self.connection()
        run = self.sync_ok(cid)
        receipt_id = self.store.records(self.p, cid, "positions", NOW)[0]["receipt_id"]
        intruders = (self.other, Principal(self.p.user_id, "tenant-other", "internal-s"), Principal("user-other", self.p.tenant_id, "internal-s"))
        for intruder in intruders:
            with self.subTest(principal=intruder):
                before = self.count("runs"), self.count("receipts"), self.count("audit")
                calls = (lambda: self.store.connection(intruder, cid), lambda: self.store.run(intruder, run["id"]),
                         lambda: self.store.receipt(intruder, receipt_id), lambda: self.store.cursor(intruder, cid, "transactions"),
                         lambda: self.store.records(intruder, cid, "positions", NOW), lambda: self.service.portfolio(intruder, cid, NOW),
                         lambda: self.service.export(intruder, cid, NOW), lambda: self.service.sync(intruder, cid, NOW),
                         lambda: self.service.revoke_connection(intruder, cid, NOW))
                for call in calls:
                    self.assertCode("NOT_FOUND", call)
                self.assertEqual((self.count("runs"), self.count("receipts"), self.count("audit")), before)
                self.assertEqual(self.store.connections(intruder), [])
                self.assertEqual(self.store.audit(intruder), [])

    def test_independent_same_provider_accounts_do_not_share_receipts_or_cache(self):
        _, cid_a = self.connection()
        _, cid_b = self.connection(synthetic_connector(NOW), self.other)
        self.sync_ok(cid_a)
        self.assertEqual(self.service.sync(self.other, cid_b, NOW)["state"], "SUCCEEDED")
        receipt_a = self.store.records(self.p, cid_a, "positions", NOW)[0]["receipt_id"]
        receipt_b = self.store.records(self.other, cid_b, "positions", NOW)[0]["receipt_id"]
        self.assertNotEqual(receipt_a, receipt_b)
        self.assertCode("NOT_FOUND", lambda: self.store.receipt(self.p, receipt_b))
        self.assertCode("NOT_FOUND", lambda: self.store.receipt(self.other, receipt_a))

    def test_one_connector_instance_cannot_bind_multiple_owners(self):
        connector, cid = self.connection()
        self.assertCode("CONNECTOR_ALREADY_BOUND", lambda: self.service.create_connection(self.other, connector, NOW))
        self.assertEqual(len(self.store.connections(self.p)), 1)
        self.assertEqual(self.store.connections(self.other), [])

    def test_ticker_only_unresolved_positions_remain_visible_without_analytics(self):
        connector, cid = self.connection()
        def ticker_only(body):
            row = body["records"][0]
            row.pop("security_id")
            row.pop("listing_id")
            row["ticker"] = "SYNTHETIC"
        self.page(connector, "positions", ticker_only)
        self.sync_ok(cid)
        portfolio = self.service.portfolio(self.p, cid, NOW)
        self.assertEqual(portfolio["identity_status"], "UNRESOLVED")
        self.assertEqual(portfolio["positions"][0]["ticker"], "SYNTHETIC")
        self.assertIsNone(portfolio["analytics"])
        self.assertIsNone(portfolio["positions"][0]["issuer_id"])

    def test_invalid_decimal_lexemes_and_float_values_fail_atomically(self):
        for value in (1.0, "NaN", "Infinity", "1e3", "", "+1", "1,000", None):
            with self.subTest(value=value):
                connector, cid = self.connection()
                self.update_record(connector, "positions", market_value=value)
                self.sync_failed(cid, "INVALID_NUMBER")
                self.assertEqual(self.store.records(self.p, cid, "positions", NOW), [])
                self.assertEqual(self.service.portfolio(self.p, cid, NOW)["data_state"], "NOT_AVAILABLE")

    def test_currency_mismatch_invalid_currency_and_cross_account_reference(self):
        cases = (("currency", "EUR", "CURRENCY_MISMATCH"), ("currency", "usd", "INVALID_CURRENCY"),
                 ("account_id", "foreign-account", "CROSS_ACCOUNT_REFERENCE"))
        for field, value, error in cases:
            with self.subTest(field=field, value=value):
                connector, cid = self.connection()
                self.update_record(connector, "positions", **{field: value})
                self.sync_failed(cid, error)
                self.assertEqual(self.store.records(self.p, cid, "accounts", NOW), [])

    def test_unknown_naive_and_future_timestamps_fail_without_fetched_time_substitution(self):
        cases = (("available_at", None, "INVALID_TIME"), ("available_at", "2026-10-05T03:48:10", "INVALID_TIME"),
                 ("available_at", LATER.isoformat(), "FUTURE_DATA"), ("effective_at", LATER.isoformat(), "FUTURE_DATA"),
                 ("provider_reported_at", LATER.isoformat(), "FUTURE_DATA"))
        for field, value, error in cases:
            with self.subTest(field=field, value=value):
                connector, cid = self.connection()
                self.update_record(connector, "positions", **{field: value})
                self.sync_failed(cid, error)
                self.assertEqual(self.store.records(self.p, cid, "positions", LATER), [])
        connector, cid = self.connection()
        self.page(connector, "positions", lambda body: body.pop("available_at"))
        self.sync_failed(cid, "SCHEMA_REJECTED")

    def test_malicious_metadata_unknown_fields_and_secret_keys_are_not_persisted_as_records(self):
        for mutate, error in ((lambda b: b.update(tenant_id="tenant-b"), "SCHEMA_REJECTED"),
                              (lambda b: b["records"][0].update(user_id="user-b"), "SCHEMA_REJECTED"),
                              (lambda b: b["records"][0].update(side_effect={"submit_order": True}), "SCHEMA_REJECTED"),
                              (lambda b: b["records"][0].update(revision=True), "SCHEMA_REJECTED"),
                              (lambda b: b.update(provider_note={"access-token": "DO-NOT-PERSIST"}), "SECRET_PAYLOAD_REJECTED")):
            with self.subTest(error=error):
                connector, cid = self.connection()
                self.page(connector, "accounts", mutate)
                self.sync_failed(cid, error)
                self.assertEqual(self.store.records(self.p, cid, "accounts", NOW), [])
                if error == "SECRET_PAYLOAD_REJECTED":
                    row = self.store.db.execute("SELECT body FROM receipts WHERE connection_id=?", (cid,)).fetchone()
                    self.assertIsNone(row)
        self.assertNotIn("DO-NOT-PERSIST", json_text(self.store.audit(self.p)))

    def test_duplicate_json_keys_invalid_json_and_payload_limit_reject_before_persistence(self):
        for body, error in ((b'{"records":[],"records":[]}', "DUPLICATE_KEY"), (b'not-json', "PAYLOAD_REJECTED"),
                            (b'{"x":NaN}', "INVALID_NUMBER"), (b'\xff', "PAYLOAD_REJECTED")):
            with self.subTest(body=body):
                connector, cid = self.connection()
                connector.pages["accounts"][None] = ReadPage("accounts", body)
                self.sync_failed(cid, error)
                self.assertEqual(self.store.records(self.p, cid, "accounts", NOW), [])
        connector, cid = self.connection()
        self.service.max_payload_bytes = 1
        self.sync_failed(cid, "PAYLOAD_REJECTED")

    def test_raw_receipt_tampering_blocks_receipt_records_portfolio_and_export(self):
        _, cid = self.connection()
        self.sync_ok(cid)
        rid = self.store.records(self.p, cid, "positions", NOW)[0]["receipt_id"]
        with self.store.db:
            self.store.db.execute("UPDATE receipts SET body=? WHERE id=?", (b'{"tampered":true}', rid))
        for call in (lambda: self.store.receipt(self.p, rid), lambda: self.store.records(self.p, cid, "positions", NOW),
                     lambda: self.service.portfolio(self.p, cid, NOW), lambda: self.service.export(self.p, cid, NOW)):
            self.assertCode("PROVENANCE_FAILED", call)

    def test_raw_receipt_resource_and_connection_metadata_tampering_are_detected(self):
        for column in ("resource", "connection_id"):
            with self.subTest(column=column):
                _, cid = self.connection()
                _, other_cid = self.connection()
                self.sync_ok(cid)
                rid = self.store.records(self.p, cid, "positions", NOW)[0]["receipt_id"]
                original = self.store.receipt(self.p, rid)
                value = "balances" if column == "resource" else other_cid
                with self.store.db:
                    self.store.db.execute("UPDATE receipts SET " + column + "=? WHERE id=?", (value, rid))
                persisted = self.store.db.execute("SELECT body,sha256 FROM receipts WHERE id=?", (rid,)).fetchone()
                self.assertEqual((persisted["body"], persisted["sha256"]), (original["body"], original["sha256"]))
                for call in (lambda: self.store.receipt(self.p, rid), lambda: self.service.portfolio(self.p, cid, NOW),
                             lambda: self.service.export(self.p, cid, NOW)):
                    self.assertCode("PROVENANCE_FAILED", call)

    def test_normalized_record_payload_timestamp_and_owner_tamper_are_detected(self):
        for column, value in (("payload", '{"market_value":"999999"}'), ("available_at", (NOW-timedelta(days=2)).isoformat()),
                              ("object_id", "injected-object")):
            with self.subTest(column=column):
                _, cid = self.connection()
                self.sync_ok(cid)
                with self.store.db:
                    self.store.db.execute("UPDATE records SET " + column + "=? WHERE connection_id=? AND resource='positions'", (value, cid))
                self.assertCode("PROVENANCE_FAILED", lambda: self.store.records(self.p, cid, "positions", NOW))

    def test_snapshot_payload_tampering_is_detected(self):
        _, cid = self.connection()
        self.sync_ok(cid)
        with self.store.db:
            self.store.db.execute("UPDATE snapshots SET payload=? WHERE connection_id=?", ('{"is_real":true}', cid))
        self.assertCode("PROVENANCE_FAILED", lambda: self.service.portfolio(self.p, cid, NOW))
        self.assertCode("PROVENANCE_FAILED", lambda: self.service.export(self.p, cid, NOW))

    def test_snapshot_availability_tampering_is_detected_before_time_filtering(self):
        cases = ((NOW-timedelta(days=1), NOW-timedelta(hours=12)), (LATER+timedelta(days=1), NOW))
        for forged_available, decision in cases:
            with self.subTest(forged_available=forged_available):
                _, cid = self.connection()
                self.sync_ok(cid)
                with self.store.db:
                    self.store.db.execute("UPDATE snapshots SET available_at=? WHERE connection_id=?", (forged_available.isoformat(), cid))
                self.assertCode("PROVENANCE_FAILED", lambda: self.store.latest_snapshot(self.p, cid, decision))
                self.assertCode("PROVENANCE_FAILED", lambda: self.service.portfolio(self.p, cid, decision))
                self.assertCode("PROVENANCE_FAILED", lambda: self.service.export(self.p, cid, decision))

    def test_historical_last_sync_attempt_excludes_future_runs_and_future_completion(self):
        connector, cid = self.connection()
        original_run = self.sync_ok(cid)
        connector.failures["positions"] = "PROVIDER_UNAVAILABLE"
        future_run = self.sync_failed(cid, "PROVIDER_UNAVAILABLE", LATER)
        historical = self.service.portfolio(self.p, cid, NOW)["last_sync_attempt"]
        self.assertEqual(historical["id"], original_run["id"])
        self.assertEqual(historical["state"], "SUCCEEDED")
        self.assertNotEqual(historical["id"], future_run["id"])

        started = NOW + timedelta(minutes=30)
        decision = NOW + timedelta(minutes=45)
        in_flight = self.store.start_run(self.p, cid, started)
        self.store.finish_run(self.p, in_flight, "FAILED", LATER, "PERMISSION_DENIED")
        during_run = self.service.portfolio(self.p, cid, decision)["last_sync_attempt"]
        self.assertEqual(during_run["id"], in_flight)
        self.assertEqual(during_run["state"], "RUNNING")
        self.assertEqual(during_run["started_at"], started.isoformat())
        self.assertIsNone(during_run["completed_at"])
        self.assertIsNone(during_run["error_code"])
        self.assertEqual(self.service.portfolio(self.p, cid, NOW)["last_sync_attempt"]["id"], original_run["id"])

    def test_closed_account_is_historical_visible_with_no_valid_current_analytics(self):
        connector, cid = self.connection()
        self.sync_ok(cid)
        self.update_record(connector, "accounts", revision=2, status="CLOSED")
        self.sync_ok(cid, LATER)
        portfolio = self.service.portfolio(self.p, cid, LATER)
        self.assertEqual(portfolio["accounts"][0]["status"], "CLOSED")
        self.assertFalse(portfolio["complete"])
        self.assertIsNone(portfolio["analytics"])
        self.assertEqual(portfolio["reconciliation"][0]["reported_values"], "NOT_COMPARABLE")
        self.assertEqual(len(self.store.records(self.p, cid, "accounts", LATER, history=True)), 2)

    def test_latest_complete_membership_removes_missing_position_without_rewriting_history(self):
        connector, cid = self.connection()
        self.sync_ok(cid)
        self.page(connector, "positions", lambda body: body.update(records=[]))
        self.update_record(connector, "balances", revision=2, total="250.00")
        self.sync_ok(cid, LATER)
        portfolio = self.service.portfolio(self.p, cid, LATER)
        self.assertEqual(portfolio["positions"], [])
        self.assertEqual(portfolio["analytics"]["calculated_weights"], {})
        self.assertEqual(Decimal(portfolio["analytics"]["calculated_total"]), Decimal("250.00"))
        self.assertEqual(len(self.store.records(self.p, cid, "positions", LATER, history=True)), 1)

    def test_empty_stale_or_delayed_resource_keeps_provider_state_and_blocks_analytics(self):
        for state in ("STALE", "DELAYED"):
            with self.subTest(state=state):
                connector, cid = self.connection()
                self.page(connector, "positions", lambda body: body.update(records=[], data_state=state))
                self.update_record(connector, "balances", total="250.00")
                self.sync_ok(cid)
                portfolio = self.service.portfolio(self.p, cid, NOW)
                self.assertEqual(portfolio["data_state"], state)
                self.assertIsNone(portfolio["analytics"])
                self.assertEqual(len(portfolio["receipt_ids"]), 5)

    def test_mismatch_remains_visible_and_transactions_statements_are_not_comparable(self):
        connector, cid = self.connection(synthetic_connector(NOW, amount="1001.00"))
        self.sync_ok(cid)
        portfolio = self.service.portfolio(self.p, cid, NOW)
        rec = portfolio["reconciliation"][0]
        self.assertEqual(rec["reported_values"], "MISMATCH")
        self.assertEqual(Decimal(rec["difference"]), Decimal("-1.00"))
        self.assertEqual((rec["transactions"], rec["statements"]), ("NOT_COMPARABLE", "NOT_COMPARABLE"))
        self.assertFalse(portfolio["analytics"]["is_reconciled"])
        self.assertEqual(Decimal(portfolio["analytics"]["calculated_total"]), Decimal("1000.00"))

    def test_same_time_comparison_does_not_invent_alignment(self):
        connector, cid = self.connection()
        self.update_record(connector, "positions", effective_at=(NOW-timedelta(days=1)).isoformat())
        self.sync_ok(cid)
        portfolio = self.service.portfolio(self.p, cid, NOW)
        self.assertEqual(portfolio["reconciliation"][0]["reported_values"], "NOT_COMPARABLE")
        self.assertFalse(portfolio["complete"])
        self.assertIsNone(portfolio["analytics"])

    def test_high_precision_reconciliation_is_exact_and_existing_analytics_are_guarded(self):
        connector, cid = self.connection()
        market = "1234567890123456789012345678.12"
        cash = "0.00000000000000000000000000001"
        total = "1234567890123456789012345678.12000000000000000000000000001"
        self.update_record(connector, "positions", market_value=market)
        self.update_record(connector, "balances", cash=cash, total=total)
        self.sync_ok(cid)
        portfolio = self.service.portfolio(self.p, cid, NOW)
        self.assertEqual(portfolio["reconciliation"][0]["reported_values"], "MATCH")
        self.assertEqual(Decimal(portfolio["reconciliation"][0]["difference"]), 0)
        self.assertEqual(portfolio["numeric_status"], "EXISTING_CONTEXT_PRECISION_INSUFFICIENT")
        self.assertIsNone(portfolio["analytics"])
        self.assertEqual(portfolio["positions"][0]["market_value"], market)
        self.assertEqual(portfolio["balances"][0]["total"], total)

    def test_sub_context_precision_mismatch_is_never_rounded_into_match(self):
        connector, cid = self.connection()
        market = "1234567890123456789012345678.12"
        self.update_record(connector, "positions", market_value=market)
        self.update_record(connector, "balances", cash="0.00", total="1234567890123456789012345678.12000000000000000000000000001")
        self.sync_ok(cid)
        rec = self.service.portfolio(self.p, cid, NOW)["reconciliation"][0]
        self.assertEqual(rec["reported_values"], "MISMATCH")
        self.assertEqual(Decimal(rec["difference"]), Decimal("-0.00000000000000000000000000001"))

    def test_unsupported_short_quantity_stays_visible_without_long_fixture_analytics(self):
        connector, cid = self.connection()
        self.update_record(connector, "positions", quantity="-5.000")
        self.sync_ok(cid)
        portfolio = self.service.portfolio(self.p, cid, NOW)
        self.assertEqual(portfolio["positions"][0]["quantity"], "-5.000")
        self.assertEqual(portfolio["quantity_status"], "UNSUPPORTED_OR_INCONSISTENT_DIRECTION")
        self.assertIsNone(portfolio["analytics"])

    def test_external_and_local_revocation_make_last_snapshot_stale_and_block_jobs(self):
        connector, cid = self.connection()
        self.sync_ok(cid)
        connector.revoke_connection()
        portfolio = self.service.portfolio(self.p, cid, LATER)
        self.assertEqual((portfolio["data_state"], portfolio["connection_state"]), ("STALE", "REVOKED"))
        self.assertEqual(self.store.connection(self.p, cid)["state"], "REVOKED")
        before = self.count("runs")
        self.assertCode("CONNECTION_REVOKED", lambda: self.service.sync(self.p, cid, LATER))
        self.assertEqual(self.count("runs"), before)
        _, cid2 = self.connection()
        self.service.revoke_connection(self.p, cid2, NOW)
        self.assertCode("CONNECTION_REVOKED", lambda: self.service.sync(self.p, cid2, NOW))

    def test_mid_sync_revocation_blocks_commit_and_preserves_last_snapshot(self):
        connector, cid = self.connection()
        self.sync_ok(cid)
        snapshot = self.service.portfolio(self.p, cid, NOW)["snapshot_id"]
        self.update_record(connector, "positions", revision=2, market_value="700.00")
        page = connector.pages["positions"][None]
        def revoked_read(cursor=None):
            connector.revoke_connection()
            return page
        connector.sync_positions = revoked_read
        run = self.service.sync(self.p, cid, LATER)
        self.assertEqual((run["state"], run["error_code"]), ("REVOKED", "CONNECTION_REVOKED"))
        portfolio = self.service.portfolio(self.p, cid, LATER)
        self.assertEqual(portfolio["snapshot_id"], snapshot)
        self.assertEqual(portfolio["data_state"], "STALE")
        self.assertEqual(self.store.connection(self.p, cid)["state"], "REVOKED")
        self.assertEqual(len(self.store.records(self.p, cid, "positions", LATER, history=True)), 1)

    def test_complete_group_with_missing_balance_has_no_current_analytics(self):
        connector, cid = self.connection()
        self.page(connector, "balances", lambda body: body.update(records=[]))
        self.sync_ok(cid)
        portfolio = self.service.portfolio(self.p, cid, NOW)
        self.assertFalse(portfolio["complete"])
        self.assertIsNone(portfolio["analytics"])
        self.assertEqual(portfolio["reconciliation"][0]["reported_values"], "NOT_COMPARABLE")

    def test_unknown_exact_identity_references_are_unresolved_without_ticker_fallback(self):
        for fields in ({"security_id": "unknown-security"}, {"listing_id": "unknown-listing"}, {"ticker": "REAL-TICKER"}):
            with self.subTest(fields=fields):
                connector, cid = self.connection()
                self.update_record(connector, "positions", **fields)
                self.sync_ok(cid)
                portfolio = self.service.portfolio(self.p, cid, NOW)
                self.assertEqual(portfolio["identity_status"], "UNRESOLVED")
                self.assertIsNone(portfolio["analytics"])

    def test_forbidden_trade_surface_and_capability_escalation_fail_closed(self):
        for name in ("place_order", "buy", "trade", "create_order", "transfer_funds"):
            with self.subTest(name=name):
                connector = synthetic_connector(NOW)
                setattr(connector, name, lambda: None)
                self.assertCode("CAPABILITY_REJECTED", lambda: self.service.create_connection(self.p, connector, NOW))
        connector, cid = self.connection()
        connector._capabilities = {"READ_ACCOUNT", "READ_BALANCE", "READ_POSITION", "READ_TRANSACTION", "ORDER_WRITE"}
        self.assertCode("CAPABILITY_REJECTED", lambda: self.service.sync(self.p, cid, NOW))
        self.assertEqual(self.count("runs"), 0)


if __name__ == "__main__":
    unittest.main()
