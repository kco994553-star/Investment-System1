"""Actual loopback HTTP integration for the synthetic audit harness.

These tests do not claim browser rendering, mobile E2E, PWA or deployment.
"""
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from http.cookies import SimpleCookie
import json
from pathlib import Path
import tempfile
import threading
import unittest

from investment_system.product_platform.api import PlatformAPI
from investment_system.product_platform.auth import SessionAuth, SyntheticIdentityProvider
from investment_system.product_platform.fixture import synthetic_connector, synthetic_identities
from investment_system.product_platform.service import PlatformService
from investment_system.product_platform.store import ScopedStore
from investment_system.product_platform.web import ASSETS, COOKIE_NAME, create_server


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = datetime(2026, 10, 5, 3, tzinfo=timezone.utc)
        self.store = ScopedStore(Path(self.temp.name) / "synthetic.sqlite")
        service = PlatformService(self.store, tuple((identity,) for identity in synthetic_identities()),
                                  max_payload_bytes=100000, max_pages=5)
        self.auth = SessionAuth(SyntheticIdentityProvider({"fixture:alice": ("alice", "tenant-a"),
                                                          "fixture:bob": ("bob", "tenant-b")}),
                                ttl=timedelta(minutes=5), max_attempts=20, rate_window=timedelta(minutes=1))
        self.api = PlatformAPI(service, self.auth, lambda: self.now, synthetic_connector)
        self.server = create_server(self.api, max_body_bytes=1024, request_timeout=2)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.store.close()
        self.temp.cleanup()

    def request(self, method, path, body=None, *, headers=None):
        request_headers = {} if headers is None else dict(headers)
        if body is not None:
            raw = body if isinstance(body, (str, bytes)) else json.dumps(body)
        else:
            raw = None
        conn = HTTPConnection(*self.server.server_address, timeout=3)
        conn.request(method, path, body=raw, headers=request_headers)
        response = conn.getresponse()
        output = response.status, dict(response.getheaders()), response.read()
        conn.close()
        return output

    def mutation_headers(self, *, credentials=None):
        headers = {"Origin": self.server.origin, "Content-Type": "application/json"}
        if credentials:
            headers.update({"Cookie": credentials["cookie"], "X-CSRF-Token": credentials["csrf"]})
        return headers

    def login(self, fixture="fixture:alice"):
        status, headers, body = self.request("POST", "/api/synthetic-login", {"fixture_id": fixture}, headers=self.mutation_headers())
        self.assertEqual(status, 200)
        payload = json.loads(body)
        cookie = SimpleCookie(headers["Set-Cookie"])
        return {"cookie": f"{COOKIE_NAME}={cookie[COOKIE_NAME].value}", "csrf": payload["data"]["csrf"],
                "hidden_token": cookie[COOKIE_NAME].value, "payload": payload}

    def create_connection(self, credentials):
        status, _, body = self.request("POST", "/api/connections", {}, headers=self.mutation_headers(credentials=credentials))
        self.assertEqual(status, 201)
        return json.loads(body)["data"]["id"]

    def test_loopback_binding_and_explicit_limits(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        with self.assertRaises(ValueError):
            create_server(self.api, max_body_bytes=0, request_timeout=1)
        with self.assertRaises(ValueError):
            create_server(self.api, max_body_bytes=1024, request_timeout=0)

    def test_login_cookie_is_httponly_samesite_and_token_never_in_body(self):
        status, headers, body = self.request("POST", "/api/synthetic-login", {"fixture_id": "fixture:alice"}, headers=self.mutation_headers())
        self.assertEqual(status, 200)
        cookie = SimpleCookie(headers["Set-Cookie"])[COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")
        self.assertEqual(cookie["path"], "/api")
        self.assertNotIn(cookie.value.encode(), body)
        self.assertNotIn("token", json.loads(body)["data"])
        self.assertFalse(cookie["secure"])  # Explicit HTTP-only synthetic loopback.
        self.assertIn("csrf", json.loads(body)["data"])

    def test_cookie_auth_sync_portfolio_and_logout_use_actual_api(self):
        credentials = self.login()
        cid = self.create_connection(credentials)
        headers = self.mutation_headers(credentials=credentials)
        status, _, body = self.request("POST", f"/api/connections/{cid}/sync", {}, headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["data"]["state"], "SUCCEEDED")
        status, _, body = self.request("GET", f"/api/connections/{cid}/portfolio", headers={"Cookie": credentials["cookie"]})
        portfolio = json.loads(body)["data"]
        self.assertEqual(status, 200)
        self.assertEqual(portfolio["analytics"]["calculated_total"], "1000.00")
        self.assertEqual(portfolio["balances"][0]["cash"], "250.00")
        self.assertEqual(portfolio["reconciliation"][0]["reported_values"], "MATCH")
        self.assertEqual(portfolio["engines"]["chart"]["state"], "NOT_AVAILABLE")
        self.assertEqual(portfolio["target"]["state"], "NOT_AVAILABLE")
        self.assertFalse(portfolio["is_real"])
        status, response_headers, _ = self.request("POST", "/api/logout", {}, headers=headers)
        self.assertEqual(status, 200)
        self.assertIn("Max-Age=0", response_headers["Set-Cookie"])
        self.assertEqual(self.request("GET", "/api/me", headers={"Cookie": credentials["cookie"]})[0], 401)

    def test_origin_required_for_login_logout_and_all_mutations(self):
        for origin in (None, "null", "https://evil.example", self.server.origin+".evil"):
            headers = self.mutation_headers()
            if origin is None:
                headers.pop("Origin")
            else:
                headers["Origin"] = origin
            status, _, _ = self.request("POST", "/api/synthetic-login", {"fixture_id": "fixture:alice"}, headers=headers)
            self.assertEqual(status, 403)
        credentials = self.login()
        headers = self.mutation_headers(credentials=credentials)
        headers["Origin"] = "https://evil.example"
        self.assertEqual(self.request("POST", "/api/logout", {}, headers=headers)[0], 403)
        self.assertEqual(self.request("POST", "/api/connections", {}, headers=headers)[0], 403)
        self.assertEqual(self.request("GET", "/api/me", headers={"Cookie": credentials["cookie"]})[0], 200)

    def test_csrf_tamper_missing_expiry_and_fixture_user_isolation(self):
        a, b = self.login(), self.login("fixture:bob")
        cid = self.create_connection(a)
        headers = self.mutation_headers(credentials=a)
        headers.pop("X-CSRF-Token")
        self.assertEqual(self.request("POST", "/api/connections", {}, headers=headers)[0], 403)
        headers["X-CSRF-Token"] = b["csrf"]
        self.assertEqual(self.request("POST", "/api/connections", {}, headers=headers)[0], 403)
        self.assertEqual(self.request("GET", f"/api/connections/{cid}/portfolio", headers={"Cookie": b["cookie"]})[0], 404)
        self.assertEqual(self.request("GET", "/api/me", headers={"Cookie": a["cookie"]+"x"})[0], 401)
        self.now += timedelta(minutes=5)
        self.assertEqual(self.request("GET", "/api/me", headers={"Cookie": a["cookie"]})[0], 401)

    def test_bearer_supported_but_ambiguous_or_duplicate_credentials_rejected(self):
        credentials = self.login()
        bearer = {"Authorization": "Bearer "+credentials["hidden_token"]}
        self.assertEqual(self.request("GET", "/api/me", headers=bearer)[0], 200)
        bearer["Cookie"] = credentials["cookie"]
        self.assertEqual(self.request("GET", "/api/me", headers=bearer)[0], 400)
        self.assertEqual(self.request("GET", "/api/me", headers={"Cookie": credentials["cookie"]+"; "+credentials["cookie"]})[0], 400)
        self.assertEqual(self.request("GET", "/api/me", headers={"Authorization": "Basic unrelated"})[0], 400)

    def test_body_type_length_json_duplicate_keys_and_secret_input(self):
        headers = self.mutation_headers()
        for raw in ("[]", "null", '{"fixture_id":"fixture:alice","fixture_id":"fixture:bob"}',
                    '{"password":"REAL_SECRET_SENTINEL"}', "{"):
            status, _, body = self.request("POST", "/api/synthetic-login", raw, headers=headers)
            self.assertEqual(status, 400)
            self.assertNotIn(b"REAL_SECRET_SENTINEL", body)
        status, _, _ = self.request("POST", "/api/synthetic-login", "x"*1025, headers=headers)
        self.assertEqual(status, 413)
        headers["Content-Type"] = "text/plain"
        self.assertEqual(self.request("POST", "/api/synthetic-login", "{}", headers=headers)[0], 415)
        headers["Content-Type"] = "application/json"
        headers["Transfer-Encoding"] = "chunked"
        self.assertEqual(self.request("POST", "/api/synthetic-login", "{}", headers=headers)[0], 400)

    def test_no_trading_route_asset_traversal_query_or_arbitrary_asset(self):
        credentials = self.login()
        headers = self.mutation_headers(credentials=credentials)
        for path in ("/api/place_order", "/api/submit_order", "/api/transfer", "/api/withdraw", "/api/cancel_order"):
            self.assertEqual(self.request("POST", path, {}, headers=headers)[0], 404)
        for path in ("/../auth.py", "/%2e%2e/auth.py", "/app.js?token=secret", "/api/me?token=secret", "/service-worker.js", "/manifest.json", "/data.json"):
            self.assertEqual(self.request("GET", path)[0], 404)
        for path in ("//api/me", "/api//me"):
            self.assertEqual(self.request("GET", path, headers={"Cookie": credentials["cookie"]})[0], 404)
        for method in ("PUT", "PATCH", "DELETE", "OPTIONS", "HEAD", "TRACE"):
            self.assertEqual(self.request(method, "/api/me")[0], 404)

    def test_headers_apply_to_assets_api_errors_and_host_rejection(self):
        for path in ("/", "/app.js", "/style.css", "/api/me", "/missing"):
            _, headers, _ = self.request("GET", path)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(headers["X-Frame-Options"], "DENY")
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
            self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertEqual(self.request("GET", "/", headers={"Host": "evil.example"})[0], 400)

    def test_mobile_markup_and_javascript_display_only_static_checks(self):
        # Structural checks only; browser/mobile rendering was not executed.
        html = (ASSETS / "index.html").read_text()
        script = (ASSETS / "app.js").read_text()
        style = (ASSETS / "style.css").read_text()
        self.assertIn('name="viewport"', html)
        self.assertIn('lang="ko"', html)
        self.assertIn('role="status"', html)
        self.assertIn('SYNTHETIC / DEMO', html)
        self.assertIn('@media(max-width:700px)', style)
        self.assertIn('overflow:auto', style)
        self.assertIn('textContent', script)
        for forbidden in ('innerHTML', 'localStorage', 'sessionStorage', 'navigator.serviceWorker', 'parseFloat(', 'parseInt('):
            self.assertNotIn(forbidden, script)
        self.assertNotIn('type="password"', html)


if __name__ == "__main__":
    unittest.main()
