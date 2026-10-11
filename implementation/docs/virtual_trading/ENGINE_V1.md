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
5. **세트 A·B의 출발:** 현금 0, 보유 없음에서 시작해 매일 입금으로 매수한다. 그림자 장부는 실제 보유 스냅샷(수량·원가)에서 시작하고, 목표 비중이 없으면 `TARGET_NOT_AVAILABLE`이다.

## 기기 러너 (S17 연결)

`web_assets/virtual-trading-runner.js`(Python 참조 `qgv/virtual_trading_inputs.py`, 합성 벡터 `tests/fixtures/virtual_trading_inputs_v1.json`)가 엔진 입력을 기기 RAM에서 조립한다.

- 시작일 전에는 아무 요청도 하지 않고 `NOT_STARTED`. 그 뒤에는 구글 로그인 세션이 연결되어 있을 때만 기존 비공개 가격 Worker로 `2y` 일봉을 순서대로(5.2초 간격) 읽는다. SPY → 환율(`KRW=X`, `JPYKRW=X`) → 종목 → 업종 ETF 순서.
- 세션 날짜는 SPY 완료 세션(시작일 이후). SPY가 없으면 장부를 만들지 않고 `SESSIONS_NOT_AVAILABLE`, 나머지 요청도 하지 않는다.
- 클라이언트 허용 목록이나 Worker가 거부한 기호는 오류 코드(예: `REQUEST_INVALID`)를 화면에 보이고 입력에서 빠진다. 없는 종가·환율은 채우지 않는다(`EXEC_PRICE_MISSING`·`EXEC_FX_MISSING`).
- Q·G는 공개 전진 검증 기록(RECORDED)에서만, V는 이 기기에 날짜별로 저장된 값(`investment.web.v1.virtual-trading-v-scores`, V만)에서만 읽는다. V는 아래 'V 기록'이 쌓는다.
- 세트 B는 사용자 정의 구성이 기기에 없어 `SET_B_NOT_DEFINED`. 그림자 장부는 ACTUAL 스냅샷(수량·평균단가)에서 출발하며, 그 스냅샷의 뉴욕 날짜 이후 세션만 쓴다. 원가는 첫 세션 이전 마지막 환율로 원화 환산한다.

## D-5 기준 표시 · V 기록 · 리허설 (S17)

`web_assets/virtual-trading-signals.js`(Python 참조 `qgv/virtual_trading_signals.py`, 합성 벡터 `tests/fixtures/virtual_trading_signals_v1.json`, 생성 `tools/virtual_trading_signals_reference.py`)와 `web_assets/virtual-trading-v-history.js`가 담당한다. 규칙 값은 바꾸지 않는다.

**D-5 기준 표시.** 러너는 2년 일봉 종가 전체(시작일 이전 포함)와 D-22 업종 ETF 시세를 엔진에 넘긴다. 시작일 필터는 세션 목록에만 걸린다. 그래서 정렬된 종가가 273개 이상이면 개별 이상 하락(`RECHECK_ABNORMAL_DROP`, ▼위험재검토)이 실제로 판정된다.
- 보고서 ③의 '업종 기준 · D-5' 칸에 회사별로 다음을 보인다: 실제로 쓴 기준(ETF 기호 또는 S&P 500), 정상·이상 하락·기준 N/A와 사유, V 기울기 사용 여부.
  - 기준 N/A 사유: `HISTORY_INSUFFICIENT`(정렬 n/273 함께 표시), `PRICE_NOT_ALIGNED`, `SECTOR_BASIS_NOT_AVAILABLE`, `DISTRIBUTION_DEGENERATE`.
- 업종 ETF 시세가 없을 때(Worker 거부 등) 엔진 코드(`sectorSeries`)는 S&P 500(SPY)으로 대체해 판정한다. 위 '업종 기준 가격이 없으면 기준 계산 불가'는 S&P 500까지 없을 때에 해당한다. 보고서는 대체를 'S&P 500 (XLY 없음 → 대체)'처럼 표시한다(엔진 동작은 그대로, 표시만 추가).
- 실제 흐름의 한계: 환율 `KRW=X`·`JPYKRW=X`(PR #191) 배포 전에는 미국·일본 종목이 판단 단계 1에서 ■차단(`DATA_FX_MISSING`)되어 D-5 단계까지 가지 않는다. 기준 칸은 판단과 별도로 계산하므로 그때도 기준 상태는 보인다.

**V 기록(생산자).** 러너가 결과를 낼 때마다(기록 모드·리허설 모두) 그 결과의 최신 완료 SPY 세션(러너의 날짜 규칙)을 날짜로 삼는다. 그 세션 종가(기기 RAM)와 공개 가격 없는 가치 입력(`sec-valuation-inputs.json`)으로 회사별 V를 계산해 저장한다.
- 대상: TARGET·세트 B·보유 회사.
- V 정의: 기기 V 요소(`DeviceValuation.view`)를 공식 v1 V 가중치 사본의 PREVIEW V 축(`EnginePreview.strategy`)으로 묶은 값이다. 빠진 요소는 재정규화하지 않는다(동결 규칙). 소수 둘째 자리로 반올림한다. V를 계산할 수 없는 회사는 기록하지 않는다(0으로 채우지 않음).
- 저장 규칙: V 숫자만 저장한다(가격·환율·장부 없음). 추가만 하며, 이미 있는 날짜·회사 값은 바꾸지 않는다. 가장 최근 기록일보다 이른 날짜는 받지 않는다(첫 기록 이전 소급 없음). 최대 400개 날짜를 남기고 오래된 날짜부터 지운다. 저장소를 읽을 수 없거나 형식이 깨졌으면 쓰지 않는다.
- V 기울기는 첫 기록 뒤 20거래일부터 쓸 수 있다. 그 전까지 S17은 'V 기록 N/20일'을 보인다. 엔진은 장부 세션 안에서 20세션 전 값을 비교하므로, 기록 모드에서는 2026-10-19부터 20세션이 지나야 실제로 쓰인다.
- 기기 백업(`device-backup.js`)에는 넣지 않는다. 백업은 명시적 설정과 보유만 담는 가격 없는 파일이다. V 기록은 가격에서 파생된 관찰 기록이라 AI 답변 보관함 같은 다른 기기 전용 키처럼 이 브라우저에만 둔다.

**리허설(리허설 · 기록 없음 / Rehearsal · not recorded).** 시작일 전 S17은 계속 `NOT_STARTED`이고 Worker 요청이 없다. '리허설 실행'을 누르면 같은 러너 경로로 2년 일봉을 받는다(시작일 관문만 건너뜀).
- 엔진 설정은 `start_date`만 최근 완료 SPY 세션 5개의 첫날로 옮긴다. 다른 규칙 값은 그대로다. 현금 0에서 매일 가상 입금으로 시작하며 RAM에서만 계산한다.
- 공개 전진 검증 기록(Q·G)이 없는 창 안 세션은 오늘 공개 화면 Q·G로 채우고 그 사실을 표시한다. 리허설 전용이며 다음 세션 Q·G를 앞당겨 쓰는 것을 알고 표시한다.
- 화면과 내보내기에는 '리허설 · 기록 없음' 배지(보라색)를 단다. 기록 모드는 '기록 모드'로 표시한다. 결과 객체에는 `mode: 'REHEARSAL'`이 붙는다. 장부·시트 저장 훅은 이 값이면 아무것도 쓰지 않아야 한다.
- 리허설은 어떤 장부·시트 데이터도 쓰지 않는다. V 기록은 장부와 독립이므로 리허설에서도 추가된다.
- 시작일 이후에도 같은 버튼으로 리허설을 볼 수 있다. '기록 모드로 돌아가기'로 되돌린다.

## 아직 연결하지 않은 것

- **가격 경로:** 개인 가격 Worker가 TARGET 19종목만 허용한다. 그래서 S&P 500, 업종 ETF, 세트 B 종목의 일봉을 기기에서 받을 수 없다([D-22 초안](D22_SECTOR_ETF_MAPPING_DRAFT.md)의 선택지 참고).
  - 그 전까지 엔진은 업종 기준 계산 불가로 동작한다.
  - 적중 판정(D+N)도 표본이 쌓이지 않는다.
- **장부 저장:** 시트 탭 저장(VirtualA·VirtualB·VirtualMine·VirtualMeta·VirtualFlags)은 다음 단계다(S17 화면 연결은 위 기기 러너로 완료).
