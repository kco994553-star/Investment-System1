from enum import Enum


class Freshness(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class QualityState(str, Enum):
    OK = "OK"
    MISSING_DATA = "MISSING_DATA"
    STALE_DATA = "STALE_DATA"
    ESTIMATED_DATA = "ESTIMATED_DATA"
    CONFLICTING_SOURCE = "CONFLICTING_SOURCE"
    PIT_UNAVAILABLE = "PIT_UNAVAILABLE"
    VERSION_MISMATCH = "VERSION_MISMATCH"
    IDENTIFIER_CHANGED = "IDENTIFIER_CHANGED"
    CALCULATION_ERROR = "CALCULATION_ERROR"
    BLOCKED_DEPENDENCY = "BLOCKED_DEPENDENCY"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    SYNTHETIC = "SYNTHETIC"
    IDENTIFIER_AMBIGUOUS = "IDENTIFIER_AMBIGUOUS"


class CoverageState(str, Enum):
    READY = "READY"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    SYNTHETIC = "SYNTHETIC"


class CalibrationLifecycle(str, Enum):
    IDEA = "IDEA"
    RESEARCH = "RESEARCH"
    PROVISIONAL = "PROVISIONAL"
    VALIDATED = "VALIDATED"
    STANDARD = "STANDARD"
    VALIDATION_SELECTED = "VALIDATION_SELECTED"
    PROVISIONAL_INITIAL_PRIOR = "PROVISIONAL_INITIAL_PRIOR"
    PIT_TESTED = "PIT_TESTED"
    OOS_TESTED = "OOS_TESTED"
    CALIBRATED = "CALIBRATED"


class ProfileKind(str, Enum):
    GENERAL_CORPORATE = "GENERAL_CORPORATE"
    FINANCIAL = "FINANCIAL"


class SimulationMode(str, Enum):
    HISTORICAL = "HISTORICAL"
    CURRENT = "CURRENT"
    FORWARD = "FORWARD"


class TechnicalRegime(str, Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    HIGH_VOL = "HIGH_VOL"
    UNKNOWN = "UNKNOWN"


class ExecutionZone(str, Enum):
    ENTRY = "ENTRY"
    ADD = "ADD"
    WAIT = "WAIT"
    RISK_REDUCTION = "RISK_REDUCTION"


class MacroState(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    EMERGENCY = "EMERGENCY"


class GateDecision(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


class StrategyStyle(str, Enum):
    DEFENSIVE = "Defensive"
    BALANCED = "Balanced"
    AGGRESSIVE = "Aggressive"
    CUSTOM = "Custom"


class WorkspaceId(str, Enum):
    HOME = "home"
    QGV = "qgv"
    TECHNICAL = "technical"
    MACRO = "macro"
    INTEGRATED = "integrated"
    LAB = "lab"


class ValidationLayer(str, Enum):
    MODULE_BACKTEST = "module_backtest"
    COMBINATION_BACKTEST = "combination_backtest"
    INTEGRATED_BACKTEST = "integrated_backtest"
    OOS = "oos"
    CALIBRATION = "calibration"
    FORWARD_TRACK_RECORD = "forward_track_record"


class TrackScope(str, Enum):
    QGV = "qgv"
    TECHNICAL = "technical"
    MACRO = "macro"
    INTEGRATED = "integrated"
