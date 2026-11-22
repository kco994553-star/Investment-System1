"""Canonical digest and date parsing for versioned classification records."""
import hashlib
import json
from datetime import date, datetime


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def timestamp(value):
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('TIMEZONE_REQUIRED')
    return t


def day(value):
    if not isinstance(value,str) or len(value)!=10: raise ValueError('INVALID_DATE')
    return date.fromisoformat(value)
