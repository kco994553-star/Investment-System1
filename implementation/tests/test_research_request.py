"""research-request/1 validator, plan() and the KIS route allow list (design PRIVATE_AREA_KIS_DESIGN_20261031.md §20, §20.1).

Synthetic requests only; no network, no Secret, no file outside pytest's tmp. KIS TR ids and e-mail canaries are assembled at
run time so this file carries no marker (tests/test_private_boundary_static.py scans every tracked file).
"""
import ast
import copy
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys

import pytest

from investment_system.private_area import kis_routes
from investment_system.private_area import research_request as rr
from investment_system.private_area.kis_routes import KisRouteError, require_route
from investment_system.private_area.research_request import ResearchRequestError, parse_request, plan, validate_request

TODAY = dt.date(2026, 10, 31)
PACKAGE = Path(rr.__file__).resolve().parent
QUOTE_TR = 'HHDFS' + '76240000'


def base():
    return {"schema": "research-request/1", "request_id": "rr-20261031-momentum-12m", "symbols": ["AAPL", "BRK.B", "MSFT"],
            "period": {"start": "2016-01-04", "end": "2025-12-31"}, "items": ["daily_raw", "volume"], "frequency": "once",
            "purpose": "momentum backtest on real closes"}


def refused(value, code, today=TODAY):
    with pytest.raises(ResearchRequestError) as caught:
        validate_request(value, today=today)
    assert caught.value.code == code and str(caught.value) == code
    return caught.value


def with_(**changes):
    value = base()
    for key, child in changes.items():
        value[key] = child
    return value


# ---- valid requests --------------------------------------------------------------------------------------------------
def test_valid_request_round_trips_and_is_immutable():
    request = validate_request(base(), today=TODAY)
    assert request.as_dict() == base()
    assert request.symbols == ("AAPL", "BRK.B", "MSFT") and request.start == dt.date(2016, 1, 4)
    with pytest.raises(Exception):
        request.purpose = "changed"
    assert parse_request(json.dumps(base(), indent=2).encode(), today=TODAY) == request


def test_items_are_kept_in_canonical_order():
    request = validate_request(with_(items=["dollar_volume", "daily_adjusted_crosscheck", "daily_raw"]), today=TODAY)
    assert request.items == ("daily_raw", "daily_adjusted_crosscheck", "dollar_volume")


def test_limits_are_inclusive():
    symbols = ["S" + "".join(chr(65 + (i // 26 ** k) % 26) for k in range(3)) for i in range(rr.MAX_SYMBOLS)]
    assert len(set(symbols)) == rr.MAX_SYMBOLS
    start = dt.date(2015, 10, 31)
    value = with_(symbols=symbols, period={"start": start.isoformat(),
                                           "end": (start + dt.timedelta(days=rr.MAX_PERIOD_DAYS)).isoformat()},
                  purpose="ab" + " ab" * 39 + "c")
    assert len(value["purpose"]) == rr.PURPOSE_MAX_CHARS
    validate_request(value, today=TODAY)
    validate_request(with_(period={"start": rr.MIN_START.isoformat(), "end": "2009-12-31"}), today=TODAY)
    validate_request(with_(period={"start": "2026-10-31", "end": "2026-10-31"}, request_id="rr-20261031-same-day"), today=TODAY)
    ahead = (TODAY + dt.timedelta(days=rr.DAILY_MAX_AHEAD_DAYS)).isoformat()
    validate_request(with_(frequency="daily", period={"start": "2026-01-02", "end": ahead}), today=TODAY)
    assert len(json.dumps(value).encode()) <= rr.MAX_REQUEST_BYTES


# ---- shape -----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("value", [None, [], "x", 1, True])
def test_non_object_is_refused(value):
    refused(value, "NOT_AN_OBJECT")


def test_unknown_or_missing_keys_are_refused_at_every_level():
    extra = base()
    extra["note"] = "x"
    refused(extra, "UNKNOWN_OR_MISSING_KEY")
    for key in rr.KEYS:
        missing = base()
        del missing[key]
        refused(missing, "UNKNOWN_OR_MISSING_KEY")
    refused(with_(period={"start": "2016-01-04", "end": "2025-12-31", "step": "1d"}), "UNKNOWN_OR_MISSING_KEY")
    refused(with_(period={"start": "2016-01-04"}), "UNKNOWN_OR_MISSING_KEY")
    refused(with_(period=["2016-01-04", "2025-12-31"]), "UNKNOWN_OR_MISSING_KEY")


@pytest.mark.parametrize("schema", ["research-request/2", "Research-Request/1", "", None, ["research-request/1"]])
def test_schema_must_be_exact(schema):
    refused(with_(schema=schema), "SCHEMA_INVALID")


@pytest.mark.parametrize("request_id", [
    "rr-20261031", "rr-20261031-", "rr-20261031-Upper", "rr-20261031-a_b", "rr-20261031-a--b", "rr-20261031-a/b",
    "rr-20261031-..", "RR-20261031-a", "legacy", "rr-2026103-a", "rr-20261332-a", "rr-20260230-a", " rr-20261031-a",
    "rr-20261031-" + "a" * 53, 20261031, None])
def test_request_id_pattern(request_id):
    refused(with_(request_id=request_id), "REQUEST_ID_INVALID")


def test_request_id_date_is_not_after_today():
    refused(with_(request_id="rr-20261101-early"), "REQUEST_ID_INVALID")
    validate_request(with_(request_id="rr-20261101-early"), today=dt.date(2026, 11, 1))


@pytest.mark.parametrize("symbols,code", [
    ([], "SYMBOLS_COUNT"), ("AAPL", "SYMBOLS_COUNT"), ({"AAPL": 1}, "SYMBOLS_COUNT"),
    (["aapl"], "SYMBOL_INVALID"), (["AAPLXX"], "SYMBOL_INVALID"), (["BRK/B"], "SYMBOL_INVALID"), (["BRK.ABC"], "SYMBOL_INVALID"),
    (["NYSE:ABT"], "SYMBOL_INVALID"), (["005930"], "SYMBOL_INVALID"), ([""], "SYMBOL_INVALID"), ([1], "SYMBOL_INVALID"),
    ([["AAPL"]], "SYMBOL_INVALID"), (["AAPL "], "SYMBOL_INVALID"), (["AAPL", "AAPL"], "SYMBOL_DUPLICATE")])
def test_symbols(symbols, code):
    refused(with_(symbols=symbols), code)


def test_too_many_symbols():
    symbols = ["S" + "".join(chr(65 + (i // 26 ** k) % 26) for k in range(3)) for i in range(rr.MAX_SYMBOLS + 1)]
    refused(with_(symbols=symbols), "SYMBOLS_COUNT")


@pytest.mark.parametrize("period,code", [
    ({"start": "2016-1-4", "end": "2025-12-31"}, "PERIOD_INVALID"),
    ({"start": "20160104", "end": "2025-12-31"}, "PERIOD_INVALID"),
    ({"start": "2016-02-30", "end": "2025-12-31"}, "PERIOD_INVALID"),
    ({"start": "2016-01-04T00:00", "end": "2025-12-31"}, "PERIOD_INVALID"),
    ({"start": None, "end": "2025-12-31"}, "PERIOD_INVALID"),
    ({"start": "1999-12-31", "end": "2025-12-31"}, "PERIOD_BOUNDS"),
    ({"start": "2025-12-31", "end": "2016-01-04"}, "PERIOD_BOUNDS"),
    ({"start": "2015-01-01", "end": "2025-01-02"}, "PERIOD_TOO_LONG"),
    ({"start": "2020-01-02", "end": "2026-11-01"}, "PERIOD_BOUNDS"),      # once: end after today
    ({"start": "2026-11-01", "end": "2026-11-02"}, "PERIOD_BOUNDS")])     # start after today
def test_period(period, code):
    refused(with_(period=period), code)


def test_daily_request_ends_within_its_window():
    late = (TODAY + dt.timedelta(days=rr.DAILY_MAX_AHEAD_DAYS + 1)).isoformat()
    refused(with_(frequency="daily", period={"start": "2026-01-02", "end": late}), "PERIOD_BOUNDS")


@pytest.mark.parametrize("items", [[], ["daily_raw", "daily_raw"], ["intraday"], ["DAILY_RAW"], "daily_raw", [None],
                                   [["volume"]], ["volume", {"x": 1}], ["minute_bars"]])
def test_items(items):
    refused(with_(items=items), "ITEMS_INVALID")


@pytest.mark.parametrize("frequency", ["weekly", "ONCE", "", None, ["once"]])
def test_frequency(frequency):
    refused(with_(frequency=frequency), "FREQUENCY_INVALID")


@pytest.mark.parametrize("purpose", [
    "", "   ", " leading space", "x" * (rr.PURPOSE_MAX_CHARS + 1), "two\nlines", "tab\there", "zero\u200bwidth",
    "bidi\u202eflip", "see https://example.invalid/x", "see www.example.invalid", "see example.com docs",
    "mail " + "someone" + "@" + "example.invalid", "a @ sign", "number-like 12345678 here", "id 1234567890",
    "key AbCd1234EfGh5678", "token " + "Q" * 24, "base64 abcd+efgh/ijkl=mnop0", None, 7, ["x"]])
def test_purpose(purpose):
    refused(with_(purpose=purpose), "PURPOSE_INVALID")


@pytest.mark.parametrize("purpose", ["momentum backtest on real closes", "12-1 모멘텀 백테스트 (2016~2025)",
                                     "volume spike study, 252-day window", "twelve-month-momentum check"])
def test_ordinary_purposes_pass(purpose):
    validate_request(with_(purpose=purpose), today=TODAY)


# ---- order / trading / balance / account words anywhere ---------------------------------------------------------------
@pytest.mark.parametrize("change", [
    {"purpose": "order flow study"}, {"purpose": "ORDER imbalance"}, {"purpose": "reorder check"},
    {"purpose": "trading days only"}, {"purpose": "rebalance monthly"}, {"purpose": "account level view"},
    {"purpose": "계좌 잔고 확인"}, {"purpose": "주문 테스트"}, {"purpose": "매매 신호"}, {"purpose": "\uff4f\uff52\uff44\uff45\uff52 fullwidth"},
    {"request_id": "rr-20261031-order-flow"}, {"request_id": "rr-20261031-balance"}, {"symbols": ["ORDER"]},
    {"period": {"start": "2016-01-04", "end": "2025-12-31", "account": "x"}}, {"account_no": "x"},
    {"items": ["daily_raw", "trading"]}, {"frequency": "order"}])
def test_forbidden_words_are_refused_anywhere(change):
    value = base()
    value.update(change)
    refused(value, "FORBIDDEN_WORD")


# ---- bytes -----------------------------------------------------------------------------------------------------------
def test_size_limit_applies_before_parsing():
    raw = json.dumps(base()).encode()
    padded = raw[:-1] + b" " * (rr.MAX_REQUEST_BYTES - len(raw)) + b"}"
    assert len(padded) == rr.MAX_REQUEST_BYTES
    parse_request(padded, today=TODAY)
    for blob in (padded + b" ", b"[" * (rr.MAX_REQUEST_BYTES + 1)):
        with pytest.raises(ResearchRequestError) as caught:
            parse_request(blob, today=TODAY)
        assert caught.value.code == "REQUEST_TOO_LARGE"


@pytest.mark.parametrize("raw,code", [
    (b"", "INVALID_JSON"), (b"not json", "INVALID_JSON"), (b"\xff\xfe{}", "INVALID_JSON"), ("\ufeff{}".encode(), "INVALID_JSON"),
    (b'{"schema": NaN}', "INVALID_JSON"), (b'{"schema": -Infinity}', "INVALID_JSON"),
    (b'{"schema": "research-request/1", "schema": "research-request/1"}', "INVALID_JSON"),
    (b"[" * 5000 + b"]" * 5000, "NOT_AN_OBJECT"), (b"[]", "NOT_AN_OBJECT")],
    ids=["empty", "text", "utf16", "bom", "nan", "infinity", "duplicate", "deep-list", "list"])
def test_invalid_json_is_refused(raw, code):
    with pytest.raises(ResearchRequestError) as caught:
        parse_request(raw, today=TODAY)
    assert caught.value.code == code


@pytest.mark.parametrize("raw", ["text", bytearray(b"{}"), None])
def test_parse_needs_bytes(raw):
    with pytest.raises(ResearchRequestError) as caught:
        parse_request(raw, today=TODAY)
    assert caught.value.code == "NOT_BYTES"


@pytest.mark.parametrize("today", [None, "2026-10-31", dt.datetime(2026, 10, 31)])
def test_today_must_be_a_date(today):
    refused(base(), "TODAY_INVALID", today=today)


def test_errors_never_echo_the_request():
    canary = "SYNTHETIC" + "CANARY" + "99123"
    for change in ({"purpose": canary + " https://example.invalid"}, {"request_id": canary}, {"symbols": [canary]},
                   {"purpose": canary + " account"}):
        value = base()
        value.update(change)
        with pytest.raises(ResearchRequestError) as caught:
            validate_request(value, today=TODAY)
        assert canary not in str(caught.value) and canary not in repr(caught.value.args)


# ---- plan --------------------------------------------------------------------------------------------------------------
def test_plan_is_token_issue_quotes_token_revoke_with_no_host():
    request = validate_request(with_(items=["volume", "daily_adjusted_crosscheck", "dollar_volume"]), today=TODAY)
    calls = plan(request)
    assert [c["route"] for c in calls] == ["TOKEN_ISSUE"] + ["OVERSEAS_DAILY_PRICE"] * 6 + ["TOKEN_REVOKE"]
    assert calls[0] == {"route": "TOKEN_ISSUE", "method": "POST", "path": "/oauth2/tokenP", "tr_id": None, "params": {}}
    assert calls[-1] == {"route": "TOKEN_REVOKE", "method": "POST", "path": "/oauth2/revokeP", "tr_id": None, "params": {}}
    quotes = calls[1:-1]
    assert [(c["symbol"], c["series"]) for c in quotes] == [
        (s, series) for s in ("AAPL", "BRK.B", "MSFT") for series in ("RAW", "ADJUSTED_CROSSCHECK")]
    raw, adjusted = quotes[0], quotes[1]
    assert raw["tr_id"] == adjusted["tr_id"] == QUOTE_TR
    assert raw["method"] == "GET" and raw["path"] == "/uapi/overseas-price/v1/quotations/dailyprice"
    assert raw["params"] == {"AUTH": "", "EXCD": "{EXCD}", "SYMB": "{SYMB}", "GUBN": "0", "BYMD": "{BYMD}", "MODP": "0"}
    assert adjusted["params"]["MODP"] == "1"
    assert raw["items"] == ["volume", "dollar_volume"] and adjusted["items"] == ["daily_adjusted_crosscheck"]
    assert raw["window"] == {"start": "2016-01-04", "end": "2025-12-31"} and raw["frequency"] == "once"
    text = json.dumps(calls)
    assert "://" not in text and "korea" not in text.casefold() and "appkey" not in text.casefold()
    assert all(require_route(c) == c["route"] for c in calls)


@pytest.mark.parametrize("items,series", [
    (["daily_raw"], ["RAW"]), (["volume"], ["RAW"]), (["dollar_volume"], ["RAW"]),
    (["daily_adjusted_crosscheck"], ["ADJUSTED_CROSSCHECK"]),
    (["daily_raw", "daily_adjusted_crosscheck"], ["RAW", "ADJUSTED_CROSSCHECK"])])
def test_adjusted_series_only_when_asked(items, series):
    calls = plan(validate_request(with_(items=items, symbols=["AAPL"]), today=TODAY))
    assert [c["series"] for c in calls[1:-1]] == series


def test_plan_needs_a_validated_request():
    for value in (base(), None, "rr-20261031-x"):
        with pytest.raises(ResearchRequestError) as caught:
            plan(value)
        assert caught.value.code == "PLAN_NEEDS_VALIDATED_REQUEST"
    # Building the dataclass directly still runs every date-free check.
    with pytest.raises(ResearchRequestError):
        rr.ResearchRequest(request_id="rr-20261031-x", symbols=("AAPL",), start=dt.date(2016, 1, 4), end=dt.date(2025, 12, 31),
                           items=("daily_raw",), frequency="once", purpose="monthly rebalance")


# ---- the route allow list ------------------------------------------------------------------------------------------------
def test_allow_list_is_token_issue_revoke_and_one_quotation_route():
    assert set(kis_routes.ROUTES) == {"TOKEN_ISSUE", "TOKEN_REVOKE", "OVERSEAS_DAILY_PRICE"}
    assert [r["tr_id"] for r in kis_routes.ROUTES.values()] == [None, None, QUOTE_TR]
    with pytest.raises(TypeError):
        kis_routes.ROUTES["X"] = {}
    for route in kis_routes.ROUTES.values():
        assert not any(word in route["path"].casefold() for word in kis_routes.FORBIDDEN_ROUTE_WORDS)


def quote_descriptor(**changes):
    descriptor = copy.deepcopy(plan(validate_request(with_(symbols=["AAPL"]), today=TODAY))[1])
    descriptor.update(changes)
    return descriptor


ORDER_PATHS = ("/uapi/overseas-stock/v1/trading/order", "/uapi/domestic-stock/v1/trading/order-cash",
               "/uapi/domestic-stock/v1/trading/inquire-balance", "/uapi/overseas-stock/v1/trading/inquire-present-balance",
               "/uapi/domestic-stock/v1/trading/inquire-account-balance", "/uapi/overseas-stock/v1/Trading/ORDER-rvsecncl")


@pytest.mark.parametrize("path", ORDER_PATHS)
def test_order_trading_balance_account_paths_are_refused(path):
    with pytest.raises(KisRouteError) as caught:
        require_route(quote_descriptor(path=path))
    assert caught.value.code == "ROUTE_FORBIDDEN_WORD" and path not in str(caught.value)


@pytest.mark.parametrize("path", ORDER_PATHS)
def test_word_refusal_holds_even_if_the_allow_list_is_edited(monkeypatch, path):
    quote = quote_descriptor(path=path)
    edited = dict(kis_routes.ROUTES)
    edited["OVERSEAS_DAILY_PRICE"] = dict(edited["OVERSEAS_DAILY_PRICE"], path=path)
    edited["ORDER"] = {"method": "POST", "path": path, "tr_id": None, "params": ()}
    monkeypatch.setattr(kis_routes, "ROUTES", edited)
    with pytest.raises(KisRouteError) as caught:
        plan(validate_request(with_(symbols=["AAPL"]), today=TODAY))   # plan() itself re-checks every descriptor
    assert caught.value.code == "ROUTE_FORBIDDEN_WORD"
    for descriptor in (quote,
                       {"route": "ORDER", "method": "POST", "path": path, "tr_id": None, "params": {}}):
        with pytest.raises(KisRouteError) as caught:
            require_route(descriptor)
        assert caught.value.code == "ROUTE_FORBIDDEN_WORD"


@pytest.mark.parametrize("tr_id", ["TTTC" + "0802U", "VTTC" + "0802U", "JTTT" + "1002U", "TTTS" + "3012R", "CTRP" + "6504R",
                                   "VTRP" + "6504R", "tttc" + "0801u"])
def test_order_and_balance_tr_ids_are_refused(tr_id):
    with pytest.raises(KisRouteError) as caught:
        require_route(quote_descriptor(tr_id=tr_id))
    assert caught.value.code == "ROUTE_FORBIDDEN_TR"


@pytest.mark.parametrize("changes", [
    {"path": "/uapi/overseas-price/v1/quotations/price"}, {"path": "/uapi/overseas-price/v1/quotations/dailyprice/"},
    {"path": "https://example.invalid/uapi/overseas-price/v1/quotations/dailyprice"},
    {"path": "//example.invalid/uapi/overseas-price/v1/quotations/dailyprice"},
    {"path": "/uapi/overseas-price/v1/quotations/dailyprice?x=1"}, {"path": "/uapi/../oauth2/tokenP"},
    {"method": "POST"}, {"tr_id": "HHDFS" + "76950200"}, {"tr_id": None}, {"route": "TOKEN_ISSUE"}, {"route": "UNKNOWN"},
    {"params": {"AUTH": "", "EXCD": "{EXCD}", "SYMB": "{SYMB}", "GUBN": "0", "BYMD": "{BYMD}"}},
    {"params": {"AUTH": "", "EXCD": "{EXCD}", "SYMB": "{SYMB}", "GUBN": "0", "BYMD": "{BYMD}", "MODP": "0", "KEYB": ""}}])
def test_anything_but_an_exact_allow_listed_route_is_refused(changes):
    with pytest.raises(KisRouteError) as caught:
        require_route(quote_descriptor(**changes))
    assert caught.value.code == "ROUTE_NOT_ALLOWED"


@pytest.mark.parametrize("descriptor", [None, [], {"route": "TOKEN_ISSUE"}, quote_descriptor(path=None),
                                        quote_descriptor(params=["AUTH"]), quote_descriptor(tr_id=76240000),
                                        quote_descriptor(route=1)])
def test_malformed_descriptors_are_refused(descriptor):
    with pytest.raises(KisRouteError) as caught:
        require_route(descriptor)
    assert caught.value.code == "ROUTE_SHAPE"


def test_parameter_words_are_checked_too():
    for params in ({"AUTH": "", "EXCD": "{EXCD}", "SYMB": "{SYMB}", "GUBN": "0", "BYMD": "{BYMD}", "MODP": "0", "ACCOUNT": "x"},
                   {"AUTH": "", "EXCD": "{EXCD}", "SYMB": "order", "GUBN": "0", "BYMD": "{BYMD}", "MODP": "0"}):
        with pytest.raises(KisRouteError) as caught:
            require_route(quote_descriptor(params=params))
        assert caught.value.code == "ROUTE_FORBIDDEN_WORD"


# ---- purity ----------------------------------------------------------------------------------------------------------------
ALLOWED_IMPORTS = {"__future__", "collections", "dataclasses", "datetime", "json", "re", "types", "unicodedata"}


@pytest.mark.parametrize("name", ["__init__.py", "kis_routes.py", "research_request.py"])
def test_modules_import_no_network_file_or_process_library(name):
    tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            assert node.module in {None, "kis_routes"} and all(a.name == "kis_routes" for a in node.names)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "eval", "exec", "compile", "__import__", "input"}, node.func.id
    assert imported <= ALLOWED_IMPORTS, imported - ALLOWED_IMPORTS
    text = (PACKAGE / name).read_text(encoding="utf-8").casefold()
    assert "requests" not in imported and "urllib" not in text and "socket" not in text and "korea" + "investment" not in text


def test_importing_the_package_loads_no_network_module():
    code = ("import sys; import investment_system.private_area.research_request; "
            "print(sorted(m for m in sys.modules if m.split('.')[0] in "
            "{'socket', 'ssl', 'http', 'urllib', 'urllib3', 'requests', 'httpx', 'aiohttp', 'subprocess'}))")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                            env={"PYTHONPATH": str(PACKAGE.parents[1])})
    assert result.stdout.strip() == "[]"
