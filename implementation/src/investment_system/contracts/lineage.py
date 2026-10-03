"""Input-derived availability for existing engines; no new scoring rule."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import math

from .models import DataStamp


def require_aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError('lineage requires timezone-aware timestamps')


@dataclass(frozen=True)
class StampedValue:
    value: float
    measured_at: datetime
    stamp: DataStamp
    vintage: str

    def validate(self, as_of: datetime, *, synthetic: bool) -> None:
        for value in (as_of, self.measured_at, self.stamp.published_at,
                      self.stamp.available_at, self.stamp.observed_at):
            require_aware(value)
        if isinstance(self.value, bool) or not isinstance(self.value, (float, int)) or not math.isfinite(self.value):
            raise ValueError('invalid stamped value')
        if not all((self.stamp.data_stamp_id, self.stamp.source_provider,
                    self.stamp.source_reference, self.vintage)):
            raise ValueError('missing input provenance/vintage')
        if self.measured_at > as_of or self.stamp.available_at > as_of:
            raise ValueError('future input cannot support a decision')
        if self.stamp.published_at > self.stamp.available_at:
            raise ValueError('availability cannot precede publication')
        if self.stamp.estimated:
            raise ValueError('estimated availability is not strict PIT evidence')
        if self.stamp.synthetic and not synthetic:
            raise ValueError('synthetic source cannot support a real-data claim')


def derived_lineage(inputs: dict[str, StampedValue], as_of: datetime,
                    *, synthetic: bool) -> dict:
    if not inputs:
        raise ValueError('strict evaluation requires stamped inputs')
    for value in inputs.values():
        value.validate(as_of, synthetic=synthetic)
    # Preserve all source metadata in the content hash; never substitute as_of.
    payload = {key: {'value': value.value, 'measured_at': value.measured_at.isoformat(),
                     'stamp': value.stamp.to_dict(), 'vintage': value.vintage}
               for key, value in sorted(inputs.items())}
    stamp_payloads = {}
    for value in inputs.values():
        stamp_id = value.stamp.data_stamp_id
        identity = (json.dumps(value.stamp.to_dict(), sort_keys=True), value.vintage)
        if stamp_id in stamp_payloads and stamp_payloads[stamp_id] != identity:
            raise ValueError('conflicting source identity')
        stamp_payloads[stamp_id] = identity
    return {
        'available_at': max(value.stamp.available_at for value in inputs.values()),
        'data_stamp_refs': tuple(sorted(stamp_payloads)),
        'source_vintages': tuple(sorted({(v.stamp.data_stamp_id, v.vintage) for v in inputs.values()})),
        'input_hash': sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest(),
    }
