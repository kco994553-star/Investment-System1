"""Exercise the deployment entry points without credentials or live requests."""
import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "tools/deploy_private_history_worker.py"
TOKEN = "synthetic_" + "t" * 36
ACCOUNT = "ab" * 16
EMAIL = "synthetic.owner" + "@" + "example.invalid"
ORIGIN = "https://private-investment-history.test-owner.workers.dev"

if HELPER.exists():
    spec = importlib.util.spec_from_file_location("worker_deployment", HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
else:
    helper = None


class HelperAvailabilityTests(unittest.TestCase):
    def test_diagnostic_entry_point_exists(self):
        self.assertTrue(HELPER.exists(), "Testable deployment diagnostic helper is missing")


@unittest.skipIf(helper is None, "Helper not implemented yet")
class DeploymentDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.summary = Path(self.temp.name) / "summary"
        self.output = Path(self.temp.name) / "output"
        self.env = {"CLOUDFLARE_API_TOKEN": " \n" + TOKEN + "\t ",
                    "CLOUDFLARE_ACCOUNT_ID": " \n" + ACCOUNT + "\t ",
                    "GITHUB_STEP_SUMMARY": str(self.summary), "GITHUB_OUTPUT": str(self.output)}
        self.calls = []
        self.sleeps = []

    def execute(self, results, operation="deploy", transport=None):
        sequence = iter(results)

        def runner(command, **kwargs):
            self.calls.append((command, kwargs))
            value = next(sequence)
            if isinstance(value, Exception):
                raise value
            return value

        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            status = helper.main(operation, environ=self.env, runner=runner, transport=transport,
                                 sleep=self.sleeps.append)
        self.logs = captured.getvalue()
        self.summary_text = self.summary.read_text() if self.summary.exists() else ""
        self.output_text = self.output.read_text() if self.output.exists() else ""
        self.public = self.logs + self.summary_text + self.output_text
        return status

    def result(self, text="", status=0, stderr=""):
        return SimpleNamespace(returncode=status, stdout=text, stderr=stderr)

    def whoami(self):
        return self.result("Logged in with an API Token.\n" + EMAIL + "\nAccount ID: " + ACCOUNT)

    def assert_private(self, *values):
        import html
        import re
        readable = html.unescape(re.sub(r"\\([\\`*_{}\[\]()#!|~])", r"\1", self.public))
        for value in (TOKEN, ACCOUNT, EMAIL, *values):
            self.assertFalse(value in self.public or value in readable,
                             "Sensitive value escaped into public diagnostic sinks")

    def test_ambiguous_overencoded_diagnostics_fail_closed_with_codes_preserved(self):
        from urllib.parse import quote
        encoded = "https://private-probe.invalid/private-session-path"
        for _ in range(8):
            encoded = quote(encoded, safe="")
        text = "[ERROR] Request failed " + encoded + " [code: 10000]"
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assert_private("private-probe.invalid", "private-session-path")
        self.assertIn("10000", self.summary_text)
        self.assertIn("Encoded diagnostic omitted", self.summary_text)

    def test_canonicalization_work_is_bounded_for_large_error_lines(self):
        text = "[ERROR] Request failed " + "\\u0041" * 100000 + " [code: 10000]"
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assertLess(len(self.summary_text), 5000)
        self.assertIn("10000", self.summary_text)

    def test_truncated_or_unterminated_control_strings_do_not_leave_secret_prefixes(self):
        first, last = TOKEN[:12], TOKEN[12:]
        for suffix in ("\x1b]0;unfinished", "\x1b]0;" + "z" * 20000 + "\x07" + last):
            self.summary.write_text("")
            text = "[ERROR] Credential rejected: " + first + suffix + " [code: 10000]"
            self.assertEqual(self.execute([self.result(text, 1)]), 1)
            self.assert_private(first, last)
            self.assertIn("10000", self.summary_text)

    def test_multiline_osc_bel_control_cannot_publish_short_credential_suffix(self):
        private_token = "unit_" + "a7" * 17 + "q"
        self.env["CLOUDFLARE_API_TOKEN"] = " \n" + private_token + "\t "
        first, last = private_token[:28], private_token[28:]
        text = "[ERROR] Credential rejected: " + first + "\x1b]0;title\nshort\x07" + last + " [code: 10000]"
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assert_private(private_token, first, last)
        self.assertIn("10000", self.summary_text)
        self.assertIn("Credential rejected", self.summary_text)

    def test_multiline_dcs_st_control_cannot_publish_short_credential_suffix(self):
        private_token = "unit_" + "a7" * 17 + "q"
        self.env["CLOUDFLARE_API_TOKEN"] = " \n" + private_token + "\t "
        first, last = private_token[:28], private_token[28:]
        text = "[ERROR] Credential rejected: " + first + "\x1bPq\nz\x1b\\" + last + " [code: 10000]"
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assert_private(private_token, first, last)
        self.assertIn("10000", self.summary_text)
        self.assertIn("Credential rejected", self.summary_text)

    def test_encoded_multiline_control_is_processed_before_summary_line_selection(self):
        private_token = "unit_" + "a7" * 17 + "q"
        self.env["CLOUDFLARE_API_TOKEN"] = private_token
        first, last = private_token[:28], private_token[28:]
        text = "[ERROR] Credential rejected: " + first + "\\u001b]0;title\nshort\\u0007" + last + " [code: 10000]"
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assert_private(private_token, first, last)
        self.assertIn("10000", self.summary_text)

    def test_oversized_crossline_control_omits_whole_diagnostic_not_suffix(self):
        private_token = "unit_" + "a7" * 17 + "q"
        self.env["CLOUDFLARE_API_TOKEN"] = private_token
        first, last = private_token[:28], private_token[28:]
        text = "[ERROR] Credential rejected: " + first + "\x1b]0;" + "z" * 13000 + "\nq\x07" + last + " [code: 10000]"
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assert_private(private_token, first, last)
        self.assertIn("10000", self.summary_text)

    def test_failed_whoami_reports_code_and_stops_before_deploy(self):
        status = self.execute([self.result("[ERROR] Authentication error [code: 10000]", 1)])
        self.assertEqual(status, 1)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("10000", self.summary_text)
        self.assertIn("Authentication error", self.summary_text)
        self.assertEqual(self.output_text, "")

    def test_account_access_must_be_confirmed_before_deploy(self):
        status = self.execute([self.result("Logged in with an API Token. No accounts available.")])
        self.assertEqual(status, 1)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("ACCOUNT_ACCESS_UNCONFIRMED", self.public)

    def test_credentials_trimmed_in_both_pinned_subprocesses(self):
        self.assertEqual(self.execute([self.whoami(), self.result(ORIGIN)]), 0)
        self.assertEqual(len(self.calls), 2)
        for command, kwargs in self.calls:
            self.assertEqual(command[:3], ["npx", "--yes", "wrangler@4.149.0"])
            self.assertTrue(kwargs["capture_output"])
            self.assertTrue(kwargs["text"])
            self.assertTrue(kwargs["env"]["CLOUDFLARE_API_TOKEN"] == TOKEN, "Token was not trimmed")
            self.assertTrue(kwargs["env"]["CLOUDFLARE_ACCOUNT_ID"] == ACCOUNT, "Account credential was not trimmed")
            self.assertEqual(kwargs["env"]["WRANGLER_SEND_METRICS"], "false")
        self.assertEqual(self.output_text, "origin=" + ORIGIN + "\n")
        self.assert_private()

    def test_blank_credentials_do_not_spawn(self):
        for key in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
            with self.subTest(credential=key):
                self.env[key] = " \t\n"
                self.assertEqual(self.execute([]), 1)
                self.assertEqual(self.calls, [])
                self.assertIn("CREDENTIALS_MISSING", self.public)

    def test_failure_redacts_credentials_email_bearer_and_urls(self):
        bearer = "unconfigured_" + "q" * 35
        url = "https://api.cloudflare.com/client/v4/accounts/" + ACCOUNT + "?token=" + TOKEN
        text = "[ERROR] Authentication failed [code: 10000]\nToken " + TOKEN + " account " + ACCOUNT + " owner " + EMAIL + " Bearer " + bearer + " " + url
        self.assertEqual(self.execute([self.whoami(), self.result(text, 1, text)]), 1)
        self.assert_private(bearer, url, "api.cloudflare.com")
        self.assertIn("10000", self.summary_text)
        self.assertIn("Authentication failed", self.summary_text)

    def test_summary_escapes_untrusted_markup_and_workflow_commands(self):
        text = "[ERROR] <script>alert(1)</script> [x](javascript:evil) `code` *bold*\n::warning::forged [code: 10001]"
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assertNotIn("<script>", self.public)
        self.assertNotIn("[x](javascript:evil)", self.public)
        self.assertNotIn("`code`", self.public)
        self.assertNotIn("::warning::", self.logs)
        self.assertIn("&lt;script&gt;", self.summary_text)

    def test_timeout_payload_stays_private_at_either_stage(self):
        for stage in ("whoami", "deploy"):
            with self.subTest(stage=stage):
                self.calls.clear()
                self.summary.write_text("")
                error = subprocess.TimeoutExpired([TOKEN], 20, output=TOKEN + EMAIL, stderr=ACCOUNT)
                results = [error] if stage == "whoami" else [self.whoami(), error]
                self.assertEqual(self.execute(results), 1)
                self.assertIn("TIMEOUT", self.public)
                self.assert_private()

    def test_os_error_does_not_leak_exception(self):
        self.assertEqual(self.execute([OSError(TOKEN + EMAIL + ACCOUNT)]), 1)
        self.assertIn("COMMAND_FAILED", self.public)
        self.assert_private()

    def test_cli_output_without_recognizable_error_is_not_echoed(self):
        self.assertEqual(self.execute([self.result("unexpected private payload " + TOKEN, 1)]), 1)
        self.assertNotIn("unexpected private payload", self.public)
        self.assertIn("No structured Wrangler error", self.summary_text)
        self.assert_private()

    def test_success_requires_strict_workers_origin(self):
        invalid = [ORIGIN + ".evil.invalid", ORIGIN + "/history", ORIGIN + "?token=" + TOKEN,
                   ORIGIN + "#fragment", ORIGIN.replace("https://", "http://"),
                   ORIGIN.replace("https://", "https://" + TOKEN + "@"),
                   "https://other.test-owner.workers.dev"]
        for url in invalid:
            with self.subTest(case=invalid.index(url)):
                self.calls.clear()
                self.summary.write_text("")
                self.assertEqual(self.execute([self.whoami(), self.result(url)]), 1)
                self.assertEqual(self.output_text, "")
                self.assertIn("URL_UNAVAILABLE", self.public)
                self.assert_private()

    def test_error_codes_are_only_numeric_not_injected_text(self):
        self.assertEqual(self.execute([self.result("[ERROR] Denied [code: " + TOKEN + "] [code: 10003]", 1)]), 1)
        self.assertIn("10003", self.summary_text)
        self.assert_private()

    def test_summary_diagnostic_is_bounded(self):
        self.assertEqual(self.execute([self.result("[ERROR] " + "A" * 10000, 1)]), 1)
        self.assertLess(len(self.summary_text), 5000)

    def test_account_id_embedded_in_other_identifier_does_not_confirm_access(self):
        self.assertEqual(self.execute([self.result("X" + ACCOUNT + "X")]), 1)
        self.assertEqual(len(self.calls), 1)

    def test_failed_whoami_does_not_claim_token_valid(self):
        self.assertEqual(self.execute([self.result("[ERROR] Authentication error [code: 10000]", 1)]), 1)
        self.assertNotIn("Token validity: confirmed", self.public)

    def test_success_summary_confirms_preflight_without_identity(self):
        self.assertEqual(self.execute([self.whoami(), self.result(ORIGIN)]), 0)
        self.assertIn("Token validity: confirmed", self.summary_text)
        self.assertIn("Configured account access: confirmed", self.summary_text)
        self.assert_private()

    def test_negated_whoami_cannot_confirm_token_validity(self):
        result = self.result("You are not logged in with an API Token. Account ID: " + ACCOUNT)
        self.assertEqual(self.execute([result, self.result(ORIGIN)]), 1)
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("Token validity: confirmed", self.public)

    def test_short_unknown_labeled_secret_and_non_http_urls_are_redacted(self):
        unknown = "small-key"
        private_url = "wss://private.invalid/session"
        text = '[ERROR] Invalid api_token="' + unknown + '"; failed endpoint ' + private_url + ' [code: 10000]'
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assert_private(unknown, private_url, "private.invalid")

    def test_json_formatted_short_unknown_secret_is_redacted(self):
        unknown = "short-key"
        text = '[ERROR] Invalid credentials: {"api_token": "' + unknown + '", "secret": "other-key"} [code: 10000]'
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assert_private(unknown, "other-key")

    def test_json_escaped_url_is_redacted_before_summary(self):
        hostname = "private-probe.invalid"
        path = "/private-session-path"
        url = "https://" + hostname + path
        text = '[ERROR] Request failed: {"url": "' + url.replace("/", "\\/") + '"} [code: 10000]'
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assert_private(hostname, path)
        self.assertIn("Request failed", self.summary_text)

    def test_json_unicode_escaped_email_is_redacted_before_summary(self):
        private_email = "probe" + "@" + "e.io"
        encoded = private_email.replace("@", "\\u0040").replace(".", "\\u002e")
        text = '[ERROR] Invalid identity {"email": "' + encoded + '"} [code: 10000]'
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assert_private(encoded, "probe", "e.io")
        self.assertIn("Invalid identity", self.summary_text)

    def test_osc_control_sequence_within_known_token_is_removed_before_redaction(self):
        first, last = TOKEN[:12], TOKEN[12:]
        for terminator in ("\x07", "\x1b\\"):
            self.summary.write_text("")
            decorated = first + "\x1b]0;terminal-title" + terminator + last
            text = "[ERROR] Credential rejected: " + decorated + " [code: 10000]"
            self.assertEqual(self.execute([self.result(text, 1)]), 1)
            self.assert_private(first, last, "terminal-title")

    def test_nested_json_percent_encoded_sensitive_values_are_canonicalized(self):
        from urllib.parse import quote
        url = "https://private-probe.invalid/private-session-path"
        encoded = quote(quote(url, safe=""), safe="")
        text = "[ERROR] Request failed " + encoded + " owner " + EMAIL.replace("@", "\\\\u0040") + " [code: 10000]"
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assert_private(encoded, "private-probe.invalid", "private-session-path", EMAIL.split("@")[0])

    def test_percent_encoded_terminal_controls_cannot_split_known_credential(self):
        from urllib.parse import quote
        first, last = TOKEN[:12], TOKEN[12:]
        text = "[ERROR] Credential rejected: " + first + quote("\x1b]0;title\x07", safe="") + last + " [code: 10000]"
        self.assertEqual(self.execute([self.result(text, 1)]), 1)
        self.assert_private(first, last)

    def test_metadata_line_cannot_confirm_configured_account_access(self):
        result = self.result("Logged in with an API Token.\nConfigured account: " + ACCOUNT + "\nNo accounts available.")
        self.assertEqual(self.execute([result, self.result(ORIGIN)]), 1)
        self.assertEqual(len(self.calls), 1)

    def test_pinned_wrangler_emoji_and_account_table_output_is_supported(self):
        output = "👋 You are logged in with an API Token, associated with the email " + EMAIL + ".\n"
        output += "┌──────────────┬──────────────────────────────────┐\n│ Account Name │ Account ID                       │\n"
        output += "│ Example      │ " + ACCOUNT + " │\n└──────────────┴──────────────────────────────────┘"
        self.assertEqual(self.execute([self.result(output), self.result(ORIGIN)]), 0)
        self.assert_private()

    def test_account_api_token_identity_output_is_supported(self):
        output = "👋 You are logged in with an Account API Token, associated with the account Example.\n│ Example │ " + ACCOUNT + " │"
        self.assertEqual(self.execute([self.result(output), self.result(ORIGIN)]), 0)
        self.assert_private()

    def test_user_api_token_identity_output_is_supported(self):
        output = "👋 You are logged in with an User API Token, associated with the email " + EMAIL + ".\n│ Example │ " + ACCOUNT + " │"
        self.assertEqual(self.execute([self.result(output), self.result(ORIGIN)]), 0)
        self.assert_private()

    def test_anonymous_checks_use_explicit_user_agent_and_keep_existing_contract(self):
        self.env["WORKER_ORIGIN"] = ORIGIN
        requests = []
        request_headers = []
        read_limits = []

        class Response:
            def __init__(self, index):
                self.status = 403
                self.headers = {"Cache-Control": "private, no-store, max-age=0"}
                if index == 2:
                    self.headers["Access-Control-Allow-Origin"] = "https://kco994553-star.github.io"
                self.code = "AUTH_FORBIDDEN" if index == 2 else "ORIGIN_FORBIDDEN"
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit):
                read_limits.append(limit)
                return json.dumps({"error": {"code": self.code}}).encode()

        def transport(request, timeout):
            requests.append(request)
            request_headers.append(dict(request.header_items()))
            return Response(len(requests) - 1)

        self.assertEqual(self.execute([], "verify", transport), 0)
        self.assertEqual(len(requests), 3)
        user_agent = "InvestmentSystem1-DeploymentVerification/1.0"
        expected_headers = [
            {"User-agent": user_agent},
            {"User-agent": user_agent, "Origin": "https://invalid-origin.example"},
            {"User-agent": user_agent, "Origin": helper.ALLOWED_ORIGIN},
        ]
        self.assertTrue(request_headers == expected_headers,
                        "Anonymous request headers do not match verification contract")
        self.assertEqual(read_limits, [4097] * 3)
        self.assertTrue(all(request.full_url == ORIGIN + "/history?symbol=NVDA&range=1mo" for request in requests))
        self.assertTrue(all(request.get_header("Authorization") is None for request in requests))
        self.assertIn("App feature remains OFF", self.summary_text)
        self.assert_private()

    def test_verify_retries_transport_and_pending_config_without_logging_payloads(self):
        self.env["WORKER_ORIGIN"] = ORIGIN
        requests = []
        class Response:
            def __init__(self, allowed, pending=False):
                self.status = 503 if pending else 403
                self.headers = {"Cache-Control": "private, no-store, max-age=0"}
                if allowed:
                    self.headers["Access-Control-Allow-Origin"] = helper.ALLOWED_ORIGIN
                self.code = "CONFIG_UNAVAILABLE" if pending else "AUTH_FORBIDDEN" if allowed else "ORIGIN_FORBIDDEN"
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return json.dumps({"error": {"code": self.code}}).encode()
        pending_count = 0
        def transport(request, timeout):
            nonlocal pending_count
            self.assertEqual(timeout, 10)
            requests.append(request)
            if len(requests) == 1:
                raise RuntimeError(TOKEN + EMAIL + ACCOUNT)
            allowed = request.get_header("Origin") == helper.ALLOWED_ORIGIN
            if allowed and pending_count < 2:
                pending_count += 1
                return Response(True, pending=True)
            return Response(allowed)
        self.assertEqual(self.execute([], "verify", transport), 0)
        self.assertEqual(self.sleeps, [2, 2, 4])
        self.assertEqual(len(requests), 6)
        self.assertNotIn("CONFIG_UNAVAILABLE", self.public)
        self.assertEqual(len(self.logs.splitlines()), 2)
        self.assertIn("NO_ORIGIN: HTTP 403 ORIGIN_FORBIDDEN", self.logs)
        self.assertIn("ALLOWED_ORIGIN_NO_AUTH: HTTP 403 AUTH_FORBIDDEN", self.logs)
        self.assertTrue(all(request.get_header("Authorization") is None for request in requests))
        self.assertTrue(all(request.get_method() == "GET" and request.data is None for request in requests))
        self.assert_private()

    def test_verify_pending_config_exhausts_bounded_retries_and_fails_closed(self):
        self.env["WORKER_ORIGIN"] = ORIGIN
        requests = []
        class Response:
            def __init__(self, allowed):
                self.status = 503 if allowed else 403
                self.headers = {"Cache-Control": "private, no-store, max-age=0"}
                if allowed: self.headers["Access-Control-Allow-Origin"] = helper.ALLOWED_ORIGIN
                self.code = "CONFIG_UNAVAILABLE" if allowed else "ORIGIN_FORBIDDEN"
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return json.dumps({"error": {"code": self.code}}).encode()
        def transport(request, timeout):
            requests.append(request)
            return Response(request.get_header("Origin") == helper.ALLOWED_ORIGIN)
        self.assertEqual(self.execute([], "verify", transport), 1)
        self.assertEqual(self.sleeps, [2, 4, 8, 16])
        self.assertEqual(len(requests), 7)
        self.assertIn("ANONYMOUS_AUTH_CONFIG_CHECK_FAILED", self.public)
        self.assertNotIn("NO_ORIGIN: HTTP", self.logs)
        self.assert_private()

    def test_anonymous_transport_exception_is_not_echoed(self):
        self.env["WORKER_ORIGIN"] = ORIGIN
        def transport(*args, **kwargs): raise RuntimeError(TOKEN + EMAIL + ACCOUNT)
        self.assertEqual(self.execute([], "verify", transport), 1)
        self.assertIn("TRANSPORT_FAILED", self.public)
        self.assertEqual(self.sleeps, [2, 4, 8, 16])
        self.assert_private()

    def test_anonymous_invalid_origin_never_calls_transport(self):
        self.env["WORKER_ORIGIN"] = ORIGIN + ".evil.invalid"
        def transport(*args, **kwargs): self.fail("Invalid origin caused outbound request")
        self.assertEqual(self.execute([], "verify", transport), 1)
        self.assertIn("WORKER_ORIGIN_INVALID", self.public)

    def test_anonymous_malformed_cache_and_payload_fail_closed(self):
        self.env["WORKER_ORIGIN"] = ORIGIN
        class Response:
            status = 403
            def __init__(self, cache, payload):
                self.headers = {"Cache-Control": cache}
                self.payload = payload
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return self.payload

        cases = [("public", b"{}", "ANONYMOUS_CHECK_CACHE_FAILED"),
                 ("private, no-store, max-age=0", b"not-json", "ORIGIN_REJECTION_CHECK_FAILED"),
                 ("private, no-store, max-age=0", b"x" * 4097, "ORIGIN_REJECTION_CHECK_FAILED")]
        for cache, payload, expected in cases:
            self.summary.write_text("")
            self.assertEqual(self.execute([], "verify", lambda *args, **kwargs: Response(cache, payload)), 1)
            self.assertIn(expected, self.public)

    def test_subprocess_stdout_is_not_forwarded_even_on_success(self):
        text = "unstructured payload " + TOKEN + EMAIL + ACCOUNT + "\n" + ORIGIN
        self.assertEqual(self.execute([self.whoami(), self.result(text)]), 0)
        self.assertNotIn("unstructured payload", self.public)
        self.assert_private()

    def test_unknown_operation_and_output_write_error_do_not_dump_tracebacks(self):
        self.assertEqual(self.execute([], "invalid"), 1)
        self.assertNotIn("Traceback", self.public)
        self.env["GITHUB_OUTPUT"] = self.temp.name
        self.assertEqual(self.execute([self.whoami(), self.result(ORIGIN)]), 1)
        self.assertIn("INTERNAL_FAILED", self.public)
        self.assertNotIn("Traceback", self.public)
        self.assert_private()


if __name__ == "__main__":
    unittest.main()
