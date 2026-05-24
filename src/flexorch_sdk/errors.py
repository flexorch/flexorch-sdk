from __future__ import annotations


class FlexOrchError(Exception):
    """Base exception for all FlexOrch SDK errors."""

    def __init__(self, message: str, status_code: int = 0, error_code: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.args[0]!r}, status={self.status_code}, code={self.error_code!r})"


class AuthError(FlexOrchError):
    """Invalid or missing API key (401)."""


class QuotaError(FlexOrchError):
    """Credit quota exceeded or trial expired (402 / 429)."""

    def __init__(
        self,
        message: str,
        status_code: int = 402,
        error_code: str = "",
        remaining_credits: int = 0,
        reset_at: str = "",
    ) -> None:
        super().__init__(message, status_code, error_code)
        self.remaining_credits = remaining_credits
        self.reset_at = reset_at


class RateLimitError(FlexOrchError):
    """Too many requests — slow down (429 with rate-limit context)."""

    def __init__(
        self,
        message: str,
        retry_after: int = 60,
    ) -> None:
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_EXCEEDED")
        self.retry_after = retry_after


class NotFoundError(FlexOrchError):
    """Requested resource does not exist (404)."""


class ValidationError(FlexOrchError):
    """Request payload failed validation (422)."""


class ServerError(FlexOrchError):
    """Unexpected server-side error (5xx)."""


class JobFailedError(FlexOrchError):
    """Job completed with status=failed — pipeline could not process the document."""

    def __init__(self, job_id: str, reason: str = "") -> None:
        super().__init__(f"Job {job_id!r} failed: {reason or 'unknown reason'}")
        self.job_id = job_id
        self.failure_reason = reason


class TimeoutError(FlexOrchError):  # noqa: A001
    """job.wait() exceeded the requested timeout without completing."""

    def __init__(self, job_id: str, timeout: int) -> None:
        super().__init__(f"Job {job_id!r} did not complete within {timeout}s")
        self.job_id = job_id
        self.timeout = timeout
