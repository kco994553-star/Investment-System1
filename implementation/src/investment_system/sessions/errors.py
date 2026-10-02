"""Fail-closed errors for the session contract. Not a Technical model."""

from __future__ import annotations


class SessionContractError(ValueError):
    code = "SESSION_CONTRACT"

    def __init__(self, message: str):
        super().__init__(f"{self.code}: {message}")


class ProvenanceMismatch(SessionContractError):
    code = "PROVENANCE_MISMATCH"


class DuplicateSessionBar(SessionContractError):
    code = "DUPLICATE_SESSION_BAR"
