"""Per-day IEX last-trade result (RAM) -> EXP-STOCK-INDICATOR-DECILES-v1 S quote records. Offline, RAM only.

Input shapes (the central-V IEX HIST provider):
  parser rows   the provider's parse_rows output: {IEX symbol: (parser status, price_e4 or None)}, parser status ROUND /
                ODD_ONLY / NO_TRADE (the published codes SUPPLIED / ODD_LOT_ONLY / NO_IEX_TRADE are accepted too), price_e4
                the integer price x 10,000 of the last regular-session round-lot trade (exact: price = price_e4 / 10000)
  IexDay        the provider's IexDay (`day` = the IEX file's day, `status` {key: code}, `quotes` {key: {price, currency}} for
                SUPPLIED keys only); read through `signal_quotes_from_iex_day`
plus the caller's mapping {security_id: IEX symbol or None} (for an IexDay: {IexDay key: security_id}).

Output (`signal_quotes`): {'quotes': {security_id: engine quote}, 'status': {security_id: code}, 'counts', 'label',
'use'}. An engine quote is {'price', 'currency': 'USD', 'month_closes': {}, 'price_label'} for SUPPLIED, else
{'price': None, 'currency': 'USD', 'month_closes': {}, 'price_label', 'withheld_reason': <status>} (the engine records the
status as the quote status; the price is never filled from another day, symbol or source, and never set to 0).

Status per security: SUPPLIED (a regular-session round-lot last trade on S), ODD_LOT_ONLY (only odd-lot trades: not used),
NO_IEX_TRADE (no regular-session trade on IEX on S), UNMAPPED (no valid IEX symbol for the security),
IEX_RESULT_MISSING_SYMBOL (a mapped symbol the day's result does not carry), IEX_DAY_NOT_SIGNAL_DAY (the IEX file's day
is not S: every security is withheld, never priced from another day).

Label IEX_LAST_REGULAR_TRADE_APPROX: the IEX last regular-session trade only APPROXIMATES the S signal price (not an
official or consolidated close; IEX trades only). It is never a T open (settings doc section 3: the T open is not
replaced by a last trade); the bundle takes ledger prices only from the Alpaca SIP daily bars. Month-end closes are not
part of a one-day result (month_closes is empty). Nothing is written to disk and nothing is printed: the result lives in
the caller's process (GSQ-010).
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
import re

from .common import AdapterError, iso_day

LABEL = 'IEX_LAST_REGULAR_TRADE_APPROX'
USE = 'S_SIGNAL_PRICE_APPROXIMATION_ONLY_NEVER_T_OPEN'
SOURCE = 'IEX HIST TOPS last regular-session trade (central V provider)'
CURRENCY = 'USD'
SUPPLIED = 'SUPPLIED'
ODD_LOT_ONLY = 'ODD_LOT_ONLY'
NO_IEX_TRADE = 'NO_IEX_TRADE'
UNMAPPED = 'UNMAPPED'
IEX_RESULT_MISSING_SYMBOL = 'IEX_RESULT_MISSING_SYMBOL'
IEX_DAY_NOT_SIGNAL_DAY = 'IEX_DAY_NOT_SIGNAL_DAY'
IEX_NOT_SUPPLIED = 'IEX_NOT_SUPPLIED'
STATUSES = (SUPPLIED, ODD_LOT_ONLY, NO_IEX_TRADE, UNMAPPED, IEX_RESULT_MISSING_SYMBOL, IEX_DAY_NOT_SIGNAL_DAY,
            IEX_NOT_SUPPLIED)
_FROM_PARSER = {'ROUND': SUPPLIED, 'ODD_ONLY': ODD_LOT_ONLY, 'NO_TRADE': NO_IEX_TRADE,
                SUPPLIED: SUPPLIED, ODD_LOT_ONLY: ODD_LOT_ONLY, NO_IEX_TRADE: NO_IEX_TRADE}
_SYMBOL = re.compile(r'[A-Z0-9][A-Z0-9.\-+=^]{0,7}')    # the provider's valid_symbol rule
MAX_PRICE_E4 = 10 ** 11                             # the provider's MAX_PRICE_E4: above is a parser fault, never a price


def _security(value):
    if not isinstance(value, str) or not value.strip():
        raise AdapterError('SECURITY_ID_INVALID')
    return value


def _quote(status, price=None):
    quote = {'price': price, 'currency': CURRENCY, 'month_closes': {}, 'price_label': LABEL}
    if status != SUPPLIED:
        quote['withheld_reason'] = status
    return quote


def _result(quotes, status):
    return {'quotes': dict(sorted(quotes.items())), 'status': dict(sorted(status.items())),
            'counts': dict(sorted(Counter(status.values()).items())), 'label': LABEL, 'use': USE}


def not_supplied(security_ids):
    """Every security withheld with IEX_NOT_SUPPLIED (no IEX result for S was given)."""
    status = {_security(sid): IEX_NOT_SUPPLIED for sid in security_ids}
    return _result({sid: _quote(code) for sid, code in status.items()}, status)


def _parser_entry(entry):
    """(status, Decimal price or None) of one parser row; AdapterError('IEX_RESULT_INVALID') when malformed."""
    if not isinstance(entry, (tuple, list)) or len(entry) != 2 or entry[0] not in _FROM_PARSER:
        raise AdapterError('IEX_RESULT_INVALID')
    status, px = _FROM_PARSER[entry[0]], entry[1]
    if status == NO_IEX_TRADE:
        return status, None
    if type(px) is not int or not 0 < px < MAX_PRICE_E4:
        raise AdapterError('IEX_RESULT_INVALID')
    return status, Decimal(px) / Decimal(10000)


def signal_quotes(rows, symbol_of, *, iex_day, signal_day):
    """S quote records from parser rows (module doc). iex_day: the IEX file's day; signal_day: S."""
    if not isinstance(rows, dict) or not isinstance(symbol_of, dict):
        raise AdapterError('IEX_RESULT_INVALID')
    parsed = {sym: _parser_entry(entry) for sym, entry in rows.items()}
    same_day = iso_day(iex_day) == iso_day(signal_day)
    quotes, status = {}, {}
    for sid, symbol in symbol_of.items():
        sid = _security(sid)
        if not same_day:
            code, price = IEX_DAY_NOT_SIGNAL_DAY, None
        elif not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol):
            code, price = UNMAPPED, None
        elif symbol not in parsed:
            code, price = IEX_RESULT_MISSING_SYMBOL, None
        else:
            code, price = parsed[symbol]
        if code != SUPPLIED:
            price = None                # an odd-lot price is not Last Sale Eligible: never used
        status[sid] = code
        quotes[sid] = _quote(code, price)
    return _result(quotes, status)


def signal_quotes_from_iex_day(iex_day, security_of_key, *, signal_day):
    """S quote records from the provider's IexDay held in RAM. Its quote price (a float price_e4 / 10000) is read through
    repr and rounded to 4 decimals, the precision of the IEX price; PRICE_SYMBOL_UNMAPPED maps to UNMAPPED and any other
    row-level code (ADR, split, identity rules of the central V) is withheld under its own code."""
    status_in, quotes_in = getattr(iex_day, 'status', None), getattr(iex_day, 'quotes', None)
    if not isinstance(status_in, dict) or not isinstance(quotes_in, dict) or not isinstance(security_of_key, dict):
        raise AdapterError('IEX_RESULT_INVALID')
    same_day = iso_day(getattr(iex_day, 'day', None)) == iso_day(signal_day)
    quotes, status = {}, {}
    for key, sid in security_of_key.items():
        sid = _security(sid)
        code = status_in.get(key)
        price = None
        if not same_day:
            code = IEX_DAY_NOT_SIGNAL_DAY
        elif code is None:
            code = IEX_RESULT_MISSING_SYMBOL
        elif code == 'PRICE_SYMBOL_UNMAPPED':
            code = UNMAPPED
        elif code == SUPPLIED:
            raw = (quotes_in.get(key) or {}).get('price')
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not 0 < raw < MAX_PRICE_E4 / 10000:
                raise AdapterError('IEX_RESULT_INVALID')
            price = Decimal(repr(raw)).quantize(Decimal('0.0001'))
        elif not isinstance(code, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{2,63}', code):
            raise AdapterError('IEX_RESULT_INVALID')
        status[sid] = code
        quotes[sid] = _quote(code, price)
    return _result(quotes, status)
