# Independent chart-contract challenger — 2026-10-04

Reviewed exact HEAD `68780785688bec33d4bdceb5c42769be7739e6b0` in chart-work, plus read-only coordination ref `bb4cb174fd4a0af3b2281d4c37ae3abb4d540f88` (GCH-014/CDR-014). No repository edits or commits performed. Scratch reproducer: `chart_guard_probes.mjs`. Existing contract tests independently rerun: 26/26 PASS. Passing tests do not disprove findings below.

## Material fixes recommended before raw-store ingestion or wider display

| Finding | Evidence in contract.mjs | Reproducer result | Minimal repair |
|---|---|---|---|
| G1 — malformed Yahoo columns silently accepted/truncated | lines 49–56 select quote[0], index optional fields | open={0:100} accepted; close=[102] for 12 timestamps accepted; extra close record ignored; second quote object ignored | Require exactly one quote object. Supplied columns must be arrays with timestamp length, retain explicit null cells. Entire absent column may deliberately become null if documented. Reject ambiguous/malformed containers. Empty response test must empty matching columns rather than retaining 12 orphan values. |
| G2 — persisted Alpaca candidate can claim raw while request disagrees | validateCandidate 102–103 only derives basis from provider | normalized candidate mutated to request=null or adjustment='all' passes with RAW_REQUEST_DECLARED | Share provider-declaration validation between normalization and persisted validator; recheck 1Day/raw/feed/currency and currency equality. This validates declaration only, not server compliance. |
| G3 — impossible capture chronology | fetched_at parsed at 98 but unused against points | fetched_at=2023-01-01 accepts bars in Jan2024 | Reject point time later than fetched_at (alongside existing as_of bound). Do not require fetched_at<=as_of: legitimate later retrospective capture remains NOT_VERIFIED for PIT. Do not consult wall clock in deterministic replay. |
| G4 — metadata type confusion | 47–48 copy arbitrary values; validator no check | timezone={x:1}, currency=['USD'] accepted | null or nonempty string shape; timezone, when used for date mapping, must be recognized IANA timezone. No invented default currency or exchange zone. |
| G5 — conflicting interval evidence ignored | 45 chooses metadata ahead of ctx.request | meta1d + request1m accepted | If both declarations exist, reject conflict; preserve explicit provider interval evidence in candidate so standalone validation can check it. Never relabel unknown/minute input. |

## Deferred/explicitly limited rather than invented policy

- G6: two times within one UTC day (00:00,01:00) accepted as DAILY_OHLCV because only exact timestamps are unique. Current renderer shows a UTC date for each. This is a real daily-display ambiguity, but globally requiring UTC-date uniqueness is not an exchange-session policy. Retain instant identity; before real daily display provide an explicit source/session date mapping and unique mapped-date check. Unknown session/timezone can remain blocked. Synthetic demo can state UTC fixture scope. No calendar, holidays, session-end, DST or corporate-action methodology should be invented here.
- G7: `corporate_action_refs` can be mutated from [] to arbitrary values and validator accepts them. For this candidate version, enforce an empty array because no verified corporate-action adapter exists. A future real adapter needs authenticated refs and an independent change.
- Candidate validation cannot authenticate a mutable doc's source values against its hash without loading original bytes; normalization does load and hash bytes. A hash-shaped string in persisted JSON is not proof of derivation. Raw-store bridge should re-normalize exact bytes and never accept caller-provided `synthetic=true` as publication authorization. DEMO state is a label, not an attestation service.
- Missing numeric values, volume zero vs null, adjustedclose separation, nonfixture publication blocking, ordering, exact duplicate, basic OHLC envelope, and raw-byte hash mismatch protections work in inspected tests.
- `fetched_at > as_of` is intentionally valid in current fixture (Jan14 capture of Jan13 cutoff). It must not be “fixed” into PIT eligibility or rejected automatically. Actual available_at/source vintage remains unknown, and current code honestly keeps NOT_VERIFIED.

## Ownership and FPIA assessment

PR41 branch diff from canonical consists only of 17 added files beneath `implementation/experiments/chart-contract-v0.1/`. No existing src, tests or workflow paths changed; worktree clean at review start/end. No duplicate network client, provider account access, MCP server, scoring or production route is implemented. Narrow demo hardening and read-only original-byte import are reasonable autonomous work on this owner branch.

GCH-014 records CDR-014 hardened Frozen Projection Identity Audit as approved and in-progress; it is not an integration PASS. Frozen records remain exact-tree history, code identity must remain SAME/DIVERGED as observed, and JS/docs additions can still interact with closed-world acceptance. Landing needs exact merge-result owner/FPIA handling; isolated path is not an exemption. Do not edit another owner's branch, repin historical hashes, issue research/Official/LIVE grant, consume Holdout, or claim canonical completion. User's continuation permission supports scoped implementation but should not silently convert synthetic validation into protected production publication.

## Recommendation

Keep API-first/shared read model, optional read-only MCP later. Fix G1–G5 and G7 with focused structural tests now, then re-run the probe set. Solve G6 through explicit display-time contract when real daily bars are displayed; do not expand into a market calendar engine. Current review status: VERIFIED_WITH_FINDINGS for isolated demo; NOT_READY_FOR_REAL_PUBLICATION. No payment or account blocker exists for these repairs.

## Follow-up independent verification (working tree after parent repairs)

- G1/G2/G3/G4/G7 original probes now reject. G5 normalizer conflict rejects, but persisted `validateCandidate` still accepted `provenance.request={interval:'1m'}` at contract sha256 `7b0359039469b57558a3f9ef3de48cb99d3b5b143972eb65ab49b1fce82acaac`; parent informed for final small repair.
- Fetched-after-as_of remains accepted and NOT_VERIFIED as intended. G6 same-day labels remain deferred explicitly, not a production readiness claim.
- Independently rerun contract tests:34/34PASS.
- Read raw_store_bridge.mjs and independently ran its13/13 tests. Inspected bridge sha256 `19aa2dd2c9e0aaf3d4cf72db6393a00b9961dd1fff43fe4d36f430318e30e926`.
- Static review briefly observed unsafe `...identity` spread after `synthetic:false` constants. Bridge author/parent changed this during review to whitelist four identity keys. Fresh direct temp-store probe with identity.synthetic=true confirms actual candidate stays synthetic=false, NOT_AVAILABLE and renderer blocked. This is a static finding repaired before independent runtime reproduction, not a proven prior runtime exploit.
- Read-only bridge rejects byte/hash mismatch, malformed/path-mismatched request metadata, symlink redirection and missing/contradictory source evidence in tested scope. It explicitly preserves CALLER_SUPPLIED_NOT_INFERRED identity and LATEST_STORED_RECORD semantics, no PIT/publication claim. No remaining material blocker for this offline importer found beyond the shared candidate G5 residual.

### Final contract disposition

Parent repaired persisted Yahoo request interval conflict and retained a regression. Independent rerun:35/35PASS; direct candidate mutation now rejects with `daily interval evidence conflict`. G1/G2/G3/G4/G5/G7 are repaired for candidate scope; G6 remains explicitly deferred to source/session date mapping before production daily display. No optional broad probe expansion is required. Identity-free preflight is a separate pending review delta.

Final inspected contract SHA-256: `8f67e2883d593c12b2b59e711c52024871b43951fa9f0732bfbb022be3a3805a`.

### Identity-free preflight delta

Reviewed bridge sha256 `15cf46afe5bf32f8728104a7b8a807ac24c318b2c0d1b76e023389e776f224a9`; independent14/14 bridge testsPASS. `inspectStoredArtifact` correctly emits no full candidate, no identity inference, acquisition_at=null, latest-slot/source-byte consistency only. Its updated evidence distinguishes store persistence from acquisition.

One narrow container-shape defect remains at this reviewed hash: replacing quote with `[[]]` is accepted and emits STORED_BYTES_AND_SHAPE_ONLY. Direct reproduction saved in scratch `chart_preflight_probe.mjs`. Require quotes array + exactly one nonnull nonarray object, same as normalizer. Numeric/OHLC envelope validation is intentionally not claimed in this preflight; no request to duplicate the full contract validator.

## Final independent re-verification — stable working tree

This final section supersedes the earlier pending dispositions while preserving their failure history. The reviewer changed this review file only; no implementation/test edits or commits were made by the reviewer.

Final checks performed at parent request:

- The exact malformed preflight quote probe (`quote=[[]]`) rejects with `one quote object required`.
- `npm test` independently rerun: **56/56 PASS** (36 contract, 17 bridge, 3 source replay tests), no skips. This includes offline replay of the captured five-row response. It does not represent a fresh provider call made by this reviewer.
- No further broad probes, full repository regression, production publication or canonical integration were attempted.

| Reviewed file | SHA-256 |
|---|---|
| contract.mjs | `5f10a4975dc1fe40c79171158187328bbf202043ea0a1e5a59e6ddaa5bdc7fbd` |
| raw_store_bridge.mjs | `7d84b10835b046dfe015ce43e9dfb04f1437c734dbc6ee2f7feb4735ca3a0b05` |
| source_replay.test.mjs | `74a0bda235ef297756970a731426bd6e88ebb05f75b98db82b744962fc54d257` |

| Issue | Final disposition |
|---|---|
| G1 malformed/alignment-ambiguous Yahoo columns | REPAIRED; strict container and supplied-column length checks. Missing whole field remains explicit null. |
| G2 persisted Alpaca raw declaration mismatch | REPAIRED; request declarations rechecked by candidate validator. |
| G3 bar later than recorded fetch/store timestamp | REPAIRED; later retrospective acquisition remains permitted without PIT inference. |
| G4 malformed currency/timezone | REPAIRED for supported candidate metadata scope. |
| G5 conflicting daily interval declarations | REPAIRED in normalizer and persisted candidate validator. |
| G6 daily date/session mapping | DEFERRED explicitly; no production daily-display readiness claim. |
| G7 unverified corporate-action references | REPAIRED; this candidate version requires none. |
| Identity spread overriding synthetic=false | REPAIRED; whitelist plus direct poisoned-input test confirms withholding. |
| Identity-free preflight malformed quote container | REPAIRED; exact counterexample now rejected. |

`STORED_BYTES_AND_SHAPE_ONLY` is an appropriately narrow inspection label: no company/security/listing identity is inferred and no chart candidate, historical availability or publication grant is created. Store persistence time is distinguished from unavailable acquisition evidence. It is not full numeric/OHLC/PIT validation. Unsupported provider kinds must remain unsupported-source classifications rather than corruption or failed Yahoo interpretation; the review does not convert renamed storage slots into Yahoo provenance.

Final outcome: **VERIFIED_WITH_EXPLICIT_LIMITATIONS** for the isolated demo, contract hardening, read-only candidate bridge and byte/shape preflight. **NOT_READY_FOR_REAL_PUBLICATION** remains correct. Ownership/FPIA and G6 dependencies above are unchanged.
