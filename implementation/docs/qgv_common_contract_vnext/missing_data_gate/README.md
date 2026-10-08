# QGV Missing-Data Decision Gate v0.1

**INACTIVE / SPEC-ONLY. M1-M5 PRINCIPLES APPROVED; bindings/runtime NOT APPROVED.**

Start with [Implementation Contract](implementation_contract/README.md) and its
exact principle approval record. The older [DECISION_PACKAGE.md](DECISION_PACKAGE.md)
is preserved proposal history, including stronger unapproved choices. Continue from
[CURRENT_HANDOFF.md](CURRENT_HANDOFF.md); do not repeat Remote Recovery.

| Artifact | Purpose |
|---|---|
| [CURRENT_BEHAVIOR.md](CURRENT_BEHAVIOR.md) | Current Q/G/V prior/candidate and upstream reason/metadata flow |
| [POLICY_COMPARISON.md](POLICY_COMPARISON.md) | Four alternatives, 14 model-impact dimensions, tradeoffs and approvals |
| [DECISION_PACKAGE.md](DECISION_PACKAGE.md) | M1–M5, recommendation, effects, migration gates and dependencies |
| [DECISION_REGISTER.md](DECISION_REGISTER.md) | Local proposal IDs; no approval inferred |
| [SIMULATION.md](SIMULATION.md) | Isolated fixture comparison and meaningful checks |
| `simulation_results.json` | Read-only inputs, policy outputs, source/golden preservation, arithmetic anchors |
| `current_behavior_probe.py` | Scoped characterization of current runtime; no patching or fixture rewrite |
| `evidence/current_behavior_probes.json` | Actual current snapshots and boundary/zero-weight probes |
| `simulate_policies.py` | Standalone research comparison; no production callers or wiring |
| `evidence/fresh_baseline.json` | Exact GitHub intake, PR #44/CI/source/integration pins |

Numerical examples use existing weights and synthetic/golden values. They are
neither proposed numeric defaults nor empirical proof of market-wide ranking,
sector fairness, real PIT/OOS or promoted Official authority. Existing golden
and history are not regenerated. Production semantics and PR #44 are untouched.

Reproduce the new Phase B checks from the repository root:

```bash
PYTHONPATH=implementation/src:implementation python implementation/docs/qgv_common_contract_vnext/missing_data_gate/current_behavior_probe.py
python implementation/docs/qgv_common_contract_vnext/missing_data_gate/simulate_policies.py
```

The current-behavior probe follows the repository's existing PYTHONPATH setup;
it does not install or change production dependencies. The simulation reads
fixture files and uses only the standard library.

Automatic continuation: [automation/CONTROL.md](automation/CONTROL.md).
Shared checkpoints: `automation/STATE.json`; additive setup receipts:
`automation/receipts/`. Enabled setup does not mean event delivery tested.
