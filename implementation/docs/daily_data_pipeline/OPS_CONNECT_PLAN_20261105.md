# 운영 연결 준비 — 계층별 실행 위치·주기·Secret·캐시·실패 재개·마지막 정상본 (2026-11-05)

오너 11/05 후속 지시 5항("Codex의 공급처·업데이트 설계를 받아 실행 위치·스케줄·Secret·캐시·실패 재개·마지막 정상본 보존을 준비한다")의 Main 준비 문서다.

- **설계 출처:** Codex 인계 #477(매크로), #478(기술), #480(KIS), #482(확장 모집단), #483(뉴스). 모두 Draft다.
- **이 문서는 준비만 한다.** 새 수집 실행, 예약 추가, Secret 등록, 운영 재개, 병합, 배포는 하지 않았다.
- 아래 "필요한 승인"은 각 작업에 필요한 범위만 적었다.

## 1. 공통 원칙 (모든 계층)

| 항목 | 규칙 |
| --- | --- |
| 실행 위치 | **공개 자료:** 이 저장소의 기존 GitHub Actions(`sec-daily-public-inputs.yml`, UTC `17 22 * * *`). **비공개 자료(KIS·연구 결과):** 비공개 저장소의 workflow. **화면 조회:** 비공개 Worker(오너 확인 뒤 읽기 전용). 공개 workflow는 비공개 Secret을 받지 않는다 |
| 캐시 키 | 공급처 + endpoint + 정규화한 공개 query + 관측 창. Secret·계정 식별값은 키·로그·manifest에 넣지 않는다. 같은 본문 hash는 재계산을 생략한다 |
| 성공 기준 | 모든 페이지와 스키마·신원·기간 검사를 마친 시각만 `last_success_at`이다. HTTP 200이나 빈 응답은 성공이 아니다 |
| 실패 재개 | 공급처(또는 원천)별로 재개한다. 이미 성공한 공유 파일은 다시 요청하지 않는다. 429는 Retry-After를 따르고, 401·403은 즉시 멈춘다. 실패나 캐시 재사용으로 성공 시각·커서를 전진시키지 않는다 |
| 마지막 정상본 | 실패하면 직전 성공본을 그대로 게시·유지한다(공개는 `--preserve-only` 바이트 재게시 경로, 비공개는 이전 디렉터리 유지). 실패한 실행이 성공본을 덮지 않는다. 화면은 `이전 자료 유지 · 최근 갱신 실패`와 `stale`로 알린다 |
| 수정치 | 이전 본문은 바꾸지 않고 새 version을 더한다. 같은 값의 재관측은 수정이 아니다 |
| 결손 | 0이나 보간값으로 채우지 않는다. null과 사유 코드를 둔다 |

## 2. 계층별 준비표

| 계층 | 실행 위치 | 주기(설계안) | Secret | 캐시·재개·정상본 | 지금 상태 | 필요한 승인 (정확 범위) |
| --- | --- | --- | --- | --- | --- | --- |
| 4 매크로 (#477) | 공개 workflow의 기존 `public_screens_pipeline.py --macro-evidence` 경로 | 계열별 발표 시각 + 30분, America/New_York 기준. 발표일이거나 원본이 바뀐 날에만 요청한다(평일 매일 전 계열 요청 아님) | Census 키(E21·E26)는 미설정이라 요청 0. DOL E14는 권리 보류 | 공급처별 재개, 원본 hash·ETag 보존, 관측기간별 revision append, 지연 재시도 1회는 설정 승인 대상 | 화면은 `macro-current-query/1` 판독 연결 중(합성). 기존 운영 보류(M-REENABLE)는 그대로 | ① 발표일 기반 새 예약 ② 원본 보존 정책 ③ 지연 재시도 1회 적용. M-REENABLE은 별도 결정 |
| 3 기술 (#478) | 연구 일봉은 비공개 저장소. 공개 OHLCV·파생지표는 사용권 미정이라 공개 게시 없음 | Alpaca SIP 일봉은 00:30 America/New_York, 최근 5거래일 겹침, 월 1회 최근 30세션 수정 점검. KIS 정기화는 보류 | Alpaca 키(비공개 저장소 Secret, 기존 소표본 승인 범위). KIS 키는 비공개 저장소에만 | 마지막 완료 페이지와 next token은 비공개. 부분 페이지는 `complete=false`. STALE 설계안은 2거래일 이상 지연 | 화면은 `technical-offline-display/1` 판독 연결 중(합성). 갱신 일정 미연결은 `UPDATE_SCHEDULE_NOT_CONNECTED`로 표시 | ① 실제 수집 대상·예산·일정 ② 비공개 정기 workflow 설치 ③ 공개 OHLCV·파생지표 사용권과 공개 범위 |
| KIS 비공개 (#480) | 비공개 저장소 workflow → `data` 가지 → 비공개 Worker `/kis/*` | 갱신마다 최근 100세션 페이지 반복(오너 계정·허용 목록) | KIS 키는 비공개 저장소에만. Worker에는 `PRIVATE_REPO_READ_TOKEN`(읽기 전용)과 만료일 변수 | 누락·거부 행이 있으면 PARTIAL/FAILED로 기록하고 `last_success_at`과 이전 값을 유지한다(행은 stale). 같은 값 재수집은 수정 아님 | Worker 경로와 펼치기 화면은 Draft. 합성 시험만 통과. `data` 가지 없음, Worker 비밀값 없음, 배포 안 함 | ① 이 세션의 비공개 저장소 접근 ② 보관본을 `data` 가지에 두는 쓰기(새 KIS 호출 없음) ③ Worker 토큰 발급·등록과 수동 배포 ④ 정기 수집은 별도(KIS 정기화 보류 중) |
| 1·2 확장 모집단 (#482) | 연구 도구, 로컬 비공개 출력(mode 0600). 공개 파일 없음 | 요청 예산 0, 예약 없음 | 없음 | 실패한 실행은 성공 디렉터리를 바꾸지 않는다. 새 출력 디렉터리로 재개한다 | 검색 첫 화면 `검색·계산 범위` 칸 연결(합성). 실제 결과는 비공개 연구 | ① 평가일 IEX 거래 상태 목록 1건 보관(Main IEX 확장 흐름) ② 확장 결과를 화면(공개 또는 비공개 펼치기)에 연결 ③ 공식 운영 모집단 변경·게시는 별도 |
| 5 뉴스 (#483) | 공개 workflow, 기존 예약 `17 22 * * *` UTC | 기존 그대로. GDELT 예산 40요청, IR 피드 10 | 없음 | 원천별 커서 `cursor`, `last_success_at`, `last_failure_at/code`. GDELT 429면 pause하고 IR 결과는 유지. 실행 사이 비공개 상태 저장(`LOCAL_NEWS_UPDATE_STATE`)은 Main 운영 연결로 남음 | 화면은 schema 2 `refresh.sources` 원천별 상태 연결 중(합성). 공개 파일은 아직 schema 1 | ① #483 병합 뒤 공개 파일 schema 2 전환 ② 실행 간 상태 저장 위치(비공개 저장소 또는 Actions cache)와 보존 기간 |

## 2-1. 단계별 연결 상태 — 수집 → 계산 → 저장 → 조회 → 화면 (11/05 저녁 기준)

○ 연결됨 · △ 개발 확인만(배포 전) · × 미연결

| 계층 | 수집 | 계산 | 저장 | 조회 | 화면 |
| --- | --- | --- | --- | --- | --- |
| KIS 일봉·분석(AMD) | ○ 보관본(Codex, 새 호출 없음) | ○ Codex #480 | ○ 비공개 `data` 가지(`chart/`·`technical/`, ad3c903) | △ Worker `/kis/chart`·`/kis/analysis`: 코드·시험 완료, 배포·읽기 토큰 없음 | △ 기술 2-1 비공개 펼치기 |
| KIS 다섯 측정(AMD) | ○ 보관본 | ○ Codex #480 | ○ `data` `measures/` | △ `/kis/technical`(오너 11/05 승인) | △ 2-1 같은 펼치기 |
| 비공개 QGV(504) | ○ 보관본 | ○ 공통 엔진(Q·G, V 미산출) | ○ `data` `qgv/latest.json` | △ `/kis/qgv` | △ QGV 2.1.6 |
| 매크로 현재 조회 | ○ 기존 보관 timeline(새 요청 0) | ○ Codex #477 | ○ `data` `macro/current.json` | △ `/kis/macro` | 공개 칸: 합성만 · 비공개 펼치기: △ |
| 뉴스 재생 | ○ 보관 공개 원천 재생 | ○ Codex #483 | ○ `data` `news/current.json` | △ `/kis/news` | 공개 원천별 상태표: 공개 파일이 schema 2가 되면 자동 · 비공개 펼치기: △ |
| 확장 모집단 | △ SEC 티커 관측만(IEX 목록 없음) | ○ Codex #482 | 비공개 연구 출력(raw 저장소) | × | 검색 첫 화면: 합성만 |

"△ 조회"의 남은 조건은 둘이다. 하나는 Worker 비밀값 `PRIVATE_REPO_READ_TOKEN`(읽기 전용, 이 저장소 하나)과 `PRIVATE_REPO_READ_TOKEN_EXPIRES_ON` 등록이다. 다른 하나는 Worker 수동 배포다. 화면은 모두 Draft PR이다. 화면은 자료 기준일·수집 시각·마지막 성공·부분 실패를 보인다. 비공개 결과는 오너 확인을 마친 Worker 경로로만 나간다.

## 2-2. 확장 명부의 입력 세 가지 — 구분 (전체 시장 완전성 선언 없음)

| 입력 | 무엇을 말하나 | 기존 승인 경로 | 이번 상태 |
| --- | --- | --- | --- |
| IEX 거래 가능 목록 | 그날 IEX가 거래 상태 메시지(Trading Status 0x48)를 보낸 기호 | 중앙 V가 매일 읽는 IEX HIST TOPS 하루 파일(`sec-daily-public-inputs.yml`, 승인된 공급원). 파서 `iex_last_trade.c`는 지금 **요청한 기호만** 거래 상태를 기록한다 | 전체 기호 목록 출력은 파서 모드 추가(같은 파일, 새 수집 없음). 보관 위치(비공개 raw 저장소) 결정이 필요하다. 10/29 측정 1회에 13,283개를 셌지만 보관하지 않았다 |
| 당일 체결 관측 | 그 기호가 그날 정규장 round-lot 체결을 가졌는지 | 같은 파일·같은 파서(중앙 V의 마지막 체결) | 연결됨(Universe504 범위). 확장 범위는 위 목록 모드와 함께 |
| 상장 증권 명부 | 증권 종류·고정 증권 ID·발행사·종류주 연결 | 공개 허용 URL: SEC `company_tickers.json`·`company_tickers_exchange.json`(티커·CIK·거래소만). 증권 ID·종류·발행사 전 종류 시총은 없다. OpenFIGI(`EXP-OPENFIGI`)는 결정 대기 | **없음.** SEC 목록 밖 기호, FDIC 신고 은행, 빈 거래소 행이 있다 |

**규칙:** IEX 목록은 "그날 IEX에서 거래 가능"만 말한다. 상장 증권 명부가 없으면 증권 ID·대표 증권·발행사 시총이 확정되지 않는다. 그래서 `full_market_denominator`는 null이고 화면은 "전체 시장 분모 미확정"으로 쓴다. IEX 목록만으로 전체 시장이 완전하다고 선언하지 않는다.

**필요한 승인(정확 범위):**
- ① 기존 IEX HIST 하루 파일에서 전체 기호 거래 상태 목록을 내는 파서 모드. 같은 실행 안에서, 새 공급원·새 요청 없이.
- ② 그 목록의 비공개 보관(raw 저장소 release, 날짜별 1개).
- ③ 상장 증권 명부 공급원 결정(OpenFIGI 키 가입·Secret 등 `EXP-OPENFIGI`).

## 2-3. Census·DOL — 정확히 필요한 조치

| 출처 | 막힌 이유 | 필요한 조치 (이것만) |
| --- | --- | --- |
| Census EITS (E21 M3 신규 주문, E26 건축 허가) | API 키 미설정. 코드(`macro_evidence_collection.py` `CENSUS_API_KEY`)와 workflow 환경 연결(`sec-daily-public-inputs.yml`)은 이미 있다. 키가 없으면 요청 0·null이다 | ① 오너가 api.census.gov/data/key_signup.html에서 무료 키를 발급한다. ② 이 저장소 Actions Secret `CENSUS_API_KEY`로 등록한다. 코드 변경·새 workflow는 없다. 출처 표시는 기존 Census API 조건을 따른다 |
| DOL ETA 539 (E14 신규 실업수당 청구) | 약관 원문 미확인(`HELD_TERMS_UNVERIFIED`): 10/20 수집 환경에서 DOL 저작권 페이지가 HTTP 403이었다. 파서·수집 코드는 있다 | ① 오너가 DOL 저작권·이용 조건 페이지(dol.gov/general/aboutdol/copyright)를 브라우저로 열어 확인한다. 미국 연방 저작물이면 공개 사용이 가능하다. ② 확인 결과를 결정 기록에 남긴다. ③ Main이 `evidence_sources.py`의 E14 `publication`을 `PUBLIC`으로 바꾸는 PR을 연다. 새 키·Secret은 필요 없다. 주간 목요일 08:30 ET + 30분 수집은 기존 경로를 쓴다 |

## 3. Main 다음 구현 순서 (승인 뒤)

1. **KIS:** `data` 가지에 보관본 배치 → Worker 토큰 등록·배포 → 오너 폰 실사용 확인. 화면은 이미 준비됐다.
2. **뉴스:** #483 병합 → 공개 파일 schema 2 → 화면이 원천별 상태를 자동으로 보인다. 상태 저장은 비공개 저장소로 제안한다.
3. **매크로:** 발표일 예약 설계를 기존 workflow 안의 조건부 단계로 만든다(새 workflow 아님). 재시도 1회와 원본 보존을 추가한다.
4. **기술:** 실제 수집 범위가 정해지면 비공개 정기 workflow를 만든다. 공개 표시는 사용권 결정 뒤에 한다.
5. **확장 모집단:** IEX 거래 상태 목록 보관을 IEX 확장 구현 PR에 포함한다.

## 4. 이번에 하지 않은 것

- 새 외부 수집 실행, 새 예약 추가, Secret 등록, 운영 보류 해제(M-REENABLE 포함), 권한 확대, 병합, 배포.
- Codex 계산의 JS 재구현과 이미 끝난 산술 감사의 반복.
