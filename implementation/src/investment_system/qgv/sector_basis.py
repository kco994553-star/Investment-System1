"""D-22 (decided 2026-10-11): SEC SIC → sector benchmark ETF for the virtual-trading abnormal-drop check.

Rows are matched in order; the first match wins. Row 2 (SIC 3559/3827, semiconductor equipment) uses option A:
SMH when the company is a theme v0 'semiconductors' member, otherwise XLI. No match or no SIC → S&P 500 (SPY).
Mirrors `VirtualTrading.sectorBenchmark` in web_assets/virtual-trading.js.
"""
from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name('sector_etf_map_v1.json')


def load_map(path=CONFIG_PATH):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sector_benchmark(sic, semis_member=None, mapping=None):
    """Returns {'etf', 'rule', 'reason'}; etf is a ticker or 'SPY' with a fallback reason."""
    m = mapping or load_map()
    if not (isinstance(sic, str) and len(sic) == 4 and sic.isdigit() and sic != '0000'):
        return {'etf': m['sp500_benchmark'], 'rule': 14, 'reason': 'SIC_NOT_AVAILABLE'}
    code = int(sic)
    for rule in m['rules']:
        if code in rule['exclude']:
            continue
        if any(lo <= code <= hi for lo, hi in rule['sic']):
            if rule['etf'] == 'SEMIS_THEME_SMH_ELSE_XLI':
                if semis_member is True:
                    return {'etf': 'SMH', 'rule': rule['order'], 'reason': None}
                return {'etf': 'XLI', 'rule': rule['order'], 'reason': None if semis_member is False else 'SEMIS_MEMBERSHIP_NOT_AVAILABLE'}
            return {'etf': rule['etf'], 'rule': rule['order'], 'reason': None}
    return {'etf': m['sp500_benchmark'], 'rule': 14, 'reason': 'SECTOR_ETF_NOT_MAPPED'}
