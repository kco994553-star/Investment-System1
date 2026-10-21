"""Public `macro-evidence.json` (schema macro-evidence/1): observations, release times, revision history and evidence
lines of the MEV-1 P1 candidate set (13 indicators, evidence_sources.INDICATORS).

Exploration only (MEV-10): `scope.official_judgement`, `scope.probability` and `scope.macro_gate` are always false and
nothing in the engines reads this file. Rules are the catalog's candidate rules ("v0 · 미검증"); interpretations are
"해석 후보 · 미승인". Market-price-based series never appear here (B-PRICE: device RAM only).

Release time (MEV-9, catalog §9):
- a record's time is the source's own posting time when the response carries one that falls between the previous and
  this collection (HTTP Last-Modified of the posted file), otherwise this collection time, labelled COLLECTION_TIME;
  a source release *date* without a time is kept beside it (`rd`) and never replaces it;
- conditions over several observations hold only once the last needed observation was released (rules run on the
  vintage of each run, so a 3-month condition is recorded when the third observation arrives);
- append only: a recorded first release, revision or event is never moved, changed or removed. A revision appends a
  version; the value seen before stays (BASELINE when it predates the series' first collection);
- no back-filling: the first collection of a series is its baseline (no release record, no event). Events computed
  over the current (revised) vintage go to `replay_events` (재구성 층, 수정치 기준), rebuilt each run, never mixed with
  the real-time `events`.

Pure: no network, clock or environment. `tools/macro_evidence.py` collects and carries the previous Pages copy forward.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import re

from . import evidence_sources as es

FILENAME = "macro-evidence.json"
SCHEMA = "macro-evidence/1"
KIND = "MACRO_EVIDENCE_LINES"
MAX_BYTES = 2 * 1024 * 1024
SIZE_BUDGET = 1_800_000
WINDOW = {"W": 312, "M": 144, "Q": 60, "E": 120}
STALE_PERIODS = {"W": timedelta(days=14), "M": timedelta(days=62), "Q": timedelta(days=184)}
PUBLICATION_LAG = {"W": timedelta(days=7), "M": timedelta(days=45), "Q": timedelta(days=100)}
LABELS = {"interpretation": "해석 후보 · 미승인", "rule": "v0 · 미검증", "replay": "재구성 · 현재 빈티지(수정치) 기준 · 발표 시각 아님",
          "collection_time": "수집 시각 기준", "scope": "탐색 화면 전용 · 공식 판정·확률·매크로 게이트에 쓰지 않음 (MEV-10)",
          "summary": "현재 유효 후보 정의(EVL-1) · 미승인", "market_price": "가격 기반 시장 근거선은 기기 전용(B-PRICE) · 공개 없음"}
SCOPE = {"screen": "EXPLORATION_ONLY", "official_judgement": False, "probability": False, "macro_gate": False, "decision": "MEV-10"}
STATES = ("LIVE", "PARTIAL", "NOT_AVAILABLE")
PREVIOUS = ("LOADED", "NO_LIVE", "UNAVAILABLE", "NOT_COLLECTED")
CONTINUITY = ("CONTINUOUS", "BASELINE", "RESET_PREVIOUS_UNAVAILABLE", "NOT_COLLECTED")
BASES = ("SOURCE_LAST_MODIFIED", "COLLECTION_TIME", "BASELINE")
RECORD_KINDS = ("FIRST", "REVISION")
VERSION_KINDS = ("BASELINE", "FIRST", "REVISION")
EVENT_KINDS = ("EDGE", "REVISION_CLEARED", "AGENCY_EVENT")
EPS = 1e-9


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso(text: str) -> datetime:
    if type(text) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", text):
        raise ValueError("MACRO_EVIDENCE_TIME")
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


# ---------------------------------------------------------------- periods

def period_index(period: str, frequency: str) -> int:
    if frequency == "M":
        return int(period[:4]) * 12 + int(period[5:7]) - 1
    if frequency == "Q":
        return int(period[:4]) * 4 + int(period[5]) - 1
    return date.fromisoformat(period).toordinal() // 7 if frequency == "W" else date.fromisoformat(period).toordinal()


def period_end(period: str, frequency: str) -> datetime:
    """End of the reference period (UTC midnight after it) - used only for freshness, never as a release time."""
    if frequency == "M":
        y, m = int(period[:4]), int(period[5:7])
        return datetime(y + m // 12, m % 12 + 1, 1, tzinfo=timezone.utc)
    if frequency == "Q":
        y, q = int(period[:4]), int(period[5])
        return datetime(y + q // 4, (q % 4) * 3 + 1, 1, tzinfo=timezone.utc)
    return datetime.fromisoformat(period).replace(tzinfo=timezone.utc) + timedelta(days=1)


_PERIOD = {"W": r"\d{4}-\d{2}-\d{2}", "E": r"\d{4}-\d{2}-\d{2}", "M": r"\d{4}-(0[1-9]|1[0-2])", "Q": r"\d{4}Q[1-4]"}


def valid_period(period, frequency) -> bool:
    if type(period) is not str or not re.fullmatch(_PERIOD[frequency], period):
        return False
    if frequency in ("W", "E"):
        try:
            date.fromisoformat(period)
        except ValueError:
            return False
    return True


# ---------------------------------------------------------------- candidate rules (catalog §5-1, v0 · 미검증)

def _sign(x: float):
    return "up" if x > EPS else "down" if x < -EPS else None


def _mean(values):
    return None if any(v is None for v in values) else sum(values) / len(values)


def rule_states(indicator: str, rows: list, frequency: str) -> list:
    """[(period, state)] over a series (sorted [(period, value)]): the rule's state after each computable period.
    State 'up'/'down' (a sign side) or 'clear' (one-sided conditions E09/E13 not met). Zero keeps the previous state."""
    at = {period_index(p, frequency): v for p, v in rows}
    get = lambda i: at.get(i)
    out, state = [], None

    def avg(i, n):
        return _mean([get(i - k) for k in range(n)])

    for period, value in rows:
        i, new = period_index(period, frequency), None
        if indicator == "E09":
            new = "down" if value < 0 else "clear"
        elif indicator == "E13":
            a = avg(i, 3)
            lows = [avg(i - k, 3) for k in range(1, 13)]
            if a is not None and None not in lows:
                new = "down" if a - min(lows) >= 0.5 - EPS else "clear"
            else:
                continue
        elif indicator in ("E25", "E36"):
            new = _sign(value) or state
        elif indicator == "E14":
            a4, a26 = avg(i, 4), avg(i, 26)
            if a4 is None or a26 is None:
                continue
            new = _sign(a4 - a26) or state
        elif indicator in ("E16", "E22"):
            base = get(i - (6 if indicator == "E16" else 12))
            if base is None:
                continue
            new = _sign(value - base) or state
        elif indicator in ("E17", "E21", "E26"):
            lag = 6 if indicator == "E26" else 12
            a, b = avg(i, 3), avg(i - lag, 3)
            if a is None or b is None:
                continue
            new = _sign(a - b) or state
        elif indicator == "E39":
            signs = []
            for k in range(3):
                x, x3, x12 = get(i - k), get(i - k - 3), get(i - k - 12)
                if None in (x, x3, x12) or x3 <= 0 or x12 <= 0:
                    signs = None
                    break
                signs.append(_sign(((x / x3) ** 4 - 1) - (x / x12 - 1)))
            if signs is None:
                continue
            new = signs[0] if signs[0] is not None and signs.count(signs[0]) == 3 else state
        elif indicator == "E01":
            signs = []
            for k in range(3):
                x, prev = get(i - k), get(i - k - 1)
                if x is None or prev is None:
                    signs = None
                    break
                signs.append(_sign(x - prev))
            if signs is None:
                continue
            new = signs[0] if signs[0] is not None and signs.count(signs[0]) == 3 else state
        else:
            raise ValueError("MACRO_EVIDENCE_RULE")
        state = new
        out.append((period, state))
    return out


def edges(indicator: str, rows: list, frequency: str) -> list:
    """[(period, direction)] edges of the rule over a series. E40 (agency events): every change is an edge."""
    if indicator == "E40":
        result, previous = [], None
        for period, value in rows:
            if previous is not None and abs(value - previous) > EPS:
                result.append((period, "up" if value > previous else "down"))
            previous = value
        return result
    defined = es.BY_ID[indicator]["edges"]
    result, previous = [], None
    for period, state in rule_states(indicator, rows, frequency):
        if previous is not None and state != previous and state in defined:
            result.append((period, state))
        previous = state
    return result


def current_state(indicator: str, rows: list, frequency: str) -> dict:
    if indicator == "E40":
        found = edges(indicator, rows, frequency)
        last = found[-1] if found else None
        return {"state": last[1] if last else None, "since": last[0] if last else None,
                "latest": rows[-1][0] if rows else None}
    progression = rule_states(indicator, rows, frequency)
    state = progression[-1][1] if progression else None
    since = None
    for period, s in reversed(progression):
        if s != state:
            break
        since = period
    return {"state": state, "since": since, "latest": rows[-1][0] if rows else None}


# ---------------------------------------------------------------- vintages and records

def _event_id(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:20]


def _timing(capture: dict, previous_success: datetime | None) -> dict:
    """{at, basis, rd} for a record found in this collection (MEV-9 rules 1, 3 and 4)."""
    acquired = capture["acquired_at"]
    release = capture.get("release") or {}
    posted = release.get("at")
    result = {"at": iso(acquired), "basis": "COLLECTION_TIME", "rd": release.get("date")}
    if (isinstance(posted, datetime) and posted <= acquired
            and (previous_success is None or posted > previous_success)):
        result.update(at=iso(posted), basis="SOURCE_LAST_MODIFIED")
    return result


def _empty_series(sid: str) -> dict:
    return {"indicator": es.SERIES_INDICATOR[sid], "frequency": es.SERIES_FREQUENCY[sid], "state": "NOT_AVAILABLE",
            "reason": "SOURCE_NOT_COLLECTED", "acquired_at": None, "last_success_at": None, "baseline_at": None,
            "release_evidence": None, "obs": [], "history": {}, "current": {"state": None, "since": None, "latest": None},
            "delayed": None}


def _held(sid: str) -> bool:
    return es.BY_ID[es.SERIES_INDICATOR[sid]]["publication"] != "PUBLIC"


def build(captures: dict, *, previous: dict | None, previous_state: str, now: datetime) -> dict:
    """The next payload from this run's captures ({series_id: capture}) and the validated previous payload.

    capture = {"rows": {period: float}, "acquired_at": aware datetime, "release": {"at": datetime|None, "date": str|None}}
    or {"reason": REASON}. Series absent from `captures` keep their previous data with SOURCE_NOT_COLLECTED."""
    if previous is not None:
        require_macro_evidence(previous)
    prev_series = (previous or {}).get("series", {})
    prev_events = list((previous or {}).get("events", []))
    prev_records = list((previous or {}).get("releases", []))
    continuity = ("CONTINUOUS" if previous is not None and previous.get("generated_at") else
                  "RESET_PREVIOUS_UNAVAILABLE" if previous_state == "UNAVAILABLE" else "BASELINE")
    series_out, records, events, replay = {}, [], [], []
    for sid in es.SERIES_IDS:
        indicator = es.SERIES_INDICATOR[sid]
        frequency = es.SERIES_FREQUENCY[sid]
        old = prev_series.get(sid) or _empty_series(sid)
        row = json.loads(json.dumps(old))  # deep copy of the carried state
        capture = captures.get(sid)
        if _held(sid):
            row.update(_empty_series(sid), state="NOT_AVAILABLE", reason="TERMS_UNVERIFIED",
                       acquired_at=iso(capture["acquired_at"]) if capture and "rows" in capture else None)
            series_out[sid] = row
            continue
        if capture is None or "rows" not in capture:
            row.update(state="NOT_AVAILABLE", reason=(capture or {}).get("reason", "SOURCE_NOT_COLLECTED"), acquired_at=None)
        else:
            acquired = capture["acquired_at"]
            last_success = parse_iso(old["last_success_at"]) if old.get("last_success_at") else None
            baseline = old.get("baseline_at") is None
            timing = _timing(capture, last_success)
            obs = {p: v for p, v in old["obs"]}
            history = row["history"]
            new_records = []
            for period, value in sorted(capture["rows"].items()):
                if period not in obs:
                    if not baseline:
                        history.setdefault(period, []).append({"v": value, "kind": "FIRST", **timing})
                        new_records.append({"series": sid, "period": period, "kind": "FIRST", **timing})
                elif abs(obs[period] - value) > EPS * max(1.0, abs(value)):
                    versions = history.setdefault(period, [])
                    if not versions:
                        versions.append({"v": obs[period], "kind": "BASELINE", "at": old["baseline_at"], "basis": "BASELINE", "rd": None})
                    versions.append({"v": value, "kind": "REVISION", **timing})
                    new_records.append({"series": sid, "period": period, "kind": "REVISION", **timing})
                obs[period] = value
            ordered = sorted(obs.items(), key=lambda item: period_index(item[0], frequency))[-WINDOW[frequency]:]
            row.update(state="LIVE", reason=None, acquired_at=iso(acquired), last_success_at=iso(acquired),
                       baseline_at=old.get("baseline_at") or iso(acquired), obs=[[p, v] for p, v in ordered],
                       release_evidence={"at": iso(capture["release"]["at"]) if (capture.get("release") or {}).get("at") else None,
                                         "date": (capture.get("release") or {}).get("date")})
            records.extend(new_records)
            current = current_state(indicator, ordered, frequency)
            before = old.get("current") or {}
            defined = es.BY_ID[indicator]["edges"]
            if not baseline and new_records:
                cause = "FIRST" if any(r["kind"] == "FIRST" for r in new_records) else "REVISION"
                if indicator == "E40":
                    firsts = {r["period"] for r in new_records if r["kind"] == "FIRST"}
                    for period, direction in edges(indicator, ordered, frequency):
                        if period in firsts:
                            events.append(_event(indicator, sid, period, direction, "AGENCY_EVENT", "FIRST", timing))
                elif current["state"] != before.get("state"):
                    # A change caused only by revisions is dated at the latest revised period (§9-6), not moved back.
                    revised = max((r["period"] for r in new_records), key=lambda q: period_index(q, frequency))
                    period = current["since"] if cause == "FIRST" else revised
                    if current["state"] in defined:
                        events.append(_event(indicator, sid, period, current["state"], "EDGE", cause, timing))
                    elif cause == "REVISION" and before.get("state") in defined:
                        events.append(_event(indicator, sid, period, before["state"], "REVISION_CLEARED", cause, timing))
            row["current"] = current
            for period, direction in edges(indicator, ordered, frequency):
                replay.append({"indicator": indicator, "series": sid, "rule": es.BY_ID[indicator]["rule"]["version"],
                               "direction": direction, "period": period})
        row["delayed"] = _delayed(row, now)
        series_out[sid] = row
    payload = {
        "schema": SCHEMA, "kind": KIND, "catalog": es.CATALOG, "generated_at": iso(now),
        "collection_started_at": (previous or {}).get("collection_started_at") or iso(now),
        "previous": previous_state, "continuity": continuity, "scope": dict(SCOPE), "labels": dict(LABELS),
        "indicators": [indicator_view(i, series_out) for i in es.INDICATORS],
        "series": series_out, "releases": prev_records + records, "events": prev_events + events,
        "replay_events": replay, "summary": summary(series_out, prev_events + events),
    }
    state_values = [i["state"] for i in payload["indicators"]]
    payload["state"] = ("LIVE" if all(s == "LIVE" for s in state_values) else
                        "NOT_AVAILABLE" if all(s == "NOT_AVAILABLE" for s in state_values) else "PARTIAL")
    return require_macro_evidence(payload)


def _event(indicator, sid, period, direction, kind, cause, timing) -> dict:
    rule = es.BY_ID[indicator]["rule"]["version"]
    return {"id": _event_id(indicator, rule, sid, period, direction, kind, timing["at"]), "indicator": indicator,
            "series": sid, "rule": rule, "direction": direction, "kind": kind, "period": period, "cause": cause,
            "at": timing["at"], "basis": timing["basis"], "rd": timing["rd"], "layer": "REALTIME"}


def _delayed(row: dict, now: datetime):
    """'자료 지연' marker (catalog §6-3 item 3, EVL-1 candidate): the latest reference period ended more than two release
    cycles plus one publication lag ago. A marker only; it never removes data or events."""
    frequency = row["frequency"]
    if frequency == "E" or row["state"] != "LIVE" or not row["obs"]:
        return None
    return now - period_end(row["obs"][-1][0], frequency) > STALE_PERIODS[frequency] + PUBLICATION_LAG[frequency]


def indicator_view(indicator: dict, series_out: dict) -> dict:
    states = [series_out[s]["state"] for s in indicator["series"]]
    reasons = [series_out[s]["reason"] for s in indicator["series"] if series_out[s]["reason"]]
    state = "LIVE" if all(s == "LIVE" for s in states) else "NOT_AVAILABLE" if all(s != "LIVE" for s in states) else "PARTIAL"
    return {"id": indicator["id"], "name": indicator["name"], "family": indicator["family"], "cycles": list(indicator["cycles"]),
            "frequency": indicator["frequency"], "unit": indicator["unit"], "series": list(indicator["series"]),
            "state": state, "reason": None if state == "LIVE" else (reasons[0] if reasons else "SOURCE_NOT_COLLECTED"),
            "rule": dict(indicator["rule"]), "edges": {k: dict(v) for k, v in indicator["edges"].items()},
            "source": {k: indicator[k] for k in ("agency", "source", "url", "official_statistic", "license_class",
                                                  "terms_checked_on", "terms_note", "publication", "collection")},
            "system_validation": "UNVALIDATED", "v0": True}


def summary(series_out: dict, events: list) -> dict:
    """Per cycle: families whose current candidate state is WARNING / IMPROVING / mixed (catalog §6-4, §7-3; the
    'current' definition is the EVL-1 candidate, not approved). One family counts once; families mix -> neither side.
    Indicators without a candidate mapping (E39, E40) are not counted. Real-time events are counted separately."""
    out = {}
    for cycle in es.CYCLES:
        families = {}
        for indicator in es.INDICATORS:
            if cycle not in indicator["cycles"]:
                continue
            for sid in indicator["series"]:
                row = series_out[sid]
                state = (row.get("current") or {}).get("state")
                edge = indicator["edges"].get(state) if row["state"] == "LIVE" and state else None
                if edge and edge["candidate"]:
                    families.setdefault(indicator["family"], set()).add(edge["candidate"])
        warning = sorted(f for f, c in families.items() if c == {"WARNING"})
        improving = sorted(f for f, c in families.items() if c == {"IMPROVING"})
        mixed = sorted(f for f, c in families.items() if len(c) > 1)
        realtime = sorted({e["indicator"] for e in events if cycle in es.BY_ID[e["indicator"]]["cycles"]})
        out[cycle] = {"warning_families": warning, "improving_families": improving, "mixed_families": mixed,
                      "realtime_event_indicators": realtime, "basis": "CURRENT_VINTAGE_CANDIDATE_RULES"}
    return out


def empty_payload(now: datetime) -> dict:
    """Offline/PR builds: a NOT_AVAILABLE copy without source data (replaced by the daily or preserve step)."""
    series = {sid: _empty_series(sid) for sid in es.SERIES_IDS}
    payload = {"schema": SCHEMA, "kind": KIND, "catalog": es.CATALOG, "generated_at": None, "collection_started_at": None,
               "previous": "NOT_COLLECTED", "continuity": "NOT_COLLECTED", "scope": dict(SCOPE), "labels": dict(LABELS),
               "indicators": [indicator_view(i, series) for i in es.INDICATORS], "series": series, "releases": [],
               "events": [], "replay_events": [], "summary": summary(series, []), "state": "NOT_AVAILABLE"}
    return require_macro_evidence(payload)


def encode(payload: dict) -> bytes:
    body = json.dumps(require_macro_evidence(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")
    if len(body) > SIZE_BUDGET:
        raise ValueError("MACRO_EVIDENCE_TOO_LARGE")
    return body


# ---------------------------------------------------------------- validator (guard and readers)

def _need(condition: bool) -> None:
    if not condition:
        raise ValueError("MACRO_EVIDENCE_INVALID")


def _keys(obj, keys) -> None:
    _need(type(obj) is dict and set(obj) == set(keys))


def _num(value) -> bool:
    return type(value) in (int, float) and type(value) is not bool and math.isfinite(value)


def _time_or_none(value) -> None:
    if value is not None:
        parse_iso(value)


def _rd(value) -> None:
    _need(value is None or (type(value) is str and valid_period(value, "E")))


def _timing_ok(obj) -> None:
    _need(obj["basis"] in BASES)
    if obj["basis"] == "BASELINE":
        _need(obj["at"] is None or type(obj["at"]) is str)
        _time_or_none(obj["at"])
    else:
        parse_iso(obj["at"])
    _rd(obj["rd"])


def require_macro_evidence(payload) -> dict:
    """Strict schema of macro-evidence/1. Raises ValueError (fixed code) on anything else."""
    try:
        return _require(payload)
    except (KeyError, TypeError, IndexError, AttributeError):
        raise ValueError("MACRO_EVIDENCE_INVALID") from None


def _require(p) -> dict:
    _keys(p, ("schema", "kind", "catalog", "generated_at", "collection_started_at", "previous", "continuity", "scope",
              "labels", "indicators", "series", "releases", "events", "replay_events", "summary", "state"))
    _need(p["schema"] == SCHEMA and p["kind"] == KIND and p["catalog"] == es.CATALOG and p["scope"] == SCOPE and p["labels"] == LABELS)
    _need(p["previous"] in PREVIOUS and p["continuity"] in CONTINUITY and p["state"] in STATES)
    _time_or_none(p["generated_at"])
    _time_or_none(p["collection_started_at"])
    _need(type(p["indicators"]) is list and [i["id"] for i in p["indicators"]] == list(es.INDICATOR_IDS))
    series = p["series"]
    _need(type(series) is dict and set(series) == set(es.SERIES_IDS))
    for sid, row in series.items():
        _keys(row, ("indicator", "frequency", "state", "reason", "acquired_at", "last_success_at", "baseline_at",
                    "release_evidence", "obs", "history", "current", "delayed"))
        frequency = es.SERIES_FREQUENCY[sid]
        _need(row["indicator"] == es.SERIES_INDICATOR[sid] and row["frequency"] == frequency)
        _need(row["state"] in ("LIVE", "NOT_AVAILABLE"))
        _need((row["state"] == "LIVE") == (row["reason"] is None) and (row["reason"] is None or row["reason"] in es.REASONS))
        for key in ("acquired_at", "last_success_at", "baseline_at"):
            _time_or_none(row[key])
        _need(row["delayed"] in (None, True, False))
        if row["release_evidence"] is not None:
            _keys(row["release_evidence"], ("at", "date"))
            _time_or_none(row["release_evidence"]["at"])
            _rd(row["release_evidence"]["date"])
        _need(type(row["obs"]) is list and len(row["obs"]) <= WINDOW[frequency])
        last = None
        for item in row["obs"]:
            _need(type(item) is list and len(item) == 2 and valid_period(item[0], frequency) and _num(item[1]))
            index = period_index(item[0], frequency)
            _need(last is None or index > last)
            last = index
        held = es.BY_ID[row["indicator"]]["publication"] != "PUBLIC"
        _need(not held or (row["state"] == "NOT_AVAILABLE" and not row["obs"] and not row["history"]
                           and row["reason"] in ("TERMS_UNVERIFIED", "SOURCE_NOT_COLLECTED")))
        _need(type(row["history"]) is dict)
        for period, versions in row["history"].items():
            _need(valid_period(period, frequency) and type(versions) is list and 1 <= len(versions) <= 64)
            for k, version in enumerate(versions):
                _keys(version, ("v", "kind", "at", "basis", "rd"))
                _need(_num(version["v"]) and version["kind"] in VERSION_KINDS)
                _need((version["kind"] == "BASELINE") == (version["basis"] == "BASELINE") and (version["kind"] != "REVISION" or k > 0))
                _need(version["kind"] != "BASELINE" or k == 0)
                _timing_ok(version)
        _keys(row["current"], ("state", "since", "latest"))
        _need(row["current"]["state"] in (None, "up", "down", "clear"))
        for key in ("since", "latest"):
            _need(row["current"][key] is None or valid_period(row["current"][key], frequency))
    _need(type(p["releases"]) is list and len(p["releases"]) <= 50000)
    for record in p["releases"]:
        _keys(record, ("series", "period", "kind", "at", "basis", "rd"))
        _need(record["series"] in series and record["kind"] in RECORD_KINDS and record["basis"] != "BASELINE")
        _need(valid_period(record["period"], es.SERIES_FREQUENCY[record["series"]]))
        _timing_ok(record)
    _need(type(p["events"]) is list and len(p["events"]) <= 20000)
    ids = set()
    for event in p["events"]:
        _keys(event, ("id", "indicator", "series", "rule", "direction", "kind", "period", "cause", "at", "basis", "rd", "layer"))
        _need(event["series"] in series and event["indicator"] == es.SERIES_INDICATOR[event["series"]])
        _need(event["rule"] == es.BY_ID[event["indicator"]]["rule"]["version"] and event["direction"] in ("up", "down"))
        _need(event["kind"] in EVENT_KINDS and event["cause"] in RECORD_KINDS and event["layer"] == "REALTIME")
        _need(type(event["id"]) is str and re.fullmatch(r"[0-9a-f]{20}", event["id"]) is not None and event["id"] not in ids)
        _need(event["basis"] != "BASELINE" and valid_period(event["period"], es.SERIES_FREQUENCY[event["series"]]))
        ids.add(event["id"])
        _timing_ok(event)
    _need(type(p["replay_events"]) is list and len(p["replay_events"]) <= 20000)
    for event in p["replay_events"]:
        _keys(event, ("indicator", "series", "rule", "direction", "period"))
        _need(event["series"] in series and event["indicator"] == es.SERIES_INDICATOR[event["series"]] and event["direction"] in ("up", "down"))
        _need(event["rule"] == es.BY_ID[event["indicator"]]["rule"]["version"] and valid_period(event["period"], es.SERIES_FREQUENCY[event["series"]]))
    _need(type(p["summary"]) is dict and set(p["summary"]) == set(es.CYCLES))
    families = {i["family"] for i in es.INDICATORS}
    for block in p["summary"].values():
        _keys(block, ("warning_families", "improving_families", "mixed_families", "realtime_event_indicators", "basis"))
        _need(block["basis"] == "CURRENT_VINTAGE_CANDIDATE_RULES")
        for key in ("warning_families", "improving_families", "mixed_families"):
            _need(type(block[key]) is list and set(block[key]) <= families)
        _need(type(block["realtime_event_indicators"]) is list and set(block["realtime_event_indicators"]) <= set(es.INDICATOR_IDS))
    for view in p["indicators"]:
        _need(view == indicator_view(es.BY_ID[view["id"]], series))
    return p
