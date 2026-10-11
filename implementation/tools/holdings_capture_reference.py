#!/usr/bin/env python3
"""Synthetic Python reference vectors for the Holdings tab parser (HoldingsCapture.parse).

Usage: holdings_capture_reference.py --write   (regenerates tests/fixtures/holdings_capture_reference_v1.json)
Every value below is invented for tests; never a real balance, never a public serializer.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/holdings_capture_reference_v1.json'
H = ['as_of', 'symbol', 'quantity', 'avg_cost', 'currency', 'cost_krw', 'name']
D = '2031-02-03'


def cases():
    c = []

    def add(case_id, values):
        c.append({'id': case_id, 'synthetic': True, 'operation': 'parse', 'input': {'values': values}})

    add('empty-sheet', [])
    add('header-only', [H])
    add('header-mismatch', [['as_of', 'symbol', 'qty', 'avg_cost', 'currency', 'cost_krw', 'name'], [D, 'SYNA', '1', '', 'USD']])
    add('header-case-and-trailing-blank', [['AS_OF', ' Symbol ', 'quantity', 'avg_cost', 'currency', 'cost_krw', 'name', ''],
                                           [D, 'SYNA', '2', '10.5', 'USD', '', 'Synthetic A']])
    add('cost-krw-preferred', [H, [D, 'SYNB', '3', '9.99', 'USD', '40000', 'Synthetic B']])
    add('avg-cost-fallback', [H, [D, 'SYNC', '4', '12.25', 'USD', '', 'Synthetic C']])
    add('no-cost-not-zero-filled', [H, [D, 'SYND', '5', '', 'USD']])
    add('half-up-rounding', [H, [D, '000111', '7', '', 'KRW', '1000000'], [D, '1234', '3', '', 'JPY', '2']])
    add('cash-rows', [H, [D, 'CASH_KRW', '123456', '', 'KRW', '', '예수금'], [D, 'CASH_USD', '0', '', 'USD', '0'],
                      [D, 'CASH_JPY', '10', '1', 'JPY']])
    add('number-format-errors', [H, [D, 'SYNE', '1,000', '', 'USD'], [D, 'SYNF', '1', '$5', 'USD'],
                                 [D, 'SYNG', '1', '', 'USD', '-3'], [D, 'SYNH', '+2', '', 'USD'], [D, 'SYNI', '0', '', 'USD'],
                                 [D, 'SYNJ', '01', '', 'USD'], [D, 'SYNK', '1.5e3', '', 'USD']])
    add('column-count', [H, [D, 'SYNL', '1', '', 'USD', '', 'L', 'extra'], [D, 'SYNM', '1', '', 'USD', '', 'M', '', '']])
    add('missing-fields', [H, ['', 'SYNN', '1', '', 'USD'], [D, '', '1', '', 'USD'], [D, 'SYNO', '', '', 'USD'], [D, 'SYNP', '1', '', '']])
    add('symbol-and-currency-rules', [H, [D, 'syna', '1', '', 'USD'], [D, '12345', '1', '', 'KRW'], [D, '000222', '1', '', 'USD'],
                                      [D, '5678', '1', '', 'KRW'], [D, 'SYNQ', '1', '', 'usd'], [D, 'BRK.B', '1', '', 'USD'],
                                      [D, 'CASH_EUR', '1', '', 'USD']])
    add('as-of-rules', [H, ['2031-02-30', 'SYNR', '1', '', 'USD'], ['2031-02-02', 'SYNS', '1', '', 'USD'], [D, 'SYNT', '1', '', 'USD']])
    add('duplicate-symbol', [H, [D, 'SYNU', '1', '', 'USD'], [D, 'SYNU', '2', '', 'USD'], [D, 'SYNV', '1', '', 'USD']])
    add('sheet-numbers-and-serial-dates', [H, [47882, 333, 7, 1.25, 'KRW', 100, 'serial'], [47882, 4321, 2, '', 'JPY', 0.000001],
                                            [47882, 'SYNW', 0.5, '', 'USD', 1e-07], [47882.5, 'SYNX', 1, '', 'USD'],
                                            [47882, 4321.5, 1, '', 'JPY'], [47882, 'SYNY', True, '', 'USD']])
    add('blank-rows-skipped', [H, [], ['', None, ''], [D, 'SYNZ', '1', '', 'USD'], [], [None]])
    add('name-rules', [H, [D, 'SYAA', '1', '', 'USD', '', 'x' * 101], [D, 'SYAB', '1', '', 'USD', '', 'tab\there'],
                       [D, 'SYAC', '1', '', 'USD', '', 42], [D, 'SYAD', '1', '', 'USD', '', '  공백 　']])
    add('cost-range', [H, [D, 'SYAE', '0.000001', '', 'USD', '999999999999999']])
    add('mixed-target-and-outside', [H, [D, 'ASML', '2', '700', 'USD', '1900000', 'ASML Holding'],
                                     [D, '8035', '1', '30000', 'JPY', '', 'Tokyo Electron'],
                                     [D, '042700', '10', '', 'KRW', '1234567', '한미반도체'],
                                     [D, 'KO', '3', '60.1', 'USD', '', 'Coca-Cola'], [D, 'CASH_KRW', '50000', '', 'KRW']])
    return c


def replay(case):
    from investment_system.product.holdings_capture import parse
    assert case['operation'] == 'parse'
    return parse(case['input']['values'])


def build():
    return {'schema': 'holdings-capture-reference/1', 'synthetic': True,
            'cases': [{**case, 'expected': replay(case)} for case in cases()]}


if __name__ == '__main__':
    if sys.argv[1:] != ['--write']:
        raise SystemExit('usage: holdings_capture_reference.py --write')
    FIXTURE.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('wrote', FIXTURE.name)
