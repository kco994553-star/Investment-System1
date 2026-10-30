# 확장 모집단 — #422 인수 결과 · E1-B / E2 / 백테스트 경계 설계 (Main, 2026-10-29)

> **2026-10-30 갱신:** 오너가 확장 정의를 정했다(DC-28): 네 기준(거래소·시총 약 $200m·거래대금 약 $1m·주가 약 $2~5), ADR 포함. Main은 시총 하한을 명목으로 읽었다(오너 확인 대기, `EXP-CPI-POLICY`). 확인되면 §4.1~4.2·4.8의 CPI 부분은 #418 과거 모집단 참고로만 남는다. 숫자 제안·공급처 약관·역산 시험은 [EXPANDED_DEFINITION_20261030](EXPANDED_DEFINITION_20261030.md).
> **상태:** 인수 검토 기록 + 설계 문서다. 코드·워크플로·일정·공급원 계약·공식 모집단·공개 범위는 바꾸지 않았다. 실수집·서버 저장·병합·배포는 각각 오너 승인 뒤다.
> **근거:** 오너 지시(2026-10-29 2차)와 [MAIN_INTEGRATION_PLAN_20261029](MAIN_INTEGRATION_PLAN_20261029.md). Codex 문서(#422)는 `E0_AUDIT`·`E1A_CONTRACT`·`SOURCE_RIGHTS`·`E1B_E2_PLAN`·`HANDOFF`이다.
> **방법:** 다관점 검토를 했다. 관점은 식별 / 시점 / 실패·결정성 / 통합 넷이고, 검토자마다 독립 반례 시험을 따로 썼다. 지적마다 재현과 현실 경로 반박 검증을 2회씩 했다. 설계 4건(E1-B·공급원·E2·백테스트)과 완결성 비평 1회가 이어졌다. Main은 전체 시험과 저장소 가드를 직접 돌렸다. 검토용 스크립트·시험은 세션 스크래치에만 두고 저장소에 넣지 않았다.

## 0. 기준

- canonical `3f3ccd2f`(#411 병합, 13:39 UTC). #422 HEAD `a30b54bb3b7bf8da3e6736f85bfc61d99fdc414b`(base `282382a7`, 커밋 2개 `4498e39d` → `a30b54bb`).
- #422는 Draft이고 mergeable_state는 clean이다. canonical과 병합할 때 텍스트 충돌이 없다(`git merge-tree`).

## 1. #422 (E0/E1-A) 인수 결과

### 1.1 판정

**병합 준비 완료. 병합을 막는 결함은 없다.** 병합은 오너 승인 뒤에 하고, 그 전에 두 가지를 다시 확인한다.

- **조건 1:** 병합 직전에 canonical을 #422에 합치고(merge 커밋, 이력 재작성 없음) 최신 기준에서 CI 6개가 녹색인지 다시 본다. PR CI는 11:21에 당시 base `282382a7` 기준으로 돌았고, 그 뒤 canonical에 사슬 #393~#405와 #411이 들어왔다.
- **조건 2:** 바뀐 파일이 여전히 신규 10개뿐인지 다시 확인한다.

E1-B를 실가동하기 전에는 아래 1.4의 **PIT-F1·PIT-F3 규칙**을 E1-B 어댑터에 넣어야 한다.

### 1.2 확인한 것

| 항목 | 결과 | 근거 |
| --- | --- | --- |
| CI 6 + build | **녹색** — ingest-and-gate·validate·presentation·guard·repository-guard 성공, build 11:21→12:04 성공 | a30b54bb check runs |
| 최신 canonical 기준 재확인(Main 로컬, canonical `3f3ccd2f` + #422) | 저장소 가드: 단위 시험 142 OK, `autonomy_gate_a_guard.py diff` 위반 0·기록 10·`READ_ONLY`, privacy·email·repository PASS. **전체 파이썬 4,115 통과**(298 subtests) = canonical 4,025 + 신규 90. Pages 빌드·아티팩트 가드 PASS(공개 파일 137개 — #422 전과 같음). 방향 검사 0건 | 이 세션 실행 로그 |
| 파일 범위 | **신규 10개(A)만, 수정·삭제 0.** 기존 코드 중 새 모듈을 import하는 곳 없음 → Pages·가드·워크플로·중앙 V·프론트엔드·전진검증 원장·Universe504 영향 없음. 새 모듈은 표준 라이브러리와 `universe.resolve.company_id_for`만 쓰고 네트워크·`print`·logging 없음 | `git diff --name-status 282382a7 a30b54bb`, grep |
| 시험 수치(서로 다른 기록, 섞지 않음) | ① Codex **3,757 통과 = 리뷰 보완 전** 전체(커밋 4498e39d, 합성 80개 포함; Main은 재실행하지 않음 — 그 시점 수집 수 3,757은 4498e39d 기준과 맞음) ② Codex **203 통과 = 보완 후** 관련 묶음 → **Main이 a30b54bb에서 그대로 203 통과 재현** ③ 같은 묶음을 canonical 위에서 돌리면 204(사슬 병합으로 기존 시험 +1, 신규 코드와 무관) ④ 신규 시험 90개: Python 3.11·3.12·3.13에서 모두 90 통과 ⑤ Main canonical+#422 전체 4,115 | 실행 로그 |
| 독립 반례 | 검토자가 PR 시험과 다른 입력으로 따로 썼다: 식별 53개, 시점 87개, 실패·결정성 62개 + 결함 재현 11개, 통합 대조. C01~C12를 모두 독립 시험으로 다시 확인했다(C11 '로그' 채널은 모듈에 출력 경로가 없음을 확인) | 세션 스크래치 |

### 1.3 맞게 동작함을 확인한 성질

- **영구 ID:** issuer_id는 검증된 CIK에서 만든다(`expanded_catalog.py:116-123`, `resolve.company_id_for`). security_id는 공급자 문자열을 그대로 키로 쓰고 티커를 키로 쓰지 않는다.
- **같은 CIK 종류주(C01):** 발행사 1, 증권 2로 센다. BRK.A/BRK.B 형태도 같다.
- **티커 재사용(C02·C12):** 다른 security_id가 되고 옛 구간이 보존된다. Universe504 자료는 그대로다.
- **상장·상폐·티커·거래소·종류·이름 변경·합병 이력:** 구간으로 보존된다.
- **시점 인과:** `available_at > cutoff` 또는 `effective_at > cutoff`인 사건은 그 스냅샷에 적용하지 않는다(C03 적용 기준).
  - `available_at ≤ collected_at`을 강제한다.
  - 시각이 없거나 거꾸로면 거절한다. 현재 시각으로 채우지 않는다(C05).
  - 시간대 오프셋·소수 초를 바르게 비교한다.
  - 여러 cutoff로 재생해도 결과가 단조롭고 재현된다.
- **실패 보존(C09·C10):** 429·중단·손상, 무효 사건, 충돌 사건이 나면 **이전 스냅샷 객체와 bytes가 그대로** 돌아오고 `FAILED` receipt가 남는다. 실패해도 `last_success_at`은 그대로다.
- **결정적 hash:** 입력 순서, `PYTHONHASHSEED` 0·1·random·12345에서 같은 hash가 나온다.
- **중복 사건(C04):** 같은 event_id·같은 내용은 1회만 적용되고 재실행해도 hash가 같다. 같은 event_id에 다른 내용이 오면 거절한다.
- **민감 문자열(C11):** 비밀값 형식의 이름·ID는 차단된다(fail-closed). receipt에는 집계만 들어간다.
- **ETF·CEF·우선주(C06):** 자동 적격 없음. ADR·REIT는 PENDING 정책 상태로 남는다(C07). CIK가 모호하면 `IDENTITY_AMBIGUOUS`로 잘못 합치지 않는다(C08).

### 1.4 발견 (반박 검증 2회 뒤)

| ID | 내용 | 판정 | 처리 |
| --- | --- | --- | --- |
| **PIT-F1** (= 실패·결정성 F1) | 미래 사건(`available_at` 또는 `effective_at` > cutoff)을 받을 때 형식만 검사하고 원장에 넣는다. 그 시점이 와서 무효로 드러나면 **그 뒤 갱신이 모두 실패**한다. 직전 스냅샷은 유지되고 데이터 손실은 없다 | **중요 — E1-B 전 해결, 병합 차단 아님**(코어가 아직 어떤 수집기에도 연결되지 않음) | E1-B 규칙: 어댑터는 cutoff 시점에 **공개·효력이 모두 지난 사건만** 코어에 넣는다. 미래 사건은 어댑터의 비공개 대기열에 둔다(§2.3.4). Codex 후속(선택): 받을 때 예상 상태로 검증하거나 `EVENT_NOT_YET_DUE`로 거절하고, 정정·철회 계약을 만든다 |
| **PIT-F3** | C03은 '적용'은 지키지만, 스냅샷 bytes·hash(`universe_version`, `input_manifest_hash`)에는 as_of 뒤에 공개된 사건도 들어간다. 그래서 같은 as_of를 나중에 다시 재생하면 hash가 달라진다 | 해석 필요(검증자 1명 사소, 1명 의도된 설계) | 위 E1-B 규칙으로 해소된다. 오너 결정 `EXP-C03-MEANING`(권장: "포함하지 않음"을 E1-B 규칙으로 보장) |
| ID-8 | `sk-` 비밀값 패턴이 접두어만 맞아도 정상 이름·ID까지 거절한다 | 사소(2/2 확인) | Codex 후속: 단어 경계 추가 |
| 통합 F6 | C11 시험의 `capsys.readouterr()` 두 번째 호출은 항상 비어 있어, 그 검사는 실제로 아무것도 확인하지 않는다 | 사소(2/2 확인) — 코드 누출은 없음 | Codex 후속: 한 번 읽은 결과로 out·err 검사 |
| 통합 F8 | E2 문서가 명목 $200m과 물가조정 $200m을 따로 두지 않았다 | 사소(2/2 확인) — 문서만 | 이 문서 §4가 보완 |
| ID-1 | 같은 시각에 두 속성이 함께 바뀌는 경우(거래소+티커, 이름+티커 de-SPAC)를 표현할 수 없어 batch 전체가 거절된다 | 의도된 차단(문서화됨) | E1-B는 HELD로 둔다. 코어 확장은 E1-B.0b 결정 |
| ID-2 | 재상장하면 새 security_id가 필요하다(`SECURITY_ID_REUSED`) | 의도된 차단(E1A_CONTRACT) | `EXP-ID-RELIST`(권장: 코어 유지 + 비공개 식별 지도로 상장 회차를 연결, §2.2) |
| ID-3 · PIT-F2 | 같은 시각 지주사 개편의 승계 연결 불가, 사전 공지 상장·상폐의 철회·변경 불가 | 의도된 차단 | 정정 계약과 함께 Codex 후속 |
| ID-4 · ID-5 | 같은 티커를 두 거래소에서 동시에 허용함, BRK.B/BRK-B 구분자를 맞추지 않음 | 사소 | E1-B 어댑터에서 기호를 정규화하고 동시 중복은 `IDENTITY_AMBIGUOUS`로 둔다. 코어 후속은 선택 |
| F2~F5·F7 | 수집 시각이 실행 시각보다 늦은 중복 사본을 조용히 버림, batch 분할에 따른 hash 차이, 유니코드 NFC/NFD 차이, 손으로 만든 레코드의 예외 경로, receipt 필드 이름이 계약과 다름 | 사소 또는 의도(1/2) | 어댑터 규칙(NFC 정규화, 실행 시각 상한 검사)과 receipt 필드 대응표로 처리 |
| 통합 F1·F3·F4·F5 | E0_AUDIT의 열린 PR 표는 그 시점 기록이다. #422 문서는 5개인데 Main 계획은 2개만 예상했다. `global_universe.py`의 식별 클래스를 재사용하지 않았다. HANDOFF에 끝맺지 않은 문장이 있다 | 문서 차이 — 결함 아님 | Main 계획을 문서 5개 기준으로 고친다. global_universe 비재사용은 설계 메모로 남긴다(동작 문제 없음) |

**Codex에 보낼 후속(병합을 막지 않음):** PIT-F1 받기 시점 검증 또는 거절, 정정·철회 계약(PIT-F2·ID-3), ID-8 정규식, F6 시험 수정, 같은 시각 두 속성 변경 표현(ID-1, 결정 뒤), receipt 필드 대응표 문서화.


## 2. E1-B 설계: 현재 상장 목록 주기 수집과 자동 갱신

이 문서는 설계만 다룬다. 실제 수집, 서버 저장, 워크플로 추가, 일정 등록은 하지 않았다.

- 기준 코드: #422 HEAD `a30b54bb`(wt-422h). 확인용으로 canonical `3f3ccd2f`에 #422를 로컬 병합한 wt-422m도 함께 봤다.
- 실제로 실행한 것: 세션 스크래치(저장소 밖)의 합성 프로브 2개뿐이다(재생 프로브·경계 프로브). 네트워크와 저장소 쓰기는 없었다.

### 2.0 코어에서 확인한 제약

#422 코어를 프로브로 직접 확인했다. 아래 제약이 E1-B 설계를 정한다.

| # | 사실 (file:line) | 프로브 결과 | E1-B에 주는 뜻 |
|---|---|---|---|
| 1 | `validate_catalog`는 `source_rights_state=='UNVERIFIED'`이고 `quality=='SYNTHETIC_NOT_LIVE'`인 스냅샷만 받는다 (expanded_catalog.py:259) | `quality=LIVE_DRY_RUN` 또는 `rights=PERMITTED`이면 `SCHEMA_INVALID` | 지금 코어로는 실자료 스냅샷을 만들 수 없다. 라벨을 거짓으로 붙이지 않는다. 그래서 E1-B.0(코어에 추가만 하는 변경)이 먼저 필요하다 |
| 2 | receipt 값이 합성 전용으로 고정돼 있다. status는 `SYNTHETIC_PASS`/`FAILED`, source_id는 `SYNTHETIC_SUPPLIED`, `real_data_executed=False` (expanded_catalog_snapshot.py:84, 100, 116-117) | 확인함 | 1번과 같이 E1-B.0에서 푼다 |
| 3 | 저장본을 다시 읽는 함수가 없다 (expanded_catalog_snapshot.py 155행 전체) | snapshot_bytes → JSON → `normalize_security_record`로 record 재구성 → genesis에서 `apply_listing_events` 재생. 결과 bytes와 hash가 완전히 같았다 | 저장본은 "재생 후 hash 대조"로 읽는다. 검증기를 새로 만들지 않는다 |
| 4 | `source_status`는 `HTTP_429`/`SOURCE_INTERRUPTED`/`SOURCE_CORRUPT`/`OK`만 받는다 (expanded_catalog_snapshot.py:14, 135) | 429가 나면 이전 객체를 그대로 돌려주고 `last_success_at`도 유지한다 | SEC 오류 코드를 이 세 개로 바꿔 넘긴다. 자세한 코드는 비공개 manifest에만 남긴다 |
| 5 | batch는 전부 성공하거나 전부 실패한다 (events.py:89-111) | 정상 50건과 무효 1건을 함께 넣으면 `FAILED(SECURITY_NOT_ACTIVE)` | 넣기 전에 문제 사건을 걸러야 한다 (§2.3.4) |
| 6 | 같은 증권에 같은 effective_at 사건이 둘이면 거절한다. 변경 사건 하나는 필드 하나만 바꿀 수 있다 (events.py:44-50, 69-73) | 티커와 거래소가 동시에 바뀌는 경우(PSKY→SKYD 형태, sec_universe_collection.py:22-25)는 `EVENT_ORDER_AMBIGUOUS` 또는 `EVENT_PAYLOAD_MISMATCH`로 실패 | 이런 사건은 HELD로 보류한다. 표현하려면 코어 확장 결정이 필요하다. 시각을 조금 어긋나게 꾸미는 방법은 쓰지 않는다 |
| 7 | MERGED는 승계 증권이 카탈로그에서 활성일 때만 된다 (events.py:75-76) | 카탈로그 밖 기업이 인수하면 `MERGER_TARGET_UNRESOLVED` | 승계 증권을 못 찾으면 DELISTED로 낸다 (프로브 PASS). 합병 근거는 source_ref에 남긴다 |
| 8 | 재상장하면 새 security_id가 필요하다 (events.py:59) | 같은 ID로 재상장하면 `SECURITY_ID_REUSED` | ID에 상장 회차(epoch)를 넣는다 |
| 9 | 정책 거래소는 NASDAQ/NYSE/NYSE_AMERICAN/BATS다 (expanded_catalog.py:57) | `OTC`는 Rejection(`EXCHANGE_UNSUPPORTED`) | SEC 목록의 OTC 행은 카탈로그에 넣지 않고 거절 수만 센다 |
| 10 | 재실행, 재수집, 나눠서 적용하는 경우 | 같은 batch를 다시 넣으면 같은 객체가 나온다. collected_at만 다른 재수집은 hash를 바꾸지 않는다. 2개 batch로 나눠 넣은 결과와 1개 batch 결과가 같았다 | checkpoint 재개가 정합하다는 근거다 |
| 11 | LISTED마다 실제 effective_at(=valid_from)이 필요하다 (events.py:27) | 해당 없음 | SEC 목록에는 상장일이 없다. 그래서 초기 적재가 막힌다 (§2.3.3) |

### 2.1 공급원과 갱신 주기

| 원본 | 쓰는 곳 | URL 허용 목록 | 승인 뒤 제안 주기 | 요청 수 | 권리 |
|---|---|---|---|---|---|
| SEC `company_tickers_exchange.json` | 현재 (cik, name, ticker, exchange) 관측 | 있음 `SEC_TICKERS_EXCHANGE` (public_price_boundary.py:53), 호출 함수 `fetch_ticker_exchange` (sec_universe_collection.py:33-37) | 미국 영업일 1회. 일일 작업(22:17 UTC, workflow:4)과 겹치지 않는 시간 | 하루 1 | 수집·비공개 보관 PERMITTED(sec.gov 웹 배포 문구, §3 표) |
| EDGAR daily-index `form.YYYYMMDD.idx` | 전날 접수된 25/25-NSE/8-A12B/8-A12G/15-12B/8-K/8-K12B | **없음.** 패턴 추가가 필요하다 (public_price_boundary.py:41-55) | 영업일 1회(전 영업일분) | 하루 1 | 수집 PERMITTED |
| submissions `CIK*.json` | form, acceptanceDateTime, 8-K items | 있음 `SEC_SUBMISSIONS` | 색인에 나온 CIK만 | 하루 수십~수백 (측정 필요) | 수집 PERMITTED |
| cover XBRL instance | 종류별 TradingSymbol, Security12bTitle, SecurityExchangeName | 있음 `SEC_XBRL_INSTANCE` (:54) | 신규 CIK와 변경 사건 CIK만. 초기 적재 때 1회 | 초기 수천 (측정 필요) | 수집 PERMITTED |
| Nasdaq Trader 디렉터리 | ETF·test issue 구분 | 해당 없음 | 사용권 계약 전 사용 안 함 | 0 | BLOCKED_ON_LICENSE (#422 SOURCE_RIGHTS.md:32, Nasdaq 약관 확인) |
| bulk `submissions.zip` | 주간 대조 | 32 MiB 응답 상한(sec_collection.py:30)을 넘을 것으로 예상 | 보류 | 해당 없음 | 해당 없음 |

**증권 종류 판정.** SEC 목록에는 종류 칸이 없다. 필드는 cik, name, ticker, exchange뿐이다 (sec_universe_collection.py:87). 종류는 다음 두 가지로 판정한다.

- cover의 Security12bTitle
- submissions의 SIC, entityType, N-계열 공시 이력

판정할 수 없으면 `TYPE_UNKNOWN`으로 HELD한다. ETF와 CEF를 구분할 수 없을 때도 HELD한다. 자동 적격은 없다 (C06/C07 유지).

**거래소 판정.** 거래소는 cover의 SecurityExchangeName을 우선한다. 목록의 exchange 값은 신호로만 쓴다. 목록에서 NYSE American과 NYSE Arca가 따로 구분되는지는 UNVERIFIED이며 M1에서 측정한다.

**요청 정책.** `SecCollectionClient` 하나만 쓴다. 이미 0.2초 간격, 최대 5회 시도, Retry-After 60초 이하 규칙이 들어 있다 (sec_collection.py:32-35, 226-298).

- 새 하위 클래스 `ExpandedSecClient`를 만든다. `UniverseSecClient`(sec_universe_collection.py:141-158)처럼 `_request`만 호출한다.
- 허용 CIK는 직전에 검증한 관측 집합과 오늘 색인에 나온 CIK다.
- 504 전용 `UniverseRegistry`, `daily_partition`, `collect_universe`(:117-147)는 호출하지 않는다.
- 일일 작업과 동시에 돌리지 않는다. 두 작업이 각각 초당 5회라 합치면 SEC 한도 10회에 닿는다.

### 2.2 영구 security_id

| 선택지 | 영구성 | 종류주 구분 | 재사용 위험 | 비용·권리 | 판정 |
|---|---|---|---|---|---|
| A. CIK + cover 종류 키 (StatementClassOfStockAxis member, dei:TradingSymbol; sec_cover_shares.py:90-160) | CIK는 영구다. member 이름은 제출자가 바꿀 수 있다 (안정성 UNVERIFIED) | 된다 | 없다 | 무료, 수집 PERMITTED | **주 근거** |
| B. OpenFIGI share-class FIGI | 높다. 공개 영역·영구·재사용 없음(OpenFIGI 약관 확인, §3) | 된다 | 없다 | 무료 API. 키 없이 분당 25요청, 키는 계정 가입 필요(오너 조치). 설명 필드(티커·거래소) 재배포권은 UNVERIFIED | 키 가입(EXP-OPENFIGI) 뒤 교차 검증 속성으로 쓴다 |
| C. CUSIP | 사명 변경이나 기업행사로 바뀐다 | 된다 | 있다 | 유료 라이선스, 재배포 제한 (UNVERIFIED) | 쓰지 않는다 |
| D. CIK + 티커 | 티커는 재사용된다 | 안 된다 | 있다 | 해당 없음 | 금지 (C02) |

**권고.** E1-B가 첫 증거를 볼 때 대리 ID를 한 번 발급하고, 비공개 식별 지도로 관리한다.

- 형식: `xs:<cik10>:<class_key>:<epoch>`. 128자 이하이고 `_ID` 정규식(expanded_catalog.py:18)에 맞는다.
- `class_key`: 종류가 하나이고 보통주로 확인되면 `COMMON`이다. 종류가 여럿이면 member local name을 쓴다.
- `epoch`: 원장에서 같은 (cik, class_key)의 LISTED 횟수에 1을 더한다. 원장만으로 결정되므로 재실행해도 같다.
- 식별 지도는 (cik, class_key)에 증거를 묶는다. 증거는 TradingSymbol 구간, member 이름 이력, 승인 뒤 FIGI다.
- member 이름이 바뀌면 다음 조건이 모두 맞을 때만 같은 종류로 잇는다. 같은 CIK, 같은 TradingSymbol, 같은 거래소가 연속 두 cover에 나와야 한다. 아니면 `IDENTITY_AMBIGUOUS`로 HELD한다. 이 규칙은 가짜 상폐·상장 사건을 막는다.
- cover가 없으면 `CLASS_EVIDENCE_MISSING`으로 HELD한다. IPO 직후, 신탁, 외국 사설 발행인이 여기에 해당한다. 티커로 ID를 만들지 않는다.

**측정할 것.** 표본 200개 CIK에서 다음 두 비율을 잰다.

- 종류 키를 확보한 비율
- 연속 filing 사이 member 이름이 바뀐 비율

이름 변화가 잦으면 B(FIGI)를 주 키로 올릴지 검토한다. 이것은 EXP-OPENFIGI 결정이 있어야 한다.

### 2.3 사건 도출

#### 2.3.1 시간 규칙

- **collected_at:** 응답을 받은 직후의 실행 UTC 시각이다. 시계는 주입할 수 있게 한다. 과거 시각으로 꾸미지 않는다.
- **available_at:** 원본이 공개된 시각이다. EDGAR 공시는 submissions의 acceptanceDateTime을 쓴다. 해석은 sec_8k_disclosures.py:234-247과 같다. 값이 없으면 HELD한다.
  - 대안: filingDate만 있을 때 그날 ET 종료 시각을 쓴다. 늦은 쪽을 고르므로 보수적이다. 오너 승인 뒤에만 쓴다.
- **목록 diff만 있는 관측(티커 등장·소멸):** 공개 시각 근거가 없으므로 엄격한 사건이 아니다. 비공개 staging에 관측 구간 `(prev_collected_at, collected_at]`만 기록한다. 기록 기준은 `OBSERVED_PUBLIC_API_UPPER_BOUND`다 (E1B_E2_PLAN.md:29-32).
- **effective_at:** 원본이 명시할 때만 쓴다.
  - 날짜만 있는 경우(8-K reportDate 등)에 시각으로 바꾸는 규칙은 승인 전까지 없다. 그때까지 `EFFECTIVE_AT_UNSTATED`로 HELD한다.
  - Form 25 접수 후 10일이라는 규칙(Rule 12d2-2(d)(1))은 원본의 명시가 아니므로 기본은 HELD다.

#### 2.3.2 사건 표

event_id는 `sec:<form>:<accession>:<security_id>:<kind>`로 만들어 재수집해도 변하지 않게 한다. raw_hash는 해당 원본 행 또는 filing 메타데이터의 정규 bytes에 대한 sha256이다.

| 사건 | 1차 근거 (SEC) | 보조 신호 (단독으로는 부족) | available_at | effective_at | HELD 조건 |
|---|---|---|---|---|---|
| LISTED | 8-A12B + cover 종류 키 | 목록에 새 행이 생김 | 8-A acceptance | 명시된 거래 개시일 | 종류 키 없음, 효력일 미명시 |
| DELISTED | Form 25 / 25-NSE, 8-K 3.01 | 목록에서 사라짐 | 25 acceptance | 명시된 경우만 | 효력일 미명시. 15-12B는 등록 종료일 뿐이라 단독 근거가 안 된다 |
| TICKER_CHANGED | 연속 cover의 TradingSymbol 변경 (같은 종류 키) | 목록 티커 변경 | 새 기호가 처음 나온 filing의 acceptance | 명시된 경우만 | 거래소도 동시에 바뀜 (§2.0-6) |
| EXCHANGE_CHANGED | cover SecurityExchangeName 변경 + 이전 거래소의 25/25-NSE 또는 8-K 3.01 | 목록 거래소 변경 | 같음 | 명시된 경우만 | 티커도 동시에 바뀜 |
| CLASS_CHANGED | cover Security12bTitle의 종류 변화 | 해당 없음 | 같음 | 명시된 경우만 | 해석이 불확실함 |
| MERGED | 8-K 2.01 + Form 25 | 목록에서 사라짐 | 25 acceptance | 명시된 경우만 | 승계 증권이 활성이 아니면 DELISTED로 낸다 |

목록에서 사라졌다는 사실만으로 DELISTED를 만들지 않는다 (E1B_E2_PLAN.md:38). 공시 근거 없이 사라진 경우는 `DISAPPEARED_UNEXPLAINED`로 비공개로만 센다. 카탈로그 상태는 바꾸지 않는다.

#### 2.3.3 초기 적재(genesis)는 막혀 있다

현재 상장된 종목의 상장일이 SEC 목록에 없다. 수집 시각을 effective_at에 넣는 것은 금지된 대체다. 선택지는 세 가지다.

- **(a)** 코어에 "관측 존재" 기준을 추가한다 (E1-B.0b, 코어 작성자 리뷰). PIT 연구에는 쓰지 못하게 표시한다.
- **(b)** 상장일을 주는 유료 원본을 쓴다 (Norgate, CRSP, 거래소 일일 목록). 지금은 BLOCKED_ON_LICENSE다.
- **(c)** 8-A12B 이력으로 근사한다. 대부분 HELD가 될 것이라 커버리지가 낮다. 커버리지는 측정 대상이다.

결정 전에는 genesis를 막는다. U-US-DISCOVERY의 검색용 현재 목록도 (a)를 승인한 뒤에만 만든다.

#### 2.3.4 batch에 넣기 전 사건 거르기

1. 원본 행마다 `normalize_security_record`를 호출한다. Rejection은 사유별로 HELD한다 (expanded_catalog.py:111-138).
2. 후보 사건마다 `apply_listing_events(previous, [e], cutoff)`로 한 건씩 시험한다. 일일 증분은 수십 건이라 비용이 작다.
3. 전체 적용이 실패하면 이분 탐색으로 충돌하는 사건을 찾는다. 이 과정도 코어 호출만 쓰고 검증을 다시 만들지 않는다.
4. 걸러진 사건은 event_id와 고정 사유만 비공개 quarantine에 남긴다.
5. dry-run에서는 걸러진 사건이 있으면 포인터를 갱신하지 않고 측정만 한다. 운영에서 "걸러낸 뒤 진행"할지 "전체 거절"할지는 오너가 정한다 (QUARANTINE-POLICY).

### 2.4 source manifest

`xcat-source-manifest/1`. 비공개이며 실행마다 하나 만든다.

| 묶음 | 필드 |
|---|---|
| 실행 정보 | run_id, attempted_at, code_sha, policy_fingerprint, rights_version, expected_previous_snapshot_hash, pointer_oid_at_start |
| 파일마다 (`files[]`) | source_id, url_template_id(public_price_boundary 키 이름), url_params(cik, accession, date만), fetched_at(=collected_at), http_status 또는 고정 코드, attempts, retry_wait_s, bytes, sha256, last_modified, rights_state, complete, asset_ref |
| 진행 상태 | cursors (§2.5) |
| 합계 | requests, bytes, wall_s, http_429, retries |
| 결과 수 | 사유별 held 수, 종류별 사건 수, 사유별 거절 수 |
| 자기 hash | manifest_hash: 자기 자신을 뺀 정규 JSON(sort_keys, compact)의 sha256 |

- `rights_version`은 SOURCE_RIGHTS 문서의 blob sha와 결정 ID로 만든다.
- `last_modified`는 지금 클라이언트가 받지 않으므로 null이다. 받으려면 E1-B.4에서 추가해야 한다.
- 다음은 넣지 않는다: 비밀값, User-Agent 연락처, 응답 본문, 회사명. 원본 bytes는 raw 묶음 asset에만 둔다.
- 코어의 `input_manifest_hash`(expanded_catalog_snapshot.py:39-41)는 사건 원장 hash다. source manifest hash와 다른 값이므로 둘 다 포인터에 기록한다.

### 2.5 checkpoint와 재개

**원본별 cursor.**
- 목록 파일: 하나라서 cursor가 없다. 받았거나 못 받았거나 둘 중 하나다.
- daily-index: 마지막으로 끝까지 처리한 영업일.
- CIK별 작업: 시작할 때 고정한 작업 목록의 위치와 목록 hash. 목록은 sha256(cik) 순으로 정렬한다. 504 `daily_partition`과 같은 해시 규칙이지만 504 레지스트리는 건드리지 않는다.

**checkpoint 파일.** `checkpoint-<seq>.json`을 asset으로 추가만 하고 덮어쓰지 않는다.
- 내용: worklist_hash, cursors, chunk 목록(이름+sha256), expected_previous_snapshot_hash, pointer_oid_at_start, rights_version, policy_fingerprint, code_sha.

**재개 (`resume_run_id`).**
1. 현재 포인터가 checkpoint의 expected와 같으면 이어서 한다. 다르면 `STALE_CHECKPOINT`로 staging을 버리고 처음부터 한다.
2. rights, policy, code_sha 중 하나라도 다르면 버린다.
3. 각 chunk의 sha256을 다시 검증한다. 맞지 않는 chunk부터 다시 받는다.

**끝나지 않은 실행.** 포인터를 바꾸지 않는다. 사건 생성과 코어 적용은 모든 chunk가 끝났을 때 한 번만 한다.

**멱등성.** 같은 원본 bytes를 넣으면 같은 event_id와 raw_hash가 나오고, 따라서 같은 snapshot_hash가 나온다 (§2.0-10에서 확인).

### 2.6 원자적 커밋과 CAS

**선택:** 비공개 raw 저장소(`kco994553-star/investment-system1-raw`)에서 두 가지를 조합한다.
- 큰 객체는 내용 주소 release asset으로 둔다.
- 포인터는 git ref로 두고 CAS로만 갱신한다.

**큰 객체.** 이름에 sha가 들어간다: `snapshot-<hash>.json.gz`, `manifest-<hash>.json`, `raw-<run>-<chunk>.tar.gz`, `receipt-<hash>.json`. 업로드와 검증은 기존 `release_for_tag`/`upload`/`download` 규칙을 그대로 쓴다. 이름과 크기로 멱등하고, 내려받은 뒤 sha를 대조한다 (raw_store_release.py:70-125).

**포인터.** 비공개 저장소의 `xcat-pointer` 브랜치에 `expanded-catalog/POINTER.json` 파일 하나만 둔다.
- GraphQL `createCommitOnBranch(expectedHeadOid=<시작 때 읽은 oid>)`로만 갱신한다. 서버가 head와 expected가 다르면 거절하므로 이것이 CAS가 된다.
- 토큰이 GraphQL을 못 쓰는 경우의 대안: REST로 blob, tree, commit(parent=expected)을 만들고 `PATCH ref force=false`(빠른 전진만)로 갱신한다. 그 직전에 GET으로 한 번 더 확인한다.
- POINTER 필드: seq, snapshot_hash, previous_snapshot_hash, as_of, source_cutoff_at, input_manifest_hash, source_manifest_hash, receipt_hash, 각 asset의 sha256, run_id, code_sha, rights_version, committed_at.

**커밋 순서.**
1. `dry_run_refresh`를 실행한다.
2. snapshot_bytes, manifest, receipt를 업로드한다.
3. 다시 내려받아 sha를 대조한다. 재생으로 읽은 hash가 같은지도 확인한다.
4. CAS 커밋을 한다.
5. 실패하면 `CAS_CONFLICT`로 끝난다. 포인터는 그대로이고, 올린 객체는 고아가 된다. 고아 객체는 해가 없으며 정리 목록에 둔다.

**거부한 대안.**

| 대안 | 거부 이유 |
|---|---|
| release asset을 포인터로 쓰기 | 조건부 쓰기가 없다. 삭제와 업로드 사이에 경쟁이 생긴다 |
| 러너 로컬 파일 rename + fsync | Actions 러너는 실행이 끝나면 사라진다. 테스트용 가짜 저장소에서만 쓴다 |
| 공개 저장소, Pages, Actions artifact·cache | 공개되거나 만료된다. 금지 패턴(test_public_price_boundary.py:140-143)과 충돌한다 |
| workflow concurrency만으로 막기 | 수동 재실행이나 다른 ref 실행을 막지 못한다 |

**미확인 (UNVERIFIED).** 토큰으로 GraphQL을 쓸 수 있는지, 비공개 저장소에 브랜치 보호 규칙이 있는지는 확인하지 못했다.

### 2.7 별도 수동 dry-run 워크플로 (초안)

파일: `.github/workflows/expanded-catalog-dry-run.yml`. 병합과 실행은 모두 승인 뒤다.

**실행 조건.**
- `workflow_dispatch`만 쓴다. `schedule`은 없다.
- 입력값:
  - `mode`: offline-fixture, fetch-measure, fetch-commit-private 중 하나
  - `confirm`: `EXP-DRYRUN`과 정확히 같아야 한다
  - `max_requests`: 기본 300, 상한 3000
  - `resume_run_id`
  - `stop_after_chunks`
- 기본 브랜치에서만 돈다.
- 권한: `contents: read`, `actions: read`.
- concurrency 그룹: `expanded-catalog-private`.
  - 일일 작업 그룹 이름을 공유하면 안 된다. 그룹당 대기 실행은 하나만 남아 기존 대기 실행이 취소될 수 있다 (workflow:15-22).

**사전 점검.**
- sec-daily-public-inputs가 실행 중이거나 대기 중이면 `SEC_BUDGET_CONFLICT`로 끝낸다.
- UTC 21:45~02:30 사이에는 시작하지 않는다.

**단계와 비밀값.**
- checkout은 `persist-credentials: false`로 한다.
- 단위 시험을 먼저 돌린다.
- 수집 단계에는 `SEC_USER_AGENT`만 준다.
- 저장 단계에는 저장용 토큰만 준다. 새 Secret을 만들지 기존 RAW_REPO_TOKEN을 재사용할지는 결정해야 한다.
- 하위 프로세스는 `env -u`로 비밀값을 지운 채 실행한다.

**정적 시험으로 금지할 것.**
- `upload-pages-artifact`, `deploy-pages`, `actions/upload-artifact`, `actions/cache`
- `git push`, `GITHUB_STEP_SUMMARY`, `schedule:`, `pages: write`, `id-token`
- public-cockpit 디렉터리 생성

**로그.** 다음 형식의 고정 줄만 남긴다.

`XCAT_DRYRUN status= reason= requests= bytes= wall_s= committed=`

회사명, 티커, 종목 수는 비공개 receipt에만 둔다.

**Pages 이중 방어.** pages_artifact_guard는 모르는 파일 이름을 거절한다 (pages_artifact_guard.py:191, 457-458). E1-B 파일 이름이 허용 목록에 없다는 것을 시험으로 고정한다.

### 2.8 dry-run 측정 계획

모두 아직 실행하지 않았다 (NOT_RUN).

| 단계 | 조건 | 측정 |
|---|---|---|
| M0 | 오프라인 CI | rerun hash 같음, 재개 결과 = 중단 없는 결과, CAS 1승 1패, 중단 지점별로 포인터 불변 |
| M1 | EXP-DRYRUN 뒤 1요청 | 목록 bytes·sha·시간, 행 수, 고유 CIK 수, 거래소 분포, CIK당 티커 수, OTC 비율, 거절 사유. 포인터 커밋 없음 |
| M2 | daily-index 5영업일 + 해당 submissions | 요청 수, 429 횟수, 재시도, 시간, bytes. form별 건수. 엄격 사건으로 만든 수와 사유별 HELD 수 |
| M3 | cover 표본 200개 | 종류 키 확보율, member 이름 변화율, 종류 판정 불가 비율 |
| M4 | 재실행 | 같은 raw로 오프라인 재처리 시 hash가 같은지. 다음 영업일 diff 수 |
| M5 | 재개 | `stop_after_chunks=k`로 멈춘 뒤 재개. 최종 hash가 중단 없는 재생 hash와 같은지 |
| M6 | CAS | 시험 브랜치에서 같은 expected로 두 번 실행. 1번은 commit, 1번은 CAS_CONFLICT여야 한다 |

**합격선 (제안).**
- rerun과 resume hash가 100% 일치한다.
- 429가 나도 이전 스냅샷이 유지된다.
- 요청 수가 `max_requests` 이하다.
- 일일 작업과 겹친 실행이 0이다.

### 2.9 PR 계획

| PR | 내용 | 네트워크 | 필요한 승인 | 합격 시험 |
|---|---|---|---|---|
| E1-B.0 코어 활성화 (추가만, 코어 작성자 리뷰) | (a) 실자료 라벨: quality/rights 고정 목록, receipt `LIVE_DRY_RUN_PASS`, source_id 목록. (b) 결정이 나면: 관측 존재 기준, 티커와 거래소 동시 변경 표현 | 없음 | 코어 변경 합의 (DC-27/DC-09) | 기존 합성 90개 통과. 합성 라벨의 hash가 바이트 단위로 그대로다. 모르는 라벨은 거절한다 |
| E1-B.1 SEC 목록 어댑터 (순수 함수) | 엄격 파싱(중복 키·비유한수 거절), 관측 diff, normalize, HELD, 재생 로드 | 없음 | 없음 | 사라짐을 DELISTED로 만들지 않는다. 티커가 재사용되면 새 ID다. OTC는 거절로 센다. 재생 로드 bytes가 같다. rerun hash가 같다. 비밀값 sentinel이 노출되지 않는다 |
| E1-B.2 공시 근거 파서 | daily-index, submissions → 25/25-NSE/8-A/15-12B/8-K 3.01·2.01 사건, cover 종류 키(`parse_cover`/`class_symbols` 재사용), §2.3.4 거르기 | 없음 | 없음 | available_at = acceptance. 효력일 미명시는 HELD. 승계 증권이 없으면 DELISTED. 티커·거래소 동시 변경은 HELD. 15-12B 단독으로는 DELISTED가 아니다 |
| E1-B.3 checkpoint와 저장소 (가짜 백엔드) | 상태기계, manifest, 추가만 하는 checkpoint, 주입식 GitHub 비공개 백엔드, CAS | 없음 | 없음 | 모든 중단 지점에서 포인터가 그대로다. 재개 결과 = 중단 없는 결과. CAS 충돌을 처리한다. sha가 다른 다운로드는 거절한다 |
| E1-B.4 수집 클라이언트와 허용 목록 | `ExpandedSecClient`, `SEC_DAILY_INDEX` 패턴, 요청 예산, 오류 코드 3개로 변환, (선택) Last-Modified/ETag 수집 | 가짜 transport만 | 경계 모듈 변경 승인. #400 계열 가드 PR 뒤에 차례로 진행 | 504 클라이언트와 레지스트리가 그대로다. 허용 밖 URL은 거절한다. 예산을 넘으면 SOURCE_INTERRUPTED다 |
| E1-B.5 수동 워크플로 | §2.7 | 없음 (병합만) | 병합 승인, 새 Secret | 정적 금지 규칙과 사전 점검이 있다 |
| E1-B.6 측정 실행 | §2.8의 M1~M6 | SEC | EXP-LISTING-SRC, EXP-DRYRUN, 비공개 보관 승인 | §2.8 합격선 |

**우선순위.**
1. E1-B.1 → E1-B.2 → E1-B.3을 먼저 한다. 셋 다 합성 자료만 쓰므로 승인 없이 할 수 있다.
2. E1-B.0(a)는 코어 담당과 합의해 같이 진행한다.
3. E1-B.4와 E1-B.5는 승인 신청과 함께 준비한다.
4. E1-B.6은 승인 뒤에 한다. 정기 일정은 EXP-SCHED 결정 전에는 없다.

### 2.10 승인 전까지 막혀 있는 것

- 실제 수집 일체 (요청 1건도 포함)
- 확장 범위 SEC 원본의 비공개 서버 보관 (SEC 문구상 허용이지만 보관 경로·양은 EXP-DRYRUN 승인 범위 안에서만)
- 새 Secret 생성
- URL 허용 목록 변경
- 워크플로 병합과 실행, 정기 일정
- 공개 (검색 포함)
- Nasdaq Trader 사용 (BLOCKED_ON_LICENSE)
- OpenFIGI 키 가입·사용 (EXP-OPENFIGI)
- genesis 초기 적재 (§2.3.3)
- CUSIP은 사용하지 않는다

다음은 건드리지 않는다: Universe504, 공식 QGV, 중앙 V, 프론트엔드, 전진검증, 일일 작업 파일.
## 3. 공급원별 비용·사용권 (2026-10-29 공식 문서 재확인)

F=수집, S=비공개 서버 보관, D=파생 점수, A=공개 집계, C=공개 회사별 값. 확인하지 못한 칸은 UNVERIFIED로 두고, 비용 0·PERMITTED를 추정해 쓰지 않는다. 가격·자료는 내려받지 않았고 공식 약관·요금·문서 페이지만 읽었다.

| 공급원 / 자료 | 비용 | 한도 | F | S | D | A | C | 판정·근거 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SEC EDGAR API·bulk ZIP·daily index / 재무·공시 | 이용료 없음("Anyone can access and download this information for free"). 보관·대역폭 비용은 미확인 | 사용자 전체 합산 초당 10요청, User-Agent 선언 필수(기존 일일 작업과 예산 공유) | 허용 | 허용 | 허용 | 허용 | 허용(제출자 서술 텍스트 재게시는 제외) | sec.gov/privacy "Website Dissemination": "may be copied or further distributed … without the SEC's permission". **#422·Main 계획의 UNVERIFIED보다 넓다 → 갱신.** ZIP 재게시 시각은 available_at이 아니다 |
| SEC `company_tickers_exchange.json` / 현재 상장 | 같음 | 같음 | 허용 | 허용 | 허용 | 허용 | 허용 | 권리는 문제없음. 다만 품질이 문제다: SEC는 정확성·범위를 보장하지 않고 갱신 시각도 없다. 그래서 목록 비교로 얻은 사건의 effective_at은 알 수 없다(§2.3) |
| Nasdaq Trader 기호 디렉터리 / 현재 상장·ETF 구분 | 미확인("prior written consent … and may require a fee") | 미확인 | 거부 | 거부 | 거부 | 거부 | 거부 | 저작권 페이지를 이번에 열어 봤다(Main 계획의 404는 해소). 개인 비상업 사본 1부 외에는 서면 동의가 필요하다 → **BLOCKED_ON_LICENSE** |
| NYSE 상장 목록(ICE 이용약관) | 미확인 | — | 거부 | 거부 | 거부 | 거부 | 거부 | robots·데이터 수집과 DB 작성을 금지한다 |
| OpenFIGI / 영구 증권 ID(FIGI) | 이용료 없음. API 키는 계정 가입 필요 | 키 없이 분당 25요청·요청당 10건, 키가 있으면 분당 250요청·요청당 100건 | 허용 | 허용 | 허용 | 허용 | 허용 | FIGI는 공개 영역이다("dedicates FIGI Identifiers to the public domain"). "never changes … never reused"라 영구 ID 후보로 가장 좋다. 다만 티커·거래소 같은 설명 필드의 보관·재배포권은 UNVERIFIED |
| BLS CPI-U API·발표 일정 | 요금 표시 없음(v2는 등록 필요). 무료 여부는 UNVERIFIED | v2 하루 500회·요청당 50계열·20년 / v1 하루 25회 | 허용 | 허용 | 허용 | 허용 | 해당 없음 | 공공 영역이다. 조회일과 BLS 면책 문구를 표기해야 한다. 발표는 08:30 ET. **2025년 10월 CPI는 발표되지 않음**(2025-10-01~11-12 업무 중단). NSA는 "final when issued"이고 SA는 최대 5년 소급 수정된다 → NSA를 쓴다 |
| IEX HIST / 가격(IEX 단독 마지막 체결가) | 이용료 없음("Data provided for free by IEX") | 하루 파일 1개(8~15GB, 저장소 문서 기준 — 오늘 재확인 못 함) | 허용 | 조건부 | 미확인 | 미확인 | 조건부 | 출처 표기 조건만 있고 파생 조항은 없다. 중앙 V 용도로만 승인됐고, 확장 시총에 쓰려면 `EXP-PRICE`와 서면 확인이 필요하다. IEX 마지막 체결가는 공식 종가가 아니다 |
| Norgate Platinum / Diamond / 가격·상폐·과거 지수 구성 | Platinum USD 346.50/6개월·630/12개월, Diamond 433.13·787.50 | 업데이터는 Windows 전용, 설치 2대 | 허용(활성 개인 구독) | 조건부 | 미확인 | 거부(원본) | 조건부 | Codex가 읽은 EULA 20261002 §2(iii)(iv)·§8·§21을 확인했다: 개인용 별도 처리 환경은 허용, 공유·다중 사용자·상업 이용은 금지, 구독이 끝나면 원본 삭제. 시작 연도는 Platinum 1990, Diamond 1950. 과거 주식수는 미제공(현재 펀더멘털만) |
| Tiingo EOD | Power USD 30/월(300/년), Commercial 50/월(499/년) | Power 하루 10만 요청 | 허용 | 미확인 | 미확인 | 거부(원본) | 미확인 | "you may not display or share the data". 약관 페이지가 403이라 파생 조항은 미확인 |
| Massive(옛 Polygon.io) | 개인 Stocks Advanced USD 199/월, Business 2,499/월 | 미확인 | 조건부 | 거부 | 거부 | 거부 | 거부 | 시장데이터 약관 §2 "display use only", §5(d) 비표시 이용·파생물 작성 금지 → 이 용도로는 쓸 수 없음 |
| EODHD 개인 | EOD USD 19.99/월(199/년), Fundamentals 59.99/월 | 유료 하루 10만 요청 | 허용 | 허용(개인) | 미확인 | 거부 | 조건부 | 개인 비상업 저장·분석은 허용, 재배포 금지 |
| Sharadar 직거래 개인 라이선스 | 번들 전체 이력 USD 69/월(499/년), 가격만 39/월(299/년) | 미확인 | 허용 | 미확인 | 조건부 | 조건부 | 조건부 | §6: 원자료를 보이지 않는 백테스트 결과·요약 통계는 공개 표시 가능(개인 용도 한정). 원자료 재배포 금지. 상폐 범위는 1990년대부터 |
| CRSP(현재 Morningstar Indexes) | 공개 가격 없음(구독 문의) | — | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 기관·학술 라이선스만 있음 → #418의 1980~2025 범위는 BLOCKED_ON_LICENSE |

**운영 자동 갱신을 막는 요소**
1. **현재 상장 원본은 SEC 지도 하나뿐이다.** Nasdaq·NYSE는 약관상 막혀 있다. SEC 지도에는 종류·ETF 구분과 상장일이 없다. 그래서 초기 적재(genesis)가 막혀 있다(§2.3.3, `EXP-GENESIS`).
2. **영구 ID:** 주 근거는 CIK와 표지 종류 키다. FIGI를 쓰려면 OpenFIGI 키 가입(오너 조치)이 필요하다(`EXP-OPENFIGI`).
3. **코어 라벨:** 코어가 합성 라벨(`SYNTHETIC_NOT_LIVE`·`UNVERIFIED`, `expanded_catalog.py:259`)만 받는다. 실자료 스냅샷을 만들려면 코어에 추가 변경(E1-B.0)이 먼저 필요하다.
4. **SEC 요청 예산:** 초당 10요청이 기존 7샤드 일일 작업과 공유된다. 측정 실행(`EXP-DRYRUN`) 전에는 일정을 만들 수 없다(`EXP-SCHED`).
5. **가격:** 확장 시총과 공개 파생값에 쓸 수 있는 가격 공급원이 없다(`EXP-PRICE`).
6. **과거 자료:** 과거 주식수(PIT) 공급원이 없다. 1980~2025 과거 구성·상폐 자료도 없다(BLOCKED_ON_DATA).


## 4. E2 설계: 명목·물가조정 $200m 시총 판정과 확장 QGV 재산정 (설계만)


### 4.0 상태와 경계
- **2026-10-30:** 확장 정의가 네 기준으로 바뀌었다(DC-28, [EXPANDED_DEFINITION_20261030](EXPANDED_DEFINITION_20261030.md) §1). Main은 시총 하한을 명목으로 읽었다(오너 확인 대기). 확인되면 아래 R200(물가조정)은 #418 과거 모집단용 참고로만 남는다. 분모 D0~D4와 확장 QGV 재산정(§4.5~4.6)은 네 기준에 맞춰 구현할 때 다시 쓴다.
- 상태는 `DESIGN_ONLY`다. E2는 `BLOCKED_ON_LICENSE`(가격)와 `BLOCKED_ON_DATA`(종류별 주식수·분할·CPI 발표 증거)에 걸려 있다. #422 `E1B_E2_PLAN.md:5`와 같다.
- 이번에 한 것은 코드 읽기와 합성 규모 측정 1건이다. 측정 스크립트는 세션 스크래치(저장소 밖)에 두었다. 저장소는 바꾸지 않았다. 가격·CPI·SEC 수집도 하지 않았다.
- 바꾸지 않는 것: Universe504(`universe_codes_v1.json`), `sec-qgv2.json`, `qgv-official.json`, `share_class_groups/v0`, `sic_industry_groups/v0`, 공식 가중치.
- Pages 허용 목록 `tools/pages_artifact_guard.py:191 ALLOWED_NAMES`에 새 이름을 넣지 않는다. 확장 산출물이 Pages에 섞이면 가드가 실패한다(fail-closed).
- #422 코어는 호출만 한다. 다시 작성하지 않는다.

### 4.1 두 조건은 따로 둔다
| 조건 | 판정식 (Decimal 교차곱, 나눗셈 없음) | CPI | 모집단 | 역할 |
|---|---|---|---|---|
| N200 명목 | `cap ≥ 200,000,000` (USD, 세션 d) | 쓰지 않음 | U-NOMINAL200 (#418 민감도) | 진단 |
| R200 물가조정 | `cap × CPI_base ≥ 200,000,000 × CPI_rel(t_d)` | 씀 | U-US-CAP200-REF (현재 참고), U-BOOK200 (역사, 차단) | 연구 필터 |
- 결과는 `n200_state`와 `r200_state`로 따로 저장한다. 값은 PASS·FAIL·NOT_VERIFIED 중 하나다. 두 결과를 합치지 않는다.
- 경계는 `≥`다. 같으면 통과한다. 성과를 본 뒤 문턱을 바꾸지 않는다.
- 예(합성): base 213.000, CPI_rel 300.000이면 문턱은 281,690,140.84…달러다. 281,690,141은 통과하고 281,690,140은 실패한다. float 나눗셈으로는 이 경계를 지킬 수 없어 Decimal 교차곱만 쓴다.
- 실제 CPI 비율은 조회하지 않았다(UNVERIFIED). 비율이 1보다 크면 N200은 PASS인데 R200은 FAIL인 구간이 생긴다. 두 집합을 섞지 않는다.

### 4.2 CPI 규칙
| 항목 | **CUUR0000SA0 (채택안)** | CPIAUCSL (쓰지 않음, 이유만 기록) |
|---|---|---|
| 계열 | BLS CPI-U, 미국 도시 전체·전품목, 계절조정 없음(NSA), 1982-84=100 | FRED 사본, 계절조정(SA) = BLS CUSR0000SA0 |
| 수정 | NSA는 원칙적으로 수정하지 않음(오류 정정만) → 빈티지가 안정적 | 계절요인을 매년 다시 계산해 과거 약 5년이 바뀜 → 빈티지에 따라 값이 다름 |
| 연평균 | BLS가 공표함(M13) | BLS 공식 SA 연평균 없음 |
| 기존 코드 | `macro/primary_contract.py:37`, `macro/growth_inflation_v0.py:30` | `providers/fred_csv.py:23` |
- #418 문서는 "2009년 CPI-U 연평균"만 적었다(`QGV_BOOK_ALL_STOCKS_UNIVERSE_20261027.md:22-24`). 계열 ID·빈티지·발표 시각은 없다. E2 정책에 이것을 명시해야 한다(승인 항목).
- **기준값 기록:** 계열 BLS:CUUR0000SA0, 기간 2009 연평균(M13), 값은 아직 조회·등록하지 않음(BLS 공식 M13 값을 증거와 함께 등록해야 함, 기억한 값을 쓰지 않음), 최초 공표는 2010년 1월 중순의 2009년 12월 CPI 발표(UNVERIFIED), 증거 참조, 가정 ID `qgv-universe/all-stocks-200m-real-2009/2026-10-27.1`.
  - 검증: 2009년 월 지수 12개의 평균을 소수 셋째 자리로 반올림한 값과 같아야 한다.
  - 기존 파서는 M13을 버린다(`providers/macro_primary.py:225-226`, `macro/evidence_sources.py:266`). 그래서 기준값은 파서 경로가 아니라 별도로 등록한 상수로 둔다.
- **역사 해석:** 1980년 판정에도 2009년 달러 단위를 쓴다(#418:26). 이것은 구매력 단위를 고른 것이다. 1980년 투자자가 알던 값이 아니다. 보고용 플래그 `BASE_UNIT_POST_DATES_DECISION`만 붙이고 판정은 막지 않는다.
- **월 선택:** `CPI_rel(t_d)`는 `release_at ≤ t_d`인 관측월 가운데 가장 최근 월의 지수다. d가 속한 달의 지수가 아니다.
  - 관측월이 빠지면(발표 취소) 보간하지 않는다. 직전 발표월을 유지하고 `CPI_MONTH_GAP` 진단을 붙인다. 실제 사례: 2025년 10월 CPI는 발표되지 않았다(BLS 공지, 2025-10-01~11-12 업무 중단).
- **발표 시각:** BLS 일정표 기준 08:30 ET(일정표 "All times on calendar are Eastern Time" 확인). 월별 발표 증거는 따로 보존한다. `release_error`는 PUBLISHED_ARTIFACT 증거와 release_at이 없으면 `RELEASE_EVIDENCE_UNCONFIRMED`을 낸다(`primary_contract.py:190-206`).
- **현재 판정(REF):** 우리 수집 시각을 공개 시각의 상한으로 쓰면 미래 정보가 들어가지 않는다. 다만 그 값을 발표 시각으로 적지 않는다(`OBSERVED_CAPTURE_UPPER_BOUND`, `primary_contract.py:104`).
- **역사 판정:** `select_observed_vintages(strict_historical=True)`는 `HISTORICAL_VINTAGE_NOT_PROVEN`을 낸다(`primary_input.py:109-110`). 발표일 기록을 확보하기 전에는 `BLOCKED_ON_DATA`다. ALFRED의 realtime_start는 날짜까지만 있으므로 시각은 BLS 일정 증거로 보완한다.
- **재사용과 추가:** `MacroObservation`, `ReleaseMetadata`, `release_error`, `select_observed_vintages`를 재사용한다. 새로 필요한 것은 "가장 최근 관측월 고르기" 얇은 함수 하나다.
- **저장 필드:** series_id, observation_period, value(Decimal 문자열), release_at, release_evidence_ref, evidence_kind, vintage_at, available_at, collected_at, response_sha256. 사용권은 BLS 공공영역이다(#422 `SOURCE_RIGHTS.md:33`).

### 4.3 회사별 시총 정의
`cap(i,d) = Σ_{c∈C(i)} P(c,d) × S(c) × k(c)`. 발행사마다 한 번만 계산한다.

| 입력 | 정의 | 시각 규칙 | 금지 |
|---|---|---|---|
| P(c,d) | 그 종류 상장증권(security_id)의 세션 d **원(비조정) 종가**, USD, 사용권 확인된 EOD 자료 | 세션 d 종가. 레코드 available_at ≤ 실행 as_of. d에 체결이 없으면 이월하지 않음 | 조정가, 다른 종류의 가격, 티커로만 찾은 가격 |
| S(c) | 그 종류의 표지 주식수 `dei:EntityCommonStockSharesOutstanding`(StatementClassOfStockAxis 차원). 차원 없는 값은 종류가 하나인 발행사만 허용 | acceptanceDateTime ≤ t_d인 최신 표지. measurement_date m ≤ d. d−m ≤ SHARES_MAX_AGE(승인 필요) | 희석 가중평균 주식수(`v2_factors.py:86`, `v_inputs_v2.diluted_shares`), 전 종류 합계를 한 종류 가격에 곱하기 |
| C(i), k(c) | 경제적 권리가 같은 종류의 집합과 전환비율. v0에서는 k=1만 허용 | 레지스트리 버전과 결정 시각을 기록 | catalog의 security_count로 합산을 추정하기 |
| 분할 정합 | 구간 (m, d]에 분할·주식병합·주식배당 ex-date가 없다는 증명 | 증거 available_at ≤ 실행 as_of | 증거가 없는데 "분할 없음"으로 가정하기 |

- **결정 시각:** t_d는 세션 d의 마감 시각이다(뉴욕 기준, 조기 마감 반영). 나중에 다시 실행해도 t_d가 같으므로 CPI와 주식수가 같다. t_d 뒤에 나온 정정 공시는 쓰지 않는다.
- **종류 합산:** 기존 규칙은 `universe/share_class_groups.py:3-19`이다. 경제적 권리가 같은 종류만 더하고, 전환비율이 1이 아니면 제외한다. 비상장 종류는 지정한 종류의 가격으로 1:1 평가한다. 한 종류라도 값이 없으면 그룹 전체가 NA다.
  - 그러나 v0 그룹은 504용 3개뿐이다(alphabet, fox, news_corp).
  - 확장용으로 새 레지스트리 `expanded_share_class_groups/v0`를 별도 파일로 만든다. v0 파일은 고치지 않는다.
  - 레지스트리에 없는 다중 종류 발행사는 `CLASS_EQUIVALENCE_UNCONFIRMED`로 NOT_VERIFIED다.
- **표지 파싱 재사용:** `providers/sec_cover_shares.py`의 `parse_cover`(:90), `class_symbols`(:153), `pit_filer_status`(:48)를 쓴다. 단, 두 가지 한계가 있다.
  - `select_filing`은 filingDate ≤ as_of 날짜로 거르고(:37) 10-K/10-Q만 본다(:17). E2는 acceptanceDateTime ≤ t_d로 한 번 더 거른다.
  - 20-F/40-F 표지는 지원하지 않는다. 그래서 해외 제출자는 `FOREIGN_COVER_UNSUPPORTED`로 NOT_VERIFIED다.
- **분할 확인 경로 두 가지:**
  - (a) 승인된 기업행사 자료로 (m, d]에 분할이 없음을 확인한다.
  - (b) 같은 승인 공급원의 원(비조정) 일별 종가에 `qgv_official.split_ratio_hit`(:214)를 적용한다. 간격은 45일 이하다(:78).
  - 둘 다 없으면 `SPLIT_UNCHECKED`, 분할이 발견되면 `CAP_BASIS_MISMATCH`다. v0에서는 주식수를 보정해 다시 계산하지 않는다.
- **남는 오차(보고만 함):** 분할이 아닌 증자나 자사주 매입은 (m, d] 구간에서 잡지 못한다. 문턱 ±10% 안의 발행사 수는 `NEAR_BOUNDARY` 진단으로 센다. 판정과 문턱은 그대로 둔다.
- **공식 V 엔진과의 차이:** 공식 V 엔진은 EV 계산에 diluted_shares를 쓴다(`qgv_v2.py:357`, `:402`). 공식 엔진은 바꾸지 않는다. 시총 필터 기준(표지 주식수)과 V의 EV 기준(희석 가중평균)이 다르다는 점을 score_basis에 적는다.

### 4.4 판정 상태와 이유 코드
- `cap_state`는 VERIFIED 또는 NOT_VERIFIED다. 이유는 모두 모은다. 이유가 하나라도 있으면 NOT_VERIFIED다.
- 예외: CPI 이유만 있으면 n200은 그대로 판정한다. r200만 NOT_VERIFIED가 된다.
- 판정 순서:
  1. 정체성·정책: NOT_IN_CATALOG_AT_D, IDENTITY_AMBIGUOUS, SECURITY_TYPE_EXCLUDED, SOURCE_POLICY_PENDING(ADR·REIT), SHELL_POLICY_PENDING(새 코드)
  2. 종류: CLASS_EQUIVALENCE_UNCONFIRMED, MULTI_CLASS_AMBIGUOUS, UNLISTED_CLASS_SHARES_NOT_AVAILABLE, CONVERSION_RATIO_UNSUPPORTED
  3. 주식수: SHARES_NOT_AVAILABLE, SHARES_AVAILABLE_AFTER_DECISION, SHARES_STALE, COVER_FACT_MISMATCH, FOREIGN_COVER_UNSUPPORTED
  4. 가격: PRICE_RIGHTS_UNCONFIRMED, PRICE_NOT_ON_SESSION, PRICE_BASIS_UNCONFIRMED, PRICE_IDENTITY_UNCONFIRMED, CURRENCY_BASIS_UNCONFIRMED
  5. 정합: CAP_BASIS_MISMATCH, SPLIT_UNCHECKED
  6. CPI(r200만): CPI_NOT_RELEASED, RELEASE_EVIDENCE_UNCONFIRMED, CPI_BASE_UNCONFIRMED, CONFLICTING_VINTAGE, SERIES_POLICY_MISMATCH
- 기존 이름은 그대로 쓴다. 출처는 `sec_universe_shares.py:34-40`과 `primary_contract.py:53-61`이다.
- **비공개 레코드 필드:** issuer_id, cik, session_date, decision_at, cap_state, n200_state, r200_state, floor_r200, cpi_used{series, period, release_at, evidence_kind}, cpi_base, share_refs[{security_id 또는 member, accession, accepted_at, measurement_date}], price_refs[{security_id, source_id, basis, kind}], policy_ids, reason_codes.
- 가격과 시총 숫자는 비공개 저장소에만 둔다. 공개하지 않는다(EXP-PUBLIC).
- 판정 스냅샷의 hash에는 catalog `snapshot_hash`, CPI·가격·주식수 manifest hash, policy digest를 넣는다. 실패한 batch에서는 이전 스냅샷을 유지한다. E1-B와 같은 atomic·CAS 방식을 쓴다.

### 4.5 분모 (발행사 단위, 각 단계는 앞 단계의 부분집합)
| 단계 | 정의 | 빠지는 이유(센다) |
|---|---|---|
| D0 검색 가능 | catalog(as_of=t_d)의 `issuer_count`. `security_count`는 따로 표시 | 없음 |
| D0a 정책 적격 | INCLUDED 증권이 1개 이상인 발행사 | SECURITY_TYPE_EXCLUDED, SOURCE_POLICY_PENDING, SHELL_POLICY_PENDING |
| D1 시총 판정 가능 | cap_state VERIFIED | §4.3·§4.4 이유 |
| D2 문턱 이상 | r200 PASS (U-US-CAP200-REF). 명목 트랙 D2n(n200 PASS)은 따로 셈 | BELOW_R200, CPI 이유 |
| D3 QGV 계산 가능 | D2 가운데 Q·G 축 점수가 있음. V와 총점은 별도 열 | ROW_NOT_AVAILABLE, AXIS_COVERAGE_BELOW_50, PEERS_BELOW_MINIMUM, CALC_VERSION_MISMATCH, V 이유 |
| D4 공식 후보 | D3 ∩ Universe504 공식 순위 행(qgv-official rank 있음). 읽기 전용 대조 숫자 | NOT_IN_UNIVERSE504, 공식 순위 없음 |
- 확장 작업은 공식 후보를 새로 만들지 않는다(EXP-OFFICIAL). D4는 그 사실을 보여 주는 대조 숫자다.
- 같은 CIK의 두 종류는 발행사 1개로 센다.
- 각 단계의 수, 이유별 수, 경계 근처 수를 함께 보고한다. 0은 0으로, 산출하지 못한 값은 NA로 쓴다.

### 4.6 확장 QGV 재산정
**6-1 모집단.**
- 모집단은 `P(t_d) = D2`다. Q·G·V 백분위는 이 안에서만 계산한다.
- `score_universe='U-US-CAP200-REF'`로 둔다.
- `score_basis`는 예를 들어 `RESEARCH_QGV_V2_ALL_US/qgv2-calc/2026-10-23.1/sic_industry_groups/v0/min_peers8`이다(#418:37).
- 504 점수는 복사하지 않는다. TARGET은 섞지 않는다(target={}).

**6-2 모집단을 받는 함수**
| 함수 | 받는 모집단 | 확장에서 쓰는 법 |
|---|---|---|
| `v2_factors.compute(companyfacts, sic, cutoff)` (:1406) | 없음 (발행사 1개) | 그대로 쓴다. 역사 재생에서는 cutoff를 명시한다 |
| `sec_qgv2.build_row` (:154) | 없음 | 현재 REF에만 쓴다. cutoff가 acquired_at 날짜라서(:172) collected_at ≤ t_d일 때만 맞다 |
| `sic_industry.classify_sic` (:90) | 없음 | 현재 SIC로 쓴다. 역사 SIC는 BLOCKED |
| `v2_scoring.score_rows(universe, target, calc_version)` (:118) | universe dict 전체. LIVE/STALE이고 CIK당 1점(:129-134) | 확장 행 dict를 그대로 넣는다 |
| `v2_scoring.volatility_rank_rows` (:156) | 위와 같음 | 위와 같음 |
| `qgv2_inputs.from_inputs` / `engine_inputs` (:237, :437) | records 전체와 in_cross_section | 확장 inputs를 직접 만든다. `to_inputs`는 504 고정인 `require_qgv2`를 거치므로 쓸 수 없다(:308-312) |
| `qgv_v2.score_universe` (:590) | in_cross_section≠False인 행(:629) | Q·G는 확장 `score_rows` 결과로만 채운다. sec-qgv2.json 값은 쓰지 않는다 |

**6-3 504에 묶인 곳과 우회 방법** (공식 파일은 고치지 않는다)
| 504에 묶인 곳 | 위치 | 확장 처리 |
|---|---|---|
| `universe_codes()` 504 목록 | `sec_universe_shares.py:67`, `sec_qgv2.merge` | merge·publish·require_qgv2를 쓰지 않는다. 새 연구 빌더가 score_rows를 직접 부른다 |
| cross_section 'UNIVERSE504_LIVE_STALE_ONE_POINT_PER_CIK' | `sec_qgv2.py:66` | 연구 manifest에 score_universe와 score_basis로 기록 |
| MAX_BYTES 2 MiB | `sec_qgv2.py:42` | 504행이 1.3–1.5MB다(`QGV_V2_QG_METHOD.md:442`). 5k행이면 약 13–15MB로 추정된다. 공개 파일 형식은 불가하고 비공개로만 둔다 |
| 키 정규식 `[A-Z]{2,8}:…` | `qgv2_inputs.py:35` | NYSE_AMERICAN이나 security_id는 키로 못 쓴다. 결정적 연구 키와 security_id 대응표를 둔다 |
| 티커 우선 섹터 배정 | `playbook.sector_for` (:670), `cyclical_basis` (`qgv2_inputs.py:380`) | 티커가 재사용되면 다른 발행사가 TARGET 배정을 물려받을 위험이 있다. CIK가 같을 때만 identities를 넘기고, 아니면 SIC 경로를 쓴다 |
| `FOREIGN_ANNUAL_FILERS` (CIK 1개) | `qgv_official.py:71` | `pit_filer_status`로 해외 제출자를 판정 |
| SUPPLY_MIN, assign_ranks, build | `qgv_official.py:57`, `:460`, `:604` | 공식 전용이다. 확장에서는 부르지 않는다 |
| MIN_PEERS 8, MIN_UNIVERSE 8, GATE_PERCENTILE 30, AXIS_COVERAGE 50 | `v2_scoring.py:32-33`, `qgv_v2.py:38-41` | 그대로 둔다(#418:35 "현행 의미 유지"). 바꾸려면 새 방법 버전과 승인이 필요하다 |

**6-4 5k 모집단에서 달라지는 점**
- **업종군:** 업종군은 10개뿐이다. 5k에서는 모든 군이 8개 이상이라 UNIVERSE_FALLBACK이 거의 사라진다.
  - 2200–3999 군은 바이오·반도체·자동차를 하나로 묶는다. 그래서 업종 상대 Q가 사실상 넓은 비교가 된다.
  - 하위군 7개를 비교군으로 쓰는 것은 새 버전 결정이 필요하다.
- **금융:** FINANCIAL 프로필(6000–6499, `v2_factors.py:58`)은 소형 지역은행이 다수가 된다. 금융 백분위 분포가 바뀐다.
- **REIT·SPAC:** 6500–6799 구간은 GENERAL 프로필이다. 여기로 REIT(6798)와 SPAC(6770)가 들어온다.
  - SPAC는 신탁금만으로 문턱을 넘을 수 있다.
  - 그래서 `SHELL_POLICY_PENDING`이 필요하다. 판별 근거는 `dei:EntityShellCompany`나 SIC 6770이다. 현재 `parse_cover`는 이 태그를 읽지 않는다.
- **점수 의미:** 백분위는 모집단에 대한 상대값이다. 같은 회사라도 504 점수와 확장 점수가 다르다. 화면에서 같은 종류의 숫자처럼 나란히 보이지 않게 한다.
- **결측 증가:** 이력이 짧은 기업이 늘어 3년 CAGR과 moat 값의 NA가 늘어난다. 그래서 `AXIS_COVERAGE_BELOW_50`도 늘어난다. 가치함정 관문(Q ≤ 30)에 걸리는 회사도 바뀐다.
- **calc_version 혼합 금지:** score_rows의 calc_version 인자로 유지한다(:146-149).

**6-5 성능 (합성 측정, 실제 자료 아님)**
같은 기계에서 전체 pytest가 돌고 있었으므로 절대값은 부풀었을 수 있다.
| n | score_rows | score_universe |
|---|---|---|
| 504 | 0.02s | 0.29s |
| 2000 | 0.12s | 2.93s |
| 5000 | 0.24s | 20.55s |
- score_rows는 bisect 풀(:76-104)이라 거의 선형이다.
- score_universe의 `_cross`(:446-471)는 행마다 모집단을 다시 만들고 선형 percentile(:58-70)을 돈다. 그래서 대략 n²이다. 이 계산을 5번 한다(:631-639).
- 하루 1회 REF 판정은 감당할 수 있다. 역사 월별(약 550시점)은 설정 하나당 수 시간이 걸린다. 연구 환경에서만 돌린다.
- bisect 방식 최적화는 공식 엔진과 JS 쌍둥이의 동치 시험이 필요하다. 별도 PR로 다룬다. v0에서는 엔진을 고치지 않는다.
- 5k companyfacts 파싱 비용은 측정하지 않았다(UNVERIFIED).

### 4.7 공식 보존 시험 (구현할 때 필수)
- 확장 실행 전후로 다음 파일의 hash가 같아야 한다: sec-qgv2.json, qgv-official.json, universe_codes_v1.json, share_class_groups.py, sic_industry_groups_v0.json.
- 확장 산출 파일명은 ALLOWED_NAMES에 없어야 한다. 그런 파일이 Pages에 들어가면 가드가 실패한다는 것을 시험으로 고정한다.
- 확장 레코드의 score_universe는 Universe504가 아니어야 한다. 공개 금지 키는 `qgv_official.FORBIDDEN_KEYS`(:87)를 재사용한다.

### 4.8 합성 반례 (기본 CPI: base 200.000, rel 300.000 → 문턱 정확히 300,000,000)
| ID | 입력 | 기대 |
|---|---|---|
| C01 | 1.00 × 300,000,000주 | r200 PASS (경계 같음), n200 PASS |
| C02 | 1.00 × 299,999,999주 | r200 FAIL, n200 PASS |
| C03 | 1.00 × 200,000,000주 / 199,999,999주 | n200 PASS / FAIL, r200은 둘 다 FAIL |
| C04 | base 213.000, rel 300.000(합성) | 281,690,141 PASS, 281,690,140 FAIL (float 금지) |
| C05 | 9월 지수 발표 10-15 08:30 ET. d=10-14와 d=10-15 | 10-14는 8월 지수, 10-15는 9월 지수. 10월 지수는 어느 쪽도 아님 |
| C06 | 10-14 판정을 10-20에 다시 실행 | 여전히 8월 지수, hash 동일 |
| C07 | 역사 시점, 발표 증거 없음 | r200 NOT_VERIFIED (HISTORICAL_VINTAGE_NOT_PROVEN), n200은 판정 |
| C08 | 관측월 결측(발표 취소) | 직전 발표월 유지, 보간 없음, CPI_MONTH_GAP 진단 |
| C09 | CPIAUCSL(SA) 값 투입 | SERIES_POLICY_MISMATCH |
| C10 | A 5.8bn, B(비상장) 0.86bn, C 5.5bn, P_A 170.00, P_C 168.50 | cap 2,058,950,000,000, 발행사 1개. 4,116,160,000,000(합계 × 각 가격)이 나오면 실패 |
| C11 | 차원 없는 합계만 있고 상장 종류가 2개 | MULTI_CLASS_AMBIGUOUS |
| C12 | 비상장 종류 주식수 결측, 부분합은 문턱 이상 | UNLISTED_CLASS_SHARES_NOT_AVAILABLE, 부분합 금지 |
| C13 | A:B = 1:1500, 레지스트리에 없음 | CONVERSION_RATIO_UNSUPPORTED |
| C14 | 표지 없음, 희석 가중평균만 있음 | SHARES_NOT_AVAILABLE (대체 금지) |
| C15 | 10-Q 접수 d 16:30 ET, filingDate d | 이전 표지 사용. filingDate만 보면 잘못 포함됨 |
| C16 | m=07-31, 4:1 분할 08-15, d=09-30 원종가 | CAP_BASIS_MISMATCH (그대로 두면 1/4로 과소) |
| C17 | 1:10 역분할이 창 안에 있음 | CAP_BASIS_MISMATCH (그대로 두면 10배 과대로 잘못 통과) |
| C18 | 분할이 m 이전(표지가 이미 분할 후 기준) | 정상 판정 |
| C19 | 기업행사 자료와 원가격 이력이 모두 없음 | SPLIT_UNCHECKED |
| C20 | 나중 분할로 다시 조정된 과거 종가 | PRICE_BASIS_UNCONFIRMED |
| C21 | 세션 d에 체결 없음(거래정지) | PRICE_NOT_ON_SESSION, 직전가 이월 금지 |
| C22 | ADR, 정책 PENDING. INCLUDE여도 20-F 제출자에 ADS 비율 미확인 | SOURCE_POLICY_PENDING / ADR_RATIO_UNCONFIRMED, FOREIGN_COVER_UNSUPPORTED |
| C23 | 가격 통화가 CAD | CURRENCY_BASIS_UNCONFIRMED, 환산 금지 |
| C24 | 티커 XYZ: 2015–19년은 증권 A, 2022년부터 증권 B | 2018년 가격은 A에만 연결. 공급원이 티커만 주면 PRICE_IDENTITY_UNCONFIRMED |
| C25 | SPAC: 10.05 × 23,000,000 = 231,150,000 | 숫자로는 n200 PASS지만 SHELL_POLICY_PENDING. D0a와 QGV 모집단에서 제외 |
| C26 | REIT, 정책 PENDING | SOURCE_POLICY_PENDING |
| C27 | 입력 순서를 섞음 / 같은 사건이 두 번 들어옴 | hash 동일 / 1회만 적용 |
| C28 | 확장 실행 | 공식 파일 hash 불변. 504 회사의 확장 점수는 공식과 다를 수 있음 |
| C29 | 다른 calc_version 행이 섞임 | CALC_VERSION_MISMATCH, 비교군 밖 |
| C30 | CPI 없음 | n200은 판정, r200은 NOT_VERIFIED (두 조건 독립) |

### 4.9 개발 순서 (승인 뒤)
1. **E2-a:** 합성 오라클과 C01–C30 시험을 만든다. 자료는 쓰지 않는다.
2. **E2-b:** CPI 기준값과 발표 증거를 등록한다.
3. **E2-c:** 종류별 표지 주식수 어댑터를 만든다. `parse_cover`를 재사용하고 접수 시각으로 거른다.
4. **E2-d:** `expanded_share_class_groups/v0`를 만들고 오너 검토를 받는다.
5. **E2-e:** 가격·기업행사 어댑터를 만든다. EXP-PRICE 승인 뒤에만 한다.
6. **E2-f:** 확장 QGV 연구 빌더를 만든다. 비공개로 둔다.
7. **E2-g:** 분모 보고를 만든다.

실제 수집, 정기 일정, 서버 저장, 공개는 각각 승인을 받은 뒤에만 한다.
## 5. E3 백테스트 경계: #417·#418 중복 없이 연결


### 5.0 확인 근거 (읽기 전용, 2026-10-29)
- 기준 HEAD: canonical `3f3ccd2f`, #422 `a30b54bb`, #417 `ec9788a6`(base `bb57398c`), #418 `ef745b96`(문서 9개, 코드 없음).
- 아래 시험은 모두 세션 스크래치(저장소 밖)에서 직접 돌렸다. 저장소 worktree에는 아무것도 쓰지 않았다.

| 실행한 것 | 결과 |
|---|---|
| #417 HEAD 그대로 `tests/research` | **141 passed** |
| #417 연구 파일을 canonical `3f3ccd2f` 위에 덮어 같은 시험 실행 | **33 failed / 108 passed**. 30건은 `ValueError: SCORING_SOURCE_CHANGED`이다. 2건은 같은 오류가 먼저 나서 정규식이 맞지 않은 것이다. 1건은 CLI 감사 종료 코드가 2가 아니라 1로 나온 것이다 |
| 어댑터 시제품 `probe_membership_adapter.py` (#422 공개 API와 #417 `choose_share_classes` 사용, 합성 자료) | **PROBE_PASS** |

- Codex 숫자 두 개는 **다른 시점의 기록**이다(3,757 = 보완 전 전체, 203 = 보완 후 관련). 203은 Main이 PR HEAD에서 재현했다(1절).

### 5.1 #422는 #417·#418 엔진과 겹치지 않는다
| 점검 | 근거 | 판정 |
|---|---|---|
| 변경 파일 | `git diff --name-status 282382a7 a30b54bb` 결과 새 파일 10개(A)만 있다. `research/`와 `docs/backtest/` 경로는 없다 | 겹침 없음 |
| import | 표준 라이브러리와 `.resolve.company_id_for`(expanded_catalog.py:14)만 쓴다. research와 qgv를 import하지 않는다 | 겹침 없음 |
| 계산 코드 | src 안에서 nav, cagr, sharpe, decile, qgv, score, price, cpi로 찾으면 0건이다. "ledger"는 상장 사건 원장을 뜻한다(expanded_catalog_events.py:40, 95–107) | 거래 장부·성과 엔진 없음 |
| 문서 | E0_AUDIT.md:16–17은 #417·#418을 읽기 전용으로 둔다. E1B_E2_PLAN.md:94–104는 "엔진 복제 없음, 어댑터는 Main/연구가 맡음"이라고 적었다 | 경계가 일치한다 |

### 5.2 연구 실행기에 필요한 E1 출력
#417의 membership 계약은 `cik, security_id, start, end(끝 날짜 제외), known_at(선택)`이다(pit_adapter.py:5–6, 81–87). `start`와 `end`는 **날짜 문자열**이어야 한다. datetime을 넣으면 `SESSION_DATE_REQUIRED` 오류가 난다(calendar_adapter.py:17).

| #417 자원 | E1 원천(#422) | 규칙 |
|---|---|---|
| `membership` | 판정 시각 기준 재생 결과의 `snapshot.current` 중 `eligibility=='INCLUDED'` | **신호일마다 한 행**: `start=S`, `end=S+1일`. UTC 날짜를 자르는 변환은 금지한다(E0_AUDIT.md:62–63) |
| `membership.known_at` | 그 증권 사건들의 `available_at` 최댓값 | 반드시 채운다. #417에서는 선택 필드지만 비워 두면 항상 보이는 것으로 처리된다(pit_adapter.py:47–55) |
| `membership.source`, manifest | `snapshot_hash`, `input_manifest_hash`, `policy_fingerprint`, `schema_version` | 비공개 manifest의 `resources.membership`와 bundle `source_hashes`에 들어간다 |
| `identities` | issuer_id↔cik↔security_id↔(exchange, ticker) 구간, MERGED의 `successor_security_id` | 가격 결합 키는 security_id다. 티커는 감사용으로만 쓴다 |
| 감사 집계(비공개) | `excluded_reason_counts`, PENDING/EXCLUDED 건수 | #418의 분모 분리에 쓴다 |
| 제공 안 함 | 정산·상폐 수익, 가격, 주식수, CPI, S&P 편입 이력 | 계속 #417의 `corporate_actions/prices/benchmark` 자원으로 받는다. U-SPX-HIST 편입 이력은 별도 공급원이 필요하다 |

### 5.3 어댑터 위치와 규칙: 연구 쪽, #417 담당
- 경로(제안, #417 담당이 이어서 낼 PR): `research/qgv_backtest/catalog_membership.py`와 `tests/research/test_qgv_backtest_catalog_membership.py`. Main과 Codex는 만들지 않는다.
- 의존 방향은 research → universe 한쪽뿐이다. universe가 research를 import하면 안 된다.
- **공개 API만 쓴다.** `_materialize`와 `_validated_event`는 쓰지 않는다.
- 판정 시각은 `decision_at = calendar.session(S).close_at`이다. 조기 폐장을 반영한다.
- 재생 방법: 먼저 `available_at <= decision_at`인 사건만 남긴다. 그다음 `apply_listing_events(CatalogSnapshot(as_of=EPOCH, policy=연구정책), known, decision_at)`로 **새로 재생**한다. 이미 있는 snapshot을 과거로 돌리면 `CUTOFF_REGRESSION`이 난다(E1B_E2_PLAN.md:98–99).
- **최신 snapshot의 구간표를 과거에 그대로 쓰는 것은 금지한다.** 시제품에서 확인했다. 효력일 03-02, 공개일 03-10인 상장폐지가 있을 때 03-05 기준으로 공개 시점 재생은 그 증권을 회원으로 유지한다. 최신 구간표를 쓰면 빠진다. 이것이 look-ahead다.
- 시제품에서 함께 확인한 것:
  - 같은 CIK의 종류주 2개는 행 2개가 되고 #417이 1개를 고른다(`SHARE_CLASS_LIQUIDITY_UNCONFIRMED` 표시).
  - 재사용된 티커는 security_id가 달라 분리된다.
  - 사전 발표된 상장은 효력일 전에는 회원이 아니다.
  - ETF는 제외, ADR(PENDING)은 보류로 집계된다.
  - 사건 순서를 바꾸거나 같은 사건을 두 번 넣어도 결과가 같다.
- 연구 정책(ADR/REIT, 증권 종류)은 #418 사전등록 명세에서 받는다. E1 기본값 PENDING을 포함으로 바꾸지 않는다.
- **실데이터에서는 거부한다.** `validate_catalog`가 `quality=='SYNTHETIC_NOT_LIVE'`와 `source_rights_state=='UNVERIFIED'`를 강제한다(expanded_catalog.py:259). 그래서 지금 이 어댑터는 합성 단계만 가능하다. 실제 단계에는 `CATALOG_SYNTHETIC_ONLY`를 차단 사유로 낸다. 검증된 상태는 E1-B에서 스키마를 올려 추가한다.

### 5.4 실행은 오프라인에서만
- #417 실행기는 공급원 호출, 네트워크, 공개 출력이 없다(runner.py:5).
- 출력 위치는 승인된 비공개 루트 아래여야 하고 공개 checkout 밖이어야 한다(runner.py:741, 744). 파일은 `O_EXCL|O_NOFOLLOW`, 권한 0600으로 쓴다(runner.py:636).
- 비공개 산출물 7종에는 `daily-nav.csv`, `contributions.csv`(members 포함)가 있다(runner.py:691–698). `report.json`은 `private_only=True`이고 `top_contributors`를 담는다(reporting.py:186, 208). 그래서 **report를 그대로 게시하는 것은 금지**한다.
- Pages 가드의 파일 이름 허용 목록(pages_artifact_guard.py:191, 457–464)이 위 파일 이름들을 이미 차단한다.
- 워크플로와 웹에는 백테스트 계산, 과거 가격, 종목별 장부를 두지 않는다. 9.1에 실행 버튼도 없다(Main 계획 §7).
- 게시까지의 순서:
  1. 연구 환경에서 실행한다.
  2. 연구 쪽 순수 투영기(제안 `research/qgv_backtest/lab_export.py`)가 비공개 report를 허용 목록 JSON 후보로 바꾼다.
  3. 오너가 검토하고 승인한다.
  4. Main PR이 승인된 파일과 그 sha256 고정값을 올린다.
  5. 가드 검증기(제안 `product/lab_results.py`의 `require_lab_results`)가 통과시킨다.

### 5.5 `lab-results.json` 스키마 `lab-results/1`: 엄격 허용 목록
최상위 키는 정확히 `schema`와 `experiments` 두 개다. 문자열 값은 모두 열거형 또는 정규식만 허용한다. 자유 텍스트는 받지 않는다.

| 키 | 형식 |
|---|---|
| experiment_id | 사전등록 레지스트리에 있는 ID만 |
| universe_id | `U-SPX-HIST`, `U-BOOK200`, `U-US-CAP200-REF` 중 하나. #417의 기준 모집단은 HISTORICAL_SP500이다 |
| run_as_of | UTC 시각. 실행하지 않았으면 null. "now"로 채우지 않는다 |
| data_manifest_hash | 64자리 hex. manifest가 없으면 null. 경로와 receipt는 넣지 않는다 |
| method_version | spec_id와 calc_version. 예: `qgv-backtest-standard/2026-10-26.5+qgv2-calc/2026-10-23.1` |
| period | `{label: TARGET_QGV_V2 / SECONDARY_DIAGNOSTIC_NOT_TARGET / DATA_LIMITED_DIAGNOSTIC_NOT_TARGET, start, end}` (config.py:43) |
| cost_basis | `ONE_WAY_BPS_{0,10,20,25,30}`만 (config.py:13) |
| quality_state | `BLOCKED_ON_DATA`, `BLOCKED_ON_PERMISSION`, `BLOCKED_ON_IMPLEMENTATION`, `REPORT_PARTIAL`, `REPORT_COMPLETE` |
| oos_state | `OOS_NOT_ESTABLISHED` 등 열거형 |
| rights_state | `UNVERIFIED` 또는 `AGGREGATE_PUBLICATION_VERIFIED` |
| reason_codes *(추가 필요)* | 차단 사유 열거형. 예: config.py:50의 `MISSING_*`, `SCORING_SOURCE_REPIN_REQUIRED`, `CATALOG_SYNTHETIC_ONLY` |
| strategies[] | `{strategy_id(레지스트리), status, metrics}` |
| metrics | cagr, annualized_volatility, max_drawdown, sharpe, annual_turnover_mean, sample_months. 각각 `{value: 유한수 또는 null, na_reason}` |
| comparisons[] *(사용자 요청 "비교 결과")* | `{strategy_id, baseline_id, metric: cagr_difference, value, lower_bound, decision_state}` |

**가드가 거부할 것:**
- 허용하지 않은 키, 중복 키, 비유한 수, 정해진 깊이·개수 초과.
- 종목 수준 내용: `security_id`, `cik`, `ticker`, `members`, `top_contributors`, `largest_absolute_contributors`, `attribution`, `exposure`, `selection_overlap`, `fills`, `trades`, `weights`, `holdings`, `rank`, `score`.
- 시계열: `nav`, `daily`, `monthly`, `annual_returns`, `benchmark`, 숫자 배열 전부.
- 가격, 시총, 주식수, CPI 수준. 기존 SENSITIVE_KEYS에 더해 이 파일 전용으로 추가한다.
- 경로, URL, 이메일, receipt.
- 레지스트리에 없는 strategy_id.
- 수치가 있는데 `quality_state`가 REPORT_*가 아니거나 `rights_state`가 VERIFIED가 아닌 경우. NA를 0으로 채운 경우.
- 승인된 sha256 고정값과 다른 파일.

**충돌 발견:** 가드는 키를 소문자 영숫자로 정규화한다. 그러면 `cost_basis`는 `costbasis`가 되어 SENSITIVE_KEYS에 걸린다(pages_artifact_guard.py:210, 정규화는 :285–287). `performance`도 금지 키다(:206). 해결 방법은 GSQ-024처럼 이 파일 안의 그 경로에만 예외를 두고 값은 열거형 문자열만 받는 것이다(:215–221 참고). 키 이름을 바꿔 피해 가지 않는다. 오너 결정이 필요하다.

### 5.6 승인된 결과가 없을 때 9.1 Lab 표시
- **현재(LAB-PUBLISH 미승인):** 파일이 없다. 9.1은 지금 문구("공개 앱에 연결된 백테스트 결과가 없습니다", screen-detail.js:144)와 준비 체크리스트를 그대로 유지한다. 이번 작업으로 바꾸지 않는다.
- **승인 뒤, 실증 결과가 없을 때:** 실험마다 다음을 보여 준다.
  - `quality_state: BLOCKED_ON_DATA`, `oos_state: OOS_NOT_ESTABLISHED`, `rights_state: UNVERIFIED`
  - 사유 목록: `MISSING_PRIVATE_MANIFEST`, `MISSING_MEMBERSHIP`, `MISSING_PRICES`, `MISSING_CORPORATE_ACTIONS` 등, 그리고 `SCORING_SOURCE_REPIN_REQUIRED`, `CATALOG_SYNTHETIC_ONLY`
  - 전략은 레지스트리 ID와 `NOT_RUN`만 둔다. 수치는 null이다. 예: "등록 30 · 실행 0"
- 0%, 차트, "최적·자동 매수" 표현은 금지한다.
- 파일이 없거나 검증에 실패하면 현재 문구로 돌아간다(fail-closed).
- 화면 구현은 LAB-PUBLISH 승인 뒤 프론트 담당의 별도 PR로 한다. 지금은 프론트를 건드리지 않는다.

### 5.7 #417 재고정 문제 (#393 이후)
- **원인:**
  - #417 spec은 `scoring_source_sha=bb57398c…`와 `calc_version=qgv2-calc/2026-10-17.1`을 고정한다(QGV_BACKTEST_SPEC_V1 json:7–8).
  - config.py:12는 SHA 하드코딩과 `CALC_VERSION`이 정확히 같은지 검사한다.
  - canonical의 `v2_factors.py:44`는 이제 `qgv2-calc/2026-10-23.1`이다. 이 값은 `a7e25584`(V-PRICE-BASIS, F_k)에서 바뀌었고 #393 병합 `a1f1b704`로 canonical에 들어왔다. bb57398c 시점 값은 v2_factors.py:38의 `…10-17.1`이었다.
- **영향(실측):** canonical 위에서 #417 시험 33개가 실패한다. **감사 CLI도 ERROR(exit 1)로 끝난다.** 그래서 지금은 BLOCKED 사유조차 만들 수 없다.
- **고칠 사람:** #417 담당이다. Main은 #417 파일을 고치지 않는다.
  1. canonical 이후 기준으로 rebase한다.
  2. spec과 config.py:12 두 곳의 SHA와 calc_version을 함께 새 값으로 고정한다.
  3. F_k가 연구 V 입력에 주는 영향을 검토한다(pit_adapter.py:389 `v2_factors.compute`).
  4. 141개 시험과 합성 CLI를 다시 돌린다.
  5. 새 spec 판으로 기록한다. 기존 사전등록은 덮어쓰지 않는다.
- `type_scope`는 바뀌지 않았다(qgv_v2.py:283).

### 5.8 진행 순서
1. #422 병합(오너 승인)
2. EXP-417-REPIN
3. #417 후속 PR: catalog_membership와 lab_export, 합성 시험만
4. LAB-PUBLISH: Main 가드와 검증기 PR
5. 9.1 화면 PR(프론트)
6. 실데이터는 권리와 manifest가 확보된 뒤에만

아래는 이번에 실행하지 않는다: 새 정기 일정, 유료 계약, 배포, 공식 모집단 변경, 프론트 변경.

스크래치 시제품: 세션 스크래치(저장소 밖)의 `probe_membership_adapter.py`
## 6. 우선 개발 계획과 승인 항목

**승인 없이 할 수 있는 것(합성 자료, 문서·코드 PR까지, 병합은 승인 뒤):**
1. **E1-B.1** SEC 목록 어댑터. 순수 함수이고, 기호 정규화(BRK.B/BRK-B), NFC 정규화, 실행 시각 상한 검사, 미래 사건 대기열(PIT-F1·F3 규칙)을 넣는다.
2. **E1-B.2** 공시 근거 파서. 25·25-NSE·8-A·15-12B·8-K를 다루고 `parse_cover`를 재사용한다.
3. **E1-B.3** checkpoint·manifest·CAS. 가짜 백엔드로 모든 중단 지점에서 포인터가 그대로인지 시험한다.
4. **E2-a** 합성 오라클과 C01~C30 시험.
5. **#422 후속 목록을 Codex에 전달한다:** PIT-F1 받기 시점 검증, 정정·철회 계약, ID-8, F6.

**오너 승인이 필요한 것**

| 번호 | 무엇 | Main 권장 |
| --- | --- | --- |
| #422 병합 | E0/E1-A 독립 코어 병합 | 승인 권장(§1.1 조건 2개) |
| EXP-C03-MEANING | C03 = "적용 안 함"인가 "스냅샷에 포함하지도 않음"인가 | "포함 안 함". 코어는 그대로 두고 E1-B 규칙으로 보장 |
| EXP-ID-RELIST | 재상장 증권의 ID | 코어를 유지하고(회차별 새 ID) 비공개 식별 지도 `xs:<cik10>:<class_key>:<epoch>`로 회차를 연결 |
| EXP-GENESIS | 상장일 없는 현재 목록의 초기 적재 | (a) "관측 존재" 기준을 코어에 추가하고 PIT 연구에는 쓰지 못하게 표시 / (b) 유료 상장일 원본 / (c) 8-A 근사. (a) 권장 |
| EXP-CORE-LIVE | E1-B.0: 코어에 실자료 라벨 추가(추가만, Codex 리뷰) | 승인 권장. 합성 라벨의 hash는 바이트 그대로 유지 |
| EXP-QUARANTINE | 문제 사건을 격리하고 진행할지, 전체 거절할지 | dry-run은 전체 보류하고 측정만. 운영 방식은 측정 뒤 결정 |
| EXP-OPENFIGI | OpenFIGI 키 가입(오너 계정)과 Secret 등록 | 측정 M3(종류 키 확보율) 뒤 결정 |
| EXP-DRYRUN · EXP-SCHED | 별도 수동 워크플로 측정 실행 · 정기 일정 | E1-B.1~.5 뒤 측정 1회. 일정은 측정 뒤 |
| EXP-PRICE | 확장 시총·거래대금·V용 가격. 2026-10-30: "점수만 공개" 조건으로만 검토, 명시 허용 공급처 없음 | Sharadar에 서면 문의 먼저(오너 계정). [EXPANDED_DEFINITION_20261030](EXPANDED_DEFINITION_20261030.md) §2 |
| EXP-CPI-POLICY | 2026-10-30: "현재 판정의 시총 하한이 명목인가" 한 줄 확인으로 축소. CPI 계열 정책은 #418 과거 모집단 자료가 생길 때 | 명목(Main 해석) |
| EXP-SHELL | SPAC·셸 회사 처리 | 확장 QGV 모집단에서 제외(`SHELL_POLICY_PENDING`) |
| LAB-PUBLISH · LAB-GUARD-KEYS | `lab-results/1` 채택. 가드가 `cost_basis`(정규화하면 `costbasis`)·`performance`를 금지 키로 막으므로 이 파일의 그 경로만 예외 | 예외 허용 권장(값은 열거형만) |
| EXP-417-REPIN | #417을 canonical 위로 옮기면 33개 실패(`SCORING_SOURCE_CHANGED`) | #417 담당이 새 SHA·`qgv2-calc/2026-10-23.1`로 다시 고정 |
| EXP-PUBLIC · EXP-OFFICIAL | 확장 결과 공개·공식 승격 | 비공개 유지, 승격 안 함 |

**하지 않는 것:** 새 정기 일정, 유료 계약, 공식 모집단 변경, 배포, 실수집, 서버 저장, 프론트엔드·중앙 V·전진검증·일일 작업 파일 변경.
