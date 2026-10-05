"""Run the explicitly synthetic loopback audit harness; no deployment."""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def main():
    from investment_system.product_platform.api import PlatformAPI
    from investment_system.product_platform.auth import SessionAuth, SyntheticIdentityProvider
    from investment_system.product_platform.fixture import synthetic_connector, synthetic_identities
    from investment_system.product_platform.service import PlatformService
    from investment_system.product_platform.store import ScopedStore
    from investment_system.product_platform.web import create_server

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0, help="Loopback port; 0 chooses an available port")
    parser.add_argument("--db", required=True, help="Local synthetic SQLite path outside the repository")
    args = parser.parse_args()
    database = Path(args.db).resolve()
    if ROOT.parent == database or ROOT.parent in database.parents:
        parser.error("synthetic database must be outside the repository")
    database.parent.mkdir(parents=True, exist_ok=True)
    store = ScopedStore(str(database))
    # Explicit audit-only limits. These do not establish production defaults.
    identities = tuple((identity,) for identity in synthetic_identities())
    service = PlatformService(store, identities, max_payload_bytes=100000, max_pages=10)
    auth = SessionAuth(SyntheticIdentityProvider({"fixture:alice": ("alice", "tenant-a"),
                                                "fixture:bob": ("bob", "tenant-b")}),
                       ttl=timedelta(minutes=30), max_attempts=20, rate_window=timedelta(minutes=1))
    clock = lambda: datetime.now(timezone.utc)
    api = PlatformAPI(service, auth, clock, synthetic_connector)
    server = create_server(api, port=args.port, max_body_bytes=16384, request_timeout=5)
    print(f"SYNTHETIC / DEMO loopback audit harness: {server.origin}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        store.close()


if __name__ == "__main__":
    main()
