# SEC FSDS 표본 확인 — 2015q4·2016q1

작성일: 2026-10-17 UTC. 상태: **표본 확인만**. 기준 커밋: `7b7d5a02`(#287 병합).
관련 문서: [BACKTEST_DATA_AUDIT.md](BACKTEST_DATA_AUDIT.md)(과거 SIC 경로 D10).

> **두 분기 표본이 통과해도 연구 구간 전체(2009~)가 검증된 것은 아니다.** 아래 결과는 2015q4·2016q1 두 파일과 그 표본에만 해당한다.

## 1. 목적

- FSDS(Financial Statement Data Sets) `sub.txt`의 구조와 채움 비율을 확인한다.
- `adsh`가 EDGAR 원 접수 건과 연결되는지 확인한다.
- `accepted` 시각의 시간대를 확인한다. PIT(당시 시점) 판정에 쓰기 위해서다.
- FSDS `sic`(제출 당시)와 현재 submissions `sic`가 다른 사례를 찾는다.

## 2. 확인 시각과 방법

- 확인 시각: 2026-10-17 07:15~08:14 UTC (같은 날 16:15~17:14 KST).
- 선언된 User-Agent 사용. 요청 간격 0.3초 이상. 총 요청 **123건**. 403·429 응답은 없었다.
  - 분기 zip 2건, 접수 색인 페이지(`-index.htm`) 20건, 헤더(`.hdr.sgml`) 20건.
  - submissions 본 JSON 20건, 과거 페이지(`-submissions-001.json`) 1건, SIC 추가 비교 60건.
- 원자료: `https://www.sec.gov/files/dera/data/financial-statement-data-sets/2015q4.zip`, `2016q1.zip`.
- 원자료는 작업 폴더에만 두었다. 레포에 넣지 않았다.
- 표본 추출: `sub.txt` 행을 `adsh` 순으로 정렬한다. Python `random.Random(seed).sample(rows, 10)`로 10건을 뽑는다.
  - 시드: 2015q4 = `20151231`, 2016q1 = `20160331`.
- 동봉 `readme.htm`의 정의:
  - `sic`: "as of the filing date"(제출일 기준) SEC 부여 코드.
  - `accepted`: 접수 일시(`yyyy-mm-dd hh:mm:ss`). **시간대는 적혀 있지 않다.**
  - `prevrpt`: 1이면 이후 정정 제출이 있었다는 뜻.

## 3. `sub.txt` 구조

헤더(두 분기 동일, 36열):

```
adsh	cik	name	sic	countryba	stprba	cityba	zipba	bas1	bas2	baph	countryma	stprma	cityma	zipma	mas1	mas2	countryinc	stprinc	ein	former	changed	afs	wksi	fye	form	period	fy	fp	filed	accepted	prevrpt	detail	instance	nciks	aciks
```

| 항목 | 2015q4 | 2016q1 |
|---|---:|---:|
| 행 수 | 7,234 | 6,532 |
| `sic` 채움 | 7,232 (99.97%) | 6,527 (99.92%) |
| 서로 다른 `sic` | 416 | 411 |
| `prevrpt`=0 | 7,047 | 6,331 |
| `prevrpt`=1 | 187 | 201 |
| 10-K | 532 | 4,498 |
| 10-Q | 6,239 | 1,540 |
| 기타 양식 | 463 | 494 |
| `accepted` 범위 | 2015-09-30 18:14 ~ 2015-12-31 17:24 | 2016-01-04 06:48 ~ 2016-03-31 17:30 |

- 기타 양식은 10-Q/A, 10-K/A, S-1, 20-F 등이다.
- `accepted`는 분 단위다. 초 자리는 늘 `00.0`이다.

## 4. `adsh` 연결

| 항목 | 2015q4 | 2016q1 |
|---|---:|---:|
| 표본 | 10 | 10 |
| EDGAR 색인 페이지 있음 | 10 | 10 |
| 색인 페이지 없음(404) | 0 | 0 |
| 기타 응답 | 0 | 0 |
| submissions `recent`에 있음 | 10 | 9 |
| submissions 과거 페이지에 있음 | 0 | 1 |
| submissions에서 못 찾음 | 0 | 0 |
| FSDS `filed` = submissions `filingDate` | 10 | 10 |

- 과거 페이지 1건은 `filings.files`에 나온 `CIK##########-submissions-001.json`에서 찾았다.

## 5. `accepted` 시간대

### 확인 방법

같은 표본 20건에 대해 네 값을 비교했다.
1. FSDS `accepted`.
2. EDGAR 색인 페이지의 "Accepted" 값.
3. `.hdr.sgml`의 `ACCEPTANCE-DATETIME`.
4. submissions `acceptanceDateTime`(끝에 `Z` 표시).

`Z` 표시만 보고 결론 내리지 않았다. 실제 시차를 계산했다. 2015q4는 2015-11-01 서머타임 종료를 걸친다. 2016q1은 2016-03-13 서머타임 시작을 걸친다.

### 결과

| 비교 | 2015q4 | 2016q1 |
|---|---:|---:|
| 색인 "Accepted" = 헤더 `ACCEPTANCE-DATETIME`(초 단위) | 10/10 | 10/10 |
| FSDS = 헤더를 **가장 가까운 분으로 반올림** | 10/10 | 10/10 |
| FSDS = 헤더를 분 단위로 버림 | 7/10 | 5/10 |
| submissions Z = 헤더와 같은 벽시계 | 0/10 | 0/10 |
| submissions Z = 헤더(뉴욕 현지)의 실제 UTC | 8/10 (EDT 3, EST 5) | 7/10 (EST 7) |
| submissions Z = 헤더 + 시차 2배 | 2/10 (EDT 1, EST 1) | 3/10 (EDT 1, EST 2) |

- 실제 UTC로 맞은 건은 시차가 날짜에 따라 바뀐다. 11-01 이전은 +4시간(EDT), 이후는 +5시간(EST)이다. 고정 시차가 아니라 뉴욕 현지 시각이라는 근거다.
- 5건은 +8시간(EDT) 또는 +10시간(EST)이었다. 시차가 두 번 적용된 모양이다. 원인은 확인하지 못했다.

### 전체 행 보조 확인(추가 요청 없음)

EDGAR는 동부 시각 17:30 이후 접수를 다음 영업일 제출로 처리한다. `accepted` 시각과 `filed` 날짜로 이를 확인했다.

| 구분 | 2015q4 | 2016q1 |
|---|---:|---:|
| 17:30 이하, 같은 날 `filed` | 6,634 | 5,692 |
| 17:30 초과, 다음 날 `filed` | 567 | 674 |
| 17:30 초과, 같은 날 `filed`(예외) | 30 | 162 |
| 17:30 이하, 다음 날 `filed`(예외) | 3 | 4 |
| 규칙 일치율 | 99.54% | 97.46% |

- 예외는 대부분 17시대 접수다. 2016q1 예외는 주로 10-K다. 원인은 확인하지 않았다.

### 결론

- **FSDS `accepted` = EDGAR 헤더 접수 시각 = 뉴욕 현지 시각(EDT/EST)이다.** 단, 분 단위로 반올림돼 있다(20/20).
- 반올림 때문에 실제 접수 시각과 최대 ±30초 차이가 난다. PIT 판정에는 여유 시간을 둔다.
- **submissions `acceptanceDateTime`은 `Z` 표시와 달리 일관된 UTC가 아니다.** 15/20은 실제 UTC였다. 5/20은 시차가 두 번 더해진 값이었다.
- 따라서 submissions 시각을 그대로 PIT 기준으로 쓰지 않는다. FSDS `accepted` 또는 헤더 값을 `America/New_York`로 해석한다.

## 6. 제출 당시 SIC와 현재 SIC

- 표본 20개 CIK: 차이 1건.
- 추가 비교: 분기별 30개 CIK(시드 `20261017`, 이미 받은 CIK 제외, `sic` 있는 행만). 차이 2건(분기별 1건).
- 합계: 80개 CIK 중 3건(3.75%)이 다르다.

| CIK | adsh | FSDS `sic`(제출 당시) | 현재 submissions `sic` |
|---|---|---|---|
| 882291 | 0001019687-16-005035 | 3826 | 3841 |
| 1113313 | 0001211524-15-000144 | 9995 | 6770 |
| 925741 | 0001136261-16-000427 | 3842 | 2836 |

- 현재 SIC로 과거 업종을 채우면 일부 종목이 다른 업종으로 분류된다. FSDS `sic`를 과거 업종 경로로 쓰는 근거가 된다(D10).

## 7. 한계와 미검증

- **두 분기만 봤다.** 2009~2015q3, 2016q2 이후는 확인하지 않았다. 헤더·`sic` 채움·시간대 규칙이 다른 분기에서 같다고 가정하지 않는다.
- `adsh`·시간대 확인은 분기당 10건 표본이다. 통계적 보증이 아니다.
- submissions 시차 2배 현상의 원인과 범위는 모른다. 다른 분기 비율도 모른다.
- 17:30 규칙 예외(30건·162건)의 원인을 조사하지 않았다.
- `num.txt`·`pre.txt`·`tag.txt`의 값은 보지 않았다. 재무 수치의 정확성은 이번 범위가 아니다.
- SIC 비교는 80개 CIK뿐이다. 전체 차이율은 추정하지 않았다. FSDS `sic`가 제출 시점 값이라는 근거는 readme 정의뿐이다. 다른 원천과 대조하지 않았다.
- `prevrpt`=1 행(정정 제출 존재)을 PIT에서 어떻게 다룰지는 정하지 않았다.
