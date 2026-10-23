# TARGET v1 확정 리허설 (B-3, 2026-10-23)

> **상태: 기록 문서.** 화면·가드·워크플로·설정은 바꾸지 않았다. 합성 자료만 썼다. 가격 값은 없다.

- 작성: 2026-10-23 12:20 UTC / 2026-10-23 21:20 KST.
- 기준 코드: `claude/number-check-fcf-20261023` 65fe33e2 (canonical db66d312 + #386 숫자 검증 기록).
- 시험 파일: `implementation/tools/target_v1_finalize_rehearsal_browser_test.js` (CI 목록에 넣지 않음).
- 인용은 `파일:줄`이다. `B` = `src/investment_system/product/web_assets/target-v1-builder.js`, `S` = 같은 폴더 `target-v1-screen.js`.

## 1. 무엇을 했나

- 합성 504개 기업(티커 `RZnnn`, 만든 CIK·지표·Q·G 요인·V 입력)을 만들었다.
- 합성 기기 가격과 합성 월말 종가를 RAM으로만 넘겼다. 엔진은 실제 화면과 같은 `QgvScores.compute`다.
- 폰 폭 390과 PC 폭 1280에서 화면 버튼으로 초안 → 카드 15장 응답 → 확정까지 갔다.
- 확정 조건을 하나씩 깨고 차단 사유와 상태 문구를 확인했다.
- 결과: 390·1280 모두 PASS. 외부 요청 0, 페이지 오류 0, 가로 스크롤 없음, 기기 저장소에 가격 키 없음.

실행 방법:

```
python3 implementation/tools/build_pages_cockpit.py --out <tmp>/site
python3 -m http.server <port> --bind 127.0.0.1   # <tmp>/site 안에서
PAGES_COCKPIT_URL=http://127.0.0.1:<port>/ CHROMIUM_EXECUTABLE_PATH=<chromium> node implementation/tools/target_v1_finalize_rehearsal_browser_test.js
```

## 2. 조건별 리허설 결과 (폰 390, 확정일 2026-11-10)

| 깬 조건 | 화면 차단 사유 | 상태 줄 |
| --- | --- | --- |
| 없음(전부 충족, NA 50행 = Q·G 454/504 경계) | 없음 · 저장됨 | `TARGET v1 저장 · calc_version qgv2-calc/2026-10-17.1 · R-C(규칙 지수) 2026-11-10 시작` |
| 숫자 검증 미통과(canonical 상태) | `NUMBER_CHECK_NOT_PASSED` | 숫자 검증(10-K 대조) 통과 전에는 … 확정 저장할 수 없습니다 |
| 숫자 검증이 다른 calc_version | `NUMBER_CHECK_CALC_VERSION_MISMATCH` | 다른 calc_version 파일로 했습니다 … |
| 공개 파일 못 읽음 | `SEC_QGV2_NOT_AVAILABLE`, `NUMBER_CHECK_CALC_VERSION_MISMATCH` | 최신 공개 sec-qgv2.json을 읽지 못함 |
| calc_version 없는 이전 형식 | `CALC_VERSION_MISSING`, `DRAFT_BASIS_CHANGED`, `NUMBER_CHECK_CALC_VERSION_MISMATCH` | calc_version 없음 |
| 값 있는 1행이 다른 calc_version | `CALC_VERSION_MIXED` | 행마다 calc_version이 다름 |
| 값 있는 1행 수집 8일 전 | `ROW_DATA_STALE` | 7일을 넘음 + 전체 샤드 수동 실행 안내 |
| Q 453/504 | `Q_COVERAGE_LOW` | Q 산출 종목 90% 미만 |
| G 453/504 | `G_COVERAGE_LOW` | G 산출 종목 90% 미만 |
| 정상 NA 51행 | `Q_COVERAGE_LOW`, `G_COVERAGE_LOW` | (NA는 분모에 남음) |
| NA 사유 없는 빈 행 3개 | `CALC_VERSION_MIXED` | 행마다 calc_version이 다름 (문구가 원인과 다름, F2) |
| 새 calc_version · 다른 as_of | `DRAFT_BASIS_CHANGED`, `NUMBER_CHECK_CALC_VERSION_MISMATCH` | 페이지를 새로 고친 뒤 다시 확정하세요 |
| 새 calc_version · 같은 as_of | 초안 재생성 후 `NUMBER_CHECK_CALC_VERSION_MISMATCH` | 응답 유지 15 · 새로 확인할 종목 0 |
| 선정 종목 재무 안전 FAIL | `FINANCIAL_SAFETY_RECHECK_FAILED` | 재무 안전 재검사 불통과 |
| 선정 종목 재무 안전 NA | `FINANCIAL_SAFETY_RECHECK_FAILED` | (NA도 불통과) |
| 카드 미응답 | 확정 버튼 비활성 | — |
| 반대 + 이유 없음 | 거절 | 반대 이유를 한 줄로 적어 주세요 |
| 월말 종가 없음(V4 전부 없음) | `V_FACTORS_V3_V4_MISSING` | 초안은 됨 · 후보 30개 모두 `4/5 V4 빠짐 · 확정 불가` |
| 기기 가격 0 | 통과 0 · 부족 15 · 버튼 비활성 | 축 산출 50% 미만 504 |
| 기기 가격 60종목 | 통과 55 · 후보 30 · 카드 15 | 확정 가능(카드 응답 후) |
| 경기민감 SIC 포함(반도체 3674 등) | `V_FACTORS_V3_V4_MISSING` | 선정 4/15 표시 → 반대 7번 뒤 저장 |
| 11-16 미확정 | 일정 문구 | 목표 주까지 조건 미충족 · 확정 연기 · 11월 회차는 위험 코드 점검만 |
| 11-16 늦은 확정 | 저장됨 | 1회차(11-16)에 종목 목록 표시 (F1) |

## 3. 발견

- **F1 (규칙 어긋남).** 마감(11-15) 뒤 11-16에 확정하면 1회차(11-16)가 종목 목록을 보인다. 사용자 규칙은 "미충족이면 연기 · 11월 회차는 위험 코드 점검만"이다. 원인 `B:335` `roundMode`가 `v.date<=round.date`만 본다. 제안(수정하지 않음):

  ```js
  function roundMode(state,round,cfg=CFG){const v=latestVersion(state),S=cfg.schedule;
   if(!v||!round||!validDay(round.date)||v.date>round.date)return S.unfinalized_round_mode;
   // 마감 뒤 확정은 마감이 속한 달의 회차 목록을 열지 않는다(2026-10-15 결정: 연기 → 11월 회차는 위험 코드 점검만).
   if(v.date>S.deadline&&round.date.slice(0,7)===S.deadline.slice(0,7))return S.unfinalized_round_mode;return 'LIST';}
  ```
- **F2 (문구).** NA 사유 없는 빈 행이 `CALC_VERSION_MIXED`로 막힌다(`B:251`). 막는 것은 규칙대로다. 문구 `S:24` "행마다 calc_version이 다름"은 원인과 다르다. 제안: `'행마다 calc_version이 다르거나 NA 사유 없는 빈 행이 있음'`.
- **F3 (기능 없음).** TARGET 화면에 V 출처 표시가 없다. "임시 V" 문구도, `qgv-official.json` 읽기 경로도 없다(`web_assets` 전체 검색 0건). 확정 기록에도 V 출처 필드가 없다(`B:317`).
- **F4 (규칙 결과).** 경기민감으로 분류된 종목(`qgv-scores.js:230` → `qgv-v2.js:114`, Python 쌍 `qgv2_inputs.py:380`)은 V4가 늘 `NORMALIZED_HISTORY_NOT_AVAILABLE`이다. 반도체(3674)·장비(3559)도 여기에 든다. 10-23 결정대로면 이 종목들은 TARGET v1에 확정될 수 없다. 선정되면 사용자가 반대로 빼야 한다. 중앙 V도 같은 분류를 쓰므로 결과가 같다.
- **F5 (운영 여유 없음).** 신선도 7일과 7개 샤드 하루 1개 갱신이 맞물린다. 그날 정기 실행 배포(최근 10:20 KST 무렵) 전에 누르면 가장 오래된 샤드가 7일을 넘을 수 있다. 정기 실행이 하루라도 실패하면 그 샤드가 막힌다.

## 4. 폰 화면 흐름

1. 사이트를 연다. 아래 탭 줄에서 `포트폴리오`를 누른다.
2. `TARGET v1 작성 →` 링크를 누른다 → 플레이북(`#playbook`).
3. 아래로 내려 `TARGET v1 빌더 · 규칙 기반 선정` 카드를 본다.
   - 가격이 없으면: `NA · QGV v2 총점에는 V가 필요 …` · 초안 버튼 비활성.
   - 가격이 있으면: `QGV v2 계산됨 · 기기 가격 n종목`.
4. `규칙으로 초안 만들기`를 누른다 → `초안 만듦 · 통과 n · 후보 30 · 입력 기준 qgv2-calc/…`.
5. 후보 30 표에서 `V 요인` 칸을 본다. `5/5` 또는 `4/5 V4 빠짐 · 확정 불가`.
6. 카드 15장에 `동의`/`반대`/`모름`을 누른다. 반대는 한 줄 이유가 먼저 필요하다. 반대한 종목은 빠지고 다음 순위가 들어온다.
7. `TARGET v1 확정` 카드: `응답 15/15 · 16절 한도 통과`, 숫자 검증 줄, 일정 줄을 본다.
8. `TARGET v1 확정 저장`을 누른다. 그 순간 공개 파일을 다시 읽는다.
   - 통과: `TARGET v1 저장 · calc_version … · R-C(규칙 지수) … 시작`, `확정 검사 통과` 줄.
   - 차단: `확정 불가 · 사유 n개` 목록과 첫 사유 문구. 숫자 검증·초안 재생성은 전용 문구.
