"""Evidence-bound source-industry query through the existing macro projection.

No numerical model, acquisition, automatic classification or source aggregation.
"""
from copy import deepcopy
import re
from .catalog import current_taxonomy, dictionary
from .records import _available
from .technical_macro import macro_projection, _rows, _text
from ..kis_price_bridge import _day
from ..sector_qgv import digest, timestamp
from ..classification_counts import require

CONTEXT = ('valuation_date', 'classification_hash', 'dictionary_version', 'mapping_version')
OBS_FIELDS = ('source_id', 'value', 'unit', 'frequency', 'seasonal_adjustment', 'observation_period',
              'state', 'reason', 'query_usable', 'stale', 'available_at', 'official_release_at',
              'official_release_status', 'source_version_id', 'archive_version_id', 'first_acquired_at',
              'selected_version_acquired_at', 'last_successful_update_at', 'update_status',
              'historical_pit_eligible', 'historical_pit_reason', 'availability_basis', 'observation_id')


def _time_reason(value, cutoff, prefix):
    try:
        known = _available(value, cutoff) if _text(value) else None
    except (TypeError, ValueError):
        known = None
    return [] if known is True else [prefix + ('_NOT_AVAILABLE' if known is False else '_TIME_UNKNOWN')]


def _query(view, bundle, cache):
    _rows(view)
    require(bundle['schema_version'] == 'macro-industry-evidence/1', 'MAPPING_SCHEMA')
    require(cache['schema_version'] == 'macro-current-query/1', 'CACHE_SCHEMA')
    require(bundle['data_kind'] == view['data_kind'], 'DATA_KIND_MISMATCH')
    require(bundle['classification_context'] == {k: view[k] for k in CONTEXT}, 'CLASSIFICATION_CONTEXT_MISMATCH')
    cutoff, day = view['knowledge_as_of'], view['valuation_date']
    # The cache remains a query at its original instant. This adapter never
    # refreshes stale flags or replaces release time with acquisition time.
    cache_future = timestamp(cache['query_at']) > timestamp(cutoff)
    evidence = {e['evidence_id']: e for e in bundle['evidence']}
    require(len(evidence) == len(bundle['evidence']), 'DUPLICATE_EVIDENCE')
    for e in evidence.values():
        require(all(_text(e.get(k)) for k in ('evidence_id', 'ref', 'locator')) and
                re.fullmatch('[0-9a-f]{64}', e.get('sha256', '')) is not None, 'EVIDENCE_REFERENCE_REQUIRED')
    industries = {r['id']: r['parent_sector'] for r in dictionary(view['dictionary_version'])['industries']}
    source_links, diagnostics, output_mappings, active_ids = [], [], [], []
    seen = set()
    for original in bundle['mappings']:
        m = deepcopy(original)
        require(all(_text(m.get(k)) for k in ('mapping_id', 'revision_id')), 'MAPPING_ID_REQUIRED')
        key = (m['mapping_id'], m['revision_id'])
        require(key not in seen, 'DUPLICATE_MAPPING_REVISION'); seen.add(key)
        require(m['allocation_weights'] is None, 'ALLOCATION_NOT_DEFINED')
        require(m['status'] in ('CONFIRMED', 'UNKNOWN'), 'MAPPING_STATUS')
        require(isinstance(m['series_ids'], list) and len(m['series_ids']) == len(set(m['series_ids'])) and
                all(_text(x) for x in m['series_ids']), 'SERIES_IDS_INVALID')
        require(all(ref in evidence for ref in m['evidence_refs']), 'MAPPING_EVIDENCE_MISSING')
        reasons = ['CACHE_FROM_FUTURE'] if cache_future else []
        if m['status'] == 'UNKNOWN':
            require(m['relation'] == 'UNKNOWN' and not m['targets'] and m['unknown_reasons'], 'UNKNOWN_MAPPING_REASON_REQUIRED')
            reasons += m['unknown_reasons']
        else:
            require(all(_text(m['source'].get(k)) for k in ('system', 'code', 'name', 'version')), 'SOURCE_DEFINITION_REQUIRED')
            defined_series = {sid for ref in m['evidence_refs']
                              if evidence[ref].get('source_definition') == m['source']
                              for sid in evidence[ref].get('series_ids', [])}
            require(m['series_ids'] and set(m['series_ids']) <= defined_series, 'SOURCE_SERIES_DEFINITION_MISMATCH')
            require(m['relation'] in ('EXACT', 'PARTIAL', 'MULTIPLE') and m['targets'] and
                    m['evidence_refs'] and m['includes'] and isinstance(m['excludes'], list), 'MAPPING_SCOPE_REQUIRED')
            require((m['relation'] == 'MULTIPLE') == (len(m['targets']) > 1), 'RELATION_CARDINALITY')
            start, end = _day(m['valid_from']), m['valid_to']
            if end is not None: require(start < _day(end), 'MAPPING_RANGE_INVALID')
            if start > day or (end is not None and day >= end): reasons.append('OUTSIDE_APPLICABILITY')
            for field in ('available_at', 'acquired_at', 'reviewed_at'):
                reasons += _time_reason(m[field], cutoff, 'MAPPING')
            for ref in m['evidence_refs']:
                e = evidence[ref]
                if e.get('status') != 'VERIFIED': reasons.append('EVIDENCE_UNVERIFIED')
                for field in ('available_at', 'acquired_at'):
                    reasons += _time_reason(e.get(field), cutoff, 'EVIDENCE')
            target_ids = []
            for target in m['targets']:
                tid = target['industry_id']; target_ids.append(tid)
                require(tid in industries and target['sector_id'] == industries[tid], 'TARGET_PARENT_MISMATCH')
                relation = target['scope_relation']
                require(relation in ('EXACT', 'SOURCE_BROADER', 'SOURCE_NARROWER', 'OVERLAP'), 'SCOPE_RELATION')
                require((m['relation'] == 'EXACT') == (relation == 'EXACT'), 'EXACT_SCOPE_MISMATCH')
            require(len(target_ids) == len(set(target_ids)), 'DUPLICATE_TARGET')
            if not reasons:
                active_ids.append(key)
                for target in m['targets']:
                    source_links.append(dict(system=m['source']['system'], version=m['source']['version'], code=m['source']['code'],
                        target_industry_id=target['industry_id'], relation=target['scope_relation'], evidence_refs=m['evidence_refs'],
                        valid_from=start, valid_to=end, recorded_at=m['reviewed_at'], acquired_at=m['acquired_at'],
                        mapping_id=m['mapping_id'], revision_id=m['revision_id'], series_ids=m['series_ids']))
        m['query_status'] = 'AVAILABLE' if not reasons else 'UNKNOWN'
        m['query_reasons'] = sorted(set(reasons)); output_mappings.append(m)
        if reasons:diagnostics.append({'mapping_id':key[0], 'revision_id':key[1], 'reasons':sorted(set(reasons))})
    # Existing contract validates source-system identity, active duplicates and
    # dated links. No per-screen classifier and no new macro scoring engine.
    projected = macro_projection(view, source_links)
    observations, companies = {}, []
    for row in projected['rows']:
        refs = row['statistic_mapping']['source_links']
        series_ids = sorted({s for link in refs for s in link['series_ids']})
        usable = []
        series_gaps = []
        for sid in series_ids:
            source = cache['series'].get(sid)
            reasons = []
            if source is None: reasons.append('SERIES_NOT_IN_CACHE')
            else:
                require(source['source_id'] == sid, 'SERIES_ID_MISMATCH')
                reasons += _time_reason(source.get('available_at'), cutoff, 'OBSERVATION')
                if source.get('query_usable') is not True: reasons.append('CURRENT_QUERY_NOT_USABLE')
                if sid not in observations:
                    observations[sid] = {k: deepcopy(source.get(k)) for k in OBS_FIELDS}
                    observations[sid]['cache_query_at'] = cache['query_at']
                    observations[sid]['query_reasons'] = sorted(set(reasons))
                    if reasons:
                        observations[sid]['value'] = None
                if not reasons:usable.append(sid)
            if reasons:series_gaps.append({'series_id':sid, 'reasons':sorted(set(reasons))})
        companies.append({'company_id':row['company_id'], 'issuer_id':row['issuer_id'],
            'classification_record_id':row['classification_record_id'], 'sector':row['sector'], 'industry':row['industry'],
            'mapping_refs':[{'mapping_id':r['mapping_id'],'revision_id':r['revision_id']} for r in refs],
            'related_series_ids':series_ids, 'query_usable_series_ids':usable, 'series_gaps':series_gaps,
            'mapping_status':row['statistic_mapping']['status'],
            'mapping_reasons':row['statistic_mapping']['reasons']})
    identity = {'view':digest(view), 'mappings':digest(bundle), 'cache':digest(cache)}
    return {'schema_version':'company-industry-macro-query/1','data_kind':view['data_kind'],
        'classification_context':deepcopy(bundle['classification_context']), 'knowledge_as_of':cutoff,
        'macro_query_at':cache['query_at'], 'cache_asof':cache.get('cache_asof'),
        'input_hashes':identity, 'cache_key':digest({'contract':'company-industry-macro-query/1',**identity}),
        'taxonomy':current_taxonomy(), 'companies':companies, 'mappings':output_mappings,
        'evidence':deepcopy(bundle['evidence']), 'observations':observations, 'diagnostics':diagnostics,
        'counts':{'company_rows':len(companies), 'linked_companies':sum(r['mapping_status']=='LINKED' for r in companies),
                  'active_mappings':len(active_ids), 'unique_series':len(observations)},
        'aggregate_value':None, 'allocation_weights':None, 'probabilities':None, 'sector_returns':None,
        'historical_pit_certified':False, 'official_results_changed':False}


def query_industry_evidence(view, bundle, cache):
    try:
        return _query(view, bundle, cache)
    except KeyError as exc:
        raise ValueError('MISSING_FIELD:'+str(exc)) from None
