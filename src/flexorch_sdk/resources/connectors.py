from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models.connector import Connector, ConnectorTestResult, SyncLog, SyncSchedule

if TYPE_CHECKING:
    from .._transport import Transport

_VALID_TYPES = {
    "s3", "gcs", "azure_blob", "google_drive",
    "pgvector_external", "pinecone", "qdrant",
}


class ConnectorsResource:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def create(self, name: str, type: str, config: dict[str, Any]) -> Connector:
        """Register a new storage connector.

        Args:
            name:   Display name (e.g. "Production S3").
            type:   Connector type — "s3", "gcs", "azure_blob", "google_drive" (file
                    sources), or "pgvector_external", "pinecone", "qdrant" (vector
                    destinations for dataset indexing push_only/both modes).
            config: Provider-specific credentials dict.
                    S3 example: {"bucket": "...", "region": "...",
                                 "access_key_id": "...", "secret_access_key": "..."}
                    Google Drive example: {"folder_id": "...", "credentials_json": "..."}
                    (service account JSON; share the folder with its client_email first)
                    Pinecone example: {"api_key": "...", "index_name": "...", "namespace": "..."}
                    (create the index yourself first — dimension=768, metric=cosine)
                    Qdrant example: {"url": "...", "collection_name": "...", "api_key": "..."}
                    pgvector_external example: {"connection_string": "postgresql://..."}
        """
        if type not in _VALID_TYPES:
            raise ValueError(f"Unknown connector type {type!r}. Valid: {sorted(_VALID_TYPES)}")
        data = self._t.post("/connectors", json={"name": name, "type": type, "config": config})
        return Connector._from_dict(data)

    def list(self) -> list[Connector]:
        """Return all connectors for the current tenant."""
        data = self._t.get("/connectors")
        items = data.get("items", data) if isinstance(data, dict) else data
        return [Connector._from_dict(item) for item in items]

    def get(self, connector_id: str) -> Connector:
        """Fetch a single connector by ID."""
        data = self._t.get(f"/connectors/{connector_id}")
        return Connector._from_dict(data)

    def delete(self, connector_id: str) -> None:
        """Delete a connector (sets active=False on the backend)."""
        self._t.delete(f"/connectors/{connector_id}")

    def test(self, connector_id: str) -> ConnectorTestResult:
        """Run a connectivity test for a connector.

        Returns:
            :class:`ConnectorTestResult` with ``success``, ``latency_ms``, and ``message``.
        """
        data = self._t.post(f"/connectors/{connector_id}/test")
        return ConnectorTestResult._from_dict(data or {})

    def create_schedule(
        self,
        connector_id: str,
        cron_expression: str,
        prefix_filter: str | None = None,
    ) -> SyncSchedule:
        """Define a scheduled sync for a connector (Pro+ required).

        Args:
            connector_id:    ID of an active connector.
            cron_expression: e.g. "0 2 * * *" for every night at 02:00.
            prefix_filter:   Only pull keys matching this prefix; None = all.
        """
        data = self._t.post(
            f"/connectors/{connector_id}/schedules",
            json={"cron_expression": cron_expression, "prefix_filter": prefix_filter},
        )
        return SyncSchedule._from_dict(data or {})

    def list_schedules(self, connector_id: str) -> list[SyncSchedule]:
        """Return active schedules for a connector."""
        data = self._t.get(f"/connectors/{connector_id}/schedules")
        items = data if isinstance(data, list) else []
        return [SyncSchedule._from_dict(item) for item in items]

    def delete_schedule(self, connector_id: str, schedule_id: str) -> None:
        """Delete a scheduled sync."""
        self._t.delete(f"/connectors/{connector_id}/schedules/{schedule_id}")

    def trigger_schedule(self, connector_id: str, schedule_id: str) -> SyncLog:
        """Run a schedule immediately instead of waiting for its cron time."""
        data = self._t.post(f"/connectors/{connector_id}/schedules/{schedule_id}/trigger")
        return SyncLog._from_dict(data or {})

    def schedule_logs(self, connector_id: str, schedule_id: str) -> list[SyncLog]:
        """Return recent sync run logs for a schedule."""
        data = self._t.get(f"/connectors/{connector_id}/schedules/{schedule_id}/logs")
        items = data if isinstance(data, list) else []
        return [SyncLog._from_dict(item) for item in items]
