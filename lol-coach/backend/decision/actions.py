from dataclasses import dataclass
from enum import IntEnum, StrEnum


class ActionType(StrEnum):
    THREAT = "THREAT"
    SINGLE_HIT = "SINGLE_HIT"
    SHORT_TRADE = "SHORT_TRADE"
    EXTENDED_TRADE = "EXTENDED_TRADE"
    ALL_IN = "ALL_IN"
    CHASE = "CHASE"
    CONCEDE_RESOURCE = "CONCEDE_RESOURCE"
    HOLD_PRESSURE = "HOLD_PRESSURE"
    FREEZE = "FREEZE"
    SLOW_PUSH = "SLOW_PUSH"
    CRASH = "CRASH"
    CLAIM_SPACE = "CLAIM_SPACE"
    CLAIM_RESOURCE = "CLAIM_RESOURCE"
    WAIT = "WAIT"
    PROBE = "PROBE"
    DISENGAGE = "DISENGAGE"


class Commitment(IntEnum):
    NONE = 0
    LOW = 1
    SHORT = 2
    HIGH = 3
    FULL = 4


class Reversibility(IntEnum):
    VERY_LOW = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


class RiskLevel(IntEnum):
    LOW = 0
    LOW_MEDIUM = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


class Purpose(StrEnum):
    PRESSURE = "PRESSURE"
    DAMAGE = "DAMAGE"
    CONVERSION = "CONVERSION"
    INFORMATION = "INFORMATION"
    SAFETY = "SAFETY"
    RESOURCE = "RESOURCE"
    WAVE = "WAVE"


@dataclass(frozen=True)
class ActionDefinition:
    action: ActionType
    purpose: Purpose
    commitment: Commitment
    reversibility: Reversibility
    risk: RiskLevel


ACTION_DEFINITIONS = {
    ActionType.THREAT: ActionDefinition(ActionType.THREAT, Purpose.PRESSURE, Commitment.LOW, Reversibility.VERY_HIGH, RiskLevel.LOW),
    ActionType.SINGLE_HIT: ActionDefinition(ActionType.SINGLE_HIT, Purpose.DAMAGE, Commitment.LOW, Reversibility.HIGH, RiskLevel.LOW_MEDIUM),
    ActionType.SHORT_TRADE: ActionDefinition(ActionType.SHORT_TRADE, Purpose.DAMAGE, Commitment.SHORT, Reversibility.HIGH, RiskLevel.LOW_MEDIUM),
    ActionType.EXTENDED_TRADE: ActionDefinition(ActionType.EXTENDED_TRADE, Purpose.DAMAGE, Commitment.HIGH, Reversibility.LOW, RiskLevel.HIGH),
    ActionType.ALL_IN: ActionDefinition(ActionType.ALL_IN, Purpose.CONVERSION, Commitment.FULL, Reversibility.VERY_LOW, RiskLevel.HIGH),
    ActionType.CHASE: ActionDefinition(ActionType.CHASE, Purpose.CONVERSION, Commitment.HIGH, Reversibility.VERY_LOW, RiskLevel.VERY_HIGH),
    ActionType.WAIT: ActionDefinition(ActionType.WAIT, Purpose.SAFETY, Commitment.NONE, Reversibility.VERY_HIGH, RiskLevel.LOW),
    ActionType.PROBE: ActionDefinition(ActionType.PROBE, Purpose.INFORMATION, Commitment.LOW, Reversibility.VERY_HIGH, RiskLevel.LOW),
    ActionType.DISENGAGE: ActionDefinition(ActionType.DISENGAGE, Purpose.SAFETY, Commitment.LOW, Reversibility.VERY_HIGH, RiskLevel.LOW),
}
