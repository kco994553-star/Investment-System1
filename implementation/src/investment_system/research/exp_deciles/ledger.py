"""Decimal account ledger for EXP-STOCK-INDICATOR-DECILES-v1 (USD, long-only, annual reselection).

Ported from research/qgv_backtest @ 56a0e8ce (#417/#430) and changed for EXP-STOCK-INDICATOR-DECILES-v1.

Kept from the source: Decimal arithmetic (precision 50, ROUND_DOWN, exact cash sums), fractional quantities, target
quantities locked at the signal close S (target = base / (N x S close)), sells before buys at the T open, buys scaled by
one common cash ratio, a fee of cost_bps on gross traded value per side with no slippage, dividends as a receivable at
the ex-date and cash at the pay date, splits that multiply quantity on the effective date, confirmed corporate-action
terms only (never inferred), no next-rank substitution.

Changed for this experiment (settings doc section 1, inventory item 7):
- Orders execute only at the T open of their own rebalance. Anything not filled there is recorded UNFILLED with a
  reason and is dropped: it is never retried on a later session, and its slot stays cash until the next reselection.
  The cash planned at S for such a slot is held back at T, so other names' open-price drift cannot spend it.
- Every corporate-action cash amount (dividends, merger and settlement cash) is reserved until the next reselection.
  The source added settlement cash to cash without reserving it; that is fixed here.
- Settlement entitlement (review F1): the quantity a Settlement's terms apply to is the legal quantity held before the
  open of its effective (ex) date, snapshot when that date is reached even if the evidence comes later. Terms are
  delivered only from activation = max(effective_date, available_at) or from a later confirmation, never back-dated.
  A SPINOFF parent keeps trading ex-distribution, so a holder that sells it after the effective date still receives the
  distribution at activation and a buyer after the effective date does not; its snapshot stays on the effective-date
  share basis because the ratio is per share held then. A terminating event applies to the legal holding at activation:
  the snapshot (rescaled by later splits of the security) less sales after the effective date plus shares delivered
  into it by other corporate actions, which are never voided. Only this portfolio's own buy fills on or after the
  effective date (tracked per pending event, rescaled by later splits) are treated differently, by kind: a DELISTING's
  shares still exist, so they stay in the holding and the scenario or terms apply to all of it; a CASH_MERGER's or
  STOCK_MERGER's shares ceased to exist, so those buys are reversed and their gross + fee is refunded to cash, reserved
  until the next reselection (flag POST_EFFECTIVE_PURCHASE_REVERSED). Any change after the effective date is flagged
  HOLDING_CHANGED_AFTER_EFFECTIVE_DATE.
- Deferred delivery (review F1): new shares delivered after the effective date (activation or confirmation later than
  it) are legally owned from the effective date, so every split of the new security effective in (effective date,
  today] scales the received quantity and every dividend of it with an ex-date in that window is booked on the
  received quantity, paid at max(pay date, today), depositary fee rules applied (event
  DIVIDEND_ON_DEFERRED_DELIVERY).
- Termination events (DELISTING / CASH_MERGER / STOCK_MERGER) act only from max(effective_date, available_at). With
  confirmed terms they settle by those terms in both scenarios. Without confirmed terms the scenario applies: LOSS sets
  the position's value to 0, CARRY keeps it at its last observed price as a non-cash, non-tradable asset (never sold,
  never turned into cash, never reinvested). The legal quantity is kept in both. A later confirmation replaces the
  scenario value from its own date (no back-dating).
- Per-security conflicts (review F5): events are global, so one security's data issue must not refuse every portfolio.
  A later terminating event of an already terminated security is supporting evidence; if the termination is still
  unconfirmed and the later event (or its confirmation) carries complete terms, those terms settle it from that date.
  Terms that contradict terms already applied, a settlement's own partial terms, or the partial terms of the open
  termination they would settle (or a CASH_MERGER against an open STOCK_MERGER, or the reverse) are recorded in
  `conflicts` (TERMINATION_TERMS_DIFFER_FROM_APPLIED_TERMS, CONFIRMED_TERMS_CONTRADICT_SETTLEMENT,
  TERMINATION_TERMS_CONTRADICT_OPEN_TERMINATION, ...) and flagged SETTLEMENT_CONFLICT on that day; the position is
  left as it was. Stock consideration delivered into an already terminated security takes that security's state
  (flag STOCK_CONSIDERATION_IN_TERMINATED_SECURITY): with confirmed terms they are chained onto the received shares
  from today (cash as a reserved receivable, stock delivered on); otherwise the shares join its frozen LOSS / CARRY
  position at its carry mark. On one date, settlements of a security that receives shares by corporate action are
  handled after those of every security delivering into it (entitlement snapshot, activation, confirmation per
  security), so the outcome never depends on how event_ids sort. A split of a terminated security scales a frozen
  position (flag SPLIT_ON_TERMINATED_SECURITY) and is ignored when nothing is held. Malformed event records (missing
  evidence, unknown kind, impossible dates or amounts) are still refused for the whole run.
- A missing price is not a termination: the position is marked at its last observed price and flagged STALE_MARK.
  Price gaps alone never trigger LOSS or CARRY.
- ADR dividends may carry depositary_fee_per_share (as in the preserved Codex research ledger, commit c68af2c0): the
  receivable is quantity x (cash_per_share - fee), the fee is recorded as an instrument fee (`instrument_fees`, kind
  DEPOSITARY_FEE, separate from trading costs) and a fee above the cash per share is refused (ADR_FEE_EXCEEDS_DIVIDEND).
- Cash interest is zero (mode 'ZERO'; no rate rows). Initial capital defaults to an internal notional USD 1,000,000 (an engine setting, not
  an owner-set capital; returns do not depend on it). Currency is USD only.
- The equal-weight target base at S is cash (reserved cash released) plus tradable holdings at S marks. Unpaid
  receivables, CARRY value and positions frozen by a corporate action cannot fund trades, so they are reported but
  left out of the base. Every NAV still includes them.
- The run never halts on a data gap; each day carries a status and reason codes.
- Terminal valuation at an open (review F4): with end_valuation='OPEN' the last session `end` (the next reselection T)
  applies that day's pre-open events and receivables, marks every tradable position at that day's OPEN, executes no
  trade and makes no decision; CARRY and LOSS values follow the same rules as any day. Every daily row says which mark
  it used ('valuation': CLOSE or OPEN); an OPEN row without that day's open is flagged STALE_MARK like a close row.

Prices must be raw (unadjusted) in USD, so a split or a dividend is counted exactly once. Pure: no file or network IO.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_DOWN, localcontext
from functools import wraps
from typing import Mapping, Sequence


class LedgerError(ValueError):
    """Invalid input or chronology. The message is an UPPER_SNAKE reason code."""


SCENARIO_LOSS = 'LOSS'
SCENARIO_CARRY = 'CARRY'
SCENARIOS = (SCENARIO_LOSS, SCENARIO_CARRY)
CASH_INTEREST_ZERO = 'ZERO'
CURRENCY = 'USD'
PRICE_BASIS_RAW = 'RAW'
VALUATION_CLOSE = 'CLOSE'
VALUATION_OPEN = 'OPEN'
VALUATIONS = (VALUATION_CLOSE, VALUATION_OPEN)
DEFAULT_INITIAL_CAPITAL = Decimal('1000000')
DEFAULT_COST_BPS = Decimal('10')

STATE_HELD = 'HELD'
STATE_CARRY = SCENARIO_CARRY
STATE_LOSS = SCENARIO_LOSS

# Unfilled order reasons.
MISSING_SIGNAL_PRICE = 'MISSING_SIGNAL_PRICE'
INCOMPLETE_SIGNAL_NAV = 'INCOMPLETE_SIGNAL_NAV'
UNAVAILABLE_OPEN = 'UNAVAILABLE_OPEN'
SUSPENDED = 'SUSPENDED'
UNSETTLED_CORPORATE_ACTION = 'UNSETTLED_CORPORATE_ACTION'
INSUFFICIENT_CASH = 'INSUFFICIENT_CASH'
UNFILLED_REASONS = (MISSING_SIGNAL_PRICE, INCOMPLETE_SIGNAL_NAV, UNAVAILABLE_OPEN, SUSPENDED,
                    UNSETTLED_CORPORATE_ACTION, INSUFFICIENT_CASH)

TERMINATING_KINDS = frozenset({'CASH_MERGER', 'STOCK_MERGER', 'DELISTING'})
MERGER_KINDS = frozenset({'CASH_MERGER', 'STOCK_MERGER'})  # The shares cease to exist at the effective date.
STOCK_KINDS = frozenset({'STOCK_MERGER', 'SPINOFF'})
SETTLEMENT_KINDS = TERMINATING_KINDS | {'SPINOFF'}


def _decimal(value, name, *, positive=False):
    if isinstance(value, bool):
        raise LedgerError(f'INVALID_{name}')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise LedgerError(f'INVALID_{name}') from exc
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise LedgerError(f'INVALID_{name}')
    return result


def _date(value, name='SESSION'):
    if type(value) is not date:
        raise LedgerError(f'{name}_MUST_BE_DATE')
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
        context.prec = (max(value.adjusted() for value in values)
                        - min(value.as_tuple().exponent for value in values) + len(str(len(values))) + 2)
        return sum(values, Decimal(0))


def _product_exact(*values):
    with localcontext() as context:
        context.prec = sum(len(value.as_tuple().digits) for value in values) + 2
        result = Decimal(1)
        for value in values:
            result *= value
        return result


@dataclass(frozen=True)
class Rebalance:
    """One reselection: signal close S, execution open T, the selected security IDs (equal weight)."""
    signal_date: date
    execution_date: date
    selected: tuple[str, ...]

    def __post_init__(self):
        if isinstance(self.selected, str):
            raise LedgerError('SELECTED_MUST_BE_A_SEQUENCE')
        object.__setattr__(self, 'selected', tuple(self.selected))


@dataclass(frozen=True)
class PriceRow:
    open: Decimal | None
    close: Decimal | None
    suspended: bool = False


@dataclass(frozen=True)
class Fill:
    session: date
    security_id: str
    quantity: Decimal  # Signed: positive buy, negative sell.
    price: Decimal
    gross: Decimal
    fee: Decimal
    signal_date: date


@dataclass(frozen=True)
class Unfilled:
    session: date
    security_id: str
    requested_quantity: Decimal | None  # None when no target could be computed.
    unfilled_quantity: Decimal | None
    reason: str
    signal_date: date
    partial: bool = False  # True when part of the order filled and only the remainder is unfilled.


@dataclass(frozen=True)
class Split:
    event_id: str
    effective_date: date
    security_id: str
    ratio: Decimal


@dataclass(frozen=True)
class Dividend:
    event_id: str
    effective_date: date  # Ex-date: the receivable is booked on this date.
    security_id: str
    cash_per_share: Decimal
    pay_date: date | None = None  # None: cash on the ex-date, flagged DIVIDEND_PAY_DATE_ASSUMED_EX_DATE.
    depositary_fee_per_share: Decimal | None = None  # ADR depositary fee per ADS, deducted from the cash per share.


@dataclass(frozen=True)
class Settlement:
    """A corporate action with evidence. Terms are confirmed only when every term field is present."""
    event_id: str
    effective_date: date
    security_id: str
    kind: str  # CASH_MERGER / STOCK_MERGER / DELISTING (terminating) or SPINOFF.
    available_at: date  # The date the evidence is available; nothing acts before it.
    evidence: str
    settlement_date: date | None = None
    cash_per_share: Decimal | None = None
    new_security_id: str | None = None
    stock_ratio: Decimal | None = None


@dataclass(frozen=True)
class SettlementConfirmation:
    """Confirmed terms for a registered Settlement, usable from available_at (never back-dated)."""
    event_id: str
    available_at: date
    evidence: str
    settlement_date: date
    cash_per_share: Decimal
    new_security_id: str | None = None
    stock_ratio: Decimal | None = None


@dataclass(frozen=True)
class Receivable:
    kind: str  # DIVIDEND or SETTLEMENT_CASH
    event_id: str
    security_id: str
    amount: Decimal
    pay_date: date


@dataclass
class _SettlementState:
    event: Settlement
    activated_on: date
    quantity: Decimal  # Entitlement quantity (snapshot before the effective-date open; terminating: less later sales).
    snapshot: Decimal  # Legal quantity held before the open of the effective date.
    confirmed: bool = False
    terms: tuple | None = None
    terms_since: date | None = None  # Effective date of the event whose terms were applied (legal holding date).
    role: str = 'PRIMARY'  # SUPPORTING: a later terminating event of an already terminated security.


@dataclass
class _Entitlement:
    """A Settlement between its effective date and its activation."""
    security_id: str
    terminating: bool
    snapshot: Decimal  # Legal quantity before the effective-date open (terminating kinds: rescaled by later splits).
    bought: Decimal = Decimal(0)  # Bought by this portfolio's own fills since the effective date (current split basis).
    cost: Decimal = Decimal(0)  # Gross + fee paid for `bought`.


@dataclass(frozen=True)
class _EntitlementSnapshot:
    """Schedule entry: the effective date of a Settlement is reached (pre-open); its entitlement quantity is recorded."""
    event: Settlement


_TERM_FIELDS = ('settlement_date', 'cash_per_share', 'new_security_id', 'stock_ratio')


def _terms(source):
    return tuple(getattr(source, name) for name in _TERM_FIELDS)


def _terms_complete(kind, settlement_date, cash_per_share, new_security_id, stock_ratio):
    complete = settlement_date is not None and cash_per_share is not None
    if kind in STOCK_KINDS:
        complete = complete and new_security_id is not None and stock_ratio is not None
    return complete


def _validate_terms(kind, security_id, effective_date, settlement_date, cash_per_share, new_security_id, stock_ratio):
    if settlement_date is not None:
        _date(settlement_date, 'SETTLEMENT_DATE')
        if settlement_date < effective_date:
            raise LedgerError('SETTLEMENT_PRECEDES_EFFECTIVE_DATE')
    if cash_per_share is not None:
        _decimal(cash_per_share, 'SETTLEMENT_CASH')
    if kind in STOCK_KINDS:
        if new_security_id is not None:
            _security(new_security_id)
            if new_security_id == security_id:
                raise LedgerError('SETTLEMENT_REQUIRES_DISTINCT_SECURITY')
        if stock_ratio is not None:
            _decimal(stock_ratio, 'STOCK_RATIO', positive=True)
    elif new_security_id is not None or stock_ratio is not None:
        raise LedgerError('UNEXPECTED_STOCK_TERMS')


def _dividend_amounts(event):
    """(cash per share, depositary fee per share); a fee above the cash is refused."""
    cash = _decimal(event.cash_per_share, 'DIVIDEND')
    fee = Decimal(0) if event.depositary_fee_per_share is None else _decimal(event.depositary_fee_per_share,
                                                                               'DEPOSITARY_FEE')
    if fee > cash:
        raise LedgerError('ADR_FEE_EXCEEDS_DIVIDEND')
    return cash, fee


def _validate_settlement(event):
    _security(event.event_id)
    _security(event.security_id)
    _date(event.effective_date, 'EFFECTIVE_DATE')
    _date(event.available_at, 'AVAILABLE_AT')
    if event.kind not in SETTLEMENT_KINDS:
        raise LedgerError('UNKNOWN_SETTLEMENT_KIND')
    if not isinstance(event.evidence, str) or not event.evidence.strip():
        raise LedgerError('SETTLEMENT_EVIDENCE_REQUIRED')
    _validate_terms(event.kind, event.security_id, event.effective_date, *_terms(event))


def activation_date(event: Settlement) -> date:
    """A corporate action acts only once it is both effective and evidenced."""
    return max(event.effective_date, event.available_at)


class Ledger:
    """Stateful account used by run_ledger; call order per session is fixed by run_ledger.

    begin_session -> apply_* events (pre-open) -> pay_due -> execute_open (T only) -> observe -> snapshot
    -> decide (S only, after the close).
    """

    def __init__(self, *, scenario, initial_cash=DEFAULT_INITIAL_CAPITAL, cost_bps=DEFAULT_COST_BPS,
                 cash_interest=CASH_INTEREST_ZERO):
        if scenario not in SCENARIOS:
            raise LedgerError('UNKNOWN_SCENARIO')
        if cash_interest != CASH_INTEREST_ZERO:
            raise LedgerError('UNSUPPORTED_CASH_INTEREST_MODE')
        self.scenario = scenario
        self.cash = _decimal(initial_cash, 'INITIAL_CASH', positive=True)
        self.initial_cash = self.cash
        cost = _decimal(cost_bps, 'COST_BPS')
        if cost >= 10000:
            raise LedgerError('INVALID_COST_BPS')
        self.cost_bps = cost
        with localcontext() as context:
            context.prec = 50
            self.cost_rate = cost / Decimal(10000)
        self.reserved_cash = Decimal(0)
        self.holdings: dict[str, Decimal] = {}  # Legal quantity in every state.
        self.states: dict[str, str] = {}  # CARRY / LOSS; absent means HELD (tradable).
        self.carry_marks: dict[str, tuple[date, Decimal] | None] = {}
        self.last_price: dict[str, tuple[date, Decimal, str]] = {}
        self.receivables: dict[tuple[str, str], Receivable] = {}
        self.pending: dict[str, Decimal] = {}
        self.requested: dict[str, Decimal] = {}
        self.terminated: dict[str, str] = {}
        self.fills: list[Fill] = []
        self.instrument_fees: list[dict] = []  # Depositary fees deducted from ADR dividends (not trading costs).
        self.unfilled: list[Unfilled] = []
        self._settlements: dict[str, _SettlementState] = {}
        self._entitlements: dict[str, _Entitlement] = {}  # event_id -> pending between effective date and activation
        self._history: dict[str, list] = {}  # security_id -> Splits and Dividends applied so far, in order
        self.conflicts: list[dict] = []
        self._signal: Rebalance | None = None
        self._planned_value: dict[str, Decimal] = {}
        self._signal_holdback = Decimal(0)
        self._session: date | None = None
        self._day_flags: list[str] = []
        self._day_events: list[str] = []
        self._day_fills: list[Fill] = []

    # -- chronology -----------------------------------------------------------------------------------------------
    def begin_session(self, session: date):
        _date(session)
        if self._session is not None and session <= self._session:
            raise LedgerError('NONCHRONOLOGICAL_SESSION')
        self._session = session
        self._day_flags, self._day_events, self._day_fills = [], [], []

    def _require_session(self):
        if self._session is None:
            raise LedgerError('SESSION_NOT_STARTED')
        return self._session

    def frozen(self, security_id: str) -> bool:
        """Not tradable: terminated, in a LOSS/CARRY scenario, or converted by confirmed terms."""
        return security_id in self.terminated or security_id in self.states

    # -- corporate actions (pre-open) ---------------------------------------------------------------------------
    def _conflict(self, event_id, security_id, reason):
        """A per-security data conflict: recorded and flagged, the position is left as it was (review F5)."""
        self.conflicts.append(dict(session=self._session, event_id=event_id, security_id=security_id, reason=reason))
        self._day_flags.append(f'SETTLEMENT_CONFLICT:{event_id}')

    @_precision
    def apply_split(self, event: Split):
        self._require_session()
        ratio = _decimal(event.ratio, 'SPLIT_RATIO', positive=True)
        sid = event.security_id
        self._history.setdefault(sid, []).append(event)
        for pending in self._entitlements.values():
            if pending.terminating and pending.security_id == sid:
                pending.snapshot = _product_exact(pending.snapshot, ratio)
                pending.bought = _product_exact(pending.bought, ratio)
        if self.carry_marks.get(sid) is not None:
            # A frozen CARRY mark moves with the legal quantity (also one recorded before any share is delivered).
            day, price = self.carry_marks[sid]
            self.carry_marks[sid] = (day, price / ratio)
        if self.frozen(sid):
            if not any(sid in book for book in (self.holdings, self.pending, self.requested)):
                self._day_events.append(f'SPLIT_IGNORED_NO_POSITION:{event.event_id}')
                return
            self._day_flags.append(f'SPLIT_ON_TERMINATED_SECURITY:{event.event_id}')
        for book in (self.holdings, self.pending, self.requested):
            if sid in book:
                book[sid] = _product_exact(book[sid], ratio)
        if sid in self.last_price:
            day, price, field = self.last_price[sid]
            # A stale mark from before the split must move to the post-split basis, or value would double.
            self.last_price[sid] = (day, price / ratio, field)
        self._day_events.append(f'SPLIT:{event.event_id}')

    @_precision
    def apply_dividend(self, event: Dividend):
        """Entitlement on the legal quantity held before the ex-date open (in every state, so both scenarios agree)."""
        self._require_session()
        self._history.setdefault(event.security_id, []).append(event)
        self._book_dividend(event, self.holdings.get(event.security_id, Decimal(0)), event.event_id)
        self._day_events.append(f'DIVIDEND_EX:{event.event_id}')

    def _book_dividend(self, event: Dividend, quantity, key):
        """Receivable quantity x (cash - depositary fee), paid at max(pay date, today)."""
        session = self._session
        cash, fee = _dividend_amounts(event)
        amount = _product_exact(quantity, _sum_exact((cash, fee.copy_negate())))
        if fee and quantity:
            self.instrument_fees.append(dict(session=session, event_id=key, security_id=event.security_id,
                                             kind='DEPOSITARY_FEE', quantity=quantity, fee_per_share=fee,
                                             amount=_product_exact(quantity, fee)))
            self._day_events.append(f'DEPOSITARY_FEE:{key}')
        if event.pay_date is None:
            self._day_flags.append(f'DIVIDEND_PAY_DATE_ASSUMED_EX_DATE:{key}')
        pay_date = session if event.pay_date is None else max(event.pay_date, session)
        if amount:
            self.receivables[('DIVIDEND', key)] = Receivable('DIVIDEND', key, event.security_id, amount, pay_date)

    def _book_settlement_cash(self, pay_id, security_id, amount, settlement_date):
        if amount:
            self.receivables[('SETTLEMENT', pay_id)] = Receivable(
                'SETTLEMENT_CASH', pay_id, security_id, amount, max(settlement_date, self._session))

    def _freeze(self, sid):
        """An unconfirmed termination: this run's scenario (LOSS at 0, CARRY at the last observed price)."""
        if sid in self.states:
            return
        self.states[sid] = self.scenario
        if self.scenario == SCENARIO_CARRY:
            mark = self.last_price.get(sid)
            self.carry_marks[sid] = None if mark is None else (mark[0], mark[1])

    @_precision
    def record_entitlement(self, event: Settlement):
        """The effective date is reached (pre-open): record the legal quantity the event's terms will apply to.

        Nothing is delivered, frozen or flagged here; the evidence may become available only later (activation)."""
        self._require_session()
        _validate_settlement(event)
        if event.event_id in self._entitlements or event.event_id in self._settlements:
            raise LedgerError('DUPLICATE_SETTLEMENT')
        self._entitlements[event.event_id] = _Entitlement(event.security_id, event.kind in TERMINATING_KINDS,
                                                          self.holdings.get(event.security_id, Decimal(0)))

    @_precision
    def apply_settlement(self, event: Settlement):
        session = self._require_session()
        _validate_settlement(event)
        if event.event_id in self._settlements:
            raise LedgerError('DUPLICATE_SETTLEMENT')
        sid = event.security_id
        terminating = event.kind in TERMINATING_KINDS
        held = self.holdings.get(sid, Decimal(0))
        pending = self._entitlements.pop(event.event_id, None) or _Entitlement(sid, terminating, held)
        if terminating and held != pending.snapshot:
            self._day_flags.append(f'HOLDING_CHANGED_AFTER_EFFECTIVE_DATE:{event.event_id}')
        state = _SettlementState(event, session, held if terminating else pending.snapshot, pending.snapshot)
        self._settlements[event.event_id] = state
        terms = _terms(event)
        complete = _terms_complete(event.kind, *terms)
        if terminating and sid in self.terminated:
            state.role = 'SUPPORTING'
            self._supporting_termination(state, terms if complete else None)
            return
        if terminating:
            self.terminated[sid] = event.event_id
            void = min(pending.bought, held) if event.kind in MERGER_KINDS else Decimal(0)
            if void:  # DELISTING: the shares still exist, so the whole legal holding stays.
                self._reverse_post_effective_buys(event, pending, void)
                state.quantity = self.holdings.get(sid, Decimal(0))
        if complete:
            self._deliver(state, terms, kind=event.kind, quantity=state.quantity, pay_id=event.event_id)
        elif terminating:
            self._freeze(sid)
            self._day_events.append(f'TERMINATION_UNCONFIRMED:{event.event_id}:{self.scenario}')
        else:
            self._day_flags.append(f'SPINOFF_TERMS_UNCONFIRMED:{event.event_id}')
            self._day_events.append(f'SPINOFF_UNCONFIRMED:{event.event_id}')

    def _reverse_post_effective_buys(self, event: Settlement, pending: _Entitlement, void):
        """Shares of a merged company cannot be bought after its effective date: the fills are reversed, their gross +
        fee goes back to cash (reserved until the next reselection) instead of being destroyed."""
        sid = event.security_id
        refund = pending.cost if void == pending.bought else pending.cost * void / pending.bought
        self.cash = _sum_exact((self.cash, refund))
        self.reserved_cash = _sum_exact((self.reserved_cash, refund))
        remaining = _sum_exact((self.holdings[sid], void.copy_negate()))
        if remaining:
            self.holdings[sid] = remaining
        else:
            del self.holdings[sid]
        self._day_flags.append(f'POST_EFFECTIVE_PURCHASE_REVERSED:{event.event_id}')

    def _settle_termination(self, owner: _SettlementState, terms, *, kind, pay_id, label, since):
        """Settle the (still unconfirmed) termination `owner` by confirmed terms from today, on the frozen legal quantity."""
        quantity = self.holdings.get(owner.event.security_id, Decimal(0))
        self._deliver(owner, terms, kind=kind, quantity=quantity, pay_id=pay_id, since=since)
        self._day_events.append(label)

    def _termination_conflict(self, owner: _SettlementState, terms, kind):
        """Reason code when `terms` (None = absent) or `kind` contradict the termination `owner`: its applied terms once
        confirmed, otherwise its own partial terms and its merger kind (review F5). None when they agree."""
        if owner.confirmed:
            if any(new is not None and new != old for old, new in zip(owner.terms, terms)):
                return 'TERMINATION_TERMS_DIFFER_FROM_APPLIED_TERMS'
            return None
        if {owner.event.kind, kind} == MERGER_KINDS or any(
                old is not None and new is not None and old != new for old, new in zip(_terms(owner.event), terms)):
            return 'TERMINATION_TERMS_CONTRADICT_OPEN_TERMINATION'
        return None

    def _supporting_termination(self, state: _SettlementState, terms):
        """A later terminating event of an already terminated security (review F5): supporting evidence, the settlement
        of a still open termination, or a recorded conflict on that security only."""
        event = state.event
        owner = self._settlements[self.terminated[event.security_id]]
        reason = self._termination_conflict(owner, _terms(event), event.kind)
        if reason is None and owner.confirmed and terms is not None and owner.terms != tuple(terms):
            reason = 'TERMINATION_TERMS_DIFFER_FROM_APPLIED_TERMS'
        if reason is not None:
            self._conflict(event.event_id, event.security_id, reason)
        elif terms is None or owner.confirmed:
            self._day_events.append(f'TERMINATION_SUPPORTING_EVIDENCE:{event.event_id}')
        else:
            self._settle_termination(owner, terms, kind=event.kind, pay_id=event.event_id, since=event.effective_date,
                                     label=f'TERMINATION_SETTLED_BY:{owner.event.event_id}:{event.event_id}')
            state.confirmed, state.terms = True, tuple(terms)

    @_precision
    def confirm_settlement(self, confirmation: SettlementConfirmation):
        self._require_session()
        state = self._settlements.get(confirmation.event_id)
        if state is None:
            raise LedgerError('CONFIRMATION_WITHOUT_SETTLEMENT')
        event = state.event
        if not isinstance(confirmation.evidence, str) or not confirmation.evidence.strip():
            raise LedgerError('SETTLEMENT_EVIDENCE_REQUIRED')
        terms = _terms(confirmation)
        _validate_terms(event.kind, event.security_id, event.effective_date, *terms)
        if not _terms_complete(event.kind, *terms):
            raise LedgerError('INCOMPLETE_CONFIRMED_TERMS')
        if any(old is not None and old != new for old, new in zip(_terms(event), terms)):
            self._conflict(event.event_id, event.security_id, 'CONFIRMED_TERMS_CONTRADICT_SETTLEMENT')
            return
        if state.confirmed:
            if state.terms != terms:
                self._conflict(event.event_id, event.security_id, 'SETTLEMENT_ALREADY_CONFIRMED_WITH_OTHER_TERMS')
            return
        if event.kind in TERMINATING_KINDS:
            owner = self._settlements[self.terminated[event.security_id]]
            if owner is not state:  # A supporting event confirmed: checked against the termination it supports.
                reason = self._termination_conflict(owner, terms, event.kind)
                if reason is None and owner.confirmed and owner.terms != terms:
                    reason = 'TERMINATION_TERMS_DIFFER_FROM_APPLIED_TERMS'
                if reason is not None:
                    self._conflict(event.event_id, event.security_id, reason)
                    return
            if not owner.confirmed:
                self._settle_termination(owner, terms, kind=event.kind, pay_id=event.event_id,
                                         since=event.effective_date,
                                         label=f'SETTLEMENT_CONFIRMED:{confirmation.event_id}')
            state.confirmed, state.terms = True, tuple(terms)
            return
        self._deliver(state, terms, kind=event.kind, quantity=state.quantity, pay_id=event.event_id)
        self._day_events.append(f'SETTLEMENT_CONFIRMED:{confirmation.event_id}')

    def _deliver(self, state: _SettlementState, terms, *, kind, quantity, pay_id, since=None):
        """Apply confirmed terms from the current session to `quantity`; cash is paid no earlier than today.

        `since` is the effective date of the event the terms belong to: the holder owns any new shares from then."""
        self._require_session()
        settlement_date, cash_per_share, new_security_id, stock_ratio = terms
        sid = state.event.security_id
        since = state.event.effective_date if since is None else since
        if kind in TERMINATING_KINDS:
            self.holdings.pop(sid, None)
            self.states.pop(sid, None)
            self.carry_marks.pop(sid, None)
        self._book_settlement_cash(pay_id, sid, _product_exact(quantity, _decimal(cash_per_share, 'SETTLEMENT_CASH')),
                                   settlement_date)
        if kind in STOCK_KINDS:
            received = _product_exact(quantity, _decimal(stock_ratio, 'STOCK_RATIO', positive=True))
            self._receive(new_security_id, received, pay_id, since)
        state.confirmed, state.terms, state.terms_since = True, tuple(terms), since
        self._day_events.append(f'SETTLEMENT_APPLIED:{pay_id}')

    def _receive(self, sid, quantity, source_id, since, chain=()):
        """Credit `quantity` shares of `sid` legally owned since `since` but delivered only today (review F1).

        The splits of `sid` effective in (since, today] scale the quantity, and its dividends with an ex-date in that
        window are booked on it (pay date no earlier than today). Shares of an already terminated security (review F5)
        take that security's terms: confirmed terms are chained onto them from today; otherwise they join its frozen
        LOSS / CARRY position. Either way the day is flagged STOCK_CONSIDERATION_IN_TERMINATED_SECURITY."""
        session = self._session
        for event in self._history.get(sid, ()):
            if since < event.effective_date <= session:
                if isinstance(event, Split):
                    quantity = _product_exact(quantity, _decimal(event.ratio, 'SPLIT_RATIO', positive=True))
                else:
                    self._book_dividend(event, quantity, f'{event.event_id}:{source_id}')
                    self._day_events.append(f'DIVIDEND_ON_DEFERRED_DELIVERY:{event.event_id}:{source_id}')
        if not quantity:
            return
        owner_id = self.terminated.get(sid)
        if owner_id is not None:
            self._day_flags.append(f'STOCK_CONSIDERATION_IN_TERMINATED_SECURITY:{source_id}:{sid}')
            owner = self._settlements[owner_id]
            if owner.confirmed:
                if sid in chain:
                    self._conflict(source_id, sid, 'CIRCULAR_STOCK_CONSIDERATION')
                    return
                settlement_date, cash_per_share, new_security_id, stock_ratio = owner.terms
                pay_id = f'{source_id}>{owner_id}'
                self._book_settlement_cash(pay_id, sid, _product_exact(
                    quantity, _decimal(cash_per_share, 'SETTLEMENT_CASH')), settlement_date)
                if new_security_id is not None:
                    received = _product_exact(quantity, _decimal(stock_ratio, 'STOCK_RATIO', positive=True))
                    self._receive(new_security_id, received, pay_id, owner.terms_since, chain + (sid,))
                self._day_events.append(f'SETTLEMENT_APPLIED:{pay_id}')
                return
            self._freeze(sid)
        self.holdings[sid] = _sum_exact((self.holdings.get(sid, Decimal(0)), quantity))

    def pay_due(self):
        """Move due receivables into cash. All of it stays reserved until the next reselection."""
        session = self._require_session()
        for key, item in sorted(self.receivables.items()):
            if item.pay_date <= session:
                self.cash = _sum_exact((self.cash, item.amount))
                self.reserved_cash = _sum_exact((self.reserved_cash, item.amount))
                del self.receivables[key]
                self._day_events.append(f'CASH_RECEIVED:{item.kind}:{item.event_id}')

    # -- prices ---------------------------------------------------------------------------------------------------
    def observe(self, rows: Mapping[str, PriceRow], *, opens_only: bool = False):
        session = self._require_session()
        for sid, row in sorted(rows.items()):
            if row.open is not None:
                self.last_price[sid] = (session, row.open, 'open')
            if row.close is not None and not opens_only:
                self.last_price[sid] = (session, row.close, 'close')

    def _close_today(self, sid):
        mark = self.last_price.get(sid)
        if mark is not None and mark[0] == self._session and mark[2] == 'close':
            return mark[1]
        return None

    def _carry_value(self):
        value, reasons = Decimal(0), []
        for sid, quantity in sorted(self.holdings.items()):
            if self.states.get(sid) == STATE_CARRY:
                mark = self.carry_marks.get(sid)
                if mark is None:
                    reasons.append(f'CARRY_PRICE_UNOBSERVED:{sid}')
                else:
                    value += quantity * mark[1]
        return value, reasons

    def _receivable_total(self):
        return _sum_exact(item.amount for item in self.receivables.values())

    # -- reselection at S (after the close) --------------------------------------------------------------------
    @_precision
    def decide(self, rebalance: Rebalance) -> dict:
        session = self._require_session()
        if session != rebalance.signal_date:
            raise LedgerError('DECISION_NOT_ON_SIGNAL_DATE')
        if self._signal is not None:
            raise LedgerError('PREVIOUS_REBALANCE_NOT_EXECUTED')
        released = self.reserved_cash
        self.reserved_cash = Decimal(0)
        held_value, reasons, stale = Decimal(0), [], []
        for sid, quantity in sorted(self.holdings.items()):
            if sid in self.states:
                continue
            mark = self.last_price.get(sid)
            if mark is None:
                reasons.append(f'UNPRICED_POSITION:{sid}')
                continue
            if self._close_today(sid) is None:
                stale.append(sid)
            held_value += quantity * mark[1]
        carry_value, carry_reasons = self._carry_value()
        reasons += carry_reasons
        receivables = self._receivable_total()
        selected = rebalance.selected
        record = dict(signal_date=rebalance.signal_date, execution_date=rebalance.execution_date,
                      selected=selected, slots=len(selected), released_reserved_cash=released,
                      frozen_positions={sid: self.states.get(sid, 'CONVERTED') for sid in sorted(self.holdings)
                                        if self.frozen(sid)},
                      stale_signal_marks=tuple(stale), receivables_excluded=receivables,
                      carry_value_excluded=carry_value, signal_prices={}, targets={}, orders={})
        if reasons:
            unfilled = tuple(Unfilled(session, sid, None, None, INCOMPLETE_SIGNAL_NAV, session) for sid in selected)
            self.unfilled.extend(unfilled)
            record.update(status=INCOMPLETE_SIGNAL_NAV, reasons=tuple(sorted(set(reasons))), nav_at_signal=None,
                          target_base=None, target_value_per_name=None, slot_cash_held_back_at_signal=None,
                          unfilled_at_signal=unfilled)
            return record
        target_base = _sum_exact((self.cash, held_value))
        nav = target_base + receivables + carry_value
        per_name = target_base / len(selected) if selected else Decimal(0)
        targets, prices, unfilled = {}, {}, []
        for sid in selected:
            if self.frozen(sid):
                unfilled.append(Unfilled(session, sid, None, None, UNSETTLED_CORPORATE_ACTION, session))
                continue
            close = self._close_today(sid)
            if close is None:
                unfilled.append(Unfilled(session, sid, None, None, MISSING_SIGNAL_PRICE, session))
                continue
            prices[sid] = close
            targets[sid] = per_name / close
        skipped = {item.security_id for item in unfilled}
        # A selected name that gets no order and holds nothing tradable keeps its slot in cash.
        holdback = _sum_exact(tuple(per_name for sid in skipped if sid not in self.holdings or self.frozen(sid)))
        orders = {}
        tradable = {sid for sid in self.holdings if not self.frozen(sid)}
        for sid in sorted(set(targets) | tradable):
            if sid in skipped:
                continue  # Selected but no target: keep any existing holding as it is.
            delta = _sum_exact((targets.get(sid, Decimal(0)), self.holdings.get(sid, Decimal(0)).copy_negate()))
            if delta:
                orders[sid] = delta
        self.pending, self.requested = dict(orders), dict(orders)
        self._planned_value = {sid: _product_exact(quantity, prices[sid]) for sid, quantity in orders.items()
                               if quantity > 0}
        self._signal_holdback = holdback
        self._signal = rebalance
        self.unfilled.extend(unfilled)
        record.update(status='OK', reasons=(), nav_at_signal=nav, target_base=target_base,
                      slot_cash_held_back_at_signal=holdback,
                      target_value_per_name=per_name, signal_prices=prices, targets=targets, orders=dict(orders),
                      unfilled_at_signal=tuple(unfilled))
        return record

    # -- execution at T (open) --------------------------------------------------------------------------------
    def _trade_amount(self, quantity, price):
        gross = _product_exact(quantity.copy_abs(), price)
        fee = _product_exact(gross, self.cost_rate)
        return gross, fee, _sum_exact((gross, fee))

    def _fill(self, sid, quantity, price, signal_date):
        gross, fee, debit = self._trade_amount(quantity, price)
        change = _sum_exact((gross, fee.copy_negate())) if quantity < 0 else debit.copy_negate()
        cash = _sum_exact((self.cash, change))
        if cash < 0:
            raise LedgerError('NEGATIVE_CASH')
        self.cash = cash
        self.holdings[sid] = _sum_exact((self.holdings.get(sid, Decimal(0)), quantity))
        if not self.holdings[sid]:
            del self.holdings[sid]
        if quantity > 0:  # A buy between a termination's effective date and its activation (review F1).
            for pending in self._entitlements.values():
                if pending.terminating and pending.security_id == sid:
                    pending.bought = _sum_exact((pending.bought, quantity))
                    pending.cost = _sum_exact((pending.cost, debit))
        return Fill(self._session, sid, quantity, price, gross, fee, signal_date)

    @_precision
    def _open_nav(self, opens):
        value = _sum_exact((self.cash, self._receivable_total()))
        carry, reasons = self._carry_value()
        value += carry
        for sid, quantity in sorted(self.holdings.items()):
            if sid in self.states:
                continue
            price = opens.get(sid)
            if price is None:
                mark = self.last_price.get(sid)
                if mark is None:
                    reasons.append(f'UNPRICED_POSITION:{sid}')
                    continue
                price = mark[1]
            value += quantity * price
        return None if reasons else value

    @_precision
    def execute_open(self, opens: Mapping[str, Decimal | None], suspended=frozenset()) -> dict:
        """Fill the pending orders of the current rebalance at this T open; drop whatever does not fill."""
        session = self._require_session()
        rebalance = self._signal
        if rebalance is None:
            raise LedgerError('NO_PENDING_REBALANCE')
        if session != rebalance.execution_date:
            raise LedgerError('ORDERS_EXECUTE_ONLY_AT_T_OPEN')
        signal = rebalance.signal_date
        open_nav = self._open_nav(opens)
        available, unfilled = {}, []
        for sid, quantity in sorted(self.pending.items()):
            if self.frozen(sid):
                reason = UNSETTLED_CORPORATE_ACTION
            elif sid in suspended:
                reason = SUSPENDED
            elif opens.get(sid) is None:
                reason = UNAVAILABLE_OPEN
            else:
                available[sid] = quantity
                continue
            unfilled.append(Unfilled(session, sid, self.requested[sid], quantity, reason, signal))
        fills = []
        for sid, quantity in available.items():
            if quantity < 0:
                if -quantity > self.holdings.get(sid, Decimal(0)):
                    raise LedgerError('SELL_EXCEEDS_HOLDING')
                fills.append(self._fill(sid, quantity, opens[sid], signal))
        buys = {sid: quantity for sid, quantity in available.items() if quantity > 0}
        requested = _sum_exact(self._trade_amount(quantity, opens[sid])[2] for sid, quantity in buys.items())
        # Cash planned at S for slots that did not fill stays cash: other names' price drift cannot use it.
        holdback = _sum_exact((self._signal_holdback,) + tuple(
            self._planned_value[item.security_id] for item in unfilled if item.security_id in self._planned_value))
        budget = max(Decimal(0), _sum_exact((self.cash, self.reserved_cash.copy_negate(), holdback.copy_negate())))
        ratio = min(Decimal(1), budget / requested) if requested else Decimal(0)
        for sid, quantity in buys.items():
            filled = quantity * ratio
            if filled:
                fills.append(self._fill(sid, filled, opens[sid], signal))
            remainder = _sum_exact((quantity, filled.copy_negate()))
            if remainder > 0:
                unfilled.append(Unfilled(session, sid, self.requested[sid], remainder, INSUFFICIENT_CASH, signal,
                                         partial=bool(filled)))
        if self.cash < self.reserved_cash:
            raise LedgerError('RESERVED_CASH_SPENT')
        self.pending, self.requested, self._signal = {}, {}, None
        self._planned_value, self._signal_holdback = {}, Decimal(0)
        self.fills.extend(fills)
        self.unfilled.extend(unfilled)
        self._day_fills.extend(fills)
        return dict(open_nav_before_trades=open_nav, fills=tuple(fills), unfilled=tuple(unfilled),
                    costs=_sum_exact(fill.fee for fill in fills),
                    gross_traded=_sum_exact(fill.gross for fill in fills), cash_ratio=ratio if buys else None,
                    slot_cash_held_back=holdback)

    def drop_unexecuted(self):
        """Orders whose T is outside the run are cancelled, not carried."""
        orders, self.pending, self.requested, self._signal = dict(self.pending), {}, {}, None
        self._planned_value, self._signal_holdback = {}, Decimal(0)
        return orders

    # -- daily valuation (close) ------------------------------------------------------------------------------
    @_precision
    def snapshot(self, *, with_positions: bool = True, valuation: str = VALUATION_CLOSE) -> dict:
        """Close (or terminal open) valuation. with_positions=False keeps every total and flag but omits the
        per-position detail."""
        if valuation not in VALUATIONS:
            raise LedgerError('UNKNOWN_VALUATION')
        fresh_field = 'close' if valuation == VALUATION_CLOSE else 'open'
        session = self._require_session()
        flags, reasons, positions = list(self._day_flags), [], {}
        market, carry = Decimal(0), Decimal(0)
        for sid, quantity in sorted(self.holdings.items()):
            state = self.states.get(sid, STATE_HELD)
            price = price_date = value = None
            stale = False
            if state == STATE_CARRY:
                mark = self.carry_marks.get(sid)
                flags.append(f'CARRY_SCENARIO:{sid}')
                if mark is None:
                    reasons.append(f'CARRY_PRICE_UNOBSERVED:{sid}')
                else:
                    price_date, price = mark
                    value = quantity * price
                    carry += value
            elif state == STATE_LOSS:
                flags.append(f'LOSS_SCENARIO:{sid}')
                price, value = Decimal(0), Decimal(0)
            else:
                mark = self.last_price.get(sid)
                if mark is None:
                    reasons.append(f'UNPRICED_POSITION:{sid}')
                else:
                    price_date, price = mark[0], mark[1]
                    value = quantity * price
                    market += value
                    if not (mark[0] == session and mark[2] == fresh_field):
                        stale = True
                        flags.append(f'STALE_MARK:{sid}')
            positions[sid] = dict(quantity=quantity, state=state, price=price, price_date=price_date, value=value,
                                  stale=stale)
        receivables = self._receivable_total()
        nav = None if reasons else self.cash + receivables + market + carry
        return dict(date=session, valuation=valuation, nav=nav, status='INCOMPLETE_NAV' if reasons else 'COMPLETE',
                    reasons=tuple(sorted(set(reasons))), cash=self.cash, reserved_cash=self.reserved_cash,
                    spendable_cash=_sum_exact((self.cash, self.reserved_cash.copy_negate())),
                    receivables=receivables,
                    receivables_detail={f'{kind}:{event_id}': item.amount
                                        for (kind, event_id), item in sorted(self.receivables.items())},
                    market_value=market, carry_value=carry, positions=positions if with_positions else None,
                    fills=tuple(self._day_fills), costs=_sum_exact(fill.fee for fill in self._day_fills),
                    flags=tuple(flags), events=tuple(self._day_events))


# -- pure driver ------------------------------------------------------------------------------------------------
def _sessions(sessions):
    days = tuple(_date(day) for day in sessions)
    if not days:
        raise LedgerError('NO_SESSIONS')
    if any(a >= b for a, b in zip(days, days[1:])):
        raise LedgerError('SESSIONS_MUST_INCREASE')
    return days


def _rebalances(rebalances, sessions):
    known = set(sessions)
    rows = tuple(rebalances)
    for row in rows:
        if not isinstance(row, Rebalance):
            raise LedgerError('REBALANCE_MUST_BE_REBALANCE')
        _date(row.signal_date, 'SIGNAL_DATE')
        _date(row.execution_date, 'EXECUTION_DATE')
        if row.signal_date not in known or row.execution_date not in known:
            raise LedgerError('REBALANCE_DATE_NOT_A_SESSION')
        if row.execution_date <= row.signal_date:
            raise LedgerError('EXECUTION_MUST_FOLLOW_SIGNAL')
        selected = tuple(_security(sid) for sid in row.selected)
        if len(set(selected)) != len(selected):
            raise LedgerError('DUPLICATE_SELECTED_SECURITY')
    for a, b in zip(rows, rows[1:]):
        if b.signal_date < a.execution_date:
            raise LedgerError('REBALANCES_OVERLAP_OR_UNORDERED')
    return rows


def index_price_rows(rows) -> dict[date, dict[str, PriceRow]]:
    """Validate raw USD price rows and index them by session and security."""
    index: dict[date, dict[str, PriceRow]] = {}
    for row in rows:
        day = _date(row.get('date'), 'PRICE_DATE')
        sid = _security(row.get('security_id'))
        if row.get('price_basis') != PRICE_BASIS_RAW:
            raise LedgerError('PRICE_BASIS_NOT_RAW')
        if row.get('currency', CURRENCY) != CURRENCY:
            raise LedgerError('PRICE_CURRENCY_NOT_USD')
        suspended = row.get('suspended', False)
        if type(suspended) is not bool:
            raise LedgerError('INVALID_SUSPENDED_FLAG')
        values = {field: None if row.get(field) is None else _decimal(row[field], 'PRICE', positive=True)
                  for field in ('open', 'close')}
        if sid in index.setdefault(day, {}):
            raise LedgerError('DUPLICATE_PRICE_KEY')
        index[day][sid] = PriceRow(values['open'], values['close'], suspended)
    return index


_BAND = {Split: 0, Dividend: 1, Settlement: 2, SettlementConfirmation: 2}
_SNAPSHOT, _ACTIVATION, _CONFIRMATION = 0, 1, 2  # Steps of one security's settlements within band 2 on one date.


def _delivery_levels(edges):
    """Rank securities so that, on one date, a security receiving shares by corporate action is handled after every
    security delivering into it, whatever the event_ids (review F1/F5). Bounded, so a cycle cannot loop."""
    level: dict[str, int] = {}
    for _ in range(len(edges)):
        changed = False
        for source, target in edges:
            if level.get(target, 0) <= level.get(source, 0):
                level[target], changed = level.get(source, 0) + 1, True
        if not changed:
            break
    return level


def _event_schedule(events):
    """Sorted (trigger date, band, delivery level, step, event_id, event) entries."""
    settlements, seen, confirmations, schedule, edges = {}, set(), set(), [], set()
    events = tuple(events)
    for event in events:
        if type(event) not in _BAND:
            raise LedgerError('UNKNOWN_EVENT_TYPE')
        _security(event.event_id)
        if isinstance(event, SettlementConfirmation):
            if event.event_id in confirmations:
                raise LedgerError('DUPLICATE_CONFIRMATION')
            confirmations.add(event.event_id)
            _date(event.available_at, 'AVAILABLE_AT')
            continue
        if event.event_id in seen:
            raise LedgerError('DUPLICATE_EVENT_ID')
        seen.add(event.event_id)
        _security(event.security_id)
        _date(event.effective_date, 'EFFECTIVE_DATE')
        if isinstance(event, Split):
            _decimal(event.ratio, 'SPLIT_RATIO', positive=True)
        elif isinstance(event, Dividend):
            _dividend_amounts(event)
            if event.pay_date is not None:
                _date(event.pay_date, 'PAY_DATE')
                if event.pay_date < event.effective_date:
                    raise LedgerError('PAY_DATE_PRECEDES_EX_DATE')
        else:
            _validate_settlement(event)
            settlements[event.event_id] = event
            if event.new_security_id is not None:
                edges.add((event.security_id, event.new_security_id))
    for event in events:
        if isinstance(event, SettlementConfirmation):
            if event.event_id not in settlements:
                raise LedgerError('CONFIRMATION_WITHOUT_SETTLEMENT')
            if event.new_security_id is not None:
                edges.add((settlements[event.event_id].security_id, event.new_security_id))
    level = _delivery_levels(sorted(edges))
    for event in events:
        band = _BAND[type(event)]
        if isinstance(event, (Split, Dividend)):
            schedule.append((event.effective_date, band, 0, 0, event.event_id, event))
        elif isinstance(event, Settlement):
            rank = level.get(event.security_id, 0)
            # The entitlement is fixed before the effective-date open; terms act from activation (review F1).
            schedule.append((event.effective_date, band, rank, _SNAPSHOT, event.event_id, _EntitlementSnapshot(event)))
            schedule.append((activation_date(event), band, rank, _ACTIVATION, event.event_id, event))
        else:
            settlement = settlements[event.event_id]
            trigger = max(event.available_at, activation_date(settlement))
            schedule.append((trigger, band, level.get(settlement.security_id, 0), _CONFIRMATION, event.event_id, event))
    schedule.sort(key=lambda item: item[:5])
    return schedule


def _apply(ledger, event):
    if isinstance(event, _EntitlementSnapshot):
        ledger.record_entitlement(event.event)
    elif isinstance(event, Split):
        ledger.apply_split(event)
    elif isinstance(event, Dividend):
        ledger.apply_dividend(event)
    elif isinstance(event, Settlement):
        ledger.apply_settlement(event)
    else:
        ledger.confirm_settlement(event)


def run_ledger(sessions: Sequence[date], rebalances: Sequence[Rebalance], prices, events=(), *, scenario: str,
               cost_bps=DEFAULT_COST_BPS, initial_capital=DEFAULT_INITIAL_CAPITAL,
               cash_interest: str = CASH_INTEREST_ZERO, end: date | None = None,
               end_valuation: str = VALUATION_CLOSE, daily_positions: bool = True) -> dict:
    """Replay one scenario from the first signal date S to `end` (default: the last supplied session).

    end_valuation: CLOSE (the run ends after `end`'s close) or OPEN (terminal valuation at `end`'s open: pre-open
    events, open marks, no trades, no decision; `end` must be a session; a rebalance whose T is `end` is cancelled).

    sessions: the verified trading sessions (strictly increasing dates).
    rebalances: Rebalance rows in order; the run starts at the first signal date with all capital in cash.
    prices: iterable of mappings {date, security_id, open, close, suspended?, price_basis='RAW', currency?='USD'}.
    events: Split / Dividend / Settlement / SettlementConfirmation objects; each acts on its first session on or after
    its trigger date (ex/effective date, max(effective_date, available_at), or the confirmation's own date).
    daily_positions=False drops the per-position detail from daily rows (totals and flags stay) for large groups.
    """
    days_all = _sessions(sessions)
    rows = _rebalances(rebalances, days_all)
    if not rows:
        raise LedgerError('NO_REBALANCE')
    start = rows[0].signal_date
    end = days_all[-1] if end is None else _date(end, 'END')
    if end < start:
        raise LedgerError('END_BEFORE_START')
    if end_valuation not in VALUATIONS:
        raise LedgerError('UNKNOWN_VALUATION')
    days = [day for day in days_all if start <= day <= end]
    if end_valuation == VALUATION_OPEN and days[-1] != end:
        raise LedgerError('END_NOT_A_SESSION')
    price_index = index_price_rows(prices)
    schedule = _event_schedule(events)
    ledger = Ledger(scenario=scenario, initial_cash=initial_capital, cost_bps=cost_bps, cash_interest=cash_interest)
    by_signal = {row.signal_date: row for row in rows}
    by_execution = {row.execution_date: row for row in rows}
    records: dict[date, dict] = {}
    daily, cursor = [], 0
    for day in days:
        ledger.begin_session(day)
        while cursor < len(schedule) and schedule[cursor][0] <= day:
            _apply(ledger, schedule[cursor][-1])
            cursor += 1
        ledger.pay_due()
        rows_today = price_index.get(day, {})
        if end_valuation == VALUATION_OPEN and day == end:
            ledger.observe(rows_today, opens_only=True)
            daily.append(ledger.snapshot(with_positions=daily_positions, valuation=VALUATION_OPEN))
            break
        if day in by_execution and by_execution[day].signal_date in records:
            record = records[by_execution[day].signal_date]
            if record['status'] == 'OK':
                executed = ledger.execute_open({sid: row.open for sid, row in rows_today.items()},
                                               frozenset(sid for sid, row in rows_today.items() if row.suspended))
                record.update(execution_status='EXECUTED', **executed)
            else:
                record.update(execution_status='NO_ORDERS', open_nav_before_trades=None, fills=(), unfilled=(),
                              costs=Decimal(0), gross_traded=Decimal(0), cash_ratio=None, slot_cash_held_back=None)
        ledger.observe(rows_today)
        daily.append(ledger.snapshot(with_positions=daily_positions))
        if day in by_signal:
            records[day] = ledger.decide(by_signal[day])
    for record in records.values():
        if 'execution_status' not in record:
            record.update(execution_status='AFTER_RUN_END', cancelled_orders=ledger.drop_unexecuted()
                          if record['status'] == 'OK' else {}, open_nav_before_trades=None, fills=(), unfilled=(),
                          costs=Decimal(0), gross_traded=Decimal(0), cash_ratio=None, slot_cash_held_back=None)
    fills = tuple(ledger.fills)
    return dict(engine='EXP_DECILES_LEDGER', scenario=scenario, currency=CURRENCY,
                initial_capital=ledger.initial_cash, cost_bps=ledger.cost_bps, cash_interest=CASH_INTEREST_ZERO,
                start=days[0], end=days[-1], end_valuation=end_valuation,
                first_fill_date=fills[0].session if fills else None,
                status='COMPLETE' if all(row['nav'] is not None for row in daily) else 'INCOMPLETE_NAV',
                daily=daily, rebalances=[records[row.signal_date] for row in rows if row.signal_date in records],
                not_reached=tuple(row.signal_date for row in rows if row.signal_date not in records),
                fills=fills, unfilled=tuple(ledger.unfilled), conflicts=tuple(ledger.conflicts),
                total_costs=_sum_exact(fill.fee for fill in fills),
                total_gross_traded=_sum_exact(fill.gross for fill in fills),
                instrument_fees=tuple(ledger.instrument_fees),
                total_instrument_fees=_sum_exact(item['amount'] for item in ledger.instrument_fees))


def run_scenarios(sessions, rebalances, prices, events=(), **kwargs) -> dict[str, dict]:
    """Both termination scenarios from the same selections, prices and events."""
    if 'scenario' in kwargs:
        raise LedgerError('SCENARIO_IS_SET_BY_RUN_SCENARIOS')
    prices, events, rebalances = tuple(prices), tuple(events), tuple(rebalances)
    return {scenario: run_ledger(sessions, rebalances, prices, events, scenario=scenario, **kwargs)
            for scenario in SCENARIOS}
