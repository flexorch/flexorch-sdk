from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._transport import Transport

_VALID_EVENTS = {"dataset.ready", "job.completed", "job.failed"}


@dataclass
class Webhook:
    id: str
    url: str
    events: list[str]
    active: bool
    created_at: str

    @classmethod
    def _from_dict(cls, data: dict) -> Webhook:
        return cls(
            id=data.get("id", ""),
            url=data.get("url", ""),
            events=data.get("events", []),
            active=data.get("active", True),
            created_at=data.get("created_at", ""),
        )

    def __repr__(self) -> str:
        return f"Webhook(id={self.id!r}, url={self.url!r}, events={self.events})"


class WebhooksResource:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def register(self, url: str, events: list[str]) -> Webhook:
        """Register a new webhook endpoint.

        Args:
            url:    HTTPS URL that will receive POST requests.
            events: List of event types, e.g. ["dataset.ready"].
        """
        invalid = set(events) - _VALID_EVENTS
        if invalid:
            raise ValueError(f"Unknown event types: {invalid}. Valid: {_VALID_EVENTS}")
        data = self._t.post("/webhooks", json={"url": url, "events": events})
        return Webhook._from_dict(data)

    def list(self) -> list[Webhook]:
        """Return all registered webhooks for the current tenant."""
        data = self._t.get("/webhooks")
        items = data.get("items", data) if isinstance(data, dict) else data
        return [Webhook._from_dict(item) for item in items]

    def delete(self, webhook_id: str) -> None:
        """Delete a webhook by ID."""
        self._t.delete(f"/webhooks/{webhook_id}")
