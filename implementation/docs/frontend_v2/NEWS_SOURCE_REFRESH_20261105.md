# 5.2.7 원천별 갱신 기록 — 뉴스 화면과 `news-signals.json` schema 2 `refresh` 연동

작성 2026-11-05 · Main.

근거는 다음과 같다.
- 오너 지시(11/05): "뉴스: 원천별 마지막 성공·부분 실패·신규·중복·변경을 표시한다. 일부 원천 실패 때문에 정상 수집된 다른 원천까지 숨기지 않는다. 근거가 없는 요약·영향·컨센서스는 미산출로 표시한다."
- Codex #483(Draft, head `e3154ee3`) 문서 `implementation/docs/daily_data_pipeline/NEWS_SIGNALS.md` "공개 파일 형식 (schema_version 2, 별도 파일)", `product/news_signals.py`(`source_refresh`, `refresh_result`, `merge`), `providers/news_update.py`.
- 계산은 Codex, 화면은 Main이다(DC-42). 이 기록은 병합·배포·공개 데이터 범위 변경 승인이 아니다.

## 1. 읽는 것

- 공개 파일 `news-signals.json`을 자료층(`IS2.data.list('news')`)으로 읽는다. 새 요청은 없다.
- 자료층은 schema 2를 **이미 받는다**. 옛 판독기 `web_assets/news-signals.js`의 `validate`가 schema 1·2를 모두 검사하고, `refresh.sources[S]`를 회사 항목에서 다시 유도해 대조한다. 그래서 `data.js`와 옛 사이트는 바꾸지 않았다.
- #483은 공개 파일 형식을 바꾸지 않는다(문서: "공개 JSON 스키마…은 이 변경에 없다"). 바뀐 것은 같은 링크의 제목 수정 반영, 오래된 입력의 `NOT_RUN/OLDER_INPUT` 이월, 로그의 `revisions=` 개수다.
- 새 판독기 `web_app/news-refresh.js`(`IS2.newsRefresh`)는 화면에 보이는 `refresh` 칸만 다시 검사한다. 주입된 자료도 검사 없이 화면에 닿지 않는다.
  - 정확한 키, 시각 형식(`…+00:00`)
  - `attempted_at` = `as_of`, 각 `last_attempt_at` = `attempted_at`
  - 결과 값: UPDATED · NO_NEW_ITEMS · PARTIAL_FAILED · FAILED · NOT_RUN
  - `last_result_code`: 성공 두 값일 때만 null, 그 밖에는 고정 코드
  - 회사 수·`new_items`는 0 이상의 정수
  - 결과와 파일이 적은 회사 수가 맞는지(모두 응답 → UPDATED/NO_NEW_ITEMS, UPDATED는 새 항목 > 0일 때만; 일부 → PARTIAL_FAILED; 응답 0 → FAILED 또는 NOT_RUN)
  - `items_carried_from`은 모두 응답했으면 null, 있으면 `last_success_at` 이전
  - `refresh.result`는 두 원천 종합, `reason_codes`의 `REFRESH_*`는 결과와 일치
- 첫 위반에서 이 칸 전체를 쓰지 않는다. 다시 계산하거나 채우지 않는다.

## 2. 화면 (#/news, 4.2 → 5.2.7 수집 상태)

새 화면·경로는 없다. 기존 수집 상태 칸 아래 "원천별 갱신 기록" 표를 더했다(항목 | GDELT | 회사 IR).

| 항목 | 출처 필드 | 없을 때 |
| --- | --- | --- |
| 마지막 성공 | `last_success_at` | 미산출 · 응답 받은 적 없음 |
| 마지막 시도 | `last_attempt_at` | — |
| 결과 | `last_result` (+코드) | 갱신 / 새 항목 없음 / 일부 실패 (코드) / 실패 (코드) / 미실행 (코드), 실패면 이전 자료 유지 또는 이전 자료 없음 |
| 회사 | `companies` | 성공 · 실패 · 미실행 수 (0은 값) |
| 이번 새 항목 | `new_items` | (0은 값) |
| 이월 시작 | `items_carried_from` | 이월 없음 · 모든 회사 응답 / 이월 없음 · 이전 자료 없음 |
| 수정 | 공개 파일에 없음 | **미제공** (0으로 쓰지 않음) |
| 중복 | 공개 파일에 없음 | **미제공** |

- 두 원천은 항상 나란히 그린다. GDELT가 실패해도 IR 열과 IR 기사 행은 그대로 보인다. 실패한 원천의 이월 행도 목록에 남는다.
- 표는 파일 전체 기준이다. 기존 원천별 한 줄(보는 범위의 기업 기준)과 배지는 그대로다.
- 위에 이번 실행 시각과 종합 결과 한 줄이 있다.
- schema 1 사본: "원천별 갱신 기록 없음 · 이전 형식 파일 (schema 1)". 수집 없이 만든 파일(`refresh` null): "… 수집 없이 만들어짐". 파일이 없으면 그 말만 쓰고 숫자는 그리지 않는다.
- 주입된 합성 자료(`source()` 대체, 시험 전용)면 "합성 개발 검증 · 실제 수집 결과 아님"을 보인다.
- 5.2.2 요약 · 5.2.3 영향 · 5.2.6 컨센서스는 그대로 미산출이며 사유를 적는다(IA-14, 외부 모델 호출 승인, 무료 컨센서스 자료원).

## 3. 시험 자료

- `implementation/tests/fixtures/news_signals_refresh_v2_synthetic.json`(SYNTHETIC). #483 소스를 임시 폴더에 풀고 그 `news_signals.merge`를 합성 입력으로 세 번 실행해 만들었다(`python3 -I`).
  - `first_run`: 두 원천 응답.
  - `gdelt_429_ir_updated`: GDELT 첫 회사 FAILED HTTP_429 · 나머지 18곳 NOT_RUN, IR 10곳 응답(새 2건, 제목 수정 1건). 로그 개수 `revisions: 1`은 파일 밖에 따로 적었다.
  - `both_no_new_items`: 두 원천 응답, 새 항목 없음.
- 모든 사례가 옛 판독기와 새 판독기를 통과한다.
- 시험
  - `tools/web_app_news_refresh_node_test.js`: 11개
  - `tools/web_app_news_refresh_browser_test.js`: 1440·390 실 Chromium, 7개 맥락. 자료층 경로, schema 1, 실행 없음, 404, 합성·계약 위반 주입, 요청·저장·스타일·가로 넘침 경계

## 4. 하지 않은 것 · 승인 필요

- 수정·중복 개수 공개: Codex가 공개 파일에 넣지 않았다. 넣으려면 schema 변경(Codex)과 옛 판독기 키 목록 변경이 함께 필요하다.
- 로컬 상태 `LOCAL_NEWS_UPDATE_STATE`(NEW·DUPLICATE·REVISION, `version_id`)는 비공개 작업 자료라 읽지 않는다.
- 새 수집·예약·워크플로·비밀값·배포는 없다. GDELT 429는 그대로이며 이 화면은 원인을 고치지 않는다.
- 실제 게시본은 #483 병합과 일일 실행 뒤에 같은 경로로 보인다. 병합은 오너 승인 대상이다.
