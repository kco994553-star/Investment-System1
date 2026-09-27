from dataclasses import dataclass, field
from enum import StrEnum

from backend.decision.actions import ActionType
from backend.decision.permission import PermissionLevel
from backend.decision.reason_codes import ReasonCode


class Validity(StrEnum):
    VALID = "VALID"
    CONDITIONAL = "CONDITIONAL"
    INVALID = "INVALID"


@dataclass
class ActionEvaluation:
    action: ActionType
    validity: Validity = Validity.VALID
    recommended: bool = False
    reasons: list[ReasonCode] = field(default_factory=list)
    unlock_conditions: list[str] = field(default_factory=list)


@dataclass
class Decision:
    permission: PermissionLevel
    opportunities: list[str]
    actions: list[ActionEvaluation]
    trace: list = field(default_factory=list)
