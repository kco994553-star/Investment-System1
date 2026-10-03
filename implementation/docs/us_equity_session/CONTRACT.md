# US_EQUITY_TRADING_SESSION_V1

Status: approved contract, implemented as a separate layer.
Not an Official Technical producer. Not Track C validation.

The Technical research record in `technical/real_model_v1.py` is unchanged.
This layer only decides whether stored Yahoo daily bars may be given an
explicit `session_index`, and which of those bars may enter that record.

## Pipeline

Calendar vintage → session binder → listing evidence → Yahoo bar →
`session_index` → close-availability guard → existing `build_research_record`.

## Session source

A session exists only as a row in a versioned calendar body.
The body hash is `calendar_id`. Missing dates are not sessions.
There is no weekday rule, federal-holiday rule, or weekend-observance function.
A key outside the schema, including a rule list, is rejected.

Each row keeps `venue_mic`, `session_date`, `open_local`, `close_local`,
`status`, `row_available_at`, and a source id whose sha256 is declared on the vintage.
`CLOSED` does not consume `session_index`. An early close is one `OPEN` row.

`row_available_at` is the PIT gate. `fetched_at` on a `RawDatasetStore` manifest is not.
If any row is known only after `decision_time`, the vintage is `CALENDAR_NOT_ADMISSIBLE`.
A later vintage does not replace the `calendar_id` of a replay that still passes the earlier bytes.

## Yahoo binding

`interval=1d` timestamps are identity only.
Conversion uses `America/New_York` from the runtime IANA data named by `tzdata_version`.
The chart offset field is not read.
A bar binds only when its UTC instant equals that row's `open_local`.
Zero matches or more than one match makes the whole series
`SESSION_CONTINUITY_UNVERIFIED`. The unmatched bar is not dropped.
Two bars on one session raise `DUPLICATE_SESSION_BAR`.
Null close and null volume stay on their original index.

`session_index` is the 0-based rank of `OPEN` rows in that vintage.
An `OPEN` session with no bar leaves a hole. The hole is not closed up.

## Listing

One `ListingIdentity` plus evidence `available_at <= decision_time` must cover
every bound session date. Otherwise `LISTING_UNVERIFIED`.
Two listings are not stitched: same ticker and different `security_id` is
`TICKER_REUSE`; different `mic` is `EXCHANGE_TRANSFER`.
Yahoo `exchangeName` must be the explicit map `NMS→XNAS`, `NYQ→XNYS`, `PCX→ARCX`.
Any other code is `UNKNOWN_EXCHANGE`.
`firstTradeDate`, `exchangeName` text, and `markets/us.py` are not listing evidence.

## Relative strength

SPY is bound on its own vintage. The `OPEN` session dates in the inclusive span
of the two eligible series must be the same set before the series share indexes.
Otherwise `rs_20` is `RS_UNALIGNED` and no union calendar is built.
Stock features that do not need SPY are left as the existing model computed them.

## Close availability

The daily timestamp is not the close's availability time.
This layer does not invent a provider publication timestamp and does not rewrite
`observed_at` or `available_at` inside the Yahoo stamp.
If `decision_time` is strictly before the row's `close_local`, that bar is not a
Technical feature input. The raw bar is retained on `excluded_before_close`.
This is only a no-lookahead lower bound.

## Readiness

`official_ready` and `research_ready` on the binding envelope are false.
`OFFICIAL_TECHNICAL_PRODUCER_READY` stays NO until Track C.
`REAL_TECHNICAL_RESEARCH_PRODUCER_READY` stays NO until a real exchange vintage
and listing evidence have been replayed through this binder into the research record.
Fixture rows in the tests are not that vintage.

## Lineage

`calendar_id`, `listing_id`, `tzdata_version`, and the Yahoo raw sha256.
SPY adds its own calendar id, listing id, and sha256 when a SPY body is supplied.
