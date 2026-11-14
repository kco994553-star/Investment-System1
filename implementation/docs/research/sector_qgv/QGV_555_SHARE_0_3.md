# 555 주당 근거: 두 단계 연구 판정

`unified-555/0.3.0`, `sector-555/0.3.0`은 기존 0.2 정책에서 역사 주당 근거만
`cross-filing-consistency-full-period/2`로 구분한다. 공식 calc 23.1, 0.1/0.2의
입력·저장 결과·정책은 보존한다. 산식, 역할 예산, 유효 역할 비중 50%, 최소 표본8,
S1의 확인된 섹터만 산출, 금융 참고 표시와 REIT 임시 GENERAL 정책은 바꾸지 않는다.

## 두 단계와 자동 처리

1. 같은 발행사·종류주·회계기간·통화·단위·연결범위의 제출본을 대조한다.
   희석 EPS에는 해당 보통주 귀속·희석조정 분자를 요구한다. 허용오차는
   원문 XBRL decimals/precision의 반 단위 구간을 사용한다. 정밀도 메타데이터가
   없으면 정확한 숫자 일치도 진단이며 확인 완료가 아니다.
2. 지표에 쓰는 모든 연도가 공통 주식 기준으로 연결되는지 확인한다.
   명시된 동일기준 비교연도 또는 소급조정 근거와 제출본 연결을 보존한다.
   중복 숫자만으로 전 기간 적격성을 선언하지 않는다.

일관성은 ‘분할 없음’을 뜻하지 않는다. 이익이 같고 EPS·주식수가 역비례하면
`SPLIT_CANDIDATE`이며, 숫자 비율만으로 보정하지 않는다. 근거가 충족되면 자동
최종 판정하고, 부족한 메타데이터·모호한 문서만 구체적 사유와 함께 미확인으로 남긴다.

## 지표별 분모와 의미

| 기존 variant | 분모·계산 의미 | 자동 승계 금지 |
|---|---|---|
| `eps_cagr_3y` | 보고된 희석 EPS의 양수 양끝 FY 3년 CAGR | 연결 순이익/현재 주식수로 EPS를 만들지 않음 |
| `fcf_per_share_cagr_3y` | FY `(CFO−현금 CAPEX)/가중평균 희석주식수`의 3년 CAGR | EPS 확인만으로 FCF 분자·기간을 승인하지 않음 |
| `dilution_3y` | 가중평균 희석주식수의 3년 CAGR | 실제 발행·소각률·기본/기말 주식수 변화로 해석하지 않음 |

가격 결합에 쓰는 평가일 증권·종류주·ADR·기업행사 검사는 별도다.
역사 성장률의 주식 기준 확인은 평가일 가격 결합을 승인하지 않는다.

## 입력·결과와 Main 판독

`qgv_555_share_review.review_share_eligibility_v2` →
`qgv_555_owner_inputs.apply_two_stage_share_review` → 기존 `run_qgv_555.py` 경로를 쓴다.
입력은 `held-555-share-eligibility/2` 검토본 해시와 원자료 해시에 연결한다.
과거의 VERIFIED 표시만 있는 입력은 새 모델에서 격리한다. 원값은 진단으로 보존한다.

기존 결과의 각 선택 주당 metric에 `share_validation`을 추가한다.

- `final_eligibility`, `review_version`, `denominator_definition`
- `stages`: 원값 연결, 제출본 일관성, 전기간 연결, 기업행사·보정·최종 상태 요약
- `source_refs`, `reviewed_at`, `retrieved_at`

`FINAL_ELIGIBLE`과 정확한 검토 버전·분모 정의가 없는 값은 점수에 들어가지 않는다.
단계별 원인과 수량은 별도 보관 audit에서 코드 행/고유 발행사를 나누어 제공한다.
자료 연결·규칙 변경에 따른 철회·기존 숫자 재사용을 신규 원문 확보로 합산하지 않는다.
현재 확보한 문서로 재구성한 결과는 역사 당시 시스템 보유를 입증하지 않는다.

Main은 `qgv-555-result/1`·기존 delivery/manifest를 유지하고 새로운 model_id를
명시적으로 인수한다. 원값, 일관성, 전기간 연결, 실제 보정, 최종 적격, 역할·축·총점은
따로 표시한다. `raw`가 있어도 미채택일 수 있으며 결측을 0점으로 표시하지 않는다.

공개 합성 예시와 생성·검증 명령은 `implementation/tests/fixtures/qgv555-share-v2/`와
`implementation/tools/generate_qgv_555_share_examples.py`에 둔다. 실자료는 포함하지 않는다.
