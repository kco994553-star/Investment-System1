# 기업 유형 v1 — PROVISIONAL

GSQ-017 승인값을 설정과 pure Python으로 구현한다. [`type_config_v1.json`](../../src/investment_system/qgv/type_config_v1.json)의 원본을 수정하지 않고 `load_official_type_config()`가 frozen `TypeConfig`를 반환한다. `to_dict()`는 새 복사본, `compile_custom_config(copy)`는 공식 상태 문구가 남아 있어도 CUSTOM_PREVIEW다. UI·기기 저장·공식 채택·serializer·Model 연결은 없다. Python 객체를 직접 위조하는 행위는 지원 계약 밖이며 loader/compile factory를 사용한다.

`calculate_company_types(metrics=..., original_qgv={Q,G,V}, config=...)`는 I/O 없는 함수다. 비율은0.10=10%, QGV는0~100, 결측은None. 같은 config 순서가 소속도 동률일 때 결정성을 제공한다(별도 금융 가중치 없음). 민감/방어 중 동률일 때도 config 순서로 하나만 남긴다. 먼저 한 번15~60 clamp하고 한 번100 재정규화한다. 사용자 극단 비중에서는 재정규화 후 기둥이60을 넘을 수 있다; 추가 반복 clamp는 승인된 순서에 없다.

## 구현 / 미정

| 유형 | 계산 계약 | 현재 불가 근거 |
| --- | --- | --- |
| 성장 | max(0,min(1,(CAGR−.10)/.10)) | 같은 재무 범위·통화·3년 연차 Revenue CAGR 입력 근거 필요 |
| 우량 | ROIC 램프 component만 별도 보존 | 마진 변동/낮은 부채 임계·3개 결합 규칙 미정, 최종 소속도NA |
| 가치 | 할인 지표 이름만 설정 | 업종/자기 과거 기준 기간·PE/EVEBIT 할인 램프·결합 미정 |
| 배당 | 5년 지급 true일 때 수익률 램프 | 지급 false는 유효0, 미확인은NA; 수익률 가격은 기기 인자 |
| 경기민감/방어 | SIC group·변동성 기준 자리 | 매핑 채택·변동성 산식/기간/램프·결합 미정 |
| 주도 | 검증된 업종 시총 순위1~3=1, 그 밖=0 | 가격/주식 종류·업종 전체 모집단 없는 경우NA |
| 테마 | EXPOSURE_ONLY·QGV 비중 없음 | ETF/사전/정규화 확인 전NA, 후속 제안 PR |

유형 추가/삭제/이름·판정/비중 수정은 JSON의 `types`로 표현한다. `ramp`, `gated_ramp`, `rank`, `unresolved`를 지원한다. 삭제한 ID는 exclusive_pairs·value_basis 참조도 정리해야 한다. 새 금융 결합 operator는 임의 추가하지 않으며 필요하면 사용자 결정을 받는다. `validate_type_config`는 reason codes를 반환하고 compile은 해당 codes로 실패한다.

공식 QGV pilllar 원본과 type-adjusted pillar·부모 비중/점수를 함께 반환한다. 결측 기둥은 점수 전체NA이며 남은 기둥 비중으로 재계산하지 않는다. 민감 유형이 인정되면 반드시 설정 `required_metric`의 **5년 정규화 이익에 근거한 V 점수**를 별도 공급해야 한다. 입력 점수 유래 검증은 호출자의 책임이다. 승인되지 않은 이익→V 점수 변환·EPS/ADR basis를 창작하지 않는다. 가격 값·metric payload·개인 선정 목록은 RAM 범위이며 공개 출력 연결 없음.

## SIC 업종군 제안 — 채택 전

SEC SIC 목록은 업종 설명이며 경기민감/방어를 제공하지 않는다. 아래 매핑은 **검토 초안**, 아직 계산에 쓰지 않는다. GICS 라이선스 자료를 사용하지 않는다. SIC가 없거나 0000/불일치면 NOT_AVAILABLE. 사업 혼합·은행/보험은 별도 검토 필요다.

| SIC 범위/코드 | 업종군 초안 | 민감/방어 제안의 한계 |
| --- | --- | --- |
| 1000~1499 | 자원/광업 | 민감 후보, commodity mix 확인 |
| 1500~1799 | 건설 | 민감 후보 |
| 2000~2199 | 식품/담배 | 방어 후보, 2080음료 등 세부 확인 |
| 2200~3999 | 제조/산업/기술 | 한 범위로 민감 판정 금지;357x컴퓨터·3674반도체·384x의료기기 분리 |
| 4000~4799 | 운송 | 물류·철도·항공 등 세부 사업 확인 |
| 4800~4899 | 통신 | 4812·4813·4899 등; 운송과 분리, 사업 혼합 확인 |
| 4900~4999 | 유틸리티 | 방어 후보, 발전/전력장비 SIC 혼동 금지 |
| 5000~5999 | 유통/소매 | 5411식품 소매와 discretionary 분리 필요 |
| 6000~6799 | 금융/부동산 | 은행·보험·REIT 별도, 통일 변동성 램프 금지 |
| 7000~8999 | 서비스/소프트웨어/의료 | 737x소프트웨어·8000~8099의료 분리 필요 |

원기관: https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list . 매핑은 설정 `industry.groups`에 **확인 후** 추가한다. SIC 사용과 민감/방어 분류 방법의 채택을 혼동하지 않는다.
