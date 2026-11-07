"""Offline coverage from explicit published factors/axes, never inferred from totals.

No data collection, score modification, identity invention or historical-market claim.
Preset availability reuses qgv_v2 weights and its unchanged total-eligibility rule;
it is derived from the archived axes, not a new PIT score reconstruction.
"""
from collections import Counter
import hashlib
import json

from ..qgv import qgv_official, qgv_v2 as q
from ..qgv.type_config import load_official_type_config


def reason_category(reason):
    if reason == 'FINANCIAL_PROFILE_V_NOT_DEFINED':
        return 'NOT_APPLICABLE'
    if reason in ('CALC_VERSION_MISMATCH', 'PRICE_IDENTITY_CONFLICT'):
        return 'INPUT_MISMATCH'
    if reason in ('NO_DEVICE_PRICE', 'V_INPUTS_NOT_AVAILABLE', 'TYPE_WEIGHTS_NOT_LINKED'):
        return 'INPUT_NOT_LINKED'
    if reason in ('SPLIT_TIMING_UNCONFIRMED', 'SHARE_BASIS_UNCONFIRMED', 'SHARE_BASIS_FACTOR_NOT_AVAILABLE'):
        return 'BASIS_UNCONFIRMED'
    return 'REPORTED_MISSING_INPUT_OR_RULE'


def measure(observations):
    values = list(observations)
    reasons = Counter((v.get('reason') or 'REASON_NOT_RECORDED') for v in values if v['score'] is None)
    categories = Counter()
    for reason, count in reasons.items():
        categories[reason_category(reason)] += count
    return {'valid': sum(v['score'] is not None for v in values), 'denominator': len(values),
            'missing': sum(reasons.values()), 'not_applicable': categories['NOT_APPLICABLE'],
            'reasons': dict(sorted(reasons.items())), 'reason_categories': dict(sorted(categories.items()))}


def preset_availability(row, weights, fallback):
    if row['total_reason'] in ('CALC_VERSION_MISMATCH', 'PRICE_IDENTITY_CONFLICT'):
        return False, row['total_reason']
    if row['type_weights'] is None:
        return None, 'TYPE_WEIGHTS_NOT_LINKED'
    effective = q.composite_weights(weights, row['type_weights'], fallback)
    # Same coverage threshold BEFORE the gate and nonempty set AFTER the gate
    # as qgv_v2.score_universe. This computes availability only, never a score.
    data = 0.0
    for axis in q.PILLARS:
        if row['axes'][axis]['score'] is not None:
            data += effective[axis]
    included = [a for a in q.PILLARS if row['axes'][a]['score'] is not None
                and not (a == 'V' and row['value_trap_gate'])]
    valid = data / 100.0 >= q.MIN_AXIS_WEIGHT and bool(included)
    return valid, None if valid else 'AXIS_WEIGHT_INSUFFICIENT'


def summarize_rows(rows, *, fallback):
    universe = {k: r for k, r in rows.items() if not k.startswith(qgv_official.TARGET_PREFIX)}
    n = len(universe)
    cik_missing = sum(r['cik'] is None for r in universe.values())
    definitions = {k: v['weights'] for k, v in q.PRESETS.items()}
    definitions.update({k: q.user_preset(k)['weights']['axis'] for k in q.USER_PRESETS})
    presets = {}
    for key, weights in definitions.items():
        outcomes = [preset_availability(r, weights, fallback) for r in universe.values()]
        unknown = sum(ok is None for ok, _ in outcomes)
        valid = sum(ok is True for ok, _ in outcomes)
        presets[key] = {'valid': None if unknown else valid, 'known_valid': valid, 'unknown': unknown,
                        'denominator': n, 'basis': 'DERIVED_FROM_ARCHIVED_AXES',
                        'reasons': dict(sorted(Counter(reason for _, reason in outcomes if reason).items()))}
    return {
        'denominator': {'kind': 'DATED_OPERATIONAL_UNIVERSE_CODES', 'count': n,
                        'published_rows': len(rows), 'target_rows_excluded': len(rows) - n,
                        'unique_code_strings': n,
                        'unique_issuer_ciks': None if cik_missing else len({r['cik'] for r in universe.values()}),
                        'missing_cik_rows': cik_missing, 'unique_securities': None,
                        'security_identity_reason': 'FIXED_SECURITY_ID_NOT_IN_PUBLICATION',
                        'cross_section_rows': sum(r['in_cross_section'] for r in universe.values())},
        'factors': {f: measure(r['factors'][f] for r in universe.values()) for f in q.FACTORS},
        'axes': {a: measure(r['axes'][a] for r in universe.values()) for a in q.PILLARS},
        'all_axes': {'valid': sum(all(r['axes'][a]['score'] is not None for a in q.PILLARS) for r in universe.values()),
                     'denominator': n},
        'presets': presets,
        'published_default_total': {'valid': sum(r['total'] is not None for r in universe.values()), 'denominator': n},
        'membership_codes': sorted(universe),
    }


def coverage_from_archive(body: bytes):
    archive = json.loads(body)
    qgv_official.require_qgv_official(archive)
    # Replaying preset eligibility against a different engine would silently
    # change its meaning. Preserve factor/axis observations, but leave presets null.
    engine_matches = hashlib.sha256(qgv_official.ENGINE_PY.read_bytes()).hexdigest() == archive['engine']['python_sha256']
    fallback = load_official_type_config().to_dict()['fallback']['weights']
    result = summarize_rows(archive['rows'], fallback=fallback)
    if not engine_matches:
        for item in result['presets'].values():
            item.update(valid=None, known_valid=None, unknown=result['denominator']['count'],
                        reasons={'ENGINE_VERSION_MISMATCH': result['denominator']['count']})
    result.update(schema_version='operational-qgv-coverage/1', result_kind='OPERATIONAL_COVERAGE',
                  publication_id=archive['publication_id'], source_sha256=hashlib.sha256(body).hexdigest(),
                  calc_version=archive['calc_version'], times=archive['times'], engine_matches=engine_matches,
                  source_inputs=archive['inputs'],
                  signal_date_pit_eligible=None, pit_reason='INPUT_VINTAGE_NOT_VERIFIED_AT_PRICE_BASIS',
                  raw_input_connection_audit=None, raw_input_reason='RAW_INPUTS_NOT_LINKED_TO_THIS_REVIEW',
                  historical_whole_market_coverage=None, scope='SELECTED_OPERATIONAL_PUBLICATION_ONLY')
    return result
