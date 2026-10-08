# P03 — Raw artifact long-term storage: detailed comparison and recommended architecture

Status: **ANALYSIS / NOT APPROVED**. Nothing was uploaded, paid for, created, moved or deleted. The only action taken was a
**read-only** restore check on a GitHub runner (§2).
Recorded 2026-10-01 UTC. Prices and limits come from public sources found on 2026-10-01 (§7). `docs.github.com` was not
reachable from the audit container, so GitHub figures come from search snippets of the official docs. **Re-check them before acting.**

## 1. Facts this comparison is based on

| Fact | Value | Evidence |
|---|---|---|
| Repository visibility | **public** (`private: false`) | GitHub API, 2026-10-01 |
| Dataset | 6,808 artifacts, 6,136,954,924 bytes uncompressed; zip archive 451,439,890 bytes | `reports/raw_persistence/raw_dataset_manifest_2026-10-01.json` |
| Only complete verified copy | Actions artifact `10927496280` (`c21-raw-store-36305927245`), digest `712e43bc…f94`, **expires 2026-12-26T08:21:15Z** (re-confirmed via API 2026-10-01, `expired:false`) | API listing; restore check §2 |
| Other copies | Seed artifact `10855214590` (partial, expires 2026-12-24); actions/cache (evictable); git: manifests only, 0 blobs | `storage_locations_2026-10-01.json` |
| Retention verdict | `AT_RISK_ONLY_EXPIRING_COPIES`, `loss_deadline_if_no_action` = 2026-12-26T08:21:15Z | raw_persistence audit |

### License classes inside the archive

Counted from the committed manifests, classified by `source_kind`.

| Class | Artifacts | Bytes | Kinds | Redistribution position |
|---|---:|---:|---|---|
| SEC EDGAR (public) | 3,940 | 5,932.7 MB (96.7 %) | companyfacts, submissions, filings, XBRL, N-PORT, index | US government data; SEC states EDGAR data is public. Low risk (still subject to SEC fair-access rules for *fetching*) |
| Yahoo | 2,700 | 178.7 MB | YAHOO_CHART, YAHOO_SPLIT_EVENTS | **High.** Yahoo Finance terms: "do not redistribute"; automated access needs permission; underlying exchange/vendor licences apply |
| Tiingo | 139 | 24.1 MB | EOD/daily/search JSON | **High.** Tiingo ToS: API data is internal use only; redistribution needs a paid licence |
| Stooq | 28 | ≈0.0 MB | daily CSV | **Unknown → treat as restricted.** No published redistribution licence found |
| iShares (N-PORT holdings file) | 1 | 1.5 MB | ISHARES_FUND_HOLDINGS | Restricted (issuer website content) |
| **Third-party total** | **2,868** | **≈204 MB** | | Must never be in a public location |

**Existing exposure (fact, not a new action):** this repository is public, so its Actions artifacts can be downloaded by
signed-in GitHub users. The current artifact therefore already exposes the third-party payloads until it expires. Re-uploading
the same archive to another public location (a public Release, or a public re-upload workflow) would extend that exposure with no end date.

## 2. Re-confirmation of expiry and actual downloadability / restorability

- Artifact API (2026-10-01): `expired=false`, `expires_at=2026-12-26T08:21:15Z`, digest `sha256:712e43…f94`. This equals the
  `raw_integrity_audit_2026-09-27.json` `archive_sha256`. Downloading does **not** extend retention.
- From the Claude cloud container the artifact could **not** be downloaded: the egress policy denies `productionresultssa10.blob.core.windows.net`.
- Read-only restore check on a GitHub runner: workflow `raw-artifact-restore-check.yml`, tool `tools/raw_artifact_restore_check.py`.
  The run downloads the zip, verifies its sha256, extracts it, checks every blob against the committed manifests and runs an
  offline replay smoke test.

### 2a. Restore check result — run 36850391139, job 110330389345, head 4c2f2d0: **PASS**
| Check | Result |
|---|---|
| Download from runner (REST, `actions: read`) | 451,439,890 bytes in 21 s |
| Archive sha256 | `712e43bc…f94`, equal to the expected value |
| Extract | 26 s, 6,186,073,534 bytes on disk (`data/`, `reports/`) |
| Blobs vs committed manifests | **6,808 / 6,808 present and sha256/size verified, 0 mismatched** |
| Restored manifests vs committed | identical (6,808); manifest-set sha `17934234…e828` reproduced |
| Offline replay smoke (existing `ingestion.replay`) | Yahoo 5y bars parsed (1,253–1,254 bars); SEC companyfacts parsed |
| Extra content | 96 `history/` prior versions (not in committed manifests; kept as-is) |
| gate_evidence in archive vs repo (info) | 68 identical, 7 later-finalized in repo, 0 only in archive |

Evidence: `reports/raw_persistence/restore_check_2026-10-01.json`. Today the archive is **fully recoverable**, until 2026-12-26T08:21:15Z.

## 3. Option comparison (dataset = 451 MB zip; 6.1 GB if stored unpacked)

| # | Option | ① Cost | ② Free allowance | ③ Fit for 6.1 GB / 451 MB | ④ Private | ⑤ Yahoo/Stooq/Tiingo redistribution risk | ⑥ Immutable / versioning | ⑦ Checksum / provenance | ⑧ Automatic backup | ⑨ Restore difficulty | ⑩ Vendor lock-in |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | **GitHub Release in this public repo** | $0 | No total-size or bandwidth limit; ≤2 GiB per file; ≤1000 assets per release | Zip fits in 1 asset | **No, public** | **Unacceptable** (public, indefinite) | Assets can be deleted/replaced by maintainers. Immutable-release setting: verify availability | Release asset digest + our manifest-set sha | Only via a workflow (needs `contents: write`) | Easy (one download) | Low to medium (GitHub) |
| A′ | GitHub Release, SEC-only partition, public | $0 | Same | 5.9 GB → zip it (≤2 GiB/file; split if needed) | Public, but SEC data is public | Low (third-party excluded) | Same as A | Same | Same | Medium (need both partitions) | Low to medium |
| B | **Private GitHub repository + Release asset** (new repo, e.g. `Investment-System1-rawdata`) | $0 on GitHub Free | Same Release limits; Release assets are not billed as LFS/Actions storage | Zip fits in 1 asset | **Yes** (private repo ⇒ private releases) | Low (private, internal use) | Same as A; protect with branch/tag rules plus our sha manifest | Asset digest + manifest-set sha recorded in public repo | Via a workflow in the private repo (artifact → release) | Easy (authenticated download) | Medium (GitHub account is a single point of failure) |
| C | Private GitHub repository, plain git | $0 | Per-file hard limit 100 MB; push limit 2 GB; GitHub strongly recommends repos < 5 GB | **Poor.** 6.1 GB exceeds the recommendation; the zip must be split; history is permanent | Yes | Low | Git history (commits) | Git hashes + manifests | Manual pushes | Hard (large clone) | Medium |
| D | Git LFS (private repo) | $0 within quota; overage $0.07/GiB-month storage, $0.0875/GiB transfer | GitHub Free: 10 GiB storage + 10 GiB bandwidth/month | Storage fits (zip 0.45 GB, or 6.1 GB unpacked). Bandwidth: one unpacked restore ≈ 6.1 GB of the monthly 10 GiB | Yes, if repo private (public repo ⇒ public LFS) | Low if private | LFS objects are content-addressed (sha256); deleting them needs repo deletion | Native sha256 + manifests | Manual push | Medium (needs git-lfs) | Medium to high (LFS store tied to repo/host) |
| E1 | Cloudflare R2 | $0 within free tier; then $0.015/GB-month; egress free | 10 GB-month storage, 1M Class A / 10M Class B ops | Fits free tier (0.45 GB or 6.1 GB) | Yes (private bucket) | Low (private) | Bucket locks / object lifecycle available | Object etag + our sha manifest | Possible via an Actions upload (needs secret) | Easy (S3-compatible) | Low (S3 API) |
| E2 | Backblaze B2 | $0 for first 10 GB; then $6.95/TB-month; egress free up to 3× stored | 10 GB storage | Fits free tier | Yes | Low | Object Lock / versions | sha1/sha256 + manifest | Same as E1 | Easy (S3-compatible) | Low |
| E3 | GCS Archive / AWS S3 Glacier Deep Archive | ≈$0.0012/GB-month (GCS) / ≈$0.00099/GB-month (AWS); retrieval fees; 365/180-day minimum | GCS always-free 5 GB is for the Standard class only; no free Deep Archive | Fits (cents per month) | Yes | Low | Retention policy / Object Lock + versioning | Checksums + manifest | Lifecycle/scheduled jobs | **Slow** (hours) plus retrieval fees | Medium (proprietary retrieval) |
| F | Local-only / offline archive (user disk, USB/NAS) | Hardware the user already owns | n/a | Fits easily | Yes | Low (internal) | Write-once media or a read-only copy | Our sha manifest (verify on restore) | **None** unless the user schedules it | Medium (physical access) | None |
| F′ | User's personal cloud drive (e.g. existing Google Drive) | $0 within the user's quota | Depends on the user's plan (Google free = 15 GB shared) | Zip fits | Yes (private sharing) | Low if not shared publicly | Drive file versions (limited) | Our sha manifest | Manual, or via a connector | Easy | Medium |
| G | Actions artifact refresh (re-upload every <90 days) | $0 on public repo | Public repo: free, retention 1–90 days | Fits | **No** (public repo) | **Same exposure, extended indefinitely** | New artifact every cycle | Digest per artifact | Scheduled workflow | Easy | Medium; a missed cycle loses the data |
| H | **Multiple copies (3-2-1)** | Sum of the chosen copies | — | — | Each copy private | Low if every copy is private | Strongest when ≥1 copy is object-locked or offline | Single manifest-set sha shared by all copies | ≥1 automated copy | Easy (fallback copies) | Low (no single vendor) |

## 4. Assessment
- **Rule out for the full archive:** A and G (public, they extend the third-party exposure), and C (repo size and per-file limits).
- **D (LFS)** works only in a private repo. Its 10 GiB/month bandwidth is shared with every clone, and LFS objects are hard to remove. It gains nothing over B for a single 451 MB zip.
- **B (private GitHub repo + Release asset)** is the cheapest durable GitHub-native primary: $0, no expiry, private, one-file restore.
  It needs one approval: creating a private repository is an outward action on the user's account. It also needs a one-time
  transfer of the artifact to the release. A workflow can do that before 2026-12-26 with no bytes passing through this container.
- **E1/E2 (R2 or B2)** are the best independent second copy: S3-compatible, inside the free 10 GB, versioning/lock available.
  They need an account (possibly a payment method on file) and a credential secret. That is a user decision; nothing was signed up for.
- **F/F′ (user-held)** is the vendor-independent copy, and the user controls it fully.
- **A′ (public SEC-only partition)** is optional and only useful if public reproducibility is wanted. It is not needed for preservation.

## 5. Recommended architecture (subject to approval)

```
             public repo (unchanged): manifests + manifest_set_sha256 + storage_locations_<date>.json + restore tool
                                     (provenance of record; no payloads)
                                                   │ same sha256 binds every copy
         ┌─────────────────────────────────────────┼──────────────────────────────────┐
 Copy 1 (primary, private, no expiry)       Copy 2 (independent vendor)          Copy 3 (offline / user-held)
 private GitHub repo Release asset          R2 or B2 private bucket,             user disk or personal drive
 c21-raw-store-36305927245.zip (451 MB)     object lock/versioning on            (zip + sha256 file)
         └────── each copy verified by tools/raw_artifact_restore_check.py → PASS before it is recorded ──────┘
```

Order of work, each step gated on user approval:
1. **Before 2026-12-26:** approve Copy 1. Create a private repo, then run a transfer workflow: download artifact → verify sha → create a private release asset. Run the restore check against the release copy.
   Record it in `storage_locations_<date>.json`. The verdict becomes `DURABLE_COPY_PRESENT` only after verification.
2. Copy 3 (user-held): the user downloads the zip once (the browser can, the container cannot) and keeps the sha256 file next to it.
3. Optional Copy 2 (R2/B2), only if the user approves an account and a secret.
4. Future runs: new raw stores go to the same private targets, with a new `dataset_id` and manifest. Old copies are never overwritten (versioned).
5. Do **not** create public copies of third-party payloads. If public reproducibility is wanted later, publish only an SEC-only partition (A′) as a separate decision.

Decisions requested:
- (a) Approve Copy 1: create a private repo and run the transfer workflow.
- (b) Is a user-held copy acceptable?
- (c) Is Copy 2 wanted, and with which provider?
- (d) Should the current public artifact be left to expire on 2026-12-26, or deleted after durable copies are verified?
  Deletion is irreversible and was **not** done.

## 6. Not done
No upload, release, repository creation, account sign-up, payment, secret, deletion, or change to the existing artifact or its retention.

## 7. Sources (accessed 2026-10-01)
- GitHub releases limits (2 GiB per file, 1000 assets, no total/bandwidth limit): https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- Git LFS billing (Free: 10 GiB storage + bandwidth; $0.07/GiB storage, $0.0875/GiB transfer): https://docs.github.com/en/github/setting-up-and-managing-billing-and-payments-on-github/about-billing-for-git-large-file-storage ; https://github.com/orgs/community/discussions/61362
- Repository limits (100 MB file, 2 GB push, <5 GB recommended): https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits
- Actions artifact retention (public 1–90 days, private 1–400 days): https://www.warpbuild.com/answers/how-long-are-github-actions-artifacts-kept ; https://github.com/actions/upload-artifact/issues/738
- Cloudflare R2 pricing: https://www.cloudflare.com/en-in/developer-platform/products/r2/
- Backblaze B2 pricing: https://www.backblaze.com/cloud-storage/pricing
- GCS / S3 archive pricing: https://www.nops.io/blog/google-cloud-storage-pricing/ ; https://securityboulevard.com/2026/06/glacier-and-deep-archive-pricing-the-complete-2026-cost-guide/
- Yahoo Finance redistribution: https://help.yahoo.com/kb/SLN2310.html ; https://www.promptcloud.com/blog/scrape-yahoo-finance/
- Tiingo terms: https://app.tiingo.com/tos/ ; https://www.tiingo.com/documentation/appendix/
- Stooq (no published licence found): https://apis.io/providers/stooq
- SEC EDGAR public data: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data ; https://data.sec.gov/
