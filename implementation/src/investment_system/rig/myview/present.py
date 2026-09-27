"""P3 page composition: 내 기업 | 전체 scope, chips, groups, ◎/★ nodes, feed order, overlay. NEW IMPLEMENTATION.

Built only on P1/P2 extension points. Client-side scope switching mirrors ``scope.select``
over embedded id sets and hides elements with a separate ``out-scope`` class, so the P1
viewport/focus state is untouched by a scope change.
"""

from __future__ import annotations

import html
import json
from dataclasses import replace
from datetime import datetime

from ..intel.intel import IntelIndex
from ..intel.present import intel_extras
from ..ledger import RelationshipLedger
from ..network.labels import Language, term
from ..network.render import PageExtras, render_page
from ..network.views import NewsIndex, RIGViewModel, build_view_model
from .prefs import HoldingsPort, UserOrganization
from .scope import (
    Chip,
    MySets,
    MyViewState,
    OverlayPort,
    Scope,
    build_sets,
    feed_order,
    feed_tiers,
    my_priority,
    overlay_rows,
)

TERMS_P3: dict[str, tuple[str, str]] = {
    "scope_MY": ("My companies", "내 기업"),
    "scope_ALL": ("All", "전체"),
    "chip_HELD": ("◎ Held", "◎ 보유"),
    "chip_INTEREST": ("★ Interest", "★ 관심"),
    "chip_GROUP": ("Group", "그룹"),
    "chip_RELATED": ("Related", "연관"),
    "overlay": ("Investment Overlay (read-only)", "투자 오버레이 (읽기 전용)"),
    "no_group": ("No group", "그룹 없음"),
}

SCOPE_JS = r"""
(()=>{const S=JSON.parse(document.getElementById('rig-scope').textContent);
let scope=S.scope,chips=new Set(S.chips),group=S.group;
function sel(){if(scope==='ALL')return null;const base=new Set();
 if(chips.has('HELD'))S.held.forEach(x=>base.add(x));if(chips.has('INTEREST'))S.interest.forEach(x=>base.add(x));
 if(chips.has('GROUP')&&group)(S.groups[group]||[]).forEach(x=>base.add(x));
 const nodes=new Set(base);if(chips.has('RELATED'))base.forEach(x=>(S.adj[x]||[]).forEach(y=>nodes.add(y)));
 const rels=new Set(Object.entries(S.edges).filter(([id,[a,b]])=>nodes.has(a)&&nodes.has(b)&&(base.has(a)||base.has(b))).map(([id])=>id));
 const evs=new Set(Object.entries(S.cards).filter(([id,is])=>is.some(i=>nodes.has(i))).map(([id])=>id));
 return{nodes,rels,evs}}
function applyScope(){const r=sel();
 document.querySelectorAll('[data-node]').forEach(e=>e.classList.toggle('out-scope',!!r&&!r.nodes.has(e.dataset.node.split(':').slice(1).join(':'))));
 document.querySelectorAll('[data-edge]').forEach(e=>e.classList.toggle('out-scope',!!r&&!r.rels.has(e.dataset.edge)));
 document.querySelectorAll('article[data-event]').forEach(e=>e.classList.toggle('out-scope',!!r&&!r.evs.has(e.dataset.event)));
 document.querySelectorAll('[data-scope]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.scope===scope));
 document.querySelectorAll('[data-chip]').forEach(b=>b.setAttribute('aria-pressed',chips.has(b.dataset.chip)))}
document.querySelectorAll('[data-scope]').forEach(b=>b.onclick=()=>{scope=b.dataset.scope;applyScope()});
document.querySelectorAll('[data-chip]').forEach(b=>b.onclick=()=>{const c=b.dataset.chip;chips.has(c)?chips.delete(c):chips.add(c);applyScope()});
const g=document.getElementById('grp');if(g)g.onchange=ev=>{group=ev.target.value||null;applyScope()};
window.rigScope=()=>{const r=sel();return{scope,chips:[...chips].sort(),group,
 nodes:r?[...r.nodes].sort():null,rels:r?[...r.rels].sort():null,evs:r?[...r.evs].sort():null}};
document.addEventListener('DOMContentLoaded',applyScope);applyScope()})();
"""


def _e(s) -> str:
    return html.escape(str(s), quote=True)


def my_extras(vm: RIGViewModel, intel: IntelIndex, sets: MySets, state: MyViewState,
              overlay: dict[str, tuple[tuple[str, str], ...]], names: dict[str, str],
              research_new: frozenset[str] = frozenset(), lang: Language = Language.KO) -> PageExtras:
    base = intel_extras(intel, vm)
    t = lambda k: _e(term(k, lang, TERMS_P3))  # noqa: E731
    symbols = {}
    for n in vm.network.nodes:
        if n.issuer_id in sets.held:
            symbols[n.node_id] = "◎"
        elif n.issuer_id in sets.interest:
            symbols[n.node_id] = "★"
    data = {
        "scope": state.scope.value, "chips": sorted(c.value for c in state.chips), "group": state.group_id,
        "held": sorted(sets.held), "interest": sorted(sets.interest),
        "groups": {g: sorted(m) for g, m in sets.groups.items()},
        "adj": {k: sorted(v) for k, v in sorted(sets.adjacency.items())},
        "edges": {e.relationship_id: [e.source_node_id.split(":", 1)[1], e.target_node_id.split(":", 1)[1]]
                  for e in vm.network.edges},
        "cards": {c.event_id: list(c.issuer_ids) for c in vm.cards},
    }
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    seg = "".join(f'<button data-scope="{s.value}"><span data-term="scope_{s.value}">{t("scope_" + s.value)}</span>'
                  f'</button>' for s in Scope)
    chips = "".join(f'<button data-chip="{c.value}"><span data-term="chip_{c.value}">{t("chip_" + c.value)}</span>'
                    f'</button>' for c in Chip)
    opts = f'<option value="" data-term="no_group">{t("no_group")}</option>' + "".join(
        f'<option value="{_e(g)}"{" selected" if g == state.group_id else ""}>{_e(n)}</option>'
        for g, n in sets.group_names.items())
    ov = ""
    if overlay:
        rows = "".join(f"<tr><td>{_e(names.get(i, i))}</td><td>{_e(k)}</td><td>{_e(v)}</td></tr>"
                       for i, rs in overlay.items() for k, v in rs)
        ov = (f'<details id="overlay"><summary><span data-term="overlay">{t("overlay")}</span></summary>'
              f'<table>{rows}</table></details>')
    toolbar = (f'<style>.out-scope{{display:none!important}}</style><div class="seg">{seg}</div>'
               f'<div class="seg">{chips}</div><select id="grp" aria-label="group">{opts}</select>{ov}'
               f'<script type="application/json" id="rig-scope">{payload}</script><script>{SCOPE_JS}</script>')
    tiers = feed_tiers(vm, intel, sets, research_new)
    return replace(base, node_symbol=symbols, toolbar_html=toolbar, terms={**base.terms, **TERMS_P3},
                   card_order=feed_order(vm, tiers))


def build_my_page(ledger: RelationshipLedger, news: NewsIndex, intel: IntelIndex, holdings: HoldingsPort,
                  org: UserOrganization, as_of: datetime, state: MyViewState | None = None,
                  lang: Language = Language.KO, overlay_port: OverlayPort | None = None,
                  research_new: frozenset[str] = frozenset()) -> tuple[RIGViewModel, MySets, str]:
    state = state or MyViewState()
    sets = build_sets(ledger, holdings, org, as_of)
    vm = build_view_model(ledger, news, as_of, state.base, priority=my_priority(intel, sets, as_of))
    names = {n.issuer_id: n.label for n in vm.network.nodes}
    for i in sets.my:
        rec = ledger.identity.issuer(i)
        names.setdefault(i, rec.legal_name if rec else i)
    extras = my_extras(vm, intel, sets, state, overlay_rows(overlay_port, sets, state, as_of), names, research_new,
                       lang)
    return vm, sets, render_page(vm, lang, extras)
