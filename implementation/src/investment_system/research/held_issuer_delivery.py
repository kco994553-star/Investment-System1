"""Private, bounded static projection of existing issuer results and evidence."""
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from urllib.parse import quote

from .classification_counts import checked_scope, load, reference, project_scope, require, MAX_BYTES
from .expanded_held_classification import issuer_members
from .retained_coverage import coverage_scope
from .sector_qgv import config_hash, default_config, digest


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def descriptor(path, body):
    return {'path': path, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def _project(job, *, index_bytes):
    require(job['schema_version'] == 'held-issuer-delivery-job/1', 'DELIVERY_JOB_SCHEMA')
    require(job['data_kind'] in ('SYNTHETIC', 'RETAINED_INPUT'), 'DATA_KIND_REQUIRED')
    require(type(index_bytes) is int and 0 < index_bytes <= MAX_BYTES, 'INDEX_BYTE_LIMIT')
    op = checked_scope(job['operating'], job['valuation_date'])
    ex = checked_scope(job['expanded'], job['valuation_date'])
    require(op[0]['as_of'] == ex[0]['as_of'], 'CONTEXT_MISMATCH')
    require(op[1]['config_hash'] == ex[1]['config_hash'] == config_hash(default_config()), 'DEFAULT_BASELINE_REQUIRED')
    held, crosswalk, gates = (load(job[k]) for k in ('held', 'crosswalk', 'gate_linkage'))
    issuer_ids = {i for i, r in held['financials'].items() if r['state'] != 'NOT_AVAILABLE'}
    input_rows, result_rows = ex[3], ex[4]
    require(issuer_ids <= {r['issuer_id'] for r in input_rows.values()}, 'HELD_OUTSIDE_CATALOG')
    members = sorted(k for k, r in input_rows.items() if r['issuer_id'] in issuer_ids)
    require(len(members) == len(issuer_ids), 'DUPLICATE_ISSUER')
    scope = project_scope(job['expanded'], ex, members=members, unit='ISSUER',
        population_id=ex[0]['universe_id'] + ':retained-financials', population_version='source-sha256:' + job['held']['sha256'])
    context = {k: v for k, v in scope.items() if k != 'counts'}
    context['sources'].update(held=reference(job['held']), crosswalk=reference(job['crosswalk']), gate_linkage=reference(job['gate_linkage']))
    context_hash = digest(context)
    by_issuer, observations, names = defaultdict(list), defaultdict(list), defaultdict(set)
    for row in op[3].values():
        by_issuer[row['issuer_id']].append(row['company_id'])
    seen = set()
    for row in crosswalk:
        key = (row['issuer_id'], row['observed_ticker'])
        require(key not in seen, 'DUPLICATE_CATALOG_OBSERVATION')
        seen.add(key)
        require(row['analysis_row_id'] in input_rows and input_rows[row['analysis_row_id']]['issuer_id'] == row['issuer_id'], 'CROSSWALK_ID_MISMATCH')
        observations[row['issuer_id']].append(deepcopy(row))
    if 'candidates' in held:
        cm, cw = issuer_members(held['candidates'])
        require(set(cm) == set(ex[0]['members']) and cw == crosswalk, 'CATALOG_SOURCE_MISMATCH')
        for row in held['candidates']:
            if row.get('title'):
                names[str(row['cik_str']).zfill(10)].add(row['title'])
    classes = {r['company_id']: r for r in ex[2]['rows']}
    sources = {r['source_id']: r for r in ex[2]['sources']}
    require(len(sources) == len(ex[2]['sources']), 'DUPLICATE_EVIDENCE_SOURCE')
    ga = {r['company_id']: r for r in gates['rows']}
    require(len(ga) == len(gates['rows']) and set(ga) == set(ex[0]['members']), 'GATE_AUDIT_MEMBERS_MISMATCH')
    gaps = load(job['input_gaps']) if 'input_gaps' in job else None
    gr = {r['company_id']: r for r in gaps['rows']} if gaps else {}
    if gaps:
        require(len(gr) == len(gaps['rows']) and set(gr) == set(ex[0]['members']), 'GAP_MEMBERS_MISMATCH')
    files, index = {}, []
    for member in members:
        row, cls = result_rows[member], classes[member]
        issuer = row['issuer_id']
        require(ga[member]['issuer_id'] == issuer, 'GATE_AUDIT_ISSUER_MISMATCH')
        require(all(ref in sources for ref in cls['source_refs']), 'EVIDENCE_REFERENCE_MISSING')
        require(ga[member]['status'] in ('CONNECTED', 'UNAVAILABLE') and
                (ga[member]['status'] == 'CONNECTED') == (input_rows[member]['gate'] is not None), 'GATE_LINKAGE_MISMATCH')
        if member in gr:
            require(gr[member]['issuer_id'] == issuer and gr[member]['valuation_date'] == job['valuation_date'], 'GAP_CONTEXT_MISMATCH')
        factors = {k: {f: deepcopy(v[f]) for f in ('score', 'score_status', 'raw_status', 'valid_n',
                                                  'raw_components_available', 'verified_external_available')}
                   for k, v in row['factors'].items() if k in row.get('selected_variants', [])}
        detail = {'schema_version': 'held-issuer-detail/1', 'data_kind': job['data_kind'],
            'issuer_id': issuer, 'analysis_row_id': member, 'context_hash': context_hash, 'context': context,
            'operating_code_rows': sorted(by_issuer[issuer]), 'observed_names': sorted(names[issuer]),
            'classification': deepcopy(cls), 'evidence': [deepcopy(sources[k]) for k in sorted(set(cls['source_refs']))],
            'business_profile': {'status': 'NOT_DELIVERED', 'description': None,
                                 'reason': 'CLASSIFICATION_EVIDENCE_IS_NOT_FULL_BUSINESS_PROFILE'},
            'catalog_observations': sorted(observations[issuer], key=lambda x: x['observed_ticker']),
            'calculation': {**{k: deepcopy(row[k]) for k in ('axes', 'rank', 'status', 'total', 'pre_gate_total', 'gate_status')},
                            'selected_variants': list(row.get('selected_variants', [])), 'factors': factors,
                            'rank_scope': 'RETAINED_CATALOG_SCORE_POPULATION_NOT_WHOLE_MARKET'},
            'official_q_gate_input': deepcopy(ga[member]),
            'security_prices_technical': {'status': 'NOT_CONNECTED', 'prices': None, 'technical': None,
                'eligibility': None, 'reason': 'ISSUER_RESULT_DOES_NOT_ESTABLISH_DATED_SECURITY_PRICE_TECHNICAL_LINK'},
            'input_gaps': {k: deepcopy(v) for k, v in gr.get(member, {}).items() if k != 'official_q_gate'},
            'input_gaps_source': reference(job['input_gaps']) if gaps else None}
        name = 'issuers/' + quote(issuer, safe='') + '.json'
        body = encode(detail)
        require(len(body) <= MAX_BYTES, 'DETAIL_BYTE_LIMIT')
        files[name] = body
        index.append({'issuer_id': issuer, 'analysis_row_id': member, 'observed_names': sorted(names[issuer]),
            'observed_tickers': sorted({r['observed_ticker'] for r in observations[issuer]}),
            'operating_code_rows': sorted(by_issuer[issuer]),
            'classification': {k: deepcopy(cls[k]) for k in ('sector', 'accounting', 'industry')},
            'calculation_status': row['status'], 'detail': descriptor(name, body)})
    indexes, page = [], []
    def page_bytes(rows):
        return encode({'schema_version': 'held-issuer-index/1', 'data_kind': job['data_kind'], 'context_hash': context_hash, 'rows': rows})
    def flush(rows):
        name = 'index-%04d.json' % (len(indexes) + 1)
        files[name] = page_bytes(rows);indexes.append(name)
    for row in index:
        require(len(page_bytes([row])) <= index_bytes, 'INDEX_ROW_BYTE_LIMIT')
        if page and len(page_bytes(page + [row])) > index_bytes:
            flush(page);page = []
        page.append(row)
    if page or not indexes:
        flush(page)
    coverage = {'schema_version': 'retained-default-coverage/1', 'data_kind': job['data_kind'],
        'valuation_date': job['valuation_date'], 'context_hash': context_hash,
        'operation': 'AGGREGATE_RETAINED_RESULTS_NOT_RECALCULATION',
        'scopes': {'operating': coverage_scope(op[1]['result_rows'], op[2]['rows']),
                   'catalog': coverage_scope(ex[1]['result_rows'], ex[2]['rows']),
                   'held_financial_subsample': coverage_scope([result_rows[k] for k in members], [classes[k] for k in members])},
        'source_refs': {'operating': {k: reference(job['operating'][k]) for k in ('snapshot', 'preview', 'view')},
                        'expanded': {k: reference(job['expanded'][k]) for k in ('snapshot', 'preview', 'view')}},
        'full_market': {'denominator': None, 'coverage': None, 'state': 'NOT_MEASURED', 'reason': 'DATED_MARKET_MEMBERSHIP_UNCONFIRMED'}}
    files['coverage.json'] = encode(coverage)
    manifest = {'schema_version': 'held-issuer-delivery/1', 'data_kind': job['data_kind'],
        'context': context, 'context_hash': context_hash, 'indexes': indexes, 'coverage_path': 'coverage.json',
        'max_file_bytes': MAX_BYTES, 'index_byte_budget': index_bytes,
        'index_rows': len(index), 'detail_rows': len(members),
        'scope': 'HELD_FINANCIAL_ISSUERS_NOT_ELIGIBLE_UNIVERSE',
        'full_market_denominator': None, 'full_market_coverage': None,
        'files': [descriptor(k, files[k]) for k in sorted(files)]}
    files['manifest.json'] = encode(manifest)
    verify_delivery(files)
    return files


def project_delivery(job, *, index_bytes=MAX_BYTES):
    try:
        return _project(job, index_bytes=index_bytes)
    except KeyError as exc:
        raise ValueError('MISSING_FIELD:' + str(exc)) from None


def verify_delivery(files):
    """Validate the whole new set before publication; no scoring or normalization."""
    m = json.loads(files['manifest.json'])
    require(m['schema_version'] == 'held-issuer-delivery/1', 'DELIVERY_SCHEMA')
    require(m['context_hash'] == digest(m['context']), 'CONTEXT_HASH_MISMATCH')
    require(m['full_market_denominator'] is None and m['full_market_coverage'] is None, 'MARKET_SCOPE_INVALID')
    entries = {r['path']: r for r in m['files']}
    require(len(entries) == len(m['files']) and set(files) == set(entries) | {'manifest.json'}, 'DELIVERY_FILE_SET')
    require(all(len(b) <= MAX_BYTES for b in files.values()), 'DELIVERY_BYTE_LIMIT')
    for name, entry in entries.items():
        require(name == 'coverage.json' or (name.startswith('issuers/') and name.endswith('.json') and name.count('/') == 1)
                or (name.startswith('index-') and name.endswith('.json') and '/' not in name), 'UNSAFE_DELIVERY_PATH')
        require(descriptor(name, files[name]) == entry, 'DELIVERY_HASH_MISMATCH')
    require(len(set(m['indexes'])) == len(m['indexes']), 'DUPLICATE_INDEX_PAGE')
    require(set(m['indexes']) == {p for p in entries if p.startswith('index-')}, 'INDEX_FILE_SET')
    ids, details = set(), set()
    for name in m['indexes']:
        p = json.loads(files[name])
        require(p['schema_version'] == 'held-issuer-index/1' and p['context_hash'] == m['context_hash'], 'INDEX_CONTEXT_MISMATCH')
        for row in p['rows']:
            require(row['issuer_id'] not in ids, 'DUPLICATE_INDEX_ISSUER');ids.add(row['issuer_id'])
            dref = row['detail'];path = dref['path']
            require(path in entries and entries[path] == dref and path not in details, 'INDEX_DETAIL_REFERENCE_MISMATCH')
            details.add(path);d = json.loads(files[path])
            require(d['schema_version'] == 'held-issuer-detail/1' and d['issuer_id'] == row['issuer_id']
                    and d['analysis_row_id'] == row['analysis_row_id'], 'DETAIL_ID_MISMATCH')
            require(d['context_hash'] == m['context_hash'] and d['context'] == m['context'], 'DETAIL_CONTEXT_MISMATCH')
            require(d['data_kind'] == p['data_kind'] == m['data_kind'], 'DATA_KIND_MISMATCH')
            require(d['operating_code_rows'] == row['operating_code_rows'] and
                    all(d['classification'][k] == row['classification'][k] for k in ('sector', 'accounting', 'industry')), 'DETAIL_STATE_MISMATCH')
            require(d['observed_names'] == row['observed_names'] and
                    sorted({r['observed_ticker'] for r in d['catalog_observations']}) == row['observed_tickers'] and
                    d['calculation']['status'] == row['calculation_status'], 'INDEX_VALUE_MISMATCH')
    require(details == {p for p in entries if p.startswith('issuers/')}, 'UNINDEXED_DETAIL')
    require(len(ids) == m['index_rows'] == m['detail_rows'] == m['context']['population']['denominator'], 'DELIVERY_DENOMINATOR_MISMATCH')
    coverage = json.loads(files[m['coverage_path']])
    require(coverage['schema_version'] == 'retained-default-coverage/1' and coverage['context_hash'] == m['context_hash'], 'COVERAGE_CONTEXT_MISMATCH')
    return m
