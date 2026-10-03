"""Fail-closed PIT/no-lookahead enforcement for Track C."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

class PITViolation(ValueError):
    pass

@dataclass(frozen=True)
class PITObservation:
    observation_id: str
    available_at: datetime
    source_id: str
    vintage: str

class PITGuard:
    @staticmethod
    def enforce(decision_time: datetime, observations: Iterable[PITObservation]) -> tuple[PITObservation, ...]:
        accepted = []
        for obs in observations:
            if not obs.source_id or not obs.vintage:
                raise PITViolation("material provenance uncertainty: source/vintage missing")
            if obs.available_at > decision_time:
                raise PITViolation(
                    f"lookahead blocked: {obs.observation_id} available_at={obs.available_at.isoformat()} "
                    f"> decision_time={decision_time.isoformat()}"
                )
            accepted.append(obs)
        return tuple(accepted)
