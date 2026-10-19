# 뉴스·신호 `news-signals.json` (GDELT + 회사 IR) — 공개 데이터 범위 변경, 사용자 승인 대기

사용자 결정(2026-10-11): GDELT를 공개 계층에 '뉴스·신호'로 추가하고, 미국 TARGET 17개사의 회사 IR 보도자료 RSS를 더한다. Finnhub는 보류(손대지 않음). 저장 항목은 제목·링크·시각·기업·분류뿐이며 본문은 저장하지 않는다. **뉴스와 공시는 어떤 점수도 바꾸지 않는다**(`score_effect: "NONE"`). 소스 비교는 `docs/news/NEWS_SOURCE_CANDIDATES_V1.md`.

## 출처 표기

- GDELT: 화면(S07·S15 카드의 '뉴스·신호 출처: The GDELT Project' 링크)과 공개 파일 `attribution.GDELT`에 모두 넣는다. 인용문: `News signals: The GDELT Project (https://www.gdeltproject.org/), DOC 2.0 API. Titles and links only; every article belongs to its publisher.`
- 회사 IR: `attribution.IR`(회사 자체 보도자료 피드, 제목·링크만). 행마다 출처 'GDELT' 또는 '회사 IR'과 링크 호스트를 표시한다.

## 수집 (`tools/news_signals.py --live`)

### GDELT DOC 2.0 (artlist, JSON)

- 회사마다 1회: `https://api.gdeltproject.org/api/v2/doc/doc?query=<표의 query> sourcelang:english&mode=artlist&format=json&maxrecords=75&timespan=7d&sort=hybridrel`.
- 간격 5.5초 이상(GDELT 요청: 5초에 1회 이하), 실행당 요청 상한 40(19개사 = 19회, 재시도 1회 포함 상한 안). 429·속도 제한 문구를 받으면 남은 회사는 요청하지 않는다(`NOT_RUN_…`, 직전 행 유지).
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

## 공개 파일 형식 (schema_version 1, 별도 파일)

공시 파일(`sec-disclosures.json`)은 채널 DISCLOSURE·8-K 전용 키로 고정되어 있어 뉴스를 넣지 않고 별도 파일로 둔다.

```json
{"schema_version":1,"kind":"NEWS_SIGNALS","as_of":"…+00:00","state":"LIVE|STALE|NOT_AVAILABLE","reason_codes":[],
 "freshness_basis":"SOURCE_ACQUISITION","stale_after_seconds":172800,"window_days":14,"channel":"NEWS","score_effect":"NONE",
 "attribution":{"GDELT":{"name":"The GDELT Project","url":"https://www.gdeltproject.org/","citation":"…"},"IR":{"name":"…","url":null,"citation":"…"}},
 "matching_rule":"TITLE_NAME_OR_TICKER_V0",
 "sources":{"GDELT":{"nvda":{"state":"LIVE","acquired_at":"…","reason_code":null},"…":{}},
            "IR":{"nvda":{"state":"LIVE","acquired_at":"…","reason_code":null,"feed_status":"UNVERIFIED_URL"},
                  "googl":{"state":"NOT_AVAILABLE","acquired_at":null,"reason_code":"NO_OFFICIAL_FEED_KNOWN","feed_status":"NOT_AVAILABLE"}}},
 "items":[{"company_id":"nvda","source":"GDELT|IR","title":"…","link":"https://…","published_at":"…+00:00",
           "classification":"EARNINGS|PRODUCT|MA|LEGAL|OTHER","group_id":"news:nvda:20261008T210000Z:0","occurrence":"NEW|REPEAT",
           "relation":"NONE|RELATED_TO_8K","related_8k_accession":null}]}
```

- GDELT 19개사(미국 17 + tokyo_electron + hanmi), IR 17개사(목록 10개 + NOT_AVAILABLE 7개).
- 창 14일(질의는 7일, 이월로 14일 유지), 회사·출처당 GDELT 40·IR 30개 상한, 전체 1,500개, 크기 예산 950KB(상한 1MiB, 넘으면 오래된 것부터 제외).
- 크기: 빈 파일 약 4.3KB, 행당 약 0.3~0.45KB. 상한까지 차도 약 0.45MB, 평상시 수십~200KB 예상.
- 검증: Python `product/news_signals.require_news_signals`(Pages 가드 `news_signals_boundary`, 허용 이름 `ALLOWED_NAMES`), JS `NewsSignals.validate`, 같은 벡터로 대조(`tests/test_news_signals.py`). 가드 비밀값 패턴에 걸리는 제목·링크는 쓰기 전에 버린다(`rows_secret_like`).

## 실패·이월

- 직전 Pages 사본: 404 → 새로 시작, 형식 불일치 → 폐기(`PREVIOUS_DISCARDED`), 네트워크 실패 → 아무것도 쓰지 않음(빌드의 NOT_AVAILABLE 사본 유지).
- 소스 실패: 그 회사는 직전 행·취득 시각 유지(48시간 지나면 `STALE`), 직전도 없으면 `NOT_AVAILABLE`(`NOT_COLLECTED`).
- **뉴스 실패로 SEC 일일 배포를 막지 않는다**: 소스·직전 사본 실패는 모두 exit 0. 로컬 출력이 검증에 실패할 때만 exit 1(DART 단계와 같은 원칙).
- `--preserve-only`(cockpit-pages 전용): 검증한 직전 게시본을 바이트 그대로 다시 씀(`as_of`·상태 그대로, 배포 시각으로 재계산하지 않음), 소스 요청 없음. 404·실패·형식 불일치는 빌드 사본 유지, exit 0. 일일 실행은 이 옵션을 쓰지 않음.
- PR 빌드: `build_pages_cockpit.py`가 NOT_AVAILABLE 사본을 낸다. `tools/fixtures/empty_public_screens.json` 포함.

## 로그 (고정 코드·개수만)

`NEWS_SIGNALS gdelt_companies=19 gdelt_collected= gdelt_requests= gdelt_budget=40 ir_feeds=10 ir_collected= ir_requests= sec_reference=AVAILABLE|NOT_AVAILABLE rows_irrelevant= rows_invalid= rows_out_of_window= rows_foreign_link= rows_secret_like= duplicates= state= items= gdelt_items= ir_items= new= repeat= related_8k= earnings= product= ma= legal= other=`, `NEWS_SIGNALS_FAILURE source=GDELT|IR company_index=n code=…`. 회사 이름·제목·URL·응답 본문은 출력하지 않는다(company_index는 GDELT는 `GDELT_COMPANIES`, IR은 위 표의 index 순서).

## 화면

S07 뉴스 탭(뉴스 영역 밖 카드, 뉴스 탭에서만)과 S15 관심 기업(관심 기업만): 한 시간순 목록.
- '공시·확정'(SEC 8-K, `DartDisclosures` 읽기 모듈과 `dart-disclosures.json`이 있으면 DART도) 배지와 '뉴스·신호' 배지(별도 색, 상태 색 아님).
- 뉴스 행: 새 소식/반복 보도, 분류, 출처(GDELT·회사 IR), 시각(UTC), 링크 호스트, 제목 링크(새 창, noopener). 같은 사건의 반복 보도는 접힌 목록.
- 8-K 행: 기존 표시 + 같은 발표의 회사 IR 보도자료를 접힌 '관련 IR 보도자료'로.
- 카드 상단: 각 자료 상태, 기준 시각, GDELT 출처 링크, '점수에 반영하지 않음'.

## 결정 필요

- 공개 파일 게시(공개 데이터 범위 변경)와 일일 워크플로 1단계·cockpit-pages 보존 1줄 병합 승인.
- IR 피드 10개 주소는 첫 실행 확인 전까지 UNVERIFIED_URL. 공개 재배포 약관(제목·링크만)은 회사별로 사용자가 확인 필요(`NEWS_SOURCE_CANDIDATES_V1.md`는 '확인 전 기기 전용'을 권고했으나 이번 결정은 공개).
- 매칭 v0의 오탐 허용 수준(Eaton·Intel 단독 언급), 한국어·일본어 GDELT 질의 추가 여부.
- 규칙 B(일반적 EX-99.1 제목일 때 실적 보도자료만 시각으로 연결)의 채택 여부.
