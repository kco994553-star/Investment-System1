#!/usr/bin/env python3
"""Connect an explicit, hash-pinned local financial V manifest; no acquisition."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.research.financial_v_bridge import VERSION, connect, summarize


def run(manifest_path):
    body = manifest_path.read_bytes()
    manifest = json.loads(body)
    receipts = []
    def read(spec):
        path = (manifest_path.parent / spec['path']).resolve()
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != spec['sha256']:
            raise ValueError('SOURCE_HASH_MISMATCH')
        receipts.append({'path': str(path), 'sha256': digest, 'bytes': len(data)})
        return data
    universe = json.loads(read(manifest['universe']))['records']
    shares = json.loads(read(manifest['shares']))['records']
    financial = {k:r for k,r in universe.items() if r.get('profile') == 'FINANCIAL'}
    issuer_codes = [r['code'] for r in manifest['issuers']]
    if len(universe) != 504 or len(set(issuer_codes)) != len(issuer_codes) or set(issuer_codes) != set(financial):
        raise ValueError('FIXED_FINANCIAL_MEMBERSHIP_REQUIRED')
    prices = json.loads(read(manifest['prices']))['records'] if manifest.get('prices') else {}
    if set(prices) - set(financial):
        raise ValueError('PRICE_CODE_OUTSIDE_FINANCIAL_POPULATION')
    rows = []
    for issuer in manifest['issuers']:
        code = issuer['code']
        rows.append(connect(record={**financial[code], 'code': code},
                            companyfacts_bytes=read(issuer['companyfacts']), shares=shares[code],
                            cover_bytes=read(issuer['cover']) if issuer.get('cover') else None,
                            valuation_date=manifest['valuation_date'], input_vintage=manifest['input_vintage'],
                            prices=prices.get(code)))
    return {'schema_version': VERSION, 'manifest_sha256': hashlib.sha256(body).hexdigest(),
            'valuation_date': manifest['valuation_date'], 'input_vintage': manifest['input_vintage'],
            'source_receipts': receipts, 'summary': summarize(rows), 'rows': rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    output = args.output.resolve()
    if any((p / '.git').exists() for p in (output.parent, *output.parents)):
        ap.error('output must be outside Git working trees')
    report = run(args.manifest.resolve())
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as handle:
        json.dump(report, handle, indent=2, allow_nan=False); handle.write('\n')
    print(json.dumps({'schema_version': VERSION, 'financial_codes': len(report['rows'])}))


if __name__ == '__main__':
    main()
