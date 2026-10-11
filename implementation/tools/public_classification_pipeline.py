"""Write company-classification.json (SIC industry group v0 + strategy theme v0) into a Pages directory.

Offline (default): every value NOT_AVAILABLE with reason codes, so the device never reads a missing file.
--live (GitHub Actions only): SEC submissions SIC, latest 10-K Item 1 and basket-ETF N-PORT holdings
identifiers through the fixed-URL client, User-Agent from the SEC_USER_AGENT secret. Raw bodies stay in
RAM; only the validated public projection is written. Output lines carry counts and fixed codes only.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.product.public_classification import FILENAME, build_classification, company_identity

# Daily acquisition cadence, same as the other public screens. Not a model threshold.
ACQUISITION_TTL = timedelta(hours=24)
MAX_BYTES = 2 * 1024 * 1024


class Parser(argparse.ArgumentParser):
    def error(self, _):
        self.exit(2, 'PUBLIC_CLASSIFICATION_ARGUMENTS_INVALID\n')


def write(directory, payload):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir() or (directory / FILENAME).is_symlink():
        raise ValueError('PUBLIC_CLASSIFICATION_OUTPUT_INVALID')
    body = json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()
    if len(body) > MAX_BYTES:
        raise ValueError('PUBLIC_CLASSIFICATION_OUTPUT_INVALID')
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as handle:
            temp = Path(handle.name)
            handle.write(body)
        temp.replace(directory / FILENAME)
        temp = None
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return payload


def emit(directory, *, as_of=None):
    """Offline NOT_AVAILABLE file (used by build_pages_cockpit)."""
    return write(directory, build_classification(as_of=as_of or datetime.now(timezone.utc), stale_after=ACQUISITION_TTL))


def collect(directory, *, environ=None, client_factory=None):
    from investment_system.providers.sec_classification_collection import (ClassificationSecClient, collect_company_inputs,
                                                                        collect_etf_inputs)
    from investment_system.qgv.theme_membership import load_theme_config_v0, basket_tickers
    environ = os.environ if environ is None else environ
    agent = environ.get('SEC_USER_AGENT')
    if not agent:
        raise ValueError('SEC_USER_AGENT_MISSING')
    client = (client_factory or ClassificationSecClient)(agent)
    identity = company_identity()
    config = load_theme_config_v0()
    etfs, mf = collect_etf_inputs(client, basket_tickers(config))
    companies = collect_company_inputs(client, {cid: row['cik'] for cid, row in identity.items() if row['cik']})
    payload = build_classification(as_of=datetime.now(timezone.utc), stale_after=ACQUISITION_TTL, companies_input=companies,
                                   etfs_input=etfs, mf_source=mf, identity=identity, theme_config=config)
    return write(directory, payload)


def summary(payload):
    rows = payload['data']['companies'].values()
    etfs = payload['data']['etfs']
    codes = sorted({e['reason_code'] for e in etfs.values() if e['reason_code']})
    return ('PUBLIC_CLASSIFICATION_OK state=' + payload['state']
            + ' industry=' + str(sum(r['industry']['state'] != 'NOT_AVAILABLE' for r in rows))
            + ' themes=' + str(sum(r['themes']['state'] != 'NOT_AVAILABLE' for r in rows))
            + ' etfs=' + str(sum(e['state'] != 'NOT_AVAILABLE' for e in etfs.values())) + '/' + str(len(etfs))
            + (' etf_codes=' + ','.join(codes) if codes else ''))


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args(argv)
    try:
        payload = collect(args.out) if args.live else emit(args.out)
    except Exception:
        if not args.live:
            print('PUBLIC_CLASSIFICATION_BUILD_FAILED')
            return 1
        # A failed live run must not block the daily Pages deploy: publish NOT_AVAILABLE instead.
        try:
            payload = emit(args.out)
        except Exception:
            print('PUBLIC_CLASSIFICATION_BUILD_FAILED')
            return 1
        print('PUBLIC_CLASSIFICATION_LIVE_UNAVAILABLE fallback=NOT_AVAILABLE')
    print(summary(payload))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
