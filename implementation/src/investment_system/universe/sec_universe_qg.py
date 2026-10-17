"""Price-free public SEC Q·G factor projection for the approved Universe504 codes.

User queue 2.1 (SEC Universe504 daily collection): the daily Universe shard already
fetches companyfacts + submissions for its issuers. The SAME bytes also produce the
price-free Q·G factor scores, through the exact path used for the TARGET
`sec-qg-factors.json` (``public_engine_screens.qg_factor_scores``: SEC M1 admission
-> M2 mapping view -> ``qgv.raw_map.map_raw``). Same 13 Q/G factors, same weights
(applied later by the reader, never here), same NOT_AVAILABLE semantics: a factor
without a score is null (NOT_AVAILABLE), never 0; a scored factor shares its row's
LIVE/STALE state, so the factor map stores only the score. No V, no price, no rank.

Rows are keyed by Universe code (an issuer's codes carry the same row) and merged
into the previously published copy like `sec-universe-shares.json`: each row keeps
its own acquired_at, a new row without scores never erases a kept one, and rows past
the shared v0 stale window (sec-universe-shares/v0, DEFAULT_V0_UNCALIBRATED) are STALE.
"""
from datetime import timedelta, timezone
import hashlib
import json
import math
import re

from .sec_universe_shares import IDENTITY_CONFLICT, PRESERVE, _clock, _hash, _iso, load_config, note, previous_decision, universe_codes

FILENAME = 'sec-universe-qg.json'
KIND = 'SEC_UNIVERSE_QG'
MAX_BYTES = 2 * 1024 * 1024
STATES = ('LIVE', 'STALE', 'NOT_AVAILABLE')
METHOD_STATUS = 'PROVISIONAL_UNCALIBRATED'
AVAILABILITY_BASIS = 'OBSERVED_CAPTURE_ONLY'
REASONS = ('NOT_COLLECTED', 'CIK_UNRESOLVED', 'INVALID_INPUT', 'M1_NOT_AVAILABLE', 'UNRESOLVED_CURRENT_FACT_AMBIGUITY',
           'QG_NOT_AVAILABLE', 'STALE_INPUT')
TOP_REASONS = ('STALE_INPUT', 'NO_ELIGIBLE_INPUT')
RECORD_KEYS = ('cik', 'acquired_at', 'source_sha256', 'factors', 'state', 'reason_codes')
HASH_KEYS = ('companyfacts', 'submissions')
TOP_KEYS = ('schema_version', 'kind', 'as_of', 'config_version', 'config_status', 'method_status', 'availability_basis',
            'freshness_basis', 'stale_after_seconds', 'shard_count', 'last_shard_index', 'registry_sha256', 'code_count',
            'state', 'reason_codes', 'records')


def _factors():
    from ..qgv.factors import G_WEIGHTS, Q_WEIGHTS
    return tuple(sorted(set(Q_WEIGHTS) | set(G_WEIGHTS)))


FACTORS = _factors()


def _need(condition):
    if not condition:
        raise ValueError('SEC_UNIVERSE_QG_INVALID')


def _score(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 100
    except OverflowError:
        return False


def empty_record(*, cik=None, reasons=('NOT_COLLECTED',)):
    return {'cik': cik, 'acquired_at': None, 'source_sha256': {'companyfacts': None, 'submissions': None},
            'factors': dict.fromkeys(FACTORS),
            'state': 'NOT_AVAILABLE', 'reason_codes': list(reasons)}


def _scored(record):
    return any(score is not None for score in record['factors'].values())


def build_issuer_row(*, cik, companyfacts_body, submissions_body, acquired_at):
    """One issuer's row from the bytes the shard already fetched. Untrusted content -> NOT_AVAILABLE with a fixed reason."""
    from ..product.public_engine_screens import parse_json, qg_factor_scores
    from ..providers.sec_m1 import build_universe_input
    if type(cik) is not str or re.fullmatch(r'[0-9]{10}', cik) is None or cik == '0000000000':
        return empty_record(reasons=('INVALID_INPUT',))
    record = empty_record(cik=cik, reasons=('INVALID_INPUT',))
    if type(companyfacts_body) is not bytes or type(submissions_body) is not bytes or getattr(acquired_at, 'utcoffset', lambda: None)() is None:
        return record
    record.update(acquired_at=_iso(acquired_at), source_sha256={'companyfacts': hashlib.sha256(companyfacts_body).hexdigest(),
                                                                 'submissions': hashlib.sha256(submissions_body).hexdigest()})
    try:
        m1 = build_universe_input(cik, parse_json(companyfacts_body), parse_json(submissions_body), acquired_at, acquired_at)
        _, scores, reason = qg_factor_scores('sec_' + cik, m1)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, UnicodeError):
        return record
    if scores is None:
        record['reason_codes'] = [reason]
        return record
    for fid in FACTORS:
        if _score(scores.get(fid)) and type(scores[fid]) is not bool:
            record['factors'][fid] = scores[fid]
    if not _scored(record):
        record['reason_codes'] = ['QG_NOT_AVAILABLE']
        return record
    record.update(state='LIVE', reason_codes=[])
    return record


def build_issuer_records(*, codes, cik, companyfacts_body, submissions_body, acquired_at):
    """Every Universe code of one issuer carries the issuer's row."""
    row = build_issuer_row(cik=cik, companyfacts_body=companyfacts_body, submissions_body=submissions_body, acquired_at=acquired_at)
    return {code: json.loads(json.dumps(row)) for code in codes}


def restate(record, as_of, stale_after):
    """Freshness from the row's own acquisition time; scores are never changed."""
    out = json.loads(json.dumps(record))
    reasons = [r for r in out['reason_codes'] if r != 'STALE_INPUT']
    if not _scored(out):
        out['state'] = 'NOT_AVAILABLE'
        out['reason_codes'] = reasons or ['QG_NOT_AVAILABLE']
        return out
    fresh = as_of.astimezone(timezone.utc) - _clock(out['acquired_at']) <= stale_after
    out['state'] = 'LIVE' if fresh else 'STALE'
    out['reason_codes'] = [] if fresh else ['STALE_INPUT']
    return out


def merge(previous, updates, *, as_of, shard_index, registry_sha256=None, unresolved=(), config=None, conflicts=(), stats=None):
    """Previous published rows + this shard's rows (same rules as the Universe shares merge, including
    `previous_decision`: a row without its own collection record is no new observation)."""
    cfg = config or load_config()
    stale_after = timedelta(days=cfg['stale_after_days'])
    cut = _clock(_iso(as_of))
    kept = previous['records'] if previous is not None else {}
    records = {}
    for code in universe_codes():
        old = kept.get(code) or empty_record()
        new = updates.get(code)
        if new is not None:
            try:
                _record(restate(new, as_of, stale_after), cut, stale_after)
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
                cik = new.get('cik') if type(new) is dict else None
                new = empty_record(cik=cik if type(cik) is str and re.fullmatch(r'[0-9]{10}', cik) and cik != '0000000000' else None,
                                   reasons=('INVALID_INPUT',))
        decision = previous_decision(old, new, code=code, unresolved=unresolved, conflicts=conflicts,
                                     new_observation=lambda r: r['acquired_at'] is not None)
        note(stats, decision, code, old)
        if decision == PRESERVE:
            pass
        elif new is not None and (decision == IDENTITY_CONFLICT or not (not _scored(new) and _scored(old))):
            old = new
        elif new is None and code in unresolved and not _scored(old):
            old = empty_record(reasons=('CIK_UNRESOLVED',))
        records[code] = restate(old, as_of, stale_after)
    states = [r['state'] for r in records.values()]
    state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
    payload = {'schema_version': 1, 'kind': KIND, 'as_of': _iso(as_of), 'config_version': cfg['config_version'],
               'config_status': cfg['config_status'], 'method_status': METHOD_STATUS, 'availability_basis': AVAILABILITY_BASIS,
               'freshness_basis': 'SOURCE_ACQUISITION', 'stale_after_seconds': int(stale_after.total_seconds()),
               'shard_count': cfg['shard_count'], 'last_shard_index': shard_index,
               'registry_sha256': registry_sha256 if registry_sha256 is not None else (previous or {}).get('registry_sha256'),
               'code_count': len(records), 'state': state,
               'reason_codes': [] if state == 'LIVE' else ['STALE_INPUT'] if state == 'STALE' else ['NO_ELIGIBLE_INPUT'],
               'records': records}
    require_universe_qg(payload)
    return payload


def _record(r, cut, ttl):
    _need(type(r) is dict and set(r) == set(RECORD_KEYS))
    _need(r['cik'] is None or type(r['cik']) is str and re.fullmatch(r'[0-9]{10}', r['cik']) is not None and r['cik'] != '0000000000')
    h = r['source_sha256']
    _need(type(h) is dict and set(h) == set(HASH_KEYS) and all(v is None or _hash(v) for v in h.values()))
    if r['acquired_at'] is None:
        _need(h['companyfacts'] is None and h['submissions'] is None)
    else:
        # A captured row carries its own capture time, issuer and both SEC hashes even without a score.
        _need(_clock(r['acquired_at']) <= cut and r['cik'] is not None and h['companyfacts'] and h['submissions'])
    _need(r['state'] in STATES)
    reasons = r['reason_codes']
    _need(type(reasons) is list and len(reasons) == len(set(reasons)) <= 4 and all(x in REASONS for x in reasons))
    factors = r['factors']
    _need(type(factors) is dict and set(factors) == set(FACTORS))
    # A factor is its 0-100 score or null (NOT_AVAILABLE); a scored factor shares the row state.
    _need(all(v is None or _score(v) and type(v) is not bool for v in factors.values()))
    scored = any(v is not None for v in factors.values())
    if not scored:
        _need(r['state'] == 'NOT_AVAILABLE' and reasons and 'STALE_INPUT' not in reasons)
    else:
        _need(r['acquired_at'] is not None)
        fresh = cut - _clock(r['acquired_at']) <= ttl
        _need(r['state'] == ('LIVE' if fresh else 'STALE') and reasons == ([] if fresh else ['STALE_INPUT']))
    return r['state']


def require_universe_qg(payload):
    """Strict public validator (also used by the Pages guard). Fixed error only."""
    try:
        _need(type(payload) is dict and set(payload) == set(TOP_KEYS))
        cfg = load_config()
        _need(type(payload['schema_version']) is int and payload['schema_version'] == 1 and payload['kind'] == KIND)
        cut = _clock(payload['as_of'])
        _need(payload['config_version'] == cfg['config_version'] and payload['config_status'] == cfg['config_status'])
        _need(payload['method_status'] == METHOD_STATUS and payload['availability_basis'] == AVAILABILITY_BASIS)
        _need(payload['freshness_basis'] == 'SOURCE_ACQUISITION')
        ttl = payload['stale_after_seconds']
        _need(type(ttl) is int and 0 < ttl <= 366 * 86400)
        _need(type(payload['shard_count']) is int and 1 <= payload['shard_count'] <= 366)
        index = payload['last_shard_index']
        _need(index is None or type(index) is int and 0 <= index < payload['shard_count'])
        _need(payload['registry_sha256'] is None or _hash(payload['registry_sha256']))
        records = payload['records']
        codes = universe_codes()
        _need(type(records) is dict and set(records) == set(codes) and type(payload['code_count']) is int and payload['code_count'] == len(codes))
        states = [_record(records[code], cut, timedelta(seconds=ttl)) for code in codes]
        state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
        _need(payload['state'] == state)
        top = payload['reason_codes']
        _need(type(top) is list and all(x in TOP_REASONS for x in top) and len(top) == len(set(top)))
        return payload
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise ValueError('SEC_UNIVERSE_QG_INVALID') from None


def parse_json(body):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('SEC_UNIVERSE_QG_INVALID')
            out[key] = value
        return out
    def constant(_):
        raise ValueError('SEC_UNIVERSE_QG_INVALID')
    try:
        if type(body) is not bytes or len(body) > MAX_BYTES:
            raise ValueError
        return json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('SEC_UNIVERSE_QG_INVALID') from None


def encode(payload):
    require_universe_qg(payload)
    body = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()
    _need(len(body) <= MAX_BYTES)
    return body
