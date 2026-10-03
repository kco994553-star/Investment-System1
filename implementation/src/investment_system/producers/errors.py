"""Typed domain errors. All subclass ValueError so existing fail-closed callers keep working."""
from __future__ import annotations


class ProducerContractError(ValueError):
    code = 'PRODUCER_CONTRACT_ERROR'

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message if field is None else f'{field}: {message}')
        self.field = field


class SchemaVersionError(ProducerContractError):
    code = 'SCHEMA_VERSION'


class MissingFieldError(ProducerContractError):
    code = 'MISSING_FIELD'


class TimestampError(ProducerContractError):
    code = 'TIMESTAMP'


class FreshnessContractError(ProducerContractError):
    code = 'FRESHNESS_CONTRACT'


class ProvenanceError(ProducerContractError):
    code = 'PROVENANCE'


class SourceHashError(ProducerContractError):
    code = 'SOURCE_HASH'


class SyntheticStateError(ProducerContractError):
    code = 'SYNTHETIC_STATE'


class UnsupportedStateError(ProducerContractError):
    code = 'UNSUPPORTED_STATE'


class ResearchStatusError(ProducerContractError):
    code = 'RESEARCH_STATUS_NOT_PUBLISHABLE'


class ValidationStatusError(ProducerContractError):
    code = 'VALIDATION_STATUS'


class IdentityError(ProducerContractError):
    code = 'IDENTITY'


class IncompatibleShapeError(ProducerContractError):
    """Upstream output exists but the Web schema-1 consumer reads a different shape.

    The assembler never reshapes upstream meaning; it publishes NOT_AVAILABLE instead.
    """
    code = 'INCOMPATIBLE_SHAPE'


class SerializationError(ProducerContractError):
    code = 'SERIALIZATION'
