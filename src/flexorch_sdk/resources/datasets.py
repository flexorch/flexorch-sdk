from __future__ import annotations

from typing import TYPE_CHECKING

from ..models.dataset import Dataset

if TYPE_CHECKING:
    from .._transport import Transport


class DatasetsResource:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def get(self, dataset_id: str) -> Dataset:
        """Fetch a single dataset by ID."""
        data = self._t.get(f"/datasets/{dataset_id}")
        return Dataset._from_dict(data, self._t)

    def list(self, page: int = 1, page_size: int = 20) -> list[Dataset]:
        """List datasets for the current tenant, newest first."""
        data = self._t.get("/datasets", params={"page": page, "page_size": page_size})
        items = data.get("items", data) if isinstance(data, dict) else data
        return [Dataset._from_dict(item, self._t) for item in items]
