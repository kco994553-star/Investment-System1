"""Private IEX month-end store reader for V4 (v_vs_own_history) of the central V publication (GSQ-024). RAM only.

The store is the U8 one-off backfill output (tools/iex_hist/monthend_backfill.py): private release assets in the raw repository,
tags `iex-v4-monthend-YYYYMMDD-shard{0..N-1}`, each `<tag>.json.gz` + `<tag>.json.gz.sha256`, schema `iex-monthend/1`:
    {schema, months: {YYYY-MM: {date, md5, size, codes: {code: SYM}, symbols: {SYM: {status, price_e4, ts_ns, n}}}}, ...}
Values are IEX last regular-session trades AS TRADED (split-unadjusted). `month_closes` puts each on the latest share basis of
`ebit_per_share_history` by dividing by that history item's `share_basis_factor` F_k (rule V-PRICE-BASIS, calc_version
2026-10-23.1, read and validated by universe/sec_qgv2.require_qgv2: a positive factor, or null + share_basis_factor_reason in
v2_factors.SHARE_BASIS_REASONS):
    month close = raw / F_k;  F_k null / missing / not positive -> that month is left out (never 1.0), public reason = the item's
    SHARE_BASIS_UNCONFIRMED / SPLIT_TIMING_UNCONFIRMED, else SHARE_BASIS_FACTOR_NOT_AVAILABLE.
`raw_series` gives the same trades AS TRADED (no F_k) for the D6 (b) split check (owner decision CV-SPLIT (ii) 2026-10-24,
qgv_official.split_check). The U8 store (stamp 20261023) holds, per month, only the codes whose FISCAL-YEAR-END month it is, so
a code's latest store month is its latest FY-end month (0-15 months old), not last month.
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

from .. import public_price_boundary as boundary
from ..qgv.v2_factors import SHARE_BASIS_REASONS
from .iex_hist import MONTHEND_BASIS_CUTS, SYMBOL_ALIASES, iex_symbol

SCHEMA = 'iex-monthend/1'
TAG_PREFIX = 'iex-v4-monthend-'
RAW_REPO = 'kco994553-star/investment-system1-raw'
API = 'https://api.github.com'
FK_MISSING = 'SHARE_BASIS_FACTOR_NOT_AVAILABLE'
MONTH_PRICE_MISSING = 'MONTH_END_PRICE_NOT_AVAILABLE'
SYMBOL_MISMATCH = 'MONTH_END_SYMBOL_MISMATCH'
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
    """(method, url, headers, auth) -> (status, headers, bytes). The store holds IEX trades, so the reader exists only inside
    the approved price route (public_price_boundary.require_price_route: ROUTE_NOT_ALLOWED otherwise), and the Bearer token
    goes only to the store's release URLs (public_price_boundary IEX_MONTHEND_STORE: TOKEN_HOST_INVALID otherwise)."""
    try:
        boundary.require_price_route()
    except boundary.PublicPriceBoundaryError:
        _fail('ROUTE_NOT_ALLOWED')
    opener = urllib.request.build_opener(_NoRedirect)

    def call(method, url, *, headers=None, auth=True):
        req = urllib.request.Request(url, method=method)
        req.add_header('Accept', (headers or {}).get('Accept', 'application/vnd.github+json'))
        req.add_header('X-GitHub-Api-Version', '2022-11-28')
        if auth:
            if boundary.price_source_kind(url) != 'IEX_MONTHEND_STORE':
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
    """(F_k, None) or (None, public reason) of one ebit_per_share_history item: the item's own V-PRICE-BASIS reason
    (v2_factors.SHARE_BASIS_REASONS) when it has one, else SHARE_BASIS_FACTOR_NOT_AVAILABLE."""
    f = item.get('share_basis_factor') if isinstance(item, dict) else None
    if type(f) in (int, float) and type(f) is not bool and math.isfinite(f) and f > 0:
        return float(f), None
    reason = item.get('share_basis_factor_reason') if isinstance(item, dict) else None
    return None, reason if reason in SHARE_BASIS_REASONS else FK_MISSING


def priceable_months(code: str, history, *, cuts=MONTHEND_BASIS_CUTS) -> list[str]:
    """The price-free part of month_closes: months (YYYY-MM) of the raw history items with a finite value, a valid
    fiscal_year_end, not before the code's basis cut and with a positive F_k. Only these months can get a close; reads no price."""
    out = []
    cut = cuts.get(code)
    for item in history if isinstance(history, list) else ():
        fe = item.get('fiscal_year_end') if isinstance(item, dict) else None
        value = item.get('value') if isinstance(item, dict) else None
        if not (isinstance(fe, str) and _DAY.fullmatch(fe)) or (cut and fe < cut[0]) or _factor(item)[0] is None:
            continue
        if type(value) in (int, float) and type(value) is not bool and math.isfinite(value):
            out.append(fe[:7])
    return out


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


def raw_series(code: str, months: dict, since_month: str, until_day: str, *, aliases=SYMBOL_ALIASES) -> list[tuple[str, float]]:
    """[(YYYY-MM-DD trade date, raw price)] of one Universe code's month-end trades AS TRADED (price_e4 / 10000, NO F_k
    division), for the store months from `since_month` (YYYY-MM, inclusive) on whose trade date is not after `until_day`
    (YYYY-MM-DD), sorted by date. Owner decision CV-SPLIT (ii) 2026-10-24, the D6 (b) split check
    (qgv_official.split_check). The symbol / alias and ROUND rules are month_closes': a month whose store symbol differs from
    the alias table's (or whose alias is None), or without a round-lot trade of that symbol, is left out, never 0. The basis
    cut (MONTHEND_BASIS_CUTS) is a V4 share-basis rule and is not applied here: a pair across it can only add a hit (withhold
    a value), never hide one. RAM only."""
    out = []
    for name in sorted(months) if isinstance(months, dict) else ():
        m = months[name]
        if not (isinstance(name, str) and _MONTH.fullmatch(name)) or name < since_month or not isinstance(m, dict):
            continue
        date, codes, symbols = m.get('date'), m.get('codes'), m.get('symbols')
        if not (isinstance(date, str) and re.fullmatch(r'\d{8}', date)) or not isinstance(codes, dict) or not isinstance(symbols, dict):
            continue
        day = f'{date[:4]}-{date[4:6]}-{date[6:]}'
        if day > until_day:
            continue
        sym = iex_symbol(code, date, aliases)
        if sym is None or codes.get(code, sym) != sym:
            continue
        row = symbols.get(sym)
        px = row.get('price_e4') if isinstance(row, dict) else None
        if not isinstance(row, dict) or row.get('status') != 'ROUND' or type(px) is not int or px <= 0:
            continue
        out.append((day, px / 10000))
    return sorted(out)


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
