"""Narrow 13F disclosure projection proposed for explicit public-boundary approval.

SEC-reported dollars/thousands are copied with their original units. They are
never divided by quantity, converted to prices, or marked as current holdings.
Only complete, comparable captures expose long SH rows without put/call options.
"""
from dataclasses import asdict
import hashlib
import json
import re

SCOPE = 'SEC_REPORTED_LONG_SH_NONOPTION'
SNAPSHOT_KEYS = {'filing_date', 'reported_holdings'}
HOLDING_KEYS = {'cusip', 'security_key', 'issuer_names', 'reported_quantity',
                'reported_value', 'reported_value_basis'}
MAX_SAFE_INTEGER = 2**53 - 1


def security_key(key):
    identity = json.dumps(asdict(key), sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(identity).hexdigest()


def project_details(previous, current):
    def snapshot(capture):
        holdings = []
        for h in capture.holdings:
            if h.key.quantity_type != 'SH' or h.key.put_call is not None or h.quantity <= 0:
                continue
            holdings.append({'cusip': h.key.cusip, 'security_key': security_key(h.key),
                             'issuer_names': sorted({r.issuer_name for r in h.raw_rows}),
                             'reported_quantity': h.quantity, 'reported_value': h.value,
                             'reported_value_basis': h.value_basis})
        return {'filing_date': capture.metadata.filing_date.isoformat(),
                'reported_holdings': sorted(holdings, key=lambda h: (h['cusip'], h['security_key']))}
    return {'scope': SCOPE, 'previous': snapshot(previous), 'current': snapshot(current)}


def require_details(details, report, cut):
    """Exact additive schema; absent details keep legacy NA semantics."""
    def need(ok):
        if not ok:
            raise ValueError('PUBLIC_SCREEN_INVALID')
    if details is None:
        need(report['state'] == 'NOT_AVAILABLE')
        return
    need(report['state'] != 'NOT_AVAILABLE' and isinstance(details, dict)
         and set(details) == {'scope', 'previous', 'current'} and details['scope'] == SCOPE)
    for side in ('previous', 'current'):
        snap = details[side]
        need(isinstance(snap, dict) and set(snap) == SNAPSHOT_KEYS)
        filed = snap['filing_date']
        need(isinstance(filed, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', filed) is not None)
        from datetime import date
        need(date.fromisoformat(report[side + '_quarter']) <= date.fromisoformat(filed) <= cut.date())
        need(isinstance(snap['reported_holdings'], list) and len(snap['reported_holdings']) <= 30000)
        seen = set()
        for h in snap['reported_holdings']:
            need(isinstance(h, dict) and set(h) == HOLDING_KEYS)
            need(isinstance(h['cusip'], str) and re.fullmatch(r'[0-9A-Z*@#]{9}', h['cusip']) is not None)
            need(isinstance(h['security_key'], str) and re.fullmatch(r'[0-9a-f]{64}', h['security_key']) is not None
                 and h['security_key'] not in seen)
            seen.add(h['security_key'])
            need(type(h['reported_quantity']) is int and 0 < h['reported_quantity'] <= MAX_SAFE_INTEGER)
            need(type(h['reported_value']) is int and 0 <= h['reported_value'] <= MAX_SAFE_INTEGER
                 and h['reported_value_basis'] in ('USD_DOLLARS', 'USD_THOUSANDS'))
            names = h['issuer_names']
            need(isinstance(names, list) and 0 < len(names) <= 100 and len(set(names)) == len(names))
            need(all(isinstance(n, str) and 0 < len(n) <= 150 and re.fullmatch(r"[A-Za-z0-9 !\\#$(),.:;`='\-{}|/&]+", n)
                     for n in names))
