# SEC 8-K 공시 `sec-disclosures.json` (대기열 2.2 a·d·e) — 공개 데이터 범위 변경, 사용자 승인 대기

TARGET 미국 기업(현재 `markets/us.US_LISTINGS` 17개)의 8-K·8-K/A 현재 보고서를 매일 모아 공개 JSON으로 낸다. 공시는 '공시·확정'(channel `DISCLOSURE`), 나중의 뉴스는 '뉴스·신호'(`NEWS`)로 한 시간순 목록에 들어간다. **공시·뉴스는 어떤 점수도 바꾸지 않는다**(`score_effect: "NONE"`).

## 수집 (`tools/sec_disclosures.py --live`)

- 기존 `SecCollectionClient`(User-Agent는 `SEC_USER_AGENT` 이름만, 0.2초 간격, 재시도 상한, 크기 상한, redirect 거부)를 상속한 `SecDisclosureClient`. 허용 경로는 submissions JSON과 8-K 공시 목록 페이지(`…/{accession}-index.htm`) 두 가지뿐이다. 첨부·본문 문서는 요청하지 않는다.
- 회사마다 submissions `filings.recent`의 form·accessionNumber·filingDate·reportDate·acceptanceDateTime·items에서 최근 90일 8-K/8-K/A만 읽는다. 같은 accession이 같은 내용이면 하나로, 다르면 충돌로 버린다(PR #16 규칙 재사용).
- 새 accession(또는 지난번 `NOT_COLLECTED`·`INDEX_UNAVAILABLE`)만 공시 목록 페이지를 하루 최대 150건 읽어 `EX-99.1` 행의 설명(없거나 꺾쇠 등이 있으면 유형 `EX-99.1`)을 제목, 문서 이름으로 sec.gov 원문 링크를 만든다. 보도자료 시각은 8-K `acceptanceDateTime`.
- 직전 Pages 사본: 404 → 새로 시작, 형식 불일치 → 폐기(`PREVIOUS_DISCARDED`), 네트워크 실패 → 아무것도 쓰지 않고 exit 1. 수집 실패 회사는 직전 행과 취득 시각을 유지하고 48시간이 지나면 `STALE`. 전부 실패하고 직전 사본도 없으면 exit 1.
- UI 전용 배포(cockpit-pages)는 `--preserve-only`로 직전 사본을 현재 시각 기준으로 다시 써서(창 밖 행 제거, 상태 재계산) 보존한다. PR 빌드는 SEC 자료 없는 `NOT_AVAILABLE` 사본을 낸다.
- 로그는 고정 코드와 개수만: `SEC_8K_DISCLOSURES companies= collected= failed= … results= officers_directors= …`, `SEC_8K_FAILURE company_index= code=`. 기업명·제목·URL·비밀값은 출력하지 않는다.

## 공개 파일 형식 (schema_version 1)

```json
{"schema_version":1,"kind":"SEC_DISCLOSURES","as_of":"…+00:00","state":"LIVE|STALE|NOT_AVAILABLE","reason_codes":[],
 "freshness_basis":"SOURCE_ACQUISITION","stale_after_seconds":172800,"window_days":90,"channel":"DISCLOSURE","score_effect":"NONE",
 "companies":{"nvda":{"state":"LIVE","acquired_at":"…","reason_code":null}, "…":{}},
 "events":[{"company_id":"nvda","accession":"0001045810-26-000101","form":"8-K","filing_date":"2026-08-27","event_date":"2026-08-27",
   "accepted_at":"2026-08-27T20:20:31+00:00","items":["2.02","9.01"],"classification":"RESULTS",
   "link":"https://www.sec.gov/Archives/edgar/data/1045810/000104581026000101/0001045810-26-000101-index.htm",
   "group_id":"nvda:0001045810-26-000101","occurrence":"NEW","first_seen_at":"…",
   "exhibit_99_1":{"state":"AVAILABLE","title":"…","url":"https://www.sec.gov/Archives/edgar/data/1045810/000104581026000101/….htm","released_at":"2026-08-27T20:20:31+00:00"}}]}
```

- 저장 항목은 제목·링크·시각·기업·분류(Item 코드)뿐. 본문·요약·가격·개인 정보 없음. 결측은 `NOT_AVAILABLE`(+고정 사유).
- 묶음: 8-K는 자기 묶음(`NEW`). 8-K/A는 같은 회사·같은 사건일(reportDate)의 원 8-K가 정확히 하나면 그 묶음에 합류하고, 아니면 자기 묶음. 8-K/A는 항상 `REPEAT`. `first_seen_at`은 처음 공개된 시각으로 이월된다.
- 크기 추정: 행당 약 0.7KB, 17개사 90일 약 80~150행 → 약 60~110KB(상한 2MiB, 넘으면 오래된 행부터 제외).
- 검증: Python `product/sec_disclosures.require_sec_disclosures`(Pages 가드 `sec_disclosures_boundary`), JS `SecDisclosures.validate`. 같은 벡터로 대조(`tests/test_sec_disclosures.py`).

## Item 분류

| 분류 | 기준 Item(우선순위 순) | 표시(한·영) |
| --- | --- | --- |
| RESULTS | 2.02 Results of Operations and Financial Condition | 실적 (Results) |
| OFFICERS_DIRECTORS | 5.02 Departure of Directors or Certain Officers; … | 임원·이사 (Officers / directors) |
| MATERIAL_AGREEMENT | 1.01 Entry into a Material Definitive Agreement | 중요 계약 (Material agreement) |
| ACQUISITION_DISPOSITION | 2.01 Completion of Acquisition or Disposition of Assets | 인수·처분 (Acquisition / disposition) |
| OTHER | 그 밖의 Item | 첫 Item(9.01 제외)의 공식 이름, 예: 공정공시(Regulation FD) (Regulation FD Disclosure) |

모든 Item(1.01~9.01, 공식 이름 영·한)은 `providers/sec_8k_disclosures.ITEMS`와 `sec-disclosures.js` `ITEMS`에 같은 표로 있다. 표에 없는 코드는 버리고 개수만 센다.

## 실적일 추정 → 확인 (`sec-filing-windows.json`)

- 기존 제출 패턴(10-Q/10-K 기간 종료 월-일)으로 오늘 이전 가장 최근 기간 종료일 P를 추정한다(`latest_period_end`, JS `latestPeriodEnd` 동일).
- 같은 submissions에서 P 이후 120일 안에 접수된 **원 8-K(8-K/A 제외) 중 Item 2.02가 있는 첫 건**이 있으면 그 접수 시각의 미국 동부 날짜를 `confirmed_earnings_date`로, `earnings_confirmation {basis:"SEC_8K_ITEM_2_02", period_end, accession, accepted_at}`을 기록한다. 없으면 둘 다 null.
- 화면: 기업 화면 '다음 실적'은 확인이면 `확인 · 날짜 · SEC 8-K Item 2.02`, 아니면 `추정 · 창 · 확정일 아님`. 새 기간 종료일이 지나면 다시 추정. S15 '이번 주 실적'은 `추정 n · 확인 m`. `earnings_confirmation` 키가 없는 예전 사본도 유효하다.

## 화면 (최소)

S07 뉴스 탭 위와 S15 관심 기업(관심 기업만)에 '공시·확정 · SEC 8-K' 카드: 시간순 목록, 배지 '공시·확정', 새 공시/정정·반복, 분류(한·영), Item 공식 이름, EX-99.1 제목 링크, SEC 원문 목록 링크(새 창, noopener).

## 범위 밖 · 결정 필요

- ASML은 외국 민간 발행인이라 8-K가 아니라 6-K를 낸다. 지금은 공시 0건(LIVE)으로 보인다. 6-K 포함 여부는 사용자 결정.
- 공개 파일 게시 자체(공개 데이터 범위 변경)와 일일 워크플로 1단계·cockpit-pages 보존 1줄은 사용자 승인 후 병합.
