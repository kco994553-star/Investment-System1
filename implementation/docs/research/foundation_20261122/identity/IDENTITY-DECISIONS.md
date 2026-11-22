# 운영 504행의 증권 식별 제안 · 2026년 11월 22일

운영 코드 504개를 발행사 501곳에 대조했다. 발행사 공시를 묶을 때는 CIK를 사용한다. 한 발행사의 복수 종류주, 상장시장, 가격 시계열에는 각각 별도 근거가 필요하다. 평가일은 11월 13일과 20일이다. 이 조사는 현재 보관한 원본을 사용한 소급 검토다. 공시일·관측일·효력일을 분리했으며 두 평가일 당시 시스템이 이 결론을 알고 있었다고 소급하지 않는다.

[504행의 SEC 대사표](sec-504.csv) · [11개 재검토 행과 출처](sec-review-11.csv)

## 11개 재검토 결과

| 운영 이름과 코드 | 확인한 문서 근거 | 표시·처리 |
|---|---|---|
| Brown-Forman · NYSE:BF.B | 이름 사전의 B종, SEC 기호 사전의 BF-B·BF-A, 표지의 BFB·비의결권 Class B가 대응한다. | B종을 표시한다. 다른 발행사나 종류주에 문장부호 치환 규칙을 확대하지 않는다. |
| Cboe Global Markets · BATS:CBOE | 동일 표지 문맥에 CBOE 보통주와 거래소 원문 CboeBZX가 있다. SEC 기호 사전의 거래소 표기는 CBOE다. | SEC 표지의 거래소 원문을 보존한다. 운영 접두사·다른 코드체계와의 효력일 있는 상장 대응은 별도로 검증한다. |
| Fifth Third Bancorp · NYSE:FITB | c-2에서 무액면 보통주·FITB·NYSE가 일치한다. 자본 단위 차원에 우선주 문맥들이 따로 있다. | 보통주만 선택한다. |
| Hilton Worldwide · NYSE:HLT | 종전 표지는 NYSE다. 11월 4일 Nasdaq 등록 및 NYSE 철회 서류가 있다. 11월 5일은 발표 당시 예정한 첫 거래일이다. | 이전 경고와 기존 행을 함께 표시한다. 실제 첫 체결일은 보류한다. |
| Kenvue · NYSE:KVUE | 11월 2일 인수 종결, 11월 12일 상장폐지 효력이 확인된다. | 두 평가일 모두 종전 상장 종료로 표시한다. |
| Nasdaq, Inc. · NASDAQ:NDAQ | c-2의 Nasdaq Stock Market 문맥에 보통주·NDAQ·NASDAQ가 함께 있다. 같은 기호의 Texas 문맥과 회사채 문맥도 있다. | 요청한 Nasdaq Stock Market 문맥을 선택한다. 다른 문맥에 이 거래소를 상속하지 않는다. |
| NiSource · NYSE:NI | c-2의 자본 구성요소 차원에 보통주·NI·NYSE가 함께 있다. | 해당 문맥의 보통주를 표시한다. |
| Skydance · NASDAQ:PSKY | 10월 6일 공시는 B종의 기호·시장 전환을 기록한다. 11월 9일 10-Q의 보관된 표지에는 SKYD와 NYSE가 있다. | 종전 PSKY는 전환으로 표시한다. 두 코드의 시계열을 이어 붙이려면 별도의 날짜 근거가 필요하다. |
| Revvity · NYSE:RVTY | 동일 CIK·기간에 표지 제목·기호·거래소가 각 한 개다. c-1은 보통주, c-2는 RVTY, c-3은 NYSE다. | 유일한 세 문맥을 함께 표시한다. 복수 후보가 있는 표지에는 이 규칙을 확대하지 않는다. |
| Warner Bros. Discovery · NASDAQ:WBD | 10월 6일 합병 8-K 표지에 Series A Common Stock·WBD·Nasdaq이 있다. 본문은 종전 보통주의 현금청구권 전환을 확인한다. | 종전 증권 종료로 표시한다. 취득사 주가를 연결하지 않는다. |
| ASML Holding · NASDAQ:ASML | SEC 기호 사전은 Nasdaq의 ASML과 OTC의 ASMLF를 구분한다. 선정한 SEC 표지에 대한 종류주 관측은 결측이다. | SEC 사전의 시장·기호를 표시하고 종류주 표지 필드는 비워 둔다. 별도 C-39 관심 목록에는 발행사 자료로 검토한 Nasdaq 등록 보통주 및 ISIN이 있다. 해당 목록에는 날짜가 입증된 상장이 없다. |

행별로 공시 원문과 accession을 연결했다. CIK는 선행 0을 보존하는 문자열이다. 기호 사전은 10월 4일 캡처이므로 이후 기업행사는 해당 공시로 판정한다. 표지의 회계기간과 자료 수집일을 상장의 시작일이나 종료일로 쓰지 않는다. [SEC 기호·거래소 사전](https://www.sec.gov/files/company_tickers_exchange.json) · [운영 이름 사전](https://github.com/kco994553-star/Investment-System1/blob/33d144ecb3a1e53c14cc4df4c3a8618d7058782a/implementation/src/investment_system/product/web_assets/company-names-ko.json) · [C-39 관심 목록과 근거](https://github.com/kco994553-star/Investment-System1/blob/33d144ecb3a1e53c14cc4df4c3a8618d7058782a/implementation/docs/security_map19_owner/v1_1_cycle_20261008/CURRENT_TARGET_IDENTITY_MAP.json)

## PR별 처리 제안

| PR | 재사용할 부분 | 반영 전 확인 |
|---|---|---|
| #562 | 공시 원문, CIK, 종류주·거래소의 문서 관측을 생산하는 경로 | 위의 국소 문맥 규칙과 기업행사 사례를 회귀 사례로 추가한다. 문서 수준 일치와 날짜가 있는 상장 판정을 나누고 비공개 근거는 비공개로 유지한다. |
| #515 | 같은 평가일·증권의 결합 계약과 실패 사례 | #498 의존성을 확인하고 C‑39의 종료일 미포함과 이 계약의 증거 종료일 포함을 어댑터에 명시한다. 상장 종료일 직전·당일, 만료·중복·결측을 검증한다. |
| #516 | 코드 행 ID와 독립된 명시적 issuer_id, 시점 분류와 그룹 명부 | #514·#515·#505 개발 의존성을 확인한다. 동일 CIK의 복수 종류주와 분류 버전 변경을 시험한다. 발행사별 그룹이 증권 ID를 제공한다고 간주하지 않는다. |
| #517 | 같은 평가일, 검증된 증권과 확인된 그룹을 요구하는 화면 소비자 | #515·#516의 입력 계약을 맞추고 기존 joinOf의 row.id/row.code 문자열 대조를 제거한 경로를 검토한다. 통과·거절·중복·다른 종류주·다른 날짜를 브라우저에서 확인한다. |

날짜가 있는 연결에는 기존 발행사·증권·상장 식별자, 시장·통화·종류주, 효력 구간, 출처와 인지 시각을 기록한다. 공급처가 쓰는 요청·반환 기호와 저장계열 참조에는 별도의 상장 대응 근거가 필요하다. 같은 날 유일한 연결이 남을 때만 기술 필터에 전달한다. 충돌은 사유·원문과 함께 격리하고, 증거 결측은 미확인으로 표시한다. 이 제안은 공식 모집단, 순위, 점수, 운영 표시를 변경하지 않는다. [#562](https://github.com/kco994553-star/Investment-System1/pull/562) · [#515](https://github.com/kco994553-star/Investment-System1/pull/515) · [#516](https://github.com/kco994553-star/Investment-System1/pull/516) · [#517](https://github.com/kco994553-star/Investment-System1/pull/517)
