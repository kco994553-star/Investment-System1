# 가상매매 엔진 v1 (PROVISIONAL) — 구현 메모

상태: **PROVISIONAL_UNCALIBRATED · 시작일 2026-10-19(D-13 결정). 그 전에는 어떤 장부도 거래를 기록하지 않음.** 근거는 [가상매매 v1 제안](VIRTUAL_TRADING_V1_PROPOSAL.md), [보고서 템플릿 v1](REPORT_TEMPLATE_V1.md) §1·§7이다. 26E 기록(GSQ-018)은 별도 PR이며 사용자 승인 후 병합한다.

| 파일 | 역할 |
| --- | --- |
| `qgv/virtual_trading_v1_provisional.json` | 수치 설정. 값마다 결정 ID(D-n)와 상태를 `provenance`에 적는다 |
| `qgv/virtual_trading.py` | Python 참조 구현(순수 함수) |
| `web_assets/virtual-trading.js` | 기기 JS 이식, RAM 전용. 설정 사본을 내장하며 원본 JSON과 같은지 테스트로 확인한다 |
| `tools/virtual_trading_reference.py` → `tests/fixtures/virtual_trading_reference_v1.json` | 합성 입력 7개 시나리오와 기대 결과 |
| `tests/test_virtual_trading.py`, `tools/virtual_trading_node_test.js` | Python 동작 테스트, JS가 벡터와 완전히 같은지 확인하는 테스트 |

가격, 장부, 손익은 함수의 인자와 반환값으로만 존재한다. 모듈은 네트워크·저장소·전송을 하지 않으며, 테스트로 이를 확인한다. 실제 주문 기능은 없다.

## 설정값 (모두 나중에 수정 가능)

| 키 | 값 | 결정 |
| --- | --- | --- |
| `start_date` | 2026-10-19 | D-13 결정(2026-10-11). 그 전 날짜는 `NOT_STARTED`, 거래 기록 0건 |
| `daily_deposit` | 1,000,000 | D-1 |
| `buy_limit` / `sell_limit` | 각 1,000,000 | D-15 결정됨 |
| `execution` | 다음 세션 종가 | D-2 |
| `cost_bps` | 0 | D-3 |
| `fractional_quantity` | true | D-4 |
| `abnormal_drop` | 20세션 · 252세션 · k=2 | D-5 |
| `band_pp` | 1 | D-7 |
| `qg_decline_threshold` | 5 | D-8 |
| `min_trade` | 10,000 | D-9 |
| `benchmark` / `hit_windows` / `hit_min_samples` | S&P 500 · 5·20·63 · 30 | D-11·D-12 |
| `v_slope` | 20세션 · 10점 | D-21 |
| `sector_basis` | `SECTOR_ETF_CONFIRMED` | D-22 결정(2026-10-11): `qgv/sector_etf_map_v1.json`(대응표 1~14, 반도체 장비는 A안). 함수 `qgv/sector_basis.py` / `VirtualTrading.sectorBenchmark`. 업종 ETF 시세는 Worker 허용 목록 PR 승인·배포 전까지 받을 수 없어 기준 계산 불가로 동작 |
| `macro_gate` | 비활성 | D-6 (8축 매핑 채택 전) |

## 하루 처리 순서 (결정적 재생)

1. **체결:** 전날 결정한 주문을 오늘 종가로 체결한다.
   - 매도를 먼저 하고 매수를 나중에 한다. 같은 쪽 안에서는 회사 ID 순서다.
   - 오늘 종가나 환율이 없으면 그 주문은 취소된다(`EXEC_PRICE_MISSING`·`EXEC_FX_MISSING`).
2. **입금:** 가상 입금 100만원.
3. **평가:** 휴장 종목은 마지막 종가로 평가하고 `stale_valuation`에 표시한다.
4. **판단:** 오늘 종가와 오늘 Q·G 스냅샷으로만 판단한다. 미래 정보는 쓰지 않는다.
5. **배분:**
   - 매도는 매도 한도를, 매수는 min(매수 한도, 현금)을 원하는 금액 비율대로 나눈다.
   - 원 단위 미만은 버린다. 1만원 미만이면 거래하지 않는다.
   - 매도대금은 한도를 늘리지 않는다.

## 판단 규칙 (주 판단 1개 + 보조)

| 판단 | 조건 | 가상매매 |
| --- | --- | --- |
| ■ 차단 | 가격·환율·스냅샷 결측, Coverage BLOCKED, 사용자 '제외' | 없음 |
| ▼ 위험재검토 | Q·G 평균이 직전 스냅샷 대비 5점 이상 하락 | 보유분 매도 후보(한도 안) |
| ▼ 위험재검토 | Coverage READY→PARTIAL, 사용자 '보류', 개별 이상 하락 | 없음(Re-check) |
| ▼ 비중축소검토 | 실제 > 목표 + Band, 또는 Q·G 유지 중 V가 20세션 전보다 10점 이상 하락 | 목표(또는 목표 − Band)까지 매도 후보 |
| ▲ 비중확대검토 | 실제 < 목표 − Band, 또는 Q·G 유지 중 V가 10점 이상 상승 | 목표(또는 목표 + Band)까지 매수 후보 |
| ● 추가검토 | Coverage PARTIAL, 실적 예상 기간, 유형 변경 | 영향 없음 |
| ● 보유맥락 / ● 관찰 | 보유 중 신호 없음 / 미보유 | 없음 |

개별 이상 하락(D-5)은 다음과 같이 판정한다.

- 최근 20세션 업종 기준 대비 초과수익률이 그 종목 지난 252개 값의 평균 − 2σ보다 낮으면 이상 하락이다. σ는 표본표준편차다.
- 일봉이 273개 미만이거나 업종 기준 가격이 없으면 `RECHECK_BASIS_NOT_AVAILABLE`로 표시하고 V 기울기 신호도 쓰지 않는다.
- 평균단가는 판단에 쓰지 않는다. 평균단가만 바꿔도 판단과 주문이 같다는 것을 테스트로 확인한다.
- 사용자 '확인: 일시적' 플래그가 있으면 이상 하락 Re-check를 풀고, '확인: 구조적'이면 유지한다.

## 제안서에서 해석이 필요했던 점 (PROVISIONAL, 사용자 확인 시 수정)

1. **'제외' 플래그:** 제안서 §4.3은 '매도 후보'로, 템플릿 §7.1(D-19 개정안)은 '차단·거래 없음'으로 적었다. 더 보수적인 템플릿 쪽을 따랐다.
2. **Coverage가 BLOCKED로 바뀐 경우:** 데이터 관문에 걸려 ■차단(거래 없음)으로 처리했다. READY→PARTIAL 악화는 ▼위험재검토(거래 없음)로 처리했다.
3. **Q·G 하락 매도:** 보유 전량을 원하는 금액으로 잡고, 실제 매도는 하루 매도 한도 안에서 비례 배분한다. 하락 판정은 직전 스냅샷 대비라서 같은 하락이 다음 날 반복 판정되지 않는다.
4. **"Q·G 유지":** V 기울기를 비교하는 20세션 동안 Q·G 평균 하락폭이 D-8 임계(5점)보다 작은 경우로 정의했다.
5. **세트 A·사용자 세트의 출발:** 현금 0, 보유 없음에서 시작해 매일 입금으로 매수한다. 그림자 장부는 실제 보유 스냅샷(수량·원가)에서 시작하고, 목표 비중이 없으면 `TARGET_NOT_AVAILABLE`이다.
6. **기록된 상태에서 이어가기(사용자 결정 2026-10-11):** 엔진 입력의 `resume`(`after`, `cash`, `positions`{수량·원화 원가}, `pending`{그날 결정된 가상 주문}, `total_value`)이 있으면 `after` 다음 세션부터만 계산한다. 세션 목록은 장부 전체를 그대로 두므로 20세션 전 V 비교·직전 스냅샷 비교는 처음부터 다시 돌린 것과 같다. 대기 주문의 사용자 플래그는 결정일 기준으로 다시 찾는다. 이어서 계산한 요약(`summary`)은 이어간 구간만 다루며 `initial_value`는 마지막 기록 평가액이다. `after` 뒤 세션이 없으면 `NO_SESSION_AFTER_RECORDED`.
7. **V 요소 구성:** 입력 `v_composition`{날짜: {회사: 구성 키}}가 같은 두 날만 V 기울기를 비교한다. 두 날의 V가 있는데 구성이 다르거나 알 수 없으면 기울기를 쓰지 않고 보조 코드 `V_COMPOSITION_CHANGED`를 단다(V 기울기 NA).

## 기기 러너 (S17 연결)

`web_assets/virtual-trading-runner.js`(Python 참조 `qgv/virtual_trading_inputs.py`, 합성 벡터 `tests/fixtures/virtual_trading_inputs_v1.json`)가 엔진 입력을 기기 RAM에서 조립한다.

- 시작일 전에는 아무 요청도 하지 않고 `NOT_STARTED`. 그 뒤에는 구글 로그인 세션이 연결되어 있을 때만 기존 비공개 가격 Worker로 `2y` 일봉을 순서대로(5.2초 간격) 읽는다. SPY → 환율(`KRW=X`, `JPYKRW=X`) → 종목 → 업종 ETF → 보고서 ⑬ ETF(XLK·VUG·QUAL·XLY·XLP 중 아직 요청하지 않은 것) 순서. SPY·⑬ ETF·`KRW=X` 종가는 결과의 `indices`로 RAM에서만 보고서에 넘긴다.
- 세션 날짜는 SPY 완료 세션(시작일 이후). SPY가 없으면 장부를 만들지 않고 `SESSIONS_NOT_AVAILABLE`, 나머지 요청도 하지 않는다.
- 클라이언트 허용 목록이나 Worker가 거부한 기호는 오류 코드(예: `REQUEST_INVALID`)를 화면에 보이고 입력에서 빠진다. 없는 종가·환율은 채우지 않는다(`EXEC_PRICE_MISSING`·`EXEC_FX_MISSING`).
- Q·G는 공개 전진 검증 기록(RECORDED)에서만, V는 이 기기에 날짜별로 저장된 값(`investment.web.v1.virtual-trading-v-scores`, V와 요소 구성 키만)에서만 읽는다. V는 아래 'V 기록'이 쌓는다.
- 세트 B·C·D는 시트(VirtualMeta)에 저장한 사용자 정의 구성(`sets`)을 쓰고, 없으면 `SET_B_NOT_DEFINED`(B) · `SET_NOT_DEFINED`(C·D), 형식이 틀리면 `SET_B_INVALID`·`SET_INVALID`. 구성 종목은 TARGET 19종목과 클라이언트 가격 허용 목록(`GoogleSheetQuotes.HISTORY_SYMBOLS`)의 ETF 15종(SPY·SMH·XLK·XLV·XLE·XLB·XLP·XLY·XLC·XLU·XLRE·XLF·XLI·VUG·QUAL, 환율 기호 제외)이다. 이 밖의 종목은 Worker 허용 목록 변경이 먼저 필요하다(이번에는 바꾸지 않음). ETF는 USD로 평가하며 공개 Q·G가 없어 ■차단(`DATA_SNAPSHOT_MISSING`, 가상 거래 없음)이다. 모든 장부 입력은 요청한 구성 종목 전체의 종가를 함께 가진다(저장된 세트 정의를 어느 장부 입력에서든 만들 수 있게).
- 그림자 장부의 목표는 **사용자 본인의 목표(USER_TARGET)만** 쓴다(사용자 결정 2026-10-11). 없으면 `TARGET_NOT_AVAILABLE`이며 TARGET v0로 대신하지 않는다. 플래그는 VirtualFlags에서 읽는다(아래 장부 시트 저장). 그림자 장부는 ACTUAL 스냅샷(수량·평균단가)에서 출발하며, 그 스냅샷의 뉴욕 날짜 이후 세션만 쓴다. 원가는 첫 세션 이전 마지막 환율로 원화 환산한다.

## 장부 시트 저장 (D-10)

`web_assets/virtual-ledger-sheets.js`(Python 참조 `qgv/virtual_ledger_sheets.py`, 합성 벡터 `tests/fixtures/virtual_ledger_sheets_v1.json`)가 가상 장부를 사용자 본인의 구글 시트에 저장한다. 기존 drive.file 세션만 쓰며 새 권한은 없다. 쓰기는 아래 일곱 탭에만(`GoogleSheetQuotes`의 쓰기 허용 목록), 버튼을 눌렀을 때만, 덧붙이기로만 한다. 머리글이 다른 탭은 `SHEET_HEADER_MISMATCH`로 거부하고 쓰지 않는다.

| 탭 | 머리글(고정) |
| --- | --- |
| `VirtualA`·`VirtualB`·`VirtualC`·`VirtualD`·`VirtualMine` | `ledger_id, session_date, row_type, company, level, aux_levels, reason_codes, aux_codes, side, amount, quantity, price_used, fx_used, cash_after, total_value` |
| `VirtualMeta` | `recorded_at, ledger_id, kind, event, start_date, end_date, config_version, engine_version, last_recorded_session, inputs_sha256, payload` |
| `VirtualFlags` | `created_at, date, company, kind` (메모 없음. 사용자가 직접 입력할 수 있고, 형식이 맞지 않는 행은 세어서 무시) |

- **장부 행:** 거래일마다 `INITIAL`(그림자 장부 첫날의 출발 보유: 수량·원화 원가) → `EXECUTED`(가상 체결: 금액·수량·사용 종가·환율·사유) → `CANCELLED`(EXEC_*_MISSING 등) → `JUDGEMENT`(종목별 주 판단·보조 판단·사유 코드) → `ORDER`(다음 거래일 가상 주문) → `SUMMARY`(입금·가상 현금·평가액, 평가 불가면 `NOT_AVAILABLE`). 숫자는 ECMAScript 숫자 문자열 형식으로 쓰고 Python 참조도 같은 글자를 만든다. 없는 값은 0으로 쓰지 않는다.
- **VirtualMeta 사건:** `LEDGER_START`(장부 ID·출발일·설정/규칙 버전·payload: 목표 기준과 비중, 세트의 `purpose`(목적 한 줄), 그림자 장부는 출발 스냅샷), `LEDGER_CLOSE`(종료일, payload `reason`: 다음 장부로 바뀜(`SET_A_CHANGED`·`SET_B_REDEFINED`·`SET_REDEFINED`·`RESYNC`) 또는 삭제 `SET_DELETED`), `RECORD`(마지막 기록 거래일, 그때까지 입력의 SHA-256), `USER_TARGET`(내 목표). 세트 정의는 이 탭에만 저장한다(새 탭 없음). 행은 고치지 않고 마지막 값이 유효하다.
- **장부 ID:** `set_a`(세트 A v1.1 예시: TARGET v0, 첫 기록 때 정의), `set_a@v2`·`set_a@v3`…(세트 A 구성을 바꿀 때마다 새 버전·새 장부), `set_b-n`·`set_c-n`·`set_d-n`(사용자 세트 구성 저장마다 새 장부), `shadow-n`(출발 스냅샷·다시 맞추기마다 새 장부). 새 장부의 출발일은 저장 시각의 뉴욕 날짜(시작일 이후, 앞 장부의 마지막 기록 다음 날 이후)다. 앞 장부는 그날로 닫고(종료) 기록과 성과는 그대로 둔다. 닫힌 장부도 남은 거래일(종료일 전)은 계속 기록한다.
- **기록(사용자 결정 2026-10-11 · 기록된 행이 기준):** "장부 시트에 기록"을 누르면 시트를 다시 읽고, 장부마다 기록된 행에서 마지막 상태를 읽는다(`recordedState`: 마지막 `SUMMARY`의 가상 현금, `INITIAL`·`EXECUTED` 행을 엔진과 같은 계산 순서로 쌓은 보유 수량·원화 원가, 마지막 기록일의 `ORDER` 행 = 다음 거래일 가상 주문, 마지막 평가액). 엔진은 이 상태에서 이어서(`resume`) 마지막 기록 다음 거래일부터 공개 Q·G 기록이 있는 마지막 거래일까지 계산하고 그 행을 덧붙인다. 처음부터 다시 돌리지 않는다.
  - 같은 입력으로 처음부터 다시 계산한 값과 기록된 행도 칸 단위로 비교한다. 다르면(예: 과거 일봉 수정) **기록을 고치지 않고 쓰기도 멈추지 않으며** `PRICE_REVISED`(첫 차이 거래일)를 장부 줄과 배지로 보인다. 예전의 `LEDGER_REPLAY_MISMATCH` 정지는 없앴다. 아무것도 바뀌지 않았으면 이어서 계산한 행은 처음부터 다시 계산한 행과 글자까지 같다(테스트로 확인).
  - 구조 점검은 그대로 쓰기를 막는다: 형식이 틀린 행(숫자가 아닌 칸, 보유하지 않은 종목의 가상 매도, `SUMMARY` 없는 거래일, `SUMMARY` 뒤에 이어진 같은 날 행, 음수 현금, 잘못된 `side`)은 `SHEET_ROWS_INVALID`, 머리글이 다르면 `SHEET_HEADER_MISMATCH`, VirtualMeta 형식 오류는 `META_INVALID`.
  - 그날 값이 없으면 엔진 결과(NOT_AVAILABLE·EXEC_*_MISSING)대로 쓰고 채우지 않는다. 시세 요청이 일시 오류(예: RATE_LIMITED)면 `INPUTS_INCOMPLETE`로 기다린다.
- **기록하지 않는 경우:** 시작일(2026-10-19) 이전 거래일, 정식 설정이 아닌 실행, 리허설 결과(`mode:'REHEARSAL'`, `rehearsal` 블록, 또는 오늘 공개 Q·G로 채운 날 `qg_filled`가 하나라도 있는 결과).
- **세트 A(사용자 결정 2026-10-11):** 현재 공식 v1.1 비중은 '예시'다(화면 'v1.1 예시'). 세트 A 탭에서 구성을 바꾸면 예시 장부(`set_a`, 아직 정의 전이면 이때 먼저 저장)를 닫고 `set_a@v2`로 새 장부를 시작한다. 이전 장부와 성과는 종료 상태로 계속 볼 수 있다.
- **사용자 세트 B·C·D:** 최대 3개. 세트마다 구성 종목 1~30개(위 허용 목록), 목적 한 줄 필수(1~120자, 줄바꿈 없음 — 없으면 `PURPOSE_REQUIRED`, 형식이 틀리면 `PURPOSE_INVALID`), 목표 비중 합계 100 이하(나머지는 가상 현금), 31개 이상이면 `SET_MEMBERS_OVER_30`. 장부 탭은 `VirtualB`·`VirtualC`·`VirtualD`(머리글은 VirtualA와 같음). 가상 매수·가상 매도 하루 한도(D-15, 각 100만원)는 세트마다 따로 적용된다. 구성을 바꾸면 새 장부 ID, 삭제하면 '종료'(`LEDGER_CLOSE`, `SET_DELETED`)만 표시하고 정의와 기록은 남긴다. 화면은 허용 목록 밖 종목은 Worker 변경이 먼저 필요하다고 안내한다.
- **내 목표:** 투자 일일보고서의 '내 목표(TARGET)'는 비공개로 VirtualMeta에만 저장되며 그림자 장부의 목표로 쓴다. 없으면 그림자 장부는 NA이고 '내 목표 설정' 안내와 **[세트 A 목표를 내 목표로 복사]** 버튼을 보인다. 이 버튼은 세트 A의 현재 목표 비중(저장된 버전, 없으면 v1.1 예시)을 `USER_TARGET` 행으로 시트에 쓴다(누를 때만). 목표는 장부 출발 때 고정되며, 바꾼 목표는 '실제 보유로 다시 맞추기' 뒤 새 장부부터 적용된다.
- **Example_ 탭(사용자 결정 2026-10-11):** 이름이 `Example_`로 시작하는 탭(예: `Example_SetA_Trades`)은 앱이 무시한다. `GoogleSheetQuotes`가 탭 목록(`sheetTitles`·`sheetTabs`)에서 빼고, 그런 탭을 가리키는 값 범위 읽기는 요청 전에 `INVALID`로 거부하며, 쓰기 허용 목록에도 없다. 그래서 Trades·Holdings·Virtual*·Quotes·Universe로 착각하거나 검증·목록에 넣지 않는다. 새 Holdings 탭 ID는 숨긴 Example_ 탭 ID와도 겹치지 않게 고른다.
- **그림자 장부(D-17):** '출발 스냅샷 만들기'가 기기 ACTUAL 보유(수량·평균단가·통화)를 저장한다. 원화 원가는 러너와 같은 규칙(장부 첫 거래일 이전 마지막 환율)으로 재생 때 계산해 첫날 `INITIAL` 행에 남는다. '실제 보유로 다시 맞추기'는 현재 장부를 닫고 오늘 보유로 새 장부를 시작한다. 스냅샷이 없으면 화면은 기기 보유 기준 미리보기이며 기록하지 않는다.
- **화면:** 날짜·개수·사유 코드·비중만 보인다. 금액·수량은 시트(사용자 비공개 저장소)에만 있고 기기 저장소·콘솔·공개 파일에는 없다.

## D-5 기준 표시 · V 기록 · 리허설 (S17)

`web_assets/virtual-trading-signals.js`(Python 참조 `qgv/virtual_trading_signals.py`, 합성 벡터 `tests/fixtures/virtual_trading_signals_v1.json`, 생성 `tools/virtual_trading_signals_reference.py`)와 `web_assets/virtual-trading-v-history.js`가 담당한다. 규칙 값은 바꾸지 않는다.

**D-5 기준 표시.** 러너는 2년 일봉 종가 전체(시작일 이전 포함)와 D-22 업종 ETF 시세를 엔진에 넘긴다. 시작일 필터는 세션 목록에만 걸린다. 그래서 정렬된 종가가 273개 이상이면 개별 이상 하락(`RECHECK_ABNORMAL_DROP`, ▼위험재검토)이 실제로 판정된다.
- 보고서 ③의 '업종 기준 · D-5' 칸에 회사별로 다음을 보인다: 실제로 쓴 기준(ETF 기호 또는 S&P 500), 정상·이상 하락·기준 N/A와 사유, V 기울기 사용 여부.
  - 기준 N/A 사유: `HISTORY_INSUFFICIENT`(정렬 n/273 함께 표시), `PRICE_NOT_ALIGNED`, `SECTOR_BASIS_NOT_AVAILABLE`, `DISTRIBUTION_DEGENERATE`.
- 업종 ETF 시세가 없을 때(Worker 거부 등) 엔진 코드(`sectorSeries`)는 S&P 500(SPY)으로 대체해 판정한다. 위 '업종 기준 가격이 없으면 기준 계산 불가'는 S&P 500까지 없을 때에 해당한다. 보고서는 대체를 'S&P 500 (XLY 없음 → 대체)'처럼 표시한다(엔진 동작은 그대로, 표시만 추가).
- 실제 흐름의 전제: 환율 `KRW=X`·`JPYKRW=X`(PR #191)를 Worker에서 받을 수 있어야 한다. 환율이 없으면 미국·일본 종목은 판단 단계 1에서 ■차단(`DATA_FX_MISSING`)되어 D-5 단계까지 가지 않는다. 기준 칸은 판단과 별도로 계산하므로 그때도 기준 상태는 보인다.

**V 기록(생산자).** 러너가 결과를 낼 때마다(기록 모드·리허설 모두) 그 결과의 최신 완료 SPY 세션(러너의 날짜 규칙)을 날짜로 삼는다. 그 세션 종가(기기 RAM)와 공개 가격 없는 가치 입력(`sec-valuation-inputs.json`)으로 회사별 V를 계산해 저장한다.
- 대상: TARGET·세트 B·C·D·보유 회사.
- V 정의: 기기 V 요소(`DeviceValuation.view`)를 공식 v1 V 가중치 사본의 PREVIEW V 축(`EnginePreview.strategy`)으로 묶은 값이다. 소수 둘째 자리로 반올림한다.
- **핵심 요소(사용자 결정 2026-10-11):** 빠진 요소를 0으로 넣어 V를 낮추는 계산은 금지한다. 명세에 '핵심 요소' 정의가 없으므로 공식 v1 V 가중치에서 가중치가 0보다 큰 요소 7개 모두를 핵심으로 본다: `fundamental_value`(25)·`reverse_dcf`(20)·`peer_relative_value`(15)·`historical_valuation`(15)·`margin_of_safety`(10)·`sector_context`(10)·`theme_premium_discount`(5). 하나라도 없으면 그날 V는 NA이며 숫자로 저장하지 않는다(사유 `V_CORE_FACTOR_MISSING`, S17 'V 기록 없음' 줄). 현재 기기 입력에는 peer·과거 밸류에이션·업종·테마 요소가 없어 V는 계속 NA이고 V 기울기 신호도 쓰이지 않는다(미결 사항).
- **요소 구성 키:** 저장하는 V마다 그날 있던 요소 ID를 정렬해 `+`로 이은 키를 함께 둔다. V 기울기(20세션 비교)는 키가 같은 두 날만 비교한다. 다르거나 모르면 NA(`V_COMPOSITION_CHANGED`).
- 저장 형식 `virtual-trading-v-scores/2`: `{schema, scores:{날짜:{회사:V}}, composition:{날짜:{회사:키}}}`. 예전 `/1` 값은 그대로 읽되 구성은 '알 수 없음'이라 기울기를 만들지 않는다. 첫 `/2` 쓰기 때 형식만 올리고 예전 값은 그대로 둔다. 그래서 새 형식으로 20거래일이 쌓일 때까지 기울기는 NA이고, 'V 기록 N/20일'도 구성 키가 있는 날부터 센다.
- 저장 규칙: V 숫자와 구성 키만 저장한다(가격·환율·장부 없음). 구성 키 없는 V는 저장하지 않는다. 추가만 하며, 이미 있는 날짜·회사 값은 바꾸지 않는다. 가장 최근 기록일보다 이른 날짜는 받지 않는다(첫 기록 이전 소급 없음). 최대 400개 날짜를 남기고 오래된 날짜부터 지운다. 저장소를 읽을 수 없거나 형식이 깨졌으면 쓰지 않는다.
- V 기울기는 첫 기록 뒤 20거래일부터 쓸 수 있다. 그 전까지 S17은 'V 기록 N/20일'을 보인다. 엔진은 장부 세션 안에서 20세션 전 값을 비교하므로, 기록 모드에서는 2026-10-19부터 20세션이 지나야 실제로 쓰인다.
- 기기 백업(`device-backup.js`)에는 넣지 않는다. 백업은 명시적 설정과 보유만 담는 가격 없는 파일이다. V 기록은 가격에서 파생된 관찰 기록이라 AI 답변 보관함 같은 다른 기기 전용 키처럼 이 브라우저에만 둔다.

**리허설(리허설 · 기록 없음 / Rehearsal · not recorded).** 시작일 전 S17은 계속 `NOT_STARTED`이고 Worker 요청이 없다. '리허설 실행'을 누르면 같은 러너 경로로 2년 일봉을 받는다(시작일 관문만 건너뜀).
- 엔진 설정은 `start_date`만 최근 완료 SPY 세션 5개의 첫날로 옮긴다. 다른 규칙 값은 그대로다. 현금 0에서 매일 가상 입금으로 시작하며 RAM에서만 계산한다.
- 공개 전진 검증 기록(Q·G)이 없는 창 안 세션은 오늘 공개 화면 Q·G로 채우고 그 사실을 표시한다. 리허설 전용이며 다음 세션 Q·G를 앞당겨 쓰는 것을 알고 표시한다. 채우는 함수(`applyRehearsalSnapshots`)는 `mode`가 `REHEARSAL`이 아니면 `REHEARSAL_ONLY`로 거부하고(기록 모드는 빈 날을 채우지 않음), 장부 시트 기록은 채운 날이 있는 결과를 `REHEARSAL_NOT_RECORDED`로 거부한다(테스트로 확인).
- 화면과 내보내기에는 '리허설 · 기록 없음' 배지(보라색)를 단다. 기록 모드는 '기록 모드'로 표시한다. 결과 객체에는 `mode: 'REHEARSAL'`이 붙는다. 장부·시트 저장 훅은 이 값이면 아무것도 쓰지 않아야 한다.
- 리허설은 어떤 장부·시트 데이터도 쓰지 않는다. V 기록은 장부와 독립이므로 리허설에서도 추가된다.
- 시작일 이후에도 같은 버튼으로 리허설을 볼 수 있다. '기록 모드로 돌아가기'로 되돌린다.

## 보고서 ⑪ 누적 검증 · ⑫ 기간별 성과 · ⑬ 상대지수 (S17)

`web_assets/report-benchmarks.js`(Python 참조 `qgv/report_benchmarks.py`, 합성 벡터 `tests/fixtures/report_benchmarks_v1.json`, 생성 `tools/report_benchmarks_reference.py`)가 계산한다. 입력은 러너의 `indices`, 엔진 장부의 날짜별 평가액·입금, 엔진 `evaluateHits`이며 모두 RAM에만 있다. 저장·전송·콘솔 출력이 없다.

- **세션 달력:** SPY 완료 세션. 기준 거래일은 대상 장부의 마지막 날(없으면 마지막 SPY 세션).
- **기간:** 1D·5D·20D·60D·120D는 기준 거래일에서 N세션, '시작 이후'는 장부 첫날부터. **기간 시작 직전 세션 종가 = 100**.
- **결측:** 종가·환율·장부 평가가 없는 세션은 공백(선이 끊김)과 사유 코드(`CLOSE_MISSING`·`FX_MISSING`·`VALUE_MISSING`)로 둔다. 보간·이월하지 않는다. 기준일이나 마지막 세션 값이 없으면 그 시리즈 수익률은 NOT_AVAILABLE(`BASE_*`·`LAST_*`). 기간이 장부보다 길면 `PERIOD_BEFORE_LEDGER_START`.
- **통화 기준(결정, 화면에 표시):** 기본 **원화(KRW)** — 장부는 기록된 원화 그대로, 미국 지수는 같은 세션 `KRW=X` 종가를 곱해 원화로 환산(원화 투자자가 그 ETF를 들고 있었다면 본 값, 환율 효과 포함). 선택 **달러(USD)** — 지수는 현지 종가, 장부는 같은 세션 `KRW=X`로 나눠 달러 환산. 환율은 같은 날짜만 쓴다(전날 환율로 채우지 않음). 화면 선택(기간·통화)은 이 페이지 세션 동안만 RAM에 둔다. AI 답 보관 키(정본 템플릿)는 20D·원화로 고정한다.
- **장부 지수:** 엔진과 같은 시간가중 연결 — (평가액 − 직전 평가 이후 입금) ÷ 직전 평가액. 장부 첫날은 엔진처럼 연결 1. 공백이 없고 원화 기준이면 '시작 이후' 값이 엔진 `summary.twr`과 같다(테스트로 확인). 공백을 건너면 그 사이 입금을 모두 뺀다(엔진 twr은 하루치 입금만 뺀다: 결정 필요 항목).
- **⑫:** 기간마다 대상·S&P 500(SPY)·초과(%p)·판정(상회/하회/같음).
- **⑬:** 대상 장부 + 비교 장부(모의투자: 세트 A↔B, 투자 보고서: 그림자 장부 + 세트 A), S&P 500, XLK, VUG, QUAL, XLY, XLP. 기존 `TechnicalChart.paths`로 선을 그리고 공백에서 끊는다. 지수·수익률은 %라 금액 숨김 대상이 아니다. 위험지표(MDD 등)는 아직 N/A.
- **⑪:** 엔진 `evaluateHits`(D+5·D+20·D+63 세션, S&P 500 현지 통화, D-11). 창마다 표본 수, 30건 이상일 때만 적중률(적중/표본), 그 전에는 '표본 부족(n<30)'(D-12). 표본이 0이면 사유(`BEFORE_START_DATE`·`NO_TRADES`·`WINDOW_NOT_ELAPSED`·`PRICE_OR_BENCHMARK_MISSING`)와 첫 평가 예상일. 달력 밖 날짜는 주말·NYSE 휴장일(2026–2027 목록)만 뺀 추산이며 '≈'로 표시한다. 시작일(2026-10-19) 기준 첫 예상일: D+5 2026-10-27, D+20 2026-11-17, D+63 2027-01-21. 최근 D+5 판정 5건(수익률·S&P 500·적중)도 보인다.

## 세트 비교 (모의투자 일일보고서 '비교' 탭, 사용자 결정 2026-10-11)

`web_assets/virtual-trading-compare.js`(Python 참조 `qgv/virtual_trading_compare.py`, 합성 벡터 `tests/fixtures/virtual_trading_compare_v1.json`, 생성 `tools/virtual_trading_compare_reference.py`)가 세트별 지표를 RAM에서 계산한다.

- 세트가 2개 이상(세트 A + 사용자 세트 1개 이상)일 때만 탭이 보인다. 휴대폰(1024px 미만)은 2~3개를 골라 비교하고(2개 미만·3개 초과 선택은 받지 않음), PC(1024px 이상)는 모든 세트를 보인다.
- 규칙 기반 숫자 표만 둔다. '전략 장점·약점·관찰항목' 같은 서술 칸은 없다. AI 해석은 내보내기의 '한 줄 요약: 【AI】' 한 칸뿐이며, 없으면 규칙 문장(기간 수익률 최고·변동성 최저 세트)을 쓴다. 금액은 같은 금액 숨김 함수를 쓴다(기본 숨김).
- 수익률은 ⑫⑬과 같은 `ReportBenchmarks` 계산을 그대로 쓴다(SPY 세션 달력, ⑬ 통화 기준 — 기본 원화, 미국 지수 × 같은 날 KRW=X —, 입금 제외 시간가중 장부 지수, 결측은 공백이며 보간·이월 없음). 기간은 세트마다 그 장부의 첫날부터(`SINCE_START`).

| 지표 | 정의 | 최소 표본 |
| --- | --- | --- |
| 평가액 | 마지막 거래일 가상 평가액(금액 숨김 대상) | 그날 평가 가능 |
| 기간 수익률 | ⑫ `SINCE_START` 대상 수익률 | ⑫ 규칙(기준·마지막 값 있음) |
| S&P 대비 초과 | ⑫ `SINCE_START` 대상 − S&P 500(SPY) 수익률 | ⑫ 규칙 |
| 집중도 | 마지막 거래일 상위 3종목 비중(총평가액 대비 %). 보유 종목 중 그날 가격·환율 없는 종목이 있으면 NA | 그날 모든 보유 종목 평가 가능 |
| 유형 노출 | 유형(성장·품질·경기민감·방어)마다 Σ 비중 × 공개 유형 소속도(0~1, `company-types-pricefree.json`). 소속도가 없는 종목(ETF 포함)은 '미분류' | 집중도와 같음 + 공개 유형 파일 |
| 상승포착 | S&P 500 상승일(b>0)의 평균 일간 수익률 ÷ 같은 날 S&P 500 평균 × 100 | 상승일 10일 |
| 하락포착(낮을수록 방어) | S&P 500 하락일(b<0)에 같은 계산 | 하락일 10일 |
| 최대낙폭 | ⑬ 장부 지수(시간가중)의 최고점 대비 최저 하락률(≤ 0) | 일간 수익률 20개 |
| 변동성 | 일간 수익률의 표본표준편차 × √252 | 일간 수익률 20개 |
| 가상매매 성과 | 가상 매수·매도 건수, 엔진 D+20 적중률 | 적중률 30건(D-12) |

- 일간 수익률은 ⑬ 지수 값이 있는 연속 세션 쌍에서만 계산한다(장부 첫날의 기준점→첫날 연결은 빼며, 공백 세션은 건너뛰고 채우지 않는다). 최소 표본 미만은 NA(`INSUFFICIENT_SAMPLE`)이며 0을 쓰지 않는다. 최소 표본 값은 이 구현의 설정이며 사용자 확인 대상이다.

## 아직 연결하지 않은 것

- **가격 경로:** 개인 가격 Worker가 TARGET 19종목만 허용한다. 그래서 S&P 500, 업종 ETF, 세트 B 종목의 일봉을 기기에서 받을 수 없다([D-22 초안](D22_SECTOR_ETF_MAPPING_DRAFT.md)의 선택지 참고).
  - 그 전까지 엔진은 업종 기준 계산 불가로 동작한다.
  - 적중 판정(D+N)은 ⑪에 연결됐다(위 절). 표본은 2026-10-19 이후 가상 거래가 쌓여야 생긴다.
