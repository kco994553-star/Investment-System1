# Company Analysis Phase A — offline candidate

This is a synthetic supplied-input display candidate for the approved QGV Company Analysis UI/UX Extension v1.1 and Historical Price Context Contract v1.0. It is not attached to a product route or provider. References are validated as declared inputs, not authenticated or admitted as authoritative sources.

Open `index.html` for Overview → Detail → Evidence. Price and return calculations come from `company_price_context_v1.py`; generated sample data carries input, adapter and exact contract hashes. Full Technical Chart remains an explicit unassembled destination. No real company/news/consensus/QGV result is invented.

| Phase A requirement | Candidate result | Remaining acceptance |
|---|---|---|
| Investment Type / GICS / Strategy Theme independence | Three independent cards; separate Overlap projection; primary/secondary/profile fields preserved in exact input contract | Taxonomy assignments and approved Type profile inputs |
| Price position / ATH / 52-week high | Decimal adapter with same identity, currency, series, adjustment basis, action receipt and snapshot; explicit lifetime/window coverage declarations | Authentication of sources and coverage/window authority |
| Quarterly / Annual positive summaries | Full completed roster, Flat in denominator, QTD/YTD/partial IPO excluded; unknown completed return invalidates whole summary | Admitted calendar, full-period roster and price-return inputs |
| Overview → Detail → Evidence | Ten sections, baseline bars, period links, local evidence, thesis recheck | Accepted owner write-set and actual product route assembly |
| News / Consensus / QGV / business | Explicit unavailable placeholders; no invented revisions, scores or weights | Existing owner outputs and contracts |
| Drawdown bands / episodes / peers / recovery | Inactive reference candidates and deferred B/C scope | Separate protected numeric/calibration decisions where applicable |

The new adapter, test and preview are Main's D1/D2 scope on `main/company-analysis-phase-a-v1`. Allowed files are this `preview/**`, `implementation/src/investment_system/product/company_price_context_v1.py` and `implementation/tests/test_company_price_context_v1.py`. Existing Chart, QGV, Platform, Web, P01 and FPIA owner paths are preserved. No new D3-A runtime/cross-Work activation is claimed.

The parser's 128-digit/exponent resource budget prevents unbounded fixed-point serialization. It does not define a drawdown, inclusion, scoring or trading threshold. Supplied metadata is deliberately conservative: all price extrema share the explicit snapshot; calendar/full-period status is never guessed. UI percentages use one decimal for display only, with the underlying Decimal projection available in Evidence.

Rebuild and verify from this directory:

```sh
python3 build_preview.py
python3 verify_preview.py
BROWSER_EXECUTABLE_PATH=/path/to/existing/chromium node browser_verify.js
```

For adapter checks, run the new test file and the affected existing product strategy test from `implementation` with `src` on `PYTHONPATH`. No whole-repository rerun is required for this isolated candidate.

Recovery: a normal descendant correction or removal of these new candidate paths. Do not rewrite history or change source admission, owner scopes, production routes or old evidence.
