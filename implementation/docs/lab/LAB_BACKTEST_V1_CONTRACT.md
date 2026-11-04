# Lab 백테스트 결과 계약 `lab-backtest-v1` (2026-10-31, 오너 확정 초안 · Main 데이터 계약)

결정: 2026-10-31 오너 지시 "[Lab 백테스트 결과 계약 lab-backtest-v1 — 확정 초안]". 개발 체계·Lab 연결 원칙은 [DEV_SYSTEM_20261031](../DEV_SYSTEM_20261031.md) 3.3절. 이 계약은 Main만 고친다. 바꿀 때는 `schema_version`을 올리고 Main·Codex 양쪽에 먼저 알린다.

## 1. 경로

- 결과 원본 경로는 기존 연구 구조(#417 `research/qgv_backtest`, #432 `bt-data-pilot-v06`)에 맞춰 Codex가 제안하고 Main이 확인한다. 임의의 새 폴더를 만들지 않는다.
- 결과 원본(비공개)과 공개용 게시 파일은 분리한다. 공개 파일은 공개권 확인 뒤 Main의 검증 경로에서만 만든다.
- 기존 `lab-results/1` 계약과의 차이·충돌은 Codex가 정리해 Main과 합의한 뒤 고정한다(5절은 Main의 현재 정리).
- **2026-10-31 상태:** Codex의 "[Lab 계약] 결과 경로 제안" Draft PR [#437](https://github.com/kco994553-star/Investment-System1/pull/437)(#432 위)이 열렸다. Main 검토는 6절. 정식 비공개 경로는 #436 구현과 함께 정한다. 그 전까지 공개 파일·실제 결과 경로는 만들지 않고, 앱은 시험용 fixture로만 구현한다.

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

## 6. Codex 제안 #437 검토 (Main, 2026-10-31)

#437(`6c285ada`)의 `LAB_CONTRACT_PROPOSAL_20261031.md`를 읽고 확인했다. **확정한 것:**

| 항목 | 확정 |
| --- | --- |
| 두 계약의 관계 | lab-backtest-v1 = 연구 결과 원본·비공개 제공 계약. lab-results/1 = 별도 공개 투영(공개권 확인 뒤 Main의 허용목록 변환·검증 경로만 생성). 공개 계약을 대체하지 않는다. 자동 변환·버전 변경 없음 |
| 월별 곡선 날짜 | 첫 점 = `period.start`가 속한 달, 실제 초기 NAV 100. 중간 점 = 각 달의 마지막 확보 거래일. 마지막 점 = `period.end`가 속한 달, 실제 종료일(부분 월). 성과가 있는 실행은 곡선이 2점 이상이다. 같은 달 안에 끝나는 0이 아닌 성과는 이 형식으로 내보내지 않는다. 이 규칙을 `limitations`에 적는다. 앱 판독기는 첫 점·끝 점의 달이 기간과 맞는지 확인한다 |
| `source_commit` | 실행한 연구 코드의 전체 SHA. 외부 연구 엔진 SHA·파일 해시·입력 manifest는 비공개 evidence에 둔다 |
| NOT_VALIDATED 표시 | 화면은 "실데이터 파일럿 · 미검증". 스키마 통과는 사실 검증·PIT 인증·게시 허가가 아니다 |
| 임시 결과 위치 | Codex 비공개 작업 루트(공개 checkout 밖, 0600)의 `v-ledger-audit/results/lab-backtest-v1.candidate.json`은 **임시로만** 인정한다. 정식 위치와 앱까지의 비공개 전달은 #436(1인 비공개 구역) 구현과 함께 Main이 정한다. 공개 PR·공개 로그에 후보 파일·수치·곡선·해시를 넣지 않는다 |
| 비교 기준이 현금인 파일럿 | `benchmark.name`에 무이자 현금임을 적는다. 그때 `benchmark_cagr` 0은 실제 값이며 결측을 0으로 채운 것이 아니다 |
| 연구 측 검증기 | `lab_results.py`는 연구 측 후보 검증기다. 앱 판독기(Main, 4.1)와 별개이고 서로 대신하지 않는다 |

**Codex 회신 필요:**

1. **KIS 수집이 공개 Actions에서 돈다.**
   - 현황: #432 연구 가지의 `bt-data-pilot-kis.yml`·`bt-data-pilot-pre2016.yml`이 공개 저장소 Secrets(`KIS_APP_KEY`·`KIS_APP_SECRET`·`RAW_REPO_TOKEN`)로 KIS를 호출한다. 10/31에 각각 3회·7회 실행됐고, 마지막은 07:17 UTC다. KIS 원자료는 기존 비공개 원자료 저장소의 release에 둔다.
   - 충돌하는 오너 결정과 규칙:
     - 10/31 #436 결정: 공개 저장소·Pages·공개 Actions 로그·결과물에 KIS 자료를 넣지 않는다. KIS 키는 비공개 저장소 Secrets로 옮기고, 공개 저장소의 KIS Secrets는 지운다.
     - #436 설계 3.1: 원자료 저장소는 공개 Actions가 쥔 토큰이 전부 읽는다.
     - DC-35: 워크플로는 Main만 바꾼다.
   - 요청:
     - 공개 Actions의 KIS 실행을 멈춘다.
     - 지금까지 KIS 원자료를 둔 release 이름을 목록으로 알린다.
     - 로그에 KIS 값·종목별 값이 찍히지 않았는지 확인한다.
     - #436 승인 뒤 비공개 구역으로 옮길 계획을 낸다.
   - 오너가 공개 KIS Secrets를 지우면 이 워크플로는 멈춘다.
2. **정식 결과 위치.** "#417 승인된 비공개 출력 루트와 나란히"는 그 루트가 어디인지(저장소·release·Codex 작업 공간) 적어 달라. 앱 연결은 #436 비공개 저장 계약(Lab 결과 절)을 따른다.

## 7. `lab-backtest-v2` (Main, 2026-11-03) — 결과 종류 · 계산 상태 · 표본 · 모집단 · 진단

근거와 버전 규칙은 다음과 같다.
- 오너 11/02 "9.Lab은 기존 lab-backtest-v1 계약을 재사용하라"와 11/03 "합성 예시로 Lab 화면 작업을 진행하라".
- Main 요청 [#437 6575853507](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6575853507), Codex 회신·합의 [#437 6600537423](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6600537423), Main 수령 [#437 6601564604](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6601564604).
- 이 문서 머리의 규칙대로 `schema_version`을 올렸다.
- v1 파일은 그대로 읽는다. v1에 새 키가 있으면 `KEY_UNKNOWN`으로 거부한다.

실행(run)마다 v1 키에 다음 7개를 더한다.

| 필드 | 규칙 |
| --- | --- |
| `result_kind` | `BACKTEST` · `SINGLE_COMPANY_METRIC` · `SAMPLE_DIAGNOSTIC` |
| `computation_status` | `COMPUTED` · `NOT_COMPUTED`. 일부 지표가 계산됐으면 COMPUTED에 나머지 null 사유를 둔다. 요청 지표가 전부 미산출이면 NOT_COMPUTED |
| `not_computed_reason` | NOT_COMPUTED일 때 비어 있지 않은 글(사유 코드), COMPUTED이면 null (`NOT_COMPUTED_REASON`) |
| `as_of` | 평가일 `YYYY-MM-DD`. BACKTEST가 아니면 필수(`AS_OF_REQUIRED`), BACKTEST는 null 허용 |
| `sample` | `{unit: company\|security, n_requested: 정수\|null, n_used: 정수, selection: 글}`. 둘 다 있으면 n_used ≤ n_requested (`SAMPLE_RANGE`). 이름·티커는 넣지 않는다 |
| `population` | `{id, scope: SAMPLE\|FULL_MARKET, as_of, completeness: COMPLETE\|INCOMPLETE\|UNKNOWN, n_total: 정수\|null, null_reason}`. n_total이 null이면 사유 필수(`POPULATION_NULL_REASON`). FULL_MARKET이면서 COMPLETE가 아니면 n_total은 null(`POPULATION_INCOMPLETE`). 일부 확인 행 수를 전체 분모로 쓰지 않는다 |
| `diagnostics` | 집계만 담는다: `[{name, value, unit: count\|fraction, null_reason, n_valid, n_total, population_ref}]`. BACKTEST는 `[]` (`DIAGNOSTICS_BACKTEST`). `population_ref`는 그 실행의 `population.id`와 같아야 한다(`POPULATION_REF`). count는 0 이상 정수. fraction은 `n_total > 0`이고 `value = n_valid / n_total`일 때만 값을 둔다(`DIAGNOSTIC_FRACTION`). 값이 null이면 사유 필수, 값이 있으면 사유는 null(`NULL_REASON_UNUSED`) |

추가 규칙:
- BACKTEST가 아니거나 NOT_COMPUTED인 실행: 성과 7개는 모두 null에 사유를 두고 곡선은 `[]`이다(`METRIC_NOT_ALLOWED`, `CURVE_NOT_ALLOWED`).
- BACKTEST가 아닌 실행: `period`·`rebalance`·`benchmark`·`costs`는 null이다(`NON_BACKTEST_FIELD`). 가짜 기간이나 비용 0은 만들지 않는다.
- BACKTEST이면서 COMPUTED인 실행은 v1 검사 규칙을 그대로 따른다.

상태 문구(IS2.lab.status):
- 합성이면 "합성 데이터 · 시험용"을 먼저 쓴다. 예: `합성 데이터 · 시험용 · 표본 진단 · 전략 성과 아님`.
- 실자료 1회사 지표 = `실자료 1회사 지표 계산 · 전략 성과 아님`
- 실자료 표본 진단 = `실자료 표본 진단 · 전략 성과 아님`
- 실자료 미산출 = `미산출 · <사유> · 실자료 <종류>`
- BACKTEST는 v1 문구를 쓴다. REAL·COMPUTED라고 해서 검증됨으로 쓰지 않는다.

사유 코드는 화면에서 글로 바꿔 보여 준다(`IS2.lab.reasonText`). 모르는 코드는 "사유 코드 미등록"으로 표시한다. Codex가 회신에 적은 사유 코드 14개를 등록했다.

화면(9.1 비공개 칸):
- BACKTEST가 아니거나 NOT_COMPUTED인 실행은 지표 7개와 곡선 대신 다음을 보여 준다: 결과 종류, 계산 상태, 평가일, 표본("요청 n개 중 m개 사용"), 모집단(범위·완전성·전체 수 또는 NA와 사유), 진단 요약 표(값 · 유효/전체), "전략 성과 아님".
- BACKTEST는 v1 화면에 표본·모집단 줄을 더한다.
- 공개 연결(`LAB-PUBLISH`)과 `lab-results/1` 공개 투영은 바뀌지 않는다. 비공개 값은 공개 화면에 잇지 않는다.

시험 자료: `tools/lab_backtest_fixture.js`의 `payloadV2()`(합의한 합성 4건), `validV2`, `invalidV2`(v2 거부 규칙마다 1개 이상).
