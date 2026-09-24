"""Product/UI architecture. NEW IMPLEMENTATION. Not backend module map."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import WorkspaceId

# Backend infrastructure — never a top-level user menu.
BACKEND_INFRA = (
    "providers",
    "sec_companyfacts",
    "yahoo_chart",
    "env_price",
    "pit.resolver",
    "qgv.raw_map",
    "qgv.pipeline",
    "qgv.book",
    "markets.us",
    "markets.kr",
)


@dataclass(frozen=True)
class NavPage:
    page_id: str
    workspace: WorkspaceId
    title: str
    path: str
    backend_engines: tuple[str, ...]


NAV_PAGES: tuple[NavPage, ...] = (
    NavPage("home", WorkspaceId.HOME, "Home", "index.html", ("integration.engine",)),
    NavPage("qgv_analysis", WorkspaceId.QGV, "QGV 분석", "qgv/analysis.html", ("qgv.analysis", "qgv.pipeline")),
    NavPage("qgv_sim", WorkspaceId.QGV, "QGV 모의투자", "qgv/simulation.html", ("qgv.simulation",)),
    NavPage("qgv_pf", WorkspaceId.QGV, "QGV 포트폴리오", "qgv/portfolio.html", ("qgv.portfolio",)),
    NavPage("qgv_lb", WorkspaceId.QGV, "QGV 리더보드", "qgv/leaderboard.html", ("qgv.leaderboard",)),
    NavPage("qgv_tr", WorkspaceId.QGV, "QGV Track Record", "qgv/track_record.html", ("qgv.track_record",)),
    NavPage("ta_search", WorkspaceId.TECHNICAL, "종목 검색", "technical/search.html", ("qgv.identifiers",)),
    NavPage("ta_chart", WorkspaceId.TECHNICAL, "Chart", "technical/chart.html", ("technical.engine",)),
    NavPage("ta_signal", WorkspaceId.TECHNICAL, "Indicator / Signal", "technical/signal.html", ("technical.engine",)),
    NavPage("ta_state", WorkspaceId.TECHNICAL, "Technical State / Regime", "technical/state.html", ("technical.engine",)),
    NavPage("ta_scenario", WorkspaceId.TECHNICAL, "Scenario", "technical/scenario.html", ("technical.engine",)),
    NavPage("ta_exec", WorkspaceId.TECHNICAL, "Execution", "technical/execution.html", ("technical.engine", "integration.engine")),
    NavPage("macro_dash", WorkspaceId.MACRO, "Macro Dashboard", "macro/dashboard.html", ("macro.engine",)),
    NavPage("macro_pillars", WorkspaceId.MACRO, "Growth / Inflation / Rates / Liquidity / Risk", "macro/pillars.html", ("macro.engine",)),
    NavPage("macro_regime", WorkspaceId.MACRO, "Macro Regime", "macro/regime.html", ("macro.engine",)),
    NavPage("integrated_dash", WorkspaceId.INTEGRATED, "Integrated Dashboard", "integrated/dashboard.html", ("integration.engine",)),
    NavPage("lab", WorkspaceId.LAB, "Strategy Lab", "lab/strategy.html", ("strategy.profile", "validation.backtest")),
)


def user_menu_ids() -> tuple[str, ...]:
    return tuple(p.page_id for p in NAV_PAGES)


def workspace_pages(ws: WorkspaceId) -> tuple[NavPage, ...]:
    return tuple(p for p in NAV_PAGES if p.workspace == ws)
