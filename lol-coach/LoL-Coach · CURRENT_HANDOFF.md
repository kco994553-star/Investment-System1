# LoL-Coach · CURRENT_HANDOFF

Timestamp: 2026-09-28 19:35 KST (R1)
AI: Claude (Claude Code)
Project Version: v0.1-core (core unchanged) + R1 validation layer
Module/Area: Fixture Runner · Golden Fixtures · Counterfactual · Metamorphic
Branch: claude/lol-coach-relay-format-y8uk0x

## Started From
R0 Next Action #2 (Fixture runner). 사용자 R1 범위 지시: **기존 Core 동작 변경 금지**,
Fixture Runner + GF-001/GF-002 + Counterfactual/Metamorphic 검증까지만. OI-1~4는 R2에서 사용자 원 설계와 대조.

## Completed
- `validation/fixture_runner.py`: JSON Golden/Counterfactual fixture 로더·실행기.
  기대값은 부분 지정(permission, opportunities, recommended, actions.{validity, reasons, reasons_include,
  unlock_conditions, unlock_include}, trace, same_as_golden). Counterfactual은 base 입력에 patch를 deep-merge하고
  base 대비 변화(diff)를 기록. `unchanged_from_base`로 불변 검증, 변화 없는 counterfactual은 실패 처리.
- `validation/metamorphic.py`: GameState 전체 열거 공간 1,296개 상태에서 MR-01~MR-08을 전수 검사(샘플링 아님).
- `python -m validation [--verbose]` CLI (실패 시 exit 1).
- Golden fixture (R1_BASELINE — 받은 그대로의 동작 고정, 설계 확인은 R2):
  - GF-001 PUNISH 창 + 적 정글 UNKNOWN → P3, SHORT_TRADE. EXTENDED_TRADE/ALL_IN CONDITIONAL(+ENEMY_JUNGLE_UNKNOWN,
    unlock ENEMY_JUNGLE_CONFIRMED_FAR), CHASE INVALID. 9개 행동 전부 validity 명시.
  - GF-002 PUNISH 창 + 적 정글 CONFIRMED_NEAR → P2, THREAT로 하향. SHORT_TRADE 이상 CONDITIONAL(reasons 비어 있음 = OI-2).
- Counterfactual 10개: CF-001-A~H(GF-001 기반), CF-002-A~B(GF-002 기반).
  CF-001-B(GF-001+NEAR)=GF-002, CF-002-A(GF-002+UNKNOWN)=GF-001 대칭 확인.
- Metamorphic relations:
  - DESIGN: MR-01 결정성·입력 불변, MR-02 정글 안전도 단조성(NEAR≤UNKNOWN≤FAR), MR-03 FAR 확인 시 어떤 행동도 악화 안 됨,
    MR-04 PUNISH 제거 시 permission 비증가, MR-05 추천 정확히 1개 & VALID.
  - CURRENT(OI 연동, R2에서 의도적으로 바뀔 수 있음): MR-06 WAIT 항상 VALID(OI-5), MR-07 trace 구조(OI-3),
    MR-08 wave/access/return_path 무영향(OI-4).
- Runner 자기검증: 틀린 기대값·미정의 행동·잘못된 입력·가짜 불변·효과 없는 counterfactual·깨진 단조성(monkeypatch)을
  모두 FAIL로 잡는지 테스트.
- Core 동결 가드: `tests/core_manifest_r0.json`(backend/*.py 13개 sha256)과 일치해야 PASS.

## Files Changed
- 신규: validation/{__init__,__main__,fixture_runner,metamorphic}.py
- 신규: fixtures/golden/GF-001.json, GF-002.json; fixtures/counterfactual/CF-001.json, CF-002.json
- 신규: tests/test_validation_r1.py, tests/core_manifest_r0.json
- 수정: pyproject.toml (setuptools 패키지 명시 — R0 설정은 flat-layout 다중 패키지로 `pip install -e .` 실패 가능, venv에서 설치·32 PASS 확인)
- 수정: README.md, LoL-Coach · {Project Index, Master Status Index, CURRENT_HANDOFF, HANDOFF_HISTORY}.md
- backend/: **변경 없음** (git diff 빈 결과, manifest 테스트 PASS)

## Tests
- `python -m pytest -q` → 32 passed (R0 baseline 11 + R1 21). Python 3.11.15, pydantic 2.13.5, pytest 9.1.1.
- `python -m validation` → fixtures 12/12 PASS, MR 8/8 PASS (총 19,411 relation checks), exit 0.
- 검증 수준: Unit + Scenario fixture + Metamorphic(전수). Replay / Live-game: NOT RUN.
- 모든 PASS는 "받은 동작과 일치"를 뜻한다. 코칭 판단이 옳다는 검증이 아니다.

## Decisions
- GF-001/GF-002의 내용은 R1에서 이 AI가 정의했다(사용자 원 설계의 GF 정의 원문은 저장소에 없음).
  R2에서 원 설계와 다르면 원 설계가 우선한다.
- Metamorphic relation을 DESIGN / CURRENT로 분리. CURRENT는 OI가 닫힐 때 의도적으로 수정·삭제 대상.
- Core 변경 라운드는 `tests/core_manifest_r0.json` 갱신 + 이유 기록을 필수로 한다.

## Provisional
- GF-001/GF-002 기대값, MR-02~MR-05의 DESIGN 분류 — 사용자 원 설계 대조 전까지 PROVISIONAL.

## Open Issues
- OI-1 ActionType 16개 중 7개(CONCEDE_RESOURCE, HOLD_PRESSURE, FREEZE, SLOW_PUSH, CRASH, CLAIM_SPACE, CLAIM_RESOURCE)
  정의 없음 → 평가·추천 불가. (runner 자기검증에서 FREEZE "not evaluated" 확인)
- OI-2 Permission 제약만으로 CONDITIONAL이 된 행동의 reasons/unlock_conditions가 비어 있음. GF-002, CF-001-A에서 재현.
- OI-3 trace에 행동 단위 근거 없음. ReasonCode 4개(FAVORABLE_MATCHUP, OPPONENT_CS_APPROACH, SAFE_RETURN_PATH,
  LOW_REVERSIBILITY) 미발행. MR-07로 현재 구조 고정.
- OI-4 wave / access / return_path가 판단에 무영향. **CF-001-G: return_path=UNSAFE인데도 SHORT_TRADE 추천 유지**,
  CF-001-H: access=CLOSED여도 동일. MR-08(7,776 checks)로 전 공간에서 무영향 확인.
- OI-5 WAIT가 VALID가 아니면 추천 0개 가능성 — 현재 규칙에선 발생 안 함(MR-06 전수 PASS).
- OI-6 Frozen v0.1 설계 원문 미등록.
- OI-7 (R1 신규) ActionDefinition의 risk(RiskLevel)·purpose(Purpose)를 어떤 단계도 읽지 않음.
  CF-001-A: P4에서 CHASE(Risk VERY_HIGH)가 SHORT_TRADE와 동일하게 VALID.

## Next Action
R2 — 사용자가 제공하는 원 설계와 대조해 OI-1~4(+OI-7)를 하나씩 닫는다.
1. 원 설계를 `lol-coach/docs/`에 등록(OI-6).
2. OI 하나씩: Existing / Proposed / Reason / Impact / Compatibility / Validation Required 기록 → Core 수정 →
   영향받는 GF/CF/MR 기대값을 **의도적으로** 갱신(예: OI-4를 닫으면 MR-08·CF-001-F/G/H가 바뀌어야 정상) →
   `tests/core_manifest_r0.json` 갱신 → 전체 pytest + `python -m validation` 재실행.
3. DESIGN MR(MR-01~05)은 OI 수정 후에도 PASS 유지가 목표. 깨지면 설계 충돌로 CONFLICT 기록 후 사용자 확인.

## Do Not Repeat
- R0: zip 이관, pyproject, baseline 테스트 11개, relay 문서 5종.
- R1: fixture runner, GF-001/GF-002, CF 10개, MR 8개, runner 자기검증, core manifest 가드.
