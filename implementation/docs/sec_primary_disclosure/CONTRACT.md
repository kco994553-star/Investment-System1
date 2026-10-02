# SEC_PRIMARY_DISCLOSURE v1

Not an Official news provider. Not general or journalistic news.
Stacked on `feature/rig-news-real-ingestion-v1`. PR #13 history is not rewritten.
PR #7 source is not copied or modified.

## Path

```text
SEC Atom bytes
  -> versioned adapter sec_primary_disclosure_v1
  -> NewsRawItem (empty body, no summary HTML)
  -> RIG_NEWS_INGEST validation
  -> explicit CIK → company_id → issuer_id map
  -> exact dedup
  -> PRIMARY_DISCLOSURE_SNAPSHOT
```

`general_news_snapshot` stays `NOT_AVAILABLE` / `NEWS_NO_SOURCE`.
`publish_web_disclosure` always raises. No LIVE TTL is defined.

## What is stored

Public items may carry the SEC feed title, form type (`8-K` or `8-K/A`),
SEC item code and label, dashed accession, feed `<updated>` timestamp, and the
sec.gov index URL. `filed_on` is the date-only `Filed:` value when that value
is `YYYY-MM-DD`. A date is not given a clock time. `<updated>` is feed
dissemination. It is not `acceptanceDateTime` and not a publication time.
`acceptance_at` stays `NOT_PROVIDED`.

The summary HTML, exhibit body, and third-party snippets are not copied.
`raw_bytes` stay in memory on `DisclosureBatch` and are not committed.

## Language

No `xml:lang` means `LANGUAGE_NOT_PROVIDED`. A present `xml:lang` is kept
exactly when it is a BCP 47-like tag. Titles are not used to guess a language.
`display_locale` is not an input.

## Identity

CIK is read from the SEC title token and the index URL. If they disagree the
entry is rejected. Company and issuer ids come only from `ExplicitIdentityMap`
or from the `cik` and `company_id` fields of a caller-supplied PR #7 registry
document. Names, tickers, and aliases are not search keys. A missing issuer
leaves `company_filter` `NOT_AVAILABLE`. An ambiguous CIK is not assigned.

## Dedup

Same accession and same raw entry bytes: `EXACT_DUPLICATE`, one item kept.
Same accession and different bytes: `CONFLICT`. Different accessions are never
folded together, including when the titles match. No similarity threshold.

## User-Agent

`fetch_sec_atom` requires `SEC_USER_AGENT` or `INVESTMENT_SYSTEM_SEC_UA`.
The contact string is not hard-coded. Parsing supplied bytes does not fetch.
