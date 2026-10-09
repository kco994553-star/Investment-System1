# GitHub Actions Pages cockpit

This bounded PR adds publication for intermediate review and personal use, as
explicitly authorized by user26E on2026-10-09. READ_ONLY remains unchanged.

The source is the canonical merge of PR68,
c8c2073ad5cdee3cc11d03fc2fe895b7d8d77114. The workflow runs a build on PRs,
canonical pushes and manual dispatch. Its deployment job runs only on the
canonical branch after a successful build. PRs and manual runs from other
branches cannot deploy. Only contents:read, pages:write and id-token:write
permissions are used; the build job has contents:read only.

The Pages builder accepts no holdings, demo or supplied bundle. It publishes
the existing cockpit and public19-instrument identity/TARGET metadata. The
publication projection drops only the500 public member mcap fields and one
cutoff_mcap field. Original Frozen files, the existing Web builder, TARGET,
ranking, provenance and scoring remain unchanged. No price/FX feed is added.

The generated folder has11 files. The artifact guard checks the exact reviewed
asset hashes and canonical public JSON hashes, populated sensitive/monetary
fields, recognizable secrets, unexpected files/directories and links. It fails
with categories/counts only. It rejects local/, repository material and private
exports even when renamed or inserted into a previously approved file.
The upload step points only at the web folder, with normalized tar owner fields.
A second check reads the actual immutable uploaded artifact.tar without
extracting it, immediately before actions/deploy-pages. Tar paths, duplicate
entries, nonregular files, links, metadata, padding and trailing bytes are
checked before the same11-file validation. New public source/asset changes
require a reviewed update of publication pins; this cycle does not connect quotes.

The expected URL is https://kco994553-star.github.io/Investment-System1/.
At the preparation checkpoint it returned404, has_pages wasfalse and the public
Pages API returned404. The user explicitly confirmed Source None on2026-10-09.
These probes do not replace authenticated Source metadata. Pages settings
are changed by the user. Configure-pages uses enablement:false and does not
enable Pages. The user should set Settings→Pages→Build and deployment→Source
to GitHub Actions before approving the workflow PR merge. A successful merged
workflow then publishes; manual dispatch on canonical can retry if needed.

Local browser validation serves the exact public folder under
/Investment-System1/, where root-relative paths would fail. Both390px and1280px,
ko/en routes, no overflow, nineteen empty ACTUAL rows, refresh and all resource
paths are checked. The current application has no PWA manifest or service-worker
registration, so no root PWA scope or private-data cache is introduced.
The attached screenshots use fresh empty IndexedDB, never populated holdings.
Synthetic ACTUAL flow validation runs in separate disposable browser contexts
and emits only check labels/counts, no populated screenshots or download files.

Public-address390px input/save/refresh/export/import verification awaits actual
deployment after the user's workflow-merge approval and Pages Source change.
Its status is NOT_RUN until that URL serves the deployed artifact. Local proofs
are recorded separately and are not described as deployed-address tests.

Rollback: revert PR for a code defect. A previously uploaded site may remain
online until a later approved deployment or user-operated Pages disablement.
Browser data deletion and local JSON backup remain user-device operations;
the site artifact contains no actual user holdings.

Verification:

```sh
cd implementation
python -m pytest -q
python tools/build_pages_cockpit.py --out /tmp/pages-root/Investment-System1
python tools/pages_artifact_guard.py --artifact-dir /tmp/pages-root/Investment-System1
cd ..
PAGES_COCKPIT_URL=http://127.0.0.1:8990/Investment-System1/ \
PAGES_COCKPIT_EVIDENCE_DIR=/tmp/pages-evidence \
node implementation/tools/pages_cockpit_browser_test.js
DEVICE_ACTUAL_URL=http://127.0.0.1:8990/Investment-System1/#actual \
DEVICE_ACTUAL_EVIDENCE_DIR=/tmp/device-evidence \
node implementation/tools/device_actual_browser_test.js
```

The HTTP server must serve /tmp/pages-root on8990 for these examples. Keep
browser evidence outside the uploaded web folder. Do not use --demo, --input,
or repository-root uploads for publication.
