"""Synthetic safety/normalization checks; these are not actual market evidence."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from github_kis_probe import KIS, choose_keys, kis_normalize, progress, RawDatasetStore


def payload(rows=None):
    return json.dumps({"rt_cd": "0", "output2": rows if rows is not None else [
        {"xymd": "20241001", "open": "10", "high": "12", "low": "9", "clos": "11", "tvol": "100"}]}).encode()


class KISTest(unittest.TestCase):
    def test_no_zero_imputation_or_adjusted_execution(self):
        row = kis_normalize(payload(), "TEST", "1", "20241001")[0]
        self.assertIsNone(row["raw"]["open"])
        self.assertIsNone(row["events"]["divCash"])
        self.assertFalse(row["ledger_ready"])
        self.assertEqual(row["observed"]["open"], 10)

    def test_future_and_duplicate_rows_rejected(self):
        with self.assertRaises(ValueError):
            kis_normalize(payload(), "TEST", "0", "20240930")
        row = json.loads(payload())["output2"][0]
        with self.assertRaises(ValueError):
            kis_normalize(payload([row, row]), "TEST", "0", "20241001")

    def test_pagination_stops_repeats_and_forward_motion(self):
        self.assertEqual(progress({"2024-10-01"}, [{"session_date": "2024-10-01"}]), "REPEATED_PAGE")
        self.assertEqual(progress({"2024-10-01"}, [{"session_date": "2024-10-02"}]), "NO_BACKWARD_PROGRESS")
        self.assertEqual(progress({"2024-10-01"}, [{"session_date": "2024-09-30"}]), "PROGRESS")

    def test_ambiguous_keys_fail_closed(self):
        self.assertEqual(choose_keys({})[1], "SECRET_BINDING_MISSING")
        self.assertEqual(choose_keys({"KIS_APP_KEY": "a", "KIS_APP_SECRET": "b",
            "KIS_APPKEY": "c", "KIS_APPSECRET": "d"})[1], "AMBIGUOUS_SECRET_BINDINGS")

    def test_auth_response_not_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = KIS(root, RawDatasetStore(root / "store"), ("synthetic-key", "synthetic-secret"))
            with patch("github_kis_probe.transport", return_value=(200, b'{"access_token":"synthetic-token"}', "", 0.1)):
                report = client.authenticate()
            self.assertEqual(report["status"], "AUTHENTICATED")
            self.assertEqual(client.headers["Content-Type"], "application/json")
            self.assertEqual(client.headers["Accept"], "text/plain")
            self.assertNotIn("synthetic", json.dumps(report))
            self.assertEqual(client.store.list_ids(), [])

    def test_cached_replay_is_byte_identical_and_no_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requests").mkdir()
            client = KIS(root, RawDatasetStore(root / "store"), ("synthetic-key", "synthetic-secret"))
            client.headers = {"authorization": "Bearer synthetic-token"}
            with patch("github_kis_probe.time.sleep"), patch("github_kis_probe.transport", return_value=(200, payload(), "M", 0.1)):
                first, meta = client.page("TEST", "NAS", "20241001", "0")
            with patch("github_kis_probe.transport", side_effect=AssertionError("network on replay")):
                replay, replay_meta = client.page("TEST", "NAS", "20241001", "0")
            self.assertEqual(first, replay)
            self.assertEqual(meta, replay_meta)
            self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()

class KISRetryArchiveTest(unittest.TestCase):
    def test_explicit_retry_preserves_rejected_original_and_reuses_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'requests').mkdir()
            client=KIS(root,RawDatasetStore(root/'store'),('synthetic-key','synthetic-secret'))
            client.headers={'authorization':'Bearer synthetic-token'}
            rejected=b'{"rt_cd":"1","msg_cd":"OPSQ1002","msg1":"SESSION FULL"}'
            with patch('github_kis_probe.time.sleep'),patch('github_kis_probe.transport',return_value=(200,rejected,'',.1)):
                first,_=client.page('TEST','NAS','20241001','0')
            with patch('github_kis_probe.time.sleep'),patch('github_kis_probe.transport',return_value=(200,payload(),'',.1)):
                second,_=client.page('TEST','NAS','20241001','0',attempt=1)
            self.assertNotEqual(first,second)
            self.assertEqual(len(client.store.list_ids()),2)
            with patch('github_kis_probe.transport',side_effect=AssertionError('duplicate network')):
                self.assertEqual(client.page('TEST','NAS','20241001','0')[0],rejected)
                self.assertEqual(client.page('TEST','NAS','20241001','0',attempt=1)[0],second)
            self.assertEqual(client.calls,2)

class KISPartitionTest(unittest.TestCase):
    def test_bad_ohlc_is_quarantined_without_losing_valid_other_dates(self):
        import github_kis_probe as module
        partition=getattr(module,'kis_partition',None)
        self.assertIsNotNone(partition,'one malformed bar must not erase valid page rows')
        good=json.loads(payload())['output2'][0]
        bad={**good,'xymd':'20241002','low':'12','high':'12','open':'12','clos':'11'}
        rows,rejected=partition(payload([good,bad]),'TEST','0','20241002')
        self.assertEqual([r['session_date']for r in rows],['2024-10-01'])
        self.assertEqual([(r['date'],r['reason'])for r in rejected],[('2024-10-02','OHLC range mismatch')])
        with self.assertRaises(ValueError):partition(payload([good,good]),'TEST','0','20241002')
        with self.assertRaises(ValueError):partition(payload([good,bad]),'TEST','0','20241001')
