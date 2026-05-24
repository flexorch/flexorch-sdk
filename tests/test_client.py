"""Tests for FlexOrchClient — process(), process_many(), error handling."""
import pytest
import respx
import httpx

from flexorch_sdk import FlexOrchClient, AuthError, ValidationError, FlexOrchError

BASE = "https://api.flexorch.com/v1"


@pytest.fixture
def client(tmp_path):
    return FlexOrchClient("fx_test_key", base_url=BASE)


def test_no_api_key_raises():
    import os
    env_backup = os.environ.pop("FLEXORCH_API_KEY", None)
    try:
        with pytest.raises(ValueError, match="No API key"):
            FlexOrchClient()
    finally:
        if env_backup is not None:
            os.environ["FLEXORCH_API_KEY"] = env_backup


def test_env_variable_key(monkeypatch):
    monkeypatch.setenv("FLEXORCH_API_KEY", "fx_from_env")
    c = FlexOrchClient()
    assert "fx_from_env" in c._transport._client.headers["x-api-key"]


def test_context_manager():
    with FlexOrchClient("fx_test") as c:
        assert c is not None


@respx.mock
def test_process_returns_job(tmp_path, client):
    pdf = tmp_path / "contract.pdf"
    pdf.write_bytes(b"%PDF fake content")

    respx.post(f"{BASE}/data-process/async").mock(
        return_value=httpx.Response(202, json={
            "job_id": "job-123",
            "status": "queued",
            "document_id": "doc-456",
        })
    )

    job = client.process(pdf)
    assert job.id == "job-123"
    assert job.status == "queued"


@respx.mock
def test_process_file_not_found(client):
    with pytest.raises(FileNotFoundError):
        client.process("/nonexistent/file.pdf")


@respx.mock
def test_process_401_raises_auth_error(tmp_path, client):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"data")

    respx.post(f"{BASE}/data-process/async").mock(
        return_value=httpx.Response(401, json={"error": {"code": "INVALID_API_KEY", "message": "Invalid key"}})
    )

    with pytest.raises(AuthError):
        client.process(pdf)


@respx.mock
def test_process_422_raises_validation_error(tmp_path, client):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"data")

    respx.post(f"{BASE}/data-process/async").mock(
        return_value=httpx.Response(422, json={"error": {"code": "UNSUPPORTED_FILE", "message": "Bad file"}})
    )

    with pytest.raises(ValidationError):
        client.process(pdf)


@respx.mock
def test_process_many(tmp_path, client):
    for name in ["a.pdf", "b.pdf"]:
        (tmp_path / name).write_bytes(b"data")

    respx.post(f"{BASE}/data-process/async").mock(
        return_value=httpx.Response(202, json={"job_id": "job-x", "status": "queued"})
    )

    jobs = client.process_many([tmp_path / "a.pdf", tmp_path / "b.pdf"])
    assert len(jobs) == 2
    assert all(j.id == "job-x" for j in jobs)
