# 확장 모집단(미국 전체 상장주식) — Main 통합 계획 (2026-10-29)

> **상태: 계획 문서(Main 담당 범위).** 코드·스케줄·공식 모집단·공개 범위·배포는 바꾸지 않는다. 병합·정기 실행·가격 계약·공식 모집단 변경·공개 필드 확대는 모두 오너 승인 뒤다.
> 근거: 오너 지시(2026-10-29, 첨부 3건 — Main 통합·운영 명세 v1.0, 공통 경계·계약 v1.0, Codex E0/E1-A 명세 v1.0). 첨부 원문은 저장소에 넣지 않았다. 이 문서는 그 지시를 지금 정본과 대조한 결과다.
> Codex 문서(#422: `E0_AUDIT`·`E1A_CONTRACT`·`SOURCE_RIGHTS`·`E1B_E2_PLAN`·`HANDOFF`)는 같은 폴더에 있다. Main은 이 파일과 [MAIN_E1B_E2_DESIGN_20261029](MAIN_E1B_E2_DESIGN_20261029.md)만 쓴다(파일 충돌 없음).
> **갱신 2026-10-29 오후:** Codex가 #422(E0/E1-A, HEAD `a30b54bb`)를 냈다. Main 인수 결과·E1-B/E2/백테스트 설계·공급원 재확인은 [MAIN_E1B_E2_DESIGN_20261029](MAIN_E1B_E2_DESIGN_20261029.md)에 있고, 아래 5절 표의 SEC·Nasdaq 줄은 그 문서 3절이 대체한다.

## 0. 기준 (처음 읽은 시각 2026-10-29 11:05 UTC 무렵, 오후 갱신)

- canonical(기본 브랜치) `claude/investment-system-top500-validation-alrugm` = `282382a7`(#420 병합). 같은 날 중앙 V 사슬(#393 → #400 → #403 → #404 → #405)을 병합하므로 HEAD는 곧 바뀐다. Codex·Main 모두 시작 때 다시 조회한다.
- 확장 관련 열린 PR과 담당:

| PR | 내용 | 상태 | 담당 | 확장 작업과의 관계 |
| --- | --- | --- | --- | --- |
| #417 | QGV 장기 백테스트 엔진·30개 전략(합성 검증) | Draft | 연구 담당(Codex 연구 예외) | E3 결과 게시 계약의 생산자. **#393 병합 뒤 깨질 곳 있음(7절)** |
| #418 | 책 기반 두 모집단·분위수 연구 명세(문서) | Draft | 연구 담당 | `U-BOOK200`·`U-SPX-HIST` 정의의 원본 |
| #416 | 백테스트 실행 기준 v1(문서) | Open | 연구 담당 | #417의 기준 |
| #392·#361·#411 | TARGET v0 결합 해소·Worker 분할·TARGET 확정 점검 | Open | Main | 셋 다 `pages_artifact_guard.py`를 고친다 → 가드는 직렬 병합 |
| 중앙 V 사슬 | F_k·calc_version 23.1·중앙 V 게시 | 10-29 병합 진행 | Main | calc_version이 바뀌어 #417의 고정값과 어긋난다 |

- Codex 확장 작업 브랜치·Draft PR: 처음 조회(11:05 UTC 무렵) 때는 없었다. **#422**(`codex/expanded-universe-e0-e1a-20261029`)는 11:21 UTC에 생성됐고 Main은 오너 2차 지시(14:2x UTC) 때 확인했다. 그 사이 문서(#423·#425)의 "Codex PR 없음" 표기는 다시 조회하지 않은 오기다. 신규 파일 10개, 기존 파일 변경 0.

## 1. 역할과 파일 경계 (Codex에 전달할 안내)

DC-27(이번 줄)로 Codex의 E0/E1-A 구현은 **이번 지시 한정 예외**다. DC-09(Codex는 검증·리뷰)를 영구히 바꾸지 않는다.

| 담당 | 쓸 수 있는 곳 | 쓰지 않는 곳 |
| --- | --- | --- |
| Codex(E0/E1-A) | 새 파일만: `implementation/src/investment_system/universe/expanded_catalog*.py`(이름은 아래 재사용 검토 뒤 확정), `implementation/tests/test_expanded_catalog*.py`, `implementation/tests/fixtures/expanded_universe/`(합성만), `implementation/docs/expanded_universe/` 아래 Codex 문서 5개(#422) | 기존 파일 전부(특히 `contracts/*.py`, `universe/*.py` 기존 모듈, `universe_codes_v1.json`), `.github/workflows/`, `implementation/tools/pages_artifact_guard.py`·`public_price_boundary.py`·`ci_*_tests.txt`, `product/web_app`·`web_assets`, `CURRENT_HANDOFF`·`DIRECTION_CHANGES`·`FUNCTION_STATUS`·`USER_DECISIONS_PENDING`, 중앙 V·원장 파일 |
| Main | 기존 모듈 어댑트가 필요하면 그 변경, 수집기·스케줄·가드·CI·공용 문서, Codex PR 인수 검증 | E1-A 카탈로그 코어를 따로 구현하지 않는다 |
| 연구(#417·#418) | 연구 엔진·연구 문서 | 웹 계산 엔진 금지 |

- 기존 모듈을 고쳐야 하면 Codex는 PR 본문에 "Main 인계" 항목으로 적고 고치지 않는다. Main이 별도 PR로 처리한다.
- 확인한 충돌: 제안 경로 `universe/expanded_catalog*.py`, `tests/test_expanded_catalog*.py`, `docs/expanded_universe/`는 지금 정본에 없다(이름 충돌 없음). 열린 PR 중 이 경로를 건드리는 것도 없다.

## 2. 먼저 재사용할 기존 코드 (E0 감사 입력)

**같은 개념이 이미 있다. 새 이름으로 복제하지 말고 아래를 감싸거나 이어 쓴다.**

| 필요한 것 | 기존 코드(실제 경로, `implementation/src/investment_system/`) | 재사용 방법 |
| --- | --- | --- |
| 발행사·증권·상장 식별 | `contracts/global_universe.py` `IssuerIdentity`·`SecurityIdentity`·`ListingIdentity`(티커는 날짜가 있는 상장의 속성, 키가 아님; `valid_from`/`valid_to` 반개구간, `active_on`) | 공통 계약의 Issuer·Security를 이 세 클래스로 맞춘다. 계약 초안의 `Security.ticker/exchange/valid_from/valid_to`는 **ListingIdentity**로 간다(같은 증권의 거래소 이전·티커 변경을 상장 이력으로 남김) |
| 시점 규칙 | `contracts/global_universe.py` `_require_pit`·`EligibilityRecord`, `contracts/universe.py` `DataEvent`·`EventKind`·`UniverseSnapshot`, `universe/events.py` `IncrementalEngine`(available_at > as_of 사건은 미루고 적용 안 함) | C03(공개 전 사건)·C05(시각 역전)를 같은 규칙으로. `EventKind`에 상장 사건 종류가 없으면 Main 인계로 확장 |
| 과거 티커 → CIK | `universe/resolve.py`(현재 지도를 과거 구간에 쓰는 오류 차단, 미해결은 `tkr:` 유지) | C02(티커 재사용)·C08(CIK 불명) |
| 종류주 묶음 | `universe/share_class_groups.py`(같은 경제적 권리의 종류주만 합산, 전환비율 ≠ 1은 제외) | C01·시총 합산 규칙(6절) |
| 상장 목록 원본(현재) | `providers/sec_universe_collection.py` `TICKER_EXCHANGE_URL`(SEC `company_tickers_exchange.json`), `UniverseRegistry`·`daily_partition` | E1-B 수집 어댑터의 첫 원본 후보 |
| SEC 요청 정책 | `providers/sec_collection.py` `SecCollectionClient`(비공개 User-Agent, 429·5xx 재시도·`Retry-After`, 간격 제어, 리다이렉트 거절) | 새 수집기는 이 클라이언트만 쓴다(요청 정책 복제 금지) |
| 공시 시각·버전 | `providers/sec_submissions.py`(as_of 시점 접수번호·접수일 고정), `providers/sec_vintage.py`(filed > as_of 제외), `providers/sec_filing_timing.py` | SEC 증분 수집의 `available_at` |
| 표지 주식수(종류별) | `providers/sec_cover_shares.py`(XBRL 인스턴스의 종류 차원 + `dei:TradingSymbol`) | 6절 시총의 주식수 |
| 공개 경계 | `public_price_boundary.py`(허용 URL 경로), `tools/pages_artifact_guard.py`(허용 파일·키) | 확장 산출물은 지금 공개 대상 아님 → 가드 변경 없음 |
| 운영 504 | `universe/universe_codes.py`·`universe_codes_v1.json`(고정 504), `universe/sec_qgv2.py` | **불변 기준선**. 확장 카탈로그와 별도 |

## 3. Codex Draft PR 인수 검증 (I0) — Main이 할 일

PR이 오면 아래 순서로 본다. 결과는 PR 댓글이 아니라 오너 보고와 인수 기록에 남긴다.

1. **기준·범위:** PR 기준 SHA = 그때 canonical인지, 변경 파일이 1절의 "쓸 수 있는 곳" 안인지(`git diff --name-only` 대조). 밖이면 인수 보류.
2. **재사용:** 2절 표와 겹치는 새 클래스·함수가 있으면 이유를 묻는다(중복 구현은 고치게 함).
3. **시험 재실행(Main 환경):** 새 시험 + 회귀 묶음 `test_universe_*`, `test_sec_universe_*`, `test_global_universe_contracts.py`, `test_us_listings_pit_universe.py`, `test_pages_artifact_guard.py`, `test_spec_direction_guard.py`, 전진검증 시험. 건너뛴 시험이 있으면 PASS로 세지 않는다.
4. **독립 반례(Main이 따로 작성, 저장소 밖 스크래치):** C01~C12를 Codex 시험과 다른 입력으로 다시 만든다. 특히 C04(같은 사건 두 번 → 해시 불변), C09·C10(부분 실패 → 직전 검증본 유지), C11(공개·로그에 sentinel 없음).
5. **운영 불변:** `universe_codes_v1.json` 바이트 동일, Pages 빌드 파일 목록·고정 해시 동일, 원장·`sec-qgv2.json` 생성 경로 미변경, 워크플로 미변경.
6. **판정 기록:** `구현 / 시험 / 통합 / 배포 / 실자료` 칸을 따로 적는다. 실자료를 쓰지 않았으면 `NOT_RUN`. 병합은 오너 승인 뒤.

## 4. 증분 갱신 설계 (E1-B, I2) — 설계만, 실행 없음

**원칙:** 기존 7샤드 정기 실행(`sec-daily-public-inputs.yml`)·T-FRESH·연속 성공 집계·중앙 V 단계와 섞지 않는다. 처음에는 **별도 워크플로 파일의 수동 실행(`--dry-run`)만** 만든다. 일정 추가는 측정 뒤 별도 승인.

단계: `collector → normalize → diff → validate → snapshot → receipt`

| 단계 | 하는 일 | 실패 시 |
| --- | --- | --- |
| collector | ① 상장 목록: SEC `company_tickers_exchange.json`(현재 지도) + 거래소 디렉터리(약관 확인 뒤) ② SEC 공시 변경분: EDGAR 일일 색인(`/Archives/edgar/daily-index`, 매일 밤 약 22:00 ET부터 생성)에서 전날 접수된 CIK만 뽑고, 그 CIK의 submissions·companyfacts만 받음 ③ 주 1회 대조: `companyfacts.zip`·`submissions.zip`(매일 약 03:00 ET 재게시) | 원본 바이트 해시만 남기고 중단. 부분 원본으로 새 스냅샷을 만들지 않음 |
| normalize | E1-A `normalize_security_record`(종류·거래소·식별자 판정) | 거절 사유 코드로 남김 |
| diff | 직전 검증 스냅샷과 비교: 신규·종료·티커/거래소/종류 변경 | — |
| validate | E1-A `validate_catalog`(발행사-증권 연결·중복·시각 역전) | 새 스냅샷 미발행, `error_codes` 갱신 |
| snapshot | 결정적 직렬화·해시, 원자적 교체(임시 파일 → 이름 바꾸기) | 직전 검증본 유지 |
| receipt | `attempted_at`·`last_success_at`·`source_cutoff_at`·`added/ended/changed/unchanged`·`ambiguous`·`error_codes`·`input_hash`·`previous/new_snapshot_version` | 실패해도 receipt는 남김 |

- **요청 예산:** SEC 공식 한도 10 요청/초(2026-10-29 확인). 자체 상한 5 요청/초 이하, `SecCollectionClient` 재사용. 매일 전 종목 companyfacts 반복 호출 금지(변경 CIK만).
- **저장:** 원본은 기존과 같이 비공개 원자료 저장소 릴리스(공개 저장소·Pages 아님). 스냅샷·receipt도 비공개. 공개 파일 없음.
- **사건 시각:** `effective_at`(효력)·`available_at`(공개)·`collected_at`(수집)·`as_of`(평가)를 따로 저장. 모르는 시각을 수집 시각으로 채우지 않는다(`NOT_VERIFIED`).
- **측정할 것(dry-run에서):** 대상 발행사·증권 수, 하루 변경 CIK 수, 요청 수·시간, 원본 크기, 재실행 해시 동일 여부, 중단 뒤 재개. 지금은 모두 `NOT_RUN`.

## 5. 공급원·비용·사용권 (2026-10-29 공식 문서 확인분)

"미확인"은 미확인으로 둔다. 비용 0은 공식 문서에 요금이 없다는 뜻일 뿐 계약 확인이 아니다.

| 자료 | 공급원 | 갱신 | 한도 | 비용 | 수집 | 서버 보관 | 파생 점수 | 공개 집계 | 공개 회사별 | 근거(확인 2026-10-29) | 상태 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 재무·공시 | SEC EDGAR API·bulk ZIP | 실시간(API), 매일 03:00 ET(ZIP), 매일 밤(색인) | 10 요청/초, User-Agent 필수 | 요금 표시 없음 | 허용(공정 접근 정책 안) | 명시 조항 없음 | 지금 504에 운영 중 | 운영 중(504) | 운영 중(504, `sec-qgv2.json`) | sec.gov "Accessing EDGAR Data", "EDGAR APIs" | 504 범위 PERMITTED(운영 관행). 확장 범위도 같은 근거지만 **양이 10배 이상이라 dry-run 측정 뒤 승인** |
| 현재 상장 목록 | SEC `company_tickers_exchange.json` | "주기적" | 위와 같음 | 같음 | 허용 | 명시 없음 | 해당 없음 | 미확인 | 미확인 | 같음 | UNVERIFIED(종류주·ETF 구분 칸 없음) |
| 종류·ETF 구분 | Nasdaq Trader 기호 디렉터리(`nasdaqlisted.txt`·`otherlisted.txt`) | 하루 여러 번 | 표시 없음 | 표시 없음 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 정의 페이지 확인. 이용 약관 페이지는 이번에 열리지 않음(404) | UNVERIFIED — 약관 확인 전 수집 안 함 |
| 물가(CPI-U) | BLS Public Data API v2 | 월 1회 발표 | v2: 하루 500회·50계열·20년, v1: 25회 | 요금 표시 없음(v2 등록 필요) | 허용 | 허용(최종 이용 통제 없음) | 허용(출처·조회일·면책 문구) | 허용(같은 조건) | 해당 없음 | bls.gov/developers API FAQ·이용 약관 | PERMITTED(조건: 조회일·면책 문구 표기) |
| EOD 가격 | IEX HIST(중앙 V가 이미 사용) | T+1 | 파일 1개/일 8~15GB | 요금 없음 | 허용 | 허용 | 약관에 파생 조항 없음 → 서면 확인 대상 | 같음 | 같음 | `daily_data_pipeline/FREE_SOURCE_COMBINATION_20261018.md` | 중앙 V 용도만 승인. **확장 시총 용도는 오너 결정 대기(EXP-PRICE)**. IEX 마지막 체결가는 공식 종가 아님 |
| EOD 가격(유료 후보) | Tiingo·Alpaca 등 | — | — | 미확인 | — | 약관상 제한 있음(위 문서) | — | — | — | 같음 | BLOCKED_ON_LICENSE. 구매·계약 진행 안 함 |
| 주식수 | SEC 표지 `dei:EntityCommonStockSharesOutstanding`(종류별, `sec_cover_shares.py`) | 공시 때 | SEC와 같음 | 같음 | 허용 | 명시 없음 | 504 M3에 운영 중 | — | — | 기존 코드 | 504 범위 운영. 표지 미확인 186/504(M3-COVER) 문제가 확장에서도 커짐 |
| 과거 상장폐지·지수 구성·가격(PIT) | CRSP 등 | — | — | 미확인 | — | — | — | — | — | — | BLOCKED_ON_DATA / BLOCKED_ON_LICENSE |

## 6. 물가조정 시총 $200m 필터 통합 설계 (E2, I3) — 권리 확인 뒤

> **2026-10-30:** 오너 결정(DC-28)으로 확장 모집단은 네 기준(거래소·시총 약 $200m·거래대금 약 $1m·주가 약 $2~5)으로 정의하고 ADR을 포함한다. Main은 시총 하한을 명목으로 읽었다(오너 확인 대기, `EXP-CPI-POLICY`). 확인되면 이 절의 CPI 부분은 #418 과거 모집단 참고로만 남는다. [EXPANDED_DEFINITION_20261030](EXPANDED_DEFINITION_20261030.md).

- `U-US-CAP200-REF`는 `U-US-DISCOVERY` 위의 **연구용 필터**다. Universe504·공식 QGV를 바꾸지 않는다.
- **시총(발행사, 기준일 d):** 종류주마다 `가격(d, 그 종류의 상장, 권리 확인된 EOD) × 그 종류의 표지 주식수(available_at ≤ d 중 최신)`를 구하고, `share_class_groups` 규칙(같은 경제적 권리)에 맞는 종류만 더한다. 희석 가중평균 주식수를 대신 쓰지 않는다. 한 종류라도 가격·주식수가 없으면 발행사 시총은 `NOT_VERIFIED`(일부 합산 금지). 주식수 기간 끝과 가격일이 분할을 사이에 두면 `CAP_BASIS_MISMATCH`.
- **문턱(d):** `200,000,000 × CPI(d 시점에 이미 발표된 최신 월) ÷ CPI(기준)`. 기준은 #418의 **연구 가정**(2009년 CPI-U 연평균). 계열 ID·발표일·vintage를 함께 기록한다. 책 원문과 같다고 쓰지 않는다.
- **분모를 따로 센다:** 검색 가능 발행사/증권 수 ≥ 시총 판정 가능 수 ≥ 문턱 이상 수 ≥ QGV 계산 가능 수 ≥ 공식 후보 수. 각 단계에서 빠진 이유(`NOT_VERIFIED`·`MODEL_UNSUPPORTED`·`IDENTITY_AMBIGUOUS` 등)를 센다.
- **확장 QGV:** 확장 연구용 비교 모집단으로 백분위를 다시 계산한다(`score_universe` 값을 따로 둠). 504 점수를 복사하지 않고, 공식 리더보드에 섞지 않는다.
- **합성 시험만 지금 가능:** 기준일 일치, CPI 발표 전후, 문턱 경계값(같음·1달러 차), 종류주 중복, 주식수 결측, 분할 사이 기간.

## 7. 백테스트 결과 게시 계약 (E3, I4) — #417·#418 연결

- **계산은 웹 밖에서만.** 웹·Pages에는 계산 모듈, 과거 가격, 종목별 장부·순위·NAV를 올리지 않는다. 9.1 Lab에 실행 버튼을 만들지 않는다.
- **게시 파일(제안, 별도 PR·승인):** `lab-results.json`, 스키마 `lab-results/1`. 허용 키만 통과(가드에 새 규칙):
  - 실험 단위: `experiment_id`, `universe_id`, `run_as_of`, `data_manifest_hash`, `method_version`, `period`, `cost_basis`, `quality_state`, `oos_state`, `rights_state`.
  - 지표(전략·기간 단위 집계만): CAGR·변동성·최대 낙폭·샤프·회전율·표본 수. 회사별 행, 가격, 일별 NAV 곡선은 v1에서 금지.
  - 결과가 없으면 `quality_state: BLOCKED_ON_DATA`와 사유만. 숫자를 지어내지 않는다.
- **지금 차단:** 과거 PIT·상장폐지·가격 이용권 없음 → #417 실데이터 `NOT_RUN`, #418 `BLOCKED_ON_DATA`·`OOS_NOT_ESTABLISHED`. 9.1 Lab은 "실증 결과 미확보 / BLOCKED_ON_DATA"만 보일 수 있다.
- **충돌(발견):** #417 `research/qgv_backtest/config.py` 12행은 명세의 `scoring_source_sha == bb57398c…`와 `calc_version == v2_factors.CALC_VERSION`을 요구한다. 오늘 #393이 병합되면 `CALC_VERSION`이 `qgv2-calc/2026-10-23.1`이 되어 #417을 canonical과 맞추는 순간 설정 검사가 실패한다. **#417 담당이 명세를 새 점수 원본(병합 뒤 SHA·23.1)으로 다시 고정**해야 한다(EXP-417-REPIN). Main은 #417 파일을 고치지 않는다.

## 8. 회귀·충돌 점검 (지금 상태)

| 대상 | 점검 | 결과(2026-10-29) |
| --- | --- | --- |
| Universe504 | `universe_codes_v1.json`·Worker 목록을 확장 작업이 건드리는가 | 지금 변경 없음. Codex 경계에 금지로 명시 |
| 공식 QGV·중앙 V | 확장 점수가 `sec-qgv2.json`·`qgv-official.json`에 섞이는가 | 섞이는 경로 없음(확장 산출물은 비공개) |
| TARGET v1 | 확정 숫자 검증(calc_version) | #393 뒤 재기록 PR 필요(중앙 V 계획 §5, 확장과 무관) |
| 전진검증 원장 | 확장 작업이 원장 단계·키를 바꾸는가 | 변경 없음. 원장은 정기 실행 V 단계 앞에서 따로 올림 |
| 새 프론트엔드 | 1.1 검색(DC-23)은 Universe504만 | 확장 검색은 E4에서 별도 PR(분할 색인, 504와 구분 표시) |
| 가드 | 공개 허용 파일 추가 여부 | 없음. `lab-results.json` 추가는 E3 별도 PR |
| 연구 #417 | calc_version 고정 | 위 7절 충돌 |

## 9. 다음 작업과 승인 항목

**Main 다음 작업(승인 불필요, 문서·검토만):**
1. 이 문서와 DC-27을 PR로 올림(병합은 승인 뒤).
2. Codex Draft PR이 오면 3절 순서로 인수 검증하고 보고.
3. 4절 dry-run 워크플로 초안은 E1-A 인수 뒤 별도 PR(실행·일정은 승인 뒤).

**오너 결정이 필요한 것(USER_DECISIONS_PENDING `EXP-*`):** 아래 표는 그 목록과 같다.

| 번호 | 무엇 | 결정 전 동작 |
| --- | --- | --- |
| EXP-LISTING-SRC | 상장 목록 원본: SEC 지도만 / + Nasdaq Trader 디렉터리(약관 확인 필요) | SEC 지도로 설계만, 실수집 없음 |
| EXP-DRYRUN | 별도 워크플로 수동 dry-run 1회(비공개 저장, 공개 없음) | 실행 안 함 |
| EXP-SCHED | 증분 갱신 정기 일정 | 없음 |
| EXP-PRICE | 확장 시총용 가격: IEX HIST 확장 사용(서면 확인 포함) / 유료 계약 / 보류 | 시총 판정 `NOT_VERIFIED` |
| EXP-PUBLIC | 확장 카탈로그·점수 공개 범위 | 비공개 |
| EXP-OFFICIAL | 공식 모집단 승격 | 하지 않음(Universe504 유지) |
| EXP-417-REPIN | #417 점수 원본 재고정(#393 뒤) | #417은 Draft 유지 |
| LAB-PUBLISH | 9.1 Lab 게시 계약 `lab-results/1` 채택 | 9.1은 BLOCKED_ON_DATA 표시만 |
