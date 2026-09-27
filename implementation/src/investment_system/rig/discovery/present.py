"""P4 page composition: discovery panel, impact panel, Common-Connection priority. NEW IMPLEMENTATION.

Composes P1 (page), P2 (badges) and P3 (scope/feed) through their public functions
and ``PageExtras``; no earlier-phase module is modified.
"""

from __future__ import annotations

import html
from dataclasses import replace
from datetime import datetime

from ..intel.intel import IntelIndex
from ..intel.present import intel_rank
from ..ledger import RelationshipLedger
from ..network.labels import Language, term
from ..network.render import render_page
from ..network.views import NetEdge, NewsIndex, RIGViewModel, build_view_model, edge_priority
from ..myview.prefs import HoldingsPort, UserOrganization
from ..myview.present import my_extras
from ..myview.scope import MySets, MyViewState, OverlayPort, build_sets, overlay_rows
from .discovery import (
    FactGraph,
    ResearchPriority,
    emerging,
    fact_graph,
    my_common_connections,
    positions,
    research_priority,
)
from .impact import CONCEPT_SYMBOL, ConceptIndex, ImpactGraph

TERMS_P4: dict[str, tuple[str, str]] = {
    "discovery": ("Discovery", "발견"),
    "HUB": ("Hub", "허브"),
    "BRIDGE": ("Bridge", "브리지"),
    "BOTTLENECK": ("Bottleneck", "병목"),
    "emerging": ("Emerging", "부상"),
    "common": ("Common connections", "공통 연결"),
    "research": ("Research Priority (not a buy/sell view)", "조사 우선순위 (매수·매도 판단 아님)"),
    "HIGH": ("High", "높음"),
    "MEDIUM": ("Medium", "보통"),
    "LOW": ("Low", "낮음"),
    "impact": ("Potential impact paths (not facts)", "잠재 영향 경로 (사실 아님)"),
}


def _e(s) -> str:
    return html.escape(str(s), quote=True)


def discovery_priority(intel: IntelIndex, sets: MySets, common: frozenset[str], as_of: datetime):
    """Critical → Portfolio/관심 → High materiality → Recent change → Common Connection → P1 order."""
    def key(e: NetEdge) -> tuple:
        crit_high, change = intel_rank(intel, e.relationship_id, as_of)
        ends = {e.source_node_id.split(":", 1)[1], e.target_node_id.split(":", 1)[1]}
        return (0 if crit_high == 0 else 1, 0 if ends & sets.my else 1, crit_high, change,
                0 if ends & common else 1) + edge_priority(e)
    return key


def impact_svg(ig: ImpactGraph, names: dict[str, str], concepts: ConceptIndex | None) -> str:
    cols: dict[int, list[str]] = {}
    depth: dict[str, int] = {}
    for p in ig.paths:
        for d, n in enumerate(p.nodes):
            if n not in depth:
                depth[n] = d
                cols.setdefault(d, []).append(n)
    pos = {n: (60 + d * 220, 40 + i * 44) for d, ns in cols.items() for i, n in enumerate(ns)}
    h = 60 + 44 * max((len(v) for v in cols.values()), default=1)
    w = 120 + 220 * max(cols, default=0)
    parts = [f'<svg class="impact" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="impact">'
             '<defs><marker id="iarr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" '
             'orient="auto"><path d="M0,0L10,5L0,10z" fill="currentColor"/></marker></defs>']
    drawn = set()
    for p in ig.paths:
        a, b = p.nodes[-2:] if len(p.nodes) > 1 else (None, None)
        if a is None or (a, b) in drawn:
            continue
        drawn.add((a, b))
        (x1, y1), (x2, y2) = pos[a], pos[b]
        parts.append(f'<line class="impact-path" x1="{x1 + 50}" y1="{y1}" x2="{x2 - 50}" y2="{y2}" '
                     f'stroke="currentColor" stroke-dasharray="2 5" marker-end="url(#iarr)">'
                     f'<title>{_e(p.hops[-1].value)}</title></line>')
    for n, (x, y) in pos.items():
        if n.startswith("concept:") and concepts is not None:
            c = concepts.concepts[n.split(":", 1)[1]]
            label = f"{CONCEPT_SYMBOL[c.kind]} {c.label}"
        else:
            label = names.get(n, n)
        parts.append(f'<text x="{x}" y="{y + 4}" text-anchor="middle" fill="currentColor">{_e(label)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def discovery_panel(fg: FactGraph, graph_emerging: frozenset[str], common: frozenset[str],
                    rp: dict[str, ResearchPriority], names: dict[str, str], lang: Language,
                    impacts: tuple[ImpactGraph, ...], concepts: ConceptIndex | None) -> str:
    t = lambda k: _e(term(k, lang, TERMS_P4))  # noqa: E731
    nm = lambda i: _e(names.get(i, i))  # noqa: E731
    rows = []
    for n, ps in positions(fg).items():
        tags = " · ".join(f'<span data-term="{p.value}">{t(p.value)}</span>' for p in sorted(ps, key=lambda p: p.value))
        rows.append(f"<li>{nm(n)} — {tags}</li>")
    rp_rows = "".join(f'<li>{nm(i)} — <span data-term="{v.value}">{t(v.value)}</span></li>'
                      for i, v in sorted(rp.items(), key=lambda kv: (list(ResearchPriority).index(kv[1]), kv[0]))
                      if v is not ResearchPriority.LOW)
    imp = "".join(impact_svg(ig, names, concepts) for ig in impacts)
    style = ("<style>#discovery{flex-basis:100%;order:9;background:var(--card);border:1px solid var(--line);"
             "padding:6px 10px}#discovery svg{max-width:760px;font-size:13px}</style>")
    return (style + f'<details id="discovery"><summary><span data-term="discovery">{t("discovery")}</span></summary>'
            f'<ul>{"".join(rows)}</ul>'
            f'<p><span data-term="emerging">{t("emerging")}</span>: {", ".join(nm(i) for i in sorted(graph_emerging))}</p>'
            f'<p><span data-term="common">{t("common")}</span>: {", ".join(nm(i) for i in sorted(common))}</p>'
            f'<p><span data-term="research">{t("research")}</span></p><ul>{rp_rows}</ul>'
            + (f'<p><span data-term="impact">{t("impact")}</span></p>{imp}' if impacts else "")
            + "</details>")


def build_rig_page(ledger: RelationshipLedger, news: NewsIndex, intel: IntelIndex, holdings: HoldingsPort,
                   org: UserOrganization, as_of: datetime, state: MyViewState | None = None,
                   lang: Language = Language.KO, overlay_port: OverlayPort | None = None,
                   impacts: tuple[ImpactGraph, ...] = (), concepts: ConceptIndex | None = None
                   ) -> tuple[RIGViewModel, str]:
    state = state or MyViewState()
    sets = build_sets(ledger, holdings, org, as_of)
    graph = ledger.graph_as_of(as_of)
    fg = fact_graph(graph)
    common = my_common_connections(fg, sets.my)
    rp = research_priority(fg, intel, graph, sets.my, as_of)
    vm = build_view_model(ledger, news, as_of, state.base, priority=discovery_priority(intel, sets, common, as_of))
    names = {}
    for i in fg.nodes | sets.my | frozenset(n.issuer_id for n in vm.network.nodes):
        rec = ledger.identity.issuer(i)
        names[i] = rec.legal_name if rec else i
    research_new = frozenset(i for i, v in rp.items() if v is ResearchPriority.HIGH)
    x = my_extras(vm, intel, sets, state, overlay_rows(overlay_port, sets, state, as_of), names, research_new, lang)
    panel = discovery_panel(fg, emerging(graph, intel, as_of), common, rp, names, lang, impacts, concepts)
    x = replace(x, toolbar_html=x.toolbar_html + panel, terms={**x.terms, **TERMS_P4})
    return vm, render_page(vm, lang, x)
