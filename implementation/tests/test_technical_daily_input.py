"""24 offline daily-input contracts using author-created synthetic bars."""
import ast
import builtins
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import logging
from pathlib import Path
import socket

import pytest

from investment_system.technical.daily_input import (
    CorporateActionEvent, DailyBar, DailyInputSeries, ExpectedSession,
    prepare_daily_returns, evaluate_daily_input,
)
from investment_system.technical.engine import TechnicalEngine
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.versions import TECHNICAL_STRUCTURAL, IMPLEMENTATION_KIND
from tests.helpers import complete_obs

START = datetime(2030, 1, 1, 21, tzinfo=timezone.utc)


def _series(prices, *, price_basis="RAW_CLOSE"):
    bars = tuple(DailyBar("synthetic-company","synthetic-listing","SYN","USD","SYNTHETIC",
                         (START+timedelta(days=i)).date(),START+timedelta(days=i),START+timedelta(days=i),
                         START+timedelta(days=i),True,price_basis,p,p/2 if p is not None else None)
                 for i,p in enumerate(prices))
    return DailyInputSeries("synthetic-company","synthetic-listing","SYN","USD","SYNTHETIC","XNYS",
                            "America/New_York","synthetic-source","1d",price_basis,START+timedelta(days=len(prices)+3),
                            True,bars,tuple(ExpectedSession(b.session,b.observed_at) for b in bars),"synthetic-calendar",
                            "CONFIRMED_SYNTHETIC","CONFIRMED_SYNTHETIC",tuple(b.session for b in bars),"synthetic-adjustment",())


def _bar(series,index=1,**changes):
    return replace(series,bars=series.bars[:index]+(replace(series.bars[index],**changes),)+series.bars[index+1:])


class CountingEngine:
    def __init__(self):
        self.calls=[]
    def evaluate(self,*args,**kwargs):
        self.calls.append((args,kwargs))
        return TechnicalEngine().evaluate(*args,**kwargs)


def _bad(series,reason,as_of=None):
    at = series.read_at if as_of is None else as_of
    engine=CountingEngine()
    result=evaluate_daily_input(series,at,engine=engine)
    assert result.state == "NOT_AVAILABLE" and result.data is None
    assert result.prepared.state == "NOT_AVAILABLE" and result.prepared.returns is None
    assert result.prepared.return_count == 0 and result.prepared.reason_codes == (reason,)
    assert engine.calls == []


def _oracle(bars,as_of):
    path=Path(__file__).parents[1]/"src/investment_system/validation/historical.py"
    function=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=="bars_to_returns")
    ns={"datetime":datetime}
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(path),"exec"),ns)
    return ns["bars_to_returns"](bars,as_of)


def _snapshot(data):
    d=data.to_dict(); d.pop("technical_snapshot_id"); return d


@pytest.mark.parametrize("n",[2,6,20,21,25])
def test_returns_match_historical_helper_short_and_last20(n):
    s=_series([100+i for i in range(n)]); p=prepare_daily_returns(s,s.read_at)
    assert p.state=="READY" and p.reason_codes==()
    assert list(p.returns)==_oracle([{"observed_at":b.observed_at,"price":b.close} for b in s.bars],s.read_at)
    assert (p.input_bar_count,p.eligible_bar_count,p.excluded_future_bar_count,p.return_count)==(n,n,0,min(n-1,20))
    assert (p.pit_status,p.model_status)==("NOT_VERIFIED","PLACEHOLDER_UNVALIDATED")


def test_future_observation_is_excluded_without_lookahead():
    s=_series([100,101,999]); at=s.bars[1].observed_at
    s=replace(s,action_covered_sessions=tuple(b.session for b in s.bars[:2]))
    p=prepare_daily_returns(s,at); changed=_bar(s,2,close=None,complete=False,company_id="wrong")
    assert p.state=="READY" and p.excluded_future_bar_count==1
    assert p==prepare_daily_returns(changed,at)
    assert _snapshot(evaluate_daily_input(s,at,engine=TechnicalEngine()).data)==_snapshot(evaluate_daily_input(changed,at,engine=TechnicalEngine()).data)


def test_unknown_or_future_availability_blocks_engine():
    s=_series([100,101]); at=s.bars[1].observed_at
    _bad(_bar(s,available_at=None),"AVAILABILITY_UNKNOWN",at)
    _bad(_bar(s,available_at=at+timedelta(seconds=1)),"AVAILABLE_AFTER_AS_OF",at)


def test_publication_unknown_is_preserved_and_future_blocks():
    s=_series([100,101]); at=s.bars[1].observed_at
    p=prepare_daily_returns(_bar(s,published_at=None),at)
    assert p.state=="READY" and {"PUBLICATION_TIME_UNKNOWN","PIT_UNAVAILABLE"}<=set(p.quality_flags)
    _bad(_bar(s,available_at=at+timedelta(seconds=2),published_at=at+timedelta(seconds=1)),"AVAILABLE_AFTER_AS_OF",at)
    _bad(_bar(s,published_at=at+timedelta(seconds=1)),"PUBLISHED_AFTER_AS_OF",at)


def test_invalid_timestamp_and_time_order_block_engine():
    s=_series([100,101])
    for at in [datetime.min.replace(tzinfo=timezone(timedelta(hours=14))),datetime.max.replace(tzinfo=timezone(timedelta(hours=-14)))]:
        _bad(s,"INVALID_TIMESTAMP",at)
    _bad(s,"INVALID_TIMESTAMP",s.read_at.replace(tzinfo=None))
    _bad(replace(s,read_at=s.read_at.replace(tzinfo=None)),"INVALID_TIMESTAMP",s.read_at)
    for field in ("observed_at","available_at","published_at"):
        _bad(_bar(s,**{field:getattr(s.bars[1],field).replace(tzinfo=None)}),"INVALID_TIMESTAMP")
    _bad(_bar(s,available_at=s.read_at+timedelta(seconds=1)),"INVALID_TIME_ORDER")
    _bad(_bar(s,published_at=s.bars[1].available_at+timedelta(seconds=1)),"INVALID_TIME_ORDER")
    calendar=(s.expected_sessions[0],replace(s.expected_sessions[1],close_at=START.replace(tzinfo=None)))
    _bad(replace(s,expected_sessions=calendar),"INVALID_TIMESTAMP")
    e=CorporateActionEvent("SPLIT",s.bars[1].session,START.replace(tzinfo=None),START,"synthetic")
    _bad(replace(s,events=(e,)),"INVALID_TIMESTAMP")


def test_empty_and_single_bar_do_not_create_unknown_wait():
    for n in [0,1]: _bad(_series([100]*n),"INSUFFICIENT_BARS")


@pytest.mark.parametrize("value",[None,0,-1,float("nan"),float("inf"),-float("inf"),True,False,"101"])
def test_invalid_prices_are_not_dropped_or_repaired(value):
    s=_bar(_series([100,101,102]),close=value); before=deepcopy(s)
    _bad(s,"INVALID_PRICE"); assert s==before or value!=value


def test_duplicate_and_unsorted_bars_are_rejected():
    s=_series([100,101,102])
    _bad(_bar(s,observed_at=s.bars[0].observed_at),"DUPLICATE_BAR")
    _bad(_bar(s,session=s.bars[0].session),"DUPLICATE_BAR")
    _bad(replace(s,bars=tuple(reversed(s.bars))),"UNSORTED_BARS")


def test_explicit_calendar_distinguishes_non_session_and_gap():
    s=_series([100,101,102]); sparse=replace(s,bars=(s.bars[0],s.bars[2]),expected_sessions=(s.expected_sessions[0],s.expected_sessions[2]),action_covered_sessions=(s.bars[0].session,s.bars[2].session))
    assert prepare_daily_returns(sparse,s.read_at).state=="READY"
    _bad(replace(sparse,expected_sessions=s.expected_sessions),"MISSING_SESSION")
    _bad(replace(s,expected_sessions=None),"CALENDAR_UNCONFIRMED")
    _bad(replace(s,expected_sessions=s.expected_sessions+s.expected_sessions[:1]),"INVALID_CALENDAR")
    _bad(replace(s,expected_sessions=tuple(reversed(s.expected_sessions))),"INVALID_CALENDAR")


def test_session_time_and_completion_must_be_explicit():
    s=_series([100,101])
    for complete in (False,None,1): _bad(_bar(s,complete=complete),"INCOMPLETE_SESSION")
    shifted=(s.expected_sessions[0],replace(s.expected_sessions[1],close_at=s.bars[1].observed_at+timedelta(seconds=1)))
    _bad(replace(s,expected_sessions=shifted),"SESSION_TIME_MISMATCH")


def test_identity_and_required_metadata_do_not_fallback():
    s=_series([100,101])
    for field in ("company_id","listing_id","symbol","currency","provider"):
        _bad(_bar(s,**{field:"other"}),"IDENTITY_MISMATCH")
    for field in ("currency","symbol","source_reference"):
        _bad(replace(s,**{field:""}),"MISSING_METADATA")
    _bad(replace(s,interval="1h"),"INVALID_INTERVAL")
    _bad(replace(s,synthetic=False),"REAL_INPUT_NOT_AUTHORIZED")


def test_mixed_basis_and_missing_adjusted_close_block_engine():
    s=_series([100,101],price_basis="PROVIDER_ADJUSTED_CLOSE")
    _bad(_bar(s,price_basis="RAW_CLOSE"),"MIXED_BASIS")
    _bad(_bar(s,adjclose=None),"ADJUSTED_CLOSE_MISSING")
    _bad(replace(s,basis_status="UNKNOWN"),"BASIS_UNCONFIRMED")


def test_ohlc_coherence_and_raw_basis_are_preserved():
    s=_series([100,101],price_basis="PROVIDER_ADJUSTED_CLOSE")
    for changes in [dict(open=100),dict(open=100,low=110,high=90,ohlc_basis="RAW"),dict(open=100,low=90,high=100,ohlc_basis="RAW"),dict(open=100,low=90,high=110,ohlc_basis="OTHER")]:
        _bad(_bar(s,**changes),"INVALID_OHLC")
    valid=_bar(s,open=100,low=90,high=110,ohlc_basis="RAW")
    assert prepare_daily_returns(valid,valid.read_at).returns==(valid.bars[1].adjclose/valid.bars[0].adjclose-1.0,)
    assert valid.bars[1].close==101


def test_volume_zero_none_and_invalid_values_are_distinct():
    s=_series([100,101])
    for changes in [dict(volume=-1),dict(open=100)]:
        _bad(_bar(_bar(s,0,**changes),1,close=0),"INVALID_PRICE")
    for v in [0,None]: assert prepare_daily_returns(_bar(s,volume=v),s.read_at).state=="READY"
    for v in [True,-1,float("nan"),float("inf")]: _bad(_bar(s,volume=v),"INVALID_VOLUME")


def test_corporate_action_metadata_is_not_inferred_from_empty_events():
    s=_series([100,101],price_basis="PROVIDER_ADJUSTED_CLOSE")
    _bad(replace(s,corporate_action_status="UNKNOWN"),"ACTION_COVERAGE_UNCONFIRMED")
    _bad(replace(s,action_covered_sessions=()),"ACTION_COVERAGE_MISMATCH")
    _bad(replace(s,adjustment_reference=None),"ADJUSTMENT_METADATA_MISSING")


def test_corporate_action_unknown_future_and_raw_events_block():
    s=_series([100,101],price_basis="PROVIDER_ADJUSTED_CLOSE")
    e=CorporateActionEvent("SPLIT",s.bars[1].session,START-timedelta(days=1),START,"synthetic-event")
    assert prepare_daily_returns(replace(s,events=(e,)),s.read_at).state=="READY"
    for event,reason in [(replace(e,available_at=None),"ACTION_AVAILABILITY_UNKNOWN"),(replace(e,available_at=s.read_at+timedelta(seconds=1)),"INVALID_TIME_ORDER"),(replace(e,source_reference=None),"ACTION_METADATA_INVALID"),(replace(e,published_at=e.available_at+timedelta(seconds=1)),"ACTION_METADATA_INVALID")]:
        _bad(replace(s,events=(event,)),reason)
    _bad(replace(s,events=(replace(e,available_at=s.read_at),)),"ACTION_AVAILABLE_AFTER_AS_OF",s.bars[1].observed_at)
    p=prepare_daily_returns(replace(s,events=(replace(e,published_at=None),)),s.read_at)
    assert p.state=="READY" and "PUBLICATION_TIME_UNKNOWN" in p.quality_flags
    raw=_series([100,101]); _bad(replace(raw,events=(e,)),"UNRESOLVED_CORPORATE_ACTION")


def test_nonfinite_return_is_rejected_before_engine():
    _bad(_series([1e-308,1e308]),"NONFINITE_RETURN")


@pytest.mark.parametrize("prices",[[100,101,102],[100,102,104.04],[100,99,98],[100,100,100],[100,120,96]])
def test_engine_full_snapshot_matches_direct_call_for_existing_branches(prices):
    s=_series(prices); p=prepare_daily_returns(s,s.read_at)
    direct=TechnicalEngine().evaluate(s.company_id,s.read_at,list(p.returns),synthetic=True)
    wrapped=evaluate_daily_input(s,s.read_at,engine=TechnicalEngine())
    assert wrapped.state=="DEMO" and _snapshot(wrapped.data)==_snapshot(direct)


def test_engine_shape_placeholder_version_and_synthetic_remain_unchanged():
    s=_series([100,101]); d=evaluate_daily_input(s,s.read_at,engine=TechnicalEngine()).data
    direct=TechnicalEngine().evaluate(s.company_id,s.read_at,[.01],synthetic=True)
    assert set(d.to_dict())==set(direct.to_dict())
    assert (d.technical_version,d.implementation_kind,d.synthetic)==(TECHNICAL_STRUCTURAL,IMPLEMENTATION_KIND,True)
    assert tuple(x["return_shock"] for x in d.scenarios)==(-.1,0,.1)
    assert all(x["kind"]=="structural-placeholder" for x in d.scenarios)
    assert d.invalidation==direct.invalidation and d.drawdown_recheck is False


def test_qgv_full_snapshot_is_unchanged_and_scores_do_not_drive_technical():
    s=_series([100,101,102]); outputs=[]
    for score in [20,90]:
        q=AnalysisEngine().analyze(s.company_id,s.read_at,complete_obs(score),synthetic=True); before=deepcopy(q.to_dict())
        d=evaluate_daily_input(s,s.read_at,engine=TechnicalEngine(),qgv=q).data
        assert q.to_dict()==before and d.qgv_snapshot_id_ref==q.qgv_snapshot_id and d.mutated_qgv is False
        snap=_snapshot(d); snap.pop("qgv_snapshot_id_ref"); outputs.append(snap)
    assert outputs[0]==outputs[1]


def test_engine_receives_prepared_values_once_and_preserves_inputs():
    s=_series([100,101]); before=deepcopy(s); e=CountingEngine()
    q=AnalysisEngine().analyze(s.company_id,s.read_at,complete_obs(),synthetic=True)
    result=evaluate_daily_input(s,s.read_at,engine=e,qgv=q)
    assert e.calls==[((s.company_id,s.read_at,list(result.prepared.returns)),dict(qgv=q,synthetic=True))]
    assert e.calls[0][1]["qgv"] is q and s==before
    assert evaluate_daily_input(s,s.read_at,engine=TechnicalEngine()).data.qgv_snapshot_id_ref is None


def test_all_preparation_failures_block_engine_and_have_no_data():
    s=_series([100,101])
    cases=[(_bar(s,close=0),"INVALID_PRICE"),(_bar(s,available_at=None),"AVAILABILITY_UNKNOWN"),
           (replace(s,bars=()),"INSUFFICIENT_BARS"),(replace(s,calendar_reference=None),"CALENDAR_UNCONFIRMED"),
           (replace(s,synthetic=False),"REAL_INPUT_NOT_AUTHORIZED")]
    for fixture,reason in cases: _bad(fixture,reason)


def test_engine_arithmetic_failure_has_no_normal_data_or_raw_exception():
    class Broken:
        def evaluate(self,*args,**kwargs): raise ArithmeticError("private-input-sentinel")
    s=_series([100,101]); prepared=prepare_daily_returns(s,s.read_at)
    result=evaluate_daily_input(s,s.read_at,engine=Broken())
    assert result.data is None and result.state=="NOT_AVAILABLE"
    assert result.prepared==replace(prepared,state="NOT_AVAILABLE",returns=None,return_count=0,reason_codes=("CALCULATION_ERROR",))
    assert "private-input-sentinel" not in repr(result)


def test_boundary_has_no_io_or_diagnostic_payload_leak(monkeypatch,capsys):
    s=_series([100,101]); invalid=_bar(s,close=None)
    def forbidden(*args,**kwargs): pytest.fail("I/O at pure boundary")
    with monkeypatch.context() as m:
        m.setattr(builtins,"open",forbidden); m.setattr(Path,"open",forbidden)
        m.setattr(socket,"create_connection",forbidden); m.setattr(socket.socket,"connect",forbidden)
        m.setattr(logging.Logger,"_log",forbidden)
        assert evaluate_daily_input(s,s.read_at,engine=TechnicalEngine()).state=="DEMO"
        _bad(invalid,"INVALID_PRICE")
    assert capsys.readouterr()==("","")
