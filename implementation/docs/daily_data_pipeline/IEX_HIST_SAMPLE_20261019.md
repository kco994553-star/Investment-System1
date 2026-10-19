# IEX HIST 하루치 표본 측정 — 중앙 V 가격 입력 후보 (2026-10-19)

> **상태: 표본 측정(SAMPLE ONLY).** 공식 채택이 아니다. 워크플로·가드·엔진·Pages 게시본은 바꾸지 않았다.
> 이 문서와 커밋에는 가격 값·가격 파생값이 없다. 개수와 시각만 있다.

- 작성: 2026-10-19 03:55 UTC / 12:55 KST.
- 소유자 승인 범위(Main 전달): 표본 측정만. 공식 경로·조건 확인, 명시 제한 우회 금지, 하루치 시험. GSQ 예외는 이 시험의 일별 가격 **메모리 처리**에만 한정. 원시 가격의 공개 로그·Git·아티팩트 저장과 운영 게시 변경은 금지.
- 기준: `claude/investment-system-top500-validation-alrugm` `fe7bbc90`(#326 병합 뒤). 엔진 입력 변환은 PR #325(`claude/qgv2-inputs-py` `172ac021`)의 `qgv/qgv2_inputs.py`를 썼다.
- 선행 문서: [무료 출처 조합](FREE_SOURCE_COMBINATION_20261018.md)의 IEX HIST 절, [중앙 V 게시 설계](../qgv_scoring_standard/CENTRAL_V_PUBLICATION_DESIGN_20261018.md).

## 요약

- **약관상 자동 다운로드를 명시 금지한 조항은 없었다.** 계정·키 요구도 없다. 그래서 하루치 시험을 진행했다.
- 다만 **iex.io 웹사이트 이용약관**에 "개인·비상업 외 다운로드·저장 금지(한 대 컴퓨터 메모리의 임시 사본 1개는 예외)"와 "사전 서면 동의 없는 배포 금지" 문구가 있다. HIST 약관 §01(출처 표시 후 배포 상정)과 겹치는지 불명확하다. **채택 전 서면 확인 대상**이다.
- 대상일 **2026-10-16(금)** TOPS 1.6 파일 1개(14.61GB gz)를 디스크 없이 끝까지 스트리밍했다. MD5가 공식 해시와 일치했다.
- **505개 중 503개**가 IEX 체결을 가졌다. 없는 2개: `NASDAQ:PSKY`, `NASDAQ:WBD`.
- 503개 모두 마지막 유효 체결이 **15:57:18 ET 이후**였다. 중앙값 15:59:54 ET.
- 처리: 벽시계 **19분 13초**, 최대 RSS **110MB**, 디스크 사용 0.
- **실제 V 산출: GENERAL 434곳 중 345곳.** Q·G·V 공통 344곳. 관문 제외 96곳.
- T+1 입수: 파일 생성 **2026-10-17 10:21:47 UTC**(19:21:47 KST). 종가 뒤 약 14시간 22분.
- GitHub 호스트 러너에서 기술상 가능하다. 하지만 GSQ-001(Actions 시세 수집 금지)은 그대로 유효하다.

## 1. 공식 경로와 약관

읽은 시각: 2026-10-19 03:19–03:22 UTC(12:19–12:22 KST). 모두 인증 없는 공개 페이지다.

| 문서 | URL | 확인 내용 |
| --- | --- | --- |
| HIST 다운로드 페이지 | https://iextrading.com/trading/market-data/ (`#hist-download`) | "HIST will be available for download on a T+1 basis. By accessing or using IEX Historical Data, you agree to the IEX Historical Data Terms of Use." 계정·키 언급 없음 |
| HIST 목록(메타데이터) | https://iextrading.com/api/1.0/hist | 날짜별 `link`·`feed`·`version`·`protocol`·`size`. 2016-12-12~2026-10-16, 2,491 날짜. 링크는 공개 Google Cloud Storage 객체(`www.googleapis.com/download/storage/v1/b/iex/o/...`, 세대 번호 고정) |
| HIST 약관 | https://www.iex.io/legal/hist-data-terms (구 경로 `iextrading.com/iex-historical-data-terms/`가 이리로 이동) | §01 출처 문구 의무. §02 불법 이용·IEX/SEC 규칙 위반 금지. §03 IEX 소유권. §04–§07 면책·배상. §08·§10 IEX 외 시장 미반영 참고값. **자동 다운로드·호출 한도·계정·종료 조항 없음** |
| iex.io 웹사이트 이용약관 | https://www.iex.io/legal/terms (최종 갱신 2016-09-06) | 아래 3개 문구. 자동 다운로드를 명시 금지하지는 않는다 |
| IEX Web Portal General Terms & Conditions | https://www.iex.io/legal/iex-web-portal-general-terms-conditions (Latest Revision 2026-07-27) | Administrator Authorization Form에 서명한 고객의 보안 포털(위험 관리·옵션 마켓메이커 등)에만 적용. 공개 HIST 다운로드와 무관 |
| robots.txt | https://iextrading.com/robots.txt | `User-Agent: *` / `Disallow:`(빈 값) — 전체 허용 |
| TOPS 명세 v1.66 | https://www.iex.io/documents/tops-v1-66 (PDF) | Trade Report 0x54, 38바이트. 부록 A: Last Sale Eligible = 확장 시간 플래그 0, 단주 플래그 0 |

웹사이트 이용약관의 관련 문구:
- "Using, copying, downloading, reformatting or storing any portion of the Website for other than personal, noncommercial use … except for one temporary copy in a single computer's memory, without the prior written consent of IEX … is expressly prohibited."
- "Customer shall not modify, sell, display, distribute, publish … the Website or the Content to others without IEX's prior written consent."
- 의심 활동 시 접근 즉시 종료 가능. 약관은 예고 없이 바뀔 수 있다.

판정:
- **중단 조건(자동 다운로드 명시 금지, 충족 불가 요건)에는 해당하지 않았다.** 그래서 진행했다.
- 이번 시험은 웹사이트 약관 예외 문구에도 맞춘다. 컴퓨터 1대, 메모리 1회 처리, 저장 없음, 비상업 측정이다.
- **남는 쟁점:** 운영(매일 자동 수집 + 파생 점수 공개)에서 HIST 약관과 웹사이트 약관 중 무엇이 우선인지. HIST 약관은 데이터 전용이고 배포를 상정한다. 웹사이트 약관의 "Content"는 사이트로 접근 가능한 데이터를 포함한다. 데이터 자체는 GCS에서 받지만 목록은 사이트에서 읽는다. **채택 전 IEX 서면 확인을 권한다.**
- 권리표 ①(자동 수집): "명시 금지 없음, 웹사이트 약관 범위 서면 확인 필요"로 갱신 제안. ⑧(종료 후 보관): HIST 약관에 여전히 조항 없음 → 미확인 유지.
- 계정 생성·키 사용·한도 우회는 하지 않았다. 범위 요청(Range)은 표준 HTTP다. 이번 실행에서 연결이 끊긴 적은 없다.

## 2. 대상 파일과 T+1 입수 시각

- 대상: **2026-10-16(금)**, 피드 TOPS 1.6, IEX-TP v1. 하루 4개 파일(DEEP·DPLC·DPLS·TOPS) 중 체결 보고가 있는 가장 작은 종류다.
- 크기: 14,606,058,896바이트 gz. 최근 10거래일 TOPS 8.01~14.61GB 중 가장 크다(최악 측정).
- 생성 시각(목록 링크의 GCS `generation`, 헤더 `last-modified`와 일치):

| 거래일 | TOPS 생성 UTC | KST | 비고 |
| --- | --- | --- | --- |
| 10-09 | 10-10 05:31:32 | 14:31 | |
| 10-12 | 10-13 04:24:30 | 13:24 | |
| 10-13 | 10-14 06:43:09 | 15:43 | |
| 10-14 | 10-15 07:59:48 | 16:59 | |
| 10-15 | 10-16 09:37:38 | 18:37 | |
| **10-16** | **10-17 10:21:47** | **19:21** | 종가(10-16 20:00 UTC) 뒤 14시간 22분 |

- TOPS는 그날 4개 파일 중 **항상 마지막**에 생성됐다. DEEP보다 약 1~2시간 늦다.
- 지금 예약 실행(22:17 UTC)과 맞추면 **하루 늦은 기준일**이 된다. D일 22:17 UTC 실행은 D−1 거래일 파일만 쓸 수 있다. 설계 문서의 "기준일 = 마지막 완료 뉴욕 거래일" 규칙과 다르다. 결정 필요.

## 3. 처리 방법

- 경로: HTTP(공식 링크) → `zlib` gzip 해제 → pcapng 블록 → Ethernet/IPv4/UDP → IEX-TP 헤더(40바이트, 프로토콜 0x8003) → 메시지 전부.
- 파일 형식은 고전 pcap이 아니라 **pcapng**(Section Header 0x0A0D0D0A, Enhanced Packet Block)였다.
- 표준 라이브러리만 썼다. 새 의존성 없음. 원시 파일·가격을 디스크에 쓰지 않았다.
- RAM 상태: 505개 심볼(Universe 504 + SPY)별 마지막 유효 체결(시각·가격·체결 ID), 체결 수, Trade Break 반영용 직전 4건.
- 유효 체결 = TOPS 부록 A "Last Sale Eligible": 확장 시간(0x40)=0 그리고 단주(0x20)=0. 가격>0, 수량>0.
- 검증: 앞 600MB(gz)에서 정밀 순회와 빠른 패턴 탐색을 비교했다. 505개 심볼 모두 체결 수·마지막 체결 ID·시각이 같았다. 본 실행은 정밀 순회를 썼다.
- 스크립트는 저장소 밖 작업 공간에만 있다. 저장소에는 가격 다운로드 코드를 넣지 않았다.

## 4. 결과 — 체결 확보

| 항목 | 값 |
| --- | --- |
| 대상 심볼 | 505(Universe 504 + SPY) |
| IEX 체결 ≥1건 | **503** |
| 유효 체결 ≥1건 | **503** |
| 체결 없음 | `NASDAQ:PSKY`, `NASDAQ:WBD` |
| 대상 심볼 체결 보고 합계 | 2,359,428 |
| 그중 유효(Last Sale Eligible) | 1,042,376 |
| 단주 | 1,316,885 |
| 확장 시간 | 919 |
| Trade Break | 0 |
| 심볼당 유효 체결 수 | 최소 14, 하위 10% 266, 중앙 1,038, 최대 21,338 |

- 파일 전체: 패킷 376,410,736개. Quote Update 428,304,460건. Trade Report 7,640,571건(전 종목).
- 체결 없는 2개: 장 전 Trading Status 일괄 전송에도 두 철자가 없었다. 그날 IEX 심볼 목록에 없었다는 뜻이다. 심볼 변경·상장 상태는 확인하지 않았다. 다른 출처로 채우지 않는다(NOT_AVAILABLE).
- **심볼 형식:** `BRK.B`, `BF.B`는 점 그대로(Nasdaq Integrated) 맞았다. 공백·슬래시·대시·붙임 변형은 0건이었다. 코드의 거래소 접두어(`NYSE:`, `NASDAQ:`, `BATS:`)를 떼면 그대로 맞는다. 매핑 문제는 없었다.

## 5. 결과 — 마지막 유효 체결 시각(가격 기준 품질)

| 구간(ET) | 심볼 수 |
| --- | --- |
| 15:55 이전 | **0** |
| 15:55:00–15:58:59 | 7 |
| 15:59:00–15:59:58 | 425 |
| 15:59:59–16:00:00 | 71 |
| 16:00:00 이후 | 0 |

- 가장 이른 마지막 체결 15:57:18 ET, 중앙값 15:59:54 ET, 가장 늦은 15:59:59 ET.
- **IEX 마지막 체결은 공식 통합 종가가 아니다.** 상장 거래소의 종가 경매(16:00)를 포함하지 않는다. 이번 표본에서는 마감 몇 초~3분 전 값이다. 마감 전 크게 이른 종목은 없었다.
- 15:55 이후만 쓰는 엄격 규칙을 적용해도 가격 확보 수는 같았다(502/504).

## 6. 결과 — 실제 V 산출(엔진 실행)

- 같은 프로세스에서 가격을 RAM에 둔 채 실행했다. 경로: `qgv2_inputs.from_published`(엄격 판독 + 신선도) → `page_identities` → `engine_inputs` → `qgv_v2.score_universe`(기본 프로필: 균형·관문 켬). 입력은 게시 `sec-qgv2.json`(as_of 2026-10-18T22:41Z, `qgv2-calc/2026-10-17.1`, 504행, 읽기 전용).
- 가격 입력: 종목별 마지막 유효 체결 1개, 통화 USD. 월말 종가(자기 과거 대비용)는 넣지 않았다.
- 엔진 실행 시간 1.0초. 프로세스 종료와 함께 가격을 버렸다.

| 항목 | 수 |
| --- | --- |
| 모집단 | 504 = GENERAL 434 + 금융 67 + 미상 3 |
| 가격 공급 코드 | 502 |
| **V 산출(GENERAL)** | **345 / 434** |
| **Q·G·V 공통** | **344** |
| 관문 제외(V 산출 후 가치 함정 관문이 종합에서 제외) | 96 |
| V 미산출(GENERAL) | 89 (축 사유 전부 `AXIS_WEIGHT_INSUFFICIENT`) |

V 미산출 89곳의 요인 사유(행마다 중복 제거, 한 행이 여러 사유 가능):

| 사유 | 행 수 |
| --- | --- |
| NORMALIZED_HISTORY_NOT_AVAILABLE | 41 |
| FCF_NOT_AVAILABLE | 35 |
| PRICE_HISTORY_NOT_AVAILABLE | 27 |
| DEBT_CASH_NOT_AVAILABLE | 25 |
| NORMALIZED_EARNINGS_NOT_AVAILABLE | 18 |
| SHARES_NOT_AVAILABLE | 10 |
| EBIT_NOT_AVAILABLE | 8 |
| NON_POSITIVE_CASHFLOW | 5 |
| NO_DEVICE_PRICE | 2 (PSKY, WBD) |
| CURRENCY_BASIS_UNCONFIRMED | 1 (ASML, EUR 재무) |
| REALIZED_GROWTH_NOT_AVAILABLE | 1 |

- 가격 의존 사유: `EV_NON_POSITIVE` **0**, `ROOT_NOT_BRACKETED` **1**(기대 점검 요인 1건, 그 행은 V 산출됨), `ROOT_NOT_CONVERGED` 0.
- 요인별 산출(GENERAL 434): 이익 수익률 370, FCF 수익률 364, 업종 대비 370, 기대 점검 343, 자기 과거 대비 0.
- 자기 과거 대비가 0인 이유: 월말 종가를 넣지 않아 `PRICE_HISTORY_NOT_AVAILABLE` 236, 경기민감 유형 `NORMALIZED_HISTORY_NOT_AVAILABLE` 177. 월말 종가는 회계연도 말월 HIST 파일 최대 5개가 더 필요하다. 이번 범위 밖이다.
- 기존 가격 무관 상한 360/434(`../qgv_scoring_standard/V_GENERAL_COVERAGE_20261018.md`)보다 15곳 적다. 가격 없음 2, 통화 1은 확인했다. 나머지 12곳은 행별로 확인하지 않았다. 미산출 행 중 `PRICE_HISTORY_NOT_AVAILABLE`이 27행이라, 월말 종가 미공급으로 V 축 50%에 못 미친 영향이 클 것으로 본다(추정).
- 소유자 관찰 목표 391/434(90%)에는 닿지 않는다. 상한 360이 이미 391보다 작다.

## 7. 자원과 실행 시각

| 항목 | 값 |
| --- | --- |
| 본 실행 | 2026-10-19 03:27:19–03:46:32 UTC (12:27–12:46 KST) |
| 벽시계 합계 | 1,153초(19분 13초). 스트림 1,152초 + 엔진 1초 |
| CPU 시간(스트림) | 1,127초 — 단일 코어 CPU가 병목 |
| 받은 바이트(gz) | 14,606,058,896 (평균 약 12.7MB/s) |
| 해제 바이트 | 62,846,153,888 (약 4.3배) |
| 최대 RSS | 109.7MB |
| 디스크 | 0(원시 파일·가격 미저장) |
| 무결성 | 스트림 MD5 = 공식 `x-goog-hash` md5 일치 |
| 전송 재시도 | 0회 |

- 빠른 패턴 탐색은 앞 600MB에서 정밀 순회보다 약 2.2배 빨랐다(22.4초 대 48.6초). 결과는 같았다. 운영 시 약 9분으로 줄일 수 있다(추정).
- 측정 전후 조회: 1MB·4MB·200MB 범위 요청, 600MB 앞부분 2회. 전체 약 16GB를 받았다.

## 8. GitHub 호스트 러너 가능성(약 14GB 디스크, 7GB RAM, 6시간)

- **기술상 가능.** 디스크 0, RAM 약 110MB, 시간 19분(같은 CPU 기준). 러너 CPU가 2배 느려도 1시간 안이다. 6시간 한도와 거리가 멀다.
- 위험: 러너→GCS 대역폭은 측정하지 않았다. 여기서는 CPU가 병목이었다(curl 200MB 범위 시험은 약 60MB/s).
- 위험: 파일 크기는 날마다 8~15GB로 변한다. 변동성 큰 날은 더 클 수 있다.
- **정책상 아직 불가.** GSQ-001(Actions 시세 수집 금지), GSQ-006·007·023(공개 V 금지), GSQ-010(공개 원시 가격 금지)은 append-only 새 결정 기록 전까지 유효하다. 이번 시험은 러너가 아니라 이 작업 컨테이너에서만 했다.
- 기준일 하루 지연(2절)과 공식 종가 아님(5절)을 게시본 `price.basis_kind`에 정직하게 적어야 한다. 예: `IEX_LAST_ELIGIBLE_TRADE`, `SESSION_CLOSE` 아님.

## 9. 남은 결정(제안만)

1. IEX 웹사이트 약관과 HIST 약관의 관계 — 자동 수집·파생 점수 공개 범위를 IEX에 서면 확인.
2. 기준일 하루 지연 수용 여부, 또는 예약 시각을 다음 날 11:00 UTC 이후로 옮길지.
3. IEX 체결 없는 종목(이번 2개)의 처리 — NOT_AVAILABLE 유지(다른 출처로 채우지 않음).
4. 자기 과거 대비용 월말 종가를 HIST 과거 파일로 얻을지(파일당 8~15GB, 최대 5개월분).
5. 통화가 다른 재무(ASML 등) 처리는 이번 범위 밖. 그대로 `CURRENCY_BASIS_UNCONFIRMED`.
