#!/usr/bin/env python3
"""Synthetic Python reference vectors for the device value view (DeviceValuation.view).

Usage: device_valuation_reference.py --write   (regenerates tests/fixtures/device_valuation_reference_v1.json)
Synthetic inputs only; never a public or live-data serializer.
"""
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/device_valuation_reference_v1.json'


def _row(fcfe=8.25, currency='USD', eps=4.0, revenue=5000.0, revenue_prev=4900.0, v_currency='USD', fcfe_state='LIVE'):
    na = fcfe is None or fcfe_state == 'NOT_AVAILABLE'
    fcfe_block = {'state': 'NOT_AVAILABLE' if na else fcfe_state, 'reason_codes': ['NET_SHORT_TERM_BORROWING_MISSING'] if na else [],
                  'fcfe_per_share': None if na else fcfe, 'currency': currency}
    present = any(v is not None for v in (eps, revenue, revenue_prev))
    v = {'state': 'LIVE' if present else 'NOT_AVAILABLE', 'eps': eps, 'revenue': revenue, 'revenue_prev': revenue_prev,
         'currency': v_currency if present else None}
    return {'state': 'LIVE', 'fcfe': fcfe_block, 'v_inputs': v}


def cases():
    from investment_system.qgv.dcf_parameters import load_default_dcf_parameters
    p = load_default_dcf_parameters()
    custom = copy.deepcopy(p)
    custom.update(status='CUSTOM_PREVIEW', discount_rate=0.09)
    usd = lambda price: {'price': price, 'currency': 'USD'}
    spec = [
        ('full', _row(), usd(100.0), p),
        ('full-low-price', _row(), usd(60.0), p),
        ('no-device-price', _row(), None, p),
        ('no-public-row', None, usd(100.0), p),
        ('no-row-no-price', None, None, p),
        ('fcfe-not-available-eps-still-used', _row(fcfe=None), usd(100.0), p),
        ('negative-fcfe', _row(fcfe=-2.0), usd(100.0), p),
        ('price-above-bracket-no-pe-proxy', _row(fcfe=0.5), usd(5000.0), p),
        ('price-below-bracket', _row(fcfe=8.25), usd(1.0), p),
        ('price-currency-mismatch', _row(), {'price': 100.0, 'currency': 'EUR'}, p),
        ('fcfe-currency-not-parameter-currency', _row(currency='EUR', v_currency='EUR'), {'price': 100.0, 'currency': 'EUR'}, p),
        ('invalid-price-zero', _row(), usd(0.0), p),
        ('negative-eps', _row(eps=-1.0), usd(100.0), p),
        ('revenue-prev-missing', _row(revenue_prev=None), usd(100.0), p),
        ('stale-row-still-computes', _row(fcfe_state='STALE'), usd(80.0), p),
        ('custom-parameters-versioned', _row(), usd(100.0), custom),
    ]
    return [{'id': i, 'synthetic': True, 'operation': 'device_value_view', 'input': {'row': r, 'quote': q, 'parameters': par}} for i, r, q, par in spec]


def replay(case):
    if case.get('synthetic') is not True:
        raise ValueError('SYNTHETIC_ONLY')
    if case.get('operation') != 'device_value_view':
        raise ValueError('UNKNOWN_OPERATION')
    from investment_system.qgv.device_valuation import device_value_view
    return device_value_view(**case['input'])


def main(argv):
    out = [dict(c, expected=replay(c)) for c in cases()]
    payload = {'schema_version': 1, 'synthetic': True, 'role': 'REFERENCE_TEST_ONLY',
               'numeric_tolerance': {'relative': 1e-10, 'absolute': 1e-10}, 'cases': out}
    text = json.dumps(payload, indent=1, sort_keys=True, allow_nan=False) + '\n'
    if '--write' in argv:
        FIXTURE.write_text(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
