"""Offline observed-capture lookup of existing macro-evidence/1 archives.

Reuses the strict public reader, candidate rules and delay policy. No collector,
regime model, interpolation or historically reconstructed first-release claim.
"""
from datetime import datetime, timezone
import hashlib
import json

from investment_system.macro import evidence_lines as el, evidence_sources as es

SCHEMA = 'macro-observed-timeline/1'
EVIDENCE_CONTRACT = 'macro-observed-evidence/1'
VALIDITY_RULES = {
    'query_usable': 'PUBLIC scope, strict archive validation and a selected finite value with capture or conservative capture bound <= query; stale values remain diagnostic.',
    'fresh_query_usable': 'query_usable and not stale under the existing period-delay policy.',
    'system_available_by_query': 'Selected version was observed in this system, or conservatively known by archive generation, no later than query; not original agency release proof.',
    'historical_pit_eligible': 'Requires original release and source-vintage evidence; macro-evidence/1 does not retain sufficient proof, so always false for this input contract.',
}
SEASONAL = {
    'E09': 'NOT_APPLICABLE', 'E13': 'SA', 'E14': 'SA', 'E16': 'SA', 'E17': 'SA',
    'E21': 'SA', 'E22': 'SA', 'E25': 'SAAR', 'E26': 'SAAR', 'E36': 'NSA',
    'E39': 'SA', 'E40': 'NOT_APPLICABLE', 'E01': 'SA',
}


def _version(version, generated):
    at = el.parse_iso(version['at'])
    if version['basis'] == 'SOURCE_LAST_MODIFIED':
        # The old contract stores posting time but not this version's receipt
        # time. The archive's generation is a safe upper bound, not first release.
        available, basis, posted = generated, 'ARCHIVE_CAPTURE_UPPER_BOUND', version['at']
    else:
        available, basis, posted = at, 'OBSERVED_CAPTURE', None
    return {**version, 'available': available, 'availability_basis': basis, 'source_posted_at': posted}


def _series_at(sid, row, as_of, generated):
    definition = es.BY_ID[es.SERIES_INDICATOR[sid]]
    output = {
        'source_id': sid, 'indicator': definition['id'], 'frequency': row['frequency'],
        'unit': definition['unit'], 'seasonal_adjustment': SEASONAL[definition['id']],
        'observation_period': None, 'value': None, 'state': 'NOT_AVAILABLE',
        'reason': None, 'first_published_at': None, 'source_posted_at': None,
        'data_asof': None, 'result_kind': 'NOT_COMPUTED', 'stale': None,
        'official_release_at': None, 'official_release_status': 'NOT_PROVEN_IN_ARCHIVE',
        'source_version_id': None, 'source_version_status': 'NOT_PROVEN_IN_ARCHIVE',
        'archive_version_id': None, 'version_time_basis': None,
        'first_acquired_at': None, 'first_acquired_by': None,
        'first_acquisition_status': 'NOT_AVAILABLE', 'selected_version_acquired_at': None,
        'query_usable': False, 'availability_status': 'NOT_AVAILABLE_AT_QUERY',
        'historical_pit_eligible': False, 'historical_pit_reason': 'NO_QUERYABLE_VALUE',
        'available_at': None, 'availability_basis': None, 'version_kind': None, 'period_origin_kind': None,
        'vintage_at': None, 'first_observed_at': None, 'new_observation': False,
        'revised': False, 'held': False, 'newly_available': False, 'observation_id': None,
        'candidate_state': None, 'candidate_rule': definition['rule']['version'],
        'model_status': 'NOT_APPLIED', 'latest_archive_success_at': row['last_success_at'],
        'collection_state_at_query': row['state'] if generated and as_of >= generated else None,
        'collection_reason_at_query': row['reason'] if generated and as_of >= generated else None,
        'valid_observations': 0, 'history_window': el.WINDOW[row['frequency']],
    }
    if definition['publication'] != 'PUBLIC':
        return {**output, 'reason': 'TERMS_UNVERIFIED'}
    if generated is None or row['baseline_at'] is None:
        return {**output, 'reason': row['reason'] or 'SOURCE_NOT_COLLECTED'}
    baseline = el.parse_iso(row['baseline_at'])
    if as_of < baseline:
        return {**output, 'reason': 'BEFORE_CAPTURE_HISTORY'}
    selected = []
    for period, value in row['obs']:
        versions = row['history'].get(period) or [
            {'v': value, 'kind': 'BASELINE', 'at': row['baseline_at'], 'basis': 'BASELINE', 'rd': None}]
        timed = [_version(v, generated) for v in versions]
        eligible = [v for v in timed if v['available'] <= as_of]
        if not eligible:
            continue
        # Preserve the source's append-only revision order. A conservative
        # upper bound must not reorder an earlier posting-based revision
        # after a later version with a known collection timestamp.
        chosen = eligible[-1]
        selected.append((period, chosen, min(v['available'] for v in timed), versions[0]))
    if not selected:
        return {**output, 'reason': 'NO_CAPTURE_AVAILABLE_AT_QUERY'}
    selected.sort(key=lambda x: el.period_index(x[0], row['frequency']))
    period, version, first_seen, origin = selected[-1]
    observations = [(p, v['v']) for p, v, _, _ in selected]
    candidate = el.current_state(definition['id'], observations, row['frequency'])
    delayed = el._delayed({'frequency': row['frequency'], 'state': 'LIVE', 'obs': observations}, as_of)
    identity = hashlib.sha256(json.dumps([sid, period, version['v'], version['at'], version['kind']],
                                        separators=(',', ':')).encode()).hexdigest()
    # A source posting timestamp is neither original release nor receipt time.
    # Preserve exact first recorded receipt only when the archive actually has it.
    first_acquired = origin['at'] if origin['basis'] != 'SOURCE_LAST_MODIFIED' else None
    selected_acquired = version['at'] if version['basis'] != 'SOURCE_LAST_MODIFIED' else None
    return {**output, 'value': version['v'], 'observation_period': period,
            'data_asof': period, 'result_kind': 'RAW_DIAGNOSTIC', 'stale': delayed,
            'archive_version_id': identity, 'version_time_basis': version['basis'],
            'first_acquired_at': first_acquired, 'first_acquired_by': el.iso(first_seen),
            'first_acquisition_status': 'RECORDED_CAPTURE' if first_acquired else 'UPPER_BOUND_ONLY',
            'selected_version_acquired_at': selected_acquired, 'query_usable': True,
            'availability_status': 'OBSERVED_CAPTURE_BY_QUERY' if selected_acquired else 'CONSERVATIVE_CAPTURE_BOUND_BY_QUERY',
            'historical_pit_reason': 'OFFICIAL_RELEASE_AND_SOURCE_VINTAGE_NOT_PROVEN',
            'state': 'STALE' if delayed else 'AVAILABLE', 'reason': 'PERIOD_DELAYED' if delayed else None,
            'source_posted_at': version['source_posted_at'], 'available_at': el.iso(version['available']),
            'availability_basis': version['availability_basis'], 'version_kind': version['kind'], 'period_origin_kind': origin['kind'],
            'vintage_at': version['at'], 'first_observed_at': el.iso(first_seen),
            'observation_id': identity, 'candidate_state': candidate['state'], 'valid_observations': len(selected)}


def timeline(payload, cutoffs):
    """One held-observation view per aware cutoff; callers choose daily display times."""
    el.require_macro_evidence(payload)
    if not cutoffs or any(not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None for t in cutoffs):
        raise ValueError('AWARE_CUTOFFS_REQUIRED')
    times = [t.astimezone(timezone.utc) for t in cutoffs]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('CUTOFFS_MUST_INCREASE')
    generated = el.parse_iso(payload['generated_at']) if payload['generated_at'] else None
    snapshots, previous = [], {}
    for at in times:
        rows = {}
        for sid, series in payload['series'].items():
            row = _series_at(sid, series, at, generated)
            old = previous.get(sid)
            if old and row['value'] is not None:
                row['newly_available'] = old['value'] is None
                changed_period = old['observation_period'] != row['observation_period']
                # A period may arrive and be revised between display cutoffs.
                # Its origin, not the selected latest version kind, identifies
                # a new observation; BASELINE remains availability only.
                row['new_observation'] = changed_period and row['period_origin_kind'] == 'FIRST'
                row['revised'] = bool(not changed_period and old['observation_id'] != row['observation_id'])
                row['held'] = old['observation_id'] == row['observation_id']
            rows[sid] = row
        counts = {
            'series': len(rows), 'query_usable': sum(r['query_usable'] for r in rows.values()),
            'fresh_query_usable': sum(r['query_usable'] and not r['stale'] for r in rows.values()),
            'system_available_by_query': sum(r['availability_status'] != 'NOT_AVAILABLE_AT_QUERY' for r in rows.values()),
            'official_release_proven': sum(r['official_release_at'] is not None for r in rows.values()),
            'source_vintage_proven': sum(r['source_version_id'] is not None for r in rows.values()),
            'historical_pit_eligible': sum(r['historical_pit_eligible'] for r in rows.values()),
            'not_computed': sum(r['result_kind'] == 'NOT_COMPUTED' for r in rows.values()),
        }
        snapshots.append({'as_of': el.iso(at), 'series': rows, 'counts': counts})
        previous = rows
    return {'schema_version': SCHEMA, 'source_schema': payload['schema'], 'archive_generated_at': payload['generated_at'],
            'historical_pit_status': 'OBSERVED_CAPTURE_ONLY', 'interpolation': 'NONE',
            'evidence_contract_version': EVIDENCE_CONTRACT, 'validity_rules': dict(VALIDITY_RULES),
            'scope': dict(el.SCOPE), 'snapshots': snapshots}
