"""Provider-truthful KIS RAW month closes for the existing calc23.1 V4 kernel.

No collection, scoring or verification upgrade. Callers must opt in and bind the
financial payload independently. Dates/declared F_k remain the old kernel's
inputs; missing evidence is never replaced by 1 or by another month's price.
"""
from calendar import monthrange
from datetime import date,timedelta

from ..providers.iex_monthend import _factor, MONTHEND_BASIS_CUTS
from ..qgv.qgv_v2 import positive
from . import pit_filings
from ._private_artifacts import digest
from .kis_price_bridge import _day,_ts,validate_contract

POLICY = 'kis-v4-month-close/1'


def _last_session(month):
    y,m=map(int,month.split('-'))
    end=date(y,m,monthrange(y,m)[1])
    while not pit_filings.is_session(end):end-=timedelta(days=1)
    return end.isoformat()


def kis_month_closes(contract, raw_history, *, company_code, evaluation_day,
                     expected_contract_hash, expected_query, available_at=None):
    """Return (month closes on the financial F_k basis, private diagnostics).

    expected_query is the existing pinned provider lookup {symb, excd}. This is
    source association, not a newly verified fixed security identity. Output
    diagnostics contain source pointers and hashes, not copied price values.
    """
    if digest(contract)!=expected_contract_hash:raise ValueError('V4_CONTRACT_PIN_MISMATCH')
    validate_contract(contract);_day(evaluation_day)
    query=contract.get('source_query') or {}
    if (query.get('MODP')!='0' or query.get('GUBN')!='0' or
        contract.get('source')!='KIS retained dailyprice MODP0' or
        contract.get('publication_scope')!='OWNER_PRIVATE_ONLY'):
        raise ValueError('V4_KIS_RAW_MODP0_REQUIRED')
    if query.get('SYMB')!=expected_query.get('symb') or query.get('EXCD')!=expected_query.get('excd'):
        raise ValueError('V4_QUERY_IDENTITY_CONFLICT')
    if available_at is not None and _ts(contract['collected_at'])>_ts(available_at):
        raise ValueError('V4_SOURCE_NOT_YET_AVAILABLE')
    bars={row['date']:row for row in contract['raw_bars']}
    closes={};observations=[];cut=MONTHEND_BASIS_CUTS.get(company_code)
    for item in raw_history if isinstance(raw_history,list) else ():
        fy=item.get('fiscal_year_end') if isinstance(item,dict) else None
        row=dict(fiscal_year_end=fy)
        try:
            _day(fy)
        except (TypeError,ValueError):
            row['reason']='INVALID_FY_DATE';observations.append(row);continue
        month=fy[:7];row['month']=month
        if cut and fy<cut[0]:row['reason']=cut[1]
        else:
            factor,reason=_factor(item)
            if factor is None:row['reason']=reason
            # A monthly close without an exact future-free trade day must not
            # enter an unfinished current month, even if a partial bar exists.
            elif month>=evaluation_day[:7]:row['reason']='INCOMPLETE_OR_FUTURE_MONTH'
            else:
                try:trade_day=_last_session(month)
                except pit_filings.CalendarNotConfigured:
                    row['reason']='CALENDAR_NOT_CONFIGURED';observations.append(row);continue
                bar=bars.get(trade_day);row['expected_session']=trade_day
                if any(r['from']<=trade_day<=r['to'] for r in contract['held_ranges']):
                    row['reason']='HISTORICAL_PRICE_HELD'
                elif bar is None or bar.get('close') is None:
                    row['reason']='EXACT_MONTH_END_SESSION_NOT_RETAINED'
                elif not positive(float(bar['close'])):
                    row['reason']='NONPOSITIVE_MONTH_CLOSE'
                else:
                    # The old V-PRICE-BASIS operation, applied to a KIS price.
                    closes[month]=float(bar['close'])/factor
                    row.update(reason='CONNECTED_KIS_MONTH_CLOSE',trade_day=trade_day,
                        share_basis_factor=factor,source_bar_sha256=bar['source_sha256'],
                        source_bar_record_hash=digest(bar),financial_history_item_hash=digest(item))
        observations.append(row)
    # The old kernel indexes closes by calendar month. Two fiscal entries
    # cannot borrow one another's normalization when their F_k differs (or one
    # basis is unknown): the month has no unambiguous shared price basis.
    by_month={}
    for item in raw_history if isinstance(raw_history,list) else ():
        if isinstance(item,dict) and isinstance(item.get('fiscal_year_end'),str):
            by_month.setdefault(item['fiscal_year_end'][:7],set()).add(_factor(item)[0])
    conflicts={month for month,bases in by_month.items() if len(bases)>1}
    for month in conflicts:closes.pop(month,None)
    for row in observations:
        if row.get('month') in conflicts:row['reason']='CONFLICTING_FISCAL_MONTH_BASIS'
    return closes,dict(policy=POLICY,provider='KIS',price_basis='RAW_MODP0',
        rule='EXISTING_CALC23_1_RAW_DIVIDED_BY_SHARE_BASIS_FACTOR',
        source_contract_hash=expected_contract_hash,financial_history_hash=digest(raw_history),
        source_query=dict(query),source_collected_at=contract['collected_at'],
        calculation_cutoff=available_at,evaluation_day=evaluation_day,
        validation_tier='UNVERIFIED_REFERENCE',historical_pit_proven=False,
        observations=observations)
