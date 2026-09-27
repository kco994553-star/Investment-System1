# Investment Prompt Library v1 · Content Regression Report

검증 시각: 2026-09-27 12:15:15 KST

결과: **PASS — 33/33 checks**

## Catalog summary

- Source: 114 canonical prompts
- Active: 70
- MERGED_INTO: 38 across 22 target groups
- RETIRED_SYSTEM_OVERLAP: 6
- Domain: {'DISCOVERY': 13, 'FUNDAMENTAL': 21, 'TECHNICAL': 14, 'MACRO': 13, 'CROSS_VALIDATION': 9}
- Role: {'BASIC': 8, 'EXPAND': 34, 'CHALLENGE': 10, 'BLIND-SPOT': 18}
- System overlap: {'LOW_TO_MEDIUM': 13, 'HIGH_CONTROLLED': 57}

## Checks

| check | result | evidence |
|---|---|---|
| 원본 Canonical 수 | PASS | actual=114, expected=114 |
| Active Canonical 수 | PASS | actual=70, expected=70 |
| Stable prompt_id 유일성 | PASS | unique=70 |
| Versioned prompt_code 유일성 | PASS | unique=70 |
| 114개 migration 완전분할 | PASS | active=70, merge=38, retire=6 |
| Merge 수 | PASS | actual=38, expected=38 |
| Merge 그룹 수 | PASS | actual=22, expected=22 |
| Merge target Active | PASS | invalid=[] |
| Retire 수 | PASS | actual=6, expected=6 |
| Retire 상태/대체경로 기록 | PASS | Decision History 6 rows checked |
| Domain 분포 | PASS | {'DISCOVERY': 13, 'FUNDAMENTAL': 21, 'TECHNICAL': 14, 'MACRO': 13, 'CROSS_VALIDATION': 9} |
| 모든 Prompt에 as_of 선언·사용 | PASS | 70/70 required |
| 미사용 선언 변수 없음 | PASS | none |
| 미선언 본문 변수 없음 | PASS | none |
| TECH/MACRO Input Mode | PASS | 27/27 required |
| SYSTEM_CONTEXT 재계산 금지 | PASS | 57/57 required |
| Discovery Research Candidate 경계 | PASS | 13/13 required |
| Evidence/불확실성 규칙 | PASS | 70/70 required |
| 정형분석 반복 금지 | PASS | 70/70 required |
| Exact 본문 중복 없음 | PASS | duplicates=0 |
| Purpose 중복 없음 | PASS | unique=70 |
| 의미중복 heuristic review | PASS | max=0.686 pair=CROSS-004/CROSS-007; pair retained because Fundamental↔Macro vs Technical↔Macro inputs/evidence/outputs differ |
| System overlap 경계 | PASS | {'LOW_TO_MEDIUM': 13, 'HIGH_CONTROLLED': 57} |
| Merge alias 추적성 | PASS | 38/38 source code + stable ID |
| Starter 6 | PASS | ids=['plv1.idea.020', 'plv1.fund.030', 'plv1.tech.001', 'plv1.macro.001', 'plv1.cross.014', 'plv1.cross.013'] |
| Bundle/Starter 참조 Active | PASS | invalid=[] |
| Bundle 본문 비복제 | PASS | ID-only contract present |
| Macro 실제 8축 ownership | PASS | 8 axes present; Rates/Risk summary-only statement present |
| 요구 흡수: 회계/희석/Footnote | PASS | FUND-030 |
| 요구 흡수: Source/citation integrity | PASS | CROSS-013 |
| 요구 흡수: Delta-only | PASS | CROSS-015 |
| 요구 흡수: Horizon mismatch | PASS | CROSS-012 |
| 요구 흡수: Technical data/corporate action | PASS | TECH-001 |

## Scope guard

- 이 검증은 Content Catalog, migration, Starter/Bundle만 대상으로 한다.
- Schema/UI/runtime 구현은 시작하지 않았다.
- Investment-System1 저장소 파일은 변경하지 않았다.

## Repository guard (independent re-run)

- HEAD: `329859898e7c8d3be38d7c540a17889f556aa73c`
- origin: `706a6c2255b1777511d908dbae807e24e45b554e`
- history: ahead 29 / behind 0; rewrite/squash/reset 없음
- working tree: clean; repository diff 없음
- baseline: **297 passed / 0 failed** in 74.32s (`mini_pytest shim`, not pytest)

## Freeze verification

- Freeze time: `2026-09-27 12:36:40 KST`
- Frozen version: `PLV1_CONTENT_V1.0`
- Frozen catalog SHA-256: `f0a6ed9005e22b8fa534d51135cc3e734aa9577150438a35d65823a4c283e68e`
- Candidate→Frozen 변경범위: catalog status/version/freeze time 및 70개 prompt status의 `ACTIVE_FREEZE_CANDIDATE`→`ACTIVE` 승격만 허용
- Canonical title·metadata·variables·body: Candidate와 동일
- Schema/UI/runtime: 미착수 유지
