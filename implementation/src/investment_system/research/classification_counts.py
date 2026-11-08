"""Small, offline projection of pinned results; no recalculation or source fetching.

The held financial subset retains the catalog's scoring population. Its official
Q gate input is an upstream replay input, never the new sector Q axis or a pass
count. Unknown full-market coverage stays null.
"""
from copy import deepcopy
import json
import math

from .sector_qgv import _input_identity, digest
from .sector_qgv_held import checked_bytes
from .sector_qgv_registry import ENGINE, MODEL, NORMALIZATION, MAPPING
from .common_classification.catalog import (VERSION, MAPPING_VERSION,
                                            POLICY_DICTIONARY_VERSION, POLICY_MAPPING_VERSION)

SCHEMA = 'common-classification-calculation-counts/1'
VERSION_KEYS = ('model_version', 'engine_version', 'normalization_version', 'mapping_version',
                'input_version', 'snapshot_id', 'universe_id', 'universe_version')
MAX_BYTES = 2 * 1024 * 1024


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def load(spec):
    require(isinstance(spec['ref'], str) and bool(spec['ref']), 'SOURCE_REFERENCE_REQUIRED')
    return json.loads(checked_bytes(spec))


def reference(spec):
    return {k: spec[k] for k in ('ref', 'sha256')}


def rows_by_id(rows, members):
    result = {}
    for row in rows:
        key = row['company_id']
        require(key not in result, 'DUPLICATE_ROW')
        require(isinstance(row['issuer_id'], str) and bool(row['issuer_id']), 'ISSUER_MISMATCH')
        result[key] = row
    require(len(set(members)) == len(members) and set(result) == set(members), 'MEMBERS_MISMATCH')
    return result


def score_present(value):
    if value is None:
        return False
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 100, 'INVALID_SCORE')
    return True


def raw_counts(rows):
    axes = {a: sum(score_present(row['axes'][a]) for row in rows) for a in 'QGV'}
    return {**axes, 'joint': sum(all(row['axes'][a] is not None for a in 'QGV') for row in rows),
            'total': sum(score_present(row['total']) for row in rows)}


def count(valid, denominator, *, reason=None):
    status = ('NOT_MEASURED' if valid is None else 'EMPTY_POPULATION' if denominator == 0 else
              'NOT_COMPUTED' if valid == 0 else 'COMPLETE' if valid == denominator else 'PARTIAL')
    return {'valid': valid, 'denominator': denominator,
            'uncomputed': None if valid is None else denominator - valid,
            'status': status, 'reason': reason}


def check_count(actual, expected):
    require(type(actual) is int and actual == expected, 'COUNT_MISMATCH')


def checked_scope(spec, valuation_date):
    s, p, v = (load(spec[k]) for k in ('snapshot', 'preview', 'view'))
    require(s['schema_version'] == 'sector-qgv-input/1' and p['schema_version'] == 'sector-qgv-preview/1'
            and v['schema_version'] == 'common-classification-view/1', 'SCHEMA_MISMATCH')
    require(not p['validation_errors'], 'INVALID_PREVIEW')
    require(s['valuation_date'] == p['valuation_date'] == v['valuation_date'] == valuation_date, 'CONTEXT_MISMATCH')
    for k in ('snapshot_id', 'universe_id', 'universe_version', 'as_of'):
        require(s[k] == p[k] == spec['expected'][k], 'CONTEXT_MISMATCH')
    for k in ('input_version', 'mapping_version'):
        require(s[k] == p[k], 'CONTEXT_MISMATCH')
    for k in ('universe_id', 'universe_version'):
        require(v[k] == s[k], 'CONTEXT_MISMATCH')
    pair = (v['dictionary_version'], v['mapping_version'])
    require(pair in {(VERSION, MAPPING_VERSION), (POLICY_DICTIONARY_VERSION, POLICY_MAPPING_VERSION)},
            'CLASSIFICATION_VERSION')
    for k in ('schema_version', 'classification_hash', 'dictionary_version', 'mapping_version', 'knowledge_as_of'):
        require(s['classification_context'][k] == v[k], 'CLASSIFICATION_MISMATCH')
    require(v['classification_hash'] == spec['expected']['classification_hash'], 'CLASSIFICATION_MISMATCH')
    for k, expected in [('model_version', MODEL), ('engine_version', ENGINE),
                        ('normalization_version', NORMALIZATION), ('mapping_version', MAPPING)]:
        require(p[k] == expected, 'ENGINE_VERSION')
    require(p['input_hash'] == _input_identity(s) and p['config_hash'] == spec['expected']['config_hash'], 'PREVIEW_IDENTITY')
    cache = digest(dict(config_hash=p['config_hash'], input_hash=p['input_hash'], **{k: p[k] for k in VERSION_KEYS}))
    require(p['cache_key'] == cache and p['preview_id'] == digest({'cache': cache, 'request_id': p['request_id']}), 'PREVIEW_IDENTITY')
    sr = rows_by_id(s['rows'], s['members'])
    pr = rows_by_id(p['result_rows'], s['members'])
    vr = rows_by_id(v['rows'], s['members'])
    require(set(v['members']) == set(s['members']) and len(v['members']) == len(s['members']), 'MEMBERS_MISMATCH')
    require(all(sr[k]['issuer_id'] == pr[k]['issuer_id'] == vr[k]['issuer_id'] for k in sr), 'ISSUER_MISMATCH')
    n = len(sr)
    counts = raw_counts(list(pr.values()))
    require(p['coverage']['denominator']['kind'] == 'ORIGINAL_MEMBER_ROWS', 'CONTEXT_MISMATCH')
    check_count(p['coverage']['denominator']['count'], n)
    check_count(p['coverage']['denominator']['unique_issuers'], len({r['issuer_id'] for r in sr.values()}))
    for key, value in counts.items():
        item = p['coverage']['axes'][key] if key in 'QGV' else p['coverage']['all_axes' if key == 'joint' else key]
        check_count(item['valid'], value)
        check_count(item['denominator'], n)
    return s, p, v, sr, pr


def project_scope(spec, checked, *, members, unit, population_id, population_version):
    s, p, v, sr, pr = checked
    rows = [pr[k] for k in sorted(members)]
    population = {'id': population_id, 'version': population_version, 'unit': unit,
                  'denominator': len(members), 'unique_issuers': len({r['issuer_id'] for r in rows}),
                  'members_hash': digest(sorted(members))}
    if unit == 'ISSUER':
        require(population['denominator'] == population['unique_issuers'], 'DUPLICATE_ISSUER')
    return {'population': population,
            'scoring_population': {'id': s['universe_id'], 'version': s['universe_version'],
                                   'denominator': len(s['members']), 'members_hash': digest(sorted(s['members']))},
            'valuation_date': s['valuation_date'], 'input_as_of': s['as_of'],
            'versions': {k: p[k] for k in VERSION_KEYS}, 'classification': deepcopy(s['classification_context']),
            'result_identity': {k: p[k] for k in ('preview_id', 'config_hash', 'input_hash', 'cache_key')},
            'sources': {k: reference(spec[k]) for k in ('snapshot', 'preview', 'view')},
            'counts': {k: count(x, len(rows), reason='NULL_IN_RETAINED_RESULT' if x < len(rows) else None)
                       for k, x in raw_counts(rows).items()}}


def _summarize(job):
    require(job['schema_version'] == 'classification-counts-job/1' and job['mode'] == 'summary-only', 'JOB_SCHEMA')
    require(job['data_kind'] in ('SYNTHETIC', 'RETAINED_INPUT'), 'JOB_DATA_KIND')
    operating = checked_scope(job['operating'], job['valuation_date'])
    expanded = checked_scope(job['expanded'], job['valuation_date'])
    require(operating[0]['as_of'] == expanded[0]['as_of'], 'CONTEXT_MISMATCH')
    summary, held, audit = (load(job[k]) for k in ('summary', 'held', 'gate_linkage'))
    require(summary['schema_version'] == 'held-expanded-classification-summary/1'
            and summary['valuation_date'] == job['valuation_date'], 'CONTEXT_MISMATCH')
    require(summary['full_market_denominator'] is None and summary['full_market_coverage'] is None, 'FULL_MARKET_UNMEASURED')
    financial_ids = set()
    for issuer, rec in held['financials'].items():
        require(isinstance(rec['state'], str) and bool(rec['state']), 'INVALID_HELD_STATE')
        if rec['state'] != 'NOT_AVAILABLE':
            financial_ids.add(issuer)
    es, _, _, erows, _ = expanded
    require(financial_ids <= {r['issuer_id'] for r in erows.values()}, 'HELD_OUTSIDE_CATALOG')
    cohort = [k for k, r in erows.items() if r['issuer_id'] in financial_ids]
    scopes = {
        'operating': project_scope(job['operating'], operating, members=operating[0]['members'], unit='CODE_ROW',
                                   population_id=operating[0]['universe_id'], population_version=operating[0]['universe_version']),
        'catalog': project_scope(job['expanded'], expanded, members=es['members'], unit='ISSUER',
                                 population_id=es['universe_id'], population_version=es['universe_version']),
        'held_financial_subsample': project_scope(job['expanded'], expanded, members=cohort, unit='ISSUER',
                                                  population_id=es['universe_id'] + ':retained-financials',
                                                  population_version='source-sha256:' + job['held']['sha256'])}
    linked = set()
    arows = rows_by_id(audit['rows'], es['members'])
    for key, a in arows.items():
        row = erows[key]
        require(a['issuer_id'] == row['issuer_id'], 'ISSUER_MISMATCH')
        require(a['status'] in ('CONNECTED', 'UNAVAILABLE'), 'GATE_LINKAGE_MISMATCH')
        gate = row['gate']
        if a['status'] == 'UNAVAILABLE':
            require(gate is None and bool(a['reason']), 'GATE_LINKAGE_MISMATCH')
            continue
        require(isinstance(gate, dict) and a['reason'] is None, 'GATE_LINKAGE_MISMATCH')
        require(score_present(gate['q_industry_percentile']), 'GATE_LINKAGE_MISMATCH')
        require(gate['as_of'] == es['valuation_date'] and gate['source_as_of'] == es['as_of']
                and gate['calc_version'] == 'qgv2-calc/2026-10-23.1'
                and gate['derivation'] == 'OFFICIAL_Q_ONLY_REPLAY'
                and 'sec-qgv2.json#sha256=' + a['gate_source_sha256'] in gate['provenance']
                and a['gate_universe_id'] == operating[0]['universe_id']
                and a['gate_universe_version'] == operating[0]['universe_version']
                and a['scope'] == 'RETAINED_UNIVERSE504_OFFICIAL_Q_REPLAY_NOT_EXPANDED_Q', 'GATE_LINKAGE_MISMATCH')
        linked.add(key)
    check_count(audit['connected'], len(linked))
    check_count(summary['official_gate_connected'], len(linked))
    scopes['operating']['official_q_gate_input'] = count(None, len(operating[0]['members']), reason='NO_OPERATING_GATE_AUDIT_REQUESTED')
    for name, members in [('catalog', es['members']), ('held_financial_subsample', cohort)]:
        scope = scopes[name]
        scope['official_q_gate_input'] = {**count(len(linked & set(members)), len(members)),
            'meaning': 'CONNECTED_INPUT_NOT_GATE_PASS_NOT_SECTOR_Q',
            'calc_version': 'qgv2-calc/2026-10-23.1',
            'basis': 'RETAINED_UNIVERSE504_OFFICIAL_Q_REPLAY_NOT_EXPANDED_Q',
            'sources': {'gate_linkage': reference(job['gate_linkage']), 'held_cohort': reference(job['held'])}}
        check_count(summary[name]['issuers'], len(members))
        for key, item in scope['counts'].items():
            check_count(summary[name][key], item['valid'])
    out = deepcopy(summary)
    out['calculation_counts'] = {'schema_version': SCHEMA, 'data_kind': job['data_kind'],
        'valuation_date': job['valuation_date'], 'operation': 'EXTRACT_EXISTING_RESULTS_NO_RECALCULATION',
        'scopes': scopes, 'source_summary': reference(job['summary']),
        'full_market_denominator': None, 'full_market_coverage': None}
    require(len((json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()) <= MAX_BYTES,
            'DELIVERY_LIMIT_EXCEEDED')
    return out


def summarize(job):
    """Fail closed before emitting output; missing fields are not zero counts."""
    try:
        return _summarize(job)
    except KeyError as exc:
        raise ValueError('MISSING_FIELD:' + str(exc)) from None
