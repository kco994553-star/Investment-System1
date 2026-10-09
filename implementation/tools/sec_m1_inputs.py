"""Manual SEC-only M1 input processing for an explicit subset of US17.

Offline import is the default. --live opts into two SEC JSON requests per issuer;
there is no price, scoring, scheduling or Pages connection.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from investment_system.ingestion.sec_m1 import load_latest, retain_input
from investment_system.markets.us import US_LISTINGS
from investment_system.providers.sec_companyfacts import SEC_FACTS_URL
from investment_system.providers.sec_submissions import URL as SUBMISSIONS_URL


def _companies(values: list[str]) -> list[str]:
    if not values or len(values) > 17:
        raise ValueError('Specify 1–17 approved US17 company IDs')
    normalized = [value.strip().lower() for value in values]
    if any(value not in US_LISTINGS for value in normalized) or len(set(normalized)) != len(normalized):
        raise ValueError('Only distinct approved US17 company IDs are permitted')
    return normalized


def run_batch(store_root: Path | str, companies: list[str], loader,
              *, as_of: datetime | None = None, form_filter: str = '10-K') -> dict:
    companies = _companies(companies)
    if form_filter not in {'10-K', '10-Q'}:
        raise ValueError('Unsupported SEC form filter')
    if as_of is not None and (as_of.tzinfo is None or as_of.utcoffset() is None):
        raise ValueError('as_of requires a timezone-aware datetime')
    results = []
    for company_id in companies:
        previous_id = None
        try:
            previous_id = load_latest(store_root, company_id)['receipt_id']
        except (FileNotFoundError, ValueError):
            pass
        row = {'company_id': company_id, 'status': None, 'receipt_id': None,
               'previous_ready_receipt_id': previous_id}
        try:
            facts, submissions, acquired_at = loader(company_id, US_LISTINGS[company_id]['cik'])
            receipt = retain_input(store_root, company_id, facts, submissions, acquired_at,
                                   acquired_at if as_of is None else as_of, form_filter=form_filter)
            row.update(status=receipt['input']['status'], receipt_id=receipt['receipt_id'])
        except (OSError, ValueError, TypeError, KeyError) as exc:
            # Do not print payloads, headers, User-Agent or exception contents.
            row['status'] = 'ERROR_' + type(exc).__name__
        results.append(row)
    ready = sum(r['status'] == 'READY' for r in results)
    return {'contract': 'SEC_M1_BATCH', 'version': 1, 'n_ready': ready,
            'n_failed': len(results) - ready, 'results': results,
            'real_data_verified': False, 'full_pit_historical': False}


def _fetch(url: str, user_agent: str) -> tuple[bytes, int, str]:
    sys.path.insert(0, str(ROOT / 'tools'))
    from fetch_real_data import _get_with_retry
    return _get_with_retry(url, user_agent)


def make_live_loader(user_agent: str):
    if (not isinstance(user_agent, str) or not re.search(r'\S+@\S+\.\S+', user_agent)
            or '.invalid' in user_agent or '\n' in user_agent or '\r' in user_agent):
        raise ValueError('Live SEC requests require a descriptive User-Agent with valid contact')

    def loader(company_id: str, cik: str):
        if company_id not in US_LISTINGS or cik != US_LISTINGS[company_id]['cik']:
            raise ValueError('Live input must match an approved US17 issuer')
        bodies = []
        for template in (SEC_FACTS_URL, SUBMISSIONS_URL):
            url = template.format(cik=cik)
            body, status, _ = _fetch(url, user_agent)
            if status != 200:
                raise HTTPError(url, status, 'SEC request did not succeed', None, None)
            bodies.append(body)
            time.sleep(0.2)
        return bodies[0], bodies[1], datetime.now(timezone.utc)

    return loader


def _timestamp(value: str) -> datetime:
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError('naive timestamp')
        return stamp.astimezone(timezone.utc)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Expected timezone-aware ISO8601 timestamp') from exc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--companies', required=True, help='Comma-separated US17 company IDs (e.g. nvda,asml)')
    parser.add_argument('--store', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--input-dir', type=Path, help='Offline <company>.companyfacts.json and <company>.submissions.json')
    mode.add_argument('--live', action='store_true')
    parser.add_argument('--acquired-at', type=_timestamp, help='Required offline acquisition assertion; never first publication')
    parser.add_argument('--as-of', type=_timestamp, help='Default: each issuer acquisition bound')
    parser.add_argument('--form-filter', choices=('10-K', '10-Q'), default='10-K')
    parser.add_argument('--user-agent', help='Required for explicit live execution; never recorded in receipts/logs')
    args = parser.parse_args(argv)
    try:
        companies = _companies(args.companies.split(','))
        if args.live:
            if args.acquired_at is not None:
                parser.error('--acquired-at is only valid for offline imports')
            loader = make_live_loader(args.user_agent)
        else:
            if args.acquired_at is None:
                parser.error('Offline import requires --acquired-at')

            def loader(company_id, cik):
                return ((args.input_dir / f'{company_id}.companyfacts.json').read_bytes(),
                        (args.input_dir / f'{company_id}.submissions.json').read_bytes(), args.acquired_at)

        report = run_batch(args.store, companies, loader, as_of=args.as_of, form_filter=args.form_filter)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, sort_keys=True))
    return int(report['n_failed'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
