# 프롬프트 변수의 뜻과 자료 준비

변수 안내는 Frozen 프롬프트 70개의 본문에 선언된 34개 입력을 설명합니다.
회사·종목·조사 범위는 직접 정하고, 기존 시스템 자료는 실제 보유한 결과에서
복사합니다. 안내 예시는 입력칸의 placeholder이며 실제 값으로 자동 입력하지 않습니다.
회사·시장·산업·테마·날짜는 구체적인 입력 예시를 보여주되 시세·수량·점수·확률을
예시 값으로 만들지 않습니다. 날짜가 있는 뉴스 사건은 가상 예시이며 실제 발표 근거가 아닙니다.

기준은 [Frozen 본문](../../src/investment_system/prompt_library/content/Investment_Prompt_Library_v1_Content_Catalog_FROZEN.md)의
`PLV1_CONTENT_V1.0`입니다. 한국어·영어 안내는
[fill.py의 VARIABLE_GUIDES](../../src/investment_system/prompt_library/fill.py)에 별도 기록하며,
Frozen 본문·변수명·필수 여부·종류·시스템 소유권·검증 규칙은 유지합니다.

## 입력할 때 지킬 규칙

- 선택한 프롬프트에 선언된 변수만 입력합니다. `qgv_snapshot_summary`만 선택이며
  비우면 기존 규칙에 따라 `NOT_PROVIDED`가 됩니다. 나머지 선언된 변수는 필수입니다.
- `as_of`는 해당 시점까지 공개·이용 가능했던 정보의 기준일입니다. ISO 날짜 또는
  시간대가 있는 ISO 시각을 사용하고 미래 시점을 넣지 않습니다. `prior_cutoff`는 그보다 앞서야 합니다.
- `candidate_count`는 양의 정수인 후보 수 상한입니다. 후보를 그 수만큼 만들어 채우라는 뜻이 아닙니다.
- `SYSTEM_CONTEXT`는 기존 결과를 재계산하지 않고 읽는 방식입니다. `STANDALONE`도
  질문만으로 충분하지 않습니다. 기술 분석은 실제 PIT OHLCV·조정 기준·시간대·기업행사·출처,
  거시 분석은 실제 발표·빈티지·시장 내재 자료와 출처가 필요합니다. 필요한 자료가 없으면
  Frozen 본문의 `INSUFFICIENT_DATA` 규칙을 따릅니다.
- `options_positioning_data`는 선택 변수가 아닙니다. 자료가 없으면 빈칸 대신
  `NOT_AVAILABLE · 옵션 자료 없음`처럼 미제공 사실을 직접 적습니다. 이 문구가 검증을 통과해도
  실제 자료가 생긴 것은 아니며 옵션·포지셔닝 결론을 만들어서는 안 됩니다.
- 기존 자료가 미제공인 상태와 확인된 빈 결과를 구분합니다. 기준일·출처·원문을
  함께 확인하고 근거 없는 점수·지표·확률·Snapshot ID를 채우지 않습니다.

## 대상과 조사 범위

| 변수 | 뜻과 준비할 내용 | 본문에서 확인한 용도 |
| --- | --- | --- |
| `as_of` | 정보 기준일. 해당 시점까지 공개·이용 가능했던 자료만 허용 | 전체 70개 공통 정보 cutoff |
| `prior_cutoff` | 이전 분석 기준일. 이번 기준일보다 앞선 비교 시작점 | MACRO-018, CROSS-015의 새 근거·Delta 비교 |
| `company` | 분석 대상 회사 이름. `ticker`와 같은 회사여야 함 | FUND, MACRO-012, CROSS의 분석 대상 |
| `ticker` | 분석 대상 상장 종목 코드. 필요한 거래소도 확인 | FUND, TECH, MACRO-012, CROSS의 대상 식별 |
| `seed_company` | 경쟁 생태계·공급업체·고객사 탐색을 시작할 회사 | IDEA-012, IDEA-013의 출발 기업 |
| `seed_ticker` | 탐색 출발 회사의 상장 종목 코드 | IDEA-012, IDEA-013의 출발 기업 식별 |
| `universe` | 후보를 찾을 국가·시장·종목 집합과 선정 기준·기준일 | Discovery 13개의 탐색 범위 |
| `candidate_count` | 출력할 Research Candidate 수의 상한 | Discovery 공통 “최대 후보 수” |
| `market` | 거시 변화·전달 경로를 조사할 시장 | Macro 13개의 분석 시장 |
| `horizon` | 거시 시나리오·영향을 검토할 기간 | Macro 13개에만 선언; 차트 과거 자료 기간과 구분 |
| `period` | 기술 분석에 제공할 가격·거래량 자료의 기간 | Technical 14개의 분석 기간 |
| `industry` | 후보 탐색·거시 영향 분석의 대상 산업과 세부 범위 | IDEA-009, MACRO-011 |
| `theme` | 직접 및 2·3차 수혜 경로를 조사할 테마 | IDEA-011 |
| `industry_or_theme` | 가치사슬 전체를 조사할 산업 또는 테마 | IDEA-010 |
| `benchmark_or_peers` | 비교 지수·기업 및 같은 기준의 실제 가격 자료 | TECH-009, TECH-020, TECH-021; 기간·통화·기업행사 기준 정렬 |
| `earnings_period` | 회사의 실적 검토 회계연도·분기 | FUND-004의 전년·전분기·기대치 비교 |
| `macro_driver` | 수혜 후보를 찾을 거시 변화와 조건 | IDEA-018의 직접·2차 수혜 경로 |
| `policy_change` | 2차 효과를 조사할 실제 정책 변화·시점·출처 | MACRO-021의 행동 변화·대체·공급 반응 |
| `rate_path_assumption` | 검증할 시장 내재 금리경로 가정·기준 시점·근거 | MACRO-009의 금리경로와 이를 틀리게 할 근거 |
| `scenario_assumptions` | 반박할 기존 거시 시나리오의 전제·근거 | MACRO-013의 연착륙·침체 가정 양방향 검증 |
| `reverse_dcf_assumptions` | 기존 성장·마진·재투자·할인율 등 검증할 가정 | FUND-015의 현실 근거 대조; 새로운 가치평가 계산 요청 아님 |
| `customer_evidence_scope` | 조사할 고객군·제품·기간·자료 유형의 범위 | FUND-023의 고객 반응 조사 범위; 확인된 조사 결과 자체가 아님 |
| `news_event_evidence` | 가격 변화와 비교할 실제 뉴스·이벤트 원문과 공개·이용 가능 시점 | TECH-019, TECH-022의 시간 선후관계·뉴스/가격 불일치 |
| `options_positioning_data` | 실제 옵션·포지셔닝 자료와 시점·출처 또는 자료 미제공 사실 | TECH-023; IV·Skew·Open Interest, Dealer/Flow 추정과 사실 분리 |
| `input_mode` | 사용자가 선택할 `SYSTEM_CONTEXT` 또는 `STANDALONE` | Technical 14개·Macro 13개; 선택만으로 자동 자료 제공 없음 |

## 기존 시스템 자료

아래 9개 변수의 소유권은 기존 [catalog.py의 SYSTEM_INPUT_VARIABLES](../../src/investment_system/prompt_library/catalog.py)를
그대로 따릅니다. 화면이 준비 중이면 거기에 자료가 있다고 가정하지 않습니다.
이미 저장된 실제 결과가 있을 때만 복사하며, 안내의 자료 위치는 자동 연결을 뜻하지 않습니다.
자료 위치는 종목 화면의 QGV 카드, 리더보드, 기술, 매크로, 오늘 화면의 통합 판단,
오늘·검증 화면의 통합 분석 범위 기록과 실제 판단이 참조한 각 화면의 Snapshot입니다.
준비 화면이나 자료 미제공 상태에서는 그 사실을 명시합니다. 통합 판단·분석 범위·참조가
없을 때 개별 QGV 범위나 임의 Snapshot ID를 조합해 통합 결과로 만들지 않습니다.
`input_mode`는 시스템 자료 입력과 함께 보여줄 수 있지만 사용자가 선택하는 값이며
새 시스템 소유권을 부여하지 않습니다.

| 변수 | 기존 owner | 가져올 자료·의미 | 본문 근거 |
| --- | --- | --- | --- |
| `qgv_snapshot_summary` | QGV | 기존 QGV 판단·근거·기준 시점. 선택 입력, 독자 Q/G/V 점수 생성 금지 | Fundamental 21개 공통 |
| `existing_system_candidates` | QGV_LEADERBOARD | 기존 후보 목록·선정 근거·기준일. 새 비정형 근거가 있을 때만 기존 후보 반복 | Discovery 13개 공통 |
| `technical_input` | TECHNICAL | 기존 TechnicalSnapshot·계산 결과 또는 STANDALONE에 필요한 실제 PIT 원자료 | Technical 14개 공통 |
| `technical_screen_summary` | TECHNICAL | 여러 종목의 기존 기술 스크리닝·상태 변화 요약 | IDEA-014 |
| `macro_input` | MACRO | 기존 MacroSnapshot·State·Regime 또는 STANDALONE용 실제 발표·빈티지·시장 내재 자료 | Macro 13개 공통 |
| `macro_snapshot_summary` | MACRO | 거시 변화 수혜 후보를 조사할 기존 거시 판단 요약 | IDEA-018 |
| `system_summary` | INTEGRATED | 기존 QGV·기술·거시 통합 판단과 근거. 원본 재계산·새 통합점수 금지 | IDEA-019, CROSS 9개 |
| `system_coverage_summary` | INTEGRATED | 기존 분석 대상·항목과 빠진 범위 기록. 새 완료율 계산 금지 | IDEA-020 |
| `snapshot_refs` | INTEGRATED | 실제 판단이 참조한 Snapshot의 ID·기준일·출처·버전 | CROSS-014 |

## 사용자 초안에서 보완한 의미

| 항목 | 보완한 안내 | Frozen 근거 |
| --- | --- | --- |
| `input_mode` | STANDALONE은 “시스템 결과 없이 질문만 보내기”가 아니라 실제 PIT 원자료를 직접 제공하는 방식 | TECH-001 등 Technical 공통, MACRO-001 등 Macro 공통 |
| `options_positioning_data` | 자료가 없으면 “비워두기” 대신 미제공 사실을 필수 텍스트로 명시; 결론을 만들지 않음 | TECH-023 및 기존 fill.py의 유일한 optional 규칙 |
| `benchmark_or_peers` | 지수·경쟁사 이름뿐 아니라 실제 비교 자료·기간·통화·기업행사 기준까지 확인 | TECH-009, TECH-020, TECH-021 |
| `reverse_dcf_assumptions` | 기존 가정 검증임을 명시하고 본문의 재투자 항목 포함; 새 역 DCF 결과 생성으로 해석하지 않음 | FUND-015 |
| `scenario_assumptions` | 초안의 예시 확률을 자동 입력하지 않고 기존 전제·근거를 안내; 근거 없는 확률 생성 금지 | MACRO-013의 양방향 근거 검증 및 공통 Evidence 규칙 |
| 시스템 자료의 위치 | “종목 카드·기술·거시·오늘 화면에서 가져오기”를 현재 데이터 제공 완료로 표현하지 않음 | 본문의 기존 결과 소비 경계; 안내는 자동 연결 아님 |

`candidate_count`의 최대 개수, `customer_evidence_scope`의 조사 범위,
`seed_company`/`seed_ticker`의 탐색 출발 기업이라는 초안 의미는 본문과 일치합니다.
`horizon`은 전체 70개 중 Macro 13개에만 쓰이며 거시 판단 기간이라는 초안 의미를 유지합니다.

## 확인 범위

Discovery 13개·Fundamental 21개·Technical 14개·Macro 13개·Cross 9개의 Frozen 본문을
모두 읽어 안내를 대조했습니다. 예시는 자료가 실제로 제공되었다는 증거가 아니며
미리보기·복사·필수 입력·날짜·입력 모드·후보 수 검증은 기존 규칙을 유지합니다.
