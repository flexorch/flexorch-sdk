"""Tests for Transport — envelope unwrapping, retries, error mapping."""
import pytest
import respx
import httpx

from flexorch_sdk._transport import Transport, _unwrap
from flexorch_sdk.errors import AuthError

BASE = "https://api.flexorch.com/v1"


def test_unwrap_strips_standard_envelope():
    body = {"status": "success", "data": {"id": "j1"}, "error": None}
    assert _unwrap(body) == {"id": "j1"}


def test_unwrap_strips_accepted_envelope_with_meta():
    body = {"status": "accepted", "data": {"job_id": 1}, "error": None, "meta": {"poll": "/v1/jobs/1"}}
    assert _unwrap(body) == {"job_id": 1}


def test_unwrap_handles_null_data():
    body = {"status": "success", "data": None, "error": None}
    assert _unwrap(body) is None


def test_unwrap_handles_list_data():
    body = {"status": "success", "data": [1, 2, 3], "error": None}
    assert _unwrap(body) == [1, 2, 3]


def test_unwrap_leaves_non_envelope_dicts_alone():
    # Defensive fallback — a dict missing "error" or "status" isn't the
    # standard wrapper, so it's returned as-is rather than guessed at.
    body = {"foo": "bar"}
    assert _unwrap(body) == body


@respx.mock
def test_transport_get_unwraps_real_response():
    respx.get(f"{BASE}/jobs/j1").mock(
        return_value=httpx.Response(200, json={"status": "success", "data": {"job_id": "j1", "status": "completed"}, "error": None})
    )
    t = Transport(api_key="fx_test", base_url=BASE)
    result = t.get("/jobs/j1")
    assert result == {"job_id": "j1", "status": "completed"}


@respx.mock
def test_transport_401_raises_auth_error_without_unwrap_crash():
    # Error bodies don't go through _unwrap at all (raised before json() is
    # parsed for the envelope) — just confirm the error path still works.
    respx.get(f"{BASE}/jobs/j1").mock(
        return_value=httpx.Response(401, json={"error": {"code": "INVALID_API_KEY", "message": "bad key"}})
    )
    t = Transport(api_key="fx_test", base_url=BASE)
    with pytest.raises(AuthError):
        t.get("/jobs/j1")
