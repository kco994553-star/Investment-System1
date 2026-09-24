"""Static HTML sample for the US working book. NEW TOOLING."""

from __future__ import annotations

from pathlib import Path


def render_us_book_html(session: dict) -> str:
    rows = []
    for r in session.get("rows", []):
        q = "" if r.get("Q") is None else f"{r['Q']:.1f}"
        g = "" if r.get("G") is None else f"{r['G']:.1f}"
        px = "—" if r.get("price") is None else f"{r['price']:,.2f}"
        w = f"{r['target_weight']*100:.2f}%"
        rows.append(
            f"<tr><td>{r['company_id']}</td><td>{r['yahoo']}</td><td>{r['exchange']}</td>"
            f"<td class='num'>{w}</td><td class='num'>{q}</td><td class='num'>{g}</td>"
            f"<td class='muted'>null</td><td class='num'>{px}</td>"
            f"<td>{r.get('price_evidence') or '—'}</td></tr>"
        )
    body = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Investment-System1 · US Working Book Sample</title>
  <style>
    :root {{ --ink:#15202b; --paper:#f4efe6; --card:#fffdf8; --line:#d7cfc2; --acc:#1f4e5f; --warn:#8a4b12; }}
    body {{ margin:0; font-family: "Iowan Old Style", Georgia, serif; background:var(--paper); color:var(--ink); }}
    header {{ padding:28px 32px 12px; border-bottom:1px solid var(--line); background:#efe8db; }}
    h1 {{ margin:8px 0 4px; font-size:26px; }}
    .sub {{ color:#4c5964; font-size:14px; }}
    .badges {{ margin-top:10px; }}
    .badge {{ display:inline-block; font-size:11px; letter-spacing:.04em; border:1px solid var(--ink); padding:3px 8px; margin:0 6px 6px 0; }}
    .warn {{ border-color:var(--warn); color:var(--warn); }}
    main {{ padding:24px 32px 48px; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-bottom:24px; }}
    .card {{ background:var(--card); border:1px solid var(--line); padding:14px 16px; }}
    .k {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:#667; }}
    .v {{ font-size:20px; margin-top:4px; }}
    table {{ width:100%; border-collapse:collapse; background:var(--card); }}
    th,td {{ border-bottom:1px solid var(--line); padding:8px 10px; font-size:13px; text-align:left; }}
    th {{ font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:#556; }}
    .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
    .muted {{ color:#888; }}
    footer {{ margin-top:24px; font-size:13px; color:#4c5964; }}
    @media (max-width:900px) {{ .grid {{ grid-template-columns:1fr 1fr; }} main,header {{ padding:16px; }} }}
  </style>
</head>
<body>
  <header>
    <div class="badges">
      <span class="badge">NEW IMPLEMENTATION</span>
      <span class="badge">US TRACK</span>
      <span class="badge">QGV SYNTHETIC</span>
      <span class="badge">PRICES LIVE_FETCH</span>
      <span class="badge warn">NOT STAGE 2</span>
      <span class="badge warn">KR DEFERRED</span>
    </div>
    <h1>US Working Book · sample console</h1>
    <p class="sub">Official v1.1은 19종목 그대로. 이 화면은 미국 상장 17종목 working book이다. V 생산점수는 null.</p>
  </header>
  <main>
    <section class="grid">
      <div class="card"><div class="k">Names</div><div class="v">{session.get("names")}</div></div>
      <div class="card"><div class="k">Priced</div><div class="v">{session.get("priced")}</div></div>
      <div class="card"><div class="k">Portfolio</div><div class="v">{session.get("portfolio_version")}</div></div>
      <div class="card"><div class="k">V production</div><div class="v">null</div></div>
    </section>
    <table>
      <thead>
        <tr><th>company_id</th><th>yahoo</th><th>exch</th><th class="num">US wt</th><th class="num">Q</th><th class="num">G</th><th>V</th><th class="num">last</th><th>price evidence</th></tr>
      </thead>
      <tbody>
        {body}
      </tbody>
    </table>
    <footer>
      Excluded: hanmi = KR_DEFERRED · tokyo_electron = C-08_NON_US.<br/>
      Q/G는 synthetic fixture. 가격은 Yahoo current session. 2026-09-14 official snapshot에 붙이지 않음.<br/>
      session as_of: {session.get("as_of_session")}
    </footer>
  </main>
</body>
</html>
"""


def write_us_book_html(session: dict, path: Path | None = None) -> Path:
    root = Path(__file__).resolve().parents[3] / "web"
    root.mkdir(exist_ok=True)
    path = path or root / "us_book_sample.html"
    path.write_text(render_us_book_html(session), encoding="utf-8")
    return path
