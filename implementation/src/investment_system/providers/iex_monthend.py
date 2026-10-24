"""Private IEX month-end store reader for V4 (v_vs_own_history) of the central V publication (GSQ-024). RAM only.

The store is the U8 one-off backfill output (tools/iex_hist/monthend_backfill.py): private release assets in the raw repository,
tags `iex-v4-monthend-YYYYMMDD-shard{0..N-1}`, each `<tag>.json.gz` + `<tag>.json.gz.sha256`, schema `iex-monthend/1`:
    {schema, months: {YYYY-MM: {date, md5, size, codes: {code: SYM}, symbols: {SYM: {status, price_e4, ts_ns, n}}}}, ...}
Values are IEX last regular-session trades AS TRADED (split-unadjusted). `month_closes` puts each on the latest share basis of
`ebit_per_share_history` by dividing by that history item's `share_basis_factor` F_k (calc_version lane cv-fk):
    month close = raw / F_k;  F_k missing / null / not positive -> that month is left out (never 1.0).
Nothing is printed, logged or written; errors are fixed codes raised `from None`. The token is passed in by the caller (the
environment variable name is the caller's argument); it is never printed.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request

from .iex_hist import MONTHEND_BASIS_CUTS, SYMBOL_ALIASES, iex_symbol

SCHEMA = 'iex-monthend/1'
TAG_PREFIX = 'iex-v4-monthend-'
RAW_REPO = 'kco994553-star/investment-system1-raw'
API = 'https://api.github.com'
FK_MISSING = 'SHARE_BASIS_FACTOR_NOT_AVAILABLE'
MONTH_PRICE_MISSING = 'MONTH_END_PRICE_NOT_AVAILABLE'
SYMBOL_MISMATCH = 'MONTH_END_SYMBOL_MISMATCH'
_REASON = re.compile(r'[A-Z0-9_]+', re.ASCII)
_MONTH = re.compile(r'\d{4}-\d{2}', re.ASCII)
_DAY = re.compile(r'\d{4}-\d{2}-\d{2}', re.ASCII)


class MonthEndError(RuntimeError):
    """Fixed code only."""


def _fail(code):
    raise MonthEndError(code) from None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def github_call(token: str):
    """(method, url, headers, auth) -> (status, headers, bytes). Bearer token only on api.github.com requests."""
    opener = urllib.request.build_opener(_NoRedirect)

    def call(method, url, *, headers=None, auth=True):
        req = urllib.request.Request(url, method=method)
        req.add_header('Accept', (headers or {}).get('Accept', 'application/vnd.github+json'))
        req.add_header('X-GitHub-Api-Version', '2022-11-28')
        if auth:
            if urllib.parse.urlsplit(url).hostname != 'api.github.com':
                _fail('TOKEN_HOST_INVALID')
            req.add_header('Authorization', 'Bearer ' + token)
        try:
            with opener.open(req, timeout=300) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers or {}), b''
        except Exception:  # noqa: BLE001
            _fail('STORE_UNAVAILABLE')
    return call


def tag_for(stamp: str, shard: int) -> str:
    if not (isinstance(stamp, str) and re.fullmatch(r'\d{8}', stamp)):
        _fail('STAMP_INVALID')
    return f'{TAG_PREFIX}{stamp}-shard{shard}'


def read_shard(tag: str, call, repo=RAW_REPO) -> dict:
    status, _, body = call('GET', f'{API}/repos/{repo}/releases/tags/{urllib.parse.quote(tag)}')
    if status != 200:
        _fail('RELEASE_NOT_FOUND')
    try:
        release = json.loads(body)
    except ValueError:
        _fail('RELEASE_INVALID')

    def asset(name):
        found = next((a for a in release.get('assets', []) if isinstance(a, dict) and a.get('name') == name), None)
        if not found or type(found.get('id')) is not int:
            _fail('ASSET_MISSING')
        st, headers, data = call('GET', f'{API}/repos/{repo}/releases/assets/{found["id"]}', headers={'Accept': 'application/octet-stream'})
        if st in (301, 302, 303, 307, 308):
            location = (headers or {}).get('Location') or (headers or {}).get('location')
            if not location or urllib.parse.urlsplit(location).scheme != 'https':
                _fail('ASSET_REDIRECT_INVALID')
            st, _, data = call('GET', location, headers={'Accept': 'application/octet-stream'}, auth=False)
        if st != 200:
            _fail('ASSET_UNREADABLE')
        return bytes(data)

    name = tag + '.json.gz'
    data = asset(name)
    if asset(name + '.sha256') != f'{hashlib.sha256(data).hexdigest()}  {name}\n'.encode('ascii'):
        _fail('SHA256_MISMATCH')
    try:
        body = json.loads(gzip.decompress(data))
    except Exception:  # noqa: BLE001
        _fail('SHARD_INVALID')
    return body


def _require_month(m) -> None:
    if not isinstance(m, dict) or not (isinstance(m.get('date'), str) and re.fullmatch(r'\d{8}', m['date'])):
        _fail('SHARD_INVALID')
    if not isinstance(m.get('codes'), dict) or not isinstance(m.get('symbols'), dict):
        _fail('SHARD_INVALID')
    for row in m['symbols'].values():
        if not isinstance(row, dict) or row.get('status') not in ('ROUND', 'ODD_ONLY', 'NO_TRADE'):
            _fail('SHARD_INVALID')
        px = row.get('price_e4')
        if row['status'] == 'NO_TRADE':
            if px is not None:
                _fail('SHARD_INVALID')
        elif type(px) is not int or px <= 0:
            _fail('SHARD_INVALID')


def merge_shards(bodies) -> dict:
    """{YYYY-MM: month} of all shards; schema checked, a month in two shards is invalid."""
    months = {}
    for body in bodies:
        if not isinstance(body, dict) or body.get('schema') != SCHEMA or not isinstance(body.get('months'), dict):
            _fail('SHARD_INVALID')
        for name, m in body['months'].items():
            if not (isinstance(name, str) and _MONTH.fullmatch(name)) or name in months:
                _fail('SHARD_INVALID')
            _require_month(m)
            months[name] = m
    return months


def read_store(stamp: str, shards: int, call, repo=RAW_REPO) -> dict:
    if type(shards) is not int or not 1 <= shards <= 64:
        _fail('SHARDS_INVALID')
    return merge_shards(read_shard(tag_for(stamp, i), call, repo) for i in range(shards))


def _factor(item):
    """(F_k, None) or (None, public reason) of one ebit_per_share_history item."""
    f = item.get('share_basis_factor') if isinstance(item, dict) else None
    if type(f) in (int, float) and math.isfinite(f) and f > 0:
        return float(f), None
    reason = item.get('share_basis_factor_reason') if isinstance(item, dict) else None
    return None, reason if isinstance(reason, str) and _REASON.fullmatch(reason) else FK_MISSING


def month_closes(code: str, history, months: dict, *, aliases=SYMBOL_ALIASES, cuts=MONTHEND_BASIS_CUTS):
    """({YYYY-MM: raw/F_k}, [(YYYY-MM, reason)] left out) for one Universe code's raw `ebit_per_share_history` items.

    A month is left out (reason) when: before the code's basis cut (cut reason); F_k missing (its fixed reason, else
    SHARE_BASIS_FACTOR_NOT_AVAILABLE); the store has no round-lot month-end trade (MONTH_END_PRICE_NOT_AVAILABLE); the store's
    symbol differs from the alias table's (MONTH_END_SYMBOL_MISMATCH). RAM only."""
    closes, left = {}, []
    cut = cuts.get(code)
    for item in history if isinstance(history, list) else ():
        fe = item.get('fiscal_year_end') if isinstance(item, dict) else None
        if not (isinstance(fe, str) and _DAY.fullmatch(fe)):
            continue
        month = fe[:7]
        if cut and fe < cut[0]:
            left.append((month, cut[1]))
            continue
        factor, reason = _factor(item)
        if factor is None:
            left.append((month, reason))
            continue
        m = months.get(month)
        if not isinstance(m, dict):
            left.append((month, MONTH_PRICE_MISSING))
            continue
        sym = iex_symbol(code, m['date'], aliases)
        if sym is None or m['codes'].get(code, sym) != sym:
            left.append((month, SYMBOL_MISMATCH))
            continue
        row = m['symbols'].get(sym)
        if not isinstance(row, dict) or row.get('status') != 'ROUND':
            left.append((month, MONTH_PRICE_MISSING))
            continue
        closes[month] = row['price_e4'] / 10000 / factor
    return closes, left


def public_v4_reason(left) -> str | None:
    """Public V4 reason when V4 is NOT_AVAILABLE because months were left out: the basis cut first, then the F_k reason."""
    reasons = [r for _, r in left]
    for r in reasons:
        if r in {c[1] for c in MONTHEND_BASIS_CUTS.values()}:
            return r
    for r in reasons:
        if r not in (MONTH_PRICE_MISSING, SYMBOL_MISMATCH):
            return r
    return None
