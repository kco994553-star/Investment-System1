"""The one KIS route allow list (design PRIVATE_AREA_KIS_DESIGN_20261031.md §3.2 '막는 경로', §7, §20.1).

Owner rules 2026-10-31: "KIS 주문·계좌·잔고 경로는 코드에서 막는다." "주문 기능은 구현·호출하지 않는다."

Only three routes exist: token issue, token revoke and the overseas period quote (daily bars, design §3.2 / §17.1). A route
is a method, a path on the KIS API host (the host is never named in this repository; the private collector adds it), a TR id
(None for the two token routes) and its exact parameter names. Order, trading, balance and account routes are not listed and
are never built. `require_route` refuses with a fixed code only, in this order:
1. ROUTE_SHAPE: not a descriptor {route, method, path, tr_id, params} of plain strings / a mapping;
2. ROUTE_FORBIDDEN_WORD: an order / trading / balance / account word (any case, inside longer words too) in the route name,
   path, parameter names or values — checked before the allow list, so even an allow-list edit cannot let one through;
3. ROUTE_FORBIDDEN_TR: a TR id of the order / balance families;
4. ROUTE_NOT_ALLOWED: a host, scheme or odd path, or anything that is not exactly one allow-listed route.
No network import, no I/O, no Secret: tests/test_research_request.py pins the imports.
"""
from __future__ import annotations

from collections.abc import Mapping
import re
from types import MappingProxyType

FORBIDDEN_ROUTE_WORDS = ("order", "trading", "balance", "account")
# KIS order / balance / account TR families: domestic and overseas (US: TTTT) stock orders, domestic futures / options orders
# (TTTO), balances and account inquiries, and their paper-trading twins (V...). The one source of the families: the route gate
# below and the Pages guard's KIS_TR_ID (tools/pages_artifact_guard.py keeps a literal copy, KIS_ORDER_TR_FAMILIES, because
# public workflows never import this package; tests/test_research_request.py asserts the two are equal).
ORDER_TR_FAMILIES = ("TTTC", "VTTC", "TTTS", "VTTS", "TTTT", "VTTT", "JTTT", "TTTO", "VTTO", "CTRP", "VTRP", "CTSC", "CTOS")
FORBIDDEN_TR_FAMILIES = re.compile(r"(?i)(?:" + "|".join(ORDER_TR_FAMILIES) + r")[0-9]{4}[A-Z]")
_PATH = re.compile(r"/[a-z0-9]+(?:[/-][A-Za-z0-9]+)*")

ROUTES = MappingProxyType({
    "TOKEN_ISSUE": MappingProxyType({"method": "POST", "path": "/oauth2/tokenP", "tr_id": None, "params": ()}),
    "TOKEN_REVOKE": MappingProxyType({"method": "POST", "path": "/oauth2/revokeP", "tr_id": None, "params": ()}),
    # Overseas period quote: GUBN 0 = daily, MODP 0 = raw / 1 = adjusted (cross-check only, design §17.1), up to 100 trading
    # days ending at BYMD per call; EXCD / SYMB come from the KIS master in the private collector (design §3.2).
    "OVERSEAS_DAILY_PRICE": MappingProxyType({
        "method": "GET", "path": "/uapi/overseas-price/v1/quotations/dailyprice", "tr_id": "HHDFS76240000",
        "params": ("AUTH", "EXCD", "SYMB", "GUBN", "BYMD", "MODP")}),
})


class KisRouteError(ValueError):
    """Fixed code only; never the refused path or value."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _words(descriptor: Mapping) -> str:
    params = descriptor["params"]
    parts = [descriptor["route"], descriptor["path"], *params, *(value for value in params.values())]
    return " ".join(part if isinstance(part, str) else repr(part) for part in parts).casefold()


def require_route(descriptor: Mapping) -> str:
    """Return the allow-listed route name of `descriptor`, or raise KisRouteError (see the module notes)."""
    if not isinstance(descriptor, Mapping) or not {"route", "method", "path", "tr_id", "params"} <= set(descriptor):
        raise KisRouteError("ROUTE_SHAPE")
    name, method, path, tr_id, params = (descriptor[k] for k in ("route", "method", "path", "tr_id", "params"))
    if type(name) is not str or type(method) is not str or type(path) is not str or not isinstance(params, Mapping) \
            or (tr_id is not None and type(tr_id) is not str):
        raise KisRouteError("ROUTE_SHAPE")
    if any(word in _words(descriptor) for word in FORBIDDEN_ROUTE_WORDS):
        raise KisRouteError("ROUTE_FORBIDDEN_WORD")
    if tr_id is not None and FORBIDDEN_TR_FAMILIES.search(tr_id):
        raise KisRouteError("ROUTE_FORBIDDEN_TR")
    if "://" in path or path.startswith("//") or not _PATH.fullmatch(path):
        raise KisRouteError("ROUTE_NOT_ALLOWED")
    allowed = ROUTES.get(name)
    if allowed is None or (method, path, tr_id) != (allowed["method"], allowed["path"], allowed["tr_id"]) \
            or tuple(params) != tuple(allowed["params"]):
        raise KisRouteError("ROUTE_NOT_ALLOWED")
    return name
