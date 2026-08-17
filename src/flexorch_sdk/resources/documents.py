from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models.document import Document

if TYPE_CHECKING:
    from .._transport import Transport


class DocumentsResource:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def get(self, document_id: str) -> Document:
        """Fetch a single document, including processing_history and related_datasets."""
        data = self._t.get(f"/documents/{document_id}")
        return Document._from_dict(data, self._t)

    def list(self, page: int = 1, page_size: int = 20) -> list[Document]:
        """List documents for the current tenant, newest first."""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        data = self._t.get("/documents", params=params)
        items = data.get("items", data) if isinstance(data, dict) else data
        return [Document._from_dict(item, self._t) for item in items]
