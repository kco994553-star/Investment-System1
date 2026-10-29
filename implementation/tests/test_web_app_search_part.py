"""The shared company search (web_app/search-part-live.js, DC-23): its listing-ended table, used for display only, has the same
codes and dates as the server table (sec_universe_shares.LISTING_ENDED_CODES). Offline, read-only."""
import re
from pathlib import Path

from investment_system.universe.sec_universe_shares import LISTING_ENDED_CODES

JS = Path(__file__).resolve().parents[1] / 'src' / 'investment_system' / 'product' / 'web_app' / 'search-part-live.js'


def test_listing_ended_table_matches_the_server_table():
    text = JS.read_text(encoding='utf-8')
    body = re.search(r"const LISTING_ENDED=Object\.freeze\(\{(.*?)\}\);\n", text).group(1)
    got = dict(re.findall(r"'((?:NYSE|NASDAQ|BATS):[A-Z0-9.\-]+)':Object\.freeze\(\{effective:'(\d{4}-\d{2}-\d{2})'\}\)", body))
    assert got == {code: entry['effective'] for code, entry in LISTING_ENDED_CODES.items()}
    assert got, 'the table is not empty while the server table names a code'
