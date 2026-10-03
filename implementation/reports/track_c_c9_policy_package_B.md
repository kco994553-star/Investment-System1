# Package B — C9 sealed Holdout transaction contract proposal

Status: PROPOSED / NOT APPROVED / NOT ACTIVE. Recorded: 2026-10-01 10:45:14 UTC.
Checkpoint:15fed506d4e67d89861221281e4879002e431b4a.
Preparation only. No Holdout content/result, storage credentials, dataset address or
consumption authorization is read or created. Real Holdout remains UNCONSUMED.
Authority: EVL_SPEC_v0.1 sections2/3/10/11; C0 HoldoutState/FreezeManifest.
Package A is a separate unapproved dependency.

## 1. Current contract
Final Holdout is isolated from the research optimizer, can be consumed once, sets
HOLDOUT_CONSUMED=true, and a failed Holdout is not reused for tuning.
Parameters and thresholds are frozen; FROZEN precedes HOLDOUT_TESTED.
C8 owns qualified Manifest; C9 owns once-only runner; no automatic Official promotion.
Current source has HoldoutState metadata but no sealed store/transaction/consumer.

## 2. Unresolved decisions
Consumption identity/unit; multiple profiles/roles; content-read versus durable record
ordering; exclusive claim, crash/recovery/retry; minimum support and exact decision
gates; execution authorization; software-only acceptance versus real consumption.
The current user approval explicitly excludes real Holdout consumption.

## 3. Proposed contract — exact approval items B1-B10
### B1 Consumption unit
One global sealed DATASET identity/commitment per registered final research campaign
is consumed ONCE, not once per profile, candidate, experiment directory, branch or run.
The external authority maps immutable campaign_id+holdout_dataset_id to a single
consumption record. Renaming an experiment/manifest cannot reopen the same dataset.
A new independent dataset/campaign requires separate research/authorization; prior
failed data never becomes tuning or a new eligible final Holdout.

### B2 Immutable multi-profile batch
Bind one ordered, preregistered batch of all three profiles and their designated
Champion/Challenger identities (six role entries; deduplicated prediction identities
may have multiple role references). Register roles, model/parameters/thresholds,
metrics/gates, partition bounds, code/config/data/vintage/Manifest hashes and
consumer identity before first read. Preserve all C7 tie/qualification lineage.
No arbitrary extra tied alternatives or adaptive candidates can enter the batch.
Identity substitutions, post-result batch extensions and favorable-profile reporting
are forbidden. One incomplete required profile/role blocks the batch preconditions.
This proposal's choice of assessing both roles is a policy decision, not an existing
six-role consumption rule. Alternative Champion-only is stated below.

### B3 Preconditions
C7 SOFTWARE Freeze and C8 approved runner are necessary software dependencies but
do not qualify a real batch. For real read: complete current REAL_PIT_RESEARCH_VALIDATION,
ALL registered C8 gates PASS, explicit real FROZEN Manifests, resolved source/approval/
code/data lineage, exact sealed commitment, all role entries, frozen real Holdout
evaluation plan and separate execution authorization must be present.
Missing evidence -> NOT_RUN before content access; observed integrity/invalidity -> FAIL.
Synthetic artifacts can never satisfy these checks. The runner has no fit/calibrate/
search hooks; research modules cannot obtain a sealed provider handle.

### B4 First-read / consumed ordering
Acquire the campaign/dataset exclusive transaction lock; recheck UNCONSUMED and all
bindings/authority; atomically write, flush/fsync and externally checkpoint an
append-only CONSUMED event BEFORE any content reader invocation.
Only after durable publication can the authority release the sealed read capability.
Record transaction_id, dataset/campaign commitment, complete batch_hash,
all source/candidate/Manifest hashes, consumer_id, code_commit/content_hash,
config_hash, authorization_ref, first_consumption_timestamp, writer/checkpoint identity.
Use existing canonical UNCONSUMED/CONSUMED; transaction phases are journal metadata,
not new profile lifecycle states.
Process-local file locks/hash chains alone do not protect against replacing the whole
store/ledger: real consumption requires protected shared authority/durable externally
retained checkpoint. A local synthetic store exercises the protocol but is not proof
of production security/durability.

### B5 Frozen evaluation
Bind exact model/predictor/threshold hashes; prediction receives only PIT features
and decision timestamps. Labels/outcomes become available solely to a separate
scoring stage after frozen prediction persistence.
Bind every prediction/result to transaction/batch/Manifest/dataset/code/config/metric
versions, decision_time/outcome publication/evaluation_time, provenance and vintage.
No threshold calibration, parameter mutation, fitted weights or candidate selection.

### B6 Crash / recovery / retry
Before a durable consumed event, recovery may retry ONLY metadata/precondition checks
under the same unconsumed authority; no content access has occurred.
After the event, there is NO second sealed content-open operation and no consumption
rollback, even if the crash occurs before the first actual read or the read fails.
After complete immutable prediction/result persistence, recovery may verify/checkpoint/
finalize those already stored bytes idempotently, using the same transaction/bindings.
It may not rerun prediction/scoring to seek another result or reopen the dataset.
Interrupted partial evaluation -> terminal failure/insufficient result evidence;
CONSUMED remains true.
This is conservative once-only semantics and may sacrifice a dataset on infrastructure
failure. The alternative resumable protocol would require additional approved enclave/
sealed cursor/protected journal design before any real use; it is not silently enabled.

### B7 Gate and failure result
Preregister the real Holdout evaluation metric paths, threshold hashes, required
coverage/support, resampling family and gate policy BEFORE B4. Package B supplies no
actual sample minimum, alpha, risk premium or numeric limit.
Recommended: apply the already frozen C8 hard-gate definitions/limits on the Holdout
batch with explicitly registered Holdout-specific support and inference dimensions;
never recalibrate those thresholds or retune resampling after read.
Any mandatory gate FAIL/NOT_RUN blocks batch promotion. Preserve each role/profile
result and every assessed hypothesis; no favorable-subset batch success.
Well-supported failed real validation follows existing REJECTED policy; missing result
evidence is NOT_RUN with no successful HOLDOUT_TESTED/promotion transition.
Observed material source/lineage invalidation follows INVALIDATED or SUSPENDED under
approved mapping. Trial/report failure and profile lifecycle remain separate fields.
HOLDOUT_TESTED is granted only for complete accepted real evaluation after explicit
result approval; evidence of an unsuccessful attempt remains immutable but does not
masquerade as a successful lifecycle transition.

### B8 Post-Holdout mutation and authorization
Separate signed/attributed approval events:
(1) batch execution authority names exact campaign/dataset/batch/Manifest/config/
code/consumer commitments and confirms once-only risk; (2) later result/promotion
authority reviews the frozen result and designates actual Official Champion/Challenger.
Package B approval authorizes software implementation ONLY; neither event is created.
No timestamp is invented before the actual authorized action.
Any post-Holdout candidate/model/parameter/threshold change requires RESEARCH_REOPENED,
new preregistered research evidence and a separate unused Holdout; never reread the old
content for tuning. Administrative verification of existing hashes/reports can continue.
No new lifecycle state such as HOLDOUT_READY is needed.

### B9 Synthetic sealed store and persistence architecture
Distinct namespace root and authority registry tagged SYNTHETIC_SOFTWARE_VALIDATION;
fixture configuration values tagged SYNTHETIC_SOFTWARE_VALIDATION_ONLY.
Synthetic reader tracks open_count and throws on a second open. Register metadata/
commitment without content access; access instrumentation proves zero pre-authorization
reads and zero reads in C0-C8/C10. A fake clock is injected and labeled synthetic.
Journal events: metadata registration -> authority check -> durable consumption ->
content-open audit -> immutable predictions -> immutable result -> terminal checkpoint.
The event names describe storage operations, not new lifecycle states.
Use exclusive writes, canonical serialization, locks/fsync and external checkpoint
interface. A path prefix/scope flag alone cannot authorize real access.
Real provider is dependency-injected separately and unavailable to default fixture CI;
no real dataset path/credential or network access belongs in acceptance fixtures.

### B10 Software Freeze
C9 SOFTWARE FROZEN may be supported by complete deterministic synthetic transaction
and algorithm acceptance only, with positive and blocking negative/concurrency/crash
cases, targeted->C0-C8->full->PIT/lineage/Holdout isolation/ledger/budget/invalidation/
cross-track audits->immutable evidence->actual Actions.
Synthetic consumption mutates only the synthetic authority's state; real stays UNCONSUMED.
Scope resolution must reject synthetic result/Manifest as real HOLDOUT_TESTED/OFFICIAL
or a real consumption authorization. Actual Holdout test remains NOT_RUN.

## 4. Alternatives
B1: per-profile/per-candidate consumption permits repeated exposure to the same unseen
data; recommend one dataset/campaign transaction with an immutable batch.
B2: Champion-only three-profile batch (less multiplicity, leaves Challenger untested);
both roles (complete role evidence, more hypotheses). Recommend both preregistered roles.
B4: consumed-after-read is less wasteful but has a crash window for duplicate reads;
recommend durable consumed-before-read.
B6: resumable exact committed read/predict operation may reduce data loss but needs a
protected capability/cursor and proven replay semantics. Recommend strict no-second-open
for baseline, with metadata/result finalization only.
B7: atomic batch qualification versus profile-wise promotion. Recommend atomic required
three-profile qualification because distinctness is jointly assessed.
B8: automatic promotion from result PASS conflicts with current explicit ownership;
recommend separate attributable result/promotion approval.

## 5. Result impact
Batch choice changes tested identities/multiplicity; B4/B6 can consume data without a
result; B7 determines qualification and lifecycle; B8 controls Official authority.
These require D3-P approval and explicit real execution authority before real read.

## 6. Overfitting / lookahead impact
Global consumption unit and fixed batch prevent repeated profile/candidate evaluation
on the same hidden data. Frozen hypotheses/limits prevent post-result tuning.
No crash retry creates a new inference attempt. Complete lineage and retained failures
expose all attempts. Confirmatory tests still need the preregistered family/selection
multiplicity contract; a hidden dataset does not waive multiple testing.

## 7. Recommendation
Approve B1-B10 for software semantics after Package A and C7 Freeze. Supply real support/
metric/method config and a separate explicit real execution authorization only later.
No automatic Holdout consumption follows from C9 SOFTWARE Freeze.

## 8. Exact approval target and implementation-ready interface
Approve/revise B1-B10 and specifically choose batch scope and crash policy.
APIs: register_sealed_metadata() -> resolve_real_preconditions() ->
consume_once(authority, exact_batch, authorization) -> predict_frozen() ->
evaluate_registered() -> finalize_existing_result(); no optimizer callback.
Proposed files: evl/holdout_contracts.py, holdout.py; tests/synthetic_sealed_store.py,
test_evl_c9_*.py; tools/track_c_c9_acceptance.py.
Failure injection at every persistence/open boundary; concurrent consumers; repeated
directory/experiment identity; mixed real/synthetic inputs; changed Manifest/code/config;
permission mismatch; missing coverage; label leakage; prediction mutation; late outcome;
partial reports; post-consumption new candidate; externally truncated/replaced ledger.
All expected failures must block acceptance and preserve durable consumed accounting.
Prepared machine draft: track_c_c8_c10_contract_drafts.json; inactive, no real address.
