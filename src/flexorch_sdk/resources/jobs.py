from __future__ import annotations

from typing import TYPE_CHECKING

from ..models.job import Job

if TYPE_CHECKING:
    from .._transport import Transport


class JobsResource:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def get(self, job_id: str) -> Job:
        """Fetch a single job by ID."""
        data = self._t.get(f"/jobs/{job_id}")
        return Job._from_dict(data, self._t)

    def list(self, page: int = 1, page_size: int = 20) -> list[Job]:
        """List jobs for the current tenant, newest first."""
        data = self._t.get("/jobs", params={"page": page, "page_size": page_size})
        items = data.get("items", data) if isinstance(data, dict) else data
        return [Job._from_dict(item, self._t) for item in items]
