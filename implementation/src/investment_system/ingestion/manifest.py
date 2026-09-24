"""Provenance manifest for raw datasets fetched by a network-enabled runner.

Ingestion provenance (when/where WE fetched something) is not PIT data
availability (when the filer/exchange published it). Do not conflate:
as_of gating for QGV/Technical/Macro keeps using the source's own filed /
observed timestamps parsed out of the raw content by the existing parsers
(sec_companyfacts, yahoo_chart, sec_submissions) — never fetched_at.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RawArtifactManifest:
    artifact_id: str
    source_url: str
    source_kind: str  # SEC_COMPANYFACTS | SEC_SUBMISSIONS | SEC_TICKERS | YAHOO_CHART | SP500_INTERVALS | ...
    fetched_at: str  # ingestion time (UTC ISO) - NOT a PIT availability timestamp
    sha256: str
    bytes: int
    content_type: str
    fetcher: str  # tool + version string that performed the fetch
    http_status: int | None = None
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def build_manifest(
    artifact_id: str,
    source_url: str,
    source_kind: str,
    body: bytes,
    content_type: str,
    fetcher: str,
    http_status: int | None = None,
    notes: str = "",
) -> RawArtifactManifest:
    return RawArtifactManifest(
        artifact_id=artifact_id,
        source_url=source_url,
        source_kind=source_kind,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        sha256=hashlib.sha256(body).hexdigest(),
        bytes=len(body),
        content_type=content_type,
        fetcher=fetcher,
        http_status=http_status,
        notes=notes,
    )
