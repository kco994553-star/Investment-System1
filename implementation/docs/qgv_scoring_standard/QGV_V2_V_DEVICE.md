# QGV v2 기기 V·종합 점수 — 구현 정의 (PROVISIONAL)

근거: [QGV v2 후보안](QGV_V2_CANDIDATE.md) 기본 비중 그대로(조정 없음, Holdout 미사용), GSQ-022(2026-10-13, 승인 대기). 계산 위치는 기기 RAM이다. 가격·시가총액·EV·V 점수·순위는 공개 파일·저장소·로그·커밋 fixture(합성 제외)에 남기지 않는다. 결측은 NOT_AVAILABLE이며 0으로 채우지 않는다.

- Python 참조: `qgv/qgv_v2.py` · JS: `web_assets/qgv-v2.js` · 대조 벡터: `tests/fixtures/qgv_v2_vectors_v1.json`(`tools/qgv_v2_reference.py --write|--check`, `tools/qgv_v2_node_test.js`).
- 점수 접근자: `web_assets/qgv-scores.js`(QgvScores) · 설정: `web_assets/scoring-default.js`.

## 1. 입력

| 입력 | 출처 |
|---|---|
| Q·G 요인 10개 점수, SIC 업종군, FINANCIAL 프로필, `v_inputs_v2` | 공개 `sec-qgv2.json`(가격 없음, Q·G 쪽 Actions 산출) |
| 현재가 | 기기 전용: ① Universe 탭 읽기(`PrivateSubsetView.prices()`, 시트 C열 가격) ② 기기 시세(`DeviceValuation.deviceQuote` = 수동·시트 Quotes·Worker 종가) |
| 월말 종가 | 기기 전용: 사용자 시트 Prices 탭 모듈 `PriceStore.monthEndCloses(symbol) -> {YYYY-MM: close}`(없으면 자기 과거 대비 NA) |

**시가총액 결정:** 시가총액 = 기기 현재가 × SEC 희석 주식수(`v_inputs_v2.diluted_shares`). Universe 탭의 marketcap 열은 쓰지 않는다. 이유: (1) 주당 재무와 같은 기준이라 자기 과거 대비(주당) 배수와 일관, (2) TARGET 기기 시세(Quotes·Worker 종가)처럼 가격만 있는 출처에도 같은 규칙 적용, (3) GOOGLEFINANCE marketcap의 주식 종류 합산 불일치(M3 MISMATCH 사례) 회피. 다중 종류 상장사는 한 종류 가격 × 회사 전체 희석 주식수(GSQ M3 Alphabet 규칙과 같은 근사).

## 2. V 요인 (비중 25/25/20/15/15)

| id | 정의 | 백분위 모집단 |
|---|---|---|
| `v_earnings_yield` | EBIT / EV | 이 기기에서 가격이 있는 Universe504 행 전체 |
| `v_fcf_yield` | FCF / EV, FCF = 영업현금흐름 − 설비투자 | 같은 전체 |
| `v_vs_industry` | EBIT/EV(= EV/EBIT 배수의 역수)의 SIC 업종군 안 백분위 | 업종군(가격 있는 동업종 ≥ 8), 미만이거나 업종군 없음 → 전체(`UNIVERSE_FALLBACK`) |
| `v_vs_own_history` | 현재 주당 EBIT / 현재가 를 과거 각 회계연도 말월(`YYYY-MM`)의 주당 EBIT / 월말 종가들과 비교한 자기 백분위(높을수록 과거보다 쌈) | 자기 과거(≥ 3개) + 현재 |
| `v_expectation_check` | 역DCF 내재 성장률(FCF/주, `dcf_parameters/v1.1-default`, 기존 역DCF 해법) − 실현 매출 성장(3년 CAGR). 낮을수록 좋음 → −차이의 백분위 | 전체 |

- EV = 현재가 × 희석 주식수 + 총부채 − 현금. EV ≤ 0 → `EV_NON_POSITIVE`. 수익률은 음수 EBIT/FCF도 그대로 순서에 반영한다.
- 백분위: 중간 순위 `100 × (작은 수 + 0.5 × (같은 수 − 1)) / (n − 1)`, 0~100. 모집단 < 8 → `CROSS_SECTION_TOO_SMALL`.
- 통화가 가격과 다르면 `CURRENCY_BASIS_UNCONFIRMED`(환산 없음). 가격 없음 `NO_DEVICE_PRICE`, 입력 없음 `V_INPUTS_NOT_AVAILABLE`, 월말 종가 없음 `PRICE_HISTORY_NOT_AVAILABLE`, 3개 미만 `HISTORY_TOO_SHORT`, 역DCF 실패는 해법 사유(`NON_POSITIVE_CASHFLOW`, `ROOT_NOT_BRACKETED` 등).
- **DCF 값은 점수가 아니다.** '참고 범위'로만 표시: FCF/주로 성장률 규칙 하한(0%)~상한(15%)의 2단계 DCF(가격 미사용).
- 테마 프리미엄 없음.
- **금융사(FINANCIAL):** 공개 입력에 P/B·ROE 기반 V 정의가 아직 없어 V 요인 전부 `FINANCIAL_PROFILE_V_NOT_DEFINED`(NA). Q·G는 공개 파일 그대로.

## 3. 축·결측 규칙 (v1·v2 공통, 사용자 결정 2026-10-13)

계산된 요인만 원래 비중 비율로 재정규화한다. 축 비중의 50% 이상이 계산될 때만 축 점수를 내고, 미만이면 NA다. 화면·내보내기에 '산출 요인 n/전체'를 표시한다. v1 미리보기(`qgv/strategy_preview.py`, `EnginePreview.strategy`)도 같은 규칙으로 바뀌었다(이전 '고정 규칙'의 결측 비중 미재분배 폐지, NA는 coverage `BLOCKED`).

## 4. 종합·관문·프로필

- 축 비중 = 프리셋(§5: 균형 34/33/33 기본, 우량 중심 50/25/25, 성장 친화 30/50/20, 가치 25/20/55) 위에 GSQ-017 유형 비중을 적용: `w_p ∝ 프리셋_p × 유형_p / 미분류_p`(미분류 34/33/33). 균형 프리셋이면 GSQ-017 유형 비중과 정확히 같다. 유형 소속도가 없으면 미분류(=프리셋 그대로).
- 총점 = 사용 가능한 축의 가중 평균. 자료가 있는 축 비중 합이 50% 미만이면 NA.
- **가치 함정 관문(기본 켬, 토글):** Q 축 점수의 업종군 안 백분위(동업종 ≥ 8, 아니면 전체; 가격 불필요) < 30이면 V를 총점에서 빼고 '가치 함정 주의'를 표시한다. 관문으로 뺀 V는 50% 판정에 영향을 주지 않는다.
- 프로필 버전 id: `qgv-v2/<preset>/gate-on|off`. 선택은 이 페이지 메모리에만 있고 저장하지 않는다.

## 5. 기본 기준 설정 (`scoring_default`)

`web_assets/scoring-default.js`의 `scoring_default:'v1'` 한 줄이 유일한 설정이다. **GSQ-022 승인 후 이 한 줄을 `'v2'`로 바꾸면** 모든 소비자가 따라 바뀐다: S04 QGV 카드·S05 종합/QGV 요소 탭(`company-screen.js`), S06 리더보드(`leaderboard-screen.js`), 가상매매 리허설 판단 행·일일보고서·보고서 내보내기(`app.js` → `QgvScores.judgmentRows` → `DailyReport`). v1이 기본이면 v2는 '비교용', v2가 기본이면 v1(재정규화)은 [자세히]에만 보인다. 테스트: `tools/qgv_scores_node_test.js`(설정을 뒤집어 모든 소비자 확인), `tools/qgv_v2_screens_browser_test.js`(390/1440, v1·v2).

## 6. `sec-qgv2.json` 가정 형태 (Q·G 쪽 병합 전, 읽기 어댑터 `web_assets/sec-qgv2.js`만 바꾸면 됨)

```text
{kind: "SEC_QGV2", as_of, config_version, method_status,
 records: {"NASDAQ:XXXX": {state, sic, industry_group, profile: GENERAL|FINANCIAL,
   factors: {q_*/g_*: 0..100 | {score} | null},
   v_inputs_v2: {currency, ebit, ocf, capex | fcf, total_debt, cash, diluted_shares,   // 숫자 또는 {value, period_end|period_label}
                 ebit_per_share_history: [{period_end, value}], revenue_cagr_3y}}}}
```

가격·시가총액·EV·순위 키가 있으면 읽지 않는다(fail closed).

## 7. 열린 항목

- 기록 모드 가상매매 판단은 전진검증 원장 스냅샷(v1 Q·G)을 쓴다. v2 Q·G가 원장에 기록되기 전에는 리허설·보고서 행만 v2를 따른다. 기기 V 기울기 저장소(`virtual-trading-v-scores`)는 v1 V를 유지한다(v2 V는 저장하지 않음).
- 금융사 V(P/B 등) 정의, 프리셋 위 유형 비중 결합식(곱 방식) 확인, 업종군 최소 동업종 수 8의 Q·G 쪽 규칙과의 일치.
