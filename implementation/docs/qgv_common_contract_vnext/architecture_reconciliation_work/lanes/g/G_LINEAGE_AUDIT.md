# G Input / Method Lineage Audit — inactive evidence continuation

**D1/D2 COMPLETE · SOURCE-PINNED · NO PRODUCTION MIGRATION · MANUAL EXECUTION.**

Source snapshot inspected: `4fb08a05728d83519b72a2bd995669f0cb06003a`. Parent freshly read the owner/review branches before delegation and subsequently reconfirmed authoritative Global `b3532a2ebbe95310bbf222937466eb04a0211263`; local cached Global `5e33b30` is stale and is not used as a newer authority. This lane does not claim ownership of PR #44 or the active owner lease, and writes only additive output files outside that tree. B4/B7 user-approved identity/boundary principles apply; production methods, roles, admission and migration remain unapproved. Previous 20 G/profile characterization checks and 42 reconciliation cases are reused, not rerun. Current method identity/version fields are audit source anchors, **not a new approved method registry**.

## Evidence delivered

`G_METHOD_REPLAY_MANIFEST.json` covers all six existing G factor identities. Each records input contract, exact method expression, observed branch ID, source hash, input period, source producer/concept/unit candidates, fallback, normalization, PIT fields and result-lineage limitations. `method_id`/`method_version` remain null because production has no factor method registry. Audit-only source identity is explicitly separate from factor identity.

`G_LINEAGE_REPLAY.json` contains six complete/missing/fallback synthetic input cases; all factor values, intermediate economic inputs, periods/units, stamp/as_of, branch source and result hashes are preserved. The existing committed SEC mini fixture is independently source-replayed with selected FactVintage rows. A persisted legacy synthetic snapshot is attached by exact payload hash without assigning it a guessed historical method. Actual real-data replay is **NOT_RUN_SOURCE_BLOB_ABSENT**.

`G_LINEAGE_VERIFICATION.json`: **47/47** bounded new lineage checks PASS. Reproduction in a second output directory is byte-identical for all four JSON outputs. No existing audit or production file was changed; source hashes are checked before/after. No full-suite/Actions/real PIT/OOS/Holdout/production migration or scheduler execution was run.

## Six-factor lineage

All source references below are relative to `implementation/src/investment_system/` at the pinned HEAD.

| Factor | Executed quantity and branch | Actual input period/meaning | Normalization | Evidence status |
|---|---|---|---|---|
| `next_3_5y_growth` | Same current/prior revenue ratio-minus-one as `revenue_growth` | Prior selected annual vintage; no forecast/3–5Y inputs | Current provisional `_growth_to_score` linear clip | **INTERIM_PROXY**; new target/method authority unresolved |
| `growth_efficiency` | Revenue ratio-minus-one divided by current invested-capital/revenue with existing floor | Flow comparison and selected balance proxy; exact matched fiscal basis not enforced | Current existing clip/multiplier | **MORE_EVIDENCE_REQUIRED** for accounting/period/economic authority |
| `revenue_growth` | Current revenue / prior selected revenue − 1 | Selected preceding vintage is not automatically an adjacent fiscal-year pair | Current provisional `_growth_to_score` | Existing concept SUPPORTED; actual paired-period/normalization authority unresolved |
| `eps_fcf_per_share_growth` | EPS ratio-minus-one if computable; otherwise current FCF / prior revenue − 1 | Primary per-share EPS series; fallback compares different measures and periods and uses no share series | Same provisional growth clip across two economically distinct branches | **METHOD_MISMATCH** for fallback; intended alternative remains unresolved |
| `growth_durability` | Supplied rubric score passed through | Rubric version/scorer/evidence horizon not represented by raw mapper | Direct score, with no independent raw metric | Existing concept SUPPORTED; rubric authority/completeness unresolved |
| `excess_growth_vs_industry` | Company revenue ratio-minus-one minus supplied industry growth | Industry universe, fiscal period, weighting and source vintage are unspecified | Existing spread clip | **MORE_EVIDENCE_REQUIRED** |

Source mapping: `raw_map.py:37–47,92–93,123–144`; identities/weights `factors.py:23–30`; raw shape `contracts/raw.py:13–57`; shared observation `contracts/models.py:74–81`.

### G 3–5Y: exact separation

| Requested dimension | Source-pinned finding |
|---|---|
| Factor intent | Preserved factor ID encodes 3–5Y, but the original detailed semantic/rubric authority is not recovered in this checkout. Intent is not inferred solely from ID or notes. |
| Method actually used | `raw_map.py:139` maps `revenue_yoy` and explicitly marks it “proxy: last yoy; not a 3-5y forecast”. |
| Input horizon | `_yoy(revenue,revenue_prev)`; SEC producer selects current/prior vintages, not 3–5Y observations. |
| Available historical data | SEC source can resolve dated annual/quarterly facts; current raw shape only passes current/prior revenues. Quarterly monitor has an independent raw-evidence path. Real raw blobs are absent here. |
| Future/forecast data | No future forecast field is consumed by this factor. A requested 3Y/5Y metadata label provides no forecast vintage. |
| Fallback | No separate 3–5Y branch; the YoY proxy is always the scored branch when revenue pair exists. |
| Display/coverage | `pipeline.py:25,27,36–42` calls `map_raw(raw)` without horizon, then emits requested/effective quarters and `mutates_g_score=False`. `g_horizon.py:14–23,42–45,74–90` supplies display/coverage meanings only. |

**Verdict: INTERIM_PROXY.** This is the exact executed/source-disclosed method, not an accepted implementation of forward or historical structural 3–5Y growth. Replacing it or endorsing its economic intent is D3. The factor overlaps revenue-growth evidence; distinct factor IDs do not establish independent economic inputs.

Historical evidence agrees: `Investment-System1 · HANDOFF_HISTORY.md:226–237` and `implementation/CHANGELOG.md:132–145` record GHorizon/quarterly monitor as metadata/evidence-only without changing G. Accessible expression history enters in imported baseline commit `6793fc55c4c4dd8c689559a8e039c1e7f2ffc1aa`; the original fine-grained introduction commits are unavailable. This limits any historical method-attribution claim.

### EPS → FCF: exact economic meaning

`raw_map.py:93,142` selects EPS YoY whenever `_yoy(eps,eps_prev)` is computable. Missing current/prior EPS **or zero prior EPS** selects `_yoy(fcf,revenue_prev)`. The latter is `current FCF / previous revenue − 1`, followed by the same growth score transformation.

This is a cross-measure, cross-period cash-flow/revenue ratio minus one. It is **not** current FCF / previous FCF growth or FCF/share growth. Although the ratio before subtracting one resembles a cash-flow/revenue measure, no authority was found to label this branch an accepted margin-like measure, EPS substitute or interim FCF growth proxy. Arithmetic being finite cannot supply that economic authority.

`sec_companyfacts.py:218–238` computes current/prior direct FreeCashFlow when available; `fcf_prev` is dropped during RawFundamentals construction (`:274–291`). Current FCF can instead be current CFO − abs(CAPEX), with separately selected source concepts. `contracts/raw.py:20,25–28` has current FCF/shares and EPS pair, but no prior FCF, prior shares or paired FCF/share contract. Current shares never enter this G fallback.

**Verdict: METHOD_MISMATCH.** The existing fallback is preserved as legacy literal behavior and bound to a separate observed method anchor. The actual replacement and financial-sector applicability remain **MORE_EVIDENCE_REQUIRED**, not guessed.

## New period, source and PIT readiness evidence

1. `sec_vintage.py:107–125`: “previous” means another `(fy,fp,end)` group. It neither requires a distinct end nor one-year separation/continuous history. A reclassified filing can form another group without proving a prior-year comparator. `:53–65` annual-duration filtering permits absent start/end and uses an existing minimum-duration rule; that rule is not certified economic period alignment.
2. `sec_companyfacts.py:132–175`: concept, unit, period and accession are present in transient FactVintage values but discarded by RawFundamentals. The adapter exports one DataStamp with maximum used filing date and CIK source, not per-field concept/period/accession closure (`:249–270`). EPS/current-revenue/FCF/equity/debt may select different latest reporting periods.
3. Date-only SEC `filed` values are coerced to midnight UTC (`sec_vintage.py:38–44`). Some fallback selection permits `end` if `filed` is absent. This replay retains original precision and flags missing form/start/fy/fp/accession in the existing mini fixture. No timestamp is upgraded to exact intraday availability.
4. Direct `pipeline.analyze_raw` does not call the provider admission guard. A DataStamp or numeric score alone is insufficient evidence of admitted PIT. Provider-path and direct raw-entry preconditions must be distinguished in the future B3 contract.
5. `industry_revenue_growth` and `growth_durability_rubric` have no source producer in the SEC adapter. A synthetic filled value does not establish source/version/rubric authority.
6. Raw observations set `raw_value=score`, so the pre-normalization input cannot be recovered by treating that field as the raw economic metric. The new replay sidecar stores true input/intermediate fields independently.

These are new lineage/evidence limitations, not proposals for a new interval threshold, valuation/growth formula or PIT relaxation.

## Source replay results and consumer consequence

All figures below come from unchanged current production functions on explicitly synthetic fixture inputs. They are not recommendations, policy calibration or expected real performance.

| Synthetic source case | G scalar | Current G coverage | Active EPS/FCF branch |
|---|---:|---|---|
| Complete | 76.29333333333334 | READY | EPS current/prior |
| Missing EPS | 65.79333333333334 | READY | FCF/current versus prior revenue |
| Zero previous EPS | 65.79333333333334 | READY | FCF/current versus prior revenue |
| Missing EPS and FCF | 65.79333333333334 | PARTIAL | Fallback unresolved/missing |
| Missing industry and rubric | 57.46 | PARTIAL | EPS current/prior |
| Missing revenue base | 21.0 | PARTIAL | EPS current/prior |

The current fallback score zero and the missing fallback case produce the **same numeric aggregate** but different coverage. READY also exists for a computed cross-measure branch without registered method identity. Therefore completeness of current arithmetic, semantic validity and consumer eligibility remain separate. No score threshold can reliably reconstruct those missing facts from the scalar.

`analysis.py:71–80,92–123` creates a new random snapshot ID and keeps scalar scores plus coverage/notes, without complete G factor/method/input lineage. `leaderboard.py:30–54` ranks scalar totals, with coverage displayed as freshness rather than used for admission; it cannot verify selected method identity or economic validity. This lane adds producer-method/input-lineage assessment evidence to B2/B3/B5/B6; it does not duplicate scoring in Leaderboard or activate a production repair.

## Historical identity protection and migration blockers

`G_LINEAGE_REPLAY.json` binds a persisted snapshot from `official_v11_book_snapshots.json` by full file SHA256, snapshot ID, canonical snapshot payload hash and existing version fields. The file itself says `kind=SYNTHETIC`, `synthetic_all=true`; **its filename does not make it real Official financial evidence**. No old score was recalculated. Its method identity remains unresolved rather than retroactively assigning today's mapper to an old result.

Existing structures can represent separate immutable method/input/result references in an **inactive sidecar** (`qgv_common_contract_vnext/CONTRACT.md:43–61,155–157,174–187`, schema generic `id/version/sha256/locator` refs). Separate approved future result IDs can point to the archived result and its exact payload hash; the current optional `revision_parent_id` can provide snapshot-level ancestry. This preserves original factor identity while separating method/version lineage. The synthetic EPS primary/fallback cases demonstrate different observed methods under the same factor without replacing production.

Runtime limitations remain:

- FactorObservation and QGVSnapshot have no first-class factor method/version/input-contract lineage (`contracts/models.py:74–81,94–122`); revisions do not solve per-factor executable identity.
- `validation/historical.py:203–214` stores prediction scalars and snapshot refs, not G selected input/method closure.
- `qgv/track_record.py:19–59` rejects overwrite via its API and creates outcome child records; `validation/file_store.py:19–48,56–67` persists/reloads those records. These paths preserve payloads through their API but cannot reconstruct an omitted method. This audit does not assert a new deep-immutability guarantee for all in-memory objects.
- `universe/events.py:65–81` stores latest snapshots keyed by company and replaces that slot on updates; it is not a factor-method archive.
- `qgv/book.py:21–28` writes the fixed report path when asked to persist. This lane never invoked persistence, and does not treat that overwrite-capable helper as append-only historical storage.
- `ingestion/raw_store.py:47–73` retains replaced raw bytes in history; `ingestion/replay.py:28–35` normally loads the current artifact. Exact archived method/input dispatch is not implemented by those references alone.
- Real source replay here is blocked because `implementation/data/raw/blobs/companyfacts__0001045810` is absent. The manifest records hash `19ef503a5770f5660964b3c3aea6937579d9b359da344afe6a9adf59c63d26ff` and fetched time `2026-09-25T08:29:08.581610+00:00`; STORE_INDEX's historical disk-count is not current blob proof. No financial network fetch or provenance substitution was attempted.

**Migration blockers:** exact archived method/input/source closure, approved new method declarations, per-field period/unit/availability binding and runtime version dispatch. Sidecar expressibility is demonstrated; production migration compatibility is not declared PASS.

## B1 authority and minimal decision dependencies

B1 remains **MORE_EVIDENCE_REQUIRED**. Existing G concept classifications are preserved: revenue growth and durability **SUPPORTED**, efficiency and excess growth **PROPOSED**, 3–5Y and EPS/FCF **UNRESOLVED**. New SUPPORTED promotions: **0**. Production REQUIRED/OPTIONAL/CONDITIONAL assignments: **0**. Source-characterized inputs do not settle requiredness, especially for mismatched methods.

Bounded authority search read pinned root specifications, scoped approvals/evidence and method-expression history. Cached Global routing/decision text was read for context only; parent's fresh remote Global governs final authority. Scoped `implementation_contract/approval.json:43–59` and `DECISION_REGISTER.md:60–66` exclude actual G/FCF replacement and migration. No chosen replacement authority was recovered in those pinned sources. Broad Global CDR-015 delegation does not override this request's narrower explicit exclusion. A-G1/A-G2 in the inspected routing text are **Chart routing** requests, not evidence of G semantic adoption.

The minimal next semantic bundle has two separate clauses:

- **G1 — horizon semantics:** decide the intended economic target for 3–5Y (forward forecast, historical structural horizon, or explicitly retained legacy proxy). Existing scores stay archived. Forecast alternatives need archived publication/vintage/target period; structural alternatives need paired history and an approved calculation. No new formula or numeric defaults are proposed in this lane.
- **G2 — EPS/FCF fallback semantics:** decide whether and under what economic/input authority another measure may substitute for EPS growth. Current FCF/prior-revenue branch is not recommended as valid growth. FCF/share alternatives need paired FCF/share periods, units, dilution/corporate actions and sector scope; none is selected.

Both depend on B4/B7 identity isolation and on the still-unapproved B2/B3/B5/B6 admission contract for evidence/applicability/completeness/consumer safeguards. They provide inputs to B1 rather than requiring B1 to prematurely assign roles. V/composite/weights are not adopted here. Historical replay/source-only work can proceed independently of these D3 clauses.

## Finite next executable D1/D2 task

Create one inactive **G source-readiness dependency matrix** for G1/G2 from the manifests already produced: enumerate the exact absent forecast/historical input contracts and paired EPS/FCF/share evidence; compare only repository-grounded method families, leaving unrepresented method equations and missing vintages unresolved. Bind every cell to this replay output hash and identify source owner/data artifact needed. The task completes when each dependency has evidence or an explicit unresolved owner/request, with no requiredness, formula, numeric policy, activation or new broad audit.

Current manual work adds **0 scheduler hops**. Existing autonomous HOP1/HOP2 remains **0/2 / UNVERIFIED** unless separate scheduler execution receipts actually prove otherwise. These files are not substituted for the preplanned 20-factor scheduler canary.

## Reproduction and hashes

```bash
PYTHONDONTWRITEBYTECODE=1 python g_lineage_replay.py --owner-root /workspace/scratch/5f9c0923784f/qgv-policy-reconciliation-2026-10-05 --out-dir /workspace/scratch/5f9c0923784f/qgv-gv-lanes-output/g
```

| Artifact | SHA256 |
|---|---|
| G_METHOD_REPLAY_MANIFEST.json | `139757a9b5cfca3317aa009bb94e92f8af72034838ea0a88711d0b1fe505216f` |
| G_LINEAGE_REPLAY.json | `77f8300c2ebf594e640582dc213d8af1b012f7c11bf825a2c2b5f536fd2595d3` |
| G_SYNTHETIC_RAW_FIXTURES.json | `dca9e8855f7e01dc5bda9404909ae9b05f980f6604341ab5c89729140cc9f90d` |
| G_LINEAGE_VERIFICATION.json | `7207436226046b26d752ee1d96a0da91777855fe2aa2bc75834535a8d7039934` |

The verification JSON also pins source files and the script. Reproduction in `g/reproduction/` matches every byte. Parent combines lane outputs, final fresh remote baseline, consumer-safety dependency package and scoped handoff; this G lane does not write Global, automation state, leases, PR #44, historical data or production files.
