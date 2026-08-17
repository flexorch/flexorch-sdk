from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Connector:
    id: str
    name: str
    type: str
    active: bool
    last_tested_at: str | None = None
    last_used_at: str | None = None
    created_at: str = ""

    @classmethod
    def _from_dict(cls, data: dict) -> Connector:
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", ""),
            active=data.get("active", True),
            last_tested_at=data.get("last_tested_at"),
            last_used_at=data.get("last_used_at"),
            created_at=data.get("created_at", ""),
        )

    def __repr__(self) -> str:
        return f"Connector(id={self.id!r}, name={self.name!r}, type={self.type!r}, active={self.active})"


@dataclass
class ConnectorTestResult:
    success: bool
    latency_ms: int | None = None
    message: str = ""

    @classmethod
    def _from_dict(cls, data: dict) -> ConnectorTestResult:
        return cls(
            success=data.get("success", False),
            latency_ms=data.get("latency_ms"),
            message=data.get("message", ""),
        )


@dataclass
class SyncSchedule:
    id: str
    connector_id: str
    cron_expression: str
    prefix_filter: str | None
    is_active: bool
    last_run_at: str | None = None
    next_run_at: str | None = None
    created_at: str = ""

    @classmethod
    def _from_dict(cls, data: dict) -> SyncSchedule:
        return cls(
            id=str(data.get("id", "")),
            connector_id=str(data.get("connector_id", "")),
            cron_expression=data.get("cron_expression", ""),
            prefix_filter=data.get("prefix_filter"),
            is_active=bool(data.get("is_active", True)),
            last_run_at=data.get("last_run_at"),
            next_run_at=data.get("next_run_at"),
            created_at=data.get("created_at", ""),
        )


@dataclass
class SyncLog:
    id: str
    schedule_id: str
    started_at: str
    completed_at: str | None
    files_found: int
    files_new: int
    files_skipped: int
    files_failed: int
    status: str
    error_message: str | None = None

    @classmethod
    def _from_dict(cls, data: dict) -> SyncLog:
        return cls(
            id=str(data.get("id", "")),
            schedule_id=str(data.get("schedule_id", "")),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            files_found=data.get("files_found", 0),
            files_new=data.get("files_new", 0),
            files_skipped=data.get("files_skipped", 0),
            files_failed=data.get("files_failed", 0),
            status=data.get("status", ""),
            error_message=data.get("error_message"),
        )
