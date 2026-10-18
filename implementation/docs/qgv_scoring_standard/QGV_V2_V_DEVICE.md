# QGV v2 기기 V·종합 점수 — 구현 정의 (PROVISIONAL)

근거: [QGV v2 후보안](QGV_V2_CANDIDATE.md) 기본 비중 그대로(조정 없음, Holdout 미사용), GSQ-022(2026-10-13 사용자 승인). 계산 위치는 기기 RAM이다. 가격·시가총액·EV·V 점수·순위는 공개 파일·저장소·로그·커밋 fixture(합성 제외)에 남기지 않는다. 결측은 NOT_AVAILABLE이며 0으로 채우지 않는다.

- Python 참조: `qgv/qgv_v2.py` · JS: `web_assets/qgv-v2.js` · 대조 벡터: `tests/fixtures/qgv_v2_vectors_v1.json`(`tools/qgv_v2_reference.py --write|--check`, `tools/qgv_v2_node_test.js`).
- 점수 접근자: `web_assets/qgv-scores.js`(QgvScores) · 설정: `web_assets/scoring-default.js`.

## 1. 입력

| 입력 | 출처 |
|---|---|
| Q·G 요인 10개 점수와 Q·G 축 점수, SIC 업종군, FINANCIAL 프로필, `v_inputs_v2` | 공개 `sec-qgv2.json`(가격 없음, Q·G 쪽 Actions 산출, §6) |
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
- **유형 소속도의 출처(TYPE-SCOPE, 소유자 지시 2026-10-17):** 점수를 매기는 모든 행(Universe 코드와 TARGET 행 똑같이)이 자기 `sec-qgv2.json` 행의 공개 `metrics`에서 같은 승인 규칙으로 소속도를 얻는다(`QgvV2.pricefreeMemberships` = `qgv_v2.pricefree_memberships`). 지금 계산하는 규칙은 type_config/1의 가격 불필요 램프 하나뿐이다: 성장 = `revenue_cagr_3y` 0.10→0.20. 미정 규칙(가치·우량·경기민감·경기방어)과 가격이 필요한 규칙(배당 `dividend_yield`, 주도 `sector_marketcap_rank`)은 누구에게나 null이다. TARGET 여부는 입력이 아니다. 이전에는 TARGET id만 `company-types-pricefree.json`(TARGET 전용)으로 소속도를 받아, 같은 입력의 Universe 기업은 미분류 34/33/33이었다. 그 파일은 표시용으로 남고 비중을 정하지 않는다. calc_version·type_config 버전은 바뀌지 않는다(공개 값·규칙 불변, 적용 범위만 변경). 대신 기기 점수 산정 기준에 유형 적용 범위 식별값 `TYPE_SCOPE`(`qgv2-type-scope/2026-10-17.1`, 소유자 결정 2026-10-17 4번)을 기록한다: `QgvScores` `basis.type_scope`·`profile.type_scope`, 기준 배지 "유형 범위 …". 프로필 id는 그대로다. 플레이북 성장 사실도 같은 행·같은 규칙(`QgvScores.typeMemberships`)을 쓴다. 근거·건수: [TYPE_SCOPE_20261017](../company_types/TYPE_SCOPE_20261017.md).
- 총점 = 사용 가능한 축의 가중 평균. 자료가 있는 축 비중 합이 50% 미만이면 NA.
- **가치 함정 관문(기본 켬, 토글):** Q 축 점수의 업종군 안 백분위(동업종 ≥ 8, 아니면 전체; 가격 불필요) ≤ 30이면 V를 총점에서 빼고 '가치 함정 주의'를 표시한다. 관문으로 뺀 V는 50% 판정에 영향을 주지 않는다.
- 프로필 버전 id: `qgv-v2/<preset>/gate-on|off`. 선택은 이 페이지 메모리에만 있고 저장하지 않는다.

## 5. 기본 기준 설정 (`scoring_default`)

`web_assets/scoring-default.js`의 `scoring_default:'v2'` 한 줄이 유일한 설정이다. **GSQ-022 승인에 따라 v2로 전환했으며, 실제 배포 준비일이 확인되기 전에는 `v2_since`를 null로 둔다.** 모든 소비자가 따라 바뀐다: S04 QGV 카드·S05 종합/QGV 요소 탭(`company-screen.js`), S06 리더보드(`leaderboard-screen.js`), 가상매매 리허설 판단 행·일일보고서·보고서 내보내기(`app.js` → `QgvScores.judgmentRows` → `DailyReport`). **2026-10-14 소유자 결정: 화면 점수는 QGV v2 하나뿐이다.** '임시 기본', 'v1 비교용', '[자세히] v1 참고'를 리더보드·기업 화면(S04/S05)·S13·일일보고서·내보내기에서 뺐다. 설정 값이 'v1'이어도 화면은 v2를 보이고(`QgvScores.scoringDefault()`는 항상 'v2'), 표시 행에는 v1 필드가 없다(`reference`는 항상 null, 판단 행의 `compare`도 null). v2를 계산할 수 없는 기업은 v2 NOT_AVAILABLE과 이유(`QgvScores.naText`: '산출 요인 n/전체', 'Q 축 비중 50% 미만' 등)를 보이며 v1로 대신하지 않는다. v1은 전진검증 원장 비교 기록(`tools/forward_validation_ledger.py`, 원장 화면 `forward-validation.js`)에만 남는다. 테스트: `tools/qgv_scores_node_test.js`(설정 'v1'·'v2' 모두 v2만 표시), `tools/qgv_v2_screens_browser_test.js`(390/1280).

## 6. `sec-qgv2.json` 정렬 (Q·G 쪽 `claude/qgv-v2-qg`의 실제 형태)

읽기는 Q·G 쪽 엄격 검증기 `web_assets/sec-qgv2.js`(SecQgv2.loadInputs)가 있으면 그것을 쓰고, 없으면 가벼운 구조 점검만 한다. 형태를 아는 곳은 `web_assets/qgv2-inputs.js`(Qgv2Inputs) 하나다.

- `records`(Universe 코드) + `target`(TARGET id). TARGET 행이 자료가 있으면 그 행(더 최신)을 `TARGET:<id>`로 쓰고, 아니면 티커로 Universe 코드를 찾는다. TARGET 행·같은 CIK의 두 번째 코드는 단면 백분위에 점으로 넣지 않고 단면에 대해서만 순위를 매긴다(Q·G 쪽 '자기 점 대체'와 같은 뜻, 한 CIK 한 점).
- Q·G 축 점수는 공개된 `axes.Q/G.score`(Q·G 쪽 동업종 규칙)를 그대로 쓰고, 산출 요인 n/전체는 요인 값에서 센다.
- `v_inputs_v2`: `ebit`/`fcf`는 `ttm_value`가 있으면 TTM, 없으면 `fy_value`(기간 표시 유지). `total_debt`·`cash_and_equivalents`·`diluted_shares`는 `{value, period_end}`. `ebit_per_share_history`는 `{fiscal_year_end, value}`. 실현 성장은 `revenue_cagr_3y`.
- 가격·시가총액·EV·순위 키가 있으면 읽지 않는다(fail closed).

## 7. 열린 항목

- v1 결측 재정규화는 `strategy_preview`를 쓰는 공개 전진검증 원장(Actions, 10-19 시작)의 Q·G 기록에도 그대로 적용된다(공식 `qgv.scoring._weighted`는 그대로).
- 기록 모드 가상매매 판단은 전진검증 원장 스냅샷(v1 Q·G)을 쓴다. v2 Q·G가 원장에 기록되기 전에는 리허설·보고서 행만 v2를 따른다. 기기 V 기울기 저장소(`virtual-trading-v-scores`)는 v1 V를 유지한다(v2 V는 저장하지 않음).
- 금융사 V(P/B 등) 정의: 별도 연구 대기열(RESEARCH / NOT ADOPTED, 공식 총점 대체값 없음) → [FINANCIAL_V_RESEARCH_PREP_20261018.md](FINANCIAL_V_RESEARCH_PREP_20261018.md). 프리셋 위 유형 비중 결합식(곱 방식) 확인. 동업종 최소 8·평균 순위 백분위·CIK 1점은 Q·G 쪽(`QGV_V2_QG_METHOD.md` §4)과 같다.

## 8. PLAYBOOK_V1 §13·§14 반영 (2026-10-13, 모두 v0 · UNCALIBRATED)

| 항목 | 상태 |
|---|---|
| §13-1 v1 V 조건 | 반영. 있는 요소의 V 비중 합 ≥ 50 **그리고** `fundamental_value`·`reverse_dcf` 중 하나 이상일 때만 v1 V(결측 제외·재정규화), 아니면 `V_CORE_FACTOR_MISSING`. 부분이면 'V(부분 · 반영 가중치 NN%)'. 설정 `V1_V_RULE`(`qgv/virtual_trading_signals.py` = `virtual-trading-signals.js`). V 기울기는 같은 구성 키끼리만 비교(그대로). |
| §13-2 경기민감 V | v2 반영: 경기민감 유형으로 선택된 기업의 EBIT 기반 수익률(이익 수익률·업종 대비)은 최근 매출 × 5년 평균 영업이익률(`type_config.value_basis.normalized_years`)로 계산하고 '정상화 이익 기준'으로 표시, 5년 이익률이 없으면 그 요인 NA(`NORMALIZED_EARNINGS_NOT_AVAILABLE`). 현재 `sec-qgv2.json`의 `v_inputs_v2`에는 매출·영업이익률 이력이 없어 실제로는 NA이고, 공식 경기민감 소속도도 아직 미정이다. v1(`value_basis.status = SCORING_MAPPING_UNRESOLVED`)은 공개 입력에 이력이 없어 미반영. |
| §14-3 v2 결측 | 반영(§3). §13-1은 v1에만 적용. |
| §14-4 관문 | 반영. 결과에 `value_trap_gate`(boolean)와 '가치 함정 주의'. 기본 켬·토글, 프로필 id에 포함. |
| §13-11 기본 전환 | 접근자 `QgvScores.basis()` → `{basis, label, since}`. 2026-10-14부터 basis는 항상 v2 '기본'이고, 이 기기에서 v2가 계산되기 전에는 v1 '임시 기본' 대신 v2 NOT_AVAILABLE과 이유를 표시. 전환 한 줄: `scoring-default.js`의 `{scoring_default:'v2',v2_since:'YYYY-MM-DD'}`. 전진검증 원장의 v1·v2 동시 기록·전략 버전 v2 기록은 공개 원장(Actions) 변경이라 이 브랜치에서는 미반영. |


## 9. 2026-10-13 후속 구현 (이 절이 이전 구현 상태보다 우선)

- 공개 QGV 입력에 매출(연간/TTM)과 5년 영업이익률 이력을 추가했다. 예전 필드 형태도 허용한다. 새 공개 필드와 원장 schema 2는 승인·배포 대기다.
- 승인된 플레이북 SIC 경기민감 후보는 V의 정상화 이익 기준에 연결한다. GSQ-017 유형 소속도·축 비중은 바꾸지 않는다.
- 6년 보고 매출이 있으면 5개 연간 성장률의 표준편차와 발행사 단면 백분위(0~100)를 가격 불필요 설명 값으로 공개한다. 플레이북에는 0~1로 변환해 승인한 상위 30% 경기민감 후보 규칙을 연결한다. 미달 이력은 NA, 기존 G 점수는 그대로다.
- V·관문 백분위에서 TARGET 및 복수 상장 행도 자기 CIK의 기존 점을 교체한다. 한 발행사가 두 번 들어가지 않는다.
- 전진 원장은 v2 기본과 v1 비교 Q·G를 별도 배열에 같은 거래일만 기록한다. 이전 schema 1 기록은 그대로 유지한다. V는 공개 원장에 들어가지 않는다.
- 기록 모드 실행기는 schema 2의 v2 Q·G만 사용하고, Q·G가 준비된 첫 날짜부터 시작한다. v1 저장 V를 v2와 섞지 않는다. `snapshot_basis`로 비교 기간의 버전을 확인한다.
- S13은 v2 5요인·4프리셋·관문을 기본으로 표시하고 v1은 비교용으로 둔다. PIT 과거 성과 자료가 없어 수익률/MDD는 확인 불가다.
- v2 V는 기존 승인된 기기 점수 이력 범위에서 별도 `investment.web.v2.virtual-trading-v-scores` 키에 기록한다. 현재 완료된 미국 거래일과 같은 공시 입력만 사용하고, 가격·환율·보유는 저장하지 않는다. v1과 버전·프로필·요인 구성·모집단을 섞지 않으며, 같은 구성의 실제 20거래일 전 점수가 없으면 기울기는 NA다. 백업에서 제외한다.
- 공개 품질 보고 입력은 HTTP 404였으나 현재 SEC 원문 사본 3/7 샤드로 실제 224/504 코드의 Q·G를 확인했다. 미수집 280은 NA다. [실제 부분 보고](QGV_V2_QUALITY_PARTIAL_20261013.md)와 [준비 상태](QGV_V2_READINESS_20261013.md)를 참조한다.

경기민감 자기 과거 대비는 같은 정상화 이익 기준의 과거 주당 이익 이력이 없어 `NORMALIZED_HISTORY_NOT_AVAILABLE`로 둔다. 보고 EBIT의 과거 배수를 정상화 EBIT의 현재 배수와 섞지 않는다. 다른 일반 기업의 자기 과거 대비는 기존 3개 이상 연말월 가격 규칙을 유지한다.
