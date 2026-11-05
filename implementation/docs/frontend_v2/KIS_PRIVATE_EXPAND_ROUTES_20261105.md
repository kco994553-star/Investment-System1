# 비공개 펼치기 · 일곱 경로 (2026-11-05)

오너 승인 2026-11-05: 좁은 예외(`web_app/kis-private.js` 한 파일)에 읽기 경로 셋(technical · macro · news)을 같은 규칙으로 더함.
같은 화면, 같은 형식, 공개 부분은 그대로(DC-44). 계산은 Codex(DC-42): 화면은 확인하고 글로 옮기기만 함.

## 경로와 자료 위치

비공개 저장소 `data` 가지의 파일 하나를 Worker가 오너 확인 뒤 그대로 넘김(`implementation/worker/src/index.js` `KIS_FILES`).

| 경로 | 파일 (`<F>` = 기호 첫 글자) | 형식 | 읽는 곳 |
|---|---|---|---|
| `status` | — | kis-status/1 | (화면 미사용) |
| `chart?symbol=` | `chart/<F>/<SYM>.json` | kis-bars/1 | `IS2.kisPrivate.validateBars` |
| `analysis?symbol=` | `technical/<F>/<SYM>.json` | kis-bars/1/analysis | `validateAnalysis` |
| `technical?symbol=` | `measures/<F>/<SYM>.json` | kis-technical-measures/1 | `validateMeasures` (새로) |
| `qgv` | `qgv/latest.json` | kis-qgv/1 | `validateQgv` |
| `macro` | `macro/current.json` | macro-current-query/1 (#477) | 공개 읽기 `IS2.macroObserved.validate` |
| `news` | `news/current.json` | news-signals schema 2 `NEWS_SIGNALS` (#483 보관 재생) | 공개 읽기 `NewsSignals.validate` + `IS2.newsRefresh.validate` |

규칙(일곱 경로 모두): 클릭 안에서만(`PRIVATE_READ`), Bearer 헤더만, `credentials: omit`, `no-store`, `no-referrer`,
`redirect: error`. 서버가 읽을 때마다 오너를 확인. 저장·기록 없음. 한 클릭은 읽기 1~3개(`prices.kisRead`).

## 화면

- 3.1.1 기술(`tech-kis-chart`): 한 클릭에 analysis · chart · technical 셋. 다섯 측정값(모멘텀 3/6/12개월, 변동성 6개월,
  거래대금 6개월): 채택값은 value가 null이 아닐 때만 `[data-ram-price]` 안에, 진단값(raw_value, 거래대금 대용값)은 개수만,
  미산출은 사유 글, 관측 창·관측/기대 일수, 신호일·자료 기준일·수집 시각, 순위 없음. measures 파일만 없으면(404) 그 부분만
  "자료 없음"(EMPTY), 계약 위반이면 그 부분만 거부(REFUSED) — 분석·차트는 그대로.
- 4.1.3 매크로(`macro-observed-private`, 공개 관측 블록 아래): 공개 블록의 그리기 함수(`macroObservedLive.nodes`)로 그림.
  관측 값은 공개 블록처럼 표시 안 함.
- 5.2.7 뉴스(`news-refresh-private`, 공개 원천별 표 아래): 공개 표 함수(`refreshBox`)로 그림.
- 매크로·뉴스 머리: "비공개 보관본 · 인증 경로"와 두 층 줄(`K.LAYER_NOTE`). 공개 블록은 비공개를 기다리지 않음.

상태: 설정 없음 NOT_READY · 로그인 필요 LOGIN_REQUIRED · 불러오는 중 · 표시 READY · 파일 없음 EMPTY · 계약 위반 ERROR(통째 거부)
· 403은 토큰을 버리고 다시 로그인 · 만료 토큰은 읽기 전에 버림 · 접기/연결 끊기는 보인 것을 지움.

`validateMeasures` 거부: schema · publication_scope · result_kind · 다섯 측정 키(빠짐/추가) · 단위 · state와 값 불일치(VALUE ⇔
value, DIAGNOSTIC = raw만+사유, NOT_COMPUTED = 둘 다 없음+사유) · 창 순서 · 일수 · raw/adopted 개수 · rank_count ≠ 0 ·
rank 필드가 null 아님. 첫 오류에서 파일 전체를 거부.

## 합성 전용 (실자료 미표시)

- 시험 자료는 모두 합성: `tools/web_app_kis_private_fixture.js`의 `measures()`는 Codex 출력의 키·값 형태·state 규칙만 보고 손으로
  만듦(Codex 코드 `technical-measures` 모드는 이 저장소에 아직 없음 · 실파일 숫자는 쓰지 않음). 매크로·뉴스는 공개 화면의 합성
  고정 파일을 재사용.
- 실제 Worker 배포, 비공개 저장소의 macro/ · news/ · measures/ 파일 게시, 스케줄은 이 작업 범위 밖(별도 승인).

## 실제 보관본 재생 확인 (2026-11-05)

**구성:** 비공개 저장소 `data` 가지(ad3c903)의 실제 보관 파일 6개를 이 가지의 실제 Worker 코드(`createHandler`)와 실제 화면(로컬 개발 사이트, 크롬)에 연결했다. 진짜가 아닌 대역은 셋뿐이다.
- Google 토큰 확인 응답
- GitHub contents 전송(`data` 작업 트리 바이트를 그대로 넘김)
- Worker가 허용하는 앱 출처 머리글

재생 도구는 저장소에 넣지 않았다. 값은 출력하지 않았고 상태·날짜·개수만 확인했다.

| 화면 | 결과 |
| --- | --- |
| 기술 2-1 (AMD) | READY. KIS 보관 일봉(MODP=0) · 원주가 · 가격 기준일 2026-10-23 · 갱신 지연(평가일 2026-11-04) · 직접 비교 제한. 진단값 12 · 채택값 5 · 미산출 8. 종가 선, 다섯 측정 칸 |
| QGV 2.1.6 | READY. Q 485/504 · G 493/504 · V 0/504 · 세 축 0/504. 비공개 순위 없음. AMD는 V 미산출(AXIS_WEIGHT_INSUFFICIENT) · 총점 미산출. 공개 기준일과 다름 |
| 매크로 | READY. 14계열의 조회 시각·캐시 기준·갱신 상태·stale·값 유지·미산출 수. 관측값은 보이지 않음(공개 규칙과 같음) |
| 뉴스 | READY. 원천별 마지막 성공·마지막 시도. GDELT 실패(이전 자료 유지), IR 일부 실패. 수정·중복은 미제공 |
| 경계 | localStorage·sessionStorage에 아무것도 없음. Worker가 읽은 파일은 6개 경로뿐 |

**이 확인으로 찾아 고친 결함 2건(합성 시험은 통과하던 것):**
1. **Worker의 schema 검사:** 실제 파일은 schema 키의 콜론 뒤에 공백을 둔다. 문자열 찾기 검사가 이 파일을 거부했다. 지금은 JSON을 해석해 schema 값을 비교한다. 바이트는 그대로 넘긴다.
2. **한 클릭의 여러 읽기:** Worker는 오너 요청을 한 번에 하나만, 5초 간격으로 받는다(MIN_SPACING_MS). 한 클릭에서 읽기 2~3개를 동시에 보내면 첫 하나 말고는 429로 거부됐다. 지금은 차례로 5초 간격을 두고 읽고, 한도 거부 때 한 번 다시 시도한다. 시험용 가짜 Worker도 같은 한도를 지킨다.

**아직 아닌 것:** 배포된 Worker를 거친 확인이 아니다. 실제 Google 로그인도 하지 않았다. 남은 조건은 Worker 읽기 토큰 등록과 수동 배포다.
