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
from investment_system.research.financial_v import _day


def _point(document, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('PRICE_EVIDENCE_POINTER_INVALID')
    try:
        for part in pointer[1:].split('/'):
            part = part.replace('~1', '/').replace('~0', '~')
            if isinstance(document, list):
                if not part.isdigit(): raise ValueError
                document = document[int(part)]
            else: document = document[part]
        return document
    except (KeyError, IndexError, TypeError, ValueError):
        raise ValueError('PRICE_EVIDENCE_POINTER_INVALID') from None


def _verify_price_sources(records, sources, valuation_date):
    """Small, retained observations/basis artifacts; never load a multi-GB pcap."""
    trade_fields = ('code', 'cik', 'value', 'date', 'currency', 'unit', 'traded_at',
                    'acquired_at', 'price_type', 'price_basis', 'trade_validation')
    for code, metrics in records.items():
        for quote in metrics.values():
            if quote is None: continue
            linked = {}
            for name in ('source', 'basis_source'):
                ref = quote.get(name) or {}
                doc = sources.get(ref.get('sha256'))
                if doc is None: raise ValueError('PRICE_EVIDENCE_FILE_REQUIRED')
                linked[name] = _point(doc, ref.get('json_pointer'))
                if not isinstance(linked[name], dict): raise ValueError('PRICE_EVIDENCE_RECORD_REQUIRED')
            if quote.get('code') != code or any(k not in quote or linked['source'].get(k) != quote[k] for k in trade_fields):
                raise ValueError('PRICE_SOURCE_FIELD_MISMATCH')
            basis = linked['basis_source']
            if (any(basis.get(k) != quote.get(k) for k in ('code', 'cik', 'share_basis'))
                    or basis.get('action_status') != 'MATCHED_TO_NUMERATOR'
                    or _day(basis.get('valid_from')) is None or _day(basis.get('valid_to')) is None
                    or not basis['valid_from'] <= valuation_date <= basis['valid_to']):
                raise ValueError('PRICE_BASIS_EVIDENCE_MISMATCH')


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
    prices = {}
    iex_report = None
    if manifest.get('prices') and manifest.get('iex_handoff'):
        raise ValueError('AMBIGUOUS_PRICE_INPUT')
    if manifest.get('iex_handoff'):
        from investment_system.research.financial_v_iex import adapt
        handoff = manifest['iex_handoff']
        main_manifest, derived, requests = (read(handoff[k]) for k in ('manifest','derived','requests'))
        basis_bytes = read(handoff['basis']) if handoff.get('basis') else b'{"records":{}}'
        basis = json.loads(basis_bytes)
        proof_hashes = set()
        for spec in handoff.get('basis_evidence', []):
            read(spec); proof_hashes.add(spec['sha256'])
        for metrics in basis.get('records', {}).values():
            for proof in metrics.values():
                if any(ref['sha256'] not in proof_hashes for ref in proof.get('evidence_refs', [])):
                    raise ValueError('PRICE_BASIS_EVIDENCE_FILE_REQUIRED')
        iex_report = adapt(main_manifest, derived, requests, basis_bytes,
                           valuation_date=manifest['valuation_date'], input_vintage=manifest['input_vintage'])
        prices = iex_report['prices']['records']
        _verify_price_sources(prices, {iex_report['trade_evidence_sha256']: iex_report['trade_evidence'],
                                      iex_report['basis_sha256']: basis}, manifest['valuation_date'])
    if manifest.get('prices'):
        supplied = json.loads(read(manifest['prices']))
        if (supplied.get('schema_version') != 'financial-v-price-input/1'
                or supplied.get('valuation_date') != manifest['valuation_date']):
            raise ValueError('PRICE_HANDOFF_SCHEMA_OR_DATE_MISMATCH')
        prices = supplied['records']
        sources = {spec['sha256']: json.loads(read(spec)) for spec in manifest.get('price_evidence', [])}
        _verify_price_sources(prices, sources, manifest['valuation_date'])
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
    report = {'schema_version': VERSION, 'manifest_sha256': hashlib.sha256(body).hexdigest(),
            'valuation_date': manifest['valuation_date'], 'input_vintage': manifest['input_vintage'],
            'source_receipts': receipts, 'summary': summarize(rows), 'rows': rows}
    if iex_report is not None:
        requested = {r['code'] for r in iex_report['rows']}
        results = {r['code']: r['result'] for r in rows if r['code'] in requested}
        for item in iex_report['rows']:
            result = results[item['code']]
            item['raw_ratio_value'] = result['metrics'][item['metric']]['value']
            item['candidate_primary_adopted'] = result['primary_available']
            item['candidate_reasons'] = result['metrics'][item['metric']]['reasons']
        iex_report['summary']['raw_ratio_metrics'] = sum(i['raw_ratio_value'] is not None for i in iex_report['rows'])
        iex_report['summary']['primary_adopted_codes'] = sum(r['primary_available'] for r in results.values())
        report['iex_handoff'] = iex_report
    return report


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
