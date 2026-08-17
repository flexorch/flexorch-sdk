from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .._transport import Transport
    from .job import Job


@dataclass
class Document:
    id: str
    filename: str
    file_ext: str
    status: str
    storage_path: str
    created_at: str = ""
    processing_count: int = 0
    latest_execution: dict[str, Any] | None = None
    dataset: dict[str, Any] | None = None
    processing_history: list[dict[str, Any]] = field(default_factory=list)
    related_datasets: list[dict[str, Any]] = field(default_factory=list)
    _transport: Any = field(default=None, repr=False)

    @classmethod
    def _from_dict(cls, data: dict, transport: Transport) -> Document:
        return cls(
            id=str(data.get("id", "")),
            filename=data.get("filename", ""),
            file_ext=data.get("file_ext", ""),
            status=data.get("status", ""),
            storage_path=data.get("storage_path", ""),
            created_at=data.get("created_at", ""),
            processing_count=data.get("processing_count", 0),
            latest_execution=data.get("latest_execution"),
            dataset=data.get("dataset"),
            processing_history=data.get("processing_history", []),
            related_datasets=data.get("related_datasets", []),
            _transport=transport,
        )

    def reprocess(self, pipeline_config: dict[str, Any] | None = None) -> Job:
        """Re-queue this document through the processing pipeline.

        Raises (via the API): 400 DOCUMENT_FILE_NOT_AVAILABLE if the source
        file is no longer on disk, or 400 REPROCESS_NOT_SUPPORTED for
        connector-sourced (e.g. S3) documents.
        """
        from .job import Job

        body: dict[str, Any] = {}
        if pipeline_config:
            body["pipeline_config"] = pipeline_config
        data = self._transport.post(f"/documents/{self.id}/reprocess", json=body)
        return Job._from_dict(data, self._transport)

    def __repr__(self) -> str:
        return f"Document(id={self.id!r}, filename={self.filename!r}, status={self.status!r})"
