# 잔고 캡처 변환 프롬프트 v1

- prompt_id: `holdings-capture-prompt/v1`
- 버전: v1 (2026-10-11)
- 앱 연결: `#actual`(내 실제 보유) 화면 → "내 증권사 연결 방법" → "캡처 + 개인 AI" → [프롬프트 복사]
- 앱 사본: `implementation/src/investment_system/product/web_assets/holdings-capture.js` `PROMPT_TEMPLATE`
  (아래 코드 블록과 글자 단위로 같아야 하며 `tools/holdings_capture_node_test.js`·`tests/test_holdings_capture.py`가 확인한다)
- `{{AS_OF}}`는 복사할 때 앱이 오늘 날짜(Asia/Seoul, `YYYY-MM-DD`)로 바꾼다.

## 프롬프트 (원문 그대로)

```text
[잔고 캡처 변환 프롬프트 v1]

첨부한 증권사 잔고 화면 캡처를 아래 형식의 표로 바꿔 주세요.

형식
- 첫 줄은 머리글이며 정확히 다음 7개 열입니다. 열 사이는 탭 문자로 구분합니다.
as_of	symbol	quantity	avg_cost	currency	cost_krw	name
- 그다음 줄부터 보유 종목 하나당 한 줄입니다. 위 7개 열만 쓰고 다른 열, 합계 줄, 빈 줄은 넣지 않습니다.

열 규칙
- as_of: 기준일입니다. 모든 줄에 {{AS_OF}} 값을 그대로 씁니다.
- symbol: 티커만 씁니다. 미국 주식은 미국 티커(예: NVDA), 한국 주식은 KRX 6자리 종목코드(예: 005930, 앞자리 0 유지), 일본 주식은 도쿄증권거래소 4자리 코드(예: 8035).
- quantity: 보유 수량입니다.
- avg_cost: 화면에 표시된 평균 매입단가(종목 통화 기준)입니다.
- currency: 종목 통화의 ISO 코드입니다(USD, KRW, JPY 등).
- cost_krw: 화면에 표시된 원화 매입금액 합계입니다.
- name: 화면에 보이는 종목명을 그대로 씁니다.
- 예수금·현금은 symbol을 CASH_통화코드(예: CASH_KRW, CASH_USD)로 쓰고, quantity에 그 통화의 금액, currency에 같은 통화 코드를 씁니다. avg_cost는 비워 둡니다. 원화 환산액이 화면에 있으면 cost_krw에 씁니다.

숫자 규칙
- 천 단위 쉼표, 통화 기호, 단위(주, 원, %), +와 - 기호를 넣지 않습니다. 소수점은 마침표(.)만 씁니다.

모르면 빈칸
- 화면에서 확실히 읽을 수 없는 값은 빈칸으로 둡니다. 추측하거나 계산해서 채우지 않고, 0으로 채우지 않습니다.

출력
- 머리글을 포함한 표만 출력합니다. 앞뒤 설명, 인사, 주석, 코드 블록 표시를 붙이지 않습니다.
```

## 사용 흐름

1. 증권사 앱에서 잔고 화면을 캡처한다(계좌번호·이름은 가려도 된다).
2. 앱에서 [프롬프트 복사]를 누른다. 기준일은 오늘(Asia/Seoul)로 자동 입력된다.
3. 본인이 쓰는 AI(ChatGPT·Claude·Gemini 등)의 새 대화에 프롬프트와 캡처를 함께 넣는다.
4. 앱에서 [시트 Holdings 탭 열기]를 누른다. 연결된 시트가 새 탭으로 열리고, `Holdings` 탭이 없으면 이때만
   정확한 머리글(`as_of, symbol, quantity, avg_cost, currency, cost_krw, name`)과 텍스트 서식으로 만든다.
   기존 탭은 수정하지 않는다.
5. AI 답(머리글 포함 표)을 `Holdings` 탭 A1에 붙여넣는다.
6. 앱으로 돌아오면 Holdings 탭을 읽어 미리보기를 보여 준다. 읽은 내용은 이 기기 RAM에만 있고 저장·전송하지 않는다.

## 읽기 규칙 (JS `HoldingsCapture.parse` = Python `investment_system.product.holdings_capture.parse`)

- 머리글이 정확히 7개 열이 아니면 아무것도 읽지 않는다: `HEADER_MISMATCH`.
- 문제가 있는 줄은 "확인 필요"로 시트 행 번호와 사유 코드를 보여 주고 읽지 않는다. 빈 숫자를 0으로 채우지 않는다.
- 평균단가: `cost_krw ÷ quantity`(정확한 십진 나눗셈, 소수 6자리 반올림, KRW)를 우선한다. 증권사 표시 단가는
  잘려 있기 때문이다. `cost_krw`가 비었을 때만 `avg_cost`(종목 통화)를 쓰고, 어느 쪽을 썼는지 표시한다.
  둘 다 비었으면 평균단가는 NOT_AVAILABLE이다.
- `CASH_<통화>` 줄은 현금이며 보유 종목이 아니다(`quantity` = 금액, 0 허용, `avg_cost`는 비어 있어야 한다).
- 한 탭은 한 시점이다: 가장 최근 `as_of`와 다른 날짜의 줄은 `AS_OF_MISMATCH`로 읽지 않는다.
  같은 `symbol`이 두 번 이상 나오면 모두 `DUPLICATE_SYMBOL`로 읽지 않는다.
- 시트가 숫자·날짜로 바꾼 값도 읽는다(날짜 일련번호, KRW 숫자 코드는 6자리로 0 채움, JPY는 4자리만).

| 사유 코드 | 뜻 |
|---|---|
| `COLUMN_COUNT` | 8번째 열 이후에 값이 있다 |
| `AS_OF_MISSING` / `AS_OF_FORMAT` / `AS_OF_MISMATCH` | 기준일 없음 / `YYYY-MM-DD` 아님 / 탭의 최신 기준일과 다름 |
| `SYMBOL_MISSING` / `SYMBOL_FORMAT` | 종목 없음 / 미국 티커·KRX 6자리·TSE 4자리·`CASH_<통화>` 아님 |
| `QUANTITY_MISSING` / `QUANTITY_FORMAT` / `QUANTITY_NOT_POSITIVE` | 수량 없음 / 숫자 형식 아님(쉼표·기호·지수 등) / 종목 수량이 0 |
| `AVG_COST_FORMAT` / `COST_KRW_FORMAT` | 평균단가 / 원화 매입금액 숫자 형식 아님 |
| `CURRENCY_MISSING` / `CURRENCY_FORMAT` / `CURRENCY_MISMATCH` | 통화 없음 / ISO 3자리 대문자 아님 / 시장과 통화 불일치(미국=USD, KRX=KRW, TSE=JPY, `CASH_X`=X) |
| `CASH_AVG_COST_PRESENT` | 현금 줄에 평균단가가 있다 |
| `NAME_FORMAT` | 종목명이 문자열이 아니거나 100자 초과·제어문자 |
| `COST_RANGE` | `cost_krw ÷ quantity` 결과가 허용 범위를 넘는다 |
| `DUPLICATE_SYMBOL` | 같은 종목이 여러 줄 |
| `COST_NOT_AVAILABLE` | (앱 반영 단계) 19개 분석 대상인데 평균단가 근거가 없어 ACTUAL에 넣지 않음 |

## 기존 보유 모델과의 연결과 우선순위

- Holdings 탭에서 읽은 19개 분석 대상 종목은 기존 ACTUAL 보유 모델(`device-actual-holdings/1`)과 같은 모양의
  RAM 스냅샷이 되어 내 실제 보유 화면, 포트폴리오·모델·보고서의 ACTUAL, 그림자 장부(shadow ledger) 입력
  (`DeviceActual.effectiveHoldings`)에 쓰인다. IndexedDB의 기기 ACTUAL과 JSON 백업은 바꾸지 않는다.
- 이 기기에 저장된 ACTUAL(직접 입력·JSON 가져오기)과 Holdings 탭이 모두 있으면 **기준일이 더 최근인 쪽**을 쓴다
  (Holdings `as_of` 대 기기 ACTUAL `effective_at`의 Asia/Seoul 날짜). 같은 날이면 더 나중에 만들어진 쪽
  (Holdings 읽은 시각 대 기기 ACTUAL 저장 시각)을 쓴다. 화면에는 어느 출처를 썼는지 항상 표시한다.
- Trades 탭은 지금 B/S 표시용으로만 읽으며 보유 수량을 만들지 않는다. Trades에서 보유를 만드는 기능이 생기면
  같은 규칙(기준일이 더 최근인 쪽, 출처 표시)을 따른다.
- 19개 밖 종목(예: KO)은 버리지 않고 "분석 범위 밖"으로 수량·평가액·손익만 보여 준다(QGV 점수 NOT_AVAILABLE).
  가격은 시트 Quotes 탭에 그 종목 코드 줄이 있거나 Worker 허용 목록에 있을 때만 쓰고, 아니면
  `QUOTE_NOT_AVAILABLE_OUT_OF_SCOPE`이다. Worker 허용 목록을 사용자 보유로 넓히려면 Worker PR과 사용자 승인이 필요하다.
