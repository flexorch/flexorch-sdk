from __future__ import annotations

import time
from typing import Any

import httpx

from .errors import (
    AuthError,
    FlexOrchError,
    NotFoundError,
    QuotaError,
    RateLimitError,
    ServerError,
    ValidationError,
)

_DEFAULT_BASE_URL = "https://api.flexorch.com/v1"
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_MAX_RETRIES = 3
_RETRY_STATUSES = {429, 500, 502, 503, 504}


def _parse_error(response: httpx.Response) -> FlexOrchError:
    status = response.status_code
    try:
        body = response.json()
        error_block = body.get("error", {})
        code = error_block.get("code", "")
        message = error_block.get("message", response.text)
    except Exception:
        code = ""
        message = response.text or f"HTTP {status}"

    if status == 401:
        return AuthError(message, status_code=status, error_code=code)
    if status in (402,):
        return QuotaError(message, status_code=status, error_code=code)
    if status == 404:
        return NotFoundError(message, status_code=status, error_code=code)
    if status == 422:
        return ValidationError(message, status_code=status, error_code=code)
    if status == 429:
        retry_after = int(response.headers.get("Retry-After", 60))
        return RateLimitError(message, retry_after=retry_after)
    if status >= 500:
        return ServerError(message, status_code=status, error_code=code)
    return FlexOrchError(message, status_code=status, error_code=code)


class Transport:
    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._client = httpx.Client(
            headers={
                "X-API-KEY": api_key,
                "User-Agent": "flexorch-sdk-python/0.1.0",
            },
            timeout=timeout,
        )

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = self._url(path)
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)
                continue

            if response.status_code in _RETRY_STATUSES and attempt < self._max_retries - 1:
                wait = int(response.headers.get("Retry-After", 2 ** attempt))
                time.sleep(wait)
                continue

            if response.is_error:
                raise _parse_error(response)

            if response.status_code == 204 or not response.content:
                return None
            return response.json()

        raise FlexOrchError(f"Request failed after {self._max_retries} attempts: {last_exc}")

    def get(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs)

    def get_bytes(self, path: str, **kwargs: Any) -> bytes:
        """GET that returns raw response bytes (for file download endpoints)."""
        url = self._url(path)
        response = self._client.request("GET", url, **kwargs)
        if response.is_error:
            raise _parse_error(response)
        return response.content

    def post(self, path: str, **kwargs: Any) -> Any:
        return self._request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self._request("DELETE", path, **kwargs)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Transport:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
