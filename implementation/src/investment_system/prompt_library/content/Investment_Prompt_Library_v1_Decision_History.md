# Investment Prompt Library v1 · Decision History

Status: **CONTENT FROZEN / MIGRATION RECORD / PHYSICAL HISTORY PRESERVED**

Decision time: 2026-09-27 KST

- Source draft SHA-256: `35bd2f4fa9940a084dd6af56dfa469518a1c3b77b6e0165a7c7f2cc74f92ab78`
- Audit SHA-256: `14180ff253902bdee3aed3f97f63d621a59e0eeb14d8484c83521ca6234ff89a`
- Approved direction: target baseline near 70; meaning and unique Research Value outrank quota.
- Result: 70 Active / 38 MERGED_INTO / 6 RETIRED_SYSTEM_OVERLAP.
- No legacy prompt text was physically deleted; the original 114-prompt source remains the historical record.

## Catalog Freeze decision

- Decision time: `2026-09-27 12:36:40 KST`
- Authority: `D2 — CONSERVATIVE AUTONOMOUS`
- Trigger: 사용자가 Freeze Candidate 결과와 검증 보고 후 `계속 진행해`를 지시했다.
- Decision: `PLV1_CONTENT_FC1`의 Canonical 본문·metadata·migration을 변경하지 않고 상태만 `PLV1_CONTENT_V1.0 / CONTENT FROZEN`으로 승격했다.
- Evidence: Content regression `33/33 PASS`; repository baseline `297/297 PASS`; Active 70 + MERGED_INTO 38 + RETIRED_SYSTEM_OVERLAP 6 = source 114.
- Alternatives considered: (1) Candidate 상태 유지, (2) Schema/UI/runtime로 즉시 이동. 검증 완료 상태를 명확히 고정하면서 구현 범위를 확대하지 않는 Freeze 승격을 선택했다.
- Impact scope: Content artifact와 Decision History만 변경. Prompt 수·본문·stable ID·prompt_code·alias·Starter·Bundle·Track A/B/C·RIG·실행 동작에는 영향 없음.
- Rollback: Freeze artifact 대신 보존된 `PLV1_CONTENT_FC1` Candidate를 다시 기준으로 사용한다. 원본 114개 Draft와 migration history는 그대로 남아 있다.
- D3 review: PIT/no-lookahead, Official/Gate, 추정 정책, Track ownership/Frozen Contract, 데이터 손실/history rewrite, 비용, 보안·권한 변경 없음.
- Frozen catalog SHA-256: `f0a6ed9005e22b8fa534d51135cc3e734aa9577150438a35d65823a4c283e68e`

## Merge migration

| source prompt_id | legacy code | status | target prompt_id | purpose preservation |
|---|---|---|---|---|
| `plv1.idea.015` | `IDEA-015` | `MERGED_INTO` | `plv1.idea.014` | `Relative Strength가 개선되는 후보 찾기` is preserved as target alias/focus mode |
| `plv1.idea.016` | `IDEA-016` | `MERGED_INTO` | `plv1.idea.014` | `Base/Breakout 준비 후보 찾기` is preserved as target alias/focus mode |
| `plv1.idea.017` | `IDEA-017` | `MERGED_INTO` | `plv1.idea.018` | `Macro 변화의 직접 수혜기업 찾기` is preserved as target alias/focus mode |
| `plv1.fund.018` | `FUND-018` | `MERGED_INTO` | `plv1.fund.011` | `경쟁우위가 과대평가됐을 가능성` is preserved as target alias/focus mode |
| `plv1.fund.019` | `FUND-019` | `MERGED_INTO` | `plv1.fund.014` | `성장률이 지속되지 못할 이유` is preserved as target alias/focus mode |
| `plv1.fund.020` | `FUND-020` | `MERGED_INTO` | `plv1.fund.008` | `Margin 정상화 위험` is preserved as target alias/focus mode |
| `plv1.fund.021` | `FUND-021` | `MERGED_INTO` | `plv1.fund.015` | `Valuation을 정당화하지 못할 Scenario` is preserved as target alias/focus mode |
| `plv1.fund.024` | `FUND-024` | `MERGED_INTO` | `plv1.fund.023` | `제품에 대한 실제 시장 반응 조사` is preserved as target alias/focus mode |
| `plv1.fund.025` | `FUND-025` | `MERGED_INTO` | `plv1.fund.023` | `가격 인상에 대한 고객 반응` is preserved as target alias/focus mode |
| `plv1.fund.027` | `FUND-027` | `MERGED_INTO` | `plv1.fund.011` | `신규 경쟁자·대체기술 등장 조사` is preserved as target alias/focus mode |
| `plv1.tech.002` | `TECH-002` | `MERGED_INTO` | `plv1.tech.001` | `현재 주가 위치 파악하기` is preserved as target alias/focus mode |
| `plv1.tech.003` | `TECH-003` | `MERGED_INTO` | `plv1.tech.001` | `추세가 살아있는지 확인하기` is preserved as target alias/focus mode |
| `plv1.tech.004` | `TECH-004` | `MERGED_INTO` | `plv1.tech.001` | `Momentum 상태 점검하기` is preserved as target alias/focus mode |
| `plv1.tech.005` | `TECH-005` | `MERGED_INTO` | `plv1.tech.001` | `지지·저항 구간 찾기` is preserved as target alias/focus mode |
| `plv1.tech.008` | `TECH-008` | `MERGED_INTO` | `plv1.tech.007` | `Pullback의 질 분석` is preserved as target alias/focus mode |
| `plv1.tech.014` | `TECH-014` | `MERGED_INTO` | `plv1.tech.007` | `False Breakout 가능성 검증` is preserved as target alias/focus mode |
| `plv1.tech.015` | `TECH-015` | `MERGED_INTO` | `plv1.tech.013` | `Momentum 신호가 잘못됐을 가능성` is preserved as target alias/focus mode |
| `plv1.tech.016` | `TECH-016` | `MERGED_INTO` | `plv1.tech.017` | `주요 Support가 실패할 가능성` is preserved as target alias/focus mode |
| `plv1.tech.018` | `TECH-018` | `MERGED_INTO` | `plv1.tech.012` | `반전 신호가 False Signal일 가능성` is preserved as target alias/focus mode |
| `plv1.tech.024` | `TECH-024` | `MERGED_INTO` | `plv1.cross.001` | `가격이 Fundamental 변화를 선반영하는지 조사` is preserved as target alias/focus mode |
| `plv1.macro.002` | `MACRO-002` | `MERGED_INTO` | `plv1.macro.001` | `Growth 상태 이해하기` is preserved as target alias/focus mode |
| `plv1.macro.003` | `MACRO-003` | `MERGED_INTO` | `plv1.macro.001` | `Inflation 상태 이해하기` is preserved as target alias/focus mode |
| `plv1.macro.004` | `MACRO-004` | `MERGED_INTO` | `plv1.macro.001` | `금리환경 이해하기` is preserved as target alias/focus mode |
| `plv1.macro.005` | `MACRO-005` | `MERGED_INTO` | `plv1.macro.001` | `Liquidity 상태 이해하기` is preserved as target alias/focus mode |
| `plv1.macro.006` | `MACRO-006` | `MERGED_INTO` | `plv1.macro.001` | `현재 시장 Risk 이해하기` is preserved as target alias/focus mode |
| `plv1.macro.014` | `MACRO-014` | `MERGED_INTO` | `plv1.macro.013` | `Soft Landing Scenario 반박` is preserved as target alias/focus mode |
| `plv1.macro.015` | `MACRO-015` | `MERGED_INTO` | `plv1.macro.013` | `Recession Scenario 반박` is preserved as target alias/focus mode |
| `plv1.macro.017` | `MACRO-017` | `MERGED_INTO` | `plv1.macro.009` | `시장 금리기대가 틀릴 가능성 검증` is preserved as target alias/focus mode |
| `plv1.macro.019` | `MACRO-019` | `MERGED_INTO` | `plv1.macro.018` | `기업 현장의 가격·수요 변화 조사` is preserved as target alias/focus mode |
| `plv1.cross.002` | `CROSS-002` | `MERGED_INTO` | `plv1.cross.001` | `기업은 약한데 주가가 강한 이유` is preserved as target alias/focus mode |
| `plv1.cross.003` | `CROSS-003` | `MERGED_INTO` | `plv1.cross.001` | `가격이 Fundamental 변화를 선반영하는지 검증` is preserved as target alias/focus mode |
| `plv1.cross.005` | `CROSS-005` | `MERGED_INTO` | `plv1.cross.004` | `Macro 수혜환경인데 기업이 약한 이유` is preserved as target alias/focus mode |
| `plv1.cross.006` | `CROSS-006` | `MERGED_INTO` | `plv1.cross.004` | `Macro 변화가 실제 Earnings로 전달되는지 검증` is preserved as target alias/focus mode |
| `plv1.cross.008` | `CROSS-008` | `MERGED_INTO` | `plv1.cross.007` | `가격은 강한데 Macro가 악화되는 이유` is preserved as target alias/focus mode |
| `plv1.cross.009` | `CROSS-009` | `MERGED_INTO` | `plv1.cross.007` | `시장이 Macro 전환을 선반영하는지 검증` is preserved as target alias/focus mode |
| `plv1.cross.011` | `CROSS-011` | `MERGED_INTO` | `plv1.cross.010` | `세 분석이 모두 부정일 때 과도한 비관 여부` is preserved as target alias/focus mode |
| `plv1.cross.017` | `CROSS-017` | `MERGED_INTO` | `plv1.cross.013` | `현재 Investment Thesis Red Team` is preserved as target alias/focus mode |
| `plv1.cross.018` | `CROSS-018` | `MERGED_INTO` | `plv1.cross.014` | `지금 가장 먼저 추가 조사해야 할 질문 찾기` is preserved as target alias/focus mode |

## Retired migration

| prompt_id | legacy code | status | reason | replacement path |
|---|---|---|---|---|
| `plv1.fund.001` | `FUND-001` | `RETIRED_SYSTEM_OVERLAP` | QGV Analysis 전체 분석과 중복 | `QGV_ANALYSIS → 목적별 FUND/CROSS Prompt` |
| `plv1.fund.005` | `FUND-005` | `RETIRED_SYSTEM_OVERLAP` | QGV Analysis Valuation/Reverse DCF와 중복 | `QGV_ANALYSIS.valuation → plv1.fund.015` |
| `plv1.idea.001` | `IDEA-001` | `RETIRED_SYSTEM_OVERLAP` | QGV Leaderboard의 통합 Q/G/V 탐색과 중복 | `QGV_LEADERBOARD → 필요 시 plv1.idea.020` |
| `plv1.idea.002` | `IDEA-002` | `RETIRED_SYSTEM_OVERLAP` | QGV Leaderboard Quality 필터와 중복 | `QGV_LEADERBOARD.quality_filter` |
| `plv1.idea.003` | `IDEA-003` | `RETIRED_SYSTEM_OVERLAP` | QGV Leaderboard Growth 필터와 중복 | `QGV_LEADERBOARD.growth_filter` |
| `plv1.idea.004` | `IDEA-004` | `RETIRED_SYSTEM_OVERLAP` | QGV Leaderboard Quality/Valuation 조합과 중복 | `QGV_LEADERBOARD.quality_valuation_filter` |

## Active ID continuity

All 70 retained prompt IDs keep the source draft's domain/number identity. Human-readable codes advance to `.v1.0`; stable IDs do not change.

- `plv1.idea.005` → `IDEA-005.v1.0`
- `plv1.idea.006` → `IDEA-006.v1.0`
- `plv1.idea.007` → `IDEA-007.v1.0`
- `plv1.idea.008` → `IDEA-008.v1.0`
- `plv1.idea.009` → `IDEA-009.v1.0`
- `plv1.idea.010` → `IDEA-010.v1.0`
- `plv1.idea.011` → `IDEA-011.v1.0`
- `plv1.idea.012` → `IDEA-012.v1.0`
- `plv1.idea.013` → `IDEA-013.v1.0`
- `plv1.idea.014` → `IDEA-014.v1.0`
- `plv1.idea.018` → `IDEA-018.v1.0`
- `plv1.idea.019` → `IDEA-019.v1.0`
- `plv1.idea.020` → `IDEA-020.v1.0`
- `plv1.fund.002` → `FUND-002.v1.0`
- `plv1.fund.003` → `FUND-003.v1.0`
- `plv1.fund.004` → `FUND-004.v1.0`
- `plv1.fund.006` → `FUND-006.v1.0`
- `plv1.fund.007` → `FUND-007.v1.0`
- `plv1.fund.008` → `FUND-008.v1.0`
- `plv1.fund.009` → `FUND-009.v1.0`
- `plv1.fund.010` → `FUND-010.v1.0`
- `plv1.fund.011` → `FUND-011.v1.0`
- `plv1.fund.012` → `FUND-012.v1.0`
- `plv1.fund.013` → `FUND-013.v1.0`
- `plv1.fund.014` → `FUND-014.v1.0`
- `plv1.fund.015` → `FUND-015.v1.0`
- `plv1.fund.016` → `FUND-016.v1.0`
- `plv1.fund.017` → `FUND-017.v1.0`
- `plv1.fund.022` → `FUND-022.v1.0`
- `plv1.fund.023` → `FUND-023.v1.0`
- `plv1.fund.026` → `FUND-026.v1.0`
- `plv1.fund.028` → `FUND-028.v1.0`
- `plv1.fund.029` → `FUND-029.v1.0`
- `plv1.fund.030` → `FUND-030.v1.0`
- `plv1.tech.001` → `TECH-001.v1.0`
- `plv1.tech.006` → `TECH-006.v1.0`
- `plv1.tech.007` → `TECH-007.v1.0`
- `plv1.tech.009` → `TECH-009.v1.0`
- `plv1.tech.010` → `TECH-010.v1.0`
- `plv1.tech.011` → `TECH-011.v1.0`
- `plv1.tech.012` → `TECH-012.v1.0`
- `plv1.tech.013` → `TECH-013.v1.0`
- `plv1.tech.017` → `TECH-017.v1.0`
- `plv1.tech.019` → `TECH-019.v1.0`
- `plv1.tech.020` → `TECH-020.v1.0`
- `plv1.tech.021` → `TECH-021.v1.0`
- `plv1.tech.022` → `TECH-022.v1.0`
- `plv1.tech.023` → `TECH-023.v1.0`
- `plv1.macro.001` → `MACRO-001.v1.0`
- `plv1.macro.007` → `MACRO-007.v1.0`
- `plv1.macro.008` → `MACRO-008.v1.0`
- `plv1.macro.009` → `MACRO-009.v1.0`
- `plv1.macro.010` → `MACRO-010.v1.0`
- `plv1.macro.011` → `MACRO-011.v1.0`
- `plv1.macro.012` → `MACRO-012.v1.0`
- `plv1.macro.013` → `MACRO-013.v1.0`
- `plv1.macro.016` → `MACRO-016.v1.0`
- `plv1.macro.018` → `MACRO-018.v1.0`
- `plv1.macro.020` → `MACRO-020.v1.0`
- `plv1.macro.021` → `MACRO-021.v1.0`
- `plv1.macro.022` → `MACRO-022.v1.0`
- `plv1.cross.001` → `CROSS-001.v1.0`
- `plv1.cross.004` → `CROSS-004.v1.0`
- `plv1.cross.007` → `CROSS-007.v1.0`
- `plv1.cross.010` → `CROSS-010.v1.0`
- `plv1.cross.012` → `CROSS-012.v1.0`
- `plv1.cross.013` → `CROSS-013.v1.0`
- `plv1.cross.014` → `CROSS-014.v1.0`
- `plv1.cross.015` → `CROSS-015.v1.0`
- `plv1.cross.016` → `CROSS-016.v1.0`
