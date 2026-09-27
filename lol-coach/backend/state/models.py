from enum import Enum
from pydantic import BaseModel


class MatchupState(str, Enum):
    FAVORABLE = "FAVORABLE"
    EVEN = "EVEN"
    UNFAVORABLE = "UNFAVORABLE"
    UNKNOWN = "UNKNOWN"


class AccessState(str, Enum):
    OPEN = "OPEN"
    LIMITED = "LIMITED"
    CLOSED = "CLOSED"


class WaveState(str, Enum):
    FAVORABLE = "FAVORABLE"
    EVEN = "EVEN"
    UNFAVORABLE = "UNFAVORABLE"


class JungleState(str, Enum):
    UNKNOWN = "UNKNOWN"
    CONFIRMED_NEAR = "CONFIRMED_NEAR"
    CONFIRMED_FAR = "CONFIRMED_FAR"


class OpponentAction(str, Enum):
    NEUTRAL = "NEUTRAL"
    CS_APPROACH = "CS_APPROACH"
    RETREAT = "RETREAT"
    COMMIT = "COMMIT"


class ReturnPath(str, Enum):
    SAFE = "SAFE"
    UNCERTAIN = "UNCERTAIN"
    UNSAFE = "UNSAFE"


class PowerState(BaseModel):
    matchup: MatchupState = MatchupState.UNKNOWN
    access: AccessState = AccessState.LIMITED


class WaveContext(BaseModel):
    state: WaveState = WaveState.EVEN


class JungleContext(BaseModel):
    enemy: JungleState = JungleState.UNKNOWN


class OpponentContext(BaseModel):
    action: OpponentAction = OpponentAction.NEUTRAL


class RiskContext(BaseModel):
    return_path: ReturnPath = ReturnPath.UNCERTAIN


class GameState(BaseModel):
    power: PowerState
    wave: WaveContext
    jungle: JungleContext
    opponent: OpponentContext
    risk: RiskContext
