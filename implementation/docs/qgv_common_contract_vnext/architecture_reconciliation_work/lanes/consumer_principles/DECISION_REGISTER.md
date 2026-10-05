# QGV architecture audit scoped Decision Register

Current event: B2/B3/B5/B6 APPROVED_SEMANTIC_CONTRACT_PRINCIPLES_ONLY.
This is this Work's append-only decision register under its approved write scope.
It extends the existing immutable owner Decision Register by exact reference;
the other owner's register/STATE/lease is not rewritten or taken over.

## Preserved preceding records

- Owner register:4fb08a05728d83519b72a2bd995669f0cb06003a,
  implementation/docs/qgv_common_contract_vnext/missing_data_gate/DECISION_REGISTER.md,
  Git blob ab00055a4f70e2674af00404fe0db2908e8d50c6. Its prior recommendation state
  is historical input, not the current approval status of this Work.
- Existing M1–M5 and B4/B7 principles remain approved. G1/G2 event:
  ../semantic/root/approval.json. No prior approved meaning is reopened.
- Recommended package:16f58f20a29516e45e202aee7d3b27b8a1378d5c:../semantic/root/DECISION_PACKAGE.md,
  SHA-256 f00a96a0e646b8c3ca3c90dc44d3b20d993ae8465f4c082fd325399c12657b2e. Preserved unchanged.

## Append-only explicit user approval — 2026-10-05T17:07:34+09:00

Event ID:QGV-B2-B3-B5-B6-PRINCIPLES-2026-10-05.
Actual recorded time:2026-10-05T17:16:16.637989+09:00.
Authority: explicit current user instruction; not inferred from CI/PR/test PASS.
Exact record:[approval.json](approval.json), SHA-256 4b531ea06bf484ef2a4c185d94f32080c2d01fe52161697d565e34d3fd21d758.

> B2/B3/B5/B6의 Decision Package 추천안을 승인한다. 단, 이번 승인은 semantic/contract principles에 한정하며 numeric policy, 개별 factor binding, runtime activation, score/history migration, canonical merge는 포함하지 않는다. 승인 내용을 Decision Register와 scoped Handoff에 history-preserving 방식으로 기록하고, 승인으로 새로 열린 D1/D2 작업은 자율 진행하라. D3에서만 다시 요청하라.

| Existing clause | Current state | Residual D3 |
|---|---|---|
| B2 | APPROVED_PRINCIPLES_ONLY | Predicates, individual bindings, exclusions/denominator |
| B3 | APPROVED_PRINCIPLES_ONLY | Rubrics/cutoffs/classification/runtime |
| B5 | APPROVED_PRINCIPLES_ONLY | Independent assessment methods/criteria/factor roles |
| B6 | APPROVED_PRINCIPLES_ONLY | Cohort/compatibility/purpose-specific criteria/grants/activation |

Numeric policy, individual factor binding, runtime activation, score/history
migration and canonical merge are explicitly excluded. G/V method choice, B1,
Composite, WeightOverride, Official, PIT, Holdout and other existing gates remain.
V2 reference/scope principles approved; actual assessment methodology unapproved.

Authorized D1/D2 successor: compile OBLIGATION_MAP.json, bounded authority/negative
verification, reconcile current scoped CONTROL/Handoff and publish Main/owner
return. Technical PASS is bounded contract acceptance, not production admission.
