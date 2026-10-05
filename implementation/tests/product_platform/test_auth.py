"""Synthetic adapter/session acceptance tests; no production auth claim."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from datetime import datetime, timedelta, timezone
import hashlib
import unittest

from investment_system.product_platform.auth import SessionAuth, SyntheticIdentityProvider
from investment_system.product_platform.domain import PlatformError, Principal


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 5, 3, 0, tzinfo=timezone.utc)
        self.provider = SyntheticIdentityProvider({
            "fixture:alice": ("user-a", "tenant-a"),
            "fixture:bob": ("user-b", "tenant-a"),
            "fixture:carol": ("user-c", "tenant-b"),
        })
        self.auth = SessionAuth(
            self.provider,
            ttl=timedelta(minutes=5),
            max_attempts=3,
            rate_window=timedelta(minutes=1),
        )

    def login(self, fixture_id="fixture:alice", key="loopback-client-a", now=None):
        return self.auth.login(fixture_id, attempt_key=key, now=now or self.now)

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(PlatformError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), code)

    def test_principal_ownership_and_session_distinction(self):
        alice = self.login()
        alice2 = self.login()
        bob = self.login("fixture:bob")
        carol = self.login("fixture:carol", key="loopback-client-b")
        self.assertIsInstance(self.auth.authenticated(alice.token, self.now), Principal)
        self.assertEqual(alice.principal.user_id, alice2.principal.user_id)
        self.assertEqual(alice.principal.tenant_id, bob.principal.tenant_id)
        self.assertNotEqual(alice.principal.user_id, bob.principal.user_id)
        self.assertNotEqual(alice.principal.tenant_id, carol.principal.tenant_id)
        self.assertNotEqual(alice.principal.session_id, alice2.principal.session_id)
        self.assertEqual(len({alice.token, alice2.token, bob.token, carol.token}), 4)

    def test_digest_only_server_storage_and_secret_free_repr_audit(self):
        credentials = self.login()
        self.assertNotIn(credentials.token, repr(credentials))
        self.assertNotIn(credentials.csrf, repr(credentials))
        self.assertNotIn(credentials.token, repr(self.auth.__dict__))
        self.assertNotIn(credentials.csrf, repr(self.auth.__dict__))
        self.assertIn(hashlib.sha256(credentials.token.encode("ascii")).digest(), self.auth._sessions)
        self.assertEqual({field.name for field in fields(self.auth.audit_events()[0])}, {"code", "user_id", "tenant_id", "time"})
        self.assertNotIn("fixture:alice", repr(self.auth.audit_events()))
        self.assertNotIn("loopback-client-a", repr(self.auth.audit_events()))
        self.assertEqual(self.auth.audit_events()[0].user_id, "user-a")

    def test_expiration_exact_boundary_and_replay(self):
        credentials = self.login()
        self.assertEqual(self.auth.authenticated(credentials.token, credentials.expires_at - timedelta(microseconds=1)), credentials.principal)
        self.assert_code("SESSION_REJECTED", self.auth.authenticated, credentials.token, credentials.expires_at)
        self.assert_code("SESSION_REJECTED", self.auth.authenticated, credentials.token, self.now)

    def test_logout_revocation_replay_and_other_session_survives(self):
        first = self.login()
        second = self.login()
        self.auth.logout(first.token, self.now)
        self.assert_code("SESSION_REJECTED", self.auth.authenticated, first.token, self.now)
        self.assert_code("SESSION_REJECTED", self.auth.revoke, first.token, self.now)
        self.assertEqual(self.auth.authenticated(second.token, self.now), second.principal)
        self.auth.revoke(second.token, self.now)
        self.assert_code("SESSION_REJECTED", self.auth.require_csrf, second.token, second.csrf, self.now)

    def test_tampering_missing_tokens_and_preissue_time(self):
        credentials = self.login()
        for value in (None, "", "unrecognized", credentials.token + "x", "한글", "x" * 257):
            self.assert_code("SESSION_REJECTED", self.auth.authenticated, value, self.now)
        self.assert_code("SESSION_REJECTED", self.auth.authenticated, credentials.token, self.now - timedelta(microseconds=1))

    def test_csrf_is_session_bound_and_required(self):
        first = self.login()
        second = self.login()
        self.assertEqual(self.auth.require_csrf(first.token, first.csrf, self.now), first.principal)
        for csrf in (None, "", "wrong", second.csrf):
            self.assert_code("CSRF_REJECTED", self.auth.require_csrf, first.token, csrf, self.now)
        self.assertEqual(self.auth.authenticated(first.token, self.now), first.principal)

    def test_fixture_identity_only_and_configuration_copied(self):
        self.assertTrue(self.provider.synthetic_only)
        self.assertTrue(self.auth.synthetic_only)
        self.assert_code("LOGIN_REJECTED", self.login, "actual-provider-token")
        self.assert_code("LOGIN_REJECTED", self.login, "fixture:missing")
        for mapping in ({"alice": ("user-a", "tenant-a")}, {"fixture:alice": ("", "tenant-a")}, {"fixture:alice": ("user-a",)}):
            with self.assertRaises(ValueError):
                SyntheticIdentityProvider(mapping)
        mutable = {"fixture:alice": ("user-a", "tenant-a")}
        provider = SyntheticIdentityProvider(mutable)
        mutable["fixture:alice"] = ("attacker", "other-tenant")
        self.assertEqual(provider.verify_identity("fixture:alice", self.now), ("user-a", "tenant-a"))

    def test_rate_limiter_counts_failed_and_successful_attempts_and_window(self):
        self.assert_code("LOGIN_REJECTED", self.login, "fixture:missing")
        self.login()
        self.login()
        self.assert_code("LOGIN_RATE_LIMITED", self.login)
        self.login(key="loopback-client-b")
        # The boundary is [now - window, now): an attempt exactly one window old expires.
        self.login(now=self.now + timedelta(minutes=1))

    def test_backward_clock_rejected_and_naive_time_rejected(self):
        self.login()
        self.assert_code("INVALID_TIME", self.login, now=self.now - timedelta(seconds=1))
        self.assert_code("INVALID_TIME", self.login, now=datetime(2026, 10, 5))
        credentials = self.login()
        self.assert_code("INVALID_TIME", self.auth.authenticated, credentials.token, datetime(2026, 10, 5))

    def test_invalid_rate_key_is_public_safe(self):
        for key in (None, "", "x" * 1025, "\ud800"):
            self.assert_code("LOGIN_REJECTED", self.login, key=key)

    def test_concurrent_revoke_has_one_success_and_replay_is_rejected(self):
        credentials = self.login()
        def revoke(_):
            try:
                self.auth.revoke(credentials.token, self.now)
                return "REVOKED"
            except PlatformError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=4) as workers:
            results = list(workers.map(revoke, range(4)))
        self.assertEqual(results.count("REVOKED"), 1)
        self.assertEqual(results.count("SESSION_REJECTED"), 3)

    def test_configuration_is_explicit_and_positive(self):
        with self.assertRaises(TypeError):
            SessionAuth(self.provider)
        for changes in ({"ttl": timedelta(0)}, {"rate_window": timedelta(0)}, {"max_attempts": 0}, {"max_attempts": True}, {"max_attempts": 1.5}):
            configuration = dict(ttl=timedelta(minutes=5), max_attempts=3, rate_window=timedelta(minutes=1))
            configuration.update(changes)
            with self.assertRaises(ValueError):
                SessionAuth(self.provider, **configuration)

    def test_provider_errors_and_invalid_identity_never_escape(self):
        class BrokenProvider:
            def verify_identity(self, identity_reference, now):
                raise RuntimeError("secret-provider-token-do-not-log")
        auth = SessionAuth(BrokenProvider(), ttl=timedelta(minutes=5), max_attempts=3, rate_window=timedelta(minutes=1))
        self.assert_code("LOGIN_REJECTED", auth.login, "secret-identity", attempt_key="client-a", now=self.now)
        self.assertNotIn("secret", repr(auth.audit_events()))
        class InvalidProvider:
            def verify_identity(self, identity_reference, now):
                return ("user-a",)
        auth = SessionAuth(InvalidProvider(), ttl=timedelta(minutes=5), max_attempts=3, rate_window=timedelta(minutes=1))
        self.assert_code("LOGIN_REJECTED", auth.login, "fixture:any", attempt_key="client-a", now=self.now)

    def test_concurrent_login_rate_limit_is_atomic(self):
        def attempt(_):
            try:
                return self.login()
            except PlatformError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=10) as workers:
            results = list(workers.map(attempt, range(10)))
        sessions = [result for result in results if not isinstance(result, str)]
        self.assertEqual(len(sessions), 3)
        self.assertEqual(results.count("LOGIN_RATE_LIMITED"), 7)
        self.assertEqual(len({session.token for session in sessions}), 3)
        self.assertEqual(len(self.auth._sessions), 3)


if __name__ == "__main__":
    unittest.main()
