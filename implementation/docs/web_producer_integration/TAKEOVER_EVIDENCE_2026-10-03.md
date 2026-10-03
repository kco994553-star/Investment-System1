# Existing Web / Producer contract integration evidence · 2026-10-03

This is additive validation of the existing Web MVP, Language/Search, Producer
Infrastructure, P01 and Invalidation stack. It creates no publication grant,
real-data verification, canonical integration or new Web implementation.

| Checkpoint | Value |
|---|---|
| Worker branch | `codex/web-producer-integration-readiness-2026-10-03` |
| Exact source base / owner upstream | PR #19 `feature/qgv-invalidation-binding-v1` @ `c3dbf8a02c9c5ed0cf4ffb15c5532d31ae45fa3e` (READ-ONLY) |
| Canonical / merge-base | `claude/investment-system-top500-validation-alrugm` @ `b8e39a2196a6d7794a04a0cd5393c68329e126ca` |
| Base topology | 0 behind / 18 ahead of canonical before this additive checkpoint |
| Maturity before → after | `SYNTHETIC_VERIFIED → SYNTHETIC_VERIFIED`; no maturity increase claimed |
| BRANCH_STATE | Existing source preserved; new local fixture E2E PASS; new Actions `NOT_RUN` |
| INTEGRATION_STATE | Existing producer assembler → P01 withheld envelope → existing static Web fixture E2E PASS locally |
| CANONICAL_STATE | `NOT_MERGED` |
| USER_DECISION_REQUIRED for this validation | NO |

## Authority and remote sources

Operational contract: PR #21 exact SHA
`f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798`; Global routing/CDR read on
`integration/global-handoff-v1` @ `f26dc7adbfedd9209e757b5e8566c665c7bbd677`.
Scoped STATUS/CONTRACT, P01 approval, original source/tests and fresh root
Actions snapshot were read. Global files and owner branches were not edited.

| Capability | Exact owner HEAD | PR | Branch / software maturity | Canonical |
|---|---|---|---|---|
| Web MVP | `a4e49c83f5783c19617fb609b8f95b179cb13e84` | #5 | SYNTHETIC_VERIFIED; scoped presentation FREEZE_READY | NOT_MERGED |
| Language/Search | `eda65bf5d9203aee05f4d28992d1ccfcd815ebd4` | #6 | SYNTHETIC_VERIFIED | NOT_MERGED |
| Producer Infrastructure | `f8af596df4d235fee1f29bf0cb6c9a3cc0f89f36` | #9 | SYNTHETIC_VERIFIED | NOT_MERGED |
| P01 | `21039a0a7f9677b123abd8587fd8d89784a73a3c` | #17 | SYNTHETIC_VERIFIED; grants NONE | NOT_MERGED |
| Invalidation | `c3dbf8a02c9c5ed0cf4ffb15c5532d31ae45fa3e` | #19 | SYNTHETIC_VERIFIED; not a display grant | NOT_MERGED |

CURRENT: P01 policy is approved and its phase-1 implementation is present at
the exact P01/Invalidation tips. HISTORICAL: the preserved initial P01 approval
header `NOT_IMPLEMENTED` and its initial no-implementation event describe the
approval event; the appended follow-up and scoped exact source describe the
later implementation. These do not issue any grant. All grants remain NONE.

Fresh Actions observed in `/workspace/takeover-evidence/runtime/actions-by-branch.json`:
#5 run 36418935056 exact HEAD success; #9 36982361014 exact HEAD success;
#17 36994066298 exact HEAD success; #19 37003833031 and 37003833035 exact
HEAD success. #6 run 36709518222 is success on `82ae07c5f0758038abda98cd8db9e0a0f2de1ee3`;
the exact diff to `eda65bf` contains only the three scoped documentation/evidence
files. This is code-SHA success, not an exact-HEAD CI claim. No Actions were
executed by this worker for the new harness.

## Narrow change and actual validation

Only new tools and this new scoped evidence directory are added. The fixture
builder uses existing registry, assembler, P01 attachment and Web builder APIs.
Its literal research records are test vectors, never real investment data.
Record bytes stay outside the served folder. Existing source, tests, approval,
Freeze records and all original evidence remain byte-identical to the base.

The pipeline verifies that producer PASS does not grant display; QGV PARTIAL and
Leaderboard/Macro/Technical BLOCKED records remain NOT_AVAILABLE; the original
records, companies and all schema-1 sections remain invariant. Withheld score,
rank, feature and regime sentinel values never enter `data.json` or visible UI.
The original provenance, producer as_of, freshness, methodology/version and
validation metadata survive the builder and browser fetch. This validates
metadata retention in original JSON; the old unavailable cards do not render
all of that metadata, and no new metadata UI was added in this cycle.

Executed locally:

- Fixture generation and an independent second build: PASS; bundle, search
  catalog and fixture manifest byte-identical on rerun.
- New Chromium harness: six check groups PASS, zero page errors; Korean and
  English at 360/390/1280px on seven existing routes; withheld ranking rows
  absent; loading state, HTTP 503 and malformed-JSON failure, retry recovery,
  and unchanged original bundle/catalog bytes verified.
- Existing targeted Web, Language/Search, Infrastructure, P01 and Invalidation
  suites under Python **3.11.16**: **64 passed**. Raw log retained.
- New Python compilation, JavaScript syntax, diff whitespace and existing
  protected-path equality checks: PASS.
- Mobile English Home screenshot inspected: explicit NOT_AVAILABLE and awaiting
  data; no research/LIVE activation or overflow.

The first regression attempt under Python 3.12.14 had 63 PASS / 1 FAIL: the
existing P01 Portfolio fingerprint differed from its Python-3.11 pin. The
single-test diagnostic is retained as historical runtime evidence. Correct
CI-matching Python 3.11.16 resolves that failure without any source or pin edit.

Reproduce from the repository root:

```sh
python implementation/tools/build_producer_contract_web_fixture.py \
  --out /tmp/withheld-web --evidence /tmp/withheld-web-evidence
WEB_TEST_CHROMIUM_PATH=/usr/bin/chromium \
  node implementation/tools/producer_contract_web_browser_test.js \
  --dir /tmp/withheld-web --evidence /tmp/withheld-web-evidence
```

Omit `WEB_TEST_CHROMIUM_PATH` when using Playwright's installed browser. The
harness serves only the generated static folder on an ephemeral loopback port.
The managed sandbox required one `network.enabled` permission for loopback
listen; this is not hosting or external publication.

Machine-readable hashes and preservation comparison are in
`evidence/preservation.json`. Consolidated fixture and browser evidence are in
`evidence/fixture-manifest.json` and `evidence/browser-validation.json`.
The full fixture output, raw records and inspected screenshot remain local in
`/workspace/takeover-evidence/web/validation` and its sibling static folder.

## Dependency, blockers and next autonomous action

Dependency chain: canonical → #5 → #6 → #9 → #17 → #19. Existing source is
reused, not rebuilt. This cycle is complete within its validation scope.
Root integration can include this additive checkpoint and execute the harness
on the fresh combined tree/Actions without changing grants or Frozen bytes.

Real producer value display remains blocked by publication/eligibility authority
and grants NONE. Canonical merge and production deployment require a separate
user decision. Backend real-data blockers are not bypassed by this fixture PASS.
No scoring, ranking, regime, zone, portfolio action, CAL_VERIFY, Holdout, Official,
paid provider, deployment or Dynamic Workflow operation was performed.
