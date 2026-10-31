"""Synthetic safety checks only; no keys or real provider requests."""
from datetime import datetime, time
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import github_alpaca_probe as probe


def response(symbol, days):
    return json.dumps({"symbol": symbol, "next_page_token": None, "bars": [
        {"t": datetime.combine(datetime.fromisoformat(day).date(), time.min, probe.NY).isoformat(),
         "o": 10, "h": 12, "l": 9, "c": 11, "v": 100} for day in days]}).encode()


class ProbeSafety(unittest.TestCase):
    def test_frozen_bounded_plan(self):
        requests = probe.plan()
        self.assertEqual(len(requests), 14)
        self.assertEqual({r["symbol"] for r in requests if r["cohort"] == "USER_ADDITIONAL4"},
                         {"AAPL", "MSFT", "NVDA", "ASML"})
        self.assertEqual(sum(r["cohort"] == "FIXED10_STAGE_A" for r in requests), 2)

    def test_adjusted_never_becomes_raw(self):
        request = dict(symbol="NVDA", feed="sip", adjustment="split", days=probe.EVENT_DAYS)
        rows = probe.normalize(response("NVDA", probe.EVENT_DAYS), request)
        self.assertTrue(all(x is None for x in rows[0]["raw"].values()))
        self.assertEqual(rows[0]["price_basis"], "SPLIT_ADJUSTED")
        self.assertIsNone(rows[0]["events"]["divCash"])
        self.assertFalse(rows[0]["v_input_ready"])

    def test_duplicate_rejected_and_empty_is_not_zero_missing(self):
        request = probe.plan()[0]
        body = json.loads(response("ABT", probe.PRIMARY_DAYS))
        body["bars"].append(body["bars"][0])
        with self.assertRaises(ValueError): probe.normalize(json.dumps(body), request)
        summary = probe.summary_for([], request)
        self.assertEqual(summary["missing_day_rate"], 1)
        self.assertFalse(summary["complete_ohlcv"])

    def test_no_secrets_no_network(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(probe.release, "http") as http:
            result = probe.collect(Path("unused"))
        self.assertEqual(result["market_data_requests"], 0)
        http.assert_not_called()

    def test_public_destination_blocks_before_prices(self):
        env = {k: "SYNTHETIC_ONLY" for k in ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "RAW_REPO_TOKEN")}
        env["GITHUB_ACTIONS"] = "true"
        with patch.dict(os.environ, env), patch.object(probe.release, "http", return_value=(200, {}, b'{"private":false}')), \
             patch.object(probe, "acquire") as acquire:
            result = probe.collect(Path("unused"))
        self.assertEqual(result["status"], "PRIVATE_STORAGE_PREFLIGHT_FAILED")
        acquire.assert_not_called()

    def test_mocked_full_flow_same_bytes_two_feeds_preserves_both(self):
        env = {k: "SYNTHETIC_ONLY" for k in ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "RAW_REPO_TOKEN")}
        env.update(GITHUB_ACTIONS="true", GITHUB_RUN_ID="SYNTHETIC", GITHUB_RUN_ATTEMPT="1")
        def acquired(store, aid, url, kind, headers):
            parts = urlparse(url)
            params = parse_qs(parts.query)
            symbol = parts.path.split('/')[-2]
            days = probe.EVENT_DAYS if params['start'][0].startswith('2024') else probe.PRIMARY_DAYS
            self.assertTrue(params['end'][0].startswith(days[-1] + 'T23:59:59'))
            body = response(symbol, days)
            receipt = store.put(aid, body, url, kind, "application/json", "SYNTHETIC", 200).to_dict()
            return body, receipt
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, env), \
             patch.object(probe.release, "http", return_value=(200, {}, b'{"private":true}')), \
             patch.object(probe, "acquire", side_effect=acquired), patch.object(probe.clock, "sleep"), \
             patch.object(probe.release, "upload") as upload, patch.object(probe.release, "download") as download:
            root = Path(temp) / "private"
            result = probe.collect(root)
            self.assertEqual(result["additional4_complete_symbols"], ["AAPL", "ASML", "MSFT", "NVDA"])
            self.assertEqual(len(result["results"]), 14)
            self.assertEqual(len(list((root / 'normalized').glob('*.json'))), 14)
            self.assertEqual(result["status"], "PRIVATE_ARCHIVE_ROUNDTRIP_VERIFIED")
            upload.assert_called_once()
            download.assert_called_once()
            self.assertNotIn('SYNTHETIC_ONLY', json.dumps(result))


if __name__ == "__main__":
    unittest.main()
