import importlib.util
import sys
import os
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "autonomy_gate_a_guard.py"
spec = importlib.util.spec_from_file_location("autonomy_guard", MODULE_PATH)
guard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(guard)


class AutonomyGateAGuardTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "immutable_exact_paths": ["frozen.json"],
            "append_only_exact_paths": ["DECISIONS.md"],
            "append_only_prefixes": ["evidence/"],
        }

    def test_parse_name_status(self):
        self.assertEqual(
            guard.parse_name_status("M\tfrozen.json\nA\tevidence/new.json\n"),
            [("M", ["frozen.json"]), ("A", ["evidence/new.json"])],
        )

    def test_immutable_modify_fails(self):
        v = guard.classify_diff([("M", ["frozen.json"])], self.cfg)
        self.assertEqual(len(v), 1)

    def test_immutable_delete_fails(self):
        v = guard.classify_diff([("D", ["frozen.json"])], self.cfg)
        self.assertEqual(len(v), 1)

    def test_append_only_add_is_allowed(self):
        self.assertEqual(
            guard.classify_diff([("A", ["evidence/new.json"])], self.cfg), []
        )

    def test_append_only_modify_fails(self):
        v = guard.classify_diff([("M", ["evidence/existing.json"])], self.cfg)
        self.assertEqual(len(v), 1)

    def test_append_only_rename_fails(self):
        v = guard.classify_diff(
            [("R100", ["evidence/a.json", "evidence/b.json"])], self.cfg
        )
        self.assertEqual(len(v), 1)

    def test_unprotected_change_allowed(self):
        self.assertEqual(
            guard.classify_diff([("M", ["implementation/src/x.py"])], self.cfg), []
        )

    def test_config_operating_values_are_pinned(self):
        cfg = guard.load_config()
        self.assertEqual(cfg["operating_values"]["cycle_max_tasks"], 5)
        self.assertEqual(cfg["operating_values"]["lease_ttl_seconds"], 7200)
        self.assertEqual(cfg["operating_values"]["repair_round_cap"], 3)

    def test_invalid_mode_fails_closed(self):
        cfg = guard.load_config()
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)
            p = fake_root / cfg["autonomy_mode_file"]
            p.parent.mkdir(parents=True)
            p.write_text("INVALID\n", encoding="utf-8")
            old_root = guard.REPO_ROOT
            try:
                guard.REPO_ROOT = fake_root
                with self.assertRaises(guard.GuardError):
                    guard.validate_mode(cfg)
            finally:
                guard.REPO_ROOT = old_root


class DeviceActualPrivacyGuardTests(unittest.TestCase):
    """Generate conspicuously synthetic exports only inside temporary repositories."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old_root = guard.REPO_ROOT
        guard.REPO_ROOT = self.root
        self.addCleanup(setattr, guard, "REPO_ROOT", self.old_root)
        self.git("init", "-q")
        self.git("config", "user.email", "synthetic-test@example.invalid")
        self.git("config", "user.name", "SYNTHETIC PRIVACY TEST ONLY")
        mode = self.root / guard.load_config()["autonomy_mode_file"]
        mode.parent.mkdir(parents=True)
        mode.write_text("READ_ONLY\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic test baseline")

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True, text=True
        ).stdout

    def write(self, path, content, *, tracked=True, committed=True):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
        if tracked:
            self.git("add", "--", path)
            if committed:
                self.git("commit", "-qm", "Synthetic test payload")

    @staticmethod
    def envelope():
        return {
            "schema": "device-actual-holdings/1",
            "version": 1,
            "kind": "ACTUAL",
            "ownership": "USER_DEVICE_ONLY",
            "owner": {"role": "USER", "storage": "USER_DEVICE_ONLY"},
            "effective_at": "2099-01-01T00:00:00Z",
            "available_at": "2099-01-01T00:00:00Z",
            "target_root_version": "SYNTHETIC_TEST_ONLY",
            "target_root_hash": "SYNTHETIC_TEST_ONLY",
            "identity_map_version": "SYNTHETIC_TEST_ONLY",
            "identity_map_hash": "SYNTHETIC_TEST_ONLY",
            "themes": [{"theme_id": "SYNTHETIC_TEST_THEME_ONLY", "holdings": [{
                "security_reference": {"scheme": "SYNTHETIC_TEST_ONLY", "value": "SYNTHETIC_TEST_SECURITY_ONLY"},
                "quantity": "99123.4567", "average_cost": "88765.4321", "currency": "ZZZ",
            }]}],
        }

    def check(self, base="HEAD"):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = guard.cmd_diff(base)
        return result, output.getvalue()

    def assert_private_failure(self):
        result, output = self.check()
        self.assertEqual(result, 1)
        data = json.loads(output)
        self.assertEqual(data["gate_a_repository_guard"], "FAIL")
        self.assertEqual(data["device_actual_privacy_guard"], "FAIL")
        self.assertEqual(data["mode"], "READ_ONLY")
        for secret in ("99123", "88765", "SYNTHETIC_TEST_SECURITY_ONLY", "sensitive-file"):
            self.assertNotIn(secret, output)

    def test_committed_nested_actual_export_fails_without_changed_diff(self):
        self.write("sensitive-file.json", json.dumps(self.envelope()))
        self.assert_private_failure()

    def test_private_payload_failure_redacts_other_guard_path_diagnostics(self):
        protected_path = guard.load_config()["append_only_prefixes"][0] + "sensitive-file.json"
        self.write(protected_path, "{}")
        self.write(protected_path, json.dumps(self.envelope()))
        result, output = self.check("HEAD^")
        self.assertEqual(result, 1)
        self.assertNotIn("sensitive-file", output)
        self.assertEqual(json.loads(output)["device_actual_privacy_guard"], "FAIL")

    def test_staged_actual_export_fails(self):
        self.write("sensitive-file.json", json.dumps(self.envelope()), committed=False)
        self.assert_private_failure()

    def test_tracked_worktree_actual_export_fails(self):
        self.write("sensitive-file.json", "{}")
        self.write("sensitive-file.json", json.dumps(self.envelope()), tracked=False)
        self.assert_private_failure()

    def test_committed_actual_cannot_be_hidden_by_worktree_scrub(self):
        self.write("sensitive-file.json", json.dumps(self.envelope()))
        self.write("sensitive-file.json", "{}", tracked=False)
        self.assert_private_failure()

    def test_staged_actual_cannot_be_hidden_by_worktree_scrub(self):
        self.write("sensitive-file.json", json.dumps(self.envelope()), committed=False)
        self.write("sensitive-file.json", "{}", tracked=False)
        self.assert_private_failure()

    def test_utf16_export_under_arbitrary_filename_fails(self):
        (self.root / "innocent.dat").write_bytes(json.dumps(self.envelope()).encode("utf-16"))
        self.git("add", "innocent.dat")
        self.git("commit", "-qm", "Synthetic encoding test")
        self.assert_private_failure()

    def test_csv_device_marker_and_zero_quantity_fail(self):
        self.write("innocent.csv", "kind,security_id,quantity\nACTUAL,SYNTHETIC_TEST_SECURITY_ONLY,0\n")
        self.assert_private_failure()

    def test_markdown_embedded_populated_export_fails(self):
        self.write("notes.md", "Synthetic test note\n```json\n" + json.dumps(self.envelope()) + "\n```\n")
        self.assert_private_failure()

    def test_yaml_flow_mappings_anchors_stream_and_zero_values_fail(self):
        self.write("innocent.yaml", "---\nschema: device-actual-holdings/1\n"
            "shared: &synthetic_ref {scheme: SYNTHETIC_TEST_ONLY, value: SYNTHETIC_TEST_SECURITY_ONLY}\n"
            "themes:\n  - holdings:\n      - {security_reference: *synthetic_ref, quantity: 0, average_cost: 0, currency: ZZZ}\n...\n")
        self.assert_private_failure()

    def test_unlabeled_yaml_anchor_numeric_holdings_fail(self):
        self.write("innocent.dat", "synthetic_quantity: &qty 99123.4567\n"
            "synthetic_cost: &cost 88765.4321\nholdings:\n"
            "  - security_id: SYNTHETIC_TEST_SECURITY_ONLY\n    quantity: *qty\n"
            "    average_cost: *cost\n    currency: ZZZ\n")
        self.assert_private_failure()

    def test_export_header_only_and_null_placeholder_rows_pass(self):
        self.write("actual_holdings.csv", "security_id,quantity,average_cost,currency\n")
        self.write("empty.yaml", "schema: device-actual-holdings/1\npositions:\n  - security_reference: null\n    quantity: null\n    average_cost: null\n    currency: null\n")
        self.write("empty.json", json.dumps({"schema": "device-actual-holdings/1", "positions": [{
            "security_reference": None, "quantity": None, "average_cost": None, "currency": None,
        }]}))
        self.assertEqual(self.check()[0], 0)

    def test_untracked_device_file_is_not_read_or_rejected(self):
        self.write("sensitive-file.json", json.dumps(self.envelope()), tracked=False)
        self.assertEqual(self.check()[0], 0)

    def test_tracked_path_under_symlink_directory_does_not_read_device_file(self):
        self.write("tracked/payload.json", "{}")
        with tempfile.TemporaryDirectory() as device:
            (Path(device) / "payload.json").write_text(json.dumps(self.envelope()), encoding="utf-8")
            (self.root / "tracked").rename(self.root / "untracked-backup")
            (self.root / "tracked").symlink_to(device, target_is_directory=True)
            self.assertEqual(self.check()[0], 0)

    def test_tracked_symlink_to_untracked_device_file_is_not_read(self):
        self.write("device.json", json.dumps(self.envelope()), tracked=False)
        (self.root / "tracked.json").symlink_to("device.json")
        self.git("add", "tracked.json")
        self.git("commit", "-qm", "Synthetic symlink test")
        self.assertEqual(self.check()[0], 0)

    def test_renamed_payload_with_synthetic_label_still_fails(self):
        payload = self.envelope()
        payload["synthetic"] = True
        self.write("sensitive-file.json", json.dumps(payload))
        self.git("mv", "sensitive-file.json", "innocent.dat")
        self.git("commit", "-qm", "Synthetic test rename")
        self.assert_private_failure()

    def test_unlabeled_json_holdings_rows_fail(self):
        positions = self.envelope()["themes"][0]["holdings"]
        self.write("innocent.dat", json.dumps({"positions": positions}))
        self.assert_private_failure()

    def test_yaml_device_actual_and_generic_holding_rows_fail(self):
        for prefix in ("", "schema: device-actual-holdings/1\nkind: ACTUAL\n"):
            with self.subTest(prefix=bool(prefix)):
                self.write("innocent.dat", prefix +
                    "themes:\n  - theme_id: SYNTHETIC_TEST_THEME_ONLY\n    holdings:\n"
                    "      - security_reference:\n          scheme: SYNTHETIC_TEST_ONLY\n"
                    "          value: SYNTHETIC_TEST_SECURITY_ONLY\n"
                    "        quantity: '99123.4567'\n        average_cost: '88765.4321'\n        currency: ZZZ\n")
                self.assert_private_failure()

    def test_yaml_scalar_notes_and_tags_do_not_hide_private_holdings(self):
        payload = "schema: device-actual-holdings/1\nholdings:\n  - security_id: SYNTHETIC_TEST_SECURITY_ONLY\n    quantity: 99123.4567\n    average_cost: 88765.4321\n    currency: ZZZ\n"
        for prefix in ("", "%TAG !synthetic! tag:example.invalid,2099:\n---\n!!map\n"):
            with self.subTest(tag=bool(prefix)):
                self.write("innocent.yaml", prefix + payload + "notes:\n  - SYNTHETIC_TEST_NOTE_ONLY\n")
                self.assert_private_failure()

    def test_git_replacement_refs_cannot_hide_committed_holdings(self):
        self.write("innocent.json", json.dumps(self.envelope()))
        actual_oid = self.git("rev-parse", "HEAD:innocent.json").strip()
        safe_oid = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=self.root,
            input="{}", text=True, capture_output=True, check=True).stdout.strip()
        self.git("replace", actual_oid, safe_oid)
        self.write("innocent.json", "{}", tracked=False)
        self.assert_private_failure()

    def test_yaml_later_placeholder_does_not_hide_numeric_holdings(self):
        self.write("innocent.yaml", "positions:\n  - security_id: SYNTHETIC_TEST_SECURITY_ONLY\n"
            "    quantity: 99123.4567\n    average_cost: 88765.4321\n    currency: ZZZ\n"
            "  - security_id: SYNTHETIC_TEST_PLACEHOLDER_ONLY\n    quantity: unavailable\n    average_cost: unavailable\n")
        self.assert_private_failure()

    def test_yaml_description_of_shape_is_not_a_populated_export(self):
        self.write("description.yaml", "schema: PORTFOLIO_TARGET/0.1\ndescription: |\n"
            "  security_id: SYNTHETIC_TEST_SECURITY_ONLY\n  quantity: 99123.4567\n"
            "  average_cost: 88765.4321\n  currency: ZZZ\n")
        self.assertEqual(self.check()[0], 0)

    def test_new_history_payload_removed_before_head_is_rejected(self):
        base = self.git("rev-parse", "HEAD").strip()
        self.write("sensitive-file.json", json.dumps(self.envelope()))
        self.git("rm", "sensitive-file.json")
        self.git("commit", "-qm", "Synthetic payload removal")
        result, output = self.check(base)
        self.assertEqual(result, 1)
        self.assertNotIn("sensitive-file", output)
        self.assertEqual(json.loads(output)["device_actual_privacy_guard"], "FAIL")

    def test_csv_export_aliases_fail_under_arbitrary_filename(self):
        for header in ("security_id,quantity,average_cost,currency", "Symbol,Shares,Average Cost,Currency"):
            with self.subTest(header=header):
                self.write("innocent.dat", header + "\nSYNTHETIC_TEST_SECURITY_ONLY,99123.4567,88765.4321,ZZZ\n")
                self.assert_private_failure()

    def test_csv_leading_blank_lines_do_not_hide_private_rows(self):
        self.write("actual_holdings.csv", "\n  \nsecurity_id,quantity,average_cost,currency\n"
            "SYNTHETIC_TEST_SECURITY_ONLY,99123.4567,88765.4321,ZZZ\n")
        self.assert_private_failure()

    def test_common_export_filename_rejects_populated_partial_holdings(self):
        self.write("actual_holdings.csv", "Symbol,Quantity\nSYNTHETIC_TEST_SECURITY_ONLY,99123.4567\n")
        self.assert_private_failure()

    def test_explicit_actual_marker_rejects_incomplete_nonempty_payload(self):
        self.write("innocent.json", json.dumps({
            "portfolio": {"kind": "ACTUAL"}, "holdings": [{"quantity": "99123.4567"}],
        }))
        self.assert_private_failure()

    def test_empty_device_envelope_target_weights_and_source_description_pass(self):
        empty = self.envelope()
        empty["themes"][0]["holdings"] = []
        self.write("device-schema-example.json", json.dumps(empty))
        self.write("target.yaml", "schema: PORTFOLIO_TARGET/0.1\nthemes:\n  - holdings:\n      - security_id: SYNTHETIC_TEST_ONLY\n        weight_units: 99123\n")
        self.write("source.py", "payload = " + repr(self.envelope()))
        self.write("schema.json", json.dumps({"properties": {
            "quantity": {"type": "string"}, "average_cost": {"type": "string"},
            "currency": {"type": "string"}, "security_reference": {"type": "object"},
        }}))
        self.assertEqual(self.check()[0], 0)

    @staticmethod
    def market_envelope(*, fx_only=False):
        quote = {
            "security_reference": {"scheme": "SYNTHETIC_TEST_ONLY", "value": "SYNTHETIC_TEST_SECURITY_ONLY"},
            "price": "77331.2468", "currency": "ZZZ",
            "as_of": "2099-01-01T00:00:00Z", "available_at": "2099-01-01T00:00:00Z",
            "source": "SYNTHETIC_TEST_MANUAL_ONLY",
        }
        fx = {
            "currency": "ZZZ", "rate": "66321.1357",
            "as_of": "2099-01-01T00:00:00Z", "available_at": "2099-01-01T00:00:00Z",
            "source": "SYNTHETIC_TEST_MANUAL_ONLY",
        }
        return {"schema": "device-market-data/1", "quotes": [] if fx_only else [quote], "fx": [fx]}

    @staticmethod
    def api_envelope():
        return {"schema": "device-api-settings/1", "service": "NOT_SELECTED",
                "enabled": False, "api_key": "SYNTHETIC_TEST_CREDENTIAL_ONLY"}

    def assert_market_or_credential_failure(self, base="HEAD"):
        result, output = self.check(base)
        self.assertEqual(result, 1)
        data = json.loads(output)
        self.assertEqual(data["gate_a_repository_guard"], "FAIL")
        self.assertEqual(data["device_actual_privacy_guard"], "FAIL")
        self.assertEqual(data["mode"], "READ_ONLY")
        for private in ("77331", "66321", "SYNTHETIC_TEST_SECURITY_ONLY",
                        "SYNTHETIC_TEST_MANUAL_ONLY", "SYNTHETIC_TEST_CREDENTIAL_ONLY", "sensitive-file"):
            self.assertNotIn(private, output)

    def test_committed_device_market_quotes_under_arbitrary_name_fail(self):
        self.write("sensitive-file.dat", json.dumps(self.market_envelope()))
        self.assert_market_or_credential_failure()

    def test_fx_only_device_market_export_fails(self):
        self.write("sensitive-file.json", json.dumps(self.market_envelope(fx_only=True)))
        self.assert_market_or_credential_failure()

    def test_yaml_device_market_quotes_fail(self):
        self.write("sensitive-file.yaml", "schema: device-market-data/1\nquotes:\n"
            "  - security_reference: SYNTHETIC_TEST_SECURITY_ONLY\n"
            "    price: '77331.2468'\n    currency: ZZZ\n    source: SYNTHETIC_TEST_MANUAL_ONLY\n")
        self.assert_market_or_credential_failure()

    def test_yaml_fx_anchor_and_zero_rate_fail(self):
        payload = "schema: device-market-data/1\nshared: &fx 0\nfx_rates:\n"
        payload += "  - {currency: ZZZ, rate: *fx, source: SYNTHETIC_TEST_MANUAL_ONLY}\n"
        self.write("sensitive-file.dat", payload)
        self.assert_market_or_credential_failure()

    def test_csv_device_market_quotes_fail(self):
        self.write("sensitive-file.csv", "schema,security_reference,price,currency,source\n"
            "device-market-data/1,SYNTHETIC_TEST_SECURITY_ONLY,77331.2468,ZZZ,SYNTHETIC_TEST_MANUAL_ONLY\n")
        self.assert_market_or_credential_failure()

    def test_csv_fx_without_security_identity_fails(self):
        self.write("sensitive-file.dat", "schema,currency,rate,source\n"
            "device-market-data/1,ZZZ,66321.1357,SYNTHETIC_TEST_MANUAL_ONLY\n")
        self.assert_market_or_credential_failure()

    def test_private_market_export_names_reject_unmarked_records(self):
        quote = self.market_envelope()["quotes"][0]
        cases = (
            ("device-quotes.json", json.dumps({"quotes": [quote]})),
            ("user-fx.csv", "currency,rate\nZZZ,66321.1357\n"),
            ("device-market-data.yaml", "fx_rates:\n  - currency: ZZZ\n    rate: 0\n"),
        )
        for path, payload in cases:
            with self.subTest(format=Path(path).suffix):
                self.assertTrue(guard.contains_device_actual(payload.encode(), path))

    def test_private_storage_marker_rejects_quote_record(self):
        payload = {"ownership": "USER_DEVICE_ONLY", "quotes": self.market_envelope()["quotes"]}
        self.write("sensitive-file.json", json.dumps(payload))
        self.assert_market_or_credential_failure()

    def test_private_market_partial_records_and_zero_values_fail(self):
        for row in ({"price": 0}, {"rate": "0"}):
            with self.subTest(field=next(iter(row))):
                payload = {"schema": "device-market-data/1", "quotes": [row]}
                self.assertTrue(guard.contains_device_actual(json.dumps(payload).encode(), "innocent.dat"))

    def test_json_credential_fields_normalize_case_and_separators(self):
        for field in ("api_key", "API-KEY", "apiKey", "AppKey", "app_secret", "ACCESS_TOKEN",
                      "refresh-token", "clientSecret", "api_secret", "secret_key", "auth_token", "bearer_token"):
            with self.subTest(field=field):
                payload = {"settings": {field: "SYNTHETIC_TEST_CREDENTIAL_ONLY"}}
                self.assertTrue(guard.contains_device_actual(json.dumps(payload).encode(), "innocent.dat"))

    @staticmethod
    def synthetic_sheet_id():
        return "1" + "synthetic" * 6

    @staticmethod
    def synthetic_google_token():
        return "ya" + "29." + "SYNTHETIC_TOKEN_ONLY"

    def test_google_sheet_id_fields_fail_in_structured_formats(self):
        for field in ("spreadsheet_id", "spreadsheetId", "SPREADSHEET-ID", "sheet_id",
                      "google_sheet_id", "google_spreadsheet_id"):
            for suffix, payload in (
                ("json", json.dumps({"settings": {field: self.synthetic_sheet_id()}})),
                ("yaml", "settings:\n  " + field + ": " + self.synthetic_sheet_id() + "\n"),
                ("csv", field + "\n" + self.synthetic_sheet_id() + "\n"),
            ):
                with self.subTest(field=field, format=suffix):
                    self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent." + suffix))

    def test_google_sheet_private_urls_fail_in_arbitrary_text(self):
        paths = (
            "https://docs.google.com/spreadsheets/d/" + self.synthetic_sheet_id() + "/edit",
            "https://docs.google.com/spreadsheets/u/0/d/" + self.synthetic_sheet_id() + "/edit",
            "https://sheets.googleapis.com/v4/spreadsheets/" + self.synthetic_sheet_id() + "/values/Quotes",
        )
        for url in paths:
            for suffix in ("md", "log", "js", "txt", "json"):
                with self.subTest(format=suffix, api_url="googleapis" in url):
                    self.assertTrue(guard.contains_device_actual(("request " + url).encode(), "innocent." + suffix))

    def test_google_sheet_id_source_assignments_fail(self):
        for field in ("spreadsheet_id", "spreadsheetId", "sheetId", "googleSheetId"):
            for separator in (" = ", ": "):
                with self.subTest(field=field, assignment=separator.strip()):
                    payload = "const settings = { " + field + separator + "'" + self.synthetic_sheet_id() + "' };"
                    self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent.js"))

    def test_google_sheet_id_template_computed_and_truncated_assignments_fail(self):
        sheet_id = self.synthetic_sheet_id()
        payloads = (
            "const spreadsheetId = `" + sheet_id + "`;",
            'settings["spreadsheetId"] = "' + sheet_id + '";',
            "settings['spreadsheet_id'] = '" + sheet_id + "';",
            "const spreadsheetId = '" + sheet_id,
        )
        for index, payload in enumerate(payloads):
            with self.subTest(case=index):
                self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent.js"))

    def test_decoded_json_google_strings_fail_without_private_field_names(self):
        sheet_url = "https://docs.google.com/spreadsheets/d/" + self.synthetic_sheet_id() + "/edit"
        token = self.synthetic_google_token()
        payloads = (
            json.dumps({"message": sheet_url}).replace("/", r"\/"),
            json.dumps({"message": token}).replace("ya" + "29.", "ya" + r"\u0032" + "9."),
            json.dumps([{"renamed": [sheet_url, token]}], ensure_ascii=True).replace("/", r"\/"),
            json.dumps(token).replace("ya" + "29.", "ya" + r"\u0032" + "9."),
        )
        for index, payload in enumerate(payloads):
            with self.subTest(case=index):
                self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent.json"))

    def test_google_access_token_fails_in_every_text_format(self):
        for token in (self.synthetic_google_token(), "ya" + "29." + "x"):
            for suffix in ("md", "log", "js", "py", "json", "txt", "map"):
                with self.subTest(format=suffix, truncated=len(token) < 8):
                    payload = "arbitrary text " + token
                    self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent." + suffix))

    def test_google_sheet_settings_staged_then_scrubbed_still_fail(self):
        self.write("sensitive-file.js", "const spreadsheetId = '" + self.synthetic_sheet_id() + "';", committed=False)
        self.write("sensitive-file.js", "// cleared", tracked=False)
        result, output = self.check()
        self.assertEqual(result, 1)
        self.assertEqual(json.loads(output)["device_actual_privacy_guard"], "FAIL")
        self.assertNotIn(self.synthetic_sheet_id(), output)
        self.assertNotIn("sensitive-file", output)

    def test_google_access_token_removed_before_head_fails_history_scan(self):
        base = self.git("rev-parse", "HEAD").strip()
        self.write("sensitive-file.log", self.synthetic_google_token())
        self.git("rm", "sensitive-file.log")
        self.git("commit", "-qm", "Synthetic Google token removal")
        result, output = self.check(base)
        self.assertEqual(result, 1)
        self.assertEqual(json.loads(output)["device_actual_privacy_guard"], "FAIL")
        self.assertNotIn(self.synthetic_google_token(), output)
        self.assertNotIn("sensitive-file", output)

    def test_empty_google_sheet_settings_and_schema_descriptions_pass(self):
        payloads = (
            json.dumps({"spreadsheet_id": "", "sheet_id": None}),
            json.dumps({"properties": {"spreadsheet_id": {"type": "string"}}}),
            "spreadsheet_id: null\nsheet_id: ''\n",
            "spreadsheet_id,sheet_id\n,\n",
            "Use spreadsheet_id only on the device; a token starts with ya29.\n",
        )
        for index, payload in enumerate(payloads):
            with self.subTest(case=index):
                self.assertFalse(guard.contains_device_actual(payload.encode(), "guide.dat"))

    def test_google_public_client_id_hash_and_fixed_mapping_pass(self):
        public_client_id = "437589281514-r5hasrua70busongkklplctm8j206k3s.apps.googleusercontent.com"
        payloads = (
            json.dumps({"googleClientId": public_client_id}),
            "const GOOGLE_CLIENT_ID = '" + public_client_id + "';",
            json.dumps({"sha256": "abcdef0123456789" * 4, "code": "NASDAQ:ASML"}),
            "https://sheets.googleapis.com/v4/spreadsheets/{id}/values/{range}\n",
            "https://docs.google.com/spreadsheets/d/<YOUR_SHEET_ID>/edit\n",
            "const settings = { spreadsheet_id: '', range: 'Quotes!A1:C22' };",
        )
        for index, payload in enumerate(payloads):
            with self.subTest(case=index):
                self.assertFalse(guard.contains_device_actual(payload.encode(), "source.js"))

    def test_nested_api_settings_record_fails_with_service_disabled(self):
        self.write("sensitive-file.json", json.dumps({"settings": self.api_envelope()}))
        self.assert_market_or_credential_failure()

    def test_yaml_credential_alias_fails(self):
        self.write("sensitive-file.yaml", "shared: &canary SYNTHETIC_TEST_CREDENTIAL_ONLY\n"
            "settings:\n  App_Secret: *canary\n")
        self.assert_market_or_credential_failure()

    def test_yaml_multiline_credential_fails(self):
        self.write("sensitive-file.yaml", "api_key: |\n  SYNTHETIC_TEST_CREDENTIAL_ONLY\n")
        self.assert_market_or_credential_failure()

    def test_yaml_credential_block_comment_text_is_populated(self):
        payload = "api_key: |\n  # SYNTHETIC_TEST_CREDENTIAL_ONLY\n"
        self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent.yaml"))

    def test_csv_credential_only_column_fails(self):
        self.write("sensitive-file.csv", "Access_Token\nSYNTHETIC_TEST_CREDENTIAL_ONLY\n")
        self.assert_market_or_credential_failure()

    def test_market_staged_payload_cannot_be_hidden_by_worktree_scrub(self):
        self.write("sensitive-file.json", json.dumps(self.market_envelope()), committed=False)
        self.write("sensitive-file.json", "{}", tracked=False)
        self.assert_market_or_credential_failure()

    def test_market_tracked_worktree_payload_fails(self):
        self.write("sensitive-file.json", "{}")
        self.write("sensitive-file.json", json.dumps(self.market_envelope()), tracked=False)
        self.assert_market_or_credential_failure()

    def test_credential_staged_payload_cannot_be_hidden_by_worktree_scrub(self):
        self.write("sensitive-file.json", json.dumps(self.api_envelope()), committed=False)
        self.write("sensitive-file.json", "{}", tracked=False)
        self.assert_market_or_credential_failure()

    def test_renamed_market_export_remains_rejected(self):
        self.write("sensitive-file.json", json.dumps(self.market_envelope()))
        self.git("mv", "sensitive-file.json", "innocent.dat")
        self.git("commit", "-qm", "Synthetic market rename")
        self.assert_market_or_credential_failure()

    def test_source_named_market_export_removed_before_head_fails_history_scan(self):
        base = self.git("rev-parse", "HEAD").strip()
        self.write("sensitive-file.py", json.dumps(self.market_envelope()))
        self.git("rm", "sensitive-file.py")
        self.git("commit", "-qm", "Synthetic market removal")
        self.assert_market_or_credential_failure(base)

    def test_credential_export_removed_before_head_fails_history_scan(self):
        base = self.git("rev-parse", "HEAD").strip()
        self.write("sensitive-file.json", json.dumps(self.api_envelope()))
        self.git("rm", "sensitive-file.json")
        self.git("commit", "-qm", "Synthetic credential removal")
        self.assert_market_or_credential_failure(base)

    def test_private_market_failure_redacts_other_guard_path_diagnostics(self):
        path = guard.load_config()["append_only_prefixes"][0] + "sensitive-file.json"
        self.write(path, "{}")
        self.write(path, json.dumps(self.market_envelope()))
        self.assert_market_or_credential_failure("HEAD^")

    def test_untracked_market_and_credentials_are_not_read(self):
        self.write("sensitive-file.json", json.dumps(self.market_envelope()), tracked=False)
        self.write("device-api-settings.json", json.dumps(self.api_envelope()), tracked=False)
        self.assertEqual(self.check()[0], 0)

    def test_empty_market_and_credential_placeholders_pass(self):
        blank = {"security_reference": None, "price": None, "currency": None,
                 "as_of": None, "available_at": None, "source": None}
        self.write("device-market-data.json", json.dumps({"schema": "device-market-data/1", "quotes": [blank], "fx_rates": []}))
        self.write("device-api-settings.json", json.dumps({"schema": "device-api-settings/1", "api_key": "", "appkey": None, "access_token": "  "}))
        self.write("device-fx.csv", "currency,rate,as_of,available_at,source\n,,,,\n")
        self.write("empty.yaml", "schema: device-market-data/1\nquotes: []\nfx_rates: []\napi_key: null\nappsecret: ''\n")
        self.assertEqual(self.check()[0], 0)

    def test_public_price_and_fx_records_remain_allowed(self):
        self.write("public.json", json.dumps({"quotes": self.market_envelope()["quotes"], "fx_rates": self.market_envelope()["fx"]}))
        self.write("public.yaml", "quotes:\n  - security_reference: SYNTHETIC_TEST_SECURITY_ONLY\n    price: 77331.2468\n    currency: ZZZ\n")
        self.write("public.csv", "currency,rate\nZZZ,66321.1357\n")
        self.assertEqual(self.check()[0], 0)

    def test_auth_guides_schema_fields_and_source_descriptions_pass(self):
        self.write("schema.json", json.dumps({"properties": {
            "api_key": {"type": "string"}, "appsecret": {"type": "string"}, "access_token": {"type": "string"},
        }}))
        self.write("source.py", "payload = " + repr(self.api_envelope()))
        self.write("guide.md", "Use api_key in a local request.\n```json\n{\"api_key\": \"\"}\n```\n"
            "CSP example: https://example.invalid/prices?api_key=LOCAL_PARAMETER\n")
        self.write("description.yaml", "description: |\n  api_key: SYNTHETIC_TEST_CREDENTIAL_ONLY\n")
        self.assertEqual(self.check()[0], 0)

    def test_blank_yaml_credentials_with_comments_and_metadata_pass(self):
        payloads = (
            "api_key: # Local setting only\nservice: NOT_SELECTED\nenabled: false\n",
            "api_key:\nservice: NOT_SELECTED\nenabled: false\n",
            "api_key: |\nservice: NOT_SELECTED\nenabled: false\n",
        )
        for index, payload in enumerate(payloads):
            with self.subTest(case=index):
                self.assertFalse(guard.contains_device_actual(payload.encode(), "schema.yaml"))


    def test_yaml_quoted_credentials_are_strings_even_when_null_or_container_shaped(self):
        payloads = (
            "api_key: 'null'\n", "api_key: '~'\n", "api_key: '[SYNTHETIC_TEST_ONLY]'\n",
            "api_key: '{SYNTHETIC_TEST_ONLY}'\n", "api_key: '|'\n", "api_key: ' # SYNTHETIC_TEST_ONLY'\n",
            "shared: &canary 'null'\napi_key: *canary\n",
        )
        for index, payload in enumerate(payloads):
            with self.subTest(case=index):
                self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent.yaml"))

    def test_marked_partial_market_records_fail_consistently_in_yaml_and_csv(self):
        payloads = (
            "schema: device-market-data/1\nquotes:\n  - security_reference: SYNTHETIC_TEST_SECURITY_ONLY\n    price: null\n",
            "schema: device-market-data/1\nfx:\n  - currency: ZZZ\n    rate: null\n",
            "schema: device-market-data/1\nquotes:\n  - source: SYNTHETIC_TEST_MANUAL_ONLY\n    price: null\n",
            "schema,security_reference,price,currency,source\ndevice-market-data/1,SYNTHETIC_TEST_SECURITY_ONLY,,,\n",
            "schema,currency,rate,source\ndevice-market-data/1,ZZZ,,\n",
            "schema,source\ndevice-market-data/1,SYNTHETIC_TEST_MANUAL_ONLY\n",
        )
        for index, payload in enumerate(payloads):
            with self.subTest(case=index):
                self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent.dat"))


    def test_csv_duplicate_credential_headers_cannot_erase_populated_cells(self):
        for header in ("API-KEY,api_key", "api_key,api_key"):
            with self.subTest(normalized_duplicate=header.startswith("API")):
                payload = header + "\nSYNTHETIC_TEST_CREDENTIAL_ONLY,\n"
                self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent.csv"))


    def test_empty_quoted_yaml_credentials_with_inline_comments_pass(self):
        for quote in ("''", '\"\"'):
            with self.subTest(double_quote=quote.startswith('\"')):
                payload = "api_key: " + quote + " # Local setting only\n"
                self.assertFalse(guard.contains_device_actual(payload.encode(), "schema.yaml"))

    def test_yaml_quoted_alias_literals_and_anchored_comment_text_fail(self):
        payloads = (
            "shared: &blank ''\napi_key: '*blank'\n",
            "shared: &canary ' # SYNTHETIC_TEST_ONLY'\napi_key: *canary\n",
        )
        for index, payload in enumerate(payloads):
            with self.subTest(case=index):
                self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent.yaml"))


    def test_marked_yaml_market_schema_property_mappings_are_descriptions(self):
        payloads = (
            "schema: device-market-data/1\nproperties:\n  price: {type: number}\n  source: {type: string}\n",
            "schema: device-market-data/1\nproperties:\n  rate:\n    type: number\n  currency:\n    type: string\n",
        )
        for index, payload in enumerate(payloads):
            with self.subTest(case=index):
                self.assertFalse(guard.contains_device_actual(payload.encode(), "schema.yaml"))


    def test_yaml_quoted_credential_delimiters_and_multiline_text_are_populated(self):
        for quote in ("'", '\"'):
            for prefix in (",", "]", "}", "\n  "):
                with self.subTest(double_quote=quote == '\"', multiline=prefix.startswith("\n")):
                    payload = "api_key: " + quote + prefix + "SYNTHETIC_TEST_ONLY" + quote + "\n"
                    self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent.yaml"))
        payload = "shared: &canary '\n  SYNTHETIC_TEST_ONLY'\napi_key: *canary\n"
        self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent.yaml"))


    def test_multiline_quoted_credential_comment_lines_are_literal_text(self):
        payloads = (
            "api_key: '\n  # SYNTHETIC_TEST_ONLY\n  '\n",
            "shared: &canary '\n  # SYNTHETIC_TEST_ONLY\n  '\napi_key: *canary\n",
        )
        for index, payload in enumerate(payloads):
            with self.subTest(case=index):
                self.assertTrue(guard.contains_device_actual(payload.encode(), "innocent.yaml"))


    def test_escaped_whitespace_credential_fields_are_blank(self):
        payloads = (
            json.dumps({"api_key": "\n\t"}),
            'api_key: "\\n\\t"\n',
        )
        for index, payload in enumerate(payloads):
            with self.subTest(case=index):
                self.assertFalse(guard.contains_device_actual(payload.encode(), "blank.dat"))

class AppendOnlyRepositoryStateTests(unittest.TestCase):
    """Exercise real Git states; fixtures contain synthetic public text only."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old_root = guard.REPO_ROOT
        guard.REPO_ROOT = self.root
        self.addCleanup(setattr, guard, "REPO_ROOT", self.old_root)
        self.cfg = guard.load_config()
        self.register = self.cfg["append_only_exact_paths"][0]
        self.evidence = self.cfg["append_only_prefixes"][0] + "synthetic.txt"
        self.frozen = self.cfg["immutable_exact_paths"][0]
        self.original = b"Synthetic original decision.\n"
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "synthetic-test@example.invalid")
        self.git("config", "user.name", "SYNTHETIC APPEND GUARD TEST")
        self.write(self.cfg["autonomy_mode_file"], b"READ_ONLY\n")
        self.write(self.register, self.original)
        self.write(self.evidence, b"Synthetic original evidence.\n")
        self.write(self.frozen, b"Synthetic frozen artifact.\n")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(
            ["git", "--no-replace-objects", *args], cwd=self.root,
            check=True, capture_output=True, text=True,
        ).stdout

    def write(self, path, content):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(content)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "Synthetic guard state")

    def check(self, base=None):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = guard.cmd_diff(self.base if base is None else base)
        return result, json.loads(output.getvalue())

    def assert_pass(self, base=None):
        result, receipt = self.check(base)
        self.assertEqual(result, 0, receipt)
        self.assertEqual(receipt["gate_a_repository_guard"], "PASS")

    def assert_fail(self, base=None):
        result, receipt = self.check(base)
        self.assertEqual(result, 1, receipt)
        self.assertEqual(receipt["gate_a_repository_guard"], "FAIL")

    def test_real_global_config_committed_register_append_passes(self):
        self.write(self.register, self.original + b"Synthetic newly authorized decision.\n")
        self.commit()
        self.assert_pass()

    def test_staged_register_append_passes(self):
        self.write(self.register, self.original + b"Synthetic appended decision.\n")
        self.git("add", "--", self.register)
        self.assert_pass()

    def test_tracked_worktree_register_append_passes(self):
        self.write(self.register, self.original + b"Synthetic appended decision.\n")
        self.assert_pass()

    def test_utf8_crlf_and_missing_final_newline_append_preserves_bytes(self):
        self.write(self.register, "Synthetic decision 한글\r\nNo newline".encode("utf-8"))
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        with (self.root / self.register).open("ab") as file:
            file.write(b" appended bytes\n")
        self.commit()
        self.assert_pass()

    def test_empty_register_can_append(self):
        self.write(self.register, b"")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write(self.register, self.original)
        self.commit()
        self.assert_pass()

    def test_committed_register_rewrite_fails(self):
        self.write(self.register, b"Rewritten old decision.\n")
        self.commit()
        self.assert_fail()

    def test_register_truncation_fails(self):
        self.write(self.register, self.original[:-1])
        self.commit()
        self.assert_fail()

    def test_committed_delete_fails(self):
        (self.root / self.register).unlink()
        self.commit()
        self.assert_fail()

    def test_committed_rename_fails(self):
        self.git("mv", self.register, self.register + ".moved")
        self.commit()
        self.assert_fail()

    def test_register_mode_change_fails(self):
        (self.root / self.register).chmod(0o755)
        self.commit()
        self.assert_fail()

    def test_register_symlink_type_change_fails(self):
        (self.root / self.register).unlink()
        (self.root / self.register).symlink_to("missing-target")
        self.commit()
        self.assert_fail()

    def test_binary_register_append_fails(self):
        self.write(self.register, b"Synthetic\0binary")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write(self.register, b"Synthetic\0binary appended")
        self.commit()
        self.assert_fail()

    def test_non_utf8_register_append_fails(self):
        self.write(self.register, b"Synthetic\xfftext")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write(self.register, b"Synthetic\xfftext appended")
        self.commit()
        self.assert_fail()

    def test_existing_evidence_append_fails(self):
        with (self.root / self.evidence).open("ab") as file:
            file.write(b"Append still changes original evidence.\n")
        self.commit()
        self.assert_fail()

    def test_new_regular_evidence_passes(self):
        self.write(self.evidence + ".new", b"Synthetic new evidence.\n")
        self.commit()
        self.assert_pass()

    def test_new_binary_evidence_passes(self):
        self.write(self.evidence + ".bin", b"Synthetic\0binary evidence")
        self.commit()
        self.assert_pass()

    def test_new_evidence_rewrite_in_later_commit_fails(self):
        path = self.evidence + ".new"
        self.write(path, b"Synthetic new evidence.\n")
        self.commit()
        self.write(path, b"Rewritten synthetic evidence.\n")
        self.commit()
        self.assert_fail()

    def test_new_evidence_removed_in_later_commit_fails(self):
        path = self.evidence + ".new"
        self.write(path, b"Synthetic new evidence.\n")
        self.commit()
        (self.root / path).unlink()
        self.commit()
        self.assert_fail()

    def test_rewrite_then_restore_fails(self):
        self.write(self.register, b"Rewritten old decision.\n")
        self.commit()
        self.write(self.register, self.original)
        self.commit()
        self.assert_fail()

    def test_delete_then_restore_fails(self):
        (self.root / self.register).unlink()
        self.commit()
        self.write(self.register, self.original)
        self.commit()
        self.assert_fail()

    def test_rename_then_restore_fails(self):
        self.git("mv", self.register, self.register + ".moved")
        self.commit()
        self.git("mv", self.register + ".moved", self.register)
        self.commit()
        self.assert_fail()

    def test_append_then_remove_appended_bytes_fails(self):
        self.write(self.register, self.original + b"Synthetic append.\n")
        self.commit()
        self.write(self.register, self.original)
        self.commit()
        self.assert_fail()

    def test_frozen_rewrite_then_restore_fails(self):
        original = (self.root / self.frozen).read_bytes()
        self.write(self.frozen, b"Rewritten synthetic frozen artifact.\n")
        self.commit()
        self.write(self.frozen, original)
        self.commit()
        self.assert_fail()

    def test_staged_register_rewrite_fails(self):
        self.write(self.register, b"Rewritten synthetic decision.\n")
        self.git("add", "--", self.register)
        self.assert_fail()

    def test_tracked_worktree_register_rewrite_fails(self):
        self.write(self.register, b"Rewritten synthetic decision.\n")
        self.assert_fail()

    def test_staged_rewrite_hidden_by_worktree_restore_fails(self):
        self.write(self.register, b"Rewritten synthetic decision.\n")
        self.git("add", "--", self.register)
        self.write(self.register, self.original)
        self.assert_fail()

    def test_staged_delete_hidden_by_untracked_restore_fails(self):
        self.git("rm", "--", self.register)
        self.write(self.register, self.original)
        self.assert_fail()

    def test_tracked_worktree_delete_fails(self):
        (self.root / self.register).unlink()
        self.assert_fail()

    def test_worktree_mode_change_detected_with_filemode_false(self):
        self.git("config", "core.filemode", "false")
        (self.root / self.register).chmod(0o755)
        self.assert_fail()

    def test_worktree_symlink_does_not_follow_untracked_target(self):
        self.write("untracked-target.txt", self.original)
        (self.root / self.register).unlink()
        (self.root / self.register).symlink_to(self.root / "untracked-target.txt")
        self.assert_fail()

    def test_worktree_symlink_parent_does_not_follow_external_target(self):
        with tempfile.TemporaryDirectory() as external:
            parent = (self.root / self.register).parent
            (Path(external) / Path(self.register).name).write_bytes(self.original)
            parent.rename(parent.with_name("untracked-backup"))
            parent.symlink_to(external, target_is_directory=True)
            # Mode validation lives below this same directory; read it before
            # changing the parent by using another valid, tracked mode path.
            self.cfg = dict(self.cfg, autonomy_mode_file="SYNTHETIC_MODE")
            self.write("SYNTHETIC_MODE", b"READ_ONLY\n")
            old_load = guard.load_config
            guard.load_config = lambda: self.cfg
            self.addCleanup(setattr, guard, "load_config", old_load)
            self.assert_fail()

    def test_staged_new_evidence_worktree_rewrite_fails(self):
        path = self.evidence + ".new"
        self.write(path, b"Synthetic new evidence.\n")
        self.git("add", "--", path)
        self.write(path, b"Rewritten synthetic evidence.\n")
        self.assert_fail()

    def test_side_parent_rewrite_restore_is_inspected(self):
        self.git("branch", "side")
        self.write("main.txt", b"Synthetic main change.\n")
        self.commit()
        self.git("checkout", "-q", "side")
        self.write(self.register, b"Rewritten old decision.\n")
        self.commit()
        self.write(self.register, self.original)
        self.commit()
        self.git("checkout", "-q", "main")
        self.git("merge", "--no-ff", "-qm", "Synthetic merge", "side")
        self.assert_fail()

    def test_merge_result_cannot_remove_side_parent_append(self):
        self.git("branch", "side")
        self.write("main.txt", b"Synthetic main change.\n")
        self.commit()
        self.git("checkout", "-q", "side")
        self.write(self.register, self.original + b"Synthetic side append.\n")
        self.commit()
        self.git("checkout", "-q", "main")
        self.git("merge", "--no-ff", "--no-commit", "side")
        self.write(self.register, self.original)
        self.commit()
        self.assert_fail()

    def test_divergent_reference_uses_resolved_merge_base(self):
        self.git("branch", "reference")
        self.write(self.register, self.original + b"Synthetic HEAD append.\n")
        self.commit()
        self.git("checkout", "-q", "reference")
        self.write(self.register, self.original + b"Different reference append.\n")
        self.commit()
        self.git("checkout", "-q", "main")
        self.assert_pass("reference")

    def test_missing_comparison_ref_fails_closed(self):
        with self.assertRaises(guard.GuardError):
            self.check("missing-comparison-reference")

    def test_option_shaped_comparison_ref_fails_closed(self):
        with self.assertRaises(guard.GuardError):
            self.check("--help")

    def test_protected_unmerged_index_fails_closed(self):
        self.git("branch", "side")
        self.write(self.register, self.original + b"Synthetic main append.\n")
        self.commit()
        self.git("checkout", "-q", "side")
        self.write(self.register, self.original + b"Synthetic side append.\n")
        self.commit()
        self.git("checkout", "-q", "main")
        merge = subprocess.run(["git", "merge", "--no-commit", "side"], cwd=self.root, capture_output=True)
        self.assertNotEqual(merge.returncode, 0)
        with self.assertRaises(guard.GuardError):
            self.check()

    def test_evidence_filename_with_tabs_newlines_unicode_is_protected(self):
        path = self.evidence + "\t한글\n:literal"
        self.write(path, b"Synthetic original evidence.\n")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write(path, b"Rewritten evidence.\n")
        self.commit()
        self.assert_fail()

    def test_new_protected_symlink_fails(self):
        path = self.evidence + ".link"
        (self.root / path).symlink_to("missing-target")
        self.commit()
        self.assert_fail()

    def test_untracked_unregistered_private_device_file_is_not_read(self):
        self.write("untracked-device.json", b'{"schema":"device-actual-holdings/1","kind":"ACTUAL","positions":[{"symbol":"SYNTHETIC","quantity":1,"average_cost":1,"currency":"ZZZ"}]}')
        self.assert_pass()

    def test_all_configured_exact_registers_allow_preserved_text_append(self):
        for path in self.cfg["append_only_exact_paths"]:
            self.write(path, self.original)
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        for path in self.cfg["append_only_exact_paths"]:
            self.write(path, self.original + b"Synthetic append.\n")
        self.commit()
        self.assert_pass()

    def test_missing_comparison_blob_fails_closed(self):
        oid = self.git("rev-parse", self.base + ":" + self.register).strip()
        self.write(self.register, self.original + b"Synthetic append.\n")
        self.commit()
        (self.root / ".git/objects" / oid[:2] / oid[2:]).unlink()
        with self.assertRaises(guard.GuardError):
            self.check()

    def test_committed_mode_change_then_restore_fails(self):
        (self.root / self.register).chmod(0o755)
        self.commit()
        (self.root / self.register).chmod(0o644)
        self.commit()
        self.assert_fail()

    def test_staged_mode_change_with_unchanged_worktree_fails(self):
        self.git("update-index", "--chmod=+x", "--", self.register)
        self.assert_fail()

    def test_evidence_prefix_protection_wins_over_exact_log_overlap(self):
        self.cfg = dict(self.cfg, append_only_exact_paths=[*self.cfg["append_only_exact_paths"], self.evidence])
        old_load = guard.load_config
        guard.load_config = lambda: self.cfg
        self.addCleanup(setattr, guard, "load_config", old_load)
        with (self.root / self.evidence).open("ab") as file:
            file.write(b"Synthetic evidence append.\n")
        self.commit()
        self.assert_fail()

    def test_worktree_read_may_update_access_time(self):
        file = self.root / self.register
        os.utime(file, (1, file.stat().st_mtime))
        self.assert_pass()

    def test_native_graft_cannot_hide_rewrite_restore_history(self):
        self.write(self.register, b"Rewritten synthetic decision.\n")
        self.commit()
        self.write(self.register, self.original + b"Synthetic restored append.\n")
        self.commit()
        self.assert_fail()
        head = self.git("rev-parse", "HEAD").strip()
        self.write(".git/info/grafts", (head + " " + self.base + "\n").encode("ascii"))
        self.assertEqual(self.git("rev-parse", "--is-shallow-repository").strip(), "false")
        self.assertEqual(len(self.git("rev-list", self.base + "..HEAD").splitlines()), 1)
        with self.assertRaises(guard.GuardError):
            self.check()

    def test_redirected_graft_cannot_hide_rewrite_restore_history(self):
        self.write(self.register, b"Rewritten synthetic decision.\n")
        self.commit()
        self.write(self.register, self.original + b"Synthetic restored append.\n")
        self.commit()
        self.assert_fail()
        head = self.git("rev-parse", "HEAD").strip()
        with tempfile.TemporaryDirectory() as external:
            graft_file = Path(external) / "synthetic-grafts"
            graft_file.write_text(head + " " + self.base + "\n", encoding="ascii")
            child_env = dict(os.environ, GIT_GRAFT_FILE=str(graft_file))
            history = subprocess.run(
                ["git", "--no-replace-objects", "rev-list", self.base + "..HEAD"],
                cwd=self.root, env=child_env, check=True, capture_output=True, text=True,
            )
            self.assertEqual(len(history.stdout.splitlines()), 1)
            child_code = (
                "import importlib.util, pathlib, sys; "
                "s=importlib.util.spec_from_file_location('synthetic_guard',sys.argv[1]); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "m.REPO_ROOT=pathlib.Path(sys.argv[2]); "
                "sys.argv=['guard','diff','--base',sys.argv[3]]; "
                "sys.exit(m.main())"
            )
            checked = subprocess.run(
                [sys.executable, "-c", child_code, str(MODULE_PATH), str(self.root), self.base],
                cwd=self.root, env=child_env, capture_output=True, text=True,
            )
            self.assertEqual(checked.returncode, 2)
            self.assertIn("AUTONOMY_GUARD_FAIL:", checked.stderr)
            self.assertNotIn(str(graft_file), checked.stderr)


if __name__ == "__main__":
    unittest.main()
