"""Synthetic G-SUP source binding, without changing a statistical kernel.

This compatibility engine retains v1 statistics to verify the approved identity
protocol independently. It is not authoritative M-B v2 and cannot grant access
to actual CAL_VERIFY, Holdout, research publication or Official operation.
"""
from copy import deepcopy

from . import superiority as legacy
from .calibration_contracts import IntegrityFailure, MissingPrerequisite, instant
from .gsup_source_identity import PROTOCOL, SourceAuthority
from .walkforward import digest


class IdentityBoundGsupRegistry(legacy.GsupRegistry):
    """Separate immutable records with a coordinator-pinned source authority.

    Only the local registration directory is caller-selected. The shared record
    and consumption stores are derived from the preconfigured trusted authority.
    Profile/role grouping and legacy numerical semantics remain unchanged.
    """

    def __init__(self, root, source_authority):
        if not isinstance(source_authority, SourceAuthority):
            raise MissingPrerequisite("trusted synthetic source authority required")
        self.source_authority = source_authority
        super().__init__(root, source_authority.record_root)

    @staticmethod
    def _validate_spec(spec):
        return legacy.validate_registration(spec)

    @staticmethod
    def _feasibility(spec, estimate):
        return legacy.assess_feasibility(spec, estimate)

    @staticmethod
    def _evaluate(spec, data):
        return legacy._evaluate(spec, data)

    @staticmethod
    def _result(spec, statistical, decision, cells, reasons):
        return legacy._result(spec, statistical, decision, cells, reasons)

    def _resolve(self, binding, spec):
        if not isinstance(binding, dict) or set(binding) != {
                "authority_ref", "registration_ref", "descriptor_hash"}:
            raise MissingPrerequisite("NOT_RUN_MISSING_SOURCE_IDENTITY")
        if binding["authority_ref"] != self.source_authority.anchor.authority_ref:
            raise IntegrityFailure("attempt source authority differs from coordinator pin")
        return self.source_authority.resolve(
            binding["registration_ref"], binding["descriptor_hash"],
            profile=spec["profile"], role=spec["role"], role_id=spec["role_id"],
            verify_periods=spec["verify_periods"], cohorts=spec["cohorts"],
            controls=spec["controls"], registered_at=spec["registered_at"])

    @staticmethod
    def _record_key(binding, spec):
        # Changing a descriptor reference cannot reopen overlapping stable
        # samples: SourceAuthority exclusively charges every stable sample key.
        return digest([PROTOCOL, binding, spec["profile"], spec["role"]])

    def register(self, spec, *, source_binding):
        s = self._validate_spec(spec)
        binding = deepcopy(source_binding)
        self._resolve(binding, s)  # Metadata only; never outcome access.
        key = self.target_key(s)
        self._create(self.root, "registration", key, {
            "registration": s, "registration_hash": digest(s),
            "source_binding": binding, "source_binding_hash": digest(binding),
            "source_protocol": PROTOCOL})
        return key

    def _bound_registration(self, key):
        stored = self._load(self.root, "registration", key)
        if stored is None:
            raise MissingPrerequisite("source-bound registration required")
        s = self._validate_spec(stored["registration"])
        binding = stored.get("source_binding")
        if (digest(s) != stored["registration_hash"]
                or stored.get("source_protocol") != PROTOCOL
                or digest(binding) != stored.get("source_binding_hash")):
            raise IntegrityFailure("source-bound registration changed after admission")
        resolved = self._resolve(binding, s)
        return s, binding, resolved

    def record_feasibility(self, key, development_series, *, dataset_role, dataset_id):
        s, binding, resolved = self._bound_registration(key)
        # The irreversible reservation precedes estimate/verdict. An infeasible
        # or crashed attempt cannot request a different numeric procedure later.
        claim = self.source_authority.claim(
            resolved, registration_hash=digest(s), at=s["registered_at"])
        estimate = legacy.development_dependence_estimate(
            development_series, dataset_role=dataset_role, dataset_id=dataset_id,
            estimator=s["feasibility"]["dependence_estimator"])
        record = self._feasibility(s, estimate)
        record.update({"registration_target": key, "source_protocol": PROTOCOL,
                       "source_binding": binding, "claim_receipt": claim.to_dict()})
        record["record_hash"] = digest({k: v for k, v in record.items() if k != "record_hash"})
        return self._create(self.shared, "feasibility", self._record_key(binding, s), record)

    def assess(self, key, provider, *, accessed_at):
        s, binding, resolved = self._bound_registration(key)
        record_key = self._record_key(binding, s)
        feasibility = self._load(self.shared, "feasibility", record_key)
        if feasibility is None:
            raise MissingPrerequisite("pre-access source-bound feasibility required")
        body = {k: v for k, v in feasibility.items() if k != "record_hash"}
        if (digest(body) != feasibility.get("record_hash")
                or feasibility.get("registration_hash") != digest(s)
                or feasibility.get("registration_target") != key
                or feasibility.get("source_binding") != binding
                or feasibility.get("source_protocol") != PROTOCOL):
            raise IntegrityFailure("source-bound feasibility tampered or reassigned")
        if instant(accessed_at) <= instant(s["registered_at"]):
            raise IntegrityFailure("outcome access must follow preregistration")
        saved_claim = feasibility.get("claim_receipt")
        if not isinstance(saved_claim, dict) or not saved_claim.get("claim_id"):
            raise IntegrityFailure("durable source reservation required")
        claim = self.source_authority.load_claim(saved_claim["claim_id"])
        if (claim.to_dict() != saved_claim or claim.registration_hash != digest(s)
                or claim.authority_ref != resolved.authority_ref
                or claim.registration_ref != resolved.registration_ref
                or claim.descriptor_hash != resolved.descriptor_hash
                or claim.profile != s["profile"] or claim.role != s["role"]):
            raise IntegrityFailure("source reservation does not match feasibility")
        if (self._load(self.shared, "result", record_key) is not None
                or self._load(self.shared, "access", record_key) is not None):
            raise IntegrityFailure("source-bound target is one-shot; no retry")
        if feasibility["status"] != "FEASIBLE":
            result = self._result(s, "NOT_RUN_INFEASIBLE", "NOT_RUN_INFEASIBLE", {},
                                  feasibility["reasons"])
            return self._create(self.shared, "result", record_key, self._attach(result, binding))
        # A returned synthetic label is too late to authorize a real reader.
        if (getattr(provider, "synthetic", None) is not True
                or getattr(provider, "scope", None) != legacy.SCOPE):
            raise MissingPrerequisite("only a declared synthetic outcome provider is authorized")
        access = self.source_authority.begin_access(claim, at=accessed_at)
        self._create(self.shared, "access", record_key, {
            "registration_hash": digest(s), "accessed_at": accessed_at,
            "source_protocol": PROTOCOL, "source_binding": binding,
            "source_access_receipt": access})
        try:
            data = provider(s["verify_dataset_id"])
            self.source_authority.validate_response(resolved, data)
            cells = self._evaluate(s, data)
        except BaseException as exc:
            result = self._result(s, "NOT_RUN", "CRASH_NO_RETRY", {}, [type(exc).__name__])
            self._create(self.shared, "result", record_key, self._attach(result, binding))
            raise
        statuses = [cell["status"] for cell in cells.values()]
        statistical = ("NOT_RUN" if any(x == "NOT_RUN" for x in statuses) else
                       "STAT_PASS" if all(x == "REJECT_H0" for x in statuses) else "STAT_FAIL")
        result = self._result(s, statistical, "NOT_RUN_EFFECT_FLOOR_DEFERRED", cells, [])
        return self._create(self.shared, "result", record_key, self._attach(result, binding))

    @staticmethod
    def _attach(result, binding):
        return {**result, "source_protocol": PROTOCOL, "source_binding": deepcopy(binding),
                "validation_mode": "SYNTHETIC_IDENTITY_COMPATIBILITY_ONLY"}
