"""Common Track Record / Prediction schema. NEW CONTRACT.

Backtest results must not use this schema as if they were live decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from ..versions import IMPLEMENTATION_KIND, IMPLEMENTATION_LINE


@dataclass(frozen=True)
class PredictionEnvelope:
    prediction_id: str
    as_of: datetime
    system_version: str
    module_version: str
    profile_id: str
    parameter_set_hash: str
    input_snapshot_ids: tuple[str, ...]
    prediction: dict[str, Any]
    decision: dict[str, Any]
    scope: str
    evaluation_horizon: Optional[str] = None
    outcome: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None
    calibration_result: Optional[dict[str, Any]] = None
    implementation_kind: str = IMPLEMENTATION_KIND
    implementation_line: str = IMPLEMENTATION_LINE
    purpose: str = "TRACK_RECORD"
    immutable: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "as_of": self.as_of.isoformat(),
            "system_version": self.system_version,
            "module_version": self.module_version,
            "profile_id": self.profile_id,
            "parameter_set_hash": self.parameter_set_hash,
            "input_snapshot_ids": list(self.input_snapshot_ids),
            "prediction": dict(self.prediction),
            "decision": dict(self.decision),
            "scope": self.scope,
            "evaluation_horizon": self.evaluation_horizon,
            "outcome": self.outcome,
            "error": self.error,
            "calibration_result": self.calibration_result,
            "purpose": self.purpose,
            "not_backtest": True,
            "immutable": self.immutable,
        }
