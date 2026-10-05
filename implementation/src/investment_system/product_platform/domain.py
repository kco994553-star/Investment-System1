"""Shared platform boundary; existing investment identities/numeric semantics stay authoritative."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import re

CONTRACT_VERSION = "product-platform-v0.1"
READ_CAPABILITIES = frozenset({"READ_ACCOUNT", "READ_BALANCE", "READ_POSITION", "READ_TRANSACTION", "READ_STATEMENT"})
RESOURCES = frozenset({"accounts", "balances", "positions", "transactions", "statements"})
TRANSACTION_KINDS = frozenset({"BUY", "SELL", "DIVIDEND", "INTEREST", "FEE", "TAX", "DEPOSIT", "WITHDRAWAL", "TRANSFER", "CORPORATE_ACTION", "UNKNOWN"})

class PlatformError(Exception):
    """Public safe code only; provider payload/credential/error details are never included."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)

@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    session_id: str

@dataclass(frozen=True)
class ReadPage:
    resource: str
    body: bytes
    next_cursor: str | None = None
    complete: bool = True
    resume_cursor: str | None = None

def require_read_only(capabilities):
    try:
        values = frozenset(capabilities)
    except (TypeError, ValueError):
        raise PlatformError("CAPABILITY_REJECTED") from None
    if not values or not values <= READ_CAPABILITIES:
        raise PlatformError("CAPABILITY_REJECTED")
    return values

def aware(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise PlatformError("INVALID_TIME") from None
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PlatformError("INVALID_TIME")
    return value

def decimal_text(value):
    if not isinstance(value, str) or not re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        raise PlatformError("INVALID_NUMBER")
    try:
        d = Decimal(value)
    except InvalidOperation:
        raise PlatformError("INVALID_NUMBER") from None
    if not d.is_finite():
        raise PlatformError("INVALID_NUMBER")
    return d

def safe_json(body, max_bytes):
    if not isinstance(body, bytes) or len(body) > max_bytes:
        raise PlatformError("PAYLOAD_REJECTED")
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise PlatformError("DUPLICATE_KEY")
            out[k] = v
        return out
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(PlatformError("INVALID_NUMBER")))
    except (ValueError, UnicodeError, RecursionError):
        raise PlatformError("PAYLOAD_REJECTED") from None
    def secrets(v):
        if isinstance(v, dict):
            for k, child in v.items():
                normalized=re.sub(r"[^a-z]", "", k.lower())
                if any(term in normalized for term in ("token","password","secret","authorization","apikey","credential","privatekey")):
                    raise PlatformError("SECRET_PAYLOAD_REJECTED")
                secrets(child)
        elif isinstance(v, list):
            for child in v:
                secrets(child)
    try:
        secrets(value)
    except RecursionError:
        raise PlatformError("PAYLOAD_REJECTED") from None
    return value

def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
