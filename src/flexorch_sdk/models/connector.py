from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
