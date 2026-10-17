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
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.markets.us import US_LISTINGS
from investment_system.providers.sec_collection import SecCollectionError, MAX_BODY_BYTES

FILENAME = 'sec-public-inputs.json'
MAX_BYTES = 2 * 1024 * 1024
SCOPE = 'US_TARGET17_REPORTED_SEC_ONLY'
SCHEMA = 'public-sec-reported-inputs/4'
SCHEMAS = ('public-sec-reported-inputs/1', 'public-sec-reported-inputs/2', 'public-sec-reported-inputs/3', SCHEMA)
# Daily acquisition cadence (public_screens_pipeline.ACQUISITION_TTL), published so readers judge a kept row's age with
# the file's own value. Not a model or calibration threshold.
STALE_AFTER_SECONDS = 24 * 3600
NEW_YORK = ZoneInfo('America/New_York')
TRIGGERS = {'schedule': 'SCHEDULED', 'workflow_dispatch': 'MANUAL'}
# Whether this run read the live copy: read and valid, first publication (404), read failed, or not asked for.
PREVIOUS_STATES = ('LOADED', 'NO_LIVE', 'UNAVAILABLE', 'NOT_REQUESTED')
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


# Owner decision 2026-10-17 (option a): a company whose collection failed transiently keeps its previous verified row.
# Preservable: transport/HTTP/response failures of the fetch (rate limits, 5xx, retries, timeouts, size, redirect) and an
# undecodable SEC body (`SEC_JSON_INVALID` from the SEC client, raised before the body's CIK is read). Never preserved:
# identity conflicts (`SEC_CIK_MISMATCH`, `SEC_ISSUER_NOT_ALLOWED`), an absent SEC resource (HTTP 404/410), an unknown
# failure (`SEC_COLLECTION_FAILED`) and every normalize-stage result (a policy NA or a confirmed invalid input of a
# successful collection).
TRANSIENT_FETCH_CODES = frozenset({
    'SEC_TRANSPORT_FAILED', 'SEC_TRANSPORT_RETRIES_EXHAUSTED', 'SEC_HTTP_RETRIES_EXHAUSTED',
    'SEC_RETRY_AFTER_EXCEEDS_BUDGET', 'SEC_RESPONSE_INVALID', 'SEC_RESPONSE_URL_MISMATCH', 'SEC_REDIRECT_REJECTED',
    'SEC_RESPONSE_TOO_LARGE', 'SEC_CLOCK_INVALID', 'SEC_SLEEP_FAILED', 'SEC_USER_AGENT_INVALID', 'SEC_URL_NOT_ALLOWED',
    'SEC_CONFIG_INVALID',
})
IDENTITY_CODES = frozenset({'SEC_CIK_MISMATCH', 'SEC_ISSUER_NOT_ALLOWED'})
# Owner decision 2026-10-17 (schema /4): a normalize-stage result of a successful collection (bytes received, both bodies
# bound to the issuer's CIK, acquisition time valid) is a policy NA that records that collection's real acquired_at.
POLICY_NA_CODES = (NORMALIZATION_CODES - {'SEC_ACQUISITION_TIMESTAMP_INVALID'}) | {'SEC_PUBLIC_INPUT_INVALID'}


def preservable_code(code, stage):
    """A failure of the collection itself (fetch/transport/undecodable body), never an identity conflict or a result."""
    if code in IDENTITY_CODES:
        return False
    if stage == 'fetch':
        return code in TRANSIENT_FETCH_CODES or (re.fullmatch(r'SEC_HTTP_[45][0-9]{2}', code) is not None
                                                 and code not in ('SEC_HTTP_404', 'SEC_HTTP_410'))
    return stage == 'parse' and code == 'SEC_JSON_INVALID'


def preservable_failure(diagnostic, error):
    """True for a collection failure (not an identity conflict, not a result of a successful collection)."""
    return isinstance(error, SecCollectionError) and preservable_code(diagnostic['code'], diagnostic['stage'])


def previous_rows(previous):
    """{company_id: row} of the rows of a validated previous copy that carry a record of the issuer, as /4 rows:
    /3 LIVE rows; /4 LIVE and NOT_AVAILABLE rows (a successful collection, `acquired_at`) and WITHDRAWN rows (an
    identity conflict that stopped an observation). Rows without a record (NOT_AVAILABLE of /3, COLLECTION_FAILED) and
    older schemas give nothing. The run marker `preserved_previous` of the previous copy is dropped (set again here)."""
    if type(previous) is not dict or previous.get('schema') not in ('public-sec-reported-inputs/3', SCHEMA):
        return {}
    v4 = previous['schema'] == SCHEMA
    out = {}
    for row in previous.get('companies', []):
        if type(row) is not dict:
            continue
        status = row.get('status')
        recorded = (status in ('LIVE', 'NOT_AVAILABLE') and type(row.get('acquired_at')) is str) if v4 or status == 'LIVE' else False
        if not (recorded or v4 and status == 'WITHDRAWN' and type(row.get('detected_at')) is str):
            continue
        company = row.get('company_id')
        if company in US_LISTINGS and row.get('cik') == US_LISTINGS[company]['cik']:
            out[company] = {k: v for k, v in json.loads(json.dumps(row)).items() if k != 'preserved_previous'}
    return out


def withdrawn_observation(kept):
    """The acquired_at a withdrawal stops: the kept row's own, or the one an earlier withdrawal already stopped."""
    if kept is None:
        return None
    return kept['withdrawn_acquired_at'] if kept['status'] == 'WITHDRAWN' else kept['acquired_at']


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


def _require_sources(row):
    if not isinstance(row['sources'], dict) or set(row['sources']) != {'companyfacts', 'submissions'}:
        invalid('SEC_SOURCE_METADATA_INVALID')
    for kind, source in row['sources'].items():
        if not isinstance(source, dict) or set(source) != {'url', 'sha256'} or source['url'] != source_url(kind, row['cik']) \
                or not isinstance(source['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', source['sha256']):
            invalid('SEC_SOURCE_METADATA_INVALID')


def _require_reported_row(row):
    acquired = timestamp(row['acquired_at'], 'SEC_ACQUISITION_TIMESTAMP_INVALID')
    as_of = acquired.date().isoformat()
    _require_sources(row)
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


# ---- schema /4 (owner decision 2026-10-17, TARGET NA schema supplement) ----
# Every row says what is known of its issuer, and a time is only ever an acquired_at when a collection succeeded:
#   LIVE               successful collection with reported share facts: acquired_at, sources, reported_shares, filings.
#   NOT_AVAILABLE      successful collection whose result is a policy NA (normalize stage): the collection's real
#                      acquired_at, its sources (SEC URL + sha256 of the bodies received) and one fixed reason code.
#   COLLECTION_FAILED  no successful collection and no kept record: checked_at (when the failure was seen), reason,
#                      stage. Never an acquired_at.
#   WITHDRAWN          identity conflict (SEC_CIK_MISMATCH / SEC_ISSUER_NOT_ALLOWED): no values; detected_at (when the
#                      conflict was seen) and withdrawn_acquired_at, the acquired_at of the observation whose use it stops
#                      (null when there was none). Readers never use the stopped observation.
# preserved_previous: null for a row produced by this run; for a row kept unchanged from the previous copy because this
# run's collection failed transiently: {checked_at, reason_codes, failure_stage, http_status} of that failed attempt.
# collection: this run (checked_at, New York run_day, trigger, whether the previous copy was read, the file's
# stale_after_seconds) and the self-certifying scheduled_streak (see scheduled_streak()).
_V4_COMMON = {'company_id', 'cik', 'status', 'excluded_fact_counts', 'share_class_basis', 'share_class_notice',
              'preserved_previous'}
_V4_FAILURE = {'reason_codes', 'failure_stage', 'company_index', 'http_status'}
V4_FIELDS = {
    'LIVE': _V4_COMMON | {'acquired_at', 'sources', 'reported_shares', 'filings'},
    'NOT_AVAILABLE': _V4_COMMON | _V4_FAILURE | {'acquired_at', 'sources'},
    'COLLECTION_FAILED': _V4_COMMON | _V4_FAILURE | {'checked_at'},
    'WITHDRAWN': _V4_COMMON | _V4_FAILURE | {'detected_at', 'withdrawn_acquired_at'},
}
COLLECTION_FIELDS = {'checked_at', 'run_day', 'trigger', 'previous', 'stale_after_seconds', 'scheduled_streak'}
STREAK_FIELDS = {'count', 'since', 'last_run_day'}


def _http_status(value):
    if value is not None and (type(value) is not int or not 400 <= value <= 599): invalid()


def _require_failure(row, index):
    if type(row['company_index']) is not int or row['company_index'] != index: invalid()
    if row['failure_stage'] not in ('fetch', 'parse', 'normalize'): invalid()
    if not isinstance(row['reason_codes'], list) or len(row['reason_codes']) != 1 or not fixed_code(row['reason_codes'][0]): invalid()
    _http_status(row['http_status'])
    return row['reason_codes'][0]


def _require_collection(collection):
    if not isinstance(collection, dict) or set(collection) != COLLECTION_FIELDS: invalid()
    checked = timestamp(collection['checked_at'])
    if collection['run_day'] != checked.astimezone(NEW_YORK).date().isoformat(): invalid()
    if collection['trigger'] not in ('SCHEDULED', 'MANUAL', 'OTHER'): invalid()
    if collection['previous'] not in PREVIOUS_STATES: invalid()
    if type(collection['stale_after_seconds']) is not int or collection['stale_after_seconds'] != STALE_AFTER_SECONDS: invalid()
    streak = collection['scheduled_streak']
    if not isinstance(streak, dict) or set(streak) != STREAK_FIELDS: invalid()
    last = None if streak['last_run_day'] is None else date.fromisoformat(day(streak['last_run_day']))
    if last is not None and last.isoformat() > collection['run_day']: invalid()
    if collection['trigger'] == 'SCHEDULED' and streak['last_run_day'] != collection['run_day']: invalid()
    if streak['count'] is None:
        if streak['since'] is not None: invalid()
    else:
        if type(streak['count']) is not int or not 1 <= streak['count'] <= 100000 or last is None: invalid()
        if (last - date.fromisoformat(day(streak['since']))).days + 1 != streak['count']: invalid()
    return checked


def _require_v4_row(row, index, run_checked):
    status = row.get('status')
    if status not in V4_FIELDS or set(row) != V4_FIELDS[status]: invalid()
    _require_exclusions(row)
    if status == 'LIVE':
        _require_reported_row(row)
        if not row['reported_shares']: invalid()
        marker = timestamp(row['acquired_at'])
    elif status == 'NOT_AVAILABLE':
        if _require_failure(row, index) not in POLICY_NA_CODES or row['failure_stage'] != 'normalize' \
                or row['http_status'] is not None: invalid()
        marker = timestamp(row['acquired_at'])
        _require_sources(row)
    else:
        code = _require_failure(row, index)
        if row['excluded_fact_counts'] or row['share_class_notice'] is not None: invalid()
        if status == 'COLLECTION_FAILED':
            if code in IDENTITY_CODES or row['preserved_previous'] is not None: invalid()
            marker = timestamp(row['checked_at'])
        else:
            if code not in IDENTITY_CODES: invalid()
            marker = timestamp(row['detected_at'])
            if row['withdrawn_acquired_at'] is not None and timestamp(row['withdrawn_acquired_at']) > marker: invalid()
    kept = row['preserved_previous']
    if kept is not None:
        if not isinstance(kept, dict) or set(kept) != {'checked_at', 'reason_codes', 'failure_stage', 'http_status'}: invalid()
        if not isinstance(kept['reason_codes'], list) or len(kept['reason_codes']) != 1 \
                or not fixed_code(kept['reason_codes'][0]) or not preservable_code(kept['reason_codes'][0], kept['failure_stage']): invalid()
        _http_status(kept['http_status'])
        checked = timestamp(kept['checked_at'])
        if checked < marker or checked > run_checked: invalid()
    elif marker > run_checked: invalid()


def _require_public_inputs(payload):
    if not isinstance(payload, dict) or payload.get('schema') not in SCHEMAS: invalid()
    v4 = payload['schema'] == SCHEMA
    if set(payload) != {'schema', 'scope', 'companies'} | ({'collection'} if v4 else set()) or payload['scope'] != SCOPE: invalid()
    companies = payload['companies']; v3 = payload['schema'].endswith('/3'); partial = payload['schema'].endswith('/2') or v3
    if not isinstance(companies, list) or len(companies) != len(US_LISTINGS): invalid()
    run_checked = _require_collection(payload['collection']) if v4 else None
    seen = []
    extra = {'excluded_fact_counts', 'share_class_basis', 'share_class_notice'} if v3 else set()
    base_fields = {'company_id', 'cik', 'acquired_at', 'sources', 'reported_shares', 'filings'}
    unavailable_fields = {'company_id', 'cik', 'status', 'reason_codes', 'failure_stage', 'company_index', 'http_status'}
    for index, row in enumerate(companies, 1):
        if not isinstance(row, dict): invalid()
        company = row.get('company_id')
        if not isinstance(company, str) or company not in US_LISTINGS or row.get('cik') != US_LISTINGS[company]['cik']: invalid()
        seen.append(company)
        if v4:
            _require_v4_row(row, index, run_checked)
            continue
        if v3: _require_exclusions(row)
        if partial and row.get('status') == 'NOT_AVAILABLE':
            if set(row) != unavailable_fields | extra: invalid()
            _require_failure(row, index)
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


def _utc_now():
    return datetime.now(timezone.utc)


def _iso(moment):
    return moment.astimezone(timezone.utc).isoformat()


def scheduled_streak(previous, previous_state, trigger, run_day):
    """Consecutive New York run days whose SCHEDULED run reached Pages, as this file will show once deployed.

    Self-certifying: a file is public only when its deploy succeeded, so a scheduled run that reads, as the live copy, the
    file of the scheduled run of the previous day continues that run's count; any other live copy (gap, failed deploy,
    /3 copy) starts again at 1. A manual run (fallback or one-off) never counts and carries the live count unchanged;
    the manual cockpit-pages deploy re-publishes the live bytes and changes nothing. Unknown when the live copy could
    not be read."""
    live = previous.get('collection', {}).get('scheduled_streak') if type(previous) is dict and previous.get('schema') == SCHEMA else None
    if live is not None and live['last_run_day'] is not None and live['last_run_day'] > run_day:
        live = None                                   # a live copy from a later run day (clock skew): no history
    if trigger != 'SCHEDULED':
        return dict(live) if previous_state == 'LOADED' and live is not None else dict.fromkeys(STREAK_FIELDS)
    today = date.fromisoformat(run_day)
    if previous_state not in ('LOADED', 'NO_LIVE'):
        return {'count': None, 'since': None, 'last_run_day': run_day}
    if live is not None and live['last_run_day'] is not None:
        last = date.fromisoformat(live['last_run_day'])
        if last == today and live['count'] is not None:
            return dict(live)
        if (today - last).days == 1:
            since = live['since'] or live['last_run_day']
            return {'count': (today - date.fromisoformat(since)).days + 1, 'since': since, 'last_run_day': run_day}
    return {'count': 1, 'since': run_day, 'last_run_day': run_day}


def collection_block(checked, *, trigger='OTHER', previous_state='NOT_REQUESTED', previous=None):
    run_day = checked.astimezone(NEW_YORK).date().isoformat()
    return {'checked_at': _iso(checked), 'run_day': run_day, 'trigger': trigger, 'previous': previous_state,
            'stale_after_seconds': STALE_AFTER_SECONDS,
            'scheduled_streak': scheduled_streak(previous, previous_state, trigger, run_day)}


def build_public_inputs(observations):
    """A /4 payload of successful collections only (no run context: trigger OTHER, previous copy not requested)."""
    rows = [dict(row, preserved_previous=None) for row in _project_observations(observations)]
    checked = max(timestamp(row['acquired_at']) for row in rows) if rows else _utc_now()
    return require_public_inputs({'schema': SCHEMA, 'scope': SCOPE, 'collection': collection_block(checked), 'companies': rows})


def _diagnostic(error, index, stage):
    code = str(error) if isinstance(error, (SecCollectionError, SecNormalizationError)) and fixed_code(str(error)) else ('SEC_PUBLIC_INPUT_INVALID' if stage == 'normalize' else 'SEC_COLLECTION_FAILED')
    phase = getattr(error, 'stage', None)
    if phase not in ('fetch', 'parse', 'normalize'): phase = stage
    status = getattr(error, 'http_status', None)
    if type(status) is not int or not 400 <= status <= 599: status = None
    if status is None and re.fullmatch(r'SEC_HTTP_[45][0-9]{2}', code): status = int(code[-3:])
    return {'company_index': index, 'stage': phase, 'code': code, 'http_status': status}


def _failure_fields(diagnostic, index):
    return {'reason_codes': [diagnostic['code']], 'failure_stage': diagnostic['stage'], 'company_index': index,
            'http_status': diagnostic['http_status']}


def collect_public_inputs(output, *, environ=None, client_factory=None, previous=None, previous_state=None, now=None):
    """Collect the 17 TARGET US issuers into schema /4. `previous`: the validated live Pages copy (/3 or /4, or None);
    `previous_state`: how it was read (PREVIOUS_STATES); `now`: the collector's clock (checked_at / detected_at).

    Per company (owner decisions 2026-10-17):
    - successful collection -> LIVE, or NOT_AVAILABLE with the collection's real acquired_at, sources and reason when
      the result is a policy NA (normalize stage);
    - identity conflict (SEC_CIK_MISMATCH / SEC_ISSUER_NOT_ALLOWED) -> WITHDRAWN: detected_at, and the acquired_at of
      the previous record it stops (withdrawn_acquired_at, null without one); never the previous values;
    - transient collection failure with a previous record of the same company_id and CIK -> that row unchanged (its
      acquired_at, sources and values, or its withdrawal) with `preserved_previous` naming this failed attempt;
    - any other failure -> COLLECTION_FAILED with checked_at. A failure time is never written as acquired_at."""
    settings = os.environ if environ is None else environ
    clock = now or _utc_now
    state = previous_state if previous_state in PREVIOUS_STATES else 'LOADED' if previous is not None else 'NOT_REQUESTED'
    kept_rows = previous_rows(previous)
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
    rows = []; diagnostics = []; preserved = []; withdrawn = []
    for index, company in enumerate(sorted(US_LISTINGS), 1):
        stage = 'fetch'; cik = US_LISTINGS[company]['cik']; collected = None
        try:
            facts, submissions, acquired = client.collect(company, cik)
            # Validate JSON separately so supplied fake clients retain parse stage.
            stage = 'parse'; parse(facts, cik); parse(submissions, cik)
            stage = 'normalize'
            if not isinstance(acquired, datetime) or acquired.utcoffset() is None: invalid('SEC_ACQUISITION_TIMESTAMP_INVALID')
            acquired_at = acquired.astimezone(timezone.utc).isoformat()
            timestamp(acquired_at, 'SEC_ACQUISITION_TIMESTAMP_INVALID')
            # From here the collection succeeded: both bodies bound to the issuer's CIK at a valid acquisition time.
            collected = {'acquired_at': acquired_at, 'sources': {kind: {'url': source_url(kind, cik),
                         'sha256': hashlib.sha256(body).hexdigest()} for kind, body in [('companyfacts', facts), ('submissions', submissions)]}}
            row = _project_observations([(company, facts, submissions, acquired_at)])[0]
            rows.append(dict(row, preserved_previous=None))
        except Exception as error:
            diagnostic = _diagnostic(error, index, stage)
            if stage == 'parse' and diagnostic['code'] == 'SEC_COLLECTION_FAILED': diagnostic['code'] = 'SEC_JSON_INVALID'
            diagnostics.append(diagnostic)
            kept = kept_rows.get(company)
            base = {'company_id': company, 'cik': cik, 'excluded_fact_counts': {}, 'share_class_basis': 'UNCONFIRMED',
                    'share_class_notice': None, 'preserved_previous': None}
            if diagnostic['code'] in IDENTITY_CODES:
                rows.append(dict(base, status='WITHDRAWN', detected_at=_iso(clock()),
                                 withdrawn_acquired_at=withdrawn_observation(kept), **_failure_fields(diagnostic, index)))
                withdrawn.append({'company_index': index, 'code': diagnostic['code'],
                                  'previous': 'NONE' if kept is None else kept['status']})
            elif kept is not None and preservable_failure(diagnostic, error):
                rows.append(dict(kept, preserved_previous={'checked_at': _iso(clock()), 'reason_codes': [diagnostic['code']],
                    'failure_stage': diagnostic['stage'], 'http_status': diagnostic['http_status']}))
                preserved.append({'company_index': index, 'code': diagnostic['code'], 'previous': kept['status']})
            elif collected is not None:
                rows.append(dict(base, status='NOT_AVAILABLE', **collected, **_failure_fields(diagnostic, index),
                    excluded_fact_counts=error.excluded_fact_counts if isinstance(error, SecNormalizationError) else {},
                    share_class_notice=error.share_class_notice if isinstance(error, SecNormalizationError) else None))
            else:
                rows.append(dict(base, status='COLLECTION_FAILED', checked_at=_iso(clock()), **_failure_fields(diagnostic, index)))
    kept_index = {p['company_index'] for p in preserved}
    # A preserved row's exclusions belong to its earlier collection, not to this run.
    exclusions = [{'company_index': i, 'code': code, 'count': count}
        for i, row in enumerate(rows, 1) if i not in kept_index for code, count in sorted(row['excluded_fact_counts'].items())]
    if len(diagnostics) == len(US_LISTINGS):
        codes = {d['code'] for d in diagnostics}
        raise CollectionFailure(next(iter(codes)) if len(codes) == 1 else 'SEC_COLLECTION_FAILED', diagnostics, exclusions=exclusions) from None
    trigger = TRIGGERS.get(settings.get('GITHUB_EVENT_NAME'), 'OTHER')
    payload = require_public_inputs({'schema': SCHEMA, 'scope': SCOPE, 'companies': rows,
        'collection': collection_block(clock(), trigger=trigger, previous_state=state, previous=previous)})
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name); handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False).encode())
        os.replace(temporary, output)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
    count = lambda status: sum(1 for row in rows if row['status'] == status and row['preserved_previous'] is None)
    return {'failed_companies': len(diagnostics), 'diagnostics': diagnostics,
        'exclusions': exclusions, 'preserved': preserved, 'withdrawn': withdrawn, 'companies': len(US_LISTINGS),
        'collected_companies': len(US_LISTINGS) - len(diagnostics), 'policy_na': count('NOT_AVAILABLE'),
        'collection_failed': count('COLLECTION_FAILED'), 'previous': state,
        'scheduled_streak': payload['collection']['scheduled_streak']}


def _print_exclusions(exclusions):
    for row in exclusions:
        print('SEC_EXCLUDED company_index={company_index} code={code} count={count}'.format(**row))


def _print_diagnostics(diagnostics):
    for row in diagnostics:
        print('SEC_FAILURE company_index={company_index} stage={stage} code={code} http_status={http_status}'.format(**row))



def _print_collection(result, previous_state='NOT_REQUESTED'):
    """Owner decisions 2026-10-17: new collections, failures, rows kept from the previous copy and identity withdrawals,
    counted separately (a preserved company is a failed collection, never today's success; a policy NA is a successful
    collection without values). `collected` keeps its meaning (new LIVE rows). Counts and fixed codes only."""
    preserved = result.get('preserved', [])
    for row in preserved:
        print('SEC_PRESERVED company_index={company_index} code={code} previous={previous}'.format(**{'previous': 'LIVE', **row}))
    for row in result.get('withdrawn', []):
        print('SEC_WITHDRAWN company_index={company_index} code={code} previous={previous}'.format(**row))
    state = previous_state if previous_state in PREVIOUS_STATES else 'UNAVAILABLE'
    streak = result.get('scheduled_streak') or {}
    print(f"SEC_PUBLIC_COLLECTION companies={result['companies']} collected={result['collected_companies']} "
          f"failed={result['failed_companies']} preserved_previous={len(preserved)} "
          f"not_available={result['failed_companies'] - len(preserved)} previous={state} "
          f"policy_na={result.get('policy_na', 0)} withdrawn={len(result.get('withdrawn', []))} "
          f"collection_failed={result.get('collection_failed', 0)} "
          f"scheduled_streak={'NONE' if streak.get('count') is None else streak['count']}")


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
    _print_collection(result)
    print(f"SEC_PUBLIC_BUILD_OK failed_companies={result['failed_companies']}"); return 0


if __name__ == '__main__':
    raise SystemExit(main())
