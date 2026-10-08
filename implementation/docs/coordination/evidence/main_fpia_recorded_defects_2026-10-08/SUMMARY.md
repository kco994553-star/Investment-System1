# Existing FPIA defect inventory

Current candidate: `7215a9f60ad7128b1748f405051eac684298614f` (PR47), stacked on PR46 `6fea6c7f0a191a4e621941ce3f6a7cac83a7f3d6` and PR42 `11d2f25ef8bef3459ca969f50eec190099f15ecb`. Global at intake: `71a19b66ec8a7bdc0b21e5543d558ef22d7631f4`.

25 intake IDs describe already recorded failures and repairs. No new findings, test cases or counterexamples were created. Every listed repair is inherited by the current candidate; no unresolved concrete implementation defect was identified in these existing reports.

| ID | Recorded failure | Existing fix |
|---|---|---|
| F1 | Literal executable source filenames with spaces or non-code suffix missed AC-32.spoof | `2135962a` |
| F2 | AC-32 workflow identity bypasses from literal expressions, confusables and invisible characters | `11d2f25e` |
| F3 | AC-32 claimed literal invocation and reached-source bypasses | `11d2f25e` |
| F4 | Explicit job and service container declarations missing external inventory | `2135962a` |
| F5 | Environment paths and OS user altered result hash or produced false FAIL | `11d2f25e` |
| F6 | Output verifier/run metadata and output handling gaps | `11d2f25e` |
| F7 | Fetch rejection parsing confused ref text or Unicode line separators | `11d2f25e` |
| F8 | AC-04 classification omitted new Track C namespace paths and summary printed empty details | `11d2f25e` |
| F9 | Verifier provenance inventory omitted files outside the primary modules | `11d2f25e` |
| F10 | Installed PyYAML dependency broke existing native owner CI | `523e702a` |
| F11 | Compound evidence identity accepted invalid GitHub owner names | `a3e3f6cf` |
| F12 | D002 implementation introduced threshold/SHA literal self-constraint failures | `6fea6c7f` |
| F13 | Applicability incorrectly treated relative imports and unresolved dynamic calls as outside scope | `50fa7f49` |
| F14 | Applicability skipped .pyw and extensionless executable source | `50fa7f49` |
| F15 | Workflow selected old subject checkout that could lack the FPIA tooling | `50fa7f49` |
| F16 | Workflow-source observer rejected separate workflow checkout or confused actual subject identity | `50fa7f49` |
| F17 | PR47 native CI retained a stale integration-branch workflow regression | `7215a9f6` |
| F18 | Shallow/incomplete Git inputs or fetch refusals could yield determinate statuses | `465354a6` |
| F19 | Frozen tools canonical premise trusted caller-local tracking ref | `465354a6` |
| F20 | A_V-type content without authenticated V ancestry was incorrectly not applicable | `465354a6` |
| F21 | Frozen tool stdout/stderr evidence was truncated instead of retained verbatim | `465354a6` |
| F22 | AC-32 spoof attribution and generic job-name collision scope were incorrect | `465354a6` |
| F23 | PR scheduling and subject/register/artifact collection omitted intended audit coverage | `50fa7f49` |
| F24 | Historical Frozen byte-protected-only scope was not explicitly disclosed | `465354a6` |
| F25 | Authority transport environment disclosure was missing | `babf0a41` |

PR46 exact `6fea6c7f`: recorded seven workflows SUCCESS; full FPIA regression 2184 passed, one explicitly disclosed optional live SEC node deselected. PR47 old `50fa7f49` retained one stale legacy workflow test failure in two native jobs (1 failed / 2241 passed). `7215a9f6` corrected that existing test: local 294 affected checks passed, six native jobs each passed 2242 tests, and the seventh FPIA workflow completed SUCCESS. FPIA job Tier1/Tier2 were skipped and are not claimed passed.

F1 preserves the original same-subject literal-source false PASS and repaired AC-32.spoof FAIL; normal read-only data and ordinary script controls are retained. F2/F3 preserve the original Claude round2 classification and S24V2 reproduction. F11/F12 and F13–F17 preserve the D002/D006 review and CI failures without replacing them with success-only history.

Independent verifier/runtime trust, authenticated receipt selection, dynamic/external/descendant coverage, GIE/governance and actual future merge-result acceptance remain separate obligations. They are not new audit findings or implied closure.

No implementation repair is queued. Fresh regression proof, if requested by root, must reuse only the mapped existing tests and normal controls on the exact candidate. Any source correction requires the root bounded claim and the same-failure three-attempt cap.

Exact paths, Git blobs, SHA256 hashes, recorded reproduction references and existing test function/line mappings are in INVENTORY.json and EVIDENCE_MANIFEST.json. No tests, scripts or CI reruns were executed during this intake.
