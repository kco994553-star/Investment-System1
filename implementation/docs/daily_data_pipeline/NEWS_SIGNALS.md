# 뉴스·신호 `news-signals.json` (GDELT + 회사 IR) — 공개 데이터 범위 변경, 사용자 승인 대기

**2026-11-05 수집 안정화·보관 입력 재생 결과는 맨 아래 절이 최신이다.** 아래 10월의 승인 대기·실행 관측은 당시 기록이며, 새 수집이나 현재 장애를 뜻하지 않는다.

사용자 결정(2026-10-11): GDELT를 공개 계층에 '뉴스·신호'로 추가하고, 미국 TARGET 17개사의 회사 IR 보도자료 RSS를 더한다. Finnhub는 보류(손대지 않음). 저장 항목은 제목·링크·시각·기업·분류뿐이며 본문은 저장하지 않는다. **뉴스와 공시는 어떤 점수도 바꾸지 않는다**(`score_effect: "NONE"`). 소스 비교는 `docs/news/NEWS_SOURCE_CANDIDATES_V1.md`.

## 출처 표기

- GDELT: 화면(S07·S15 카드의 '뉴스·신호 출처: The GDELT Project' 링크)과 공개 파일 `attribution.GDELT`에 모두 넣는다. 인용문: `News signals: The GDELT Project (https://www.gdeltproject.org/), DOC 2.0 API. Titles and links only; every article belongs to its publisher.`
- 회사 IR: `attribution.IR`(회사 자체 보도자료 피드, 제목·링크만). 행마다 출처 'GDELT' 또는 '회사 IR'과 링크 호스트를 표시한다.

## 수집 (`tools/news_signals.py --live`)

### GDELT DOC 2.0 (artlist, JSON)

- 회사마다 1회: `https://api.gdeltproject.org/api/v2/doc/doc?query=<표의 query> sourcelang:english&mode=artlist&format=json&maxrecords=75&timespan=7d&sort=hybridrel`.
- 간격 5.5초 이상(GDELT 요청: 5초에 1회 이하), 실행당 요청 상한 40(19개사 = 19회, 재시도 1회 포함 상한 안). 429·속도 제한 문구를 받으면 남은 회사는 요청하지 않는다(`NOT_RUN_…`, 직전 행 유지). 재시도 정책은 아래 '429 재시도 정책'.
- 기사에서 `url`·`title`·`seendate`만 읽는다(이미지·도메인·국가는 버림). 시각은 GDELT가 처음 본 시각(`seendate`, UTC).
- 관련성 통과 행 중 GDELT 순서(관련도+최신) 앞 15개만 남긴다.

### 회사별 질의·매칭 표 (규칙 v0, `product/news_signals.MATCH` = `news-signals.js` `MATCH`)

제목 최소 관련성: 이름 변형(대소문자 무시, 단어 단위) 또는 대소문자 구분 기호(티커 등, 단어 단위)가 제목에 있어야 하고, 제외어가 하나라도 있으면 버린다. 일반어 단독 티커(ROK=대한민국, RTX=GeForce RTX 등)는 쓰지 않거나 제외어로 막는다.

| 회사 | GDELT query (+ `sourcelang:english`) | 이름 변형 | 대소문자 구분 기호 | 제외어 |
| --- | --- | --- | --- | --- |
| amd | `("Advanced Micro Devices" OR AMD) -macular` | advanced micro devices | AMD | macular, degeneration |
| amzn | `(Amazon OR AMZN) -rainforest -deforestation` | amazon com, amazon web services | Amazon, AMZN, AWS | rainforest, deforestation, amazon river/basin/forest/fires, amazonia, indigenous |
| asml | `ASML` | asml | — | — |
| avgo | `(Broadcom OR AVGO)` | broadcom | AVGO | — |
| etn | `(Eaton OR ETN) -"Eaton Vance" -"Eaton fire"` | eaton corp, eaton corporation | Eaton, ETN | eaton vance, eaton fire, eaton canyon, eaton centre/center |
| gev | `("GE Vernova" OR GEV)` | ge vernova | GEV | — |
| googl | `(Alphabet OR Google OR GOOGL)` | alphabet, google | GOOGL, GOOG | alphabet soup |
| hanmi | `"Hanmi Semiconductor"` | hanmi semiconductor | — | — (Hanmi Financial·Hanmi Pharm은 이름 불일치로 탈락) |
| hubb | `(Hubbell OR HUBB)` | hubbell | HUBB | — |
| intc | `(Intel OR INTC)` | intel corp, intel corporation | Intel, INTEL, INTC | intel officials/chief/community/report/agencies/sharing, military intel, us intel |
| klac | `("KLA Corp" OR "KLA Corporation" OR KLAC)` | kla corp, kla corporation, kla tencor | KLA, KLAC | — |
| lrcx | `("Lam Research" OR LRCX)` | lam research | LRCX | — |
| msft | `(Microsoft OR MSFT)` | microsoft | MSFT | — |
| nvda | `(Nvidia OR NVDA)` | nvidia | NVDA | — |
| qcom | `(Qualcomm OR QCOM)` | qualcomm | QCOM | — |
| rok | `"Rockwell Automation"` | rockwell automation | — (ROK 미사용) | — |
| rtx | `(Raytheon OR "RTX Corp" OR RTX) -GeForce -Nvidia -GPU` | raytheon, rtx corp(oration), pratt whitney, collins aerospace | RTX | geforce, nvidia, gpu(s), graphics, gaming, laptop, dlss, ray tracing |
| stry | `(Stryker OR SYK) -brigade -army` | stryker | SYK | brigade, army, armored, stryker vehicle(s), combat vehicle |
| tokyo_electron | `"Tokyo Electron"` | tokyo electron | — | — |

정규화: 제목의 A–Z만 소문자로 바꾸고 a–z·0–9 이외 문자는 모두 구분자로 본다(Python·JS 동일 결과, 공용 벡터로 검사). 알려진 한계: 'Eaton'·'Intel' 단독 언급의 동명이인·일반어 오탐, 영어 기사만(한미반도체·도쿄일렉트론은 영어 보도가 적음).

### 회사 IR 보도자료 피드 (`IR_FEEDS`)

회사 자체 사이트에서 알고 있는 공식 보도자료 RSS만 넣었다. 이 컨테이너에서는 접속이 막혀 있어 **모두 `UNVERIFIED_URL`**이다. 첫 Actions 실행의 `NEWS_SIGNALS_FAILURE source=IR company_index=n code=…`(없으면 수집 성공)로 확인한 뒤 표의 status를 `VERIFIED`로 바꾼다(예전 사본도 계속 유효). 모르는 회사는 `NOT_AVAILABLE`(사유 `NO_OFFICIAL_FEED_KNOWN`)이며, 배포사·제3자 피드나 추측한 주소는 쓰지 않는다. 피드 안의 링크는 https이면서 회사 도메인일 때만 받는다. 리다이렉트는 거부한다(`REDIRECT_REJECTED`로 기록되어 주소 확인에 쓰인다).

| index | 회사 | 피드 URL | 링크 허용 도메인 | 상태 | 근거 |
| --- | --- | --- | --- | --- | --- |
| 1 | amd | https://ir.amd.com/rss/news-releases.xml | amd.com | UNVERIFIED_URL | 회사 IR 사이트(Q4) 보도자료 RSS 경로 |
| 2 | amzn | https://ir.aboutamazon.com/rss/news-releases.xml | aboutamazon.com | UNVERIFIED_URL | 회사 IR 사이트(Q4) |
| 3 | avgo | https://investors.broadcom.com/rss/news-releases.xml | broadcom.com | UNVERIFIED_URL | 회사 IR 사이트(Q4) |
| 4 | intc | https://www.intc.com/rss/news-releases.xml | intc.com, intel.com | UNVERIFIED_URL | 회사 IR 사이트(Q4) |
| 5 | klac | https://ir.kla.com/rss/news-releases.xml | kla.com | UNVERIFIED_URL | 회사 IR 사이트(Q4) |
| 6 | lrcx | https://investor.lamresearch.com/rss/news-releases.xml | lamresearch.com | UNVERIFIED_URL | 회사 IR 사이트(Q4) |
| 7 | msft | https://news.microsoft.com/feed/ | microsoft.com | UNVERIFIED_URL | Microsoft News Center 피드(보도자료와 기사 혼합) |
| 8 | nvda | https://investor.nvidia.com/rss/news-releases.xml | nvidia.com | UNVERIFIED_URL | 회사 IR 사이트(Q4) |
| 9 | qcom | https://investor.qualcomm.com/rss/news-releases.xml | qualcomm.com | UNVERIFIED_URL | 회사 IR 사이트(Q4) |
| 10 | stry | https://investors.stryker.com/rss/news-releases.xml | stryker.com | UNVERIFIED_URL | 회사 IR 사이트(Q4) |
| — | asml, etn, gev, googl, hubb, rok, rtx | — | — | NOT_AVAILABLE | 회사 자체 공식 보도자료 RSS를 확인하지 못함 |

- Q4 플랫폼 IR 사이트의 `/rss/news-releases.xml` 경로는 회사 도메인의 공식 경로로 알고 있으나, 회사별 실재 여부는 첫 실행 전까지 확인되지 않았다.
- 안전한 파싱: 1MiB 상한, `<!DOCTYPE`·`<!ENTITY`가 있으면 파싱 전에 거부(외부 엔티티·엔티티 확장 차단), RSS 2.0 `item`/Atom `entry`의 제목·링크·날짜만 읽고 설명·본문은 버린다. 피드당 최근 20개, 실행당 요청 상한 20.

## 중복 제거·묶음 규칙 (v0, Python == JS)

1. 링크 정규화: scheme·host 소문자, 사용자 정보 거부, `#` 이하 제거, `utm_*` 매개변수 제거. ASCII http(s)만.
2. 중복: 같은 정규화 링크는 하나, 같은 회사의 같은 정규화 제목(토큰 열)도 하나. 남기는 순서: 회사 IR 우선, 그다음 이른 것.
3. 같은 사건 묶음: 오래된 것부터 보며, 같은 회사·묶음 첫 항목 이후 72시간 이내·주요 토큰(불용어 제외) 3개 이상 공유·Jaccard 50% 이상이면 그 묶음(`REPEAT`), 아니면 새 묶음(`NEW`, id `news:{company}:{첫 시각}:{n}`). 묶음은 창 적용 후 매번 다시 계산하며 검증기도 다시 계산해 대조한다.
4. 8-K EX-99.1 중복(회사 IR만): 같은 회사, 8-K 접수 시각과 ±24시간 이내이고
   - A: IR 제목과 EX-99.1 제목이 주요 토큰 2개 이상·Jaccard 50% 이상 → 가장 가까운 8-K, 또는
   - B: EX-99.1 제목이 일반적('PRESS RELEASE, DATED …'처럼 보도자료·날짜·회사명뿐)일 때 RESULTS 8-K ↔ EARNINGS 보도자료이고 후보가 정확히 1건.
   이면 `relation: RELATED_TO_8K`, `related_8k_accession`, `group_id`는 그 8-K 묶음(`{company}:{accession}`), `occurrence: REPEAT`(우선순위 낮춤). 화면에서는 그 8-K 행 아래 접힌 '관련 IR 보도자료'로만 보인다. 같은 실행의 `sec-disclosures.json`이 없으면 새로 판정하지 않고 직전 판정만 유지한다.

## 분류 v0 (제목 키워드, 앞 규칙 우선)

| 분류 | 표시 | 키워드(정규화 토큰·구) |
| --- | --- | --- |
| LEGAL | 법률·규제 | lawsuit(s), sues/sued/suing, court, antitrust, probe, investigation, settlement/settles, regulator(s), fine(d), ftc, doj, class action, verdict, judge, patent, export controls/curbs/ban, ban, tariff(s), recall |
| MA | 인수·합병 | acquire(s/d/ing), acquisition(s), merger(s), merge, buyout, takeover, to buy, divest(s/iture), spin off, spinoff, stake |
| EARNINGS | 실적 | earnings, results, revenue(s), profit(s), eps, guidance, outlook, forecast, quarterly, quarter, fiscal, dividend, beats/misses estimates |
| PRODUCT | 제품·서비스 | launch(es/ed), unveil(s/ed), introduce(s/d), rolls out, debut(s), release(s/d), product(s), platform |
| OTHER | 기타 | 그 밖 |

## 429 재시도 정책 (2026-10-19 확인)

관측(10/19 정기 실행): GDELT 1번 회사가 HTTP 429 → 10초 뒤 1회 재시도도 429 → `HTTP_429`로 GDELT 중단, 2~19번은 `NOT_RUN_HTTP_429`. 그래서 `gdelt_requests=2`다(예산 40 중 2). 같은 실행에서 IR 9개 피드도 실패(`HTTP_FAILED`, `REDIRECT_REJECTED`), 1개만 응답(새 항목 0).

| 항목 | 현재(이 변경 후) |
| --- | --- |
| 간격 | 요청 사이 5.5초 이상(직렬, 병렬 없음) |
| 재시도 | 429·5xx·전송 실패에 1회만(`MAX_ATTEMPTS=2`). 기본 대기 10초 |
| Retry-After | 응답에 있으면 따른다. 대기 = max(10초, Retry-After). 60초(`MAX_RETRY_AFTER`)를 넘으면 이번 실행에서는 재시도하지 않는다(요청 추가 없음). 초·HTTP 날짜 형식 모두 읽고, 못 읽으면 기본 10초 |
| 429 뒤 | 그 회사는 `FAILED HTTP_429`, 남은 GDELT 회사는 요청하지 않고 `NOT_RUN HTTP_429`. IR은 별도 호스트라 계속 |
| 바꾸지 않은 것 | 요청 예산(GDELT 40, IR 20), 시도 횟수, 직렬 실행, 같은 User-Agent·같은 엔드포인트. 주소·신원 교체, 병렬화, 우회는 하지 않는다 |

근거: 저장소에 있는 GDELT 쪽 지침은 응답 문구 'Please limit requests to one every 5 seconds'(→ 5초 1회)뿐이다(`providers/news_feeds.py` `GDELT_MIN_INTERVAL`, `parse_gdelt`). GDELT의 429·Retry-After·일일 한도에 대한 문서는 저장소에 없다(**미확인**). 그래서 예산은 그대로 둔다. GitHub Actions 실행기는 IP를 여럿이 함께 쓰므로, 첫 요청부터 429면 우리 요청량과 무관하게 제한일 수 있다. 권고(결정 필요, 미구현): 실행 시각 조정, 또는 회사 질의를 묶어 요청 수를 줄이는 방안(매칭 규칙 변경이 따름).

## 공개 파일 형식 (schema_version 2, 별도 파일)

공시 파일(`sec-disclosures.json`)은 채널 DISCLOSURE·8-K 전용 키로 고정되어 있어 뉴스를 넣지 않고 별도 파일로 둔다.

```json
{"schema_version":2,"kind":"NEWS_SIGNALS","as_of":"…+00:00","state":"LIVE|STALE|NOT_AVAILABLE","reason_codes":[],
 "freshness_basis":"SOURCE_ACQUISITION","stale_after_seconds":172800,"window_days":14,"channel":"NEWS","score_effect":"NONE",
 "attribution":{"GDELT":{"name":"The GDELT Project","url":"https://www.gdeltproject.org/","citation":"…"},"IR":{"name":"…","url":null,"citation":"…"}},
 "matching_rule":"TITLE_NAME_OR_TICKER_V0",
 "sources":{"GDELT":{"nvda":{"state":"LIVE","acquired_at":"…","reason_code":null,"last_result":"NOT_RUN","last_result_code":"HTTP_429"},"…":{}},
            "IR":{"nvda":{"state":"LIVE","acquired_at":"…","reason_code":null,"feed_status":"UNVERIFIED_URL","last_result":"NO_NEW_ITEMS","last_result_code":null},
                  "googl":{"state":"NOT_AVAILABLE","acquired_at":null,"reason_code":"NO_OFFICIAL_FEED_KNOWN","feed_status":"NOT_AVAILABLE","last_result":null,"last_result_code":null}}},
 "refresh":{"attempted_at":"<as_of>","result":"UPDATED|NO_NEW_ITEMS|PARTIAL_FAILED|FAILED|NOT_RUN",
            "sources":{"GDELT":{"last_attempt_at":"…","last_success_at":"…","last_result":"FAILED","last_result_code":"HTTP_429",
                                "items_carried_from":"…","companies":{"succeeded":0,"failed":1,"not_run":18},"new_items":0},"IR":{"…":"…"}}},
 "items":[{"company_id":"nvda","source":"GDELT|IR","title":"…","link":"https://…","published_at":"…+00:00",
           "classification":"EARNINGS|PRODUCT|MA|LEGAL|OTHER","group_id":"news:nvda:20261008T210000Z:0","occurrence":"NEW|REPEAT",
           "relation":"NONE|RELATED_TO_8K","related_8k_accession":null}]}
```

- GDELT 19개사(미국 17 + tokyo_electron + hanmi), IR 17개사(목록 10개 + NOT_AVAILABLE 7개).
- 회사별 이번 실행 결과 `last_result`: `UPDATED`(응답, 새 항목 있음) · `NO_NEW_ITEMS`(응답, 새 항목 0 = '새 뉴스 없음') · `FAILED`(요청 실패 = '조회 실패', 코드) · `NOT_RUN`(앞선 429 등으로 요청 안 함, 코드) · `null`(피드 없음, 또는 수집 없이 만든 사본). '새 항목'은 직전 게시본에 없던 링크로, 게시 목록에 남은 것만 센다.
- `refresh.sources[S]`: `last_attempt_at`(= 이 실행 as_of), `last_success_at`(그 출처 회사들의 가장 늦은 acquired_at = 마지막으로 응답을 받은 시각), `last_result`(회사 결과에서 유도: 모두 응답 → UPDATED/NO_NEW_ITEMS, 일부 실패 → PARTIAL_FAILED, 응답 0 → FAILED 또는 NOT_RUN), `last_result_code`(목록 순서상 첫 실패 코드), `items_carried_from`(이번에 갱신되지 않고 유지된 회사의 가장 오래된 acquired_at), 회사 수, `new_items`. 검증기가 회사 항목에서 다시 계산해 대조한다.
- `refresh.result`: 두 출처 종합. `refresh`는 수집 없이 만든 사본(PR 빌드)에서 `null`.
- **state는 의미를 바꾸지 않는다**: 게시된 acquired_at의 신선도(48시간 지나면 STALE). 이번 실행이 실패해도 이전 자료가 48시간 안이면 LIVE로 둔다(STALE은 '수집 갱신 시각 경과'라는 뜻이라 한 번의 실패로 바꾸면 계약과 어긋난다; `sec-public-inputs.json`의 `preserved_previous`와 같은 방식). 대신 `reason_codes`에 `REFRESH_FAILED`(모든 출처 응답 0) / `REFRESH_PARTIAL_FAILED`(일부 실패) / `REFRESH_NOT_RUN`을 더한다. 예: `["REFRESH_FAILED"]`, 48시간이 지나면 `["STALE_INPUT","REFRESH_FAILED"]`. 그래서 실패한 갱신이 'LIVE'만으로 보이지 않는다.
- schema 1(이 변경 전 게시본)도 읽는다: 직전 사본 이월과 `--preserve-only` 바이트 재게시. 새로 쓰는 파일은 항상 2.
- 창 14일(질의는 7일, 이월로 14일 유지), 회사·출처당 GDELT 40·IR 30개 상한, 전체 1,500개, 크기 예산 950KB(상한 1MiB, 넘으면 오래된 것부터 제외).
- 크기: 빈 파일 약 4.3KB, 행당 약 0.3~0.45KB. 상한까지 차도 약 0.45MB, 평상시 수십~200KB 예상.
- 검증: Python `product/news_signals.require_news_signals`(Pages 가드 `news_signals_boundary`, 허용 이름 `ALLOWED_NAMES`), JS `NewsSignals.validate`, 같은 벡터로 대조(`tests/test_news_signals.py`). 가드 비밀값 패턴에 걸리는 제목·링크는 쓰기 전에 버린다(`rows_secret_like`).

## 실패·이월

- 직전 Pages 사본: 404 → 새로 시작, 형식 불일치 → 폐기(`PREVIOUS_DISCARDED`), 네트워크 실패 → 아무것도 쓰지 않음(빌드의 NOT_AVAILABLE 사본 유지).
- 소스 실패: 그 회사는 직전 행·취득 시각 유지(48시간 지나면 `STALE`), 직전도 없으면 `NOT_AVAILABLE`(`NOT_COLLECTED`). 이전 자료 보존은 그대로이고, 회사 `last_result`(FAILED/NOT_RUN + 코드)와 `refresh`가 실패를 적는다. 실패 시각을 acquired_at으로 쓰지 않는다.
- **뉴스 실패로 SEC 일일 배포를 막지 않는다**: 소스·직전 사본 실패는 모두 exit 0. 로컬 출력이 검증에 실패할 때만 exit 1(DART 단계와 같은 원칙).
- `--preserve-only`(cockpit-pages 전용): 검증한 직전 게시본을 바이트 그대로 다시 씀(`as_of`·상태 그대로, 배포 시각으로 재계산하지 않음), 소스 요청 없음. 404·실패·형식 불일치는 빌드 사본 유지, exit 0. 일일 실행은 이 옵션을 쓰지 않음.
- PR 빌드: `build_pages_cockpit.py`가 NOT_AVAILABLE 사본을 낸다. `tools/fixtures/empty_public_screens.json` 포함.

## 로그 (고정 코드·개수만)

`NEWS_SIGNALS gdelt_companies=19 gdelt_collected= gdelt_requests= gdelt_budget=40 ir_feeds=10 ir_collected= ir_requests= sec_reference=AVAILABLE|NOT_AVAILABLE rows_irrelevant= rows_invalid= rows_out_of_window= rows_foreign_link= rows_secret_like= duplicates= state= refresh= gdelt_result=<결과>[:<코드>] gdelt_added= ir_result=… ir_added= items= gdelt_items= ir_items= occurrence_new= occurrence_repeat= related_8k= earnings= product= ma= legal= other=`. `occurrence_new/repeat`은 게시 목록 전체(이월 항목 포함)의 묶음 표시(첫 보도/반복) 개수다. 이번 실행이 더한 항목 수는 `*_added`다. (10/19 로그의 `new=27`은 이 묶음 표시 개수였고 셈 오류는 아니지만 '이번에 새로 받음'으로 읽혀 이름을 바꿨다.), `NEWS_SIGNALS_FAILURE source=GDELT|IR company_index=n code=…`. 회사 이름·제목·URL·응답 본문은 출력하지 않는다(company_index는 GDELT는 `GDELT_COMPANIES`, IR은 위 표의 index 순서).

## 화면

S07 뉴스 탭(뉴스 영역 밖 카드, 뉴스 탭에서만)과 S15 관심 기업(관심 기업만): 한 시간순 목록.
- '공시·확정'(SEC 8-K, `DartDisclosures` 읽기 모듈과 `dart-disclosures.json`이 있으면 DART도) 배지와 '뉴스·신호' 배지(별도 색, 상태 색 아님).
- 뉴스 행: 새 소식/반복 보도, 분류, 출처(GDELT·회사 IR), 시각(UTC), 링크 호스트, 제목 링크(새 창, noopener). 같은 사건의 반복 보도는 접힌 목록.
- 8-K 행: 기존 표시 + 같은 발표의 회사 IR 보도자료를 접힌 '관련 IR 보도자료'로.
- 카드 상단: 각 자료 상태, 기준 시각, GDELT 출처 링크, '점수에 반영하지 않음'.
- 갱신 결과 줄(출처마다 한 줄, 보고 있는 기업 기준: S07 전체·기업, S15 관심 기업), `data-news-refresh`:
  - 응답, 새 항목: `GDELT · 새 뉴스 반영 · 확인 <시각>`
  - 응답, 새 항목 0: `GDELT · 새 뉴스 없음 · 확인 <시각>`
  - 응답 0: `GDELT · 이전 자료 유지 · 마지막 성공 <시각> · 최근 갱신 실패(GDELT HTTP_429, <시각>)`(요청 안 한 회사만이면 `요청 안 함 · HTTP_429`, 이전 자료가 없으면 `이전 자료 없음`)
  - 일부 실패: `회사 IR · 일부 갱신 실패 9/10곳 · 이전 자료 유지 · 마지막 성공 <시각> · 최근 갱신 실패(회사 IR HTTP_FAILED 등, <시각>) · 나머지 1곳 새 뉴스 없음 · 확인 <시각>`
  - schema 1 사본: `… · 최근 갱신 결과 미기록(이전 형식)`.
- 실패가 있으면 상태 배지 옆에 '최근 갱신 실패 · 이전 자료 유지' 또는 '일부 갱신 실패' 배지. 이월 항목은 그대로 목록에 남고 자기 발표 시각을 보인다. 근거 보기에 '최근 갱신'(이 기업의 이번 결과, 실패면 '이 행은 이전 수집분').

## 결정 필요

- 공개 파일 게시(공개 데이터 범위 변경)와 일일 워크플로 1단계·cockpit-pages 보존 1줄 병합 승인.
- IR 피드 10개 주소는 첫 실행 확인 전까지 UNVERIFIED_URL. 공개 재배포 약관(제목·링크만)은 회사별로 사용자가 확인 필요(`NEWS_SOURCE_CANDIDATES_V1.md`는 '확인 전 기기 전용'을 권고했으나 이번 결정은 공개).
- 매칭 v0의 오탐 허용 수준(Eaton·Intel 단독 언급), 한국어·일본어 GDELT 질의 추가 여부.
- 규칙 B(일반적 EX-99.1 제목일 때 실적 보도자료만 시각으로 연결)의 채택 여부.

## 2026-11-05 수집 안정화 — 기존 입력으로 실행한 구현

범위는 기능 5.2.1·5.2.5·5.2.7의 데이터 수집·정규화다. 새 공급처·본문·외부 AI·요약·영향 모델·관계망 정의를 추가하지 않았다. 운영 UI·공개 JSON 스키마·워크플로·Secret은 이 변경에 없다. 로컬 상태와 결과는 공개 게시용 파일이 아니다.

### 실제 보관 근거와 현재 판정의 범위

기준 코드는 `620f57f264896c1efa34ac8e6c19ccd28c10d7d3`. 신규 네트워크 요청 없이 기존 [run 41759732114](https://github.com/kco994553-star/Investment-System1/actions/runs/41759732114)의 Pages 아티팩트와 10/28~11/03 SEC 샤드 아카이브를 읽었다. 원문·결과는 비공개 작업 경로 `/workspace/private-current-news-20261105`에 보관한다.

| 확인 대상 | 보관된 실제 결과 | 이번 판정 |
| --- | --- | --- |
| GDELT | 11/04 02:39:33 UTC 게시본: `FAILED HTTP_429`, 실패 1·요청 안 함 18·성공 0. 마지막 성공 11/02 01:41:16 UTC, 보존 기사 20개 | **가장 최근에 확보한 실행 근거에서 429 재확인**. 이번에 API를 요청하여 확인한 결과는 아님 |
| IR | 같은 게시본: 성공 1·실패 9, 첫 실패 `REDIRECT_REJECTED`, 마지막 성공 11/04 02:39:29 UTC, 기사 0개 | 부분 실패 보존. 피드 주소·권리·상태를 임의로 VERIFIED로 바꾸지 않음 |
| SEC | 게시본 11/04 02:38:09 UTC: LIVE·35개. 별도 submissions 20스냅샷/17회사에서 기존 파서의 제외·충돌·알 수 없는 item 모두 0 | **옛 8-K/6-K 파서 실패는 이 입력에서 재현 안 됨**. 재무용 `sec_submissions.FORMS`를 공시용으로 넓히지 않음 |
| ASML 6-K | 기존 파서가 후보 1개 발견. 보관 SEC 게시본에 분기 실적 Exhibit 확인 근거 없음 | `foreign_unconfirmed=1`, 결과에 추가하지 않음. 6-K 전체를 실적으로 취급하지 않음 |
| DART | 11/04 02:21:01 UTC 게시본: LIVE·한미반도체 17개 | 기존 검증기·corp_code·receipt 식별을 재사용. 날짜 정밀도 `DATE_KST`, 접수 시각은 null 유지 |

지원 형식에서 빠진 파서 사례를 찾지 못했으므로 SEC/DART 파서 지원 범위는 그대로다. 확인된 결함은 뉴스의 **같은 URL 제목 수정이 버려지는 것**과 더 오래된 수집분이 늦게 도착하면 최신 자료를 덮을 수 있는 것이었다. `product/news_signals.merge`가 수정 제목을 반영하고 `counts.revisions`로 센다. 기사 ID는 유지되므로 공개 `new_items`를 늘리지 않는다. 이전 취득 시각보다 오래된 응답은 `NOT_RUN/OLDER_INPUT`으로 이월한다.

### 출처별 갱신 계약·요청량·권리

| 출처 / endpoint | 최초·증분·캐시 | 실패·예상 요청량 | 권리·스케줄 |
| --- | --- | --- | --- |
| SEC `data.sec.gov/submissions/CIK{cik}.json`, 기존 filing index | 기존 90일 recent, accession 단위. 기존 파서 및 Exhibit 확인 규칙 재사용. 로컬 증분은 보관 overlap도 대사 | 기본 17 submissions + 필요한 index 최대 150개, 기존 0.2초 간격·최대 5시도·대기 상한 유지. 이번 요청 0 | 무료 공식 메타데이터 기존 범위. filing/exhibit 본문 수집 없음 |
| GDELT DOC 2.0 `api.gdeltproject.org/api/v2/doc/doc` | 기존 7일 질의·14일 이월. URL+발행사 식별, 수정·늦은 도착은 cursor보다 앞이어도 대사 | 19개 질의, 한 번 재시도 포함 최대 40회. 5.5초 간격. 429 뒤 해당 호스트 중단; Retry-After가 없으면 600초 cooldown, 있으면 더 긴 시각까지 | 기존 GDELT 인용·원문 링크 유지. 기사 본문·이미지 저장 없음 |
| IR | 기존 10개 고정 RSS/Atom endpoint만. 동일 제목 반복과 같은 URL 수정 구별 | 기본 10회·상한 20회, 1초 간격. 호스트별 pause이므로 GDELT 제한이 다른 IR 호스트를 막지 않음 | 회사별 약관·URL 미확인 상태 유지. 신규 공개 재배포 권리 승인으로 해석하지 않음 |
| DART `opendart.fss.or.kr/api/list.json` 및 기존 corpCode | corpCode 근거의 발행사 + rcept_no. 같은 일반 제목의 서로 다른 접수번호는 별도 공시 | 기존 예산·중단 코드 재사용. API 키를 읽거나 사용하지 않고 보관 게시본만 재생 | 기존 한미반도체 범위. 본문·새 endpoint 없음 |

운영 예약은 기존 `sec-daily-public-inputs.yml`의 `17 22 * * *`(UTC) 그대로다. 지연 실행 시각은 예약 시각과 다를 수 있다. 새 예약·수동 실행은 하지 않았다. `PacedClient(state=...)`는 호출자가 보존하는 호스트별 pause 상태를 지원한다. 기본 일일 도구도 이번 실행 내 pause를 적용하지만, **실행 간 영속 저장 연결은 Main의 운영 경로 작업**이다. `UpdateLedger.cached`와 재생 CLI의 `--cache-ttl`은 검증된 메타데이터 캐시를 재사용하며 원래 취득 시각을 유지한다(0=캐시 안 씀, 최대 86400초). 이 변경만으로 정기 실행 간 캐시가 연결됐다고 보지 않는다.

### 로컬 결과 계약과 신규·중복·수정

`providers/news_update.py`의 `LOCAL_NEWS_UPDATE_STATE` v1은 제품 공개 계약을 바꾸지 않는 로컬 수집 상태다.

| 필드 | 의미 |
| --- | --- |
| `issuer_id` | 미국 `SEC:<CIK>`, DART `DART:<corp_code>`, 그 밖은 기존 company 식별. 제목으로 발행사를 추측하지 않음 |
| `item_id`, `filing_id` | 출처+발행사+정규화 URL 또는 공시 접수번호. 같은 URL이 여러 회사를 다뤄도 회사 연결을 버리지 않음 |
| `content_hash`, `version_id`, `previous_version_id`, `revision` | 허용 메타데이터 변경 대사. 같은 항목의 제목/메타데이터가 바뀌면 REVISION. 이전 버전 ID 연결; 본문 변경 탐지는 지원하지 않음 |
| `related_item_id`, `related_filing_id` | 같은 회사의 72시간 내 같은 정규화 뉴스 제목은 반복 항목 연결. IR↔SEC 연결은 기존 Exhibit 규칙만. SEC/DART의 일반 제목이 같다는 이유로 다른 접수번호를 중복 처리하지 않음 |
| `published_at`, `accepted_at`, `source_seen_at`, `filing_date` | 각각 발표 시각·접수 시각·발견 시각·공시 날짜. GDELT seendate는 `source_seen_at`이며 발표 시각은 null. DART는 날짜만 있고 접수 시각 null |
| `first_acquired_at`, `acquired_at` | 실제 보관 입력의 원래 취득 시각. 로컬 재생 시각으로 바꾸지 않음 |
| source별 `cursor`, `last_success_at`, `last_failure_at/code`, `result` | 커서는 관측된 최댓값+ID. 커서 이전 overlap도 처리하므로 늦게 도착한 기사·수정을 놓치지 않음. 실패·캐시는 성공 시각/커서/기존 항목을 전진시키지 않음. 실패 이력은 캐시 사용 뒤에도 유지 |

동일 항목 동일 메타데이터의 재관측은 DUPLICATE이며 새 버전이 아니다. 새 접수번호는 NEW, 동일 접수번호 메타데이터 수정은 REVISION이다. 10,000개 상태 상한을 넘으면 명시적으로 실패하며 일부만 저장하지 않는다. 대용량 장기 이력·운영 보관 주기 확대는 별도 작업이다. 로컬 `last_attempt_at`은 정규화 시도 시각이고, 보관 뉴스 실패를 복원할 때는 원래 게시본의 실패 시각을 쓴다. 보고서 `retained_source_status`에는 원래 출처 상태와 시각을 별도로 둔다.

### 정상 CLI와 실제 재생 결과

```bash
PYTHONPATH=implementation/src python implementation/tools/news_collection_replay.py \
  --inputs /workspace/private-current-news-20261105/inputs.json \
  --out /workspace/private-current-news-20261105/initial \
  --as-of 2026-11-05T00:00:00+00:00

PYTHONPATH=implementation/src python implementation/tools/news_collection_replay.py \
  --inputs /workspace/private-current-news-20261105/inputs.json \
  --state /workspace/private-current-news-20261105/initial/state.json \
  --out /workspace/private-current-news-20261105/incremental \
  --as-of 2026-11-05T00:00:00+00:00
```

입력 23개 = SEC submissions 20개(17회사, 일부 두 시점) + 실제 게시 JSON 3개. 최초 정규화 관측 114건 → 고유 항목 **74개(SEC 37·GDELT 20·DART 17)**, NEW 74·동일 관측 DUPLICATE 40·REVISION 0. 재실행은 고유 74 유지, NEW 0·DUPLICATE 72·REVISION 0, 오래된 입력 20배치는 최신 source 상태를 되돌리지 않음. 두 실행 모두 입력 파싱 실패 0·공급처 요청 0이다. `OK`는 보관 입력 재생 성공이며, 원래 GDELT/IR 수집 실패가 해결됐다는 뜻이 아니다.

- SEC 37개는 7/31~11/03의 **보관 자료 합집합**(8-K, 실제 이벤트 있는 발행사 16개). 최신 게시본 35개나 현재 90일 목록을 대체하는 숫자가 아니다. ASML은 후보만 있어 37개에 포함되지 않는다.
- GDELT 기사 20개는 10/21 09:45~10/27 05:15 UTC 발견, 이벤트 있는 회사 2개. 출처 마지막 성공은 11/02이며 기사 발표 날짜와 다르다. IR 기사 0개도 그대로 유지한다.
- DART 17개는 8/10~11/04, 한미반도체 1개사. 전체 시장 커버리지로 해석하지 않는다.
- 실제 항목 취득 범위는 10/29 01:56:30~11/04 02:38:06 UTC. 상태와 보고서 및 입력 digest는 비공개 `initial/`·`incremental/`에 있다. 공개 저장소에는 실제 회사별 결과를 넣지 않는다.

합성 회귀 예: 같은 URL 제목 정정 → 수정 1·새 URL 0, 재시작 후 3600초 Retry-After → 추가 요청 0, 서로 다른 두 DART 접수번호의 같은 일반 제목 → 신규 2, 잘못된 SEC reference+정상 GDELT 입력 → 부분 실패와 정상 항목 보존, 오래된 입력 → 최신 제목/취득 시각 유지. 새 테스트 `test_news_update_stability.py` 12개와 기존 뉴스·SEC 공시·DART 수집 회귀를 함께 검사한다. 기존 파서·제목 규칙·출처 검증기·분류·IR↔Exhibit 연결을 재사용했으며 새 요약·영향 계산은 없다.

Main 최소 후속 작업은 이 브랜치 파일·CI 검토 후 승인 범위의 병합과, 필요하면 비공개 상태 경로를 기존 운영 호출에 연결하는 것이다. UI의 수정 표기나 공개 스키마 변경은 Main이 별도로 검토한다. 이번 작업 때문에 오너가 공급처 가입·키 등록·새 요금제·새 실행을 할 일은 없다.
