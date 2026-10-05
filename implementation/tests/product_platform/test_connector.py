"""Connector boundaries and failure fixtures: no credentials or live calls."""
from datetime import datetime, timezone
import json
import unittest

from investment_system.contracts.global_universe import IssuerIdentity, ListingIdentity, SecurityIdentity
from investment_system.personal.ports import BrokerCapability
from investment_system.product_platform.connector import FinancialConnector, ReadOnlyBrokerBridge, SyntheticConnector
from investment_system.product_platform.domain import PlatformError, READ_CAPABILITIES, ReadPage
from investment_system.product_platform.fixture import synthetic_connector, synthetic_identities


NOW = datetime(2026, 10, 5, 3, 48, 10, tzinfo=timezone.utc)


class FakeBroker:
    def __init__(self, capabilities=None):
        self.values = capabilities if capabilities is not None else frozenset(BrokerCapability)
        self.calls = []

    def get_capabilities(self):
        self.calls.append("get_capabilities")
        return self.values

    def connect(self):
        self.calls.append("connect")

    def get_accounts(self):
        self.calls.append("get_accounts")
        return [{"id": "provider-account"}]

    def disconnect(self):
        self.calls.append("disconnect")


class ConnectorTests(unittest.TestCase):
    def assertCode(self, code, call):
        with self.assertRaises(PlatformError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), code)

    def test_fixture_is_deterministic_synthetic_and_complete(self):
        a, b = synthetic_connector(NOW), synthetic_connector(NOW)
        self.assertIsInstance(a, FinancialConnector)
        self.assertTrue(a.synthetic)
        self.assertEqual(a.connection_status(), "ACTIVE")
        self.assertEqual(a.capabilities(), READ_CAPABILITIES)
        methods = {"accounts": "list_accounts", "balances": "sync_balances", "positions": "sync_positions",
                   "transactions": "sync_transactions", "statements": "sync_statements"}
        for resource, method in methods.items():
            page = getattr(a, method)()
            self.assertEqual(page, getattr(b, method)())
            self.assertEqual(page.resource, resource)
            self.assertIsNone(page.next_cursor)
            self.assertTrue(page.complete)
            envelope = json.loads(page.body)
            self.assertEqual(envelope["schema_version"], "synthetic-financial-v1")
            self.assertEqual(envelope["data_state"], "DEMO")
            for field in ("effective_at", "available_at", "provider_reported_at"):
                self.assertEqual(envelope[field], NOW.isoformat())
                for record in envelope["records"]:
                    self.assertEqual(record[field], NOW.isoformat())
                    self.assertEqual(record["revision"], 1)
        balances = json.loads(a.sync_balances().body)["records"][0]
        positions = json.loads(a.sync_positions().body)["records"][0]
        self.assertEqual((balances["cash"], balances["total"], positions["market_value"], positions["quantity"]),
                         ("250.00", "1000.00", "750.00", "5.000"))
        self.assertEqual(json.loads(a.sync_transactions().body)["records"][0]["kind"], "BUY")
        self.assertEqual(json.loads(a.sync_statements().body)["records"], [])

    def test_fixture_custom_amount_preserves_reported_value_without_recalculation(self):
        connector = synthetic_connector(NOW, "acct-custom", "999.1234")
        balances = json.loads(connector.sync_balances().body)["records"][0]
        self.assertEqual(balances["account_id"], "acct-custom")
        self.assertEqual(balances["total"], "999.1234")
        self.assertEqual(balances["cash"], "250.00")
        self.assertCode("INVALID_NUMBER", lambda: synthetic_connector(NOW, amount=1000.0))
        self.assertCode("INVALID_TIME", lambda: synthetic_connector(datetime(2026, 10, 5)))

    def test_existing_global_identity_types_and_explicit_synthetic_labels(self):
        issuer, security, listing = synthetic_identities()
        self.assertIsInstance(issuer, IssuerIdentity)
        self.assertIsInstance(security, SecurityIdentity)
        self.assertIsInstance(listing, ListingIdentity)
        self.assertEqual(security.issuer_id, issuer.issuer_id)
        self.assertEqual(listing.security_id, security.security_id)
        self.assertEqual((security.security_id, listing.listing_id), ("synthetic-security-1", "synthetic-listing-1"))
        self.assertIn("SYNTHETIC", issuer.legal_name)
        self.assertIn("SYNTHETIC", security.security_type)
        self.assertIn("SYNTHETIC", listing.ticker)

    def test_pagination_returns_exact_bytes_and_partial_page(self):
        first = ReadPage("accounts", b'{"provider":"unchanged"}', "opaque-next", False)
        last = ReadPage("accounts", b'{"provider":"last"}')
        connector = SyntheticConnector({"accounts": {None: first, "opaque-next": last}}, capabilities={"READ_ACCOUNT"})
        self.assertIs(connector.list_accounts(), first)
        self.assertIs(connector.list_accounts("opaque-next"), last)
        self.assertCode("CURSOR_REJECTED", lambda: connector.list_accounts("other-connection-cursor"))
        self.assertCode("CURSOR_REJECTED", lambda: connector.list_accounts(""))

    def test_permission_outage_wrong_resource_and_revocation(self):
        connector = synthetic_connector(NOW)
        connector.failures["positions"] = "PERMISSION_DENIED"
        self.assertCode("PERMISSION_DENIED", connector.sync_positions)
        connector.failures["positions"] = "PROVIDER_UNAVAILABLE"
        self.assertCode("PROVIDER_UNAVAILABLE", connector.sync_positions)
        connector.failures["positions"] = "provider secret credential text"
        self.assertCode("PROVIDER_UNAVAILABLE", connector.sync_positions)
        del connector.failures["positions"]
        connector.pages["positions"][None] = ReadPage("balances", b"{}")
        self.assertCode("PAGE_REJECTED", connector.sync_positions)
        connector.revoke_connection()
        connector.revoke_connection()
        self.assertEqual(connector.connection_status(), "REVOKED")
        self.assertCode("CONNECTION_REVOKED", connector.list_accounts)

    def test_capability_revalidated_and_no_trading_surface(self):
        connector = synthetic_connector(NOW)
        for forbidden in ("place_order", "submit_order", "cancel_order", "transfer", "withdraw", "buy", "sell"):
            self.assertFalse(hasattr(connector, forbidden))
        self.assertCode("CAPABILITY_REJECTED", lambda: SyntheticConnector({}, capabilities={"PLACE_ORDER"}))
        self.assertCode("CAPABILITY_REJECTED", lambda: SyntheticConnector({}, capabilities={"READ_UNKNOWN"}))
        connector._capabilities = {"READ_ACCOUNT", "SUBMIT_ORDER"}
        self.assertCode("CAPABILITY_REJECTED", connector.list_accounts)
        limited = SyntheticConnector({}, capabilities={"READ_ACCOUNT"})
        self.assertCode("PERMISSION_DENIED", limited.sync_balances)

    def test_broker_candidate_maps_only_explicit_equivalents_and_never_fabricates_schema(self):
        broker = FakeBroker()
        bridge = ReadOnlyBrokerBridge(broker, provider_id="provider-candidate")
        self.assertFalse(bridge.synthetic)
        self.assertFalse(bridge.normalization_ready)
        self.assertEqual(bridge.adapter_state, "ADAPTER_CANDIDATE")
        self.assertEqual(bridge.capabilities(), {"READ_ACCOUNT", "READ_BALANCE", "READ_POSITION", "READ_TRANSACTION"})
        self.assertCode("PROVIDER_SCHEMA_UNAVAILABLE", bridge.list_accounts)
        self.assertCode("PERMISSION_DENIED", bridge.sync_statements)
        self.assertEqual(set(broker.calls), {"get_capabilities"})
        bridge.revoke_connection()
        self.assertCode("CONNECTION_REVOKED", bridge.list_accounts)
        self.assertNotIn("disconnect", broker.calls)

    def test_broker_rejects_write_exposure_unknown_and_dynamic_capability_escalation(self):
        broker = FakeBroker({BrokerCapability.ACCOUNTS})
        broker.place_order = lambda: None
        self.assertCode("CAPABILITY_REJECTED", lambda: ReadOnlyBrokerBridge(broker, provider_id="provider-candidate"))
        unknown = FakeBroker({"READ_ACCOUNT"})
        self.assertCode("CAPABILITY_REJECTED", lambda: ReadOnlyBrokerBridge(unknown, provider_id="provider-candidate"))
        broker = FakeBroker({BrokerCapability.ACCOUNTS})
        bridge = ReadOnlyBrokerBridge(broker, provider_id="provider-candidate")
        broker.values = {BrokerCapability.ACCOUNTS, "TRANSFER"}
        self.assertCode("CAPABILITY_REJECTED", bridge.list_accounts)
        known_unmapped = FakeBroker({BrokerCapability.ORDERS_READ})
        self.assertCode("CAPABILITY_REJECTED", lambda: ReadOnlyBrokerBridge(known_unmapped, provider_id="provider-candidate"))

    def test_broker_dynamic_write_alias_and_provider_error_are_sanitized(self):
        broker = FakeBroker({BrokerCapability.ACCOUNTS})
        bridge = ReadOnlyBrokerBridge(broker, provider_id="provider-candidate")
        broker.buy = lambda: None
        self.assertCode("CAPABILITY_REJECTED", bridge.list_accounts)

        class FailingBroker(FakeBroker):
            @property
            def place_order(self):
                raise RuntimeError("SECRET-CREDENTIAL-TEXT")

        self.assertCode("CAPABILITY_REJECTED", lambda: ReadOnlyBrokerBridge(FailingBroker(), provider_id="provider-candidate"))


if __name__ == "__main__":
    unittest.main()
