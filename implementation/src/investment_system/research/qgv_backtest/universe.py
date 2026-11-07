"""Dated listing/issuer, capitalization and standalone-factor input adapters.

This module consumes authorized local observations, not today's ticker lists.
Unavailable evidence fails closed; it never substitutes FFO, a 6-K quarterly
recipe, diluted EPS shares for issued shares, or an assumed ADR ratio/currency.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median
from zoneinfo import ZoneInfo

from .calendar_adapter import aware, day
from .extensions import ACTIVE_FACTORS, GROUPS, finite
from .pit_adapter import _price_index, _visible


@dataclass(frozen=True)
class UniverseView:
    group: str
    identities: dict
    membership: tuple
    exclusions: dict
    floor_usd: float | None


def _evidence(row, decision):
    return (bool(row.get('source')) and bool(row.get('receipt')) and row.get('known_at') is not None
            and _visible(row, decision))


def _latest(rows, signal, decision, *, effective='effective_date'):
    eligible = []
    for row in rows:
        if not _evidence(row, decision):
            continue
        effective_day = day(row[effective])
        if effective_day <= signal:
            eligible.append((effective_day, aware(row['known_at']), row))
    if not eligible:
        return None
    key = max((a,b) for a,b,_ in eligible)
    winners = [row for a,b,row in eligible if (a,b) == key]
    if any(row != winners[0] for row in winners):
        raise ValueError('CONFLICTING_PIT_OBSERVATIONS')
    return winners[0]


def adr_bridge(bundle, sid, signal, decision):
    bridge = _latest([r for r in bundle.get('adr_bridges', []) if r.get('security_id') == sid], signal, decision)
    if (not bridge or not finite(bridge.get('ordinary_per_adr')) or bridge['ordinary_per_adr'] <= 0
            or not bridge.get('financial_currency')):
        raise ValueError('ADR_BRIDGE_UNVERIFIED')
    return bridge


def _cap(bundle, issuer, types, signal, decision, prices):
    row = _latest([r for r in bundle.get('capitalization', []) if r.get('issuer_id') == issuer], signal, decision)
    if not row or not row.get('components'):
        raise ValueError('MISSING_ISSUED_SHARE_CAPITALIZATION')
    total, seen = 0.0, set()
    for component in row['components']:
        sid = component['security_id']
        class_id = component.get('class_id', sid)
        if class_id in seen:
            raise ValueError('DUPLICATE_ECONOMIC_SHARE_CLASS')
        seen.add(class_id)
        shares = component.get('issued_shares')
        if component.get('share_basis') != 'ISSUED_ORDINARY' or not finite(shares) or shares <= 0:
            raise ValueError('ISSUED_ORDINARY_SHARES_REQUIRED')
        price = prices.get((sid, signal), {})
        if price.get('currency') != 'USD' or price.get('price_basis') != 'RAW' or not finite(price.get('close')) or price['close'] <= 0:
            raise ValueError('CURRENT_RAW_USD_CAP_PRICE_REQUIRED')
        ratio = adr_bridge(bundle, sid, signal, decision)['ordinary_per_adr'] if types.get(sid) == 'ADR' else 1
        total += shares * price['close'] / ratio
    return total


def build_universe_view(bundle, group, signal, calendar):
    signal = day(signal)
    if group not in GROUPS:
        raise ValueError('UNKNOWN_RESEARCH_GROUP')
    decision = calendar.session(signal).close_at
    coverage = bundle.get('universe_coverage', {})
    if (coverage.get('complete') is not True or coverage.get('delistings_included') is not True
            or not coverage.get('source') or not coverage.get('receipt')
            or coverage.get('start', '9999') > str(signal) or coverage.get('end', '') < str(signal)):
        raise ValueError('HISTORICAL_UNIVERSE_COVERAGE_UNVERIFIED')
    master, exclusions = {}, {}
    for sid in sorted({r['security_id'] for r in bundle.get('security_master', [])}):
        rows = [r for r in bundle['security_master'] if r['security_id'] == sid]
        record = _latest(rows, signal, decision, effective='start')
        potentially_active=any(day(r['start'])<=signal and (r.get('end') is None or signal<day(r['end'])) for r in rows)
        if record is None and potentially_active:
            # A completeness receipt cannot turn an unverified current member
            # into a genuine non-member. Never shrink the percentile universe.
            raise ValueError('IDENTITY_PIT_COVERAGE_UNVERIFIED')
        if record and (record.get('end') is None or signal < day(record['end'])):
            if record.get('security_type') is None:
                raise ValueError('IDENTITY_PIT_COVERAGE_UNVERIFIED')
            if not record.get('issuer_id') or not str(record.get('cik', '')).isdigit():
                raise ValueError('ECONOMIC_ISSUER_MAPPING_UNVERIFIED')
            master[sid] = dict(record)
    if not master:
        raise ValueError('MISSING_DATED_SECURITY_MASTER')
    types = {sid:r.get('security_type') for sid,r in master.items()}
    if group == 'U-SPX-HIST':
        members = {r['security_id'] for r in bundle['membership'] if day(r['start']) <= signal
                   and (r.get('end') is None or signal < day(r['end'])) and _visible(r, decision)}
        if members - master.keys():
            raise ValueError('SPX_IDENTITY_COVERAGE_UNVERIFIED')
    else:
        members = set(master)
    floor = None
    if group == 'U-BOOK200':
        reference = bundle.get('cpi_2009_annual', {})
        cpi = _latest(bundle.get('cpi', []), signal, decision, effective='period_end')
        if (not reference.get('source') or not reference.get('receipt') or not finite(reference.get('value'))
                or reference['value'] <= 0 or not cpi or not finite(cpi.get('value')) or cpi['value'] <= 0):
            raise ValueError('CPI_VINTAGE_UNVERIFIED')
        floor = 200000000 * cpi['value'] / reference['value']
    prices = _price_index(bundle['prices'], signal, decision_at=decision)
    groups = {}
    for sid in sorted(members):
        row = master[sid]
        if row.get('security_type') not in ('COMMON', 'ADR', 'REIT'):
            exclusions[sid] = 'INELIGIBLE_SECURITY_TYPE'
            continue
        groups.setdefault(row['issuer_id'], []).append(row)
    identities, membership = {}, []
    sessions = calendar.completed_sessions(signal, 60)
    for issuer, classes in sorted(groups.items()):
        liquidity = {}
        for identity in classes:
            values = []
            for session in sessions:
                price = prices.get((identity['security_id'], session.day), {})
                value = price.get('dollar_volume')
                if value is None and finite(price.get('close')) and finite(price.get('volume')):
                    value = price['close'] * price['volume']
                if finite(value) and value >= 0:
                    values.append(value)
            if len(sessions) == len(values) == 60:
                liquidity[identity['security_id']] = median(values)
        confirmed = len(liquidity) == len(classes)
        identity = min(classes, key=lambda r: (-liquidity[r['security_id']], r['security_id']) if confirmed else (0, r['security_id']))
        sid = identity['security_id']
        cap = None
        if group == 'U-BOOK200' or any(r.get('issuer_id') == issuer for r in bundle.get('capitalization', [])):
            cap = _cap(bundle, issuer, types, signal, decision, prices)
        if floor is not None and cap < floor:
            exclusions[sid] = 'BELOW_REAL_CAP_FLOOR'
            continue
        identity = dict(identity, cik=str(identity['cik']).zfill(10), market_cap_usd=cap,
                        currency='USD', liquidity_confirmed=confirmed)
        quote=prices.get((sid,signal),{})
        if quote.get('currency')=='USD' and finite(quote.get('close')) and quote['close']>0:
            ratio=adr_bridge(bundle,sid,signal,decision)['ordinary_per_adr'] if identity['security_type']=='ADR' else 1
            identity['ordinary_price_usd']=quote['close']/ratio
        identities[sid] = identity
        # Preserve the dated choice and identity, rather than letting a later
        # price or different CIK for an ADR choose the representative again.
        membership.append(dict(identity, start=str(signal), end=None))
        for other in classes:
            if other['security_id'] != sid:
                exclusions[other['security_id']] = 'DUPLICATE_ECONOMIC_ISSUER'
    return UniverseView(group, identities, tuple(membership), exclusions, floor)


def validate_adr_distributions(bundle,identities,signal):
    """An unknown ADR fee or tax basis is unavailable data, not a zero fee.

    Legacy ordinary dividends retain their contract. ADR records must state
    gross-before-withholding cash and an explicitly attested fee, including0.
    """
    adrs={sid for sid,row in identities.items() if row.get('security_type')=='ADR'}
    for event in bundle.get('events',[]):
        if event.get('security_id') not in adrs or event.get('type')!='DIVIDEND' or day(event['effective_date'])<day(signal):
            continue
        fee=event.get('depositary_fee_per_share')
        if (not finite(fee) or fee<0 or not event.get('depositary_fee_receipt')
                or event.get('cash_amount_basis')!='GROSS_BEFORE_WITHHOLDING' or not event.get('distribution_receipt')):
            raise ValueError('ADR_DISTRIBUTION_EVIDENCE_UNVERIFIED')


def adjust_valuation_quotes(bundle, identities, rows, quotes, signal, calendar):
    """Bridge ADR USD quotes to ordinary-share financial units for QGV only.

    The ledger continues to trade the original USD instrument. Every historical
    monthly quote needs its own dated bridge; absent history stays NA.
    """
    signal = day(signal)
    decision = calendar.session(signal).close_at
    result, reasons = {}, {}
    for sid, quote in quotes.items():
        if sid not in identities:
            continue
        currency = rows[sid].get('currency')
        is_adr = identities[sid].get('security_type') == 'ADR'
        if not is_adr and currency == 'USD':
            result[sid] = quote
            continue
        if not is_adr:
            reasons[sid] = 'NON_USD_ORDINARY_FX_BRIDGE_UNSUPPORTED'
            continue
        def factor(at):
            bridge = adr_bridge(bundle, sid, at, decision)
            if bridge['financial_currency'] != currency:
                raise ValueError('ADR_FINANCIAL_CURRENCY_MISMATCH')
            fx = bridge.get('usd_per_financial_unit')
            if not finite(fx) or fx <= 0:
                raise ValueError('ADR_FX_UNVERIFIED')
            if currency != 'USD' and (bridge.get('fx_date') != str(at) or not bridge.get('fx_receipt')):
                raise ValueError('ADR_FX_UNVERIFIED')
            if currency == 'USD' and fx != 1:
                raise ValueError('ADR_FX_UNVERIFIED')
            return 1 / bridge['ordinary_per_adr'] / fx
        try:
            multiplier = factor(signal)
        except ValueError as exc:
            reasons[sid] = str(exc)
            continue
        history = {}
        for month, value in quote.get('month_closes', {}).items():
            candidates = [s.day for s in calendar.sessions if s.day.strftime('%Y-%m') == month and s.day <= signal]
            if candidates:
                try:
                    history[month] = value * factor(max(candidates))
                except ValueError:
                    pass
        result[sid] = dict(quote, price=quote['price']*multiplier, currency=currency, month_closes=history)
    return result, reasons


def factor_values(bundle, identities, signal, calendar=None):
    """Six preregistered recipes on explicit PIT raw amounts; no book claim.

    Monetary inputs are USD-normalized with source/FX receipts and one complete
    trailing year. Equity and issued-share capitalization are as-of balances.
    F14 requires exactly 253 consecutive verified total-return closes.
    """
    from datetime import datetime, time, timezone
    signal = day(signal)
    decision = calendar.session(signal).close_at if calendar else datetime.combine(signal, time.max, timezone.utc)
    values, reasons = {f:{} for f in ACTIVE_FACTORS}, {f:{} for f in ACTIVE_FACTORS}
    by_security,financials_by_security={},{}
    for observation in bundle['prices']:
        by_security.setdefault(observation.get('security_id'),[]).append(observation)
    for observation in bundle.get('factor_inputs',[]):
        financials_by_security.setdefault(observation.get('security_id'),[]).append(observation)
    for sid, identity in identities.items():
        raw = _latest([r for r in financials_by_security.get(sid,[]) if r.get('security_id') == sid
                       and r.get('filed', '9999') < str(signal)], signal, decision)
        base_reason = 'MISSING_PIT_FACTOR_INPUT'
        chronology=False
        if raw is not None:
            try:
                filed=day(raw['filed'])
                available=aware(raw['known_at']).astimezone(ZoneInfo('America/New_York')).date()
                chronology=day(raw['period_start'])<=day(raw['period_end'])<=filed<=available and filed<signal
            except (KeyError,ValueError,TypeError):
                pass
            if not chronology:
                base_reason='INVALID_FACTOR_CHRONOLOGY'
        cap = identity.get('market_cap_usd')
        valid = bool(raw and chronology and raw.get('currency') == 'USD' and finite(cap) and cap > 0
                     and raw.get('period_end', '9999') < str(signal))
        if valid:
            try:
                duration = (day(raw['period_end']) - day(raw['period_start'])).days
                valid = 330 <= duration <= 380 and (day(raw['effective_date']) <= signal)
                if raw.get('original_currency', 'USD') != 'USD' and not raw.get('fx_receipt'):
                    valid = False
            except (KeyError, ValueError, TypeError):
                valid = False
        amounts = raw.get('values', {}) if valid else {}
        def have(*keys):
            return all(finite(amounts.get(k)) for k in keys)
        if valid:
            eps=amounts.get('trailing_eps')
            ordinary_price=identity.get('ordinary_price_usd')
            if (have('trailing_eps') and eps>0 and finite(ordinary_price) and ordinary_price>0
                    and raw.get('eps_share_basis')=='ORDINARY_USD_ASOF_SIGNAL' and raw.get('eps_price_basis_receipt')):
                values['F03'][sid]=ordinary_price/eps
            else:
                reasons['F03'][sid]='NONPOSITIVE_EPS' if have('trailing_eps') and eps<=0 else 'EPS_PRICE_BASIS_UNVERIFIED'
            for f,key in (('F07','equity'),('F06','sales_ttm')):
                if have(key) and amounts[key] > 0:
                    values[f][sid] = cap / amounts[key]
                else:
                    reasons[f][sid] = 'NONPOSITIVE_DENOMINATOR' if have(key) else 'MISSING_RAW_COMPONENT'
            if have('ebitda_ttm','debt','cash','preferred_equity','minority_interest'):
                ev = cap + amounts['debt'] + amounts['preferred_equity'] + amounts['minority_interest'] - amounts['cash']
                if ev > 0:
                    values['F04'][sid] = amounts['ebitda_ttm'] / ev
                else:
                    reasons['F04'][sid] = 'NONPOSITIVE_EV'
            else:
                reasons['F04'][sid] = 'MISSING_RAW_COMPONENT'
            if have('cash_dividends_ttm','buybacks_ttm','issuance_ttm'):
                values['F10'][sid] = (amounts['cash_dividends_ttm']+amounts['buybacks_ttm']-amounts['issuance_ttm']) / cap
            else:
                reasons['F10'][sid] = 'MISSING_RAW_COMPONENT'
        else:
            for f in ACTIVE_FACTORS:
                reasons[f][sid] = base_reason
        history = [r for r in by_security.get(sid,[]) if day(r['date']) <= signal
                   and _visible(r, decision) and r.get('total_return_verified') is True
                   and r.get('total_return_receipt') and finite(r.get('total_return_index')) and r['total_return_index'] > 0]
        keyed = {r['date']:r for r in history}
        expected = [str(s.day) for s in calendar.completed_sessions(signal,253)] if calendar else []
        if len(expected) == 253 and all(d in keyed for d in expected):
            values['F14'][sid] = keyed[expected[-1]]['total_return_index'] / keyed[expected[0]]['total_return_index'] - 1
            reasons['F14'].pop(sid, None)
        else:
            reasons['F14'][sid] = 'MISSING_253_VERIFIED_TOTAL_RETURN_CLOSES'
    return values, reasons
