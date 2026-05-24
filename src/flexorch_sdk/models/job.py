from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..errors import JobFailedError, TimeoutError

if TYPE_CHECKING:
    from .dataset import Dataset
    from .._transport import Transport

_TERMINAL_STATUSES = {"completed", "failed"}
_DEFAULT_POLL_INTERVAL = 2
_DEFAULT_TIMEOUT = 300


@dataclass
class Job:
    id: str
    status: str
    quality_grade: str | None = None
    quality_score: float | None = None
    document_id: str | None = None
    has_dataset: bool = False
    failure_reason: str | None = None
    created_at: str = ""
    completed_at: str | None = None
    _transport: Any = field(default=None, repr=False)

    @classmethod
    def _from_dict(cls, data: dict, transport: Transport) -> Job:
        return cls(
            id=data.get("job_id") or data.get("id", ""),
            status=data.get("status", ""),
            quality_grade=data.get("quality", {}).get("grade") if isinstance(data.get("quality"), dict) else data.get("quality_grade"),
            quality_score=data.get("quality", {}).get("score") if isinstance(data.get("quality"), dict) else data.get("quality_score"),
            document_id=data.get("document_id"),
            has_dataset=bool(data.get("has_dataset", False)),
            failure_reason=data.get("failure_reason"),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at"),
            _transport=transport,
        )

    def wait(
        self,
        timeout: int = _DEFAULT_TIMEOUT,
        poll_interval: int = _DEFAULT_POLL_INTERVAL,
    ) -> Job:
        """Poll until the job reaches a terminal status or timeout is exceeded."""
        if self.status in _TERMINAL_STATUSES:
            return self

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = self._transport.get(f"/jobs/{self.id}")
            updated = Job._from_dict(data, self._transport)
            self.__dict__.update(updated.__dict__)

            if self.status in _TERMINAL_STATUSES:
                break
            time.sleep(poll_interval)
        else:
            raise TimeoutError(self.id, timeout)

        if self.status == "failed":
            raise JobFailedError(self.id, self.failure_reason or "")

        return self

    def dataset(self) -> Dataset | None:
        """Return the dataset built from this job, if one exists."""
        from .dataset import Dataset

        if not self.has_dataset:
            return None
        data = self._transport.get("/datasets", params={"job_id": self.id})
        items = data.get("items", data) if isinstance(data, dict) else data
        if not items:
            return None
        return Dataset._from_dict(items[0], self._transport)

    def __repr__(self) -> str:
        return f"Job(id={self.id!r}, status={self.status!r}, grade={self.quality_grade!r})"
