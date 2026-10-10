"""Synthetic trading-session contracts and independent TA-Lib reference values."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import socket
import sys
from zoneinfo import ZoneInfo

import pytest

from investment_system.technical.daily_input import DailyBar, DailyInputSeries, ExpectedSession
from investment_system.technical.engine import TechnicalEngine
from investment_system.technical.research_display import calculate_research_display


ROLE = "RESEARCH_DISPLAY_ONLY"
START = datetime(2030, 1, 1, 21, tzinfo=timezone.utc)


def series(prices, *, ohlc=True, basis="RAW_CLOSE", exchange="XNYS", zone="America/New_York", currency="USD"):
    # Supplied synthetic sessions deliberately have calendar gaps; no real calendar.
    times = [START + timedelta(days=i*2) for i in range(len(prices))]
    bars = tuple(DailyBar("synthetic-company", "synthetic-listing", "SYN", currency,
                         "SYNTHETIC", t.date(), t, t, t, True, basis, p, p/2,
                         p if ohlc else None, p+2+i%3 if ohlc else None,
                         p-2-i%2 if ohlc else None, 0, "RAW" if ohlc else None)
                 for i, (p, t) in enumerate(zip(prices, times)))
    return DailyInputSeries("synthetic-company", "synthetic-listing", "SYN", currency,
                            "SYNTHETIC", exchange, zone, "synthetic-source", "1d", basis,
                            (times[-1] if times else START)+timedelta(days=3), True, bars,
                            tuple(ExpectedSession(b.session, b.observed_at) for b in bars),
                            "synthetic-calendar", "CONFIRMED_SYNTHETIC", "CONFIRMED_SYNTHETIC",
                            tuple(b.session for b in bars), "synthetic-adjustment", ())


def calculate(s, **kwargs):
    result = calculate_research_display(s, s.read_at, **kwargs)
    assert result.state == "DEMO" and result.data is not None
    assert result.role == result.data.role == ROLE
    assert result.prepared.pit_status == "NOT_VERIFIED"
    assert result.prepared.model_status == "PLACEHOLDER_UNVALIDATED"
    assert result.prepared.synthetic is True
    return {item.indicator_id: item for item in result.data.indicators}


REFERENCE = json.loads((Path(__file__).parent / "fixtures/technical_research_reference.json").read_text())


@pytest.mark.parametrize("name", list(REFERENCE["expected"]))
def test_independent_c_reference_checkpoints(name):
    prices = [100+(i*7)%19+i//6 for i in range(260)]
    items = calculate(series(prices), include_sma240=True)
    assert REFERENCE["reference"] == "TA-Lib" and REFERENCE["version"] == "0.6.8"
    assert REFERENCE["synthetic"] is True
    item = items[name]
    assert item.role == ROLE
    for index, expected in REFERENCE["expected"][name].items():
        value = item.values[int(index)]
        if expected is None:
            assert value is None and item.unavailable_reasons[int(index)] == "WARMUP"
        else:
            assert value == pytest.approx(expected, rel=1e-10, abs=1e-10)
            assert item.unavailable_reasons[int(index)] is None


def test_only_approved_components_and_display_defaults():
    s = series([100+i for i in range(260)])
    items = calculate(s)
    assert set(items) == set(REFERENCE["expected"]) - {"SMA_240"}
    for n in (5, 20, 60, 120):
        assert items[f"SMA_{n}"].default_visible is True
    assert all(item.default_visible is None for name, item in items.items() if not name.startswith("SMA_"))
    optional = calculate(s, include_sma240=True)["SMA_240"]
    assert optional.default_visible is False


@pytest.mark.parametrize("name,first", [("SMA_5",4),("SMA_20",19),("SMA_60",59),
    ("SMA_120",119),("SMA_240",239),("EMA_20",19),("RSI_14",14),
    ("MACD_12_26",25),("MACD_SIGNAL_9",33),("MACD_HISTOGRAM_12_26_9",33),
    ("BOLL_MIDDLE_20",19),("BOLL_UPPER_20_2",19),("BOLL_LOWER_20_2",19),("ATR_14",14)])
def test_warmup_is_null_until_exact_trading_session_boundary(name, first):
    s = series([100+i for i in range(first)])
    item = calculate(s, include_sma240=True)[name]
    assert item.values == (None,)*first
    assert item.latest_state == "NOT_AVAILABLE"
    ready = calculate(series([100+i for i in range(first+1)]), include_sma240=True)[name]
    assert ready.values[first] is not None and ready.latest_state == "AVAILABLE"


def test_known_linear_and_flat_values_do_not_replace_undefined_with_zero():
    items = calculate(series([100+i for i in range(260)]), include_sma240=True)
    for n in (5, 20, 60, 120, 240):
        assert items[f"SMA_{n}"].values[-1] == 359-(n-1)/2
    assert items["EMA_20"].values[19] == 109.5
    assert items["MACD_12_26"].values[25] == pytest.approx(7)
    assert items["MACD_SIGNAL_9"].values[33] == pytest.approx(7)
    assert items["MACD_HISTOGRAM_12_26_9"].values[33] == pytest.approx(0, abs=1e-12)
    assert items["RSI_14"].values[-1] == 100
    falling = calculate(series([400-i for i in range(260)]))
    assert falling["RSI_14"].values[-1] == 0  # genuine calculated zero
    s = series([100]*40)
    s = replace(s, bars=tuple(replace(b, high=102, low=98) for b in s.bars))
    flat = calculate(s)
    assert flat["BOLL_UPPER_20_2"].values[-1] == flat["BOLL_LOWER_20_2"].values[-1] == 100
    assert flat["ATR_14"].values[14:] == (4,)*26
    assert flat["RSI_14"].values == (None,)*40
    assert flat["RSI_14"].unavailable_reasons[-1] == "ZERO_TOTAL_CHANGE"


@pytest.mark.parametrize("exchange,zone,currency", [("XNYS","America/New_York","USD"),
    ("XKRX","Asia/Seoul","KRW"),("XTKS","Asia/Tokyo","JPY")])
def test_market_uses_supplied_trading_sessions_instead_of_calendar_days(exchange, zone, currency):
    s = series([100+i for i in range(120)], exchange=exchange, zone=zone, currency=currency)
    local = tuple(replace(b, observed_at=b.observed_at.astimezone(ZoneInfo(zone))) for b in s.bars)
    s = replace(s, bars=local, expected_sessions=tuple(ExpectedSession(b.session,b.observed_at) for b in local))
    result = calculate_research_display(s, s.read_at)
    assert result.data.sessions == tuple(b.session for b in s.bars)
    assert result.data.currency == currency and result.data.listing_id == s.listing_id
    assert calculate(s)["SMA_120"].values[-1] == 159.5
    assert s.bars[-1].session-s.bars[0].session == timedelta(days=238)


@pytest.mark.parametrize("change,reason", [(dict(synthetic=False),"REAL_INPUT_NOT_AUTHORIZED"),
    (dict(expected_sessions=None),"CALENDAR_UNCONFIRMED"),
    (dict(basis_status="UNKNOWN"),"BASIS_UNCONFIRMED"),
    (dict(corporate_action_status="UNKNOWN"),"ACTION_COVERAGE_UNCONFIRMED")])
def test_input_gate_preserves_reason_and_emits_no_display_data(change, reason):
    s = replace(series([100+i for i in range(40)]), **change)
    r = calculate_research_display(s,s.read_at)
    assert r.state == "NOT_AVAILABLE" and r.data is None and r.role == ROLE
    assert r.prepared.reason_codes == (reason,)


@pytest.mark.parametrize("price", [None, float("nan"), float("inf"), 0])
def test_bad_price_never_gets_repaired(price):
    s = series([100+i for i in range(40)])
    s = replace(s,bars=(replace(s.bars[0],close=price),)+s.bars[1:])
    r = calculate_research_display(s,s.read_at)
    assert r.state == "NOT_AVAILABLE" and r.data is None
    assert r.prepared.reason_codes == ("INVALID_PRICE",)


def test_cutoff_excludes_future_bar_but_rejects_late_available_eligible_bar():
    s = series([100+i for i in range(41)])
    cutoff = s.bars[-2].observed_at
    s = replace(s, bars=s.bars[:-1]+(replace(s.bars[-1],close=None),),
                action_covered_sessions=tuple(b.session for b in s.bars[:-1]))
    r = calculate_research_display(s,cutoff)
    assert r.state == "DEMO" and r.prepared.excluded_future_bar_count == 1
    assert len(r.data.sessions) == 40
    assert {x.indicator_id:x.values for x in r.data.indicators} == {k:x.values for k,x in calculate(series([100+i for i in range(40)])).items()}
    late = replace(s,bars=(replace(s.bars[0],available_at=cutoff+timedelta(seconds=1)),)+s.bars[1:])
    r = calculate_research_display(late,cutoff)
    assert r.state == "NOT_AVAILABLE" and r.prepared.reason_codes == ("AVAILABLE_AFTER_AS_OF",)


def test_adjusted_close_is_selected_without_mixing_raw_ohlc_for_atr():
    items = calculate(series([100+i for i in range(40)],basis="PROVIDER_ADJUSTED_CLOSE"))
    assert items["SMA_5"].values[-1] == 68.5
    assert items["ATR_14"].values == (None,)*40
    assert set(items["ATR_14"].unavailable_reasons) == {"OHLC_BASIS_UNCONFIRMED"}


def test_missing_ohlc_affects_only_atr_and_gap_requires_new_warmup():
    no_ohlc = calculate(series([100+i for i in range(40)],ohlc=False))
    assert no_ohlc["SMA_20"].latest_state == "AVAILABLE"
    assert no_ohlc["ATR_14"].values == (None,)*40
    assert no_ohlc["ATR_14"].unavailable_reasons[1] == "OHLC_MISSING"
    s = series([100+i for i in range(40)])
    s = replace(s,bars=s.bars[:20]+(replace(s.bars[20],open=None,high=None,low=None,ohlc_basis=None),)+s.bars[21:])
    atr = calculate(s)["ATR_14"]
    assert atr.values[19] is not None and atr.values[20:34] == (None,)*14
    assert atr.values[34] is not None  # TR21..34: no skipped-gap splice


@pytest.mark.parametrize("invalid", [None, 1, "true"])
def test_optional_sma_requires_explicit_boolean(invalid):
    s = series([100+i for i in range(40)])
    r = calculate_research_display(s,s.read_at,include_sma240=invalid)
    assert r.state == "NOT_AVAILABLE" and r.data is None
    assert r.prepared.reason_codes == ("INVALID_DISPLAY_CONFIG",)


def test_finite_input_overflow_is_unavailable_without_nonfinite_output():
    s = series([sys.float_info.max]*260,ohlc=False)
    items = calculate(s,include_sma240=True)
    for name in ("SMA_5","SMA_20","SMA_60","SMA_120","SMA_240","EMA_20"):
        assert items[name].values[-1] == pytest.approx(sys.float_info.max)
    varying = calculate(series([1e308,1e307]*20,ohlc=False))
    assert varying["BOLL_UPPER_20_2"].values[-1] is None
    assert varying["BOLL_UPPER_20_2"].unavailable_reasons[-1] == "CALCULATION_ERROR"
    assert varying["SMA_20"].values[-1] is not None
    for item in items.values():
        assert all(v is None or math.isfinite(v) for v in item.values)


def test_ram_results_are_immutable_hide_values_and_do_not_call_models_or_network(monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError("unexpected model/network call")
    monkeypatch.setattr(TechnicalEngine,"evaluate",forbidden)
    monkeypatch.setattr(socket,"create_connection",forbidden)
    s = series([123.456789+i for i in range(260)])
    before = s
    r = calculate_research_display(s,s.read_at)
    assert s == before and not hasattr(r,"to_dict") and not hasattr(r.data,"to_dict")
    assert "123.456789" not in repr(r) and "values=" not in repr(r.data.indicators[0])
    with pytest.raises(FrozenInstanceError):
        r.role = "MODEL"
    for item in r.data.indicators:
        assert isinstance(item.values,tuple) and len(item.values) == len(r.data.sessions)
        assert len(item.values) == len(item.unavailable_reasons)
        with pytest.raises(FrozenInstanceError):
            item.role = "MODEL"
