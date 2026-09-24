"""File-backed raw dataset store. NEW IMPLEMENTATION.

A network-enabled runner (see tools/fetch_real_data.py, tools/fetch_sp500_intervals.py)
writes raw bytes + a provenance manifest here. Everything under validation/, qgv/,
technical/, macro/ reads only from this store (via ingestion/replay.py) and never
imports urllib — that keeps the Analysis Engine importable and runnable with zero
network access, satisfying environments where outbound HTTP is policy-blocked.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .manifest import RawArtifactManifest, build_manifest


class RawDatasetStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        (self.root / "blobs").mkdir(parents=True, exist_ok=True)
        (self.root / "manifests").mkdir(parents=True, exist_ok=True)
        (self.root / "history").mkdir(parents=True, exist_ok=True)

    def _blob_path(self, artifact_id: str) -> Path:
        # artifact ids may contain ':' (e.g. "companyfacts:0001045810"); safe as a filename.
        return self.root / "blobs" / artifact_id.replace(":", "__")

    def _manifest_path(self, artifact_id: str) -> Path:
        return self.root / "manifests" / (artifact_id.replace(":", "__") + ".json")

    def put(
        self,
        artifact_id: str,
        body: bytes,
        source_url: str,
        source_kind: str,
        content_type: str,
        fetcher: str,
        http_status: int | None = None,
        notes: str = "",
    ) -> RawArtifactManifest:
        m = build_manifest(artifact_id, source_url, source_kind, body, content_type, fetcher, http_status, notes)
        blob_path = self._blob_path(artifact_id)
        manifest_path = self._manifest_path(artifact_id)
        # Preserve every replaced raw artifact. The canonical artifact id remains
        # stable for offline replay, while history/<artifact>/<fetched_at>_<sha>/
        # makes repeated real ingests auditable instead of destructive.
        if blob_path.exists() and manifest_path.exists():
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            stamp = str(previous.get("fetched_at", "unknown")).replace(":", "-")
            sha = str(previous.get("sha256", "unknown"))[:12]
            hist = self.root / "history" / artifact_id.replace(":", "__") / f"{stamp}_{sha}"
            hist.mkdir(parents=True, exist_ok=True)
            shutil.copy2(blob_path, hist / "blob")
            shutil.copy2(manifest_path, hist / "manifest.json")
        blob_path.write_bytes(body)
        manifest_path.write_text(json.dumps(m.to_dict(), indent=2), encoding="utf-8")
        return m

    def list_history(self, artifact_id: str) -> list[Path]:
        root = self.root / "history" / artifact_id.replace(":", "__")
        return sorted(p for p in root.glob("*") if p.is_dir()) if root.exists() else []

    def has(self, artifact_id: str) -> bool:
        return self._blob_path(artifact_id).exists()

    def get_bytes(self, artifact_id: str) -> bytes:
        return self._blob_path(artifact_id).read_bytes()

    def get_manifest(self, artifact_id: str) -> dict:
        return json.loads(self._manifest_path(artifact_id).read_text(encoding="utf-8"))

    def list_ids(self) -> list[str]:
        return sorted(p.stem.replace("__", ":") for p in (self.root / "manifests").glob("*.json"))
