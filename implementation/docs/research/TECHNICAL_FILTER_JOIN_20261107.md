# 기술 필터의 평가일·고정 증권 결합 — 연구 구현과 Main 인계

작성: 코덱스, 2026-11-07. 작업 가지 `research/technical-filter-join-20261107`.
기반은 #498 `5597e25e0f1eef13432250d6ebfb440f7da152f5`이고 canonical
`ab6a83c3be2276abdcf855c71c5f273926e2dcc4`를 포함한다. 기존 #498 머리는 보존한다.
DC-42에 따른 연구·자료 구현이다. 화면·가드·CI 목록·워크플로·결정 문서는 변경하지 않았다.

## 기존 코드 재사용과 추가 범위

- `technical-leaderboard/1`과 Main `tech-screen.js::validate/evaluate`의 입력 형식을 그대로 쓴다.
  `inputs.json`은 기존 `{data_kind, cases: {original_board: board}, ...}` 형태다.
  결합 입력과 기대 결과는 보드 바깥에 두어 strict 판독기의 필드를 바꾸지 않는다.
- 이미 계산한 조건 선택은 `technical_leaderboard.filter_board`를 그대로 호출한다.
- 고정 증권 매핑은 `private_technical_board.SECURITY_IDENTIFIER_TYPES`와 기존 link 필드
  `series_id, security_id, identifier_type, reference, valid_from, valid_to`를 재사용한다.
  날짜는 `kis_price_bridge._day`로 검사한다.
- 기존 함수에는 QGV 행의 날짜·고정 증권·발행사 관계를 함께 검사하는 결합기가 없었다.
  연구 소유 `technical_filter_join.join_filtered_rows`만 추가했다. 가격·점수·순위 엔진은 만들지 않는다.

## 결합 계약

키는 정확히 **`(signal_day, security_id)`**다. `signal_day`는 실제 계산 평가일이며,
조회일·수집일·게시일·최근 확보일로 대신 채우지 않는다. 서로 다른 날짜의 동일 증권도 결합 실패다.

| 필드 | 의미와 제약 |
| --- | --- |
| QGV `id` | 기존 Main 행의 `company_id`, 즉 발행사 ID. 결합키가 아니다 |
| QGV `ticker`, `code` | 표시 티커와 Universe 코드. 증권 ID로 승격하거나 대체 결합하지 않는다 |
| QGV `security_id` | 이미 검증된 고정 증권 ID. 현재 값이 없으면 null/결손 그대로 두고 결합 실패 |
| QGV `signal_day` | QGV 행의 계산 평가일. 기술 보드의 평가일과 정확히 같아야 한다 |
| link `issuer_id` | 해당 증권을 발행한 발행사. QGV `id`와 일치해야 한다 |
| link `symbol` | 해당 유효기간에 그 증권을 가리키는 티커. QGV `ticker`, 기술 행의 선택적 `symbol`과 일치해야 한다 |
| link `share_class` | 검증된 종류주 구분. 같은 발행사의 다른 종류주는 다른 증권 ID를 유지한다 |
| link `series_id` | 기술 보드의 실제 입력 시리즈. 같은 티커의 다른 시리즈를 임의로 연결하지 않는다 |
| link `identifier_type`, `reference` | 기존 허용 ID 유형과 증권 매핑 근거. 발행사·티커 문자열을 증권 ID로 사용하지 않는다 |
| link `identity_status`, `identity_reference` | 이번 결합은 `CONFIRMED`와 신원 근거를 요구한다. 기존 단일 기업 진단의 `DOCUMENT_RECONSTRUCTED` 허용 범위는 바꾸지 않는다 |
| link `valid_from`, `valid_to` | 발행사·증권·티커·종류주·시리즈 관계 전체의 유효기간. 양 끝 날짜 포함. 평가일을 포함하는 매핑이 정확히 하나여야 한다 |

발행사는 여러 종류주를 가질 수 있고, 티커는 시기별로 다른 증권에 재사용될 수 있다.
과거와 현재 매핑은 겹치지 않는 유효기간으로 함께 보관할 수 있다. 평가일에 겹치는 매핑,
같은 기술 지표 안의 중복 증권 행, QGV의 중복 결합키는 거부한다. 서로 다른 종류주/증권은
대표 증권이라는 이유만으로 합치지 않는다. 검증된 매핑이 있어도 **서로 다른 증권 ID 간 결합**을
이 어댑터가 허용하는 것은 아니다.

함수는 근거가 첨부된 입력 계약을 검사하며 근거의 진실성을 새로 조사하는 도구가 아니다.
임의 ID 생성·실자료 신원 채움·새 신원 검색은 하지 않았다. `SYNTHETIC:*` 또는 합성 ID 유형은
`data_kind=SYNTHETIC`에서만 허용하고, `RETAINED_INPUT`에 끼워 넣으면 거부한다.

호출 전 보드는 기존 Main 판독기 또는 기존 보드 빌더에서 검증된 것이어야 한다.
어댑터는 수치 계약 검증기를 복제하지 않고 결합 경계(날짜·고정 ID·지표 간 신원 일치)를 추가한다.
한 요청 묶음에 문제가 하나라도 있으면 `ValueError(사유코드)`로 전체 결합을 거부한다.
필터에서 탈락할 행도 먼저 검사한다. 호출자는 결합 실패를 표시하고 티커/회사 ID 경로로 재시도하지 않는다.

성공하면 조건을 만족하는 QGV 행의 복사본만 입력 순서대로 돌려준다. QGV의 `score`, `rank`,
원래 모집단 수 `rank.of`는 그대로다. 기술 보드의 N·중앙값·점수·순위·분위도 그대로이며,
원래 보드는 변경하거나 필터 이후 다시 만들지 않는다.

## 공개 합성 입력과 기대 결과

위치: `implementation/tests/research/fixtures/technical_filter_join_v1/`.
`inputs.json`에 기존 화면용 보드 하나와 결합 시나리오별 입력을 넣었고,
`expectations.json`에 오류 또는 선택 행·원래 QGV 점수·순위를 고정했다.
모든 기업·증권·수치는 저자 생성 합성값이다. 실제 가격·기업 신원·회사 자료는 없다.
기존 private board 투영 형식의 `publication_scope`는 그대로 유지한다.

| 시나리오 | 기대 |
| --- | --- |
| 같은 날짜·같은 증권 | 성공. 기존 QGV 순위 4·9, 점수 80·70, 모집단 10 유지 |
| 다른 날짜 | `SIGNAL_DAY_MISMATCH` |
| 같은 티커·다른 증권 | `SECURITY_ID_NOT_IN_BOARD` |
| 같은 발행사의 다른 종류주·검증 맵 없음 | `SECURITY_ID_NOT_IN_BOARD` |
| 매핑 누락 | `FIXED_SECURITY_LINK_MISSING` |
| QGV 결합키 중복 | `DUPLICATE_QGV_KEY` |
| 매핑 중복 | `DUPLICATE_SECURITY_LINK` |
| 만료된 매핑 / 아직 유효하지 않은 매핑 | 각각 `SECURITY_LINK_OUTSIDE_SIGNAL_DAY` |
| 유효기간 양 끝이 모두 평가일 | 성공 |
| 고정 증권 ID 누락 | `PERMANENT_SECURITY_ID_REQUIRED` |

추가 시험은 기술 보드 중복·지표 간 시리즈 불일치·합성 ID의 실자료 혼입·티커/발행사 ID 대체·
미확인 신원·근거 없음·발행사/티커 불일치·미확인 모집단을 거부한다.

## Main 지원 요청 — 정확한 변경 지점

1. `product/web_app/qgv.js::rowRecord`는 현재 `id, ticker, code, score, rank`를 내지만
   `signal_day, security_id`는 내지 않는다. 기존 보관 근거가 제공하는 **두 필드만 추가**하고,
   근거가 없으면 결합 불가를 유지한다. 이 작업이 실제 신원 채움 승인은 아니다.
2. `product/web_app/screen-tech-filter-live.js::joinOf(rows)`는 현재
   `by.set(r.id, r)`와 `by.set(r.code, r)`를 만든 뒤 기술 `security_id`로 찾는다.
   이 결합을 같은 날짜·검증된 고정 증권 ID·활성 매핑 검사로 교체한다. 기존
   `tech-screen.js::validate/evaluate`와 `keep` 이후의 QGV 정렬·원래 순위 표시는 재사용한다.
3. Python 어댑터를 서버에서 호출하거나 동일 계약을 Main의 순수 JS 결합기에 적용할 수 있다.
   소비자 시험은 이번 `inputs.json`/`expectations.json`을 그대로 읽어 위 실패를 확인한다.
   화면 미연결 시 현재 표를 기술 필터 적용 성공으로 표시하지 않는다.
4. 신규 연구 시험 `tests/research/test_technical_filter_join.py`는 기존
   `.github/workflows/cockpit-pages.yml`의 `Full Python unit suite`
   (`PYTHONPATH=src python -m pytest -q --tb=short -p no:cacheprovider tests`)에서 자동 발견한다.
   별도 CI 목록 등록·워크플로·가드 변경은 필요 없다.
   #497의 성질 시험 의존성과 기존 성공시험은 이번에 반복하지 않았다.

현재 Main 화면은 이 계약을 아직 소비하지 않는다. UI 완료·실자료 연결 완료로 계산하지 않는다.

## 실행과 한계

일반 재현 명령(저장소 루트에서 실행):

```sh
PYTHONPATH=implementation/src python -m pytest -q implementation/tests/research/test_technical_filter_join.py
```

Python과 시험 의존성은 저장소 `.github/workflows/cockpit-pages.yml`의 설치 절차를 따른다
(현재 Python 3.12, `pytest==9.1.1`, `jsonschema==4.26.0`). 새 fixture를 기존 Main 판독기에
직접 넣는 시험은 `node` 명령도 사용한다. 이 변경에서 새 의존성은 추가하지 않았다.

당시 실행 환경에는 pytest 8.4.2가 이미
`/workspace/scratch/technical-leaderboard-test-deps`에 설치돼 있어 위 명령의 `PYTHONPATH`에
그 경로를 덧붙여 사용했다. 이는 기존 설치를 재사용한 당시 환경 기록이며,
다른 세션에서 그 경로를 만들거나 같은 위치에 설치할 필요는 없다.

결과: 신규 시험 **13 passed**. 공개 합성 시나리오 11개, 추가 실패 경계 10개,
과거 매핑이 평가일의 신원을 덮어쓰지 않음과 기존 Main `techScreen.validate/evaluate`로
**새 fixture** 직접 판독을 확인했다.
기존 동일 성공시험·전체 계산시험·실측은 실행하지 않았다.

**실제 채택 증가 0, 새 실측 0, 새 신원 확보 0.** 합성 계약 통과를 실제 자료 채택이나
운영 결합 완료로 세지 않는다. 병합·배포·수집·외부 메시지는 실행하지 않았다.
