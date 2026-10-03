"""Provider-neutral news ingestion boundary for RIG. Not a news provider."""

from .contract import CONTRACT, METHODOLOGY_VERSION, SCHEMA_VERSION
from .entities import AliasIndex, index_from_registry
from .pipeline import ingest

__all__ = [
    "CONTRACT",
    "SCHEMA_VERSION",
    "METHODOLOGY_VERSION",
    "AliasIndex",
    "index_from_registry",
    "ingest",
]
