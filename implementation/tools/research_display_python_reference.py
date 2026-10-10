#!/usr/bin/env python3
"""Emit fixed synthetic research-display reference vectors, without provider input.

This standalone reference is a cross-language test aid. It is not imported by the
application, model, TSV/QGV pipeline, or a public-data serializer. It uses only
the Python standard library; its CLI deliberately accepts no market-data input.
"""
from __future__ import annotations

import argparse
import json
import math


ROLE = 'RESEARCH_DISPLAY_ONLY'
_SMA_PERIODS = (5, 20, 60, 120, 240)
_SYNTHETIC_START = 1893456000  # 2030-01-01; synthetic ordering, not a selected data period.


def _mean(values):
    return sum(values) / len(values)


def _sma(prices, period):
    values, reasons, window = [], [], []
    for price in prices:
        if price is None:
            window = []
        else:
            window.append(price)
            window = window[-period:]
        value = _mean(window) if len(window) == period else None
        values.append(value)
        reasons.append(None if value is not None else 'WARMUP')
    return values, reasons


def _ema(prices, period):
    values, reasons, seed = [], [], []
    previous = None
    alpha = 2 / (period + 1)
    for price in prices:
        value = None
        if price is None:
            seed, previous = [], None
        elif previous is None:
            seed.append(price)
            if len(seed) == period:
                value = previous = _mean(seed)
                seed = []
        else:
            value = previous = previous + alpha * (price - previous)
        values.append(value)
        reasons.append(None if value is not None else 'WARMUP')
    return values, reasons


def _rsi(prices):
    values, reasons, gains, losses = [], [], [], []
    previous = gain = loss = None
    for price in prices:
        value, reason = None, 'WARMUP'
        if price is None:
            previous = gain = loss = None
            gains, losses = [], []
        elif previous is not None:
            change = price - previous
            today_gain, today_loss = max(change, 0), max(-change, 0)
            if gain is None:
                gains.append(today_gain)
                losses.append(today_loss)
                if len(gains) == 14:
                    gain, loss = _mean(gains), _mean(losses)
            else:
                gain += (today_gain - gain) / 14
                loss += (today_loss - loss) / 14
            if gain is not None:
                total = gain + loss
                if total == 0:
                    reason = 'ZERO_TOTAL_CHANGE'
                else:
                    value, reason = 100 * gain / total, None
        if price is not None:
            previous = price
        values.append(value)
        reasons.append(reason)
    return values, reasons


def _atr(bars, prices, price_basis):
    if price_basis != 'RAW_CLOSE':
        return [None] * len(bars), ['OHLC_BASIS_UNCONFIRMED'] * len(bars)
    values, reasons, seed = [], [], []
    previous = None
    for i, bar in enumerate(bars):
        value, reason = None, 'WARMUP'
        high, low = bar['high'], bar['low']
        if prices[i] is None or high is None or low is None:
            seed, previous = [], None
            reason = 'OHLC_MISSING'
        elif i == 0 or prices[i - 1] is None:
            seed, previous = [], None
        else:
            true_range = max(high - low, abs(high - prices[i - 1]), abs(low - prices[i - 1]))
            if previous is None:
                seed.append(true_range)
                if len(seed) == 14:
                    value = previous = _mean(seed)
                    seed = []
            else:
                value = previous = previous + (true_range - previous) / 14
            if value is not None:
                reason = None
        values.append(value)
        reasons.append(reason)
    return values, reasons


def _series(name, values, reasons, default_visible=None):
    return {
        'indicator_id': name,
        'role': ROLE,
        'values': values,
        'unavailable_reasons': reasons,
        'default_visible': default_visible,
        'latest_state': 'AVAILABLE' if values and values[-1] is not None else 'NOT_AVAILABLE',
    }


def _calculate(bars, price_basis):
    key = 'close' if price_basis == 'RAW_CLOSE' else 'adjusted_close'
    prices = [bar[key] if bar['session_status'] == 'COMPLETE' else None for bar in bars]
    items = [_series(f'SMA_{period}', *_sma(prices, period), period != 240) for period in _SMA_PERIODS]
    items.append(_series('EMA_20', *_ema(prices, 20)))
    items.append(_series('RSI_14', *_rsi(prices)))

    fast, slow = _ema(prices, 12)[0], _ema(prices, 26)[0]
    macd = [None if a is None or b is None else a - b for a, b in zip(fast, slow)]
    macd_reasons = ['WARMUP' if value is None else None for value in macd]
    signal, signal_reasons = _ema(macd, 9)
    histogram = [None if value is None or sig is None else value - sig for value, sig in zip(macd, signal)]
    histogram_reasons = [macd_reasons[i] if value is None else signal_reasons[i]
                         for i, value in enumerate(macd)]
    items.extend([
        _series('MACD_12_26', macd, macd_reasons),
        _series('MACD_SIGNAL_9', signal, signal_reasons),
        _series('MACD_HISTOGRAM_12_26_9', histogram, histogram_reasons),
    ])

    middle, bollinger_reasons = _sma(prices, 20)
    upper, lower = [], []
    for i, mean in enumerate(middle):
        if mean is None:
            upper.append(None)
            lower.append(None)
        else:
            sigma = math.sqrt(sum((price - mean) ** 2 for price in prices[i - 19:i + 1]) / 20)
            upper.append(mean + 2 * sigma)
            lower.append(mean - 2 * sigma)
    items.extend([
        _series('BOLL_MIDDLE_20', middle, bollinger_reasons),
        _series('BOLL_UPPER_20_2', upper, bollinger_reasons.copy()),
        _series('BOLL_LOWER_20_2', lower, bollinger_reasons.copy()),
        _series('ATR_14', *_atr(bars, prices, price_basis)),
    ])
    return {'role': ROLE, 'state': 'INPUT_RESEARCH', 'price_basis': price_basis,
            'pit_status': 'NOT_VERIFIED', 'indicators': items}


def _bars(prices, *, checkpoint=False):
    bars = []
    for i, price in enumerate(prices):
        bars.append({
            'timestamp': _SYNTHETIC_START + i * 86400,
            'session_status': 'COMPLETE',
            'close': float(price),
            'adjusted_close': float(price) / 2,
            'open': float(price),
            'high': float(price + 2 + (i % 3 if checkpoint else 0)),
            'low': float(price - 2 - (i % 2 if checkpoint else 0)),
        })
    return bars


def _case(name, bars, price_basis='RAW_CLOSE'):
    return {'case_id': name, 'synthetic': True, 'role': ROLE,
            'input': {'bars': bars, 'options': {'priceBasis': price_basis, 'includeSma240': True}},
            'expected': _calculate(bars, price_basis)}


def reference_vectors():
    """Return fresh full-index arrays for fixed, synthetic test cases only."""
    checkpoint = _bars([100 + (i * 7) % 19 + i // 6 for i in range(260)], checkpoint=True)
    wilder = _bars([100 + i for i in range(40)])
    wilder[15].update(open=111.0, close=111.0, adjusted_close=55.5, high=116.0, low=106.0)
    missing = _bars([100 + i for i in range(70)])
    missing[30].update(open=None, close=None, adjusted_close=None, high=None, low=None)
    incomplete = _bars([100 + i for i in range(35)])
    incomplete[-1]['session_status'] = 'IN_PROGRESS'
    return {
        'schema_version': 1,
        'version': 'v1',
        'synthetic': True,
        'role': ROLE,
        'display_defaults': {'sma_periods': [5, 20, 60, 120], 'optional_sma_period': 240,
                             'include_sma240': False, 'ema_period': 20, 'rsi_period': 14,
                             'macd_periods': [12, 26, 9], 'bollinger_period': 20,
                             'bollinger_population_sigma_multiplier': 2, 'atr_period': 14},
        'conventions': {
            'session_unit': 'one synthetic trading session per array index; same rule for every market',
            'warmup': 'null / NOT_AVAILABLE / WARMUP; zero is never a missing-value replacement',
            'ema_seed': 'first period closes SMA; alpha=2/(period+1)',
            'rsi_seed': 'first 14 close changes; Wilder recurrence; flat total change stays null',
            'macd_seed': 'independent full-history EMA12/EMA26; EMA9 over valid differences',
            'bollinger_sigma': 'population standard deviation of 20 closes',
            'atr_seed': 'first true range uses index 1 previous close; mean of 14 true ranges, then Wilder',
            'missing_session': 'reset seeds; do not bridge missing or incomplete observations',
            'atr_basis': 'RAW_CLOSE OHLC only; adjusted/raw mix NOT_AVAILABLE',
            'checkpoint_reference': 'technical_research_reference.json; TA-Lib 0.6.8 synthetic checkpoints',
        },
        'cases': [
            _case('checkpoint_260', checkpoint),
            _case('flat_40', _bars([100] * 40)),
            _case('rising_40', _bars([100 + i for i in range(40)])),
            _case('falling_40', _bars([200 - i for i in range(40)])),
            _case('empty', []),
            _case('one_session', _bars([100])),
            _case('short_14', _bars([100 + i for i in range(14)])),
            _case('wilder_recurrence_40', wilder),
            _case('missing_session_70', missing),
            _case('adjusted_basis_40', _bars([100 + i for i in range(40)]), 'PROVIDER_ADJUSTED_CLOSE'),
            _case('incomplete_last_35', incomplete),
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Emit fixed synthetic research-display vectors; no live inputs.')
    parser.parse_args(argv)
    print(json.dumps(reference_vectors(), indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
