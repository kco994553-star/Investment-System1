# SEC 1회용 수집 계획 — 승인 요청 (2026-11-01, Main)

> **상태: 계획과 코드만. 실행하지 않았다.** 오너가 승인(이 PR 병합)한 뒤 Main이 실행 가지를 한 번 push해야 돈다.
> **근거(오너 2026-11-01 원문):** 「1. SEC 1회용 수집: 조건부 승인. 기간·자료 종류·요청량·비공개 저장·재사용 범위·실패 재개 방식을 적은 PR을 먼저 올리고, 승인 뒤 실행한다.」
> 함께 넣은 것(Main 11/01 결정, [EXP 문서](EXP_STOCK_INDICATOR_DECILES_V1.md) 5·6.3·7·9절): 8% 불일치 원인 분류, 비공개 인계 release 쓰기 경로.
> **숫자의 성격:** 요청 수는 코드의 고정 목록에서 센 값이다. 바이트·시간은 **추정**이고, 줄마다 출처를 적었다. 이 세션은 SEC에 요청하지 않았다(SEC 규정 User-Agent가 Actions Secret에만 있음).

## 0. 한눈에

| 항목 | 내용 |
| --- | --- |
| 기간 | full-index 2014 Q1 ~ 2026 Q4(실행일까지), FSDS 2014q1 ~ 2026q3, 일괄 zip 2개는 전체 이력 |
| 자료 | `companyfacts.zip` · `submissions.zip` · `form.idx`/`company.idx` 104개 · FSDS 51개 |
| SEC 요청 | 수집 **157건** + 8% 분류 **약 880건** = 약 1,040건. 한 번에 1건, 초당 최대 6.7건 |
| 내려받기 | 약 8.5~11.5 GB (추정) |
| 저장 | 비공개 raw 저장소의 **새 release 1개** `sec-once-v1-<run id>`. 자산 약 320개, 약 8.1 GB (추정) |
| 시간 | 약 20~35분 (추정). 작업 한도 180분 |
| 로그 | 고정된 개수 줄만 (티커·CIK·회사 이름·URL·키 없음) |
| 재개 | 같은 실행에서 "Re-run failed jobs". sha256이 맞는 자산은 다시 받지도, 다시 올리지도 않는다 |
| 하지 않는 것 | 가격, KIS, 공개 파일, 승인 전 실행 |

## 1. 목적

- EXP-STOCK-INDICATOR-DECILES-v1의 **역사 모집단**(상장폐지 포함 전 발행사)과 **PIT 재무 입력**의 원본을 한 번에 확보한다.
- 지금 있는 SEC 자료는 오늘 Universe504 생존 기업 사본뿐이다(EXP 5절). 이것으로는 생존 편향을 피할 수 없다.
- 같은 실행에서 두 가지를 더 한다.
  - 8% 불일치(공시 기호 ≠ 인스턴스 파일 이름 앞부분)의 원인 분류(EXP 9절, 9절 아래).
  - 비공개 인계 release 쓰기 경로(EXP 6.3절)를 실제로 한 번 쓴다.
- 이 실행은 **원본 확보만** 한다. 모집단 판정·점수 계산·장부는 하지 않는다(엔진 PR의 일).

## 2. 기간

S(신호일)와 공시 마감 F는 EXP 2절 표 그대로다(S 2017-02-17 ~ 2026-02-13, 후보 S 2016-02-12).

| 자료 | 받는 범위 | 이유 |
| --- | --- | --- |
| `companyfacts.zip` | 전체(기간 지정 불가) | 회사마다 XBRL 사실 전체 이력(2009년~)과 접수일·accn·서식이 들어 있다. 3년 성장률·5년 영업이익률 표준편차(FY-5까지)도 여기서 나온다 |
| `submissions.zip` | 전체(기간 지정 불가) | 회사마다 공시 목록 전체(오래된 공시는 `-submissions-001.json` 같은 추가 파일) |
| full-index `form.idx`·`company.idx` | **2014 Q1 ~ 2026 Q4** | 아래 |
| FSDS | **2014q1 ~ 2026q3** | 아래 |

full-index·FSDS를 2014년부터 받는 이유:
- 가장 이른 후보 S는 2016-02-12이고 F는 2016-02-04다. 그때 쓰는 최신 10-K는 대부분 2015년 접수다(12월 결산 FY2014).
- 결산월이 다르거나 늦게 낸 회사도 F 전 약 15개월 안이다. 2014 Q1이면 여유가 있다.
- 상장폐지(Form 25)·등록 말소(Form 15)를 첫 S 전부터 볼 수 있다.
- 8% 분류 표본(2016~2019)도 이 안에 있다.
- 재무 이력은 companyfacts가 접수일과 함께 준다. 그래서 2014년보다 앞의 색인은 필요하지 않다.

끝:
- full-index 2026 Q4는 실행일까지의 부분 색인이다. 2026 선정의 보유 기간(2027-02까지) 중 상장폐지 일부를 본다. 날마다 바뀌므로 다시 받으면 sha256이 달라진다(정상).
- FSDS 2026q3는 실행일에 아직 공개되지 않았을 수 있다. 그래서 **선택 항목**이다. 404면 `optional_missing`으로 적고 실패로 보지 않는다.
- 기간은 코드에 고정했다. 2027년 이후에 실행하게 되면 계획을 고쳐 다시 승인받는다.

## 3. 자료 종류

| 자료 | 경로 (모두 `https://www.sec.gov`) | 개수 | 무엇에 쓰나 | 엔진 입력 |
| --- | --- | --- | --- | --- |
| `companyfacts.zip` | `/Archives/edgar/daily-index/xbrl/companyfacts.zip` | 1 | 전 발행사 XBRL 재무 사실(상장폐지 회사 포함). 사실마다 `accn`·`filed`·`form`·`fy`·`fp` | PIT 재무(Q·G·V 요인), 표지 주식 수(`dei`), 발행사 시총의 주식 수 쪽 |
| `submissions.zip` | `/Archives/edgar/daily-index/bulkdata/submissions.zip` | 1 | 회사별 공시 목록, SIC, 지금 티커, 이전 이름, 8-K 항목 번호(`items`) | 발행사 목록, **8-K 3.01** 탐지, SIC 대조, 티커 구간 보조 |
| `form.idx` | `/Archives/edgar/full-index/<연>/QTR<n>/form.idx` | 52 | 분기별 모든 공시 행(서식·회사·CIK·접수일·파일), 서식 순 | **Form 25 / 25-NSE**(상장폐지), 15-12B·15-12G(등록 말소), 8-A12B(거래소 등록), 10-K·10-Q 접수일, 8% 분류 표본 |
| `company.idx` | 같은 곳 `company.idx` | 52 | form.idx와 같은 행을 회사 이름 순으로 정렬 | 이름 기반 대조(내용 중복, 열린 질문 Q3) |
| FSDS | `/files/dera/data/financial-statement-data-sets/<연>q<n>.zip` | 51 | `sub.txt`: 공시 당시 SIC·period·form·fy·fp·filed·accepted·인스턴스 이름. `num.txt`: 공시 당시 숫자 | **공시 당시 SIC**(산업군), 정정 전 원래 값 대조 |

Form 25 · 8-K 3.01 탐지:
- full-index에는 서식 이름만 있다. 8-K 항목 번호는 없다.
- 그래서 3.01(상장 기준 미달·상장폐지 통지)은 `submissions.zip`의 `items`로 엔진이 나중에 찾는다.
- 이번 실행은 연도별 서식 행 수만 센다(`SECONCE_INDEX`). 판정하지 않는다.
- 25-NSE는 거래소가, 25는 발행사가 내는 상장폐지 통지다. 8-A12B는 거래소 등록(상장 시작 근거)이다.
- 이것을 상장 상태 판정에 어떻게 쓸지는 수집 뒤 측정해서 엔진 PR에서 정한다(EXP 7절 "상장 정의").

쓰지 않는 것: `data.sec.gov` 회사별 API, EDGAR 전문 검색(`efts`), `sec.gov`(www 없는 주소). 일괄 zip이 회사별 API를 대신한다. 코드의 허용 목록은 위 네 가지 경로 모양만 받는다.

## 4. 요청량과 속도

| 종류 | 요청 | 내려받기 (추정) | 근거 |
| --- | ---: | --- | --- |
| `companyfacts.zip` | 1 | 1.41 GB | 10/30 GitHub 실행기 측정, [IEX_UNIVERSE_PLAN](../expanded_universe/IEX_UNIVERSE_PLAN_20261030.md) 2.5절 (8~15초) |
| `submissions.zip` | 1 | 1.57 GB | 같은 측정 (15초) |
| `form.idx` + `company.idx` | 104 | 원본 약 3.6 GB, gzip 전송이면 약 0.6 GB | **추정.** SEC 디렉터리 목록(웹 검색 요약)에서 현재 분기 form.idx가 10/24에 9.25 MB(약 17거래일) → 분기 약 35 MB. 옛 분기 크기는 미확인 |
| FSDS | 51 (마지막 1개 선택) | 약 4.5 GB (파일당 약 55~120 MB) | **추정.** SEC FSDS 페이지(웹 검색 요약): 2011q3 55 MB, 2021q2 87 MB, 2024q1 119 MB |
| 8% 분류: 공시 목록 + 인스턴스 | 약 880 | 약 0.1~1 GB | 10/31 실행 896건(form.idx 16건 포함, 이번에는 저장본을 읽어 0건). 바이트는 기록이 없어 **추정** |
| **합계** | **약 1,040** | **약 8.5~11.5 GB** | |

- 속도: 모든 요청 전에 0.15초를 쉰다. 초당 최대 6.7건이다(SEC 공정 접근 한도 초당 10건). 한 번에 하나만 보낸다.
- User-Agent: Secret `SEC_USER_AGENT`만 쓴다. 로그·파일 어디에도 남기지 않는다.
- 상한: 수집은 요청 500건(재시도 포함)·60분. 분류는 옮긴 측정 코드의 상한(2,500건·20분)을 그대로 쓴다.
- 멈춤: 403 연속 5번 또는 429 누적 10번이면 멈춘다(차단 신호).
- 크기 상한: 일괄 zip 4 GiB, 색인 512 MiB, FSDS 1 GiB(파일당 본문).
- 시간(추정): 일괄 zip 1분 미만 + 색인 3~6분 + FSDS 2~5분 + zip CRC 검사 3~5분 + 분류 5~6분(10/31 315초) + 업로드 2~5분 + 되받아 검사 2~5분 = **약 20~35분**.
- 디스크: 약 8.3 GB를 실행기에 둔다. 시작 전에 빈 공간 14 GB 이상인지 확인하고, 모자라면 요청 전에 멈춘다.

## 5. 비공개 저장

위치와 경로:
- 비공개 저장소 `investment-system1-raw`의 **새 release 1개**, 이름 `sec-once-v1-<run id>`.
- 기존 승인 방식(EXP 6.3절)이다. 공개 저장소 Actions가 Secret `RAW_REPO_TOKEN`으로 release를 만든다. `sec-universe-raw-*`·`qgv-official-*`·`forward-ledger-*`도 이렇게 저장된다.

코드 제한(토큰은 저장소 전체 범위라서 권한이 아니라 **코드로** 막는다):
- release 이름은 `sec-once-v1-` + 숫자 run id만 된다. 다른 이름은 코드가 거부한다.
- 허용 호출은 네 가지뿐이다.
  - release 만들기(POST).
  - 그 release에 자산 올리기(POST).
  - 그 release를 자기 이름으로 읽기(재시도 때만).
  - 그 release의 자산 내려받기(검사용).
- PATCH·PUT·DELETE는 없다. release 목록 조회도 없다.
- 첫 시도는 아무것도 읽지 않고 만들기만 한다. 같은 이름이 이미 있으면 멈춘다(`RELEASE_EXISTS`).
- 다른 release(KIS 포함)는 이름 검사에서 막힌다. 읽지도, 바꾸지도, 지우지도 않는다.
- `make_latest=false`로 만든다. raw 저장소의 "최신" 표시를 바꾸지 않는다.
- 실행 가지·저장소 이름도 코드가 다시 확인한다. 다른 가지에서는 요청 전에 멈춘다.

자산 이름:

| 자산 | 개수 |
| --- | ---: |
| `companyfacts.zip`, `submissions.zip` | 2 |
| `full-index-<연>-QTR<n>-form.idx.gz`, `…-company.idx.gz` | 104 |
| `fsds-<연>q<n>.zip` | 51 (2026q3가 없으면 50) |
| `ticker-mismatch-rows.json` (8% 분류 건별 행) | 1 |
| 위 각 자산의 `<이름>.sha256` | 158 |
| `sec-once-manifest-a<시도>.json` + `.sha256` | 2 |
| 합계 | 약 318 |

- 색인은 gzip으로 줄여 저장한다(mtime 0이라 같은 입력이면 같은 바이트). 원본 sha256은 manifest에 적는다.
- manifest에는 파일마다 원본 URL·원본 바이트·원본 sha256·저장 바이트·저장 sha256·`Last-Modified`·받은 시각·zip 검사 결과를 적는다. 실행 ID·커밋·시도 번호, 실패 목록, 권리·재사용 문구도 적는다.
- manifest는 **맨 마지막에** 올린다. manifest가 있고 `complete: true`인 release만 완성본으로 본다.
- **2 GiB 한도:** GitHub release 자산은 개당 2 GiB 미만이어야 한다.
  - 지금 가장 큰 것은 `submissions.zip` 1.57 GB(10/30 측정)다. 나누지 않을 것으로 본다.
  - 2,000,000,000 바이트를 넘으면 1,900,000,000 바이트 조각(`.part01`, `.part02` …)과 `.parts.json`(전체 sha256·조각 목록)으로 올린다.
  - 복원: 조각을 순서대로 이어 붙이고 전체 sha256을 확인한다. (열린 질문 Q4)
- 크기(추정): 약 8.1 GB. GitHub 문서 기준 release 전체 크기 한도는 없고, release당 자산 1,000개다(이 세션에서 다시 확인하지 못함).

## 6. 재사용 범위

- 읽는 사람: 오너, Main, Codex. 저장소 접근 권한이 있는 사람, 또는 기존 읽기 토큰 `RAW_REPO_READ_TOKEN`을 쓰는 **따로 승인된** Actions 단계.
- 쓰는 연구:
  - EXP-STOCK-INDICATOR-DECILES-v1: 역사 모집단, PIT 재무, 공시 당시 SIC, 상장폐지·등록 말소 사건.
  - 전진검증 v3의 시점별 티커 ↔ CIK 구간(`FV3-PIT-TICKER`).
  - 8% 불일치 분류.
  - 다른 연구에 쓰려면 새 오너 결정이 필요하다.
- 성격: SEC 공개 자료다(재배포 허용, SEC "Privacy and dissemination"). 그래도 **비공개로 둔다.** 파생 연구 결과와 한곳에 두기 위해서다. 공개 저장소·Pages에는 원본도 건별 파생 행도 넣지 않는다.
- 들어가지 않는 것: 가격, 가격에서 나온 값, KIS 자료, 개인 자료.
- 보존: 오너가 지울 때까지(release 자산은 만료되지 않는다).

## 7. 실패와 재개

| 상황 | 동작 |
| --- | --- |
| 429 · 5xx · 네트워크 오류 · 잘린 본문 | 같은 요청을 최대 2번 다시 한다(5초, 20초 대기. 429는 `Retry-After` 최대 60초) |
| 404 · 그 밖의 4xx | 다시 하지 않는다. 실패 목록에 적고 다음 파일로 간다 (FSDS 2026q3의 404만 실패 아님) |
| 403 연속 5번 · 429 누적 10번 · 요청 상한 · 시간 상한 | 그 자리에서 멈춘다. 받은 것은 저장한다 |
| 크기·sha256 확인 | 파일마다 받으면서 sha256과 바이트를 센다. `Content-Length`와 다르거나 gzip 끝이 없으면 "잘림"으로 다시 받는다 |
| zip CRC 실패 | 그 zip을 한 번 새로 받는다(밤사이 다시 만들어지는 중일 수 있음). 또 실패하면 실패 목록 |
| 업로드 실패 | 그 자산만 실패로 적고 다음 자산을 올린다. manifest는 `complete: false` |
| 업로드 뒤 검사 | 이번 시도에 올린 자산을 모두 내려받아 sha256을 다시 맞춘다 |
| 부분 실패 | 받은 것과 manifest를 올린다. 마지막 단계가 작업을 실패로 끝낸다 |
| **재개** | 같은 실행에서 "Re-run failed jobs"를 누른다. run id가 같아 release도 같다. sidecar sha256이 맞는 자산은 내려받아 쓰고, SEC에 다시 요청하지도 다시 올리지도 않는다 |
| 이전 시도의 깨진 자산 | 지우지 않는다(만들기만 허용). 새 파일을 `a<시도>-<이름>`으로 올리고 manifest가 그것을 가리킨다 |
| 분류 결과 | 완성본이 이미 저장돼 있으면 다시 하지 않는다. 미완성이면 다시 한다 |
| 새 push | 새 run id → 새 release가 된다(재개가 아님). 하지 않는다 |

## 8. 로그에 남는 것

고정 형식 줄만 남는다. 숫자·코드·MB·초뿐이다.
- `SECONCE_PLAN`, `SECONCE_DISK`: 고정 목록과 빈 디스크.
- `SECONCE_RESUME`: 재시도 때 이미 있는 자산 수.
- `SECONCE_FILES kind=bulk|index|fsds`: 계획·성공·재사용·실패·선택 누락 수, MB.
- `SECONCE_ZIP`: zip 항목 수, `-submissions-NNN.json` 추가 파일 수, CRC 결과.
- `SECONCE_INDEX year=…`: 연도별 색인 행 수와 서식별 수(10-K, 10-Q, 8-K, 25, 25-NSE, 8-A12B, 15-12B, 15-12G, 15-15D).
- `SECONCE_REQUESTS`: 요청·재시도·403/429/5xx 수, MB, 초, 멈춘 이유, 완료 여부.
- `TICKERMIX_*`, `PITTICKER*`: 8% 분류(9절).
- `SECONCE_RELEASE`, `SECONCE_VERIFY`, `SECONCE_DONE`: 업로드·되받기 검사·완료.
- 남지 않는 것: 티커, CIK, 회사 이름, URL, User-Agent, 토큰, 예외 메시지(클래스 이름과 고정 코드만).

## 9. 8% 불일치 원인 분류

- 대상: 10/31 측정(run 41255597310)에서 `dei:TradingSymbol`이 있는 209건 중 16건. 인스턴스 파일 이름 앞부분이 기호와 달랐다(대소문자 무시). 건별 자료는 남아 있지 않다.
- 방법:
  - 옮긴 측정 코드(`fv3_pit_ticker_measure.py`)로 같은 표본을 다시 만든다. 같은 120개 패널, 같은 2016~2019 공시 선택, 같은 인스턴스 선택, 같은 `dei` 읽기다.
  - form.idx는 이번에 저장한 사본을 읽는다(SEC 재요청 없음). 공시 목록과 인스턴스는 다시 받는다(약 880건).
  - 회사 이름은 form.idx, 지금 티커와 이전 이름은 저장한 `submissions.zip`에서 읽는다.
- 분류(규칙 순서대로, 처음 맞는 것):

| 분류 | 규칙 |
| --- | --- |
| 표기 차이 | 점·하이픈·공백·거래소 표기("NYSE:")를 빼면 같다 (대소문자만 다른 경우는 원래 측정에서 이미 같음으로 셌다) |
| 종류주 기호 | 끝 글자 하나만 다르다. 구분 기호 뒤 글자(BRK / BRK.B)이거나 A·B·C·K·L(GOOG / GOOGL). 또는 둘 다 그 발행사의 지금 티커다(티커 2개 이상) |
| 옛 기호 | 앞부분이 같은 발행사의 다른 기호다. 다른 해 공시의 기호나 확인된 앞부분, 또는 지금 티커 |
| inline XBRL 문서 이름 | inline 공시다(인스턴스 이름이 회사가 정한 문서 이름을 따른다) |
| 회사 약칭·문서 이름 | 티커 모양이 아니다(6자 이상이거나 숫자 포함), 문서 단어(form, annual, report …), 또는 회사 이름의 단어·머리글자 |
| 기타 | 나머지. 값이 빈 기호(`xsi:nil`)는 따로 센다 |

- 출력: 분류별 개수와 10/31과 같은지(`same=yes|no`)만 로그에 남긴다. 원래 형식의 `PITTICKER` 줄도 같이 남겨 10/31과 비교한다.
- 건별 행(CIK, accession, 기호, 앞부분, 인스턴스 이름, 분류, 근거)은 비공개 release의 `ticker-mismatch-rows.json`에만 둔다.
- 한계:
  - 규칙 기반이다. 사람이 검토한 분류가 아니다.
  - 표본은 지금 살아 있는 발행사다(10/31과 같은 한계).
  - "옛 기호"는 같은 회사의 다른 해 공시 기호와 지금 티커로만 안다. 옛 기호 이력 전체는 없다.
- 결과가 나올 때까지 공시 기호와 파일 이름이 다른 연결은 확정 신원으로 쓰지 않는다(EXP 9절 그대로).

## 10. 하지 않는 것

- 승인 전에 병합하거나 실행하지 않는다. 이 PR은 계획과 코드뿐이다.
- 가격·가격 파생 값·KIS 자료를 받지도 저장하지도 않는다.
- 공개 파일을 만들지 않는다. Pages·Actions artifact·캐시·step summary가 없다.
- `data.sec.gov` API·EDGAR 전문 검색을 쓰지 않는다.
- 모집단 판정·점수 계산·장부 계산을 하지 않는다.
- 기존 워크플로·가드·방법론·가중치를 바꾸지 않는다.
- 측정 가지의 push 워크플로(`fv3-pit-ticker-measure.yml`)는 옮기지 않는다. 이 PR의 워크플로가 대신한다.

## 11. 승인 뒤 실행 절차

1. 오너: 이 PR을 승인하고 병합한다.
2. Main: 병합 커밋에서 가지 `claude/sec-once-collect-run`을 만들어 **한 번** push한다. 워크플로가 한 번 돈다.
   - 다른 이벤트(PR, 일정, 수동 실행)로는 돌지 않는다. 작업 조건과 코드가 가지·저장소를 다시 확인한다.
3. 확인: 로그 끝의 `SECONCE_DONE complete=yes`, `SECONCE_VERIFY … bad=0`, `TICKERMIX … same=yes`.
4. 실패하면: 같은 실행에서 "Re-run failed jobs"를 누른다. 새 push는 하지 않는다.
5. 끝나면:
   - 오너가 실행 가지를 지운다(세션에는 가지 삭제 권한이 없다).
   - 측정 가지 `claude/fv3-pit-ticker-measure`도 지워도 된다(코드는 이 PR로 옮겼다).
   - Main이 후속 PR로 이 워크플로를 지운다(Q5).
6. 보고: 개수 줄과 release 이름을 [USER_DECISIONS_PENDING](../USER_DECISIONS_PENDING.md)과 인계 문서에 적는다.

## 12. 열린 질문 (오너 결정)

| # | 질문 | 기본안 |
| --- | --- | --- |
| Q1 | full-index·FSDS 시작 연도 | **2014.** 2009년(XBRL 시작)부터 받으면 요청 +60건, 약 +2~3 GB(추정). companyfacts가 재무 이력을 주므로 필요하지 않다고 본다 |
| Q2 | 승인 방식 | **병합 뒤 실행.** 검토한 코드와 실행하는 코드가 같다. PR 머리 커밋을 실행 가지로 push하는 방법도 있다 |
| Q3 | `company.idx` | **받는다**(지시대로). form.idx와 같은 행(정렬만 다름)이라 빼면 요청 52건·저장 약 0.3 GB(추정)를 줄인다 |
| Q4 | 2 GiB 넘는 zip 나누기 | **허용 제안.** 조각 + `.parts.json` + 전체 sha256. 지금 크기로는 나눌 일이 없을 것으로 본다 |
| Q5 | 실행 뒤 워크플로 | **후속 PR로 지운다.** 남겨 두면 실행 가지에 push할 때만 돈다 |

## 13. 이 PR의 파일

| 파일 | 내용 |
| --- | --- |
| `implementation/docs/lab/SEC_ONCE_COLLECTION_PLAN_20261101.md` | 이 계획 |
| `.github/workflows/sec-once-collect.yml` | 1회용 워크플로. 실행 가지 push로만, `contents: read`, 단계마다 Secret 하나 |
| `implementation/tools/measure_once/sec_once_collect.py` | 수집·재개·비공개 release 업로드·완료 확인 |
| `implementation/tools/measure_once/sec_once_ticker_mismatch.py` | 8% 분류 |
| `implementation/tools/measure_once/fv3_pit_ticker_measure.py` | 10/31 측정 코드. `claude/fv3-pit-ticker-measure`(`ead5ffdd`)에서 옮김, 동작 그대로 |
| `implementation/tests/test_sec_once_collect.py`, `test_sec_once_ticker_mismatch.py`, `test_fv3_pit_ticker_measure.py` | 가짜 입력만 쓰는 시험(네트워크·Secret 없음). 워크플로 모양 시험 포함 |

- 재사용한 것: 측정 코드의 User-Agent 규칙·form.idx 읽기·인스턴스 선택, `tools/raw_store_release.py`의 GitHub 전송(리다이렉트 거부, 토큰은 `RAW_REPO_TOKEN`에서만).
- 저장소의 SEC 클라이언트(`providers/sec_collection.py`)는 응답 상한이 32 MiB라 1.5 GB zip을 받을 수 없다. 그래서 스트리밍 다운로더를 새로 두었다.
