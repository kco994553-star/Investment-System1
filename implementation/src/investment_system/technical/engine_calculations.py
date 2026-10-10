"""RAM-only values from the three existing TechnicalEngine expressions.

Uses the synthetic #105 input gate. No new indicator, threshold, engine change,
provider, serializer or persistence connection.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime
import math
from typing import Literal

from .daily_input import DailyInputSeries, PreparedDailyReturns, prepare_daily_returns


@dataclass(frozen=True)
class EngineReturnCalculations:
    population_stddev: float = field(repr=False)
    last_return: float = field(repr=False)
    last5_sum: float = field(repr=False)
    return_count: int
    role: Literal['EXISTING_ENGINE_INPUTS'] = 'EXISTING_ENGINE_INPUTS'


@dataclass(frozen=True)
class DailyEngineCalculationsResult:
    state: Literal['DEMO', 'NOT_AVAILABLE']
    data: EngineReturnCalculations | None = field(repr=False)
    prepared: PreparedDailyReturns


def calculate_daily_engine_inputs(series: DailyInputSeries, as_of: datetime) -> DailyEngineCalculationsResult:
    """Expose the unchanged expressions over exactly the adapter's returns.

    All returns means all returns supplied to the engine: #105 keeps the last
    20. Short, nonempty input keeps the existing engine's arithmetic semantics.
    This is synthetic evidence, not a validated model or a live recommendation.
    """
    prepared = prepare_daily_returns(series, as_of)
    if prepared.state != 'READY':
        return DailyEngineCalculationsResult('NOT_AVAILABLE', None, prepared)
    rets = prepared.returns
    try:
        vol = (sum((r - sum(rets) / len(rets)) ** 2 for r in rets) / len(rets)) ** 0.5
        last = rets[-1]
        last5 = sum(rets[-5:])
        if not all(math.isfinite(value) for value in (vol, last, last5)):
            raise ArithmeticError
    except ArithmeticError:
        failed = replace(prepared, state='NOT_AVAILABLE', returns=None, return_count=0,
                         reason_codes=('CALCULATION_ERROR',))
        return DailyEngineCalculationsResult('NOT_AVAILABLE', None, failed)
    return DailyEngineCalculationsResult('DEMO', EngineReturnCalculations(vol, last, last5, len(rets)), prepared)
