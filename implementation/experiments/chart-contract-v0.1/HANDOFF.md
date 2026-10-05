# Chart Contract capability handoff

Scope: PR #41 only; isolated experiment on canonical b8e39a2196a6d7794a04a0cd5393c68329e126ca. GCH-014 / bb4cb174 was fresh-read at continuation. This file is scoped evidence, not a change to Global Handoff or an integration-owner instruction.

| Dimension | State |
|---|---|
| Shared OHLCV candidate / read-only RawDatasetStore bridge | IMPLEMENTED; synthetic contract/store tests PASS |
| Actual source | One no-key NVDA daily5d response, HTTP200; five complete OHLCV rows; exact-byte offline source preflight PASS |
| Original historical raw baseline | NOT_REPLAYED; blobs absent from fresh checkout. Manifests alone are not data |
| Complete real identity / session / PIT | BLOCKED by missing sourced mapping and exchange-calendar/vintage evidence |
| Renderer | SYNTHETIC_VERIFIED; no real publication enabled |
| MCP server | NOT_IMPLEMENTED; optional future reader over shared payload |
| Canonical / owner integration | NOT_MERGED; exact merge-result FPIA NOT_RUN |

## Evidence

- `ACCEPTANCE.json`: 36 contract +17 store +3 captured-source tests =56 PASS. Browser:12 checks at each of360/390/1280px. No full existing Python regression or GitHub Actions success claimed.
- `reviews/chart_guard_review.md`: independent challenge history and final reviewed file hashes. G6 (daily bar → exchange-local session mapping) remains deferred; no UTC-day policy was invented.
- `evidence/2026-10-04-source`: immutable small captured response bytes, source URL, HTTP status, raw hash, acquisition window, later RawDatasetStore persistence and explicit no-identity result.
- `evidence/acceptance-demo-v1.json`: prior synthetic-only checkpoint retained.

## Reuse and boundaries

Reused `tools/fetch_real_data.py:_get`, `ingestion/raw_store.py:RawDatasetStore.put`, existing manifest layout and the common candidate normalizer. No network client or financial calculator was duplicated. Existing Python source, owner branches, Frozen records, numeric policy, publication grants, Holdout and canonical were unchanged.

These additive experiment files are not an exemption from closed-world Frozen checks. Before integration, the designated integration owner must assess the exact merge-result SHA under the current FPIA rules. Existing same-named `yahoo_chart` slots may contain `TIINGO_DAILY_RAW`; actual `source_kind` and original URL control adapter choice, never filename alone.

## Minimal next dependencies

1. A recoverable archive/source locator for original raw bytes matching frozen manifests, where historical replay is needed. Fresh data must not overwrite vintage claims.
2. Existing issuer/security/listing schema populated from sourced, dated identity records. Current ticker reports are not historical listing evidence.
3. Technical US Equity Session owner contract plus an exchange-calendar vintage for daily labels, finality and availability; provider timezone and currentTradingPeriod alone are insufficient.
4. Web/P01 integration and scoped publication disposition after readiness is evidenced. No grant is issued here.

No payment or account information was used or requested. Remaining data/identity/integration dependencies are explicitly recorded; no missing part is represented as completed.

## Portfolio / requirements continuation

Source-derived19-holding TARGET reference, unknown actual company types, separate fictional overlap fixture, and three portfolio display components now exist in this PR. Scope is REFERENCE/DEMO only. 19 unit tests +11 independent oracle checks (one covers40 generated portfolios) +3 viewport browser validation PASS; combined node suite75 PASS.

Requirements inventory: core81 preserved; repository additions24; Macro Candidate8 kept separate. New J7 rows require subsequent implementation layer audit rather than assumed completion. Detailed complete list: `CHART_INVENTORY.md`, machine-readable `chart_inventory.json`, with UI search/filter.

Next independent work can connect existing sourced Portfolio snapshots/classification histories while the price identity/session path continues. User-specified groups are not GICS; no actual account or company type is inferred. Preserve quarterly snapshots and missing-vs-none classification. Full historical identity, P01 and FPIA integration remain pending; no existing owner branch was changed.

## Current bounded owner closure routing — v0.5

This append supersedes earlier routing only; all preceding historical statements and evidence remain unchanged. Intake source PR41 HEAD was `d93c7ace37603d91f1d9342152c97e8acb3d4e8c`; published current HEAD is resolved from this file’s containing commit/PR metadata, not guessed from the intake pin.

Read [v0.5 scoped HANDOFF](p0-slice-owner-closure-v0.5/HANDOFF.md) and [bounded delta](p0-slice-owner-closure-v0.5/OWNER_CLOSURE_DELTA_v0.5.md), then the preserved v0.4 readiness report. Target IMPLEMENTATION_NOT_READY remains six distinct gates OPEN/zero CLOSED; Market admission0/19 with eight evidence families. Concrete owner-return packets and existing capability limits now define exact next inputs. No broad audit or requirement expansion.

Actual automatic continuation is configured in this same conversation: [scoped runbook/state/setup receipts](automation/RUNBOOK.md). PR events and pending-CI follow-up are separate; no pending CI exists. Approval/ownership protections persist. All Global and other owner branches remain read-only. No production code, package/protected/Frozen change or merge authorization is created.

## Executable owner-return preflight successor — v0.6

The current user continuation authorizes independent Chart-owned implementation
and verification. Read [v0.6 scoped HANDOFF](p0-receipt-preflight-v0.6/HANDOFF.md)
and [CLI usage](p0-receipt-preflight-v0.6/README.md) after the preserved v0.5
owner packets. The earlier evidence-only phase restriction does not prohibit
this additive offline tool. Source/Product/Web/Integration owner acceptance,
Frozen protections and prohibited canonical merge remain separate requirements.

Fresh intake was PR41 `a89ac6dd4336027ddab52b145ab87e3bc5edb3e5`. No owner
gate closed: IMPLEMENTATION_NOT_READY / 6 OPEN / 0 CLOSED; Market admission0/19.
New returned-slot preflight closes a tooling gap in v0.4's null-security-only
reference replay. It verifies preserved source/joins/weights/time and reports
untrusted filled claims without authenticating or publishing them. Final
29 unittest cases and6 actual CLI cases PASS; earlier75 Node experiment cases
re-executed PASS. Original current input remains INCOMPLETE (expected exit3).
Production L1→L5, browser/API, Actions and exact Chart merge-result FPIA are
NOT_RUN unless separately observed at the final subject; no production success
is inferred from these diagnostic tests.

Exact publication/evidence identities and source preservation are in the new
checkpoint's receipts and PR metadata. Prior audit/raw/anomaly/acceptance history
is unchanged. Only own Chart scope is written; no package or P01 digest impact.
Actual task inventory confirms both existing resume tasks enabled, with their
returned conversation IDs differing from the old setup record. Task IDs and
shared lease remain the routing controls; no task is recreated or moved.

Next: receive the six source/authority/write-set/FPIA owner receipts, run this
preflight at explicit decision time, verify actual owner evidence separately,
then rejudge the existing minimal production plan. A filled packet/CLI0 still
means INPUT_COMPLETE_UNAUTHENTICATED, not IMPLEMENTATION_READY. Other-owner
prerequisites are the current stopping condition; no new Chart D3 is selected.


## Scoped successor — dependency continuation v0.7

See [current checkpoint](p0-dependency-continuation-v0.7/HANDOFF.md) and [execution policy](p0-dependency-continuation-v0.7/EXECUTION_POLICY.md). Global CDR-015/016/017 and FPIA round-3 exact head are dependency inputs; 6 source/Product/write-set/governance gates remain open and Market admission stays0/19. Actual audit Main and CI tasks are enabled, old event task paused; latest user authorizes approved-write-set implementation automatically after actual closure. Earlier evidence stays historical.


## 2026-10-05 continuation — diagnostic repair v0.8

Fresh takeover a0ad46bb and verified shared lease ebeb8b1f; canonical/merge-base
b8e39a21, Global b3532a2e, FPIA42 actual11d2f25.
[Scoped handoff](p0-diagnostic-repair-v0.8/HANDOFF.md) preserves all history and
records six-gate/eight-gap rejudgment. Three actual independent diagnostic
repairs implemented: structured malformed JSON failure, truthful unattempted
reference replay status, and portable source-pinned nine-probe replay with
optimization-safe checks. Fresh33/33 unit tests;9/9 normal+9/9 optimized probes;
negative/guard checks PASS. Prior production/Market tests remain historical.
Lane A IMPLEMENTATION_NOT_READY6 remaining (A-G3 PARTIALLY_RESOLVED); no new
Chart D3. Lane B0/19, eight gap families, five UNKNOWN anomalies untouched.
PR42 six successful runs plus exact FPIA run37260997788attempt1 in progress;
final owner review/governance/GIE still absent. Existing Main/CI automation
remains enabled and Global-aware; prior writer release and43/43 output hashes
verified; no current reproducible framework failure. Current independent
repairs completed while only production owner dependencies wait.
Next: consume exact owner/CI evidence, authenticate adopted returns, rejudge;
when6close automatically implement accepted exact write set through E2E and
required actual-result FPIA. No material delta/action means read-only no-op.
Exact publication/coordination SHA and byte verification resolve from subsequent
PUBLICATION_RECEIPT/STATE and actual PR41 ref.

Late v0.8 intake: Global af264713 (CDR018/GCH016) transfers PIW to successor GPT;
PR45 17244b4 synthetic Platform harness is a downstream Chart consumer, no
Target gate closure/new prerequisite. Latest open count40. See v0.8 appended
handoff/LATE_OWNER_INTAKE/PUBLICATION_RECEIPT for fresh verified routing.

Terminal successor: exact PR42 run37260997788attempt1/11d2f25 SUCCESS; all7
sourceheadworkflowsPASS. FPIA_PASS/CODE_IDENTITY_DIVERGED; Tier1/Tier2SKIPPED,
verbatimFrozen-toolsFAIL and nonclaims retained. Completed run consumed and
pending queue cleared with history. A-G3 remainsPARTIALLY_RESOLVED awaiting
finalownerreview/decision/GIE; sixTargetgates/Market0of19/no newChartD3.
See v0.8 FPIA_TERMINAL_RECEIPT and terminal handoff append.


## 2026-10-05 v0.9 — SAMPLE UI repairs, exact late owner intake

History-preserving continuation: [scoped handoff](p0-fixture-review-v0.9/HANDOFF.md). Fresh start b6f15eef; verified lease/preparation eedab592; canonical b8e39a2. Global GCH0187a29 / PR46a3e3 consumed, old213 CI PASS preserved onlyoldsubject.6production gates remain OPEN (G2/G3partial),Market0/19/eightgaps,ACTUAL NOT_AVAILABLE. Existing SAMPLE renderer reused and repaired;75NodePASS,3new viewport runs and6existing browser runsPASS;5independent closure casesPASS. Context7 actual5.2.1 official cross-check and user-selected private MagicPath screenshot canvas complete. No production/source/protected/package/Global changes or newD3. Exact verified publication HEAD/hashes resolve from automation/STATE.json after remote verification.

Late exact CI observation: current a3e3 has six non-FPIA workflow failures (new D002 self-constraint regression), FPIA remains running; prior213 success is not latest-subject PASS. Optional QGV2ba semantics-only/storage-auth11dba audit do not close Chart source/authority gates.


## 2026-10-05 v0.10 — Risk-Proportional Verification adopted

Continue the existing safe checkpoint with [scoped handoff](p0-risk-policy-v0.10/HANDOFF.md) and [current risk policy](p0-risk-policy-v0.10/EXECUTION_POLICY.md). FAST renderer/mobile checks; STANDARD contract/negative/affected-integration/browser; CRITICAL only changed financial semantics with necessary independent verification. Default1 Chart owner, optional1 backend/PIT verifier. No default full regression/FPIA/adversarial or repeated immutable evidence audit. Existing Main/CI prompts read back exactly; cadence and protections unchanged. All105 prior output hashes compatible, so v0.9 completed tests/browser evidence reused without reruns. This policy-only checkpoint closes0 product requirements/0 production blockers and creates0 blockers; sixLaneA gates/Market0of19 remain. Global9cd598 adds only Main's PR46 repair lease; exact a3/run37267962000 still running. Production contracts unadmitted; SAMPLE frontend verified. Exact verified publication/coordination HEAD resolves from STATE and current PR41.


## 2026-10-05 v0.11 — PR #46 exact FPIA terminal failure

[Scoped receipt](p0-ci-followup-v0.11/PR46_FPIA_TERMINAL_FAILURE_RECEIPT.json) and [handoff](p0-ci-followup-v0.11/HANDOFF.md) bind PR46 `a3e3f6c` run `37267962000` attempt1/job `111628676484` to terminal **FPIA_FAIL**. Artifact verification passed; full regression failed 2/2184 at the two FPIA self-constraint tests. A-G3 remains OWNER_ACTION_REQUIRED; Lane A 6 open/0 closed, Lane B 0/19. Requirements closed0, blockers closed0, new Chart product blockers0, production-ready contracts0. No retry, PR46 write, production promotion or merge occurred.
