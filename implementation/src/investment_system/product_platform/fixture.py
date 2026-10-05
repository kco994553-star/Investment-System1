"""Deterministic synthetic records; never live accounts or market data."""
from datetime import date, datetime

from investment_system.contracts.global_universe import IssuerIdentity, ListingIdentity, SecurityIdentity

from .connector import SyntheticConnector
from .domain import PlatformError, ReadPage, aware, decimal_text, json_text


def synthetic_identities() -> tuple[IssuerIdentity, SecurityIdentity, ListingIdentity]:
    return (
        IssuerIdentity("synthetic-issuer-1", "SYNTHETIC DEMO ISSUER", "US"),
        SecurityIdentity("synthetic-security-1", "synthetic-issuer-1", "SYNTHETIC_DEMO_EQUITY", "SYNTHETIC"),
        ListingIdentity("synthetic-listing-1", "synthetic-security-1", "SYNTHETIC", "SYNTHETIC", "USD", date(2000, 1, 1)),
    )


def synthetic_connector(now: datetime, account_id: str = "acct-1", amount: str = "1000.00") -> SyntheticConnector:
    """Reported amount is customizable; no reconciliation values are derived."""
    stamp = aware(now).isoformat()
    decimal_text(amount)
    if not isinstance(account_id, str) or not account_id.strip():
        raise PlatformError("ACCOUNT_ID_REJECTED")
    times = {"effective_at": stamp, "available_at": stamp, "provider_reported_at": stamp}

    def record(record_id, **fields):
        return {"id": record_id, "revision": 1, **times, **fields}

    records = {
        "accounts": [record(account_id, currency="USD", status="OPEN")],
        "balances": [record("bal-1", account_id=account_id, cash="250.00", total=amount, currency="USD")],
        "positions": [record("pos-1", account_id=account_id, quantity="5.000", market_value="750.00", currency="USD",
                             security_id="synthetic-security-1", listing_id="synthetic-listing-1")],
        "transactions": [record("txn-1", account_id=account_id, kind="BUY", amount="-750.00", currency="USD")],
        "statements": [],
    }
    pages = {}
    for resource, resource_records in records.items():
        envelope = {"schema_version": "synthetic-financial-v1", "data_state": "DEMO", **times, "records": resource_records}
        pages[resource] = {None: ReadPage(resource, json_text(envelope).encode("utf-8"))}
    return SyntheticConnector(pages)
