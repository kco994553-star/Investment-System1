# LoL-Coach · Multi-AI Relay Protocol v1.0

목적
여러 AI(GPT → Grok → Claude → GPT …)가 역할 분담 없이 순차적으로 같은 LoL Coach 프로젝트를 이어서 작업한다.
Investment-System1 Multi-AI Relay Protocol v1.0과 같은 형식을 따르되, LoL Coach는 투자 시스템과 독립된 프로젝트다.

Single Source of Truth
GitHub `kco994553-star/Investment-System1` 저장소의 `lol-coach/` 디렉터리.
이전 AI와의 채팅, 개별 AI의 기억·추측보다 이 디렉터리의 최신 기록이 우선한다.
투자 시스템(Track A~E) 문서와 코드는 LoL Coach의 근거가 아니며, 서로 import하지 않는다.

작업 시작 순서
1. `lol-coach/LoL-Coach · Project Index.md`
2. `lol-coach/LoL-Coach · Master Status Index.md`
3. `lol-coach/LoL-Coach · CURRENT_HANDOFF.md`
4. CURRENT_HANDOFF가 지정한 코드/문서

핵심 규칙
- 이전 AI와의 채팅을 알고 있다고 가정하지 않는다.
- Frozen v0.1 설계(Action taxonomy, Permission P0–P5, Validity VALID/CONDITIONAL/INVALID, Commitment/Reversibility 척도)를 임의로 재설계하지 않는다.
- 이전 Handoff의 Next Action부터 실제 작업을 진행한다. 이미 완료되었거나 잘못된 Next Action이면 그 사실을 기록하고 실제 필요한 다음 단계로 간다.
- 이미 완료된 작업을 이유 없이 다시 구현하지 않는다.
- 설계 변경이 필요하면 Existing / Proposed / Reason / Impact / Compatibility / Validation Required를 기록하고, 검증 전에는 PROPOSED 또는 PROVISIONAL로 둔다.
- 설계 문서에 없는 수치(Action 정의값, 임계값, 가중치)를 추측으로 채우지 않는다. 필요하면 OPEN으로 남기고 사용자 확인을 받는다.
- 기존 PASS 영역을 수정하면 전체 테스트(Regression)를 재실행한다.
- 실제 실행하지 않은 테스트를 PASS라고 기록하지 않는다.
- Unit / Scenario Fixture / Replay / Live-Game Validation을 구분한다. 코어 Unit PASS를 코칭 품질 검증으로 확대하지 않는다.

작업 순서
확인 → 구현 → 테스트 → 오류 수정 → Regression Check → 문서 갱신 → 다음 단계

작업 종료
1. `LoL-Coach · CURRENT_HANDOFF.md`를 아래 형식으로 **덮어써서** 갱신한다.
2. 직전 CURRENT_HANDOFF 전문을 `LoL-Coach · HANDOFF_HISTORY.md` 끝에 **append-only**로 추가한다.
3. 상태가 바뀐 모듈은 `LoL-Coach · Master Status Index.md`를 갱신한다.

CURRENT_HANDOFF 형식
Timestamp (KST) / AI / Project Version / Module-Area / Branch
Started From
Completed
Files Changed
Tests
Decisions
Provisional
Open Issues
Next Action
Do Not Repeat

Conflict 우선순위
CURRENT_HANDOFF(최신) → Master Status Index → Frozen v0.1 설계 → 코드 → HANDOFF_HISTORY.
해결되지 않으면 CONFLICT로 기록하고, 설계 변경이 필요한 충돌이면 사용자에게 확인한다.

완료 원칙
진행률을 채우기 위해 기능을 추가하지 않는다.
Implementation → Integration Test → Regression Test → Inconsistency Check → Documentation → Release Candidate → Freeze.
