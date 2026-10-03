"""Fail-closed errors for the Technical real-input producer. Not a new model."""

from __future__ import annotations


class TechnicalProducerError(ValueError):
    code = "TECHNICAL_PRODUCER"

    def __init__(self, message: str):
        super().__init__(f"{self.code}: {message}")


class FutureInputError(TechnicalProducerError):
    code = "FUTURE_INPUT"


class MissingProvenanceError(TechnicalProducerError):
    code = "MISSING_PROVENANCE"


class MissingLookbackError(TechnicalProducerError):
    code = "MISSING_LOOKBACK"


class CompanyIdentityError(TechnicalProducerError):
    code = "COMPANY_IDENTITY"


class PublicationError(TechnicalProducerError):
    code = "PUBLICATION_BLOCKED"


class SyntheticLiveError(PublicationError):
    code = "SYNTHETIC_LIVE"
