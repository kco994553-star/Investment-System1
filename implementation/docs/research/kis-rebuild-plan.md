# Offline KIS rebuild and compact delivery implementation plan

Goal: one keyless/network-free command reuses the canonical calculation kernels
to rebuild private delivery from pinned monthly retained inputs, with legacy byte
comparison and a separate compact layout. Main owns Worker/UI/workflow integration.
Spec: owner request 2026-11-16 and Main #437 comments6893685527/6893826916.
Base: 0e13bb6cf640c09763d70b03e38c2241c5707f94; #564 is merged and CI successful.

Constraints: standard-library runtime only; RAW plus confirmed splits only;
UNVERIFIED_REFERENCE and existing holds preserved; deterministic service bytes;
counts-only logs; new private output directory; no collection, merge or deployment.
The owner separately authorized only the held day1 offline rebuild/comparison.

- [x] Extract the undecorated retained contract from monthly_price_store without
  changing existing query output. Test canonical header/rows roundtrip.
- [x] Add research/kis_rebuild.py and tests/research/test_kis_rebuild.py. A pinned
  request supplies source index/store, financial snapshot, lookup, evaluation and
  fixed calculation clock. Reuse calculate_and_project/reference_files and
  official_reference. Compare hashes against a pinned delivery manifest; fail on
  missing/extra/different files. Atomic new-directory publication, explicit exit
  codes, deterministic output and standard-library/no-network tests.
- [x] Add research/kis_compact.py and tests/research/test_kis_compact.py. Share
  repeated latest metadata, preserve latest values/states, separate QGV raw detail
  from the view, and emit immutable RAW chart periods plus current daily rows.
  Test decoding, ties/nulls/holds, stable old chunks, corrections, limits and the
  changed-file byte budget. Do not relabel derived hashes as original source hashes.
- [x] Compare layouts using measured day1 projection and clearly labelled
  synthetic five-year capacity/runtime tests. Count Git-retained changed payloads,
  periodic sealing copies, metadata and bootstrap separately; no assumed4x ratio.
  Distinguish data-view growth from raw-source and other-feature repository growth.
- [ ] Run only changed-boundary checks, preserve private results and timings,
  open one Draft PR on canonical, and hand Main the command, fields/paths, limits,
  failure policy and exact code/input/result pins. Consumer/browser/deploy remain
  separate. No force push or history erasure.

Review focus: wrong snapshot/clock; source pointer drift; a failed run replacing a
good batch; omitted/extra series hidden by subset comparison; immutable chart
corrections/split rebasing; byte-budget claims that ignore old Git blobs.
