"""#502 source-native receipt -> #499 price contract. Offline, no ratio engine."""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

from investment_system.providers.iex_values import MAX_PRICE_E4, session_ns, valid_symbol
from investment_system.research.financial_v_bridge import _capture, _quote_time_faults

VERSION = 'financial-v-iex-adapter/1'
STATES = ('PRICE', 'NO_TRADE', 'NOT_IN_FILE', 'PRICE_INVALID')
SOURCE = 'IEX_HIST TOPS 1.6 last regular-session trade'


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _fail(reason):
    raise ValueError(reason)


def _hash(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _ns(stamp):
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d{9})Z', str(stamp))
    if not match:
        raise ValueError('PRICE_TIMESTAMP_NS_MISMATCH')
    dt = datetime.fromisoformat(match[1]).replace(tzinfo=timezone.utc)
    return int(dt.timestamp()) * 10**9 + int(match[2])


def adapt(manifest_bytes, derived_bytes, request_bytes, basis_bytes, *, valuation_date, input_vintage):
    """Integrity errors reject the batch; per-row absence/proof gaps remain null.

    Whole-file integrity is Main's pinned manifest/reassembly attestation. This
    function hashes the small derived body, not a multi-GB original file.
    Basis is separately reviewed retained evidence, never inferred from ticker.
    """
    m, d, request, basis = (json.loads(x) for x in (manifest_bytes, derived_bytes, request_bytes, basis_bytes))
    if (m.get('schema_version') != 'iex-day-preserve-once/2' or m.get('state') != 'COMPLETE'
            or d.get('schema_version') != 'iex-day-financial11-last-trade/1'
            or request.get('schema') != 'financial-v-pending-price-requests/1'):
        _fail('HANDOFF_SCHEMA_OR_COMPLETION_INVALID')
    metadata = m.get('derived', {})
    if metadata.get('sha256') != _sha(derived_bytes) or metadata.get('bytes') != len(derived_bytes):
        _fail('DERIVED_HASH_MISMATCH')
    if m.get('day') != valuation_date or d.get('basis_date') != valuation_date:
        _fail('DATE_MISMATCH')
    if (d.get('manifest') != m.get('manifest_name') or d.get('release_tag') != m.get('release_tag')
            or metadata.get('schema_version') != d['schema_version']):
        _fail('MANIFEST_LINK_MISMATCH')
    received, original = m.get('received', {}), d.get('original', {})
    if not _hash(original.get('sha256')) or not re.fullmatch('[0-9a-f]{32}', str(original.get('md5'))):
        _fail('ORIGINAL_RECEIPT_MISMATCH')
    if any(original.get(k) != received.get(k) for k in ('sha256', 'md5', 'bytes')) or type(original.get('bytes')) is not int or original['bytes'] <= 0:
        _fail('ORIGINAL_RECEIPT_MISMATCH')
    complete = m.get('completeness', {})
    reassembly = m.get('reassembly', {})
    if (any(complete.get(k) is not True for k in ('size_match','md5_match','gzip_exit_0','parser_exit_0','curl_exit_0','all_chunks_verified','reassembly_streaming_verified'))
            or any(reassembly.get(k) is not True for k in ('sha256_match','md5_match','gzip_test_ok'))
            or reassembly.get('bytes') != original['bytes'] or reassembly.get('mode') != 'STREAMING_NO_FILE'
            or received.get('exit_codes') != [0, 0, 0]):
        _fail('ORIGINAL_REASSEMBLY_UNVERIFIED')
    chunks = m.get('chunks', [])
    if (not chunks or len({c['name'] for c in chunks}) != len(chunks)
            or any(type(c.get('size')) is not int or c['size'] <= 0 or not _hash(c.get('sha256')) for c in chunks)
            or sum(c['size'] for c in chunks) != original['bytes'] or reassembly.get('chunks') != len(chunks)):
        _fail('ORIGINAL_CHUNK_RECEIPT_INVALID')
    try:
        acquired = _capture(received['completed_at_utc'])
        captured = _capture(d['acquired_at_utc'])
    except (KeyError, ValueError):
        _fail('ACQUISITION_COMPLETED_REQUIRED')
    vintage = _capture(input_vintage)
    if acquired > vintage:
        _fail('CAPTURE_AFTER_VINTAGE')
    generated = _capture(d.get('generated_at_utc'))
    if (acquired != captured or not _capture(received.get('started_at_utc')) <= acquired
            <= _capture(reassembly.get('verified_at_utc')) <= generated <= _capture(m.get('written_at_utc')) <= vintage
            or generated > vintage or metadata.get('generated_at_utc') != d['generated_at_utc']):
        _fail('HANDOFF_CLOCK_MISMATCH')
    if (d.get('basis_kind') != 'IEX_LAST_REGULAR_SESSION_TRADE' or d.get('adjustment_basis') != 'AS_TRADED'
            or d.get('currency') != 'USD' or d.get('unit') != 'USD/share' or d.get('source') != SOURCE):
        _fail('PRICE_BASIS_CONTRACT_MISMATCH')
    window = list(session_ns(valuation_date.replace('-', '')))
    if d.get('session_window_ns') != window or m.get('session_window_ns') != window:
        _fail('SESSION_WINDOW_MISMATCH')
    if acquired.timestamp() * 10**9 < window[1]:
        _fail('CAPTURE_BEFORE_SESSION_COMPLETE')
    parser = m.get('parser', {})
    if (not _hash(parser.get('source_sha256')) or parser['source_sha256'] != d.get('parser_source_sha256')
            or parser.get('git_commit') != d.get('parser_git_commit')):
        _fail('PARSER_RECEIPT_MISMATCH')
    requested = request['records']; rows = d['rows']
    codes = [r['code'] for r in requested]
    if (len(set(codes)) != len(codes) or len({r['row_index'] for r in requested}) != len(requested)
            or len(rows) != len(codes) or {r['code'] for r in rows} != set(codes)
            or len({r['code'] for r in rows}) != len(rows)):
        _fail('REQUEST_MEMBERSHIP_MISMATCH')
    if (any(r.get('valuation_date') != valuation_date for r in requested)
            or d.get('input', {}).get('row_indexes') != [r['row_index'] for r in requested]):
        _fail('REQUEST_DATE_OR_INDEX_MISMATCH')
    if any(m.get('input', {}).get(k) != d.get('input', {}).get(k) or d.get('input', {}).get(k) is None
           for k in ('commit', 'path', 'file_sha256', 'row_indexes')):
        _fail('INPUT_RECEIPT_MISMATCH')
    counts = {s: sum(r.get('state') == s for r in rows) for s in STATES}
    if (sum(counts.values()) != len(rows) or counts != d.get('states') or counts != metadata.get('states')
            or any(complete.get(k) != len(rows) for k in ('derived_rows','derived_rows_expected'))
            or metadata.get('rows') != len(rows)):
        _fail('SOURCE_COUNT_MISMATCH')
    wanted = {r['code']: r for r in requested}
    output, trades, diagnostics = {}, {}, []
    for index, row in enumerate(rows):
        code = row['code']; req = wanted[code]; metric = req['primary_metric']
        if metric not in {'earnings_yield','book_yield','tangible_book_yield'}:
            _fail('REQUEST_METRIC_INVALID')
        if (row.get('basis_date') != valuation_date or row.get('row_index') != req['row_index']
                or row.get('source') != SOURCE or row.get('parser_source_sha256') != parser['source_sha256']):
            _fail('ROW_PROVENANCE_MISMATCH')
        reasons = []
        price = None
        if row['state'] == 'PRICE':
            try:
                raw = row.get('price')
                if not isinstance(raw, str) or not re.fullmatch(r'\d+\.\d{4}', raw):
                    raise ValueError
                dec = Decimal(raw)
                if not 0 < dec * 10000 < MAX_PRICE_E4:
                    raise ValueError
                price = float(dec)
                if Decimal(str(price)) != dec:
                    raise ValueError
            except (ValueError, InvalidOperation, OverflowError):
                reasons.append('PRICE_INVALID_VALUE'); price = None
            try:
                if type(row.get('last_trade_ns')) is not int or _ns(row.get('last_trade_utc')) != row['last_trade_ns']:
                    raise ValueError
                if not window[0] <= row['last_trade_ns'] < window[1]:
                    raise ValueError
            except ValueError:
                reasons.append('PRICE_TIMESTAMP_NS_MISMATCH')
            if row.get('parser_status') != 'ROUND' or row.get('reason') != 'REGULAR_SESSION_ROUND_LOT_LAST_TRADE':
                reasons.append('PRICE_TRADE_VALIDATION_UNCONFIRMED')
        else:
            reasons.append(row.get('reason') or row['state'])
            if any(row.get(k) is not None for k in ('price','last_trade_ns','last_trade_utc')):
                _fail('NONPRICE_ROW_HAS_PRICE')
        proof = (basis.get('records', {}).get(code) or {}).get(metric)
        if proof is None:
            reasons.append('PRICE_BASIS_UNCONFIRMED')
        else:
            if (not valid_symbol(row.get('iex_symbol')) or proof.get('code') != code or proof.get('cik') != req.get('cik')
                    or proof.get('iex_symbol') != row.get('iex_symbol') or proof.get('identity_status') != 'DOCUMENT_LINKED'):
                reasons.append('PRICE_IDENTITY_UNCONFIRMED')
            if proof.get('currency') != d['currency']:
                reasons.append('PRICE_CURRENCY_MISMATCH')
            if not req.get('required_share_basis') or proof.get('share_basis') != req['required_share_basis']:
                reasons.append('PRICE_SHARE_BASIS_MISMATCH')
            try:
                dates_ok = date.fromisoformat(proof['valid_from']) <= date.fromisoformat(valuation_date) <= date.fromisoformat(proof['valid_to'])
            except (KeyError, TypeError, ValueError):
                dates_ok = False
            if proof.get('action_status') != 'MATCHED_TO_NUMERATOR' or not dates_ok:
                reasons.append('PRICE_ACTIONS_UNCONFIRMED')
            refs = proof.get('evidence_refs', [])
            if not refs or any(not _hash(e.get('sha256')) or not e.get('locator') for e in refs):
                reasons.append('PRICE_BASIS_EVIDENCE_REQUIRED')
        quote = None
        if not reasons:
            quote = dict(code=code,cik=req['cik'],value=price,date=valuation_date,currency=d['currency'],unit=d['unit'],
                         traded_at=row['last_trade_utc'],acquired_at=d['acquired_at_utc'],price_type='IEX_LAST_REGULAR_TRADE',
                         price_basis='RAW',trade_validation='ELIGIBLE',share_basis=proof['share_basis'])
            reasons.extend(_quote_time_faults(quote, date.fromisoformat(valuation_date), vintage))
        if reasons:
            quote = None
        if quote is not None:
            trades[code] = {**quote, 'original_price_text': row['price'], 'original_trade_ns': row['last_trade_ns'],
                            'source_derived_sha256': _sha(derived_bytes), 'source_row_pointer': f'/rows/{index}',
                            'original_sha256': original['sha256']}
        output[code] = {metric: quote}
        diagnostics.append(dict(code=code,metric=metric,source_state=row['state'],source_reason=row['reason'],
                                price_present=price is not None,price_input_ready=quote is not None,reasons=sorted(set(reasons))))
    evidence = {'schema_version':'financial-v-normalized-trades/1','records':trades}
    trade_sha = _sha(encode(evidence)); basis_sha = _sha(basis_bytes)
    for code, metrics in output.items():
        for metric, q in metrics.items():
            if q is not None:
                escaped = code.replace('~','~0').replace('/','~1')
                q['source'] = {'sha256':trade_sha,'json_pointer':f'/records/{escaped}'}
                q['basis_source'] = {'sha256':basis_sha,'json_pointer':f'/records/{escaped}/{metric}'}
    return dict(schema_version=VERSION,valuation_date=valuation_date,acquired_at=d['acquired_at_utc'],generated_at=d['generated_at_utc'],
                manifest_sha256=_sha(manifest_bytes),derived_sha256=_sha(derived_bytes),requests_sha256=_sha(request_bytes),
                original_integrity='PINNED_MANIFEST_REASSEMBLY_ATTESTATION_NOT_LOCAL_RAW_REHASH',
                prices={'schema_version':'financial-v-price-input/1','valuation_date':valuation_date,'records':output},
                trade_evidence=evidence,trade_evidence_sha256=trade_sha,basis_sha256=basis_sha,rows=diagnostics,
                summary={'requested_codes':len(rows),'source_states':counts,'price_available_codes':sum(x['price_present'] for x in diagnostics),
                         'price_ready_codes':sum(x['price_input_ready'] for x in diagnostics)})
