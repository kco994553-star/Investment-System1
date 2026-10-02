# SEC primary disclosure — status

Branch `feature/sec-primary-disclosure-v1`, stacked on `feature/rig-news-real-ingestion-v1`.
Not merged. PR #13 was not rewritten. PR #7 source was not copied.

| Flag | Verdict |
|---|---|
| SEC_PRIMARY_DISCLOSURE_PROVIDER_READY | YES for supplied Atom bytes. Live fetch is configuration-gated and was not run |
| SEC_ENTITY_MAPPING_READY | NO. The explicit CIK map exists. No production company/issuer map is shipped |
| PRIMARY_DISCLOSURE_SNAPSHOT_READY | YES. Public record only. Web publication is blocked |
| PRODUCER_INFRA_COMPATIBLE | YES. General news remains `NOT_AVAILABLE` / `NEWS_NO_SOURCE`. This snapshot is not a Web section |
| GENERAL_NEWS_PROVIDER_READY | NO |
| RIG_REAL_PRODUCER_READY | NO. Kind, statement, and polarity are not invented |
| CONSENSUS_PRODUCER_READY | NO |

`LANGUAGE_NOT_PROVIDED` is a general schema-1 token. Existing BCP 47 tags still pass.
A date-only `Filed` value is not turned into a clock time. `<updated>` is not stored as acceptance time.

Targeted `tests/test_sec_primary_disclosure_v1.py`: 13 passed, 0 failed.
Full regression on this branch: 423 passed, 0 failed, mini_pytest shim (not pytest).
Existing `tests/test_rig_news_ingest.py` still passes. Frozen RIG modules outside `ingest/` were not edited.

