"""Trusted metadata-only source admission for synthetic G-SUP software tests.

The coordinator pins a SourceAnchor outside untrusted attempt specifications.
Bootstrap and descriptor issuance are privileged fixture-coordinator actions,
not provider actions. This local POSIX protocol protects compliant workers from
replays, overlapping/concurrent claims and interrupted writes. Privileged deletion
of the authority or replacement of its externally pinned trust configuration is
outside that threat model. It neither unifies the foundation registry nor reads
outcomes, chooses numeric conventions or grants real CAL_VERIFY access.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
import fcntl
from hashlib import sha1
import json
import os
from pathlib import Path

from .calibration_contracts import IntegrityFailure, MissingPrerequisite, identity, instant
from .ledger import canonical_json
from .selection_contracts import PROFILES
from .walkforward import digest

PROTOCOL = "C8_GSUP_SOURCE_IDENTITY_v1"
SCOPE = "SYNTHETIC_SOFTWARE_VALIDATION"
FIXTURE_SCOPE = "SYNTHETIC_SOFTWARE_VALIDATION_ONLY"
CONTROLS = ("EQUAL_SIMPLE", "MARKET_CAP")
COHORTS = tuple(f"{m}-{v}" for m in ("ROLLING", "EXPANDING")
                for v in ("PRIMARY", "REBALANCE_GAP_STRESS"))
ROLES = ("CHAMPION", "CHALLENGER")
APPROVAL_BLOB = "a5279d516c028f0a8cb9166ee2d54366da00877b"
APPROVAL_PATH = Path(__file__).resolve().parents[3] / "reports" / "track_c_c8_gsup_v2_source_identity_approval_2026-10-03.json"


def _approval():
    raw = APPROVAL_PATH.read_bytes()
    if sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() != APPROVAL_BLOB:
        raise IntegrityFailure("source identity approval changed")
    record = json.loads(raw)
    if (record["source_identity"]["protocol_version"] != PROTOCOL
            or record["source_identity"]["status"] != "APPROVED_SYNTHETIC_SOFTWARE_VALIDATION_ONLY"):
        raise IntegrityFailure("synthetic source identity authority mismatch")


def _directory_sync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _create(path, value, *, mode=0o444):
    """Exclusive intent, then file and directory durability; never remove on error."""
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    except FileExistsError as exc:
        raise IntegrityFailure("immutable record exists; no retry") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(canonical_json(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    _directory_sync(path.parent)


def _read(path):
    try:
        if path.is_symlink():
            raise IntegrityFailure("authority record may not be a symlink")
        raw = path.read_text(encoding="utf-8")
        if not raw.endswith("\n"):
            raise IntegrityFailure("incomplete immutable authority record")
        return json.loads(raw)
    except (OSError, ValueError, TypeError) as exc:
        if isinstance(exc, IntegrityFailure):
            raise
        raise IntegrityFailure("missing/malformed authority record") from exc


def _timestamp(value):
    if not isinstance(value, str):
        raise IntegrityFailure("explicit aware ISO timestamp string required")
    instant(value)
    return value


@dataclass(frozen=True)
class SourceAnchor:
    root: Path
    authority_ref: str
    manifest_hash: str

    def to_dict(self):
        return {"root": str(self.root), "authority_ref": self.authority_ref,
                "manifest_hash": self.manifest_hash}

    @classmethod
    def from_dict(cls, value):
        if set(value) != {"root", "authority_ref", "manifest_hash"}:
            raise IntegrityFailure("exact external authority anchor required")
        return cls(Path(value["root"]), identity(value["authority_ref"]), identity(value["manifest_hash"]))


@dataclass(frozen=True)
class ResolvedSource:
    authority_ref: str
    registration_ref: str
    descriptor_hash: str
    _canonical_descriptor: str

    @property
    def descriptor(self):
        return json.loads(self._canonical_descriptor)

    def to_dict(self):
        return {"authority_ref": self.authority_ref, "registration_ref": self.registration_ref,
                "descriptor_hash": self.descriptor_hash, "descriptor": self.descriptor}


@dataclass(frozen=True)
class ClaimReceipt:
    authority_ref: str
    claim_id: str
    registration_hash: str
    registration_ref: str
    descriptor_hash: str
    profile: str
    role: str
    claimed_at: str

    def to_dict(self):
        return dict(self.__dict__)


def _validate_descriptor(metadata):
    d = deepcopy(metadata)
    fields = {"schema", "scope", "configuration_scope", "temporal_origin", "synthetic",
              "registered_at", "source_id", "vintage", "profile", "role", "role_id",
              "role_designation_ref", "period_ids", "cohorts"}
    if not isinstance(d, dict) or set(d) != fields:
        raise IntegrityFailure("exact metadata-only descriptor fields required; no outcomes")
    if (d["schema"] != PROTOCOL or d["scope"] != SCOPE
            or d["configuration_scope"] != FIXTURE_SCOPE or d["temporal_origin"] != "SIMULATED"
            or d["synthetic"] is not True):
        raise MissingPrerequisite("only trusted synthetic software descriptors are approved")
    if d["profile"] not in PROFILES or d["role"] not in ROLES:
        raise IntegrityFailure("unchanged registered profile/role required")
    if d["role_designation_ref"] != "SYNTHETIC_FIXTURE_ROLE":
        raise MissingPrerequisite("real role designation is not approved")
    _timestamp(d["registered_at"])
    for field in ("source_id", "vintage", "role_id"):
        identity(d[field])
    periods = d["period_ids"]
    if not isinstance(periods, list) or not periods:
        raise IntegrityFailure("explicit nonempty ordered unique period identities required")
    for period in periods:
        identity(period)
    if len(set(periods)) != len(periods):
        raise IntegrityFailure("explicit nonempty ordered unique period identities required")
    if not isinstance(d["cohorts"], dict) or set(d["cohorts"]) != set(COHORTS):
        raise IntegrityFailure("complete registered cohort alignment required")
    sample_periods = {}
    for block in d["cohorts"].values():
        if (not isinstance(block, dict) or set(block) != {"role", "controls"}
                or not isinstance(block["controls"], dict) or set(block["controls"]) != set(CONTROLS)):
            raise IntegrityFailure("complete registered control/role alignment required")
        for stream in [block["role"], *block["controls"].values()]:
            if (not isinstance(stream, dict) or set(stream) != {"sample_ids", "period_ids"}
                    or stream["period_ids"] != periods or not isinstance(stream["sample_ids"], list)
                    or len(stream["sample_ids"]) != len(periods)):
                raise IntegrityFailure("full ordered period/sample alignment required")
            samples = stream["sample_ids"]
            for sample, period in zip(samples, periods):
                identity(sample)
                if sample in sample_periods and sample_periods[sample] != period:
                    raise IntegrityFailure("same stable sample cannot denote different periods")
                sample_periods[sample] = period
            if len(set(samples)) != len(samples):
                raise IntegrityFailure("unique samples within each aligned stream required")
    canonical_json(d)
    return d


def initialize_synthetic_authority(root, *, authority_id, registered_at, legacy_registry):
    """Privileged trusted coordinator only; attempts/providers must never call this.

    The returned reference binds the absolute store and existing v1 registry.
    Unknown historical records are retained and fail closed, never migrated or
    treated as unconsumed. Resetting trusted bootstrap/configuration is privileged.
    """
    _approval()
    identity(authority_id)
    _timestamp(registered_at)
    root = Path(root).absolute()
    legacy = Path(legacy_registry).absolute()
    if root.resolve() != root or legacy.resolve() != legacy or not legacy.is_dir():
        raise IntegrityFailure("explicit existing non-symlink legacy registry and absolute authority root required")
    if root == legacy or root in legacy.parents or legacy in root.parents:
        raise IntegrityFailure("authority and historical registry must be independent stores")
    manifest = {"schema": PROTOCOL, "scope": SCOPE, "synthetic": True,
                "root": str(root), "authority_id": authority_id, "registered_at": registered_at,
                "legacy_registry": str(legacy), "approval_blob": APPROVAL_BLOB}
    ref = "gsup-source-authority:" + digest(manifest)
    manifest["authority_ref"] = ref
    try:
        root.mkdir()
    except FileExistsError as exc:
        raise IntegrityFailure("authority already exists; missing stores may not be reinitialized") from exc
    for name in ("descriptors", "claim-intents", "accesses", "gsup_assessments"):
        (root / name).mkdir()
    _create(root / "manifest.json", manifest)
    _create(root / "lock", {"authority_ref": ref})
    genesis = {"kind": "GENESIS", "authority_ref": ref, "previous_hash": None}
    _create(root / "claims.jsonl", {"record": genesis, "record_hash": digest(genesis)}, mode=0o644)
    _directory_sync(root)
    _directory_sync(root.parent)
    return SourceAnchor(root, ref, digest(manifest))


class SourceAuthority:
    """Existing shared coordinator authority; no automatic creation or fallback."""

    def __init__(self, anchor, *, expected_authority_ref):
        if not isinstance(anchor, SourceAnchor) or anchor.authority_ref != identity(expected_authority_ref):
            raise IntegrityFailure("untrusted substitute source authority")
        self.anchor = anchor
        self._expected_ref = expected_authority_ref
        with self._locked():
            self._claims()

    @property
    def record_root(self):
        return self.anchor.root / "gsup_assessments"

    def _check_anchor(self):
        _approval()
        a = self.anchor
        if a.root.resolve() != a.root or not a.root.is_dir():
            raise IntegrityFailure("missing/copied source authority root")
        manifest = _read(a.root / "manifest.json")
        if (digest(manifest) != a.manifest_hash or manifest["authority_ref"] != self._expected_ref
                or manifest["root"] != str(a.root) or manifest["approval_blob"] != APPROVAL_BLOB):
            raise IntegrityFailure("source authority manifest/pinned reference mismatch")
        ref_body = {k: v for k, v in manifest.items() if k != "authority_ref"}
        if "gsup-source-authority:" + digest(ref_body) != self._expected_ref:
            raise IntegrityFailure("source authority identity mismatch")
        for name in ("descriptors", "claim-intents", "accesses", "gsup_assessments"):
            path = a.root / name
            if path.is_symlink() or not path.is_dir():
                raise IntegrityFailure("missing/redirected authority directory")
        if _read(a.root / "lock") != {"authority_ref": self._expected_ref}:
            raise IntegrityFailure("source authority lock identity mismatch")
        legacy = Path(manifest["legacy_registry"])
        if not legacy.is_dir() or legacy.resolve() != legacy:
            raise IntegrityFailure("missing/redirected historical registry")
        # No source-resolved historical migration is approved. Any opaque record,
        # including a pending registration or interrupted record, closes admission.
        if any(not p.is_dir() or p.is_symlink() for p in legacy.rglob("*")):
            raise MissingPrerequisite("unresolved historical G-SUP identity; no inferred unseen samples")

    @contextmanager
    def _locked(self):
        self._check_anchor()
        fd = os.open(self.anchor.root / "lock", os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            self._check_anchor()
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _claims(self):
        path = self.anchor.root / "claims.jsonl"
        try:
            if path.is_symlink():
                raise IntegrityFailure("redirected claims journal")
            raw = path.read_text(encoding="utf-8")
            if not raw or not raw.endswith("\n"):
                raise IntegrityFailure("missing/incomplete durable claim journal; fail closed")
            rows = [json.loads(line) for line in raw.splitlines()]
            genesis = {"kind": "GENESIS", "authority_ref": self._expected_ref, "previous_hash": None}
            if rows[0] != {"record": genesis, "record_hash": digest(genesis)}:
                raise IntegrityFailure("claim journal authority mismatch")
            previous = rows[0]["record_hash"]
            claimed, ids = set(), set()
            for row in rows[1:]:
                r = row["record"]
                fields = {"kind", "authority_ref", "registration_hash", "registration_ref", "descriptor_hash",
                          "profile", "role", "claimed_at", "sample_keys", "previous_hash", "claim_id"}
                if (set(row) != {"record", "record_hash"} or set(r) != fields or r["kind"] != "CLAIM"
                        or r["authority_ref"] != self._expected_ref or r["previous_hash"] != previous
                        or row["record_hash"] != digest(r)
                        or r["claim_id"] != digest({k: v for k, v in r.items() if k != "claim_id"})
                        or r["claim_id"] in ids or not r["sample_keys"]
                        or sorted(set(r["sample_keys"])) != r["sample_keys"]
                        or claimed.intersection(r["sample_keys"])):
                    raise IntegrityFailure("invalid/overlapping durable claim chain")
                _timestamp(r["claimed_at"])
                claimed.update(r["sample_keys"])
                ids.add(r["claim_id"])
                previous = row["record_hash"]
                if _read(self.anchor.root / "claim-intents" / (r["claim_id"] + ".json")) != r:
                    raise IntegrityFailure("claim differs from exclusive durable pre-append intent")
            intents = list((self.anchor.root / "claim-intents").iterdir())
            if {p.name for p in intents} != {claim_id + ".json" for claim_id in ids}:
                raise IntegrityFailure("interrupted or foreign reservation intent; fail closed")
            return rows
        except (OSError, ValueError, TypeError, KeyError) as exc:
            if isinstance(exc, IntegrityFailure):
                raise
            raise IntegrityFailure("missing/malformed durable claim journal; fail closed") from exc

    def register_descriptor(self, metadata):
        """Trusted coordinator metadata issuance; never obtains outcome arrays."""
        d = _validate_descriptor(metadata)
        with self._locked():
            self._claims()
            manifest = _read(self.anchor.root / "manifest.json")
            if instant(d["registered_at"]) < instant(manifest["registered_at"]):
                raise IntegrityFailure("descriptor predates trusted authority")
            dh = digest(d)
            ref = digest([self._expected_ref, dh])
            stored = {"authority_ref": self._expected_ref, "registration_ref": ref,
                      "descriptor_hash": dh, "descriptor": d}
            _create(self.anchor.root / "descriptors" / (ref + ".json"), stored)
            return {k: stored[k] for k in ("registration_ref", "descriptor_hash", "authority_ref")}

    def _resolved(self, ref, descriptor_hash):
        identity(ref)
        identity(descriptor_hash)
        if ref != digest([self._expected_ref, descriptor_hash]):
            raise IntegrityFailure("unresolved source descriptor reference")
        stored = _read(self.anchor.root / "descriptors" / (ref + ".json"))
        if set(stored) != {"authority_ref", "registration_ref", "descriptor_hash", "descriptor"}:
            raise IntegrityFailure("descriptor issuance record malformed")
        d = _validate_descriptor(stored["descriptor"])
        if (stored["authority_ref"] != self._expected_ref or stored["registration_ref"] != ref
                or stored["descriptor_hash"] != descriptor_hash or digest(d) != descriptor_hash):
            raise IntegrityFailure("trusted descriptor changed after registration")
        return ResolvedSource(self._expected_ref, ref, descriptor_hash, canonical_json(d))

    def resolve(self, ref, descriptor_hash, *, profile, role, role_id, verify_periods,
                cohorts, controls, registered_at):
        with self._locked():
            self._claims()  # corrupted/pending journal closes even metadata admission
            resolved = self._resolved(ref, descriptor_hash)
            d = resolved.descriptor
            if (d["profile"] != profile or d["role"] != role or d["role_id"] != role_id
                    or type(verify_periods) is not int or len(d["period_ids"]) != verify_periods
                    or len(cohorts) != len(COHORTS) or set(cohorts) != set(d["cohorts"])
                    or len(controls) != len(CONTROLS) or set(controls) != set(CONTROLS)):
                raise IntegrityFailure("source descriptor differs from registered full alignment")
            if instant(_timestamp(registered_at)) < instant(d["registered_at"]):
                raise IntegrityFailure("source identity must be issued before attempt registration")
            return resolved

    def _check_resolved(self, resolved):
        if not isinstance(resolved, ResolvedSource) or resolved.authority_ref != self._expected_ref:
            raise IntegrityFailure("foreign/unresolved source authority")
        current = self._resolved(resolved.registration_ref, resolved.descriptor_hash)
        if current != resolved:
            raise IntegrityFailure("resolved descriptor changed before admission")
        return current.descriptor

    @staticmethod
    def _receipt(record):
        return ClaimReceipt(**{k: record[k] for k in ClaimReceipt.__dataclass_fields__})

    def claim(self, resolved, *, registration_hash, at):
        """Reserve all samples atomically before feasibility; no release/idempotent retry."""
        identity(registration_hash)
        _timestamp(at)
        with self._locked():
            d = self._check_resolved(resolved)
            if instant(at) < instant(d["registered_at"]):
                raise IntegrityFailure("claim precedes source registration")
            rows = self._claims()
            samples = {s for b in d["cohorts"].values()
                       for stream in [b["role"], *b["controls"].values()] for s in stream["sample_ids"]}
            keys = sorted(digest([d["source_id"], d["vintage"], s, d["profile"], d["role"]]) for s in samples)
            used = {key for row in rows[1:] for key in row["record"]["sample_keys"]}
            if used.intersection(keys):
                raise IntegrityFailure("same stable samples already reserved; no relabel/reencode/retry")
            r = {"kind": "CLAIM", "authority_ref": self._expected_ref, "registration_hash": registration_hash,
                 "registration_ref": resolved.registration_ref, "descriptor_hash": resolved.descriptor_hash,
                 "profile": d["profile"], "role": d["role"], "claimed_at": at, "sample_keys": keys,
                 "previous_hash": rows[-1]["record_hash"]}
            r["claim_id"] = digest(r)
            line = canonical_json({"record": r, "record_hash": digest(r)}) + "\n"
            # A durable exclusive pre-append intent covers a crash before the
            # journal write. Unmatched/partial intents close the authority.
            _create(self.anchor.root / "claim-intents" / (r["claim_id"] + ".json"), r)
            # Under this authority lock the whole sample-set reservation is one
            # append. A torn tail closes every future admission, never rolls back.
            fd = os.open(self.anchor.root / "claims.jsonl", os.O_WRONLY | os.O_APPEND)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            _directory_sync(self.anchor.root)
            return self._receipt(r)

    def load_claim(self, claim_id):
        identity(claim_id)
        with self._locked():
            for row in self._claims()[1:]:
                if row["record"]["claim_id"] == claim_id:
                    return self._receipt(row["record"])
            raise IntegrityFailure("missing durable claim")

    def begin_access(self, receipt, *, at):
        """Exclusive durable access intent before provider; interrupted access stays spent."""
        _timestamp(at)
        with self._locked():
            if not isinstance(receipt, ClaimReceipt) or receipt.authority_ref != self._expected_ref:
                raise IntegrityFailure("untrusted access receipt")
            rows = self._claims()
            record = next((r["record"] for r in rows[1:] if r["record"]["claim_id"] == receipt.claim_id), None)
            if record is None or self._receipt(record) != receipt:
                raise IntegrityFailure("access receipt differs from durable reservation")
            self._resolved(receipt.registration_ref, receipt.descriptor_hash)
            if instant(at) < instant(receipt.claimed_at):
                raise IntegrityFailure("access precedes pre-feasibility reservation")
            value = {"claim": receipt.to_dict(), "accessed_at": at, "scope": SCOPE,
                     "synthetic": True, "approval_blob": APPROVAL_BLOB}
            _create(self.anchor.root / "accesses" / (receipt.claim_id + ".json"), value)
            return value

    def validate_response(self, resolved, data):
        """Verify provider identity/alignment without numeric conversion or recalculation."""
        with self._locked():
            self._claims()
            d = self._check_resolved(resolved)
            if (not isinstance(data, dict) or data.get("dataset_role") != "CAL_VERIFY"
                    or data.get("synthetic") is not True or data.get("role_id") != d["role_id"]):
                raise IntegrityFailure("only registered synthetic CAL_VERIFY fixture responses admitted")
            if data.get("source_identity") != response_identity(resolved):
                raise IntegrityFailure("provider source/vintage/ordered sample alignment mismatch")
            if not isinstance(data.get("cohorts"), dict) or set(data["cohorts"]) != set(d["cohorts"]):
                raise IntegrityFailure("provider cohort alignment mismatch")
            for block in data["cohorts"].values():
                if (not isinstance(block, dict) or set(block) != {"role", "controls"}
                        or not isinstance(block["controls"], dict) or set(block["controls"]) != set(CONTROLS)):
                    raise IntegrityFailure("provider control/role alignment mismatch")
                for values in [block["role"], *block["controls"].values()]:
                    if not isinstance(values, (list, tuple)) or len(values) != len(d["period_ids"]):
                        raise IntegrityFailure("provider ordered vector/sample alignment mismatch")
            return data  # preserve exact numerical objects and existing kernel inputs


def response_identity(resolved):
    if not isinstance(resolved, ResolvedSource):
        raise IntegrityFailure("trusted resolved metadata required")
    d = resolved.descriptor
    return {"authority_ref": resolved.authority_ref, "registration_ref": resolved.registration_ref,
            "descriptor_hash": resolved.descriptor_hash, "source_id": d["source_id"], "vintage": d["vintage"],
            "period_ids": d["period_ids"], "cohorts": d["cohorts"]}
