# IF-1 / C-28 independent takeover adoption audit

2026-10-03. Read-only existing remote branches; local detached no-commit trial merges only.

Authority: current CDR-004 (A1 + Technical owner adoption + separate current-dated Macro adoption). CDR-001 operational contract exact HEAD is f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798. Scoped authority and original evidence were read without changes.

## Exact refs

- canonical: `b8e39a2196a6d7794a04a0cd5393c68329e126ca`
- global_handoff: `f26dc7adbfedd9209e757b5e8566c665c7bbd677`
- worker_contract: `f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798`
- track_C: `b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565`

## Independent results

Real CPython 3.11.16 with pytest 9.1.1 matches the workflows’ declared Python 3.11 major/minor. Each row ran the original scoped tests at its proposal exact HEAD, then on that proposal + Track C exact HEAD merged into a detached trial tree. Each branch’s owner base equals merge-base (no owner drift).

| Owner scope | Proposal HEAD | Owner base / merge-base | Scoped tests before / after | Combined trial tree |
|---|---|---|---|---|
| technical_real_producer | `248e3d3e83db9a2db3d90583ae53929db936d0f3` | `a2e0790dd7fb267ebaa7d052acae59220ecf631e` | 16 passed in 0.08s / 16 passed in 0.06s | `0bc876f3e9a5ee5dab8bfe6473eb4de70409dadf` |
| macro_real_producer | `4a07099e36ec3cecda24b82ecedad53800f0aa81` | `61d3352d5d68c7830e924f17613598ca79fcec6f` | 11 passed in 0.18s / 11 passed in 0.15s | `610fbc575928ec499c989e5fc8a931f0f55283dd` |
| leaderboard_real_producer | `a4805dbcdf37b890f74f6d00c00952ff95b91c8f` | `0d48d863afec0d50481d585a3d1ae0e56d4b380c` | 17 passed in 0.43s / 17 passed in 0.42s | `704742b035c0d70d92e1393e1ff0165758dc9426` |
| technical_real_model | `5c9dd5abd760116df626e9b2e88e3fe48852066a` | `ce587040e7beb31b66a423eab6ca89767f2a2cf8` | 19 passed in 0.09s / 19 passed in 0.09s | `129925994f565d3a8eec1662d907b380b4fcd098` |
| research_publication | `dc7daf70a42fb3f2bbfe96a775a1654a92ff95c1` | `21039a0a7f9677b123abd8587fd8d89784a73a3c` | 13 passed in 0.29s / 13 passed in 0.28s | `cb84a4e3483154a43cf54844a5b744693a3eefc9` |
| us_equity_session | `9c71781c62e46a4f2972d58c1439ef6ca2a85b07` | `2c088cea34314af0ccc33fd2e2dc1ccf21502cb4` | 23 passed in 0.16s / 23 passed in 0.08s | `f985c56a33663c6a91abd2c88ee9a73ddd0523fa` |

All six independent semantic/field comparisons PASS: 103 direct synthetic Technical inputs, 46 direct synthetic Macro inputs (including threshold-adjacent fixtures), the original fingerprint tool’s 19 QGV and Technical fixture outputs, four Macro fixtures, Leaderboard fixture and synthetic Portfolio book. Existing fields retain values and JSON types. Exactly 688 added lineage keys per probe appear; only Technical and Macro serialized-shape fingerprints change. No score/regime/zone/state/ranking/portfolio-action rule changes. CAL_VERIFY and Holdout were NOT_ACCESSED. Synthetic book naming does not constitute an Official grant.

No proposal changes implementation/src. The adoption target changes models.py with exactly four appended optional fields on each of TechnicalSnapshot/MacroSnapshot, adds contracts/lineage.py, and adds evaluate_stamped entry points/imports to engines. Original evaluate() ASTs are identical before/after at all six trees. Original producer source and protected QGV/Leaderboard/Portfolio/Integration bytes are preserved by the proposal deltas and scoped regression checks. State-exact repin selectors retain old constants, accept only the selected state’s exact new digest, and fail partial adoption. No source was rewritten or changed to pass a test.

## Runtime diagnostic preserved

Initial CPython 3.12 execution had 12 PASS / 1 FAIL in P01 before and after: unchanged portfolio_official_book hash 7b0baaa07660bc0609fc1ec33b165cdffde31f2a01257515ba2d5531067e7694 differed from pinned 53d930a7e3d2009347ac36f84e8a3b7504e6e5e9b0a4fe62fa5d1fb1be5a4a68. Python 3.12 changed sum(float) precision. Evidence-only sequential-sum emulation reproduced the pin, then true CPython 3.11 reproduced it and all 13 P01 tests PASS in both states. No numerical algorithm or pin was changed. Original 3.12 logs/probes remain in python312/. Emulation is diagnostic, not test PASS evidence.

## Remaining integration-context compatibility items

- QGV test_qgv_producer_infra_compat.py and Leaderboard test_leaderboard_producer_infra_compat.py default paths assert the dependency is absent. In combined trees, the existing supplied-source path exercises real compatibility: QGV_PRODUCER_INFRA_SRC / LEADERBOARD_PRODUCER_INFRA_SRC can point to actual combined source. Any repair must retain branch-isolated coverage and validate actual integrated dependency rather than delete the guard.
- tools/qgv_producer_infra_compat.py SHARED includes models.py; tools/leaderboard_producer_infra_compat.py likewise. When compared with old pinned external Infrastructure tree, C-28 additive schema fails their byte identity. Current approved target should be verified via exact four-field AST delta plus unchanged protected QGV/other contract content and real outputs, with actual dependency mode/ref recorded; do not falsely call combined source old INFRA_PIN.
- .github/workflows/leaderboard-real-producer.yml broad git diff guard will fail approved integration deltas. Replace only in integration proposal with exact protected source/schema acceptance evidence; no blanket ignored files.
- QGV real workflow includes automatic git pull --rebase evidence commits. It was NOT_DISPATCHED here; read-only dedicated integration validation avoids that history mutation.

## Checkpoint

- BRANCH_STATE: existing six remote Draft proposals retained read-only; exact refs above.
- INTEGRATION_STATE: six text-clean local trial merges, scoped tests and independent output comparison PASS, no owner merge. Root performs separate all-capability trial regression.
- CANONICAL_STATE: NOT_MERGED.
- Maturity: unchanged; integration audit alone is not INTEGRATED or OPERATIONAL.
- Actions actually executed by this worker: NOT_RUN (root independently reads/validates remote Actions).
- USER_DECISION_REQUIRED: NO for approved audit. Canonical merge remains separately gated.
- Next autonomous action: root compatibility repair in actual combined integration context, preserving all proposal histories.

## Artifact hashes

- `pr11-technical-producer-after-probe.json`: sha256 `919859846ab00c407a02d8f0ad1040bb57d3680942b388326962958d89861331`
- `pr11-technical-producer-after-pytest.log`: sha256 `a69d2990726df276b5a4cfaeacac7f9093820d18ffed4eb92ce996c1b18f0c44`
- `pr11-technical-producer-before-probe.json`: sha256 `d112c0b12843fa88b76baa08d1b8c4ba29445827fecac7fa9f69fd0686bff0b3`
- `pr11-technical-producer-before-pytest.log`: sha256 `7f93bc43afc95267c0e35273a11ad60e5b37262b98e4c6fa02b6d95ef1f057f5`
- `pr11-technical-producer-merge.log`: sha256 `96bb6a194a796153cbd0c640642866371219451832063763d544b942a8d97c4e`
- `pr12-macro-producer-after-probe.json`: sha256 `919859846ab00c407a02d8f0ad1040bb57d3680942b388326962958d89861331`
- `pr12-macro-producer-after-pytest.log`: sha256 `ad02a8741201d47e6fca91bc0e613f043355714159e51d4751fb9cdc3fa74447`
- `pr12-macro-producer-before-probe.json`: sha256 `d112c0b12843fa88b76baa08d1b8c4ba29445827fecac7fa9f69fd0686bff0b3`
- `pr12-macro-producer-before-pytest.log`: sha256 `0c42ab8123fcb13fb141f85fe1c2ccfba497885db9741e077f51097581cc42ee`
- `pr12-macro-producer-merge.log`: sha256 `96bb6a194a796153cbd0c640642866371219451832063763d544b942a8d97c4e`
- `pr14-leaderboard-after-probe.json`: sha256 `919859846ab00c407a02d8f0ad1040bb57d3680942b388326962958d89861331`
- `pr14-leaderboard-after-pytest.log`: sha256 `e7295eefdf7692e1719c685c5d8a3edd1f0dc7f77f25aab9bd8153dec6d4def1`
- `pr14-leaderboard-before-probe.json`: sha256 `d112c0b12843fa88b76baa08d1b8c4ba29445827fecac7fa9f69fd0686bff0b3`
- `pr14-leaderboard-before-pytest.log`: sha256 `6da83c60180bebece7040432348b685adc5cf7c874c9e27876b09fe9a36f5ea2`
- `pr14-leaderboard-merge.log`: sha256 `96bb6a194a796153cbd0c640642866371219451832063763d544b942a8d97c4e`
- `pr15-technical-model-after-probe.json`: sha256 `919859846ab00c407a02d8f0ad1040bb57d3680942b388326962958d89861331`
- `pr15-technical-model-after-pytest.log`: sha256 `d30644bb1db9337ac1adce249e90cc224662e8ee76cab56508c92b579590c4c4`
- `pr15-technical-model-before-probe.json`: sha256 `d112c0b12843fa88b76baa08d1b8c4ba29445827fecac7fa9f69fd0686bff0b3`
- `pr15-technical-model-before-pytest.log`: sha256 `d30644bb1db9337ac1adce249e90cc224662e8ee76cab56508c92b579590c4c4`
- `pr15-technical-model-merge.log`: sha256 `96bb6a194a796153cbd0c640642866371219451832063763d544b942a8d97c4e`
- `pr17-p01-after-probe.json`: sha256 `919859846ab00c407a02d8f0ad1040bb57d3680942b388326962958d89861331`
- `pr17-p01-after-pytest.log`: sha256 `daeeeae4bf8d68b762163d903b7ff852a3427aabd71376a6286207fc2514bc75`
- `pr17-p01-before-probe.json`: sha256 `d112c0b12843fa88b76baa08d1b8c4ba29445827fecac7fa9f69fd0686bff0b3`
- `pr17-p01-before-pytest.log`: sha256 `581955483c307ccd4a0c065b7f00d71b3b75589d839aa32922f04b2e14b054ed`
- `pr17-p01-merge.log`: sha256 `96bb6a194a796153cbd0c640642866371219451832063763d544b942a8d97c4e`
- `pr18-us-equity-session-after-probe.json`: sha256 `919859846ab00c407a02d8f0ad1040bb57d3680942b388326962958d89861331`
- `pr18-us-equity-session-after-pytest.log`: sha256 `614e544c270f7bd0389babf1c69d82509429bd083bb1694b7a57efbae140246d`
- `pr18-us-equity-session-before-probe.json`: sha256 `d112c0b12843fa88b76baa08d1b8c4ba29445827fecac7fa9f69fd0686bff0b3`
- `pr18-us-equity-session-before-pytest.log`: sha256 `0b2d60910038563d9c68f9904c6be07577cdfc7b0f66acf2a1c6887d1d8e0358`
- `pr18-us-equity-session-merge.log`: sha256 `96bb6a194a796153cbd0c640642866371219451832063763d544b942a8d97c4e`
- `probe.py`: sha256 `2e1af594c34f3ab6cc397466f5392ad3c5255736829a09feb6d1174502b48de0`
- `results.json`: sha256 `6c7c1fb18d95da309605c4f2d873feb659a0819691bd1c4e2deb999972dde12e`
- `run_audit.py`: sha256 `a45b92098bcfddb02591a8726ba3a2267bedc495b373ad51cba36adc5b2b4abe`
