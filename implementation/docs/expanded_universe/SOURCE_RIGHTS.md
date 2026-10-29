# 데이터 확보·사용권·비용 조사

확인일: **2026-10-29 UTC**, 공식 웹 문서 조회 + 기존 BACKTEST_DATA_AUDIT 대조.
현재 데이터 계약·구독 증거·실자료는 연결하지 않았다. 표의 PERMITTED는 해당 조건을
충족했을 때 문서상 허용되는 용도이며 구독 구매·자동 수집 승인이 아니다.
DENIED는 조사한 공개 약관/현재 경로로는 허용되지 않음을 뜻한다.
UNVERIFIED는 보수적 보류다. 후보를 실제 선택했다는 뜻이 아니다.

## 출처·커버리지·갱신 비용

| source / data | coverage / update_cadence | rate_limit | expected_cost 및 조건 | 증거 |
| --- | --- | --- | --- | --- |
| SEC EDGAR API / SEC_filing, shares, current_listing 참고 | 공개 submissions·표준 entity-wide XBRL; 실시간, bulk ZIP 매일 약 03:00 ET. 현재 ticker/exchange는 전 과거 상장 마스터가 아님. 주식종류 차원·모든 과거 주식수·상폐 수익은 보장하지 않음 | 사용자 전체 합산 최대 10 requests/s; 식별 User-Agent. 기존 client 5/s이며 여러 프로세스 합계 조정 필요 | 공개 API key 불필요, API 이용료 0으로 조사. 저장·네트워크·서버 비용은 환경별 미확인 | [S1][S2] |
| Nasdaq Trader / current_listing | nasdaqlisted/otherlisted 디렉터리, ETF·test issue·exchange·creation timestamp 필드. 완전한 영구 ID·역사 상폐 파일 아님. 파일 날짜 대조 필요 | 문서상 수치 미확인 | 브라우저 열람과 본인 비상업 사본 예외 존재. 운영 저장·주기 수집·재배포 계약/비용 미확인 | [S3][S4] |
| BLS 직접 / CPI | CPI-U, 월간 발표. 관측 월·발표 시각·빈티지는 분리 보존해야 함 | 미등록 25 queries/day, 등록 500/day; 각 25/50 series, 10/20년 | 공개 API 무료, 등록키는 사용자가 별도로 관리. 월 1회 + 필요한 과거 구간 요청 비용을 계획 가능; 서버 비용 별도 | [S5][S6] |
| Norgate US Platinum / price, historical_delisting, index history | 현재 종목 + 선택된 상폐 종목·역사 지수 구성 1990부터. Diamond는 1950부터. current fundamentals가 PIT historical shares를 보장하지 않음. EOD | updater 운영 한도·Linux 직접 수집 지원 미확인 | Platinum USD 346.50/6개월, 630/12개월. Diamond 433.13/6개월, 787.50/12개월. 공식 표, 환율·세금 별도 미확인. 구매/가입 실행 없음 | [S7][S8][S9] |
| 기존 IEX HIST / price | 중앙 V 별도 승인용 사슬. 확장 전체시장·과거 상폐·재배포 권리의 증거로 쓰지 않음 | 확장 목적 미확인 | 기존 중앙 V 결정이 이번 E2 비용·사용권 승인이 아님 | 기존 `CENTRAL_V_DC02_PLAN_20261024.md`, #400/#403/#404 |
| Yahoo / GOOGLEFINANCE / price | 기존 기기 개인 참고 경로 | 서버 수집용 미확인 | 기존 결정 DC-05상 서버 수집·공개 금지; 새로운 무료 서버 공급원으로 사용하지 않음 | DIRECTION_CHANGES DC-05, 기존 BACKTEST_DATA_AUDIT |
| Sharadar / CRSP 등 / price, shares, historical_delisting | 기존 감사의 후보. 이번 사용자 계정·계약·커버리지 미검증 | 미확인 | 이번에 검증한 견적 없음. 과거 문서 수치를 현행 가격으로 인용하지 않음 | 기존 BACKTEST_DATA_AUDIT, #417/#418 차단 상태 |

## 용도별 권리 매트릭스

F=fetch_allowed, S=server_store_allowed, R=private_research_allowed,
D=derived_score_allowed, A=public_aggregate_allowed, C=public_company_level_allowed.
각 열의 PERMITTED/DENIED는 **아래 제한 조건과 함께** 해석한다.

| source / data_type | F | S | R | D | A | C | status / 제한 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SEC / SEC_filing | PERMITTED | UNVERIFIED | PERMITTED | UNVERIFIED | UNVERIFIED | UNVERIFIED | SOURCE_POLICY_PENDING: API/bulk 접근·분석 경로 확인. 제출자가 작성한 내용의 포괄 재배포권까지 추정하지 않음 |
| SEC / shares | PERMITTED | UNVERIFIED | PERMITTED | UNVERIFIED | UNVERIFIED | UNVERIFIED | BLOCKED_ON_DATA: entity-wide 사실은 증권별 PIT shares 대사가 아님 |
| SEC / current_listing | PERMITTED | UNVERIFIED | PERMITTED | UNVERIFIED | UNVERIFIED | UNVERIFIED | 현재 메타데이터의 역사 최초 공개·완전성 미증명 |
| Nasdaq / current_listing | UNVERIFIED | DENIED | UNVERIFIED | UNVERIFIED | DENIED | DENIED | BLOCKED_ON_LICENSE: 개인 사본 예외와 별개로 사전 서면동의 없는 운영 저장·배포를 허용하지 않음 |
| BLS 직접 / CPI | PERMITTED | PERMITTED | PERMITTED | PERMITTED | PERMITTED | PERMITTED | 공공영역 통계, 출처 표기. 사진/그림/엠블럼 예외. CPI 회사별 배분값은 해당 없음; 다른 가격을 결합한 값은 그 공급원 권리도 필요 |
| Norgate / price | PERMITTED | PERMITTED | PERMITTED | PERMITTED | UNVERIFIED | DENIED | **활성 유료 개인 구독을 확보했을 때만**, 독립 목적 사용권이 없는 처리 서비스. 지금은 BLOCKED_ON_LICENSE |
| Norgate / historical_delisting | PERMITTED | PERMITTED | PERMITTED | PERMITTED | UNVERIFIED | DENIED | 위 구독 조건 + 패키지별 시작연도·상폐 종목 유형 대조 필요; BLOCKED_ON_DATA도 유지 |
| Norgate / historical shares | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | current fundamentals를 historical shares로 대체 금지 |
| IEX HIST / expanded price | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | 별도 확장 계약 확인 전 BLOCKED_ON_LICENSE |
| Yahoo·GOOGLEFINANCE / server price | DENIED | DENIED | UNVERIFIED | DENIED | DENIED | DENIED | 서버 확대 경로는 기존 결정상 금지. 기기 개인 열람과 혼동 금지 |
| Sharadar·CRSP / price, shares, historical_delisting | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | 실제 계약·자료 확보 전 BLOCKED_ON_LICENSE/BLOCKED_ON_DATA |

**Norgate 현행 EULA는 예전의 “Windows 외 처리 불가”라는 단순 가정을 뒷받침하지 않는다.**
20261002 EULA §2(iii)-(iv), §8은 개인 전용인 다른 컴퓨터·서버·VM·클라우드와
사용자 대신 처리하는 제3자 서비스를 허용한다. Updater 설치 환경과 데이터 처리 환경은 다르다.
그러나 §8은 다른 사람의 사용·공개/공용 접근·상업 이용을 금지한다. 정의상 backtest 결과는
엄격한 비대체성·비역공학 조건을 충족한 Derived Data일 수 있지만, 모든 회사별 점수·순위나
공개 집계가 자동으로 그 정의를 충족하지는 않는다. 공개 결과는 별도 확인 전 UNVERIFIED다.
§21은 구독 만료 시 로컬·서버·백업·export 포함 Content 삭제, 조건에 맞는 Derived Data만
유지를 허용한다. 장기 원자료 재현성·구독 갱신 비용/삭제 계획을 공급원 선택 전에 해결해야 한다.
표의 Norgate C=DENIED는 회사별 원본 Content 공개를 말한다. 회사별 파생 점수의 공개는
Derived Data 정의와 별도 허용 증거를 대조하기 전까지 UNVERIFIED다.

## 아직 필요한 확보 결정

1. 현재 상장 디렉터리의 주기 수집·private 서버 저장·검색 회사별 공개권이 명확한 공급원.
2. 발행사↔영구 증권↔종류↔상장거래소↔과거 ticker 유효기간의 권위 있는 매핑.
3. 당시 공개된 과거 shares와 가격·분할 기준 대사, 상폐/합병 정산·누락 표본.
4. #418 목표 1980~2025를 덮는 과거 구성/상폐 자료. Platinum의 1990 시작으로는 부족하다.
5. 승인된 비공개 저장 경로·보관/만료 조건·공개 집계/회사별 점수 권리.

모든 권리의 마지막 상태는 이 표가 아니라 실제 사용자 계약·공급원 문서·오너 결정에
따라 Main이 확인한다. 이번 작업에서는 자료·계정·구독을 생성/구매하지 않았다.

## 증거 URL

- [S1 SEC API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [S2 SEC Developer Resources](https://www.sec.gov/about/developer-resources)
- [S3 Nasdaq directory definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs)
- [S4 Nasdaq copyright/disclaimer](https://www.nasdaqtrader.com/Trader.aspx?id=CopyDisclaimMain)
- [S5 BLS API FAQ](https://www.bls.gov/developers/api_faqs.htm)
- [S6 BLS copyright/public domain](https://www.bls.gov/bls/linksite.htm)
- [S7 Norgate package pricing](https://norgatedata.com/stockmarketpackages.php)
- [S8 Norgate EULA 20261002](https://norgatedata.com/subscribe/eula.php)
- [S9 Norgate licensing FAQ](https://norgatedata.com/faq.php)

증거는 이번에 읽은 문서이며 원자료 자동 수집 시험은 아니다. 실패한 Norgate
`terms-and-conditions.php` 경로는 근거에서 제외하고 실제 EULA URL로 재확인했다.
