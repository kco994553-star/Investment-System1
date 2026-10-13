"""Navigation must preserve the exact external permissions approved before IA work."""
from html.parser import HTMLParser
from pathlib import Path


class _CspMetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.policies = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "meta" and values.get("http-equiv", "").lower() == "content-security-policy":
            self.policies.append(values["content"])


def test_navigation_does_not_expand_approved_external_csp_permissions():
    """A wildcard, unsafe-inline, extra provider or new directive would fail here."""
    asset = Path(__file__).resolve().parents[1] / "src/investment_system/product/web_assets/index.html"
    parser = _CspMetaParser()
    parser.feed(asset.read_text(encoding="utf-8"))
    assert len(parser.policies) == 1
    directives = [part.split() for part in parser.policies[0].split(";") if part.strip()]
    assert len({parts[0] for parts in directives}) == len(directives)
    actual = {parts[0]: set(parts[1:]) for parts in directives}
    assert actual == {
        "default-src": {"'self'"},
        # TradingView display-only widgets: the embed-script path only (owner-approved CSP change).
        "script-src": {"'self'", "https://accounts.google.com/gsi/client", "https://apis.google.com/js/api.js", "https://apis.google.com/_/scs/", "https://s3.tradingview.com/external-embedding/"},
        "style-src": {"'self'", "https://accounts.google.com/gsi/style"},
        "worker-src": {"'self'"},
        "manifest-src": {"'self'"},
        "connect-src": {"'self'", "https://sheets.googleapis.com", "https://oauth2.googleapis.com", "https://private-investment-history.kco994553.workers.dev"},
        # Runtime company logos: logo.dev / Brandfetch (device key only) and one fixed favicon origin.
        "img-src": {"'self'", "data:", "https://img.logo.dev", "https://cdn.brandfetch.io", "https://icons.duckduckgo.com"},
        "frame-src": {"'self'", "https://accounts.google.com", "https://docs.google.com", "https://www.tradingview-widget.com", "https://s.tradingview.com"},
        "object-src": {"'none'"},
        "base-uri": {"'none'"},
        "form-action": {"'none'"},
    }
