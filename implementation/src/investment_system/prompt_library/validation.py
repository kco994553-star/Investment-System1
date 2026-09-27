"""E2 — fail-closed validation of the Frozen catalog (Track E).

Re-checks, at every load, the structural invariants the Content Regression Report (33/33 PASS) established for
PLV1_CONTENT_V1.0. These checks never edit content: any violation makes the catalog unusable.
"""
from __future__ import annotations

from collections import Counter

from .catalog import DOMAINS, INPUT_MODES, MIGRATION_STATUSES, ROLES, Catalog, variables_in

EXPECTED_ACTIVE = 70
EXPECTED_SOURCE = 114
EXPECTED_MERGED = 38
EXPECTED_MERGE_GROUPS = 22
EXPECTED_RETIRED = 6
EXPECTED_DOMAINS = {"DISCOVERY": 13, "FUNDAMENTAL": 21, "TECHNICAL": 14, "MACRO": 13, "CROSS_VALIDATION": 9}
EXPECTED_STARTERS = 6
# Body contract lines every Frozen prompt carries (Evidence / no-recompute / PIT rules)
BODY_RULES = (
    "정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.",
    "확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.",
    "기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.",
    "BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.",
)
DISCOVERY_RULE = "결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다."


def validate_prompt(p) -> list[str]:
    out = []
    code = p.prompt_code
    if not (p.prompt_id.startswith("plv1.") and p.prompt_code.endswith(".v1.0")):
        out.append(f"{code}: identifier format")
    if p.status != "ACTIVE":
        out.append(f"{code}: status {p.status} is not ACTIVE")
    if p.domain not in DOMAINS:
        out.append(f"{code}: unknown domain {p.domain}")
    if p.role not in ROLES:
        out.append(f"{code}: unknown role {p.role}")
    if "as_of" not in p.variables:
        out.append(f"{code}: as_of not declared")
    body_vars = set(variables_in(p.body))
    declared = set(p.variables)
    if body_vars - declared:
        out.append(f"{code}: body variables not declared {sorted(body_vars - declared)}")
    if declared - body_vars:
        out.append(f"{code}: declared variables unused in body {sorted(declared - body_vars)}")
    if len(p.variables) != len(declared):
        out.append(f"{code}: duplicate declared variables")
    for rule in BODY_RULES:
        if rule not in p.body:
            out.append(f"{code}: body contract line missing: {rule[:30]}...")
    # TECH / MACRO: explicit input mode with both modes defined in the body (SYSTEM_CONTEXT never recomputes;
    # STANDALONE ends INSUFFICIENT_DATA without PIT input); no other domain declares input_mode
    if p.domain in ("TECHNICAL", "MACRO"):
        if not p.requires_input_mode:
            out.append(f"{code}: TECH/MACRO prompt without input_mode")
        for mode in INPUT_MODES:
            if mode not in p.body:
                out.append(f"{code}: input mode {mode} not defined in body")
        if "`INSUFFICIENT_DATA`로 종료해" not in p.body:
            out.append(f"{code}: STANDALONE fail-closed (INSUFFICIENT_DATA) missing")
    elif p.requires_input_mode:
        out.append(f"{code}: input_mode declared outside TECH/MACRO")
    if p.domain == "DISCOVERY" and DISCOVERY_RULE not in p.body:
        out.append(f"{code}: Discovery Research Candidate boundary missing")
    return out


def validate_catalog(cat: Catalog, declared_active: int | None = None) -> list[str]:
    out = []
    prompts = list(cat.prompts.values())
    if cat.content_version != "PLV1_CONTENT_V1.0":
        out.append(f"content_version {cat.content_version}")
    if "CONTENT FROZEN" not in cat.status_line:
        out.append(f"catalog status is not CONTENT FROZEN: {cat.status_line}")
    if len(prompts) != EXPECTED_ACTIVE or (declared_active is not None and declared_active != len(prompts)):
        out.append(f"active count {len(prompts)} (declared {declared_active}, expected {EXPECTED_ACTIVE})")
    codes = [p.prompt_code for p in prompts]
    if len(set(codes)) != len(codes):
        out.append("prompt_code not unique")
    if len({p.body for p in prompts}) != len(prompts):
        out.append("exact duplicate prompt bodies")
    dom = Counter(p.domain for p in prompts)
    if dict(dom) != EXPECTED_DOMAINS:
        out.append(f"domain distribution {dict(dom)} != {EXPECTED_DOMAINS}")
    for p in prompts:
        out.extend(validate_prompt(p))

    migs = list(cat.migrations.values())
    status = Counter(m.status for m in migs)
    if any(s not in MIGRATION_STATUSES for s in status):
        out.append(f"unknown migration status {sorted(status)}")
    if status.get("MERGED_INTO", 0) != EXPECTED_MERGED or status.get("RETIRED_SYSTEM_OVERLAP", 0) != EXPECTED_RETIRED:
        out.append(f"migration counts {dict(status)}")
    if len({m.target_prompt_id for m in migs if m.status == "MERGED_INTO"}) != EXPECTED_MERGE_GROUPS:
        out.append("merge group count")
    overlap = set(cat.migrations) & set(cat.prompts)
    if overlap:
        out.append(f"migrated IDs still active {sorted(overlap)}")
    if len(cat.prompts) + len(cat.migrations) != EXPECTED_SOURCE:
        out.append(f"active + migrated = {len(cat.prompts) + len(cat.migrations)} != {EXPECTED_SOURCE}")
    for m in migs:
        if m.status == "MERGED_INTO":
            if m.target_prompt_id not in cat.prompts:
                out.append(f"{m.prompt_id}: merge target {m.target_prompt_id} not active")
            elif m.prompt_id not in cat.prompts[m.target_prompt_id].aliases:
                # merge traceability: the source stable ID survives as an alias of its target
                out.append(f"{m.prompt_id}: not preserved as alias of {m.target_prompt_id}")
        elif not m.replacement_path:
            out.append(f"{m.prompt_id}: retired without replacement path")

    if len(cat.starters) != EXPECTED_STARTERS or len(set(cat.starters)) != len(cat.starters):
        out.append(f"starters {cat.starters}")
    for s in cat.starters:
        if s not in cat.prompts:
            out.append(f"starter {s} not active")
    if not cat.bundles:
        out.append("no bundles")
    for b in cat.bundles:
        if not b.prompt_ids:
            out.append(f"bundle {b.number} empty")
        for pid in b.prompt_ids:
            if pid not in cat.prompts:
                out.append(f"bundle {b.number} references non-active {pid}")
    return out
