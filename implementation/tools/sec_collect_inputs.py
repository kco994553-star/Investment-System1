"""Explicit US17 SEC collection entrypoint; scheduling belongs to Codex1.

Only SEC_USER_AGENT's setting name is accepted. No credential value CLI flag,
price path, deployment, workflow, or public export is provided.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from investment_system.markets.us import US_LISTINGS
from investment_system.providers.sec_collection import SecCollectionClient, SEC_USER_AGENT_SLOT
from sec_m1_inputs import _companies, _timestamp, run_batch


class _ValueFreeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's usual error includes unrecognized arguments and their
        # values. A mistaken credential flag must never echo its value.
        super().error('SEC_COLLECTION_CONFIGURATION_ERROR; use --help and SEC_USER_AGENT')


def main(argv=None, *, environ=None, client_factory=None) -> int:
    parser = _ValueFreeParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument('--companies', help='Comma-separated approved US17 company IDs')
    scope.add_argument('--all-us17', action='store_true')
    parser.add_argument('--store', required=True, type=Path, help='Local raw financial input store; never Pages')
    parser.add_argument('--live', action='store_true', help='Explicitly enable SEC requests')
    parser.add_argument('--as-of', type=_timestamp)
    parser.add_argument('--form-filter', choices=('10-K', '10-Q'), default='10-K')
    args = parser.parse_args(argv)
    if not args.live:
        parser.error('Explicit --live is required; offline import uses sec_m1_inputs.py')
    try:
        companies = _companies(list(US_LISTINGS) if args.all_us17 else args.companies.split(','))
        settings = os.environ if environ is None else environ
        user_agent = settings.get(SEC_USER_AGENT_SLOT)
        client = (SecCollectionClient if client_factory is None else client_factory)(user_agent)
        report = run_batch(args.store, companies, client.collect, as_of=args.as_of, form_filter=args.form_filter)
    except (ValueError, OSError, TypeError):
        parser.error('SEC_COLLECTION_CONFIGURATION_ERROR; check SEC_USER_AGENT and approved scope')
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return int(report['n_failed'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
