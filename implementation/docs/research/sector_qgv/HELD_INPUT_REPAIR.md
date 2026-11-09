# Held financial/REIT input repair

Owner instruction 2026-11-09. Default `sector-qgv-default/0.1.0`, strict policy,
minimum20, official Q gate and classification remain unchanged. This is
`INPUT_CONNECTION_REPAIR`, not a factor/weight change or a classification treatment.

## Existing paths reused

`sector_qgv_held.py` now sends the confirmed accounting template to the common
factor calculator and generates the missing common ROE, common equity/assets,
common BPS annual series and REIT CFO/assets improvement inputs. Unknown accounting
is retained as unknown: explicitly requested Q/G raw diagnostics may calculate,
but unclassified rows cannot enter score pools. This opt-in does not apply to V.

The existing `financial_v.py` from #499
`e1f1f35dd91ca64f3640624e0e51e0cf52bdf00f` is integrated at its original module
path. Its balance observation parser is reused, not reimplemented. The optional
history window selects the exact oldest required annual component; existing V
callers retain the original 550-day rule. Common equity requires a direct common
concept, or parent equity and explicitly zero preferred shares in the same filing.
No total-equity/NCI/preferred par fallback. Conflicting common values cannot fall
back to parent equity. TTM common income uses the existing same-concept monetary
flow parser; this is not an EPS reconstruction. BPS components without documented
class/ADR/action continuity remain ineligible in the existing common kernel.

## Reproduction and Main boundary

The existing offline CLI accepts `mode=held-input-repair` with hash-pinned
`snapshot`, `before_preview`, `repair_plan`, and unchanged default configuration:

```sh
PYTHONPATH=implementation/src python implementation/tools/sector_qgv.py \
  --job /approved/private/operating-job.json --output /approved/private/new-result
PYTHONPATH=implementation/src python -m pytest \
  implementation/tests/test_sector_qgv_held_financial.py \
  implementation/tests/test_sector_qgv.py \
  implementation/tests/research/test_expanded_held_classification.py \
  implementation/tests/test_sector_qgv_v.py -q
```

The plan supplies exact archive/member/source hashes and original record context;
the original observation must reference that exact companyfacts hash. No search
or HTTP occurs. An immutable prior repair can be reused only with matching source
code hash, evaluation time, record and accounting context. Output refuses overwrite.
`held-sec-sector-adapter/2` changes the generated-input identity; original settings,
source acquisitions, classification hashes, official gate and old results survive.

Outputs include the usual snapshot, preview, saved configuration and manifest,
plus `sector-qgv-held-repair-audit/1` and
`sector-qgv-input-repair-comparison/1`. The latter reports raw/score transitions
for all rows and selected-default rows separately, Q/G/V/joint/total gains and
losses, common-valid score changes and peer counts. Causes can overlap. A
`VALUE_EXCLUDED` gate is V-weight exclusion, not issuer removal. Missing evidence
is never 0, a pass, or proof that the document lacks the fact.

Main can reuse #523 calculation_counts and #524 detail/shard contracts for the new
results. The optional comparison requires the distinct treatment label
“입력 연결 수정”; it must not be displayed as element/weight or classification changes.
Frontend/auth/Worker/CI-list changes remain Main-owned. No deployment is claimed.

## Held-real delta

Frozen evaluation 2026-11-04, original504 code rows / 501 issuers and original
8004-issuer comparison catalog, with the held1057 cohort projected afterward.
The 44 financial +23 REIT operating rows are reviewed targets, not an assumed
67 recoveries. Additional financial-profile rows retain unknown accounting.

The REIT bridge restores23 selected raw values,23 factor scores and23 G axes.
Operating G320→343; held1057 G670→693; catalog8004 G671→694. Q remains232/494/495,
respectively; V, joint and total remain0. No existing common-valid Q/G score
changes or axis losses. Financial selected common-equity/assets raw values become
3 operating /11 catalog; common ROE0 operating /2 catalog. No corresponding
financial factor scores yet. BPS growth remains ineligible. Raw diagnostics on
unclassified rows are reported separately from selected-factor coverage.

The 95% target remains unmet: valid joint+final total0/501 operating issuers and
0/1057 held issuers. Whole-market denominator and coverage remain null. The8004
catalog is not an eligible whole-market roster. Some groups have fewer than20
members before any input collection; others have enough members but too few valid
common-capital observations. Prices alone cannot repair those Q/G constraints.

## Source reading, not a book-derived optimization claim

Direct Drive EPUB: [What Works on Wall Street, Fourth Edition](https://drive.google.com/file/d/1ZmzhcJONp4Wi2UDiMVLg5deBt7fiozaC/view),
modified2026-11-02T10:35:50.487Z,35046571 bytes,
SHA256 `019de18190d4e5e12c10871fbd7db8efac8f5ba5c8eacf812d43a9c4867e9921`.
Opened EPUB contents and relevant passages in `ops/ch14.html` (accounting ratios),
`ops/ch19.html` (ROE definition/results), `ops/ch24.html` (sector methodology and
2009 sector definitions). Chapter24 uses quintiles and equal-weight sector
benchmarks for its historical experiment. This does not establish our minimum20,
strict missingness, default Q/G/V weights, 95% target, or current universe policy.
Chapter19's income-before-extraordinary-items/common-equity ROE description is
not identical to the approved TTM common-income/average-common-equity variant.
Chapter14's reported findings do not make our balance-sheet capacity role an
empirically optimized alpha weight. Approved system policy is preserved.

Directly read Drive copies:
[Nov7 #503/#505/#509 contracts](https://docs.google.com/document/d/1yMnP49BjAwZApnlcD8BoE9LaG_sCqhYrIrRDZ6hoxg8/edit)
(modified06:09:13.531Z, #505 e3df0c1e; V_RESUME and CONTRACT sections),
[Nov7 #510 contracts](https://docs.google.com/document/d/1YguAuXKCNiLOkVkZb3W2FcpJAf1GfSRsn-CI581n0lE/edit)
(modified06:09:05.765Z; Main/partial comparison sections), and
[Nov2 95% planning note](https://docs.google.com/document/d/1UxICmVrVKHp7gGq-U6It9yL1ONNCnij7LvPfe8z3NLw/edit)
(modified10:34:55.540Z; B/C sections). These dated copies do not supersede newer
GitHub #520/#524 and owner decisions. Exact standalone Nov6 implementation/catalog
MD files were not located in the accessible Drive search/project folders; no
claim that their original bytes were read here. Their existing GitHub contracts,
registry and approved owner definitions remain the implementation basis.
The current name is **투자시스템 공통 10섹터**; legacy stable IDs and historical
dictionary versions are not renamed or substituted with SIC/GICS/ETF taxonomies.
