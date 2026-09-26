"""PIL v1 P0 Common Contracts — independent unit tests (Track B). No existing module is imported or changed."""
import ast
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from investment_system.personal import fit, ports, portfolio, quality, security, versioning, weights
from investment_system.personal.money import FxRate, Money, convert
from investment_system.personal.timecontract import TimeContractError, TimeStamps, usable_at

UTC = timezone.utc
T0 = datetime(2024, 12, 31, 21, tzinfo=UTC)
PKG = Path(__file__).resolve().parents[1] / "src" / "investment_system" / "personal"


def test_pil_package_imports_nothing_from_the_existing_system():
    for f in PKG.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert node.level >= 1 or not mod.startswith("investment_system"), (f.name, mod)
                assert node.level <= 1, (f.name, mod)  # no '..' imports into qgv/technical/integration/...
            if isinstance(node, ast.Import):
                assert not any(a.name.startswith("investment_system") for a in node.names), f.name


def test_time_contract_no_lookahead_and_no_generated_times():
    TimeStamps(observed_at=T0 - timedelta(days=1), available_at=T0, decision_time=T0)
    with pytest.raises(TimeContractError):
        TimeStamps(observed_at=None, available_at=T0 + timedelta(seconds=1), decision_time=T0)
    with pytest.raises(TimeContractError):
        TimeStamps(observed_at=None, available_at=None, decision_time=T0)  # C-28: never filled from as_of
    with pytest.raises(TimeContractError):
        TimeStamps(observed_at=None, available_at=datetime(2024, 12, 31), decision_time=T0)  # naive
    assert usable_at(None, T0) is False and usable_at(T0, T0) is True


def test_quality_worst_and_missing_is_not_valid():
    Q = quality.DataQuality
    assert quality.worst(Q.VALID, Q.STALE, Q.PARTIAL) == Q.STALE
    assert quality.worst() == Q.UNRESOLVED
    assert quality.is_actionable(Q.PARTIAL) and not quality.is_actionable(Q.STALE)


def test_content_hash_is_canonical_and_rejects_nan():
    a = versioning.content_hash({"b": 1, "a": [1.5, T0]})
    assert a == versioning.content_hash({"a": [1.5, T0], "b": 1})
    assert a != versioning.content_hash({"a": [1.5000001, T0], "b": 1})
    with pytest.raises(ValueError):
        versioning.content_hash({"x": float("nan")})


def test_fx_conversion_explicit_stale_and_no_lookahead():
    fx = FxRate("USDKRW", Decimal("1470.5"), fx_as_of=T0 - timedelta(days=3), available_at=T0 - timedelta(days=3))
    c = convert(Money(Decimal("100"), "USD"), fx, "KRW", T0, max_age=timedelta(days=1))
    assert c.converted == Money(Decimal("147050.0"), "KRW") and c.quality == quality.DataQuality.STALE
    assert c.original.currency == "USD"
    with pytest.raises(TimeContractError):
        convert(Money(Decimal("1"), "USD"), FxRate("USDKRW", Decimal("1"), T0, T0 + timedelta(hours=1)), "KRW", T0, timedelta(days=1))
    with pytest.raises(TypeError):
        Money(1.0, "USD")


def _records():
    I = security.SecurityIdentifiers
    return [
        security.SecurityRecord("sec_aapl", I(ticker="AAPL", exchange="XNAS", cik="0000320193", isin="US0378331005"), date(2000, 1, 1)),
        security.SecurityRecord("sec_brk_a", I(ticker="BRK.A", exchange="XNYS", share_class="A", isin="US0846701086"), date(2000, 1, 1)),
        security.SecurityRecord("sec_brk_b", I(ticker="BRK.B", exchange="XNYS", share_class="B", isin="US0846707026"), date(2000, 1, 1)),
        # ticker reuse: WOLF before and after 2025-09 are different securities
        security.SecurityRecord("sec_wolf_old", I(ticker="WOLF", exchange="XNYS", isin="US9778521024"), date(2021, 10, 4), date(2025, 9, 29)),
        security.SecurityRecord("sec_wolf_new", I(ticker="WOLF", exchange="XNYS", isin="US9778522014"), date(2025, 9, 29)),
    ]


def test_security_resolver_fail_closed():
    r = security.InMemorySecurityResolver(_records())
    I, S = security.SecurityIdentifiers, security.ResolutionStatus
    assert r.resolve(I(isin="us0378331005"), date(2024, 12, 31)).security_id == "sec_aapl"
    assert r.resolve(I(ticker="AAPL"), date(2024, 12, 31)).status == S.UNRESOLVED  # ticker alone is not an identity
    assert r.resolve(I(ticker="AAPL", exchange="XNAS"), date(2024, 12, 31)).security_id == "sec_aapl"
    assert r.resolve(I(ticker="WOLF", exchange="XNYS"), date(2024, 12, 31)).security_id == "sec_wolf_old"
    assert r.resolve(I(ticker="WOLF", exchange="XNYS"), date(2026, 1, 5)).security_id == "sec_wolf_new"
    assert r.resolve(I(isin="US0000000000", ticker="AAPL", exchange="XNAS"), date(2024, 12, 31)).status == S.UNRESOLVED
    assert r.resolve(I(ticker="BRK.B", exchange="XNYS", share_class="B"), date(2024, 12, 31)).security_id == "sec_brk_b"
    amb = security.InMemorySecurityResolver(_records() + [security.SecurityRecord(
        "sec_dup", I(ticker="AAPL", exchange="XNAS"), date(2000, 1, 1))])
    assert amb.resolve(I(ticker="AAPL", exchange="XNAS"), date(2024, 12, 31)).status == S.AMBIGUOUS


def _registry():
    N, T, M = weights.NodeDefinition, weights.NodeType, weights.Maturity
    return weights.OfficialRegistry("reg-test-1", (
        N("qgv", None, "QGV", T.GROUP, M.PRODUCTION, "QGV"),
        N("q", "qgv", "QGV", T.GROUP, M.PRODUCTION, "Q", official_weight=0.5),
        N("g", "qgv", "QGV", T.GROUP, M.PRODUCTION, "G", official_weight=0.5),
        N("q1", "q", "QGV", T.WEIGHT, M.PRODUCTION, "q1", official_weight=0.6),
        N("q2", "q", "QGV", T.WEIGHT, M.PROVISIONAL, "q2", official_weight=0.4),
        N("g1", "g", "QGV", T.WEIGHT, M.UNRESOLVED, "g1"),
        N("g2", "g", "QGV", T.WEIGHT, M.UNRESOLVED, "g2"),
        N("pit", "qgv", "QGV", T.LOCKED, M.LOCKED, "PIT / no-lookahead"),
        N("lookback", "qgv", "QGV", T.PARAMETER, M.PROVISIONAL, "lookback"),
    ))


def _version(ns, overrides):
    return weights.PersonalStrategyVersion("v1", "s1", "reg-test-1", ns, tuple(overrides), weights.StrategyStatus.DRAFT, T0)


def test_weight_tree_official_isolation_editability_and_global_weights():
    reg, W, NS = _registry(), weights.WeightOverride, versioning.ResultNamespace
    eff = weights.effective_tree(reg, _version(NS.SANDBOX, [W("q1", 0.75), W("q2", 0.25)]))
    assert eff["q1"].local_weight == 0.75 and abs(eff["q1"].global_weight - 0.375) < 1e-12 and eff["q1"].source == "OVERRIDE"
    assert reg.node("q1").official_weight == 0.6  # official registry unchanged by the override
    assert eff["g1"].global_weight is None  # UNRESOLVED weights stay unset; nothing redistributed
    with pytest.raises(weights.WeightTreeError):  # PROVISIONAL editable only in research namespaces
        weights.effective_tree(reg, _version(NS.CUSTOM_ACTIVE, [W("q1", 0.2), W("q2", 0.8)]))
    weights.effective_tree(reg, _version(NS.SANDBOX, [W("q1", 0.2), W("q2", 0.8)]))
    for bad in ([W("g1", 0.5), W("g2", 0.5)], [W("pit", 1.0)], [W("lookback", 1.0)], [W("q1", 0.9)]):
        with pytest.raises(weights.WeightTreeError):
            weights.effective_tree(reg, _version(NS.SANDBOX, bad))
    with pytest.raises(weights.WeightTreeError):  # no silent rebase onto another registry version
        weights.effective_tree(reg, weights.PersonalStrategyVersion("v2", "s1", "reg-test-2", NS.SANDBOX, (), weights.StrategyStatus.DRAFT, T0))
    with pytest.raises(weights.WeightTreeError):  # UNRESOLVED nodes cannot carry an official weight
        weights.OfficialRegistry("r", (weights.NodeDefinition("x", None, "QGV", weights.NodeType.WEIGHT, weights.Maturity.UNRESOLVED, "x", 1.0),))


def test_parent_zero_keeps_child_mix_with_zero_contribution():
    N, T, M, NS = weights.NodeDefinition, weights.NodeType, weights.Maturity, versioning.ResultNamespace
    reg = weights.OfficialRegistry("r0", (
        N("root", None, "TECHNICAL", T.GROUP, M.PRODUCTION, "root"),
        N("a", "root", "TECHNICAL", T.WEIGHT, M.PRODUCTION, "a", 1.0),
        N("b", "root", "TECHNICAL", T.WEIGHT, M.PRODUCTION, "b", 0.0),
        N("b1", "b", "TECHNICAL", T.WEIGHT, M.PRODUCTION, "b1", 0.3),
        N("b2", "b", "TECHNICAL", T.WEIGHT, M.PRODUCTION, "b2", 0.7),
    ))
    eff = weights.effective_tree(reg, weights.PersonalStrategyVersion("v", "s", "r0", NS.SANDBOX, (), weights.StrategyStatus.DRAFT, T0))
    assert eff["b1"].local_weight == 0.3 and eff["b1"].global_weight == 0.0


def test_strategy_version_hash_changes_with_overrides_only():
    NS, W = versioning.ResultNamespace, weights.WeightOverride
    a, b = _version(NS.SANDBOX, [W("q1", 0.2), W("q2", 0.8)]), _version(NS.SANDBOX, [W("q2", 0.8), W("q1", 0.2)])
    assert a.override_set_hash == b.override_set_hash != _version(NS.SANDBOX, [W("q1", 0.3), W("q2", 0.7)]).override_set_hash


def _model():
    MH = portfolio.ModelHolding
    return portfolio.ModelPortfolioSnapshot("v1", T0, "us_top500_2024-12-31", (MH("sec_aapl", 0.6), MH("sec_brk_b", 0.3)), 0.1, "pp1", "calc1")


def _actual(complete, positions):
    return portfolio.ActualPortfolioSnapshot("u1", ("acc1", "acc2"), T0, tuple(positions), (Money(Decimal("100"), "USD"),), "USD",
                                             complete, quality.DataQuality.VALID)


def _pos(acc, sid, mv, q=quality.DataQuality.VALID):
    return portfolio.Position(acc, sid, Decimal("1"), Money(Decimal(mv), "USD"), T0, T0, portfolio.PositionSource.BROKER, q)


def test_gap_is_model_minus_actual_descriptive_and_missing_is_not_zero():
    gap = portfolio.portfolio_gap(_model(), _actual(True, [_pos("acc1", "sec_aapl", "300"), _pos("acc2", "sec_aapl", "300"),
                                                          _pos("acc1", "sec_x", "300")]), "act1", T0)
    rows = {r.security_id: r for r in gap.rows}
    assert abs(rows["sec_aapl"].gap - (0.6 - 600 / 1000)) < 1e-12
    assert rows["sec_brk_b"].actual_weight == 0.0 and rows["sec_brk_b"].reason_codes == ("NOT_HELD",)
    assert rows["sec_x"].model_weight == 0.0 and abs(rows["sec_x"].gap + 0.3) < 1e-12
    assert not any(hasattr(r, a) for r in gap.rows for a in ("side", "quantity", "order"))
    inc = portfolio.portfolio_gap(_model(), _actual(False, [_pos("acc1", "sec_aapl", "600")]), "act2", T0)
    brk = next(r for r in inc.rows if r.security_id == "sec_brk_b")
    assert brk.actual_weight is None and brk.gap is None and brk.quality_status == quality.DataQuality.UNRESOLVED
    assert inc.quality_status == quality.DataQuality.UNRESOLVED


def test_actual_snapshot_requires_broker_or_user_data_and_base_currency():
    with pytest.raises(ValueError):
        _actual(True, [_pos("other_acc", "sec_aapl", "1")])
    with pytest.raises(ValueError):
        portfolio.ActualPortfolioSnapshot("u", ("acc1",), T0, (portfolio.Position("acc1", "s", Decimal(1), Money(Decimal(1), "KRW"), T0, T0,
                                          portfolio.PositionSource.BROKER, quality.DataQuality.VALID),), (), "USD", True, quality.DataQuality.VALID)
    with pytest.raises(ValueError):
        portfolio.ModelPortfolioSnapshot("v", T0, "u", (portfolio.ModelHolding("a", 0.5),), 0.1, "p", "c")  # sums to 0.6


def test_personal_fit_is_multi_axis_and_restricted_when_unresolved():
    A, X, Q, D = fit.AxisContext, fit.FitAxis, quality.DataQuality, fit.DecisionState
    ok = fit.PersonalFitSnapshot("v1", "sec_aapl", (A(X.FUNDAMENTAL, Q.VALID, ("R1",)), A(X.RISK, Q.VALID, ())), D.HOLD_CONTEXT, "policy-x", (), T0)
    assert not hasattr(ok, "score") and D.HOLD_CONTEXT.value not in ("BUY", "SELL")
    with pytest.raises(ValueError):
        fit.PersonalFitSnapshot("v1", "s", (A(X.TECHNICAL, Q.UNRESOLVED, ("NO_AVAILABLE_AT",)),), D.ELIGIBLE_TO_ADD, "policy-x", (), T0)
    with pytest.raises(ValueError):
        fit.PersonalFitSnapshot("v1", "s", (), D.OBSERVE, "", (), T0)


def test_ports_pit_quality_and_read_only_broker_boundary():
    Q = quality.DataQuality
    ctx = ports.UpstreamContext("ta_1", "TECHNICAL", T0, None, (), (("regime", "TREND_UP"),), Q.VALID)
    assert ports.pit_quality(ctx, T0) == Q.UNRESOLVED  # C-28: no available_at -> unresolved, never derived from as_of
    assert ports.pit_quality(ports.UpstreamContext("q", "QGV", T0, T0 + timedelta(1), (), (), Q.VALID), T0) == Q.INVALID
    assert ports.pit_quality(None, T0) == Q.UNRESOLVED
    members = set(dir(ports.BrokerAdapter))
    assert not members & set(ports.FORBIDDEN_BROKER_METHODS)
    s = ports.ScoreValue(72.0, "0-100", "QGV", "qgv_1", T0, Q.VALID)
    assert s.value == 72.0 and s.scale == "0-100"  # C-29: carried unchanged with its scale
