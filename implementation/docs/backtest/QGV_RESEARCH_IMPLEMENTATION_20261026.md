# QGV 장기 연구 구현·실행 기록

계획: 2026-10-26 사용자 승인. 연구 명세 .5; 문서 출발 ce6acdfa47e7b3eabb63f4673e6e1053f9c6a621, 점수 소스 bb57398c9c22a2dfa2443c5f3a23db3848cbe5ce; qgv-v2 / qgv2-calc/2026-10-17.1.

## 실제 상태

구현·검사 진행 중. 실데이터는 1980·2000·2016 시작 모두 미실행이다. 30개 구조 설정은 정확 집합·ID·주검정·비중 정책을 검사한다. 실행 셀은 기간당 300개, 지연/유형 진단은 별도다. 운영 모델 승격·병합·배포 없음.

## 자료 감사와 재개 조건

현재 실행환경에 연구용 승인 비공개 입력 manifest와 시장자료 이용권이 없다. GitHub의 과거 raw manifest 포인터는 원자료 확보 증거가 아니다. 각 연도/시점의 역사 구성·영구ID/CIK·원본 재무·실제 공개일/정정·as-filed SIC·원시 OHLCV·주식수·기업행사/상폐대가·배당락/지급일·총수익 벤치마크·T-bill investment yield·검증 달력이 필요하다.

| 기간 | 상태 | 원인 |
|---|---|---|
| 1975~1979 준비 | 미확인 | 원본 공시/공개일·지표 이력과 권리 미연결 |
| 1980~1989 | BLOCKED_ON_DATA | 비전자 공시 PIT/역사 구성/가격/행사/정산/금리 미검증 |
| 1990~1999 | BLOCKED_ON_DATA | 역사 PIT 재무·종류주·정산·권리 미검증 |
| 2000~2009 | BLOCKED_ON_DATA | 초기 준비 이력·정정 원본·역사 입력 미검증 |
| 2010~2015 | BLOCKED_ON_DATA | 역사 구성원 전부의 자료·가용시점 미검증 |
| 2016~2025 | BLOCKED_ON_DATA | 전체 모집단·시가·배당 지급일·상폐 정산·벤치마크/금리 미연결 |

요인별 계산 가능 기업 수/비율은 원자료가 없어 미확인이다(0%로 표시하지 않음). 정상 NA/금융 V 미지원과 공급 부족은 구분한다. 보호/사용 이력은 UNCONFIRMED; OOS_NOT_ESTABLISHED다. 현재값·미래 수정치·프록시·현재504 소급은 금지한다.

후보 근거: https://www.marketplace.spglobal.com/en/datasets/compustat-financials-(8) 는 장기 북미 재무 1950과 PIT snapshots 1987을 구분한다. https://www.crsp.org/wp-content/uploads/2023/10/crsp_us_stock.pdf 는 영구ID·상폐수익·배당일자·종류주 스키마를 설명하지만 전필드 완전성을 보증하지 않는다. 후보의 존재는 사용권 확보가 아니다.

재개: 기간별 입력 manifest/access receipt/rights receipt/승인 private_output_root 및 bundle SHA → 무결성 검사 → 의미/PIT 검사 → 첫 시간순 smoke → 주비교 → 사전등록 민감도. 공용 가드 확장이나 유료 구매로 우회하지 않는다.

## 작업 기록

- 기준 회귀: 86 passed (QGV, custom weights, PIT). 신규 config RED 5 failures → GREEN 5 passed; CLI RED 2 failures → GREEN 2 passed.
- Ruling: 사용자가 병렬 Fan-out을 승인해 점수/PIT·장부·지표·실행 조정을 분리했다. 공용 파일 변경은 Main 인계로 제한했다.
- 최종 통합 검증 결과는 실제 실행 뒤 아래에 추가한다.

## 30개 구조 전략의 실제 실행 상태

세 기간 모두 감사 CLI 종료 코드 2(BLOCKED_ON_DATA). 수익률·위험·비용 성과는 NA이며 실행 성공 0/30이다. 아래는 구조 설정의 상태이고 기간/패널/비용 실행 횟수와 다르다.

| 전략 | 1980 정식 | 2000 진단 | 2016 진단 | 성과 |
|---|---|---|---|---|
| W0-N15-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W1-N15-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W2-N15-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W3-N15-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W0-N10-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W1-N10-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W2-N10-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W3-N10-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W0-N20-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W1-N20-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W2-N20-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W3-N20-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W0-N15-Y | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W3-N15-Y | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W0-N25-Y | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W3-N25-Y | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W0-N50-Y | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W3-N50-Y | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W0-N25-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W1-N25-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W2-N25-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W3-N25-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W1-N25-Y | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W2-N25-Y | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W0-N50-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W1-N50-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W2-N50-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W3-N50-Q | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W1-N50-Y | NOT_RUN | NOT_RUN | NOT_RUN | NA |
| W2-N50-Y | NOT_RUN | NOT_RUN | NOT_RUN | NA |

## 재개용 비공개 입력 계약

CLI는 네트워크 수집기를 호출하지 않는다. `--input-manifest`는 승인된 비공개 JSON 메타데이터 경로다. 필수 필드는 `protection_status`, `access_receipt`, `rights`(research/ai_processing/storage), `rights_receipt`, `private_destination_verified`, `private_output_root`, `resources`, `bundle`이다. 보호 구간에는 평가기간을 포함하는 `protected_scope`와 receipt도 필요하다. 무결성 통과는 PIT 적합성/투자 유효성 통과를 뜻하지 않는다.

`resources`의 membership/identities/financials/filings/prices/corporate_actions/benchmark/rates/calendar 각각은 path/sha256/start/end/verified/source/rights_receipt를 갖는다. `bundle`은 path/sha256를 갖고, 본문의 source_hashes는 이 9개 입력 해시와 일치해야 한다. 실제 경로와 해시는 비공개로만 보관한다.

bundle 계약은 runner/PIT 모듈과 합성 통합 검사가 실행 예시다. sessions는 day/open_at/close_at(시간대 포함), companyfacts_by_cik는 원본 SEC 모양 자료, filings는 cik/filed/sic/accn/accepted/known_at, membership은 cik/security_id/start/end(끝 제외), prices는 security_id/date/open/close/volume/currency/price_basis/shares_basis를 받는다. 주식·가격 기준이 확인되지 않으면 해당 V는 NA다. signal별 basis_alignment/basis_alignments 영수증은 PIT 어댑터가 실제 지원하는 필드와 검사로 검증한다. 데이터 공급자별 회계 필드 대응은 별도 감사가 필요하다.

rates의 annual_yield는 **연율 소수 단위**(퍼센트 숫자가 아님), public_date는 실제 공표일이다. bundle.benchmark_id는 정식 SP500_TR_INDEX / 단축 SPY_TR이다. benchmark는 일자별 USD 배당재투자 total_return_index와 최초 체결일 open_total_return_index를 받는다. 지수/ETF 식별과 권리는 manifest에서 고정한다. events는 ledger의 Split/Dividend/Settlement 데이터클래스 계약을 따른다. 검증되지 않은 날짜·정산·가격을 생성하지 않는다.

합성: `python implementation/tools/qgv_backtest_research.py --stage synthetic`
자료 감사: 같은 CLI에 `--stage audit --period-id TARGET_QGV_V2 --input-manifest`와 실제 비공개 메타데이터 경로를 전달한다. 이어 smoke/primary/sensitivity/report에 승인된 `--output` 하위 경로를 전달한다. 2000·2016 진단은 각각 SECONDARY_DIAGNOSTIC_NOT_TARGET / DATA_LIMITED_DIAGNOSTIC_NOT_TARGET을 사용한다. 기간을 몰래 줄이지 않는다.

## 구현 스냅샷 1의 경계·후속 보완 중

- 비거래일 효력 기업행사는 현재 무시하지 않고 BLOCKED_ON_IMPLEMENTATION으로 차단한다. 재개하려면 실제 효력일·정산일을 유지하는 비거래일 사건/일할 금리의 시간순 처리를 추가 검증해야 한다. 거래일로 날짜를 임의 이동하지 않는다.
- benchmark_id는 정식 SP500_TR_INDEX / 단축 SPY_TR이어야 한다. 최초 시가 기준 총수익 입력이 없으면 INCOMPLETE_REFERENCE다. 종가로 최초 시가를 대체하지 않는다.
- 단일 기간 report는 다른 두 기간의 NOT_RUN 행을 보존해 REPORT_PARTIAL일 수 있다. 이것은 전체 장기 연구 완료가 아니다. 표본 부족·금리/자료 결측도 별도 이유로 남는다.
- 종목별 수익 기여 계산기는 독립 구현·합성 검증되어 있지만 이벤트 포함 거래 원장의 종목/업종/유형별 연결 기여는 아직 report에 완전히 결합되지 않았다. 노출·집중도와 연결 기여를 혼동하지 않는다. 따라서 소수 기업 의존성의 최종 투자 판정은 보류한다.
- 공급자 원자료 획득·회계 필드 매핑·권리 검증은 미완료다. 이 구현 PR은 합성으로 검증한 연구 기반이며, 정식 장기 검증 완료 PR이 아니다. Main 공용 작업/인계 표 갱신은 이 문서와 PR을 근거로 통합한다.

## 스냅샷 1 실제 검증 (후속 코드 변경 전)

- 전체: `cd implementation && PYTHONPATH=src:. python -m pytest -q` → **3881 passed, 391 subtests passed**, 270.73초.
- 합성 CLI: `python implementation/tools/qgv_backtest_research.py --stage synthetic` → SYNTHETIC_PASS, 123 passed, real_data_executed=false.
- 경계·회귀 묶음: 299 passed, 137 subtests passed; direction guard 0 hits.
- 1980/2000/2016 audit 각각 종료 코드 2, BLOCKED_ON_DATA, 전략 30개 모두 NOT_RUN. 실제 성과는 없다.
- 독립 검토에서 가용시각, 분할 기준, PRACTICAL 자격, 거래정지, 보호 범위, 출력 symlink, 설정/기간 동결, 진입 전 이자, 음수 금리, 벤치마크 이름 오류를 발견하고 재현 검사 후 수정했다. 검토자 집중 검사 56 passed. 미사용 OOS와 투자 유효성을 확인한 검사가 아니다.
