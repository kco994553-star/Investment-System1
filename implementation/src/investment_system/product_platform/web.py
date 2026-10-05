"""Loopback-only transport for the synthetic Product Platform audit harness.

This is not a production server, authentication provider, deployment or PWA.
Opaque sessions stay in HttpOnly cookies; the browser receives only the CSRF
credential. Only three fixed public assets are served, with no file browsing.
"""
from copy import deepcopy
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import socket

from .domain import PlatformError, json_text, safe_json

COOKIE_NAME = "synthetic_platform_session"
ASSETS = Path(__file__).with_name("web_assets")
_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,256}\Z")
_ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
           "/app.js": ("app.js", "text/javascript; charset=utf-8"),
           "/style.css": ("style.css", "text/css; charset=utf-8")}
_CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; object-src 'none'"


class SyntheticHTTPServer(ThreadingHTTPServer):
    """Fixed loopback bind; trusted attempt keys are derived from the socket."""
    daemon_threads = True

    def __init__(self, api, *, port, max_body_bytes, request_timeout):
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError("INVALID_PORT")
        if type(max_body_bytes) is not int or max_body_bytes <= 0:
            raise ValueError("EXPLICIT_BODY_LIMIT_REQUIRED")
        if not isinstance(request_timeout, (int, float)) or isinstance(request_timeout, bool) or not 0 < request_timeout < 60:
            raise ValueError("EXPLICIT_REQUEST_TIMEOUT_REQUIRED")
        self.api = api
        self.max_body_bytes = max_body_bytes
        self.request_timeout = request_timeout
        super().__init__(("127.0.0.1", port), SyntheticHandler)
        self.origin = f"http://127.0.0.1:{self.server_address[1]}"
        self.expected_host = self.origin.removeprefix("http://")

    def handle_error(self, request, client_address):
        # Base server prints tracebacks; request/provider/session bytes must not
        # appear in server logs, including failure paths.
        pass


class SyntheticHandler(BaseHTTPRequestHandler):
    server_version = "SyntheticAuditHarness"
    sys_version = ""

    def setup(self):
        self.request.settimeout(self.server.request_timeout)
        super().setup()

    def log_message(self, format, *args):
        pass

    def _reply(self, status, body, *, content_type="application/json; charset=utf-8", cookie=None):
        raw = body if isinstance(body, bytes) else json_text(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", _CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("X-Synthetic-Only", "true")
        self.send_header("Connection", "close")
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.close_connection = True
        if self.command != "HEAD":
            self.wfile.write(raw)

    def _error(self, status, code):
        self._reply(status, {"error": {"code": code}, "is_real": False, "data_state": "DEMO"})

    def _one(self, name, *, required=False):
        values = self.headers.get_all(name, [])
        if len(values) > 1 or (required and len(values) != 1):
            raise PlatformError("REQUEST_REJECTED")
        return values[0] if values else None

    def _token(self):
        cookie_header = self._one("Cookie")
        token = None
        if cookie_header:
            if len(cookie_header) > 8192:
                raise PlatformError("REQUEST_REJECTED")
            # Reject duplicate session cookies instead of silently taking one.
            names = [piece.split("=", 1)[0].strip() for piece in cookie_header.split(";")]
            if names.count(COOKIE_NAME) > 1:
                raise PlatformError("REQUEST_REJECTED")
            cookies = SimpleCookie()
            try:
                cookies.load(cookie_header)
            except Exception:
                raise PlatformError("REQUEST_REJECTED") from None
            if COOKIE_NAME in cookies:
                token = cookies[COOKIE_NAME].value
        authorization = self._one("Authorization")
        if authorization:
            if token is not None or not authorization.startswith("Bearer "):
                raise PlatformError("REQUEST_REJECTED")
            token = authorization[7:]
        if token is not None and _TOKEN.fullmatch(token) is None:
            raise PlatformError("REQUEST_REJECTED")
        return token

    def _dispatch(self):
        try:
            # BaseHTTPRequestHandler normalizes a leading // to /. Preserve
            # the original bounded request-target for the strict path rule.
            parts = self.requestline.split()
            raw_target = parts[1] if len(parts) >= 2 else ""
            if not raw_target.startswith("/") or any(character in raw_target for character in ("%", "?", "#", "\\")) or "//" in raw_target:
                return self._error(404, "NOT_FOUND")
            if self._one("Host", required=True) != self.server.expected_host:
                return self._error(400, "HOST_REJECTED")
            if any(character in self.path for character in ("%", "?", "#", "\\")) or "//" in self.path:
                return self._error(404, "NOT_FOUND")
            if self.command == "GET" and self.path in _ASSETS:
                filename, content_type = _ASSETS[self.path]
                return self._reply(200, (ASSETS / filename).read_bytes(), content_type=content_type)
            if not self.path.startswith("/api/"):
                return self._error(404, "NOT_FOUND")
            if self.command not in {"GET", "POST"}:
                return self._error(404, "NOT_FOUND")
            body = None
            if self.command == "POST":
                if self._one("Origin") != self.server.origin:
                    return self._error(403, "ORIGIN_REJECTED")
                if self._one("Transfer-Encoding") is not None:
                    return self._error(400, "REQUEST_REJECTED")
                content_type = self._one("Content-Type") or ""
                if content_type.lower().replace(" ", "") not in {"application/json", "application/json;charset=utf-8"}:
                    return self._error(415, "JSON_REQUIRED")
                length_text = self._one("Content-Length", required=True)
                if not re.fullmatch(r"[0-9]{1,10}", length_text):
                    return self._error(400, "REQUEST_REJECTED")
                length = int(length_text)
                if length <= 0 or length > self.server.max_body_bytes:
                    return self._error(413, "BODY_LIMIT")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    return self._error(400, "REQUEST_REJECTED")
                body = safe_json(raw, self.server.max_body_bytes)
                if not isinstance(body, dict):
                    return self._error(400, "JSON_OBJECT_REQUIRED")
            elif self._one("Transfer-Encoding") is not None or self._one("Content-Length") not in {None, "0"}:
                return self._error(400, "REQUEST_REJECTED")
            token = self._token()
            csrf = self._one("X-CSRF-Token")
            if csrf is not None and _TOKEN.fullmatch(csrf) is None:
                return self._error(400, "REQUEST_REJECTED")
            path = self.path.removeprefix("/api")
            # A request body/header cannot choose the rate-limit or ownership key.
            status, payload = self.server.api.request(self.command, path, token=token, csrf=csrf,
                                                    body=body, attempt_key=self.client_address[0])
            cookie = None
            if path == "/synthetic-login" and self.command == "POST" and 200 <= status < 300:
                payload = deepcopy(payload)
                credential = payload["data"].pop("token")
                if not isinstance(credential, str) or _TOKEN.fullmatch(credential) is None:
                    raise PlatformError("TRANSPORT_FAILURE")
                # Secure cannot be used over this explicitly HTTP-only loopback
                # test harness. Production TLS/auth remains a separate gate.
                cookie = f"{COOKIE_NAME}={credential}; Path=/api; HttpOnly; SameSite=Strict"
            if path == "/logout" and self.command == "POST" and 200 <= status < 300:
                cookie = f"{COOKIE_NAME}=; Path=/api; Max-Age=0; HttpOnly; SameSite=Strict"
            self._reply(status, payload, cookie=cookie)
        except (PlatformError, ValueError):
            self._error(400, "REQUEST_REJECTED")
        except (TimeoutError, socket.timeout):
            self._error(408, "REQUEST_TIMEOUT")
        except Exception:
            self._error(500, "HARNESS_FAILURE")

    do_GET = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_PATCH = _dispatch
    do_DELETE = _dispatch
    do_OPTIONS = _dispatch
    do_HEAD = _dispatch
    do_TRACE = _dispatch
    do_CONNECT = _dispatch


def create_server(api, *, port=0, max_body_bytes, request_timeout):
    """Return an unstarted server bound to 127.0.0.1 only."""
    return SyntheticHTTPServer(api, port=port, max_body_bytes=max_body_bytes,
                               request_timeout=request_timeout)
