"""Decimal self-financing event ledger for the isolated QGV research path.

Prices must be unadjusted prices in the same currency/share basis as positions.
Call corporate events before that session's open, then mark with that session's
close. This module never caches prices or infers corporate settlement terms.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_DOWN, localcontext
from functools import wraps
from typing import Mapping, Sequence


class LedgerError(ValueError):
    """An invalid input, chronology, or incomplete valuation blocks an action."""


def _decimal(value, name, *, positive=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise LedgerError(f'INVALID_{name}') from exc
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise LedgerError(f'INVALID_{name}')
    return result


def _date(value):
    if type(value) is not date:
        raise LedgerError('SESSION_MUST_BE_DATE')
    return value


def _security(value):
    if not isinstance(value, str) or not value.strip():
        raise LedgerError('INVALID_SECURITY_ID')
    return value


def _precision(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        with localcontext() as context:
            context.prec = 50
            context.rounding = ROUND_DOWN
            return method(*args, **kwargs)
    return wrapped


def _sum_exact(values):
    """Add finite decimal cash amounts without losing the last available cent/ulp."""
    values = tuple(values)
    if not values:
        return Decimal(0)
    with localcontext() as context:
        context.prec = max(value.adjusted() for value in values) - min(value.as_tuple().exponent for value in values) + len(str(len(values))) + 2
        return sum(values, Decimal(0))


def _product_exact(*values):
    with localcontext() as context:
        context.prec = sum(len(value.as_tuple().digits) for value in values) + 2
        result = Decimal(1)
        for value in values:
            result *= value
        return result


@dataclass(frozen=True)
class Fill:
    session: date
    security_id: str
    quantity: Decimal  # Signed: positive buy, negative sell.
    price: Decimal
    gross: Decimal
    fee: Decimal


@dataclass(frozen=True)
class Unfilled:
    session: date
    security_id: str
    quantity: Decimal
    reason: str
    signal_date: date


@dataclass(frozen=True)
class Cancellation:
    session: date
    security_id: str
    quantity: Decimal
    reason: str = 'NEXT_REGULAR_REBALANCE'


@dataclass(frozen=True)
class NavSnapshot:
    session: date
    nav: Decimal | None
    status: str
    reasons: tuple[str, ...]
    cash: Decimal
    receivables: Decimal
    market_value: Decimal | None


@dataclass(frozen=True)
class Split:
    event_id: str
    effective_date: date
    security_id: str
    ratio: Decimal


@dataclass(frozen=True)
class Dividend:
    event_id: str
    effective_date: date
    security_id: str
    cash_per_share: Decimal
    pay_date: date


@dataclass(frozen=True)
class Settlement:
    event_id: str
    effective_date: date
    security_id: str
    kind: str
    settlement_date: date | None
    cash_per_share: Decimal | None
    new_security_id: str | None = None
    stock_ratio: Decimal | None = None


class Ledger:
    """Long-only fractional holdings, pending net quantities, and dated cash claims.

    Inputs use permanent security IDs. Missing/None opens mean unavailable;
    nonfinite/nonpositive prices are malformed. Missing current marks produce
    INCOMPLETE_NAV. Paid dividends enter cash but remain reserved for the next
    regular signal; receivables contribute to signal NAV without funding buys.
    All mutation calls are chronological and same-input retries are idempotent.
    """

    def __init__(self, initial_cash=Decimal('100000'), cost_bps=Decimal('10')):
        self.cash = _decimal(initial_cash, 'INITIAL_CASH')
        cost_bps = _decimal(cost_bps, 'COST_BPS')
        if cost_bps >= 10000:
            raise LedgerError('INVALID_COST_BPS')
        with localcontext() as context:
            context.prec = 50
            self.cost_rate = cost_bps / Decimal(10000)
        self.reserved_cash = Decimal(0)
        self.holdings: dict[str, Decimal] = {}
        self.pending: dict[str, Decimal] = {}
        self.receivables: dict[str, Decimal] = {}
        self.fills: list[Fill] = []
        self.unfilled: list[Unfilled] = []
        self.cancellations: list[Cancellation] = []
        self._events: dict[str, Split | Dividend | Settlement] = {}
        self._dividends: dict[str, Dividend] = {}
        self._settlements: dict[str, tuple[Settlement, Decimal]] = {}
        self._executions: dict[date, tuple[object, tuple[Fill, ...]]] = {}
        self._decisions: dict[date, tuple[object, dict[str, Decimal]]] = {}
        self._interest: dict[tuple[date, date], tuple[Decimal, int, Decimal]] = {}
        self._last_session: date | None = None
        self._signal_date: date | None = None

    def _check_session(self, session):
        _date(session)
        if self._last_session is not None and session < self._last_session:
            raise LedgerError('NONCHRONOLOGICAL_SESSION')

    @staticmethod
    def _prices(prices):
        return {_security(key): None if value is None else _decimal(value, 'PRICE', positive=True)
                for key, value in prices.items()}

    @_precision
    def nav(self, session: date, close_prices: Mapping[str, Decimal | None]) -> NavSnapshot:
        """Value current positions using supplied current-session marks only."""
        self._check_session(session)
        prices = self._prices(close_prices)
        reasons = []
        market_value = Decimal(0)
        for security, quantity in sorted(self.holdings.items()):
            if prices.get(security) is None:
                reasons.append(f'MISSING_MARK:{security}')
            else:
                market_value += quantity * prices[security]
        for event, quantity in self._settlements.values():
            if quantity:
                reasons.append(f'UNSETTLED_CORPORATE_ACTION:{event.security_id}')
        receivables = sum(self.receivables.values(), Decimal(0))
        return NavSnapshot(session,
                           None if reasons else self.cash + market_value + receivables,
                           'INCOMPLETE_NAV' if reasons else 'COMPLETE',
                           tuple(sorted(set(reasons))), self.cash, receivables,
                           None if reasons else market_value)

    @_precision
    def rebalance(self, signal_date: date, selected: Sequence[str], slots: int,
                  close_prices: Mapping[str, Decimal | None]) -> dict[str, Decimal]:
        """Cancel prior remainder and lock A/(N*S-close) target quantities."""
        _date(signal_date)
        selected = tuple(_security(security) for security in selected)
        if type(slots) is not int or slots <= 0 or len(selected) > slots or len(set(selected)) != len(selected):
            raise LedgerError('INVALID_SLOTS_OR_SELECTION')
        prices = self._prices(close_prices)
        fingerprint = (selected, slots, tuple(sorted(prices.items())))
        if signal_date in self._decisions:
            previous, orders = self._decisions[signal_date]
            if fingerprint != previous:
                raise LedgerError('CONFLICTING_DECISION_RETRY')
            return dict(orders)
        self._check_session(signal_date)
        snapshot = self.nav(signal_date, prices)
        if snapshot.nav is None:
            raise LedgerError('INCOMPLETE_NAV')
        if any(prices.get(security) is None for security in selected):
            raise LedgerError('MISSING_SIGNAL_CLOSE')
        targets = {security: snapshot.nav / (Decimal(slots) * prices[security]) for security in selected}
        orders = {}
        for security in sorted(set(targets) | set(self.holdings)):
            delta = _sum_exact((targets.get(security, Decimal(0)),
                                self.holdings.get(security, Decimal(0)).copy_negate()))
            if delta:
                orders[security] = delta
        self.cancellations.extend(Cancellation(signal_date, key, value) for key, value in sorted(self.pending.items()))
        self.pending = dict(orders)
        self.reserved_cash = Decimal(0)
        self._signal_date = signal_date
        self._last_session = signal_date
        self._decisions[signal_date] = (fingerprint, dict(orders))
        return dict(orders)

    @_precision
    def execute_open(self, session: date, open_prices: Mapping[str, Decimal | None],
                     suspended=()) -> tuple[Fill, ...]:
        """Sell first, then scale all available buys by their common cash ratio."""
        _date(session)
        prices = self._prices(open_prices)  # Validate atomically before any sale.
        suspended = frozenset(_security(security) for security in suspended)
        fingerprint = (tuple(sorted(prices.items())), tuple(sorted(suspended)))
        if session in self._executions:
            previous, fills = self._executions[session]
            if previous != fingerprint:
                raise LedgerError('CONFLICTING_OPEN_RETRY')
            return fills
        self._check_session(session)
        if self._signal_date is not None and session <= self._signal_date:
            raise LedgerError('OPEN_MUST_FOLLOW_SIGNAL')
        self.settle_events(session)
        unresolved = {event.security_id for event, _ in self._settlements.values()}
        available = {}
        for security, quantity in sorted(self.pending.items()):
            if security in unresolved:
                reason = 'UNSETTLED_CORPORATE_ACTION'
            elif security in suspended:
                reason = 'SUSPENDED'
            elif prices.get(security) is None:
                reason = 'UNAVAILABLE_OPEN'
            else:
                available[security] = quantity
                continue
            self.unfilled.append(Unfilled(session, security, quantity, reason, self._signal_date))
        fills = []
        for security, quantity in available.items():
            if quantity < 0:
                if -quantity > self.holdings.get(security, 0):
                    raise LedgerError('SELL_EXCEEDS_HOLDING')
                fills.append(self._fill(session, security, quantity, prices[security]))
        buys = {key: quantity for key, quantity in available.items() if quantity > 0}
        requested = _sum_exact(self._trade_amount(quantity, prices[key])[2]
                               for key, quantity in buys.items())
        budget = max(Decimal(0), _sum_exact((self.cash, self.reserved_cash.copy_negate())))
        ratio = min(Decimal(1), budget / requested) if requested else Decimal(0)
        for security, quantity in buys.items():
            filled = quantity * ratio
            if filled:
                fills.append(self._fill(session, security, filled, prices[security]))
            if security in self.pending:
                self.unfilled.append(Unfilled(session, security, self.pending[security],
                                              'INSUFFICIENT_CASH', self._signal_date))
        result = tuple(fills)
        self.fills.extend(result)
        self._executions[session] = (fingerprint, result)
        self._last_session = session
        return result

    def _trade_amount(self, quantity, price):
        gross = _product_exact(quantity.copy_abs(), price)
        fee = _product_exact(gross, self.cost_rate)
        return gross, fee, _sum_exact((gross, fee))

    def _fill(self, session, security, quantity, price):
        gross, fee, debit = self._trade_amount(quantity, price)
        cash_change = _sum_exact((gross, fee.copy_negate())) if quantity < 0 else debit.copy_negate()
        new_cash = _sum_exact((self.cash, cash_change))
        if new_cash < 0:
            raise LedgerError('NEGATIVE_CASH')
        self.cash = new_cash
        self.holdings[security] = _sum_exact((self.holdings.get(security, Decimal(0)), quantity))
        self.pending[security] = _sum_exact((self.pending[security], quantity.copy_negate()))
        if not self.holdings[security]:
            del self.holdings[security]
        if not self.pending[security]:
            del self.pending[security]
        return Fill(session, security, quantity, price, gross, fee)

    @_precision
    def apply_event(self, event: Split | Dividend | Settlement, session: date):
        """Apply on effective date using pre-open quantities; identical retries do nothing."""
        if not isinstance(event, (Split, Dividend, Settlement)):
            raise LedgerError('UNKNOWN_EVENT_TYPE')
        _security(event.event_id)
        _security(event.security_id)
        _date(event.effective_date)
        _date(session)
        if event.event_id in self._events:
            if self._events[event.event_id] != event:
                raise LedgerError('CONFLICTING_EVENT_RETRY')
            return
        self._check_session(session)
        if session != event.effective_date or session in self._executions:
            raise LedgerError('EVENT_MUST_PRECEDE_EFFECTIVE_SESSION_OPEN')
        if isinstance(event, Split):
            ratio = _decimal(event.ratio, 'SPLIT_RATIO', positive=True)
            if any(item.security_id == event.security_id for item, _ in self._settlements.values()):
                raise LedgerError('SPLIT_DURING_UNRESOLVED_SETTLEMENT')
            if event.security_id in self.holdings:
                self.holdings[event.security_id] = _product_exact(self.holdings[event.security_id], ratio)
            if event.security_id in self.pending:
                self.pending[event.security_id] = _product_exact(self.pending[event.security_id], ratio)
        elif isinstance(event, Dividend):
            amount = _decimal(event.cash_per_share, 'DIVIDEND')
            _date(event.pay_date)
            if event.pay_date < event.effective_date:
                raise LedgerError('PAY_DATE_PRECEDES_EX_DATE')
            self.receivables[event.event_id] = self.holdings.get(event.security_id, Decimal(0)) * amount
            self._dividends[event.event_id] = event
        else:
            self._validate_settlement(event)
            if any(item.security_id == event.security_id for item, _ in self._settlements.values()):
                raise LedgerError('OVERLAPPING_CORPORATE_SETTLEMENT')
            self._settlements[event.event_id] = (event, self.holdings.get(event.security_id, Decimal(0)))
        self._events[event.event_id] = event
        self._last_session = session
        self.settle_events(session)

    @staticmethod
    def _validate_settlement(event):
        if event.kind not in {'CASH_MERGER', 'STOCK_MERGER', 'SPINOFF', 'DELISTING'}:
            raise LedgerError('UNKNOWN_SETTLEMENT_KIND')
        if event.settlement_date is not None:
            _date(event.settlement_date)
            if event.settlement_date < event.effective_date:
                raise LedgerError('SETTLEMENT_PRECEDES_EFFECTIVE_DATE')
        if event.cash_per_share is not None:
            _decimal(event.cash_per_share, 'SETTLEMENT_CASH')
        if event.kind in {'STOCK_MERGER', 'SPINOFF'}:
            if event.new_security_id is not None:
                _security(event.new_security_id)
                if event.new_security_id == event.security_id:
                    raise LedgerError('SETTLEMENT_REQUIRES_DISTINCT_SECURITY')
            if event.stock_ratio is not None:
                _decimal(event.stock_ratio, 'STOCK_RATIO', positive=True)
        elif event.new_security_id is not None or event.stock_ratio is not None:
            raise LedgerError('UNEXPECTED_STOCK_TERMS')

    @_precision
    def confirm_settlement(self, event: Settlement, session: date):
        """Fill missing terms of a previously registered corporate action.

        The caller supplies the actual confirmation session. Confirmed terms
        cannot be rewritten, and original entitlement quantities stay locked.
        """
        if not isinstance(event, Settlement):
            raise LedgerError('UNKNOWN_SETTLEMENT')
        _date(session)
        original = self._events.get(event.event_id)
        if not isinstance(original, Settlement):
            raise LedgerError('UNKNOWN_SETTLEMENT')
        if original == event:
            self.settle_events(session)
            return
        self._check_session(session)
        self._validate_settlement(event)
        for field in ('effective_date', 'security_id', 'kind', 'settlement_date',
                      'cash_per_share', 'new_security_id', 'stock_ratio'):
            old = getattr(original, field)
            if old is not None and old != getattr(event, field):
                raise LedgerError('CONFLICTING_CONFIRMED_TERMS')
        if event.event_id not in self._settlements:
            raise LedgerError('SETTLEMENT_ALREADY_COMPLETED')
        _, quantity = self._settlements[event.event_id]
        self._events[event.event_id] = event
        self._settlements[event.event_id] = (event, quantity)
        self.settle_events(session)

    @_precision
    def accrue_cash_interest(self, start_date: date, end_date: date,
                             annual_yield: Decimal | None, *, stale_sessions: int = 0) -> Decimal:
        """Accrue verified decimal annual yield over actual calendar days/365.

        Call before end-date events/trades. The caller verifies publication and
        next-session availability and splits intervals when rates/cash change.
        A missing rate or more than five stale exchange sessions blocks accrual;
        zero is permitted only when explicitly supplied by the calling research
        mode. Negative interest reduces reserved and spendable cash in the same
        proportion. Identical intervals are idempotent; overlaps are rejected.
        """
        _date(start_date)
        _date(end_date)
        if type(stale_sessions) is not int or stale_sessions < 0:
            raise LedgerError('INVALID_RATE_AGE')
        if annual_yield is None or stale_sessions > 5:
            raise LedgerError('CASH_RATE_UNVERIFIED')
        try:
            rate = Decimal(str(annual_yield))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise LedgerError('INVALID_CASH_RATE') from exc
        if not rate.is_finite():
            raise LedgerError('INVALID_CASH_RATE')
        key = (start_date, end_date)
        if key in self._interest:
            old_rate, old_age, amount = self._interest[key]
            if (rate, stale_sessions) != (old_rate, old_age):
                raise LedgerError('CONFLICTING_INTEREST_RETRY')
            return amount
        self._check_session(start_date)
        if end_date <= start_date:
            raise LedgerError('INVALID_ACCRUAL_INTERVAL')
        amount = self.cash * rate * Decimal((end_date - start_date).days) / Decimal(365)
        new_cash = _sum_exact((self.cash, amount))
        if new_cash < 0:
            raise LedgerError('INTEREST_EXCEEDS_TOTAL_CASH')
        if amount < 0 and self.reserved_cash:
            if self.reserved_cash == self.cash:
                new_reserved = new_cash
            else:
                new_reserved = _product_exact(self.reserved_cash, new_cash) / self.cash
            self.reserved_cash = new_reserved
        self.cash = new_cash
        self._interest[key] = (rate, stale_sessions, amount)
        self._last_session = end_date
        return amount

    @_precision
    def settle_events(self, session: date):
        """Pay due entitlements and transform only confirmed settlement terms."""
        self._check_session(session)
        for event_id, event in tuple(sorted(self._dividends.items())):
            if event.pay_date <= session:
                amount = self.receivables.pop(event_id)
                self.cash += amount
                self.reserved_cash += amount
                del self._dividends[event_id]
        for event_id, (event, quantity) in tuple(sorted(self._settlements.items())):
            complete = event.settlement_date is not None and event.cash_per_share is not None
            if event.kind in {'STOCK_MERGER', 'SPINOFF'}:
                complete = complete and event.new_security_id is not None and event.stock_ratio is not None
            if not complete or session < event.settlement_date:
                continue
            self.cash += quantity * _decimal(event.cash_per_share, 'SETTLEMENT_CASH')
            if event.kind != 'SPINOFF':
                self.holdings.pop(event.security_id, None)
                if event.security_id in self.pending:
                    self.cancellations.append(Cancellation(session, event.security_id,
                                                          self.pending.pop(event.security_id), 'CORPORATE_SETTLEMENT'))
            if event.new_security_id is not None:
                self.holdings[event.new_security_id] = self.holdings.get(event.new_security_id, Decimal(0)) + quantity * _decimal(event.stock_ratio, 'STOCK_RATIO', positive=True)
                if not self.holdings[event.new_security_id]:
                    del self.holdings[event.new_security_id]
            del self._settlements[event_id]
        self._last_session = session
