# Market 19-symbol identity / time / quote-state evidence audit v0.3

Status: READ_ONLY_EVIDENCE_REVIEW / PRODUCTION_ADMISSION_BLOCKED. No production code, registered schema, protected Web or package adapter was implemented. Prior v0.1/v0.2/audit/raw artifacts remain unchanged.

## Exact source trees and method

- Chart source: `54ee25446ccf6cfa32ddf164a8ed31b7e1036b9a`.
- Read-only Integration/FPIA source: `523e702a806a718d163cfbf62aa3fc29d8c3ef3c`.
- All nineteen prior Yahoo raw hashes were rechecked against both acquisition and coverage records. No nineteen-price refetch was performed.
- Existing `tools/fetch_real_data.py._get` was reused unchanged for public source byte capture, with at most three concurrent requests, no credential, login or payment. Exact URLs, original SHA256 and observation windows are in the four `*_SOURCE_ACQUISITION.json` records and the machine-readable matrix.
- Twenty-two public source responses were captured byte-for-byte. Their nominal document dates or effective dates are kept separate from this audit's current acquisition clocks. None supplies exact historical per-bar `available_at`.
- Source pin hashes for both trees are in `SOURCE_PIN_REPLAY.json`. Root owns fresh remote/Actions review and publication; this subtask did not mutate another owner branch.

`READY` below means a narrow raw/current source fact is present, never whole-chart or producer admission. `PARTIAL` means evidence exists but required dated/economic/availability bindings remain incomplete. `BLOCKED` marks a required join that cannot admit inputs. `NOT_AVAILABLE` preserves an absent fact as `UNKNOWN`, never zero or an invented identifier.

## What the new authority evidence narrows

1. The SEC current company/ticker/exchange file corroborates all seventeen US issuer CIK/ticker/exchange pairs against the repository's current CIK map (17/17 exact matches). Its documentation says the file is updated periodically and does not guarantee accuracy or scope. It is a current issuer association, not a security master, share-class record or historical listing interval.
2. Tokyo Electron's current issuer page corroborates domestic common stock code `8035`, Tokyo Stock Exchange Prime. It also separately lists `TELWY` OTC ADR and its own CUSIP/ratio. Those ADR identifiers must never be assigned to `8035.T`; bare US `TEL` is not used to repair the mapping.
3. FSS DART's current company information corroborates HANMI Semiconductor, code `042700`, KOSPI market. It does not establish an admitted internal security ID, MIC, listing history, effective period or historical source-publication time.
4. ASML's current issuer share information distinguishes registered ASML NASDAQ ordinary shares from its Euronext form, with NASDAQ ISIN `USN070592100` / CUSIP `N07059210` and Euronext ISIN `NL0010273215`. Do not infer an ADR because the issuer is foreign. These current identifiers are not a full historical interval or internal-ID assignment.
5. GEV's issuer planned announcement identifies anticipated `GEV WI` when-issued trading beginning about 2024-03-27 and regular-way `GEV` from 2024-04-02. Its actual 2024-04-02 release confirms regular-way trading effective at market opening. Three prior raw `GEV` bars (March27, March28 and April1) predate the confirmed regular-way interval. Their vendor splice/mapping is unverified; preserve them and require `trading_regime` plus dated provider-series binding.

Every symbol still lacks an admitted internal issuer → security → listing → exact provider-series interval. No ticker, CIK, company alias, suffix, or vendor firstTradeDate is promoted to a stable security/listing ID.

## 19-symbol field coverage

Detailed field-level records, exact values, status/reason and source references are in `MARKET19_IDENTITY_TIME_READINESS.json`. These nineteen rows preserve prior span/shape facts by hash reference; OHLC basis/anomaly evidence is owned separately.

| Provider symbol | Current authority venue | Security/listing IDs | Listing history | Declared timezone | Raw local bar clock | General delay guidance | Exact response state |
|---|---|---|---|---|---|---|---|
| ASML | Nasdaq / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | Real-time service candidate | UNKNOWN |
| LRCX | Nasdaq / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | Real-time service candidate | UNKNOWN |
| KLAC | Nasdaq / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | Real-time service candidate | UNKNOWN |
| 8035.T | Tokyo Stock Exchange / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | Asia/Tokyo / PARTIAL | 09:00:00 | 20 min service candidate | UNKNOWN |
| 042700.KS | KOSPI Market / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | Asia/Seoul / PARTIAL | 09:00:00 | 20 min service candidate | UNKNOWN |
| NVDA | Nasdaq / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | Real-time service candidate | UNKNOWN |
| AMD | Nasdaq / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | Real-time service candidate | UNKNOWN |
| AVGO | Nasdaq / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | Real-time service candidate | UNKNOWN |
| QCOM | Nasdaq / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | Real-time service candidate | UNKNOWN |
| INTC | Nasdaq / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | Real-time service candidate | UNKNOWN |
| MSFT | Nasdaq / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | Real-time service candidate | UNKNOWN |
| GOOGL | Nasdaq / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | Real-time service candidate | UNKNOWN |
| AMZN | Nasdaq / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | Real-time service candidate | UNKNOWN |
| RTX | NYSE / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | UNKNOWN service candidate | UNKNOWN |
| SYK | NYSE / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | UNKNOWN service candidate | UNKNOWN |
| ETN | NYSE / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | UNKNOWN service candidate | UNKNOWN |
| HUBB | NYSE / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | UNKNOWN service candidate | UNKNOWN |
| GEV | NYSE / PARTIAL | BLOCKED / UNKNOWN | PARTIAL | America/New_York / PARTIAL | 09:30:00 | UNKNOWN service candidate | UNKNOWN |
| ROK | NYSE / PARTIAL | BLOCKED / UNKNOWN | NOT_AVAILABLE | America/New_York / PARTIAL | 09:30:00 | UNKNOWN service candidate | UNKNOWN |

All nineteen historical availability fields are `NOT_AVAILABLE / UNKNOWN`. Exact per-row publication, revision/finality and complete source-admitted calendar vintage are absent for all nineteen. The original price data scope stays nineteen provider labels, not nineteen certified economic identities.

## Session authority, history and timestamp counterexamples

- NYSE original current hours/calendar gives ordinary core 09:30–16:00 ET and 2026–2028 holiday/early-close notices.
- NasdaqTrader current source includes the 2026 holiday/early-close table; original 2021–2025 calendar PDFs and current system-hours PDF were additionally captured. The separately captured Jimmy Carter notice establishes the extraordinary closure on 2025-01-09; an annual recurring-holiday table alone is insufficient. PDF bytes/nominal year do not provide complete historical knowledge-time, a parsed session-row vintage or certification for NYSE calendars.
- JPX current hours provides morning 09:00–11:30 and afternoon12:30–15:30. The **actual go-live** notice dated 2024-11-03 confirms the system upgrade and 30-minute extension effective2024-11-05. This is stronger than the earlier planned announcement, but no exact first-publication clock or complete 2021–2026 exceptional-session dataset was obtained. Current JPX holiday page covers2026/2027 only.
- KRX current stock authority gives ordinary09:00–15:30 and holiday rules. The exact KOSPI CSAT notice for2025-11-13 instead gives10:00–16:30.

A new deterministic counterexample is material: old `042700.KS` raw index1004 has timestamp `1762992000`, which renders as **2025-11-13 09:00KST**, while that date's official exchange open was10:00KST. Consequently the daily bar timestamp cannot be treated universally as actual session open. The prior ordinary-clock observation is preserved but narrowed: it is a provider bar label that often resembles nominal open, not proof of actual open. The same raw response also labels2024-11-14 at09:00; no arbitrary historical rule is inferred for that date here.

Another preserved conflict remains: latest Hanmi vendor regular period ends15:00KST, while current KRX ordinary-close authority says15:30 and latest `regularMarketTime` is15:30:19. These facts stay separate, without repairing the raw end hint.

The reusable US binder currently supports only `NMS→XNAS`, `NYQ→XNYS`, `PCX→ARCX` and matches bar timestamp exactly against calendar open. It also carries close/volume rather than lossless full OHLCV. A JP/KR extension cannot safely consist of adding exchange aliases: it needs explicit provider label semantics, split sessions, dated exceptions and reviewed calendar admission. This is a deferred domain-owner/package change, not implemented by this audit.

Original evidence and exact indices are in `TIMESTAMP_AND_LISTING_COUNTEREXAMPLES.json`. No raw timestamp/row was moved, relabeled or deleted.

## Separate time roles

| Role | Actual available evidence | Missing production binding |
|---|---|---|
| event_time | No per-trade events for aggregate candles | UNKNOWN; never copied from bar label |
| bar/session label | Original timestamp array; local date/clock under declared provider IANA timezone | Provider role declaration and dated session join |
| provider timestamp | Latest `regularMarketTime` only | Historical per-bar publication/revision/finality |
| market close | Ordinary authority rules plus some dated exceptions | Complete source-admitted per-date/calendar vintage |
| observed_at | Prior exact request-start and recorded-completion windows | First-four completion records include post-read work; not exact receipt clock |
| available_at | No historical per-bar exact source evidence | NOT_AVAILABLE, not bar timestamp/close/retrieval default |
| knowledge_time | Current observation bound for this response | Historical knowability UNKNOWN; no v0.2 rule adopted |
| ingestion/persistence time | Explicit persistence clock for the later fifteen probes | Separate precise persisted_at absent for first-four; file clock not substituted |

The meta `gmtoffset=-14400` is a current hint. The old US timestamps span both `-0400` and `-0500` under declared `America/New_York`; a constant current offset must not be applied to five years. Derived timezone rendering is an audit observation, not an exchange-calendar vintage. Calendar close can be a lower-bound guard without proving provider publication or revisions.

Current historical-response capture proves access now. It cannot prove that today’s history, revisions or adjustments were available at a prior decision point. A future prospective collection may record current access bounds explicitly, but should not claim exact earlier provider availability or fill historical PIT fields.

## Quote-state source support

The newly captured official Yahoo help page succeeded, narrowing the prior help-retrieval gap. It declares **general** Nasdaq stock guidance as real-time and Tokyo`.T` / Korea`.KS` as20-minute delay. The captured table has **NYSE Indices15-minute delay**, but no NYSE stock-equity row; no NYSE-listed equity feed-state claim is inferred from it. It also separately describes international historical chart data/daily updates under Morningstar, so live-exchange guidance is not a complete per-history-row vendor lineage.

This table is service-level guidance. All nineteen exact v8 price responses still lack `marketState`, `exchangeDataDelayedBy` and `quoteType`, so every exact quote-state remains`UNKNOWN`. `regularMarketTime`, end-of-session timing, provider LIVE guidance, exchange open/closed state and product publication are different facts. No `CLOSE`/finality label is inferred from market closure. **Price feed state != Investment-System Official/LIVE state**; no product promotion or grant occurred.

## Schema/dependency implications, proposals only

- Preserve current authority associations as evidence candidates while keeping internal IDs/date ranges unknown until owner admission.
- C05 timestamp correction needs explicit provider-bar label role, authoritative session/calendar refs, conflict status, knowledge/access bounds and per-row admission reason. Never make`bar_timestamp==market_open` universal.
- Add or retain effective provider-series relation and **trading_regime** evidence for when-issued/regular-way boundaries, independent of corporate-action price basis.
- Keep general quote-feed guidance separate from exact endpoint/row quote-state and product authority. Missing per-response state should remain explicit.
- Hash-addressed dated notices narrow calendar evidence but are not an auto-created CalendarVintage; complete exception coverage and historical publication must be assessed separately.

| Work | Protected mutation | P01 impact | Track C package code_hash | Implementation condition |
|---|---|---|---|---|
| This field matrix/source capture/counterexample/docs | None | None | None | Completed read-only evidence scope |
| Further public data inventory or out-of-package read-only checks | None if paths stay scoped | None | None | Possible now; no admission claim |
| Identity/calendar population as proposed data | None by itself | None by itself | None by itself | Domain-owner admission/evidence semantics needed before product use |
| Full OHLCV binder/projection or foreign-session changes under package | Package change | Path-dependent | Affected | Defer; owner boundary, exact tree, FPIA/Integration |
| Product schema/validator/assembler registration | Protected/package changes | Affected for guarded Web | Affected for packagePython | Defer; exact owner impact and exact merge-result audit |

No new paid data, account access, Frozen/Official semantic decision or D3 execution was needed for this evidence work. Adoption of proposed runtime session/identity semantics remains a separate reviewed implementation decision. Production regression, Actions and FPIA are **NOT_RUN by this subtask**; root reports the independently observed Integration state.
