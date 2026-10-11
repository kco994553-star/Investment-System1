"""Python reference for the Holdings tab parser (web_assets/holdings-capture.js ``HoldingsCapture.parse``).

The Holdings tab is filled by the user from a brokerage balance screenshot via their own AI
("잔고 캡처 변환 프롬프트 v1"). Rows are read only on this device; this module is a pure
reference for the shared synthetic vectors (tests/fixtures/holdings_capture_reference_v1.json).

Rules (identical in JS):
- header must be exactly ``as_of, symbol, quantity, avg_cost, currency, cost_krw, name``
  (case-insensitive, trailing blank cells ignored) or nothing is read (HEADER_MISMATCH);
- rows with a problem are reported under ``review`` with the sheet row number and reason codes
  and are not read; missing numbers are never filled with 0;
- average cost prefers ``cost_krw / quantity`` (exact decimal, half-up to 6 decimals, KRW),
  falls back to ``avg_cost`` (row currency) only when ``cost_krw`` is empty;
- ``CASH_<CCY>`` rows are cash, not positions.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import re

SCHEMA = 'holdings-capture/1'
HEADER = ('as_of', 'symbol', 'quantity', 'avg_cost', 'currency', 'cost_krw', 'name')
MAX_ROWS = 1000
_WS = ' \t\r\n 　'
_DECIMAL = re.compile(r'^(?:0|[1-9]\d{0,14})(?:\.\d{1,12})?$')
_US = re.compile(r'^[A-Z][A-Z0-9]{0,5}(?:[.-][A-Z0-9]{1,3})?$')
_KRX = re.compile(r'^\d{6}$')
_TSE = re.compile(r'^\d{4}$')
_CASH = re.compile(r'^CASH_([A-Z]{3})$')
_CCY = re.compile(r'^[A-Z]{3}$')
_DAY = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_CONTROL = re.compile(r'[\x00-\x1f\x7f]')
_SCALE = 6


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and value.strip(_WS) == '')


def _number_text(value):
    if _is_number(value):
        number = float(value)
        if number != number or number in (float('inf'), float('-inf')) or number < 0:
            return None
        if number != 0 and (number < 1e-6 or number >= 1e21):
            return None  # JS would print these with an exponent; both sides reject.
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if isinstance(value, int):
            return str(value)
        return format(Decimal(repr(value)), 'f')
    if isinstance(value, str):
        return value.strip(_WS)
    return None


def _decimal(value):
    text = _number_text(value)
    return text if text is not None and _DECIMAL.fullmatch(text) else None


def _valid_day(text) -> bool:
    if not isinstance(text, str) or not _DAY.fullmatch(text) or text < '1970-01-01':
        return False
    try:
        return date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


def _day(value):
    if _is_number(value):
        if isinstance(value, float) and not value.is_integer():
            return None
        serial = int(value)
        if serial < 1 or serial > 2958465:
            return None
        return (date(1899, 12, 30) + timedelta(days=serial)).isoformat()
    if not isinstance(value, str):
        return None
    text = value.strip(_WS)
    return text if _valid_day(text) else None


def _parts(text: str):
    whole, _, fraction = text.partition('.')
    return int(whole + fraction), len(fraction)


def divide(numerator: str, denominator: str):
    """Exact ``numerator / denominator`` of decimal strings, half-up to 6 decimals."""
    n, ns = _parts(numerator)
    d, ds = _parts(denominator)
    if d == 0:
        return None
    top, bottom = n * 10 ** (ds + _SCALE), d * 10 ** ns
    quotient, remainder = divmod(top, bottom)
    if remainder * 2 >= bottom:
        quotient += 1
    digits = str(quotient).rjust(_SCALE + 1, '0')
    text = (digits[:-_SCALE] + '.' + digits[-_SCALE:]).rstrip('0').rstrip('.')
    return text if _DECIMAL.fullmatch(text) else None


def _symbol(raw, currency):
    if _is_number(raw):
        if isinstance(raw, float) and not raw.is_integer():
            return None
        number = int(raw)
        if number < 0:
            return None
        if currency == 'KRW' and number <= 999999:
            return str(number).rjust(6, '0')
        if currency == 'JPY' and 1000 <= number <= 9999:
            return str(number)
        return None
    if not isinstance(raw, str):
        return None
    text = raw.strip(_WS)
    return text if (_CASH.fullmatch(text) or _KRX.fullmatch(text) or _TSE.fullmatch(text) or _US.fullmatch(text)) else None


def _market(symbol: str) -> str:
    if _CASH.fullmatch(symbol):
        return 'CASH'
    if _KRX.fullmatch(symbol):
        return 'KRX'
    if _TSE.fullmatch(symbol):
        return 'TSE'
    return 'US'


def _expected_currency(symbol: str, market: str) -> str:
    if market == 'CASH':
        return _CASH.fullmatch(symbol).group(1)
    return {'KRX': 'KRW', 'TSE': 'JPY'}.get(market, 'USD')


def _header_matches(row) -> bool:
    if not isinstance(row, list):
        return False
    cells = list(row)
    while cells and _blank(cells[-1]):
        cells.pop()
    return len(cells) == len(HEADER) and all(
        isinstance(cell, str) and cell.strip(_WS).lower() == HEADER[i] for i, cell in enumerate(cells))


def parse(values) -> dict:
    result = {'schema': SCHEMA, 'state': 'EMPTY', 'as_of': None, 'positions': [], 'cash': [], 'review': []}
    if not isinstance(values, list) or not values:
        return result
    if not _header_matches(values[0]):
        return {**result, 'state': 'HEADER_MISMATCH'}
    end = len(values)
    while end > 1 and (not isinstance(values[end - 1], list) or all(_blank(c) for c in values[end - 1])):
        end -= 1
    if end - 1 > MAX_ROWS:
        return {**result, 'state': 'ROW_LIMIT'}
    checked = []
    for index in range(1, end):
        row, number = values[index], index + 1
        if not isinstance(row, list):
            result['review'].append({'row': number, 'symbol': None, 'reason_codes': ['COLUMN_COUNT']})
            continue
        if all(_blank(c) for c in row):
            continue
        if any(not _blank(c) for c in row[len(HEADER):]):
            result['review'].append({'row': number, 'symbol': None, 'reason_codes': ['COLUMN_COUNT']})
            continue
        cell = (lambda i: row[i] if i < len(row) else None)
        as_of_raw, symbol_raw, quantity_raw, avg_raw, currency_raw, cost_raw, name_raw = (cell(i) for i in range(7))
        reasons = []
        as_of = None if _blank(as_of_raw) else _day(as_of_raw)
        if _blank(as_of_raw):
            reasons.append('AS_OF_MISSING')
        elif as_of is None:
            reasons.append('AS_OF_FORMAT')
        currency = None
        if not _blank(currency_raw) and isinstance(currency_raw, str) and _CCY.fullmatch(currency_raw.strip(_WS)):
            currency = currency_raw.strip(_WS)
        if _blank(currency_raw):
            reasons.append('CURRENCY_MISSING')
        elif currency is None:
            reasons.append('CURRENCY_FORMAT')
        symbol = None if _blank(symbol_raw) else _symbol(symbol_raw, currency)
        if _blank(symbol_raw):
            reasons.append('SYMBOL_MISSING')
        elif symbol is None:
            reasons.append('SYMBOL_FORMAT')
        market = None if symbol is None else _market(symbol)
        quantity = None if _blank(quantity_raw) else _decimal(quantity_raw)
        if _blank(quantity_raw):
            reasons.append('QUANTITY_MISSING')
        elif quantity is None:
            reasons.append('QUANTITY_FORMAT')
        elif market != 'CASH' and Decimal(quantity) <= 0:
            reasons.append('QUANTITY_NOT_POSITIVE')
        avg = None if _blank(avg_raw) else _decimal(avg_raw)
        if not _blank(avg_raw) and avg is None:
            reasons.append('AVG_COST_FORMAT')
        if market == 'CASH' and not _blank(avg_raw):
            reasons.append('CASH_AVG_COST_PRESENT')
        cost = None if _blank(cost_raw) else _decimal(cost_raw)
        if not _blank(cost_raw) and cost is None:
            reasons.append('COST_KRW_FORMAT')
        if symbol is not None and currency is not None and _expected_currency(symbol, market) != currency:
            reasons.append('CURRENCY_MISMATCH')
        name = None if _blank(name_raw) else (name_raw.strip(_WS) if isinstance(name_raw, str) else None)
        if not _blank(name_raw) and (name is None or len(name) > 100 or _CONTROL.search(name)):
            reasons.append('NAME_FORMAT')
        average, average_currency, basis = None, None, 'NOT_AVAILABLE'
        if not reasons and market != 'CASH':
            if cost is not None:
                average, average_currency, basis = divide(cost, quantity), 'KRW', 'COST_KRW_DIV_QTY'
                if average is None:
                    reasons.append('COST_RANGE')
            elif avg is not None:
                average, average_currency, basis = avg, currency, 'AVG_COST_FIELD'
        if reasons:
            result['review'].append({'row': number, 'symbol': symbol, 'reason_codes': reasons})
            continue
        if market == 'CASH':
            checked.append(('cash', as_of, {'row': number, 'symbol': symbol, 'currency': currency, 'amount': quantity,
                                            'cost_krw': cost, 'name': name}))
        else:
            checked.append(('position', as_of, {'row': number, 'symbol': symbol, 'market': market, 'quantity': quantity,
                                                'currency': currency, 'avg_cost': avg, 'cost_krw': cost,
                                                'average_cost': average, 'average_cost_currency': average_currency,
                                                'cost_basis': basis, 'name': name}))
    newest = max((item[1] for item in checked), default='')
    dated = []
    for kind, as_of, value in checked:
        if as_of != newest:
            result['review'].append({'row': value['row'], 'symbol': value['symbol'], 'reason_codes': ['AS_OF_MISMATCH']})
        else:
            dated.append((kind, value))
    counts = {}
    for _, value in dated:
        counts[value['symbol']] = counts.get(value['symbol'], 0) + 1
    for kind, value in dated:
        if counts[value['symbol']] > 1:
            result['review'].append({'row': value['row'], 'symbol': value['symbol'], 'reason_codes': ['DUPLICATE_SYMBOL']})
        else:
            result['cash' if kind == 'cash' else 'positions'].append(value)
    result['review'].sort(key=lambda item: item['row'])
    result['state'] = 'OK' if checked or result['review'] else 'EMPTY'
    result['as_of'] = newest if (result['positions'] or result['cash']) else None
    return result
