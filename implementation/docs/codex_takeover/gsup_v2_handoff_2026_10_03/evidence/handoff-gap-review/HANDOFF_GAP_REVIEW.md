# PR31 bounded handoff gap review

Live read-only GitHub observation: PR31 is Draft/Open at exact
`675d0d298fbaab5b8473ed048a561ef84e2f3e78`, based on
`86ad3628dd5c62c6d873e42511e577f24f4fb588`; PR35 is Draft/Open at
`fc6720bdc8143e97bf25e37e4091b1f2aa54b69f`, based on675.
Latest routing examined: Global `994eb114ef14838d09d6233cfd2367d4d19738e2`.
Scoped approval blob `a5279d516c028f0a8cb9166ee2d54366da00877b` remains exact.

The synthetic source identity protocol, its unchanged-v1 compatibility wrapper,
independent negative validation and arithmetic diagnostic are complete within
their approved software scope. They can become **HANDOFF_READY for read-only
validation**. The authoritative M-B v2 production kernel is absent/inactive and
remains DESIGN / USER_DECISION_REQUIRED_ARITHMETIC_REDUCTION. A handoff must
retain that separation. This review does not certify the full method as implemented.

## CDR008 thirteen-point acceptance mapping

| Item | Result at675 | Exact qualification |
| --- | --- | --- |
| 1 exact HEAD | PASS | Live PR31 head675, base86ad; source/tree identities retained |
| 2 approval record | PASS | Approval recorded before implementation at823; exact JSON bloba5279 |
| 3 changed files | PASS | Baseline existing source/tests unchanged; two new source modules and approved additive tests/tools/evidence |
| 4 v1 preservation | PASS | Existing owner EVL and baseline source/tests retain exact bytes; old v1 CE4 p=.15 reproduced by this reviewer |
| 5 M-B↔v2 exact agreement | DEFERRED | Authoritative new v2 does not exist; arithmetic choice remains required; legacy invariance is not M-v2 agreement |
| 6 p=.10/.15 counterexample | DIAGNOSTIC COMPLETE; production v2 NOT_RUN | Historical owner CE4 M=.10/v1=.15 retained; newer three-reduction traces separately expose .10/.20 and .35/.40; no active v2 result is claimed |
| 7 source/vintage/sample negatives | PASS SYNTHETIC | Metadata-only admission, incomplete lineage, overlap, TOCTOU, historical opaque and response identity failures covered |
| 8 2.0→2 rejection | PASS SYNTHETIC | Existing source identity blocks reencoding replay before a second provider call |
| 9 campaign/root/label bypass | PASS SYNTHETIC | Shared authority is pinned outside attempts; privileged coordinator reset is explicitly outside threat model |
| 10 targeted regression | PASS | Native675 JUnit contains source33, adversarial48, invariance11, diagnostic20 without failures/skips |
| 11 full regression | PASS ON EXACT675 | Archived native JUnit1277/0failure/error/skip reparsed; no full-suite rerun in this review |
| 12 Actions | PASS ON EXACT675 | Eight observed successful runs; native675, inherited547676d distinct SHA/tree-identical; Macro actually4a07099 |
| 13 CAL_VERIFY/Holdout untouched | PASS BOUNDED SCOPE | Synthetic fixtures only; real numeric/access/Frozen/grant gates remain unapproved |

The current scoped decision register is an approved additive record, with owner
prefix preserved. Old pending M-vs-K/source-descriptor statements are superseded
only by the explicit scoped approvals. The latest Global still retains
date-qualified historical lines saying no Codex TrackC branch existed and older
IF1 pending wording; those are HISTORICAL/SUPERSEDED routing text, not current
source or policy authority. Its arithmetic gate and CDR008/009 owner restrictions
remain CURRENT. No Global, scoped register or historical evidence was edited.

## Independently READY gap and dependency implications

The consolidated checkpoint/CI audit exists on the audit branch, but is not part
of exact PR31 source675. A new **additive branch-scoped handoff/status/manifest**
is READY. It must link exact current source and existing validation artifacts,
declare the thirteen-point partial/deferred method scope, expose the new-head CI
state and identify the separate PR35 F1 guard repair. It must not move historical
pins or claim a completed authoritative kernel. Root owns this documentation.

Root has selected `implementation/docs/codex_takeover/gsup_v2_handoff_2026_10_03/`
for all new JSON/driver/review artifacts, preserving `reports/**/*.json` inventory.
This addresses the discovered Entity Metadata whole-stdout inventory effect.
If any report JSON is nevertheless added, its inventory change needs separate
classification rather than a historical fingerprint rewrite. C8 code_hash covers
source `.py` only, so static docs do not affect it. Legacy TrackC acceptance tools
also enforce an owner addition scope; combined integration must retain its
explicit existing scope qualification rather than weakening those tools.

PR35fc is ahead4/behind0 from675, merge-base675. Adding PR31 docs creates a new
head that is not yet an ancestor of currentfc. Root should normal-merge the new
PR31 head into its PR35 descendant. All prior history and F1 implementation remain
preserved; no rebase/reset/force-push is needed. Existing1277 PASS at675 and1295
PASS atfc become **historical exact-head validation** when either head moves.
Source/test/workflow equality may be recorded separately but does not make an old
Actions run fresh for a new SHA. Root plans actual new exact-head Actions before
publishing final handoff freshness.

## Checks actually executed

Fresh PR31/35 connector reads; fixed-SHA source/AST/blob/prefix checks; archived
native675 JUnit parse; exact existing-source/test/workflow/reportJSON comparison
against the current675 worktree; one explicit synthetic v1 CE4 kernel call that
reproduced p=.15/r2/degenerate1. Existing report inventory is unchanged. No
provider/realCAL/Holdout read, full suite, Actions dispatch/rerun, source mutation,
commit, PR update or remote write occurred.

`bounded_checks.py --candidate-root <root-worktree> --output <receipt-name>` is
ready for the primary writer's post-copy read-only verification. It asserts exact
source/test/workflow/old reportJSON bytes and identical report inventory. Root
will then separately verify the committed doc-only path allowlist, optional
register append, normal dependency merge and actual new-head CI. Until those
steps, current675 checks do not certify a not-yet-created doc head.

No implementation defect or independent READY source work remains within this
bounded handoff review. Authoritative M-v2, actual numeric configuration, real
CAL_VERIFY/Holdout, foundation unification, C8 Freeze, grants, canonical merge and
deployment remain separate gates. This is a handoff review result, not percentage
progress or a software/real-data promotion.
