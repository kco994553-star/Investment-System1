# Investment Prompt Library v1 · Content Catalog

Status: **CONTENT FROZEN / CONTENT ONLY / NO SCHEMA-UI-RUNTIME**

Catalog version: `PLV1_CONTENT_V1.0`

Freeze time: `2026-09-27 12:36:40 KST`

Active canonical prompts: **70**

## Product boundary

- Investment System의 최상위 분석축은 Fundamental(QGV) / Technical / Macro다.
- Discovery는 세 분석축 전의 Research Candidate 생성 단계이며 BUY 추천이 아니다.
- Cross Validation은 세 분석 결과의 충돌·누락·새 Evidence를 찾는 후단이며 새 분석엔진이 아니다.
- 사용 방식은 Copy-first다. Investment System은 Prompt 검색·복사 과정에서 LLM Token을 소비하지 않는다.
- Prompt Library는 기존 QGV/Technical/Macro/Leaderboard의 정형 계산을 외부 AI에게 그대로 반복시키지 않는다.
- SYSTEM_CONTEXT는 기존 Snapshot을 재계산하지 않고 Delta/Divergence/Catalyst/Blind Spot을 조사한다.
- TECH/MACRO STANDALONE은 PIT 입력이 없으면 `INSUFFICIENT_DATA`로 fail-closed한다.
- `{{as_of}}`는 모든 Prompt의 PIT/정보 cutoff다.
- Macro의 Rates/Risk 5축 표시는 Summary View일 뿐이며 실제 소유축은 Growth / Inflation / Liquidity / Monetary Policy / Credit / Labor / Fiscal / FX다.

## Identifier rule

- `prompt_id`: `plv1.<domain>.<nnn>` 형태의 stable internal ID. Merge/rename 후에도 재사용하거나 변경하지 않는다.
- `prompt_code`: 사람이 읽는 versioned code `<LEGACY_CODE>.v1.0`.
- Merge source ID는 Decision History에서 `MERGED_INTO`로 보존하고 target의 alias로 남긴다.
- Retired ID는 삭제하지 않고 `RETIRED_SYSTEM_OVERLAP`과 replacement path를 기록한다.

## Starter 6

1. `plv1.idea.020`
2. `plv1.fund.030`
3. `plv1.tech.001`
4. `plv1.macro.001`
5. `plv1.cross.014`
6. `plv1.cross.013`

## Bundle reference

Bundle은 Canonical 본문을 복제하지 않고 stable prompt_id만 참조한다.

1. **기업 외부 Evidence 확장** — `plv1.fund.002` → `plv1.fund.003` → `plv1.fund.011` → `plv1.fund.017`
2. **신규 투자 종합 검토** — `plv1.idea.020` → `plv1.fund.030` → `plv1.tech.001` → `plv1.macro.001` → `plv1.cross.014`
3. **실적 발표 Delta 분석** — `plv1.fund.004` → `plv1.fund.007` → `plv1.fund.008` → `plv1.tech.019` → `plv1.cross.015`
4. **Technical 검증** — `plv1.tech.001` → `plv1.tech.007` → `plv1.tech.017` → `plv1.tech.022`
5. **Macro 환경 검증** — `plv1.macro.001` → `plv1.macro.007` → `plv1.macro.009` → `plv1.macro.013` → `plv1.macro.018`
6. **투자 Thesis Red Team** — `plv1.fund.017` → `plv1.fund.022` → `plv1.cross.013`
7. **보유 종목 재점검** — `plv1.fund.004` → `plv1.fund.013` → `plv1.tech.001` → `plv1.macro.012` → `plv1.cross.015`
8. **숨겨진 위험 찾기** — `plv1.fund.030` → `plv1.tech.019` → `plv1.macro.022` → `plv1.cross.014`
9. **새로운 종목 발굴** — `plv1.idea.009` → `plv1.idea.010` → `plv1.idea.020` → `plv1.fund.030`
10. **시스템 Red Team** — `plv1.cross.012` → `plv1.cross.013` → `plv1.cross.014` → `plv1.cross.015` → `plv1.cross.016`

## Active canonical prompts

### IDEA-005.v1.0 — 실적 개선이 시작되는 Research Candidate 찾기

- prompt_id: `plv1.idea.005`
- prompt_code: `IDEA-005.v1.0`
- status: `ACTIVE`
- purpose: 최근 실적의 절대 수준보다 매출·수주·Backlog·Guidance·Estimate Revision의 방향 전환과 일회성 요인을 분리해 초기 개선 신호를 찾는다.
- domain: `DISCOVERY`
- role: `BASIC`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `FUNDAMENTAL_INFLECTION`
- tags: `discovery`, `basic`, `fundamental_inflection`
- keywords: `실적`, `개선이`, `시작되는`, `Research`, `Candidate`, `찾기`
- aliases: `실적이 좋아지기 시작하는 기업 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: 실적 개선이 시작되는 Research Candidate 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: 최근 실적의 절대 수준보다 매출·수주·Backlog·Guidance·Estimate Revision의 방향 전환과 일회성 요인을 분리해 초기 개선 신호를 찾는다.

출력:
1. 후보와 초기 변곡점
2. 선행·후행 Evidence
3. 개선 지속 조건
4. 반대 Evidence/Value Trap
5. 다음 QGV 분석 항목

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-006.v1.0 — Margin 개선 Research Candidate 찾기

- prompt_id: `plv1.idea.006`
- prompt_code: `IDEA-006.v1.0`
- status: `ACTIVE`
- purpose: 가격·Mix·원가·가동률·공급망·회계 분류를 분해하고 구조적 Margin 개선과 일시적 정상화를 구분한다.
- domain: `DISCOVERY`
- role: `EXPAND`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `FUNDAMENTAL_INFLECTION`
- tags: `discovery`, `expand`, `fundamental_inflection`
- keywords: `Margin`, `개선`, `Research`, `Candidate`, `찾기`
- aliases: `Margin이 개선되는 기업 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: Margin 개선 Research Candidate 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: 가격·Mix·원가·가동률·공급망·회계 분류를 분해하고 구조적 Margin 개선과 일시적 정상화를 구분한다.

출력:
1. 후보와 Margin 종류
2. 개선 원인 분해
3. 지속 가능 기간
4. 정상화/역전 위험
5. 추가 확인 자료

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-007.v1.0 — FCF 개선 Research Candidate 찾기

- prompt_id: `plv1.idea.007`
- prompt_code: `IDEA-007.v1.0`
- status: `ACTIVE`
- purpose: 영업현금흐름, 운전자본, CAPEX, 세금, SBC와 일회성 현금흐름을 분리해 현금전환의 질이 좋아지는 후보를 찾는다.
- domain: `DISCOVERY`
- role: `EXPAND`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `FUNDAMENTAL_INFLECTION`
- tags: `discovery`, `expand`, `fundamental_inflection`
- keywords: `FCF`, `개선`, `Research`, `Candidate`, `찾기`
- aliases: `FCF가 좋아지는 기업 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: FCF 개선 Research Candidate 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: 영업현금흐름, 운전자본, CAPEX, 세금, SBC와 일회성 현금흐름을 분리해 현금전환의 질이 좋아지는 후보를 찾는다.

출력:
1. 후보와 FCF 변곡점
2. 현금전환 원인
3. 회계이익과 차이
4. 지속성/역전 조건
5. 추가 확인 자료

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-008.v1.0 — 시장점유율 상승 Research Candidate 찾기

- prompt_id: `plv1.idea.008`
- prompt_code: `IDEA-008.v1.0`
- status: `ACTIVE`
- purpose: 가격 인상에 따른 명목 성장과 실제 Unit/Customer Share 상승을 구분하고 경쟁사·채널·지역별 교차 Evidence로 점유율 개선을 검증한다.
- domain: `DISCOVERY`
- role: `EXPAND`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `FUNDAMENTAL_INFLECTION`
- tags: `discovery`, `expand`, `fundamental_inflection`
- keywords: `시장점유율`, `상승`, `Research`, `Candidate`, `찾기`
- aliases: `시장점유율이 올라가는 기업 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: 시장점유율 상승 Research Candidate 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: 가격 인상에 따른 명목 성장과 실제 Unit/Customer Share 상승을 구분하고 경쟁사·채널·지역별 교차 Evidence로 점유율 개선을 검증한다.

출력:
1. 후보와 세부시장
2. 점유율 방향/격차
3. Share Gain 원인
4. 경쟁사 반증
5. 추가 QGV 조사

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-009.v1.0 — 유망 산업의 핵심 Research Candidate 찾기

- prompt_id: `plv1.idea.009`
- prompt_code: `IDEA-009.v1.0`
- status: `ACTIVE`
- purpose: {{industry}}의 성장률 자체보다 Profit Pool, Bottleneck, Switching Cost, 표준 지배력과 공급 제약을 확인해 핵심 후보를 찾는다.
- domain: `DISCOVERY`
- role: `EXPAND`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `ECOSYSTEM`
- tags: `discovery`, `expand`, `ecosystem`
- keywords: `유망`, `산업의`, `핵심`, `Research`, `Candidate`, `찾기`
- aliases: `유망 산업에서 핵심기업 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`, `{{industry}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: 유망 산업의 핵심 Research Candidate 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: {{industry}}의 성장률 자체보다 Profit Pool, Bottleneck, Switching Cost, 표준 지배력과 공급 제약을 확인해 핵심 후보를 찾는다.

출력:
1. 산업 구조
2. 후보의 Value Capture 위치
3. 핵심 Evidence
4. 산업 과열/반대 Evidence
5. QGV 진입 우선순위

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-010.v1.0 — Value Chain 전 구간에서 후보 찾기

- prompt_id: `plv1.idea.010`
- prompt_code: `IDEA-010.v1.0`
- status: `ACTIVE`
- purpose: {{industry_or_theme}}의 Upstream→Downstream 단계를 그리고 직접 수혜·병목·Enabler·Aftermarket 후보를 빠짐없이 비교한다.
- domain: `DISCOVERY`
- role: `EXPAND`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `ECOSYSTEM`
- tags: `discovery`, `expand`, `ecosystem`
- keywords: `Value`, `Chain`, `전`, `구간에서`, `후보`, `찾기`
- aliases: `산업 Value Chain 전체에서 후보 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`, `{{industry_or_theme}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: Value Chain 전 구간에서 후보 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: {{industry_or_theme}}의 Upstream→Downstream 단계를 그리고 직접 수혜·병목·Enabler·Aftermarket 후보를 빠짐없이 비교한다.

출력:
1. Value Chain 단계
2. 단계별 후보
3. 가치/협상력 흐름
4. 중복·누락 구간
5. 추가 분석 후보

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-011.v1.0 — 테마의 2·3차 수혜 Research Candidate 찾기

- prompt_id: `plv1.idea.011`
- prompt_code: `IDEA-011.v1.0`
- status: `ACTIVE`
- purpose: {{theme}}에서 유명한 1차 수혜주를 반복하지 말고 필수 부품·인프라·서비스·대체 공급자까지 인과경로가 검증되는 후보를 찾는다.
- domain: `DISCOVERY`
- role: `EXPAND`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `ECOSYSTEM`
- tags: `discovery`, `expand`, `ecosystem`
- keywords: `테마의`, `2`, `3차`, `수혜`, `Research`, `Candidate`, `찾기`
- aliases: `테마의 2·3차 수혜기업 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`, `{{theme}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: 테마의 2·3차 수혜 Research Candidate 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: {{theme}}에서 유명한 1차 수혜주를 반복하지 말고 필수 부품·인프라·서비스·대체 공급자까지 인과경로가 검증되는 후보를 찾는다.

출력:
1. 테마 인과경로
2. 2·3차 후보
3. 필수성/수익화 Evidence
4. 테마 과장 위험
5. 후보 제외 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-012.v1.0 — 특정 기업의 경쟁 생태계에서 후보 찾기

- prompt_id: `plv1.idea.012`
- prompt_code: `IDEA-012.v1.0`
- status: `ACTIVE`
- purpose: {{seed_company}}({{seed_ticker}})의 직접 경쟁사·간접 대체재·지역 강자 중 시장이 과소평가할 수 있는 후보를 비교한다.
- domain: `DISCOVERY`
- role: `EXPAND`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `ECOSYSTEM`
- tags: `discovery`, `expand`, `ecosystem`
- keywords: `특정`, `기업의`, `경쟁`, `생태계에서`, `후보`, `찾기`
- aliases: `특정 기업의 경쟁사에서 후보 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`, `{{seed_company}}`, `{{seed_ticker}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: 특정 기업의 경쟁 생태계에서 후보 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: {{seed_company}}({{seed_ticker}})의 직접 경쟁사·간접 대체재·지역 강자 중 시장이 과소평가할 수 있는 후보를 비교한다.

출력:
1. 경쟁 지도
2. 후보별 차별점
3. 고객 전환 Evidence
4. Seed 기업 대비 위험
5. 후속 QGV 질문

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-013.v1.0 — 공급업체·고객사 관계에서 후보 찾기

- prompt_id: `plv1.idea.013`
- prompt_code: `IDEA-013.v1.0`
- status: `ACTIVE`
- purpose: {{seed_company}}({{seed_ticker}})의 실제 공급·고객 관계를 확인하고 매출 민감도, 대체 가능성, 협상력 변화가 있는 후보를 찾는다.
- domain: `DISCOVERY`
- role: `EXPAND`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `ECOSYSTEM`
- tags: `discovery`, `expand`, `ecosystem`
- keywords: `공급업체`, `고객사`, `관계에서`, `후보`, `찾기`
- aliases: `공급업체·고객사에서 후보 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`, `{{seed_company}}`, `{{seed_ticker}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: 공급업체·고객사 관계에서 후보 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: {{seed_company}}({{seed_ticker}})의 실제 공급·고객 관계를 확인하고 매출 민감도, 대체 가능성, 협상력 변화가 있는 후보를 찾는다.

출력:
1. 확인된 관계
2. 후보와 관계 유형
3. 경제적 중요도
4. 의존성/집중 위험
5. 추가 Relationship Evidence

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-014.v1.0 — Technical 변화 기반 Research Candidate 찾기

- prompt_id: `plv1.idea.014`
- prompt_code: `IDEA-014.v1.0`
- status: `ACTIVE`
- purpose: {{technical_screen_summary}}를 재계산하지 않고 Trend·Relative Strength·Base/Breakout 준비 상태가 동시에 개선되는 후보와 False Signal 조건을 찾는다.
- domain: `DISCOVERY`
- role: `EXPAND`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `TECHNICAL`
- tags: `discovery`, `expand`, `technical`
- keywords: `Technical`, `변화`, `기반`, `Research`, `Candidate`, `찾기`
- aliases: `기술적으로 추세가 좋아지는 기업 찾기`, `IDEA-015`, `plv1.idea.015`, `Relative Strength가 개선되는 후보 찾기`, `IDEA-016`, `plv1.idea.016`, `Base/Breakout 준비 후보 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`, `{{technical_screen_summary}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: Technical 변화 기반 Research Candidate 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: {{technical_screen_summary}}를 재계산하지 않고 Trend·Relative Strength·Base/Breakout 준비 상태가 동시에 개선되는 후보와 False Signal 조건을 찾는다.

출력:
1. 후보와 Technical 변화
2. 동시 확인 Evidence
3. Breakout/Pullback 상태
4. Invalidation
5. QGV/Macro 추가 확인

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-018.v1.0 — Macro 변화의 직접·2차 수혜 Candidate 찾기

- prompt_id: `plv1.idea.018`
- prompt_code: `IDEA-018.v1.0`
- status: `ACTIVE`
- purpose: {{macro_driver}}와 {{macro_snapshot_summary}}에서 기업 실적으로 이어지는 Transmission, Lag, Duration을 추적해 직접·2차 수혜를 구분한다.
- domain: `DISCOVERY`
- role: `EXPAND`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `MACRO`
- tags: `discovery`, `expand`, `macro`
- keywords: `Macro`, `변화의`, `직접`, `2차`, `수혜`, `Candidate`, `찾기`
- aliases: `Macro 변화의 2차 수혜기업 찾기`, `IDEA-017`, `plv1.idea.017`, `Macro 변화의 직접 수혜기업 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`, `{{macro_driver}}`, `{{macro_snapshot_summary}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: Macro 변화의 직접·2차 수혜 Candidate 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: {{macro_driver}}와 {{macro_snapshot_summary}}에서 기업 실적으로 이어지는 Transmission, Lag, Duration을 추적해 직접·2차 수혜를 구분한다.

출력:
1. Macro Driver
2. Transmission Path
3. 직접/2차 후보
4. Lag·Duration
5. 반대 Scenario/제외 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-019.v1.0 — 시장은 싫어하지만 사업이 개선되는 후보 찾기

- prompt_id: `plv1.idea.019`
- prompt_code: `IDEA-019.v1.0`
- status: `ACTIVE`
- purpose: {{system_summary}}에서 약한 시장평가와 개선되는 운영 Evidence가 동시에 존재하는지 확인하고 Turnaround와 Value Trap을 구분한다.
- domain: `DISCOVERY`
- role: `CHALLENGE`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `CONTRARIAN_BLIND_SPOT`
- tags: `discovery`, `challenge`, `contrarian_blind_spot`
- keywords: `시장은`, `싫어하지만`, `사업이`, `개선되는`, `후보`, `찾기`
- aliases: `시장이 싫어하지만 사업이 개선되는 기업 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`, `{{system_summary}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: 시장은 싫어하지만 사업이 개선되는 후보 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: {{system_summary}}에서 약한 시장평가와 개선되는 운영 Evidence가 동시에 존재하는지 확인하고 Turnaround와 Value Trap을 구분한다.

출력:
1. 후보와 부정적 시장판단
2. 사업 개선 Evidence
3. Catalyst/시간축
4. Value Trap Evidence
5. 후보 유지 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### IDEA-020.v1.0 — 시스템·Consensus가 놓친 후보 찾기

- prompt_id: `plv1.idea.020`
- prompt_code: `IDEA-020.v1.0`
- status: `ACTIVE`
- purpose: {{system_coverage_summary}}의 Coverage Gap, 작은 세부시장, 비정형 Evidence와 Consensus 부재를 이용하되 단순 저유동성·데이터 부족을 강점으로 오인하지 않는다.
- domain: `DISCOVERY`
- role: `BLIND-SPOT`
- category: `RESEARCH_CANDIDATE_DISCOVERY`
- subcategory: `CONTRARIAN_BLIND_SPOT`
- tags: `discovery`, `blind-spot`, `contrarian_blind_spot`
- keywords: `시스템`, `Consensus가`, `놓친`, `후보`, `찾기`
- aliases: `시스템/Consensus가 아직 잘 보지 않는 후보 찾기`
- variables: `{{universe}}`, `{{candidate_count}}`, `{{as_of}}`, `{{existing_system_candidates}}`, `{{system_coverage_summary}}`
- system_overlap: `LOW_TO_MEDIUM`

```text
목적: 시스템·Consensus가 놓친 후보 찾기

정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
Universe는 `{{universe}}`, 최대 후보 수는 `{{candidate_count}}`, 기존 시스템 후보는 `{{existing_system_candidates}}`다. 결과는 매수 추천이 아니라 다음 QGV/Technical/Macro 분석으로 보낼 Research Candidate다. 기존 후보를 반복할 때는 새로운 비정형 Evidence가 있을 때만 포함해.

조사 초점: {{system_coverage_summary}}의 Coverage Gap, 작은 세부시장, 비정형 Evidence와 Consensus 부재를 이용하되 단순 저유동성·데이터 부족을 강점으로 오인하지 않는다.

출력:
1. 미포착 후보
2. 왜 시스템 밖인지
3. 새 Evidence
4. 데이터 공백/유동성 위험
5. Research Candidate 등록 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-002.v1.0 — 사업모델과 경제적 엔진 이해하기

- prompt_id: `plv1.fund.002`
- prompt_code: `FUND-002.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 고객, 지불 주체, 가격결정, 비용구조, 반복성, 단위경제와 Value Chain 위치를 설명하되 QGV 점수를 다시 계산하지 않는다.
- domain: `FUNDAMENTAL`
- role: `BASIC`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `BUSINESS_AND_RESULTS`
- tags: `fundamental`, `basic`, `business_and_results`
- keywords: `사업모델과`, `경제적`, `엔진`, `이해하기`
- aliases: `사업모델 쉽게 이해하기`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 사업모델과 경제적 엔진 이해하기

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 고객, 지불 주체, 가격결정, 비용구조, 반복성, 단위경제와 Value Chain 위치를 설명하되 QGV 점수를 다시 계산하지 않는다.

출력:
1. 수익 창출 구조
2. 고객/지불 주체
3. Unit Economics
4. 확장 제약
5. 검증할 원자료

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-003.v1.0 — 경쟁사·대체재 Evidence 비교

- prompt_id: `plv1.fund.003`
- prompt_code: `FUND-003.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})와 직접 경쟁사·간접 대체재를 동일 세부시장 기준으로 비교하고 시장점유율·기술·가격·채널의 출처 차이를 확인한다.
- domain: `FUNDAMENTAL`
- role: `BASIC`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `BUSINESS_AND_RESULTS`
- tags: `fundamental`, `basic`, `business_and_results`
- keywords: `경쟁사`, `대체재`, `Evidence`, `비교`
- aliases: `경쟁사와 한 번에 비교하기`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 경쟁사·대체재 Evidence 비교

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})와 직접 경쟁사·간접 대체재를 동일 세부시장 기준으로 비교하고 시장점유율·기술·가격·채널의 출처 차이를 확인한다.

출력:
1. 동일 기준 Peer Set
2. 직접 비교표
3. 우위/열위 Evidence
4. 비교 불가능 항목
5. QGV에 없는 새 정보

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-004.v1.0 — 최근 실적의 질과 변화 분석

- prompt_id: `plv1.fund.004`
- prompt_code: `FUND-004.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{earnings_period}} 실적을 기대치·전년·전분기와 비교하고 가격/물량/Mix, 일회성, 현금흐름, Guidance 변화를 분해한다.
- domain: `FUNDAMENTAL`
- role: `BASIC`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `BUSINESS_AND_RESULTS`
- tags: `fundamental`, `basic`, `business_and_results`
- keywords: `최근`, `실적의`, `질과`, `변화`, `분석`
- aliases: `최근 실적 쉽게 분석하기`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`, `{{earnings_period}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 최근 실적의 질과 변화 분석

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 {{earnings_period}} 실적을 기대치·전년·전분기와 비교하고 가격/물량/Mix, 일회성, 현금흐름, Guidance 변화를 분해한다.

출력:
1. 핵심 Surprise
2. 성장·Margin Bridge
3. 현금흐름 품질
4. Guidance 변화
5. 지속/반전 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-006.v1.0 — 핵심 기업위험과 전염경로 파악

- prompt_id: `plv1.fund.006`
- prompt_code: `FUND-006.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 운영·재무·고객·공급·규제·기술 위험을 발생가능성만이 아니라 전달경로와 조기경보로 정리한다.
- domain: `FUNDAMENTAL`
- role: `BASIC`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `BUSINESS_AND_RESULTS`
- tags: `fundamental`, `basic`, `business_and_results`
- keywords: `핵심`, `기업위험과`, `전염경로`, `파악`
- aliases: `기업의 핵심 위험 한 번에 파악하기`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 핵심 기업위험과 전염경로 파악

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 운영·재무·고객·공급·규제·기술 위험을 발생가능성만이 아니라 전달경로와 조기경보로 정리한다.

출력:
1. 위험 Event
2. 전달경로
3. 노출/민감도
4. 조기경보
5. 완화 Evidence와 잔여위험

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-007.v1.0 — 매출 성장 Driver 분해

- prompt_id: `plv1.fund.007`
- prompt_code: `FUND-007.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 매출 변화를 가격·물량·Mix·환율·인수·신규고객·Churn으로 분해하고 Reported와 Organic Growth를 구분한다.
- domain: `FUNDAMENTAL`
- role: `EXPAND`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `BUSINESS_AND_RESULTS`
- tags: `fundamental`, `expand`, `business_and_results`
- keywords: `매출`, `성장`, `Driver`, `분해`
- aliases: `매출 성장의 실제 원인 분해`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 매출 성장 Driver 분해

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 매출 변화를 가격·물량·Mix·환율·인수·신규고객·Churn으로 분해하고 Reported와 Organic Growth를 구분한다.

출력:
1. Growth Bridge
2. 반복/일회성 Driver
3. 세그먼트 기여
4. 반대 Evidence
5. 다음 분기 확인치

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-008.v1.0 — Margin 변화와 정상화 위험 분석

- prompt_id: `plv1.fund.008`
- prompt_code: `FUND-008.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 Gross/Operating/FCF Margin 변화를 가격·Mix·원가·가동률·SBC·일회성으로 분해하고 정상화/역전 Scenario를 함께 검증한다.
- domain: `FUNDAMENTAL`
- role: `EXPAND`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `BUSINESS_AND_RESULTS`
- tags: `fundamental`, `expand`, `business_and_results`
- keywords: `Margin`, `변화와`, `정상화`, `위험`, `분석`
- aliases: `Margin 변화 원인 분석`, `FUND-020`, `plv1.fund.020`, `Margin 정상화 위험`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Margin 변화와 정상화 위험 분석

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 Gross/Operating/FCF Margin 변화를 가격·Mix·원가·가동률·SBC·일회성으로 분해하고 정상화/역전 Scenario를 함께 검증한다.

출력:
1. Margin Bridge
2. 구조적/순환적 요인
3. 정상화 범위
4. 역전 Trigger
5. 검증 Evidence

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-009.v1.0 — FCF 변화와 현금전환 품질 분석

- prompt_id: `plv1.fund.009`
- prompt_code: `FUND-009.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 FCF를 영업현금흐름·운전자본·CAPEX·SBC·세금·인수 관련 현금흐름으로 분해해 질과 지속성을 검증한다.
- domain: `FUNDAMENTAL`
- role: `EXPAND`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `BUSINESS_AND_RESULTS`
- tags: `fundamental`, `expand`, `business_and_results`
- keywords: `FCF`, `변화와`, `현금전환`, `품질`, `분석`
- aliases: `FCF 변화 원인 분석`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: FCF 변화와 현금전환 품질 분석

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 FCF를 영업현금흐름·운전자본·CAPEX·SBC·세금·인수 관련 현금흐름으로 분해해 질과 지속성을 검증한다.

출력:
1. FCF Bridge
2. 현금전환율
3. 운전자본 효과
4. SBC/희석 연결
5. 지속 가능성

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-010.v1.0 — 시장점유율 변화 원인 검증

- prompt_id: `plv1.fund.010`
- prompt_code: `FUND-010.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 Share 변화가 가격, 제품력, 공급능력, 유통, 경쟁사 문제 중 무엇에서 왔는지 세부시장과 기간을 맞춰 검증한다.
- domain: `FUNDAMENTAL`
- role: `EXPAND`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `BUSINESS_AND_RESULTS`
- tags: `fundamental`, `expand`, `business_and_results`
- keywords: `시장점유율`, `변화`, `원인`, `검증`
- aliases: `시장점유율 변화 원인 분석`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 시장점유율 변화 원인 검증

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 Share 변화가 가격, 제품력, 공급능력, 유통, 경쟁사 문제 중 무엇에서 왔는지 세부시장과 기간을 맞춰 검증한다.

출력:
1. 세부시장 정의
2. 점유율 추세
3. 변화 원인
4. 경쟁사 교차검증
5. 측정 한계

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-011.v1.0 — 경쟁우위·신규 경쟁·대체기술 심층검증

- prompt_id: `plv1.fund.011`
- prompt_code: `FUND-011.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 Moat를 고객 행동과 경제적 Evidence로 검증하고 과대평가 가능성, 신규 경쟁자, 대체기술과 침식 경로까지 함께 조사한다.
- domain: `FUNDAMENTAL`
- role: `EXPAND`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ASSUMPTION_AND_RED_TEAM`
- tags: `fundamental`, `expand`, `assumption_and_red_team`
- keywords: `경쟁우위`, `신규`, `경쟁`, `대체기술`, `심층검증`
- aliases: `경쟁우위 지속 가능성 심층검증`, `FUND-018`, `plv1.fund.018`, `경쟁우위가 과대평가됐을 가능성`, `FUND-027`, `plv1.fund.027`, `신규 경쟁자·대체기술 등장 조사`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 경쟁우위·신규 경쟁·대체기술 심층검증

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 Moat를 고객 행동과 경제적 Evidence로 검증하고 과대평가 가능성, 신규 경쟁자, 대체기술과 침식 경로까지 함께 조사한다.

출력:
1. Moat별 Evidence
2. 지속 조건
3. 침식/대체 경로
4. 신규 경쟁 Signal
5. 판단 변경 Trigger

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-012.v1.0 — 경영진 자본배분 Track Record 검증

- prompt_id: `plv1.fund.012`
- prompt_code: `FUND-012.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 R&D, CAPEX, M&A, 배당, 자사주, 부채 의사결정을 당시 선택지와 이후 결과로 평가한다.
- domain: `FUNDAMENTAL`
- role: `EXPAND`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ASSUMPTION_AND_RED_TEAM`
- tags: `fundamental`, `expand`, `assumption_and_red_team`
- keywords: `경영진`, `자본배분`, `Track`, `Record`, `검증`
- aliases: `경영진 자본배분 Track Record`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 경영진 자본배분 Track Record 검증

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 R&D, CAPEX, M&A, 배당, 자사주, 부채 의사결정을 당시 선택지와 이후 결과로 평가한다.

출력:
1. 자본배분 Timeline
2. 당시 근거
3. 실제 결과
4. 주당가치 영향
5. 반복되는 오류/강점

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-013.v1.0 — Guidance 신뢰도와 편향 검증

- prompt_id: `plv1.fund.013`
- prompt_code: `FUND-013.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 과거 Guidance, 중간 수정, 실제 결과와 경영진 표현을 비교해 보수성·낙관성·가시성 변화를 확인한다.
- domain: `FUNDAMENTAL`
- role: `EXPAND`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ASSUMPTION_AND_RED_TEAM`
- tags: `fundamental`, `expand`, `assumption_and_red_team`
- keywords: `Guidance`, `신뢰도와`, `편향`, `검증`
- aliases: `Guidance 신뢰도 검증`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Guidance 신뢰도와 편향 검증

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 과거 Guidance, 중간 수정, 실제 결과와 경영진 표현을 비교해 보수성·낙관성·가시성 변화를 확인한다.

출력:
1. Guidance Track Record
2. 오차 방향/크기
3. 표현 변화
4. 현재 Guidance 취약점
5. 다음 검증 시점

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-014.v1.0 — 성장 가정과 지속 가능성 Red Team

- prompt_id: `plv1.fund.014`
- prompt_code: `FUND-014.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 TAM, 침투율, 가격, 고객획득, 공급능력 가정을 분리하고 성장률이 지속되지 못할 조건과 Base Rate를 검증한다.
- domain: `FUNDAMENTAL`
- role: `EXPAND`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ASSUMPTION_AND_RED_TEAM`
- tags: `fundamental`, `expand`, `assumption_and_red_team`
- keywords: `성장`, `가정과`, `지속`, `가능성`, `Red`, `Team`
- aliases: `성장 가정 현실성 검증`, `FUND-019`, `plv1.fund.019`, `성장률이 지속되지 못할 이유`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 성장 가정과 지속 가능성 Red Team

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 TAM, 침투율, 가격, 고객획득, 공급능력 가정을 분리하고 성장률이 지속되지 못할 조건과 Base Rate를 검증한다.

출력:
1. 핵심 성장 가정
2. 근거와 Base Rate
3. 용량/수요 제약
4. 실패 Scenario
5. 가정별 Invalidation

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-015.v1.0 — Reverse DCF·Valuation Scenario 검증

- prompt_id: `plv1.fund.015`
- prompt_code: `FUND-015.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{reverse_dcf_assumptions}}가 요구하는 성장·Margin·재투자·할인율을 현실 Evidence와 비교하고 Valuation을 정당화하지 못하는 Scenario를 찾는다.
- domain: `FUNDAMENTAL`
- role: `EXPAND`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ASSUMPTION_AND_RED_TEAM`
- tags: `fundamental`, `expand`, `assumption_and_red_team`
- keywords: `Reverse`, `DCF`, `Valuation`, `Scenario`, `검증`
- aliases: `Reverse DCF 가정 현실성 검증`, `FUND-021`, `plv1.fund.021`, `Valuation을 정당화하지 못할 Scenario`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`, `{{reverse_dcf_assumptions}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Reverse DCF·Valuation Scenario 검증

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 {{reverse_dcf_assumptions}}가 요구하는 성장·Margin·재투자·할인율을 현실 Evidence와 비교하고 Valuation을 정당화하지 못하는 Scenario를 찾는다.

출력:
1. 내재 가정
2. 역사/Peer 비교
3. 달성 난이도
4. 실패 Scenario
5. 확인할 선행지표

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-016.v1.0 — 신규사업 경제성 검증

- prompt_id: `plv1.fund.016`
- prompt_code: `FUND-016.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}}) 신규사업의 고객문제, 수익모델, Unit Economics, Cannibalization, 초기투자, Scale 조건을 기존사업과 분리해 평가한다.
- domain: `FUNDAMENTAL`
- role: `EXPAND`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ASSUMPTION_AND_RED_TEAM`
- tags: `fundamental`, `expand`, `assumption_and_red_team`
- keywords: `신규사업`, `경제성`, `검증`
- aliases: `신규사업 경제성 분석`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 신규사업 경제성 검증

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}}) 신규사업의 고객문제, 수익모델, Unit Economics, Cannibalization, 초기투자, Scale 조건을 기존사업과 분리해 평가한다.

출력:
1. 신규사업 범위
2. Unit Economics
3. Scale/투자 조건
4. Cannibalization
5. 중단/성공 기준

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-017.v1.0 — Bull Case의 가장 약한 전제 찾기

- prompt_id: `plv1.fund.017`
- prompt_code: `FUND-017.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 긍정 Thesis를 구성하는 전제를 나열하고 결과 민감도와 Evidence 강도를 기준으로 가장 취약한 전제를 검증한다.
- domain: `FUNDAMENTAL`
- role: `CHALLENGE`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ASSUMPTION_AND_RED_TEAM`
- tags: `fundamental`, `challenge`, `assumption_and_red_team`
- keywords: `Bull`, `Case의`, `가장`, `약한`, `전제`, `찾기`
- aliases: `Bull Case의 가장 약한 전제`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Bull Case의 가장 약한 전제 찾기

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 긍정 Thesis를 구성하는 전제를 나열하고 결과 민감도와 Evidence 강도를 기준으로 가장 취약한 전제를 검증한다.

출력:
1. Bull Case 전제
2. 민감도
3. 반대 Evidence
4. 붕괴 순서
5. Thesis Invalidation

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-022.v1.0 — 경영진 주장과 반대 Evidence 검증

- prompt_id: `plv1.fund.022`
- prompt_code: `FUND-022.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}}) 경영진의 핵심 주장을 원문으로 특정하고 고객·경쟁사·직원·공급망·규제 자료에서 반대되는 Evidence를 찾는다.
- domain: `FUNDAMENTAL`
- role: `CHALLENGE`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ASSUMPTION_AND_RED_TEAM`
- tags: `fundamental`, `challenge`, `assumption_and_red_team`
- keywords: `경영진`, `주장과`, `반대`, `Evidence`, `검증`
- aliases: `경영진 주장과 반대되는 Evidence`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 경영진 주장과 반대 Evidence 검증

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}}) 경영진의 핵심 주장을 원문으로 특정하고 고객·경쟁사·직원·공급망·규제 자료에서 반대되는 Evidence를 찾는다.

출력:
1. 경영진 주장
2. 지지 Evidence
3. 반대 Evidence
4. 출처 신뢰도
5. 판단 영향

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-023.v1.0 — 고객·제품·가격 반응 통합 조사

- prompt_id: `plv1.fund.023`
- prompt_code: `FUND-023.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{customer_evidence_scope}}에서 불만, 실제 제품반응, 가격 인상 수용도, Churn·대체 행동을 표본 편향과 함께 조사한다.
- domain: `FUNDAMENTAL`
- role: `BLIND-SPOT`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ALTERNATIVE_EVIDENCE`
- tags: `fundamental`, `blind-spot`, `alternative_evidence`
- keywords: `고객`, `제품`, `가격`, `반응`, `통합`, `조사`
- aliases: `고객이 실제로 불만을 가지는 부분 찾기`, `FUND-024`, `plv1.fund.024`, `제품에 대한 실제 시장 반응 조사`, `FUND-025`, `plv1.fund.025`, `가격 인상에 대한 고객 반응`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`, `{{customer_evidence_scope}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 고객·제품·가격 반응 통합 조사

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 {{customer_evidence_scope}}에서 불만, 실제 제품반응, 가격 인상 수용도, Churn·대체 행동을 표본 편향과 함께 조사한다.

출력:
1. 고객 Segment
2. 반응 유형
3. 가격/제품 Evidence
4. 표본·선택 편향
5. 사업지표 연결

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-026.v1.0 — 고객·공급업체 의존성 변화 조사

- prompt_id: `plv1.fund.026`
- prompt_code: `FUND-026.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 핵심 고객·공급업체 집중도, 계약 변화, Dual Sourcing, 내재화와 협상력 변화를 확인한다.
- domain: `FUNDAMENTAL`
- role: `BLIND-SPOT`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ALTERNATIVE_EVIDENCE`
- tags: `fundamental`, `blind-spot`, `alternative_evidence`
- keywords: `고객`, `공급업체`, `의존성`, `변화`, `조사`
- aliases: `핵심 고객·공급업체 의존성 변화`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 고객·공급업체 의존성 변화 조사

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 핵심 고객·공급업체 집중도, 계약 변화, Dual Sourcing, 내재화와 협상력 변화를 확인한다.

출력:
1. 의존 관계
2. 집중도 변화
3. 계약/대체 Evidence
4. 실적 민감도
5. 조기경보

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-028.v1.0 — 핵심 인력·조직 변화 조사

- prompt_id: `plv1.fund.028`
- prompt_code: `FUND-028.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 경영진·기술·영업 핵심 인력 이동, 조직개편, 채용·이탈 패턴이 전략 실행에 주는 신호를 검증한다.
- domain: `FUNDAMENTAL`
- role: `BLIND-SPOT`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ALTERNATIVE_EVIDENCE`
- tags: `fundamental`, `blind-spot`, `alternative_evidence`
- keywords: `핵심`, `인력`, `조직`, `변화`, `조사`
- aliases: `핵심 인력·조직 변화 조사`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 핵심 인력·조직 변화 조사

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 경영진·기술·영업 핵심 인력 이동, 조직개편, 채용·이탈 패턴이 전략 실행에 주는 신호를 검증한다.

출력:
1. 인력/조직 Event
2. 역할 중요도
3. 반복 패턴
4. 실행 영향
5. 확인 불가 영역

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-029.v1.0 — 규제·소송의 새로운 변화 조사

- prompt_id: `plv1.fund.029`
- prompt_code: `FUND-029.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}}) 관련 법안·규칙·집행·소송의 절차단계와 새 Evidence를 구분하고 최종 결과를 단정하지 않는다.
- domain: `FUNDAMENTAL`
- role: `BLIND-SPOT`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ALTERNATIVE_EVIDENCE`
- tags: `fundamental`, `blind-spot`, `alternative_evidence`
- keywords: `규제`, `소송의`, `새로운`, `변화`, `조사`
- aliases: `규제·소송의 새로운 변화 조사`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 규제·소송의 새로운 변화 조사

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}}) 관련 법안·규칙·집행·소송의 절차단계와 새 Evidence를 구분하고 최종 결과를 단정하지 않는다.

출력:
1. 사건/절차단계
2. 새로운 변화
3. 가능한 경로
4. 재무·사업 노출
5. 다음 확인일

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### FUND-030.v1.0 — 회계·공시·숫자 밖 사업 변화 찾기

- prompt_id: `plv1.fund.030`
- prompt_code: `FUND-030.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 Footnote, 회계정책, Accrual, SBC, 희석, Convertible, Off-balance-sheet 항목과 숫자에 아직 반영되지 않은 사업 변화를 함께 조사한다.
- domain: `FUNDAMENTAL`
- role: `BLIND-SPOT`
- category: `FUNDAMENTAL_EVIDENCE_EXTENSION`
- subcategory: `ALTERNATIVE_EVIDENCE`
- tags: `fundamental`, `blind-spot`, `alternative_evidence`
- keywords: `회계`, `공시`, `숫자`, `밖`, `사업`, `변화`, `찾기`
- aliases: `숫자에 아직 나타나지 않은 사업 변화 찾기`
- variables: `{{company}}`, `{{ticker}}`, `{{as_of}}`, `{{qgv_snapshot_summary}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 회계·공시·숫자 밖 사업 변화 찾기

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
기존 QGV 요약은 `{{qgv_snapshot_summary}}`다. 이를 재계산하거나 새로운 Q/G/V 점수로 대체하지 말고, 시스템이 아직 갖지 못한 외부·비정형·반대 Evidence를 조사해. 요약이 비어 있어도 독자 QGV 점수를 만들지 마.

조사 초점: {{company}}({{ticker}})의 Footnote, 회계정책, Accrual, SBC, 희석, Convertible, Off-balance-sheet 항목과 숫자에 아직 반영되지 않은 사업 변화를 함께 조사한다.

출력:
1. 새 비정형 Evidence
2. 회계/자본구조 항목
3. SBC·희석 Bridge
4. 사업 변화와 시차
5. 감사·추가 확인 질문

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-001.v1.0 — TechnicalSnapshot 해석과 데이터 품질 점검

- prompt_id: `plv1.tech.001`
- prompt_code: `TECH-001.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}의 Trend·Momentum·Volume/Flow·Relative Strength·Structure·Volatility·Support/Resistance를 함께 해석하고 Corporate Action·결측·시간대·조정가격 오류를 먼저 점검한다.
- domain: `TECHNICAL`
- role: `BASIC`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_STRUCTURE`
- tags: `technical`, `basic`, `state_and_structure`
- keywords: `TechnicalSnapshot`, `해석과`, `데이터`, `품질`, `점검`
- aliases: `차트 한 번에 분석하기`, `TECH-002`, `plv1.tech.002`, `현재 주가 위치 파악하기`, `TECH-003`, `plv1.tech.003`, `추세가 살아있는지 확인하기`, `TECH-004`, `plv1.tech.004`, `Momentum 상태 점검하기`, `TECH-005`, `plv1.tech.005`, `지지·저항 구간 찾기`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: TechnicalSnapshot 해석과 데이터 품질 점검

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}의 Trend·Momentum·Volume/Flow·Relative Strength·Structure·Volatility·Support/Resistance를 함께 해석하고 Corporate Action·결측·시간대·조정가격 오류를 먼저 점검한다.

출력:
1. Input/Data Quality
2. Technical State
3. 상충 Signal
4. Scenario/Confirmation
5. Invalidation/추가 데이터

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-006.v1.0 — Multi-timeframe 정합성 분석

- prompt_id: `plv1.tech.006`
- prompt_code: `TECH-006.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}에서 장·중·단기 Trend와 Structure가 일치하는지, 짧은 신호가 긴 Timeframe 구조를 실제로 변경했는지 구분한다.
- domain: `TECHNICAL`
- role: `BASIC`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_STRUCTURE`
- tags: `technical`, `basic`, `state_and_structure`
- keywords: `Multi`, `timeframe`, `정합성`, `분석`
- aliases: `Multi-timeframe으로 한 번에 보기`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Multi-timeframe 정합성 분석

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}에서 장·중·단기 Trend와 Structure가 일치하는지, 짧은 신호가 긴 Timeframe 구조를 실제로 변경했는지 구분한다.

출력:
1. Timeframe별 State
2. 정합/충돌
3. 지배 Timeframe
4. 전환 조건
5. Invalidation

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-007.v1.0 — Breakout·Pullback 구조 무결성 검증

- prompt_id: `plv1.tech.007`
- prompt_code: `TECH-007.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}에서 Base, Breakout, Retest/Pullback, 거래량, 공급 Overhang을 연결하고 False Breakout 가능성까지 하나의 구조로 검증한다.
- domain: `TECHNICAL`
- role: `EXPAND`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_STRUCTURE`
- tags: `technical`, `expand`, `state_and_structure`
- keywords: `Breakout`, `Pullback`, `구조`, `무결성`, `검증`
- aliases: `Breakout 구조 심층검증`, `TECH-008`, `plv1.tech.008`, `Pullback의 질 분석`, `TECH-014`, `plv1.tech.014`, `False Breakout 가능성 검증`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Breakout·Pullback 구조 무결성 검증

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}에서 Base, Breakout, Retest/Pullback, 거래량, 공급 Overhang을 연결하고 False Breakout 가능성까지 하나의 구조로 검증한다.

출력:
1. 구조 단계
2. Breakout/Pullback 품질
3. Volume 확인
4. False Breakout Evidence
5. Trigger/Invalidation

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-009.v1.0 — Relative Strength 변화 검증

- prompt_id: `plv1.tech.009`
- prompt_code: `TECH-009.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}와 {{benchmark_or_peers}}를 동일 기간·통화·Corporate Action 기준으로 맞춰 절대수익률과 상대강도의 개선을 구분한다.
- domain: `TECHNICAL`
- role: `EXPAND`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_STRUCTURE`
- tags: `technical`, `expand`, `state_and_structure`
- keywords: `Relative`, `Strength`, `변화`, `검증`
- aliases: `Relative Strength 변화 분석`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`, `{{benchmark_or_peers}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Relative Strength 변화 검증

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}와 {{benchmark_or_peers}}를 동일 기간·통화·Corporate Action 기준으로 맞춰 절대수익률과 상대강도의 개선을 구분한다.

출력:
1. 비교 기준
2. RS 추세
3. Peer/Market 분해
4. Divergence
5. 지속/무효화 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-010.v1.0 — 거래량·Flow 변화의 의미 검증

- prompt_id: `plv1.tech.010`
- prompt_code: `TECH-010.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}의 거래량을 가격 위치, Gap, Event, 평균 대비, 누적/분배 맥락에서 해석하고 단순 거래량 급증을 매수신호로 취급하지 않는다.
- domain: `TECHNICAL`
- role: `EXPAND`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_STRUCTURE`
- tags: `technical`, `expand`, `state_and_structure`
- keywords: `거래량`, `Flow`, `변화의`, `의미`, `검증`
- aliases: `거래량 변화의 의미 분석`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 거래량·Flow 변화의 의미 검증

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}의 거래량을 가격 위치, Gap, Event, 평균 대비, 누적/분배 맥락에서 해석하고 단순 거래량 급증을 매수신호로 취급하지 않는다.

출력:
1. Volume 이상
2. 가격과 결합 의미
3. Event 연결
4. 반대 해석
5. 확인 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-011.v1.0 — Volatility Regime 변화 분석

- prompt_id: `plv1.tech.011`
- prompt_code: `TECH-011.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}에서 실현변동성, ATR, Gap, Tail, Range 변화가 Trend 강화인지 불안정성 확대인지 구분하고 Regime 전환을 검증한다.
- domain: `TECHNICAL`
- role: `EXPAND`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_STRUCTURE`
- tags: `technical`, `expand`, `state_and_structure`
- keywords: `Volatility`, `Regime`, `변화`, `분석`
- aliases: `Volatility Regime 변화 분석`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Volatility Regime 변화 분석

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}에서 실현변동성, ATR, Gap, Tail, Range 변화가 Trend 강화인지 불안정성 확대인지 구분하고 Regime 전환을 검증한다.

출력:
1. Volatility State
2. Regime 변화 Evidence
3. Trend와 관계
4. Risk Range
5. 전환 Invalidation

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-012.v1.0 — 추세전환 구조와 False Reversal 검증

- prompt_id: `plv1.tech.012`
- prompt_code: `TECH-012.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}에서 저점/고점 구조, Momentum, Volume, RS, 변동성 수축·확장을 결합해 실제 추세전환과 일시적 반등을 구분한다.
- domain: `TECHNICAL`
- role: `EXPAND`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_STRUCTURE`
- tags: `technical`, `expand`, `state_and_structure`
- keywords: `추세전환`, `구조와`, `False`, `Reversal`, `검증`
- aliases: `추세전환 구조 심층검증`, `TECH-018`, `plv1.tech.018`, `반전 신호가 False Signal일 가능성`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 추세전환 구조와 False Reversal 검증

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}에서 저점/고점 구조, Momentum, Volume, RS, 변동성 수축·확장을 결합해 실제 추세전환과 일시적 반등을 구분한다.

출력:
1. 기존/후보 추세
2. 전환 Evidence
3. False Reversal Evidence
4. Confirmation
5. Invalidation

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-013.v1.0 — 상승추세·Momentum Signal Red Team

- prompt_id: `plv1.tech.013`
- prompt_code: `TECH-013.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}의 강세 해석에 반대되는 Momentum Divergence, 약한 Participation, RS 둔화, Volume/Structure 손상을 찾아 억지 반론과 구분한다.
- domain: `TECHNICAL`
- role: `CHALLENGE`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_STRUCTURE`
- tags: `technical`, `challenge`, `state_and_structure`
- keywords: `상승추세`, `Momentum`, `Signal`, `Red`, `Team`
- aliases: `현재 상승추세가 틀릴 수 있는 이유`, `TECH-015`, `plv1.tech.015`, `Momentum 신호가 잘못됐을 가능성`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 상승추세·Momentum Signal Red Team

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}의 강세 해석에 반대되는 Momentum Divergence, 약한 Participation, RS 둔화, Volume/Structure 손상을 찾아 억지 반론과 구분한다.

출력:
1. 현재 Bullish 해석
2. 반대 Signal
3. Evidence 강도
4. 추세 유지 조건
5. 판단 변경 Trigger

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-017.v1.0 — Scenario·Support Invalidation 검증

- prompt_id: `plv1.tech.017`
- prompt_code: `TECH-017.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}의 Bullish Scenario와 주요 Support가 실패하는 가격·기간·거래량 조건을 사전에 정의하고 단일 장중 이탈과 구조적 실패를 구분한다.
- domain: `TECHNICAL`
- role: `CHALLENGE`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_STRUCTURE`
- tags: `technical`, `challenge`, `state_and_structure`
- keywords: `Scenario`, `Support`, `Invalidation`, `검증`
- aliases: `Bullish Scenario의 Invalidation 검증`, `TECH-016`, `plv1.tech.016`, `주요 Support가 실패할 가능성`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Scenario·Support Invalidation 검증

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}의 Bullish Scenario와 주요 Support가 실패하는 가격·기간·거래량 조건을 사전에 정의하고 단일 장중 이탈과 구조적 실패를 구분한다.

출력:
1. Scenario 전제
2. Support 근거
3. Confirmation
4. Invalidation
5. 실패 후 대안 Scenario

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-019.v1.0 — 최근 가격 움직임의 실제 Catalyst 찾기

- prompt_id: `plv1.tech.019`
- prompt_code: `TECH-019.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}과 {{news_event_evidence}}의 시간순서를 맞춰 실적·정책·Peer·Positioning 중 실제 Catalyst와 사후 설명을 구분한다.
- domain: `TECHNICAL`
- role: `BLIND-SPOT`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `CATALYST_AND_DIVERGENCE`
- tags: `technical`, `blind-spot`, `catalyst_and_divergence`
- keywords: `최근`, `가격`, `움직임의`, `실제`, `Catalyst`, `찾기`
- aliases: `최근 가격 움직임의 실제 Catalyst 찾기`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`, `{{news_event_evidence}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 최근 가격 움직임의 실제 Catalyst 찾기

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}과 {{news_event_evidence}}의 시간순서를 맞춰 실적·정책·Peer·Positioning 중 실제 Catalyst와 사후 설명을 구분한다.

출력:
1. 가격 Event
2. 후보 Catalyst
3. 시간 선후관계
4. 설명되지 않은 잔차
5. 추가 확인 Source

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-020.v1.0 — 기업·산업·Macro 가격 움직임 분해

- prompt_id: `plv1.tech.020`
- prompt_code: `TECH-020.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}과 {{benchmark_or_peers}}를 이용해 기업 고유, 산업 공통, 시장/Macro 요인을 분리하되 회귀계수를 임의 생성하지 않는다.
- domain: `TECHNICAL`
- role: `BLIND-SPOT`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `CATALYST_AND_DIVERGENCE`
- tags: `technical`, `blind-spot`, `catalyst_and_divergence`
- keywords: `기업`, `산업`, `Macro`, `가격`, `움직임`, `분해`
- aliases: `기업 vs 산업 vs Macro 움직임 분해`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`, `{{benchmark_or_peers}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 기업·산업·Macro 가격 움직임 분해

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}과 {{benchmark_or_peers}}를 이용해 기업 고유, 산업 공통, 시장/Macro 요인을 분리하되 회귀계수를 임의 생성하지 않는다.

출력:
1. 가격 움직임 구간
2. 기업/산업/시장 Evidence
3. 설명 비중의 한계
4. 고유 잔차
5. 추가 데이터

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-021.v1.0 — Peer 가격행동 Divergence 조사

- prompt_id: `plv1.tech.021`
- prompt_code: `TECH-021.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}과 {{benchmark_or_peers}}에서 동일 Event·기간의 Peer 반응을 비교해 기업 고유 Divergence와 데이터 차이를 찾는다.
- domain: `TECHNICAL`
- role: `BLIND-SPOT`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `CATALYST_AND_DIVERGENCE`
- tags: `technical`, `blind-spot`, `catalyst_and_divergence`
- keywords: `Peer`, `가격행동`, `Divergence`, `조사`
- aliases: `Peer 가격행동과 Divergence 찾기`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`, `{{benchmark_or_peers}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Peer 가격행동 Divergence 조사

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}과 {{benchmark_or_peers}}에서 동일 Event·기간의 Peer 반응을 비교해 기업 고유 Divergence와 데이터 차이를 찾는다.

출력:
1. Peer Set
2. 공통 움직임
3. Divergence
4. 가능한 원인
5. 확인/무효화 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-022.v1.0 — 뉴스와 가격반응 불일치 조사

- prompt_id: `plv1.tech.022`
- prompt_code: `TECH-022.v1.0`
- status: `ACTIVE`
- purpose: {{technical_input}}과 {{news_event_evidence}}에서 뉴스의 방향·기대 대비 새로움·공개시점과 가격반응을 비교해 Buy-the-rumor/Sell-the-news 가능성을 검증한다.
- domain: `TECHNICAL`
- role: `BLIND-SPOT`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `CATALYST_AND_DIVERGENCE`
- tags: `technical`, `blind-spot`, `catalyst_and_divergence`
- keywords: `뉴스와`, `가격반응`, `불일치`, `조사`
- aliases: `뉴스와 가격반응의 불일치 조사`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`, `{{news_event_evidence}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 뉴스와 가격반응 불일치 조사

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{technical_input}}과 {{news_event_evidence}}에서 뉴스의 방향·기대 대비 새로움·공개시점과 가격반응을 비교해 Buy-the-rumor/Sell-the-news 가능성을 검증한다.

출력:
1. News Claim
2. 기대 대비 Surprise
3. 가격/Volume 반응
4. 불일치 설명
5. 후속 확인 Event

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### TECH-023.v1.0 — Options·Positioning 보조신호 조사

- prompt_id: `plv1.tech.023`
- prompt_code: `TECH-023.v1.0`
- status: `ACTIVE`
- purpose: {{options_positioning_data}}를 {{technical_input}}과 함께 보되 IV, Skew, Open Interest, Dealer/Flow 추정을 사실과 분리하고 데이터가 없으면 결론내리지 않는다.
- domain: `TECHNICAL`
- role: `BLIND-SPOT`
- category: `TECHNICAL_EVIDENCE_EXTENSION`
- subcategory: `CATALYST_AND_DIVERGENCE`
- tags: `technical`, `blind-spot`, `catalyst_and_divergence`
- keywords: `Options`, `Positioning`, `보조신호`, `조사`
- aliases: `Options/Positioning의 다른 신호 조사`
- variables: `{{input_mode}}`, `{{ticker}}`, `{{period}}`, `{{as_of}}`, `{{technical_input}}`, `{{options_positioning_data}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Options·Positioning 보조신호 조사

분석 대상 Ticker는 `{{ticker}}`, 기간은 `{{period}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{technical_input}}`의 기존 TechnicalSnapshot/계산 결과를 사실로 받아들이고 지표를 다시 계산하거나 새 점수를 만들지 마. STANDALONE이면 `{{technical_input}}`에 {{period}}의 PIT OHLCV, 조정/비조정 기준, 거래소 시간대, Corporate Action과 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{options_positioning_data}}를 {{technical_input}}과 함께 보되 IV, Skew, Open Interest, Dealer/Flow 추정을 사실과 분리하고 데이터가 없으면 결론내리지 않는다.

출력:
1. 데이터 Provenance
2. Options/Positioning Signal
3. 현물과 일치/충돌
4. 추정 한계
5. 확인할 후속 데이터

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-001.v1.0 — MacroSnapshot 해석과 누락 Evidence 점검

- prompt_id: `plv1.macro.001`
- prompt_code: `MACRO-001.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}을 Growth / Inflation / Liquidity / Monetary Policy / Credit / Labor / Fiscal / FX 축으로 해석한다. Rates/Risk 5축 표시는 Summary View일 뿐 새 Schema가 아니다.
- domain: `MACRO`
- role: `BASIC`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_DRIVERS`
- tags: `macro`, `basic`, `state_and_drivers`
- keywords: `MacroSnapshot`, `해석과`, `누락`, `Evidence`, `점검`
- aliases: `현재 시장환경 한 번에 이해하기`, `MACRO-002`, `plv1.macro.002`, `Growth 상태 이해하기`, `MACRO-003`, `plv1.macro.003`, `Inflation 상태 이해하기`, `MACRO-004`, `plv1.macro.004`, `금리환경 이해하기`, `MACRO-005`, `plv1.macro.005`, `Liquidity 상태 이해하기`, `MACRO-006`, `plv1.macro.006`, `현재 시장 Risk 이해하기`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: MacroSnapshot 해석과 누락 Evidence 점검

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}을 Growth / Inflation / Liquidity / Monetary Policy / Credit / Labor / Fiscal / FX 축으로 해석한다. Rates/Risk 5축 표시는 Summary View일 뿐 새 Schema가 아니다.

출력:
1. 축별 State/Direction
2. 축간 충돌
3. Regime/Confidence
4. 누락·지연 Evidence
5. Scenario/Invalidation

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-007.v1.0 — Growth 변화 Driver 분석

- prompt_id: `plv1.macro.007`
- prompt_code: `MACRO-007.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}에서 소비·고용·소득·생산·주문·주택·재정의 Level, Direction, Momentum, Surprise를 분리해 Growth 변화 원인을 찾는다.
- domain: `MACRO`
- role: `EXPAND`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_DRIVERS`
- tags: `macro`, `expand`, `state_and_drivers`
- keywords: `Growth`, `변화`, `Driver`, `분석`
- aliases: `Growth 변화 원인 분석`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Growth 변화 Driver 분석

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}에서 소비·고용·소득·생산·주문·주택·재정의 Level, Direction, Momentum, Surprise를 분리해 Growth 변화 원인을 찾는다.

출력:
1. Growth State
2. Driver별 Evidence
3. 선행/후행 관계
4. 시장 기대 차이
5. 반대 Scenario

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-008.v1.0 — Inflation 구성요소와 지속성 분석

- prompt_id: `plv1.macro.008`
- prompt_code: `MACRO-008.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}에서 Goods/Services/Housing/Wage/Commodity/Supply 요소와 Base Effect를 분리해 Inflation의 Breadth와 Persistence를 검증한다.
- domain: `MACRO`
- role: `EXPAND`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_DRIVERS`
- tags: `macro`, `expand`, `state_and_drivers`
- keywords: `Inflation`, `구성요소와`, `지속성`, `분석`
- aliases: `Inflation 구성요소 분석`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Inflation 구성요소와 지속성 분석

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}에서 Goods/Services/Housing/Wage/Commodity/Supply 요소와 Base Effect를 분리해 Inflation의 Breadth와 Persistence를 검증한다.

출력:
1. Inflation 구성
2. Momentum/Breadth
3. 지속/일시 요인
4. 정책 경로 영향
5. 재상승/둔화 Trigger

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-009.v1.0 — 시장 금리경로와 오류 가능성 검증

- prompt_id: `plv1.macro.009`
- prompt_code: `MACRO-009.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}의 정책금리·국채곡선·Real Yield·Inflation Expectation을 비교해 시장의 {{rate_path_assumption}}과 이를 틀리게 만들 Evidence를 함께 조사한다.
- domain: `MACRO`
- role: `EXPAND`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_DRIVERS`
- tags: `macro`, `expand`, `state_and_drivers`
- keywords: `시장`, `금리경로와`, `오류`, `가능성`, `검증`
- aliases: `시장이 기대하는 금리경로 조사`, `MACRO-017`, `plv1.macro.017`, `시장 금리기대가 틀릴 가능성 검증`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`, `{{rate_path_assumption}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 시장 금리경로와 오류 가능성 검증

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}의 정책금리·국채곡선·Real Yield·Inflation Expectation을 비교해 시장의 {{rate_path_assumption}}과 이를 틀리게 만들 Evidence를 함께 조사한다.

출력:
1. 시장 내재 경로
2. 정책/데이터 Evidence
3. 기대 불일치
4. 오류 Scenario
5. 재평가 Trigger

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-010.v1.0 — Liquidity 변화 Driver 조사

- prompt_id: `plv1.macro.010`
- prompt_code: `MACRO-010.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}에서 중앙은행 Balance Sheet, Treasury Cash, Bank Credit, Funding, Dollar, Cross-border Flow를 구분해 Liquidity 변화와 위험자산 전달경로를 조사한다.
- domain: `MACRO`
- role: `EXPAND`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `STATE_AND_DRIVERS`
- tags: `macro`, `expand`, `state_and_drivers`
- keywords: `Liquidity`, `변화`, `Driver`, `조사`
- aliases: `Liquidity 변화 원인 조사`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Liquidity 변화 Driver 조사

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}에서 중앙은행 Balance Sheet, Treasury Cash, Bank Credit, Funding, Dollar, Cross-border Flow를 구분해 Liquidity 변화와 위험자산 전달경로를 조사한다.

출력:
1. Liquidity 구성요소
2. 순방향/역방향 Driver
3. 전달경로
4. 시차
5. 반대 Evidence

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-011.v1.0 — Macro→산업 Transmission 분석

- prompt_id: `plv1.macro.011`
- prompt_code: `MACRO-011.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}의 Shock이 {{industry}}의 수요·가격·원가·자금조달·재고·CAPEX로 전달되는 경로와 Lag/Duration을 분석한다.
- domain: `MACRO`
- role: `EXPAND`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `TRANSMISSION_AND_RISK`
- tags: `macro`, `expand`, `transmission_and_risk`
- keywords: `Macro`, `산업`, `Transmission`, `분석`
- aliases: `Macro 변화가 산업에 전달되는 과정`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`, `{{industry}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Macro→산업 Transmission 분석

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}의 Shock이 {{industry}}의 수요·가격·원가·자금조달·재고·CAPEX로 전달되는 경로와 Lag/Duration을 분석한다.

출력:
1. Macro Shock
2. 산업 Transmission
3. Exposure/Sensitivity
4. Lag·Duration
5. 수혜/피해 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-012.v1.0 — Macro→기업 Earnings Transmission 분석

- prompt_id: `plv1.macro.012`
- prompt_code: `MACRO-012.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}의 Shock이 {{company}}({{ticker}})의 Revenue, Margin, FCF, Discount Rate에 전달되는 경로를 QGV Base와 분리해 분석한다.
- domain: `MACRO`
- role: `EXPAND`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `TRANSMISSION_AND_RISK`
- tags: `macro`, `expand`, `transmission_and_risk`
- keywords: `Macro`, `기업`, `Earnings`, `Transmission`, `분석`
- aliases: `Macro 변화가 특정 기업 실적으로 전달되는 과정`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`, `{{company}}`, `{{ticker}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Macro→기업 Earnings Transmission 분석

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}의 Shock이 {{company}}({{ticker}})의 Revenue, Margin, FCF, Discount Rate에 전달되는 경로를 QGV Base와 분리해 분석한다.

출력:
1. Shock와 기업 노출
2. Earnings Bridge
3. Exposure vs Sensitivity
4. Lag·Duration
5. 반대/완충 Evidence

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-013.v1.0 — 현재 Regime·Soft Landing·Recession Red Team

- prompt_id: `plv1.macro.013`
- prompt_code: `MACRO-013.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}과 {{scenario_assumptions}}에서 현재 Regime 및 Soft Landing/Recession 가정을 반박할 가장 강한 Evidence를 양방향으로 검증한다.
- domain: `MACRO`
- role: `CHALLENGE`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `TRANSMISSION_AND_RISK`
- tags: `macro`, `challenge`, `transmission_and_risk`
- keywords: `현재`, `Regime`, `Soft`, `Landing`, `Recession`, `Red`, `Team`
- aliases: `현재 경기국면과 반대되는 Evidence 찾기`, `MACRO-014`, `plv1.macro.014`, `Soft Landing Scenario 반박`, `MACRO-015`, `plv1.macro.015`, `Recession Scenario 반박`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`, `{{scenario_assumptions}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 현재 Regime·Soft Landing·Recession Red Team

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}과 {{scenario_assumptions}}에서 현재 Regime 및 Soft Landing/Recession 가정을 반박할 가장 강한 Evidence를 양방향으로 검증한다.

출력:
1. 기준 Scenario
2. 지지 Evidence
3. 반대 Evidence
4. 확률을 바꿀 Data
5. Invalidation

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-016.v1.0 — Inflation 재상승 위험 조사

- prompt_id: `plv1.macro.016`
- prompt_code: `MACRO-016.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}에서 Wage, Shelter, Commodity, Fiscal, Supply, FX의 재가속 경로와 시장 기대에 아직 반영되지 않은 Trigger를 찾는다.
- domain: `MACRO`
- role: `CHALLENGE`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `TRANSMISSION_AND_RISK`
- tags: `macro`, `challenge`, `transmission_and_risk`
- keywords: `Inflation`, `재상승`, `위험`, `조사`
- aliases: `Inflation 재상승 위험 조사`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Inflation 재상승 위험 조사

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}에서 Wage, Shelter, Commodity, Fiscal, Supply, FX의 재가속 경로와 시장 기대에 아직 반영되지 않은 Trigger를 찾는다.

출력:
1. 재상승 경로
2. 선행 Evidence
3. 시장 기대 차이
4. Rates/기업 영향
5. 무효화 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-018.v1.0 — 공식지표 이전의 현장·Delta Evidence 찾기

- prompt_id: `plv1.macro.018`
- prompt_code: `MACRO-018.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}} 이후 {{prior_cutoff}}부터 새로 나온 기업 Commentary, 가격·수요, 물류, 채용, Survey 등 고빈도 Evidence를 찾되 대표성 한계를 표시한다.
- domain: `MACRO`
- role: `BLIND-SPOT`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `TRANSMISSION_AND_RISK`
- tags: `macro`, `blind-spot`, `transmission_and_risk`
- keywords: `공식지표`, `이전의`, `현장`, `Delta`, `Evidence`, `찾기`
- aliases: `공식 경제지표에 아직 나타나지 않은 변화`, `MACRO-019`, `plv1.macro.019`, `기업 현장의 가격·수요 변화 조사`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`, `{{prior_cutoff}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 공식지표 이전의 현장·Delta Evidence 찾기

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}} 이후 {{prior_cutoff}}부터 새로 나온 기업 Commentary, 가격·수요, 물류, 채용, Survey 등 고빈도 Evidence를 찾되 대표성 한계를 표시한다.

출력:
1. Delta Evidence
2. 공식지표와 차이
3. 대표성/편향
4. Macro 축 영향
5. 확인할 공식 Release

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-020.v1.0 — 해외발 미국시장 위험 조사

- prompt_id: `plv1.macro.020`
- prompt_code: `MACRO-020.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}에 없는 해외 Growth, FX, Commodity, Geopolitics, Trade, Funding Shock이 미국 산업·시장으로 전염되는 경로를 조사한다.
- domain: `MACRO`
- role: `BLIND-SPOT`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `TRANSMISSION_AND_RISK`
- tags: `macro`, `blind-spot`, `transmission_and_risk`
- keywords: `해외발`, `미국시장`, `위험`, `조사`
- aliases: `해외에서 발생하는 미국시장 위험 찾기`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 해외발 미국시장 위험 조사

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}에 없는 해외 Growth, FX, Commodity, Geopolitics, Trade, Funding Shock이 미국 산업·시장으로 전염되는 경로를 조사한다.

출력:
1. 해외 Shock
2. 미국 전달경로
3. 노출 산업/기업
4. 시차/완충
5. Tail 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-021.v1.0 — 정책 변화의 2차 효과 조사

- prompt_id: `plv1.macro.021`
- prompt_code: `MACRO-021.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}과 {{policy_change}}에서 1차 수혜·피해를 넘어 행동 변화, 대체, 재정비용, 공급반응, 규제 Arbitrage 같은 2차 효과를 추적한다.
- domain: `MACRO`
- role: `BLIND-SPOT`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `TRANSMISSION_AND_RISK`
- tags: `macro`, `blind-spot`, `transmission_and_risk`
- keywords: `정책`, `변화의`, `2차`, `효과`, `조사`
- aliases: `정책 변화의 2차 효과 찾기`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`, `{{policy_change}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 정책 변화의 2차 효과 조사

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}과 {{policy_change}}에서 1차 수혜·피해를 넘어 행동 변화, 대체, 재정비용, 공급반응, 규제 Arbitrage 같은 2차 효과를 추적한다.

출력:
1. 정책 변화
2. 1차 효과
3. 2차 Feedback
4. 의도치 않은 결과
5. 확인 지표

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### MACRO-022.v1.0 — 시장이 무시하는 Tail Risk 찾기

- prompt_id: `plv1.macro.022`
- prompt_code: `MACRO-022.v1.0`
- status: `ACTIVE`
- purpose: {{macro_input}}의 Base Scenario 밖에서 발생가능성은 낮지만 손실경로가 큰 Credit, Liquidity, Policy, Geopolitical, Correlation Breakdown 위험을 찾는다.
- domain: `MACRO`
- role: `BLIND-SPOT`
- category: `MACRO_EVIDENCE_EXTENSION`
- subcategory: `TRANSMISSION_AND_RISK`
- tags: `macro`, `blind-spot`, `transmission_and_risk`
- keywords: `시장이`, `무시하는`, `Tail`, `Risk`, `찾기`
- aliases: `시장이 무시하고 있는 Tail Risk 찾기`
- variables: `{{input_mode}}`, `{{market}}`, `{{horizon}}`, `{{as_of}}`, `{{macro_input}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 시장이 무시하는 Tail Risk 찾기

분석 시장은 `{{market}}`, Horizon은 `{{horizon}}`다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
입력 모드 `{{input_mode}}`를 먼저 확인해. SYSTEM_CONTEXT이면 `{{macro_input}}`의 기존 MacroSnapshot, State/Regime을 재계산하거나 덮어쓰지 말고 Delta Evidence와 Divergence만 조사해. STANDALONE이면 `{{macro_input}}`에 {{market}}·{{horizon}}에 필요한 PIT release/vintage/market-implied data와 출처가 있어야 한다. 필요한 데이터가 없으면 `INSUFFICIENT_DATA`로 종료해.

조사 초점: {{macro_input}}의 Base Scenario 밖에서 발생가능성은 낮지만 손실경로가 큰 Credit, Liquidity, Policy, Geopolitical, Correlation Breakdown 위험을 찾는다.

출력:
1. Tail Event
2. 전염경로
3. 취약 Exposure
4. 조기경보
5. 확률 미부여/한계

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### CROSS-001.v1.0 — Fundamental↔가격 Divergence 통합 검증

- prompt_id: `plv1.cross.001`
- prompt_code: `CROSS-001.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{system_summary}}에서 Fundamental과 가격 방향이 다른 이유, 가격의 선반영, 좋은 기업의 약한 가격·약한 기업의 강한 가격을 하나의 방향 변수로 검증한다.
- domain: `CROSS_VALIDATION`
- role: `EXPAND`
- category: `CROSS_SYSTEM_VALIDATION`
- subcategory: `DIVERGENCE`
- tags: `cross_validation`, `expand`, `divergence`
- keywords: `Fundamental`, `가격`, `Divergence`, `통합`, `검증`
- aliases: `좋은 기업인데 주가가 약한 이유`, `TECH-024`, `plv1.tech.024`, `가격이 Fundamental 변화를 선반영하는지 조사`, `CROSS-002`, `plv1.cross.002`, `기업은 약한데 주가가 강한 이유`, `CROSS-003`, `plv1.cross.003`, `가격이 Fundamental 변화를 선반영하는지 검증`
- variables: `{{company}}`, `{{ticker}}`, `{{system_summary}}`, `{{as_of}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Fundamental↔가격 Divergence 통합 검증

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
현재 Investment System 요약은 `{{system_summary}}`다. 이 요약과 QGV/Technical/Macro 결과를 다시 계산하거나 새 통합점수를 만들지 말고 충돌, 누락, Delta Evidence를 조사해.

조사 초점: {{company}}({{ticker}})의 {{system_summary}}에서 Fundamental과 가격 방향이 다른 이유, 가격의 선반영, 좋은 기업의 약한 가격·약한 기업의 강한 가격을 하나의 방향 변수로 검증한다.

출력:
1. Divergence 방향
2. 시간순 Evidence
3. 가능한 Catalyst
4. 선반영/오판 구분
5. 해소·Invalidation 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### CROSS-004.v1.0 — Fundamental↔Macro Divergence·Transmission 검증

- prompt_id: `plv1.cross.004`
- prompt_code: `CROSS-004.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{system_summary}}에서 좋은 기업-위험 Macro, Macro 수혜-약한 기업, Macro→Earnings 전달 실패를 구분한다.
- domain: `CROSS_VALIDATION`
- role: `EXPAND`
- category: `CROSS_SYSTEM_VALIDATION`
- subcategory: `DIVERGENCE`
- tags: `cross_validation`, `expand`, `divergence`
- keywords: `Fundamental`, `Macro`, `Divergence`, `Transmission`, `검증`
- aliases: `좋은 기업인데 Macro가 위험한 이유`, `CROSS-005`, `plv1.cross.005`, `Macro 수혜환경인데 기업이 약한 이유`, `CROSS-006`, `plv1.cross.006`, `Macro 변화가 실제 Earnings로 전달되는지 검증`
- variables: `{{company}}`, `{{ticker}}`, `{{system_summary}}`, `{{as_of}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Fundamental↔Macro Divergence·Transmission 검증

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
현재 Investment System 요약은 `{{system_summary}}`다. 이 요약과 QGV/Technical/Macro 결과를 다시 계산하거나 새 통합점수를 만들지 말고 충돌, 누락, Delta Evidence를 조사해.

조사 초점: {{company}}({{ticker}})의 {{system_summary}}에서 좋은 기업-위험 Macro, Macro 수혜-약한 기업, Macro→Earnings 전달 실패를 구분한다.

출력:
1. Fundamental/Macro State
2. Transmission Path
3. Exposure/Sensitivity
4. Lag/누락 연결
5. 판단 변경 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### CROSS-007.v1.0 — Technical↔Macro Divergence·선반영 검증

- prompt_id: `plv1.cross.007`
- prompt_code: `CROSS-007.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{system_summary}}에서 Macro와 가격 방향 불일치, 시장의 Macro 전환 선반영, 기업 고유 가격요인을 구분한다.
- domain: `CROSS_VALIDATION`
- role: `EXPAND`
- category: `CROSS_SYSTEM_VALIDATION`
- subcategory: `DIVERGENCE`
- tags: `cross_validation`, `expand`, `divergence`
- keywords: `Technical`, `Macro`, `Divergence`, `선반영`, `검증`
- aliases: `Macro는 좋은데 시장가격이 약한 이유`, `CROSS-008`, `plv1.cross.008`, `가격은 강한데 Macro가 악화되는 이유`, `CROSS-009`, `plv1.cross.009`, `시장이 Macro 전환을 선반영하는지 검증`
- variables: `{{company}}`, `{{ticker}}`, `{{system_summary}}`, `{{as_of}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Technical↔Macro Divergence·선반영 검증

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
현재 Investment System 요약은 `{{system_summary}}`다. 이 요약과 QGV/Technical/Macro 결과를 다시 계산하거나 새 통합점수를 만들지 말고 충돌, 누락, Delta Evidence를 조사해.

조사 초점: {{company}}({{ticker}})의 {{system_summary}}에서 Macro와 가격 방향 불일치, 시장의 Macro 전환 선반영, 기업 고유 가격요인을 구분한다.

출력:
1. Technical/Macro State
2. Divergence 기간
3. 선반영 Evidence
4. 기업 고유 잔차
5. 해소 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### CROSS-010.v1.0 — 세 분석 Consensus의 숨은 위험·과도한 비관 검증

- prompt_id: `plv1.cross.010`
- prompt_code: `CROSS-010.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{system_summary}}에서 QGV/Technical/Macro가 모두 같은 방향일 때 Groupthink, 공통 데이터 오류, 누락 변수와 과도한 비관을 양방향 검증한다.
- domain: `CROSS_VALIDATION`
- role: `CHALLENGE`
- category: `CROSS_SYSTEM_VALIDATION`
- subcategory: `DIVERGENCE`
- tags: `cross_validation`, `challenge`, `divergence`
- keywords: `세`, `분석`, `Consensus의`, `숨은`, `위험`, `과도한`, `비관`, `검증`
- aliases: `세 분석이 모두 긍정일 때 놓친 위험`, `CROSS-011`, `plv1.cross.011`, `세 분석이 모두 부정일 때 과도한 비관 여부`
- variables: `{{company}}`, `{{ticker}}`, `{{system_summary}}`, `{{as_of}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 세 분석 Consensus의 숨은 위험·과도한 비관 검증

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
현재 Investment System 요약은 `{{system_summary}}`다. 이 요약과 QGV/Technical/Macro 결과를 다시 계산하거나 새 통합점수를 만들지 말고 충돌, 누락, Delta Evidence를 조사해.

조사 초점: {{company}}({{ticker}})의 {{system_summary}}에서 QGV/Technical/Macro가 모두 같은 방향일 때 Groupthink, 공통 데이터 오류, 누락 변수와 과도한 비관을 양방향 검증한다.

출력:
1. Consensus 방향
2. 공통 전제
3. 숨은 위험/기회
4. 독립 Evidence
5. Consensus 붕괴 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### CROSS-012.v1.0 — 가장 약한 Evidence와 Horizon 충돌 찾기

- prompt_id: `plv1.cross.012`
- prompt_code: `CROSS-012.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{system_summary}}에서 가장 약한 Evidence와 Fundamental·Technical·Macro의 서로 다른 Horizon이 만든 가짜 충돌을 구분한다.
- domain: `CROSS_VALIDATION`
- role: `CHALLENGE`
- category: `CROSS_SYSTEM_VALIDATION`
- subcategory: `RED_TEAM_AND_BLIND_SPOT`
- tags: `cross_validation`, `challenge`, `red_team_and_blind_spot`
- keywords: `가장`, `약한`, `Evidence와`, `Horizon`, `충돌`, `찾기`
- aliases: `세 분석 중 가장 약한 Evidence 찾기`
- variables: `{{company}}`, `{{ticker}}`, `{{system_summary}}`, `{{as_of}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 가장 약한 Evidence와 Horizon 충돌 찾기

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
현재 Investment System 요약은 `{{system_summary}}`다. 이 요약과 QGV/Technical/Macro 결과를 다시 계산하거나 새 통합점수를 만들지 말고 충돌, 누락, Delta Evidence를 조사해.

조사 초점: {{company}}({{ticker}})의 {{system_summary}}에서 가장 약한 Evidence와 Fundamental·Technical·Macro의 서로 다른 Horizon이 만든 가짜 충돌을 구분한다.

출력:
1. 레이어별 Horizon
2. Evidence 강도
3. 실제/가짜 충돌
4. 가장 취약한 연결
5. 재검증 우선순위

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### CROSS-013.v1.0 — Investment System 판단·Thesis·Source Red Team

- prompt_id: `plv1.cross.013`
- prompt_code: `CROSS-013.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{system_summary}}를 요약하지 말고 결론을 바꿀 Evidence와 Source/Citation 무결성을 감사한다. 1차/2차 출처, 날짜, 원문 일치 여부를 확인한다.
- domain: `CROSS_VALIDATION`
- role: `CHALLENGE`
- category: `CROSS_SYSTEM_VALIDATION`
- subcategory: `RED_TEAM_AND_BLIND_SPOT`
- tags: `cross_validation`, `challenge`, `red_team_and_blind_spot`
- keywords: `Investment`, `System`, `판단`, `Thesis`, `Source`, `Red`, `Team`
- aliases: `Investment System 판단과 충돌하는 Evidence 찾기`, `CROSS-017`, `plv1.cross.017`, `현재 Investment Thesis Red Team`
- variables: `{{company}}`, `{{ticker}}`, `{{system_summary}}`, `{{as_of}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: Investment System 판단·Thesis·Source Red Team

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
현재 Investment System 요약은 `{{system_summary}}`다. 이 요약과 QGV/Technical/Macro 결과를 다시 계산하거나 새 통합점수를 만들지 말고 충돌, 누락, Delta Evidence를 조사해.

조사 초점: {{company}}({{ticker}})의 {{system_summary}}를 요약하지 말고 결론을 바꿀 Evidence와 Source/Citation 무결성을 감사한다. 1차/2차 출처, 날짜, 원문 일치 여부를 확인한다.

출력:
1. 검증 대상 Claim
2. Source Integrity
3. 반대 Evidence
4. Thesis 취약점
5. 결론 변경 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### CROSS-014.v1.0 — 빠진 변수와 다음 Research 질문 찾기

- prompt_id: `plv1.cross.014`
- prompt_code: `CROSS-014.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{system_summary}}와 {{snapshot_refs}}에서 Coverage Gap, 확인되지 않은 가정, 비정형 Evidence를 찾아 가장 가치 높은 다음 질문으로 우선순위화한다.
- domain: `CROSS_VALIDATION`
- role: `BLIND-SPOT`
- category: `CROSS_SYSTEM_VALIDATION`
- subcategory: `RED_TEAM_AND_BLIND_SPOT`
- tags: `cross_validation`, `blind-spot`, `red_team_and_blind_spot`
- keywords: `빠진`, `변수와`, `다음`, `Research`, `질문`, `찾기`
- aliases: `현재 분석에서 빠진 변수 찾기`, `CROSS-018`, `plv1.cross.018`, `지금 가장 먼저 추가 조사해야 할 질문 찾기`
- variables: `{{company}}`, `{{ticker}}`, `{{system_summary}}`, `{{as_of}}`, `{{snapshot_refs}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 빠진 변수와 다음 Research 질문 찾기

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
현재 Investment System 요약은 `{{system_summary}}`다. 이 요약과 QGV/Technical/Macro 결과를 다시 계산하거나 새 통합점수를 만들지 말고 충돌, 누락, Delta Evidence를 조사해.

조사 초점: {{company}}({{ticker}})의 {{system_summary}}와 {{snapshot_refs}}에서 Coverage Gap, 확인되지 않은 가정, 비정형 Evidence를 찾아 가장 가치 높은 다음 질문으로 우선순위화한다.

출력:
1. 누락 변수
2. 왜 중요한지
3. 필요 Evidence
4. 우선순위
5. 다음 Research 질문

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### CROSS-015.v1.0 — 이전 cutoff 이후 Delta Evidence 찾기

- prompt_id: `plv1.cross.015`
- prompt_code: `CROSS-015.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{system_summary}} 이후 {{prior_cutoff}}부터 {{as_of}}까지 새로 공개된 정보만 조사하고 기존 정보의 반복을 제외한다.
- domain: `CROSS_VALIDATION`
- role: `BLIND-SPOT`
- category: `CROSS_SYSTEM_VALIDATION`
- subcategory: `RED_TEAM_AND_BLIND_SPOT`
- tags: `cross_validation`, `blind-spot`, `red_team_and_blind_spot`
- keywords: `이전`, `cutoff`, `이후`, `Delta`, `Evidence`, `찾기`
- aliases: `최근 정보 중 시스템 판단을 바꿀 수 있는 것 찾기`
- variables: `{{company}}`, `{{ticker}}`, `{{system_summary}}`, `{{as_of}}`, `{{prior_cutoff}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 이전 cutoff 이후 Delta Evidence 찾기

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
현재 Investment System 요약은 `{{system_summary}}`다. 이 요약과 QGV/Technical/Macro 결과를 다시 계산하거나 새 통합점수를 만들지 말고 충돌, 누락, Delta Evidence를 조사해.

조사 초점: {{company}}({{ticker}})의 {{system_summary}} 이후 {{prior_cutoff}}부터 {{as_of}}까지 새로 공개된 정보만 조사하고 기존 정보의 반복을 제외한다.

출력:
1. 새 Event/Claim
2. 이전 분석 대비 Delta
3. 시스템 레이어 영향
4. Evidence 강도
5. Snapshot 재검토 필요 여부

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

### CROSS-016.v1.0 — 시장과 시스템 판단 차이의 원인 찾기

- prompt_id: `plv1.cross.016`
- prompt_code: `CROSS-016.v1.0`
- status: `ACTIVE`
- purpose: {{company}}({{ticker}})의 {{system_summary}}와 시장가격·Consensus가 다른 이유를 정보차이, Horizon, Positioning, Liquidity, Risk Premium, 모델 누락으로 분해한다.
- domain: `CROSS_VALIDATION`
- role: `BLIND-SPOT`
- category: `CROSS_SYSTEM_VALIDATION`
- subcategory: `RED_TEAM_AND_BLIND_SPOT`
- tags: `cross_validation`, `blind-spot`, `red_team_and_blind_spot`
- keywords: `시장과`, `시스템`, `판단`, `차이의`, `원인`, `찾기`
- aliases: `시장이 시스템과 다르게 판단하는 이유 찾기`
- variables: `{{company}}`, `{{ticker}}`, `{{system_summary}}`, `{{as_of}}`
- system_overlap: `HIGH_CONTROLLED`

```text
목적: 시장과 시스템 판단 차이의 원인 찾기

분석 대상은 `{{company}}`(`{{ticker}}`)다. 정보 cutoff는 `{{as_of}}`다. `{{as_of}}` 시점에 공개·이용 가능했던 정보만 사용해.
현재 Investment System 요약은 `{{system_summary}}`다. 이 요약과 QGV/Technical/Macro 결과를 다시 계산하거나 새 통합점수를 만들지 말고 충돌, 누락, Delta Evidence를 조사해.

조사 초점: {{company}}({{ticker}})의 {{system_summary}}와 시장가격·Consensus가 다른 이유를 정보차이, Horizon, Positioning, Liquidity, Risk Premium, 모델 누락으로 분해한다.

출력:
1. 시스템 판단
2. 시장 내재 판단
3. 차이의 원인
4. 누가 틀렸는지 확인할 Evidence
5. 수렴/확대 조건

Evidence 규칙:
- 핵심 Claim마다 Source, 공개일/시간, 해당 정보가 이용 가능해진 시점, 원문 근거를 표시해.
- Fact / Interpretation / Estimate / Scenario를 분리하고 Source 간 충돌은 양쪽을 보존해.
- 확인할 수 없는 수치·관계·가격·지표·확률은 만들지 말고 `UNKNOWN` 또는 `INSUFFICIENT_DATA`로 표시해.
- 기존 Investment System의 정형 분석을 외부 AI가 그대로 다시 계산하지 마.
- BUY/SELL/HOLD나 최종 투자결정을 대신하지 말고 다음 Research 조건과 판단 변경 조건만 제시해.
```

