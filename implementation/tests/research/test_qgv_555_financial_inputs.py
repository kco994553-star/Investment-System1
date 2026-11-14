"""Synthetic source bindings for the temporary official FINANCIAL raw bridge."""
from copy import deepcopy
import hashlib
import json
import math

import pytest

from investment_system.research.qgv_555_financial_inputs import (
    apply_temporary_financial_inputs,
    review_official_book_value_history,
)
from investment_system.qgv import v2_factors as vf
from investment_system.research.qgv_555_financial_temporary import (
    CALC_VERSION, financial_catalog,
)
from investment_system.research.qgv_555_official_share import FORMULAS
from investment_system.research.sector_qgv import digest


SOURCE_BLOB_SHA = 'a' * 64
COMPANYFACTS_SHA = 'b' * 64
CONTEXT_KEY = 'synthetic/source~1'
ACQUIRED = '2026-11-03T12:00:00Z'
OLD_REVIEW = '2026-11-12T12:00:00Z'
NEW_REVIEW = '2026-11-14T12:00:00Z'
BOOK_FORMULA = 'OFFICIAL_EQUITY_OVER_WEIGHTED_DILUTED_SHARES_CAGR_3Y'


def share_claim(metric, value):
    return dict(value=value, reusable=True, adoption_basis='EVIDENCE_LINKED',
        strict_verified=False, requires_assumption=False, allowed_assumptions=[],
        evidence_only_eligible=True, formula_source='EXISTING_OFFICIAL_KERNEL',
        formula_variant=BOOK_FORMULA if metric == 'book_value_per_share_cagr_3y'
            else FORMULAS[metric],
        denominator_definition='WEIGHTED_AVERAGE_DILUTED_SHARES',
        additional_verification_required=True,
        additional_verification=['SYNTHETIC_SHARE_CLASS_CONTEXT'],
        periods=[dict(label='FY0', fiscal_year_end='2025-12-31'),
                 dict(label='FY-3', fiscal_year_end='2022-12-31')])


def source_fixture():
    raw = dict(roe=.12, roa=.01, net_interest_income_to_assets=.03,
        moat_proxy=.08, equity_to_assets=.1, dilution_3y=0., incremental_roe_5y=-.02,
        revenue_cagr_3y=.04, eps_cagr_3y=.09,
        book_value_per_share_cagr_3y=.05, incremental_roe_3y=.11,
        revenue_positive_growth_share=.6, revenue_growth_volatility=.07,
        revenue_acceleration=-.01)
    record = dict(cik='SYN:ISSUER', acquired_at=ACQUIRED, state='LIVE',
        calc_version=CALC_VERSION, profile='FINANCIAL', sic='6020',
        industry_group='synthetic-bank', fiscal_year_end='2025-12-31', currency='USD',
        source_sha256=dict(companyfacts=COMPANYFACTS_SHA), metrics=raw,
        axes='official score structure must never be read',
        factors=['official factors must never be copied'])
    anchor = f'sha256:{SOURCE_BLOB_SHA}#/records/synthetic'
    owner = dict(source_sha256=SOURCE_BLOB_SHA, source_pointer='/records/synthetic',
        record_hash=digest(record), profile='FINANCIAL', sic=record['sic'],
        industry_group=record['industry_group'], fiscal_year_end=record['fiscal_year_end'],
        acquired_at=ACQUIRED, currency='USD', calc_version=CALC_VERSION,
        companyfacts_sha256=COMPANYFACTS_SHA)
    row = dict(company_id='SYN:FINANCIAL', issuer_id=record['cik'], security_id=None,
        accounting_template='BANK', sector_id='FINANCIALS',
        classification_status='VERIFIED', industry_group='synthetic-bank',
        metrics={'retained-general-key': .25}, metric_evidence={}, gate={'status': 'PASS'},
        owner_source_context=owner,
        financial_reference=dict(profile='FINANCIAL', source_refs=[anchor],
            axes=deepcopy(record['axes']), factors=deepcopy(record['factors']),
            counts_as_555=False))
    general = dict(company_id='SYN:GENERAL', issuer_id='SYN:GENERAL_ISSUER',
        accounting_template='GENERAL', sector_id='INDUSTRIALS', metrics={'roic': .2},
        metric_evidence={'roic': dict(status='VERIFIED')}, gate={'status': 'PASS'})
    snapshot = dict(rows=[row, general], members=['SYN:FINANCIAL', 'SYN:GENERAL'],
        input_cutoff='2026-11-04T12:00:00Z', evaluation_day='2026-11-04',
        source_anchors=[dict(sha256=SOURCE_BLOB_SHA)])
    context = dict(source_record=record, source_sha256=COMPANYFACTS_SHA,
        source_key='/records/synthetic', issuer_id=record['cik'], acquired_at=ACQUIRED,
        fiscal_year_end=record['fiscal_year_end'], currency='USD',
        official_calc_version=CALC_VERSION, source_refs=[f'sha256:{COMPANYFACTS_SHA}'],
        metrics={m: share_claim(m, raw[m]) for m in ('eps_cagr_3y', 'dilution_3y')})
    review = dict(reviewed_at=OLD_REVIEW, source_contexts={CONTEXT_KEY: context})
    book = {CONTEXT_KEY: dict(source_record_hash=digest(record),
        source_body_sha256=COMPANYFACTS_SHA,
        claim=share_claim('book_value_per_share_cagr_3y', raw['book_value_per_share_cagr_3y']))}
    return snapshot, review, book


def write_review(tmp_path, review):
    path = tmp_path / 'synthetic-review.json'
    body = json.dumps(review, ensure_ascii=False, indent=2).encode('utf-8')
    path.write_bytes(body)
    return path, hashlib.sha256(body).hexdigest()


def apply(tmp_path, snapshot, review, *, book=None, reviewed_at=NEW_REVIEW,
          input_cutoff=NEW_REVIEW):
    path, file_sha = write_review(tmp_path, review)
    return apply_temporary_financial_inputs(snapshot, path, file_sha,
        reviewed_at, input_cutoff, book_value_reviews=book)


def refresh_record_binding(snapshot, review, book=None):
    record = review['source_contexts'][CONTEXT_KEY]['source_record']
    snapshot['rows'][0]['owner_source_context']['record_hash'] = digest(record)
    if book is not None:
        book[CONTEXT_KEY]['source_record_hash'] = digest(record)


def test_fourteen_namespaced_raw_values_are_source_copies_and_general_row_is_unchanged(tmp_path):
    snapshot, review, book = source_fixture()
    before = deepcopy(snapshot)
    out, audit = apply(tmp_path, snapshot, review, book=book)
    row = out['rows'][0]
    raw = review['source_contexts'][CONTEXT_KEY]['source_record']['metrics']
    assert snapshot == before
    assert out['rows'][1] == before['rows'][1]
    assert set(row['metrics']) - set(before['rows'][0]['metrics']) == set(financial_catalog())
    assert {key: row['metrics']['financial::' + key] for key in raw} == raw
    assert row['metrics']['financial::dilution_3y'] == 0
    assert row['metrics']['financial::incremental_roe_5y'] < 0
    for key in ('accounting_template', 'sector_id', 'industry_group', 'security_id',
                'gate', 'owner_source_context', 'financial_reference'):
        assert row[key] == before['rows'][0][key]
    assert 'axes' not in row and 'factors' not in row
    assert out['members'] == before['members']
    assert out['evaluation_day'] == before['evaluation_day']
    assert audit


def test_missing_book_review_does_not_inherit_eps_or_dilution_approval(tmp_path):
    snapshot, review, _ = source_fixture()
    out, _ = apply(tmp_path, snapshot, review)
    row = out['rows'][0]
    assert row['metrics']['financial::eps_cagr_3y'] == .09
    assert row['metrics']['financial::dilution_3y'] == 0
    assert row['metrics']['financial::book_value_per_share_cagr_3y'] is None
    assert row['metric_evidence']['financial::book_value_per_share_cagr_3y']['raw_reusable'] is False


def test_source_review_and_new_application_clocks_and_original_anchor_remain_distinct(tmp_path):
    snapshot, review, book = source_fixture()
    out, _ = apply(tmp_path, snapshot, review, book=book)
    _, file_sha = write_review(tmp_path, review)
    row = out['rows'][0]
    for key in financial_catalog():
        proof = row['metric_evidence'][key]
        assert proof['status'] == 'TEMPORARY_OFFICIAL_FINANCIAL_RAW'
        assert proof['financial_temporary_policy'] == 'official-financial-role-bridge/1'
        assert proof['available_at'] == NEW_REVIEW
        assert proof['source_available_at'] == ACQUIRED
        assert proof['retrieved_at'] == ACQUIRED
        assert proof['source_review_created_at'] == OLD_REVIEW
        assert proof['review_file_received_at'] is None
        assert any(f'sha256:{file_sha}#' in ref for ref in proof['source_refs'])
    eps = row['metric_evidence']['financial::eps_cagr_3y']
    assert any('/source_contexts/synthetic~1source~01' in ref for ref in eps['source_refs'])
    assert row['financial_reference']['source_refs'] == snapshot['rows'][0]['financial_reference']['source_refs']


@pytest.mark.parametrize('tamper', ['wrong_digest', 'appended_bytes'])
def test_review_sha_verifies_actual_file_bytes(tmp_path, tamper):
    snapshot, review, _ = source_fixture()
    path, expected = write_review(tmp_path, review)
    if tamper == 'wrong_digest':
        expected = 'c' * 64
    else:
        path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(ValueError):
        apply_temporary_financial_inputs(snapshot, path, expected, NEW_REVIEW, NEW_REVIEW)


@pytest.mark.parametrize('tamper', [
    'context_issuer', 'context_body_sha', 'context_anchor', 'context_acquired',
    'context_fiscal_year', 'context_currency', 'record_digest', 'row_record_hash',
    'row_blob_sha', 'row_companyfacts_sha', 'row_currency', 'duplicate_context',
])
def test_context_binding_tampering_is_rejected(tmp_path, tamper):
    snapshot, review, _ = source_fixture()
    context = review['source_contexts'][CONTEXT_KEY]
    owner = snapshot['rows'][0]['owner_source_context']
    if tamper == 'context_issuer':
        context['issuer_id'] = 'SYN:OTHER'
    elif tamper == 'context_body_sha':
        context['source_sha256'] = 'c' * 64
    elif tamper == 'context_anchor':
        context['source_refs'] = [f'sha256:{"c" * 64}']
    elif tamper == 'context_acquired':
        context['acquired_at'] = '2026-11-03T13:00:00Z'
    elif tamper == 'context_fiscal_year':
        context['fiscal_year_end'] = '2024-12-31'
    elif tamper == 'context_currency':
        context['currency'] = 'EUR'
    elif tamper == 'record_digest':
        context['source_record']['metrics']['roe'] = .13
    elif tamper == 'row_record_hash':
        owner['record_hash'] = 'd' * 64
    elif tamper == 'row_blob_sha':
        owner['source_sha256'] = 'd' * 64
    elif tamper == 'row_companyfacts_sha':
        owner['companyfacts_sha256'] = 'd' * 64
    elif tamper == 'row_currency':
        owner['currency'] = 'EUR'
    else:
        review['source_contexts']['duplicate'] = deepcopy(context)
    with pytest.raises(ValueError):
        apply(tmp_path, snapshot, review)


@pytest.mark.parametrize('tamper', ['old_review_in_future', 'review_before_snapshot',
    'review_after_cutoff', 'source_after_old_review', 'source_after_snapshot'])
def test_source_and_review_clock_order_is_enforced(tmp_path, tamper):
    snapshot, review, _ = source_fixture()
    reviewed_at, input_cutoff = NEW_REVIEW, NEW_REVIEW
    if tamper == 'old_review_in_future':
        review['reviewed_at'] = '2026-11-14T12:00:01Z'
    elif tamper == 'review_before_snapshot':
        reviewed_at = '2026-11-04T11:59:59Z'
    elif tamper == 'review_after_cutoff':
        input_cutoff = '2026-11-14T11:59:59Z'
    elif tamper == 'source_after_old_review':
        review['reviewed_at'] = '2026-11-02T12:00:00Z'
    else:
        context = review['source_contexts'][CONTEXT_KEY]
        acquired = '2026-11-04T12:00:01Z'
        context['acquired_at'] = context['source_record']['acquired_at'] = acquired
        snapshot['rows'][0]['owner_source_context']['acquired_at'] = acquired
        refresh_record_binding(snapshot, review)
    with pytest.raises(ValueError):
        apply(tmp_path, snapshot, review, reviewed_at=reviewed_at, input_cutoff=input_cutoff)


@pytest.mark.parametrize('value', [True, '0.1', float('nan'), float('inf')])
def test_invalid_official_raw_value_is_not_connected(tmp_path, value):
    snapshot, review, _ = source_fixture()
    review['source_contexts'][CONTEXT_KEY]['source_record']['metrics']['roe'] = value
    # Nonfinite values cannot have a canonical record digest. The adapter must
    # reject them before attempting to publish a bound raw observation.
    if type(value) is not float or math.isfinite(value):
        refresh_record_binding(snapshot, review)
    with pytest.raises(ValueError):
        apply(tmp_path, snapshot, review)


@pytest.mark.parametrize('metric', ['eps_cagr_3y', 'dilution_3y', 'book_value_per_share_cagr_3y'])
def test_share_claim_cannot_replace_official_raw_with_different_numeric_value(tmp_path, metric):
    snapshot, review, book = source_fixture()
    claim = book[CONTEXT_KEY]['claim'] if metric == 'book_value_per_share_cagr_3y' else (
        review['source_contexts'][CONTEXT_KEY]['metrics'][metric])
    claim['value'] += .01
    with pytest.raises(ValueError):
        apply(tmp_path, snapshot, review, book=book)


@pytest.mark.parametrize('tamper', ['strict', 'formula', 'denominator', 'reusable_type',
    'evidence_type', 'undisclosed_assumption'])
def test_share_claim_definition_and_assumption_flags_are_not_relabelled(tmp_path, tamper):
    snapshot, review, _ = source_fixture()
    claim = review['source_contexts'][CONTEXT_KEY]['metrics']['eps_cagr_3y']
    if tamper == 'strict':
        claim['strict_verified'] = True
    elif tamper == 'formula':
        claim['formula_variant'] = FORMULAS['dilution_3y']
    elif tamper == 'denominator':
        claim['denominator_definition'] = 'ACTUAL_OUTSTANDING_SHARES'
    elif tamper == 'reusable_type':
        claim['reusable'] = 'true'
    elif tamper == 'evidence_type':
        claim['evidence_only_eligible'] = 'true'
    else:
        claim.update(adoption_basis='OFFICIAL_ASSUMPTION_INHERITED',
            requires_assumption=True, evidence_only_eligible=False, allowed_assumptions=[])
    with pytest.raises(ValueError):
        apply(tmp_path, snapshot, review)


def test_assumption_inherited_claim_preserves_its_limits_per_metric(tmp_path):
    snapshot, review, _ = source_fixture()
    claim = review['source_contexts'][CONTEXT_KEY]['metrics']['eps_cagr_3y']
    claim.update(adoption_basis='OFFICIAL_ASSUMPTION_INHERITED', requires_assumption=True,
        evidence_only_eligible=False, allowed_assumptions=['NO_OVERLAP_FACTOR_ONE'])
    out, _ = apply(tmp_path, snapshot, review)
    proof = out['rows'][0]['metric_evidence']['financial::eps_cagr_3y']
    assert out['rows'][0]['metrics']['financial::eps_cagr_3y'] == .09
    assert proof['raw_reusable'] is True
    assert proof['strict_verified'] is False
    assert proof['requires_assumption'] is True
    assert proof['evidence_only_eligible'] is False
    assert proof['allowed_assumptions'] == ['NO_OVERLAP_FACTOR_ONE']
    assert out['rows'][0]['metric_evidence']['financial::dilution_3y']['requires_assumption'] is False


@pytest.mark.parametrize('field', ['source_record_hash', 'source_body_sha256'])
def test_book_review_has_independent_record_and_companyfacts_binding(tmp_path, field):
    snapshot, review, book = source_fixture()
    book[CONTEXT_KEY][field] = 'c' * 64
    with pytest.raises(ValueError):
        apply(tmp_path, snapshot, review, book=book)


def book_source(split=1):
    """Annual comparative filings connect both book endpoints to the FY0 basis."""
    facts = {}
    filings = {2022: ('old', '2023-02-01'), 2023: ('middle', '2024-02-01'),
        2024: ('new', '2025-02-01'), 2025: ('basis', '2026-02-01')}
    for filing in range(2022, 2026):
        accession, filed = filings[filing]
        for year in range(max(2022, filing - 1), filing + 1):
            factor = split if filing >= 2024 else 1
            for tag, unit, value in (
                ('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', 100 * factor),
                ('EarningsPerShareDiluted', 'USD/shares', 2 / factor),
                ('NetIncomeLoss', 'USD', 200)):
                facts.setdefault(tag, {'units': {}})['units'].setdefault(unit, []).append(
                    dict(val=value, start=f'{year}-01-01', end=f'{year}-12-31',
                         filed=filed, accn=accession, form='10-K'))
    equity = []
    for year, amount in ((2022, 80), (2025, 200)):
        accession, filed = filings[year]
        equity.append(dict(val=amount, end=f'{year}-12-31', filed=filed,
            accn=accession, form='10-K'))
    facts['StockholdersEquity'] = {'units': {'USD': equity}}
    expected = 2.5 ** (1 / 3) - 1
    record = dict(cik='0000000001', acquired_at='2026-02-03T00:00:00Z',
        fiscal_year_end='2025-12-31', currency='USD', profile='FINANCIAL',
        state='LIVE', calc_version=CALC_VERSION,
        metrics={'book_value_per_share_cagr_3y': vf._round(expected)})
    return dict(cik=1, facts={'us-gaap': facts}), record


def book_rows(payload, tag, unit):
    return payload['facts']['us-gaap'][tag]['units'][unit]


def review_book(payload, record):
    return review_official_book_value_history(payload, record, 'SYNTHETIC_ONLY')


def test_book_review_matches_hand_expected_value_without_eps_or_cover_reference():
    payload, record = book_source()
    del payload['facts']['us-gaap']['EarningsPerShareDiluted']
    before = deepcopy(payload)
    claim = review_book(payload, record)
    assert payload == before
    assert claim['value'] == vf._round(2.5 ** (1 / 3) - 1)
    assert claim['unrounded_value'] == pytest.approx(2.5 ** (1 / 3) - 1)
    assert claim['reusable'] and claim['evidence_only_eligible']
    assert claim['adoption_basis'] == 'EVIDENCE_LINKED'
    assert claim['formula_variant'] == BOOK_FORMULA
    assert claim['denominator_definition'] == 'WEIGHTED_AVERAGE_DILUTED_SHARES'
    assert claim['strict_verified'] is False and claim['common_attribution_confirmed'] is False
    assert {x['status'] for x in claim['cover_scale_diagnostics']} == {'NO_REFERENCE'}
    assert not claim['valuation_price_identity_verified']
    assert len([p for p in claim['periods'] if p['item'] == 'equity']) == 2


def test_book_review_cover_scale_error_blocks_its_own_reuse():
    payload, record = book_source()
    payload['facts']['dei'] = {'EntityCommonStockSharesOutstanding': {'units': {'shares': [
        dict(val=100000000, end='2025-12-31', filed='2026-02-01',
             accn='basis', form='10-K')]}}}
    claim = review_book(payload, record)
    assert claim['value'] is None and not claim['reusable']
    assert claim['adoption_basis'] == 'ADDITIONAL_VERIFICATION_REQUIRED'
    assert 'SHARES_SCALE_UNCONFIRMED' in claim['blocking_reasons']


@pytest.mark.parametrize('tag,unit', [
    ('StockholdersEquity', 'USD'),
    ('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares'),
])
def test_book_review_same_filing_equity_or_share_conflict_is_excluded(tag, unit):
    payload, record = book_source()
    rows = book_rows(payload, tag, unit)
    original = next(row for row in rows if row['accn'] == 'basis' and row['end'] == '2025-12-31')
    rows.append(dict(original, val=999))
    claim = review_book(payload, record)
    assert claim['value'] is None and not claim['reusable']
    assert claim['adoption_basis'] == 'EXPLICIT_CONFLICT_EXCLUDED'
    assert any(reason.startswith('LATEST_FILING_CONFLICT:') for reason in claim['blocking_reasons'])


@pytest.mark.parametrize('equity', [0, -80])
def test_book_review_nonpositive_equity_is_not_a_positive_endpoint_cagr(equity):
    payload, record = book_source()
    book_rows(payload, 'StockholdersEquity', 'USD')[0]['val'] = equity
    claim = review_book(payload, record)
    assert claim['value'] is None and not claim['reusable']
    assert 'EQUITY_ENDPOINT_NOT_POSITIVE' in claim['blocking_reasons']


def test_book_review_unconfirmed_split_does_not_borrow_eps_or_dilution_approval():
    payload, record = book_source(split=2)
    claim = review_book(payload, record)
    assert claim['value'] is None and not claim['reusable']
    assert claim['adoption_basis'] == 'EXPLICIT_CONFLICT_EXCLUDED'


def test_book_review_disconnected_factor_one_remains_an_explicit_assumption():
    payload, record = book_source()
    for node in payload['facts']['us-gaap'].values():
        for rows in node['units'].values():
            rows[:] = [row for row in rows if int(row['end'][:4]) == int(row['filed'][:4]) - 1]
    claim = review_book(payload, record)
    assert claim['value'] == vf._round(2.5 ** (1 / 3) - 1)
    assert claim['reusable'] and claim['requires_assumption']
    assert claim['adoption_basis'] == 'OFFICIAL_ASSUMPTION_INHERITED'
    assert not claim['evidence_only_eligible']
    assert 'OFFICIAL_NO_OVERLAP_NO_REPORTED_SPLIT_FACTOR_ONE' in claim['allowed_assumptions']
