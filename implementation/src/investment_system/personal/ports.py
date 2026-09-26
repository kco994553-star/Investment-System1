"""Ports (interfaces) between PIL and the rest of the system / brokers. Boundaries only: nothing here is bound to the
existing QGV / Technical / Macro / Portfolio code (integration waits for the upstream contracts or the Main Track freeze).

Open upstream contracts (not solved here, see Contract Conflict Register):
- C-28 Technical output has no available_at: TechnicalContextPort must return available_at; None -> UNRESOLVED (PIL never
  derives it from as_of).
- C-29 no QGV<->Technical scale contract: scores cross this boundary with their scale metadata and are never converted.
- C-30 Official weight dataset: OfficialWeightRegistryPort supplies maturity/weights from the authoritative SSoT only.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Protocol, runtime_checkable

from .quality import DataQuality
from .weights import OfficialRegistry


@dataclass(frozen=True)
class ScoreValue:
    """An upstream score passed through unchanged, with its scale (e.g. '0-100'). No cross-scale arithmetic (C-29)."""

    value: Optional[float]
    scale: str
    source_system: str
    snapshot_ref: str
    available_at: Optional[datetime]
    quality: DataQuality


@dataclass(frozen=True)
class UpstreamContext:
    snapshot_ref: str
    system: str
    as_of: datetime
    available_at: Optional[datetime]  # None -> the context is UNRESOLVED for PIT use
    scores: tuple[ScoreValue, ...]
    labels: tuple[tuple[str, str], ...]  # categorical outputs, e.g. ("regime", "TREND_UP")
    quality: DataQuality


@runtime_checkable
class QGVContextPort(Protocol):
    def context(self, security_id: str, decision_time: datetime) -> Optional[UpstreamContext]: ...


@runtime_checkable
class TechnicalContextPort(Protocol):
    def context(self, security_id: str, decision_time: datetime) -> Optional[UpstreamContext]: ...


@runtime_checkable
class MacroContextPort(Protocol):
    def context(self, decision_time: datetime) -> Optional[UpstreamContext]: ...


@runtime_checkable
class OfficialWeightRegistryPort(Protocol):
    def registry(self, registry_version: str) -> OfficialRegistry: ...


def pit_quality(ctx: Optional[UpstreamContext], decision_time: datetime) -> DataQuality:
    """Quality of an upstream context for use at decision_time: missing context or available_at -> UNRESOLVED;
    available_at after decision_time -> INVALID (look-ahead); otherwise the context's own quality."""
    if ctx is None or ctx.available_at is None:
        return DataQuality.UNRESOLVED
    if ctx.available_at > decision_time:
        return DataQuality.INVALID
    return ctx.quality


class BrokerCapability(str, Enum):
    ACCOUNTS = "ACCOUNTS"
    POSITIONS = "POSITIONS"
    CASH = "CASH"
    TRANSACTIONS = "TRANSACTIONS"
    ORDERS_READ = "ORDERS_READ"
    REALTIME_POSITIONS = "REALTIME_POSITIONS"
    COST_BASIS = "COST_BASIS"
    REALIZED_PNL = "REALIZED_PNL"
    UNREALIZED_PNL = "UNREALIZED_PNL"


class Unsupported(Exception):
    """Raised by an adapter for a capability it does not offer (never emulated)."""


@dataclass(frozen=True)
class SyncStatus:
    last_success_at: Optional[datetime]
    quality: DataQuality
    detail: str = ""


@runtime_checkable
class BrokerAdapter(Protocol):
    """READ-ONLY v1. Broker-specific auth/API differences stay inside the adapter. Deliberately no order placement,
    cancellation, transfer or withdrawal methods (out of scope for v1). Credentials never leave the adapter."""

    def connect(self) -> None: ...
    def refresh_auth(self) -> None: ...
    def disconnect(self) -> None: ...
    def get_capabilities(self) -> frozenset[BrokerCapability]: ...
    def get_accounts(self) -> list[dict]: ...
    def get_balances(self, account_id: str) -> list[dict]: ...
    def get_positions(self, account_id: str) -> list[dict]: ...
    def get_transactions(self, account_id: str, since: datetime) -> list[dict]: ...
    def get_orders(self, account_id: str, since: datetime) -> list[dict]: ...
    def get_sync_status(self) -> SyncStatus: ...
    def sync(self) -> SyncStatus: ...


FORBIDDEN_BROKER_METHODS = ("place_order", "submit_order", "cancel_order", "modify_order", "transfer", "withdraw")
