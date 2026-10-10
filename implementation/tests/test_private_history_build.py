"""Private history connects only to the approved Worker; public data stays price-free."""
from html.parser import HTMLParser
import json
import re

from investment_system.product.web_mvp import build, repository_bundle


class PolicyParser(HTMLParser):
    policy = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy":
            self.policy = attrs["content"]


def test_private_history_assets_are_local_and_load_before_app(tmp_path):
    build(tmp_path)
    html = (tmp_path / "index.html").read_text()
    for name in ("private-history.js", "private-history.css"):
        assert (tmp_path / name).is_file(), "local private history asset missing"
        assert name in html
    assert html.index("google-sheet-quotes.js") < html.index("private-history.js") < html.index("app.js")
    script = (tmp_path / "app.js").read_text()
    assert "private-history-settings" in script and "private-history-chart" in script
    assert "PrivateHistory.mountSettings" in script and "PrivateHistory.mount" in script


def test_private_history_build_pins_one_worker_without_expanding_other_permissions(tmp_path):
    build(tmp_path)
    config = (tmp_path / "app-config.js").read_text()
    origin = "https://private-investment-history.kco994553.workers.dev"
    assert re.search(r"privateHistoryEnabled\s*:\s*true\b", config)
    assert re.search(r"privateHistoryWorkerOrigin\s*:\s*(['\"])" + re.escape(origin) + r"\1", config)
    parser = PolicyParser()
    parser.feed((tmp_path / "index.html").read_text())
    directives = {parts[0]: parts[1:] for raw in parser.policy.split(";") if (parts := raw.split())}
    assert directives["connect-src"] == ["'self'", "https://sheets.googleapis.com", "https://oauth2.googleapis.com", origin]
    assert directives["script-src"] == ["'self'", "https://accounts.google.com/gsi/client", "https://apis.google.com/js/api.js", "https://apis.google.com/_/scs/"]
    assert directives["style-src"] == ["'self'", "https://accounts.google.com/gsi/style"]
    assert parser.policy.count("workers.dev") == 1
    assert "*.workers.dev" not in parser.policy
    assert "unsafe-inline" not in parser.policy and "unsafe-eval" not in parser.policy


def test_history_feature_does_not_add_history_or_credentials_to_public_data(tmp_path):
    build(tmp_path)
    assert json.loads((tmp_path / "data.json").read_text()) == repository_bundle()
    assert not any("history" in path.name for path in tmp_path.glob("*.json"))
    for name in ("app-config.js", "private-history.js", "private-history.css"):
        text = (tmp_path / name).read_text()
        assert "client_secret" not in text and "refresh_token" not in text
    history = (tmp_path / "private-history.js").read_text()
    assert "serviceWorker.register" not in history
