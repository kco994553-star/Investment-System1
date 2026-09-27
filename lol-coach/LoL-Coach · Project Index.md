# LoL-Coach · Project Index

Purpose
League of Legends 실시간 판단 코치. 게임 상태(GameState)를 받아 기회(Opportunity) → 허용 수준(Permission) →
행동 유효성(Validity) → 추천(Recommendation) → 판단 근거(Decision Trace)를 결정론적으로 산출한다.

Relay
Multi-AI Relay 형식으로 진행한다. 규칙: `LoL-Coach · Multi-AI Relay Protocol v1.0.md`.
읽는 순서: Project Index → Master Status Index → CURRENT_HANDOFF.

Architecture (v0.1 core, FROZEN design)
GameState (backend/state/models.py)
→ detect_opportunities (backend/decision/opportunity.py)
→ calculate_permission (backend/decision/permission.py)   P0–P5
→ evaluate_actions (backend/decision/evaluator.py)        VALID / CONDITIONAL / INVALID
→ select_recommendation (backend/decision/selector.py)
→ build_trace (backend/decision/trace.py)
→ Decision (backend/decision/models.py)
Orchestration: analyze() in backend/decision/engine.py

Planned Layers (NOT STARTED, v0.1 README "Not included yet")
Fixture runner · Replay · Windows Bridge · AI/API analysis · React UI · SQLite persistence

Layout
lol-coach/backend/   core decision code
lol-coach/tests/     pytest suite
lol-coach/pyproject.toml  Python >= 3.11, pydantic >= 2

How to run
cd lol-coach && pip install -e '.[test]' && python -m pytest -q

Boundary
LoL Coach는 Investment-System1 저장소 안에 있지만 독립 프로젝트다. 투자 시스템 코드와 서로 import하지 않으며,
`.github/workflows/c21-real-data.yml`은 LoL Coach와 무관하다.
