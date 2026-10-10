"""Public artifact checks use temporary synthetic mutations, never private exports."""
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tarfile
import unittest

from investment_system.product.web_mvp import build, repository_bundle


GUARD_PATH = Path(__file__).resolve().parents[1] / "tools" / "pages_artifact_guard.py"


class PagesArtifactGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline_temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.baseline_temp.cleanup)
        cls.baseline = Path(cls.baseline_temp.name) / "site"
        bundle = deepcopy(repository_bundle())
        builder_spec = importlib.util.spec_from_file_location('public_cockpit_builder', GUARD_PATH.with_name('build_pages_cockpit.py'))
        builder = importlib.util.module_from_spec(builder_spec)
        builder_spec.loader.exec_module(builder)
        builder.build_public_cockpit(cls.baseline)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name) / "site"
        shutil.copytree(self.baseline, self.site)

    def cli(self, site=None):
        return subprocess.run(
            [sys.executable, str(GUARD_PATH), "--artifact-dir", str(site or self.site)],
            capture_output=True, text=True, check=False,
        )

    def test_approved_public_build_passes_cli(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["pages_artifact_guard"], "PASS")
        self.assertEqual(receipt["files_scanned"], 37)
        self.assertEqual(receipt["violations"], {})
        self.assertEqual(result.stderr, "")

    def scan(self, site=None):
        return self.guard().scan_artifact(site or self.site)

    def guard(self):
        spec = importlib.util.spec_from_file_location("pages_artifact_guard", GUARD_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def write_json(self, mutate, name="data.json"):
        path = self.site / name
        data = json.loads(path.read_text(encoding="utf-8"))
        mutate(data)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def assert_rejected(self, category=None):
        receipt = self.scan()
        self.assertEqual(receipt["pages_artifact_guard"], "FAIL")
        self.assertTrue(receipt["violations"])
        if category:
            self.assertGreater(receipt["violations"].get(category, 0), 0)
        return receipt

    def test_importable_scan_accepts_approved_catalog_and_ui_sources(self):
        catalog = json.loads((self.site / "actual-catalog.json").read_text())
        self.assertEqual(len(catalog["instruments"]), 19)
        self.assertTrue(all("target_units" in row for row in catalog["instruments"]))
        self.assertEqual(self.scan()["pages_artifact_guard"], "PASS")

    def test_default_build_is_price_free_and_accepted(self):
        shutil.rmtree(self.site)
        spec = importlib.util.spec_from_file_location('public_cockpit_builder', GUARD_PATH.with_name('build_pages_cockpit.py'))
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        builder.build_public_cockpit(self.site)
        self.assertEqual(self.scan()["pages_artifact_guard"], "PASS")
        data = json.loads((self.site / "data.json").read_text())
        self.assertEqual(data["companies"], [])
        self.assertIsNone(data["universe"]["data"])

    def test_pwa_icon_bytes_are_allowlisted_without_allowing_hidden_binary_data(self):
        for name in ('icon-192.png', 'icon-512.png'):
            with self.subTest(name=name):
                icon = self.site / name
                original = icon.read_bytes()
                icon.write_bytes(original + b'SYNTHETIC_PRIVATE_ICON_CANARY')
                self.assert_rejected('unapproved_content')
                icon.write_bytes(original)

    def test_legacy_ranked_membership_is_rejected_in_directory_and_tar(self):
        self.write_json(lambda data: data["universe"].update({"data": {
            "members": [{"company_id": "invented", "rank": 1}], "cutoff_mcap": 12345}}))
        receipt = self.assert_rejected("public_price_boundary")
        archive = Path(self.temp.name) / 'legacy.tar'
        with tarfile.open(archive, 'w', format=tarfile.USTAR_FORMAT) as handle:
            for path in sorted(self.site.iterdir()):
                info = handle.gettarinfo(str(path), arcname='./' + path.name)
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                with path.open('rb') as body:
                    handle.addfile(info, body)
        self.assertEqual(self.guard().validate_pages_tar(archive), receipt)

    def test_altered_assets_with_unrecognized_data_fail_pinned_manifest(self):
        for name in ("app.js", "index.html", "style.css", "research.html",
                     "device-actual.js", "device-market.js", "locale.js", "entity-search.js", "device-actual.css",
                     "private-history.js", "private-history.css"):
            with self.subTest(asset=name):
                path = self.site / name
                original = path.read_bytes()
                path.write_bytes(original + b'\n/* arbitrary renamed synthetic payload */\n')
                self.assert_rejected("unapproved_content")
                path.write_bytes(original)

    def test_renamed_or_stringified_holdings_fail_in_all_public_json(self):
        for name in ("data.json", "entities.json", "actual-catalog.json"):
            for payload in ({"renamed": [{"unrecognized": "synthetic"}]},
                            json.dumps({"quantity": "99123.4567", "average_cost": "88765.4321"})):
                with self.subTest(file=name, kind=type(payload).__name__):
                    path = self.site / name
                    original = path.read_bytes()
                    self.write_json(lambda data: data.update({"unreviewed": payload}), name)
                    self.assert_rejected("unapproved_content")
                    path.write_bytes(original)

    def test_unknown_json_fields_fail_even_when_values_are_empty(self):
        self.write_json(lambda data: data.update({"unknown_future_field": None}))
        self.assert_rejected("unapproved_content")

    def test_existing_json_fields_deletions_and_array_order_are_pinned(self):
        mutations = (
            ("data.json", lambda data: data["companies"].append({"name": "SYNTHETIC_RENAMED_ONLY"})),
            ("entities.json", lambda data: data.update({"schema_version": 999})),
            ("actual-catalog.json", lambda data: data["instruments"][0].update({"target_units": 999})),
            ("data.json", lambda data: data.pop("changes")),
            ("actual-catalog.json", lambda data: data["instruments"].reverse()),
        )
        for name, mutate in mutations:
            with self.subTest(file=name):
                original = (self.site / name).read_bytes()
                self.write_json(mutate, name)
                self.assert_rejected("unapproved_content")
                (self.site / name).write_bytes(original)

    def test_populated_sensitive_fields_are_reported_in_nested_json(self):
        cases = ("quantity", "average_cost", "averageCost", "amount", "cash", "balance",
                 "account", "account_number", "market_value", "marketValue", "money",
                 "money_value", "mcap", "cutoff_mcap", "cost_basis", "purchase_price",
                 "net_worth", "holdings", "positions", "actual_holdings")
        original = (self.site / "data.json").read_bytes()
        for key in cases:
            with self.subTest(key=key):
                self.write_json(lambda data: data.update({"nested": [{key: "99123.4567"}]}))
                self.assert_rejected("sensitive_json_fields")
                (self.site / "data.json").write_bytes(original)

    def test_zero_false_and_nested_values_are_populated_sensitive_fields(self):
        original = (self.site / "data.json").read_bytes()
        for value in (0, "0", False, {"renamed": None}, [None]):
            with self.subTest(value_type=type(value).__name__):
                self.write_json(lambda data: data.update({"quantity": value}))
                self.assert_rejected("sensitive_json_fields")
                (self.site / "data.json").write_bytes(original)

    def test_empty_sensitive_fields_still_fail_hash_without_false_populated_count(self):
        for value in (None, "", [], {}):
            with self.subTest(value_type=type(value).__name__):
                original = (self.site / "data.json").read_bytes()
                self.write_json(lambda data: data.update({"quantity": value}))
                receipt = self.assert_rejected("unapproved_content")
                self.assertNotIn("sensitive_json_fields", receipt["violations"])
                (self.site / "data.json").write_bytes(original)

    def test_private_device_schema_fails_without_any_amount_fields(self):
        for schema in ("device-actual-holdings/1", "device-actual-export/1"):
            with self.subTest(schema=schema):
                original = (self.site / "data.json").read_bytes()
                self.write_json(lambda data: data.update({"nested": {"schema": schema}}))
                self.assert_rejected("private_device_schema")
                (self.site / "data.json").write_bytes(original)

    def test_secret_injection_in_html_js_css_and_json_fails_without_leaking(self):
        canary = "SYNTHETIC_" + "CANARY_99123_88765_ONLY"
        samples = ('-----BEGIN PRIVATE KEY-----\n' + canary + '\n-----END PRIVATE KEY-----',
                   'api_key="' + canary + '"', 'access_token: "' + canary + '"',
                   'Authorization: Bearer ' + canary)
        for name in ("index.html", "app.js", "style.css"):
            original = (self.site / name).read_bytes()
            for sample in samples:
                with self.subTest(file=name, kind=sample.split()[0]):
                    (self.site / name).write_bytes(original + sample.encode())
                    receipt = self.assert_rejected("secret_patterns")
                    self.assertNotIn(canary, json.dumps(receipt))
                    (self.site / name).write_bytes(original)
        self.write_json(lambda data: data.update({"api_key": canary}))
        self.assert_rejected("secret_patterns")

    def test_extra_repo_environment_archive_and_local_files_fail_safe_diagnostics(self):
        for name in ("README.md", ".env", "private-canary.zip", "local/sensitive-canary.json",
                     ".git/config", "nested/extra.js"):
            with self.subTest(kind=Path(name).suffix):
                path = self.site / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("SYNTHETIC_ONLY", encoding="utf-8")
                receipt = self.assert_rejected("unexpected_entries")
                diagnostic = json.dumps(receipt)
                self.assertNotIn(name, diagnostic)
                self.assertNotIn("SYNTHETIC_ONLY", diagnostic)
                path.unlink()
                if path.parent != self.site:
                    path.parent.rmdir()

    def test_missing_expected_file_fails(self):
        (self.site / "actual-catalog.json").unlink()
        self.assert_rejected("missing_files")

    def test_symlink_file_and_directory_fail_without_following_targets(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "synthetic-private.json").write_text('{"quantity":"99123.4567"}')
        (self.site / "outside-link").symlink_to(outside, target_is_directory=True)
        self.assert_rejected("nonregular_entries")
        (self.site / "outside-link").unlink()
        (self.site / "data.json").unlink()
        (self.site / "data.json").symlink_to(outside / "synthetic-private.json")
        receipt = self.assert_rejected("nonregular_entries")
        self.assertNotIn("sensitive_json_fields", receipt["violations"])

    def test_symlink_artifact_root_fails(self):
        link = Path(self.temp.name) / "site-link"
        link.symlink_to(self.site, target_is_directory=True)
        self.assertEqual(self.scan(link)["pages_artifact_guard"], "FAIL")

    def test_nonregular_fifo_fails_without_opening(self):
        os.mkfifo(self.site / "injected-fifo")
        self.assert_rejected("nonregular_entries")

    def test_missing_or_nondirectory_root_fails_cli_without_paths_or_traceback(self):
        for path in (Path(self.temp.name) / "absent-private-canary", self.site / "app.js"):
            with self.subTest(kind=path.exists()):
                result = self.cli(path)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stdout)["pages_artifact_guard"], "FAIL")
                self.assertEqual(result.stderr, "")
                self.assertNotIn(str(path), result.stdout)

    def test_invalid_json_duplicate_keys_and_nonfinite_numbers_fail(self):
        for payload in ('{broken', '{"quantity":null,"quantity":"99123.4567"}',
                        '{"quantity":null,"\\u0071uantity":"SYNTHETIC_ONLY"}',
                        '{"unrecognized":NaN}', '{"unrecognized":Infinity}',
                        '{"unrecognized":1e999}', '{"unrecognized":"\\ud800"}'):
            with self.subTest(kind=payload[:15]):
                (self.site / "data.json").write_text(payload, encoding="utf-8")
                self.assert_rejected("invalid_format")

    def test_invalid_utf8_and_binary_text_files_fail(self):
        for name, payload in (("data.json", b'\xff'), ("app.js", b'\xff'),
                              ("index.html", b'\x00binary'), ("style.css", b'\x01binary')):
            with self.subTest(file=name):
                original = (self.site / name).read_bytes()
                (self.site / name).write_bytes(payload)
                self.assert_rejected("invalid_format")
                (self.site / name).write_bytes(original)

    def test_oversized_and_extremely_nested_payloads_fail_safely(self):
        (self.site / "app.js").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        self.assert_rejected("oversized_files")
        (self.site / "app.js").write_bytes((self.baseline / "app.js").read_bytes())
        (self.site / "data.json").write_text("[" * 1200 + "0" + "]" * 1200)
        self.assert_rejected("invalid_format")

    def test_canonical_json_reformatting_remains_approved(self):
        for name in ("data.json", "entities.json", "actual-catalog.json"):
            self.write_json(lambda data: None, name)
            path = self.site / name
            path.write_text(json.dumps(json.loads(path.read_text()), indent=2, sort_keys=True))
        self.assertEqual(self.scan()["pages_artifact_guard"], "PASS")

    def test_cli_malformed_json_never_emits_parser_values_or_paths(self):
        for payload in ('{"SYNTHETIC_CANARY_99123_ONLY":',
                        '{"quantity":null,"\\u0071uantity":"SYNTHETIC_CANARY_99123_ONLY"}',
                        '{"unrecognized":"\\ud800"}', "[" * 1200 + "0" + "]" * 1200):
            with self.subTest(kind=payload[:2]):
                (self.site / "data.json").write_text(payload)
                result = self.cli()
                self.assertEqual(result.returncode, 1)
                receipt = json.loads(result.stdout)
                self.assertGreater(receipt["violations"].get("invalid_format", 0), 0)
                self.assertNotIn("SYNTHETIC_CANARY", result.stdout)
                self.assertNotIn(str(self.site), result.stdout)
                self.assertEqual(result.stderr, "")

    def test_cli_failure_diagnostics_contain_only_status_and_counts(self):
        canary = "SYNTHETIC_" + "PRIVATE_99123_88765_ONLY"
        self.write_json(lambda data: data.update({"quantity": canary}))
        result = self.cli()
        self.assertEqual(result.returncode, 1)
        receipt = json.loads(result.stdout)
        self.assertEqual(set(receipt), {"pages_artifact_guard", "files_scanned", "violations"})
        self.assertTrue(all(isinstance(count, int) for count in receipt["violations"].values()))
        self.assertNotIn(canary, result.stdout + result.stderr)
        self.assertNotIn(str(self.site), result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")

    def test_invalid_cli_arguments_fail_without_echoing_paths_or_values(self):
        for args in ([], ["--artifact-dir"],
                     ["--artifact-dir", str(self.site), "--pages-artifact", "SYNTHETIC_PRIVATE_ARG_ONLY"],
                     ["--artifact-dir", str(self.site), "SYNTHETIC_PRIVATE_ARG_ONLY"]):
            with self.subTest(argument_count=len(args)):
                result = subprocess.run(
                    [sys.executable, str(GUARD_PATH), *args],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 1)
                receipt = json.loads(result.stdout)
                self.assertEqual(receipt["violations"], {"invalid_arguments": 1})
                self.assertNotIn("SYNTHETIC_PRIVATE_ARG_ONLY", result.stdout)
                self.assertNotIn(str(self.site), result.stdout)
                self.assertEqual(result.stderr, "")

    def make_tar(self, *, extras=(), omit=(), root=True, format=tarfile.GNU_FORMAT):
        archive_path = Path(self.temp.name) / "artifact.tar"
        with tarfile.open(archive_path, "w", format=format) as archive:
            if root:
                info = tarfile.TarInfo("./")
                info.type = tarfile.DIRTYPE
                archive.addfile(info)
            for path in sorted(self.site.iterdir()):
                if path.name in omit:
                    continue
                info = tarfile.TarInfo("./" + path.name)
                payload = path.read_bytes()
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
            for info, payload in extras:
                archive.addfile(info, io.BytesIO(payload))
        return archive_path

    def tar_receipt(self, path=None):
        return self.guard().validate_pages_tar(path or self.make_tar())

    def test_github_pages_tar_shape_passes_same_guard(self):
        receipt = self.tar_receipt()
        self.assertEqual(receipt["pages_artifact_guard"], "PASS")
        self.assertEqual(receipt["files_scanned"], 37)
        self.assertEqual(receipt["violations"], {})

    def test_exact_upload_action_tar_command_with_normalized_owners_passes(self):
        archive_path = Path(self.temp.name) / "action-artifact.tar"
        environment = os.environ.copy()
        environment["TAR_OPTIONS"] = "--owner=0 --group=0 --numeric-owner"
        subprocess.run(
            ["tar", "--dereference", "--hard-dereference", "--directory", str(self.site),
             "-cf", str(archive_path), "--exclude=.git", "--exclude=.github", "."],
            env=environment, capture_output=True, check=True,
        )
        self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "PASS")

    def test_tar_cli_passes_and_emits_only_same_safe_receipt(self):
        archive_path = self.make_tar()
        result = subprocess.run(
            [sys.executable, str(GUARD_PATH), "--pages-artifact", str(archive_path)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["pages_artifact_guard"], "PASS")
        self.assertEqual(result.stderr, "")

    def test_tar_file_names_without_dot_prefix_are_allowed(self):
        archive_path = Path(self.temp.name) / "artifact.tar"
        with tarfile.open(archive_path, "w", format=tarfile.GNU_FORMAT) as archive:
            for path in self.site.iterdir():
                info = tarfile.TarInfo(path.name)
                payload = path.read_bytes()
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
        self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "PASS")

    def test_tar_rejects_absolute_traversal_nested_and_unknown_paths_without_extracting(self):
        for name in ("/tmp/private-canary.json", "../outside.json", "./../outside.json",
                     "./local/holdings.json", "./.git/config", "./.env", "./extra.zip",
                     "./nested/../app.js", ".//app.js", "././app.js", "app.js/"):
            with self.subTest(kind=name[:5]):
                payload = b'{"quantity":"99123.4567"}'
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                archive_path = self.make_tar(extras=((info, payload),))
                receipt = self.tar_receipt(archive_path)
                self.assertEqual(receipt["pages_artifact_guard"], "FAIL")
                self.assertNotIn(name, json.dumps(receipt))
                self.assertFalse((Path(self.temp.name) / "outside.json").exists())

    def test_tar_rejects_duplicate_expected_files_even_if_both_are_approved(self):
        payload = (self.site / "app.js").read_bytes()
        for name in ("app.js", "./app.js"):
            with self.subTest(prefix=name[:2]):
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                receipt = self.tar_receipt(self.make_tar(extras=((info, payload),)))
                self.assertEqual(receipt["pages_artifact_guard"], "FAIL")
                self.assertGreater(receipt["violations"].get("duplicate_entries", 0), 0)

    def test_tar_rejects_symlink_hardlink_directory_fifo_and_sparse_members(self):
        for type_ in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE,
                      tarfile.FIFOTYPE, tarfile.GNUTYPE_SPARSE):
            with self.subTest(type=type_):
                info = tarfile.TarInfo("./app.js")
                info.type = type_
                info.linkname = "../outside-private-canary"
                receipt = self.tar_receipt(self.make_tar(extras=((info, b""),), omit=("app.js",)))
                self.assertEqual(receipt["pages_artifact_guard"], "FAIL")
                self.assertGreater(receipt["violations"].get("nonregular_entries", 0), 0)

    def test_tar_rejects_changed_private_json_and_missing_public_catalog(self):
        self.write_json(lambda data: data.update({"quantity": "99123.4567"}))
        receipt = self.tar_receipt()
        self.assertEqual(receipt["pages_artifact_guard"], "FAIL")
        self.assertGreater(receipt["violations"].get("sensitive_json_fields", 0), 0)
        shutil.copyfile(self.baseline / "data.json", self.site / "data.json")
        receipt = self.tar_receipt(self.make_tar(omit=("actual-catalog.json",)))
        self.assertGreater(receipt["violations"].get("missing_files", 0), 0)

    def test_tar_rejects_pax_metadata_and_compressed_archives(self):
        payload = (self.site / "app.js").read_bytes()
        info = tarfile.TarInfo("./app.js")
        info.size = len(payload)
        info.pax_headers = {"comment": "SYNTHETIC_PRIVATE_CANARY_ONLY"}
        archive_path = self.make_tar(extras=((info, payload),), omit=("app.js",), format=tarfile.PAX_FORMAT)
        self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "FAIL")
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(self.site, arcname=".")
        self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "FAIL")

    def test_tar_rejects_hidden_gnu_longname_and_longlink_metadata(self):
        for type_, metadata in ((tarfile.GNUTYPE_LONGNAME, b"./app.js\x00"),
                                (tarfile.GNUTYPE_LONGLINK, b"SYNTHETIC_PRIVATE_CANARY\x00")):
            with self.subTest(type=type_):
                hidden = tarfile.TarInfo("././@LongLink")
                hidden.type = type_
                hidden.size = len(metadata)
                approved = tarfile.TarInfo("./app.js")
                payload = (self.site / "app.js").read_bytes()
                approved.size = len(payload)
                archive_path = self.make_tar(
                    extras=((hidden, metadata), (approved, payload)), omit=("app.js",),
                )
                self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "FAIL")

    def test_tar_rejects_unchecked_trailing_data_and_member_padding(self):
        archive_path = self.make_tar()
        archive_path.write_bytes(archive_path.read_bytes() + b'{"quantity":"SYNTHETIC_ONLY"}')
        with self.subTest(kind="trailing"):
            self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "FAIL")
        archive_path = self.make_tar()
        with tarfile.open(archive_path, "r:") as archive:
            member = next(member for member in archive if member.isfile() and member.size % 512)
            padding_offset = member.offset_data + member.size
        payload = bytearray(archive_path.read_bytes())
        payload[padding_offset] = ord("X")
        archive_path.write_bytes(payload)
        with self.subTest(kind="padding"):
            self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "FAIL")

    def test_tar_rejects_private_data_in_regular_header_metadata(self):
        payload = (self.site / "app.js").read_bytes()
        for field in ("uname", "gname", "linkname"):
            with self.subTest(field=field):
                info = tarfile.TarInfo("./app.js")
                info.size = len(payload)
                setattr(info, field, "SYNTHETIC_PRIVATE_CANARY_ONLY")
                receipt = self.tar_receipt(self.make_tar(extras=((info, payload),), omit=("app.js",)))
                self.assertEqual(receipt["pages_artifact_guard"], "FAIL")
                self.assertNotIn("SYNTHETIC_PRIVATE_CANARY", json.dumps(receipt))

    def test_tar_rejects_ignored_numeric_suffixes_and_unused_device_numbers(self):
        for start, field in ((108, b"0\x00123456"), (136, b"0\x001234567\x00\x00\x00"),
                             (329, b"1234567\x00"), (337, b"1234567\x00")):
            with self.subTest(header_field_offset=start):
                archive_path = self.make_tar()
                with tarfile.open(archive_path, "r:") as archive:
                    offset = next(member.offset for member in archive if member.name.endswith("/app.js"))
                payload = bytearray(archive_path.read_bytes())
                payload[offset + start:offset + start + len(field)] = field
                payload[offset + 148:offset + 156] = b" " * 8
                checksum = sum(payload[offset:offset + 512])
                payload[offset + 148:offset + 156] = f"{checksum:06o}".encode() + b"\x00 "
                archive_path.write_bytes(payload)
                self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "FAIL")

    def test_tar_missing_symlink_binary_oversized_and_truncated_archives_fail_safely(self):
        archive_path = Path(self.temp.name) / "missing-private-canary.tar"
        self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "FAIL")
        archive_path.symlink_to(self.make_tar())
        self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "FAIL")
        archive_path.unlink()
        for payload in (b"not an archive", b"x" * (4 * 1024 * 1024 + 1)):
            archive_path.write_bytes(payload)
            self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "FAIL")
        valid = self.make_tar()
        archive_path.write_bytes(valid.read_bytes()[:10000])
        self.assertEqual(self.tar_receipt(archive_path)["pages_artifact_guard"], "FAIL")


if __name__ == "__main__":
    unittest.main()
