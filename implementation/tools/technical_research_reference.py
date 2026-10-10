"""Generate synthetic display-only test references with TA-Lib 0.6.8.

Standalone test utility, never imported by production. Run in a disposable
environment with TA-Lib==0.6.8; no market/provider inputs or network calls.
"""
import argparse
import json
import math
from pathlib import Path


def main():
    import numpy as np
    import talib
    if talib.__version__ != '0.6.8':
        raise SystemExit('Reference generator requires TA-Lib 0.6.8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    close = np.array([100 + (i*7)%19 + i//6 for i in range(260)], dtype=float)
    high = close + np.array([2+i%3 for i in range(260)])
    low = close - np.array([2+i%2 for i in range(260)])
    arrays = {f'SMA_{n}': talib.SMA(close, n) for n in (5,20,60,120,240)}
    arrays['EMA_20'] = talib.EMA(close, 20)
    arrays['RSI_14'] = talib.RSI(close, 14)
    # Full-history EMA seeds: TA-Lib MACD() internally seeds its fast EMA later.
    # Reference the explicitly documented EMA components independently.
    line = talib.EMA(close, 12) - talib.EMA(close, 26)
    signal = np.full(260, np.nan)
    signal[25:] = talib.EMA(line[25:], 9)
    arrays.update(MACD_12_26=line, MACD_SIGNAL_9=signal, MACD_HISTOGRAM_12_26_9=line-signal)
    upper, middle, lower = talib.BBANDS(close, 20, 2, 2, 0)
    arrays.update(BOLL_MIDDLE_20=middle, BOLL_UPPER_20_2=upper, BOLL_LOWER_20_2=lower)
    arrays['ATR_14'] = talib.ATR(high, low, close, 14)
    indices = (0,3,4,13,14,18,19,20,24,25,26,32,33,34,58,59,60,118,119,120,238,239,240,259)
    expected = {name: {str(i): float(v[i]) if math.isfinite(v[i]) else None for i in indices}
                for name,v in arrays.items()}
    payload = dict(reference='TA-Lib', version=talib.__version__, numpy_version=np.__version__,
                   synthetic=True, close_recipe='100 + (i*7)%19 + i//6, i=0..259',
                   high_recipe='close + 2 + i%3', low_recipe='close - 2 - i%2',
                   macd_seed='independent full-history EMA12/EMA26; EMA9 over valid differences',
                   expected=expected)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
