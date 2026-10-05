"""Provider-neutral read boundary and a deterministic, credential-free fixture.

The legacy BrokerAdapter bridge is an adapter candidate: its native dictionaries
have no approved financial schema or PIT provenance, so they cannot be admitted
to platform sync.  It never invents those missing fields.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Protocol, runtime_checkable

from investment_system.personal.ports import BrokerAdapter, BrokerCapability, FORBIDDEN_BROKER_METHODS

from .domain import PlatformError, READ_CAPABILITIES, RESOURCES, ReadPage, require_read_only


RESOURCE_CAPABILITY = {
    "accounts": "READ_ACCOUNT",
    "balances": "READ_BALANCE",
    "positions": "READ_POSITION",
    "transactions": "READ_TRANSACTION",
    "statements": "READ_STATEMENT",
}


@runtime_checkable
class FinancialConnector(Protocol):
    provider_id: str
    synthetic: bool

    def capabilities(self) -> Iterable[str]: ...
    def connection_status(self) -> str: ...
    def list_accounts(self, cursor: str | None = None) -> ReadPage: ...
    def sync_balances(self, cursor: str | None = None) -> ReadPage: ...
    def sync_positions(self, cursor: str | None = None) -> ReadPage: ...
    def sync_transactions(self, cursor: str | None = None) -> ReadPage: ...
    def sync_statements(self, cursor: str | None = None) -> ReadPage: ...
    def revoke_connection(self) -> None: ...


class SyntheticConnector:
    """Explicit DEMO fixture. Mutable overrides support adversarial sync tests.

    ``pages[resource][cursor]`` returns a page without rewriting its raw bytes.
    ``failures[resource]`` may be PERMISSION_DENIED or PROVIDER_UNAVAILABLE.
    A partial response is represented by ReadPage(..., complete=False).
    """

    synthetic = True

    def __init__(
        self,
        pages: Mapping[str, Mapping[str | None, ReadPage]],
        *,
        provider_id: str = "synthetic-financial",
        capabilities: Iterable[str] = READ_CAPABILITIES,
        failures: Mapping[str, str] | None = None,
    ):
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise PlatformError("PROVIDER_ID_REJECTED")
        if not set(pages) <= RESOURCES:
            raise PlatformError("RESOURCE_REJECTED")
        self.provider_id = provider_id
        self.pages = {resource: dict(resource_pages) for resource, resource_pages in pages.items()}
        self.failures = dict(failures or {})
        self._capabilities = require_read_only(capabilities)
        self._status = "ACTIVE"

    def capabilities(self) -> frozenset[str]:
        return require_read_only(self._capabilities)

    def connection_status(self) -> str:
        return self._status

    def _read(self, resource: str, cursor: str | None) -> ReadPage:
        if self._status != "ACTIVE":
            raise PlatformError("CONNECTION_REVOKED")
        if RESOURCE_CAPABILITY[resource] not in self.capabilities():
            raise PlatformError("PERMISSION_DENIED")
        if cursor is not None and (not isinstance(cursor, str) or not cursor):
            raise PlatformError("CURSOR_REJECTED")
        if resource in self.failures:
            code = self.failures[resource]
            if code not in {"PERMISSION_DENIED", "PROVIDER_UNAVAILABLE"}:
                code = "PROVIDER_UNAVAILABLE"
            raise PlatformError(code)
        try:
            page = self.pages[resource][cursor]
        except (KeyError, TypeError):
            raise PlatformError("CURSOR_REJECTED") from None
        if not isinstance(page, ReadPage) or page.resource != resource:
            raise PlatformError("PAGE_REJECTED")
        return page

    def list_accounts(self, cursor: str | None = None) -> ReadPage:
        return self._read("accounts", cursor)

    def sync_balances(self, cursor: str | None = None) -> ReadPage:
        return self._read("balances", cursor)

    def sync_positions(self, cursor: str | None = None) -> ReadPage:
        return self._read("positions", cursor)

    def sync_transactions(self, cursor: str | None = None) -> ReadPage:
        return self._read("transactions", cursor)

    def sync_statements(self, cursor: str | None = None) -> ReadPage:
        return self._read("statements", cursor)

    def revoke_connection(self) -> None:
        self._status = "REVOKED"


_BROKER_CAPABILITY_MAP = {
    BrokerCapability.ACCOUNTS: "READ_ACCOUNT",
    BrokerCapability.CASH: "READ_BALANCE",
    BrokerCapability.POSITIONS: "READ_POSITION",
    BrokerCapability.REALTIME_POSITIONS: "READ_POSITION",
    BrokerCapability.TRANSACTIONS: "READ_TRANSACTION",
}

_FORBIDDEN_ADAPTER_METHODS = frozenset(FORBIDDEN_BROKER_METHODS) | {
    "buy", "sell", "trade", "create_order", "execute_order", "replace_order",
    "transfer_funds", "withdraw_funds", "deposit_funds",
}


class ReadOnlyBrokerBridge:
    """Validated adapter candidate, deliberately unavailable for platform sync.

    Existing read-only capabilities such as ORDERS_READ, COST_BASIS and PNL are
    known but have no equivalent platform resource. They are not reinterpreted
    as transactions, balance, or positions. Unknown capabilities are rejected.
    No connect/refresh_auth/sync operation is invoked by this bridge.
    """

    synthetic = False
    adapter_state = "ADAPTER_CANDIDATE"
    normalization_ready = False

    def __init__(self, adapter: BrokerAdapter, *, provider_id: str):
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise PlatformError("PROVIDER_ID_REJECTED")
        self.provider_id = provider_id
        self._adapter = adapter
        self._status = "ACTIVE"
        self.capabilities()

    def capabilities(self) -> frozenset[str]:
        # Recheck every read: an adapter's capabilities can change after login.
        try:
            for name in _FORBIDDEN_ADAPTER_METHODS:
                if callable(getattr(self._adapter, name, None)):
                    raise PlatformError("CAPABILITY_REJECTED")
            supplied = frozenset(self._adapter.get_capabilities())
        except Exception:
            raise PlatformError("CAPABILITY_REJECTED") from None
        if any(not isinstance(value, BrokerCapability) for value in supplied):
            raise PlatformError("CAPABILITY_REJECTED")
        mapped = {_BROKER_CAPABILITY_MAP[value] for value in supplied if value in _BROKER_CAPABILITY_MAP}
        return require_read_only(mapped)

    def connection_status(self) -> str:
        return self._status

    def _unavailable(self, resource: str) -> ReadPage:
        if self._status != "ACTIVE":
            raise PlatformError("CONNECTION_REVOKED")
        if RESOURCE_CAPABILITY[resource] not in self.capabilities():
            raise PlatformError("PERMISSION_DENIED")
        raise PlatformError("PROVIDER_SCHEMA_UNAVAILABLE")

    def list_accounts(self, cursor: str | None = None) -> ReadPage:
        return self._unavailable("accounts")

    def sync_balances(self, cursor: str | None = None) -> ReadPage:
        return self._unavailable("balances")

    def sync_positions(self, cursor: str | None = None) -> ReadPage:
        return self._unavailable("positions")

    def sync_transactions(self, cursor: str | None = None) -> ReadPage:
        return self._unavailable("transactions")

    def sync_statements(self, cursor: str | None = None) -> ReadPage:
        return self._unavailable("statements")

    def revoke_connection(self) -> None:
        # This is local revocation. A provider revoke contract has not been
        # supplied, so disconnect is not represented as credential revocation.
        self._status = "REVOKED"
