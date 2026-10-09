# v1.1 Identity and Integration Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Identify the 19 TARGET securities and publish an independently verified integration PR without merging canonical.

**Architecture:** Start at canonical c109c81. Preserve immutable source histories and include only the dependency closure required by PR63/64/65/66. Keep new identity evidence separate from Frozen input data and distinguish issuer, security and listing bindings.

**Tech Stack:** Git, GitHub Git Data API, Python/pytest, Node/Chromium, existing CI and FPIA.

**Spec:** User's 2026-10-08 next-cycle directive, recorded in the candidate cycle receipt; repository authority v1.1 section 26E.

## Global Constraints

- READ_ONLY mode remains byte-identical; the user's named observed-session work is authorized.
- No canonical merge, new investment calculation, Holdout consumption, automation expansion or operational data-refresh work.
- US issuer evidence comes from Frozen Track A and C-39; Alphabet is GOOGL Class A; TSE8035/KRX042700 are user-sourced listing identities.
- No invented identifiers; unresolved rows list missing fields and acquisition sources.
- Final candidate tests and separate fresh-context verification run anew.
- Ask for canonical merge approval only after a concrete verified candidate exists.

## Review Focus

- Issuer CIK incorrectly promoted to share-class or listing identity.
- Ticker ambiguity, specifically GOOGL versus GOOG.
- TARGET used as ACTUAL when actual holdings are missing.
- Hidden dependency/tool-source differences mistaken for Frozen equality.
- Green prior-branch tests mistaken for final-candidate acceptance.

### Task 1: Identity evidence and gate reassessment

- [ ] Reconstruct 19 input rows from immutable TARGET and verify source hashes.
- [ ] Map allowed existing identities; validate independently of row assertions and preserve source coordinates.
- [ ] Record row-level unresolved fields/sources and reassess A-S2/A-S3/A-G1–3.

### Task 2: Dependency-safe candidate

- [ ] Audit source graph, required files and workflow provenance before selecting merges.
- [ ] Assemble from canonical in an isolated clone/new branch; document each conflict resolution.
- [ ] Preserve Frozen/history/Holdout and mode; classify F1–F25 as candidate blockers, repaired or LATER.
- [ ] Run baseline and final affected/full checks, browser tests and exact-candidate FPIA as applicable.

### Task 3: Publish and independently verify

- [ ] Publish exact local tree through GitHub API and open PR against canonical.
- [ ] Obtain repository-guard/existing CI outcomes on candidate/PR merge result.
- [ ] Dispatch fresh-context verifier with only user requirements and exact candidate; rerun tests, inspect findings, fix relevant defects and rerun affected checks.

### Task 4: Decisions and final report

- [ ] Publish honest mapping/gate/CI/FPIA receipts without changing global owner state.
- [ ] Request ACTUAL choice via 26E; implementation waits for that decision.
- [ ] Request canonical merge via 26E after verification, with candidate identity and rollback.

## Execution ledger

- Fresh isolated clone created; candidate branch starts at c109c81. Independent mapping and dependency audits use separate worktrees.
- Ruling: proceed under the user's explicit named execution directive while preserving READ_ONLY; no mode override or autonomous writer claim.
- Ruling: the user already specified execution and independent review, so plan approval is not an extra prerequisite.
