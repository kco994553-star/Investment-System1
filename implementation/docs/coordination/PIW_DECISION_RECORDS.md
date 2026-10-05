# Investment-System1 · PIW_DECISION_RECORDS

Append-only record of decisions the Primary Integration Writer takes under delegated authority (CDR-015, D2). Single writer: the Primary Integration Writer. User decisions are recorded verbatim in `COORDINATION_DECISION_REGISTER.md`, not here; capability owners record their own D2 decisions in their scoped Decision Registers.

Rules: never edit or delete an entry. A later decision that changes an earlier one is a new entry naming the entry it supersedes. Every entry states:

- **Decision** and the authority it rests on (a CDR entry).
- **Reason**: requirements, the alternatives considered, and why this one.
- **Impact**: what changes, for whom, and what is not claimed.
- **Verification**: the evidence (GIE, commits, CI runs) that supports it, and what is still unverified.
- **Recovery**: how to reverse or supersede it, and what cannot be reversed.

A decision here never rewrites Frozen records or history, never hides a failure or unverified scope, and is not an approval of anything outside its stated scope. D3 (paid payment, paid subscription, extra charges, exceeding a free quota) is never decided here.

---

## PIW-D001 · Verifier authentication (former D3-a)

- Recorded: 2026-10-05T13:43:35+09:00. Authority: CDR-014 execution-integrity requirements; CDR-015 D2 as narrowed by CDR-016 §13 / CDR-017 / CDR-018.
- Status: **D2_DISPOSITION_DECIDED / IMPLEMENTATION_AND_EVIDENCE_PENDING**. This closes the operational decision question only, not its technical gate.
- Decision: Candidate verifier CI is not trusted acceptance. Independently accept an immutable verifier/launcher manifest and authenticate it separately from the subject; historical self-placement blobs are not automatically trusted.
- Reason/alternative: Self-attesting PR-head verifier is rejected because it either hides unverified scope or creates unrelated false positives.
- Impact: additive Integration/FPIA tooling and owner routing only; existing raw FPIA result and Frozen historical meaning remain intact. No QGV semantics, owner protected source, canonical merge, Holdout/PIT relaxation or production activation.
- Verification: independent source review of exact `11d2f25ef8bef3459ca969f50eec190099f15ecb` in `evidence/main_takeover_2026-10-05/FPIA_GOVERNANCE_INDEPENDENT_REVIEW.md`; implementation obligation: Exact accepted revision/launcher/runtime receipt and negative substitution evidence. This record does not claim that obligation is already met.
- Recovery: supersede this entry with reason/evidence; preserve the old entry and all raw runs; roll back a future tooling proposal on its own branch without changing canonical or Frozen history.

## PIW-D002 · Evidence identity (former D3-b)

- Recorded: 2026-10-05T13:43:35+09:00. Authority: CDR-014 execution-integrity requirements; CDR-015 D2 as narrowed by CDR-016 §13 / CDR-017 / CDR-018.
- Status: **D2_DISPOSITION_DECIDED / IMPLEMENTATION_AND_EVIDENCE_PENDING**. This closes the operational decision question only, not its technical gate.
- Decision: Use repository, workflow path+blob, run ID/attempt, job ID, subject SHA and trusted verifier identity for evidence binding. Generic job-label collisions alone are not rejection; ambiguous/bare-name receipts fail closed. Existing AC32 findings stay effective.
- Reason/alternative: Reject every common test/verify job label or trust labels alone is rejected because it either hides unverified scope or creates unrelated false positives.
- Impact: additive Integration/FPIA tooling and owner routing only; existing raw FPIA result and Frozen historical meaning remain intact. No QGV semantics, owner protected source, canonical merge, Holdout/PIT relaxation or production activation.
- Verification: independent source review of exact `11d2f25ef8bef3459ca969f50eec190099f15ecb` in `evidence/main_takeover_2026-10-05/FPIA_GOVERNANCE_INDEPENDENT_REVIEW.md`; implementation obligation: Compound-identity consumer and standalone collision diagnostics with adversarial/control checks. This record does not claim that obligation is already met.
- Recovery: supersede this entry with reason/evidence; preserve the old entry and all raw runs; roll back a future tooling proposal on its own branch without changing canonical or Frozen history.

## PIW-D003 · Dynamic invocation (former D3-c)

- Recorded: 2026-10-05T13:43:35+09:00. Authority: CDR-014 execution-integrity requirements; CDR-015 D2 as narrowed by CDR-016 §13 / CDR-017 / CDR-018.
- Status: **D2_DISPOSITION_DECIDED / IMPLEMENTATION_AND_EVIDENCE_PENDING**. This closes the operational decision question only, not its technical gate.
- Decision: Unknown acceptance-relevant executed source remains uncovered. Preserve raw historic results/nonclaims, but do not issue integration acceptance until resolved audited bytes or enforced noninterference are verified.
- Reason/alternative: Turn an honest NOT_CLAIMED label into unrestricted acceptance is rejected because it either hides unverified scope or creates unrelated false positives.
- Impact: additive Integration/FPIA tooling and owner routing only; existing raw FPIA result and Frozen historical meaning remain intact. No QGV semantics, owner protected source, canonical merge, Holdout/PIT relaxation or production activation.
- Verification: independent source review of exact `11d2f25ef8bef3459ca969f50eec190099f15ecb` in `evidence/main_takeover_2026-10-05/FPIA_GOVERNANCE_INDEPENDENT_REVIEW.md`; implementation obligation: Explicit execution coverage gate and independent source agreement evidence. This record does not claim that obligation is already met.
- Recovery: supersede this entry with reason/evidence; preserve the old entry and all raw runs; roll back a future tooling proposal on its own branch without changing canonical or Frozen history.

## PIW-D004 · Optional audit importers (former D3-d)

- Recorded: 2026-10-05T13:43:35+09:00. Authority: CDR-014 execution-integrity requirements; CDR-015 D2 as narrowed by CDR-016 §13 / CDR-017 / CDR-018.
- Status: **D2_DISPOSITION_DECIDED / IMPLEMENTATION_AND_EVIDENCE_PENDING**. This closes the operational decision question only, not its technical gate.
- Decision: Keep PR28 historical evidence intact outside code-integration subjects by default. Any subject containing unowned importers must satisfy generic source-bound attribution/isolation; no PR/path whitelist or rename workaround.
- Reason/alternative: Add a PR28-specific exemption or rewrite evidence is rejected because it either hides unverified scope or creates unrelated false positives.
- Impact: additive Integration/FPIA tooling and owner routing only; existing raw FPIA result and Frozen historical meaning remain intact. No QGV semantics, owner protected source, canonical merge, Holdout/PIT relaxation or production activation.
- Verification: independent source review of exact `11d2f25ef8bef3459ca969f50eec190099f15ecb` in `evidence/main_takeover_2026-10-05/FPIA_GOVERNANCE_INDEPENDENT_REVIEW.md`; implementation obligation: Owner attribution/packaging receipt or exact candidate that genuinely omits optional branch. This record does not claim that obligation is already met.
- Recovery: supersede this entry with reason/evidence; preserve the old entry and all raw runs; roll back a future tooling proposal on its own branch without changing canonical or Frozen history.

## PIW-D005 · External execution (former D3-e)

- Recorded: 2026-10-05T13:43:35+09:00. Authority: CDR-014 execution-integrity requirements; CDR-015 D2 as narrowed by CDR-016 §13 / CDR-017 / CDR-018.
- Status: **D2_DISPOSITION_DECIDED / IMPLEMENTATION_AND_EVIDENCE_PENDING**. This closes the operational decision question only, not its technical gate.
- Decision: Inventory actions/reusable workflows/container/runtime execution with immutable identity and actual influence. Unanalysed relevant external execution blocks integration acceptance until content/provenance or enforced noninterference is verified.
- Reason/alternative: Treat mutable tags or declarations as audited safe dependencies is rejected because it either hides unverified scope or creates unrelated false positives.
- Impact: additive Integration/FPIA tooling and owner routing only; existing raw FPIA result and Frozen historical meaning remain intact. No QGV semantics, owner protected source, canonical merge, Holdout/PIT relaxation or production activation.
- Verification: independent source review of exact `11d2f25ef8bef3459ca969f50eec190099f15ecb` in `evidence/main_takeover_2026-10-05/FPIA_GOVERNANCE_INDEPENDENT_REVIEW.md`; implementation obligation: Source-bound external dependency closure and negative substitution evidence. This record does not claim that obligation is already met.
- Recovery: supersede this entry with reason/evidence; preserve the old entry and all raw runs; roll back a future tooling proposal on its own branch without changing canonical or Frozen history.

## PIW-D006 · FPIA applicability (G7)

- Recorded: 2026-10-05T13:43:35+09:00. Authority: CDR-014 execution-integrity requirements; CDR-015 D2 as narrowed by CDR-016 §13 / CDR-017 / CDR-018.
- Status: **D2_DISPOSITION_DECIDED / IMPLEMENTATION_AND_EVIDENCE_PENDING**. This closes the operational decision question only, not its technical gate.
- Decision: Apply FPIA based on authenticated Track C ancestry/content/imports of the exact subject, not branch spelling. Pre-Track-C evidence is outside-scope/NOT_RUN, never PASS; ambiguous Track-C content without references fails closed. Each actual integration merge result still needs its own audit.
- Reason/alternative: Use integration/ prefix as proof of applicability or treat skipped job as PASS is rejected because it either hides unverified scope or creates unrelated false positives.
- Impact: additive Integration/FPIA tooling and owner routing only; existing raw FPIA result and Frozen historical meaning remain intact. No QGV semantics, owner protected source, canonical merge, Holdout/PIT relaxation or production activation.
- Verification: independent source review of exact `11d2f25ef8bef3459ca969f50eec190099f15ecb` in `evidence/main_takeover_2026-10-05/FPIA_GOVERNANCE_INDEPENDENT_REVIEW.md`; implementation obligation: Branch-independent subject applicability receipt and final exact-result audit. This record does not claim that obligation is already met.
- Recovery: supersede this entry with reason/evidence; preserve the old entry and all raw runs; roll back a future tooling proposal on its own branch without changing canonical or Frozen history.

Overall current disposition: **INTEGRATION_ACCEPTANCE_BLOCKED**. No unsupported raw FPIA_PASS is promoted to GIE/governance/exact-merge closure. Literal execution-source and container-evidence repair proceeds separately as a verified bounded successor.


## PIW-D007 · PIW-D002 bounded implementation checkpoint

- Recorded: 2026-10-05T14:32:45.200094+09:00; authority CDR-015 D1/D2 narrowed by CDR-016 §13/CDR-017/CDR-018; CDR-019 supplements tool use only.
- Status: **COMPOUND_CONSISTENCY_CONSUMER_IMPLEMENTED / AUTHENTICATED_BINDING_AND_INTEGRATION_ACCEPTANCE_PENDING**. Supersedes PIW-D002 technical status only in this finite sub-scope; PIW-D002 history is retained.
- Decision/reason: publish an additive stdlib importable utility and read-only JSON CLI on existing draft PR46 rather than change raw FPIA semantics. Match the entire workflow/run/attempt/job/subject/nominated-verifier identity; generic labels cannot select evidence, ambiguity/malformed receipts fail closed. Consistency never authenticates caller-supplied strings. All outputs retain authentication NOT_VERIFIED and integration_acceptance BLOCKED.
- Impact: two new ordinary integration-tool/test files; zero existing source or workflow edits, no new dependencies, no owner contracts or production policy. Exact remote `a3e3f6cf5452d056de2df7845a17014765aa3ff3`, parent `2135962a1e6fd19c3acd220a30c6464431eddf95`, tree `cdade46e1c9402a90272fbe325d6e04398b7b5ea`; TREE_IDENTICAL local/API, no local COMMIT_IDENTICAL claim.
- Verification: 157 initial RED; independent review exposed 8 owner-hyphen cases RED, fixed before final 165/165 GREEN; root readback 165/165. Evidence `evidence/main_tools_2026-10-05/PIW_D002_IMPLEMENTATION_RECEIPT.json`. New exact-head CI collected once and pending separately; old subject CI7/7 SUCCESS is not reused for new code.
- Limits/next: actual authenticated expected identity/receipt, independently authorized verifier/launcher, dynamic/transitive/external coverage, importer attribution, applicability and exact final merged subject still required. PIW-D001/D003-D006 remain runnable D1/D2 obligations, not fresh approval requests based on former D3 labels.
- Recovery: revert this additive utility on its proposal branch if a defect is found; preserve all runs/decision history and fail-closed acceptance. No canonical merge/Frozen rewrite.

## PIW-D008 · PIW-D003/D005 bounded execution coverage consumer

- Recorded 2026-10-05T07:22:30.181Z; CDR-015 D1/D2 narrowed by016§13/017/018; proportional verificationCDR-021 and continuationCDR-022.
- **BOUNDED_IMPLEMENTATION_VERIFIED / FULL_EXECUTION_COVERAGE_PENDING**. Two additive source/test files on codex/fpia-execution-coverage-2026-10-05, exact ce2ea5b08b600b07c9a6ba9179a47ea8e199c497, tree8660fe1335f99275dec01f3f2f0a1f3535eeaa8e, parent6fea6c7f0a191a4e621941ce3f6a7cac83a7f3d6; TREE_IDENTICAL, not COMMIT_IDENTICAL.
- Decision: read-only consumer pins exact subject and externally selected result anchor, strictly parses JSON and verifies canonical result digest. It reports explicit dynamic/external/descendant limitations; every v2 result remains fail-closed, even rawFPIA_PASS. No executor, no dependency invocation, no semantic rewrite.
- Verification: initial15RED; final16targeted +683affected PASS; current exact6feaartifact consumed and COVERAGE_BLOCKED, result6261005636109c32705ae7a4e9266a1cac3ddab588ce96dcbcab8ac893231500. CI7/7currentSUCCESS consumed without rerun. Existing source evidence2019 reused only for unchanged scope; currentCI2184 separately identified. Independent accepted verifier/launcher/runtime/source coverage still OPEN.
- Impact/recovery: no canonical/owner-source/production/Frozen modification. Revert additive proposal independently if defective; preserve first failures, raw runs and historical receipts. Main continues remaining READY tasks; not whole Work WAIT.
