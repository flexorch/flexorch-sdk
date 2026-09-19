from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .._transport import Transport

_VALID_EVENTS = {"dataset.ready", "job.completed", "job.failed", "quota.warning"}


@dataclass
class Webhook:
    id: str
    url: str
    events: list[str]
    active: bool
    created_at: str
    auto_export: dict[str, Any] | None = None
    secret: str | None = None
    """Signing secret — only present on the response from register(). Store it
    securely; it is never returned again by list()/get()."""

    @classmethod
    def _from_dict(cls, data: dict) -> Webhook:
        return cls(
            id=data.get("id", ""),
            url=data.get("url", ""),
            events=data.get("events", []),
            active=data.get("active", True),
            created_at=data.get("created_at", ""),
            auto_export=data.get("auto_export"),
            secret=data.get("secret"),
        )

    def __repr__(self) -> str:
        return f"Webhook(id={self.id!r}, url={self.url!r}, events={self.events})"


class WebhooksResource:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def register(
        self,
        url: str,
        events: list[str],
        auto_export: dict[str, Any] | None = None,
    ) -> Webhook:
        """Register a new webhook endpoint.

        Args:
            url:    HTTPS URL that will receive POST requests.
            events: List of event types, e.g. ["dataset.ready"].
            auto_export: Optional, only meaningful with the "dataset.ready" event —
                automatically push the finished dataset to a connector on delivery.
                Shape: {"connector_id": int, "format": str, "prefix": str (optional,
                default "exports/")}.
        """
        invalid = set(events) - _VALID_EVENTS
        if invalid:
            raise ValueError(f"Unknown event types: {invalid}. Valid: {_VALID_EVENTS}")
        payload: dict[str, Any] = {"url": url, "events": events}
        if auto_export is not None:
            payload["auto_export"] = auto_export
        data = self._t.post("/webhooks", json=payload)
        return Webhook._from_dict(data)

    def list(self) -> list[Webhook]:
        """Return all registered webhooks for the current tenant."""
        data = self._t.get("/webhooks")
        items = data.get("items", data) if isinstance(data, dict) else data
        return [Webhook._from_dict(item) for item in items]

    def delete(self, webhook_id: str) -> None:
        """Delete a webhook by ID."""
        self._t.delete(f"/webhooks/{webhook_id}")
