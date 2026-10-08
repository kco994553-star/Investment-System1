"""User-adopted scoring semantics, separate from legacy frozen schema versions.

Adoption is forward-only. These fields are assigned to newly computed results;
historical persisted results are not relabelled. Future calibration requires a
separate v2 decision and preserves this v1 definition.
"""

SCORING_STANDARD_VERSION = "v1"
SCORING_CALIBRATION = "UNCALIBRATED"
SCORING_STANDARD_STATUS = "STANDARD v1 · UNCALIBRATED"
# CDR040 recording time; not an inferred earlier user submission timestamp.
SCORING_STANDARD_EFFECTIVE_AT = "2026-10-08T11:50:25Z"
SCORING_STANDARD_SOURCE_HEAD = "d1566aeb1bbf11b1d514ad874b069d8b127ff1c7"
Q7_LABEL_EN = "Management Quality"
Q7_LABEL_KO = "경영진 품질"
