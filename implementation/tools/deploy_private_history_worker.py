"""Manual deployment diagnostics; raw command output never reaches public sinks."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


WRANGLER = ["npx", "--yes", "wrangler@4.149.0"]
CONFIG = "implementation/worker/wrangler.toml"
ORIGIN_PATTERN = r"https://private-investment-history\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.workers\.dev"
ALLOWED_ORIGIN = "https://kco994553-star.github.io"
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CONTROL_STRING = re.compile(r"(?:\x1b\]|\x9d)[\s\S]*?(?:\x07|\x1b\\|\x9c|$)|(?:\x1b[P^_X]|[\x90\x98\x9e\x9f])[\s\S]*?(?:\x1b\\|\x9c|$)")
JSON_ESCAPE = re.compile(r'\\(?:u[0-9a-fA-F]{4}|["\\/bfnrt])')
ENCODED_REMAINDER = re.compile(r'\\(?:u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|["\\/bfnrt])|%[0-9a-fA-F]{2}|&(?:[a-zA-Z]+|#[xX]?[0-9a-fA-F]+);')
SIZE_OMITTED = "Oversized diagnostic omitted."
CONTROL_OMITTED = "Incomplete terminal-control diagnostic omitted."
ENCODING_OMITTED = "Encoded diagnostic omitted because normalization remained ambiguous."


def canonical_message(message: str) -> str:
    """Bound decoding, then reconnect values split by terminal formatting."""
    if len(message) > 12000:
        return SIZE_OMITTED
    for _ in range(4):
        previous = message
        if any(not match.group(0).endswith(("\x07", "\x1b\\", "\x9c"))
               for match in CONTROL_STRING.finditer(message)):
            return CONTROL_OMITTED
        # Remove original ST-terminated strings before JSON decoding can consume
        # the terminator's backslash; repeat after decoding encoded controls.
        message = CONTROL_STRING.sub("", message)
        message = ANSI.sub("", message)
        message = JSON_ESCAPE.sub(lambda match: json.loads('"' + match.group(0) + '"'), message)
        message = urllib.parse.unquote(html.unescape(message))
        if any(not match.group(0).endswith(("\x07", "\x1b\\", "\x9c"))
               for match in CONTROL_STRING.finditer(message)):
            return CONTROL_OMITTED
        message = CONTROL_STRING.sub("", message)
        message = ANSI.sub("", message)
        message = "".join(c for c in message if c.isprintable() or c in "\n\r\t")
        if message == previous:
            break
    if ENCODED_REMAINDER.search(message):
        return ENCODING_OMITTED
    return message


def redact_message(message: str, environ: dict[str, str]) -> str:
    """Normalize and redact the complete block before selecting any lines."""
    message = canonical_message(message)
    for name in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        value = environ.get(name, "").strip()
        if value:
            message = message.replace(value, "[REDACTED]")
    message = re.sub(r"\b[a-z][a-z0-9+.-]*://[^\s<>\"']+", "[REDACTED_URL]", message, flags=re.I)
    message = re.sub(r"\bBearer\s+[^\s,;]+", "Bearer [REDACTED]", message, flags=re.I)
    message = re.sub(r"\b((?:api[_ -]?)?token|authorization|secret|password)\b[\"']?\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
                     r"\1=[REDACTED]", message, flags=re.I)
    message = re.sub(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w.-]+", "[REDACTED_EMAIL]", message)
    message = re.sub(r"\b[0-9a-f]{32}\b", "[REDACTED_ACCOUNT]", message, flags=re.I)
    message = re.sub(r"[A-Za-z0-9_+/=-]{20,}", "[REDACTED_VALUE]", message)
    return message


def safe_message(message: str, environ: dict[str, str]) -> str:
    """Redact before escaping any untrusted text for a GitHub Markdown Summary."""
    message = redact_message(message, environ)
    message = " ".join("".join(c if c.isprintable() else " " for c in message).split())[:600]
    message = html.escape(message, quote=True)
    return re.sub(r"([\\`*_{}\[\]()#!|~])", r"\\\1", message)


def summary(environ: dict[str, str], text: str) -> None:
    path = environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with Path(path).open("a", encoding="utf-8") as output:
            output.write(text + "\n\n")


def fail(environ: dict[str, str], status: str, result=None) -> int:
    # Only fixed status identifiers go to stdout; no exception or command repr.
    print(status)
    details = ["Worker diagnostic: " + status]
    if result is not None:
        raw = ANSI.sub("", (result.stdout or "") + "\n" + (result.stderr or ""))
        codes = sorted(set(re.findall(r"\[code:\s*([0-9]{1,10})\]", raw, flags=re.I)))[:10]
        details.append("Wrangler error codes: " + (", ".join(codes) if codes else "unavailable"))
        # Controls can cross physical lines. Normalize and redact the bounded
        # stdout/stderr block before any line can become publishable text.
        normalized = redact_message(raw, environ)
        if normalized in (SIZE_OMITTED, CONTROL_OMITTED, ENCODING_OMITTED):
            normalized = "[ERROR] " + normalized
        messages = []
        in_error = False
        for line in normalized.splitlines():
            if "[ERROR]" in line:
                in_error = True
                line = line.split("[ERROR]", 1)[1]
            elif not line.strip():
                in_error = False
                continue
            elif not in_error and not re.search(r"\[code:\s*[0-9]+\]", line, re.I):
                continue
            cleaned = safe_message(line, environ)
            if cleaned and cleaned not in messages:
                messages.append(cleaned)
            if len(messages) >= 5:
                break
        details.extend("- " + message for message in messages)
        if not messages:
            details.append("No structured Wrangler error was available; inspect account permissions and configuration.")
    summary(environ, "\n".join(details))
    return 1


def invoke(environ: dict[str, str], runner, stage: str, command: list[str], timeout: int):
    try:
        result = runner(command, capture_output=True, text=True, timeout=timeout, env=environ)
    except subprocess.TimeoutExpired:
        fail(environ, "WORKER_" + stage + "_TIMEOUT")
        return None
    except OSError:
        fail(environ, "WORKER_" + stage + "_COMMAND_FAILED")
        return None
    if result.returncode:
        fail(environ, "WORKER_" + stage + "_FAILED", result)
        return None
    return result


def deployment_origin(output: str) -> str | None:
    candidates = re.findall(r"https://[^\s<>\"']+", ANSI.sub("", output))
    origins = [url for url in candidates if re.fullmatch(ORIGIN_PATTERN, url)]
    return origins[-1] if origins else None


def deploy(environ: dict[str, str], runner) -> int:
    for name in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        environ[name] = environ.get(name, "").strip()
    environ["WRANGLER_SEND_METRICS"] = "false"
    if not all(environ[name] for name in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")):
        return fail(environ, "WORKER_CREDENTIALS_MISSING")
    preflight = invoke(environ, runner, "PREFLIGHT", WRANGLER + ["whoami"], 90)
    if preflight is None:
        return 1
    identity = ANSI.sub("", preflight.stdout or "")
    if not re.search(r"^[^\w\n]*(?:You are )?logged in with an (?:(?:Account|User) )?API Token\b", identity, re.I | re.M):
        return fail(environ, "WORKER_TOKEN_VALIDITY_UNCONFIRMED")
    summary(environ, "Token validity: confirmed by pinned Wrangler whoami.")
    account = environ["CLOUDFLARE_ACCOUNT_ID"]
    account_row = r"^\s*(?:Account ID:\s*" + re.escape(account) + r"|[│|].*[│|]\s*" + re.escape(account) + r"\s*[│|])\s*$"
    if not re.search(account_row, identity, re.I | re.M):
        return fail(environ, "WORKER_ACCOUNT_ACCESS_UNCONFIRMED")
    summary(environ, "Configured account access: confirmed by pinned Wrangler whoami.")
    result = invoke(environ, runner, "DEPLOY", WRANGLER + ["deploy", "--config", CONFIG], 300)
    if result is None:
        return 1
    origin = deployment_origin(result.stdout or "")
    if origin is None:
        return fail(environ, "WORKER_DEPLOY_RETURNED_SUCCESS_BUT_URL_UNAVAILABLE")
    # This origin alone is intended to be public; no raw output is written.
    with Path(environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
        output.write("origin=" + origin + "\n")
    print("WORKER_DEPLOY_SUCCEEDED: " + origin)
    summary(environ, "Worker address: " + origin)
    return 0


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def verify(environ: dict[str, str], transport=None) -> int:
    origin = environ.get("WORKER_ORIGIN", "")
    if not re.fullmatch(ORIGIN_PATTERN, origin):
        return fail(environ, "WORKER_ORIGIN_INVALID")
    if transport is None:
        transport = urllib.request.build_opener(NoRedirect()).open
    cases = [("NO_ORIGIN", {}), ("DISALLOWED_ORIGIN", {"Origin": "https://invalid-origin.example"}),
             ("ALLOWED_ORIGIN_NO_AUTH", {"Origin": ALLOWED_ORIGIN})]
    receipts = []
    for name, headers in cases:
        request = urllib.request.Request(
            origin + "/history?symbol=NVDA&range=1mo",
            headers={"User-Agent": "InvestmentSystem1-DeploymentVerification/1.0", **headers},
        )
        try:
            try:
                response = transport(request, timeout=30)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                status = response.status
                cors = response.headers.get("Access-Control-Allow-Origin")
                cache = response.headers.get("Cache-Control")
                payload = response.read(4097)
        except Exception:
            return fail(environ, "ANONYMOUS_CHECK_TRANSPORT_FAILED")
        try:
            code = json.loads(payload)["error"]["code"] if len(payload) <= 4096 else None
        except Exception:
            code = None
        if cache != "private, no-store, max-age=0":
            return fail(environ, "ANONYMOUS_CHECK_CACHE_FAILED")
        if name != "ALLOWED_ORIGIN_NO_AUTH":
            if status != 403 or code != "ORIGIN_FORBIDDEN" or cors is not None:
                return fail(environ, "ORIGIN_REJECTION_CHECK_FAILED")
        elif cors != ALLOWED_ORIGIN or (status, code) not in [(503, "CONFIG_UNAVAILABLE"), (403, "AUTH_FORBIDDEN")]:
            return fail(environ, "ANONYMOUS_AUTH_CONFIG_CHECK_FAILED")
        receipts.append(name + ": HTTP " + str(status) + " " + code)
    for receipt in receipts:
        print(receipt)
    summary(environ, "\n".join("- " + receipt for receipt in receipts) +
            "\n\nGoogle/Yahoo verification not run. App feature remains OFF.")
    return 0


def main(operation: str, environ=None, runner=subprocess.run, transport=None) -> int:
    environ = dict(os.environ if environ is None else environ)
    try:
        if operation == "deploy":
            return deploy(environ, runner)
        if operation == "verify":
            return verify(environ, transport)
        return fail(environ, "WORKER_OPERATION_INVALID")
    except Exception:
        # Filesystem and unexpected failures must not produce credential-bearing tracebacks.
        print("WORKER_DIAGNOSTIC_INTERNAL_FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) == 2 else ""))
