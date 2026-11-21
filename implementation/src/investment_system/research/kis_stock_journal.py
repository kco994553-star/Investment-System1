"""Storage-neutral KIS source journal and disposable stock responses.

Only staged files are produced. A publisher must validate and promote the
complete private view generation separately from the immutable source commit.
"""
import argparse
from collections.abc import Mapping
import gzip
import io
import json
from pathlib import Path
import re
import time
import zlib

from ._private_artifacts import digest, json_bytes, MAX_BYTES
from .kis_rebuild import child, load_request, pinned, sha, need, write_bundle
from .kis_price_bridge import validate_contract, price_rows, _day, _ts
from .kis_stock_bundle import indicator_series, FIELDS, INDICATORS
from .private_kis_preprocess import calculate_and_project
from .private_kis_reference import reference_files, official_reference

SCOPE = 'OWNER_PRIVATE_ONLY'
JOURNAL = 'kis-stock-journal/1'
INDEXED_JOURNAL = 'kis-stock-journal/2'
VIEW = 'kis-stock-generation/1'
PROJECTION_VERSION = 'KIS_STOCK_GSQ015_1'
SMALL_LIMIT = 3072
ROW_FIELDS = ('raw_bars', 'bars', 'basis', 'price_basis_date')


def ref(path, value):
    return dict(path=path, bytes=len(value), sha256=sha(value))


def read(root, reference):
    value = child(root, reference['path']).read_bytes()
    need(len(value) == reference['bytes'] and sha(value) == reference['sha256'], 'STOCK_ARCHIVE_PIN')
    return value


def parse(root, reference):
    return json.loads(read(root, reference))


def clock_context(config):
    return {key: config[key] for key in ('evaluation_day', 'calculated_at', 'series_id_prefix',
            'price_basis', 'financial', 'symbols', 'monthends') if key in config}


def header(contract):
    return {key: value for key, value in contract.items() if key not in ROW_FIELDS}


def contract_from_state(state, basis):
    raw = [row for _, row in sorted(state['rows'].items())]
    value = dict(state['header'], raw_bars=raw, basis=basis,
                 price_basis_date=raw[-1]['date'] if raw else None)
    value['bars'] = price_rows(value, value['price_basis_date']) if raw else []
    validate_contract(value)
    return value


def economic_row(row):
    return {key: value for key, value in row.items() if key not in ('source_sha256', 'collected_at')}


def changes(contracts, prior, config, revision):
    """A repeated provider window neither drops history nor rewrites row provenance."""
    need(not (set(prior)-set(contracts)), 'JOURNAL_SCOPE_REMOVAL')
    patches = {}
    for code in contracts:
        contract = contracts[code]
        need(contract.get('publication_scope') == SCOPE and contract.get('source_query', {}).get('MODP') == '0',
             'RAW_PRIVATE_SOURCE_REQUIRED')
        before = prior.get(code, {'rows': {}, 'header': {}})
        after_header = header(contract)
        old_header = before['header']
        need(not old_header or _ts(after_header['collected_at']) >= _ts(old_header['collected_at']),
             'JOURNAL_SERIES_CLOCK_REGRESSION')
        need(not old_header or all(old_header.get(key) == after_header.get(key)
             for key in ('symbol', 'security_id', 'source', 'exchange', 'currency')), 'JOURNAL_SERIES_IDENTITY')
        changes = {key: value for key, value in after_header.items()
                   if key not in old_header or old_header[key] != value}
        removed = sorted(old_header.keys() - after_header.keys())
        rows = []
        prior_day = max(before['rows'], default='')
        admitted = {row['date'] for row in contract['raw_bars']}
        for row in contract['raw_bars']:
            day = row['date']
            need(day <= config['evaluation_day'], 'JOURNAL_FUTURE_ROW')
            old = before['rows'].get(day)
            if old and economic_row(old) == economic_row(row):
                continue
            need(not prior_day or day > prior_day or revision, 'JOURNAL_REVISION_REFERENCE_REQUIRED')
            rows.append(dict(row=row, supersedes=digest(old) if old else None))
        # A newly rejected previously admitted observation must not stay active.
        for rejected in contract.get('rejected_rows', []):
            day = rejected.get('date')
            old = before['rows'].get(day)
            if old and day not in admitted:
                need(revision, 'JOURNAL_REVISION_REFERENCE_REQUIRED')
                rows.append(dict(date=day, row=None, supersedes=digest(old)))
        if old_header and any(k in changes or k in removed for k in ('splits', 'identity', 'confirmed_ranges', 'held_ranges')):
            need(revision, 'JOURNAL_REVISION_REFERENCE_REQUIRED')
        if prior and not old_header and any(row['row']['date'] < config['evaluation_day'] for row in rows):
            need(revision, 'JOURNAL_REVISION_REFERENCE_REQUIRED')
        if rows or changes or removed:
            patches[code] = dict(header=changes, remove=removed, rows=rows)
    return patches


def apply_frame(state, patches, day, *, revision):
    for code, patch in patches.items():
        part = state.setdefault(code, {'header': {}, 'rows': {}})
        newest = max(part['rows'], default='')
        seen = set()
        for item in patch['rows']:
            row = item['row']
            observed = _day(row['date'] if row is not None else item['date'])
            need(observed <= day and observed not in seen, 'JOURNAL_ROW_DATE')
            seen.add(observed)
            old = part['rows'].get(observed)
            need(item['supersedes'] == (digest(old) if old else None), 'JOURNAL_REVISION_CHAIN')
            need(not newest or observed > newest or revision, 'JOURNAL_REVISION_REFERENCE_REQUIRED')
            if row is None:
                need(old is not None, 'JOURNAL_MISSING_REJECTION_TARGET')
                del part['rows'][observed]
            else:
                part['rows'][observed] = row
        for key in patch['remove']:
            del part['header'][key]
        part['header'].update(patch['header'])


def patch_files(patches, *, bootstrap=False):
    """Split large baselines without an unbounded blob or per-symbol daily index."""
    def chunks(items):
        value = gzip.compress(json_bytes(dict(items)), compresslevel=6, mtime=0)
        if len(value) <= MAX_BYTES:
            yield value
        else:
            need(len(items) > 1, 'STOCK_ARCHIVE_FILE_LIMIT')
            middle = len(items)//2
            yield from chunks(items[:middle])
            yield from chunks(items[middle:])
    items = sorted(patches.items())
    if bootstrap:
        for start in range(0, len(items), 32):
            yield from chunks(items[start:start+32])
    elif items:
        yield from chunks(items)


def archive_files(config, patches, parent, revision=None):
    files = {}
    parts = []
    for value in patch_files(patches, bootstrap=parent is None):
        path = f'rows/{sha(value)}.json.gz'
        files[path] = value
        parts.append(ref(path, value))
    frame = dict(schema=JOURNAL, publication_scope=SCOPE, previous=parent,
                 context=clock_context(config), parts=parts, revision=revision)
    value = json_bytes(frame)
    limit = MAX_BYTES if parent is None else SMALL_LIMIT
    if len(value) > limit and parts:
        # A historical append may have many independently capped row blobs.
        # Keep regular frames byte-compatible and pin one list on overflow.
        part_list = json_bytes(parts)
        need(len(part_list) <= MAX_BYTES, 'STOCK_ARCHIVE_FILE_LIMIT')
        part_index = gzip.compress(part_list, compresslevel=6, mtime=0)
        need(len(part_index) <= MAX_BYTES, 'STOCK_ARCHIVE_FILE_LIMIT')
        path = f'rows/{sha(part_index)}.json.gz'
        files[path] = part_index
        del frame['parts']
        frame.update(schema=INDEXED_JOURNAL, parts_index=ref(path, part_index))
        value = json_bytes(frame)
    need(len(value) <= limit, 'STOCK_ARCHIVE_SUMMARY_LIMIT')
    index = ref(f'captures/{sha(value)}.json', value)
    files[index['path']] = value
    return files, index


def replay(root, head):
    """Replay a SHA-pinned capture chain, without any materialized views."""
    chain = []
    seen = set()
    while head:
        need(head['sha256'] not in seen, 'JOURNAL_CAPTURE_CYCLE')
        seen.add(head['sha256'])
        frame = parse(root, head)
        need(frame['schema'] in (JOURNAL, INDEXED_JOURNAL) and frame['publication_scope'] == SCOPE, 'JOURNAL_CONTRACT')
        chain.append(frame)
        head = frame['previous']
    need(chain, 'STOCK_ARCHIVE_HEAD_REQUIRED')
    state = {}
    previous_day = ''
    previous_time = None
    for frame in reversed(chain):
        day = _day(frame['context']['evaluation_day'])
        need(day >= previous_day, 'JOURNAL_DATE_REGRESSION')
        moment = _ts(frame['context']['calculated_at'])
        need(previous_time is None or moment >= previous_time, 'JOURNAL_CLOCK_REGRESSION')
        previous_day, previous_time = day, moment
        codes = set()
        if frame['schema'] == INDEXED_JOURNAL:
            need('parts' not in frame, 'JOURNAL_CONTRACT')
            with gzip.GzipFile(fileobj=io.BytesIO(read(root, frame['parts_index']))) as stream:
                part_list = stream.read(MAX_BYTES + 1)
            need(len(part_list) <= MAX_BYTES, 'STOCK_ARCHIVE_FILE_LIMIT')
            parts = json.loads(part_list)
            need(isinstance(parts, list) and bool(parts), 'JOURNAL_PARTS_INDEX')
        else:
            need('parts_index' not in frame, 'JOURNAL_CONTRACT')
            parts = frame['parts']
        for part in parts:
            patches = json.loads(gzip.decompress(read(root, part)))
            need(not codes.intersection(patches), 'JOURNAL_DUPLICATE_CODE')
            codes.update(patches)
            apply_frame(state, patches, day, revision=frame['revision'])
    return chain[0]['context'], state


class Contracts(Mapping):
    """Compute one source contract at a time; journals contain only RAW rows."""
    def __init__(self, state, basis):
        self.state = state
        self.basis = basis

    def __len__(self):
        return len(self.state)

    def __iter__(self):
        return iter(sorted(self.state))

    def __getitem__(self, code):
        return contract_from_state(self.state[code], self.basis)


def history_key(raw, chart):
    return digest(dict(rows=raw, basis=chart['basis'], splits=chart['splits'],
                       display_state=chart['display']['state']))


def project_stock(contract, config, code, *, previous=None):
    day = config['evaluation_day']
    items = reference_files(calculate_and_project(contract, evaluation_day=day,
        series_id=config['series_id_prefix']+code, expected_contract_hash=digest(contract)), contract, day)
    payload = {path.split('/')[0]: json.loads(value) for path, value in items.items()
               if not path.startswith('manifests/')}
    chart = payload['chart']
    raw = chart.pop('raw_bars')
    bars = chart.pop('bars')
    count = len(previous['rows']) if previous else 0
    reuse = bool(count and count <= len(raw) and
                 history_key(raw[:count], chart) == previous['history_sha256'])
    start = count if reuse else 0
    series = indicator_series(dict(chart, raw_bars=raw), evaluation_day=day, start_index=start)
    values = series.pop('rows')
    series.pop('dates')
    rows = (previous['rows'][:] if reuse else []) + [
        [row[field] for field in FIELDS] + indicators for row, indicators in zip(bars[start:], values)]
    if reuse:
        runs = [dict(run) for run in previous['indicators']['reason_runs']]
        for run in series['reason_runs']:
            match = next((item for item in reversed(runs)
                          if item['field'] == run['field'] and item['to']+1 == run['from']
                          and item['reason'] == run['reason']), None)
            if match:
                match['to'] = run['to']
            else:
                runs.append(run)
        order = {name: i for i, name in enumerate(INDICATORS)}
        series['reason_runs'] = sorted(runs, key=lambda r: (order[r['field']], r['from']))
    result = dict(schema='kis-stock-view/1', publication_scope=SCOPE, symbol=chart['symbol'],
        evaluation_day=day, chart=dict(chart, schema='kis-chart-metadata/1',
        row_source_scope='DERIVED_VIEW_RETAINED_ORIGINALS_SEPARATE'),
        fields=FIELDS+INDICATORS, rows=rows, indicators=series,
        latest={k: payload[k] for k in ('technical','measures')},
        coverage=dict(scope='ALL_RETAINED_SESSIONS', retained_sessions=len(rows),
                      retained_start=rows[0][0] if rows else None, retained_end=rows[-1][0] if rows else None),
        additional_requests_for_toggle=0, additional_requests_for_retained_period=0,
        history_sha256=history_key(raw, chart))
    if chart['basis'] == 'SPLIT_ADJUSTED':
        result.update(raw_fields=FIELDS, raw_rows=[[r[k] for k in FIELDS] for r in raw])
    return result, start


def generation(contracts, config, capture, store_root, *, previous=None, stats=None):
    """Yield changed stock objects and the complete small-to-read serving manifest."""
    stats = stats if stats is not None else {}
    old = {}
    previous_root = None
    if previous:
        previous_root, previous_ref = previous
        manifest = parse(previous_root, previous_ref)
        need(manifest['schema'] == VIEW and manifest['publication_scope'] == SCOPE, 'STOCK_GENERATION_CONTRACT')
        need(manifest.get('projection_version') == PROJECTION_VERSION, 'STOCK_PROJECTION_VERSION')
        old = manifest['stocks']
        need(manifest['evaluation_day'] <= config['evaluation_day'], 'STOCK_GENERATION_DATE')
    references = {}
    contract_hashes = {}
    max_raw = max_compressed = 0
    stats.update(stock_written=0, stock_unchanged=0, stock_prefix_reused=0, stock_full_history=0)
    for code in contracts:
        contract = contracts[code]
        symbol = contract['symbol']
        need(symbol not in references, 'DUPLICATE_STOCK_SYMBOL')
        # Includes the label/clock context used by the existing technical engine.
        contract_hashes[code] = digest(contract)
        key = digest([PROJECTION_VERSION, code, contract_hashes[code], config['evaluation_day'], config['series_id_prefix']])
        old_ref = old.get(symbol)
        if old_ref and old_ref['input_sha256'] == key:
            # Confirm the previous object is still available before reusing it.
            read(previous_root, old_ref)
            entry = old_ref
            stats['stock_unchanged'] += 1
        else:
            prior_view = json.loads(gzip.decompress(read(previous_root, old_ref))) if old_ref else None
            view, reused = project_stock(contract, config, code, previous=prior_view)
            raw = json_bytes(view)
            need(len(raw) <= MAX_BYTES, 'STOCK_RESPONSE_LIMIT')
            compressed = gzip.compress(raw, compresslevel=6, mtime=0)
            object_path = f'stock/{sha(compressed)}.json.gz'
            entry = dict(ref(object_path, compressed), input_sha256=key, json_bytes=len(raw), json_sha256=sha(raw))
            stats['stock_written'] += 1
            stats['stock_prefix_reused' if reused else 'stock_full_history'] += 1
            yield object_path, compressed
        references[symbol] = entry
        max_raw = max(max_raw, entry['json_bytes'])
        max_compressed = max(max_compressed, entry['bytes'])
    stats.update(max_stock_json_bytes=max_raw, max_stock_gzip_bytes=max_compressed)
    # Independent, pinned QGV inputs are read from the checked-out private sources.
    financial = pinned(store_root, config['financial'])
    symbols = pinned(store_root, config['symbols'])
    months = pinned(store_root, config['monthends']) if config.get('monthends') else {}
    qgv = official_reference(financial, contracts, symbols, day=config['evaluation_day'],
        calculated_at=config['calculated_at'], expected_payload_hash=digest(financial),
        expected_links_hash=digest(symbols), expected_contract_hashes=contract_hashes,
        monthends=months)
    qgv.pop('private_raw_detail')
    qgv['raw_detail_state'] = 'REBUILDABLE_NOT_IN_VIEW'
    qgv_json = json_bytes(qgv)
    need(len(qgv_json) <= MAX_BYTES, 'QGV_FILE_LIMIT')
    compressed = gzip.compress(qgv_json, compresslevel=6, mtime=0)
    q_path = f'qgv/{sha(compressed)}.json.gz'
    q_ref = ref(q_path, compressed)
    if previous and manifest['qgv'] == q_ref:
        read(previous_root, q_ref)
    else:
        yield q_path, compressed
    manifest = json_bytes(dict(schema=VIEW, publication_scope=SCOPE, capture=capture,
                          projection_version=PROJECTION_VERSION,
                          evaluation_day=config['evaluation_day'], stocks=references,
                          qgv=q_ref, content_encoding='gzip'))
    yield 'generation.json', manifest
    pointer = json_bytes(dict(schema='kis-stock-query-ref/1', publication_scope=SCOPE,
                              capture=capture, generation=ref('generation.json', manifest)))
    need(len(pointer) <= SMALL_LIMIT, 'STOCK_ARCHIVE_SUMMARY_LIMIT')
    yield f'query-refs/{sha(pointer)}.json', pointer


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('append', 'restore'))
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--head', help='relative capture path')
    parser.add_argument('--head-sha256')
    parser.add_argument('--request', type=Path)
    parser.add_argument('--request-sha256')
    parser.add_argument('--revision-reference')
    parser.add_argument('--previous-view', type=Path)
    parser.add_argument('--previous-view-sha256')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    started = time.perf_counter()
    stats = {}
    try:
        need(args.check_only != bool(args.output_dir), 'CHOOSE_OUTPUT_OR_CHECK_ONLY')
        need(bool(args.head) == bool(args.head_sha256), 'STOCK_ARCHIVE_HEAD_PIN')
        need(bool(args.previous_view) == bool(args.previous_view_sha256), 'STOCK_GENERATION_PIN')
        parent = None
        state = {}
        if args.head:
            value = child(args.source_root, args.head).read_bytes()
            need(sha(value) == args.head_sha256, 'STOCK_ARCHIVE_HEAD_PIN')
            parent = ref(args.head, value)
            config, state = replay(args.source_root, parent)
        if args.mode == 'append':
            need(args.request and args.request_sha256, 'JOURNAL_REQUEST_REQUIRED')
            need(not args.previous_view, 'JOURNAL_APPEND_VIEW_OPTION')
            root, incoming, contracts = load_request(args.request, args.request_sha256)
            if parent:
                need(config['evaluation_day'] <= incoming['evaluation_day'], 'JOURNAL_DATE_REGRESSION')
                need(_ts(config['calculated_at']) <= _ts(incoming['calculated_at']), 'JOURNAL_CLOCK_REGRESSION')
                need(config.get('price_basis','RAW') == incoming.get('price_basis','RAW') or args.revision_reference,
                     'JOURNAL_REVISION_REFERENCE_REQUIRED')
            if args.revision_reference:
                need(len(args.revision_reference) <= 160, 'JOURNAL_REVISION_REFERENCE_LENGTH')
            for key in ('financial', 'symbols', 'monthends'):
                if incoming.get(key):
                    # The same independently pinned snapshots must exist in the Git source root.
                    pinned(args.source_root, incoming[key])
            patches = changes(contracts, state, incoming, args.revision_reference)
            # Replay is validated before emitting any object or capture pointer.
            apply_frame(state, patches, incoming['evaluation_day'], revision=args.revision_reference)
            for code in state:
                contract_from_state(state[code], incoming.get('price_basis','RAW'))
            if parent and not patches and clock_context(incoming) == config:
                files, head = {}, parent
            else:
                files, head = archive_files(incoming, patches, parent, args.revision_reference)
            files = files.items()
            stats.update(changed_series=len(patches), capture=head)
        else:
            need(parent and not args.request and not args.request_sha256 and not args.revision_reference,
                 'RESTORE_REQUIRES_COMMITTED_CAPTURE')
            previous = None
            if args.previous_view:
                value = args.previous_view.read_bytes()
                need(sha(value) == args.previous_view_sha256, 'STOCK_GENERATION_PIN')
                previous = args.previous_view.parent, ref(args.previous_view.name, value)
            files = generation(Contracts(state, config.get('price_basis','RAW')), config, parent, args.source_root,
                               previous=previous, stats=stats)
        if args.output_dir:
            dest = args.output_dir.resolve()
            need(not any((p/'.git').exists() for p in (dest,*dest.parents)), 'PRIVATE_OUTPUT_OUTSIDE_GIT_REQUIRED')
            stats.update(write_bundle(files,dest))
        else:
            size = count = 0
            for _, value in files:
                need(len(value) <= MAX_BYTES, 'OUTPUT_FILE_LIMIT')
                size += len(value)
                count += 1
            stats.update(files=count,bytes=size)
        stats['elapsed_seconds'] = round(time.perf_counter()-started,3)
        print(json.dumps(stats,sort_keys=True))
        return 0
    except (ValueError, KeyError, TypeError, AttributeError, OSError, EOFError, zlib.error) as error:
        reason = str(error)
        print(json.dumps(dict(failures=1, reason=reason if re.fullmatch('[A-Z0-9_]+',reason) else 'STOCK_INPUT_OR_IO')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
