# Technical mock 일봉 입력 경계 — Codex1 구현 명세

> 후속 code PR 제안이다. 이번 작업은 문서만 작성하며 구현·테스트 실행·실제 source 활성화를 하지 않는다. 구현 시 `superpowers:executing-plans` 또는 `superpowers:subagent-driven-development`를 적용하되 사용자의 작업·승인 범위가 우선한다.

**Goal:** 합성 완료 일봉을 검증하고 기존 historical helper와 동일한 returns를 기존 Technical 엔진에 전달하는 첫 offline 입력 경계를 만든다.
**Architecture:** 새 모듈이 sidecar metadata와 가격 시리즈를 검증한다. 정상 입력만 기존 수익률 계약으로 변환하고 injected 엔진을 한 번 호출한다. 실패는 정상 snapshot 없이 `NOT_AVAILABLE`로 반환한다.
**Tech Stack:** 기존 Python·dataclass·typing·datetime·math·pytest만 사용한다. timezone label 검증에 표준 `zoneinfo`를 사용할 수 있으며 거래 calendar를 가져오거나 추정하지 않는다.
**Spec:** `implementation/docs/technical_live_data/DESIGN.md` §7–9(PR #90). 읽기 기준 canonical은 `ee039041ae7f5cb94e6a127930c7e43effb811ec`; DESIGN의 이전 SHA는 문서 작성 당시 근거 고정점이다.

## Global constraints / write-set

- 신규 `implementation/src/investment_system/technical/daily_input.py`: 아래 타입·검증·변환·주입 호출만 구현한다.
- 신규 `implementation/tests/test_technical_daily_input.py`: 합성 fixtures와 아래 의미 있는 계약 검사를 구현한다.
- 신규 `implementation/docs/technical_live_data/MOCK_DAILY_INPUT_VERIFICATION.md`: 실행한 명령·결과·한계와 합성 데이터임을 기록한다.
- 기존 `engine.py`, `technical/__init__.py`, shared contracts, versions, providers, runtime, Web, workflows, 기존/frozen tests를 수정하지 않는다. 새 모듈은 직접 import한다.
- 실제 가격/source/API/계정/토큰/Secret 조회, runner/pipeline import·실행, provider 활성화, 저장·배포·public bundle 연결을 하지 않는다.
- 새 지표·period·임계값·가중치·TSV·scenario·PIT/OOS/calibration 보장을 추가하지 않는다. `21 prices -> 20 returns`는 길이 관계이며 최소 모델 충분성 gate가 아니다.
- 기존 Worker/auth 코드의 존재와 이번 범위는 별개다. 첫 PR은 browser/Worker Technical runtime 또는 실제 공급자 연결을 완성하지 않는다.
- `synthetic=False`는 첫 PR에서 거부한다. false를 LIVE 승인으로 해석하거나 실제값을 DEMO로 표시하지 않는다.
- 오류/진단에는 고정 reason code와 필요 시 필드명·bar index만 쓴다. 가격·bar·원 metadata·토큰·예외의 `str/repr`를 포함하지 않는다. 입력·파생값을 persist/log하지 않는다.
- 문서의 승인·조건충족 병합 허가는 후속 code PR의 자체 병합 허가가 아니다. code PR은 별도 review·승인·병합 대기로 끝낸다.

## Interfaces — `daily_input.py`

아래 타입은 모두 이 모듈의 `@dataclass(frozen=True)` sidecar다. 공유 `PricePoint`, `DataStamp`, `TechnicalSnapshot`에 필드를 추가하지 않는다. metadata를 실제 공급자 검증 증거로 해석하지 않는다.

| 타입 | 정확한 필드·타입 |
|---|---|
| `ExpectedSession` | `session: date`, `close_at: datetime` |
| `CorporateActionEvent` | `kind: Literal["SPLIT","DIVIDEND","OTHER"]`, `effective_session: date`, `published_at: datetime | None`, `available_at: datetime | None`, `source_reference: str | None` |
| `DailyBar` | 필수 `company_id, listing_id, symbol, currency, provider: str`; `session: date`, `observed_at: datetime`, `available_at: datetime | None`, `published_at: datetime | None`, `complete: bool | None`, `price_basis: Literal["RAW_CLOSE","PROVIDER_ADJUSTED_CLOSE"]`; `close: float | None`, `adjclose: float | None`; optional `open, high, low, volume: float | None = None`, `ohlc_basis: Literal["RAW"] | None = None` |
| `DailyInputSeries` | `company_id, listing_id, symbol, currency, provider, exchange, market_timezone, source_reference: str`; `interval: Literal["1d"]`, `price_basis: Literal["RAW_CLOSE","PROVIDER_ADJUSTED_CLOSE"]`, `read_at: datetime`, `synthetic: bool`; `bars: tuple[DailyBar, ...]`; `expected_sessions: tuple[ExpectedSession, ...] | None`, `calendar_reference: str | None`; `basis_status, corporate_action_status: Literal["CONFIRMED_SYNTHETIC","UNKNOWN"]`, `action_covered_sessions: tuple[date, ...]`, `adjustment_reference: str | None`, `events: tuple[CorporateActionEvent, ...]` |
| `PreparedDailyReturns` | `state: Literal["READY","NOT_AVAILABLE"]`, `returns: tuple[float, ...] | None`, `reason_codes: tuple[str, ...]`, `input_bar_count, eligible_bar_count, excluded_future_bar_count, return_count: int`, `quality_flags: tuple[str, ...]`, `synthetic: bool = True`, `pit_status: Literal["NOT_VERIFIED"] = "NOT_VERIFIED"`, `model_status: Literal["PLACEHOLDER_UNVALIDATED"] = "PLACEHOLDER_UNVALIDATED"` |
| `DailyTechnicalResult` | `state: Literal["DEMO","NOT_AVAILABLE"]`, `data: TechnicalSnapshot | None`, `prepared: PreparedDailyReturns` |

`returns`, `data`, `bars`는 `repr=False`로 둔다. 내부 tuple/list/dict를 수정하거나 원 입력을 정렬·삭제·보간하지 않는다. 검사 실패는 생성자가 raw 예외를 내는 방식보다 아래 준비 함수의 고정 reason 반환으로 처리한다.

```python
class TechnicalEvaluator(Protocol):
    def evaluate(self, company_id: str, as_of: datetime, returns: list[float],
                 qgv: QGVSnapshot | None = None, synthetic: bool = True) -> TechnicalSnapshot: ...

def prepare_daily_returns(series: DailyInputSeries, as_of: datetime) -> PreparedDailyReturns: ...
def evaluate_daily_input(series: DailyInputSeries, as_of: datetime, *,
                         engine: TechnicalEvaluator, qgv: QGVSnapshot | None = None) -> DailyTechnicalResult: ...
```

`evaluate_daily_input`는 준비 실패 시 엔진을 호출하지 않는다. 성공 시 `engine.evaluate(series.company_id, as_of, list(prepared.returns), qgv=qgv, synthetic=True)`를 정확히 한 번 호출한다. 빈 returns를 정상 엔진의 UNKNOWN/WAIT로 바꾸지 않는다. 엔진의 `ArithmeticError`는 raw exception 없이 wrapper `state="NOT_AVAILABLE", data=None`으로 반환한다. 이때 준비 결과도 counts와 flags를 보존하되 `state="NOT_AVAILABLE", returns=None, return_count=0, reason_codes=("CALCULATION_ERROR",)`로 교체한다.

## Validation order / exact behavior

1. 타입·필수 metadata를 검사한다. 문자열은 명시된 nonempty 값이어야 하며 trim/대문자화·USD/현재 UTC fallback을 하지 않는다. interval은 `1d`, synthetic는 엄격히 `True`다. timezone은 명시 label만 검증하며 휴일/session을 생성하지 않는다.
2. `as_of`, `read_at`, 모든 supplied 관측/가용/공개/expected-close/event 시각은 aware datetime이어야 한다. `None`을 `read_at`이나 `now()`로 채우지 않는다. 알려진 가용 시각은 `read_at` 이후일 수 없다.
3. 전체 bar의 `observed_at`과 session은 중복 없이 엄격한 오름차순이어야 한다. duplicate와 역순을 거부하며 sort/deduplicate하지 않는다.
4. `observed_at > as_of`인 bar만 cutoff projection으로 제외하고 개수를 보존한다. 이후 가격·finality·bar identity·basis 검사는 eligible bars에만 적용한다. 이것은 결측 bar 삭제와 다른 정상 cutoff 동작이다.
5. eligible bar가 0/1개면 실패한다. 2~20개는 짧은 정상 returns를 만든다. 모든 준비 결과에 실제 개수를 보존하며 21개 이상도 모델 충분성을 주장하지 않는다.
6. `expected_sessions`와 `calendar_reference`가 명시돼야 한다. expected sessions도 중복 없는 오름차순과 aware close를 검사한다. `close_at <= as_of`의 명시 expected sessions와 eligible session 배열이 정확히 같고 관측 시각은 해당 명시 close와 같아야 한다.
7. 명시 expected fixture에서 건너뛴 날짜는 정상 비거래일, expected에 있으나 bar가 없는 session은 gap이다. 실제 exchange/주말/휴일 규칙이나 timestamp 간격으로 둘을 추정하지 않는다. calendar 증거가 없으면 실패한다.
8. eligible의 `complete is True`, close/finality 일치, company/listing/symbol/currency/provider와 series의 정확한 일치를 요구한다. 가격·통화·심볼 fallback, 다른 상장/series 이어 붙이기를 하지 않는다.
9. eligible `available_at=None`은 실패한다. `available_at > as_of`와 알려진 `published_at > as_of`를 별도 이유로 거부한다. `observed_at <= available_at <= read_at`, 알려진 publication은 `observed_at <= published_at <= available_at`이어야 한다. publication 미확인은 그대로 두고 `PUBLICATION_TIME_UNKNOWN`/`PIT_UNAVAILABLE` flags를 보존한다.
10. 가격은 bool이 아닌 int/float, finite, strictly positive여야 한다. close는 필요하며 adjusted 선택이면 모든 eligible adjclose가 필요하다. 제공된 optional 가격도 검사한다. bar basis는 series basis와 같아야 하며 per-bar adjusted→raw fallback을 하지 않는다.
11. raw open/high/low는 모두 없거나 모두 있어야 한다. 있으면 `ohlc_basis="RAW"`와 `low <= min(open,close) <= max(open,close) <= high`를 요구한다. adjusted close는 별도 필드에서 선택하며 raw OHLC의 close를 교체하지 않는다. volume은 None과 실제 0을 보존하며 bool/비유한/음수를 거부한다.
12. basis/event coverage는 `CONFIRMED_SYNTHETIC`여야 하고 `action_covered_sessions`는 eligible session과 정확히 같아야 한다. 빈 event 배열만으로 행사 없음이 확인됐다고 처리하지 않는다. adjusted 선택은 nonempty adjustment reference를 요구한다.
13. event는 명시 kind/effective session/source/가용 시각과 supplied 공개 시각을 검사한다. `available_at=None`은 `ACTION_AVAILABILITY_UNKNOWN`, `available_at>as_of`는 `ACTION_AVAILABLE_AFTER_AS_OF`다. 알려진 `published_at`은 `published_at<=available_at` 및 `published_at<=as_of`를 모두 만족해야 하며 위반은 `ACTION_METADATA_INVALID`다. 행사 공개는 effective session보다 먼저일 수 있어 그 날짜를 publication의 하한으로 쓰지 않는다. 공개 시각 미확인은 그대로 두고 두 미확인 flags를 보존한다. unknown source, eligible coverage와 맞지 않는 event도 `ACTION_METADATA_INVALID`다. raw 선택의 행사 구간은 `UNRESOLVED_CORPORATE_ACTION`으로 차단한다. adjusted fixture의 명시 확인 metadata만 허용하며 split/dividend 보정 공식을 구현하지 않는다.
14. 선택 가격의 인접 쌍마다 `p_cur / p_prev - 1.0`을 계산한 뒤 마지막 20개만 선택한다. 연산 결과가 nonfinite면 실패한다. gap/null/불량값을 삭제하고 양옆 가격을 잇지 않는다. engine threshold·scenarios·invalidation·version을 재계산/덮어쓰지 않는다.

모든 실패는 `prepared.state="NOT_AVAILABLE"`, `returns=None`, `return_count=0`, 고정 nonempty reason codes로 표현하며 wrapper는 `state="NOT_AVAILABLE", data=None`이다. 복수 오류 fixture는 위 순서의 첫 실패 이유만 assert한다. 성공은 `READY`, empty reason codes이며 wrapper는 `DEMO`다. 모든 결과의 PIT는 `NOT_VERIFIED`, 모델은 `PLACEHOLDER_UNVALIDATED`다.

| 실패 묶음 | 고정 reason codes |
|---|---|
| 형태/필수 metadata/실입력/시각 | `INVALID_INPUT_TYPE`, `MISSING_METADATA`, `INVALID_INTERVAL`, `REAL_INPUT_NOT_AUTHORIZED`, `INVALID_TIMESTAMP`, `INVALID_TIME_ORDER` |
| 구조/길이/calendar/finality/identity | `DUPLICATE_BAR`, `UNSORTED_BARS`, `INSUFFICIENT_BARS`, `CALENDAR_UNCONFIRMED`, `INVALID_CALENDAR`, `MISSING_SESSION`, `UNEXPECTED_SESSION`, `SESSION_TIME_MISMATCH`, `INCOMPLETE_SESSION`, `IDENTITY_MISMATCH` |
| 가용성/가격/OHLC/volume | `AVAILABILITY_UNKNOWN`, `AVAILABLE_AFTER_AS_OF`, `PUBLISHED_AFTER_AS_OF`, `INVALID_PRICE`, `ADJUSTED_CLOSE_MISSING`, `MIXED_BASIS`, `INVALID_OHLC`, `INVALID_VOLUME`, `NONFINITE_RETURN` |
| basis/event/연산 | `BASIS_UNCONFIRMED`, `ACTION_COVERAGE_UNCONFIRMED`, `ACTION_COVERAGE_MISMATCH`, `ADJUSTMENT_METADATA_MISSING`, `ACTION_METADATA_INVALID`, `ACTION_AVAILABILITY_UNKNOWN`, `ACTION_AVAILABLE_AFTER_AS_OF`, `UNRESOLVED_CORPORATE_ACTION`, `CALCULATION_ERROR` |

## Fixtures / existing helper oracle

- tests 내부 `_series(prices, *, price_basis="RAW_CLOSE")`와 dataclass `replace`로 합성 fixture를 만든다. 식별은 `synthetic-company`, `synthetic-listing`, `SYNTHETIC`, 통화는 명시 `SYN`, source/calendar reference는 `synthetic://...` 문자열이다. 실제 공급자·종목·가격 샘플을 복사하지 않는다.
- 시간은 fixture가 선언한 aware UTC close와 acquisition time을 사용한다. 기본 metadata는 `complete=True`, publication/availability=관측 close, explicit synthetic coverage와 events=()다. `_series`는 test 작성용이며 production의 누락 metadata를 채우는 fallback이 아니다.
- `_historical_returns_oracle(bars: list[dict], as_of: datetime) -> list[float]`: canonical `implementation/src/investment_system/validation/historical.py`를 text/AST로 읽고 **실제 `bars_to_returns` FunctionDef 하나만** 분리 compile/exec한다. 필요한 globals는 `datetime`이다. 함수를 복제한 미러를 새로 쓰지 않는다.
- `investment_system.validation.historical` 자체를 import하지 않는다. 그 파일의 provider/storage/runner imports와 다른 함수는 실행하지 않는다. oracle 입력은 이미 정상인 synthetic `{"observed_at": ..., "price": ...}` 배열에만 한정한다.
- 수익률과 엔진 비교는 exact equality를 사용한다. 근거 없는 새 tolerance를 추가하지 않는다. 직접 엔진 비교에는 실제 준비된 returns를 전달한다.

## Task 1 — validation / returns 준비

**Files:** 위 신규 모듈과 신규 test 파일. **Produces:** `prepare_daily_returns`, 타입들, 고정 failure reasons.

- [ ] 아래 계약 tests를 먼저 작성한다. Task 1에서는 `prepare_daily_returns`의 state/returns/reason을 검사한다. Task 2 wrapper 구현 후 같은 불량 fixture마다 `CountingEngine.calls == []`, `result.data is None`, `result.state == "NOT_AVAILABLE"`, `result.prepared.returns is None`도 확인한다.

| 정확한 test 이름 | fixture / 핵심 assertions |
|---|---|
| `test_returns_match_historical_helper_short_and_last20` | 2·6·20·21·25 가격 parametrization; `list(p.returns) == oracle(...)`, `len(p.returns) == min(n-1,20)`, 실제 counts 일치, flags가 모델/PIT 승격을 하지 않음. |
| `test_future_observation_is_excluded_without_lookahead` | cutoff 뒤 extra bar의 가격을 바꿔도 eligible returns/engine 결과 동일; `excluded_future_bar_count == 1`; cutoff 경계 bar는 포함. |
| `test_unknown_or_future_availability_blocks_engine` | None/future eligible availability를 각각 `AVAILABILITY_UNKNOWN`/`AVAILABLE_AFTER_AS_OF`로 assert; 관측 cutoff 검사를 통과한 bar로 두 조건의 독립성을 증명. |
| `test_publication_unknown_is_preserved_and_future_blocks` | None은 READY+두 flags+`NOT_VERIFIED`; known future는 `PUBLISHED_AFTER_AS_OF`+엔진 미호출. |
| `test_invalid_timestamp_and_time_order_block_engine` | naive as_of/read/observed/available/published/expected/event와 available>read, known pub>available; 정확한 `INVALID_TIMESTAMP`/`INVALID_TIME_ORDER`. |
| `test_empty_and_single_bar_do_not_create_unknown_wait` | n=0/1; `INSUFFICIENT_BARS`; snapshot 부재와 미호출; 짧은 정상은 이전 test로 별도 보증. |
| `test_invalid_prices_are_not_dropped_or_repaired` | eligible close=None/0/negative/NaN/±inf/True/False/string; `INVALID_PRICE`; 중간 불량값을 건너뛴 returns 없음; original bars unchanged. |
| `test_duplicate_and_unsorted_bars_are_rejected` | duplicate timestamp/session와 reversed 순서; `DUPLICATE_BAR`/`UNSORTED_BARS`; sort/dedup 없음. |
| `test_explicit_calendar_distinguishes_non_session_and_gap` | expected=[명시 첫날, 명시 건너뛴 후날]은 정상; expected=[첫날,중간날,후날]에 bars 첫날/후날은 `MISSING_SESSION`; None calendar는 `CALENDAR_UNCONFIRMED`; calendar duplicate/order 오류는 `INVALID_CALENDAR`. |
| `test_session_time_and_completion_must_be_explicit` | incomplete/None complete는 `INCOMPLETE_SESSION`; expected-close mismatch는 `SESSION_TIME_MISMATCH`; complete값 True를 임의 truthy로 대체하지 않음. |
| `test_identity_and_required_metadata_do_not_fallback` | 각 identity mismatch=`IDENTITY_MISMATCH`; empty currency/symbol/reference=`MISSING_METADATA`; interval!=1d=`INVALID_INTERVAL`; synthetic=False=`REAL_INPUT_NOT_AUTHORIZED`. |
| `test_mixed_basis_and_missing_adjusted_close_block_engine` | mixed bar basis=`MIXED_BASIS`; adjusted 중간 adjclose=None=`ADJUSTED_CLOSE_MISSING`; raw로 fallback 없음; unknown basis=`BASIS_UNCONFIRMED`. |
| `test_ohlc_coherence_and_raw_basis_are_preserved` | partial OHLC/low>high/close outside range/non-RAW label=`INVALID_OHLC`; raw OHLC+별도 adjusted 입력의 raw fields unchanged; returns는 선택 adjusted 가격과 exact equality. |
| `test_volume_zero_none_and_invalid_values_are_distinct` | volume=0/None 모두 READY이고 원 값 그대로; bool/negative/NaN/inf는 `INVALID_VOLUME`; volume 기반 feature 생성 없음. |
| `test_corporate_action_metadata_is_not_inferred_from_empty_events` | empty events+UNKNOWN coverage=`ACTION_COVERAGE_UNCONFIRMED`; 범위 불일치=`ACTION_COVERAGE_MISMATCH`; adjusted reference missing=`ADJUSTMENT_METADATA_MISSING`. |
| `test_corporate_action_unknown_future_and_raw_events_block` | known synthetic adjusted event 정상; unknown/future event available, missing source, raw event 각각 해당 reason; supplied publication>available 또는 >as_of는 `ACTION_METADATA_INVALID`, None은 미확인 flags 유지; effective session 전 공개도 허용. event 확인 여부를 수익률 jump 임계값으로 추정하지 않음. |
| `test_nonfinite_return_is_rejected_before_engine` | 유한 양수 prices이지만 division이 inf를 만드는 fixture; `NONFINITE_RETURN`; engine 미호출. |

- [ ] 후속 구현 단계에서 신규 파일만 선택하여 tests를 실행한다. 신규 모듈 부재로 실패함을 확인한다.
- [ ] 명세의 타입·validation 순서·순수 반환 변환을 최소 구현하고 같은 tests를 다시 실행한다. normal helper의 불량값 skip 동작은 복제하지 않는다.

## Task 2 — engine / QGV / absence / side effects

**Consumes:** Task 1 준비 결과, 기존 `TechnicalEngine.evaluate` signature. **Produces:** `evaluate_daily_input`.

- [ ] `CountingEngine`은 호출 args를 메모리에만 기록하고 기존 엔진에 위임한다. 다음 tests를 먼저 작성한 뒤 wrapper를 구현한다.

| 정확한 test 이름 | fixture / 핵심 assertions |
|---|---|
| `test_engine_full_snapshot_matches_direct_call_for_existing_branches` | prices [100,101,102]/[100,102,104.04]/[100,99,98]/[100,100,100]/[100,120,96]로 ENTRY/ADD/DOWN/RANGE/HIGH_VOL 기존 분기 확인; prepared returns 직접 호출과 경유 결과의 `to_dict()`에서 **`technical_snapshot_id` 하나만 제거**해 전체 equality. |
| `test_engine_shape_placeholder_version_and_synthetic_remain_unchanged` | field set은 기존 TechnicalSnapshot과 동일; version=`TECHNICAL_STRUCTURAL`, kind=`IMPLEMENTATION_KIND`, shocks=(-0.1,0.0,0.1), scenario kind=`structural-placeholder`, 기존 invalidation 문자열 exact equality, drawdown_recheck=False, synthetic=True, wrapper DEMO. |
| `test_qgv_full_snapshot_is_unchanged_and_scores_do_not_drive_technical` | `AnalysisEngine().analyze("synthetic-company", as_of, tests.helpers.complete_obs(score), synthetic=True)`로 서로 다른 합성 high/low QGV 생성; 각각 full `qgv.to_dict()` before==after; tech ref ID 정확, mutated_qgv=False; ID/ref 두 QGV간 차이만 구분하고 regime/zone/scenarios 동일. |
| `test_engine_receives_prepared_values_once_and_preserves_inputs` | calls 길이1; company/asof/list returns/qgv 동일 객체/synthetic=True 정확; original series 및 QGV full snapshot unchanged; qgv=None ref도 None. |
| `test_all_preparation_failures_block_engine_and_have_no_data` | Task 1의 invalid fixture/reason cases를 재사용하여 wrapper를 parameterize; calls=[]/NOT_AVAILABLE/data=None/returns=None/reason exact equality. 실패 이유를 UNKNOWN/WAIT 정상 snapshot으로 바꾸는 경로 없음. |
| `test_engine_arithmetic_failure_has_no_normal_data_or_raw_exception` | injected engine raises ArithmeticError에 원 입력 sentinel 포함; wrapper NOT_AVAILABLE/data=None; prepared NOT_AVAILABLE/returns=None/return_count=0/reason_codes=("CALCULATION_ERROR",), counts/flags 보존; reason에 sentinel 부재. 이 test는 입력 실패 미호출과 구분한다. |
| `test_boundary_has_no_io_or_diagnostic_payload_leak` | fixture/oracle 준비·module import 후 socket connection/open/Path.open/logging emit를 실패 spy로 막고 정상+실패 호출; I/O calls=0, stdout/stderr/logs empty; reason은 고정 코드만; source review로 provider/storage/runtime import 없음도 확인. |

- [ ] 기존 엔진과 wrapper의 비교를 실행하고 모든 항목 PASS를 확인한다. 새 snapshot 필드나 정상 data를 failure에 추가하지 않는다.

## Task 3 — verification / review handoff

아래 명령은 **후속 code PR 구현 단계용**이다. 이번 문서 작성에서는 실행하지 않는다. cwd는 repository root이며 pytest가 없으면 임의 dependency 설치·runner 대체를 하지 말고 그 제한을 기록한다.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=implementation/src python -m pytest -p no:cacheprovider -q implementation/tests/test_technical_daily_input.py
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=implementation/src python -m pytest -p no:cacheprovider -q implementation/tests/test_downstream_and_integration.py::test_technical_does_not_mutate_qgv
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=implementation/src python -m pytest -p no:cacheprovider -q implementation/tests/test_v_prior_and_c15.py::test_technical_ignores_qgv_scores
git diff --name-status
git diff --check
```

- [ ] 신규 의미 있는 tests와 기존 Technical QGV 불변성 검사가 PASS, diff check가 clean이어야 한다. 이번 task의 현재 실행 결과는 **미실행**으로 기록한다.
- [ ] diff의 파일 목록이 허용된 신규 세 파일과 일치하는지 확인한다. engine/shared/provider/runtime/web/workflow/frozen test 변경은 없어야 한다.
- [ ] 검증 기록에는 합성 fixtures, 정확 명령·실행결과, short history도 정상 호환이라는 점, PIT/model/runtime/source 미완료를 적는다. 실제 가격·payload·credentials 또는 합성 returns dump를 기록하지 않는다.
- [ ] `validation/adapters.py::TechnicalAdapter`의 QGV 불변성 의미를 준수하되 해당 adapter/pipeline을 import하여 first boundary를 확장하지 않는다.
- [ ] review에서는 no repair, availability와 observation의 독립 gate, 명시 calendar, series basis/event metadata, error engine 미호출, full snapshot equality/QGV nonmutation을 점검한다.
- [ ] code PR 제목은 `Technical: mock 일봉 검증과 기존 returns 입력 어댑터`; 검증된 offline 입력 경계와 제한을 설명하고 별도 승인·병합 대기로 인계한다.

**완료 조건:** 허용 write-set 안에서 mock 검증·정상 helper 호환·기존 engine shape/분기/placeholder/version·QGV 불변성·실패 부재 표현이 확인된다. 실제 공급자·개인 가격·browser/Worker Technical 실행·모델 유효성·PIT 완성을 완료 조건이나 성공 주장에 포함하지 않는다.
