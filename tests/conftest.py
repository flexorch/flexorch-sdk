"""Shared test helpers.

The real API wraps every /v1/* response in {status, data, error} (see
dev-docs/api-reference.md "Standart Response Wrapper" in the flexorch repo).
Transport._request() unwraps this and hands resources the `data` payload —
these tests mock the *wrapped* shape so they actually exercise that unwrap
step instead of assuming it away.
"""
from typing import Any


def envelope(data: Any, status: str = "success", meta: dict | None = None) -> dict:
    body: dict[str, Any] = {"status": status, "data": data, "error": None}
    if meta is not None:
        body["meta"] = meta
    return body


def accepted(data: Any, meta: dict | None = None) -> dict:
    return envelope(data, status="accepted", meta=meta or {"poll": "/v1/jobs/{id}"})
