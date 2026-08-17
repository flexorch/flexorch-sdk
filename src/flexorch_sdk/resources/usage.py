from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._transport import Transport


@dataclass
class UsageSnapshot:
    plan: str
    credits_used: int
    credits_limit: int | None
    credits_remaining: int | None
    is_trial: bool
    trial_ends_at: str | None
    trial_days_remaining: int | None

    @classmethod
    def _from_dict(cls, data: dict) -> UsageSnapshot:
        trial = data.get("trial") or {}
        credits = (data.get("usage") or {}).get("credits") or {}
        return cls(
            plan=data.get("plan", ""),
            credits_used=credits.get("used", 0),
            credits_limit=credits.get("limit"),
            credits_remaining=credits.get("remaining"),
            is_trial=bool(trial.get("is_trial", False)),
            trial_ends_at=trial.get("trial_ends_at"),
            trial_days_remaining=trial.get("trial_days_remaining"),
        )

    def __repr__(self) -> str:
        return (
            f"UsageSnapshot(plan={self.plan!r}, "
            f"used={self.credits_used}/{self.credits_limit}, "
            f"remaining={self.credits_remaining})"
        )


@dataclass
class UsageHistoryItem:
    date: str
    credits_used: int
    jobs_count: int

    @classmethod
    def _from_dict(cls, data: dict) -> UsageHistoryItem:
        return cls(
            date=data.get("date", ""),
            credits_used=data.get("credits_used", 0),
            jobs_count=data.get("jobs_count", 0),
        )


@dataclass
class QualityTrendItem:
    date: str
    avg_quality_score: float
    grade_distribution: dict[str, int]
    avg_field_fill_rate: float | None
    job_count: int

    @classmethod
    def _from_dict(cls, data: dict) -> QualityTrendItem:
        return cls(
            date=data.get("date", ""),
            avg_quality_score=data.get("avg_quality_score", 0.0),
            grade_distribution=data.get("grade_distribution", {}),
            avg_field_fill_rate=data.get("avg_field_fill_rate"),
            job_count=data.get("job_count", 0),
        )


@dataclass
class RateLimitStatus:
    plan: str
    unlimited: bool
    limit: int | None
    used: int | None
    remaining: int | None
    window_seconds: int
    reset_in_seconds: int | None

    @classmethod
    def _from_dict(cls, data: dict) -> RateLimitStatus:
        return cls(
            plan=data.get("plan", ""),
            unlimited=bool(data.get("unlimited", False)),
            limit=data.get("limit"),
            used=data.get("used"),
            remaining=data.get("remaining"),
            window_seconds=data.get("window_seconds", 0),
            reset_in_seconds=data.get("reset_in_seconds"),
        )


class UsageResource:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def current(self) -> UsageSnapshot:
        """Return the current billing period usage and credit balance."""
        data = self._t.get("/usage")
        return UsageSnapshot._from_dict(data or {})

    def history(self, period: str = "30d") -> list[UsageHistoryItem]:
        """Return daily credit consumption and completed-job counts.

        Args:
            period: "7d", "30d", or "90d". Default: "30d".
        """
        data = self._t.get("/usage/history", params={"period": period})
        items = data if isinstance(data, list) else []
        return [UsageHistoryItem._from_dict(item) for item in items]

    def quality_trend(self, period: str = "30d") -> list[QualityTrendItem]:
        """Return the daily pipeline quality trend.

        Args:
            period: "7d", "30d", or "90d". Default: "30d".
        """
        data = self._t.get("/usage/quality-trend", params={"period": period})
        items = data if isinstance(data, list) else []
        return [QualityTrendItem._from_dict(item) for item in items]

    def rate_limits(self) -> RateLimitStatus:
        """Return the current rate limit configuration and window usage.

        Does not consume a request slot.
        """
        data = self._t.get("/usage/rate-limits")
        return RateLimitStatus._from_dict(data or {})
