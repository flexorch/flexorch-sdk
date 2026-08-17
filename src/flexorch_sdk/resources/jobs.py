from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models.job import Job, JobFeedback

if TYPE_CHECKING:
    from .._transport import Transport

_VALID_RATINGS = {"up", "down"}
_VALID_ISSUES = {
    "wrong_doc_type", "missing_fields", "wrong_values",
    "pii_missed", "pii_over_masked", "other",
}


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

    def submit_feedback(
        self,
        job_id: str,
        rating: str,
        *,
        issue: str | None = None,
        notes: str | None = None,
    ) -> JobFeedback:
        """Submit user feedback for a completed job. Upsert — a second call

        for the same job replaces the previous feedback.

        Args:
            rating: "up" or "down".
            issue:  When rating="down", one of "wrong_doc_type",
                    "missing_fields", "wrong_values", "pii_missed",
                    "pii_over_masked", "other".
            notes:  Optional free-text notes.
        """
        if rating not in _VALID_RATINGS:
            raise ValueError(f"Invalid rating {rating!r}. Valid: {sorted(_VALID_RATINGS)}")
        if issue is not None and issue not in _VALID_ISSUES:
            raise ValueError(f"Invalid issue {issue!r}. Valid: {sorted(_VALID_ISSUES)}")
        body: dict[str, Any] = {"rating": rating, "issue": issue, "notes": notes}
        data = self._t.post(f"/jobs/{job_id}/feedback", json=body)
        return JobFeedback._from_dict(data or {})

    def get_feedback(self, job_id: str) -> JobFeedback | None:
        """Return existing feedback for a job, or None if none was submitted."""
        data = self._t.get(f"/jobs/{job_id}/feedback")
        if not data:
            return None
        return JobFeedback._from_dict(data)
