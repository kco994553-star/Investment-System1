"""E0/E1 — Frozen Catalog loader and runtime schema for Prompt Library v1 (Track E).

The single source of truth is the Frozen Markdown catalog `PLV1_CONTENT_V1.0` shipped verbatim in `content/`
(SHA-256 pinned below) plus its Decision History (merge / retire migration). Nothing here re-authors content: the
loader parses the Frozen text into immutable records and fails closed if the bytes differ from the Frozen baseline.

Schema (`SCHEMA_VERSION`) — only fields present in the Frozen catalog plus a few DERIVED, read-only views:
  PromptRecord: prompt_id, prompt_code, title, purpose, status, domain, role, category, subcategory, tags,
                keywords, aliases, variables, system_overlap, body (+ derived: requires_input_mode, scopes,
                system_input_variables)
  MigrationRecord: prompt_id, legacy_code, status (MERGED_INTO | RETIRED_SYSTEM_OVERLAP), target_prompt_id,
                   note (preserved purpose or retire reason), replacement_path
  Bundle: number, name, prompt_ids (IDs only -- a Bundle never copies a prompt body)
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

SCHEMA_VERSION = "plv1.runtime.schema.v1"
CONTENT_VERSION = "PLV1_CONTENT_V1.0"
CONTENT_DIR = Path(__file__).resolve().parent / "content"
CATALOG_FILE = "Investment_Prompt_Library_v1_Content_Catalog_FROZEN.md"
DECISION_HISTORY_FILE = "Investment_Prompt_Library_v1_Decision_History.md"
# Frozen catalog SHA-256 as recorded in the Decision History / Content Regression Report (Freeze 2026-09-27 12:36:40 KST)
FROZEN_CATALOG_SHA256 = "f0a6ed9005e22b8fa534d51135cc3e734aa9577150438a35d65823a4c283e68e"
# Decision History as received with the Frozen catalog (Track E intake 2026-09-27)
DECISION_HISTORY_SHA256 = "a8e764c29cd0ec6346fd0798503c6bd6d0ee67de89595cffcb526122f5589208"

DOMAINS = ("DISCOVERY", "FUNDAMENTAL", "TECHNICAL", "MACRO", "CROSS_VALIDATION")
ROLES = ("BASIC", "EXPAND", "CHALLENGE", "BLIND-SPOT")
INPUT_MODES = ("SYSTEM_CONTEXT", "STANDALONE")
MIGRATION_STATUSES = ("MERGED_INTO", "RETIRED_SYSTEM_OVERLAP")

# Applicable scope, derived from which subject variables a prompt declares (no new content field).
SCOPE_VARIABLES = MappingProxyType({
    "COMPANY": ("company", "ticker", "seed_company", "seed_ticker"),
    "INDUSTRY": ("industry", "industry_or_theme"),
    "THEME": ("theme", "industry_or_theme"),
    "UNIVERSE": ("universe",),
    "MARKET": ("market",),
})
# Variables through which a prompt CONSUMES an existing system result (it never recomputes it); owner in brackets.
SYSTEM_INPUT_VARIABLES = MappingProxyType({
    "qgv_snapshot_summary": "QGV",
    "existing_system_candidates": "QGV_LEADERBOARD",
    "technical_input": "TECHNICAL",
    "technical_screen_summary": "TECHNICAL",
    "macro_input": "MACRO",
    "macro_snapshot_summary": "MACRO",
    "system_summary": "INTEGRATED",
    "system_coverage_summary": "INTEGRATED",
    "snapshot_refs": "INTEGRATED",
})

_VAR = re.compile(r"\{\{([a-z_]+)\}\}")


class CatalogIntegrityError(ValueError):
    """The Frozen catalog is missing, altered or internally inconsistent (fail-closed)."""


@dataclass(frozen=True)
class PromptRecord:
    prompt_id: str
    prompt_code: str
    title: str
    purpose: str
    status: str
    domain: str
    role: str
    category: str
    subcategory: str
    tags: tuple[str, ...]
    keywords: tuple[str, ...]
    aliases: tuple[str, ...]
    variables: tuple[str, ...]
    system_overlap: str
    body: str
    content_version: str = CONTENT_VERSION

    @property
    def requires_input_mode(self) -> bool:
        return "input_mode" in self.variables

    @property
    def scopes(self) -> tuple[str, ...]:
        return tuple(s for s, names in SCOPE_VARIABLES.items() if any(n in self.variables for n in names))

    @property
    def system_input_variables(self) -> tuple[str, ...]:
        return tuple(v for v in self.variables if v in SYSTEM_INPUT_VARIABLES)

    @property
    def legacy_code(self) -> str:
        return self.prompt_code.rsplit(".v", 1)[0]


@dataclass(frozen=True)
class MigrationRecord:
    prompt_id: str
    legacy_code: str
    status: str
    target_prompt_id: str | None
    note: str
    replacement_path: str | None = None


@dataclass(frozen=True)
class Bundle:
    number: int
    name: str
    prompt_ids: tuple[str, ...]


@dataclass(frozen=True)
class Catalog:
    content_version: str
    status_line: str
    freeze_time: str
    sha256: str
    prompts: Mapping[str, PromptRecord]
    starters: tuple[str, ...]
    bundles: tuple[Bundle, ...]
    migrations: Mapping[str, MigrationRecord]
    schema_version: str = SCHEMA_VERSION
    _codes: Mapping[str, str] = field(default_factory=dict, repr=False)

    def active(self) -> tuple[PromptRecord, ...]:
        return tuple(self.prompts.values())

    def get(self, prompt_id: str) -> PromptRecord:
        return self.prompts[prompt_id]


def variables_in(text: str) -> tuple[str, ...]:
    """Distinct {{variable}} names in order of first appearance."""
    seen: dict[str, None] = {}
    for m in _VAR.finditer(text):
        seen.setdefault(m.group(1), None)
    return tuple(seen)


def _ticks(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"`([^`]*)`", value))


def _one_tick(value: str, key: str, code: str) -> str:
    vals = _ticks(value)
    if len(vals) != 1:
        raise CatalogIntegrityError(f"{code}: field {key} must hold exactly one `value`")
    return vals[0]


def parse_catalog(text: str) -> tuple[dict, list[PromptRecord]]:
    """Header facts + prompt records, parsed from the Frozen Markdown (no content interpretation)."""
    head = text.split("\n## Active canonical prompts", 1)
    if len(head) != 2:
        raise CatalogIntegrityError("section '## Active canonical prompts' not found")
    header, body = head
    m_ver = re.search(r"^Catalog version: `([^`]+)`", header, re.M)
    m_status = re.search(r"^Status: \*\*(.+?)\*\*", header, re.M)
    m_time = re.search(r"^Freeze time: `([^`]+)`", header, re.M)
    m_n = re.search(r"^Active canonical prompts: \*\*(\d+)\*\*", header, re.M)
    if not (m_ver and m_status and m_time and m_n):
        raise CatalogIntegrityError("catalog header (version/status/freeze time/active count) incomplete")
    starter_sec = re.search(r"^## Starter \d+\n(.*?)(?=^## )", header, re.M | re.S)
    bundle_sec = re.search(r"^## Bundle reference\n(.*)", header, re.M | re.S)
    if not (starter_sec and bundle_sec):
        raise CatalogIntegrityError("Starter / Bundle sections not found")
    starters = tuple(re.findall(r"^\d+\. `([^`]+)`\s*$", starter_sec.group(1), re.M))
    bundles = []
    for num, name, ids in re.findall(r"^(\d+)\. \*\*(.+?)\*\* — (.+)$", bundle_sec.group(1), re.M):
        bundles.append(Bundle(int(num), name, _ticks(ids)))
    facts = {"content_version": m_ver.group(1), "status_line": m_status.group(1), "freeze_time": m_time.group(1),
             "declared_active": int(m_n.group(1)), "starters": starters, "bundles": tuple(bundles)}

    records = []
    for chunk in re.split(r"^### ", body, flags=re.M)[1:]:
        title_line, _, rest = chunk.partition("\n")
        m_title = re.match(r"(\S+) — (.+)$", title_line.strip())
        if not m_title:
            raise CatalogIntegrityError(f"prompt heading not parseable: {title_line!r}")
        meta_part, sep, after = rest.partition("```text\n")
        prompt_body, sep2, _ = after.partition("\n```")
        if not sep or not sep2:
            raise CatalogIntegrityError(f"{m_title.group(1)}: ```text body block missing")
        meta = {}
        for k, v in re.findall(r"^- ([a-z_]+): (.*)$", meta_part, re.M):
            if k in meta:
                raise CatalogIntegrityError(f"{m_title.group(1)}: duplicate field {k}")
            meta[k] = v
        need = ("prompt_id", "prompt_code", "status", "purpose", "domain", "role", "category", "subcategory", "tags",
                "keywords", "aliases", "variables", "system_overlap")
        missing = [k for k in need if k not in meta]
        if missing:
            raise CatalogIntegrityError(f"{m_title.group(1)}: missing fields {missing}")
        code = _one_tick(meta["prompt_code"], "prompt_code", m_title.group(1))
        if code != m_title.group(1):
            raise CatalogIntegrityError(f"heading {m_title.group(1)} != prompt_code {code}")
        records.append(PromptRecord(
            prompt_id=_one_tick(meta["prompt_id"], "prompt_id", code), prompt_code=code, title=m_title.group(2),
            purpose=meta["purpose"].strip(), status=_one_tick(meta["status"], "status", code),
            domain=_one_tick(meta["domain"], "domain", code), role=_one_tick(meta["role"], "role", code),
            category=_one_tick(meta["category"], "category", code),
            subcategory=_one_tick(meta["subcategory"], "subcategory", code),
            tags=_ticks(meta["tags"]), keywords=_ticks(meta["keywords"]), aliases=_ticks(meta["aliases"]),
            variables=tuple(v.strip("{}") for v in _ticks(meta["variables"])),
            system_overlap=_one_tick(meta["system_overlap"], "system_overlap", code),
            body=prompt_body, content_version=facts["content_version"]))
    return facts, records


def parse_decision_history(text: str) -> list[MigrationRecord]:
    out = []
    merge = re.search(r"^## Merge migration\n(.*?)(?=^## )", text, re.M | re.S)
    retire = re.search(r"^## Retired migration\n(.*?)(?=^## )", text, re.M | re.S)
    if not (merge and retire):
        raise CatalogIntegrityError("Decision History merge/retire tables not found")
    for row in merge.group(1).splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")] if row.startswith("| `") else []
        if len(cells) == 5:
            out.append(MigrationRecord(cells[0].strip("`"), cells[1].strip("`"), cells[2].strip("`"),
                                       cells[3].strip("`"), cells[4]))
    for row in retire.group(1).splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")] if row.startswith("| `") else []
        if len(cells) == 5:
            out.append(MigrationRecord(cells[0].strip("`"), cells[1].strip("`"), cells[2].strip("`"), None,
                                       cells[3], cells[4].strip("`")))
    return out


def _read_pinned(path: Path, sha: str) -> str:
    if not path.exists():
        raise CatalogIntegrityError(f"CATALOG_NOT_PRESENT: {path.name}")
    raw = path.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != sha:
        raise CatalogIntegrityError(f"FROZEN_CONTENT_HASH_MISMATCH: {path.name} sha256={got} expected={sha}")
    return raw.decode("utf-8")


def build_catalog(catalog_text: str, history_text: str, sha256: str) -> Catalog:
    """Assemble and fully validate a Catalog from texts (raises CatalogIntegrityError on any violation)."""
    from .validation import validate_catalog  # local import: validation imports this module

    facts, records = parse_catalog(catalog_text)
    prompts = {}
    for r in records:
        if r.prompt_id in prompts:
            raise CatalogIntegrityError(f"duplicate prompt_id {r.prompt_id}")
        prompts[r.prompt_id] = r
    migrations = {}
    for m in parse_decision_history(history_text):
        if m.prompt_id in migrations:
            raise CatalogIntegrityError(f"duplicate migration row {m.prompt_id}")
        migrations[m.prompt_id] = m
    cat = Catalog(content_version=facts["content_version"], status_line=facts["status_line"],
                  freeze_time=facts["freeze_time"], sha256=sha256, prompts=MappingProxyType(prompts),
                  starters=facts["starters"], bundles=facts["bundles"], migrations=MappingProxyType(migrations),
                  _codes=MappingProxyType({r.prompt_code: r.prompt_id for r in records}))
    problems = validate_catalog(cat, declared_active=facts["declared_active"])
    if problems:
        raise CatalogIntegrityError("; ".join(problems))
    return cat


_CACHE: dict[str, Catalog] = {}


def load_catalog(content_dir: Path | None = None) -> Catalog:
    """Deterministic load of the Frozen catalog; the same bytes always yield the same Catalog (cached per dir)."""
    d = Path(content_dir) if content_dir else CONTENT_DIR
    key = str(d)
    if key not in _CACHE:
        cat_text = _read_pinned(d / CATALOG_FILE, FROZEN_CATALOG_SHA256)
        hist_text = _read_pinned(d / DECISION_HISTORY_FILE, DECISION_HISTORY_SHA256)
        _CACHE[key] = build_catalog(cat_text, hist_text, FROZEN_CATALOG_SHA256)
    return _CACHE[key]


class RetiredPromptError(LookupError):
    """The identifier names a RETIRED_SYSTEM_OVERLAP prompt; use its replacement path instead."""

    def __init__(self, migration: MigrationRecord):
        super().__init__(f"{migration.prompt_id} ({migration.legacy_code}) is RETIRED_SYSTEM_OVERLAP: "
                         f"{migration.note}; replacement: {migration.replacement_path}")
        self.migration = migration


@dataclass(frozen=True)
class Resolution:
    prompt: PromptRecord
    requested: str
    via: str  # PROMPT_ID | PROMPT_CODE | LEGACY_CODE | MERGED_INTO
    migration: MigrationRecord | None = None


def resolve(catalog: Catalog, identifier: str) -> Resolution:
    """Stable ID, versioned code, legacy code, or a merged source (ID/legacy code) -> the Active canonical prompt.
    Retired identifiers raise RetiredPromptError (with replacement path); unknown identifiers raise KeyError."""
    ident = str(identifier or "").strip()
    if ident in catalog.prompts:
        return Resolution(catalog.prompts[ident], ident, "PROMPT_ID")
    if ident in catalog._codes:
        return Resolution(catalog.prompts[catalog._codes[ident]], ident, "PROMPT_CODE")
    by_legacy = {p.legacy_code: p for p in catalog.prompts.values()}
    if ident in by_legacy:
        return Resolution(by_legacy[ident], ident, "LEGACY_CODE")
    mig = catalog.migrations.get(ident) or next((m for m in catalog.migrations.values() if m.legacy_code == ident), None)
    if mig is not None:
        if mig.status == "RETIRED_SYSTEM_OVERLAP":
            raise RetiredPromptError(mig)
        return Resolution(catalog.prompts[mig.target_prompt_id], ident, "MERGED_INTO", mig)
    raise KeyError(f"UNKNOWN_PROMPT_IDENTIFIER: {ident!r}")
