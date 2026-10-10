"""Strict, price-free presentation of an explicitly supplied private M2 export.

No discovery, providers, receipt replay, or score calculations. Native exports
remain private; only this allowlisted projection may enter the public sidecar.
"""
from __future__ import annotations
from datetime import datetime
import json
import math
from pathlib import Path
import re
from ..markets.us import US_LISTINGS

ERROR = 'M2_CANDIDATE_INVALID'
CONTRACT = 'PUBLIC_SEC_QG_CANDIDATES'
FLAGS = {'candidate_only': True, 'prices_used': False, 'publication_approved': False,
         'publication_eligible': False, 'real_data_verified': False, 'full_pit_historical': False}
REASONS = frozenset({'RECEIPT_INTEGRITY_FAILURE', 'ORIGINAL_REPLAY_MISMATCH', 'ANNUAL_FORM_REQUIRED',
    'ACQUISITION_AFTER_CUTOFF', 'M1_NOT_AVAILABLE', 'AVAILABILITY_AFTER_CUTOFF',
    'UNRESOLVED_CURRENT_FACT_AMBIGUITY', 'INCOMPLETE_QG', 'REPLAY_OR_NORMALIZED_INPUT_FAILURE'})
COVERAGE = {'READY', 'PARTIAL', 'BLOCKED', 'SYNTHETIC'}


def _need(condition):
    if not condition:
        raise ValueError(ERROR)


def _hash(value, prefix=''):
    _need(isinstance(value, str) and re.fullmatch(re.escape(prefix) + '[0-9a-f]{64}', value) is not None)
    return value


def _clock(value):
    _need(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value) is not None)
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _need(dt.tzinfo is not None)
    return dt


def _score(value, maximum=100):
    _need(value is None or (type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum))
    return value


def _flags(value, expected):
    _need(isinstance(value, dict))
    for key, item in FLAGS.items():
        if key in value:
            _need(value[key] is item)
    for key, item in expected.items():
        _need(value.get(key) == item and type(value.get(key)) is type(item))


def _native_metadata(value):
    """Validate claims at known native nodes; omitted optional state makes no claim."""
    _flags(value, {})
    for key, expected in {'standard': 'v1', 'calibration': 'UNCALIBRATED',
                          'standard_status': 'STANDARD v1 · UNCALIBRATED',
                          'V_policy_status': 'STANDARD v1 · UNCALIBRATED'}.items():
        if value.get(key) is not None:
            _need(value[key] == expected)


def _keys(value, expected):
    _need(isinstance(value, dict) and set(value) == set(expected))


def unavailable_candidates():
    return {'contract': CONTRACT, 'version': 1, 'display_state': 'NOT_AVAILABLE',
            'reason_code': 'M2_INPUT_NOT_CONNECTED', 'companies': {}}


def _availability(value):
    _flags(value, {'basis': 'OBSERVED_PUBLIC_API_UPPER_BOUND', 'precision': 'CONSERVATIVE',
                   'historical_first_publication': False})
    _need(value.get('published_at') is None)
    if value['available_at'] is not None:
        _clock(value['available_at'])
    return {k: value[k] for k in ('available_at', 'basis', 'precision', 'historical_first_publication')}


def _source(value, receipt, cutoff, calculated):
    if value is None:
        _need(not calculated)
        return None
    _flags(value, {})
    _need(value['receipt_id'] == receipt)
    sha = _hash(value['receipt_sha256'])
    acquired = _clock(value['acquired_at'])
    original = _availability(value['original_availability'])
    if calculated:
        _need(acquired <= cutoff)
        _need(original['available_at'] is not None and _clock(original['available_at']) <= cutoff)
        requested = value.get('requested_availability')
        _need(requested is not None)
        req = _availability(requested)
        _need(req['available_at'] is not None and _clock(req['available_at']) <= cutoff)
    return {'receipt_sha256': sha, 'acquired_at': value['acquired_at'], 'original_availability': original}


def _coverage(value):
    if value is None:
        return None
    _need(value['native_coverage'] in COVERAGE and value['weights_renormalized'] is False)
    _need(value.get('V_observed_weight', 0) == 0)
    result = {k: _score(value[k], 1) for k in ('Q_observed_weight', 'G_observed_weight')}
    _need(all(v is not None for v in result.values()))
    return {**result, 'native_coverage': value['native_coverage'], 'weights_renormalized': False}


def _snapshot(snapshot, cid, row, synthetic, as_of):
    _need(snapshot['company_id'] == cid and snapshot['synthetic'] is synthetic)
    _need(_clock(snapshot['as_of']) == as_of)
    _need(_hash(snapshot['qgv_snapshot_id'], 'sec_m2_qgv_') == row['snapshot_id'])
    _need(snapshot['V_score'] is None)
    _need(snapshot.get('calibration') == 'UNCALIBRATED')
    _need(snapshot.get('standard') == 'v1' and snapshot.get('standard_status') == 'STANDARD v1 · UNCALIBRATED')
    _native_metadata(snapshot)
    _need(isinstance(snapshot.get('v_candidates'), list))
    for candidate in snapshot['v_candidates']:
        _native_metadata(candidate)
        _need(candidate.get('lifecycle') in {None, 'RESEARCH', 'STANDARD v1 · UNCALIBRATED'})
        _need(candidate.get('v_score') is None)
    return (_score(snapshot['Q_score']), _score(snapshot['G_score']))


def _project(value):
    _flags(value, {'contract': 'OFFLINE_SEC_QG_CANDIDATE', 'version': 1, 'schema_version': 1, **FLAGS})
    synthetic = value['synthetic_inputs']
    _need(type(synthetic) is bool and value['input_kind'] == ('SYNTHETIC' if synthetic else 'OBSERVED_UNVERIFIED'))
    cutoff, evaluated = _clock(value['as_of']), _clock(value['evaluated_at'])
    _need(cutoff <= evaluated)
    cid = _hash(value['candidate_id'], 'sec_m2_')
    _flags(value['research_state'], {'status': 'PROVISIONAL_RESEARCH', 'candidate_only': True})
    _flags(value['publication'], {'status': 'NOT_RUN', 'grant': 'NONE'})
    _flags(value['methodology'], {'status': 'PROVISIONAL_RESEARCH'})
    existing_method = value['methodology'].get('existing_method')
    if existing_method is not None:
        _native_metadata(existing_method)
    method = _hash(value['methodology']['method_sha256'])
    scope = value['scope']
    _flags(scope, {'basis': 'EXPLICIT_RECEIPTS_US17_SUBSET', 'public_500_rank': False})
    requested = scope['requested_receipt_ids']
    _need(isinstance(requested, list) and 1 <= len(requested) <= 17)
    _need(len(set(_hash(r) for r in requested)) == len(requested))
    companies = value['companies']
    _need(isinstance(companies, dict) and set(companies) <= set(US_LISTINGS))
    _need(scope['company_ids'] == sorted(companies))
    qgv = value['candidate_data']['qgv']
    _flags(qgv, {'scope': 'ENTITY_MAP', 'candidate_only': True, 'score_basis': 'LEGACY_QG_ONLY', 'complete_qgv_available': False})
    snapshots = qgv['data']
    unavailable = value['unavailable_snapshots']
    _need(isinstance(snapshots, dict) and isinstance(unavailable, dict))
    calculated_ids = {k for k, row in companies.items() if row.get('status') == 'CALCULATED'}
    _need(set(snapshots) == calculated_ids and set(unavailable) <= set(companies) - calculated_ids)
    _need(qgv.get('adapter_synthetic') is (synthetic and bool(calculated_ids)))
    lb = value['candidate_data']['leaderboard']
    _flags(lb, {'scope': 'ROWS', 'synthetic_inputs': synthetic, 'preview_only': True, 'candidate_only': True,
               'rank_basis': 'EXPLICIT_SUBSET_LEGACY_QG_ONLY_CANDIDATE', 'qgv_ranking_validated': False})
    # adapter_synthetic is adapter implementation metadata, not input provenance.
    _need(lb.get('adapter_synthetic') is False)
    lbdata = lb['data']
    _native_metadata(lbdata)
    _need(lbdata['recomputed_qgv'] is False and _clock(lbdata['generated_at']) == cutoff)
    _hash(lbdata['leaderboard_snapshot_id'], 'sec_m2_lb_')
    lbrows = lbdata['rows']
    _need(isinstance(lbrows, list) and len(lbrows) == len(calculated_ids))
    _need({r['company_id'] for r in lbrows} == calculated_ids)
    projected, receipts = {}, set()
    for company_id, row in companies.items():
        _flags(row, {'company_id': company_id, 'ticker': US_LISTINGS[company_id]['yahoo'],
                     'candidate_only': True, 'prices_used': False, 'publication_approved': False,
                     'score_basis': 'LEGACY_QG_ONLY'})
        receipt = _hash(row['receipt_id'])
        _need(receipt in requested and receipt not in receipts)
        receipts.add(receipt)
        calculated = company_id in calculated_ids
        _need(row['status'] in {'CALCULATED', 'NOT_AVAILABLE'})
        reasons = row['reason_codes']
        _need(isinstance(reasons, list) and all(isinstance(r, str) and r in REASONS for r in reasons))
        _need((not reasons) if calculated else bool(reasons))
        snapshot = snapshots.get(company_id) or unavailable.get(company_id)
        scores = _snapshot(snapshot, company_id, row, synthetic, cutoff) if snapshot else (None, None)
        if calculated:
            _need(all(s is not None for s in scores))
        for key, score in zip(('Q_score', 'G_score'), scores):
            if key in row:
                _need(_score(row[key]) == score)
        _need(row.get('V_score') is None and row.get('V_status', 'NOT_AVAILABLE') == 'NOT_AVAILABLE')
        source = _source(row.get('source'), receipt, cutoff, calculated)
        coverage = _coverage(row.get('coverage'))
        factors = row.get('factors', {})
        _need(isinstance(factors, dict))
        for factor_id, factor in factors.items():
            if isinstance(factor, dict) and (factor.get('group') == 'V' or factor_id in {
                    'fundamental_value', 'margin_of_safety', 'reverse_dcf', 'sector_context',
                    'theme_premium_discount', 'peer_relative_value', 'historical_valuation'}):
                _need(factor.get('status') == 'NOT_AVAILABLE')
                _need(factor.get('observation', {}).get('score_0_100') is None)
        if snapshot:
            _need(coverage is not None and snapshot['coverage_state'] == coverage['native_coverage'])
        projected[company_id] = {'company_id': company_id, 'ticker': US_LISTINGS[company_id]['yahoo'],
            'status': row['status'], 'reason_codes': list(reasons), 'receipt_id': receipt,
            'snapshot_id': _hash(row['snapshot_id'], 'sec_m2_qgv_') if row.get('snapshot_id') else None,
            'source': source, 'coverage': coverage, 'Q_score': scores[0] if calculated else None,
            'G_score': scores[1] if calculated else None, 'V_score': None, 'V_status': 'NOT_AVAILABLE'}
    for row in lbrows:
        snapshot = snapshots[row['company_id']]
        _need(row['ticker'] == US_LISTINGS[row['company_id']]['yahoo'])
        _need(row['qgv_snapshot_id'] == snapshot['qgv_snapshot_id'])
        _flags(row, {})
        _need(row.get('calibration') == snapshot['calibration'] and row.get('standard') == snapshot['standard']
              and row.get('standard_status') == snapshot['standard_status'])
        _need(row.get('freshness') == ('SYNTHETIC' if synthetic else snapshot['coverage_state']))
        for key in ('Q_score', 'G_score', 'V_score'):
            _need(_score(row[key]) == snapshot[key])
    _need(type(value['n_calculated']) is int and value['n_calculated'] == len(calculated_ids))
    _need(type(value['n_unavailable']) is int and value['n_unavailable'] == len(requested) - len(calculated_ids))
    result = {'contract': CONTRACT, 'version': 1, 'display_state': 'RESEARCH_CANDIDATE',
        'candidate_id': cid, 'as_of': value['as_of'], 'evaluated_at': value['evaluated_at'],
        'input_kind': value['input_kind'], 'synthetic_inputs': synthetic, **FLAGS,
        'research_status': 'PROVISIONAL_RESEARCH', 'publication_grant': 'NONE',
        'scope_basis': 'EXPLICIT_RECEIPTS_US17_SUBSET', 'public_500_rank': False,
        'method_sha256': method, 'n_calculated': value['n_calculated'], 'n_unavailable': value['n_unavailable'],
        'companies': projected}
    require_public_candidates(result)
    return result


def project_candidates(value):
    try:
        return _project(value)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, AttributeError, RecursionError):
        raise ValueError(ERROR) from None


def _validate_public(value):
    if value == unavailable_candidates():
        _need(type(value["version"]) is int)
        return
    _keys(value, {'contract', 'version', 'display_state', 'candidate_id', 'as_of', 'evaluated_at', 'input_kind',
        'synthetic_inputs', *FLAGS, 'research_status', 'publication_grant', 'scope_basis', 'public_500_rank',
        'method_sha256', 'n_calculated', 'n_unavailable', 'companies'})
    _flags(value, {'contract': CONTRACT, 'version': 1, 'display_state': 'RESEARCH_CANDIDATE', **FLAGS,
        'research_status': 'PROVISIONAL_RESEARCH', 'publication_grant': 'NONE',
        'scope_basis': 'EXPLICIT_RECEIPTS_US17_SUBSET', 'public_500_rank': False})
    _need(type(value['synthetic_inputs']) is bool)
    _need(value['input_kind'] == ('SYNTHETIC' if value['synthetic_inputs'] else 'OBSERVED_UNVERIFIED'))
    _hash(value['candidate_id'], 'sec_m2_'); _hash(value['method_sha256'])
    cutoff = _clock(value['as_of'])
    _need(cutoff <= _clock(value['evaluated_at']))
    companies = value['companies']
    _need(isinstance(companies, dict) and set(companies) <= set(US_LISTINGS))
    receipts, calculated = set(), 0
    for cid, row in companies.items():
        _keys(row, {'company_id', 'ticker', 'status', 'reason_codes', 'receipt_id', 'snapshot_id',
                    'source', 'coverage', 'Q_score', 'G_score', 'V_score', 'V_status'})
        _flags(row, {'company_id': cid, 'ticker': US_LISTINGS[cid]['yahoo'], 'V_status': 'NOT_AVAILABLE'})
        _need(row['V_score'] is None and row['status'] in {'CALCULATED', 'NOT_AVAILABLE'})
        receipt = _hash(row['receipt_id']); _need(receipt not in receipts); receipts.add(receipt)
        reasons = row['reason_codes']
        _need(isinstance(reasons, list) and all(isinstance(r, str) and r in REASONS for r in reasons))
        is_calculated = row['status'] == 'CALCULATED'
        _need((not reasons) if is_calculated else bool(reasons))
        scores = [_score(row[k]) for k in ('Q_score', 'G_score')]
        _need(all(s is not None for s in scores) if is_calculated else scores == [None, None])
        calculated += is_calculated
        if row['snapshot_id'] is not None:
            _hash(row['snapshot_id'], 'sec_m2_qgv_')
        _need(not is_calculated or row['snapshot_id'] is not None)
        source = row['source']
        if source is not None:
            _keys(source, {'receipt_sha256', 'acquired_at', 'original_availability'})
            _hash(source['receipt_sha256']); acquired = _clock(source['acquired_at'])
            availability = source['original_availability']
            _keys(availability, {'available_at', 'basis', 'precision', 'historical_first_publication'})
            _availability(availability)
            if is_calculated:
                _need(acquired <= cutoff and availability['available_at'] is not None and _clock(availability['available_at']) <= cutoff)
        _need(not is_calculated or source is not None)
        coverage = row['coverage']
        if coverage is not None:
            _keys(coverage, {'Q_observed_weight', 'G_observed_weight', 'native_coverage', 'weights_renormalized'})
            _coverage(coverage)
        _need(not is_calculated or coverage is not None)
    _need(type(value['n_calculated']) is int and value['n_calculated'] == calculated)
    _need(type(value['n_unavailable']) is int and len(companies) - calculated <= value['n_unavailable'])
    _need(1 <= calculated + value['n_unavailable'] <= 17)


def require_public_candidates(value):
    try:
        _validate_public(value)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, AttributeError, RecursionError):
        raise ValueError(ERROR) from None


def load_candidates(path):
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result)
            result[key] = value
        return result
    def constant(_):
        raise ValueError(ERROR)
    try:
        raw = Path(path).read_bytes()
        _need(len(raw) <= 16 * 1024 * 1024)
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        project_candidates(value)
        return value
    except (OSError, ValueError, TypeError, RecursionError, UnicodeError):
        raise ValueError(ERROR) from None
