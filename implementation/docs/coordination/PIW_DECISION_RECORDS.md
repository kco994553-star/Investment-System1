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
