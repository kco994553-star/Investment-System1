"""Pure request limits shared by news and offline research; no I/O or provider imports."""
from datetime import datetime
from email.utils import parsedate_to_datetime

MAX_BODY_BYTES = 1024 * 1024


def retry_after_seconds(value, now):
    """Retry-After (delta-seconds or HTTP-date) -> seconds >= 0 from `now`, or None when absent or unreadable."""
    if not isinstance(value, str) or not value.strip() or len(value) > 64:
        return None
    text = value.strip()
    if text.isascii() and text.isdigit():
        return float(int(text))
    try:
        moment = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    if moment is None or moment.utcoffset() is None or not isinstance(now, datetime) or now.utcoffset() is None:
        return None
    return max(0.0, (moment - now).total_seconds())

