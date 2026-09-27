"""E3 — deterministic search / filter over the Active catalog (Track E). No ranking model, no recommendation engine:
filters are exact matches on Frozen metadata (or derived views), keyword is a case-insensitive substring match over
title / purpose / keywords / aliases / tags / codes. Results keep catalog order."""
from __future__ import annotations

from typing import Iterable

from .catalog import DOMAINS, INPUT_MODES, ROLES, SCOPE_VARIABLES, Catalog, PromptRecord


class SearchFilterError(ValueError):
    """An unknown filter value (fail-closed instead of silently returning nothing)."""


def _haystack(p: PromptRecord) -> str:
    return "\n".join((p.prompt_id, p.prompt_code, p.title, p.purpose, *p.keywords, *p.aliases, *p.tags)).casefold()


def search(catalog: Catalog, keyword: str | None = None, *, domain: str | None = None, role: str | None = None,
           category: str | None = None, subcategory: str | None = None, scope: str | None = None,
           starter: bool | None = None, bundle: int | None = None, input_mode: str | None = None,
           tags: Iterable[str] = ()) -> tuple[PromptRecord, ...]:
    """Active prompts matching every given filter.

    domain: DISCOVERY | FUNDAMENTAL | TECHNICAL | MACRO | CROSS_VALIDATION
    role: BASIC | EXPAND | CHALLENGE | BLIND-SPOT
    scope: COMPANY | INDUSTRY | THEME | UNIVERSE | MARKET (derived from the prompt's declared subject variables)
    starter: True -> Starter 6 only; bundle: Bundle number -> its prompts (in Bundle order)
    input_mode: SYSTEM_CONTEXT | STANDALONE -> prompts that accept that mode (TECH/MACRO only)
    """
    if domain is not None and domain not in DOMAINS:
        raise SearchFilterError(f"unknown domain {domain!r}; one of {DOMAINS}")
    if role is not None and role not in ROLES:
        raise SearchFilterError(f"unknown role {role!r}; one of {ROLES}")
    if scope is not None and scope not in SCOPE_VARIABLES:
        raise SearchFilterError(f"unknown scope {scope!r}; one of {tuple(SCOPE_VARIABLES)}")
    if input_mode is not None and input_mode not in INPUT_MODES:
        raise SearchFilterError(f"unknown input_mode {input_mode!r}; one of {INPUT_MODES}")
    if category is not None and category not in {p.category for p in catalog.active()}:
        raise SearchFilterError(f"unknown category {category!r}")
    if subcategory is not None and subcategory not in {p.subcategory for p in catalog.active()}:
        raise SearchFilterError(f"unknown subcategory {subcategory!r}")
    pool: list[PromptRecord] = list(catalog.active())
    if bundle is not None:
        b = next((b for b in catalog.bundles if b.number == bundle), None)
        if b is None:
            raise SearchFilterError(f"unknown bundle {bundle!r}")
        pool = [catalog.prompts[pid] for pid in b.prompt_ids]
    want_tags = {t.casefold() for t in tags}
    kw = (keyword or "").strip().casefold()
    out = []
    for p in pool:
        if domain and p.domain != domain:
            continue
        if role and p.role != role:
            continue
        if category and p.category != category:
            continue
        if subcategory and p.subcategory != subcategory:
            continue
        if scope and scope not in p.scopes:
            continue
        if starter is not None and (p.prompt_id in catalog.starters) != starter:
            continue
        if input_mode and not p.requires_input_mode:
            continue
        if want_tags and not want_tags <= {t.casefold() for t in p.tags}:
            continue
        if kw and not all(term in _haystack(p) for term in kw.split()):
            continue
        out.append(p)
    return tuple(out)


def facets(catalog: Catalog) -> dict[str, dict[str, int]]:
    """Counts per filter value for navigation (Domain / Role / Scope / Category)."""
    out: dict[str, dict[str, int]] = {"domain": {}, "role": {}, "scope": {}, "category": {}}
    for p in catalog.active():
        out["domain"][p.domain] = out["domain"].get(p.domain, 0) + 1
        out["role"][p.role] = out["role"].get(p.role, 0) + 1
        out["category"][p.category] = out["category"].get(p.category, 0) + 1
        for s in p.scopes:
            out["scope"][s] = out["scope"].get(s, 0) + 1
    return out
