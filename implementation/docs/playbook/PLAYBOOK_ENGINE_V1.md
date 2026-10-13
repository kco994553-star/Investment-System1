# 플레이북 판정 엔진 v1 — 입력·출력·해석 메모

기준 문서: `PLAYBOOK_V1.md`(원문 그대로). 설정: `qgv/playbook_v1.json`(v0 · UNCALIBRATED).
엔진: `qgv/playbook.py`(Python 참조) = `web_assets/playbook-engine.js`(기기). 공통 벡터: `tests/fixtures/playbook_reference_v1.json`(합성).
화면·기록은 별도 PR이다. 이 엔진은 외부 호출·저장·주문 기능이 없는 순수 함수다.

## 1. 함수

| 함수 | 내용 |
|---|---|
| `evaluate(cfg, situation, mode='CORE_V0')` | 한 종목의 사실 → 주 코드·보조 코드·확인 항목·선택지(활성/비활성 사유)·확인 불가 목록 |
| `active_codes(cfg, mode, target_version)` | 0-1절 핵심 v0 코드(+TARGET v1 채택 후 T2·U2). `mode='ALL'`은 후보 코드까지 판정 |
| `transition(cfg, code, choice, ctx)` | 4절 전이(+3절 기준, 13-3 제안 TARGET, 13-5 분할·위기 편입 비중) |
| `criteria(cfg, code, facts, ctx)` | 3절 기준 중 기계적으로 정할 수 있는 것(R2·T1·T2·H1·R5·W2) → 해당 선택지 |
| `classify_types_v0(cfg, metrics)` | 6-2절 유형 판정(예/아니오/확인 불가) |
| `e4_level(cfg, drawdown, max_drawdown_3y, history_years, user_threshold)` | 13-6절 재평가 신호 단계 |
| `portfolio_limits(cfg, rows, cash_pct)` | 16절 한도(+합계 100%) |
| `sector_for(cfg, symbol, etf)` | 7-2절 배정 → 없으면 ETF가 하나의 묶음에만 해당할 때만 |

## 2. `situation` 입력 키 (모르는 값은 `null`; 0이나 좋은 값으로 취급하지 않음)

- 기본: `symbol`, `held`, `watched`, `basis`('v1'|'v2', 13-11), `target_version`('v1'이면 T2·U2 작동)
- 유형·업종: `memberships`{growth, value, dividend, quality, cyclical, defensive, leader}, `sector`(7-1 id)
- 데이터: `data`{price_missing, fx_missing, snapshot_missing}, `coverage`, `coverage_prev`, `qg_source_missing`(13-7)
- 사용자: `user_excluded`, `user_hold`, `invalidation_triggered`(모든 보유 종목, 0-1), `conviction`{active, invalidated, months_held, risk_review_count}, `conviction_total_pct`
- 점수: `q_now`, `q_prev`, `g_now`, `g_prev`, `v_now`, `v_prev20`, `dividend_cut`, `own_value_worsened`(14-1), `q_industry_pct`, `v_industry_pct`, `expectation_check_passed`(14-2), `value_trap_gate`(14-4, V 모듈 출력)
- 업종 대비: `excess_20`, `excess_mean_252`, `excess_sd_252`, `market_explained_ratio_60`(13-5)
- 비중: `actual_pct`, `target_pct`
- 일정·신호: `earnings_days_until`, `earnings_pending_reflection`, `type_changed`, `leaderboard_signal`, `followup_due`, `quarterly_check_due`, `post_earnings_check_due`, `leaderboard_rank`, `thirteenf_full_exit_managers`, `structural_news`
- 특수 규칙: `operating_margin_5y_position`, `q_decline_streak_quarters`, `sector_marketcap_rank`, `theme_weight_pct`, `safety_margin_pct`, `net_debt_to_ebitda`, `interest_coverage`
- 매크로: `macro_state`('NORMAL'|'WARNING'|'CRISIS'|null, 13-5 경고등 모듈 출력)

## 3. 구현 중 선택한 해석 (문서는 바꾸지 않음)

각 항목은 아래 4절 "모순·빠진 부분"과 짝을 이룬다. 결정이 나면 설정 값이나 엔진 한 곳만 바꾸면 된다.

- 핵심 v0 밖의 코드는 계산하되 판정에 넣지 않고 `candidate_signals`에 남긴다(2027-02 점검에서 "실제 사례" 수를 세기 위해).
- "해당 유형" = 소속 점수 ≥ `type_config/1 mixing.minimum_membership`(0.3).
- "Q·G 유지" = 해당 유형의 R2 조건이 하나도 걸리지 않고 모두 확인 가능.
- R2 기준 3절 순서: 앞 기준을 확인할 수 없으면 뒤 기준으로 넘어가지 않는다.
- 판정 핵심 항목이 확인 불가이거나 특수 규칙 입력이 확인 불가이면 확대·편입 선택지를 끈다(5절, 0절-6).
- 위기 중 편입은 U3 조건 2~5가 모두 참일 때만 켠다. W2 체크리스트 5개는 `criteria('W2')`가 판정한다.

## 4. 모순·빠진 부분 (결정 필요 목록은 PR 본문과 보고에 번호로)

1. 8절 "무효화 조건 발생 시 R1로 자동 해제" ↔ 3절 R1 "공시로 확인 → 확신 해제, 뉴스로만 → 7일 확인". 현재: 공시 확인(R1_FILING) 때만 해제.
2. 1절 H2 "12개월 경과" ↔ 8·12절 "12개월 또는 위험재검토 2회". 현재: 둘 다.
3. 1절 R1 "확신 보유 종목" ↔ 0-1절 "모든 보유 종목". 현재: 0-1절.
4. '주도' 유형은 6-1 기준값 행과 6-3 동률 순서에 없다. 현재: 기준값은 기본(유형 불명)을 쓰고 6-4 주도 규칙만 적용.
5. 유형 소속 기준(몇 점부터 "해당 유형")이 없다. 현재: type_config 최소 소속 0.3.
6. R2 Q·G 하락의 비교 기간이 없다(V는 20세션). 현재: 호출하는 쪽이 넘긴 전·후 값.
7. 우량 유형은 R2가 Q 단독 3점뿐이라 "Q·G 유지" 정의가 모호. 현재: R2 조건 미발동.
8. 복수 유형일 때 T1의 V 임계는 6-3에 없다(확대만 "가장 엄격"). 현재: 주 유형 값.
9. T2 "V 변화 임계 미만"의 방향. 현재: 20세션 V 변화의 절댓값 < 주 유형 V 임계.
10. R2 일회성 "해당 유형 R2 임계의 절반"이 복수 유형·우량(Q 단독)일 때 모호. 현재: 해당 지표 임계 중 가장 작은 값.
11. W1(관심 종목)은 0-1절의 핵심·후보 어디에도 없다. 현재: 꺼짐(UNLISTED).
12. U3 조건 5는 "{유형} V 임계"를 쓰지만 0-1절은 R2 외 유형 열을 후보로 둔다. 현재: 설정 값 사용.
13. v2에서 "상대적 하락"은 E4로 보내는데 E4는 후보 코드. 현재: 핵심 모드에서는 화면 코드 없이 `candidate_signals`에만 남음.
14. 위기에서 U1(주 코드, 코드 순서)과 U3(보조)가 함께 뜨면 주 플레이북은 U1이고 U1 확대는 꺼진다. 현재: U1이 후보라 핵심 모드에서는 U3가 주 코드. 전체 모드는 `choices_by_code`로 U3 선택지를 따로 제공.
15. 매크로 상태를 전혀 모를 때(경고등 0/5)의 처리. 현재: 확대 제한 없음, U3 불가.
16. E4 이유 코드는 1절에 REASSESS_SIGNAL 하나뿐. 현재: 원인 코드 추가(QG_RELATIVE_DECLINE, QG_RELATIVE_DECLINE_UNVERIFIED, THIRTEENF_FULL_EXIT, STRUCTURAL_NEWS).
17. 13-6 "관찰" 단계는 1절 E4 진입 조건(NEAR_TRIGGER·REASSESS)에 없다. 현재: OBSERVE는 E4를 띄우지 않음.
18. 6-2 "경기민감 후보"·"경기방어 후보" 업종군이 정의되지 않았다. 현재: 확인 불가. "5년 매출 변동성" = 연 매출 성장률의 5년 표준편차, 504 안 순위.
19. 6-2 "5년 영업이익률 변동" = 최대 − 최소(%p)로 계산. 19종목 중 우량 조건을 모두 통과한 종목이 없다(MSFT 5.0%p).
20. XLI·SMH는 7-1의 여러 하위 묶음에 걸친다. 19종목 밖은 하위 묶음을 정할 규칙이 없다. 현재: ETF_AMBIGUOUS.
21. 3절 U 제목 "▼ 신호가 있으면 진입 불가" ↔ 2절 "▲ 행동 비활성". 현재: ▲ 코드는 보조 칩으로 남기고 확대 선택지만 끔.
22. 4절 T1 전이에 3절의 "목표 −1%p" 경로가 없다. 현재: 3절에서 추가(source '3').
23. U2에 안전마진 조건이 있는지 불명확. 현재: U1과 W2만 안전마진(v2는 V 백분위·기대 점검)으로 막음.
24. 13-7 "실적 발표 후 H1 필수"는 1절 H1 "신호 없음" 조건과 충돌. 현재: Q·G 없는 종목은 실적 후 H1을 다른 코드와 함께 띄움.
25. 기존 가상매매 엔진 이유 코드(USER_EXCLUDE, COVERAGE_WORSENED, DATA_PRICE_MISSING…)와 1절 이유 코드(USER_EXCLUDED, COVERAGE_DEGRADED, PRICE_MISSING…)가 다르다. 현재: 플레이북은 1절 코드, 가상매매 엔진은 그대로.
26. 14-4 "Q가 업종 내 하위 30%"의 경계(30 포함 여부). 현재: V 모듈의 `value_trap_gate` 값을 그대로 받음.

## 5. 2026-10-13 2차 결정 반영

4절의 26개 항목은 모두 결정됨이다. §17이 우선하며 기존 원문은 보존했다. `q_prev/g_prev`는 직전 분기이고 `q_prev2/g_prev2`는 2분기 전이다. 2분기 비교가 없으면 해당 비교만 확인 불가로 두며 소급 스냅샷을 만들지 않는다. 우량 유지 조건은 Q < 3·G < 5 하락, 분류는 5년 영업이익률 표준편차 < 3%p다. `sic` 입력으로 후보 업종·하위 묶음을 정한다. `macro_available_count=0`이면 상태 입력이 있더라도 매크로 확인 불가로 처리한다.

W1·E4는 핵심이며 E4 선택지는 항상 비어 있다. E4 원인은 `REASSESS_SIGNAL`, `QG_RELATIVE_DECLINE`, `QG_RELATIVE_DECLINE_UNVERIFIED`, `THIRTEENF_FULL_EXIT`, `STRUCTURAL_NEWS`로 유지한다. 이유 코드는 엔진별로 보존한다.

| 가상매매 이유 코드 | 플레이북 이유 코드 | 대응 |
|---|---|---|
| DATA_PRICE_MISSING | PRICE_MISSING | X1 가격 결측 |
| DATA_FX_MISSING | FX_MISSING | X1 환율 결측 |
| DATA_SNAPSHOT_MISSING | SNAPSHOT_MISSING | X1 스냅샷 결측 |
| USER_EXCLUDE | USER_EXCLUDED | X3 제외 |
| COVERAGE_WORSENED | COVERAGE_DEGRADED | R4 품질 하락 |
| USER_HOLD | USER_HOLD | R5 보류 |
| QG_DECLINE | QG_DECLINE | R2 분기 하락 |
| FOLLOWUP_DUE | FOLLOWUP_DUE | E5 확인일 도래 |

화면·저장은 `playbook-screen.js`의 기기 저장소만 사용한다. 기록·산 이유·보류·제안 TARGET을 백업 /4에 포함하며 이전 /1~ /3은 기록 원본을 보존한다. 가격이나 수익률 시계열은 백업에 넣지 않는다. 채점은 기기 RAM에 입력된 실제 종가 자료로만 계산하며 자료 없으면 NA다. TARGET v1은 A의 v2가 준비되기 전 최종 저장을 비활성으로 둔다.
