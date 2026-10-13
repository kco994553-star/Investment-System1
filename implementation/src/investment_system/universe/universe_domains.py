"""Public company-domain list for logos (Pages file ``universe-domains.json``).

Domains only: one row per Universe504 code (``universe_codes_v1.json`` order) plus the two non-US TARGET
listings, each ``[code, domain | null, source | null]`` with source ``sec`` / ``wikidata`` / ``manual``.
Unknown stays null, never guessed. The browser uses a domain only to ask a logo or favicon service for an
image at runtime; no logo file is stored in the repository or in Pages.

Source priority: SEC submissions ``website`` > Wikidata P856 (official website) joined on P5531 (SEC CIK,
CC0) > the reviewed in-repo ``manual`` rows in ``universe_domains_v1.json``.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .universe_codes import source_codes

FILENAME = 'universe-domains.json'
SCHEMA = 'universe-domains/1'
SOURCES = ('sec', 'wikidata', 'manual')
REVIEWED = Path(__file__).with_name('universe_domains_v1.json')
# TARGET listings outside Universe504 (same code formats as universe_codes: KRX 6-digit, TYO 4-digit).
EXTRA_CODES = ('KRX:042700', 'TYO:8035')
MAX_BYTES = 256 * 1024
_DOMAIN = re.compile(r'(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}')


def all_codes() -> list[str]:
    return [*source_codes(), *EXTRA_CODES]


def normalize_domain(value):
    """URL or host -> lower-case host without 'www.'; None when it is not a plain public host name."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > 2048 or any(ch.isspace() for ch in text):
        return None
    if '://' not in text:
        text = 'https://' + text
    try:
        parts = urlsplit(text)
        host = parts.hostname
        if parts.scheme not in ('http', 'https') or parts.username or parts.password or parts.port is not None:
            return None
    except ValueError:
        return None
    if not host:
        return None
    host = host.rstrip('.').lower()
    if host.startswith('www.'):
        host = host[4:]
    return host if _DOMAIN.fullmatch(host) else None


def reviewed_rows() -> dict:
    """{code: (domain, source)} from the reviewed in-repo list (manual or a reviewed Wikidata export)."""
    value = json.loads(REVIEWED.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or set(value) != {'schema', 'rows'} or value['schema'] != 'universe-domains-source/1':
        raise ValueError('universe domains source envelope')
    codes = set(all_codes())
    out = {}
    for code, row in value['rows'].items():
        if code not in codes or not isinstance(row, dict) or set(row) != {'domain', 'source'}:
            raise ValueError('universe domains source row')
        if row['source'] not in ('wikidata', 'manual') or normalize_domain(row['domain']) != row['domain']:
            raise ValueError('universe domains source value')
        out[code] = (row['domain'], row['source'])
    return out


def merge(*, reviewed=None, previous=None, sec=None, sec_checked=(), wikidata=None):
    """Priority sec > wikidata > manual. Values: {code: domain}.

    ``previous`` (last published payload) keeps SEC rows for codes not checked today, and Wikidata rows when
    today's Wikidata query did not run (``wikidata is None``). Returns {code: (domain, source) | None}.
    """
    reviewed = reviewed_rows() if reviewed is None else reviewed
    prev = {code: (domain, source) for code, domain, source in previous['rows'] if domain} if previous else {}
    checked = set(sec_checked)
    sec_rows = {c: d for c, (d, s) in prev.items() if s == 'sec' and c not in checked}
    sec_rows.update({c: d for c, d in (sec or {}).items() if d})
    wiki_rows = {c: d for c, (d, s) in prev.items() if s == 'wikidata'} if wikidata is None else {c: d for c, d in wikidata.items() if d}
    out = {}
    for code in all_codes():
        if code in sec_rows:
            out[code] = (sec_rows[code], 'sec')
        elif code in wiki_rows:
            out[code] = (wiki_rows[code], 'wikidata')
        elif code in reviewed:
            out[code] = reviewed[code]
        else:
            out[code] = None
    return out


def public_payload(rows=None) -> dict:
    rows = merge() if rows is None else rows
    payload = {'schema': SCHEMA, 'rows': [[code, *(rows.get(code) or (None, None))] for code in all_codes()]}
    require_universe_domains(payload)
    return payload


def counts(payload) -> dict:
    out = {source: 0 for source in SOURCES}
    out['empty'] = 0
    for _code, _domain, source in payload['rows']:
        out[source or 'empty'] += 1
    return out


def require_universe_domains(value) -> None:
    """Strict: exactly {schema, rows}; every approved code once, in order; domain/source both set or both null."""
    if not isinstance(value, dict) or set(value) != {'schema', 'rows'} or value['schema'] != SCHEMA:
        raise ValueError('universe domains envelope')
    rows = value['rows']
    if not isinstance(rows, list) or [r[0] if isinstance(r, list) and r else None for r in rows] != all_codes():
        raise ValueError('universe domains codes')
    for row in rows:
        if len(row) != 3:
            raise ValueError('universe domains row')
        _code, domain, source = row
        if domain is None and source is None:
            continue
        if source not in SOURCES or not isinstance(domain, str) or normalize_domain(domain) != domain:
            raise ValueError('universe domains value')
