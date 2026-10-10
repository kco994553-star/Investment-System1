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
CONCEPTS = {('dei', 'EntityCommonStockSharesOutstanding'), ('us-gaap', 'CommonStockSharesOutstanding')}
FORMS = {'10-K', '10-Q', '10-K/A', '10-Q/A', '20-F', '20-F/A', '40-F', '6-K', '8-K'}
FACT_FIELDS = {'namespace', 'concept', 'unit', 'end', 'val', 'accn', 'form', 'filed'}
FACT_OPTIONAL = {'start', 'fy', 'fp', 'frame'}


def invalid():
    raise ValueError('SEC_PUBLIC_INPUT_INVALID') from None


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value): invalid()
    try: date.fromisoformat(value)
    except ValueError: invalid()
    return value


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value): invalid()
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.utcoffset() is None or result > datetime.now(timezone.utc): invalid()
        return result
    except ValueError: invalid()


def accession(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', value): invalid()


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
})


def fixed_code(value):
    return type(value) is str and (value in FIXED_COLLECTION_CODES or re.fullmatch(r'SEC_HTTP_[45][0-9]{2}', value) is not None)


class CollectionFailure(ValueError):
    def __init__(self, code, diagnostics, failed_companies=17):
        super().__init__(code)
        self.diagnostics = diagnostics
        self.failed_companies = failed_companies


def _require_reported_row(row):
    acquired = timestamp(row['acquired_at']); as_of = acquired.date().isoformat()
    if not isinstance(row['sources'], dict) or set(row['sources']) != {'companyfacts', 'submissions'}: invalid()
    for kind, source in row['sources'].items():
        if not isinstance(source, dict) or set(source) != {'url', 'sha256'} or source['url'] != source_url(kind, row['cik']) \
                or not isinstance(source['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', source['sha256']): invalid()
    if not isinstance(row['reported_shares'], list) or len(row['reported_shares']) > 10000: invalid()
    for fact in row['reported_shares']:
        if not isinstance(fact, dict) or not FACT_FIELDS <= set(fact) or set(fact) - FACT_FIELDS - FACT_OPTIONAL: invalid()
        if (fact['namespace'], fact['concept']) not in CONCEPTS or fact['unit'] != 'shares' or fact['form'] not in FORMS: invalid()
        if type(fact['val']) not in (int, float) or not math.isfinite(fact['val']) or not 0 < fact['val'] <= 2**53 - 1: invalid()
        if day(fact['end']) > as_of or day(fact['filed']) > as_of: invalid()
        accession(fact['accn'])
        if 'start' in fact and day(fact['start']) > fact['end']: invalid()
        if 'fy' in fact and (type(fact['fy']) is not int or not 1900 <= fact['fy'] <= 9999): invalid()
        if 'fp' in fact and fact['fp'] not in {'FY', 'Q1', 'Q2', 'Q3', 'Q4'}: invalid()
        if 'frame' in fact and (not isinstance(fact['frame'], str) or not re.fullmatch(r'CY\d{4}(?:Q[1-4])?I?', fact['frame'])): invalid()
    if not isinstance(row['filings'], list) or len(row['filings']) > 10000: invalid()
    for filing in row['filings']:
        if not isinstance(filing, dict) or set(filing) != {'accession', 'form', 'filed', 'report_date', 'accepted_at'}: invalid()
        accession(filing['accession'])
        if filing['form'] not in FORMS or day(filing['filed']) > as_of or timestamp(filing['accepted_at']) > acquired: invalid()
        if filing['report_date'] is not None and day(filing['report_date']) > as_of: invalid()


def _require_public_inputs(payload):
    if not isinstance(payload, dict) or set(payload) != {'schema', 'scope', 'companies'} \
            or payload['schema'] not in ('public-sec-reported-inputs/1', 'public-sec-reported-inputs/2') or payload['scope'] != 'US_TARGET17_REPORTED_SEC_ONLY': invalid()
    companies = payload['companies']; partial = payload['schema'].endswith('/2')
    if not isinstance(companies, list) or len(companies) != len(US_LISTINGS): invalid()
    seen = []
    base_fields = {'company_id', 'cik', 'acquired_at', 'sources', 'reported_shares', 'filings'}
    unavailable_fields = {'company_id', 'cik', 'status', 'reason_codes', 'failure_stage', 'company_index', 'http_status'}
    for index, row in enumerate(companies, 1):
        if not isinstance(row, dict): invalid()
        company = row.get('company_id')
        if not isinstance(company, str) or company not in US_LISTINGS or row.get('cik') != US_LISTINGS[company]['cik']: invalid()
        seen.append(company)
        if partial and row.get('status') == 'NOT_AVAILABLE':
            if set(row) != unavailable_fields or row['company_index'] != index or type(row['company_index']) is not int: invalid()
            if row['failure_stage'] not in ('fetch', 'parse', 'normalize'): invalid()
            if not isinstance(row['reason_codes'], list) or len(row['reason_codes']) != 1 or not fixed_code(row['reason_codes'][0]): invalid()
            if row['http_status'] is not None and (type(row['http_status']) is not int or not 400 <= row['http_status'] <= 599): invalid()
            continue
        if set(row) != base_fields | ({'status'} if partial else set()) or partial and row.get('status') != 'LIVE': invalid()
        _require_reported_row(row)
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


def _project_observations(observations):
    rows = []
    try:
        for company, facts_body, submissions_body, acquired_at in observations:
            if company not in US_LISTINGS: invalid()
            cik = US_LISTINGS[company]['cik']; facts = parse(facts_body, cik); submissions = parse(submissions_body, cik)
            shares = []
            for namespace, concept in sorted(CONCEPTS):
                entries = facts.get('facts', {}).get(namespace, {}).get(concept, {}).get('units', {}).get('shares', [])
                if not isinstance(entries, list) or len(entries) > 10000: invalid()
                for entry in entries:
                    shares.append({'namespace': namespace, 'concept': concept, 'unit': 'shares',
                                   **{k: entry[k] for k in ('end', 'val', 'accn', 'form', 'filed')},
                                   **{k: entry[k] for k in FACT_OPTIONAL if k in entry}})
            recent = submissions['filings']['recent']; keys = ['accessionNumber', 'form', 'filingDate', 'reportDate', 'acceptanceDateTime']
            if not all(isinstance(recent.get(k), list) for k in keys) or len(recent['form']) > 10000 \
                    or any(len(recent[k]) != len(recent['form']) for k in keys): invalid()
            filings = [{'accession': recent['accessionNumber'][i], 'form': form, 'filed': recent['filingDate'][i],
                        'report_date': recent['reportDate'][i] or None, 'accepted_at': recent['acceptanceDateTime'][i]}
                       for i, form in enumerate(recent['form']) if form in FORMS]
            rows.append({'company_id': company, 'cik': cik, 'acquired_at': acquired_at,
                         'sources': {kind: {'url': source_url(kind, cik), 'sha256': hashlib.sha256(body).hexdigest()}
                                     for kind, body in [('companyfacts', facts_body), ('submissions', submissions_body)]},
                         'reported_shares': shares, 'filings': filings})
        rows.sort(key=lambda row: row['company_id'])
        for row in rows: _require_reported_row(row)
        return rows
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError, RecursionError): invalid()


def build_public_inputs(observations):
    return require_public_inputs({'schema': 'public-sec-reported-inputs/1',
        'scope': 'US_TARGET17_REPORTED_SEC_ONLY', 'companies': _project_observations(observations)})


def _diagnostic(error, index, stage):
    code = str(error) if isinstance(error, SecCollectionError) and fixed_code(str(error)) else ('SEC_PUBLIC_INPUT_INVALID' if stage == 'normalize' else 'SEC_COLLECTION_FAILED')
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
            if not isinstance(acquired, datetime) or acquired.utcoffset() is None: invalid()
            row = _project_observations([(company, facts, submissions, acquired.astimezone(timezone.utc).isoformat())])[0]
            rows.append(row)
        except Exception as error:
            diagnostic = _diagnostic(error, index, stage)
            if stage == 'parse' and diagnostic['code'] == 'SEC_COLLECTION_FAILED': diagnostic['code'] = 'SEC_JSON_INVALID'
            diagnostics.append(diagnostic)
            rows.append({'company_id': company, 'cik': cik, 'status': 'NOT_AVAILABLE',
                'reason_codes': [diagnostic['code']], 'failure_stage': diagnostic['stage'],
                'company_index': index, 'http_status': diagnostic['http_status']})
    if len(diagnostics) == len(US_LISTINGS):
        codes = {d['code'] for d in diagnostics}
        raise CollectionFailure(next(iter(codes)) if len(codes) == 1 else 'SEC_COLLECTION_FAILED', diagnostics) from None
    if diagnostics:
        for row in rows:
            if 'status' not in row: row['status'] = 'LIVE'
    payload = require_public_inputs({'schema': 'public-sec-reported-inputs/2' if diagnostics else 'public-sec-reported-inputs/1',
        'scope': 'US_TARGET17_REPORTED_SEC_ONLY', 'companies': rows})
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name); handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False).encode())
        os.replace(temporary, output)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
    return {'failed_companies': len(diagnostics), 'diagnostics': diagnostics}


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
            print(str(error)); print(f'SEC_PUBLIC_BUILD_FAILED failed_companies={error.failed_companies}')
        else: print('SEC_PUBLIC_BUILD_FAILED')
        return 1
    _print_diagnostics(result['diagnostics'])
    print(f"SEC_PUBLIC_BUILD_OK failed_companies={result['failed_companies']}"); return 0


if __name__ == '__main__':
    raise SystemExit(main())
