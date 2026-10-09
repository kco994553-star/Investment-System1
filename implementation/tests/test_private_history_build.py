"""Private history ships as local code; public builds stay disabled and data-free."""
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


def test_private_history_default_build_cannot_connect_to_a_worker(tmp_path):
    build(tmp_path)
    config = (tmp_path / "app-config.js").read_text()
    assert re.search(r"privateHistoryEnabled\s*:\s*false\b", config)
    assert re.search(r"privateHistoryWorkerOrigin\s*:\s*(['\"])\1", config)
    parser = PolicyParser()
    parser.feed((tmp_path / "index.html").read_text())
    directives = {parts[0]: parts[1:] for raw in parser.policy.split(";") if (parts := raw.split())}
    assert directives["connect-src"] == ["'self'", "https://sheets.googleapis.com", "https://oauth2.googleapis.com"]
    assert directives["script-src"] == ["'self'", "https://accounts.google.com/gsi/client"]
    assert directives["style-src"] == ["'self'", "https://accounts.google.com/gsi/style"]
    assert "workers.dev" not in parser.policy
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
