# Common SEC class / KIS correspondence

Owner scope: execute security correspondence only. No share-basis batch, action
interval batch, price correction, verification promotion, representative-security
selection or Top500 transition. Base canonical
`4a3141b8fa1593e68552390c7ad4b1ea16b89d2f`.

`research.security_correspondence.cover_observations` calls the existing
`providers.sec_cover_shares.parse_cover`; it reads class/symbol/venue contexts and
source periods. Existing shares extraction is not used as valuation data. No
provider or operating module is modified. No network or file writes in the API.

`correspondence(company_id, issuer_id, document, provider, evaluation_day=...,
known_conflicts=..., symbol_transitions=...)` returns `security-correspondence/1`.
Document source body SHA is checked before extraction; private execution also
checks cover/submissions hashes against the held raw archive manifest. New source
requests are zero. The observed provider symbol/request linkage reuses the pinned
day-1 receipt/body validation; a request lookup is not a permanent security ID.

Fields kept distinct:

- `company_id`: existing Universe code row; `issuer_id`: existing CIK issuer key.
- `class_member`, `security_title`, `security_kind`: source class fields, not an
  accounting model. `class_observation_id` is only an internal source-observation
  fingerprint; `security_id` and Top500 `economic_class_id` stay null.
- `sec_symbol`, reported symbols, exchanges and context IDs/periods; provider
  `symb/excd/returned_symbol` plus receipt/source pointers.
- `sec.filing_date`, `report_date`, acquired/reviewed timestamps and source hashes.
  A report period and filing date never become `valid_from` or `valid_to`.
- `document_status=CONFIRMED|UNCONFIRMED` is a claim about the document-to-provider
  correspondence. `evaluation_status=VALIDITY_UNCONFIRMED` separately records the
  absence of complete evaluation-day validity proof. `verification` stays
  `UNVERIFIED_REFERENCE`; there is no price/score adoption here.

Rules: exact code/class matching; no lowercase conversion or generic ticker alias.
Only literal quotation wrappers and literal exchange suffixes can be stripped,
with raw strings retained and an independent venue check. Registered debt is not
an alternative common class for the stock quote endpoint. Multiple venues of the
same explicit class are preserved as venues rather than duplicate classes.
Different equity class members remain separate. Dated symbol transitions require
an explicit reviewed statement, issuer, exact class title, cover hash, source hash,
locator and effective day; neither title similarity nor a ticker alone suffices.
Future filings and source/issuer/class/venue conflicts remain unconfirmed. Known
identity changes are not overwritten by matching older source strings.

A held HTML cover can be supplied as literal reviewed table facts with its source
body hash and exact locator. It is labelled as manual cover review, not falsely
represented as XML extraction. Existing dated identity-event statements can link
an old cover symbol to a current provider symbol without inventing an interval.

`top500_class_candidate(row)` projects the **same** issuer/class/source fields for
#544. It preserves `identity_status=UNVERIFIED`, null permanent/economic class IDs,
null price/shares/validity, and `corporate_action_status=NOT_EVALUATED`. A matched
query venue is not a representative or primary listing decision. The existing
Top500 selector must continue rejecting the incomplete valuation/eligibility input.

## Actual held-source result

Evaluation context:2026-11-13; new review/current knowledge:2026-11-15. Universe504,
504 code rows /501 issuers; original denominator unchanged.

| Claim | Count |
|---|---:|
| Document correspondence confirmed |493 code rows /490 issuers |
| Document correspondence unconfirmed |11 code rows /11 issuers |
| Full evaluation-day validity proven |0 issuers |
| Permanent security IDs assigned |0 |
| Price adjustments / verification promotions / new QGV scores |0 /0 /0 |

Mutually exclusive primary reasons for the11 unconfirmed issuers: known dated
identity conflict4; source symbol unresolved4; held cover absent1; class ambiguity1;
exchange unresolved1. Multiple-reason counts are separately preserved privately
and must not be summed into an issuer total. In particular, absent source is not
reported as a failed issuer match.

The retained inventory supplied577 cover observations /500 distinct XML bodies;
499 issuers had held covers. One existing reviewed HTML cover and one existing
explicit dated symbol-change statement were additionally reused. No source was
re-downloaded and no missing market observation was filled. Repeated source hashes
were parsed once, and the same issuer was not investigated per code row.

Private JSON/CSV includes row-level reasons, class/source locators and timestamps;
Top500 candidates are grouped into501 issuers without merging class rows. Public
files include code, synthetic tests and aggregate status only. Implementation
checks cover hash/CIK/date conflicts, missing source/response, distinct classes,
multi-venue registrations, debt exclusion, literal formatting, dated transitions
and no Top500 promotion. CI's existing full pytest discovery includes these tests.

## 11/11 comparison boundary

Main #437 comment6890042634 reports the exact central financial input bytes
(SHA256 `001e0f39b0b7a26fe782870d1a93cd82f08e5df88593915b8db8e579ce87d084`)
have not been located; the original Pages artifact has expired. The score
publication and raw SEC shards remain, but are not the cumulative input snapshot.
No same-input comparison was run, and explained/unexplained counts remain
unmeasured. Do not reconstruct from a few shards and call it identical unless the
full original hash matches. Do not use current financial inputs or infer prices
from scores. KIS remains an unverified private reference.
