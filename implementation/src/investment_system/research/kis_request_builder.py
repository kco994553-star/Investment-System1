"""Keyless KIS page intake and deterministic rebuild request freezing.

The page and receipt stay in runner scratch. Only the existing monthly store
and a pinned request/index are written to the private staging directory.
"""
import argparse
import json
from pathlib import Path
import re
import zlib

from ._private_artifacts import json_bytes
from .kis_price_bridge import _day, _ts, normalize_page
from .kis_rebuild import child, load_request, need, pinned, sha
from .kis_stock_journal import ref, replay
from .monthly_price_store import _immutable, ingest, load_manifest, retained_contract, retained_metadata


def checked(path, expected):
    value = path.read_bytes()
    need(sha(value) == expected, 'BUILDER_INPUT_PIN_MISMATCH')
    return value


def scratch(path):
    resolved = path.resolve()
    need(not any((parent/'.git').exists() for parent in (resolved, *resolved.parents)),
         'PRIVATE_OUTPUT_OUTSIDE_GIT_REQUIRED')
    return resolved



def freeze_evidence(request, request_pin, output):
    """Keep the approved non-price evidence paired with the exact KIS query."""
    _, _, contracts = load_request(request, request_pin)
    entries = {}
    keys = ('security_id', 'issuer_id', 'currency', 'currency_reference', 'splits',
            'confirmed_ranges', 'held_ranges', 'session_scope', 'price_scope_status')
    for code in contracts:
        contract = contracts[code]
        query = contract['source_query']
        evidence = {key: contract[key] for key in keys}
        evidence.update(contract['identity'])
        entries[code] = dict(symbol=query['SYMB'], exchange=query['EXCD'], evidence=evidence)
    value = json_bytes(dict(schema='kis-intake-evidence/1', publication_scope='OWNER_PRIVATE_ONLY',
                            baseline_request_sha256=request_pin, entries=entries))
    _immutable(output, value)
    return dict(series=len(entries), evidence_sha256=sha(value))


def page_evidence(payload, code, receipt):
    if payload.get('schema') != 'kis-intake-evidence/1':
        need(code is None, 'SCOPE_EVIDENCE_REQUIRED')
        return payload
    need(payload.get('publication_scope') == 'OWNER_PRIVATE_ONLY', 'PRIVATE_EVIDENCE_REQUIRED')
    binding = payload['entries'].get(code)
    query = json.loads(receipt)['request']
    need(binding is not None and binding['symbol'] == query['SYMB'] and
         binding['exchange'] == query['EXCD'], 'PAGE_EVIDENCE_QUERY_MISMATCH')
    return binding['evidence']

def ingest_page(store, body, receipt_bytes, receipt_pin, evidence, review=None, daily_as_of=None):
    need(sha(receipt_bytes) == receipt_pin, 'RECEIPT_PIN')
    receipt = json.loads(receipt_bytes)
    contract = normalize_page(body, receipt=receipt, request=receipt['request'], evidence=evidence,
                              daily_as_of=daily_as_of)
    details = {}
    if daily_as_of is not None:
        policy = contract['daily_finalization']
        reasons = {}
        for item in policy['deferred']:
            reason = item['reason']
            reasons[reason] = reasons.get(reason, 0) + 1
        details = dict(deferred_reasons=reasons, target_present=contract['price_basis_date'] == policy['target'],
                       deferred_only=bool(reasons) and not contract['raw_bars'] and not contract['rejected_rows'])
        if details['deferred_only']:
            return dict(details, new_rows=0, revised_rows=0, unchanged_rows=0, appended_bytes=0)
    need(bool(contract['raw_bars']), 'NO_ADMISSIBLE_PRICE_ROWS')
    contract_bytes = json_bytes(contract)
    result = ingest(store, contract_bytes=contract_bytes, body=body, receipt_bytes=receipt_bytes,
                  expected_contract_sha256=sha(contract_bytes), expected_receipt_sha256=receipt_pin,
                  revision_reference=review)
    return dict(result, **details)


def freeze(root, *, store_path, evaluation_day, calculated_at, financial, symbols,
           monthends=None, expected_series, price_basis='RAW'):
    day = _day(evaluation_day)
    clock = _ts(calculated_at)
    need(day <= clock.date().isoformat(), 'FUTURE_EVALUATION')
    need(expected_series > 0, 'EXPECTED_SERIES_REQUIRED')
    financial_payload = pinned(root, financial)
    need(_ts(financial_payload['as_of']) <= clock, 'FINANCIAL_AFTER_CALCULATION')
    links = pinned(root, symbols)
    need(len(links) == expected_series, 'SYMBOL_SCOPE_COUNT_MISMATCH')
    by_query = {(v['symb'], v['excd']): code for code, v in links.items()}
    need(len(by_query) == len(links), 'SYMBOL_LOOKUP_DUPLICATE_QUERY')
    if monthends is not None:
        pinned(root, monthends)
    store = child(root, store_path)
    by_code = {}
    count = 0
    for pointer in sorted((store/'series').glob('*/latest.json')):
        series_id = pointer.parent.name
        need(re.fullmatch('[0-9a-f]{64}', series_id) is not None, 'MONTHLY_SERIES_ID')
        manifest = load_manifest(store, series_id)
        meta = retained_metadata(store, manifest)
        contract = retained_contract(store, manifest)
        query = contract['source_query']
        code = by_query.get((query['SYMB'], query['EXCD']))
        need(code is not None and code not in by_code, 'MONTHLY_SERIES_LOOKUP')
        need(query['MODP'] == '0' and contract['basis'] == 'RAW', 'RAW_DAILY_PRIVATE_REQUIRED')
        need(_ts(contract['collected_at']) <= clock, 'SOURCE_AFTER_CALCULATION')
        need(bool(contract['raw_bars']) and contract['price_basis_date'] <= day, 'JOURNAL_FUTURE_OR_EMPTY_ROW')
        by_code[code] = dict(code=code, symbol=query['SYMB'], series_id=series_id,
                            store_manifest_sha256=manifest['manifest_sha256'],
                            source_contract_sha256=meta['input_contract_sha256'])
        count += len(contract['raw_bars'])
    need(set(by_code) == set(links), 'MONTHLY_SERIES_SCOPE_MISMATCH')
    index = json_bytes(dict(files=[by_code[code] for code in sorted(by_code)]))
    index_pin = sha(index)
    name = f'indexes/{index_pin}.json'
    request = dict(schema='kis-offline-rebuild/1', publication_scope='OWNER_PRIVATE_ONLY',
                   evaluation_day=day, calculated_at=calculated_at, store=store_path,
                   series_id_prefix='OWNER_KIS:', price_basis=price_basis, financial=financial, symbols=symbols,
                   series_index=dict(path=name, sha256=index_pin))
    if monthends is not None:
        request['monthends'] = monthends
    value = json_bytes(request)
    request_path = child(root, 'request.json')
    if request_path.exists():
        need(request_path.read_bytes() == value, 'IMMUTABLE_FILE_MISMATCH')
    _immutable(child(root, name), index)
    _immutable(request_path, value)
    return dict(series=len(by_code), rows=count, request_path='request.json', request_sha256=sha(value))



def plan_coverage(source_root, head_path, head_sha256, output):
    """Build the collector's private plan input from committed usable RAW rows."""
    blob = checked(child(source_root, head_path), head_sha256)
    _, state = replay(source_root, ref(head_path, blob))
    coverage = {code: dict(earliest=min(rows).replace('-', ''), latest=max(rows).replace('-', ''))
                for code, item in state.items() if (rows := item['rows'])}
    value = json_bytes(coverage)
    _immutable(output, value)
    return dict(series=len(coverage), coverage_sha256=sha(value))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    page = modes.add_parser('ingest-page')
    for name in ('store', 'body', 'receipt', 'evidence'):
        page.add_argument('--'+name, type=Path, required=True)
    page.add_argument('--receipt-sha256', required=True)
    page.add_argument('--evidence-sha256', required=True)
    page.add_argument('--revision-reference')
    page.add_argument('--daily-as-of')
    page.add_argument('--code', help='exact input code for a pinned scope evidence file')
    evidence = modes.add_parser('evidence')
    evidence.add_argument('--baseline-request', type=Path, required=True)
    evidence.add_argument('--baseline-request-sha256', required=True)
    evidence.add_argument('--output', type=Path, required=True)
    coverage = modes.add_parser('coverage')
    coverage.add_argument('--source-root', type=Path, required=True)
    coverage.add_argument('--head', required=True)
    coverage.add_argument('--head-sha256', required=True)
    coverage.add_argument('--output', type=Path, required=True)
    request = modes.add_parser('freeze')
    request.add_argument('--root', type=Path, required=True)
    request.add_argument('--store', default='store')
    request.add_argument('--evaluation-day', required=True)
    request.add_argument('--calculated-at', required=True)
    request.add_argument('--expected-series', type=int, required=True)
    request.add_argument('--price-basis', choices=('RAW', 'SPLIT_ADJUSTED'), default='RAW')
    for name in ('financial', 'symbols', 'monthends'):
        request.add_argument('--'+name, required=name != 'monthends')
        request.add_argument('--'+name+'-sha256', required=name != 'monthends')
    args = parser.parse_args(argv)
    try:
        if args.mode == 'ingest-page':
            evidence = json.loads(checked(args.evidence, args.evidence_sha256))
            receipt = checked(args.receipt, args.receipt_sha256)
            result = ingest_page(scratch(args.store), args.body.read_bytes(), receipt,
                                 args.receipt_sha256, page_evidence(evidence, args.code, receipt),
                                 args.revision_reference, args.daily_as_of)
            out = {key: result[key] for key in ('new_rows', 'revised_rows', 'unchanged_rows', 'appended_bytes')}
            if args.daily_as_of is not None:
                out.update({key: result[key] for key in ('deferred_reasons', 'deferred_only', 'target_present')})
        elif args.mode == 'evidence':
            out = freeze_evidence(args.baseline_request, args.baseline_request_sha256, scratch(args.output))
        elif args.mode == 'coverage':
            out = plan_coverage(args.source_root, args.head, args.head_sha256, scratch(args.output))
        else:
            need(bool(args.monthends) == bool(args.monthends_sha256), 'MONTHEND_PIN_REQUIRED')
            monthends = (dict(path=args.monthends, sha256=args.monthends_sha256) if args.monthends else None)
            out = freeze(scratch(args.root), store_path=args.store, evaluation_day=args.evaluation_day,
                         calculated_at=args.calculated_at, expected_series=args.expected_series,
                         price_basis=args.price_basis, financial=dict(path=args.financial, sha256=args.financial_sha256),
                         symbols=dict(path=args.symbols, sha256=args.symbols_sha256), monthends=monthends)
        print(json.dumps(out, sort_keys=True))
        return 0
    except (ValueError, KeyError, TypeError, AttributeError, OSError, EOFError, zlib.error) as error:
        reason = str(error)
        print(json.dumps(dict(failures=1, reason=reason if re.fullmatch('[A-Z0-9_]+', reason) else 'KIS_BUILDER_INPUT_OR_IO')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
