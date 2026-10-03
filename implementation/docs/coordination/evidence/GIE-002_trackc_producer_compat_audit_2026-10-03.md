# GIE-002 · Track C 2137883 ↔ producer pins: compatibility audit · 2026-10-03

Requested by the user (CDR-002). The question: is there a **result-invariant** compatibility layout that keeps both of these satisfied **unmodified**, so that no merge order has to be chosen?

- every Track C C0–C7 Frozen blob and acceptance pin;
- every producer byte and fingerprint pin.

| Field | Value |
|---|---|
| Method | Workflow `wf_56296124-2cc` with 7 agents: Track C inventory, producer inventory, constraint solver, trial A, trial B and an adversarial skeptic, plus the C8 analysis in GIE-004 |
| Refs | canonical `b8e39a2`; Track C PR #4 `ff78c4f`, tip `97d1b94`; producer tips as in GIE-001 |
| Scope | Read-only on remotes. All trials ran in throwaway local worktrees, which were removed afterwards. Trial commits were never pushed. Nothing is CI_VERIFIED. No CAL_VERIFY or Holdout access |
| Raw results | `GIE-002_trackc_producer_compat_audit_2026-10-03.json` (inventories, constraints, candidates, trials, skeptic) |
| Reference patches (NOT applied anywhere) | `GIE-002_patches/solver_optionA1_producer_repin.patch`, `…A2_producer_repin_strip.patch`, `…B_trackc_sidecar.patch` |

## 1. Verdict

**IMPOSSIBLE_WITHOUT_ONE_SIDE_CHANGE.** The adversarial skeptic attacked this independently and did **not** refute it (`refuted=false`, confidence high). It re-derived every pin at the exact refs and recomputed the key fingerprints itself.

The difference between the two minimal options is **schema ownership, not values**. Both options were built and measured:

- numbers, decisions, lineage values and the C4 run_fold hashes are identical;
- only the serialized shape and which side changes its frozen or protected content differ.

## 2. The four changes against the user's six questions

Blob identities are the same at 2137883, `ff78c4f`, `97d1b94`, C6 START `88da6f3`, C7 START `88f66c5` and C8 BASE `86e345e`.

| | `contracts/lineage.py` (new, 288caba) | `contracts/models.py` (ef4f80e; canonical 2367d2e) | `technical/engine.py` (5365653; canonical 0f6c274) | `macro/engine.py` (08d79c2; canonical f7b9979) |
|---|---|---|---|---|
| Why Track C needs it | Fail-closed PIT/provenance primitive. `StampedValue.validate` rejects naive, future, estimated, synthetic-for-real and missing-provenance inputs. `derived_lineage` sets available_at = max of the stamp available_at values (never `as_of`), plus sorted refs/vintages and an input_hash. Also used by frozen C6 `evl/execution.py`, where its layout is part of the C6 execution input_hash | Four optional fields (`available_at`, `data_stamp_refs`, `source_vintages`, `input_hash`) on TechnicalSnapshot and MacroSnapshot, so that `replace(output, **lineage)` works. **No Track C source module reads them.** Only frozen test assertions read them (`test_evl_c4_bindings.py` L43-46, L86, L111-114) | `TechnicalEngine.evaluate_stamped`: chronological, unique stamped returns; derives lineage; then calls the byte-unchanged legacy `evaluate()`. Called by frozen `evl/bindings.py:69-70` and frozen test L41, L67 | `MacroEngine.evaluate_stamped`: exactly {growth, inflation}, no defaulting. Called by frozen `evl/bindings.py:71` and frozen test L51, L54 |
| Must it be in the core snapshot schema? | No (standalone module) | **Not for any Track C result.** Required only by frozen test assertions and Track C pins | Not a schema item. It sits on the engine class only because frozen code calls it there | Same as technical. No frozen test asserts MacroSnapshot lineage fields |
| Movable to adapter / wrapper / sidecar? | Already standalone. It stays in place in every option, because moving it would break frozen `evl/execution.py` and 2 frozen tests | **Yes**, as a sidecar `Lineage` object returned next to the unmodified snapshot (prototype `evl/stamped.py`; `evaluate_bound` exposes `result['lineage']`) | **Yes**, as a free function in `evl/stamped.py` with the same checks and messages | **Yes**, same |
| Solvable without changing C0–C7 Frozen blobs? | **Yes** (byte-unchanged in all options) | **No**. Frozen test L113-114 needs `available_at`/`input_hash` keys in legacy `to_dict()`, and `to_dict = _to_json(asdict(self))` | **No**. Frozen `bindings.py` needs the method on the class. Canonical bytes have no `evaluate_stamped`. Every module in the import closure is frozen, pinned or protected | **No**, same argument |
| Solvable without changing producer byte pins? | **Yes** (no producer pin references it) | Only if models.py returns to canonical (option B). Otherwise the asdict fingerprints in #11 and #17 fail, and so does the CI-mode `models.py` compare in #10/#14 | Only by relocating it (option B). Otherwise the byte pins in #11, #15, #18, #12, #14 and #17 fail | Only by relocating it (option B). Otherwise the pins in #11, #12, #14 and #17 fail |
| Serialized numerical values and semantic outputs identical? | Yes (byte-identical; lineage values identical in both layouts) | **Values yes. Shape differs.** Stripping exactly the 4 lineage keys when null/empty reproduces every pin (28e910f3, 82165414, 7bbfad69). A generic "drop None" normalizer does **not**, because it also drops the pre-existing `qgv_snapshot_id_ref` | Yes. The legacy `evaluate()` body is identical, and the stamped output is the legacy decision plus lineage | Yes |

## 3. Proof sketch (full proof in the JSON, `solver.proof`)

1. **Same path, two contents.** The producer pins fix sha256(`technical/engine.py`) = `f7268f52…` and sha256(`macro/engine.py`) = `c593a2ef…`, i.e. the canonical bytes. Track C's acceptance tool (C6 L57-59, and C7/C8 preservation) fixes the same paths to `86607bf7…` and `a0a7c983…`. One path in one tree has one content, so no layout satisfies both.
2. **No outside injection point.** Frozen `evl/bindings.py` calls `.evaluate_stamped` on classes imported from the engine modules. All 17–18 modules in the import closure of `evl.bindings` are Track C-frozen, producer-pinned, or protected by Track C's boundary checks. Hooks (conftest, sitecustomize/.pth, `__path__` overlay) need a new or changed file that the same checks forbid.
   - The only layout that passed both test suites was a runtime monkeypatch from `technical/__init__.py` / `macro/__init__.py`. It is **rejected** for three reasons:
     - it still fails Track C C6 L41-43 and L57-62, C7 and C8;
     - it changes the core snapshots at runtime;
     - it makes class behaviour depend on import order (measured).
3. **Independent schema contradiction.** The frozen test needs legacy `to_dict()` to contain `available_at`/`input_hash`. The producer fingerprints hash `asdict()` of the same legacy objects, and those pins were computed without the keys. Both serializations come from the same dataclass in the same pinned file.
4. **Merge order cannot help.** It changes no path's content.

## 4. The two minimal options (both measured result-invariant)

| | **Option A: lineage stays in the core schema** (Track C untouched; producers re-pin) | **Option B: lineage becomes a Track C sidecar** (core schema and engines canonical; producers untouched) |
|---|---|---|
| Changes | 9 byte constants across 6 producer test files: #11 L36-37, #15 L291, #18 L27, #12 L37/39, #14 L37-38, #17 L385. Plus the 3 fingerprint constants (#11 L34, #17 L39/43), either re-pinned (**A1**) or kept by a targeted 4-key strip in the #11 test and the #9 fingerprint tool (**A2**; A2 makes the fingerprints blind to this shape change). Plus the CI-mode `models.py` compare in #10/#14 and their compat evidence, and the #17 invariance evidence and #7 numeric_fingerprint evidence, which would need an additive re-record | Track C changes 2 **C4-frozen** blobs: `evl/bindings.py` (5+/6−) and `tests/test_evl_c4_bindings.py` (12+/11−). It restores `models.py` and the two engines to canonical, adds `evl/stamped.py`, and keeps `lineage.py`. The Track C acceptance tools must record the change, and the C4 SOFTWARE_FROZEN identity must be re-accepted (C4–C8 re-verification) |
| Measured | Full combined suite 1133 passed / 3 failed (IF-2 only). All Track C content checks PASS (0 Track C paths changed). CI-mode #10/#14 compat: 2 FAIL unless also changed | Full combined suite 1133 passed / 3 failed (IF-2 only). All 7 IF-1 guards PASS. Engine fingerprints equal every pin. CI-mode #10/#14 compat: PASS. Track C-only tip+B: C4/C6/C7/C8 tests 443 passed |
| Result impact | Values and decisions identical. **Every** Technical/Macro snapshot serialization gains 4 keys (null/empty on the legacy path). #12's real MacroSnapshot would carry null core lineage while its PIT provenance stays in `environment['pit']`: two representations until #12 adopts the stamped path | Values, decisions and lineage identical. Probe digests are identical old vs new: semantic 771e0ab9, lineage fd76022d, core 6f546546; C4 run_fold model 67a61ba5, prediction 55032e05. 37 fail-closed cases give identical exceptions. `evaluate_bound` gains a `lineage` key. Legacy "unknown qualification" becomes key **absence** instead of `None` |
| Whose contract changes | Technical/Macro core schema and producer guards. Technical and Macro owners would be accepting a Track C-authored core change | A Track C SOFTWARE_FROZEN phase (C4) |
| Executor | 6 producer branch owners (several have no recorded Claude session owner) | The Track C owner session (active) |

## 5. Ownership facts the decision should weigh

- **Canonical C-28** ("Technical output has no available_at", Contract Conflict Register L348-353) prescribes the core shape and names the Technical owner: *"Fix belongs to the Technical system (upstream PATCH: add available_at from input data stamps)"*. Track C's models.py and engine change is that patch's shape, but it was authored by Track C. **No register item covers the MacroSnapshot lineage fields** (C-30 is unrelated).
- **The authorization for the "four authorized C4 repairs" is self-recorded.** `track_c_c4_acceptance.md` L19 says: "The user's 2026-09-29 continuation authorized repair of the former upstream blocker." There is no verbatim user quote, timestamp or D3-P id. Compare TC-D3P-002, recorded with the user's words "어 진행해" at 2026-09-29 19:19:50 KST. One day earlier, Track C's handoff stated "EVL_SPEC_v0.1 §13 requires reporting these existing contract gaps, not redefining upstream modules." No Technical or Macro owner acceptance exists.
- Frozen `evl/bindings.py` docstring: "This adapter never … modifies legacy engines". Yet it depends on methods that the same commit added to the legacy engines.

## 6. Integration items required under BOTH options (not a reason to prefer either)

- The Track C acceptance tools (C6/C7/C8) raise in **any** integrated tree. Two checks are branch-isolation checks: "new file outside authorized Track C" (204 producer files, including `.github/workflows/*`) and "canonical advanced". The owner must rebaseline them at integration time.
- #14 CI step `git diff --exit-code` over `technical/`, `macro/`, `contracts/` fails in any integrated tree, because of the producers' own new files.
- The 3 IF-2 sentinels (#10, #14, #13) fail in every integrated tree.

## 7. NOT_RUN

- GitHub Actions on any tree.
- The `__main__` full_acceptance of the C6/C7/C8 tools on integrated trees (boundary/preservation raise first; content checks were run per condition).
- The A1 full combined suite. It was run once in trial A and passed (1133/3). The solver's own A1 run was targeted only.
- Option B-ii (subclass variant).
- Regeneration of real-data evidence, and of the C5–C8 evidence-family hashes, under option B.
