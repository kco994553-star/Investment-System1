# 기존 계산 결과의 화면 집계

`held-expanded-classification-summary/1`에 선택 필드 `calculation_counts`를 추가한다.
내부 계약은 `common-classification-calculation-counts/1`이다. 구 필드는 그대로 유지한다.
구 판독기는 추가 필드를 무시한다. 필드가 없는 구 파일을 새 집계 0건으로 표시하면 안 된다.

이 경로는 보존된 preview의 결과 행을 세고 기존 coverage와 대사한다. 원지표 변환,
요소 점수화, 관문 재판정, 순위 계산을 호출하지 않는다. 신규 계산·채택 수는 늘지 않는다.
스냅샷·결과·분류 view·관문 연결 감사·기존 summary·보유 재무 목록의 바이트 해시를 검증한다.
결과의 입력/설정/캐시 정체성, 기대 스냅샷, 평가일, cutoff, 원래 구성원과 발행사를 대조한다.
부족한 필드나 불일치 파일은 전체 요약 생성 실패이며 정상 빈 결과가 아니다.

## Main의 최소 연결

기존 `/kis/classification?part=expanded_summary` 응답은
`private-expand-live.js`의 `CC_KEY`에 따라 `classification.validate`의 `expanded`로 전달된다.
`expanded_summary`를 통합 판독기의 최상위 키로 직접 넣지 않는다.
새 part·Worker 권한·경로·2MiB 상한 변경은 필요하지 않다.

`expanded.calculation_counts.scopes`에서 다음을 읽는다.

| scope | 모집단 단위 | 화면 값 |
| --- | --- | --- |
| `operating` | `CODE_ROW` | `counts.Q`, `counts.G`: 운영504 코드 행 산출 수 |
| `held_financial_subsample` | `ISSUER` | `official_q_gate_input`: 보유1057 발행사의 기존 공식 Q 관문 입력 연결 |
| `catalog` | `ISSUER` | 관측8004 카탈로그. 기존 최상위 `official_gate_connected`의 범위 |

각 scope는 `population`(ID·버전·단위·분모·고유 발행사·구성원 해시),
`scoring_population`, `valuation_date`, `input_as_of`, `versions`, `classification`,
`result_identity`, `sources`(참조와 SHA-256)를 갖는다.
보유 재무 하위표본의 Q/G는 카탈로그 전체에서 이미 점수화한 값이다.
하위표본만으로 다시 점수화한 결과로 표시하지 않는다.
`versions.mapping_version`은 섹터 엔진의 대응표이고 `classification.mapping_version`은
공통 분류 대응표다. 두 이름의 버전을 혼합하지 않는다.

각 count는 `valid`, `denominator`, `uncomputed`, `status`, `reason`이다.

| status | 의미 |
| --- | --- |
| `PARTIAL` / `COMPLETE` | 해당 원결과에서 실제 산출된 수 |
| `NOT_COMPUTED` | 원래 분모에서 산출 0건. 기업 점수 0점이라는 뜻이 아님 |
| `EMPTY_POPULATION` | 명시적으로 확인된 빈 모집단 |
| `NOT_MEASURED` | 분자는 null. 이 요약에서 그 항목을 측정하지 않음 |

운영504 관문 감사는 이번 요약의 요청 범위가 아니므로 `NOT_MEASURED`다.
확장 관문 입력은 `CONNECTED_INPUT_NOT_GATE_PASS_NOT_SECTOR_Q`이다.
유효한 공식 Q 백분위 0도 입력 연결로 센다. 관문 통과 수나 새 섹터 Q 산출 수가 아니다.
`full_market_denominator`와 `full_market_coverage`는 원래 summary와 새 하위 계약 모두 null이다.
부분 모집단의 분모를 전체시장으로 표시하지 않는다.

Main은 새 내부 계약을 사용하기 전에 버전·필수 필드·정수 수량·분모 관계를 확인하고,
운영 scope의 평가일·모집단·공통 분류 해시를 실제 view와 맞춰야 한다.
확장 scope에는 독립 분류 해시와 모집단이 있으므로 운영 view 해시와 억지로 일치시키지 않는다.
새 필드가 누락되거나 불일치하면 해당 집계는 미측정/연결 오류로 둔다.
이 검증과 화면 두 항목 연결은 Main 소유다. 기존 판독기가 추가 키를 허용하는 것만으로
새 필드 검증·화면 표시 완료를 주장하지 않는다.

## 합성 인계

`implementation/tests/fixtures/classification_counts/summary.json`은 공개 가능한 수작업 입력에서
생성한 요약이다. `test_classification_counts.py`의 `inputs()`가 원입력·해시를 재현하고,
`test_main_fixture_matches_projected_bytes`가 공급 바이트와 대사한다.

- 운영: 코드 행 2, 고유 발행사 1. Q=1/G=2/V=0, 관문 입력 수는 null.
- 보유 하위표본: 발행사 2, Q=1/G=2, 관문 입력 연결 1.
- 카탈로그: 발행사 3, Q=2/G=2, 관문 입력 연결 2.
- 실제 점수 0과 공식 Q 백분위 0은 유효하다. V·동시·총점 산출은 0건이다.
- 집계와 기존 점수·순위에는 화면 필터를 적용하지 않는다.

## 실행·보존

기존 CLI의 새 `mode: summary-only`는 `classification-counts-job/1`을 받는다.
각 파일 descriptor는 `path`, `sha256`, `ref`를 갖는다. `expected`는 읽으려는
스냅샷·모집단·cutoff·분류 해시·설정 해시를 고정한다. 최신 파일로 자동 대체하지 않는다.
실자료 출력은 공개 checkout 밖에만 허용하며 기존 입력을 덮어쓰지 않는다.

```sh
PYTHONPATH=implementation/src python implementation/tools/expanded_held_classification.py \
  --job /private/job.json --output /private/new-summary/final
PYTHONPATH=implementation/src python -m pytest -q \
  implementation/tests/research/test_classification_counts.py \
  implementation/tests/research/test_expanded_held_classification.py::test_full_cli_preserves_missing_issuer_class_observations_and_uses_shared_raw_formula
```

출력은 `summary.json`, `replay-job.json`, `manifest.json`이다.
Main의 기존 staging에서 `--expanded-source /private/new-summary`와
`final/summary.json`을 열거한 인계 manifest를 사용한다. 기존 다섯 분류 파일은
이미 검증한 delivery-compatible 보존본을 재사용한다.
실자료 source ref·경로·요약·대사 증거는 비공개 인계에만 보존한다.
Worker 데이터 가지 갱신·화면·브라우저 실행·배포는 이 CLI가 수행하지 않는다.
