# Applicability / N/A authority audit — inactive Binding Gate

**Status: SOURCE_CHARACTERIZATION_COMPLETE / B2 D2 RECOMMENDATION / CONCRETE PREDICATES NOT_APPROVED.**

The approved M1–M5 principles are read from `../implementation_contract/approval.json`. This audit extends the inactive Implementation Contract §§3–5; it does not promote a current bool or QualityState to vNext N/A proof and does not change scores or historical evidence.

## Current predicate and method branches

| Current branch | Predicate / evidence used | Existing version/reason | Evidence/time limitation | New vNext proof status |
|---|---|---|---|---|
| Structural Q ROIC/WACC exclusion | `profile == FINANCIAL` and `factor_id == roic_wacc`; uses caller enum | Git source pin; note `roic_wacc=NOT_APPLICABLE` | No independent classification-source stamp, effective interval, approval ref or admitted predicate evidence | UNRESOLVED_APPLICABILITY for new admission until explicit authority is bound; legacy branch preserved |
| Raw financial ROIC N/A | `raw.profile_kind == FINANCIAL` | Notes `FINANCIAL ROIC N/A`; shared raw stamp | Raw source stamp dates fundamentals, not financial issuer classification | Same limitation; not proof from missing observation |
| NIM margin alternative | Raw financial classification and NIM present | Existing provisional linear clip; generic output note says `ebit margin` | Method switches by raw context and field presence; output note does not identify NIM branch or classification provenance | A method-selection proposal requiring B2/B4 binding, not N/A exclusion |
| CET1 health alternative | Raw financial classification and CET1 present | Existing provisional linear clip; generic note says `net cash / revenue` | Same context/branch provenance loss; fallback remains General proxy if CET1 absent | Method-selection authority unresolved; absence cannot prove N/A |
| Other 19 factor applicability | `factor_applicable` returns True | Default bool return | No predicate evidence or policy reference; domain applicability not established solely by bool | Preserved legacy behavior; independent vNext classification authority still needed |
| Caller-supplied observation NOT_APPLICABLE | QualityState present on observation | Prior reducer removes contribution; candidate may accept numeric N/A | Quality label alone is no economic predicate, source or denominator permission | Not valid N/A proof |

Sources: `implementation/src/investment_system/qgv/factors.py:42,103–117`; `qgv/raw_map.py:104–115,136–137,163–165`; `qgv/scoring.py:30–57,87–104`. All precise repository references use the source pin from `factor_roles.json`.

### Source/time/version authority

`ProfileKind` is GENERAL_CORPORATE or FINANCIAL (`contracts/enums.py:46–48`); `RawFundamentals.profile_kind` is a plain string with GENERAL default (`contracts/raw.py:53`). It is not a dated industry classification object. `Identifier` has optional sector/industry but no dated predicate provenance (`contracts/models.py:56–68`). The live JPM wrapper deliberately replaces `profile_kind` with FINANCIAL (`qgv/financial_issuer.py:39–46`) after the SEC General parser. This is source-supported current code; it is not an issuer-independent classification/economic-N/A authority.

DataStamp already contains provider, source type/reference, published_at, available_at, observed_at and optional period bounds (`contracts/models.py:34–50`). Memory provider selection rejects both future published_at and available_at (`providers/memory.py:20–28`; `pit/resolver.py:21–38`). Direct `analyze_raw` does not require_available before mapping (`qgv/pipeline.py:21–43`). The mapper gives every factor the shared fundamentals stamp ID (`qgv/raw_map.py:87–90,159–169`). This does not separately pin classification proof, financial applicability predicate, raw-method branch, NIM/CET1 source, or method version. Do not fabricate a classification date from fundamentals availability or current sector metadata.

A deterministic branch can be reproduced with pinned code and the raw context, but current snapshot profile/notes alone are insufficient to reproduce all branch choices. This is a **representation and authority gap**, not proof that all historical Official data leaked.

## Actual current context divergence counterexample

`AnalysisPipeline.analyze_raw` accepts an explicit scoring `profile_kind`, maps `raw` using its own raw-profile string, then passes the explicit enum to AnalysisEngine (`qgv/pipeline.py:21–33`). As a result, raw General input can use General margin/health methods and still be emitted under a FINANCIAL snapshot. Conversely raw financial input can emit financial NIM/CET1 methods under a General snapshot.

A bounded new probe used the existing synthetic JPM fixture copied with EBIT/revenue=.25, cash=debt=0, CET1=.14, NIM=.03. Both calls supplied explicit scoring profile FINANCIAL. These numbers are counterexample inputs only and propose no numeric default.

| Raw mapping context | Emitted snapshot profile | Margin method score | Health method score | Q result |
|---|---|---:|---:|---:|
| GENERAL_CORPORATE | FINANCIAL | EBIT margin: 100 | Net cash: 50 | 35.8 |
| FINANCIAL | FINANCIAL | NIM: 66.66666666666666 | CET1: 75.00000000000003 | 34.96666666666667 |

This was executed against unchanged current functions. Results are retained in `factor_roles.json.context_divergence_probe`. It does not establish a new consumer ranking result or modify a stored snapshot. Recommendation: B2/B4 bind **one resolved subject/profile/period context reference** and explicit selected-method branch; conflicting context stays unresolved in the new path. Preserve literal historical output rather than pretending its snapshot profile uniquely determines its method.

## Financial 56→70 decomposition

The original synthetic `financial_na` golden has all factor scores70 and profile FINANCIAL (`../../golden_cases.json:1351–1380`); the full actual path is `implementation/docs/qgv_common_contract_vnext/golden_cases.json`. Legacy expectation Q56 and Q coverage PARTIAL remain byte-preserved. Current financial applicability skips `roic_wacc` before reading its score (`qgv/scoring.py:30–33`). Its local weight is.20 (`qgv/factors.py:15`). All six remaining weights sum.80. The current reducer returns the accumulated numerator without division or redistribution (`qgv/scoring.py:48–57`).

| Factor | Registered weight | Score | Legacy numerator contribution | Hypothetical proven N/A excluded denominator |
|---|---:|---:|---:|---:|
| competitive_advantage | .20 | 70 | 14 | .20 |
| roic_wacc | .20 | 70 in fixture, unconsumed | 0 | 0 |
| market_position | .15 | 70 | 10.5 | .15 |
| fcf_quality | .15 | 70 | 10.5 | .15 |
| margin_quality | .10 | 70 | 7 | .10 |
| financial_health | .10 | 70 | 7 | .10 |
| management_quality | .10 | 70 | 7 | .10 |
| Total | 1.00 | — | **56** | **.80** |

- Legacy registered denominator1:56 /1 = **56**.
- Hypothetical specifically admitted N/A exclusion denominator.8:56 /.8 = **70**, delta+14.
- This preserves stored local weights but raises effective applicable weights by1/.8 =1.25; it is semantic redistribution, not display metadata.
- If ordinary market_position is also missing, numerator becomes56−10.5 =45.5. Approved M3 ordinary-missing principle retains the hypothetical planned denominator.8, giving **56.875**. An available-only denominator.65 would give70 and conceal the ordinary missing contribution; that candidate is rejected.

The original golden `financial_na_even_if_bad_roic` records a blocked ROIC observation (`golden_cases.json:1688–1707`), which the existing structural applicability branch never consumes. A preadmitted, explicitly out-of-scope observation can be distinguished from already consumed classification/shared-identity contamination. Future applicability must not read invalid evidence, call it N/A, and erase the admission failure. An unconsumed ROIC observation alone also cannot prove the financial classification.

M3 approves **permitted exclusion of proven N/A**, not automatic exclusion of all legacy financial bools. Domain predicate/admitted evidence, exclusion permission, calculation version and consumer comparison still require D3. The hypothetical70 is not applied to production, ranking or history.

## Minimum N/A authority recommendation

Reuse existing sidecar APPLICABLE / NOT_APPLICABLE / UNASSESSED and QualityState reasons. Add only pinned references already identified in Implementation Contract §§2–4:

| Authority component | Minimum bound evidence | Failure treatment candidate |
|---|---|---|
| Policy source / approval | Exact immutable applicability declaration, approval ref and supported domain scope | Missing rule = UNRESOLVED_APPLICABILITY, not company MISSING_DATA and not N/A |
| Subject and economic scope | Resolved company/security identity, profile classification source/effective interval, applicable period | Invalid identity/version = invalid admission in the affected scope |
| Predicate and method | Exact predicate definition/version/content identity and selected method/input contract | Missing method binding cannot manufacture a predicate |
| Predicate inputs | Original sources/vintages/stamps/locators, both time fields and explicit dependency use | Future/PIT/integrity failure cannot become N/A even at weight0 |
| Reproducible reason | Economic explanation and deterministic result from exact inputs/context | Data absence/insufficient history stays missing; contradiction/unassessed stays unresolved |
| Exclusion permission | Separate approved denominator-policy binding for this proof and method/version | Proven N/A without permission is not automatic denominator exclusion |

`PROVEN_NOT_APPLICABLE` is a **proof assessment description**, not a new runtime enum. Existing sidecar applicability state stays NOT_APPLICABLE with evidence refs; MISSING_EVIDENCE, UNRESOLVED_APPLICABILITY and INVALID_EVIDENCE remain reason/assessment distinctions. Missing→N/A, zero→N/A, caller profile→proof and numeric N/A→valid are rejected alternatives.

Technical recommendation for B2: **APPROVE_RECOMMENDED** for this evidence-and-permission authority boundary only. Actual industry predicate/issuer classification/exclusion adoption: **MORE_EVIDENCE_REQUIRED** and D3. Legacy compatibility: no change; proposed proof boundary changes future scoring/ranking admission, and future denominator exclusion requires parallel version migration. B1 requiredness follows method/input authority; B3 admits predicate evidence before B2 truth; B4 supplies selected-method identity. No evidence value or classification is inferred from weighting.
