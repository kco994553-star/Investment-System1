"""Offline 555 adapter for the owner-approved central weighted-diluted V variant.

The caller authenticates/hash-checks files before passing these objects. This
module reuses the old financial normalizer and raw V kernel; no pricing, share
reconstruction, percentile computation or type-dependent normalization lives here.
"""
from copy import deepcopy
from datetime import date
import re
from zoneinfo import ZoneInfo

from ..qgv import qgv2_inputs, qgv_v2
from ..qgv.dcf_parameters import load_default_dcf_parameters
from .sector_qgv import digest, timestamp

ADAPTER = 'held-555-central-wad/1'
SHARE_BASIS = 'WEIGHTED_AVERAGE_DILUTED'
METRICS = ('ebit_yield', 'fcf_yield', 'own_history', 'gap')
STATUSES = ('TRADED', 'NO_TRADE', 'NOT_IN_FILE', 'INELIGIBLE')
NY = ZoneInfo('America/New_York')


def _stamp(value, code):
    try:
        return timestamp(value)
    except (AttributeError, TypeError, ValueError):
        raise ValueError(code) from None


def _refs(value):
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x for x in value)


def _price(quote, row, evaluation_day, cutoff, reviewed):
    """retrieved_at means completed acquisition, never the trade timestamp."""
    if quote.get('provider') != 'IEX_HIST' or quote.get('price_definition') != 'IEX_LAST_REGULAR_SESSION_TRADE':
        raise ValueError('CENTRAL_PRICE_PROVIDER_OR_DEFINITION')
    if quote.get('status') not in STATUSES:
        raise ValueError('CENTRAL_PRICE_STATUS')
    if quote.get('company_id') != row['company_id'] or quote.get('issuer_id') != row.get('issuer_id'):
        raise ValueError('CENTRAL_PRICE_IDENTITY')
    if quote.get('trade_day') != evaluation_day:
        raise ValueError('CENTRAL_PRICE_DAY')
    acquired = _stamp(quote.get('retrieved_at'), 'CENTRAL_PRICE_ACQUISITION_TIME')
    if acquired > reviewed or acquired > cutoff:
        raise ValueError('CENTRAL_PRICE_AFTER_CUTOFF')
    if not _refs(quote.get('source_refs')):
        raise ValueError('CENTRAL_PRICE_SOURCE')
    # Acquisition failure/no trade is not a valid numerical zero. Keep the exact
    # status without asking for a nonexistent trade timestamp or a price.
    if quote['status'] != 'TRADED':
        if quote.get('price') is not None:
            raise ValueError('CENTRAL_NONTRADE_HAS_PRICE')
        return acquired
    trade = _stamp(quote.get('traded_at'), 'CENTRAL_PRICE_TRADE_TIME')
    if trade > acquired or trade.astimezone(NY).date().isoformat() != evaluation_day:
        raise ValueError('CENTRAL_PRICE_TRADE_DAY_OR_TIME')
    if not isinstance(quote.get('currency'), str) or not re.fullmatch(r'[A-Z]{3}', quote['currency']):
        raise ValueError('CENTRAL_PRICE_CURRENCY')
    if not qgv_v2.positive(quote.get('price')) or quote.get('price_basis') != 'AS_TRADED':
        raise ValueError('CENTRAL_PRICE_BASIS')
    if (quote.get('security_basis_status') != 'VERIFIED' or
        quote.get('corporate_action_basis_status') != 'VERIFIED' or
        not _refs(quote.get('basis_evidence_refs'))):
        raise ValueError('CENTRAL_PRICE_CLASS_OR_ACTIONS_UNVERIFIED')
    if quote.get('share_basis', SHARE_BASIS) != SHARE_BASIS:
        raise ValueError('CENTRAL_PRICE_SHARE_BASIS')
    return acquired


def _history(quote, evaluation_day):
    closes = quote.get('month_closes')
    if not closes:
        return None, 'PRICE_HISTORY_NOT_LINKED'
    if (quote.get('history_basis_status') != 'VERIFIED' or
        quote.get('history_share_basis') != SHARE_BASIS or
        not _refs(quote.get('history_source_refs'))):
        return None, 'HISTORY_PRICE_SHARE_BASIS_UNVERIFIED'
    if not isinstance(closes, dict):
        raise ValueError('CENTRAL_HISTORY_FORMAT')
    for month, value in closes.items():
        if (not isinstance(month, str) or not re.fullmatch(r'\d{4}-\d{2}', month) or
            not qgv_v2.positive(value)):
            raise ValueError('CENTRAL_HISTORY_FORMAT')
        try:
            date.fromisoformat(month+'-01')
        except ValueError:
            raise ValueError('CENTRAL_HISTORY_FORMAT') from None
        # A bare YYYY-MM close has no exact trade timestamp. Only completed
        # prior months can be proven usable at this evaluation day.
        if month >= evaluation_day[:7]:
            raise ValueError('CENTRAL_HISTORY_FUTURE')
    return deepcopy(closes), None


def bind_central_prices(snapshot, financial_records, price_rows, reviewed_at, input_cutoff, parameters=None):
    """Return (new snapshot, audit); never modify the provided source objects.

    financial_records = {company_id: {record: original calc23.1 row,
                                      source_refs: [pinned source locator]}}.
    price_rows is a list of previously authenticated/validated source mappings:
    company_id, issuer_id, status, trade_day, retrieved_at (collection complete),
    source_refs, provider=IEX_HIST, price_definition=IEX_LAST_REGULAR_SESSION_TRADE;
    TRADED additionally requires price, currency, traded_at,
    price_basis=AS_TRADED, VERIFIED security/action statuses and
    basis_evidence_refs. No invented fixed security ID is required when reviewed
    same-security documentary mapping exists. Optional month_closes needs a
    separately verified WAD history basis and completed prior months only.
    The caller must not call a title or
    ticker string alone a reviewed identity mapping.
    """
    evaluation_day = snapshot['evaluation_day']
    try:
        date.fromisoformat(evaluation_day)
    except (TypeError, ValueError):
        raise ValueError('CENTRAL_EVALUATION_DAY') from None
    reviewed = _stamp(reviewed_at, 'CENTRAL_REVIEW_TIME')
    cutoff = _stamp(input_cutoff, 'CENTRAL_INPUT_CUTOFF')
    if not _stamp(snapshot['input_cutoff'], 'CENTRAL_ORIGINAL_CUTOFF') <= reviewed <= cutoff:
        raise ValueError('CENTRAL_REVIEW_TIME')
    out = deepcopy(snapshot); out['input_cutoff'] = input_cutoff
    rows = {r['company_id']: r for r in out['rows']}
    if len(rows) != len(out['rows']):
        raise ValueError('CENTRAL_DUPLICATE_MEMBER')
    prices = {}
    for quote in price_rows:
        cid = quote.get('company_id')
        if cid not in rows or cid in prices:
            raise ValueError('CENTRAL_PRICE_MEMBER')
        prices[cid] = quote
    params = load_default_dcf_parameters() if parameters is None else deepcopy(parameters)
    audit = []
    for cid, row in rows.items():
        entry = dict(company_id=cid, issuer_id=row.get('issuer_id'),
                     source_state='NOT_EVALUATED', price_status='NOT_IN_FILE',
                     raw_values={m: None for m in METRICS}, reasons={},
                     share_basis=SHARE_BASIS, adopted_metrics=[])
        # No stale metric from a previous price set survives an incomplete update.
        for key in METRICS:
            row.setdefault('metrics', {}).pop('central::'+key, None)
            row.setdefault('metric_evidence', {}).pop('central::'+key, None)
        quote = prices.get(cid)
        if quote is not None:
            _price(quote, row, evaluation_day, cutoff, reviewed)
            entry.update(price_status=quote['status'], price_trade_at=quote.get('traded_at'),
                         price_acquired_at=quote['retrieved_at'], price_record_hash=digest(quote),
                         price_source_refs=deepcopy(quote['source_refs']))
        wrapped = financial_records.get(cid)
        context = row.get('owner_source_context') or {}
        if not wrapped:
            entry['source_state'] = 'RETAINED_FINANCIAL_NOT_LINKED'
            audit.append(entry); continue
        if not context:
            entry['source_state'] = 'OWNER_SOURCE_CONTEXT_MISSING'
            audit.append(entry); continue
        record = wrapped['record']
        if (record.get('calc_version') != 'qgv2-calc/2026-10-23.1' or
            digest(record) != context.get('record_hash') or
            record.get('cik') != row.get('issuer_id') or
            any(context.get(k) != record.get(k) for k in
                ('acquired_at', 'fiscal_year_end', 'currency', 'calc_version')) or
            not _refs(wrapped.get('source_refs'))):
            raise ValueError('CENTRAL_SOURCE_CONTEXT_MISMATCH')
        financial_at = _stamp(record.get('acquired_at'), 'CENTRAL_FINANCIAL_ACQUISITION_TIME')
        if financial_at > reviewed:
            raise ValueError('CENTRAL_FINANCIAL_AFTER_CUTOFF')
        entry['source_state'] = 'PINNED_RETAINED_FINANCIAL'
        if quote is None:
            entry['reasons'] = {m:'NOT_IN_FILE' for m in METRICS}
            audit.append(entry); continue
        if quote['status'] != 'TRADED':
            entry['reasons'] = {m:quote['status'] for m in METRICS}
            audit.append(entry); continue
        normalized, periods = qgv2_inputs._v_inputs(record.get('v_inputs_v2'))
        if (record.get('currency') and quote.get('currency') != record['currency']) or (normalized is not None and quote.get('currency') != normalized.get('currency')):
            raise ValueError('CENTRAL_PRICE_CURRENCY')
        closes, history_reason = _history(quote, evaluation_day)
        converted_quote = dict(price=quote['price'], currency=quote.get('currency'))
        if closes is not None:converted_quote['month_closes'] = closes
        # Fixed reported-flow version; Lynch tags/type weights cannot choose
        # normalized earnings or a different calculation for individual issuers.
        values = qgv_v2._metrics(dict(profile=record.get('profile'), v_inputs=normalized),
                                converted_quote, params, cyclical_years=None)
        entry.update(raw_values={m:values[m] for m in METRICS}, reasons=deepcopy(values['reasons']),
                     normalized_periods=deepcopy(periods), earnings_basis=values['earnings_basis'],
                     history_connection_reason=history_reason,
                     source_record_hash=context['record_hash'])
        all_refs = [*wrapped['source_refs'], *quote['source_refs'], *quote['basis_evidence_refs']]
        for metric in METRICS:
            value = values[metric]
            if value is None:continue
            name = 'central::'+metric
            row['metrics'][name] = value
            refs = [*all_refs, *(quote.get('history_source_refs', []) if metric == 'own_history' else [])]
            row['metric_evidence'][name] = dict(status='VERIFIED',
                variant=metric+'/central-wad-reported-1', source_refs=list(dict.fromkeys(refs)),
                available_at=reviewed_at, retrieved_at=quote['retrieved_at'], reviewed_at=reviewed_at,
                valuation_day=evaluation_day, share_basis=SHARE_BASIS,
                share_basis_label='기간 가중평균 희석 주식수 · 실제 종류별 발행주식수 아님',
                security_and_actions='VERIFIED', source_record_hash=context['record_hash'],
                normalized_periods=deepcopy(periods), price_trade_at=quote['traded_at'],
                price_acquired_at=quote['retrieved_at'], source_financial_acquired_at=record['acquired_at'],
                adapter_version=ADAPTER, dcf_parameters_hash=digest(params), earnings_basis='REPORTED')
            entry['adopted_metrics'].append(name)
        audit.append(entry)
    out['central_v_context'] = dict(adapter_version=ADAPTER, original_input_hash=digest(snapshot),
        reviewed_at=reviewed_at, input_cutoff=input_cutoff, evidence_hash=digest(audit),
        share_basis=SHARE_BASIS, dcf_parameters_hash=digest(params),
        no_actual_capital_claim=True, historical_system_pit_complete=False)
    return out, audit
