"""Static link, deterministic projection and inert serialization checks."""
from html.parser import HTMLParser
from copy import deepcopy
import json
from pathlib import Path
from urllib.parse import urlsplit, unquote

from build_preview import build, script_json, validate_context

HERE = Path(__file__).resolve().parent


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("src", "href") and value:
                self.links.append(value)


def main():
    prior = {name: (HERE / name).read_bytes() for name in ("sample.json", "sample.js")}
    result = build()
    for name, data in prior.items():
        assert (HERE / name).read_bytes() == data, name + " is stale or non-deterministic"
    assert result["quarterly"]["positive_count"] == 2
    assert result["quarterly"]["completed_count"] == 4
    assert result["annual"]["positive_count"] == 2
    assert result["annual"]["completed_count"] == 3
    assert all(result[key]["source_admission"] is False for key in ("price_position", "quarterly", "annual"))
    for filename in ("index.html", "detail.html", "evidence.html"):
        parser = Links()
        parser.feed((HERE / filename).read_text(encoding="utf-8"))
        for link in parser.links:
            parts = urlsplit(link)
            assert not parts.scheme and not parts.netloc, (filename, link, "external route")
            if parts.path:
                target = (HERE / unquote(parts.path)).resolve()
                assert target.is_relative_to(HERE) and target.is_file(), (filename, link, "missing/locality violation")
    malicious = {"name": "</script><img src=x onerror=alert(1)>&\u2028\u2029"}
    inert = script_json(malicious)
    assert "<" not in inert and ">" not in inert and "&" not in inert
    assert "\u2028" not in inert and "\u2029" not in inert
    assert json.loads(inert) == malicious
    inputs = json.loads((HERE / "input_sample.json").read_text(encoding="utf-8"))
    for keys, bad in [
        (("company", "currency"), "EUR"),
        (("company", "security_ref"), "synthetic:OTHER"),
        (("quarterly", "security_ref"), "synthetic:OTHER"),
        (("annual", "currency"), "EUR"),
        (("price_position", "current", "currency"), "EUR"),
        (("price_position", "decision_time"), "2026-10-09T12:00:00Z"),
        (("quarterly", "decision_time"), "2026-10-09T12:00:00Z"),
        (("annual", "decision_time"), "2026-10-09T12:00:00Z"),
        (("decision_time",), "2026-10-09T12:00:00Z"),
    ]:
        conflict = deepcopy(inputs)
        record = conflict
        for key in keys[:-1]:
            record = record[key]
        record[keys[-1]] = bad
        try:
            validate_context(conflict)
        except ValueError:
            pass
        else:
            raise AssertionError("Conflicting context accepted: " + ".".join(keys))
    print("PASS: deterministic adapter projection, synthetic boundary, all static local links, inert JSON serialization, nine fail-closed context mismatch cases.")


if __name__ == "__main__":
    main()
