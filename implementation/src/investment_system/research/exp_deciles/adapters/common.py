"""Shared helpers of the EXP-STOCK-INDICATOR-DECILES-v1 input adapters (no network, no writes, no output)."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re

SUPPLIED = 'SUPPLIED'
UNKNOWN = 'UNKNOWN'
_CHUNK = 1 << 20
_CODE = re.compile(r'[A-Z][A-Z0-9_]{2,63}')


class AdapterError(ValueError):
    """Refused input. The message is an UPPER_SNAKE reason code."""


def code(value):
    """`value` when it is an UPPER_SNAKE reason code, else AdapterError (reason codes are fixed, never free text)."""
    if not isinstance(value, str) or not _CODE.fullmatch(value):
        raise AdapterError('REASON_CODE_INVALID')
    return value


def item(status, reasons=(), **fields):
    """One per-item status record {'status', 'reasons', ...}; UNKNOWN needs at least one reason code."""
    reasons = [code(r) for r in reasons]
    if status not in (SUPPLIED, UNKNOWN):
        raise AdapterError('ITEM_STATUS_INVALID')
    if status == UNKNOWN and not reasons:
        raise AdapterError('UNKNOWN_WITHOUT_REASON')
    return dict(fields, status=status, reasons=reasons)


def counts_by_status(items):
    """{'supplied': n, 'unknown': n, 'unknown_by_reason': {first reason: n}} of {key: item}."""
    supplied = sum(1 for i in items.values() if i['status'] == SUPPLIED)
    by_reason = Counter(i['reasons'][0] for i in items.values() if i['status'] == UNKNOWN)
    return {'supplied': supplied, 'unknown': len(items) - supplied, 'unknown_by_reason': dict(sorted(by_reason.items()))}


def cik10(value):
    """A CIK as 10 digits, or None when it is not a usable CIK (never guessed)."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    text = str(value).strip()
    if not text.isdigit() or len(text) > 10 or int(text) == 0:
        return None
    return text.zfill(10)


def iso_day(value):
    """date from a date or ISO text; AdapterError('DATE_INVALID') otherwise."""
    if isinstance(value, datetime):
        raise AdapterError('DATE_INVALID')
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise AdapterError('DATE_INVALID')


def compact_day(text):
    """date from YYYY-MM-DD or YYYYMMDD text, else None."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    if re.fullmatch(r'[0-9]{8}', text):
        text = f'{text[:4]}-{text[4:6]}-{text[6:]}'
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def positive_decimal(value):
    """A finite Decimal > 0 from an int, Decimal, finite float (through its repr) or decimal text; else None.

    None is the missing value: nothing is ever filled with 0."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        value = repr(value)
    if isinstance(value, (int, str, Decimal)):
        try:
            number = Decimal(value) if not isinstance(value, str) else Decimal(value.strip())
        except (InvalidOperation, ValueError):
            return None
        return number if number.is_finite() and number > 0 else None
    return None


def sha256_file(path):
    digest = hashlib.sha256()
    try:
        with open(path, 'rb') as handle:
            for block in iter(lambda: handle.read(_CHUNK), b''):
                digest.update(block)
    except OSError:
        raise AdapterError('SOURCE_FILE_NOT_READABLE') from None
    return digest.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(bytes(data)).hexdigest()


def json_exact(data):
    """JSON with every non-integer number as Decimal; NaN / Infinity refused."""
    def refuse(_value):
        raise AdapterError('NON_FINITE_NUMBER_IN_SOURCE')
    try:
        return json.loads(data.decode('utf-8') if isinstance(data, (bytes, bytearray)) else data,
                          parse_float=Decimal, parse_constant=refuse)
    except (UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, AdapterError):
            raise
        raise AdapterError('SOURCE_NOT_JSON') from None


def dumps(value):
    """Stable JSON bytes: sorted keys, Decimals as exact JSON numbers, dates as ISO text, one trailing newline."""
    def encode(o):
        if isinstance(o, Decimal):
            return f'@@D{o}@@'
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        raise TypeError(type(o).__name__)
    text = json.dumps(value, default=encode, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    return (re.sub(r'"@@D([-0-9.E+]+)@@"', r'\1', text) + '\n').encode('ascii')
