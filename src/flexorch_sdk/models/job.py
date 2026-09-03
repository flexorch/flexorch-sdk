from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..errors import JobFailedError, TimeoutError

if TYPE_CHECKING:
    from .._transport import Transport
    from .dataset import Dataset

_TERMINAL_STATUSES = {"completed", "failed"}
_DEFAULT_POLL_INTERVAL = 2
_DEFAULT_TIMEOUT = 300


@dataclass
class JobFeedback:
    id: str
    job_id: str
    rating: str
    issue: str | None
    notes: str | None
    created_at: str = ""

    @classmethod
    def _from_dict(cls, data: dict) -> JobFeedback:
        return cls(
            id=str(data.get("id", "")),
            job_id=str(data.get("job_id", "")),
            rating=data.get("rating", ""),
            issue=data.get("issue"),
            notes=data.get("notes"),
            created_at=data.get("created_at", ""),
        )


@dataclass
class Job:
    id: str
    status: str
    quality_grade: str | None = None
    quality_score: float | None = None
    document_id: str | None = None
    execution_id: int | None = None
    dataset_id: int | None = None
    has_dataset: bool = False
    degraded: bool = False
    failure_reason: str | None = None
    pii_masked: bool = False
    pii_findings_count: int = 0
    pii_type_summary: dict[str, int] = field(default_factory=dict)
    created_at: str = ""
    completed_at: str | None = None
    _transport: Any = field(default=None, repr=False)

    @classmethod
    def _from_dict(cls, data: dict, transport: Transport) -> Job:
        execution_summary = data.get("execution_summary")
        processing_summary = data.get("processing_summary")
        dataset_summary = data.get("dataset_summary")
        privacy = execution_summary.get("privacy") if isinstance(execution_summary, dict) else None
        quality = data.get("quality")
        if not isinstance(quality, dict) and isinstance(processing_summary, dict):
            quality = processing_summary.get("quality")
        return cls(
            id=str(data.get("job_id") or data.get("id", "")),
            status=data.get("status", ""),
            quality_grade=quality.get("grade") if isinstance(quality, dict) else data.get("quality_grade"),
            quality_score=quality.get("score") if isinstance(quality, dict) else data.get("quality_score"),
            document_id=data.get("document_id"),
            # execution_summary.execution_id (data_process jobs) or
            # processing_summary.execution_id (raw UI job shape) — needed by
            # build_dataset() to call POST /datasets/build-from-execution/{id}.
            execution_id=(
                (execution_summary.get("execution_id") if isinstance(execution_summary, dict) else None)
                or (processing_summary.get("execution_id") if isinstance(processing_summary, dict) else None)
                or data.get("execution_id")
            ),
            # dataset_summary.dataset_id — present on a completed dataset_build
            # job's response (build_dataset() polls this job type). It's the
            # only place that job type reports the dataset it produced;
            # neither top-level has_dataset nor processing_summary is set for
            # dataset_build jobs, so without this .dataset() always returned
            # None for the job.build_dataset().wait().dataset() chain even
            # though the dataset had been built successfully.
            dataset_id=dataset_summary.get("dataset_id") if isinstance(dataset_summary, dict) else None,
            has_dataset=bool(data.get("has_dataset", False)) or bool(
                isinstance(processing_summary, dict) and processing_summary.get("has_dataset")
            ) or isinstance(dataset_summary, dict),
            # execution_summary.degraded — true when the underlying pipeline
            # execution completed but one or more non-critical steps failed
            # (e.g. structured extraction couldn't find a table in the
            # document). The job still succeeds and quality/PII results are
            # still meaningful, but structured `records`/columns may be
            # empty. Not present for jobs with no execution (e.g. dataset_build).
            degraded=bool(execution_summary.get("degraded", False)) if isinstance(execution_summary, dict) else False,
            failure_reason=data.get("failure_reason"),
            # execution_summary.privacy — computed fresh on every read
            # (GET /v1/jobs/{id}), not frozen at job-completion time, so it
            # stays correct even for jobs that predate a given PII detector
            # change. pii_type_summary defaults to {} for jobs with no
            # execution (e.g. dataset_build) or against an older API version.
            pii_masked=bool(privacy.get("privacy_applied", False)) if isinstance(privacy, dict) else False,
            pii_findings_count=privacy.get("pii_findings_count", 0) if isinstance(privacy, dict) else 0,
            pii_type_summary=dict(privacy.get("pii_type_summary", {})) if isinstance(privacy, dict) else {},
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

        if self.dataset_id is not None:
            data = self._transport.get(f"/datasets/{self.dataset_id}")
            return Dataset._from_dict(data, self._transport)

        if not self.has_dataset:
            return None
        data = self._transport.get("/datasets", params={"job_id": self.id})
        items = data.get("items", data) if isinstance(data, dict) else data
        if not items:
            return None
        return Dataset._from_dict(items[0], self._transport)

    def build_dataset(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        slug: str | None = None,
        force_rebuild: bool = False,
        replace_existing: bool = False,
    ) -> Job:
        """Build a dataset from this job's execution.

        A completed data_process job does not have a dataset yet — building
        one is a separate, explicit step (``POST
        /datasets/build-from-execution/{execution_id}``). Call this after
        ``.wait()``, then ``.wait()`` again on the returned dataset_build
        Job before calling ``.dataset()``::

            job = client.process("invoice.pdf").wait()
            dataset = job.build_dataset().wait().dataset()

        Raises:
            ValueError: If this job has no execution to build from (e.g. it
                failed, or is itself a dataset_build job).
        """
        if not self.execution_id:
            raise ValueError(
                f"Job {self.id!r} has no execution_id to build a dataset from "
                "(job must be a completed data_process job)."
            )
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
        data = self._transport.post(
            f"/datasets/build-from-execution/{self.execution_id}", json=body
        )
        return Job._from_dict(data, self._transport)

    def __repr__(self) -> str:
        return f"Job(id={self.id!r}, status={self.status!r}, grade={self.quality_grade!r})"
