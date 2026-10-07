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

## PIWD-009 · Runtime execution source observer · 2026-10-05 07:56:57 UTC

CDR015/018/021/022 D2 CRITICAL additive Main proposal at9ab/#47: observes actual workflow SHA/ref vs subject, run/attempt, Git blob verifier hashes and launcher; missing/dirty/untracked/symlink data fails closed. 207 scoped checks PASS after preserved14RED/4decodeFAIL/3selfFAIL history. API TREE_IDENTICAL, not COMMIT_IDENTICAL. Authority acceptance remains OPEN; observer is not attestation. Shared lease released, CI waiting does not consume lease.

## PIWD-010 · Optional PR28 omission · 2026-10-05 07:56:57 UTC

Existing PIW-D004 omission option verified exact9ab tree5b3ad: complete412-file PR28 inventory; 14optional executable audit/importer paths absent, PR28notancestor. CLOSED for exact subject packaging only. History preserved, no whitelist, no future merge-result/authentication acceptance. D006 currentR ancestry independently confirmed; branch-prefix automation repair still READY.

## PIWD-011 · D006 bounded implementation and source-checkout correction · 2026-10-05 08:19:50 UTC
D2CRITICAL under015/016/017/018/021/022. Exact50fa7f49080b3fa3d1808f9745d8f97770d1c9df treece6a9092cbeb79f7ac55626b7d8931061167cd4d, fiveboundedfiles; existingrawcoreunchanged. Local229PASS, independent4findingsaddressed. DefaultexistingCDRauthloader only; noreferenceoverride. RealGitpreflightUNAVAILABLE/CIpending; acceptance notgranted. Legacyobservercalls retain SUBJECTbinding; explicitworkflowmode bindsworkflowSHA and preservesactualsubject. Conservative unresolvedimports/calls/executionBLOCKED; preTrackCoutsideNOTRUNneverPASS. D006implementation VERIFIED inproposal, fullgateOPENuntilexactCI/authority/actualintegrationresult. PreserveallFAILhistory/revertboundedproposalonly. QGVscopeacceptanceconsumed separately, noQGVmethodorproductionapproval.


## PIWD-012 · CI-discovered stale workflow regression repair · 2026-10-05 08:43:02 UTC

- **Decision/authority:** Under CDR-015 D1/D2 as narrowed by CDR-016 §13, CDR-017/018 and risk/continuation CDR-021/022, repair the legacy regression test on the existing approved D006 proposal. This is a bounded test-contract correction, not a new methodology or production decision.
- **Reason:** Exact-50fa Actions run `37282319537` failed 1/2242 because the legacy test required a job-level integration-branch gate. D006 intentionally removed that gate so every pull request reaches authenticated applicability; retaining the old assertion would reinstate branch-name dependence. Run `37282319630` independently reproduced the same failing test.
- **Impact:** Only `implementation/tests/test_integration_fpia_fix2.py` changed. Draft #47 exact `7215a9f60ad7128b1748f405051eac684298614f`, parent `50fa7f49080b3fa3d1808f9745d8f97770d1c9df`, tree `d5a61fad01b84ef5e84daf2949572911a14a6782`; raw FPIA logic, Frozen/PIT/Holdout, QGV production semantics, canonical state, owner contracts and production authority are unchanged.
- **Verification:** Original CI failures preserved; RED reproduced locally; corrected single test GREEN; affected suite 294/294 PASS. Seven exact-7215 Actions runs are nonterminal; CI PASS is not claimed and no duplicate rerun was requested.
- **Recovery:** Revert the single test-only commit if independent evidence shows the contract is wrong; never restore branch-name gating as a substitute for authenticated applicability. Preserve all prior failures and exact-head run receipts.


## PIWD-013 · D3-A/D3-R adoption and fresh bounded return consumption · 2026-10-05T09:23:18Z

- **Decision/authority:** CDR-023 explicit user policy, CDR-015 as narrowed by016§13/017/018/020/021/022. Adopt evidenced delegated approval, not blanket “only cost D3”; preserve all historical decisions. Actual pending reclassification is in evidence/main_d3_delegation_2026-10-05/DECISION_RECEIPT.json. Main newD3-A approvals0; owner Chart alreadyexecuted presentation fallbackD3-A1, not Product authority.
- **Reason/alternatives:** Old-label reapproval creates unjustified waits; blanket reasonable approval cannot prove SSoT alignment. Selected exact-scope conservative classification with allten conditions and reserved exclusions. Evidence/owner gaps remain factual dependencies.
- **Impact/alignment/protection:** Operational traceability and immutable owner returns only. QGV ab07 principle return consumed4 contract-authority gates/2 boundedacceptances; actual methods/numeric/runtime excluded. Chartd84 nativeSAMPLE+cdareference repair consumed1 deliveryacceptance; all6production gatesopen,Market0/19. Platformed525policy+edd firstevent/Globalintake consumed;9Product blockersremain, source adoptionfalse. No production gate closure, source owner takeover, canonicalmerge, Frozen/PIT/Holdout/LIVE/security/tenant/credential/cost changes.
- **Verification:** QGV13payload SHA/byte/Gitblob matches; root1positive+5authority-expansionnegativePASS; owner25new/prior59/79/30reused. Chart10receiptSHA+9component/2persisted screenshotGitblobsPASS; owner18browserchecksreused, noMainbrowserrerun. Platformexactreceipt/policy/STATE hashes and firstevent identity verified;24structural/7readbackpolicy checks reused. Current47 exact7215 sixofsevenCISUCCESS; run37284465900attempt1nonterminal; no rerun. Fullaudit/fullregression not repeated. Structural assertions recorded in VERIFICATION.json.
- **Recovery:** Add superseding decision and ordinary descendant revert of Main coordination delta if defective; never rewrite/deletetheCDR/PIW/history/rawfailures/owner sources. Currentlease released with completed checkpoint, nolease held for CI. CanonicalcandidateNOT_READY, MainREADY0 after completion; only realterminalCI/newowner/materialsources reactivates exactscope.

## PIWD-014 · CDR-024 exact adoption and post-merge state reconciliation · 2026-10-05T10:12:00Z

- **Decision:** consume explicit CDR-024 adoption, preserve CDR-024 verbatim, and reconcile stale Main state/owner routing after the exact Global merge.
- **Authority/SSoT:** CDR-024; adopted v1.1 blob `4736bbcb508ce1f4310fbe96cbcfdd8e080b275f`; PR #48 merge `82de599ee90a6beabd774dd22e7e2b939ff75b44`.
- **Alternatives:** stale PROPOSED_NOT_ADOPTED state (rejected); rewrite CDR-024 (rejected); append identity clarification and state receipt (selected).
- **Alignment/protections:** append-only, exact-parent non-force publication, watcher read-only and Gate A fail-closed. No canonical, Holdout, Official/LIVE, production, paid, credential, financial operation, PIT/Frozen/history, QGV-production-semantic or owner-scope grant.
- **Verification:** three-file diff and blobs revalidated; CDR-024 remains single; 11 gaps/Gate A disabled; D3 = 7 reserved / 1 candidate / 3 dependency / 0 executed.
- **Rollback:** mutable live state can be superseded by later exact evidence; append-only history is not rewritten.

## PIWD-015 · CDR-027 bounded Chart owner routing and FPIA nomination · 2026-10-06T09:49:45.650Z

D1/D2 under explicit CDR-027 / adopted CDR-024. Preserve6owner gates; source ownership is not inferred from GitHub login or existing frozen contracts. Publish #54 with concrete unclaimed branch/write-set proposals; current P01/Web requests supplemented only with authority/evidence delta. Reconfirm original three-additive-asset Main planning acceptance on fresh exactacaf; no product/source/Web implementation authorization or whole-gate closure.

Nominate exact candidate verifier/workflow manifest33 with fresh actual workflow8479 versus subject7215/job111679955410/artifact11335872268 bindings; byte agreement/CI/observed runtime are distinct from independently accepted trust/external coverage/GIE. Alternative self-trust or invented source facts rejected.0newD3-A;0protectedsemantic decisions.

Verification: scoped schema/nonclaim predicates,19unresolved source rows,33blob equalities,3absentordinarypaths, artifactdigest/run/attempt/head identity, actual runtime-source log,4comment exactbytes/IDs and sourceissue readback. Existing tests/raw evidence reused, nofullaudit/test/rerun. Rollback: later superseding coordination record and ordinary descendant changes; preserve every original receipt/comment/history. Five-taskcycle ends with ownlease release/READ_ONLY restoration, no unattended activation. Actual source-owner claims/Product-Web returns/independent reviewer/runtime/GIE remain dependencies. [Receipt](evidence/main_chart_owner_cycle_2026-10-06/FINAL_RECEIPT.json).


## PIW-SC-001 · 2026-10-07T11:03:58.150028+00:00 · Bounded Main evidence roles / inactive Phase A

Authority: CDR029/030 under CDR024. D1/D2 only,0D3-A. Main assigns three distinct free ordinary docs evidence scopes on one canonical-based new branch, without protected source transfer. Existing19row TARGET, unresolvedSecurity roster and authored Theme are returned as reference-only; no fabricated admission/version/IDs. New userdesign becomes inactive PhaseA contract; oldcomponents reused and all protectednumeric/runtime activation deferred.

Operational QGV d156 return consumed with12exactpayloadmatches;193existingchecks reused. Platform3d997 state consumed only; no sourceACK. HG selectors corrected against latest register, historical records retained. Independent review PASS_DOC_SCOPE. Recovery: superseding append-only records and ordinary descendant docs, no history rewrite. Cost if wrong: later docs correction or branch/path split; no runtime behavior changed. Chart6gates/19sourceadmissions unchanged; finalmode restoration closes this5taskcycle.
