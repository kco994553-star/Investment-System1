"""Trusted identity adapters and opaque, server-side sessions.

The supplied synthetic provider is a local test fixture, never production
authentication. A production provider must validate its own identity evidence;
this module does not implement passwords, identity proof, or a crypto protocol.
The caller supplies trusted server time and a server-derived rate-limit key.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import secrets
import threading
from types import MappingProxyType
from typing import Mapping, Protocol

from .domain import PlatformError, Principal, aware


class IdentityProvider(Protocol):
    """Boundary for an independently trusted identity verification adapter."""

    def verify_identity(self, identity_reference: str, now: datetime) -> tuple[str, str]:
        """Return trusted (user_id, tenant_id), or reject identity evidence."""
        ...


def _valid_identity(value):
    return (
        isinstance(value, str)
        and 0 < len(value) <= 200
        and all(ord(character) >= 32 and ord(character) != 127 for character in value)
    )


class SyntheticIdentityProvider:
    """TEST ONLY: fixture IDs resolve identities without authenticating a person.

    Only explicitly registered ``fixture:`` references are accepted. No password,
    token, credential, network request, or fallback authentication is supported.
    """

    synthetic_only = True

    def __init__(self, identities: Mapping[str, tuple[str, str]]):
        fixtures = dict(identities)
        for fixture_id, identity in fixtures.items():
            if (
                not isinstance(fixture_id, str)
                or not fixture_id.startswith("fixture:")
                or len(fixture_id) <= len("fixture:")
                or len(fixture_id) > 200
                or not isinstance(identity, tuple)
                or len(identity) != 2
                or not all(_valid_identity(value) for value in identity)
            ):
                raise ValueError("INVALID_SYNTHETIC_IDENTITY_CONFIGURATION")
        self._identities = MappingProxyType(fixtures)

    def verify_identity(self, identity_reference: str, now: datetime) -> tuple[str, str]:
        aware(now)
        if not isinstance(identity_reference, str):
            raise PlatformError("LOGIN_REJECTED")
        identity = self._identities.get(identity_reference)
        if identity is None:
            raise PlatformError("LOGIN_REJECTED")
        return identity


@dataclass(frozen=True)
class SessionCredentials:
    """One-time login response. Secrets must go only to the requesting client."""

    token: str = field(repr=False)
    csrf: str = field(repr=False)
    principal: Principal
    expires_at: datetime


@dataclass(frozen=True)
class AuthAuditEvent:
    """Audit metadata deliberately excludes identity evidence and secrets."""

    code: str
    user_id: str | None
    tenant_id: str | None
    time: datetime


@dataclass(frozen=True)
class _Session:
    principal: Principal
    csrf_digest: bytes = field(repr=False)
    issued_at: datetime
    expires_at: datetime


class SessionAuth:
    """In-memory session abstraction with explicit test/runtime configuration.

    TTL and rate-limit settings have no default values. Every login attempt,
    successful or rejected, consumes a slot for the trusted caller's attempt_key
    within a rolling window. A production runtime additionally needs its own
    durable session backend and independently approved identity provider.
    """

    def __init__(
        self,
        provider: IdentityProvider,
        *,
        ttl: timedelta,
        max_attempts: int,
        rate_window: timedelta,
    ):
        if (
            not isinstance(ttl, timedelta)
            or ttl <= timedelta(0)
            or type(max_attempts) is not int
            or max_attempts <= 0
            or not isinstance(rate_window, timedelta)
            or rate_window <= timedelta(0)
            or not callable(getattr(provider, "verify_identity", None))
        ):
            raise ValueError("INVALID_AUTH_CONFIGURATION")
        self._provider = provider
        self._ttl = ttl
        self._max_attempts = max_attempts
        self._rate_window = rate_window
        self._sessions: dict[bytes, _Session] = {}
        self._attempts: dict[bytes, deque[datetime]] = {}
        self._attempt_times: dict[bytes, datetime] = {}
        self._events: list[AuthAuditEvent] = []
        self._lock = threading.RLock()
        self.synthetic_only = bool(getattr(provider, "synthetic_only", False))

    @staticmethod
    def _digest(secret):
        if not isinstance(secret, str) or not 0 < len(secret) <= 256:
            raise PlatformError("SESSION_REJECTED")
        try:
            return hashlib.sha256(secret.encode("ascii")).digest()
        except UnicodeError:
            raise PlatformError("SESSION_REJECTED") from None

    def _record(self, code, now, principal=None):
        self._events.append(
            AuthAuditEvent(
                code,
                principal.user_id if principal else None,
                principal.tenant_id if principal else None,
                now,
            )
        )

    def _rate_limit(self, attempt_key, now):
        if not isinstance(attempt_key, str) or not 0 < len(attempt_key) <= 1024:
            raise PlatformError("LOGIN_REJECTED")
        try:
            key = hashlib.sha256(attempt_key.encode("utf-8")).digest()
            cutoff = now - self._rate_window
        except (UnicodeError, OverflowError):
            raise PlatformError("LOGIN_REJECTED") from None
        prior_time = self._attempt_times.get(key)
        if prior_time is not None and now < prior_time:
            raise PlatformError("INVALID_TIME")
        # Discard stale keys as well as old attempts; raw keys are never retained.
        for known_key, attempts in tuple(self._attempts.items()):
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if not attempts:
                del self._attempts[known_key]
                self._attempt_times.pop(known_key, None)
        attempts = self._attempts.setdefault(key, deque())
        self._attempt_times[key] = now
        if len(attempts) >= self._max_attempts:
            raise PlatformError("LOGIN_RATE_LIMITED")
        attempts.append(now)

    def login(self, identity_reference: str, *, attempt_key: str, now: datetime) -> SessionCredentials:
        now = aware(now)
        with self._lock:
            try:
                self._rate_limit(attempt_key, now)
            except PlatformError as error:
                self._record(error.code, now)
                raise
            try:
                identity = self._provider.verify_identity(identity_reference, now)
                if not isinstance(identity, tuple) or len(identity) != 2 or not all(_valid_identity(value) for value in identity):
                    raise PlatformError("LOGIN_REJECTED")
                expires_at = now + self._ttl
            except Exception:
                self._record("LOGIN_REJECTED", now)
                raise PlatformError("LOGIN_REJECTED") from None
            token = secrets.token_urlsafe(32)
            token_digest = self._digest(token)
            while token_digest in self._sessions:
                token = secrets.token_urlsafe(32)
                token_digest = self._digest(token)
            csrf = secrets.token_urlsafe(32)
            principal = Principal(identity[0], identity[1], secrets.token_urlsafe(24))
            self._sessions[token_digest] = _Session(principal, self._digest(csrf), now, expires_at)
            self._record("LOGIN_SUCCEEDED", now, principal)
            return SessionCredentials(token, csrf, principal, expires_at)

    def _authenticated(self, token, now):
        try:
            token_digest = self._digest(token)
        except PlatformError:
            self._record("SESSION_REJECTED", now)
            raise
        session = self._sessions.get(token_digest)
        if session is None or now < session.issued_at or now >= session.expires_at:
            if session is not None and now >= session.expires_at:
                del self._sessions[token_digest]
            self._record("SESSION_REJECTED", now)
            raise PlatformError("SESSION_REJECTED")
        return token_digest, session

    def authenticated(self, token: str, now: datetime) -> Principal:
        now = aware(now)
        with self._lock:
            return self._authenticated(token, now)[1].principal

    def require_csrf(self, token: str, csrf: str, now: datetime) -> Principal:
        now = aware(now)
        with self._lock:
            _, session = self._authenticated(token, now)
            try:
                csrf_digest = self._digest(csrf)
            except PlatformError:
                self._record("CSRF_REJECTED", now, session.principal)
                raise PlatformError("CSRF_REJECTED") from None
            if not secrets.compare_digest(csrf_digest, session.csrf_digest):
                self._record("CSRF_REJECTED", now, session.principal)
                raise PlatformError("CSRF_REJECTED")
            return session.principal

    def revoke(self, token: str, now: datetime) -> None:
        now = aware(now)
        with self._lock:
            token_digest, session = self._authenticated(token, now)
            del self._sessions[token_digest]
            self._record("SESSION_REVOKED", now, session.principal)

    def logout(self, token: str, now: datetime) -> None:
        self.revoke(token, now)

    def audit_events(self) -> tuple[AuthAuditEvent, ...]:
        with self._lock:
            return tuple(self._events)
