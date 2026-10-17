# 전진 검증 v1 (forward_validation/v1 · UNCALIBRATED)

사용자 결정 (2026-10-11):
"전진 검증: 2026-10-19(월) 시작, 대상 TARGET v0 포트폴리오, 전략 QGV standard v1. V(DCF)가 붙으면 별도 버전으로 기록하고 이전 기록은 절대 바꾸지 않는다. Holdout은 계속 사용하지 않는다."
모든 기본값은 "v1 UNCALIBRATED"(보정 전)입니다.

## 1. 구성

| 부분 | 위치 | 가격 사용 |
|---|---|---|
| 공개 일별 기록(ledger) | `forward-validation-ledger.json` (Pages) | 없음 |
| 기록 생성·검증 (Python) | `src/investment_system/validation/forward_ledger.py`, `tools/forward_validation_ledger.py` | 없음 |
| 공개 파일 검사 | `tools/pages_artifact_guard.py` (`forward_ledger_boundary`) | 없음 |
| 기기 화면·수익률 계산 (JS, RAM 전용) | `web_assets/forward-validation.js`, S10 '검증·연구' 화면 | 기기에서만 |
| 기기 계산 기준 구현 (Python, 교차 검증용) | `src/investment_system/validation/forward_device_reference.py`, `tools/forward_validation_reference.py`, `tests/fixtures/forward_validation_reference_v1.json` | 합성 값만 |

GitHub Actions는 가격이 필요 없는 공개 자료만 계산합니다. 가격이 필요한 계산(전진 수익률)은 기기 JS에서 메모리로만 하며, Python 기준 구현은 합성 벡터로 같은 결과인지 확인하는 데만 씁니다. 공개 저장소·Pages·Actions 로그에는 가격, 가격에서 나온 값, 개인 정보가 들어가지 않습니다.

## 2. 기록 규칙

- 시작일: 2026-10-19. 그 전에는 상태 `NOT_STARTED`, 기록 0건으로 공개합니다.
- 기록 단위: 완료된 미국(NYSE) 정규 거래일마다 1건. 그 거래일 당일(뉴욕 시각 16:00 이후)에 실행된 경우에만 그 날짜를 기록합니다. 다음 날 아침 실행은 전날을 기록하지 않습니다(소급 없음).
- 휴장일: NYSE 공식 전일 휴장일 표(2026~2028)를 코드에 고정했습니다. 2028-12-31 이후 날짜는 `CALENDAR_NOT_CONFIGURED`로 기록하지 않습니다(표 연장 필요).
- 기록 내용 (`versions["forward_validation/v1"]`의 각 항목):
  - `date`, `version`(`forward_validation/v1`), `strategy`(`QGV_STANDARD_V1`), `calibration`(`UNCALIBRATED`)
  - `target`: TARGET v0 id·버전·원본 sha256·19종목 목표 비중(`weights_units`, 합계 10000). 같은 실행의 공개 `actual-catalog.json`에서 그대로 가져오며 새로 만들지 않습니다. 검증기는 비중이 공식 TARGET v0와 정확히 같은지 확인합니다.
  - `companies`: 19종목별 상태와 Q·G(점수·coverage·누락 요인 수). 같은 실행에서 공개된 `sec-qg-factors.json`의 요인 점수를 QGV standard v1 가중치(기존 엔진 `recalculate_strategy_preview`, 기기 `EnginePreview.strategy`와 같음)로 묶은 값입니다. LIVE → OK, STALE → STALE_DATA로 다루며 V는 없습니다.
  - `qg_as_of`, `qg_screen_state`, `source_sha256`(두 입력 파일의 sha256), `created_at`
- 입력이 없거나 잘못되면 상태 `NOT_AVAILABLE`과 이유 코드(`SEC_QG_FACTORS_MISSING`, `SEC_QG_FACTORS_INVALID`, `SEC_QG_FACTORS_NOT_SAME_SESSION`, `SEC_QG_FACTORS_NOT_AVAILABLE`, `TARGET_CATALOG_MISSING`, `TARGET_CATALOG_INVALID`)로 기록하고, 값은 null로 둡니다. 0으로 채우지 않습니다.

## 3. 불변성 (append-only)

- 이미 있는 기록은 바이트 단위로 그대로 유지합니다. 다시 쓰기·삭제·순서 변경·소급 추가를 하지 않으며 시작일 이전 날짜는 만들지 않습니다.
- 같은 날 다시 실행하면 기존 기록을 그대로 두고 `record=EXISTS`를 출력합니다(나중 입력으로 덮어쓰지 않음).
- 매 실행은 라이브 Pages의 이전 기록을 읽어 이어 붙입니다.
  - 네트워크 오류, 404가 아닌 HTTP 오류, 검증 실패 → 아무것도 쓰지 않고 실패(exit 1). 배포가 멈추므로 공개된 이력은 사라지지 않습니다.
  - 시작일 전 404 → 새 `NOT_STARTED` 기록을 만듭니다.
  - 시작일 이후 404 → 실패(exit 1). 최초 공개가 시작일 이후가 된 경우에만 `--bootstrap-after-start`를 명시적으로 한 번 붙입니다.
- 검증기(`require_ledger`, JS `validate`)는 날짜 오름차순·거래일·시작일 이후·생성 시각(그 날 뉴욕 16:00 이후)·비중·V 부재를 확인하고, `require_append_only`는 이전 기록이 앞부분에 그대로 있는지 확인합니다.

## 4. 버전

```
versions: {
  "forward_validation/v1": [...],                       # Q·G만, 매 거래일 추가
  "forward_validation/v1+dcf_v1_default": []            # V 포함 버전: 별도 배열, 추가만 가능
}
version_status["forward_validation/v1+dcf_v1_default"] = {state: NOT_AVAILABLE, reason_codes: [V_REQUIRES_DEVICE_PRICES]}
```

V(DCF)는 가격이 필요하므로 Actions에서 계산하지 않습니다. V가 붙으면 v1 배열은 그대로 두고 V 포함 버전 배열에만 새로 추가합니다. 현재 검증기는 V 포함 버전이 비어 있어야 통과합니다(생산자가 생기면 별도 결정과 검증기 변경 필요).

## 5. 비공개 보관본

`RAW_REPO_TOKEN`이 있으면 그 날 기록이 있는 실행마다 기록 JSON과 `.sha256`을 비공개 저장소 `kco994553-star/investment-system1-raw`의 릴리스 `forward-ledger-YYYY-MM-DD`에 올립니다(`raw_store_release.release_for_tag`·`http` 재사용, 이미 있으면 건너뜀). 토큰이 없으면 `RAW_UPLOAD_NOT_CONFIGURED`를 출력하고 계속합니다. 업로드 실패는 고정 코드만 출력하며 공개 기록 생성을 막지 않습니다. 토큰은 출력하지 않습니다.

## 6. 기기 화면 (S10 '검증·연구' → 전진 검증)

- 표시: 기록 상태·시작일·기록 수·전략과 버전·V 포함 버전 상태·일별 Q·G 요약(가용 종목 수, 점수가 있는 종목만 TARGET v0 비중으로 낸 가중평균 — 화면 표시값, 저장 안 함)·"Holdout UNCONFIRMED · 사용 금지" 배지.
- 전진 수익률: 사용자가 'TARGET 가격 불러오기 (RAM)'를 누를 때만 기존 비공개 가격 Worker(PrivateHistory와 같은 조건: 기능 ON, 승인된 Worker 주소, 구글 로그인)에서 19종목 일별 이력을 읽어 메모리에만 둡니다. Worker 제한(분당 12회)에 걸리면 읽은 종목은 메모리에 두고, 다시 누르면 남은 종목만 읽습니다. '가격 지우기'나 화면 이동 시 지웁니다. 계산한 수익률은 저장·전송하지 않습니다.
- 계산 규칙(Python 기준 구현과 동일): `IN_PROGRESS`가 아닌 봉 중 시작일 이후 첫 봉을 기준, 마지막 봉을 종료로 하여 수정종가 비율 − 1. 현지 통화 기준, 환율 미적용(`ADJUSTED_CLOSE_LOCAL_CURRENCY_NO_FX`). 한 종목이라도 없으면 포트폴리오 수익률은 `NOT_AVAILABLE`(부분 재정규화·0 대입 없음).
- S&P 500 비교: `NOT_AVAILABLE · SP500_NOT_IN_PRIVATE_HISTORY_WORKER` (Worker는 TARGET 19종목만 제공, Worker는 변경하지 않음).
- Holdout은 사용하지 않습니다.

## 7. 한계 (NOT_AVAILABLE · 미보정)

- V 포함 버전: 기록 없음(`V_REQUIRES_DEVICE_PRICES`).
- S&P 500 기준선: 없음.
- 환율: 미적용. 도쿄일렉트론(JPY)·한미반도체(KRW)는 현지 통화 수익률이 그대로 합산됩니다.
- 한미반도체 KRX 대체 경로는 1개월 범위만 지원하므로, 시작 후 약 25일이 지나면 그 종목(따라서 포트폴리오 수익률)이 NOT_AVAILABLE이 될 수 있습니다.
- 시장별 마지막 거래일이 다를 수 있습니다(화면에 종료일 표시).
- 거래일 실행이 빠지면 그 날짜는 빈칸으로 남습니다(소급 없음).
- 같은 날 Pages 배포 직후(캐시 약 10분 이내) 수동 재실행하면 오래된 Pages 사본을 읽어 그날 기록이 다른 내용으로 다시 만들어질 수 있습니다. 같은 날 재실행은 피하고, 필요하면 비공개 보관본과 대조합니다.
- 파일 크기: v1·v2를 함께 기록하므로 거래일당 약 8.5KB씩 늘어납니다(v1 약 3.8KB + v2 약 4.7KB, v2의 관측 기준 약 0.27KB 포함 — 10절, 합성 리허설 측정, [READINESS_20261019.md](READINESS_20261019.md) §4 F3). 생성기 한도 2MB(`MAX_BYTES`)에는 약 246거래일 뒤인 2027년 10월 전후에 닿으므로, 2027-09 이전에 분할 방식을 결정해야 합니다. 한도를 넘으면 생성기는 아무것도 쓰지 않고 실패하며, 그날 일일 작업도 멈춥니다.
- 모든 기준(가중치·범위·휴장일 처리)은 v1 UNCALIBRATED입니다.

## 8. 워크플로 연결 (저장소 소유자 적용)

`.github/workflows/sec-daily-public-inputs.yml` build 작업에서 SEC 수집 단계들 뒤(같은 실행의 `sec-qg-factors.json` 생성 후), Node 검증 단계 앞에:

```yaml
      - name: Append forward validation ledger (price-free, append-only)
        env:
          RAW_REPO_TOKEN: ${{ secrets.RAW_REPO_TOKEN }}
        run: |
          python implementation/tools/forward_validation_ledger.py --out "$RUNNER_TEMP/public-cockpit"
          python implementation/tools/pages_artifact_guard.py --artifact-dir "$RUNNER_TEMP/public-cockpit"
```

`.github/workflows/cockpit-pages.yml`의 'Preserve previously published validated SEC observations for UI deployment' 단계에 (가드 실행 줄 앞):

```yaml
          python implementation/tools/forward_validation_ledger.py --preserve-only --out "$RUNNER_TEMP/public-cockpit"
```

## 9. 테스트

- `tests/test_forward_validation_ledger.py`: 달력, 시작 전/후, 불변성, NOT_AVAILABLE 기록, 실패 시 미기록, 404 처리, 보존, 비공개 업로드, 검증기, Pages 가드, 기준 벡터, JS 검증기 일치.
- `tools/forward_validation_node_test.js`: 합성 벡터 Python=JS 정확히 일치, 읽기·검증, 저장/전송 없음.
- `tools/forward_validation_browser_test.js`: S10 표시(390/1440), 분당 제한 후 남은 종목만 다시 읽기, 저장·전송 없음, 준비 관측 표시와 구간별 수익률.
- `tests/test_forward_validation_v2.py`: 관측 기준(주 평가·준비 관측 사유, 경계값 454·7일), 기존 행 보존, Python=JS 검증기 일치, 구간 분리.
- `tests/test_forward_validation_rehearsal_1019.py`: 10/19 기록의 관측 기준(합성 Universe라 준비 관측), 10/20에 그대로 이어짐.

## 10. 관측 기준·평가 대상·평가 구간 (소유자 지시 2026-10-16)

v2 기록(`forward_validation/v2`)마다 `basis`를 남깁니다. 원장이 그날 실제로 읽은 `sec-qgv2.json`의 계산 기준입니다. 이미 있는 항목은 다시 적지 않습니다. 입력 파일 sha256은 `source_sha256["sec-qgv2.json"]`, 파일 시각은 `qg_as_of`에 이미 있습니다.

| 항목 | 내용 |
|---|---|
| `calc_version` | 입력 파일의 계산 규칙 버전. 없으면 null |
| `q_scored`, `g_scored` | 입력 파일에서 Q·G 점수가 있는 행 수(분모 504) |
| `population` | 실제 순위 계산 모집단. `n`(CIK 수)과 `id`(정렬한 CIK 목록 sha256의 앞 16자리). 목록 자체는 적지 않습니다 |
| `acquired` | 실제 사용한 행의 수집일 범위 [가장 오래된 날, 가장 최근 날] (UTC 날짜) |
| `evaluation` | 관측 당시 평가 대상 여부: `eligible`, `status`(`PRIMARY`/`PREPARATORY`), `reasons` |
| `segment` | 평가 구간. `calc_version` 값, 없으면 `NONE` |

**주 평가(`PRIMARY`) 조건.** 모두 충족해야 합니다. 기준은 2026-10-15 결정을 그대로 씁니다.
- Q·G 각 454개 이상(T-COV: 504의 90%).
- 계산 버전 일관성: 파일에 `calc_version`이 있고, 값이 있는 모든 행이 같은 버전입니다. 원자료가 없어 정상적으로 NA인 행은 막지 않습니다.
- 최신성(T-FRESH 7일): 실제 사용한 행 중 가장 오래된 수집일이 세션 날짜로부터 7일 이내입니다. 파일 `as_of`는 보지 않습니다.

하나라도 못 미치면 `PREPARATORY`("준비 관측·주 평가 대상 아님")로 기록하고 사유를 남깁니다.

| 사유 코드 | 뜻 |
|---|---|
| `Q_BELOW_454`, `G_BELOW_454` | Q 또는 G 산출 수가 454 미만 |
| `CALC_VERSION_MISSING` | 입력 파일에 calc_version이 없음 |
| `CALC_VERSION_MIXED` | 값이 있는 행 중 다른(옛) calc_version 행이 있음 |
| `ROW_DATA_STALE` | 수집 후 7일을 넘은 행이 있음(또는 사용한 행이 없음) |
| `POPULATION_MISMATCH` | 다시 센 모집단 수가 파일의 `cross_section_size`와 다름 |
| `RECORD_NOT_AVAILABLE` | 그날 기록이 NOT_AVAILABLE(입력 없음·무효) |
| `BASIS_NOT_COMPUTED` | 기준 계산이 예상 밖으로 실패. 그날 기록은 잃지 않고 준비 관측(`NONE` 구간)으로 남김 |

**평가 구간**
- calc_version이 바뀌면 그 날부터 새 구간입니다. 이전 구간은 그대로 보존합니다.
- 서로 다른 구간의 성과를 하나로 잇지 않습니다. 화면은 구간별로 따로 보여 줍니다.
- 나중에 정한 최종 calc_version으로 과거 기록을 한꺼번에 빼지 않습니다. 각 기록은 관측 당시 판정을 따릅니다.
- `PREPARATORY` 기록은 보존하고 화면에 사유와 함께 표시합니다. 주 평가 계산에는 쓰지 않습니다.
- NOT_AVAILABLE 기록은 구간을 나누지 않습니다.

**기존 기록**
- 이 규칙 이전에 쓴 행(`basis` 없음)은 바꾸지 않습니다. 검증기는 그대로 통과시킵니다. `require_append_only`는 바이트 단위 동일을 계속 확인합니다.
- 그런 행은 "관측 기준 미기록(이전 기록)"으로 표시하고 별도 구간(`LEGACY`)으로 둡니다.
- 한 번 `basis`가 있는 v2 행이 나오면, 그 뒤의 v2 행은 모두 `basis`가 있어야 합니다. 빠지면 검증 실패입니다. 시작일을 미리 고정하지 않아도 되고, 이후 기록에서 기준이 빠지는 것은 막습니다.
- v1 비교 기록에는 `basis`를 넣지 않습니다. v1 입력(`sec-qg-factors.json`)에는 504종목 모집단과 calc_version이 없습니다. v1 행은 "비교용 · 평가 대상 아님"으로 표시합니다.

**검증기 일치**
- Python `require_ledger`와 기기 JS `validate`는 같은 규칙으로 `basis`를 검사합니다.
- 사유 코드는 정해진 순서이고 중복이 없습니다. `status`·`eligible`·사유가 서로 맞아야 합니다.
- Q·G 수와 454 사유, calc_version과 `CALC_VERSION_MISSING`·`segment`, `acquired`와 `ROW_DATA_STALE`이 서로 맞는지 다시 확인합니다.
- 구간 계산(`evaluation_segments` / JS `segments`)은 합성 기준 벡터(`forward_validation_reference_v1.json`)로 같은 결과인지 확인합니다.

**기기 계산**
- S10 화면: 일별 표에 '평가 구분' 열, 그 아래 '평가 구간' 표(구간, 기간, 주 평가 기록 수, 준비 관측 수).
- TARGET v0 수익률: 구간마다 따로 계산합니다. 시작은 그 구간의 첫 주 평가 기록, 끝은 마지막 주 평가 기록입니다. 현재 구간은 끝이 열려 있습니다. 현재 구간에 주 평가 기록이 없으면 NOT_AVAILABLE입니다.
- 가상 운용(`virtual-trading-runner.js`, Python `virtual_trading_inputs.py`): 현재 구간의 주 평가 기록만 씁니다. 준비 관측 기록과 이전 구간은 잇지 않습니다. 시작일은 현재 구간에서 Q·G 숫자가 있는 첫 주 평가 기록입니다.
- 배포 성공 여부는 원장에 넣지 않습니다. 같은 날짜의 실행 보고(`PUBLISHED_COVERAGE` 줄 등)와 연결합니다.

**크기**
- 합성 리허설 기준 거래일당 8,237바이트 → 8,515바이트(+278바이트, 약 3.4%). `basis` 하나는 약 270바이트입니다.
- 2MB 한도까지 약 254거래일 → 약 246거래일(약 8거래일 감소). 분할 방식 결정 시점(2027-09 이전)은 그대로입니다.
