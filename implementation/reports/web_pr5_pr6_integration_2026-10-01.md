# Web PR #5 → PR #6 sequential integration — PASS

Recorded: 2026-10-01 18:48:36 KST. Session start: 2026-10-01 18:12:58 KST.
Actual runner verification: 2026-10-01T18:46:09.153466+09:00 → 2026-10-01T18:47:08.438865+09:00.
Scope: Web implementation integration only. No new product feature, canonical merge, source repair, policy change or deployment.

## GitHub inputs and dependency

- Default/canonical branch: claude/investment-system-top500-validation-alrugm.
- Canonical HEAD: b8e39a2196a6d7794a04a0cd5393c68329e126ca.
- PR #5 / feature/web-mvp-v1: a4e49c83f5783c19617fb609b8f95b179cb13e84; base canonical; OPEN/DRAFT.
- PR #6 / feature/global-language-search-v1: eda65bf5d9203aee05f4d28992d1ccfcd815ebd4; base feature/web-mvp-v1; OPEN/DRAFT.
- PR5 is canonical +6/-0; PR6 is Web +4/-0 and canonical +10/-0.
- Merge-base(canonical, PR5)=canonical; merge-base(PR5, PR6)=PR5 HEAD. PR6 includes the whole PR5 ancestry.
- Track C at initial API audit: 88da6f30560c4a2aee281a4cc45760eb3e0f4e80; at runner fetch: 038f03cf45ad515d2e07522674dd496ed9cae0da; latest recording: fcc033545889a47c402164ca93464c021e474c33.
- Actual runner git fetch/ls-remote checked the pinned canonical and both PR heads before replay.
- Post-run GitHub refs confirmed canonical and both PR heads unchanged; both PRs remain Draft/Open.

## Execution environment and actual normal merges

GitHub Actions Ubuntu runner, Python 3.11, Node 22, Playwright 1.58.2/Chromium.
Validation harness branch: integration/web-mvp-language-search-audit.
Harness commit: 9fd8099fed59961f990cb64e99d4953a931ea508.
Workflow permissions: contents read. Checkout fetch-depth 0 and persist-credentials false.
A detached git worktree was created from exact canonical HEAD. Actual git merge --no-ff used the ort strategy.
No push/remote-ref mutation command exists in the runner harness. Track C was not merged.

| State | Temporary merge SHA | Parents | Tree |
|---|---|---|---|
| canonical + PR5 | 0238545974dc2ea0468fba9a536bccf687a77de2 | b8e39a2196a6d7794a04a0cd5393c68329e126ca + a4e49c83f5783c19617fb609b8f95b179cb13e84 | dd640e8b8900b4051369f2fae3a03277c3dcb2e0 |
| previous PR5 merge + PR6 | c24689311ad289f15b76b7f73e11ee1341cdfd31 | 0238545974dc2ea0468fba9a536bccf687a77de2 + eda65bf5d9203aee05f4d28992d1ccfcd815ebd4 | 7e03505f79202ff3f3a94d0054b6f74b48d84a49 |

Both merges have exactly two verified ordered parents. Conflicts: 0. PR5 merged tree equals PR5 HEAD tree.
Combined merged tree equals PR6 HEAD tree. PR6 was applied only after PR5 execution gates passed.
Temporary merge commits exist in the runner's detached worktree, not canonical or the evidence branch.

## Actual execution gates

| Gate | PR5 normal merge | Combined sequential merge |
|---|---:|---:|
| Web/Global Python targeted | 8/8 PASS | 13/13 PASS |
| Full repository pytest | 404/404 PASS | 409/409 PASS |
| Default and public DEMO static builds | PASS | PASS |
| Existing Web browser scenarios | 10/10 PASS | 10/10 PASS |
| Search/locale original Node checks | N/A | 26/26 PASS |
| New Global Language/Search browser scenarios | N/A | 8/8 PASS |
| Page errors | 0 | 0 |
| Responsive automated checks | 360/390/1280 px PASS | 360/390/1280 px PASS |
| Frozen acceptance manifest SHA256 | 17/17 PASS | 17/17 PASS |
| Modified/deleted canonical files | 0 | 0 |
| Tracked changes left by execution | 0 | 0 |

No failed/error/skipped Python cases; no test source/expectation edit. Full suite includes all 396 canonical cases.
Python full durations: PR5 21.54s, combined 21.44s. Responsive checks are headless Chromium automation, not a physical-device or manual visual QA claim.

Search cases include NVDA, nvda, NVIDIA, NVIDIA Corporation, 엔비디아, nvida, nvdia, 엔디비아, nvd, 엔비디; same canonical company route.
False-positive controls, normalization, prefix/substring/fuzzy, duplicate identity rejection and deterministic ordering passed.
Both ko-KR and en-US display locales passed. News source_language remains independent; original raw news/identifiers/provenance are preserved.
Frozen Prompt payload/preview, existing graph interactions, local preferences, settings corruption protection and Leaderboard supplied order/ranks passed.

## Numerical and cross-track preservation

QGV, Technical, Macro and Portfolio engines were actually executed with the same public synthetic inputs before and after PR6.
All output fields are exactly equal after excluding only each engine's newly generated top-level snapshot UUID.
No numeric or semantic field is excluded. No runtime module or UUID generator is patched.
All nine producer envelopes (Universe/QGV/Technical/Macro/Portfolio/Leaderboard/News/relationships/changes) are exactly equal across PR5 and combined default/demo builds.
Company presentation-name changes and explicit DEMO identity links are separately permitted metadata changes.
Browser locale toggles additionally preserve full data JSON, original identifiers/raw source and nontrivial supplied Leaderboard row/rank ordering.

All 7,698 canonical blobs are retained unchanged. Track A/B/C/D/E, common contracts, numerical engines, original tests and tracked Frozen artifacts have zero changes.
Frozen manifest's 17 files are rehashed against their stored SHA256 in both real worktree states.
Original external raw archives are not re-ingested/rehashed by this Web audit.
PR5 adds 16 files; combined canonical diff adds 25. The full exact file lists and merge output are in the companion JSON.

Track C advanced independently. Latest inspected delta from 038f03c to fcc033545889a47c402164ca93464c021e474c33 has Web path overlap 0; latest file list is in JSON.
This is a static compatibility/ownership audit, not Track C regression against Web or PR4 integration.
No Track C branch/source/evidence was written or merged.

## Immutable evidence

Workflow SUCCESS: https://github.com/kco994553-star/Investment-System1/actions/runs/36844773375
Job: 110312164374.
Artifact: https://github.com/kco994553-star/Investment-System1/actions/runs/36844773375/artifacts/11152153928
Artifact name: web-sequential-integration-evidence; bytes: 1439436.
ZIP SHA256: edec430319ae12901098612de8f01e4cf732441fa0225d0bf3aee2fcffe00797.

Artifact contains merge logs, summary JSON, targeted/full JUnit and text logs, engine outputs, default/demo data, browser JSON, screenshots and server/build logs.
Companion committed file: web_pr5_pr6_integration_2026-10-01.json.
Evidence branch contains only integration harness/workflow/report/evidence additions relative to canonical, no merged product implementation source.

## Readiness and remaining work

- PR #5: INTEGRATION_READY.
- PR #6: INTEGRATION_READY_AFTER_PR5.
- Combined: PR5_PLUS_PR6_INTEGRATION_READY / WEB_PR5_PR6_INTEGRATION_READY.
- REAL_PRODUCER_READY: false.
- DAILY_OPERATION_READY: false.
- PRIVATE_DEPLOYMENT_READY: false.

Integration execution blockers: none at the pinned heads. Any canonical/PR source-head change requires compatibility recheck.
Top-500 company-name/Korean/historical-alias coverage is separate producer metadata follow-up; it is not an engine/entity-resolution failure. No aliases were created.
Current real producer snapshots, actual holdings, operating feed and private hosting/access remain separate unconnected requirements.
Recommended future human-reviewed normal-merge order: PR5 → PR6, preserving ancestry; canonical merges require the separate explicit merge instruction.
This worker keeps both PRs Draft/Open and does not auto-merge, rebase, force push, deploy or introduce features.
