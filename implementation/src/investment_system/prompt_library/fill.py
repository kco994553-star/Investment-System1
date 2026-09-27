"""E4 Variable Fill / E5 Preview / E6 Copy-Export (Track E).

Copy-first: the output is a vendor-neutral plain-text prompt the user pastes into any AI. Nothing is sent anywhere
and no engine is called. The canonical body is never mutated (records are frozen; every fill returns a new string).

Variable rules (D2 — derived from the Frozen text, recorded in the Track E Decision Log):
  - every declared variable is REQUIRED and must be a non-empty value, except `qgv_snapshot_summary`, the only
    variable the Frozen body explicitly allows to be empty ("요약이 비어 있어도 ...") -> blank becomes `NOT_PROVIDED`;
  - `as_of` / `prior_cutoff`: ISO date (YYYY-MM-DD) or ISO datetime with offset; `as_of` may not lie after `now`
    (an information cutoff cannot be in the future); `prior_cutoff` must be strictly before `as_of`;
  - `input_mode`: SYSTEM_CONTEXT | STANDALONE (TECH/MACRO prompts);
  - `candidate_count`: positive integer;
  - values may not contain `{{` / `}}`; unknown variable names are rejected (typo -> fail-closed, not ignored).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from typing import Mapping

from .catalog import INPUT_MODES, SYSTEM_INPUT_VARIABLES, Catalog, PromptRecord

KST = timezone(timedelta(hours=9))
OPTIONAL_VARIABLES = frozenset({"qgv_snapshot_summary"})
NOT_PROVIDED = "NOT_PROVIDED"
DATE_VARIABLES = frozenset({"as_of", "prior_cutoff"})
_PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")

VARIABLE_HINTS = {
    "as_of": "정보 cutoff (PIT). YYYY-MM-DD",
    "prior_cutoff": "이전 분석 cutoff. YYYY-MM-DD, as_of보다 이전",
    "input_mode": "SYSTEM_CONTEXT (기존 Snapshot 소비, 재계산 금지) | STANDALONE (PIT 데이터 직접 제공, 없으면 INSUFFICIENT_DATA)",
    "candidate_count": "최대 후보 수 (양의 정수)",
    "qgv_snapshot_summary": "기존 QGV 요약 (선택; 비우면 NOT_PROVIDED)",
}


class VariableFillError(ValueError):
    def __init__(self, prompt_code: str, missing=(), invalid=(), unknown=()):
        self.missing, self.invalid, self.unknown = tuple(missing), tuple(invalid), tuple(unknown)
        parts = []
        if self.missing:
            parts.append(f"missing required {list(self.missing)}")
        if self.invalid:
            parts.append(f"invalid {list(self.invalid)}")
        if self.unknown:
            parts.append(f"unknown variables {list(self.unknown)}")
        super().__init__(f"{prompt_code}: " + "; ".join(parts))


@dataclass(frozen=True)
class VariableSpec:
    name: str
    required: bool
    kind: str  # DATE | INPUT_MODE | POSITIVE_INT | TEXT
    system_input_owner: str | None
    hint: str


def variable_specs(prompt: PromptRecord) -> tuple[VariableSpec, ...]:
    out = []
    for v in prompt.variables:
        kind = ("DATE" if v in DATE_VARIABLES else "INPUT_MODE" if v == "input_mode"
                else "POSITIVE_INT" if v == "candidate_count" else "TEXT")
        out.append(VariableSpec(v, v not in OPTIONAL_VARIABLES, kind, SYSTEM_INPUT_VARIABLES.get(v),
                                VARIABLE_HINTS.get(v, "")))
    return tuple(out)


def _parse_instant(value: str) -> datetime | None:
    s = value.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            d = date.fromisoformat(s)
            return datetime(d.year, d.month, d.day, tzinfo=KST)
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else None  # naive datetimes are ambiguous -> rejected


def check_values(prompt: PromptRecord, values: Mapping[str, object], now: datetime | None = None,
                 partial: bool = False) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    """(normalized values, missing, invalid, unknown). partial=True reports missing without raising."""
    declared = set(prompt.variables)
    unknown = sorted(k for k in values if k not in declared)
    norm, missing, invalid = {}, [], []
    for spec in variable_specs(prompt):
        raw = values.get(spec.name)
        text = "" if raw is None else str(raw).strip()
        if not text:
            if spec.required:
                missing.append(spec.name)
            else:
                norm[spec.name] = NOT_PROVIDED
            continue
        if "{{" in text or "}}" in text:
            invalid.append(f"{spec.name}: placeholder braces are not allowed in values")
            continue
        if spec.kind == "DATE" and _parse_instant(text) is None:
            invalid.append(f"{spec.name}: not an ISO date (YYYY-MM-DD) or offset-aware ISO datetime")
            continue
        if spec.kind == "INPUT_MODE" and text not in INPUT_MODES:
            invalid.append(f"input_mode: {text!r} not in {INPUT_MODES}")
            continue
        if spec.kind == "POSITIVE_INT" and not (text.isdigit() and int(text) > 0):
            invalid.append(f"{spec.name}: not a positive integer")
            continue
        norm[spec.name] = text
    as_of = _parse_instant(norm["as_of"]) if "as_of" in norm else None
    if as_of is not None:
        ref = now or datetime.now(timezone.utc)
        if as_of > ref:
            invalid.append("as_of: information cutoff lies in the future")
        prior = _parse_instant(norm["prior_cutoff"]) if "prior_cutoff" in norm else None
        if prior is not None and not prior < as_of:
            invalid.append("prior_cutoff: must be strictly before as_of")
    return norm, missing, invalid, unknown


def fill(prompt: PromptRecord, values: Mapping[str, object], now: datetime | None = None) -> str:
    """Filled plain-text prompt; raises VariableFillError on any missing/invalid/unknown variable (fail-closed)."""
    norm, missing, invalid, unknown = check_values(prompt, values, now)
    if missing or invalid or unknown:
        raise VariableFillError(prompt.prompt_code, missing, invalid, unknown)
    text = _PLACEHOLDER.sub(lambda m: norm[m.group(1)], prompt.body)
    if "{{" in text or "}}" in text:  # defensive: a declared variable left unsubstituted
        raise VariableFillError(prompt.prompt_code, invalid=["unsubstituted placeholder after fill"])
    return text


@dataclass(frozen=True)
class Preview:
    prompt_id: str
    prompt_code: str
    title: str
    content_version: str
    text: str
    ready_to_copy: bool
    missing: tuple[str, ...]
    invalid: tuple[str, ...]
    unknown: tuple[str, ...]
    variables: tuple[VariableSpec, ...]


def preview(prompt: PromptRecord, values: Mapping[str, object], now: datetime | None = None) -> Preview:
    """Substitution result for whatever is filled so far; unfilled / invalid variables stay as `{{name}}` and the
    preview is not ready to copy until every check passes."""
    norm, missing, invalid, unknown = check_values(prompt, values, now)
    bad = {s.split(":", 1)[0] for s in invalid}
    text = _PLACEHOLDER.sub(lambda m: norm[m.group(1)] if m.group(1) in norm and m.group(1) not in bad
                            else m.group(0), prompt.body)
    return Preview(prompt.prompt_id, prompt.prompt_code, prompt.title, prompt.content_version, text,
                   not (missing or invalid or unknown), tuple(missing), tuple(invalid), tuple(unknown),
                   variable_specs(prompt))


def copy_text(prompt: PromptRecord, values: Mapping[str, object], now: datetime | None = None) -> str:
    """What the Copy button puts on the clipboard: exactly the filled canonical body, nothing vendor-specific."""
    return fill(prompt, values, now)


def export(catalog: Catalog, prompt_ids, values: Mapping[str, object], fmt: str = "text",
           now: datetime | None = None) -> str:
    """Fill several prompts (e.g. a Bundle, in its order) with one shared value set.

    Each prompt receives only the variables it declares; a variable required by any prompt must be supplied.
    fmt="text": prompts separated by a plain divider line; fmt="json": list of {prompt_id, prompt_code,
    content_version, catalog_sha256, as_of, text}. Fail-closed on the first prompt that cannot be filled."""
    if fmt not in ("text", "json"):
        raise ValueError(f"unknown export format {fmt!r}")
    ids = list(prompt_ids)
    all_vars = {v for pid in ids for v in catalog.prompts[pid].variables}
    unknown = sorted(k for k in values if k not in all_vars)
    if unknown:
        raise VariableFillError("EXPORT", unknown=unknown)
    items = []
    for pid in ids:
        p = catalog.prompts[pid]
        own = {k: v for k, v in values.items() if k in p.variables}
        items.append({"prompt_id": p.prompt_id, "prompt_code": p.prompt_code, "content_version": p.content_version,
                      "catalog_sha256": catalog.sha256, "as_of": str(values.get("as_of", "")).strip(),
                      "text": fill(p, own, now)})
    if fmt == "json":
        return json.dumps(items, ensure_ascii=False, indent=1)
    n = len(items)
    return "\n\n".join(f"----- [{i}/{n}] {it['prompt_code']} -----\n{it['text']}" for i, it in enumerate(items, 1))


def bundle_variables(catalog: Catalog, bundle_number: int) -> tuple[VariableSpec, ...]:
    """Union of the variables a Bundle needs, first-appearance order, required if any member requires it."""
    b = next(b for b in catalog.bundles if b.number == bundle_number)
    seen: dict[str, VariableSpec] = {}
    for pid in b.prompt_ids:
        for s in variable_specs(catalog.prompts[pid]):
            if s.name not in seen or (s.required and not seen[s.name].required):
                seen[s.name] = s
    return tuple(seen.values())
