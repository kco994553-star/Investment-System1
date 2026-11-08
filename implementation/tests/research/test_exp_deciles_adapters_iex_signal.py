"""adapters/iex_signal.py: IEX last regular-session trade (RAM) -> S quote records, labelled as an approximation.
Invented RAM results only (no IEX download, nothing written)."""
from decimal import Decimal

import pytest

import exp_deciles_adapter_fixtures as fx
from investment_system.research.exp_deciles import scoring
from investment_system.research.exp_deciles.adapters import iex_signal
from investment_system.research.exp_deciles.adapters.common import AdapterError

MAP = {'SEC-A': 'XQA', 'SEC-B1': 'XQB1', 'SEC-B2': 'XQB2', 'SEC-E': 'XQE', 'SEC-NOCIK': None, 'SEC-BAD': 'bad sym'}


def test_status_per_symbol_and_exact_price():
    out = iex_signal.signal_quotes(fx.iex_rows(), MAP, iex_day=fx.S, signal_day=fx.S)
    assert out['status'] == {'SEC-A': 'SUPPLIED', 'SEC-B1': 'ODD_LOT_ONLY', 'SEC-B2': 'NO_IEX_TRADE',
                             'SEC-BAD': 'UNMAPPED', 'SEC-E': 'IEX_RESULT_MISSING_SYMBOL', 'SEC-NOCIK': 'UNMAPPED'}
    assert out['quotes']['SEC-A'] == {'price': Decimal('10.4107'), 'currency': 'USD', 'month_closes': {},
                                      'price_label': 'IEX_LAST_REGULAR_TRADE_APPROX'}
    assert out['label'] == 'IEX_LAST_REGULAR_TRADE_APPROX'
    assert out['use'] == 'S_SIGNAL_PRICE_APPROXIMATION_ONLY_NEVER_T_OPEN'
    assert out['counts'] == {'IEX_RESULT_MISSING_SYMBOL': 1, 'NO_IEX_TRADE': 1, 'ODD_LOT_ONLY': 1, 'SUPPLIED': 1,
                             'UNMAPPED': 2}


def test_odd_lot_and_no_trade_are_withheld_never_priced_or_zero():
    out = iex_signal.signal_quotes(fx.iex_rows(), MAP, iex_day=fx.S, signal_day=fx.S)
    for sid, code in (('SEC-B1', 'ODD_LOT_ONLY'), ('SEC-B2', 'NO_IEX_TRADE'), ('SEC-E', 'IEX_RESULT_MISSING_SYMBOL')):
        assert out['quotes'][sid]['price'] is None and out['quotes'][sid]['withheld_reason'] == code
    # the engine records the withheld code as the quote status (no price reaches scoring)
    priced, status = scoring.engine_quotes(out['quotes'], list(out['quotes']))
    assert set(priced) == {'SEC-A'} and status['SEC-B1'] == 'ODD_LOT_ONLY' and status['SEC-B2'] == 'NO_IEX_TRADE'


def test_another_day_is_never_used():
    out = iex_signal.signal_quotes(fx.iex_rows(), MAP, iex_day='2018-02-15', signal_day=fx.S)
    assert set(out['status'].values()) == {'IEX_DAY_NOT_SIGNAL_DAY'}
    assert all(q['price'] is None for q in out['quotes'].values())


def test_malformed_result_is_refused():
    for rows in ({'XQA': ('ROUND', 0)}, {'XQA': ('ROUND', 1.5)}, {'XQA': ('LAST', 100)}, {'XQA': 'ROUND'},
                 {'XQA': ('ROUND', 10 ** 11)}):
        with pytest.raises(AdapterError, match='IEX_RESULT_INVALID'):
            iex_signal.signal_quotes(rows, {'SEC-A': 'XQA'}, iex_day=fx.S, signal_day=fx.S)
    # published codes are accepted as well as parser codes
    out = iex_signal.signal_quotes({'XQA': ('SUPPLIED', 104107), 'XQB1': ('ODD_LOT_ONLY', 5)},
                                   {'SEC-A': 'XQA', 'SEC-B1': 'XQB1'}, iex_day=fx.S, signal_day=fx.S)
    assert out['status'] == {'SEC-A': 'SUPPLIED', 'SEC-B1': 'ODD_LOT_ONLY'}


class FakeIexDay:
    """The attributes of iex_hist.IexDay that the adapter reads (RAM only)."""
    def __init__(self, day, quotes, status):
        self.day, self.quotes, self.status = day, quotes, status


def test_iex_day_object():
    day = FakeIexDay('2018-02-16', {'k1': {'price': 10.4107, 'currency': 'USD'}},
                     {'k1': 'SUPPLIED', 'k2': 'ODD_LOT_ONLY', 'k3': 'NO_IEX_TRADE', 'k4': 'PRICE_SYMBOL_UNMAPPED',
                      'k5': 'ADR_RATIO_UNCONFIRMED'})
    keys = {'k1': 'SEC-1', 'k2': 'SEC-2', 'k3': 'SEC-3', 'k4': 'SEC-4', 'k5': 'SEC-5', 'k6': 'SEC-6'}
    out = iex_signal.signal_quotes_from_iex_day(day, keys, signal_day=fx.S)
    assert out['quotes']['SEC-1']['price'] == Decimal('10.4107')
    assert out['status'] == {'SEC-1': 'SUPPLIED', 'SEC-2': 'ODD_LOT_ONLY', 'SEC-3': 'NO_IEX_TRADE', 'SEC-4': 'UNMAPPED',
                             'SEC-5': 'ADR_RATIO_UNCONFIRMED', 'SEC-6': 'IEX_RESULT_MISSING_SYMBOL'}
    late = iex_signal.signal_quotes_from_iex_day(FakeIexDay('2018-02-20', day.quotes, day.status), keys,
                                                 signal_day=fx.S)
    assert set(late['status'].values()) == {'IEX_DAY_NOT_SIGNAL_DAY'}


def test_not_supplied_and_nothing_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = iex_signal.not_supplied(['SEC-A', 'SEC-B1'])
    assert out['status'] == {'SEC-A': 'IEX_NOT_SUPPLIED', 'SEC-B1': 'IEX_NOT_SUPPLIED'}
    iex_signal.signal_quotes(fx.iex_rows(), MAP, iex_day=fx.S, signal_day=fx.S)
    assert list(tmp_path.iterdir()) == []
