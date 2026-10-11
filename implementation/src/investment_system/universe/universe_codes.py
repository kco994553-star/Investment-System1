"""Public Universe504 code list for new Google sheets (Pages file ``universe-codes.json``).

Price-free: only GOOGLEFINANCE exchange codes, in the order of ``universe_codes_v1.json``. The browser
(``google-sheet-setup.js`` ``codes()``) writes them into the user's own Universe tab with
``=IFERROR(GOOGLEFINANCE(A<n>,"marketcap"),"")`` / ``"price"`` formulas; no value is ever published.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

FILENAME = 'universe-codes.json'
SCHEMA = 'universe-codes/1'
MAX_CODES = 1024
SOURCE = Path(__file__).with_name('universe_codes_v1.json')
# Same formats as google-sheet-setup.js codes(): NASDAQ/NYSE/BATS tickers, KRX 6-digit, TYO 4-digit.
_CODE = re.compile(r'(?:(?:NASDAQ|NYSE|BATS):[A-Z][A-Z0-9.]{0,15}|KRX:\d{6}|TYO:\d{4})')


def source_codes() -> list[str]:
    codes = json.loads(SOURCE.read_text(encoding='utf-8'))
    if not isinstance(codes, list):
        raise ValueError('universe codes source must be a list')
    return codes


def public_payload() -> dict:
    payload = {'schema': SCHEMA, 'codes': source_codes()}
    require_universe_codes(payload)
    return payload


def require_universe_codes(value) -> None:
    """Strict: exactly {schema, codes}, valid unique codes, and equal to the reviewed in-repo list."""
    if not isinstance(value, dict) or set(value) != {'schema', 'codes'} or value['schema'] != SCHEMA:
        raise ValueError('universe codes envelope')
    codes = value['codes']
    if not isinstance(codes, list) or not codes or len(codes) > MAX_CODES or len(set(map(str, codes))) != len(codes):
        raise ValueError('universe codes list')
    if any(not isinstance(code, str) or not _CODE.fullmatch(code) for code in codes):
        raise ValueError('universe code format')
    if codes != source_codes():
        raise ValueError('universe codes differ from the reviewed list')
