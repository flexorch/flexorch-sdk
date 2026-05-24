from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .._transport import Transport

_SUPPORTED_FORMATS = {"json", "jsonl", "csv", "parquet", "md", "xml", "xlsx", "rag"}

_INDEX_STATUSES = {"not_indexed", "indexing", "ready", "failed"}


@dataclass
class Dataset:
    id: str
    name: str
    slug: str
    status: str
    row_count: int = 0
    created_at: str = ""
    available_formats: list[str] = field(default_factory=list)
    _transport: Any = field(default=None, repr=False)

    @classmethod
    def _from_dict(cls, data: dict, transport: Transport) -> Dataset:
        fmt_summary = data.get("format_summary", {})
        formats = list(fmt_summary.get("files", {}).keys()) if isinstance(fmt_summary, dict) else []
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            slug=data.get("slug", ""),
            status=data.get("status", ""),
            row_count=data.get("row_count", 0),
            created_at=data.get("created_at", ""),
            available_formats=formats,
            _transport=transport,
        )

    def export(self, format: str, path: str | Path | None = None) -> bytes:
        """Download dataset in the requested format.

        Args:
            format: One of json, jsonl, csv, parquet, md, xml, xlsx, rag.
            path:   If given, write bytes to this file and return them.
                    If None, return raw bytes without writing.

        Returns:
            Raw file content as bytes.
        """
        if format not in _SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format {format!r}. Choose from: {sorted(_SUPPORTED_FORMATS)}")

        raw = self._transport.get_bytes(
            f"/datasets/{self.id}/export",
            params={"format": format},
        )

        if path is not None:
            Path(path).write_bytes(raw)

        return raw

    def export_to_s3(
        self,
        connector_id: str,
        format: str,
        prefix: str = "",
    ) -> dict[str, Any]:
        """Push an exported file directly to an S3 connector.

        Args:
            connector_id: ID of an active S3 connector.
            format:       Export format (same set as :meth:`export`).
            prefix:       Optional S3 key prefix (e.g. "exports/datasets/").

        Returns:
            Dict with ``s3_key`` and ``size_bytes``.
        """
        if format not in _SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format {format!r}. Choose from: {sorted(_SUPPORTED_FORMATS)}")
        return self._transport.post(
            f"/datasets/{self.id}/export-s3",
            json={"format": format, "connector_id": connector_id, "prefix": prefix},
        )

    def index(self) -> dict[str, Any]:
        """Trigger semantic indexing for this dataset (Pro+ plan required).

        Returns:
            Dict with ``status`` and ``message``.
        """
        return self._transport.post(f"/datasets/{self.id}/index") or {}

    def index_status(self) -> dict[str, Any]:
        """Return the current semantic index status.

        Returns:
            Dict with ``status`` (not_indexed | indexing | ready | failed),
            ``chunks_indexed``, and ``total_chunks``.
        """
        return self._transport.get(f"/datasets/{self.id}/index/status") or {}

    def __repr__(self) -> str:
        return f"Dataset(id={self.id!r}, name={self.name!r}, rows={self.row_count}, status={self.status!r})"
