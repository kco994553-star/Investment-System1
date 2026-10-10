# TARGET19 유형 소속도 — 가격 없는 실행 결과

2026-10-10 현재 작업 환경과 저장소 근거를 확인했다. type_config/1 OFFICIAL_PROVISIONAL·v2 보정 대상. 합성 값을 실제 종목 결과로 대체하지 않았다. 아래 NA는 **NOT_AVAILABLE**, 0 소속도가 아니다. 유형·기준 정의와 실제 입력 확보는 별개다.

SEC raw STORE_INDEX에는 companyfacts 취득 메타데이터가 있으나 두 작업 환경의 blobs 디렉터리는 .gitkeep만 있고 원문 bytes가 없다. 따라서 SHA/CIK/연차 단위·3Y Revenue CAGR·ROIC를 재현할 수 없다. metadata 성공 기록만으로 실측을 확정하지 않았다. 실행 환경에는 SEC_USER_AGENT가 설정되지 않아 연락처를 임의 생성하거나 신규 SEC 취득을 실행하지 않았다. Secret 값/개인 시트/가격·Holdout을 조회하지 않았다.

가격 불필요 유형만 표에 포함한다. 우량 최종 결합과 민감/방어 기준은 입력 확보와 별개로 정의도 미정이다. 배당·가치·주도는 가격이 필요하므로 이번 결과 대상에서 제외한다. 테마는 바스켓/정규화 확인 전NA다.

| 종목 | 성장 | 우량 | 경기민감 | 경기방어 | 입력 근거 상태 |
| --- | --- | --- | --- | --- | --- |
| ASML (asml) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| LRCX (lrcx) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| KLAC (klac) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| tokyo_electron (tokyo_electron) | NA | NA | NA | NA | EDINET_DEFERRED; companyfacts metadata 0건 |
| hanmi (hanmi) | NA | NA | NA | NA | DART_WAITING_USER_NOTICE; companyfacts metadata 0건 |
| NVDA (nvda) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| AMD (amd) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| AVGO (avgo) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| QCOM (qcom) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| INTC (intc) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| MSFT (msft) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| GOOGL (googl) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| AMZN (amzn) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| RTX (rtx) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| SYK (stry) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| ETN (etn) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| HUBB (hubb) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| GEV (gev) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |
| ROK (rok) | NA | NA | NA | NA | RAW_BODY_NOT_PRESENT; companyfacts metadata 1건 |

각 종목은 미분류 fallback34/33/33 + TYPE_UNCONFIRMED이며 실제 Q/G/V도 공급되지 않아 점수는NA다. 성장 결과 산출의 다음 조건은 source bytes+SHA·CIK·같은 회계 범위/통화·연차 4개(3년 간격) 확인된 revenue_cagr_3y 공급이다. 이 표는 현재 실측불가 판정이며 실제 membership 숫자·보호 기간·forward 시작일을 만들지 않는다.
