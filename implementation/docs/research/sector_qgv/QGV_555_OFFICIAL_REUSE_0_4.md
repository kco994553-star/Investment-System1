# 555 공식 원지표 재사용 연구0.4

공식 calc23.1, 공개 결과, 연구0.1/0.2/0.3과 저장 설정은 보존한다.
`unified-555/0.4.0`, `sector-555/0.4.0`은 공식 fiscal kernel의 동일 정의 원지표만
재사용하고, 555의 역할·비중·참조집단으로 새 점수를 계산하는 별도 연구다.
공식 점수·순위·분위를 가져오지 않는다. 0.3 엄격 통과와 같은 의미가 아니다.

## 공식 경로와 의미

원문 구현은 `qgv/v2_factors.py`의 `_Company`, `_shares_scale`, `_v_inputs`다.
운영 함수를 수정하거나 별도 보정 엔진을 만들지 않는다.

| 경로 | 실제 처리 | 이 연구에서의 해석 |
|---|---|---|
| `_edge` | 공통기간 WAD 비율이 모두1의 ±5%이면1, 아니면 보고 분할비·역수의 ±3%와 일치해야 보정, 나머지는 거부 | 정확한 공통값 연결과 ordinary revision 허용 가정을 구분 |
| `share_factor` | 확인 edge 연결을 우선. 연결 자체가 없고 제출 사이 분할 사실이 없으면1 | 분할 없음의 증명이 아닌 공식 허용 가정 |
| `shares` | 원 WAD×factor, FY0 대비 설명 안 되는3배 초과 변화 거부 | 실제 발행·소각률이 아닌 WAD 기준 |
| `eps` | 보고 희석 EPS÷factor, 해당 WAD 불연속 거부 전파 | 연결 순이익/현재 주식수로 EPS 생성하지 않음 |
| `per_share` | 각 FY 분자/조정 WAD | FCF는 CFO−현금 CAPEX; EPS의 근거만으로 자동 승인하지 않음 |
| `share_basis_factor(F_k)` | 최초 보고 연간 제출본과 FY0·최신 기준을 연결해 과거 RAW 월말가격을 보정. 분할 시점 불명확은 거부 | 역사 가격용이며 모든 주당 성장률 검증 완료 표시가 아님 |
| `_shares_scale` | 자기 제출본의 단일 표지 주식수와 비교. 표지가 없거나 복수면 NO_REFERENCE | 역사 성장의 공식 차단 조건과 별도. 표지 없음은 검증 완료가 아님 |
| 중앙 V 기업행사 검사 | 평가 가격의 증권·ADR·분할·RAW 가격 기준 등 별도 검사 | 역사 기준 연결은 평가일 가격 결합을 승인하지 않음 |

공식 허용 가정과 추가 검증 요구는 운영 결함이 아니다. 확인된 수치 충돌·공식 거부를
되살리지 않으며, 운영 오류는 별도 재현 근거가 있을 때만 보고한다.

## 채택 근거와 두 비교 범위

`historical_share_policy=official-kernel-share-reuse/1`.

| `adoption_basis` | 의미 |
|---|---|
| `EVIDENCE_LINKED` | 동일 제출본 비교자료 또는 정확한 공통기간 주식 기준 연결 |
| `FILING_SPLIT_ADJUSTED` | 공식 함수가 보고 분할 사실과 비율을 연결해 보정 |
| `OFFICIAL_ASSUMPTION_INHERITED` | overlap 없는1.0, ordinary revision 허용 등 공식 가정 승계 |
| `ADDITIONAL_VERIFICATION_REQUIRED` | 필수 계산자료·문서 ID·규모 등의 추가 검증 필요 |
| `EXPLICIT_CONFLICT_EXCLUDED` | 명시적 충돌·설명되지 않는 불연속·공식 기준 연결 거부 |

`share_evidence_scope`는 저장 설정·캐시·결과 해시에 포함한다.

- `ALL_OFFICIAL_REUSE`: 첫 세 범위의 계산 적격 원값을 사용한다.
- `EVIDENCE_ONLY`: 첫 두 범위 중 `requires_assumption=false`이고
  `evidence_only_eligible=true`인 값만 쓴다. 참조집단의 원값에도 같은 필터를 적용해
  다시 점수화한다. 이를 0.3 엄격 통과 또는 전체시장 커버리지라고 부르지 않는다.

보고값의 숫자 일치, EPS×WAD와 귀속분자의 산술 일관성, 전기간 기준 연결은 별도다.
정밀도가 없어도 보고값 일치는 기록할 수 있다. 정밀도가 없을 때 산술 비일치를
확정 오류로 단정하지 않는다. 종류주 차원이 보관 응답에 없다는 사실을 동일 종류주
귀속 확인으로 바꾸지 않는다. 추가 원문 문맥이 없어도 공식 가정 범위의 연구 산출은
명시적으로 가능하지만 strict proof로 표시하지 않는다.

## 재사용과 차단의 반례

- 공통기간 없이1.0을 쓰는 경우: 미발견 분할 가능성을 `allowed_assumptions`로 표시.
- 정확히 같은 EPS·WAD의 반복: 보고값 일치이며 분할 부재·전기간 귀속을 증명하지 않음.
- EPS 반올림: 원문 decimals/precision 부재를 숫자 일치 자체의 차단으로 쓰지 않음.
- 동일 제출본·같은 기간에 충돌하는 값: 단순 ordinary revision으로 숨기지 않음.
- 표지 없음: NO_REFERENCE를 역사 성장 차단 또는 규모 검증 통과로 바꾸지 않음.
- WAD 규모 불일치: 추가 검증으로 보류하며 잠재주식·다중 종류주 가능성을 확정 오류로 단정하지 않음.
- FCF 분자·기간 불일치: EPS 확인만으로 재채택하지 않음.
- 가정 표시를 끄고 evidence-only로 전달: bridge와 직접 CLI 공통 불변 조건으로 거부.
- 현재 평가일 가격·증권 ID가 없음: 역사 성장 계산과 가격 결합을 분리.

## 실행·Main 계약

`qgv_555_official_share.review_official_share_history` →
`qgv_555_official_inputs.apply_official_share_reuse` → 기존 `run_qgv_555.py`.
검토본 원바이트 해시는 caller가 독립 고정하고, bridge는 발행사·원자료·record hash·
FY·취득/검토/입력 마감 시각을 대조한다. 분류·가격·관문·비주당 입력은 변경하지 않는다.

선택 주당 metric의 `share_validation`:

- `review_version`, `adoption_basis`, `strict_verified=false`
- `requires_assumption`, `allowed_assumptions`, `evidence_only_eligible`, `coverage_scope`
- `additional_verification_required`(boolean), `additional_verification`(사유 배열)
- `denominator_definition`, `diagnostic_raw`, `source_reason`, `source_refs`
- `reviewed_at`, `retrieved_at`, `verifies_valuation_security=false`

입력 proof의 `RESEARCH_USABLE`은 연구 채택 가능 표시다. strict VERIFIED와 구분한다.
두 범위의 결과·요약·전체 D1~D10은 각각의 설정·참조 유효N·원결과 해시에 연결한다.
구간·순위 규칙,555 최소8·유효 역할 비중50%, 기존 공식 관문을 변경하지 않는다.
금융 참고값은 555 분자에 넣지 않고 REIT 임시GENERAL 표시는 유지한다.

공개 합성 예시는 `tests/fixtures/qgv555-official-reuse/`, 생성기는
`tools/generate_qgv_555_official_examples.py`다. 실제 회사별 값과 결과는 비공개 보존한다.
Main은 모델0.4·두 범위·근거/가정/추가검증 표시를 인수한다. 브라우저·인증·배포는
별도 상태다. 신규 원천 요청·공식 전환·병합·배포를 실행하지 않는다.
