# 섹터 후보·거래대금 진단 v1 구현 계획과 입력 계약

오너 2026-11-02 지시. 기능 9.Lab, 비공개 탐색. 기존 calc 23.1·프리셋·CPI2025·매매 규칙은 유지한다.

## 설계와 근거

기존 scoring/selection을 호출하는 비교 도구만 추가한다. 가격·PIT·장부 엔진을 복제하지 않는다.
A는 balanced, B는 섹터별 축 내부 비중, C는 섹터별 축 비중이다. 현재 확보된 발췌에는 검증 가능한
섹터별 지표 표/주석과 당시 섹터 매핑이 없어 **활성 후보 0개**로 동결한다. B/C는 명시적 baseline fallback이다.
임의 후보값이나 관문 변경으로 결과를 만들지 않는다. 미확인 후보의 활성화는 거부한다.

향후 결합 순서: 동일 모집단의 원지표 백분위 → B의 내부 비중(미확인 섹터는 공식값) →
해당 혼합 Q 점수 전체를 이용한 기존 업종 관문 → C의 축 비중 × 기존 유형 비중 / 유형 fallback →
기존 50% 가용 비중·관문 적용 → 사용 가능한 축의 최종 정규화.
B에서 섹터마다 독립 score_universe를 실행한 뒤 행을 조립하면 관문의 비교 모집단이 달라질 수 있으므로 금지한다.
현재 공통 API의 weights는 모집단 전체 공통이다. 원문 후보 확보 후 per-security 내부 비중 지원을
같은 공통 계산 경로에 추가해야 하며, 현재 fallback 준비를 B/C 활성 후보 구현 완료로 표시하지 않는다.

| 확인 대상 | 현재 증거 | 판정 |
|---|---|---|
| 섹터별 지표·방향·비교 대상 | 제24장 Sector Analysis, p501 시작이라는 서지 목차; CXO 서평 p545 인용 | 원문 표·주석 미확인, B/C 보류 |
| 모멘텀·거래량 결합 | 제20장 Relative Price Strength, p407 시작이라는 서지 목차; Brandsma 서평은 높은 거래량에 감점하는 방향 설명 | 거래액 단위·6개월 정의·정렬 분모·순서 원문 미확인 |
| All Stocks $200m 물가 기준 | OSAM 2012 저자 연구 PDF p2/p4, 최근 연말 기준 설명 | 책 기준연도/월/산식 미확인; cpi-2025-v1 유지 |

서지 목차: https://www.kriso.ee/what-works-wall-street-fourth-edition-db-9780071625760.html

2차 문헌: https://www.cxoadvisory.com/fundamental-valuation/a-few-notes-on-what-works-on-wall-street/

2차 문헌: https://www.linkedin.com/pulse/what-works-wall-street-james-oshaughnessy-vincent-brandsma-burce

필요 발췌(한 번에 요청): 제20장 거래액·변동성 비교 표와 앞뒤 정의/주석(통화 단위, 6개월 날짜·유효일,
순위 모집단, 모멘텀/거래액/변동성 적용 순서); 제24장 첫 후보 섹터의 지표별 비교 표·주석과
섹터 분류 설명; 제4장 All Stocks $200m 구매력 기준 문장·주석. 페이지/표 번호는 발췌로 확정한다.
한국어판 쪽수는 위 영문 목차 쪽수와 동일하다고 주장하지 않는다.

## 고정 진단 설정

`sector_liquidity_v1.json`을 계산 전 고정한다. 거래대금 창은 `(S-6 calendar months, S]`,
S=2018-02-16, NYSE 달력. 책의 정확한 기간 정의가 아닌 데이터 연결 진단이다.
일별 VWAP×volume은 공급사 집계 기반 근사 거래대금, close×volume은 종가 대용치다.
공급사 VWAP 반올림·거래 집계 범위 때문에 실제 모든 체결의 정확한 합계로 표현하지 않는다.
원주가와 원거래량만 결합한다. 신원·통화 미확인은 그대로 표시하고 과거/현재 티커를 합치지 않는다.
관측된 유효 거래일 평균과 완전한 창의 평균을 분리한다. 결측일은 null이며 0 대입하지 않는다.
유효하게 관측된 volume=0만 0을 허용한다. 동일 날짜 중복은 동일 값만 중복 제거하고 상충 값은 거부한다.
변동성 공식/분할 기준·전체 모집단 미확인: 변동성·백분위·유동성 등급 null.

## 구현 계획

- [x] `liquidity.py`: 공유 정규화 행 → 일별 두 산식·6개월 유효일/결측/평균/출처. 외부 호출 없음.
- [x] `sector_comparison.py`: 기존 score_population 기준선 및 select 재사용. 후보별 적격/공통적격 순위·편입탈락·섹터 구성 비교, B/C 보류 상태.
- [x] 의미 있는 검사: 결측≠0, 결측 VWAP≠종가 대체, 날짜 경계·중복 충돌·심볼 혼합 거부, 커버리지 변화와 순위 변화 분리, 기준선 일치.
- [ ] 비공개 기존 응답만 사용하여 진단 실행; source/config/code hash와 재현 스크립트 보존.

## Main 리더보드 계약

가격 자료 권한을 상속하므로 실제 수치의 공개 게시 권한을 부여하지 않는다. 화면 변경은 Main 담당.
`schema`, `symbol`, `security_id`, `identity_status`, `currency`, `currency_status`, `signal_day`,
`window_start_exclusive`, `window_end_inclusive`, `expected_sessions`, `observed_sessions`,
`vwap_volume.valid_days`, `vwap_volume.mean_observed`, `vwap_volume.mean_complete`,
`close_volume_proxy.*`, `missing_dates`, `invalid_dates`, `source_hashes`, `reasons`,
`market_percentile=null`, `price_volatility_6m=null`을 전달한다. 단위는 통화/거래일이며 통화 미검증이면 표기한다.
숫자는 Decimal 문자열, null은 사유와 함께. `mean_observed`를 완전한 6개월 평균으로 표시하지 않는다.

합성 예: USD/share로 확인한 VWAP 10.25 × 100 shares = 1025 USD;
종가 10 × 100 = 1000 USD 대용치. 이 예는 실제 기업 데이터가 아니다.
