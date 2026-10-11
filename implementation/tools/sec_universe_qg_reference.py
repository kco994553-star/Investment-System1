#!/usr/bin/env python3
"""Synthetic Python reference vectors for the public `sec-universe-qg.json` validator (JS parity).

A sparse base payload (rows absent from `base.records` are `empty_record()`, filled over
universe_codes_v1.json in both languages) plus mutation cases, each with the verdict of
Python `require_universe_qg`. tools/sec_universe_qg_node_test.js replays every case through
JS `SecUniverseQg.validate` and must reach the same verdict. Synthetic CIKs/hashes only;
test-only, never a public or live-data serializer. `--write` regenerates
tests/fixtures/sec_universe_qg_vectors_v1.json.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/sec_universe_qg_vectors_v1.json'
AS_OF = '2026-10-10T22:30:00Z'
DELETE = {'$delete': True}


def _h(text):
    return sha256(text.encode()).hexdigest()


def _row(n, acquired_at, scores=None, reasons=None):
    from investment_system.universe.sec_universe_qg import FACTORS
    cik = str(n).zfill(10)
    factors = dict.fromkeys(FACTORS)
    factors.update(scores or {})
    scored = any(v is not None for v in factors.values())
    stale = acquired_at < '2026-09-26'
    return {'cik': cik, 'acquired_at': acquired_at, 'source_sha256': {'companyfacts': _h('facts' + cik), 'submissions': _h('sub' + cik)},
            'factors': factors, 'state': ('STALE' if stale else 'LIVE') if scored else 'NOT_AVAILABLE',
            'reason_codes': (['STALE_INPUT'] if stale else []) if scored else list(reasons or ['QG_NOT_AVAILABLE'])}


def base():
    from investment_system.universe.sec_universe_qg import empty_record
    records = {
        'NASDAQ:ADBE': _row(1, '2026-10-10T22:00:00Z', {'revenue_growth': 80.00000000000003, 'next_3_5y_growth': 80.00000000000003,
                                                       'margin_quality': 62.5, 'roic_wacc': 0, 'financial_health': 100}),
        'NYSE:MMM': _row(3, '2026-09-20T22:00:00Z', {'fcf_quality': 41.25}),
        'NASDAQ:AMD': _row(4, '2026-10-09T22:00:00.123456Z', reasons=['M1_NOT_AVAILABLE']),
        'NYSE:AOS': _row(5, '2026-10-09T22:00:00Z', reasons=['UNRESOLVED_CURRENT_FACT_AMBIGUITY']),
        'BATS:CBOE': empty_record(reasons=('CIK_UNRESOLVED',)),
    }
    return {'schema_version': 1, 'kind': 'SEC_UNIVERSE_QG', 'as_of': AS_OF, 'config_version': 'sec-universe-shares/v0',
            'config_status': 'DEFAULT_V0_UNCALIBRATED', 'method_status': 'PROVISIONAL_UNCALIBRATED',
            'availability_basis': 'OBSERVED_CAPTURE_ONLY', 'freshness_basis': 'SOURCE_ACQUISITION', 'stale_after_seconds': 14 * 86400,
            'shard_count': 7, 'last_shard_index': 3, 'registry_sha256': _h('registry'), 'code_count': 504, 'state': 'LIVE',
            'reason_codes': [], 'records': records}


R = ['records']
CASES = [
    ('base_valid', []),
    ('null_shard_and_registry_valid', [(['last_shard_index'], None), (['registry_sha256'], None)]),
    ('zero_score_is_a_score_not_missing', [(R + ['NASDAQ:ADBE', 'factors', 'margin_quality'], 0)]),
    ('top_price_key', [(['price'], 1)]),
    ('row_price_key', [(R + ['NASDAQ:ADBE', 'price'], 1)]),
    ('row_market_cap_key', [(R + ['NASDAQ:ADBE', 'market_cap'], 1)]),
    ('v_factor_added', [(R + ['NASDAQ:ADBE', 'factors', 'fundamental_value'], 50)]),
    ('factor_missing', [(R + ['NASDAQ:ADBE', 'factors', 'roic_wacc'], DELETE)]),
    ('score_negative', [(R + ['NASDAQ:ADBE', 'factors', 'roic_wacc'], -1)]),
    ('score_above_100', [(R + ['NASDAQ:ADBE', 'factors', 'roic_wacc'], 100.5)]),
    ('score_string', [(R + ['NASDAQ:ADBE', 'factors', 'roic_wacc'], '50')]),
    ('score_bool', [(R + ['NASDAQ:ADBE', 'factors', 'roic_wacc'], True)]),
    ('score_object_target_shape', [(R + ['NASDAQ:ADBE', 'factors', 'roic_wacc'], {'score': 50, 'state': 'LIVE'})]),
    ('fresh_row_marked_stale', [(R + ['NASDAQ:ADBE', 'state'], 'STALE'), (R + ['NASDAQ:ADBE', 'reason_codes'], ['STALE_INPUT'])]),
    ('stale_row_marked_live', [(R + ['NYSE:MMM', 'state'], 'LIVE'), (R + ['NYSE:MMM', 'reason_codes'], [])]),
    ('stale_row_without_reason', [(R + ['NYSE:MMM', 'reason_codes'], [])]),
    ('scored_row_extra_reason', [(R + ['NASDAQ:ADBE', 'reason_codes'], ['M1_NOT_AVAILABLE'])]),
    ('not_available_row_with_score', [(R + ['NASDAQ:AMD', 'factors', 'roic_wacc'], 50)]),
    ('not_available_row_without_reason', [(R + ['NASDAQ:AMD', 'reason_codes'], [])]),
    ('not_available_row_with_stale_reason', [(R + ['NASDAQ:AMD', 'reason_codes'], ['STALE_INPUT'])]),
    ('unknown_reason', [(R + ['NASDAQ:AMD', 'reason_codes'], ['RANK'])]),
    ('duplicate_reason', [(R + ['NASDAQ:AMD', 'reason_codes'], ['M1_NOT_AVAILABLE', 'M1_NOT_AVAILABLE'])]),
    ('record_removed', [(R + ['NYSE:AOS'], DELETE)]),
    ('acquired_after_as_of', [(R + ['NASDAQ:ADBE', 'acquired_at'], '2026-10-11T00:00:00Z')]),
    ('acquired_without_hash', [(R + ['NASDAQ:ADBE', 'source_sha256', 'submissions'], None)]),
    ('hash_without_acquired', [(R + ['BATS:CBOE', 'source_sha256', 'companyfacts'], _h('x'))]),
    ('bad_hash', [(R + ['NASDAQ:ADBE', 'source_sha256', 'companyfacts'], 'x')]),
    ('short_cik', [(R + ['NASDAQ:ADBE', 'cik'], '1')]),
    ('zero_cik', [(R + ['NASDAQ:ADBE', 'cik'], '0000000000')]),
    ('acquired_without_cik', [(R + ['NASDAQ:AMD', 'cik'], None)]),
    ('scored_row_without_acquired', [(R + ['NASDAQ:ADBE', 'acquired_at'], None),
                                     (R + ['NASDAQ:ADBE', 'source_sha256'], {'companyfacts': None, 'submissions': None})]),
    ('config_calibrated', [(['config_status'], 'CALIBRATED')]),
    ('method_status_changed', [(['method_status'], 'APPROVED')]),
    ('kind_changed', [(['kind'], 'SEC_QG_FACTORS')]),
    ('stale_after_float', [(['stale_after_seconds'], 1.5)]),
    ('top_state_mismatch', [(['state'], 'STALE')]),
    ('top_unknown_reason', [(['reason_codes'], ['RANK'])]),
    ('shard_index_out_of_range', [(['last_shard_index'], 7)]),
    ('code_count_changed', [(['code_count'], 503)]),
    ('bad_as_of', [(['as_of'], '2026-10-10')]),
]


def expand(payload):
    """Sparse base -> full 504-code payload (missing codes are NOT_COLLECTED empty rows)."""
    from investment_system.universe.sec_universe_qg import empty_record, universe_codes
    out = json.loads(json.dumps(payload))
    out['records'] = {code: out['records'].get(code) or empty_record() for code in universe_codes()}
    return out


def apply(payload, ops):
    for path, value in ops:
        target = payload
        for key in path[:-1]:
            target = target[key]
        if value == DELETE:
            del target[path[-1]]
        else:
            target[path[-1]] = json.loads(json.dumps(value))
    return payload


def verdict(payload):
    from investment_system.universe.sec_universe_qg import require_universe_qg
    try:
        require_universe_qg(payload)
        return True
    except ValueError:
        return False


def build():
    from investment_system.universe.sec_universe_qg import FACTORS
    sparse = base()
    cases = [{'id': cid, 'ops': [{'path': path, 'value': value} for path, value in ops],
              'valid': verdict(apply(expand(sparse), ops))} for cid, ops in CASES]
    return {'synthetic': True, 'as_of': AS_OF, 'factors': list(FACTORS), 'delete_marker': DELETE, 'base': sparse, 'cases': cases}


def main(argv):
    text = json.dumps(build(), sort_keys=True, indent=1, ensure_ascii=True, allow_nan=False) + '\n'
    if '--write' in argv:
        FIXTURE.write_text(text)
        print('SEC_UNIVERSE_QG_VECTORS_WRITTEN')
        return 0
    ok = FIXTURE.exists() and FIXTURE.read_text() == text
    print('SEC_UNIVERSE_QG_VECTORS_OK' if ok else 'SEC_UNIVERSE_QG_VECTORS_STALE')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
