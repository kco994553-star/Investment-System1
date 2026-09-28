# LoL Coach v0.1 — Core Decision Skeleton

Initial private MVP core extracted from the frozen v0.1 design.

Current scope:
- GameState minimum model
- Action taxonomy
- Opportunity detection
- Permission calculation
- Action validity evaluation
- Recommendation selection
- Decision trace
- Thin orchestration engine

Validation (R1):
- Fixture runner (golden GF-001/GF-002 + counterfactuals)
- Metamorphic relations over the full GameState space

Not included yet:
- Replay
- Windows Bridge
- AI/API analysis
- React UI
- SQLite persistence

## Relay

This project is developed as a Multi-AI Relay (same format as Investment-System1).
Start every session by reading, in order:

1. `LoL-Coach · Project Index.md`
2. `LoL-Coach · Master Status Index.md`
3. `LoL-Coach · CURRENT_HANDOFF.md`

Rules: `LoL-Coach · Multi-AI Relay Protocol v1.0.md`

## Run tests

```
pip install -e '.[test]'
python -m pytest -q
python -m validation --verbose   # fixtures + metamorphic report
```
