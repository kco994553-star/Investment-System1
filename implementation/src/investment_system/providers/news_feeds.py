"""News-signal sources: GDELT DOC 2.0 artlist JSON and official company IR press-release RSS/Atom feeds.

Importing this module performs no requests or environment lookup. Only fixed URLs are requested:
one GDELT DOC query per company (built from product.news_signals.MATCH) and the IR feed URLs in
product.news_signals.IR_FEEDS. Redirects are refused, bodies are size-capped, XML with a DOCTYPE
or entity declaration is rejected before parsing. Only title, link and time are read from each
article/item; descriptions, bodies and images are ignored. Errors carry fixed codes only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import json
import math
import re
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree

from ..product.news_signals import IR_FEEDS, MATCH, QUERY_DAYS

GDELT_API = 'https://api.gdeltproject.org/api/v2/doc/doc'
GDELT_MIN_INTERVAL = 5.5  # GDELT asks for at most one request every 5 seconds
GDELT_MAX_RECORDS = 75
GDELT_KEEP_PER_COMPANY = 15
GDELT_REQUEST_BUDGET = 40
IR_MIN_INTERVAL = 1.0
IR_REQUEST_BUDGET = 20
IR_KEEP_PER_FEED = 20
MAX_BODY_BYTES = 1024 * 1024
REQUEST_TIMEOUT = 30
MAX_ATTEMPTS = 2
RETRY_WAIT = 10.0
# 429 / 5xx: one retry after RETRY_WAIT, or after the server's Retry-After when it is longer. A Retry-After above
# MAX_RETRY_AFTER is honoured by not retrying in this run (no further request). Never more attempts, budget or parallelism.
MAX_RETRY_AFTER = 60.0
USER_AGENT = 'Investment-System1 news-signals/1 (+https://github.com/kco994553-star/Investment-System1)'
XML_ITEMS_MAX = 200


class NewsFetchError(Exception):
    """Fixed code only, never an upstream message or URL."""


@dataclass(frozen=True)
class NewsResponse:
    status: int
    body: bytes = field(repr=False)
    final_url: str = field(repr=False)
    retry_after: str | None = field(default=None, repr=False)  # raw Retry-After header of an error response


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


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise NewsFetchError('REDIRECT_REJECTED') from None


def gdelt_url(company_id):
    rule = MATCH[company_id]
    return GDELT_API + '?' + urlencode({'query': rule['query'] + ' sourcelang:english', 'mode': 'artlist', 'format': 'json',
                                        'maxrecords': str(GDELT_MAX_RECORDS), 'timespan': f'{QUERY_DAYS}d',
                                        'sort': 'hybridrel'})


ALLOWED_URLS = frozenset([gdelt_url(cid) for cid in MATCH] + [f['url'] for f in IR_FEEDS.values()])


def default_transport(url, *, headers, timeout, max_body_bytes):
    """Fixed GDELT and IR feed URLs only, no redirects, bounded body; error bodies are not read."""
    if url not in ALLOWED_URLS:
        raise NewsFetchError('URL_NOT_ALLOWED') from None
    if (type(max_body_bytes) is not int or not 0 < max_body_bytes <= 4 * MAX_BODY_BYTES
            or type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= REQUEST_TIMEOUT):
        raise NewsFetchError('CONFIG_INVALID') from None
    try:
        with build_opener(_RejectRedirects()).open(Request(url, headers=dict(headers)), timeout=timeout) as response:
            body = response.read(max_body_bytes + 1)
            if len(body) > max_body_bytes:
                raise NewsFetchError('RESPONSE_TOO_LARGE') from None
            return NewsResponse(response.status, body, response.geturl())
    except HTTPError as error:
        header = error.headers.get('Retry-After') if error.headers is not None else None
        return NewsResponse(error.code, b'', error.geturl(), header if isinstance(header, str) else None)


class PacedClient:
    """Serial GET of allowed URLs with a minimum interval, a per-run request budget and one retry."""

    def __init__(self, *, min_interval, budget, transport: Callable = default_transport, sleep: Callable = time.sleep,
                 monotonic: Callable = time.monotonic, now: Callable = lambda: datetime.now(timezone.utc)):
        self._interval, self._budget, self._transport = float(min_interval), int(budget), transport
        self._sleep, self._time, self._now = sleep, monotonic, now
        self._last = None
        self.used = 0

    def _pace(self):
        if self._last is not None:
            wait = self._last + self._interval - self._time()
            if wait > 0:
                self._sleep(wait)
        self._last = self._time()

    def get(self, url, *, accept):
        """Body bytes and the UTC acquisition time; NewsFetchError(code) otherwise."""
        if url not in ALLOWED_URLS:
            raise NewsFetchError('URL_NOT_ALLOWED')
        for attempt in range(MAX_ATTEMPTS):
            if self.used >= self._budget:
                raise NewsFetchError('BUDGET_EXHAUSTED')
            self._pace()
            self.used += 1
            try:
                response = self._transport(url, headers={'User-Agent': USER_AGENT, 'Accept': accept},
                                           timeout=REQUEST_TIMEOUT, max_body_bytes=MAX_BODY_BYTES)
            except NewsFetchError as error:
                code = error.args[0] if error.args else 'TRANSPORT_FAILED'
                raise NewsFetchError(code if code in ('REDIRECT_REJECTED', 'RESPONSE_TOO_LARGE', 'URL_NOT_ALLOWED',
                                                      'CONFIG_INVALID') else 'TRANSPORT_FAILED') from None
            except (URLError, OSError):
                if attempt == MAX_ATTEMPTS - 1:
                    raise NewsFetchError('TRANSPORT_FAILED') from None
                self._sleep(RETRY_WAIT)
                continue
            except Exception:
                raise NewsFetchError('TRANSPORT_FAILED') from None
            if (not isinstance(response, NewsResponse) or type(response.status) is not int or not isinstance(response.body, bytes)
                    or response.final_url != url or len(response.body) > MAX_BODY_BYTES):
                raise NewsFetchError('RESPONSE_INVALID')
            if response.status == 200:
                at = self._now()
                if not isinstance(at, datetime) or at.utcoffset() is None:
                    raise NewsFetchError('CLOCK_INVALID')
                return response.body, at.astimezone(timezone.utc)
            if response.status in (429, 500, 502, 503, 504) and attempt < MAX_ATTEMPTS - 1:
                asked = retry_after_seconds(response.retry_after, self._now())
                if asked is None or asked <= MAX_RETRY_AFTER:
                    self._sleep(max(RETRY_WAIT, asked or 0.0))
                    continue
            raise NewsFetchError('HTTP_429' if response.status == 429 else 'HTTP_FAILED')
        raise NewsFetchError('TRANSPORT_FAILED')


# --- GDELT ---------------------------------------------------------------------------------------

_SEENDATE = re.compile(r'([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2})([0-9]{2})([0-9]{2})Z')


def _seendate(value):
    match = _SEENDATE.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        return None
    try:
        return datetime(*map(int, match.groups()), tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_gdelt(body):
    """artlist JSON -> raw rows [{'title','link','published_at'}] in GDELT order; ValueError(code) if not JSON.

    GDELT answers some errors (rate limit, bad query) with plain text and status 200.
    """
    try:
        text = body.decode('utf-8')
    except UnicodeError:
        raise ValueError('GDELT_RESPONSE_INVALID') from None
    if not text.strip():
        return []
    if 'limit requests' in text.lower() and not text.lstrip().startswith('{'):
        raise ValueError('GDELT_RATE_LIMITED')
    try:
        data = json.loads(text, strict=False)
    except (ValueError, RecursionError):
        raise ValueError('GDELT_RESPONSE_INVALID') from None
    if not isinstance(data, dict):
        raise ValueError('GDELT_RESPONSE_INVALID')
    articles = data.get('articles', [])
    if not isinstance(articles, list):
        raise ValueError('GDELT_RESPONSE_INVALID')
    rows = []
    for a in articles[:GDELT_MAX_RECORDS]:
        if not isinstance(a, dict):
            continue
        title = a.get('title')
        rows.append({'title': html.unescape(title) if isinstance(title, str) else None, 'link': a.get('url'),
                     'published_at': _seendate(a.get('seendate'))})
    return rows


# --- IR RSS / Atom ---------------------------------------------------------------------------------

_ATOM = '{http://www.w3.org/2005/Atom}'
_FORBIDDEN_XML = re.compile(rb'<!(?:DOCTYPE|ENTITY)', re.I)


def _local(tag):
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def _text(node):
    return ''.join(node.itertext()) if node is not None else None


def _rss_date(value):
    try:
        moment = parsedate_to_datetime((value or '').strip())
    except (TypeError, ValueError, IndexError):
        return None
    return moment.astimezone(timezone.utc) if moment is not None and moment.utcoffset() is not None else None


def _iso_date(value):
    try:
        moment = datetime.fromisoformat((value or '').strip().replace('Z', '+00:00'))
    except ValueError:
        return None
    return moment.astimezone(timezone.utc) if moment.utcoffset() is not None else None


def parse_feed(body):
    """RSS 2.0 or Atom bytes -> raw rows [{'title','link','published_at'}]; ValueError('IR_FEED_INVALID').

    No DTD, no entity declarations, size-capped by the client; only title, link and date are read.
    """
    if not isinstance(body, bytes) or len(body) > MAX_BODY_BYTES or _FORBIDDEN_XML.search(body):
        raise ValueError('IR_FEED_INVALID')
    try:
        root = ElementTree.fromstring(body)
    except (ElementTree.ParseError, ValueError, RecursionError):
        raise ValueError('IR_FEED_INVALID') from None
    rows = []
    if _local(root.tag) == 'rss':
        channel = root.find('channel')
        if channel is None:
            raise ValueError('IR_FEED_INVALID')
        for item in channel.findall('item')[:XML_ITEMS_MAX]:
            rows.append({'title': _text(item.find('title')), 'link': (_text(item.find('link')) or '').strip(),
                         'published_at': _rss_date(_text(item.find('pubDate')))})
    elif root.tag == _ATOM + 'feed':
        for entry in root.findall(_ATOM + 'entry')[:XML_ITEMS_MAX]:
            link = None
            for node in entry.findall(_ATOM + 'link'):
                if node.get('rel', 'alternate') == 'alternate':
                    link = node.get('href')
                    break
            rows.append({'title': _text(entry.find(_ATOM + 'title')), 'link': link,
                         'published_at': _iso_date(_text(entry.find(_ATOM + 'published')) or _text(entry.find(_ATOM + 'updated')))})
    else:
        raise ValueError('IR_FEED_INVALID')
    return rows
