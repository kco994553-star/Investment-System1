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
- **공식 V** = 서버가 IEX HIST로 계산해 공개하는 점수·순위(2026-10-23 결정). 원시 가격은 공개하지 않는다. **아직 구현되지 않았다.** 지금 화면의 V는 기기 V이며 공식값이 아니다(DC-02).
- 화면 점수는 **QGV v2만**(DC-03). TARGET 19는 QGV가 고른 것이 아니다(DC-04).
- 기능 번호는 **명세 v1.0의 1~9**만 쓴다. 메뉴 번호(0 검색, 1 QGV…)로 보고하지 않는다(DC-08).
- 새 프론트엔드는 **손그림 칠판 시안대로 새로 작성** 중이다. 무채색 미니멀 지시는 대체됐다(DC-07).
- 역할: 병합·공용 파일은 Claude Code Main 하나. Codex는 검증·리뷰만(DC-09).

## 3. 매 작업 규칙

- 사용자가 방향을 바꾸면 **같은 PR에서** DIRECTION_CHANGES에 한 줄을 더한다. 결정만 하고 코드가 아직 옛 방향이면 "구현 상태"에 그렇게 적는다.
- 기능을 병합하면 FUNCTION_STATUS의 해당 번호 줄을 같은 PR에서 고친다.
- 금지 표현 검사: `python implementation/tools/spec_direction_guard.py`(CI 전체 시험 `test_spec_direction_guard.py`에 포함).
- 원시 가격·개인 자료·토큰·이메일은 저장소·Pages·로그에 넣지 않는다. 병합·배포는 사용자 승인 범위에서만 한다.
- 사용자는 폰만 쓴다. 사용자에게 시키는 절차는 폰 브라우저에서 할 수 있어야 한다. 보고는 한국어로 묶어서 한다.
