# Device ACTUAL implementation plan

Spec: docs/superpowers/specs/2026-10-09-device-local-actual-design.md.
Base: ab295f7d4e66b5cada04a8ad93361152d4e6d665. Execute the already authorized
work continuously; independent final review runs in a fresh context.

## Task 1: Decisions and PR67 acceptance

Append the user's exact decision to Global Decision Register using an exact
parent lease and a byte-prefix proof. Freshly evaluate public deployment links,
unchanged FPIA applicability, final-head guard CI and independent technical
verification. Record any user-authorized fallback before PR merge. Merge only
PR67 when its deployment condition permits; preserve history, no force push.

## Task 2: Public identity catalog and cockpit attachment

Own product/device_actual_catalog.py, product/web_mvp.py and existing
web_assets/index.html/app.js plus tests/test_device_actual_build.py.
First test: builder emits the exact19 A-S2 refs and TARGET weights, no private
holdings fields; catalog tamper and private build input fail closed. Observe
RED, implement public catalog and optional #actual route/portfolio summary,
then GREEN and affected Web regressions. DeviceActual.mount/summary consume
{catalog,locale,quotes:[]} and do not write the shared producer bundle.

## Task 3: Device browser module

Delegate isolated ownership of device-actual.js/css and new Node/browser
tests. Meaningful RED/GREEN covers strict versioned envelope, atomic IndexedDB,
no average-cost substitution, incomplete/mixed-currency denominator,
local export/import/delete and storage failure. Root integrates reviewed
commit and runs390px ko/en flows on the actual static build.

## Task 4: Privacy guard and final review

Delegate guard/helper and tests only. RED/GREEN rejection of populated
ACTUAL payloads in tracked/index/HEAD data, including renamed/common formats;
no synthetic-label bypass. Existing source/tests and public TARGET pass.
Integrate, run full Python, Node, Web browser and repository-guard checks.
Fresh-context reviewer checks privacy, source integrity, build artifacts and
requested mobile flows independently. Publish an isolated PR; no ACTUAL
canonical merge or public deployment is authorized by this decision.

## Review focus

- Private holdings leaking into fetch/console/error/test evidence/static build.
- Import preserving bad identities/clocks or destroying a good saved snapshot.
- Price missingness/mixed currencies producing misleading total weights.
- Refresh/storage failure being reported as saved or missing without warning.
- Privacy guard exposing values or accepting populated export via rename.

## Execution ledger

- User explicitly approved device-only design and implementation in26E;
  internal spec/plan approval loops do not repeat that decision.
- Own worktree created; original candidate/source owner branches untouched.
- Parallel ownership: root static builder/hooks; module agent new JS/CSS/tests;
  privacy agent guard/tests. Interfaces documented above and shared explicitly.
