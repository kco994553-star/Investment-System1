"""Boundary and ownership tests using synthetic finance and trusted clock."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from investment_system.product_platform.api import PlatformAPI
from investment_system.product_platform.auth import SessionAuth, SyntheticIdentityProvider
from investment_system.product_platform.domain import PlatformError, ReadPage, json_text
from investment_system.product_platform.fixture import synthetic_connector, synthetic_identities
from investment_system.product_platform.service import PlatformService
from investment_system.product_platform.store import ScopedStore


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ScopedStore(Path(self.temp.name) / "synthetic.sqlite")
        self.now = datetime(2026, 10, 5, 3, tzinfo=timezone.utc)
        self.service = PlatformService(self.store, tuple((identity,) for identity in synthetic_identities()), max_payload_bytes=100000, max_pages=5)
        self.auth = SessionAuth(SyntheticIdentityProvider({
            "fixture:alice": ("user-a", "tenant-a"),
            "fixture:bob": ("user-b", "tenant-a"),
            "fixture:carol": ("user-c", "tenant-b"),
        }), ttl=timedelta(minutes=5), max_attempts=20, rate_window=timedelta(minutes=1))
        self.api = PlatformAPI(self.service, self.auth, lambda: self.now, synthetic_connector)
        self.a = self.login("fixture:alice")
        self.b = self.login("fixture:bob")
        self.c = self.login("fixture:carol")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def login(self, fixture):
        status, payload = self.api.request("POST", "/synthetic-login", body={"fixture_id": fixture}, attempt_key="test-server-client")
        self.assertEqual(status, 200)
        return payload["data"]

    def request(self, method, path, credentials=None, body=None, csrf=True):
        credentials = credentials or self.a
        return self.api.request(method, path, token=credentials["token"], csrf=credentials["csrf"] if csrf else None, body=body)

    def connection(self, credentials=None):
        status, payload = self.request("POST", "/connections", credentials)
        self.assertEqual(status, 201)
        return payload["data"]["id"]

    def sync(self, cid, credentials=None):
        status, payload = self.request("POST", f"/connections/{cid}/sync", credentials)
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["state"], "SUCCEEDED")
        return payload["data"]["id"]

    def assert_error(self, expected_status, expected_code, response):
        self.assertEqual(response, (expected_status, {"error": {"code": expected_code}}))

    def test_me_and_login_explicitly_synthetic(self):
        status, payload = self.request("GET", "/me")
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["user_id"], "user-a")
        self.assertFalse(payload["is_real"])
        self.assertEqual(self.a["authentication_state"], "LOCAL_TEST_FIXTURE")
        self.assertTrue(self.a["synthetic"])
        self.assert_error(401, "LOGIN_REJECTED", self.api.request("POST", "/synthetic-login", body={"fixture_id": "real-token"}))

    def test_authentication_expiry_logout_tampering_and_csrf(self):
        self.assert_error(401, "SESSION_REJECTED", self.api.request("GET", "/connections"))
        self.assert_error(401, "SESSION_REJECTED", self.api.request("GET", "/me", token=self.a["token"] + "x"))
        self.assert_error(403, "CSRF_REJECTED", self.request("POST", "/connections", csrf=False))
        self.assert_error(403, "CSRF_REJECTED", self.api.request("POST", "/connections", token=self.a["token"], csrf=self.b["csrf"]))
        status, _ = self.request("POST", "/logout")
        self.assertEqual(status, 200)
        self.assert_error(401, "SESSION_REJECTED", self.request("GET", "/me"))
        self.assert_error(401, "SESSION_REJECTED", self.request("POST", "/logout"))
        self.now += timedelta(minutes=5)
        self.assert_error(401, "SESSION_REJECTED", self.request("GET", "/me", self.b))

    def test_all_object_routes_reject_other_user_same_and_different_tenant(self):
        cid = self.connection()
        run_id = self.sync(cid)
        _, portfolio = self.request("GET", f"/connections/{cid}/portfolio")
        receipt_id = portfolio["data"]["receipt_ids"][0]
        routes = [f"/connections/{cid}", f"/connections/{cid}/portfolio", f"/connections/{cid}/export", f"/sync/{run_id}", f"/raw/{receipt_id}"]
        routes += [f"/connections/{cid}/{resource}" for resource in ("accounts", "balances", "positions", "transactions", "statements")]
        for credentials in (self.b, self.c):
            with self.subTest(user=credentials["principal"]["user_id"]):
                self.assertEqual(self.request("GET", "/connections", credentials)[1]["data"], [])
                for route in routes:
                    self.assert_error(404, "NOT_FOUND", self.request("GET", route, credentials))
                for action in ("sync", "revoke"):
                    self.assert_error(404, "NOT_FOUND", self.request("POST", f"/connections/{cid}/{action}", credentials))
        self.assert_error(404, "NOT_FOUND", self.request("GET", "/raw/nonexistent"))
        self.assert_error(404, "NOT_FOUND", self.request("GET", "/connections/nonexistent/portfolio"))

    def test_same_fixture_ids_stay_separate_between_user_tenant_scopes(self):
        cids = [self.connection(credentials) for credentials in (self.a, self.b, self.c)]
        for credentials, cid in zip((self.a, self.b, self.c), cids):
            self.sync(cid, credentials)
            own = self.request("GET", "/connections", credentials)[1]["data"]
            self.assertEqual([row["id"] for row in own], [cid])
            self.assertNotIn("user_id", own[0])
            self.assertEqual(self.request("GET", f"/connections/{cid}/accounts", credentials)[1]["data"][0]["id"], "acct-1")

    def test_closed_body_ownership_time_cursor_rejected_without_side_effect(self):
        cid = self.connection()
        for body in ({"user_id": "user-b"}, {"tenantId": "tenant-b"}, {"principal": {}}, {"decision_time": self.now.isoformat()}, {"cursor": "external-cursor"}, {"access_token": "secret"}, {"amount": "100"}, []):
            response = self.request("POST", f"/connections/{cid}/sync", body=body)
            self.assertEqual(response[0], 400)
        self.assert_error(400, "QUERY_REJECTED", self.request("GET", f"/connections/{cid}/portfolio?now=2099"))
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 0)
        self.assert_error(400, "REQUEST_REJECTED", self.api.request("POST", "/synthetic-login", body={"fixture_id": "fixture:alice", "password": "secret"}))

    def test_financial_action_routes_are_absent_but_historical_buy_is_data(self):
        cid = self.connection()
        self.sync(cid)
        for action in ("buy", "sell", "order", "orders", "transfer", "deposit", "withdraw", "cancel_order", "trade"):
            self.assert_error(404, "ROUTE_NOT_FOUND", self.request("POST", f"/connections/{cid}/{action}"))
        rows = self.request("GET", f"/connections/{cid}/transactions")[1]["data"]
        self.assertEqual(rows[0]["kind"], "BUY")
        self.assertFalse(self.request("GET", f"/connections/{cid}/export")[1]["data"]["is_real"])

    def test_raw_is_metadata_only_and_provenance_tampering_rejected(self):
        cid = self.connection()
        self.sync(cid)
        receipt_id = self.request("GET", f"/connections/{cid}/portfolio")[1]["data"]["receipt_ids"][0]
        status, payload = self.request("GET", f"/raw/{receipt_id}")
        self.assertEqual(status, 200)
        self.assertEqual(set(payload["data"]), {"id", "connection_id", "resource", "sha256", "fetched_at", "byte_length"})
        with self.store.lock, self.store.db:
            self.store.db.execute("UPDATE receipts SET body=? WHERE id=?", (b"tampered", receipt_id))
        self.assert_error(409, "PROVENANCE_FAILED", self.request("GET", f"/raw/{receipt_id}"))
        self.assert_error(409, "PROVENANCE_FAILED", self.request("GET", f"/connections/{cid}/portfolio"))

    def test_provider_exception_and_unknown_error_never_leak_secret(self):
        def broken_factory(now):
            raise RuntimeError("real-password-secret-do-not-log")
        api = PlatformAPI(self.service, self.auth, lambda: self.now, broken_factory)
        self.assert_error(500, "INTERNAL_ERROR", api.request("POST", "/connections", token=self.a["token"], csrf=self.a["csrf"]))
        def hostile_factory(now):
            raise PlatformError("real-token-from-provider")
        api = PlatformAPI(self.service, self.auth, lambda: self.now, hostile_factory)
        self.assert_error(500, "INTERNAL_ERROR", api.request("POST", "/connections", token=self.a["token"], csrf=self.a["csrf"]))

    def test_capability_escalation_and_real_connector_rejected(self):
        connector = synthetic_connector(self.now)
        connector._capabilities = {"READ_ACCOUNT", "PLACE_ORDER"}
        api = PlatformAPI(self.service, self.auth, lambda: self.now, lambda now: connector)
        self.assert_error(403, "CAPABILITY_REJECTED", api.request("POST", "/connections", token=self.a["token"], csrf=self.a["csrf"]))
        connector.synthetic = False
        self.assert_error(403, "REAL_CONNECTOR_NOT_AUTHORIZED", api.request("POST", "/connections", token=self.a["token"], csrf=self.a["csrf"]))

    def test_revoke_disallows_sync_and_csrf_required(self):
        cid = self.connection()
        self.sync(cid)
        self.assert_error(403, "CSRF_REJECTED", self.request("POST", f"/connections/{cid}/sync", csrf=False))
        self.assert_error(403, "CSRF_REJECTED", self.request("POST", f"/connections/{cid}/revoke", csrf=False))
        self.assertEqual(self.request("POST", f"/connections/{cid}/revoke")[1]["data"]["state"], "REVOKED")
        self.assert_error(409, "CONNECTION_REVOKED", self.request("POST", f"/connections/{cid}/sync"))
        portfolio = self.request("GET", f"/connections/{cid}/portfolio")[1]
        self.assertEqual(portfolio["data_state"], "STALE")
        self.assertEqual(portfolio["data"]["data_state"], "STALE")
        self.assertEqual(portfolio["connection_state"], "REVOKED")
        self.assertEqual(portfolio["as_of"], self.now.isoformat())
        self.assertEqual(portfolio["last_sync_attempt"]["state"], "SUCCEEDED")
        for resource in ("accounts", "balances", "positions"):
            response = self.request("GET", f"/connections/{cid}/{resource}")[1]
            self.assertIsInstance(response["data"], list)
            self.assertEqual(response["data_state"], "STALE")
            self.assertEqual(response["connection_state"], "REVOKED")
            self.assertEqual(response["as_of"], portfolio["as_of"])
            self.assertEqual(response["last_sync_attempt"], portfolio["last_sync_attempt"])
            self.assertEqual(response["data"][0]["data_state"], "DEMO")
        exported = self.request("GET", f"/connections/{cid}/export")[1]
        self.assertEqual(exported["data_state"], "STALE")
        self.assertEqual(exported["data"]["portfolio"]["data_state"], "STALE")

    def test_missing_complete_sync_reports_unavailable_in_all_envelopes(self):
        cid = self.connection()
        for action in ("portfolio", "export", "accounts", "balances", "positions"):
            response = self.request("GET", f"/connections/{cid}/{action}")[1]
            self.assertEqual(response["data_state"], "NOT_AVAILABLE")
            self.assertEqual(response["connection_state"], "ACTIVE")
            self.assertIsNone(response["as_of"])
            self.assertIsNone(response["last_sync_attempt"])
            if action in {"accounts", "balances", "positions"}:
                self.assertEqual(response["data"], [])
                self.assertEqual(response["reason"], "NO_COMPLETE_SYNC")

    def test_current_positions_disappearance_uses_complete_snapshot_not_history(self):
        cid = self.connection()
        self.assertEqual(self.request("GET", f"/connections/{cid}/positions")[1]["data_state"], "NOT_AVAILABLE")
        self.sync(cid)
        principal = self.auth.authenticated(self.a["token"], self.now)
        connector = self.service._connectors[(*self.store.scope(principal), cid)]
        envelope = json.loads(connector.pages["positions"][None].body)
        envelope["records"] = []
        connector.pages["positions"][None] = ReadPage("positions", json_text(envelope).encode())
        self.sync(cid)
        self.assertEqual(self.request("GET", f"/connections/{cid}/positions")[1]["data"], [])
        self.assertEqual(len(self.store.records(principal, cid, "positions", self.now, history=True)), 1)


if __name__ == "__main__":
    unittest.main()
