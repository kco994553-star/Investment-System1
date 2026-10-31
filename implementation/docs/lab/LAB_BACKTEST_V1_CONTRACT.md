# Lab 백테스트 결과 계약 `lab-backtest-v1` (2026-10-31, 오너 확정 초안 · Main 데이터 계약)

결정: 2026-10-31 오너 지시 "[Lab 백테스트 결과 계약 lab-backtest-v1 — 확정 초안]". 개발 체계·Lab 연결 원칙은 [DEV_SYSTEM_20261031](../DEV_SYSTEM_20261031.md) 3.3절. 이 계약은 Main만 고친다. 바꿀 때는 `schema_version`을 올리고 Main·Codex 양쪽에 먼저 알린다.

## 1. 경로

- 결과 원본 경로는 기존 연구 구조(#417 `research/qgv_backtest`, #432 `bt-data-pilot-v06`)에 맞춰 Codex가 제안하고 Main이 확인한다. 임의의 새 폴더를 만들지 않는다.
- 결과 원본(비공개)과 공개용 게시 파일은 분리한다. 공개 파일은 공개권 확인 뒤 Main의 검증 경로에서만 만든다.
- 기존 `lab-results/1` 계약과의 차이·충돌은 Codex가 정리해 Main과 합의한 뒤 고정한다(5절은 Main의 현재 정리).
- **2026-10-31 상태:** Codex의 "[Lab 계약] 결과 경로 제안" Draft PR은 아직 없다. 실제 결과 경로·공개 파일은 만들지 않는다. 앱은 시험용 fixture로만 구현한다.

## 2. 구조

```json
{
  "schema_version": "lab-backtest-v1",
  "generated_at": "타임존 포함 ISO 8601",
  "source_commit": "결과 생성에 사용한 연구 코드 전체 SHA",
  "runs": [
    {
      "id": "고유 실험 ID",
      "name": "표시용 이름",
      "description": "전략 한 줄 설명",
      "run_type": "PILOT | FORMAL",
      "data_status": "REAL | SYNTHETIC | MIXED",
      "validation_status": "NOT_VALIDATED | PIT_VERIFIED | REVIEWED",
      "qgv_version": "v2",
      "universe": {
        "definition": "모집단 정의와 표본 선정 방법",
        "point_in_time": true,
        "survivorship_note": "생존·선정 편향 처리 또는 한계"
      },
      "period": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
      "rebalance": "monthly | quarterly 등",
      "benchmark": { "name": "예: SPY", "total_return": true },
      "costs": { "fee_bps": 0, "slippage_bps": 0 },
      "metrics": {
        "cagr": null, "total_return": null,
        "max_drawdown": null, "volatility": null,
        "sharpe": null,
        "benchmark_cagr": null, "excess_cagr": null
      },
      "null_reasons": { "지표명": "계산 불가 사유" },
      "equity_curve": [ { "date": "YYYY-MM", "strategy": 100, "benchmark": 100 } ],
      "limitations": [ "알려진 한계" ]
    }
  ]
}
```

(예시의 값은 형식만 보인다. `point_in_time`·`total_return`은 true/false, 지표는 숫자 또는 null.)

## 3. 지표 정의

- 수익률·변동성·낙폭은 소수 단위다(0.123 = 12.3%).
- `max_drawdown`: 음수로 저장한다(-0.25 = -25%).
- `excess_cagr`: `cagr - benchmark_cagr`(롱숏 전략 수익률 아님).
- `volatility`: 연율화 표준편차. 표본 빈도는 연구 근거에 기록한다.
- `sharpe`: 무위험금리·빈도·연율화 방식을 연구 근거에 기록한다.
- `fee_bps`·`slippage_bps`: 매수·매도 각각 한쪽 체결당 비용.
- `benchmark.total_return`: 배당 재투자 포함 여부.

## 4. 상태 의미와 규칙

- `REAL`은 실제 입력을 썼다는 뜻일 뿐 검증 완료가 아니다.
- 실자료와 합성 입력이 섞이면 `MIXED`. 가능하면 실행을 나눈다.
- `universe.point_in_time`은 모집단 시점 정합성만 뜻한다. 재무·가격·기업행사 검증 범위는 `limitations`와 연구 근거에 따로 적는다.
- `PIT_VERIFIED`·`REVIEWED`는 그 검증 근거가 실제로 있을 때만 쓴다.
- `equity_curve`: 시작 100, 날짜 오름차순·중복 없음, 전략과 비교지수는 같은 날짜. 원 가격·종목별 장부·개인 자료는 넣지 않는다.
- 계산할 수 없는 값은 null + `null_reasons`. 0이나 임의값으로 채우지 않는다.
- 결과가 없으면 `runs`는 빈 배열.

### 4.1 앱 판독기가 거부하는 것 (Main, 파일 전체 거부)

- 스키마 이름이 다름, 필수 항목 누락, 모르는 키, 형식·열거형 위반, 유한하지 않은 수.
- 날짜가 아님, `period.start >= period.end`, 곡선 날짜가 기간 밖.
- 곡선이 100에서 시작하지 않음, 날짜 순서·중복 위반, 0 이하 값.
- 지표가 null인데 `null_reasons`에 사유가 없음.
- `max_drawdown`이 양수이거나 -1보다 작음, `volatility` 음수, 비용 음수.
- `excess_cagr`가 `cagr - benchmark_cagr`와 다름.
- `total_return`·`cagr`·`benchmark_cagr`가 곡선 끝값·기간과 맞지 않음(허용 오차는 판독기 시험에 고정).
- `id` 중복.

화면 상태 문구(오너 지정):
- 결과 없음 → "연구 결과가 아직 없습니다"
- REAL + NOT_VALIDATED → "실데이터 파일럿 · 미검증"
- SYNTHETIC → "합성 데이터 · 시험용"
- MIXED → 혼합 사실을 명시
- 비공개 결과 미인증 → "비공개 연구 결과 · 로그인 필요"
- 불러오기 실패·스키마 불일치·필수 항목 누락 → 오류 상태(파일 전체 적용 거부)
- null 지표 → "–"와 `null_reasons`

## 5. `lab-results/1`(공개 게시 계약 제안, `LAB-PUBLISH` 미결정)과의 관계 — Main 정리, Codex 합의 대기

| 항목 | lab-backtest-v1 | lab-results/1 |
| --- | --- | --- |
| 역할 | 결과 원본·비공개 제공 계약(Codex 생산 → Main 검증 → 본인 인증 비공개 경로) | 공개 게시 계약(공개권 확인 뒤 Main 검증 경로만 생성) |
| 시계열 | `equity_curve`(시작 100, 월) 있음 | 숫자 배열·`nav`·`monthly`·`benchmark` 금지 |
| 자유 텍스트 | `name`·`description`·`limitations`·`null_reasons` | 금지(열거형·정규식만) |
| 상태 | `data_status`·`validation_status`·`run_type` | `quality_state`·`oos_state`·`rights_state` |
| 지표 | cagr, total_return, max_drawdown, volatility, sharpe, benchmark_cagr, excess_cagr | cagr, annualized_volatility, max_drawdown, sharpe, annual_turnover_mean, sample_months (`{value, na_reason}`) |
| 식별자 | 자유 `id` | 사전등록 레지스트리 ID만 |

- 정리: 두 계약은 충돌하지 않게 역할을 나눈다. lab-backtest-v1의 곡선·자유 텍스트는 공개되지 않는다.
- 공개가 승인되면 Main의 검증 경로가 lab-backtest-v1에서 lab-results/1 형식의 집계만 만든다(필드 대응표는 Codex 제안 뒤 고정).
- 이름이 다른 지표(volatility ↔ annualized_volatility)와 한쪽에만 있는 지표의 대응은 Codex 제안을 기다린다.
- 공개 가드 규칙(`LAB-GUARD-KEYS`: `cost_basis`·`performance` 정규화 충돌)은 공개 게시를 승인할 때 함께 정한다.
