"""Transport-independent synthetic, read-only Product API audit harness.

All ownership comes from SessionAuth. Client bodies never define principal,
decision time, provider cursor, credential, or financial action parameters.
"""
import json
import re
import threading

from .domain import CONTRACT_VERSION, PlatformError, RESOURCES, aware


_STATUS = {
    "UNAUTHENTICATED": 401, "SESSION_REJECTED": 401, "LOGIN_REJECTED": 401,
    "CSRF_REJECTED": 403, "SYNTHETIC_AUTH_ONLY": 403, "CAPABILITY_REJECTED": 403,
    "MISSING_READ_CAPABILITY": 403, "REAL_CONNECTOR_NOT_AUTHORIZED": 403,
    "PERMISSION_DENIED": 403, "NOT_FOUND": 404, "ROUTE_NOT_FOUND": 404,
    "LOGIN_RATE_LIMITED": 429, "CONNECTION_REVOKED": 409,
    "CONNECTOR_NOT_ATTACHED": 409, "PROVENANCE_FAILED": 409,
    "REVISION_COLLISION": 409, "REVISION_REGRESSION": 409,
    "PROVIDER_UNAVAILABLE": 503, "PROVIDER_FAILURE": 503,
}
_BAD_REQUEST = frozenset({
    "REQUEST_REJECTED", "QUERY_REJECTED", "OWNERSHIP_FIELDS_REJECTED",
    "INVALID_TIME", "INVALID_IDENTIFIER", "INVALID_NUMBER", "INVALID_CURRENCY",
    "INVALID_TRANSACTION_KIND", "SCHEMA_REJECTED", "PAYLOAD_REJECTED",
    "DUPLICATE_KEY", "SECRET_PAYLOAD_REJECTED", "FUTURE_DATA", "CURSOR_REJECTED",
    "CURSOR_LOOP", "PAGE_LIMIT", "DUPLICATE_ACCOUNT", "DUPLICATE_BALANCE",
    "CROSS_ACCOUNT_REFERENCE", "CURRENCY_MISMATCH", "RESOURCE_REJECTED",
    "PROVIDER_ID_REJECTED", "PAGE_REJECTED", "ACCOUNT_ID_REJECTED",
})
_SAFE_CODES = frozenset(_STATUS) | _BAD_REQUEST
_OWNERSHIP = frozenset({"userid", "tenantid", "sessionid", "user", "tenant", "principal"})


def _project_connection(value):
    return {key: value[key] for key in ("id", "provider", "state", "created_at")}


def _project_run(value):
    output = {key: value[key] for key in ("id", "connection_id", "state", "started_at", "completed_at", "error_code")}
    if output["error_code"] is not None and output["error_code"] not in _SAFE_CODES:
        output["error_code"] = "PROVIDER_FAILURE"
    return output


class PlatformAPI:
    """VERIFIED only through synthetic tests, never production authentication."""

    def __init__(self, service, auth, clock, connector_factory):
        if not callable(clock) or not callable(connector_factory):
            raise ValueError("INVALID_API_CONFIGURATION")
        self.service = service
        self.auth = auth
        self.clock = clock
        self.connector_factory = connector_factory
        self._lock = threading.RLock()

    @staticmethod
    def _body(body, allowed=(), required=()):
        value = {} if body is None else body
        if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
            raise PlatformError("REQUEST_REJECTED")
        for key in value:
            canonical = re.sub(r"[^a-z0-9]", "", key.lower())
            if canonical in _OWNERSHIP:
                raise PlatformError("OWNERSHIP_FIELDS_REJECTED")
        if not set(value) <= set(allowed) or not set(required) <= set(value):
            raise PlatformError("REQUEST_REJECTED")
        return value

    @staticmethod
    def _success(data, status=200, *, data_state="DEMO", metadata=None):
        if data_state not in {"DEMO", "STALE", "DELAYED", "NOT_AVAILABLE"}:
            raise ValueError("INVALID_API_DATA_STATE")
        payload = {"data": data, "contract_version": CONTRACT_VERSION, "data_state": data_state, "is_real": False}
        if metadata:
            payload.update(metadata)
        return status, payload

    def _portfolio_metadata(self, principal, cid, portfolio, now):
        connection = self.service.store.connection(principal, cid)
        attempt = portfolio.get("last_sync_attempt")
        if attempt is None:
            attempt = self.service.store.last_run(principal, cid, now)
        return {
            "connection_state": connection["state"],
            "last_sync_attempt": _project_run(attempt) if attempt is not None else None,
            "as_of": portfolio.get("as_of"),
        }

    def request(self, method, path, token=None, csrf=None, body=None, attempt_key="trusted-server"):
        """Return public-safe JSON objects. attempt_key must come from transport."""
        with self._lock:
            try:
                return self._request(method, path, token, csrf, body, attempt_key)
            except PlatformError as error:
                if error.code not in _SAFE_CODES:
                    return 500, {"error": {"code": "INTERNAL_ERROR"}}
                return _STATUS.get(error.code, 400), {"error": {"code": error.code}}
            except Exception:
                return 500, {"error": {"code": "INTERNAL_ERROR"}}

    def _request(self, method, path, token, csrf, body, attempt_key):
        now = aware(self.clock())
        if not isinstance(method, str) or not isinstance(path, str):
            raise PlatformError("REQUEST_REJECTED")
        if "?" in path or "#" in path:
            raise PlatformError("QUERY_REJECTED")
        if method not in {"GET", "POST"} or re.fullmatch(r"/(?:[A-Za-z0-9_-]+/?)+", path) is None or "//" in path or path.endswith("/"):
            raise PlatformError("ROUTE_NOT_FOUND")
        if method == "POST" and path == "/synthetic-login":
            value = self._body(body, {"fixture_id"}, {"fixture_id"})
            if self.auth.synthetic_only is not True:
                raise PlatformError("SYNTHETIC_AUTH_ONLY")
            if not isinstance(value["fixture_id"], str):
                raise PlatformError("REQUEST_REJECTED")
            credentials = self.auth.login(value["fixture_id"], attempt_key=attempt_key, now=now)
            principal = credentials.principal
            return self._success({
                "token": credentials.token, "csrf": credentials.csrf,
                "principal": {"user_id": principal.user_id, "tenant_id": principal.tenant_id, "session_id": principal.session_id},
                "expires_at": credentials.expires_at.isoformat(), "synthetic": True,
                "authentication_state": "LOCAL_TEST_FIXTURE",
            })
        principal = self.auth.authenticated(token, now)
        self._body(body)
        if method == "GET" and path == "/me":
            return self._success({"user_id": principal.user_id, "tenant_id": principal.tenant_id, "session_id": principal.session_id, "synthetic": self.auth.synthetic_only})
        if method == "GET" and path == "/connections":
            return self._success([_project_connection(connection) for connection in self.service.store.connections(principal)])
        if method == "POST" and path == "/connections":
            self.auth.require_csrf(token, csrf, now)
            connector = self.connector_factory(now)
            cid = self.service.create_connection(principal, connector, now)
            return self._success(_project_connection(self.service.store.connection(principal, cid)), 201)
        if method == "POST" and path == "/logout":
            self.auth.require_csrf(token, csrf, now)
            self.auth.logout(token, now)
            return self._success({"logged_out": True})
        match = re.fullmatch(r"/connections/([A-Za-z0-9_-]+)(?:/([A-Za-z0-9_-]+))?", path)
        if match:
            cid, action = match.groups()
            if action is None and method == "GET":
                return self._success(_project_connection(self.service.store.connection(principal, cid)))
            if method == "POST" and action in {"sync", "revoke"}:
                self.auth.require_csrf(token, csrf, now)
                if action == "sync":
                    return self._success(_project_run(self.service.sync(principal, cid, now)))
                self.service.revoke_connection(principal, cid, now)
                return self._success(_project_connection(self.service.store.connection(principal, cid)))
            if method == "GET" and action == "portfolio":
                portfolio = self.service.portfolio(principal, cid, now)
                return self._success(portfolio, data_state=portfolio["data_state"], metadata=self._portfolio_metadata(principal, cid, portfolio, now))
            if method == "GET" and action == "export":
                exported = self.service.export(principal, cid, now)
                portfolio = exported["portfolio"]
                return self._success(exported, data_state=portfolio["data_state"], metadata=self._portfolio_metadata(principal, cid, portfolio, now))
            if method == "GET" and action in RESOURCES:
                self.service.store.connection(principal, cid)
                if action in {"accounts", "balances", "positions"}:
                    portfolio = self.service.portfolio(principal, cid, now)
                    metadata = self._portfolio_metadata(principal, cid, portfolio, now)
                    if portfolio.get("data_state") == "NOT_AVAILABLE":
                        metadata["reason"] = portfolio.get("reason", "NO_COMPLETE_SYNC")
                    return self._success(portfolio.get(action, []), data_state=portfolio["data_state"], metadata=metadata)
                rows = self.service.store.records(principal, cid, action, now)
                return self._success([json.loads(row["payload"]) | {"receipt_id": row["receipt_id"]} for row in rows])
        match = re.fullmatch(r"/sync/([A-Za-z0-9_-]+)", path)
        if method == "GET" and match:
            return self._success(_project_run(self.service.store.run(principal, match[1])))
        match = re.fullmatch(r"/raw/([A-Za-z0-9_-]+)", path)
        if method == "GET" and match:
            receipt = self.service.store.receipt(principal, match[1])
            metadata = {key: receipt[key] for key in ("id", "connection_id", "resource", "sha256", "fetched_at")}
            metadata["byte_length"] = len(receipt["body"])
            return self._success(metadata)
        raise PlatformError("ROUTE_NOT_FOUND")
