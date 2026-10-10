"""Pure, RAM-only V factor calculations using the adopted v1 mappings.

No DCF solver, price-to-multiple definition, history/context rubric, aggregate,
currency conversion, or share-basis conversion is introduced here. Callers must
confirm a common currency and per-share basis for paths that use price. Results
retain neither price nor inputs and have no persistence or public serializer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType, SimpleNamespace
from typing import Callable, Literal, Mapping

from . import raw_map
from .scoring_standard import (
    SCORING_CALIBRATION,
    SCORING_STANDARD_STATUS,
    SCORING_STANDARD_VERSION,
)


UNDEFINED_PRICE_DEFINITIONS = (
    "DCF_SOLVER",
    "REVERSE_DCF_SOLVER",
    "OWN_MULTIPLE_PRICE_MAPPING",
    "HISTORICAL_VALUATION_PRICE_MAPPING",
    "SECTOR_CONTEXT_PRICE_MAPPING",
    "THEME_PRICE_MAPPING",
)

CalculationState = Literal["CALCULATED", "PASSTHROUGH", "NOT_AVAILABLE"]


@dataclass(frozen=True)
class VPriceInputs:
    """Caller-supplied inputs; basis confirmation performs no conversion."""

    dcf_value: float | None = field(default=None, repr=False)
    eps: float | None = field(default=None, repr=False)
    revenue: float | None = field(default=None, repr=False)
    revenue_prev: float | None = field(default=None, repr=False)
    reverse_dcf_implied_growth: float | None = field(default=None, repr=False)
    own_multiple: float | None = field(default=None, repr=False)
    peer_median_multiple: float | None = field(default=None, repr=False)
    hist_valuation_percentile: float | None = field(default=None, repr=False)
    sector_context_score: float | None = field(default=None, repr=False)
    theme_premium_score: float | None = field(default=None, repr=False)
    basis_confirmed: bool = False


@dataclass(frozen=True)
class FactorCalculation:
    score: float | None = field(repr=False)
    state: CalculationState
    reason: str


@dataclass(frozen=True)
class VPriceResult:
    factors: Mapping[str, FactorCalculation] = field(repr=False)
    role: str = field(default="RAM_ONLY_V1", init=False)
    standard: str = field(default=SCORING_STANDARD_VERSION, init=False)
    calibration: str = field(default=SCORING_CALIBRATION, init=False)
    standard_status: str = field(default=SCORING_STANDARD_STATUS, init=False)
    undefined_price_definitions: tuple[str, ...] = field(default=UNDEFINED_PRICE_DEFINITIONS, init=False)


def _finite_number(value: object) -> bool:
    if type(value) not in (float, int):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def _checked(value: float | int) -> _CheckedNumber:
    # Integer arithmetic has no infinity and must retain its exact precision.
    if isinstance(value, float) and not isfinite(value):
        raise ArithmeticError("non-finite intermediate")
    return _CheckedNumber(value)


def _value(number):
    return number._value if isinstance(number, _CheckedNumber) else number


class _CheckedNumber:
    """Check every helper intermediate before its legacy clip can hide overflow.

    Original int/float arithmetic preserves exact integers and the approved
    expression's operation order and rounding; only float results can overflow.
    """

    __slots__ = ("_value",)

    def __init__(self, value: float | int):
        self._value = value

    def __bool__(self):
        return bool(self._value)

    def __float__(self):
        return float(self._value)

    def __eq__(self, other):
        return self._value == _value(other)

    def __lt__(self, other):
        return self._value < _value(other)

    def __gt__(self, other):
        return self._value > _value(other)

    def __add__(self, other):
        return _checked(self._value + _value(other))

    def __radd__(self, other):
        return _checked(_value(other) + self._value)

    def __sub__(self, other):
        return _checked(self._value - _value(other))

    def __rsub__(self, other):
        return _checked(_value(other) - self._value)

    def __mul__(self, other):
        return _checked(self._value * _value(other))

    def __rmul__(self, other):
        return _checked(_value(other) * self._value)

    def __truediv__(self, other):
        return _checked(self._value / _value(other))

    def __rtruediv__(self, other):
        return _checked(_value(other) / self._value)


def _unavailable(reason: str) -> FactorCalculation:
    return FactorCalculation(None, "NOT_AVAILABLE", reason)


def _price_reason(inputs: VPriceInputs, price: float | None) -> str | None:
    if price is None:
        return "MISSING_PRICE"
    if not _finite_number(price) or price <= 0:
        return "INVALID_PRICE"
    if inputs.basis_confirmed is not True:
        return "BASIS_UNCONFIRMED"
    return None


def _calculate(
    helper: Callable[[SimpleNamespace], float | None], raw: SimpleNamespace,
) -> FactorCalculation:
    try:
        score = helper(raw)
        if score is None:
            return _unavailable("MISSING_INPUT")
        if not isfinite(score):
            return _unavailable("CALCULATION_ERROR")
        return FactorCalculation(float(score), "CALCULATED", "APPROVED_V1_MAPPING")
    except ArithmeticError:
        return _unavailable("CALCULATION_ERROR")


def _intrinsic(
    inputs: VPriceInputs, price: float | None,
    helper: Callable[[SimpleNamespace], float | None],
) -> FactorCalculation:
    reason = _price_reason(inputs, price)
    if reason is not None:
        return _unavailable(reason)
    dcf = inputs.dcf_value
    if dcf is not None and not _finite_number(dcf):
        return _unavailable("INVALID_INPUT")
    if dcf:
        raw = SimpleNamespace(price=_CheckedNumber(price), dcf_value=_CheckedNumber(dcf), eps=None)
    else:
        eps = inputs.eps
        if eps is not None and not _finite_number(eps):
            return _unavailable("INVALID_INPUT")
        if eps is None or eps <= 0:
            return _unavailable("MISSING_INPUT")
        raw = SimpleNamespace(price=_CheckedNumber(price), dcf_value=None, eps=_CheckedNumber(eps))
    return _calculate(helper, raw)


def _reverse_dcf(inputs: VPriceInputs, price: float | None) -> FactorCalculation:
    implied = inputs.reverse_dcf_implied_growth
    if implied is not None:
        if not _finite_number(implied):
            return _unavailable("INVALID_INPUT")
        raw_price = raw_eps = None
    else:
        reason = _price_reason(inputs, price)
        if reason is not None:
            return _unavailable(reason)
        eps = inputs.eps
        if eps is not None and not _finite_number(eps):
            return _unavailable("INVALID_INPUT")
        if eps is None or eps <= 0:
            return _unavailable("MISSING_INPUT")
        raw_price, raw_eps = _CheckedNumber(price), _CheckedNumber(eps)
    revenue, previous = inputs.revenue, inputs.revenue_prev
    if any(value is not None and not _finite_number(value) for value in (revenue, previous)):
        return _unavailable("INVALID_INPUT")
    if revenue is None or previous is None or previous == 0:
        return _unavailable("MISSING_INPUT")
    raw = SimpleNamespace(
        price=raw_price, eps=raw_eps,
        reverse_dcf_implied_growth=_CheckedNumber(implied) if implied is not None else None,
        revenue=_CheckedNumber(revenue), revenue_prev=_CheckedNumber(previous),
    )
    return _calculate(raw_map._reverse_dcf_score, raw)


def _peer_score(raw: SimpleNamespace) -> float:
    # The exact existing map_raw expression; no price-to-multiple inference.
    return raw_map._clip_score(
        50.0 + ((raw.peer_median_multiple - raw.own_multiple) / raw.peer_median_multiple) / 0.3 * 50.0,
    )


def _peer_relative(inputs: VPriceInputs) -> FactorCalculation:
    own, peer = inputs.own_multiple, inputs.peer_median_multiple
    if any(value is not None and not _finite_number(value) for value in (own, peer)):
        return _unavailable("INVALID_INPUT")
    if not own or not peer:
        return _unavailable("MISSING_INPUT")
    return _calculate(_peer_score, SimpleNamespace(
        own_multiple=_CheckedNumber(own), peer_median_multiple=_CheckedNumber(peer),
    ))


def _passthrough(score: float | None) -> FactorCalculation:
    if score is None:
        return _unavailable("UNDEFINED_PRICE_MAPPING")
    if not _finite_number(score) or not 0 <= score <= 100:
        return _unavailable("INVALID_INPUT")
    return FactorCalculation(float(score), "PASSTHROUGH", "SUPPLIED_SCORE")


def calculate_v_price_factors(inputs: VPriceInputs, *, price: float | None) -> VPriceResult:
    """Calculate separate v1 factors with an explicit transient price.

    Only dependencies used by the selected legacy branch are validated. A
    supplied implied-growth value, including zero, needs no price or basis
    confirmation. Supplied multiples and scores also remain independent of
    price. Missing, invalid, unconfirmed, or overflowing paths return no score
    and a fixed reason; no missing component is filled with zero.
    """

    factors = {
        "fundamental_value": _intrinsic(inputs, price, raw_map._central_value_score),
        "peer_relative_value": _peer_relative(inputs),
        "historical_valuation": _passthrough(inputs.hist_valuation_percentile),
        "sector_context": _passthrough(inputs.sector_context_score),
        "theme_premium_discount": _passthrough(inputs.theme_premium_score),
        "reverse_dcf": _reverse_dcf(inputs, price),
        "margin_of_safety": _intrinsic(inputs, price, raw_map._mos_score),
    }
    return VPriceResult(MappingProxyType(factors))
