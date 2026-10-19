# V 단계별 집계(418·360·341)와 D-CV1~16 결정 상태 (2026-10-19)

> **상태: 문서만.** 계산 코드·게시 파일·calc_version·가드·워크플로는 바꾸지 않는다.
> 가격 값·가격 파생값·개인 자료는 이 문서에 없다. 합성 가격으로 세지 않았다.

- 작성: 2026-10-19 03:40 UTC / 2026-10-19 12:40 KST.
- 기준 브랜치: `claude/investment-system-top500-validation-alrugm` `fe7bbc90`(#326 병합 뒤).
- 앞선 문서: [V_GENERAL_COVERAGE_20261018](V_GENERAL_COVERAGE_20261018.md)(418·360·341 처음 보고), [CENTRAL_V_PUBLICATION_DESIGN_20261018](CENTRAL_V_PUBLICATION_DESIGN_20261018.md) §13(D-CV1~16), [FREE_SOURCE_COMBINATION_20261018](../daily_data_pipeline/FREE_SOURCE_COMBINATION_20261018.md)(가격 출처).
- 문의 초안(IEX·Alpaca, 미발송): [PRICE_PROVIDER_INQUIRY_DRAFTS_20261019](../daily_data_pipeline/PRICE_PROVIDER_INQUIRY_DRAFTS_20261019.md).

## 요약

- 네 단계를 따로 센다. **(a) 입력 완비 341 · (b) V 계산 가능 360 · (c) 투자 관문 통과 254(관문 제외 105, 미평가 1) · (d) Q·G·V 공통 산출 상한 357, 실제 수는 가격 필요 · 미판정.** 모두 GENERAL 434 기준이다.
- 폭포는 **434 → 418 → 360**이다. 434→418은 주식수 없음 10, EBIT·FCF 둘 다 없음 6. 418→360은 통화 1(ASML)과 V 축 50% 미달 57이다. 57의 첫 원인은 부채·현금 25, 경기순환형 정상화 EBIT 14, FCF 12, EBIT 5, 정상화 EBIT+FCF 1이다(§3).
- **관문 제외는 계산 실패가 아니다.** V는 계산되고, 승인된 관문 규칙이 V를 종합에서만 뺀다. 그래서 (b)·(d)와 따로 센다(§4-3).
- **341은 360·418의 부분 단계가 아니다.** 규칙이 다르다. 341 중 4곳은 (b) 미달이다(ASML, EXE, ROST, SW). (b) 통과 360 중 23곳은 (a) 결측이다. 418은 엔진 규칙이 아니라 입력 존재 상한이다(§5).
- 최신 게시 파일(as_of 2026-10-18T22:41Z)로 다시 셌다. 수는 10-17 파일 기준 보고와 같다.
- D-CV1~16 중 **기존 소유자 결정으로 이미 정해진 것은 D-CV15 하나다.** D-CV10의 통화 부분(환율을 만들지 않음)도 이미 정해져 있다. 나머지는 열려 있다. 대부분은 원칙이 이미 있고 선택만 남았다(§7).
- 보완 넷(정밀도·복원 위험, 이력과 전진검증, 다중 종류, 버전 필드)과 ASML 통화안은 §8·§9에 있다. **ASML은 결정 전까지 미산출이다.**

## 1. 기준 자료와 계산 경로

| 항목 | 값 |
| --- | --- |
| 파일 | Pages `sec-qgv2.json`. 2026-10-19 03:21 UTC(12:21 KST)에 받아 작업 공간에만 둠 |
| `as_of` | **2026-10-18T22:41:21.820666Z**(2026-10-19 07:41 KST) |
| `calc_version` | `qgv2-calc/2026-10-17.1` |
| 행 | 504(GENERAL 434, 금융 67, 자료 없음 3: BATS:CBOE, NASDAQ:HONA, NYSE:XOM), `cross_section_size` 498 |
| 파일 sha256 | `f7a6f1505cb305cd2532d4d902a2b45dbbd7eaf4959ad939638612b0a6c19425` |

- **(a) JS 경로(node):** 기준 브랜치 `web_assets`의 `SecQgv2.toInputs`(엄격 판독) → `Qgv2Inputs.fromInputs` → `QgvScores.compute`(가격 `{}`) → `coverageFor`의 `v_inputs_missing`.
- **(b)(c)(d) Python 경로:** PR #325 `claude/qgv2-inputs-py`(`172ac021`, 최신 `294b3ab8`에서도 결과 바이트 동일)의 `qgv2_inputs.from_published` → `engine_inputs`(경기순환 기준 `cyclical_basis`·유형 소속도 포함) → `qgv_v2.score_universe(gate=True, 기본 균형 프리셋, quotes={})`.
- (b)의 가격 무관 규칙은 `score_universe`가 부르는 `_metrics` 순서 그대로 판정했다. 가격 검사 다음의 통화 → 주식수 → 요인별 입력 조건이다. 가격이 필요한 조건은 판정하지 않고 "통과 가능"으로 두었다. 그래서 (b)는 상한이다.
- **대조:** Python (b) 판정·최대 가중치는 JS 판정(앞선 문서의 node 스크립트)과 434곳 모두 같다. 관문 결과와 Q·G 유무도 Python과 JS(`QgvScores.compute` 플래그 `VALUE_TRAP_CAUTION`)가 434곳 모두 같다.
- 가격이 없어서 434곳 모두 엔진 V 사유는 `NO_DEVICE_PRICE`다. 가격 값을 만들어 넣지 않았다.
- 스크립트와 원자료는 저장소 밖 작업 공간에만 있다.

## 2. 네 단계 정의

| 단계 | 이름 | 규칙 | 가격 필요? |
| --- | --- | --- | --- |
| 418 | 공개 입력 상한 | 희석 주식수 > 0 이고 EBIT 또는 FCF가 있음(`vCoverage.upper_bound`) | 아니오. 엔진 규칙이 아니다 |
| (a) | 입력 완비 | `coverageFor`: `V_INPUT` 7항목이 모두 유한값, `ebit_per_share_history` 3개 이상 | 아니오 |
| (b) | V 계산 가능 | 엔진 규칙 중 가격 무관 조건으로 V 축이 가중치 50%에 닿을 수 있음 | 가격 조건은 미판정(상한) |
| (c) | 투자 관문 통과 | Q 업종 백분위 > 30. ≤ 30이면 V를 종합에서 뺀다(`GATE_PERCENTILE`) | 아니오. Q만 쓴다 |
| (d) | QGV 공통 산출 | Q·G·V 축 점수가 모두 있음 | V 때문에 필요. 가격 무관 상한만 셈 |

- (c)는 (b)의 하위 단계가 아니다. 관문은 V 계산과 무관하게 Q로만 정해진다. 관문 제외 행도 V는 계산된다. 공식 순위에도 플래그와 함께 남는다(#318 D11 규칙, `qgv-scores.js` `qgReference` 주석).
- (d)는 관문과 무관하다. 관문 제외 행도 Q·G·V가 모두 있으면 (d)다.

## 3. 폭포 434 → 418 → 360

| 단계 | 남은 수 | 빠진 수 | 첫 실패 규칙(사유 코드) | 기업 |
| --- | --- | --- | --- | --- |
| GENERAL | **434** | | | (발행사 431, 같은 CIK 두 번째 코드 3: GOOGL, FOXA, NWSA) |
| | | −10 | `SHARES_NOT_AVAILABLE` | NASDAQ:BKR, NASDAQ:REG, NASDAQ:TTWO, NYSE:HSY, NYSE:LYB, NYSE:MCD, NYSE:SJM, NYSE:STZ, NYSE:V, NYSE:WAT |
| | | −6 | `EBIT_AND_FCF_NOT_AVAILABLE` | NYSE:ARE, NYSE:BXP, NYSE:CPT, NYSE:INVH, NYSE:O, NYSE:WELL |
| 공개 입력 상한 | **418** | | | (발행사 415) |
| | | −1 | `CURRENCY_BASIS_UNCONFIRMED`(보고 통화 EUR, 상장 가격 USD) | NASDAQ:ASML |
| | | −25 | `AXIS_WEIGHT_BELOW_50` ← `DEBT_CASH_NOT_AVAILABLE`(총부채 NA 24, 현금 NA 1: PCAR). 이익·FCF·업종 70 상실. 최대 0~30 | NASDAQ:AKAM, CDNS, DASH, DDOG, DXCM, INCY, PANW, PCAR, SMCI, TTD, VRSN, VRTX, NYSE:AES, DE, DECK, DHI, DLR, EME, EXPD, EXR, F, GM, MAA, ORCL, TPL |
| | | −14 | `AXIS_WEIGHT_BELOW_50` ← `NORMALIZED_EARNINGS_NOT_AVAILABLE`(경기순환형, 5년 마진 부족, FCF 있음). 최대 25~40 | NASDAQ:CASY, EXE, ROST, NYSE:COHR, CVNA, EMR, FDXF, GE, LEN, NEM, NVR, PHM, Q, SW |
| | | −12 | `AXIS_WEIGHT_BELOW_50` ← `FCF_NOT_AVAILABLE`(EBIT 있음, 모두 경기순환형). 최대 45 | NASDAQ:ABNB, APP, FANG, HST, NYSE:COP, D, DTE, EOG, PSX, VICI, VLO, WY |
| | | −5 | `AXIS_WEIGHT_BELOW_50` ← `EBIT_NOT_AVAILABLE`(FCF 있음). 최대 40 | NASDAQ:NWS, NWSA, NYSE:JCI, NKE, TXT |
| | | −1 | `AXIS_WEIGHT_BELOW_50` ← `NORMALIZED_EARNINGS_NOT_AVAILABLE` + `FCF_NOT_AVAILABLE`. 최대 0 | NASDAQ:APA |
| V 계산 가능 (b) | **360** | | | (발행사 358: GOOG·GOOGL, FOX·FOXA가 둘 다 통과) |

- "최대"는 가격 조건을 모두 통과한다고 가정한 V 축 최대 가중치(%)다. 실제 값이 아니다.
- 434→418의 16곳 원인 분석(태그·클래스 차원·리츠 방법론)은 [V_GENERAL_COVERAGE_20261018 §3·§4](V_GENERAL_COVERAGE_20261018.md)와 같다. 리츠 6곳은 (b)에서도 최대 0이다.
- 경기순환 판정은 기기와 같은 코드다(`classify_types_v0`, 유형 소속도). 이 파일에서 GENERAL 434곳 중 182곳이 경기순환형이다(10-17 파일 보고는 178).

## 4. 단계별 수

### 4-1. (a) 입력 완비 — 341

- 결측 0개 341, 1개 58, 2개 26, 3개 9.
- 항목별 결측(중복 가능): EBIT/주 이력 3개 미만 38, FCF 36, 총부채 24, EBIT 22, 희석 주식수 10, 3년 매출 CAGR 6, 현금 1.

### 4-2. (b) V 계산 가능 — 360 (상한)

- 360 = 418 − 58(§3). 실패 74 = 주식수 10 + 50% 미달 63(그중 6곳은 418 밖 리츠) + 통화 1.
- **가격 필요 · 미판정 조건:** EV > 0, 가격 있는 단면 8곳 이상, 업종 동료 8곳 이상(미만이면 전체로 대체), 회계연도 말월 월말 종가 3개 이상, 역DCF 근이 탐색 범위 안. 실제 V 수는 이 조건 때문에 360보다 작을 수 있다.
- 소유자 관찰 목표 391(= ceil(434×0.9))은 상한 360보다 크다. 지금 규칙·입력으로는 가격이 모두 붙어도 닿지 않는다.

### 4-3. (c) 투자 관문 — 가격 무관

| 모집단 | 통과(Q 백분위 > 30) | 관문 제외(≤ 30) | 미평가(Q 없음) |
| --- | --- | --- | --- |
| (b) 360 | **254** | 105 | 1 (NASDAQ:BKNG) |
| GENERAL 434 | 292 | 126 | 16 |

- Q 업종 백분위 기준: 업종 412, 전체 대체 6(업종 8곳 미만), 없음 16.
- GENERAL 미평가 16: NASDAQ:BKNG, BKR, CASY, DASH, NWS, NWSA, NYSE:ARE, EXPD, GE, GM, INVH, LEN, NEM, NVR, PHM, TXT(Q 축 미게시).
- 관문 제외 105곳은 **V 계산 실패가 아니다.** 가격이 붙으면 V가 계산되고 종합에서만 빠진다(`v_excluded = VALUE_TRAP_GATE`).

### 4-4. (d) QGV 공통 산출 — 가격 필요 · 미판정

- 가격 무관 상한: (b) 360 중 Q·G가 모두 있는 **357**. 빠진 3: NASDAQ:BKNG(Q 없음), NASDAQ:PSKY·NYSE:VMRK(G 없음).
- 참고: 357 중 관문 통과 253. 이것은 "V가 종합에 들어갈 수 있는 상한"이다. (d) 자체는 관문과 무관하다.
- **실제 (d) 수는 가격 필요 · 미판정이다.** 가격 공급자 결정(D-CV1) 뒤 비공개 실행에서 개수만 잰다.

## 5. 341과 360·418의 관계 — 깔때기가 아니다

| | (b) 통과 | (b) 미달 | 합 |
| --- | --- | --- | --- |
| (a) 완비 | 337 | 4 | **341** |
| (a) 결측, 418 안 | 23 | 54 | 77 |
| 418 밖 | 0 | 16 | 16 |
| 합 | **360** | 74 | 434 |

- 341은 모두 418 안에 있다. 418 = 337 + 4 + 23 + 54.
- **(a) 완비인데 (b) 미달 4곳:** NASDAQ:ASML(통화), NASDAQ:EXE·NASDAQ:ROST·NYSE:SW(경기순환형인데 5년 마진이 없어 정상화 EBIT 불가). (a)는 통화와 경기순환 정상화를 보지 않는다.
- **(b) 통과인데 (a) 결측 23곳:** FCF만 12, EBIT/주 이력만 8, 이력+CAGR 1, CAGR만 1, FCF+CAGR 1. (b)는 가중치 규칙이라 FCF가 없어도 이익·업종·자기 역사로 60이 된다.
- 418은 "주식수 + EBIT 또는 FCF"라는 입력 존재 상한이다. 엔진 50% 규칙·통화·경기순환 정상화를 보지 않는다. 그래서 418 ⊃ 360이지만 418 ⊃ 341 ⊄ 360이다.
- 정리: 화면·보고에서 세 수를 한 줄 깔때기로 그리지 않는다. 418(입력 상한) → 360(엔진 가격 무관 상한) → 실제 V(가격 필요)만 깔때기다. 341은 별도 진단 지표다.

## 6. 기업별 표

434행 전체는 [부록 A](#부록-a--기업별-단계-434행)에 있다. 열: 코드, 도달 단계, 첫 실패 규칙, (a), 418, (b), (c), (d).

## 7. D-CV1~16 — 이미 결정된 것과 실제로 열린 것

표기: **(i) 결정됨** = 기존 소유자 결정이 그 선택을 이미 정함. **(ii) 열림** = 소유자 선택이 남음. "원칙"은 선택지를 좁히는 기존 결정이다. 소유자는 보완 자료 전에 일괄 승인하지 않는다. 그래서 권장안을 승인된 것처럼 쓰지 않는다.

| 번호 | 상태 | 근거(기존 결정·지시) | 남은 선택 / 보완 |
| --- | --- | --- | --- |
| D-CV1 가격 공급자·사용권 | **(ii) 열림** | 중앙 V 방향은 이 세션 소유자 지시로 승인(CENTRAL :10). 그러나 GSQ-001(Actions 시세 수집 금지), GSQ-006·007·023(공개 V 금지), GSQ-010(공개 원시 가격 금지)은 append-only 새 기록 전까지 유효([FREE_SOURCE 유지 경계](../daily_data_pipeline/FREE_SOURCE_COMBINATION_20261018.md)) | 공급자 선택과 서면 사용권. 문의 초안(IEX·Alpaca, 미발송) |
| D-CV2 가격 의존 사유 공개 형태 | **(ii) 열림** | 원칙: 원시 가격·EV·수익률 비공개, 공개는 0~100 점수·순위·사유·커버리지·기준일뿐(이 세션 소유자 지시). 사유 코드가 주는 "가격 경계"는 이 원칙이 직접 다루지 않는다 | 보완 1에서 함께 판단 |
| D-CV3 V 요인 정밀도 | **(ii) 열림** | 같은 원칙 | 보완 1 |
| D-CV4 개인 미리보기 | **(ii) 열림** | #300 승인(2026-10-18): 공식 세부 비중과 같은 축은 공개 축 점수 그대로, 세부 비중을 바꾸면 요인부터 다시 집계([USER_DECISIONS_PENDING](../USER_DECISIONS_PENDING.md) 10-18 오후). V 세부 비중 변경은 공개 V 요인 점수와 엔진 입력 경로가 있어야 정확하다 | 엔진 확장(코드 변경) 승인 여부, 그 전 "근사" 표시 또는 차단 |
| D-CV5 공급 전체 실패 기준 | **(ii) 열림** | 원칙: 적격이 모자라도 조건을 완화하지 않는다(10-15 TARGET v1 확정 조건). 원장 주 평가는 Q·G 90%(454) 기준(10-15·10-16). V 기준 숫자는 없다 | 95%/90%/부분 게시 |
| D-CV6 오래된 정상본 표시 | **(ii) 열림** | 원칙: 이전 관측을 유지할 때 수집 시각을 갱신하지 않고 원래 시각으로 최신성을 판단(10-17 #278 선택지 a). 숨김(c)은 이 원칙과 어긋나지 않지만 "기준일 표시" 원칙과 맞지 않는다 | 2거래일/5거래일 |
| D-CV7 버전 필드 | **(ii) 열림** | 원칙: 행마다 `calc_version`, 다른 버전은 같은 순위 모집단에 넣지 않음(10-15). V가 붙으면 별도 버전으로 기록하고 기존 기록은 바꾸지 않음(GSQ-020 전진검증, FORWARD_VALIDATION_V1 결정 원문). calc_version이 바뀌면 평가 구간을 새로 연다(10-16) | 보완 4 |
| D-CV8 TARGET 회사 순위 | **(ii) 열림** | 원칙: TARGET 행은 단면 점이 아니고 단면에 대해서만 백분위를 매김([QGV_V2_V_DEVICE](QGV_V2_V_DEVICE.md):55, GSQ-022 v2 기준). 042700 v2 순위는 참고 순위(10-13 결정). 공개 전체 순위는 새 대상이다 | CIK 점 교체 / Universe 행만 / 둘 다 |
| D-CV9 다중 종류 순위 | **(ii) 열림** | 원칙: 경제적으로 같은 종류(GOOGL/GOOG 등)는 합산해 한 회사로 순위에 넣고, 비율이 다르거나 불명확한 종류는 제외(GSQ-020 2차, M3 맥락). 자동 합산·비율 추정 금지(GSQ-014). 상장 안 된 Alphabet B는 A 가격으로 평가(GSQ-021) | 보완 3 |
| D-CV10 ADR·해외 발행인 | **(ii) 열림**(통화 부분은 (i)) | 통화: "통화가 다르면 `CURRENCY_BASIS_UNCONFIRMED`, 환율을 만들지 않는다"(GSQ-020 2차 DCF IFRS, [DCF_V1_1_PARAMETERS](../valuation/DCF_V1_1_PARAMETERS.md) 결정 2). ASML은 미국 상장 USD 라인만(FREE_SOURCE) | 상장 증권·비율 표 확인 규칙. ASML 통화는 §9 |
| D-CV11 분할 확인 근거 | **(ii) 열림**((c) 생략은 배제됨) | 가격 기준 불연속 구간은 판정 불가로 두고 가격을 임의 보정하지 않음(10-17 차트 Q3). 임의 배수 보정 금지(10-17 V-SHARES-SCALE). Q-SPLIT(10-15) | (a) 공급자 분할 사건 필수 / (b) 비율 변화 감지 |
| D-CV12 실행 안 JS 대조 | **(ii) 열림** | 소유자 결정 없음. Python=JS 벡터 대조는 기존 관행이다 | (a) collect 안 대조 / (b) 벡터 시험만 |
| D-CV13 게시 시각 표시 | **(ii) 열림** | 원칙: 배포에 실패하면 생성 산출물을 "실제 게시 데이터"라 부르지 않음(10-16 보완). "실제 게시 커버리지"는 같은 실행 deploy 성공 확인 때만(CURRENT_HANDOFF 보고 규칙). 읽은 시각과 가격 시각 분리(#319) | (a)(b)(c) 모두 원칙과 맞다. 선택만 남음 |
| D-CV14 게시본 이력 | **(ii) 열림** | 원칙: 원장은 다시 쓰지 않음(10-15), 추가 전용·소급 금지(FORWARD_VALIDATION_V1 §3), V 포함은 별도 버전(GSQ-020), Frozen은 값 삭제·receipt만(GSQ-010 3항), 과거 공개 사본 재작성 안 함(GSQ-010 4항) | 보완 2 |
| D-CV15 모델 포트폴리오 위치 | **(i) 결정됨** | GSQ-018 경계: 가격·장부·손익·보고서는 공개 저장소·Pages·로그에 넣지 않고 계산은 기기 RAM에서만. 선정 규칙은 10-14 결정(TARGET v1·세트 B). 게시본에서 기기 계산하는 (a)는 이 범위 안이다. 중앙 파일 (b)는 새 공개 경로라 따로 결정이 필요하다 | 없음((b)를 원할 때만 새 결정) |
| D-CV16 라이브 게시본 손상 | **(ii) 열림** | **충돌 주의:** `LIVE_INVALID`(HTTP 200이지만 JSON이 깨진 게시본)는 자동 통과시키지 않고 차단한다(10-17 #278 보완). 지금 패턴은 전체 배포 거부다. CENTRAL 권장 (a)는 이와 다르다. CENTRAL이 든 "V 실패가 다른 공개를 멈추면 안 된다"는 직접 결정이 아니라 비슷한 결정(DART: 외부 접근 실패는 원인만 보고하고 배포 계속)에서 끌어온 것이다 | (a) 게시본만 실패 / (b) 기존 LIVE_INVALID 패턴 |

## 8. 보완 자료

### 보완 1 — 전체 정밀도 공개와 복원 위험 (D-CV2·D-CV3)

**무엇을 알 수 있나.** 공개 SEC 입력에 EBIT·FCF·총부채·현금·희석 주식수·주당 이력이 있다. 백분위는 중간 순위 `100·(less + 0.5·(equal−1))/(n−1)`이다(`qgv_v2.percentile`). 그래서 백분위 = 순위다.

| 정보원 | 외부 가격 없이 | 다른 종목 시장 가격을 알 때 |
| --- | --- | --- |
| V 단면 요인 4개(이익·FCF·업종·기대) 전체 정밀도 | 순서만 나온다. 순서 제약은 열린 영역이라 해가 무수히 많다. **점 복원 불가, 절대 경계도 없음** | 순위 이웃 두 종목의 수익률 사이로 그 종목 EV가 묶인다 → 가격 **구간**. 요인 넷(이익·FCF·업종·기대)이 각각 구간을 줘서 교집합이 더 좁아진다 |
| 자기 과거 대비 | 점이 4~6개라 백분위가 20칸 단위다. 현재 수익률이 과거 몇 번째 사이인지 나온다 | 과거 월말 종가(시장 공개)와 공개 주당 EBIT로 현재 가격이 두 값 사이 구간 |
| V 축 + 요인 4개 | 축은 가중 평균이라 빠진 요인 1개가 정확히 역산된다 | 같음 |
| 종합 + Q·G + 비중 | 관문 밖 행은 V 축이 역산된다(종합 = 축 가중 평균) | 같음 |
| `EV_NON_POSITIVE` | 가격 ≤ (현금 − 부채)/주식수. **절대 상한** | 같음 |
| `ROOT_NOT_BRACKETED` | 가격 ≤ DCF(−50%) 또는 ≥ DCF(+100%). 두 값 모두 공개 입력·공개 DCF 설정으로 계산됨. **절대 한쪽 경계** | 같음 |

**크기(이 파일, 가격 무관 상한 기준).**

| 단면 | n(상한) | 백분위 한 칸 | 소수 1자리 반올림 | 정수 반올림 |
| --- | --- | --- | --- | --- |
| 이익 수익률 | 370 | 0.271 | 순위 그대로 남음 | 한 값에 약 3.7순위 → ±2순위 |
| FCF 수익률 | 363 | 0.276 | 그대로 | ±2순위 |
| 기대 점검 | 342 | 0.293 | 그대로 | ±2순위 |
| 업종 대비(제조·산업기술) | 159 | 0.63 | 그대로 | ±1순위 |
| 업종 대비(서비스·소프트웨어·헬스) | 65 | 1.56 | 그대로 | **그대로** |
| 업종 대비(나머지 7개 업종, 9~36곳) | 9~36 | 2.9~12.5 | 그대로 | **그대로** |
| 자기 과거 대비 | 4~6점 | 20~33 | 그대로 | 그대로 |

- n은 단면 점(한 CIK 한 점) 중 가격 무관 조건을 통과한 수다. 실제 n은 가격 조건 때문에 이보다 작다. 작을수록 한 칸이 넓어져 반올림 효과는 더 줄어든다.
- **소수 1자리 반올림은 방어가 0이다.** 한 칸(≥ 0.27)이 0.1보다 커서 순위가 그대로 복원된다. 정확성만 잃는다.
- **정수 반올림은 큰 단면 3개에서만 ±2순위를 흐린다.** 업종 대비 9개 중 8개 업종과 자기 과거 대비는 그대로다. 대신 개인 미리보기 동등성과 공개 자기 검증(축 = 요인 가중 평균)을 깬다.
- 절대 경계를 주는 것은 정밀도가 아니라 **사유 코드 두 개**다. (b) 360 중 순현금(현금 > 부채) 54곳만 `EV_NON_POSITIVE`가 가능하다. 역DCF 사유는 기대 점검 대상 310곳 모두에서 가능하다.
- 가격 구간의 실제 폭(중앙값 등)은 **가격 필요 · 미측정**이다. 측정하려면 공급자 결정 뒤 비공개 실행에서 정밀도별 구간 폭의 분포 통계(개수·분위수만)를 낸다. 가격·종목별 구간은 출력하지 않는다.

**판단 틀.** S&P 500 종가는 원래 시장에 공개된 정보다. 위험의 핵심은 "가격 비밀"이 아니라 **공급자 데이터를 대신하거나 역산할 수 있는 파생물인가**(사용권)다(Tiingo §1.6(c)의 대체 불가·역산 불가 요건과 같은 원리, FREE_SOURCE). 순위·백분위는 공급자 값을 점으로 되살리지 못한다. 그러나 순위 자체가 가격 파생 정보다. 이것을 공개해도 되는지는 서면 사용권으로만 정해진다.

| 안 | 순서 정보 | 절대 경계 | 미리보기·자기 검증 | 판단 |
| --- | --- | --- | --- | --- |
| (a) 전체 정밀도 + 사유 묶음(D-CV2 b) | 정확한 순위 | 없음 | 정확 | **권장** |
| (b) 소수 1자리 + 사유 묶음 | 정확한 순위(같음) | 없음 | 깨짐 | (a)에 지배됨 |
| (c) 정수 + 사유 묶음 | 큰 단면만 ±2순위 | 없음 | 깨짐 | 이득 작음 |
| (d) V 요인은 5분위·10분위, 축·종합은 정수 | 구간 크게 흐림. 그러나 공식 순위가 종합 순서를 그대로 줌 | 없음 | 미리보기는 "근사"만 | 순위를 공개하는 한 효과 제한 |
| (e) 원 사유 코드 공개(D-CV2 a) | — | **있음**(상한·한쪽 경계) | — | 비권장 |

- 권장 조건: (a)는 공급자 서면 확인(파생 점수·순위 공개 허용) 뒤에만 유효하다. 사유 묶음 `PRICE_DEPENDENT_NOT_COMPUTABLE`은 표시 어휘만 바꾼다. 점수·규칙은 그대로다.

### 보완 2 — 최신 게시본만 공개 vs 전진검증 이력 (D-CV14)

**지금 규칙(사실).**
- 공개 원장 `forward-validation-ledger.json`은 추가 전용이다. 이미 쓴 기록은 바이트 그대로 둔다. 소급하지 않는다(FORWARD_VALIDATION_V1 §2·§3).
- 원장에는 TARGET 19종목의 Q·G만 있다. 가격·V는 없다. V 포함 버전 배열(`forward_validation/v1+dcf_v1_default`)은 **비어 있어야 검증을 통과한다**(`forward_ledger.py:517`). V를 넣으려면 별도 결정과 검증기 변경이 필요하다(§4).
- 원장 사본은 비공개 저장소 릴리스 `forward-ledger-YYYY-MM-DD`에도 올라간다(§5).
- 평가 구간은 `calc_version`으로 나뉜다. 다른 구간을 잇지 않는다. 각 기록은 관측 당시 판정을 따른다(10-16 지시, §10).
- PIT: 게시본은 기준일 D 종가와 D 22시대 UTC에 받은 SEC 자료의 "지금" 점수다. 전진 관측에는 맞다. 백테스트 증거로는 쓰지 않는다(CENTRAL §7).
- Frozen은 값을 지우고 해시·기준일·출처·크기 receipt만 둔다(GSQ-010 3항).
- Pages 배포본은 git에 커밋되지 않는다. 그래서 "최신본만"이 우리 쪽에서는 성립한다. 제3자가 매일 받아 쌓는 것은 막지 못한다. 막을 수 있는 것은 **우리가 보관·배포하는 범위**다.

**왜 이력이 문제인가.** SEC 입력이 같은 두 날의 순위 변화는 상대 가격 변화의 방향이다. 날짜별 공개 이력이 길수록 가격 경로 정보가 쌓인다. 공급자 권리 표에서 ⑦(날짜별 점수·검증 이력 보관)·⑧(종료 후 보관)은 IEX를 빼면 모두 미확인 또는 불가다(FREE_SOURCE 표 A).

| 안 | 공개 | 검증 증거 | 권리 필요 | 판단 |
| --- | --- | --- | --- | --- |
| (a) 최신본만, 보관 없음 | 최신 게시본 1개 | 없음. V 전략 전진검증을 나중에 재현할 수 없다 | ④⑤⑥ | 검증 공백 |
| (b) 공개 이력 누적(원장 V 버전에 매일 V·순위) | 매일 누적 | 공개·재현 가능 | ④~⑦, ⑧ | 가격 경로 정보 축적. 권리 대부분 미확인 |
| (c) 최신본 공개 + 비공개 보관(날짜별 게시본 바이트) | 최신 1개 | 비공개로 재현 | ④⑤⑥ + ⑦(비공개)·⑧ | 이력은 남지만 공개 쪽 위변조 증명이 없다 |
| (d) **(c) + 공개 원장에 가격 무관 지문만** | 최신 1개 + 날짜별 `publication_id`·게시본 sha256·`v_calc_version`·기준일·커버리지 개수 | 비공개 바이트를 나중에 공개 해시로 대조해 "그날 그 게시본"임을 증명 | (c)와 같음 | **권장** |

- (d)의 해시는 점수 묶음 전체의 해시다. 점수는 수백 개의 배정밀도 값이라 추측 대조가 불가능하다. 가격 해시와 다르다(가격은 후보를 넣어 맞춰 볼 수 있어 금지, CENTRAL §3-3).
- (d)는 원장 새 버전 키가 필요하다. 지금 검증기는 V 포함 배열이 비어 있어야 통과한다. 그래서 원장 스키마·검증기 변경과 소유자 승인이 필요하다. 기존 v1·v2 배열은 그대로 둔다(GSQ-020).
- 전진 수익률 계산은 지금처럼 기기에서 한다(GSQ-018). 공식 V 전략의 평가는 비공개 보관본과 공개 지문을 함께 쓴다.
- 비공개 보관 권리(⑦·⑧)가 거부되면: (a)로 가되 공개 원장에 지문만 남긴다. 지문만으로는 재계산이 안 된다는 한계를 보고에 적는다.
- 문의 초안은 이 권장에 맞췄다(공개는 최신본, 날짜별 점수 묶음은 허락될 때만 비공개 보관). 기존 FREE_SOURCE 부록 초안의 "날짜별 점수·검증 이력을 공개 저장소에 계속 남깁니다" 문장은 이 권장과 다르다. 새 초안에서 고쳤다.

### 보완 3 — CIK당 한 순위 vs 증권별 가격·가치 (D-CV9)

**사실(이 파일).**

| 회사(CIK) | 코드 | 단면 점 | (b) | 관문 |
| --- | --- | --- | --- | --- |
| Alphabet | NASDAQ:GOOG / NASDAQ:GOOGL | **GOOG**(정렬 첫 코드) | 둘 다 통과 | 둘 다 평가됨 |
| Fox | NASDAQ:FOX / NASDAQ:FOXA | **FOX** | 둘 다 통과 | 둘 다 평가됨 |
| News Corp | NASDAQ:NWS / NASDAQ:NWSA | **NWS** | 둘 다 미달(EBIT 없음, 최대 40) | 미평가(Q 없음) |

- Q·G는 CIK 단위 재무라 두 코드가 같다. V만 다르다. 엔진은 **그 코드 종류의 가격 × 회사 전체 희석 주식수**로 EV를 만든다(기존 근사, QGV_V2_V_DEVICE :16). 종류 간 가격 차이만큼 두 코드의 EV가 다르다.
- 단면 점은 정렬된 첫 코드다(`qgv2-inputs.js:70`). 두 번째 코드는 같은 발행사 점을 뺀 단면에 대해 백분위를 받는다(`_cross` issuers 규칙).
- TARGET은 Alphabet Class A `GOOGL`을 쓴다(소유자 승인 식별, QUOTES_FX_OPTIONS_26E :19). 단면 점 GOOG와 다르다.
- 가격은 코드마다 따로 받는다. 한 종류 가격을 다른 종류에 쓰지 않는다(FREE_SOURCE 심볼 매핑).
- 커버리지는 코드 기준(360)과 발행사 기준(358)을 둘 다 적어야 한다.

| 안 | 내용 | 장점 | 단점 |
| --- | --- | --- | --- |
| (a) CIK 한 순위, 대표 = 단면 점 코드 | 공식 `rank`는 GOOG·FOX·NWS 행에만. 다른 코드는 자기 V와 가격 상태를 보이되 순위 없음 | 새 규칙 없음. 단면과 순위가 같은 점. GSQ-020 "한 회사로 순위" 원칙과 맞음 | TARGET GOOGL과 대표가 다름. 대표가 덜 거래되는 종류일 수 있음 |
| (b) CIK 한 순위, 대표 = 명시 대표 코드 표 | 회사별 대표 코드 표(버전 관리). 단면 점도 같은 코드로 | TARGET·M3와 맞출 수 있음 | 새 표·새 규칙. 단면 점이 바뀌면 V 백분위가 바뀜(`v_calc_version` 올림) |
| (c) 코드마다 순위 | 두 코드가 각각 순위 | 증권별로 보임 | 같은 회사가 두 번 오름. 한 CIK 한 점·GSQ-020 원칙과 충돌 |
| (d) CIK 한 순위 + 회사 단위 시가총액 | 종류별 가격 × 종류별 주식수 합으로 EV | EV가 정확함 | 종류별 주식수가 필요. SEC 차원 태그(V-DIM-SHARES 후보)·SH-BASIS 미결. 상장 안 된 종류는 GSQ-021 규칙. 방법론 변경 |

- **권장: 지금은 (a).** 다른 종류 코드는 "같은 회사 다른 주식 종류 · 공식 순위는 대표 코드 1개"로 표시한다. TARGET 보기에서 GOOGL은 TARGET 안 순위만 보인다. (d)는 SH-BASIS 결정 뒤 새 `v_calc_version`으로 검토한다. (c)는 비권장이다.

### 보완 4 — `v_calc_version`과 최상위 `calc_version` 호환 (D-CV7)

**지금 `calc_version`을 읽는 곳과 기대.**

| 소비자·가드 | 기대 |
| --- | --- |
| `sec_qgv2.require_qgv2`, JS `SecQgv2` 엄격 판독기 | 최상위·행 **정확한 키 집합**(`TOP_KEYS`, `ROW_KEYS`). 값은 `qgv2-calc/YYYY-MM-DD.n` 형식(`CALC_VERSION_PATTERN`). 새 키가 생기면 파일 전체를 거부한다 |
| `qgv2-inputs.js` `versionMismatch` | 행 버전 ≠ 파일 버전이면 `CALC_VERSION_MISMATCH`, 단면 밖 |
| `leaderboard-screen.js` `populationOf`, `stat-radar.js`, `universe-company.js` | 같은 버전 행만 모집단·표시 |
| `forward_ledger.py` `basis` | `calc_version`, 구간 `segment` = calc_version. 바뀌면 새 구간 |
| `virtual_trading_inputs.py`, `virtual-trading-runner.js` | 최신 기록 calc_version의 현재 구간만 씀 |
| TARGET v1 확정(#248·#263) | 확정 때 calc_version 일관성(`CALC_VERSION_MIXED`), 숫자 재대조는 calc_version에 묶임 |
| `pages_freshness_guard.py` | 수집 시각 표지로 비교. 다른 calc_version으로의 정상 전환은 후퇴가 아님 |
| `v-coverage.js` | "계산 버전" 칸에 sec-qgv2 calc_version 표시 |

**안 비교.**
- **(b) 하나로 합침:** V 규칙만 바꿔도 `v2_factors.CALC_VERSION`을 올려야 한다. 그러면 새 파일이 새 버전을 선언하고, 아직 다시 수집되지 않은 샤드 행은 옛 버전이라 `CALC_VERSION_MISMATCH`로 단면에서 빠진다. 수집은 하루 한 샤드(7샤드)라 **Q·G 행 대부분이 최대 7일간 순위 밖**이 된다. 원장 구간도 쓸데없이 끊긴다. 비권장.
- **(a) 분리(권장):**
  1. `qgv-official.json` 최상위 `calc_version`은 같은 실행 입력 `sec-qgv2.json`의 값과 **같아야 한다**. 엄격 검증기가 확인한다. 의미를 바꾸지 않는다.
  2. `v_calc_version`은 **다른 접두어**를 쓴다(예: `qgv2-vpub/YYYY-MM-DD.n`). `CALC_VERSION_PATTERN`에 맞지 않으므로 기존 판독기가 calc_version으로 오인할 수 없다.
  3. `sec-qgv2.json`에는 `v_calc_version`을 넣지 않는다. 넣으면 정확한 키 집합 검사로 Python·JS 판독기가 파일을 거부한다.
  4. 원장에 V 포함 기록이 생기면 구간 키는 (`calc_version`, `v_calc_version`) 쌍이어야 한다. calc_version만 보면 V 규칙이 바뀐 날 구간이 이어져 "다른 버전 순위를 섞지 않는다"(10-15)를 어긴다. 지금 Q·G 원장은 그대로 둔다.
  5. 가상매매·TARGET 확정이 공식 V 순위를 쓰게 되면, 현재 구간과 확정 일관성 검사에 `v_calc_version`도 넣는다.
  6. 화면 "계산 버전" 칸은 공식 게시본 모드에서 두 값을 함께 보인다.
- 어느 쪽이든 기존 기록·calc_version 값은 바꾸지 않는다.

## 9. ASML 통화 방법론 — 결정 전까지 미산출

**근거(이 파일).**
- `NASDAQ:ASML` 행: `currency` **EUR**, `taxonomy` us-gaap, 회계연도 말 2025-12-31, LIVE, `TARGET:asml`도 EUR. V 입력 7항목은 모두 있다((a) 완비).
- EBIT·FCF의 TTM 끝이 FY 끝(2025-12-31)과 같다. 분기 6-K 수치는 companyfacts에 없어 입력이 연간뿐이다. 미국 10-Q 기업보다 입력이 오래됐다.
- 경기순환형이다. 자기 과거 대비는 원래 쓰지 않는다. 관문은 통과(Q 백분위 > 30)다.
- **엔진:** `_metrics`가 가격 통화 ≠ 입력 통화면 V 요인 5개 모두 `CURRENCY_BASIS_UNCONFIRMED`(`qgv_v2.py`). 미국 상장 가격은 USD다.
- **역DCF 매개변수:** `dcf_parameters/v1.1-default`의 `currency`는 USD다. `dcf._parameters`는 매개변수 통화 = 현금흐름 통화 = 가격 통화일 때만 계산한다. 할인율 10%·영구성장 2%도 USD 기본값(UNCALIBRATED)이다.
- **기존 결정:** 통화가 다르면 환율을 만들지 않고 `CURRENCY_BASIS_UNCONFIRMED`(GSQ-020 2차). 환율은 기기 RAM에서만, 공개 저장소·로그 금지(GSQ-021). FX 값 공개 게시는 제외(GSQ-020 2차 매크로). ASML은 미국 상장 USD 라인만, 유로넥스트 가격·환산으로 대체 금지(FREE_SOURCE).
- **상장 증권:** NASDAQ ASML은 보통주 1주를 나타내는 뉴욕 등록 주식으로 알려져 있다. 저장소 안에 확인 근거가 없다. D-CV10 비율 표 확인 대상이다.
- **FX 시점:** ECB 기준환율은 TARGET 근무일 16:00 CET 전후 갱신이다(QUOTES_FX_OPTIONS_26E). 뉴욕 종가 16:00 ET는 22:00 CET라 약 6시간 차이가 있다. 휴무일에는 그날 값이 없다. EUR/1 USD는 ECB 공시값(USD/1 EUR)의 역수라 파생 환율 표시가 필요하다.

| 안 | 방법 | 산출 범위(가격 무관 최대) | 필요한 결정·변경 | 위험 |
| --- | --- | --- | --- | --- |
| A. 현행 유지 | 미산출 `CURRENCY_BASIS_UNCONFIRMED` | 0 | 없음(GSQ-020과 같음) | TARGET 1종목이 V·공식 순위 없음 |
| B. 가격을 EUR로 환산(비율만) | 기준일 D의 USD 종가 × 같은 날 ECB 환율(역수) → EUR EV. 엔진에 `{price, currency:'EUR'}`로 넘김 | 이익 25 + FCF 25 + 업종 20 = **70**. 기대 점검은 DCF 매개변수가 USD라 계속 NA | GSQ-020 "환율 만들지 않음"을 공식 V에서만 바꾸는 새 결정. FX 출처(ECB, 출처 표시·파생 표시) 사용 경로. 어댑터 규칙 → `v_calc_version` 올림. 엔진 변경 없음 | 6시간 시차. 같은 날 환율이 없으면 그날 ASML NA(이전 환율로 채우지 않음) |
| C. 재무를 USD로 환산 | 흐름은 기간 평균 환율, 잔액은 기간 말 환율로 환산 후 USD 엔진 | 85(기대 점검 포함) | 환산 방법론 결정, 환율 다수 시점, USD DCF 매개변수를 EUR 사업에 적용하는 근거 | 방법론 변경이 큼. 공개 입력의 의미가 바뀜 |
| D. 유로넥스트 EUR 종가 | 1차 상장 가격 | 85 | 승인 식별(NASDAQ ASML)·FREE_SOURCE 규칙 변경, 비미국 공급자 | 다른 시장·다른 날짜 혼합. 비권장 |
| E. 구조적 해당 없음 | 금융처럼 "해당 없음" 표시 | 0 | 표시 규칙 결정(FIN-NA-CODE와 같은 성격) | 정보 손실 |

**권장.**
1. 결정 전까지 **A(미산출)** 를 유지한다. 화면 사유는 "통화 기준 미확인 · 공식 순위 없음"이다.
2. 결정할 때는 **B**를 권장한다. 비율 요인(이익·FCF·업종)은 통화에 무관한 무차원 값이다. 환율 하나만 기준일에 쓴다. 엔진·DCF는 바꾸지 않는다. 기대 점검 NA로 남는 비중 70이 50% 규칙을 넘는다.
3. B의 조건: 환율은 RAM에서만 쓰고 게시하지 않는다. 게시본에는 "가격 EUR 환산 · ECB 기준환율 역수 · 기준일"만 적는다. 같은 날 환율이 없으면 NA다. 상장 증권 비율(1:1) 근거를 D-CV10 표에 먼저 넣는다.
4. C·D는 비권장이다.

## 10. 하지 않은 것

- 코드·게시 파일·가드·워크플로 변경 없음. 가격 조회·공급자 연락 없음. 문의 초안은 보내지 않았다.
- 실제 V 수, 실제 (d) 수, 가격 구간 폭은 측정하지 않았다(가격 필요).
- D-CV 권장안을 승인된 것으로 기록하지 않았다. 결정 목록(USER_DECISIONS_PENDING)에도 아직 넣지 않았다.

## 부록 A — 기업별 단계 (434행)

- 도달 단계: **S0** GENERAL만(418 미달) · **S1** 418 통과, (b) 미달 · **S2** (b) V 계산 가능.
- 첫 실패 규칙: S0은 418 규칙의 실패. 괄호 안은 같은 행의 (b) 실패 원인. S1은 (b)의 첫 실패(50% 미달이면 그 원인).
- (a): `coverageFor` 결과. 결측 항목 이름을 적는다.
- (b): 50% 미달이면 가격 무관 최대 V 가중치(%).
- (c): 통과 = Q 업종 백분위 > 30, 제외 = ≤ 30(V를 종합에서만 뺌, 실패 아님), 미평가 = Q 없음.
- (d): "가격 필요 · 미판정" = Q·G가 있고 (b) 통과. 실제 산출은 가격 연결 뒤에만 정해진다.

| 코드 | 도달 단계 | 첫 실패 규칙 | (a) 입력 완비 | 418 | (b) | (c) 관문 | (d) Q·G·V |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NASDAQ:AAPL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:ABNB | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 통과 | 불가((b) 미달) |
| NASDAQ:ADBE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:ADI | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:ADP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:ADSK | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:AEP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:AKAM | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 30%) | 통과 | 불가((b) 미달) |
| NASDAQ:ALGN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:AMAT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:AMD | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:AMGN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:AMZN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:APA | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_FCF_NOT_AVAILABLE | 결측: FCF, 3년 매출 CAGR | 예 | 아니오(최대 0%) | 통과 | 불가((b) 미달) |
| NASDAQ:APP | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 통과 | 불가((b) 미달) |
| NASDAQ:ASML | S1 공개 입력 상한 | CURRENCY_BASIS_UNCONFIRMED | 완비 | 예 | 아니오 | 통과 | 불가((b) 미달) |
| NASDAQ:AVGO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:AXON | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:BIIB | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:BKNG | S2 V 계산 가능 | — | 결측: EBIT/주 이력 | 예 | 예 | 미평가(Q 없음) | 불가(Q 없음) |
| NASDAQ:BKR | S0 GENERAL | SHARES_NOT_AVAILABLE | 결측: EBIT, 희석 주식수, EBIT/주 이력 | 아니오 | 아니오 | 미평가(Q 없음) | 불가((b) 미달) |
| NASDAQ:CASY | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 미평가(Q 없음) | 불가((b) 미달) |
| NASDAQ:CDNS | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 30%) | 통과 | 불가((b) 미달) |
| NASDAQ:CDW | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:CEG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:CHRW | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:CHTR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:CMCSA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:COO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:COST | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:CPRT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:CRWD | S2 V 계산 가능 | — | 결측: EBIT/주 이력 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:CSCO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:CSGP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:CSX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:CTAS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:CTSH | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:DASH | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 15%) | 미평가(Q 없음) | 불가((b) 미달) |
| NASDAQ:DDOG | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 15%) | 통과 | 불가((b) 미달) |
| NASDAQ:DLTR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:DPZ | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:DXCM | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 30%) | 통과 | 불가((b) 미달) |
| NASDAQ:EBAY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:ECHO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:EQIX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:EVRG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:EXC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:EXE | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 완비 | 예 | 아니오(최대 40%) | 통과 | 불가((b) 미달) |
| NASDAQ:EXPE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:FANG | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 제외(Q≤30) | 불가((b) 미달) |
| NASDAQ:FAST | S2 V 계산 가능 | — | 결측: EBIT/주 이력 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:FFIV | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:FISV | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:FLEX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:FOX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:FOXA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:FSLR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:FTNT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:GEHC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:GEN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:GILD | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:GOOG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:GOOGL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:HAS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:HON | S2 V 계산 가능 | — | 결측: EBIT/주 이력 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:HSIC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:HST | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 통과 | 불가((b) 미달) |
| NASDAQ:IDXX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:INCY | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 30%) | 통과 | 불가((b) 미달) |
| NASDAQ:INTC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:INTU | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:ISRG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:JBHT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:JKHY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:KDP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:KLAC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:KMB | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:LIN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:LITE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:LNT | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:LRCX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:LULU | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:MAR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:MCHP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:MDLZ | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:META | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:MNST | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:MPWR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:MRNA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:MRVL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:MSFT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:MU | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:NDSN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:NFLX | S2 V 계산 가능 | — | 결측: EBIT/주 이력 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:NTAP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:NVDA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:NWS | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← EBIT_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 미평가(Q 없음) | 불가((b) 미달) |
| NASDAQ:NWSA | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← EBIT_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 미평가(Q 없음) | 불가((b) 미달) |
| NASDAQ:NXPI | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:ODFL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:ON | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:ORLY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:PANW | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 30%) | 통과 | 불가((b) 미달) |
| NASDAQ:PAYX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:PCAR | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: EBIT, 현금, EBIT/주 이력 | 예 | 아니오(최대 15%) | 제외(Q≤30) | 불가((b) 미달) |
| NASDAQ:PEP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:PLTR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:PODD | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:PSKY | S2 V 계산 가능 | — | 결측: EBIT/주 이력, 3년 매출 CAGR | 예 | 예 | 제외(Q≤30) | 불가(G 없음) |
| NASDAQ:PTC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:PYPL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:QCOM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:REG | S0 GENERAL | SHARES_NOT_AVAILABLE | 결측: FCF, 희석 주식수, EBIT/주 이력 | 아니오 | 아니오 | 통과 | 불가((b) 미달) |
| NASDAQ:REGN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:ROP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:ROST | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 완비 | 예 | 아니오(최대 40%) | 통과 | 불가((b) 미달) |
| NASDAQ:SBAC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:SBUX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:SMCI | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 0%) | 제외(Q≤30) | 불가((b) 미달) |
| NASDAQ:SNDK | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:SNPS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:STLD | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:STX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:SWKS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:TECH | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:TER | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:TMUS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:TRMB | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:TSCO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:TSLA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:TTD | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 30%) | 통과 | 불가((b) 미달) |
| NASDAQ:TTWO | S0 GENERAL | SHARES_NOT_AVAILABLE | 결측: 희석 주식수 | 아니오 | 아니오 | 제외(Q≤30) | 불가((b) 미달) |
| NASDAQ:TXN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:UAL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:ULTA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:VRSK | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:VRSN | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 30%) | 통과 | 불가((b) 미달) |
| NASDAQ:VRTX | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 30%) | 통과 | 불가((b) 미달) |
| NASDAQ:VTRS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:WBD | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:WDAY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:WDC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:WMT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NASDAQ:WYNN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:XEL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NASDAQ:ZBRA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:A | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ABBV | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ABT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ACN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ADM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:AEE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:AES | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 15%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:ALB | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:ALLE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:AMCR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:AME | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:AMT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ANET | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:AOS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:APD | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:APH | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:APTV | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:ARE | S0 GENERAL | EBIT_AND_FCF_NOT_AVAILABLE (+(b) EBIT_FCF_NOT_AVAILABLE) | 결측: EBIT, FCF, EBIT/주 이력 | 아니오 | 아니오(최대 0%) | 미평가(Q 없음) | 불가((b) 미달) |
| NYSE:ATO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:AVY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:AWK | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:AZO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:BA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:BALL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:BAX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:BBY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:BDX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:BF.B | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:BG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:BLDR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:BMY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:BR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:BSX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:BXP | S0 GENERAL | EBIT_AND_FCF_NOT_AVAILABLE (+(b) EBIT_FCF_NOT_AVAILABLE) | 결측: EBIT, FCF, EBIT/주 이력 | 아니오 | 아니오(최대 0%) | 통과 | 불가((b) 미달) |
| NYSE:CAH | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CARR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:CAT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CBRE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CCI | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CCL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:CF | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CHD | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CIEN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CLX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CMG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CMI | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CMS | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:CNP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:COHR | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 결측: EBIT | 예 | 아니오(최대 25%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:COP | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 통과 | 불가((b) 미달) |
| NYSE:COR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CPAY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CPT | S0 GENERAL | EBIT_AND_FCF_NOT_AVAILABLE (+(b) NORMALIZED_EARNINGS_FCF_NOT_AVAILABLE) | 결측: EBIT, FCF, EBIT/주 이력 | 아니오 | 아니오(최대 0%) | 통과 | 불가((b) 미달) |
| NYSE:CRH | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CRL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:CRM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CTVA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:CVNA | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 결측: EBIT/주 이력 | 예 | 아니오(최대 40%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:CVS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:CVX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:D | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:DAL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:DD | S2 V 계산 가능 | — | 결측: EBIT/주 이력 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:DE | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 15%) | 통과 | 불가((b) 미달) |
| NYSE:DECK | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 30%) | 통과 | 불가((b) 미달) |
| NYSE:DELL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:DG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:DGX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:DHI | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: EBIT, 총부채, EBIT/주 이력 | 예 | 아니오(최대 15%) | 통과 | 불가((b) 미달) |
| NYSE:DHR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:DIS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:DLR | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: FCF, 총부채 | 예 | 아니오(최대 15%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:DOC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:DOV | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:DOW | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:DRI | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:DTE | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 통과 | 불가((b) 미달) |
| NYSE:DUK | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:DVA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:DVN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ECL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ED | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:EFX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:EIX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:EL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:EME | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 15%) | 통과 | 불가((b) 미달) |
| NYSE:EMR | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 통과 | 불가((b) 미달) |
| NYSE:EOG | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 통과 | 불가((b) 미달) |
| NYSE:EQT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:ES | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ESS | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ETN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ETR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:EW | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:EXPD | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 15%) | 미평가(Q 없음) | 불가((b) 미달) |
| NYSE:EXR | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 30%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:F | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 15%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:FCX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:FDS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:FDX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:FDXF | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 결측: 3년 매출 CAGR | 예 | 아니오(최대 25%) | 통과 | 불가((b) 미달) |
| NYSE:FE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:FERG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:FICO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:FIS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:FIX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:FRT | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:FTV | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:GD | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:GDDY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:GE | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 미평가(Q 없음) | 불가((b) 미달) |
| NYSE:GEV | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:GIS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:GLW | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:GM | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 15%) | 미평가(Q 없음) | 불가((b) 미달) |
| NYSE:GNRC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:GPC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:GPN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:GRMN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:GWW | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:HAL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:HCA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:HD | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:HII | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:HLT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:HPE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:HPQ | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:HRL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:HSY | S0 GENERAL | SHARES_NOT_AVAILABLE | 결측: 희석 주식수, EBIT/주 이력 | 아니오 | 아니오 | 통과 | 불가((b) 미달) |
| NYSE:HUBB | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:HWM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:IBM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:IEX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:IFF | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:INVH | S0 GENERAL | EBIT_AND_FCF_NOT_AVAILABLE (+(b) NORMALIZED_EARNINGS_FCF_NOT_AVAILABLE) | 결측: EBIT, FCF, EBIT/주 이력 | 아니오 | 아니오(최대 0%) | 미평가(Q 없음) | 불가((b) 미달) |
| NYSE:IP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:IQV | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:IR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:IRM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:IT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ITW | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:J | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:JBL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:JCI | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← EBIT_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:JNJ | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:KEYS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:KHC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:KIM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:KMI | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:KO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:KR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:KVUE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:LDOS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:LEN | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 미평가(Q 없음) | 불가((b) 미달) |
| NYSE:LH | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:LHX | S2 V 계산 가능 | — | 결측: 3년 매출 CAGR | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:LII | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:LLY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:LMT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:LOW | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:LUV | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:LVS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:LYB | S0 GENERAL | SHARES_NOT_AVAILABLE | 결측: 희석 주식수, EBIT/주 이력 | 아니오 | 아니오 | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:LYV | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MAA | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: FCF, 총부채 | 예 | 아니오(최대 15%) | 통과 | 불가((b) 미달) |
| NYSE:MAS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MCD | S0 GENERAL | SHARES_NOT_AVAILABLE | 결측: 희석 주식수, EBIT/주 이력 | 아니오 | 아니오 | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:MCK | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MCO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MDT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MGM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MKC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MLM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:MMM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:MO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MOS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:MPC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MRK | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MSCI | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MSI | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:MTD | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:NCLH | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:NEE | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:NEM | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 미평가(Q 없음) | 불가((b) 미달) |
| NYSE:NI | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:NKE | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← EBIT_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 통과 | 불가((b) 미달) |
| NYSE:NOC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:NOW | S2 V 계산 가능 | — | 결측: EBIT/주 이력 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:NRG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:NSC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:NUE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:NVR | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 미평가(Q 없음) | 불가((b) 미달) |
| NYSE:O | S0 GENERAL | EBIT_AND_FCF_NOT_AVAILABLE (+(b) NORMALIZED_EARNINGS_FCF_NOT_AVAILABLE) | 결측: EBIT, FCF | 아니오 | 아니오(최대 0%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:OKE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:OMC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:ORCL | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: 총부채 | 예 | 아니오(최대 15%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:OTIS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:OXY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:PCG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:PEG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:PFE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:PG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:PH | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:PHM | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 미평가(Q 없음) | 불가((b) 미달) |
| NYSE:PKG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:PLD | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:PM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:PNR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:PNW | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:PPG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:PPL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:PSA | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:PSX | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:PWR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:Q | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 결측: EBIT/주 이력, 3년 매출 CAGR | 예 | 아니오(최대 25%) | 통과 | 불가((b) 미달) |
| NYSE:RCL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:RDDT | S2 V 계산 가능 | — | 결측: EBIT/주 이력 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:RL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:RMD | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ROK | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ROL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:RSG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:RTX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:RVTY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:SHW | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:SJM | S0 GENERAL | SHARES_NOT_AVAILABLE | 결측: 희석 주식수, EBIT/주 이력 | 아니오 | 아니오 | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:SLB | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:SNA | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:SO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:SOLV | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:SPG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:SPGI | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:SRE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:STE | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:STZ | S0 GENERAL | SHARES_NOT_AVAILABLE | 결측: 희석 주식수, EBIT/주 이력 | 아니오 | 아니오 | 통과 | 불가((b) 미달) |
| NYSE:SW | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← NORMALIZED_EARNINGS_NOT_AVAILABLE | 완비 | 예 | 아니오(최대 40%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:SWK | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:SYK | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:SYY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:T | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:TAP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:TDG | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:TDY | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:TEL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:TGT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:TJX | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:TKO | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:TMO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:TPL | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← DEBT_CASH_NOT_AVAILABLE | 결측: FCF, 총부채, EBIT/주 이력 | 예 | 아니오(최대 0%) | 통과 | 불가((b) 미달) |
| NYSE:TPR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:TRGP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:TSN | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:TT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:TXT | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← EBIT_NOT_AVAILABLE | 결측: EBIT, EBIT/주 이력 | 예 | 아니오(최대 40%) | 미평가(Q 없음) | 불가((b) 미달) |
| NYSE:TYL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:UBER | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:UDR | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:UHS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:UNP | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:UPS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:URI | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:V | S0 GENERAL | SHARES_NOT_AVAILABLE | 결측: 희석 주식수, EBIT/주 이력 | 아니오 | 아니오 | 통과 | 불가((b) 미달) |
| NYSE:VEEV | S2 V 계산 가능 | — | 결측: FCF | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:VICI | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 통과 | 불가((b) 미달) |
| NYSE:VLO | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 통과 | 불가((b) 미달) |
| NYSE:VLTO | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:VMC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:VMRK | S2 V 계산 가능 | — | 결측: FCF, 3년 매출 CAGR | 예 | 예 | 통과 | 불가(G 없음) |
| NYSE:VRT | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:VST | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:VTR | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:VZ | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:WAB | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:WAT | S0 GENERAL | SHARES_NOT_AVAILABLE | 결측: 희석 주식수 | 아니오 | 아니오 | 통과 | 불가((b) 미달) |
| NYSE:WEC | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:WELL | S0 GENERAL | EBIT_AND_FCF_NOT_AVAILABLE (+(b) EBIT_FCF_NOT_AVAILABLE) | 결측: EBIT, FCF | 아니오 | 아니오(최대 0%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:WM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:WMB | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:WSM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:WST | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:WY | S1 공개 입력 상한 | AXIS_WEIGHT_BELOW_50 ← FCF_NOT_AVAILABLE | 결측: FCF | 예 | 아니오(최대 45%) | 제외(Q≤30) | 불가((b) 미달) |
| NYSE:XYL | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:XYZ | S2 V 계산 가능 | — | 완비 | 예 | 예 | 제외(Q≤30) | 가격 필요 · 미판정 |
| NYSE:YUM | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ZBH | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
| NYSE:ZTS | S2 V 계산 가능 | — | 완비 | 예 | 예 | 통과 | 가격 필요 · 미판정 |
