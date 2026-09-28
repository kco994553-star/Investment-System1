# LoL-Coach · HANDOFF_HISTORY

Append-only 인계 기록. 과거 기록을 삭제하거나 사후 수정하지 않는다.
각 라운드 종료 시 직전 CURRENT_HANDOFF 전문을 이 파일 끝에 추가한다.

------------------------------------------------------------------------

2026-09-27 20:50 KST · R0 · Claude (Claude Code)
- LoL Coach Multi-AI Relay 시작. SSoT = `lol-coach/` (Investment-System1 저장소).
- v0.1 core zip을 수정 없이 이관, baseline 11/11 PASS.
- Open Issues OI-1~OI-6 기록. Next Action: 설계 원문 확보 → Fixture runner.
- 전문은 R0 시점 `LoL-Coach · CURRENT_HANDOFF.md` 참조 (다음 라운드가 전문을 여기에 append).

------------------------------------------------------------------------

R0 CURRENT_HANDOFF snapshot (archived at R1, do not edit)

# LoL-Coach · CURRENT_HANDOFF

Timestamp: 2026-09-27 20:50 KST (R0)
AI: Claude (Claude Code)
Project Version: v0.1-core
Module/Area: Relay bootstrap + core import
Branch: claude/lol-coach-relay-format-y8uk0x

## Started From
사용자가 업로드한 `lol-coach-v0.1-core.zip`(sha256 prefix ef3b1b7bf927cfa9)과 README("Core Decision Skeleton,
extracted from the frozen v0.1 design"). 이전 Handoff 없음 — 이번이 첫 라운드(R0).

## Completed
- LoL Coach를 Investment-System1과 같은 Multi-AI Relay 형식으로 개설 (`lol-coach/` = SSoT).
- v0.1 core 코드 13개 파일을 **수정 없이** `lol-coach/backend/`로 이관.
- `pyproject.toml` 추가 (Python >= 3.11 — StrEnum 사용, pydantic >= 2).
- 현재 동작을 고정하는 characterization test 11개 작성.
- 코드 감사 후 Open Issues 기록 (설계값을 추측으로 채우지 않음).

## Files Changed
- lol-coach/backend/** (imported unchanged)
- lol-coach/README.md (uploaded README + relay pointer)
- lol-coach/pyproject.toml
- lol-coach/tests/__init__.py, lol-coach/tests/test_core_baseline.py
- lol-coach/LoL-Coach · {Multi-AI Relay Protocol v1.0, Project Index, Master Status Index, CURRENT_HANDOFF, HANDOFF_HISTORY}.md

## Tests
`cd lol-coach && python -m pytest -q` → 11 passed (Python 3.11.15, pydantic 2.13.5, pytest 9.1.1).
Unit/characterization 수준만 실행. Scenario fixture / Replay / Live 검증은 NOT RUN.

## Decisions
- SSoT는 Google Drive가 아니라 GitHub 저장소의 `lol-coach/` 디렉터리.
- LoL Coach와 투자 시스템 코드는 상호 import 금지.
- R0 테스트는 "받은 그대로의 동작"을 고정한다. 동작을 바꾸는 수정은 해당 테스트를 의도적으로 갱신하고 이유를 Handoff에 남긴다.

## Provisional
- 없음 (R0에서 설계·수치를 새로 도입하지 않음).

## Open Issues
- OI-1 Action taxonomy 불완전: ActionType 16개 중 7개(CONCEDE_RESOURCE, HOLD_PRESSURE, FREEZE, SLOW_PUSH, CRASH,
  CLAIM_SPACE, CLAIM_RESOURCE)가 ACTION_DEFINITIONS에 없어 평가·추천 대상에서 제외된다. Purpose.WAVE/RESOURCE도 미사용.
  Commitment/Reversibility/Risk 값은 Frozen v0.1 설계 원문이 필요 — 추측 금지, 사용자에게 원문 요청.
- OI-2 Permission 제약으로 CONDITIONAL이 된 행동은 reasons/unlock_conditions가 비어 있다 (근거 없는 CONDITIONAL).
  PERMISSION 관련 ReasonCode가 설계에 있는지 확인 필요.
- OI-3 build_trace가 evaluations를 받지만 사용하지 않는다. Action 단위 validity/추천 근거가 trace에 없다.
  ReasonCode FAVORABLE_MATCHUP, OPPONENT_CS_APPROACH, SAFE_RETURN_PATH, LOW_REVERSIBILITY는 어디서도 발행되지 않는다.
- OI-4 GameState의 wave(WaveState), power.access(AccessState), risk.return_path(ReturnPath)는 판단에 쓰이지 않는다.
- OI-5 selector는 WAIT도 VALID가 아니면 추천 없음(0개)이 될 수 있다. 현재 규칙상 WAIT는 항상 VALID라 발생하지 않지만
  (테스트로 1개 추천 보장 확인) 향후 규칙 추가 시 보호 필요.
- OI-6 Frozen v0.1 설계 문서 원문이 저장소에 없다. 위 OI-1~4를 해결하려면 원문이 필요하다.

## Next Action
1. 사용자에게 Frozen v0.1 설계 원문을 요청해 `lol-coach/docs/`에 등록 (OI-6). 원문 없이는 OI-1~4의 값을 채우지 않는다.
2. 원문 대조가 불가능한 동안 진행 가능한 작업: README "Not included yet" 1순위인 **Fixture runner** —
   JSON 시나리오(GameState 입력 + 기대 permission/opportunities/recommendation)를 읽어 analyze()와 대조하는 runner와
   R0 baseline 시나리오 fixture 세트. 기존 동작 변경 없음.

## Do Not Repeat
- zip 이관, pyproject 작성, baseline 테스트 11개 작성, relay 문서 5종 생성 — 완료.

------------------------------------------------------------------------

2026-09-28 19:35 KST · R1 · Claude (Claude Code)
- 사용자 지시 범위: Core 동작 변경 금지, Fixture Runner + GF-001/GF-002 + Counterfactual/Metamorphic 검증까지만.
- validation/ 패키지(fixture_runner, metamorphic, CLI) + GF-001/GF-002 + Counterfactual 10개 + MR 8개 추가.
- Core는 R0와 byte-identical (sha256 manifest 테스트로 강제). 전체 pytest 32/32 PASS, CLI ALL PASS.
- 신규 관찰 OI-7(RiskLevel/Purpose 미사용). Next Action: R2에서 사용자 원 설계와 OI-1~4(+OI-7) 대조 후 하나씩 닫기.
