"""Publish only allowlisted reported SEC share facts and filing metadata.

Collection is delegated to Codex2's SEC client. No scoring, price fetching,
market-cap calculation, model input selection or share-class correction occurs.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.markets.us import US_LISTINGS
from investment_system.providers.sec_collection import SecCollectionError, MAX_BODY_BYTES

FILENAME = 'sec-public-inputs.json'
MAX_BYTES = 2 * 1024 * 1024
CONCEPTS = {('dei', 'EntityCommonStockSharesOutstanding'), ('us-gaap', 'CommonStockSharesOutstanding'),
            ('ifrs-full', 'NumberOfSharesOutstanding')}
FORMS = {'10-K', '10-Q', '10-K/A', '10-Q/A', '10-KT', '10-QT', '10-KT/A', '10-QT/A', '20-F', '20-F/A', '40-F', '40-F/A', '6-K', '6-K/A', '8-K', '8-K/A'}
FACT_FIELDS = {'namespace', 'concept', 'unit', 'end', 'val', 'accn', 'form', 'filed'}
FACT_OPTIONAL = {'start', 'fy', 'fp', 'frame'}


NORMALIZATION_CODES = frozenset({
    'SEC_SHARE_CONCEPT_MISSING', 'SEC_SHARE_UNIT_MISMATCH', 'SEC_SHARE_SCHEMA_INVALID',
    'SEC_SHARE_VALUE_INVALID', 'SEC_FACT_DATE_INVALID', 'SEC_FACT_AFTER_ACQUISITION',
    'SEC_FACT_ACCESSION_INVALID', 'SEC_FACT_FORM_UNSUPPORTED', 'SEC_FACT_PERIOD_METADATA_INVALID',
    'SEC_SUBMISSIONS_SCHEMA_INVALID', 'SEC_FILING_DATE_INVALID', 'SEC_FILING_TIMESTAMP_INVALID',
    'SEC_FILING_AFTER_ACQUISITION', 'SEC_FILING_ACCESSION_INVALID', 'SEC_FILING_REPORT_DATE_INVALID',
    'SEC_ACQUISITION_TIMESTAMP_INVALID', 'SEC_SOURCE_METADATA_INVALID', 'SEC_NO_ELIGIBLE_SHARE_FACTS',
})


EXCLUSION_CODES = frozenset({'FORM_NOT_ALLOWED', 'UNIT_MISMATCH', 'DATE_INVALID',
    'DATE_AFTER_ACQUISITION', 'VALUE_INVALID', 'FACT_SCHEMA_INVALID', 'ACCESSION_INVALID',
    'PERIOD_METADATA_INVALID', 'CLASS_SPLIT', 'FACT_CONFLICT', 'UNKNOWN_DIMENSION',
    'FILING_DATE_INVALID', 'FILING_TIMESTAMP_INVALID', 'FILING_ACCESSION_INVALID',
    'FILING_REPORT_DATE_INVALID', 'FILING_AFTER_ACQUISITION', 'FILING_SCHEMA_INVALID'})
FACT_REASON_MAP = {
    'SEC_FACT_FORM_UNSUPPORTED': 'FORM_NOT_ALLOWED', 'SEC_SHARE_UNIT_MISMATCH': 'UNIT_MISMATCH',
    'SEC_FACT_DATE_INVALID': 'DATE_INVALID', 'SEC_FACT_AFTER_ACQUISITION': 'DATE_AFTER_ACQUISITION',
    'SEC_SHARE_VALUE_INVALID': 'VALUE_INVALID', 'SEC_FACT_ACCESSION_INVALID': 'ACCESSION_INVALID',
    'SEC_FACT_PERIOD_METADATA_INVALID': 'PERIOD_METADATA_INVALID',
    'SEC_FILING_DATE_INVALID': 'FILING_DATE_INVALID', 'SEC_FILING_TIMESTAMP_INVALID': 'FILING_TIMESTAMP_INVALID',
    'SEC_FILING_ACCESSION_INVALID': 'FILING_ACCESSION_INVALID',
    'SEC_FILING_REPORT_DATE_INVALID': 'FILING_REPORT_DATE_INVALID',
    'SEC_FILING_AFTER_ACQUISITION': 'FILING_AFTER_ACQUISITION',
}


class SecNormalizationError(ValueError):
    """Only reviewed fixed codes cross the normalization/logging boundary."""
    def __init__(self, code):
        super().__init__(code if code in NORMALIZATION_CODES else 'SEC_PUBLIC_INPUT_INVALID')
        self.stage = 'normalize'
        self.excluded_fact_counts = {}
        self.share_class_basis = 'UNCONFIRMED'
        self.share_class_notice = None


def invalid(code='SEC_PUBLIC_INPUT_INVALID'):
    if code in NORMALIZATION_CODES:
        raise SecNormalizationError(code) from None
    raise ValueError('SEC_PUBLIC_INPUT_INVALID') from None


def day(value, code='SEC_PUBLIC_INPUT_INVALID'):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value): invalid(code)
    try: date.fromisoformat(value)
    except ValueError: invalid(code)
    return value


def timestamp(value, code='SEC_PUBLIC_INPUT_INVALID'):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value): invalid(code)
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.utcoffset() is None or result > datetime.now(timezone.utc): invalid(code)
        return result
    except ValueError: invalid(code)


def accession(value, code='SEC_PUBLIC_INPUT_INVALID'):
    if not isinstance(value, str) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', value): invalid(code)


def source_url(kind, cik):
    return ('https://data.sec.gov/api/xbrl/companyfacts/CIK' if kind == 'companyfacts' else 'https://data.sec.gov/submissions/CIK') + cik + '.json'


FIXED_COLLECTION_CODES = frozenset({
    'SEC_USER_AGENT_INVALID', 'SEC_URL_NOT_ALLOWED', 'SEC_CONFIG_INVALID',
    'SEC_REDIRECT_REJECTED', 'SEC_RESPONSE_TOO_LARGE', 'SEC_JSON_INVALID',
    'SEC_CIK_MISMATCH', 'SEC_CLOCK_INVALID', 'SEC_SLEEP_FAILED',
    'SEC_RETRY_AFTER_EXCEEDS_BUDGET', 'SEC_TRANSPORT_RETRIES_EXHAUSTED',
    'SEC_TRANSPORT_FAILED', 'SEC_RESPONSE_INVALID', 'SEC_RESPONSE_URL_MISMATCH',
    'SEC_HTTP_RETRIES_EXHAUSTED', 'SEC_ISSUER_NOT_ALLOWED',
    'SEC_COLLECTION_FAILED', 'SEC_PUBLIC_INPUT_INVALID',
    'SEC_MODULE_NOT_MERGED', 'SEC_USER_AGENT_MISSING',
}) | NORMALIZATION_CODES


def fixed_code(value):
    return type(value) is str and (value in FIXED_COLLECTION_CODES or re.fullmatch(r'SEC_HTTP_[45][0-9]{2}', value) is not None)


class CollectionFailure(ValueError):
    def __init__(self, code, diagnostics, failed_companies=17, exclusions=()):
        super().__init__(code)
        self.diagnostics = diagnostics
        self.failed_companies = failed_companies
        self.exclusions = list(exclusions)


def _require_share_fact(fact, as_of):
    if not isinstance(fact, dict) or not FACT_FIELDS <= set(fact) or set(fact) - FACT_FIELDS - FACT_OPTIONAL:
        invalid('SEC_SHARE_SCHEMA_INVALID')
    if (fact['namespace'], fact['concept']) not in CONCEPTS: invalid('SEC_SHARE_CONCEPT_MISSING')
    if fact['unit'] != 'shares': invalid('SEC_SHARE_UNIT_MISMATCH')
    if fact['form'] not in FORMS: invalid('SEC_FACT_FORM_UNSUPPORTED')
    if type(fact['val']) not in (int, float) or not math.isfinite(fact['val']) or not 0 < fact['val'] <= 2**53 - 1:
        invalid('SEC_SHARE_VALUE_INVALID')
    if day(fact['end'], 'SEC_FACT_DATE_INVALID') > as_of or day(fact['filed'], 'SEC_FACT_DATE_INVALID') > as_of:
        invalid('SEC_FACT_AFTER_ACQUISITION')
    accession(fact['accn'], 'SEC_FACT_ACCESSION_INVALID')
    if 'start' in fact and day(fact['start'], 'SEC_FACT_DATE_INVALID') > fact['end']: invalid('SEC_FACT_DATE_INVALID')
    if 'fy' in fact and (type(fact['fy']) is not int or not 1900 <= fact['fy'] <= 9999): invalid('SEC_FACT_PERIOD_METADATA_INVALID')
    if 'fp' in fact and fact['fp'] not in {'FY', 'Q1', 'Q2', 'Q3', 'Q4'}: invalid('SEC_FACT_PERIOD_METADATA_INVALID')
    if 'frame' in fact and (not isinstance(fact['frame'], str) or not re.fullmatch(r'CY\d{4}(?:Q[1-4])?I?', fact['frame'])):
        invalid('SEC_FACT_PERIOD_METADATA_INVALID')


def _require_filing(filing, acquired, as_of):
    if not isinstance(filing, dict) or set(filing) != {'accession', 'form', 'filed', 'report_date', 'accepted_at'}:
        invalid('SEC_SUBMISSIONS_SCHEMA_INVALID')
    accession(filing['accession'], 'SEC_FILING_ACCESSION_INVALID')
    if filing['form'] not in FORMS: invalid('SEC_SUBMISSIONS_SCHEMA_INVALID')
    if day(filing['filed'], 'SEC_FILING_DATE_INVALID') > as_of: invalid('SEC_FILING_AFTER_ACQUISITION')
    if timestamp(filing['accepted_at'], 'SEC_FILING_TIMESTAMP_INVALID') > acquired: invalid('SEC_FILING_AFTER_ACQUISITION')
    if filing['report_date'] is not None and day(filing['report_date'], 'SEC_FILING_REPORT_DATE_INVALID') > as_of:
        invalid('SEC_FILING_AFTER_ACQUISITION')


def _require_exclusions(row):
    counts = row['excluded_fact_counts']
    if not isinstance(counts, dict) or not set(counts) <= EXCLUSION_CODES: invalid()
    if any(type(v) is not int or not 0 < v <= 100000 for v in counts.values()): invalid()
    if row['share_class_basis'] != 'UNCONFIRMED': invalid()
    if row['share_class_notice'] != ('SHARE_CLASS_BASIS' if counts.get('CLASS_SPLIT', 0) else None): invalid()


def _require_reported_row(row):
    acquired = timestamp(row['acquired_at'], 'SEC_ACQUISITION_TIMESTAMP_INVALID')
    as_of = acquired.date().isoformat()
    if not isinstance(row['sources'], dict) or set(row['sources']) != {'companyfacts', 'submissions'}:
        invalid('SEC_SOURCE_METADATA_INVALID')
    for kind, source in row['sources'].items():
        if not isinstance(source, dict) or set(source) != {'url', 'sha256'} or source['url'] != source_url(kind, row['cik']) \
                or not isinstance(source['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', source['sha256']):
            invalid('SEC_SOURCE_METADATA_INVALID')
    if not isinstance(row['reported_shares'], list) or len(row['reported_shares']) > 10000:
        invalid('SEC_SHARE_SCHEMA_INVALID')
    fact_keys = {}
    for fact in row['reported_shares']:
        _require_share_fact(fact, as_of)
        key = tuple(fact[k] for k in ('namespace', 'concept', 'unit', 'end', 'accn', 'form', 'filed'))
        if key in fact_keys and fact_keys[key] != fact['val']: invalid()
        fact_keys[key] = fact['val']
    if not isinstance(row['filings'], list) or len(row['filings']) > 10000: invalid('SEC_SUBMISSIONS_SCHEMA_INVALID')
    for filing in row['filings']: _require_filing(filing, acquired, as_of)


def _require_public_inputs(payload):
    if not isinstance(payload, dict) or set(payload) != {'schema', 'scope', 'companies'} \
            or payload['schema'] not in ('public-sec-reported-inputs/1', 'public-sec-reported-inputs/2', 'public-sec-reported-inputs/3') or payload['scope'] != 'US_TARGET17_REPORTED_SEC_ONLY': invalid()
    companies = payload['companies']; v3 = payload['schema'].endswith('/3'); partial = payload['schema'].endswith('/2') or v3
    if not isinstance(companies, list) or len(companies) != len(US_LISTINGS): invalid()
    seen = []
    extra = {'excluded_fact_counts', 'share_class_basis', 'share_class_notice'} if v3 else set()
    base_fields = {'company_id', 'cik', 'acquired_at', 'sources', 'reported_shares', 'filings'}
    unavailable_fields = {'company_id', 'cik', 'status', 'reason_codes', 'failure_stage', 'company_index', 'http_status'}
    for index, row in enumerate(companies, 1):
        if not isinstance(row, dict): invalid()
        company = row.get('company_id')
        if not isinstance(company, str) or company not in US_LISTINGS or row.get('cik') != US_LISTINGS[company]['cik']: invalid()
        seen.append(company)
        if v3: _require_exclusions(row)
        if partial and row.get('status') == 'NOT_AVAILABLE':
            if set(row) != unavailable_fields | extra or row['company_index'] != index or type(row['company_index']) is not int: invalid()
            if row['failure_stage'] not in ('fetch', 'parse', 'normalize'): invalid()
            if not isinstance(row['reason_codes'], list) or len(row['reason_codes']) != 1 or not fixed_code(row['reason_codes'][0]): invalid()
            if row['http_status'] is not None and (type(row['http_status']) is not int or not 400 <= row['http_status'] <= 599): invalid()
            continue
        if set(row) != base_fields | ({'status'} if partial else set()) | extra or partial and row.get('status') != 'LIVE': invalid()
        _require_reported_row(row)
        if v3 and not row['reported_shares']: invalid()
    if seen != sorted(US_LISTINGS): invalid()
    if len(json.dumps(payload, ensure_ascii=True, allow_nan=False).encode()) > MAX_BYTES: invalid()
    return payload


def require_public_inputs(payload):
    try: return _require_public_inputs(payload)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError): invalid()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result: invalid()
        result[key] = value
    return result


def parse(body, cik):
    if not isinstance(body, bytes) or len(body) > MAX_BODY_BYTES: invalid()
    try:
        value = json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=unique,
                           parse_constant=lambda _: invalid())
        raw_cik = value['cik']
        if type(raw_cik) not in (int, str) or not re.fullmatch(r'\d{1,10}', str(raw_cik)) or str(raw_cik).zfill(10) != cik: invalid()
        return value
    except (KeyError, ValueError, TypeError, UnicodeError, RecursionError): invalid()


def _bump(counts, code, amount=1):
    counts[code] = counts.get(code, 0) + amount


def _share_rows(facts, acquired_at):
    acquired = timestamp(acquired_at, 'SEC_ACQUISITION_TIMESTAMP_INVALID')
    counts = {}; clean = []; found_concept = False; found_share_unit = False
    root = facts.get('facts')
    if not isinstance(root, dict): invalid('SEC_SHARE_SCHEMA_INVALID')
    for namespace, concept in sorted(CONCEPTS):
        ns = root.get(namespace, {})
        if not isinstance(ns, dict):
            _bump(counts, 'FACT_SCHEMA_INVALID'); continue
        if concept not in ns: continue
        found_concept = True; obj = ns[concept]
        if not isinstance(obj, dict) or not isinstance(obj.get('units'), dict):
            _bump(counts, 'FACT_SCHEMA_INVALID'); continue
        for unit, entries in obj['units'].items():
            if unit == 'shares': found_share_unit = True
            if not isinstance(entries, list) or len(entries) > 10000:
                _bump(counts, 'FACT_SCHEMA_INVALID'); continue
            if unit != 'shares':
                if entries: _bump(counts, 'UNIT_MISMATCH', len(entries))
                continue
            for entry in entries:
                try:
                    required = ('end', 'val', 'accn', 'form', 'filed')
                    if not isinstance(entry, dict) or not set(required) <= set(entry): invalid('SEC_SHARE_SCHEMA_INVALID')
                    fact = {'namespace': namespace, 'concept': concept, 'unit': 'shares',
                            **{k: entry[k] for k in required},
                            **{k: entry[k] for k in FACT_OPTIONAL if k in entry and entry[k] is not None}}
                    _require_share_fact(fact, acquired.date().isoformat())
                    # Explicit class dimensions are excluded, never added together. Numerical conflict alone is not proof.
                    if any(k in entry for k in ('dimensions', 'segment', 'context')):
                        dimensions = entry.get('dimensions')
                        if isinstance(dimensions, dict) and dimensions and all(
                            k == 'us-gaap:StatementClassOfStockAxis' and isinstance(v, str)
                            and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*:[A-Za-z_][A-Za-z0-9_.-]*', v)
                            for k, v in dimensions.items()):
                            _bump(counts, 'CLASS_SPLIT')
                        else: _bump(counts, 'UNKNOWN_DIMENSION')
                        continue
                    clean.append(fact)
                except (ValueError, TypeError, KeyError, OverflowError) as error:
                    # Typed fixed errors only: never provider text or an arbitrary ValueError string.
                    code = FACT_REASON_MAP.get(str(error), 'FACT_SCHEMA_INVALID') if isinstance(error, SecNormalizationError) else 'FACT_SCHEMA_INVALID'
                    _bump(counts, code)
    grouped = {}
    for fact in clean:
        key = tuple(fact[k] for k in ('namespace', 'concept', 'unit', 'end', 'accn', 'form', 'filed'))
        grouped.setdefault(key, []).append(fact)
    shares = []
    for bucket in grouped.values():
        if len({r['val'] for r in bucket}) > 1: _bump(counts, 'FACT_CONFLICT', len(bucket))
        else: shares.extend(bucket)
    class_notice = 'SHARE_CLASS_BASIS' if counts.get('CLASS_SPLIT') else None
    if not shares:
        code = 'SEC_SHARE_CONCEPT_MISSING' if not found_concept else 'SEC_SHARE_UNIT_MISMATCH' if not found_share_unit else 'SEC_NO_ELIGIBLE_SHARE_FACTS'
        error = SecNormalizationError(code); error.excluded_fact_counts = counts; error.share_class_notice = class_notice
        raise error from None
    return shares, counts, class_notice


def _filing_rows(submissions, acquired_at, counts):
    acquired = timestamp(acquired_at, 'SEC_ACQUISITION_TIMESTAMP_INVALID')
    if not isinstance(submissions.get('filings'), dict) or not isinstance(submissions['filings'].get('recent'), dict):
        _bump(counts, 'FILING_SCHEMA_INVALID'); return []
    recent = submissions['filings']['recent']; keys = ['accessionNumber', 'form', 'filingDate', 'reportDate', 'acceptanceDateTime']
    if not all(isinstance(recent.get(k), list) for k in keys) or len(recent['form']) > 10000 \
            or any(len(recent[k]) != len(recent['form']) for k in keys):
        _bump(counts, 'FILING_SCHEMA_INVALID'); return []
    filings = []
    for i, form in enumerate(recent['form']):
        if not isinstance(form, str):
            _bump(counts, 'FILING_SCHEMA_INVALID'); continue
        if form not in FORMS: continue  # Non-target filing types are outside this projection, not bad share facts.
        filing = {'accession': recent['accessionNumber'][i], 'form': form, 'filed': recent['filingDate'][i],
                  'report_date': recent['reportDate'][i] if recent['reportDate'][i] != '' else None,
                  'accepted_at': recent['acceptanceDateTime'][i]}
        try:
            _require_filing(filing, acquired, acquired.date().isoformat()); filings.append(filing)
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            code = FACT_REASON_MAP.get(str(error), 'FACT_SCHEMA_INVALID') if isinstance(error, SecNormalizationError) else 'FACT_SCHEMA_INVALID'
            _bump(counts, code)
    return filings


def _project_observations(observations):
    rows = []
    try:
        for company, facts_body, submissions_body, acquired_at in observations:
            if company not in US_LISTINGS: invalid()
            cik = US_LISTINGS[company]['cik']; facts = parse(facts_body, cik); submissions = parse(submissions_body, cik)
            shares, counts, class_notice = _share_rows(facts, acquired_at)
            filings = _filing_rows(submissions, acquired_at, counts)
            rows.append({'company_id': company, 'cik': cik, 'acquired_at': acquired_at,
                         'sources': {kind: {'url': source_url(kind, cik), 'sha256': hashlib.sha256(body).hexdigest()}
                                     for kind, body in [('companyfacts', facts_body), ('submissions', submissions_body)]},
                         'reported_shares': shares, 'filings': filings, 'status': 'LIVE',
                         'excluded_fact_counts': counts, 'share_class_basis': 'UNCONFIRMED', 'share_class_notice': class_notice})
        rows.sort(key=lambda row: row['company_id'])
        for row in rows: _require_reported_row(row)
        return rows
    except SecNormalizationError: raise
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError, RecursionError): invalid()


def build_public_inputs(observations):
    return require_public_inputs({'schema': 'public-sec-reported-inputs/3',
        'scope': 'US_TARGET17_REPORTED_SEC_ONLY', 'companies': _project_observations(observations)})


def _diagnostic(error, index, stage):
    code = str(error) if isinstance(error, (SecCollectionError, SecNormalizationError)) and fixed_code(str(error)) else ('SEC_PUBLIC_INPUT_INVALID' if stage == 'normalize' else 'SEC_COLLECTION_FAILED')
    phase = getattr(error, 'stage', None)
    if phase not in ('fetch', 'parse', 'normalize'): phase = stage
    status = getattr(error, 'http_status', None)
    if type(status) is not int or not 400 <= status <= 599: status = None
    if status is None and re.fullmatch(r'SEC_HTTP_[45][0-9]{2}', code): status = int(code[-3:])
    return {'company_index': index, 'stage': phase, 'code': code, 'http_status': status}


def collect_public_inputs(output, *, environ=None, client_factory=None):
    settings = os.environ if environ is None else environ
    if not isinstance(settings.get('SEC_USER_AGENT'), str) or not settings['SEC_USER_AGENT'].strip():
        raise CollectionFailure('SEC_USER_AGENT_MISSING', [{'company_index': 0, 'stage': 'fetch', 'code': 'SEC_USER_AGENT_MISSING', 'http_status': None}])
    if client_factory is None:
        try:
            from investment_system.providers.sec_collection import SecCollectionClient
            client_factory = SecCollectionClient
        except ImportError: raise CollectionFailure('SEC_MODULE_NOT_MERGED', []) from None
    try: client = client_factory(settings.get('SEC_USER_AGENT'))
    except Exception as error:
        diagnostic = _diagnostic(error, 0, 'fetch')
        raise CollectionFailure(diagnostic['code'], [diagnostic]) from None
    rows = []; diagnostics = []
    for index, company in enumerate(sorted(US_LISTINGS), 1):
        stage = 'fetch'; cik = US_LISTINGS[company]['cik']
        try:
            facts, submissions, acquired = client.collect(company, cik)
            # Validate JSON separately so supplied fake clients retain parse stage.
            stage = 'parse'; parse(facts, cik); parse(submissions, cik)
            stage = 'normalize'
            if not isinstance(acquired, datetime) or acquired.utcoffset() is None: invalid('SEC_ACQUISITION_TIMESTAMP_INVALID')
            row = _project_observations([(company, facts, submissions, acquired.astimezone(timezone.utc).isoformat())])[0]
            rows.append(row)
        except Exception as error:
            diagnostic = _diagnostic(error, index, stage)
            if stage == 'parse' and diagnostic['code'] == 'SEC_COLLECTION_FAILED': diagnostic['code'] = 'SEC_JSON_INVALID'
            diagnostics.append(diagnostic)
            rows.append({'company_id': company, 'cik': cik, 'status': 'NOT_AVAILABLE',
                'reason_codes': [diagnostic['code']], 'failure_stage': diagnostic['stage'],
                'company_index': index, 'http_status': diagnostic['http_status'],
                'excluded_fact_counts': error.excluded_fact_counts if isinstance(error, SecNormalizationError) else {},
                'share_class_basis': 'UNCONFIRMED',
                'share_class_notice': error.share_class_notice if isinstance(error, SecNormalizationError) else None})
    exclusions = [{'company_index': i, 'code': code, 'count': count}
        for i, row in enumerate(rows, 1) for code, count in sorted(row['excluded_fact_counts'].items())]
    if len(diagnostics) == len(US_LISTINGS):
        codes = {d['code'] for d in diagnostics}
        raise CollectionFailure(next(iter(codes)) if len(codes) == 1 else 'SEC_COLLECTION_FAILED', diagnostics, exclusions=exclusions) from None
    if diagnostics:
        for row in rows:
            if 'status' not in row: row['status'] = 'LIVE'
    payload = require_public_inputs({'schema': 'public-sec-reported-inputs/3',
        'scope': 'US_TARGET17_REPORTED_SEC_ONLY', 'companies': rows})
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name); handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False).encode())
        os.replace(temporary, output)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
    return {'failed_companies': len(diagnostics), 'diagnostics': diagnostics,
        'exclusions': exclusions}


def _print_exclusions(exclusions):
    for row in exclusions:
        print('SEC_EXCLUDED company_index={company_index} code={code} count={count}'.format(**row))


def _print_diagnostics(diagnostics):
    for row in diagnostics:
        print('SEC_FAILURE company_index={company_index} stage={stage} code={code} http_status={http_status}'.format(**row))


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        self.exit(2, 'SEC_ARGUMENTS_INVALID\n')


def main(argv=None):
    parser = Parser(description='Collect public reported SEC inputs only; SEC_USER_AGENT is an environment Secret name.')
    parser.add_argument('--output', required=True, type=Path); parser.add_argument('--live', action='store_true')
    args = parser.parse_args(argv)
    if not args.live: parser.error('SEC_LIVE_REQUIRED')
    try: result = collect_public_inputs(args.output)
    except Exception as error:
        if isinstance(error, CollectionFailure):
            _print_diagnostics(error.diagnostics)
            _print_exclusions(error.exclusions)
            print(str(error)); print(f'SEC_PUBLIC_BUILD_FAILED failed_companies={error.failed_companies}')
        else: print('SEC_PUBLIC_BUILD_FAILED')
        return 1
    _print_diagnostics(result['diagnostics'])
    _print_exclusions(result.get('exclusions', []))
    print(f"SEC_PUBLIC_BUILD_OK failed_companies={result['failed_companies']}"); return 0


if __name__ == '__main__':
    raise SystemExit(main())
