from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models.dataset import Dataset
from ..models.job import Job

if TYPE_CHECKING:
    from .._transport import Transport


class DatasetsResource:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def get(self, dataset_id: str) -> Dataset:
        """Fetch a single dataset by ID."""
        data = self._t.get(f"/datasets/{dataset_id}")
        return Dataset._from_dict(data, self._t)

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        *,
        status: str | None = None,
        source_execution_id: int | None = None,
        source_document_id: int | None = None,
        q: str | None = None,
    ) -> list[Dataset]:
        """List datasets for the current tenant, newest first."""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if status is not None:
            params["status"] = status
        if source_execution_id is not None:
            params["source_execution_id"] = source_execution_id
        if source_document_id is not None:
            params["source_document_id"] = source_document_id
        if q is not None:
            params["q"] = q
        data = self._t.get("/datasets", params=params)
        items = data.get("items", data) if isinstance(data, dict) else data
        return [Dataset._from_dict(item, self._t) for item in items]

    def build_from_execution(
        self,
        execution_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        slug: str | None = None,
        force_rebuild: bool = False,
        replace_existing: bool = False,
    ) -> Job:
        """Build a dataset from a completed execution.

        Prefer ``Job.build_dataset()`` when you already have a Job object —
        this is the lower-level call for when you only have an execution_id
        (e.g. from ``Document.latest_execution``).

        Returns:
            A dataset_build :class:`Job` — call ``.wait()`` then ``.dataset()``.
        """
        body: dict[str, Any] = {
            "force_rebuild": force_rebuild,
            "replace_existing": replace_existing,
        }
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if slug is not None:
            body["slug"] = slug
        data = self._t.post(f"/datasets/build-from-execution/{execution_id}", json=body)
        return Job._from_dict(data, self._t)
