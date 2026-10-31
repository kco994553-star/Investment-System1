# 시작 문서 — 모든 AI 세션은 이것부터 읽는다

이 저장소는 사용자 한 명이 폰으로 지휘하는 투자시스템 웹이다. 문서가 많고 방향이 여러 번 바뀌었다. **아래 순서대로만 읽고, 여기와 다른 옛 문서는 따르지 않는다.**

## 1. 읽는 순서

1. **이 파일**
2. [docs/SPEC/DIRECTION_CHANGES.md](docs/SPEC/DIRECTION_CHANGES.md) — 바뀐 방향과 금지 표현. **가장 자주 틀리는 곳이다.**
3. [WORKING_RULES.md](WORKING_RULES.md) — 작업 규칙
4. [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md) — 지금 상태(기준 HEAD·게시·열린 PR·다음 할 일)
5. [docs/SPEC/FUNCTION_HIERARCHY_v1.0.md](docs/SPEC/FUNCTION_HIERARCHY_v1.0.md) — 제품 기능 명세 원문(수정 금지)
6. [docs/SPEC/FUNCTION_STATUS.md](docs/SPEC/FUNCTION_STATUS.md) — 명세 번호별 현황과 메뉴 번호 대응표
7. [implementation/docs/USER_DECISIONS_PENDING.md](implementation/docs/USER_DECISIONS_PENDING.md) — 결정 원문과 남은 결정

루트의 2026-09 문서와 `SUPERSEDED` 머리말이 붙은 문서는 **기록 보존용**이다. 현재 상태 판단에 쓰지 않는다.

## 2. 절대 틀리면 안 되는 것 (상세는 DIRECTION_CHANGES)

- **Universe504** = S&P 500 구성에서 출발해 **고정한** 504코드 목록이다. 시가총액 상위 504가 아니고, S&P 500 지수를 따라가지도 않는다(DC-01).
- **공식 V** = 서버가 IEX HIST로 계산해 공개하는 점수·순위(2026-10-23 결정, 2026-10-29 첫 게시, 정밀값 공개 허용 GSQ-025). 원시 가격은 공개하지 않는다. **기기 V는 폐지됐다(DC-31, 2026-10-31, #435·#439 병합)**: 화면은 중앙 V만 보이고, 중앙 V가 없거나 늦으면 마지막 중앙 V를 갱신 시각·STALE과 함께 보인다(기기 값으로 채우지 않음). TARGET v1 빌더만 11/16 PR까지 옛 V 출처를 유지한다.
- 화면 점수는 **QGV v2만**(DC-03).
- **TARGET v0(카탈로그 19, `actual-catalog.json`)은 QGV와 전혀 무관하다.** 사용자가 QGV 없이 고른 목록이다(DC-04). QGV 화면·점수·순위·후보·공개 데이터의 "TARGET"에 v0을 쓰지 않는다. 공개 TARGET은 **확정된 TARGET v1만**이다(DC-24, 사용자 2026-10-27: "이유를 계속 잊는 것 같다").
- 기능 번호는 **명세 v1.0의 1~9**만 쓴다. 메뉴 번호(0 검색, 1 QGV…)로 보고하지 않는다(DC-08).
- 새 프론트엔드는 **시안(같은 아티팩트) 배치대로 새로 작성** 중이다. 무채색 미니멀 지시는 대체됐다(DC-07). 시각 양식은 **혼잡스 영상 기준(DC-25, [VISUAL_STYLE](implementation/docs/frontend_v2/VISUAL_STYLE.md))**: 흰 바탕 선화, 제목 Jua·본문 기기 고딕, 그림자 없음. 색은 6가지에 뜻 하나씩, 메뉴별 색 없음(DC-26).
- 역할(DC-32, 2026-10-31): 병합·공용 파일·워크플로·`docs/SPEC`·인수인계·결정 문서는 **Main만**. 화면 세션(Frontend)은 아래 4절 담당 화면 파일만 바꾸고 Draft PR까지만. Codex는 연구 가지와 문서만.

## 3. 매 작업 규칙

- 사용자가 방향을 바꾸면 **같은 PR에서** DIRECTION_CHANGES에 한 줄을 더한다. 결정만 하고 코드가 아직 옛 방향이면 "구현 상태"에 그렇게 적는다.
- 기능을 병합하면 FUNCTION_STATUS의 해당 번호 줄을 같은 PR에서 고친다.
- 금지 표현 검사: `python implementation/tools/spec_direction_guard.py`(CI 전체 시험 `test_spec_direction_guard.py`에 포함).
- 원시 가격·개인 자료·토큰·이메일은 저장소·Pages·로그에 넣지 않는다. 병합·배포는 사용자 승인 범위에서만 한다.
- 사용자는 폰만 쓴다. 사용자에게 시키는 절차는 폰 브라우저에서 할 수 있어야 한다. 보고는 한국어로 묶어서 한다.

## 4. 파일 담당표 (2026-10-31, DC-35 — DC-32를 대체)

개발 흐름은 둘이다(결정 문서: [DEV_SYSTEM_20261031](implementation/docs/DEV_SYSTEM_20261031.md)).

| 담당 | 파일 | 할 수 있는 것 |
| --- | --- | --- |
| **Main** | `implementation/src/investment_system/product/web_app/` 전부(화면 파일 `screen-*.js` 포함), 옛 화면(`web_assets/`), 공용 엔진, 가드·CI 목록, 워크플로, `docs/SPEC`, CURRENT_HANDOFF, USER_DECISIONS_PENDING, 결정 문서, 데이터 계약(lab-backtest-v1, 기업 목록 공통 접근 계약) | 바꾸고 병합한다(병합·배포는 오너 승인 범위에서). 독립 화면은 하위 에이전트로 병렬 구현할 수 있다 |
| **Codex** | 백테스트 연구 가지(`research/*`)의 연구 코드·결과 원본·연구 문서(백테스트 한정 예외) | 연구 PR까지. 병합하지 않는다. 결과 원본 경로는 제안하고 Main이 확인한다 |

- Main은 Codex 소유 연구 코드·결과 원본을 고치거나 숫자를 다시 계산하지 않는다.
- 외부 개발 책임자(별도 화면 세션 등)는 늘리지 않는다. DC-32의 "화면 세션(Frontend)"은 시행 전에 대체됐다.
- Codex PR 병합 조건: canonical과 동기화, 필수 CI 6개 녹색, **담당 파일만 바뀜**(Main이 파일 목록으로 확인), 오너 승인.
