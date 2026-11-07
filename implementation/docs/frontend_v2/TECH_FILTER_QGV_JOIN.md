# 1.1.8 기술 조건 필터 — QGV 리더보드 결합 계약 제안

작성 2026-11-07 · Main. 근거는 오너 감사(11/07)다. "같은 평가일, 같은 증권으로 확인될 때만 결합한다."

이 문서는 Main이 Codex에 요청하는 필드 제안이다. Codex 계약 `technical-leaderboard/1`(#469)을 바꾸지 않는다.

## 1. 지금 결합하지 않는 이유

- 보드에는 `signal_day`와 `security_id`(고정 증권 ID, null 가능)가 있다. 문서상 QGV 결합 키는 `[signal_day, security_id]`다.
- 그런데 고정 증권 ID를 Universe504 상장 키(`NASDAQ:GOOGL` 같은 행 code)와 기업 ID(행 id)로 잇는 표가 계약에 없다. 유효기간도 없다.
- 그래서 Main은 결합을 추측하지 않는다. 지금은 모든 보드가 **증권 매핑 계약 없음**으로 거부된다.
- 이전 코드는 `security_id`가 행 id나 code와 글자가 같으면 결합했다. 이 방식은 없앴다.

## 2. Main이 Codex에 요청하는 필드

| 필드 | 뜻 |
|---|---|
| 보드 `signal_day` | 평가일(완결된 NYSE 거래일, YYYY-MM-DD). 지금도 있다. |
| 행 `security_id` | 고정 증권 ID. 티커나 CIK가 아니고, null이면 결합하지 않는다. |
| 매핑 `listing_key` | Universe504 상장 키(행 code, 거래소:티커). 클래스주마다 따로 둔다. |
| 매핑 `company_id` | Universe504 행 id. `listing_key`와 함께 맞아야 한다. |
| 매핑 `valid_from`, `valid_to` | 그 증권이 그 상장 키를 쓴 기간. `valid_to`가 null이면 지금까지다. |

매핑 표 모양(Main 제안 `tech-qgv-security-map/0`)은 다음과 같다.

```json
{"schema": "tech-qgv-security-map/0",
 "entries": [{"security_id": "…", "company_id": "…", "listing_key": "NASDAQ:GOOGL", "valid_from": "2020-01-01", "valid_to": null}]}
```

- 보드의 모든 증권이 평가일에 유효한 항목을 정확히 하나 가져야 한다.
- Universe504에 없는 증권은 `company_id`와 `listing_key`를 둘 다 null로 적는다. 이 증권은 결합하지 않는다.
- 평가일에 한 상장 키에는 증권 하나만 있어야 한다.

## 3. QGV 쪽 평가일

- QGV 목록의 평가일은 공식 게시본(`qgv-official.json`)의 `price_basis_date`로 본다.
- 게시본이 있고 입력이 맞을 때만 쓴다(`inputs_match = true`). 둘 중 하나라도 아니면 평가일이 없는 것으로 본다.
- 보드 `signal_day`와 글자 그대로 같아야 한다.

## 4. 결합 실패 때 Main이 하는 일

결합이 안 되면 리더보드 표에 기술 조건을 적용하지 않는다. 표는 그대로 두고, 블록에 사유를 적는다(`data-tf-join`, `data-na`에 코드).

| 코드 | 화면 문구 |
|---|---|
| `QGV_DATE_MISSING` | QGV 평가일 없음 · 공식 게시본의 가격 기준일이 없거나 입력이 다름 |
| `DATE_MISMATCH` | 평가일 불일치 · 보드 (날짜) · QGV (날짜) |
| `MAPPING_CONTRACT_MISSING` | 증권 매핑 계약 없음 · 고정 증권 ID ↔ 상장 키·유효기간 매핑이 오지 않음 |
| `MAPPING_INVALID` | 증권 매핑이 계약과 다름 |
| `MAPPING_MISSING` | 매핑 없음 · 증권 n개 (항목 없음, 유효기간 밖, 증권 ID null, 리더보드에 없는 상장 키, 맨 티커) |
| `MAPPING_AMBIGUOUS` | 매핑 중복 · 한 증권이 두 행에, 또는 두 증권이 한 행에 |
| `IDENTITY_MISMATCH` | 증권 신원 불일치 · 같은 상장 키, 다른 기업 ID (재사용된 티커, 클래스주 혼동) |
| `NO_JOINED_ROWS` | 매핑은 맞지만 리더보드 행과 결합된 증권 없음 |

문구 앞에는 "리더보드 표에 적용할 수 없음"이, 뒤에는 "리더보드는 기술 조건 없이 그대로"가 붙는다.

클래스주(GOOGL·GOOG, BRK.A·BRK.B)는 상장 키가 다르다. 그래서 매핑이 어느 클래스인지 정확히 적을 때만 결합한다.

## 5. 결론

- Codex가 매핑 표(2절)를 주기 전에는 아무것도 결합하지 않는다.
- 판독기는 `web_app/tech-screen.js`의 `joinRows`이고, 원천은 지금 `NONE`(`map: null`)이다.
- 시험은 `tools/web_app_tech_filter_node_test.js`와 `tools/web_app_tech_filter_browser_test.js`에 있다. 성공 사례는 시험 안에서 만든 합성 매핑으로만 확인한다.
