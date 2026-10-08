# CI compatibility repair

Subject before repair: `f21e254c45c8bd29bd9c6801ed5982bf38e52bf6`, PR #67.

The first GitHub execution passed repository-guard, web-research-guard and
web-state-presentation. Two full regression workflows failed:

- [web-mvp-validation run 37861099505](https://github.com/kco994553-star/Investment-System1/actions/runs/37861099505): ten failed checks, 658 passed and 90 passed subtests.
- [qgv-common-contract-vnext run 37861099469](https://github.com/kco994553-star/Investment-System1/actions/runs/37861099469): nine failed checks, 659 passed and 90 passed subtests.

Both used the default shallow checkout. Chart receipt diagnostics authenticate
historical source pins with `git show <exact commit>:<path>`, including
`a89ac6dd4336027ddab52b145ab87e3bc5edb3e5`. Missing Git objects cause
`PINNED_BASELINE_UNAVAILABLE` and `SOURCE_PIN_UNRESOLVED`, followed by the
intended fail-closed INVALID result. A separate depth-one clone of the exact
remote candidate reproduced the same nine failures. Fetching its complete
history made those same tests pass without changing any test or source pin.
Both affected workflows now specify `fetch-depth: 0`.

Web also used Python 3.11 while the adopted QGV immutable AST hash tests and
QGV workflow use Python 3.12. Python 3.12 adds `FunctionDef.type_params` to the
AST representation. Removing only that field from the 3.12 representation
reproduced the exact 3.11 hash reported by GitHub:

| Shape | `_clip_score` AST SHA256 |
| --- | --- |
| Python 3.12, adopted golden | `d3d7ac1572b6e29301245d5ccbb7e90387e25cbd3e25b236ff51ad99b78392f6` |
| Python 3.11 field shape, GitHub failure | `d44aacba7480320cc68b4c5f8bdaa1fd2bcb9bd139fa5403fcf5fcad101f47c8` |

Web now uses Python 3.12. All numeric goldens, scoring code, historical source
pins and failure behavior are preserved. This is a CI execution compatibility
repair within the authorized integration work; it changes no investment rule,
mode, publication authority or automation scope. The earlier missing-jsonschema
dependency repair is recorded in CANDIDATE_MANIFEST.json.

Final GitHub run links and independent exact-commit verification are recorded
in PR #67 after publication. Earlier local green results cannot substitute for
the final GitHub runs.
