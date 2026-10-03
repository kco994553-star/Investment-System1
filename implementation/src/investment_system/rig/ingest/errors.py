"""Fail-closed errors for provider-neutral news ingestion.

Codes are part of the contract. Callers branch on ``code``, not on message text.
"""

from __future__ import annotations


class IngestError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
