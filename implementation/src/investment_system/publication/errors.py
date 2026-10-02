"""Fail-closed errors for publication. Not an investment result."""


class PublicationContractError(ValueError):
    code = "PUBLICATION_CONTRACT"

    def __init__(self, message: str):
        super().__init__(f"{self.code}: {message}")


class AuthorizationError(PublicationContractError):
    code = "AUTHORIZATION"


class ExtractionError(PublicationContractError):
    code = "EXTRACTION"


class PromotionForbidden(PublicationContractError):
    code = "PROMOTION_FORBIDDEN"
