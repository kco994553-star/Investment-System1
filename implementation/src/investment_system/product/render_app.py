"""Generate static App Shell pages. NEW TOOLING."""

from __future__ import annotations

import os
from pathlib import Path

from ..contracts.enums import WorkspaceId
from ..contracts.product import NAV_PAGES, workspace_pages
from ..contracts.strategy import builtin_profile
from ..qgv.factors import G_WEIGHTS, Q_WEIGHTS
from ..versions import IMPLEMENTATION_LINE, MACRO_CONFIRMED, PORTFOLIO_OFFICIAL, PORTFOLIO_US_WORKING


CSS = """
:root { --ink:#14202b; --paper:#f3eee4; --card:#fffdf8; --line:#d8cfc0; --acc:#1d4f61; --muted:#5b6770; }
* { box-sizing:border-box; }
body { margin:0; font-family:Georgia,"Iowan Old Style",serif; background:var(--paper); color:var(--ink); }
.app { display:grid; grid-template-columns:240px 1fr; min-height:100vh; }
nav { background:#1b2a33; color:#e8efe9; padding:18px 14px; }
nav a { color:#e8efe9; text-decoration:none; display:block; padding:5px 8px; font-size:13px; }
nav a:hover, nav a.active { background:#2b4552; }
nav .ws { margin-top:14px; font-size:10px; letter-spacing:.12em; text-transform:uppercase; color:#9bb; }
nav .brand { font-size:15px; margin:0 0 6px; }
main { padding:24px 28px 48px; }
h1 { margin:0 0 8px; font-size:26px; }
.sub { color:var(--muted); margin:0 0 18px; font-size:14px; }
.badge { display:inline-block; border:1px solid var(--ink); font-size:11px; padding:2px 7px; margin:0 6px 6px 0; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }
.card { background:var(--card); border:1px solid var(--line); padding:14px; }
.card a { color:var(--acc); }
table { width:100%; border-collapse:collapse; background:var(--card); }
th,td { border-bottom:1px solid var(--line); text-align:left; padding:8px; font-size:13px; }
.note { font-size:13px; color:var(--muted); margin-top:16px; }
@media (max-width:800px) { .app { grid-template-columns:1fr; } }
"""


def _nav(active: str) -> str:
    blocks = []
    order = [
        WorkspaceId.HOME,
        WorkspaceId.QGV,
        WorkspaceId.TECHNICAL,
        WorkspaceId.MACRO,
        WorkspaceId.INTEGRATED,
        WorkspaceId.LAB,
    ]
    labels = {
        WorkspaceId.HOME: "Investment System",
        WorkspaceId.QGV: "QGV System",
        WorkspaceId.TECHNICAL: "Technical Analysis",
        WorkspaceId.MACRO: "Macro",
        WorkspaceId.INTEGRATED: "Integrated",
        WorkspaceId.LAB: "Strategy Lab",
    }
    for ws in order:
        blocks.append(f'<div class="ws">{labels[ws]}</div>')
        for p in workspace_pages(ws):
            cls = ' class="active"' if p.page_id == active else ""
            href = p.path if active == p.page_id else _rel(active, p.path)
            blocks.append(f'<a href="{href}"{cls}>{p.title}</a>')
    return "\n".join(blocks)


def _rel(active_id: str, target: str) -> str:
    src = Path(next(p.path for p in NAV_PAGES if p.page_id == active_id))
    return Path(os.path.relpath(target, start=str(src.parent))).as_posix()


def page(active: str, title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} · Investment System</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="app">
    <nav>
      <div class="brand">Investment System</div>
      <div style="font-size:11px;color:#9bb">{IMPLEMENTATION_LINE}</div>
      {_nav(active)}
    </nav>
    <main>
      {body}
    </main>
  </div>
</body>
</html>
"""


def bodies() -> dict[str, tuple[str, str]]:
    qn = len(Q_WEIGHTS)
    gn = len(G_WEIGHTS)
    from ..contracts.enums import StrategyStyle
    from ..contracts.strategy import builtin_profile as bp
    styles = "".join(f"<li>{s.value} · {bp(s).profile_id}</li>" for s in (StrategyStyle.DEFENSIVE, StrategyStyle.BALANCED, StrategyStyle.AGGRESSIVE))
    return {
        "home": (
            "Home",
            f"""
      <div class="badge">PRODUCT UI</div><div class="badge">US TRACK</div><div class="badge">KR DEFERRED</div>
      <h1>Investment System</h1>
      <p class="sub">사용자 Workspace는 QGV / Technical / Macro / Integrated / Strategy Lab. Provider·PIT·Raw Map은 백엔드다.</p>
      <section class="grid">
        <div class="card"><b>QGV System</b><p>분석·모의투자·포트폴리오·리더보드·Track Record</p></div>
        <div class="card"><b>Technical Analysis</b><p>검색·차트·시그널·레짐·시나리오·실행</p></div>
        <div class="card"><b>Macro</b><p>시장 단위 Workspace. Snapshot만 타 모듈이 참조</p></div>
        <div class="card"><b>Integration</b><p>최종 Decision은 여기서만. 모듈별 독자 Decision 없음</p></div>
      </section>
      <p class="note">Official portfolio {PORTFOLIO_OFFICIAL} · US working {PORTFOLIO_US_WORKING} · Macro confirmed {MACRO_CONFIRMED} · Q factors {qn} / G factors {gn} frozen · V production null</p>
            """,
        ),
        "qgv_analysis": ("QGV 분석", "<h1>QGV 분석</h1><p class='sub'>기업 검색 → 기업 분석. Security Context를 Technical과 공유한다.</p><p>Backend: AnalysisEngine / AnalysisPipeline. V_score는 생산 경로에서 null.</p>"),
        "qgv_sim": ("QGV 모의투자", "<h1>QGV 모의투자</h1><p class='sub'>PIT-safe simulation. Backtest와 Track Record는 다른 개념이다.</p>"),
        "qgv_pf": ("QGV 포트폴리오", "<h1>QGV 포트폴리오</h1><p class='sub'>Official v1.1 19종목은 보존. 현재 구현선은 US working 17종목.</p>"),
        "qgv_lb": ("QGV 리더보드", "<h1>QGV 리더보드</h1><p class='sub'>기존 Snapshot을 재채점하지 않는다.</p>"),
        "qgv_tr": ("QGV Track Record", "<h1>QGV Track Record</h1><p class='sub'>as_of Prediction을 immutable 저장한 뒤 Outcome을 연결한다. Backtest 재실행이 아니다.</p>"),
        "ta_search": ("종목 검색", "<h1>종목 검색</h1><p class='sub'>US listings. 선택 결과는 Security Context로 QGV 분석과 공유.</p>"),
        "ta_chart": ("Chart", "<h1>Chart</h1><p class='sub'>Technical workspace. Yahoo는 인프라이지 메뉴가 아니다.</p>"),
        "ta_signal": ("Indicator / Signal", "<h1>Indicator / Signal</h1><p class='sub'>Structural freeze v0.6 엔진 위에 표시만 추가.</p>"),
        "ta_state": ("Technical State / Regime", "<h1>Technical State / Regime</h1>"),
        "ta_scenario": ("Scenario", "<h1>Scenario</h1>"),
        "ta_exec": ("Execution", "<h1>Execution</h1><p class='sub'>주문 의도만. 최종 비중은 Integration Layer.</p>"),
        "macro_dash": ("Macro Dashboard", "<h1>Macro Dashboard</h1><p class='sub'>시장 단위 독립 Workspace. confirmed baseline v0.1.1.</p>"),
        "macro_pillars": ("Pillars", "<h1>Growth / Inflation / Rates / Liquidity / Risk</h1>"),
        "macro_regime": ("Macro Regime", "<h1>Macro Regime</h1><p class='sub'>NORMAL / WARNING / EMERGENCY. v0.1.4 candidate는 승격하지 않음.</p>"),
        "integrated_dash": ("Integrated Dashboard", "<h1>Integrated Dashboard</h1><p class='sub'>QGV Snapshot + Technical Snapshot + Macro Snapshot + Portfolio/Risk → Gate → Target Weight / Execution.</p>"),
        "lab": (
            "Strategy Lab",
            f"""
      <h1>Strategy Lab</h1>
      <p class="sub">Profile 선택 · Custom parameter · Backtest 비교 · Calibration. Frozen contract와 분리.</p>
      <ul>{styles}</ul>
      <p>조합 백테스트: QGV / TA / Macro / QGV+TA / QGV+Macro / TA+Macro / All.</p>
      <p class="note">Profile 수치는 PROVISIONAL. Q/G 공식 가중치와 Q7 라벨은 여기서 바꾸지 않는다.</p>
            """,
        ),
    }


def render_all(root: Path | None = None) -> list[Path]:
    root = root or Path(__file__).resolve().parents[3] / "web" / "app"
    mapping = {p.page_id: p for p in NAV_PAGES}
    written = []
    content = bodies()
    for page_id, nav in mapping.items():
        title, body = content[page_id]
        html = page(page_id, title, body)
        dest = root / nav.path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        written.append(dest)
    return written
