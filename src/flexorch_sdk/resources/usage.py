from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._transport import Transport


@dataclass
class UsageSnapshot:
    plan: str
    credits_used: int
    credits_limit: int
    credits_remaining: int
    reset_at: str
    period_start: str
    period_end: str

    @classmethod
    def _from_dict(cls, data: dict) -> UsageSnapshot:
        return cls(
            plan=data.get("plan", ""),
            credits_used=data.get("credits_used", 0),
            credits_limit=data.get("credits_limit", 0),
            credits_remaining=data.get("credits_remaining", 0),
            reset_at=data.get("reset_at", ""),
            period_start=data.get("period_start", ""),
            period_end=data.get("period_end", ""),
        )

    def __repr__(self) -> str:
        return (
            f"UsageSnapshot(plan={self.plan!r}, "
            f"used={self.credits_used}/{self.credits_limit}, "
            f"remaining={self.credits_remaining})"
        )


class UsageResource:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def current(self) -> UsageSnapshot:
        """Return the current billing period usage and credit balance."""
        data = self._t.get("/usage/current")
        return UsageSnapshot._from_dict(data)
