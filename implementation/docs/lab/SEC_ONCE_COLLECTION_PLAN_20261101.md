# SEC 1회용 수집 계획 — 승인 요청 (2026-11-01, Main)

> **상태: 계획과 코드만. 실행하지 않았다.** 오너가 승인(이 PR 병합)한 뒤 Main이 실행 가지를 한 번 push해야 돈다.
> **근거(오너 2026-11-01 원문):** 「1. SEC 1회용 수집: 조건부 승인. 기간·자료 종류·요청량·비공개 저장·재사용 범위·실패 재개 방식을 적은 PR을 먼저 올리고, 승인 뒤 실행한다.」
> **함께 넣은 것:** 8% 불일치 원인 분류(오너 결정 9). 엔진 인계 release(`exp-deciles-v1-*`) 쓰기는 **넣지 않았다**(1절, Q6).
> **먼저 병합할 PR:** 결정 PR(`claude/decisions-1101-second`, `e360c41b`). 이 문서가 인용하는 [EXP 문서](EXP_STOCK_INDICATOR_DECILES_V1.md) 5·6.3·7·9·10.8절은 그 PR에만 있다. 필요한 문장은 아래에 그대로 옮겨 적었다.
> **숫자의 성격:** 요청 수는 코드의 고정 목록에서 센 값이다. 바이트·시간은 **추정**이다. 출처와 미확인 여부를 줄마다 적었다(14절). 이 세션은 SEC에 요청하지 않았다(SEC 규정 User-Agent가 Actions Secret에만 있음).

## 0. 한눈에

| 항목 | 내용 |
| --- | --- |
| 기간 | full-index 2014 Q1 ~ 2026 Q4(실행일까지) · FSDS 2014q1 ~ 2026q3 · 일괄 zip 2개는 전체 이력 |
| 자료 | `companyfacts.zip` · `submissions.zip` · `form.idx`/`company.idx` 104개 · FSDS 51개 |
| SEC 요청 | 수집 **157건** + 8% 분류 **약 880건** = **약 1,040건** |
| 요청 상한 | 시도 1번에 최대 **3,000건**(수집 500 + 분류 2,500). 한 번에 1건, 초당 최대 6.7건 |
| 내려받기 | **약 8~9 GB**(색인을 gzip으로 받을 때, 추정). gzip이 안 되면 최대 **약 14 GB** |
| 저장 | 비공개 raw 저장소의 **새 release 1개** `sec-once-v1-<run id>`. 자산 318개, 약 8.1 GB(추정) |
| 비공개 확인 | 시도마다 SEC 요청 **전에** raw 저장소가 비공개인지 확인. 아니면 멈춤 |
| 시간 | 약 20~35분(추정). 작업 한도 180분 |
| 로그 | 고정된 개수 줄만(티커·CIK·회사 이름·URL·키 없음) |
| 재개 | 오너가 "Re-run failed jobs"(30일 안). sha256이 맞는 자산은 다시 받지도, 다시 올리지도 않음 |
| 하지 않는 것 | 가격, KIS, 공개 파일, 승인 전 실행, 엔진 인계 release |

## 1. 목적

- EXP-STOCK-INDICATOR-DECILES-v1에 필요한 **SEC 원본의 일부**를 한 번에 받는다. 상장폐지 회사까지 포함한 발행사 목록·XBRL 재무·공시 목록·공시 당시 SIC다.
- 지금 있는 SEC 자료는 오늘 Universe504 생존 기업 사본뿐이다(EXP 5절). 이것으로는 생존 편향을 피할 수 없다.
- **이 수집만으로 역사 모집단을 확보했다고 하지 않는다.** 오너 결정 4: 「SEC 발행사 목록만으로 역사 모집단 확보를 선언하지 마라.」 채워지지 않는 입력은 3.1절에 있다.
- 같은 실행에서 8% 불일치(공시 기호 ≠ 인스턴스 파일 이름 앞부분)의 원인을 분류한다(9절).
- 이 실행은 **원본 확보만** 한다. 모집단 판정·점수 계산·장부는 하지 않는다(엔진 PR의 일).
- **엔진 인계 release는 이 PR에 없다.**
  - EXP 6.3절은 인계 release 이름을 `exp-deciles-v1-<run_id>`로 고정하고 "SEC 1회용 수집 PR에 함께 넣어 승인받는다"고 적었다.
  - 그런데 인계할 엔진 출력(선정 입력·장부 입력)이 아직 없다. 그래서 이 PR은 원본 release `sec-once-v1-*`만 쓴다.
  - 쓰는 방식은 같다: 공개 저장소 Actions + `RAW_REPO_TOKEN`, 코드로 이름 고정, 새 release만 만들기.
  - 인계 release 쓰기와, 엔진·Main이 이 release를 읽는 Actions 단계는 **후속 PR과 승인**이 필요하다(Q6).

## 2. 기간

S(신호일)와 공시 마감 F는 EXP 2절 표 그대로다(S 2017-02-17 ~ 2026-02-13, 후보 S 2016-02-12).

| 자료 | 받는 범위 |
| --- | --- |
| `companyfacts.zip` | 전체(기간 지정 불가). 회사마다 XBRL 사실 전체 이력(2009년~)과 접수일·accn·서식 |
| `submissions.zip` | 전체(기간 지정 불가). 회사마다 공시 목록 전체. 오래된 공시는 `CIK…-submissions-001.json` 같은 추가 파일 |
| full-index `form.idx`·`company.idx` | **2014 Q1 ~ 2026 Q4** |
| FSDS | **2014q1 ~ 2026q3** |

full-index·FSDS를 2014년부터 받는 이유:
- 가장 이른 후보 S는 2016-02-12이고 F는 2016-02-04다. 그때 쓰는 최신 10-K는 대부분 2015년 접수다(12월 결산 FY2014).
- 결산월이 다르거나 늦게 낸 회사도 F 전 약 15개월 안이다. 2014 Q1이면 여유가 있다.
- 2014년부터의 상장폐지(Form 25)·등록 말소(Form 15)는 색인으로 바로 센다. **2014년 전 사건은 `submissions.zip`의 전체 공시 목록(추가 파일 포함)에서 엔진이 찾는다.** 색인은 그 교차 확인이다.
- 8% 분류 표본(2016~2019)도 이 안에 있다.

재무 이력의 한계(XBRL에 있는 범위에서만):
- 3년 성장률·5년 영업이익률 표준편차(FY-5까지)는 companyfacts에서 나온다. **XBRL에 있는 범위에서만**이다.
- S 2016-02-12의 FY-5는 대략 FY2009다. 소규모 회사는 2011-06-15 이후 끝나는 기간부터, IFRS 외국 발행사는 2017-12-15 이후 끝나는 기간부터 XBRL이 있다.
- 그래서 S 2016·2017에는 이런 회사의 FY-5·성장률 입력이 빠질 수 있다. 엔진이 사유 있는 NA로 둔다.
- full-index·FSDS를 2014년보다 일찍 받아도 이 빈칸은 채워지지 않는다(FSDS도 같은 XBRL 공시에서 나옴). 그래서 시작 연도는 2014로 둔다(Q1).

끝:
- full-index 2026 Q4는 실행일까지의 부분 색인이다. 날마다 바뀌므로 다시 받으면 sha256이 달라진다(정상).
- FSDS 2026q3는 SEC 페이지에 이미 올라와 있다(62.13 MB, 검토자 확인). 코드에서는 여전히 **선택 항목**이다. 404면 `optional_missing`으로 적고 실패로 보지 않는다.
- 기간은 코드에 고정했다. 2027년 이후에 실행하게 되면 계획을 고쳐 다시 승인받는다.

## 3. 자료 종류

| 자료 | 개수 | 쓰는 곳 |
| --- | ---: | --- |
| `companyfacts.zip` | 1 | PIT 재무(Q·G·V 요인). 단일 종류 발행사의 표지 주식 수 |
| `submissions.zip` | 1 | 발행사 목록, 지금 티커·이전 이름, SIC, 8-K 항목 번호(3.01 탐지), Form 25·15·8-A12B 전체 이력 |
| `form.idx` | 52 | 분기별 모든 공시 행. Form 25/25-NSE·15·8-A12B 수, 10-K·10-Q 접수일, 8% 분류 표본 |
| `company.idx` | 52 | form.idx와 같은 행(회사 이름 순). 이름 대조(Q3) |
| FSDS | 51 | `sub.txt` 공시 당시 SIC·기간·접수 시각·인스턴스 이름, `num.txt` 공시 당시 숫자(정정 전 대조) |
| 분류용 공시 목록·인스턴스 | 약 880 요청 | 8% 분류만. 2016~2019 표본 공시. 저장은 파생 행만(9절) |

경로(모두 `https://www.sec.gov`, 검토자가 SEC 공식 페이지로 확인):
- `/Archives/edgar/daily-index/xbrl/companyfacts.zip`
- `/Archives/edgar/daily-index/bulkdata/submissions.zip` (SEC "EDGAR Application Programming Interfaces" 페이지)
- `/Archives/edgar/full-index/<연>/QTR<n>/form.idx`, `…/company.idx` (SEC가 따로 두는 `form.gz`·`company.gz`는 받지 않는다. 대신 gzip 전송을 요청하고 실행기에서 gzip으로 저장한다)
- `/files/dera/data/financial-statement-data-sets/<연>q<n>.zip` (SEC FSDS 페이지. 2009q1부터 있음)
- 분류만: `/Archives/edgar/data/<cik>/<accession>/index.json`, `<accession>-index.htm`, XBRL 인스턴스 파일. 저장한 form.idx가 없는 분기만 `/Archives/edgar/full-index/<연>/QTR<n>/form.idx`를 다시 받는다.

허용 목록(코드):
- 수집 도구는 위 네 가지 경로 모양만 받는다(정확히 일치).
- 분류 도구는 옮긴 측정 코드의 규칙대로 `www.sec.gov/Archives/edgar/` 아래만 받는다. 표본 공시 경로만 만든다.
- 둘 다 리다이렉트를 거부한다. `data.sec.gov` 회사별 API, EDGAR 전문 검색(`efts`), `sec.gov`(www 없는 주소)는 쓰지 않는다.

Form 25 · 8-K 3.01 · 8-A12B:
- full-index에는 서식 이름만 있다. 8-K 항목 번호는 없다. 3.01(상장 기준 미달·상장폐지 통지)은 `submissions.zip`의 `items`로 엔진이 나중에 찾는다.
- 25-NSE는 거래소가, 25는 발행사가 내는 상장폐지 통지다. 8-A12B는 거래소 등록(상장 시작 근거)이다.
- **EDGAR 이전(1990년대 중반 전)에 등록한 회사는 8-A12B가 어디에도 없다.** 이 자료로는 그 회사의 상장 시작을 알 수 없다.
- 이번 실행은 연도별 서식 행 수만 센다(`SECONCE_INDEX`). 판정하지 않는다. 상장 상태 판정 규칙은 수집 뒤 측정해서 엔진 PR에서 정한다(EXP 7절: "SEC 수집 뒤 상장 등록·폐지 공시로 판정 범위를 잰다").

### 3.1 이 수집으로 채워지지 않는 엔진 입력

EXP 5절·10.8절이 요구하는 입력과 비교했다. **"아님"과 "일부"는 엔진 첫 구간(S 2018-02-16)에도 따로 필요하다.**

| 입력 | 이 수집 | 이유 |
| --- | --- | --- |
| PIT 재무 숫자 | 일부 | XBRL 범위만. 소규모 회사·IFRS 외국 발행사의 이른 연도는 없다(2절) |
| 공시 당시 SIC | 대부분 | FSDS `sub.sic`("공시일 기준" 배정). XBRL 없는 공시는 없다 |
| 발행사 주식 수(시총용) | 일부 | **단일 종류 발행사만**(종류 구분 없는 `dei:EntityCommonStockSharesOutstanding`). 종류별 표지 주식 수는 일괄 파일에 없다. 10/30 측정: 국내 다중 종류주 279곳·외국 145곳 판정 불가([IEX_UNIVERSE_PLAN](../expanded_universe/IEX_UNIVERSE_PLAN_20261030.md)). 공시별 표지 XBRL 수집이 따로 필요하다(Q7) |
| S의 상장 상태 | 일부 | 근거 사건(Form 25/25-NSE·15·8-A12B)만 준다. EDGAR 이전 등록은 시작 근거가 없다. 판정은 엔진 PR |
| 증권 종류·거래소(보통주·종류주·ADR·REIT) | 아님 | `dei:Security12bTitle`·`SecurityExchangeName`은 글자 사실이라 companyfacts·FSDS 숫자 파일에 없다. 2019-06 이후 공시에만 붙는다 |
| ADR 비율 | 아님 | 네 원천 어디에도 없다 |
| 거래 가능 여부 | 아님 | 승인된 가격 원천의 실제 거래 기록이 필요하다 |
| 배당·분할·합병 대가 | 아님 | 배당락일은 XBRL에 없다. 합병 대가는 공시 문서를 읽어야 한다 |
| 시점별 티커 ↔ CIK 구간 | 아님 | `dei:TradingSymbol`은 글자 사실이라 일괄 파일에 없다. `submissions.zip` 티커는 오늘 값이다. 분류 표본 437건만 읽는다 |
| 가격(S 신호 가격, T 시가) | 아님 | 이 수집 범위 밖 |

## 4. 요청량과 속도

| 종류 | 요청 | 내려받기(추정) | 근거 |
| --- | ---: | --- | --- |
| `companyfacts.zip` | 1 | 1.41 GB | 10/30 GitHub 실행기 측정([IEX_UNIVERSE_PLAN](../expanded_universe/IEX_UNIVERSE_PLAN_20261030.md) 2.5절) |
| `submissions.zip` | 1 | 1.57 GB | 같은 측정 |
| `form.idx` + `company.idx` | 104 | gzip 전송 약 0.5 GB. 아니면 약 4.5~5.6 GB | SEC 디렉터리 목록: 온전한 분기 파일당 약 50~54 MB(2023~2025 Q1), SEC `form.gz`는 약 5 MB(약 10%). 2014~2022 분기 크기는 **미확인**(40~55 MB로 가정) |
| FSDS | 51 | 약 4.55 GB | SEC FSDS 페이지 목록 합계 4,548.5 MB(검토자 확인). 파일 하나 최대 약 120 MB |
| 8% 분류: 공시 목록 + 인스턴스 | 약 880 | 약 0.1~1 GB | 10/31 실행 896건(form.idx 16건 포함, 이번에는 저장본을 읽어 0건). 바이트 기록이 없어 **추정** |
| **합계** | **약 1,040** | **약 8~9 GB**(gzip이 안 되면 최대 약 14 GB) | |

- 속도: 모든 요청 전에 0.15초를 쉰다. 초당 최대 6.7건이다(SEC 공정 접근 한도 초당 10건). 한 번에 하나만 보낸다.
- User-Agent: Secret `SEC_USER_AGENT`만 쓴다. 로그·파일 어디에도 남기지 않는다.
- 상한(시도 1번 기준):
  - 수집: 요청 500건(재시도 포함)·60분.
  - 분류: 옮긴 측정 코드의 상한 2,500건·20분.
  - **합쳐서 최대 3,000건.** 수집이 차단 신호·상한으로 멈추면 분류는 요청을 하나도 보내지 않는다(7절). 다시 실행(재개)하면 그 시도에 다시 최대 3,000건이다.
- 멈춤: 403 연속 5번 또는 429 누적 10번이면 멈춘다(차단 신호).
- 크기 상한: 일괄 zip 4 GiB, 색인 512 MiB, FSDS 1 GiB(파일당 본문). 분류 인스턴스 96 MiB.
- 시간(추정): 일괄 zip 1분 미만 + 색인 3~6분 + FSDS 2~5분 + zip CRC 검사 3~5분 + 분류 5~6분(10/31 315초) + 업로드 2~5분 + 되받아 검사 2~5분 = **약 20~35분**.
- 단계 시간 한도: 재개 확인 25분, 수집 75분, 분류 25분, 업로드 45분. 작업 전체 180분.
- 디스크:
  - 실행기에 두는 양은 최대 약 8.1 GB(7.5 GiB, 추정)다. 받는 중인 파일(`.part`)도 이 안에 든다.
  - 시작 전에 빈 공간이 **11 GiB** 이상인지 본다. 모자라면 요청 전에 멈춘다(7절).
  - GitHub가 보장하는 표준 Linux 실행기 SSD는 14 GB다. 2025-10 보고로 ubuntu-24.04의 실제 빈 공간은 약 19 GiB였다(이 세션에서 재지 않음).

## 5. 비공개 저장

위치와 경로:
- 비공개 저장소 `investment-system1-raw`의 **새 release 1개**, 이름 `sec-once-v1-<run id>`.
- 기존 승인 방식이다. 공개 저장소 Actions가 Secret `RAW_REPO_TOKEN`으로 release를 만든다. `sec-universe-raw-*`·`qgv-official-*`·`forward-ledger-*`도 이렇게 저장된다.

비공개인지 먼저 확인(시도마다):
- 재개 확인 단계가 **매 시도 맨 먼저** raw 저장소 정보를 읽는다(`GET /repos/kco994553-star/investment-system1-raw`).
- 통과 조건: 응답 200, 저장소 이름이 정확히 같음, `private: true`, `visibility: private`.
- 하나라도 아니면 고정 코드로 멈춘다: `RAW_REPO_NOT_PRIVATE`, `RAW_REPO_MISMATCH`, `RAW_REPO_HTTP401`(토큰 만료 등), `RAW_REPO_UNREACHABLE`.
- 통과하면 그 시도 번호를 적은 표시 파일을 남긴다. **수집과 분류는 이 표시가 없으면 SEC 요청 없이 멈춘다**(`RAW_PREFLIGHT_MISSING`).
- 업로드 단계는 release를 만들기 직전에 한 번 더 확인한다.
- 그래서 토큰이 만료됐으면 SEC에 요청하기 전에 멈춘다. 저장소가 공개로 바뀌었으면 아무것도 올리지 않는다.

코드 제한(토큰은 저장소 전체 범위라서 권한이 아니라 **코드로** 막는다):
- release 이름은 `sec-once-v1-` + 숫자 run id만 된다. 다른 이름은 코드가 거부한다.
- 허용 호출은 다섯 가지뿐이다.
  - raw 저장소 정보 읽기(비공개 확인).
  - release 만들기(POST).
  - 그 release에 자산 올리기(POST).
  - 그 release를 자기 이름으로 읽기(재시도 때만).
  - 그 release의 자산 내려받기(검사·재개용).
- PATCH·PUT·DELETE는 없다. release 목록 조회도 없다.
- 첫 시도는 release를 읽지 않고 만들기만 한다. 같은 이름이 이미 있으면 멈춘다(`RELEASE_EXISTS`).
- 다른 release(KIS 포함)는 이름 검사에서 막힌다. 읽지도, 바꾸지도, 지우지도 않는다.
- `make_latest=false`로 만든다. raw 저장소의 "최신" 표시를 바꾸지 않는다.
- 실행 가지·저장소 이름도 워크플로와 코드가 다시 확인한다. 다른 가지에서는 요청 전에 멈춘다.

Secret을 가진 단계의 보호:
- 오프라인 시험은 **따로 된 작업(job)**에서 돈다. pytest를 거기서만 설치한다. 그 실행기는 Secret을 보지 않는다.
- Secret을 가진 수집 작업은 새 실행기에서 돈다. pip로 아무것도 설치하지 않는다.
- 도구는 모두 `python -I -S`로 시작한다. 설치된 패키지·`.pth` 파일·`PYTHONPATH`를 읽지 않는다. 도구는 표준 라이브러리만 쓴다.
- 단계마다 Secret은 하나뿐이다(`RAW_REPO_TOKEN` 또는 `SEC_USER_AGENT`).

자산 이름:

| 자산 | 개수 |
| --- | ---: |
| `companyfacts.zip`, `submissions.zip` | 2 |
| `full-index-<연>-QTR<n>-form.idx.gz`, `…-company.idx.gz` | 104 |
| `fsds-<연>q<n>.zip` | 51 |
| `ticker-mismatch-rows.json` (8% 분류 건별 행) | 1 |
| 위 각 자산의 `<이름>.sha256` | 158 |
| `sec-once-manifest-a<시도>.json` + `.sha256` | 2 |
| 합계(첫 시도가 모두 성공할 때) | 318 |

- 색인은 gzip으로 줄여 저장한다(mtime 0이라 같은 입력이면 같은 바이트). 원본 sha256은 manifest에 적는다.
- manifest에는 파일마다 원본 URL·원본 바이트·원본 sha256·저장 바이트·저장 sha256·`Last-Modified`·받은 시각·zip 검사 결과를 적는다. 실행 ID·커밋·시도 번호, 실패 목록, 되받아 검사 결과, 권리·재사용 문구도 적는다.
- 순서: 자료 자산 올리기 → 모두 되받아 sha256 확인 → manifest를 **맨 마지막에** 올리고 다시 되받아 확인.
- manifest의 `complete: true`는 수집 완료 + 분류 완료 + 업로드 실패 0 + 되받아 검사 불일치 0일 때만이다.
- **완성본의 정의:** 가장 높은 시도 번호의 manifest가 `complete: true`이고, 그 실행 로그 끝이 `SECONCE_DONE complete=yes`다. 앞 시도의 manifest는 기록으로만 남는다.
- **2 GiB 한도:** GitHub release 자산은 개당 2 GiB 미만이어야 한다.
  - 지금 가장 큰 것은 `submissions.zip` 1.57 GB(10/30 측정)다. 나누지 않을 것으로 본다.
  - 2,000,000,000 바이트를 넘으면 1,900,000,000 바이트 조각(`.part01`, `.part02` …)과 `.parts.json`(전체 sha256·조각 목록)으로 올린다.
  - 복원: 조각을 순서대로 이어 붙이고 전체 sha256을 확인한다(Q4).
- 크기(추정): 약 8.1 GB. release 전체 크기 한도는 없고 release당 자산 1,000개라는 GitHub 문서 내용은 이 세션에서 다시 확인하지 못했다(14절).

## 6. 재사용 범위

- 읽는 사람: 오너, Main, Codex. 저장소 접근 권한이 있는 사람, 또는 기존 읽기 토큰 `RAW_REPO_READ_TOKEN`을 쓰는 **따로 승인된** Actions 단계.
  - Main 세션은 raw 저장소를 붙일 수 없다(EXP 6.3절: 세션 자동 권한 검사가 거절, 우회 금지). 그래서 엔진이 이 release를 읽으려면 읽기 단계를 넣은 후속 PR과 승인이 필요하다(Q6).
- 쓰는 연구:
  - EXP-STOCK-INDICATOR-DECILES-v1: 발행사 목록, PIT 재무, 공시 당시 SIC, 상장폐지·등록 말소 사건(3.1절의 한계 그대로).
  - 전진검증 v3의 시점별 티커 ↔ CIK 구간(`FV3-PIT-TICKER`): **보조만.** 일괄 파일에는 공시별 `dei:TradingSymbol`이 없다. 쓸 수 있는 것은 공시 목록·오늘 티커·8% 분류 행이다.
  - 8% 불일치 분류.
  - 다른 연구에 쓰려면 새 오너 결정이 필요하다.
- 성격: SEC 공개 자료다(재배포 허용, SEC "Privacy and dissemination"). 그래도 **비공개로 둔다.** 파생 연구 결과와 한곳에 두기 위해서다. 공개 저장소·Pages에는 원본도 건별 파생 행도 넣지 않는다.
- 들어가지 않는 것: 가격, 가격에서 나온 값, KIS 자료, 개인 자료.
- 보존: 오너가 지울 때까지(release 자산은 만료되지 않는다).

## 7. 실패와 재개

요청 전 멈춤(SEC 요청 0건):

| 로그 | 뜻 | 할 일 |
| --- | --- | --- |
| `SECONCE_DISK … ok=no` | 빈 공간 11 GiB 미만 | 같은 실행기 이미지라 다시 실행해도 같을 수 있다. 한 번 다시 실행해 보고, 또 멈추면 후속 PR(공간 확보 단계) |
| `SECONCE_STOP reason=RAW_REPO_TOKEN_MISSING` · `RAW_REPO_HTTP401` | 토큰 없음·만료 | 오너가 Secret을 고친 뒤 다시 실행 |
| `RAW_REPO_NOT_PRIVATE` · `RAW_REPO_MISMATCH` | raw 저장소가 비공개가 아님·다른 저장소 | **실행하지 않는다.** 오너가 저장소를 확인한다 |
| `SEC_USER_AGENT_MISSING` · `SEC_USER_AGENT_INVALID` | SEC Secret 없음·형식 틀림 | 오너가 Secret을 고친 뒤 다시 실행 |
| `RAW_PREFLIGHT_MISSING` | 이번 시도의 비공개 확인이 없음 | 앞 단계 실패. 그 원인을 고친 뒤 다시 실행 |
| `NOT_THE_RUN_BRANCH` | 다른 가지·저장소 | 정상 거부. 할 일 없음 |
| `RELEASE_EXISTS` | 같은 이름 release가 이미 있음(첫 시도) | 멈춘다. 오너가 확인한다 |
| 오프라인 시험 실패 | 코드 문제 | 수집 작업이 시작되지 않는다. 후속 PR |

요청 중:

| 상황 | 동작 |
| --- | --- |
| 429 · 5xx · 네트워크 오류 · 잘린 본문 | 같은 요청을 최대 2번 다시 한다. 수집: 5초·20초 대기, 429는 `Retry-After` 최대 60초. 분류(옮긴 측정 코드): 2초·6초, `Retry-After` 최대 30초, 응답 대기 20초 |
| 404 · 그 밖의 4xx | 다시 하지 않는다. 실패 목록에 적고 다음으로 간다(FSDS 2026q3의 404만 실패 아님) |
| 403 연속 5번 · 429 누적 10번 · 요청 상한 · 시간 상한 | 수집이 그 자리에서 멈춘다. 받은 것은 저장한다. **분류는 SEC 요청을 하나도 보내지 않는다**(`TICKERMIX_SKIP reason=COLLECT_STOPPED`) |
| 실행기 디스크 오류(공간 부족·입출력 오류) | 네트워크 오류로 보지 않는다. 다시 요청하지 않고 바로 멈춘다(`stopped=LOCAL_DISK_FULL` / `LOCAL_IO`). 받은 것은 저장한다 |
| 크기·sha256 확인 | 파일마다 받으면서 sha256과 바이트를 센다. `Content-Length`와 다르거나 gzip 끝이 없으면 "잘림"으로 다시 받는다 |
| zip CRC 실패 | 그 zip을 한 번 새로 받는다(밤사이 다시 만들어지는 중일 수 있음). 또 실패하면 실패 목록 |
| 분류 단계 실패 | 따로 된 단계라 **수집한 파일은 그대로 업로드된다.** 마지막 단계가 작업을 실패로 끝낸다 |
| 분류 중 일시 오류(5xx·429·403·네트워크) | 그 공시는 빠지고 분류 결과는 `complete: false`. 다시 실행하면 분류를 다시 한다. 크기 상한·404·해석 오류처럼 다시 해도 같은 것은 세기만 하고 완료로 본다 |
| 업로드 실패 | 그 자산만 실패로 적고 다음 자산을 올린다. manifest는 `complete: false` |
| 업로드 뒤 검사 | 이번 시도에 올린 자산을 모두 내려받아 sha256을 다시 맞춘다 |
| 부분 실패 | 받은 것과 manifest를 올린다. 마지막 단계가 작업을 실패로 끝낸다 |

재개:

| 상황 | 동작 |
| --- | --- |
| **누가·언제** | **오너가** 같은 실행 화면에서 "Re-run failed jobs"를 누른다(휴대폰 GitHub 앱·웹). Main 세션에 Actions 쓰기 권한이 있는지는 확인하지 않았다. GitHub는 첫 실행 뒤 **30일 안에만** 다시 실행을 허용한다 |
| 다시 실행 | run id가 같아 release도 같다. 비공개 확인을 다시 한다. sidecar sha256이 맞는 자산은 내려받아 쓰고, SEC에 다시 요청하지도 다시 올리지도 않는다 |
| 같은 파일이 여러 시도에 있음 | 가장 최근 시도의 자산부터 확인한다(`a10-`은 `a2-`보다 최근). 맞는 것이 나오면 더 오래된 것은 읽지 않는다 |
| 이전 시도의 깨진 자산 | 지우지 않는다(만들기만 허용). 새 파일을 `a<시도>-<이름>`으로 올린다. 이름이 겹치는지는 그 업로드가 만들 **모든 이름**(sidecar, `.partNN`, `.parts.json`)으로 확인한다. 나눠 올리다 끊긴 파일도 다음 시도에 새 이름으로 다시 올라간다 |
| 분류 결과 | 완성본이 이미 저장돼 있으면 다시 하지 않는다. 미완성이면 다시 한다 |
| 새 push | 새 run id → 새 release가 된다(재개가 아님). 하지 않는다 |

## 8. 로그에 남는 것

고정 형식 줄만 남는다. 숫자·코드·MB·초뿐이다.
- `SECONCE_PLAN`, `SECONCE_DISK`: 고정 목록과 빈 디스크(GiB).
- `SECONCE_PREFLIGHT raw_repo=private`: 이번 시도의 비공개 확인 통과.
- `SECONCE_RESUME`: 재시도 때 이미 있는 자산 수.
- `SECONCE_FILES kind=bulk|index|fsds`: 계획·성공·재사용·실패·선택 누락 수, MB.
- `SECONCE_ZIP`: zip 항목 수, `-submissions-NNN.json` 추가 파일 수, CRC 결과.
- `SECONCE_INDEX year=…`: 연도별 색인 행 수와 서식별 수(10-K, 10-Q, 8-K, 25, 25-NSE, 8-A12B, 15-12B, 15-12G, 15-15D).
- `SECONCE_REQUESTS`: 요청·재시도·403/429/5xx 수, MB, 초, 멈춘 이유, 완료 여부.
- `TICKERMIX_*`, `PITTICKER*`: 8% 분류(9절).
- `SECONCE_RELEASE`, `SECONCE_VERIFY`, `SECONCE_DONE`: 업로드·되받기 검사·완료.
- 오프라인 시험: 시험 이름과 통과·실패만(`pytest -v --tb=no -rN -p no:warnings`). 실패해도 비교 값·예외 메시지·경고 문구는 나오지 않는다.
- 남지 않는 것: 티커, CIK, 회사 이름, URL, User-Agent, 토큰, 예외 메시지(클래스 이름과 고정 코드만).

## 9. 8% 불일치 원인 분류

- 대상: 10/31 측정(run 41255597310)에서 `dei:TradingSymbol`이 있는 209건 중 16건. 인스턴스 파일 이름 앞부분이 기호와 달랐다(대소문자 무시). 건별 자료는 남아 있지 않다.
- 방법:
  - 옮긴 측정 코드(`fv3_pit_ticker_measure.py`)로 같은 표본을 다시 만든다. 같은 120개 패널, 같은 2016~2019 공시 선택, 같은 인스턴스 선택, 같은 `dei` 읽기다.
  - form.idx는 이번에 저장한 사본을 읽는다(SEC 재요청 없음). 공시 목록과 인스턴스는 다시 받는다(약 880건).
  - 회사 이름은 form.idx, 지금 티커와 이전 이름은 저장한 `submissions.zip`에서 읽는다.
  - 시작 조건: 이번 시도의 비공개 확인 표시가 있고, 수집이 멈추지 않았을 것(`stopped=NONE`). 아니면 요청 0건.
- 용어: "지금 티커" = 등록부·`submissions.zip`의 오늘 티커. "앞선 공시 기호" = 같은 발행사의 **더 이른 해** 표본 공시의 기호(또는 기호와 같다고 확인된 앞부분). "뒤 공시 기호" = 더 늦은 해.
- 분류(규칙 순서대로, 처음 맞는 것). 기호 값 하나에 여러 기호가 있으면("GOOGL, GOOG") 먼저 나눈다.

| 분류 | 규칙 |
| --- | --- |
| 표기 차이 | 점·하이픈·공백·거래소 표기("NYSE:")를 빼거나 여러 기호를 나누면 같다 |
| 종류주 기호 | 끝 글자 하나만 다르고 **종류주 근거가 있다**: 구분 기호가 적혀 있다(BRK / BRK.B), 또는 끝 글자가 A·B·C·K·L이면서 그 발행사가 지금 티커 2개 이상이거나 두 문자열이 모두 그 발행사의 티커다. 또는 둘 다 지금 티커다(티커 2개 이상) |
| 옛 기호 | 앞부분이 **공시 전에** 그 발행사가 쓰던 기호다(앞선 공시 기호). 지금 티커가 아니고, 공시 기호와 다르다 |
| 기호 값 이상 | 앞부분이 그 발행사의 **지금 티커**(또는 뒤 공시 기호)다. 앞부분은 정상이고 다른 것은 표지 기호 값 쪽이다(다른 종류, 오타, 낡은 값). "옛 기호"로 세지 않는다 |
| inline XBRL 문서 이름 | inline 공시다(인스턴스 이름이 회사가 정한 문서 이름을 따른다) |
| 회사 약칭·문서 이름 | 티커 모양이 아니다(6자 이상이거나 숫자 포함), 문서 단어(form, annual, report …), 또는 회사 이름의 단어·머리글자 |
| 기타 | 나머지. 값이 빈 기호(`xsi:nil`)는 따로 센다 |

- 출력: 분류별 개수와 10/31과 같은지(`same=yes|no`)만 로그에 남긴다. 원래 형식의 `PITTICKER` 줄도 같이 남겨 10/31과 비교한다.
- 건별 행(CIK, accession, 기호, 앞부분, 인스턴스 이름, 분류, 근거)은 비공개 release의 `ticker-mismatch-rows.json`에만 둔다.
- 완료 조건: 멈춤 없음, form.idx 16개 모두 읽음, 일시 오류 0건.
- **신원 규칙(조건 없음):** 오너 결정 9 「미확인 매핑을 확정 신원으로 쓰지 마라.」
  - 규칙 기반 분류는 **어떤 경우에도** 신원을 확정하지 않는다. 분류 결과가 나온 뒤에도 같다.
  - 파일과 모든 행에 `identity_confirmed: false`와 "원인 개수용, 신원 원천 아님" 문구를 적는다.
  - 신원으로 쓰려면 따로 근거(S일 거래소 확인 등)나 오너 결정이 필요하다.
- 한계:
  - 규칙 기반이다. 사람이 검토한 분류가 아니다.
  - 표본은 지금 살아 있는 발행사다(10/31과 같은 한계).
  - 앞선·뒤 공시 기호는 2016~2019 표본 안에서만 안다. 2016년 공시는 앞선 기호가 없어 "옛 기호"가 될 수 없다. 옛 기호 이력 전체는 없다.

## 10. 하지 않는 것

- 승인 전에 병합하거나 실행하지 않는다. 이 PR은 계획과 코드뿐이다.
- 가격·가격 파생 값·KIS 자료를 받지도 저장하지도 않는다.
- 공개 파일을 만들지 않는다. Pages·Actions artifact·캐시·step summary가 없다.
- `data.sec.gov` API·EDGAR 전문 검색을 쓰지 않는다.
- 모집단 판정·점수 계산·장부 계산을 하지 않는다. 역사 모집단 확보를 선언하지 않는다.
- 엔진 인계 release(`exp-deciles-v1-*`)를 쓰지 않는다. 엔진·Main이 이 release를 읽는 단계도 넣지 않는다(Q6).
- 종류별 표지 주식 수용 공시별 XBRL은 받지 않는다(Q7).
- 기존 워크플로·가드·방법론·가중치를 바꾸지 않는다.
- 측정 가지의 push 워크플로(`fv3-pit-ticker-measure.yml`)는 옮기지 않는다. 이 PR의 워크플로가 대신한다.

## 11. 승인 뒤 실행 절차

1. 오너: 결정 PR(`claude/decisions-1101-second`)을 먼저 병합한다. 그다음 이 PR을 승인하고 병합한다.
2. Main: 병합 커밋에서 가지 `claude/sec-once-collect-run`을 만들어 **한 번** push한다. 워크플로가 한 번 돈다.
   - 다른 이벤트(PR, 일정, 수동 실행)로는 돌지 않는다. 작업 조건과 코드가 가지·저장소를 다시 확인한다.
   - 순서: 오프라인 시험 작업 → (통과하면) 수집 작업.
3. 확인: 로그 끝의 `SECONCE_DONE complete=yes`, `SECONCE_VERIFY … bad=0`, `TICKERMIX … same=yes`.
4. 실패하면: 7절 표대로 원인을 고친 뒤 **오너가** 같은 실행에서 "Re-run failed jobs"를 누른다(30일 안). 새 push는 하지 않는다.
5. 끝나면:
   - 오너가 실행 가지를 지운다(세션에는 가지 삭제 권한이 없다).
   - 측정 가지 `claude/fv3-pit-ticker-measure`도 지워도 된다(코드는 이 PR로 옮겼다).
   - Main이 후속 PR로 이 워크플로를 지운다(Q5).
6. 보고: 개수 줄과 release 이름을 [USER_DECISIONS_PENDING](../USER_DECISIONS_PENDING.md)과 인계 문서에 적는다.

## 12. 열린 질문 (오너 결정)

| # | 질문 | 기본안 |
| --- | --- | --- |
| Q1 | full-index·FSDS 시작 연도 | **2014.** 2009년부터 받으면 요청 +60건, 약 +1~3 GB(추정, gzip 여부에 따라). 이른 연도 XBRL 빈칸은 그래도 채워지지 않는다(2절) |
| Q2 | 승인 방식 | **병합 뒤 실행.** 검토한 코드와 실행하는 코드가 같다. PR 머리 커밋을 실행 가지로 push하는 방법도 있다 |
| Q3 | `company.idx` | **받는다**(지시대로). form.idx와 같은 행(정렬만 다름)이라 빼면 요청 52건, 내려받기 약 0.25 GB(gzip이 안 되면 약 2.5 GB), 저장 약 0.25 GB를 줄인다 |
| Q4 | 2 GiB 넘는 zip 나누기 | **허용 제안.** 조각 + `.parts.json` + 전체 sha256. 지금 크기로는 나눌 일이 없을 것으로 본다 |
| Q5 | 실행 뒤 워크플로 | **후속 PR로 지운다.** 남겨 두면 실행 가지에 push할 때만 돈다 |
| Q6 | 엔진 인계 release(`exp-deciles-v1-*`)와 읽기 단계 | **후속 PR로 나눈다.** EXP 6.3·7절은 이 PR에 넣기로 했지만, 인계할 엔진 출력이 아직 없다. 같은 방식(Actions + `RAW_REPO_TOKEN`, 코드로 이름 고정)으로 엔진 PR과 함께 올린다 |
| Q7 | 종류별 표지 주식 수(다중 종류 279·외국 145) | **따로 계획.** 공시별 표지 XBRL을 받아야 한다. 요청량을 따로 세어 별도 승인받는다 |

## 13. 이 PR의 파일

| 파일 | 내용 |
| --- | --- |
| `implementation/docs/lab/SEC_ONCE_COLLECTION_PLAN_20261101.md` | 이 계획 |
| `.github/workflows/sec-once-collect.yml` | 1회용 워크플로. 실행 가지 push로만, `contents: read`. 오프라인 시험 작업과 수집 작업(`needs:`)을 나눔. 수집 작업은 `python -I -S`, 단계마다 Secret 하나 |
| `implementation/tools/measure_once/sec_once_collect.py` | 비공개 확인·수집·재개·비공개 release 업로드·완료 확인 |
| `implementation/tools/measure_once/sec_once_ticker_mismatch.py` | 8% 분류 |
| `implementation/tools/measure_once/fv3_pit_ticker_measure.py` | 10/31 측정 코드. `claude/fv3-pit-ticker-measure`(`ead5ffdd`)에서 옮김, 동작 그대로 |
| `implementation/tests/test_sec_once_collect.py`, `test_sec_once_ticker_mismatch.py`, `test_fv3_pit_ticker_measure.py` | 가짜 입력만 쓰는 시험(네트워크·Secret 없음). 워크플로 모양 시험 포함 |

- 재사용한 것: 측정 코드의 User-Agent 규칙·form.idx 읽기·인스턴스 선택, `tools/raw_store_release.py`의 GitHub 전송(리다이렉트 거부, 토큰은 `RAW_REPO_TOKEN`에서만).
- 저장소의 SEC 클라이언트(`providers/sec_collection.py`)는 응답 상한이 32 MiB라 1.5 GB zip을 받을 수 없다. 그래서 스트리밍 다운로더를 새로 두었다.

## 14. 확인한 것과 미확인

검토자가 SEC·GitHub 공식 페이지로 확인한 것(캐시·웹 검색. 이 세션은 SEC에 직접 요청하지 않음):
- 일괄 zip 두 경로(SEC "EDGAR Application Programming Interfaces"), 매일 밤 다시 만들어짐.
- full-index 분기 폴더와 `form.idx`·`company.idx`, 2026 폴더·현재 분기 폴더.
- FSDS 2009q1~2026q3 경로와 크기(51개 합계 4,548.5 MB). `sub.sic`는 공시일 기준 배정.
- SEC 공정 접근: 초당 10건, User-Agent에 회사 이름과 연락처.
- GitHub: release 자산 개당 2 GiB 미만, 다시 실행은 30일 안, 표준 Linux 실행기 SSD 14 GB.

미확인(코드는 추측하지 않고 고정 코드로 멈추거나 양쪽을 다 처리한다):

| 사실 | 코드의 처리 |
| --- | --- |
| www.sec.gov가 `.idx`를 gzip으로 보내는지 | 둘 다 받는다(어느 쪽이든 같은 gzip으로 저장). 바이트 추정만 8~9 GB / 최대 14 GB로 달라진다 |
| 2014~2022 분기 색인 크기 | 추정만. 파일당 512 MiB 상한을 넘으면 `SIZE_CAP` |
| 분류 요청의 바이트 | 추정만. 인스턴스당 96 MiB 상한 |
| ubuntu-24.04의 빈 공간 | 11 GiB 미만이면 `SECONCE_DISK ok=no`로 요청 전에 멈춘다 |
| release당 자산 1,000개, 전체 크기 한도 없음 | 업로드 실패는 그 자산의 고정 코드로 남고 완료가 되지 않는다 |
| raw 저장소 응답에 `visibility`가 오는지 | 없으면 `RAW_REPO_NOT_PRIVATE`로 멈춘다 |
| Main 세션이 "Re-run failed jobs"를 누를 수 있는지 | 기본은 오너가 누른다 |
