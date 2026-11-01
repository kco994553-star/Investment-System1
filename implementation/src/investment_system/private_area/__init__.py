"""Private area (owner only, KIS) — pure code kept in the public repository (design
implementation/docs/private_area/PRIVATE_AREA_KIS_DESIGN_20261031.md, owner approval 2026-10-31).

Nothing in this package opens a network connection, reads a Secret or touches a file. The collector and the request
workflow run only in the private repository's Actions; public workflows never import this package
(tests/test_private_boundary_static.py).

- kis_routes: the one allow list of KIS routes (token issue / revoke and quotation only) and the refusal of order /
  trading / balance / account routes, shared by the request validator and the future collector (design §7).
- research_request: the `research-request/1` validator and `plan()` (design §20).
"""
