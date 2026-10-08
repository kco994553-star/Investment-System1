# Company Analysis Phase A Implementation Plan

Goal: implement the approved inactive Phase A contract as an isolated supplied-input display adapter and offline overview/detail/evidence preview.

Spec: Global c2dad0c1b09a89c5688d8253d53f8a137237bef8; CONTRACT blob6ffe3966b5191d70727a166822ff4bea54566c62; FIELD_CONTRACT blob3abd1b79e9cab5d1a7ab4bcbf84a8fbdecb6094e; OWNER_DELTA_ROUTES blob714d4039cddb87e82605200d8befb5aff214c741.

Global constraints: observed session only; five tasks; lease7200s; same-failure repair<=3; pre-publish RUN/own lease/exact parent; non-force API path. Existing owner files/source authority/scoring/thresholds/runtime routes remain unclaimed. Phase B/C deferred. Whole-repo reruns prohibited by user proportional-verification policy; new adapter boundary cases plus affected existing product checks and preview browser checks only.

1. Fresh-read exact Global/scoped states; record CDR033 grant and own bounded claim. Verify Main idle/null, Chart NONE, QGV operational null, Platform null. MissingData qgv-b47-muupb538 preserved. New module/test/preview paths absent and candidate branch absent.
2. RED→GREEN: implement price_position(payload:dict)->dict and period_summary(payload:dict)->dict in new product/company_price_context_v1.py, tested by new tests/test_company_price_context_v1.py. Pure supplied-input validation, Decimal display outputs, same security/currency/series/basis/receipt/time authority; explicit historical ATH/lifetime and52W/window; future/unavailable data clears values. Completed full-period roster must match rows, include Flat in denominator and exclude QTD/YTD/partial IPO. Unknown/missing complete return and empty denominator fail unavailable.
3. New preview/**: index.html, detail.html, evidence.html, preview.css, preview.js, sample.json and renderer/verification helpers as needed. Ten approved overview sections; independent axes; baseline bars and internal drill-down; synthetic-only examples; missing profiles/news/revisions/reference calibration stay unavailable. Reuse existing render_app visual tokens/cards/nav references without changing/calling old output generator or connecting production routes. Preview consumes adapter-projected sample fields; one calculation authority.
4. Run targeted adapter/affected product checks, static link/provenance boundary checks and local browser UI at mobile+desktop. Independent context-free whole-branch review with exact input/contract; fix concrete findings in<=3 same-failure rounds. No D3-A runtime/cross-Work activation.
5. Record verification/source hashes/limits/rollback; scoped API publication with local tree equality, explicit native-commit identity and remote byte readback. Global append-only receipt/handoff; restore READ_ONLY, own lease null/runtimeIDLE, retain all owner/history state. Re-evaluate pending lanes and update next candidate; no gate closure inferred.

Review focus: unmatched price operand identities; malicious/nonfinite data; partial/unknown completed-period roster; future availability versus decision time; preview stale retained values and injection/navigation errors.

Pre-flight interfaces: Task2 produces validated display dicts consumed by Task3 sample renderer; sample schema fixed before preview generation. Task4 verifies this exact assembly; Task5 pins source/verification objects and releases only this cycle token.
