# 일반 연구 선정·비중의 Lab 인수 입력

#473의 `validation.vertical_slice`와 #485 판독기 계약을 재사용한다. 엔진·공식 산식 변경 없음.
생산자 계산 기준 f14262a6a9f1583e81c53f642c4384141f2bb1af, 소비자 #485 edcff4a5505d2b7bbe16c296573b31a14657b509.
기존 137개 전부/N20/%10 시험은 반복하지 않았다. 새 공개 합성 인수 파일만 추가했다.

`implementation/tests/fixtures/research_selection_handoff_v1_synthetic.json`의 cases[].expected는
기존 `researchScope.validateSelection` 입력이다. 정상·빈 결과·동점·상위% 경계 위/아래·종목 부족·부분결측 7사례.
각 경우 기존 rank_cross_section→select_provisional→to_portfolio를 실행하고 저장 설정을 다시 적용한 selected가 같은지 대사했다.
원래 population/분모/랭킹, 선택 사유, 입력·저장 설정 SHA, 실행한 엔진 소스 SHA를 sidecar로 제공한다.
이 SHA는 fixture provenance이며 기존 엔진 cache_key라고 부르지 않는다. outcomes/성과는 만들지 않았다.

기존 규칙:
- 적격: Q와 G 존재. V 결손 허용. 정책 지정 시 수치 유한성 검사.
- 기본 미지정은 legacy 순서·전부. 명시 정책은 Q/G/V 내림차순, 동점 company_id 오름차순.
- all 전부, top_n min(적격,N), top_percent floor(적격×Decimal(str(percent))/100).
- 빈 선정은 portfolio/weights null, 실제 0종목. 부족종목은 임의 보충하지 않는다.
- 일반 연구는 균등 비중·기본 cash0, 별도 종목 상한 없음. TARGET/N10/N15/N20·책 고정 규칙과 별도다.
- 입력 키 company_id는 기존 발행사/기업 집합이어야 한다. 서로 다른 증권 코드가 같은 발행사인지 이 엔진이 발견하지 않는다.
  복수 코드의 발행사 집계·대표 증권·상한 규칙이 없는 입력은 완료로 표시하지 않는다. 합성 해당 사례는 POLICY_INPUT_REQUIRED/미실행으로 둔다.

## 새 소비자 차이 — Main 수정

3개 적격, top_percent=33.3333334: 생산자는 1개, 판독기는 `SELECTED_COUNT_MISMATCH`로 거부한다.
`Math.round(value*1e6)`가 저장 설정의 소수 정밀도를 바꾸기 때문이다. 바로 아래 33.3333333은 양쪽0개다.
7사례 중6수락·1거부. Node 판독 직접 실행이며 브라우저 통합 확인이 아니다.
수정 위치: #485 `product/web_app/research-scope.js` validateSelection의 expect 계산.
Main은 숫자를 임의 반올림하지 말고, 생산자가 지원하는 Decimal(str(percent))의 floor 의미와 맞춰야 한다.
이 수정 때문에 Codex 선정 규칙이나 저장 설정을 축소하지 않는다. 동일 fixture로 소비자 수정본만 재검증한다.
현재 #522 11bdab57에는 해당 판독기 파일이 없어 이 결과를 통합 화면의 실행 완료로 간주하지 않는다.

재현: fixture.cases[].expected를 require('research-scope.js').validateSelection에 전달한다.
기존 시험 진입점: `implementation/tests/test_vertical_slice.py`, `test_vertical_slice_from_store.py`.
새 엔진 결함은 확인되지 않았으므로 엔진 코드/성공 회귀시험/공식 포트폴리오를 변경·반복하지 않는다.

## Main 6721478474 회신 반영 — 실제 API 부가 계약

`run_vertical_slice` / `run_vertical_slice_from_store` / walk-forward의 각 step에
`selection_details: research-selection-details/1`을 제공한다. 기존 5개 판독 필드와 선정·비중은 그대로다.
새 helper는 순위/선정/비중을 계산하지 않고 이미 나온 결과를 설명한다.

- original_population: 실제 요청한 기업 ID·분모와 원래 universe/가용시각/source_vintage.
- rows: Q_MISSING, G_MISSING, OUTSIDE_SELECTION_LIMIT; 원래 순위·선정 여부·발행사 ID(선언된 CIK).
- portfolio: 기존 weights/cash_weight/weight_sum, 0종목은 NOT_FORMED/cash null. 전액 현금으로 새 포트폴리오를 만들지 않는다.
- issuers: 미연결 ID·동일 발행사 그룹. 기존 규칙에는 발행사 통합/상한이 없어 별도 회사 ID를 유지하고 그 상태를 명시한다.
  이 결과는 증권 신원·대표 증권 확인이 아니다. 추가 발행사 상한/집계 규칙이 필요할 때만 별도 결정한다.
- reproduction: 설정·원래 선택 입력·결과 hash 및 실제 엔진/비중/부가 계약 소스 SHA256.
  원래 Q/G 축 입력에서의 선정/비중 재현이며 QGV·PIT·성과 재현이 아니다.
  QGV 계산 버전이 원결과에 없으면 null/NOT_SUPPLIED_BY_SOURCE_RESULT. 최신 입력은 새 계산이다.

새 API 계약3건과 변경 영향을 받는 기존 vertical/store 경로 합계22통과.
같은 보관 universe ID/가용시각·설정·입력은 같은 식별자를 재현하고, 입력 변경은 input/result hash만 바꾼다.
새 실자료 포트폴리오 계산·전략 성과는0. Main #522 cbd1da52의 판독에서도 소수% 경계1차이는 그대로 재현된다.
Main은 기존 validateSelection의 허용 정밀도를 맞추고, sample.selection.selection_details를 선택 부가 필드로 판독하면 된다.
